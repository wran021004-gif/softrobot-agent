"""Short owned-object choices and exact bindings for existing research Plans."""
from copy import deepcopy
import json
import math
import re

from tools.research.state import state,readable_results


def remove_fields(schema,names):
    """Remove derived fields from both compact and conditional decision constraints."""
    if isinstance(schema,list):
        for child in schema:remove_fields(child,names)
    elif isinstance(schema,dict):
        for name in names:schema.get('properties',{}).pop(name,None)
        if 'required' in schema:schema['required']=[k for k in schema['required'] if k not in names]
        for child in schema.values():remove_fields(child,names)


def reference_choices(host, *, include_all=False):
    build=lambda:_reference_choices(host,include_all=include_all)
    if hasattr(host.store,'snapshot_value'):
        return host.store.snapshot_value(('reference_choices',include_all),build)
    return build()


def _reference_choices(host, *, include_all=False):
    """Short selectors in this original Store; immutable references remain authoritative."""
    s=state(host);choices={}
    candidates=list(s.get('candidates',{}).values())
    evaluations=[r for key in ('results','physical_replays','rl_evaluations') for r in s.get(key,[])]
    analyses=s.get('analysis_results',[])
    from tools.research.evidence_policy import registered_references
    refs=[] if include_all else [*candidates,*s.get('plans',[]),*readable_results(s),*registered_references(host)]
    # Row identities are local selectors, not portable scientific identities.
    # Each advertised schema retains the exact alias-to-reference binding below.
    with host.store.connect(True) as db:
        if include_all:
            refs=[dict(artifact_id=i,media_type=m) for i,m in db.execute('SELECT id,media FROM artifacts')]
            if s['spec'].get('knowledge',{}).get('organization')=='typed_knowledge_v1':
                from tools.research.evidence_policy import study_references
                owned=study_references(host)
                refs=[r for r in refs if r in owned]
        for ref in refs:
            if ref in choices.values():continue
            if ref in analyses:name='result_'+str(analyses.index(ref)+1)
            elif ref in s.get('plans',[]):name='plan_'+str(s['plans'].index(ref)+1)
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
    if action in ('execute','initialize_control','control_search','physical_replay','select','confirm','replay'):
        decision=schema['$defs']['ResearchDecision']
        decision['properties'].pop('selected_candidate',None)
        decision['required']=[k for k in decision.get('required',[]) if k!='selected_candidate']
        schema['properties']['decision']={'$ref':'#/$defs/ResearchDecision'}
        remove_fields(schema,('selected_candidate',))
    if action in ('select','confirm','replay'):
        schema['properties'].pop('supporting_evidence',None)
        schema['required']=[k for k in schema.get('required',[]) if k!='supporting_evidence']
    from tools.research.contracts import prune_schema_definitions
    prune_schema_definitions(schema)
    return schema


def expand_references(payload, schema, *, strict=True):
    """Resolve only schema-typed reference positions, never scientific text."""
    choices=schema.get('x-research-reference-choices',{});definitions=schema.get('$defs',{})
    def expand(value,node):
        if '$ref' in node:
            name=node['$ref'].rsplit('/',1)[-1]
            if name=='EvidenceRef':
                if isinstance(value,str) and (strict or value in choices):
                    if value not in choices:raise ValueError('UNKNOWN_SAVED_OBJECT_CHOICE: '+value)
                    return deepcopy(choices[value])
                return value
            return expand(value,definitions[name])
        if isinstance(value,dict):
            properties=node.get('properties',{})
            result={key:expand(child,properties[key]) if key in properties else child for key,child in value.items()}
        elif isinstance(value,list) and 'items' in node:result=[expand(v,node['items']) for v in value]
        else:result=value
        for keyword in ('anyOf','allOf','oneOf'):
            branches=node.get(keyword,[])
            matching=[]
            for branch in branches:
                from jsonschema import Draft202012Validator
                if Draft202012Validator({**branch,'$defs':definitions}).is_valid(value):
                    matching.append(branch)
                    if keyword!='allOf':break
            if not matching and keyword in ('anyOf','oneOf') and isinstance(value,(dict,list)):
                # An unrelated invalid scientific field must not suppress typed
                # reference expansion in a unique object/array branch. Original
                # validation still rejects that field; scientific text is untouched.
                shaped=[b for b in branches if (definitions.get(b.get('$ref','').rsplit('/',1)[-1],b).get('type')
                    ==('object' if isinstance(value,dict) else 'array' if isinstance(value,list) else None))]
                if len(shaped)==1:matching=shaped
            for branch in matching:result=expand(result,branch)
        return result
    return expand(payload,schema)


def bind_plan_selection(host,payload):
    """One chosen object owns repeated candidate/evidence fields in the original Plan."""
    value=deepcopy(payload);action=value['action'];candidate=None
    if value.get('decision') is not None:
        from tools.research.contracts import PLAN_RESEARCH_INTENTS
        value['decision'].setdefault('research_intent',PLAN_RESEARCH_INTENTS[action])
    if action=='execute':candidate=value['candidate']
    elif action=='initialize_control':candidate=value['control_seed']['candidate']
    elif action=='control_search':candidate=value['control_search']['candidate']
    elif action=='physical_replay':candidate=value['physical_replay'].get('candidate')
    elif action in ('select','confirm','replay'):
        selected=value['mechanics_source'] if action=='replay' else value['selected_execution']
        refs=selected if isinstance(selected,list) else [selected]
        if action=='select' and isinstance(selected,list):
            from tools.research.conditions import joint_assessment
            with host.store.read_snapshot():
                candidate=joint_assessment(host,refs)['candidate']
        else:
            results=[host.store.artifact(ref,paths=('candidate','design_candidate')) for ref in refs]
            candidate=results[0].get('candidate') or results[0].get('design_candidate')
            if any((r.get('candidate') or r.get('design_candidate'))!=candidate for r in results):
                raise ValueError('SELECTION_REQUIRES_IDENTICAL_CANDIDATE')
        value['supporting_evidence']=refs
    if candidate:
        chosen=value['decision'].get('selected_candidate')
        if chosen is not None and chosen!=candidate:raise ValueError('CONFLICTING_CANDIDATE_REFERENCES')
        value['decision']['selected_candidate']=candidate
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
            description='Choose exactly one saved result from saved_replay_choices. Its candidate, control and supporting result are bound together.')),
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


def main_context_enabled(spec):
    return (spec.get('research_decisions',{}).get('analysis_interface')=='scientific_question_v4' or
        spec.get('research_decisions',{}).get('tool_schema_policy',{}).get('version')=='research_information_flow_v1')


def main_projection(host, value):
    """Last-mile presentation only. Exact artifacts and SDK history stay in Store."""
    choices=reference_choices(host,include_all=True);aliases={ref['artifact_id']:name for name,ref in choices.items()}
    identities=re.compile(r'(?<![0-9a-f])[0-9a-f]{40,64}(?![0-9a-f])',re.I)
    authored_text={'hypothesis','expected_observation','weakening_observation','fixed_conditions',
        'interpretation','question','user_request','instruction'}
    def project(item):
        if isinstance(item,dict):
            if item.get('version')=='evidence_continuation_v1':
                # Executable opaque cursor, not a display-only scientific ID.
                # Dropping/redacting its identities makes saved pages unusable.
                return deepcopy(item)
            if isinstance(item.get('artifact_id'),str):
                alias=aliases.get(item['artifact_id'],'unavailable_external_reference')
                rest={k:project(v) for k,v in item.items() if k not in ('artifact_id','media_type')}
                return dict(reference=alias,**rest) if rest else alias
            return {k:(v if isinstance(v,str) and (k in authored_text or
                k=='content' and item.get('role')=='user' and not v.startswith('CURRENT_RESEARCH_PACKET\n')) else project(v))
                for k,v in item.items() if not k.startswith('x-research-') and not (
                (k.endswith('_identity') or k in ('freeze','sha','sha256','identities')) and
                identities.search(json.dumps(v)))}
        if isinstance(item,list):return [project(v) for v in item]
        if isinstance(item,str):
            # SDK historical previews may cut a JSON object in half. They are
            # not authoritative evidence; never expose raw identity fragments
            # from an unparseable preview. Current fixed facts and exact reads
            # are delivered independently in CURRENT_RESEARCH_PACKET.
            if re.match(r'^\[Truncated: \d+ blocks?, ~[\d,]+ tokens\]\n\n',item):
                return 'SDK truncated historical preview. Use the current research packet and original-result query for evidence; this preview gives no complete-read credit.'
            # Tool results and action arguments are JSON inside the SDK wire.
            try:decoded=json.loads(item)
            except (ValueError,TypeError):decoded=None
            if isinstance(decoded,(dict,list)):return json.dumps(project(decoded),separators=(',',':'))
            if item.startswith('CURRENT_RESEARCH_PACKET\n'):
                return 'CURRENT_RESEARCH_PACKET\n'+json.dumps(project(json.loads(item.split('\n',1)[1])),separators=(',',':'))
            return aliases.get(item,item) if not identities.fullmatch(item) else aliases.get(item,'[internal identity]')
        return item
    return project(value)


def main_packet(host, packet):
    """One fact owner in normal L0; replay/menu/history carry navigation only."""
    value=deepcopy(packet);research=value.get('research',{})
    replay=value.get('saved_replay_choices',{}).get('options',[])
    for row in replay:
        for key in ('result_reference','candidate','control_source','metrics','J'):
            row.pop(key,None)
        row['facts_at']='research.scientific_results (result '+row['choice']+')'
    for row in value.get('saved_object_choices',[]):
        row.pop('reference',None)
    # Keep one current-packet owner for the latest numerical card. A past wire
    # receipt is not current context after a handoff drops the old conversation.
    latest=(research.get('mathematical_research') or {}).get('latest_result') or {}
    if latest.get('structure_research'):
        reference=latest['reference']
        delivered=research.get('scientific_results') or {}
        if (delivered.get('latest_evaluation') or {}).get('reference')==reference:
            delivered['latest_evaluation']=dict(reference=reference,facts_at='mathematical_research.latest_result')
        research['verified_facts']=[f for f in research.get('verified_facts',[]) if
            f.get('result_reference')!=reference and (f.get('source') or {}).get('reference')!=reference]
        research['verified_facts'].append(dict(result_reference=reference,facts_at='mathematical_research.latest_result'))
    continuation=research.get('tool_continuation') or {}
    if continuation.get('pending_feedback'):
        from tools.research.session_handoff import main_feedback_projection
        continuation['pending_feedback']=main_feedback_projection(host,continuation['pending_feedback'])
    if state(host)['spec'].get('canonical_task',{}).get('physical_problem'):
        mathematical=research.get('mathematical_research') or {}
        research['mathematical_research']={k:v for k,v in mathematical.items() if k in
            ('status','candidate','latest_result','parameters','method_directory_query','detail_query')}
        handoff=continuation.get('analysis_handoff')
        if handoff:
            handoff.pop('parameter_catalog',None)
            handoff['parameter_query']=dict(reference=mathematical.get('candidate'),view='mathematical_capabilities',pointer='/structure_research/parameters')
            handoff['next']='Choose a frozen load and registered constrained target; inspect, differentiate, optimize or compare. Main independently decides whether to generate a proposed structure.'
    seen={}
    def deduplicate(item,path):
        if isinstance(item,dict):
            if 'signed_task_gap' in item and 'constraints' in item:
                item={k:v for k,v in item.items() if k not in ('constraints','components','interpretation')}
                fingerprint=json.dumps(item,sort_keys=True)
                if fingerprint in seen:return dict(facts_at=seen[fingerprint])
                seen[fingerprint]=path
                item['constraint_details']='/acceptance/constraint_observations'
            # Exact repeated scientific cards become navigation; distinct scopes
            # and estimates keep their own content even when values coincide.
            if item.get('reference') and any(k in item for k in ('metrics','J','structure_research')):
                fingerprint=json.dumps(item,sort_keys=True)
                if fingerprint in seen:return dict(reference=item['reference'],facts_at=seen[fingerprint])
                seen[fingerprint]=path
            return {k:deduplicate(v,path+'.'+k) for k,v in item.items()}
        if isinstance(item,list):return [deduplicate(v,path+'['+str(i)+']') for i,v in enumerate(item)]
        return item
    value=deduplicate(value,'L0')
    return main_projection(host,value)


def main_tool_schema(schema, choices):
    """Shared typed reference input projection; bindings remain SDK-only."""
    schema=deepcopy(schema)
    if 'ResearchDecision' in schema.get('$defs',{}) and 'action' in schema.get('properties',{}):
        remove_fields(schema,('research_intent',))
        schema['$defs']['ResearchDecision']['description']='Main chooses hypothesis, candidate and scientific variables. The host derives research_intent from the explicit Plan action before original validation.'
        schema['description']=schema.get('description','')+' Candidate selection belongs only in decision.selected_candidate when advertised there. Never add a top-level selected_candidate field.'
    if 'EvidenceRef' in schema.get('$defs',{}):
        schema['$defs']['EvidenceRef']=dict(type='string',pattern=r'^(candidate|plan|evaluation|result|evidence)_[1-9][0-9]*$',
            description='Use the stable short reference in the research packet or an evidence response.')
        schema['x-research-reference-choices']=choices
    if any('family_space_identity' in node.get('properties',{}) for node in schema.get('$defs',{}).values()):
        remove_fields(schema,('family_space_identity',))
    return schema
