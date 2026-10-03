"""Scoped aliases, small report deltas and exact field corrections (wire v5)."""
from copy import deepcopy
from pydantic import ValidationError
from tools.platform_store import plain
from tools.platform_handoff import pointer
from tools.diagnostic_facts import resolve_handles
from schemas.diagnostic_revision import CompactRevision, Corrections


def ensure_aliases(state):
    scope=state['fact_scope']
    table=state.setdefault('reference_interface',dict(version='1.0.0',scope=deepcopy(scope),aliases={}))
    if table['scope']!=scope:raise ValueError('REFERENCE_SCOPE_CHANGED')
    aliases=table['aliases'];known=set(aliases.values())
    if len(known)!=len(aliases) or known-set(state['fact_catalog']):raise ValueError('AMBIGUOUS_OR_MISSING_ALIAS_BINDING')
    for handle in sorted(set(state['fact_catalog'])-known):aliases['F%03d'%(len(aliases)+1)]=handle
    return table


def alias_errors(state, selections, prefix='fact_handles'):
    aliases=ensure_aliases(state)['aliases'];errors=[]
    if not isinstance(selections,dict):return errors
    for key,refs in selections.items():
        if not isinstance(refs,list) or not refs:
            errors.append(dict(path=prefix+'.'+key,submitted=refs,expected='Nonempty list of exact scope aliases'));continue
        for i,ref in enumerate(refs):
            if not isinstance(ref,str) or ref not in aliases:
                errors.append(dict(path=f'{prefix}.{key}.{i}',submitted=ref,expected='Unknown or out-of-scope alias. Copy an exact alias from the supplied reference_view; no lookup is required.'))
    return errors


def resolve_aliases(state, selections):
    errors=alias_errors(state,selections)
    if errors:raise ValueError(str(errors))
    table=ensure_aliases(state)['aliases']
    return resolve_handles(state,{k:[table[x] for x in refs] for k,refs in selections.items()})


def correct(draft, corrections):
    value=deepcopy(draft)
    for change in Corrections.model_validate(corrections).corrections:
        if not change.path.startswith('/') or change.path=='/':raise ValueError('EXISTING_FIELD_POINTER_REQUIRED')
        parent_path,_,key=change.path.rpartition('/');parent=pointer(value,parent_path)
        key=key.replace('~1','/').replace('~0','~')
        if isinstance(parent,list):
            if not key.isdigit() or int(key)>=len(parent):raise ValueError('CORRECTION_FIELD_MISSING: '+change.path)
            key=int(key)
        elif not isinstance(parent,dict) or key not in parent:raise ValueError('CORRECTION_FIELD_MISSING: '+change.path)
        if change.operation=='remove':del parent[key]
        else:parent[key]=deepcopy(change.value)
    return value


def materialize(initial, revision, state):
    delta=CompactRevision.model_validate(revision);report=deepcopy(initial)
    ids={f['fact_id'] for f in report['report']['facts']}
    selectors=resolve_aliases(state,{f.fact_id:f.references for f in delta.new_facts})
    for fact in delta.new_facts:
        if fact.fact_id in ids:raise ValueError('NEW_FACT_ID_ALREADY_EXISTS: '+fact.fact_id)
        ids.add(fact.fact_id);sources=selectors[fact.fact_id]
        report['report']['facts'].append(dict(fact_id=fact.fact_id,statement=fact.statement,
            evidence=list({s['reference']['artifact_id']:s['reference'] for s in sources}.values()),observed=None))
        report['fact_selectors'][fact.fact_id]=sources
    seen=set()
    for change in delta.changes:
        key=(change.kind,change.identifier)
        if key in seen:raise ValueError('DUPLICATE_ASSESSMENT_CHANGE: '+str(key))
        seen.add(key)
        if set(change.supporting_fact_ids)-ids:raise ValueError('CHANGE_FACT_NOT_DECLARED: '+change.identifier)
        rows=report['report']['attribution'] if change.kind=='hypothesis' else report['recommendations']
        field='cause' if change.kind=='hypothesis' else 'recommendation_id'
        row=next((r for r in rows if r[field]==change.identifier),None)
        if row is None:raise ValueError('PREVIOUS_ASSESSMENT_NOT_FOUND: '+change.identifier)
        if change.kind=='hypothesis':
            if change.disposition!='retained':row['status']={'weakened':'possible','rejected':'ruled_out','unresolved':'insufficient_evidence'}[change.disposition]
            row['fact_ids']=list(dict.fromkeys(row['fact_ids']+change.supporting_fact_ids));row['reason']=change.reason
        else:
            row['rationale']=change.disposition+': '+change.reason
            if change.disposition in ('rejected','unresolved','weakened'):row.update(action='defer',parameter=None,value=None)
        report['report']['recommended_actions'].append(f'{change.kind} {change.identifier}: {change.disposition}. {change.reason}')
    report['report']['limitations']+=delta.new_limitations
    report['report']['recommended_actions'].append(delta.recommendation+' '+delta.rationale)
    configuration=next(iter(initial['recommendations']),{}).get('configuration_scope')
    if configuration:
        if any(r['recommendation_id']=='revision_recommendation' for r in report['recommendations']):
            raise ValueError('REVISION_RECOMMENDATION_ID_ALREADY_EXISTS')
        report['recommendations'].append(dict(recommendation_id='revision_recommendation',action='defer',parameter=None,value=None,
            rationale=delta.recommendation+' '+delta.rationale,configuration_scope=configuration))
    return report


def comparison_view(role, state):
    feedback=role.get('improvement_feedback_content')
    if not feedback:return None
    aliases=ensure_aliases(state)['aliases'];reverse={v:k for k,v in aliases.items()}
    result=feedback.get('execution') or {};profile=result.get('receipts',{}).get('profile',{}).get('output')
    comparison=feedback.get('campaign_comparison')
    fields={}
    for h,row in state['fact_catalog'].items():
        p=row['selector']['pointer']
        if p.startswith('/campaign_comparison/') or (row['selector']['reference']==profile and
            (p.startswith('/detail/sampled_settling/') or p in {'/detail/terminal_error_m','/detail/mean_update_s','/detail/evaluation_validity'})):
            fields[reverse[h]]=dict(field=row['field'],value=row['value'],units=row['units'])
    return dict(comparison=comparison,identities=dict(baseline=feedback['baseline_facts']['candidate'],candidate=(result.get('factual_result') or {}).get('candidate')),
        actual_parameter_changes=(role.get('preparation_content') or {}).get('actual_diff',
        (result.get('design_statement') or {}).get('parameters',[])),references=fields,
        thresholds=dict(terminal_error_m=.01,holding_max_error_m=.01,holding_max_speed_m_s=.02,holding_window_s=.05),
        note='Sealed evaluation/profile arithmetic. Candidate profile references are required for new measured facts. Citations do not establish causality.')
