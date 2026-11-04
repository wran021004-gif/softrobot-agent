"""Compile scientific information needs into existing, read-only fact projections.

This module owns navigation only. Registries, raw provenance, numerical facts,
authorization and formal reading credit retain their existing owners.
"""
from copy import deepcopy
import json

from tools.platform_store import plain
from tools.state_io import digest
from tools.research.contracts import EvidenceIntentQuery, EvidenceContinuation
from tools.research.state import state


def _choices(reason, choices):
    return dict(status='selection_required',reason=reason,choices=choices,formal_read_credit=False)


def _scientific_details(value):
    """Retain facts, not the old projection's internal navigation instructions."""
    if isinstance(value,list):return [_scientific_details(v) for v in value]
    if not isinstance(value,dict):return value
    return {k:_scientific_details(v) for k,v in value.items()
        if k=='group_queries' or not (k.endswith(('_query','_queries','_pointer')) or k=='query_rule')}


def resolve_evidence_intent(host, query):
    """Deterministic lookup only; no registration, writes, or scientific launch."""
    from tools.research.core import read_evidence
    from tools.research.research_context import (decision_candidate, research_intent,
        resolved_candidate_facts, mathematical_decision_view)
    from tools.research.task_constraints import mathematical_method_view, mathematical_catalog, mathematical_action_view
    from tools.research.scientific_intent import parameter_catalog
    from tools.research.evidence_views import result_card
    from tools.research.evidence_policy import registered_references
    q=EvidenceIntentQuery.model_validate(query);s=state(host)
    candidates=list(s.get('candidates',{}).values())
    math=list(s.get('analysis_results',[]))+list(s.get('mechanics_results',[]))
    physics=[r for k in ('results','physical_replays','matched_state_results','rl_evaluations') for r in s.get(k,[])]
    from tools.research.reporter import entries
    reports=[r for r,_ in entries(host)] if q.topic=='reporter_explanations' or q.subject=='reports' else []
    with host.store.connect(True) as db:
        snapshot=dict(artifact_id=db.execute('SELECT snapshot FROM sessions WHERE run_id=?',(host.run_id,)).fetchone()[0],
            media_type='application/json')
    subject=plain(q.subject)
    task_topics=('task','research_history','research_opportunities')
    if subject=='current_task':
        if q.topic not in task_topics:raise ValueError('CURRENT_TASK_REQUIRES_TASK_OR_HISTORY_TOPIC')
        subject=snapshot
    elif subject=='current_candidate':
        subject=decision_candidate(host,{},research_intent(host))
        if subject is None:return _choices('NO_CURRENT_CANDIDATE',candidates)
    if subject==snapshot and q.topic not in task_topics:raise ValueError('FROZEN_TASK_SUBJECT_SCOPE_MISMATCH')
    registered=[*candidates,*registered_references(host),*reports,snapshot]
    if isinstance(subject,dict) and subject not in registered:
        raise ValueError('EVIDENCE_SUBJECT_NOT_REGISTERED_IN_STUDY')
    # Even a registered object must pass the original protected/raw read boundary.
    raw=read_evidence(host,dict(reference=subject),record_read=False) if isinstance(subject,dict) else None
    selected=[plain(r) for r in q.selection]
    sources=[];view='derived_research_view';authority=False
    def source(ref,pointer=''):
        read_evidence(host,dict(reference=ref,pointer=pointer),record_read=False)
        location=dict(reference=ref,pointer=pointer)
        if location not in sources:sources.append(location)
    def candidate_required():
        if subject not in candidates:raise ValueError('OWNED_CANDIDATE_REQUIRED_FOR_TOPIC')
    def no_selectors():
        if q.group is not None or selected:raise ValueError('EVIDENCE_TOPIC_HAS_NO_GROUP_OR_SELECTION')
    if q.topic=='structure':
        candidate_required();no_selectors();data=resolved_candidate_facts(raw,subject)
        data['fixed_payout_lengths_m']=raw['configuration']['robot']['structure']['data'].get('fixed_payout_lengths_m',{})
        from tools.research_tasks import task_adapter
        data['physical_capabilities']=task_adapter(raw['configuration']).physical_capabilities()
        source(subject,'/configuration');source(subject,'/parameters')
    elif q.topic=='structure_parameters':
        candidate_required();rows=parameter_catalog(s['spec'],raw)
        groups=sorted({r['parameter_group'] for r in rows})
        if q.group is not None and q.group not in groups:return _choices('REGISTERED_PARAMETER_GROUP_REQUIRED',groups)
        rows=[r for r in rows if q.group is None or r['parameter_group']==q.group]
        ids=[r['parameter_id'] for r in rows]
        if any(k not in ids for k in selected):return _choices('REGISTERED_PARAMETER_SELECTION_REQUIRED',ids)
        if selected:rows=[r for r in rows if r['parameter_id'] in selected]
        data=rows if q.detail_level!='summary' else [{k:r[k] for k in ('parameter_group','parameter_id',
            'physical_meaning','unit','current_value','domain','design_supported','differentiation','authorization_reason',
            'execution_admission','effective','continuous','selectable','study_authorized')} for r in rows]
        source(subject,'/parameters');source(subject,'/configuration')
    elif q.topic=='task':
        if subject not in [*candidates,snapshot]:raise ValueError('FROZEN_TASK_OR_OWNED_CANDIDATE_REQUIRED')
        no_selectors();configuration=raw['input'] if subject==snapshot else raw['configuration']
        from tools.research_tasks import task_adapter
        adapter=task_adapter(configuration)
        data=dict(description=adapter.describe(),constraints=adapter.constraint_observations({}),
            frozen_task=configuration['task'])
        source(subject,'/input/task' if subject==snapshot else '/configuration/task')
    elif q.topic in ('mathematical_methods','mechanism_capabilities'):
        candidate_required();method_view=mathematical_method_view(host,subject)
        if q.topic=='mathematical_methods':
            if q.group is not None:raise ValueError('SELECT_A_REGISTERED_METHOD_WITH_SELECTION')
            methods=method_view['methods'];keys=list(methods)
            if any(k not in keys for k in selected):return _choices('REGISTERED_METHOD_REQUIRED',keys)
            if selected:
                data=[mathematical_action_view(methods[k]) for k in selected]
            else:data=[dict(id=k,**v) for k,v in mathematical_catalog(method_view)['methods'].items()]
        else:
            research=method_view.get('structure_research') or {}
            mechanisms=research.get('mechanisms') or {}
            groups=list(mechanisms)
            # Group keys come from the existing mechanism projection, including
            # primitives/compositions/unavailable; no physics alias registry.
            if q.group is not None and q.group not in groups:return _choices('REGISTERED_MECHANISM_GROUP_REQUIRED',groups)
            if q.group is None:
                if selected:return _choices('SELECT_MECHANISM_GROUP_FIRST',groups)
                data={k:v for k,v in research.items() if k in ('mechanism_categories','effective_parameter_groups',
                    'working_point_semantics','task_conditioned_view','finite_time_response','operation_admission','task_scope')}
                data['registered_groups']=groups
                data['group_queries']=[dict(subject=subject,topic=q.topic,group=g) for g in groups]
            else:
                data=mechanisms[q.group]
                if selected:
                    keys=list(data) if isinstance(data,dict) else data
                    if any(k not in keys for k in selected):return _choices('REGISTERED_MECHANISM_SELECTION_REQUIRED',keys)
                    data={k:data[k] for k in selected} if isinstance(data,dict) else selected
        source(subject,'/configuration')
    elif q.topic in ('mathematical_results','physical_results'):
        if q.group is not None:raise ValueError('RESULT_TOPIC_HAS_NO_GROUP')
        refs=math if q.topic=='mathematical_results' else physics
        if subject in candidates:
            refs=[r for r in refs if host.store.artifact(r).get('candidate',host.store.artifact(r).get('design_candidate'))==subject]
        elif isinstance(subject,dict):refs=[r for r in refs if r==subject]
        elif subject!='registered_results':raise ValueError('RESULT_SUBJECT_REQUIRED')
        if any(r not in refs for r in selected):return _choices('REGISTERED_RESULT_SELECTION_REQUIRED',refs)
        refs=selected or refs;data=[]
        for ref in refs:
            source(ref);card=plain(result_card(host,ref))
            facts=mathematical_decision_view(card) if q.topic=='mathematical_results' else card
            if q.detail_level=='summary' and q.topic=='physical_results':
                facts={k:card[k] for k in ('identity','metrics','original_constraint_violations','evidence_summary') if k in card}
            data.append(dict(reference=ref,facts=facts))
        view='raw_scientific_projection';authority=True
    elif q.topic=='comparison':
        no_group=q.group is None
        if not no_group:raise ValueError('COMPARISON_TOPIC_HAS_NO_GROUP')
        refs=[*math,*physics]
        if len(selected)!=2 or any(r not in refs for r in selected) or selected[0]==selected[1]:
            return _choices('SELECT_TWO_DISTINCT_REGISTERED_RESULTS',refs)
        # Reuse the established report relation verifier. It preserves missing
        # task/model/timing/coverage and multi-factor limitations.
        from tools.research.reporter import assemble
        report=plain(assemble(host,selected,question='Compare the two explicitly selected existing results.'))
        data=dict(results=report['results'],relations=report['relations'],
            limitations='Only recorded comparison relations are supported; no new causal or acceptance conclusion.')
        view='derived_research_comparison'
        for ref in selected:source(ref)
    elif q.topic=='reporter_explanations':
        no_group=q.group is None
        if not no_group:raise ValueError('REPORT_TOPIC_HAS_NO_GROUP')
        refs=reports if subject=='reports' else [subject] if subject in reports else []
        if subject in candidates or subject in math or subject in physics:
            refs=[r for r,saved in entries(host) if any(c['identity'].get('candidate')==subject or
                c['identity']['result']['reference']==subject for c in saved['report']['results'])]
        if any(r not in refs for r in selected):return _choices('REGISTERED_REPORT_SELECTION_REQUIRED',refs)
        data=[];view='reporter_interpretation'
        for ref in selected or refs:
            saved=read_evidence(host,dict(reference=ref),record_read=False);report=saved['report']
            source(ref,'/report/interpretations')
            for card in report['results']:source(card['identity']['result']['reference'])
            data.append(dict(report_reference=ref,status=saved.get('interpretation_status'),interpretations=report['interpretations'],
                original_results=[c['identity']['result']['reference'] for c in report['results']]))
    elif q.topic in ('research_history','research_opportunities'):
        no_selectors();anchor=s['family_space_reference']
        pointer='/research_history_index' if q.topic=='research_history' else '/research_opportunities'
        data=read_evidence(host,dict(reference=anchor,view='working_set',pointer=pointer),record_read=False)
        source(anchor)
        if q.topic=='research_history':
            for row in data.values():
                location=row.get('source') or {}
                if location.get('reference'):source(location['reference'],location.get('pointer',''))
    else:raise ValueError('UNSUPPORTED_EVIDENCE_TOPIC')
    data=_scientific_details(data)
    bound=q.model_dump(mode='json',exclude={'continuation'});bound['subject']=subject
    query_identity=digest(dict(study=host.run_id,query=bound))
    content_identity=digest(data)
    start=0
    if q.continuation:
        c=q.continuation
        if c.study_id!=host.run_id or c.query_identity!=query_identity:
            raise ValueError('EVIDENCE_CONTINUATION_SCOPE_MISMATCH')
        if c.content_identity!=content_identity:raise ValueError('STALE_EVIDENCE_CONTINUATION')
        start=c.offset
    envelope=dict(version='semantic_evidence_v1',status='available',study_id=host.run_id,subject=subject,
        topic=q.topic,view_kind=view,authoritative_scientific_evidence=authority,
        formal_read_credit=False,content_identity=content_identity,sources=sources,
        query=bound,scientific_result_created=False)
    if q.detail_level=='evidence_review':
        envelope['review_queries']=[dict(**location,view='full') for location in sources]
    items=list(data.items()) if isinstance(data,dict) else data
    if start>len(items):raise ValueError('EVIDENCE_CONTINUATION_OFFSET_INVALID')
    # Fixed program owns pagination; never return a bare raw pointer. A single
    # registered detail remains exact even if large (SDK can offload it).
    page=[];end=start
    for item in items[start:]:
        if page and (len(page)>=6 or len(json.dumps(page+[item],ensure_ascii=False).encode())>2600):break
        page.append(item);end+=1
    envelope['facts']=dict(page) if isinstance(data,dict) else page
    envelope['total']=len(items)
    if end<len(items):
        cursor=EvidenceContinuation(study_id=host.run_id,query_identity=query_identity,content_identity=content_identity,offset=end)
        envelope['next_query']={**bound,'continuation':plain(cursor)}
    return envelope


def evidence_intent_access():
    """Small executable L0 entry points; choices are resolved from existing data."""
    return dict(interface='semantic_evidence_v1',tool='evidence_read',
        queries=[dict(subject='current_candidate',topic=t) for t in
            ('structure','structure_parameters','mechanism_capabilities','mathematical_methods','mathematical_results','physical_results')]
            +[dict(subject='current_task',topic=t) for t in ('task','research_history','research_opportunities')]
            +[dict(subject='reports',topic='reporter_explanations')],
        guidance='Use registered choices and next_query verbatim. Exact EvidenceQuery remains available for deliberate raw review and formal acceptance; ordinary queries grant no complete-read credit.')


def semantic_query_handles(value):
    """Adapt existing L0 discovery links, retaining raw provenance/review links."""
    if isinstance(value,list):return [semantic_query_handles(v) for v in value]
    if not isinstance(value,dict):return value
    if value.get('version')=='pending_feedback_delivery_v1' or value.get('preserve_once'):
        return deepcopy(value)
    ref=value.get('reference');view=value.get('view');path=value.get('pointer','')
    if ref and view=='mathematical_capabilities':
        query=dict(subject=ref,topic='mathematical_methods')
        if path.startswith('/methods/'):
            query.update(selection=[path.split('/')[2]],detail_level='targeted')
        elif path.startswith('/structure_research'):
            query['topic']='structure_parameters' if path.startswith('/structure_research/parameters') else 'mechanism_capabilities'
            parts=path.split('/')
            if len(parts)>=4 and parts[2]=='mechanisms':
                query['group']=parts[3]
                if len(parts)>4:query['selection']=[parts[4]]
        return query
    if ref and view in ('full','fields','summary') and path=='/parameters':
        return dict(subject=ref,topic='structure_parameters')
    if ref and view in ('full','summary','range') and path.startswith('/report/interpretations'):
        return dict(subject=ref,topic='reporter_explanations')
    if view=='working_set' and path in ('/research_history_index','/research_opportunities'):
        return dict(subject='current_task',topic='research_history' if path=='/research_history_index' else 'research_opportunities')
    return {k:semantic_query_handles(v) for k,v in value.items()}
