"""Short owned-object choices and exact bindings for existing research Plans."""
from copy import deepcopy
import json
import math

from tools.research.state import state,readable_results


def remove_fields(schema,names):
    """Remove derived fields from both compact and conditional decision constraints."""
    if isinstance(schema,list):
        for child in schema:remove_fields(child,names)
    elif isinstance(schema,dict):
        for name in names:schema.get('properties',{}).pop(name,None)
        if 'required' in schema:schema['required']=[k for k in schema['required'] if k not in names]
        for child in schema.values():remove_fields(child,names)


def reference_choices(host):
    """Short selectors in this original Store; immutable references remain authoritative."""
    s=state(host);choices={}
    candidates=list(s.get('candidates',{}).values())
    evaluations=[r for key in ('results','physical_replays','rl_evaluations') for r in s.get(key,[])]
    analyses=s.get('analysis_results',[])
    from tools.research.evidence_policy import registered_references
    refs=[*readable_results(s),*registered_references(host)]
    # Row identities are local selectors, not portable scientific identities.
    # Each advertised schema retains the exact alias-to-reference binding below.
    with host.store.connect(True) as db:
        for ref in refs:
            if ref in choices.values():continue
            if ref in analyses:name='result_'+str(analyses.index(ref)+1)
            else:
                row=db.execute('SELECT rowid FROM artifacts WHERE id=?',(ref['artifact_id'],)).fetchone()
                if row is None:continue
                prefix='candidate' if ref in candidates else 'evaluation' if ref in evaluations else 'evidence'
                name=prefix+'_'+str(row[0])
            choices[name]=ref
    return choices


def reference_schema(schema, choices, action):
    """Shorten existing Plan reference fields without changing scientific parameters."""
    schema=deepcopy(schema)
    if 'EvidenceRef' in schema.get('$defs',{}):
        schema['$defs']['EvidenceRef']=dict(type='string',enum=list(choices),
            description='Choose the exact named object from saved_object_choices; do not enter hashes.')
    # Freeze the mapping with the advertised schema so no later insertion can rebind it.
    schema['x-research-reference-choices']=choices
    if action in ('execute','initialize_control','control_search','select','confirm','replay'):
        decision=schema['$defs']['ResearchDecision']
        decision['properties'].pop('selected_candidate',None)
        decision['required']=[k for k in decision.get('required',[]) if k!='selected_candidate']
        schema['properties']['decision']={'$ref':'#/$defs/ResearchDecision'}
        remove_fields(schema,('selected_candidate',))
    if action in ('select','confirm','replay'):
        schema['properties'].pop('supporting_evidence',None)
        schema['required']=[k for k in schema.get('required',[]) if k!='supporting_evidence']
    needed=set()
    def visit(node):
        if isinstance(node,dict):
            if '$ref' in node:
                name=node['$ref'].rsplit('/',1)[-1]
                if name not in needed:needed.add(name);visit(schema['$defs'][name])
            for child in node.values():visit(child)
        elif isinstance(node,list):
            for child in node:visit(child)
    visit({k:v for k,v in schema.items() if k not in ('$defs','x-research-reference-choices')})
    schema['$defs']={k:v for k,v in schema.get('$defs',{}).items() if k in needed}
    return schema


def expand_references(payload, schema):
    """Resolve only schema-typed reference positions, never scientific text."""
    choices=schema.get('x-research-reference-choices',{});definitions=schema.get('$defs',{})
    def expand(value,node):
        if '$ref' in node:
            name=node['$ref'].rsplit('/',1)[-1]
            if name=='EvidenceRef':return deepcopy(choices[value]) if isinstance(value,str) else value
            return expand(value,definitions[name])
        if isinstance(value,dict):
            properties=node.get('properties',{})
            result={key:expand(child,properties[key]) if key in properties else child for key,child in value.items()}
        elif isinstance(value,list) and 'items' in node:result=[expand(v,node['items']) for v in value]
        else:result=value
        for keyword in ('anyOf','allOf','oneOf'):
            for branch in node.get(keyword,[]):
                from jsonschema import Draft202012Validator
                if Draft202012Validator({**branch,'$defs':definitions}).is_valid(value):
                    result=expand(result,branch)
                    if keyword!='allOf':break
        return result
    return expand(payload,schema)


def bind_plan_selection(host,payload):
    """One chosen object owns repeated candidate/evidence fields in the original Plan."""
    value=deepcopy(payload);action=value['action'];candidate=None
    if action=='execute':candidate=value['candidate']
    elif action=='initialize_control':candidate=value['control_seed']['candidate']
    elif action=='control_search':candidate=value['control_search']['candidate']
    elif action in ('select','confirm','replay'):
        selected=value['mechanics_source'] if action=='replay' else value['selected_execution']
        refs=selected if isinstance(selected,list) else [selected]
        results=[host.store.artifact(ref,paths=('candidate','design_candidate')) for ref in refs]
        candidate=results[0].get('candidate') or results[0].get('design_candidate')
        if any((r.get('candidate') or r.get('design_candidate'))!=candidate for r in results):
            raise ValueError('SELECTION_REQUIRES_IDENTICAL_CANDIDATE')
        value['supporting_evidence']=refs
    if candidate:value['decision']['selected_candidate']=candidate
    return value


def saved_choice(host, choice):
    """Resolve an append-only Study result ordinal; never infer a candidate."""
    s=state(host)
    if not isinstance(choice,str) or not choice.startswith('result_'):
        raise ValueError('SAVED_REPLAY_RESULT_CHOICE_REQUIRED')
    ordinal=choice.removeprefix('result_')
    if not ordinal.isdecimal() or str(int(ordinal))!=ordinal or not 1<=int(ordinal)<=len(s.get('analysis_results',[])):
        raise ValueError('UNKNOWN_SAVED_REPLAY_RESULT_CHOICE')
    reference=s['analysis_results'][int(ordinal)-1]
    value=host.store.artifact(reference,paths=('candidate','status','control_schedule_reference',
        'native_dynamics.optimization.best.measure','native_dynamics.optimization.best.task_gap.valid_complete'))
    best=(value.get('native_dynamics') or {}).get('optimization',{}).get('best',{})
    score=(best.get('measure') or {}).get('signed_maximum_excess')
    if (value.get('status')!='computed' or not best.get('task_gap',{}).get('valid_complete')
            or not isinstance(score,(int,float)) or not math.isfinite(score) or not value.get('control_schedule_reference')):
        raise ValueError('COMPLETE_SAVED_REPLAY_CONTROL_REQUIRED')
    candidate=value['candidate'];source=value['control_schedule_reference']
    if host.store.artifact(candidate,paths=('profile_identity',)).get('profile_identity')!=s['profile']['identity']:
        raise ValueError('CURRENT_PROFILE_REPLAY_CHOICE_REQUIRED')
    control=host.store.artifact(source,paths=('provenance.candidate',))
    if control.get('provenance',{}).get('candidate')!=candidate:
        raise ValueError('SAVED_REPLAY_CANDIDATE_CONTROL_MISMATCH')
    return dict(choice=choice,result_reference=reference,candidate=candidate,control_source=source,
        J=score,mathematical_status='satisfied' if score<=0 else 'not_satisfied',
        metrics=best['measure'],independent_task_acceptance='unmeasured_for_this_choice',
        formal_acceptance_read_credit=False)


def replay_choices(host, delivery):
    """Offer existing comparable best and representative failures, without a decision."""
    s=state(host);refs=[]
    latest=delivery.get('latest_search') or {}
    refs.extend(f['reference'] for f in (latest.get('fixed_result') or {}).get('best_mathematical',[]))
    refs.extend(r['fact']['reference'] for r in delivery.get('study_best_mathematical',[]) if r.get('fact'))
    refs.extend(r['reference'] for r in delivery.get('critical_failures',[]) if r.get('reference'))
    if (delivery.get('latest_evaluation') or {}).get('reference'):
        refs.append(delivery['latest_evaluation']['reference'])
    options=[];seen=set()
    for ref in refs:
        if ref not in s.get('analysis_results',[]) or ref['artifact_id'] in seen:continue
        seen.add(ref['artifact_id'])
        choice='result_'+str(s['analysis_results'].index(ref)+1)
        try:option=saved_choice(host,choice)
        except ValueError:continue
        replays=[]
        for replay in s.get('physical_replays',[]):
            result=host.store.artifact(replay,paths=('candidate','source_reference','acceptance.status','acceptance.accepted'))
            if result.get('candidate')==option['candidate'] and result.get('source_reference')==option['control_source']:
                replays.append(dict(reference=replay,acceptance=result.get('acceptance')))
        option['recorded_independent_replays']=replays
        if replays:option['independent_task_acceptance']='see_recorded_independent_replays'
        options.append(option)
    return options


def choice_schema(schema, options):
    """Keep Main's scientific rationale; remove all mechanical identity fields."""
    schema=deepcopy(schema)
    schema['properties']['physical_replay']=dict(type='object',additionalProperties=False,
        properties=dict(result_choice=dict(type='string',enum=[r['choice'] for r in options],
            description='Choose exactly one saved result. Its candidate, control and supporting result are bound together. Options: '+json.dumps(options))),
        required=['result_choice'])
    schema['properties'].pop('supporting_evidence',None)
    schema['required']=[k for k in schema['required'] if k!='supporting_evidence']
    # The compact Plan schema may wrap decision constraints in allOf.
    schema['properties']['decision']={'$ref':'#/$defs/ResearchDecision'}
    decision=schema['$defs']['ResearchDecision']
    mechanical=('selected_candidate','selected_method','requested_budget','research_intent','selected_variables')
    for key in mechanical:decision['properties'].pop(key,None)
    decision['required']=[k for k in decision.get('required',[]) if k not in mechanical]
    remove_fields(schema,mechanical)
    schema['description']='Select one saved result for independent Replay and explain your scientific rationale. Do not fill candidate/control/evidence hashes or numerical settings. Original Plan admission and all acceptance gates still apply.'
    return schema


def expand_choice(host, payload):
    """Expand a validated selection into the unchanged Plan execution contract."""
    value=deepcopy(payload);selected=saved_choice(host,value['physical_replay']['result_choice'])
    value['physical_replay']=dict(candidate=selected['candidate'],source=selected['control_source'])
    value['supporting_evidence']=[selected['result_reference']]
    value['decision'].update(selected_candidate=selected['candidate'],selected_method='saved_result_physical_replay',
        requested_budget=1,research_intent='PHYSICAL_VALIDATION',selected_variables=[])
    return value,selected
