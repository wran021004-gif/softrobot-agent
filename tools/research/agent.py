"""Production Strands harness, accounted provider transport and persisted conversation."""
import asyncio
from copy import deepcopy
import json, time
from pathlib import Path
from uuid import uuid4
import httpx
from strands_harness import create_harness
from tools.platform_store import plain,zero,encode
from tools.state_io import atomic_json,digest
from tools.research.state import (state, update, save, guard, enabled, protected,
    closeout_operations, admit_closeout, readable_results)
from tools.research.budget import engineering_closeout
from tools.research.core import read_tool_evidence
from tools.research.session_handoff import session_storage, session_storage_path
from tools.research.provider import (DeepSeekModel, LiveBoundary, IncompleteModelOutput,
    RequestBoundaryHandoff, CompletedBoundaryHandoff, SupervisorReviewPause,
    pilot, record, pending, received, provider_outcome, live_model_class, load_credential,
    credential, build_model)
PLAN_TOOL_DESCRIPTION=('Propose/search/execute/initialize_control/physical_replay/diagnose. '
    'Tool arguments are the Plan object itself, without an outer plan property. '
    'control_search uses physical replay callbacks; Native mathematical sequence optimization uses research_analysis, not a selected_method label. '
    'Diagnose reads existing evidence; selected_method does not execute a mathematical/native worker '
    '(use research_analysis with its registered template). Only an explicit diagnostic payload requests local solves. '
    'Control sources and optional NMPC handoff are described in control_initialization_methods. '
    'When route_review.required, use interpretation to compare continuation, structure/control changes and diagnosis with evidence and remaining budget; no route is prescribed. '
    'Select an exact publicly read fresh complete passing evaluation and freeze it; zero configured extra repetitions seals immediately. '
    'Positive configured confirmations preserve failures and identity. History never satisfies fresh gates; failures/counters persist. STOP seals study.')
DECISION_PLAN_DESCRIPTION=('Choose an available research action with a typed decision and evidence. '
    'A diagnose selected_method records intent; it does not execute analysis. After choosing a registered method and candidate, '
    'use research_analysis when offered and obtain exact method details through evidence_read. '
    'Only independent evaluation establishes acceptance. SELECT requires the Main Agent to read the full fresh passing result. '
    'For STOP, retrieve and cite the complete new result index.')
QUESTION_PLAN_DESCRIPTION=('Record a scientific hypothesis and an owned candidate through diagnose; no mathematical solver name is required. '
    'Then submit ScientificQuestion directly to research_analysis. Other Plan payloads retain their original contracts. '
    'Only independent evaluation establishes task acceptance. SELECT requires a public read of the exact fresh passing result; STOP requires the complete new result index.')
def plan_schema(actions, *, decision_required=False,family_version=None,diagnose_candidate_required=False,focused=False,study=None):
    """Advertise only executable action payloads and their reachable definitions."""
    from tools.research.contracts import Plan, PLAN_PAYLOADS, PLAN_OPTIONAL_PAYLOADS, PLAN_RESEARCH_INTENTS
    schema=Plan.model_json_schema()
    from tools.research.scientific_intent import enabled as question_enabled
    scientific_question = question_enabled(study or {})
    from tools.research.scientific_intent import explicit_actions
    if not explicit_actions(study or {}) or 'diagnose' not in actions:
        schema['properties'].pop('next_research_action')
    from tools.research.structure_intent import enabled as structure_enabled
    structure_intent=structure_enabled(study or {}) and 'search' in actions
    if scientific_question:
        decision=schema['$defs']['ResearchDecision']
        decision['properties']['selected_candidate']['description']+=' For diagnose, place the owned candidate here at decision.selected_candidate; there is no top-level selected_candidate field.'
        decision['required'].remove('selected_method')
        decision['properties']['selected_method']['description']='Optional action intent label; no solver name is required. The scientific question selects semantics after diagnose.'
        schema['$defs']['ControlSeedRequest']['properties']['method']['description']=(
            'baseline with only candidate uses candidate pretensions over the full frozen task grid, without task evaluation. '
            'Use the returned legal control source, never the structure candidate, when source selection is needed. '
            'Initialization supersedes the latest diagnose: submit a new candidate-bound diagnose Plan with your hypothesis; '
            'no underlying mathematical method name is required. Then submit ScientificQuestion directly to research_analysis. '
            'Original AnalysisRequest and execution admission still apply.')
        if explicit_actions(study or {}):
            schema['$defs']['ControlSeedRequest']['properties']['method']['description']='baseline uses candidate pretensions over the full frozen task grid without evaluation. Use the returned control source, not candidate. Initialization supersedes the latest diagnose; record a new hypothesis/candidate and optionally next_research_action. Main chooses the subsequent research action.'
    if family_version:
        schema['properties']['search']['anyOf']=[{'$ref':'#/$defs/FamilyMixedSearch'},{'type':'null'}]
        generation='GenerationRequestV2' if family_version=='serial_family_space_v2' else 'GenerationRequest'
        schema['properties']['generation']['anyOf']=[{'$ref':'#/$defs/'+generation},{'type':'null'}]
    if structure_intent:
        from tools.research.contracts import ScientificStructureSearch
        intent_schema=ScientificStructureSearch.model_json_schema()
        properties=intent_schema['properties'];grant=study['family_search']
        properties['design_variable_groups']['items']['enum']=[g for g in grant['variable_groups'] if g!='control']
        for name in ('segment_counts','tendon_counts'):
            for branch in properties[name]['anyOf']:
                if branch.get('type')=='array':branch['items']['enum']=grant[name]
        schema['$defs'].update(intent_schema.pop('$defs'))
        schema['$defs']['ScientificStructureSearch']=intent_schema
        schema['properties']['search']['anyOf']=[{'$ref':'#/$defs/ScientificStructureSearch'},{'type':'null'}]
        decision=schema['$defs']['ResearchDecision']
        decision['required'].remove('research_intent')
        if actions==['search']:
            decision['properties'].pop('research_intent')
            decision['properties'].pop('selected_method')
            decision['properties'].pop('requested_budget')
            decision['required']=[k for k in decision['required'] if k not in ('selected_method','requested_budget')]
    payloads=PLAN_PAYLOADS
    allowed={payloads[a] for a in actions if a in payloads}
    allowed.update(f for a in actions for f in PLAN_OPTIONAL_PAYLOADS.get(a,()))
    for field in set(payloads.values())-allowed:schema['properties'].pop(field,None)
    schema['properties']['action']={'type':'string','enum':actions}
    if decision_required:
        schema['required'].append('decision')
        schema['properties']['decision']={'$ref':'#/$defs/ResearchDecision'}
    schema['allOf']=[]
    for intent in dict.fromkeys(PLAN_RESEARCH_INTENTS[a] for a in actions):
        owners=[a for a in actions if PLAN_RESEARCH_INTENTS[a]==intent and not (structure_intent and a=='search')]
        if not owners:continue
        schema['allOf'].append({'if':{'properties':{'action':{'enum':owners}}},
            'then':{'properties':{'decision':{'properties':{'research_intent':{'const':intent}}}}}})
        if structure_intent:schema['allOf'][-1]['then']['properties']['decision']['required']=['research_intent']
    for field in dict.fromkeys(payloads.values()):
        owners=[a for a in actions if payloads.get(a)==field or field in PLAN_OPTIONAL_PAYLOADS.get(a,())]
        if not owners:continue
        required_by=[a for a in owners if field not in PLAN_OPTIONAL_PAYLOADS.get(a,())]
        branch=dict(required=[field],properties={field:{'not':{'type':'null'}}}) if required_by else {}
        if required_by and required_by!=owners:
            branch={'if':{'properties':{'action':{'enum':required_by}}},'then':branch}
        if len(actions)==1:
            if required_by:
                schema['required'].append(field)
                schema['properties'][field].pop('default',None)
                schema['properties'][field]['anyOf']=[v for v in schema['properties'][field]['anyOf'] if v.get('type')!='null']
        else:
            schema['allOf'].append({'if':{'properties':{'action':{'enum':owners}}},'then':branch,
                'else':{'properties':{field:{'type':'null'}}}})
    schema['allOf'].append({'if':{'properties':{'action':{'not':{'enum':['select','confirm']}}}},
        'then':{'properties':{'revise_selection':{'const':False}}}})
    if decision_required:
        if scientific_question and any(a!='diagnose' and not (structure_intent and a=='search') for a in actions):
            schema['allOf'].append({'if':{'properties':{'action':{'enum':[a for a in actions if a!='diagnose' and not (structure_intent and a=='search')]}}},
                'then':{'properties':{'decision':{'required':['selected_method']}}}})
        if scientific_question and 'diagnose' in actions:
            schema['allOf'].append({'if':{'properties':{'action':{'enum':['diagnose']}}},
                'then':{'properties':{'decision':{'required':['selected_candidate'],
                    'properties':{'selected_candidate':{'$ref':'#/$defs/EvidenceRef'}}}}}})
        bound=[a for a in actions if a in ('execute','initialize_control','control_search','physical_replay')]
        schema['allOf'].append({'if':{'properties':{'action':{'enum':bound}}},'then':{'properties':{
            'decision':{'required':['selected_candidate'],'properties':{'selected_candidate':{'$ref':'#/$defs/EvidenceRef'}}}}}})
        if diagnose_candidate_required and 'diagnose' in actions:
            from tools.research.task_constraints import registered_analysis_method_names
            schema['allOf'].append({'if':{'properties':{'action':{'const':'diagnose'},'decision':{
                'properties':{'selected_method':{'enum':registered_analysis_method_names()}},'required':['selected_method']}},'required':['action','decision']},
                'then':{'properties':{'decision':{'required':['selected_candidate'],
                    'properties':{'selected_candidate':{'$ref':'#/$defs/EvidenceRef'}}}}}})
    if focused:
        if len(actions)!=1:raise ValueError('FOCUSED_PLAN_REQUIRES_ONE_ACTION')
        common=set(schema['required'])|{'supporting_evidence','experience_disposition','next_step'}
        keep=common|allowed
        if actions[0]=='diagnose' and explicit_actions(study or {}):keep.add('next_research_action')
        if actions[0]=='stop':keep.add('stop_reason')
        if actions[0] in ('select','confirm'):keep.add('revise_selection')
        schema['properties']={k:v for k,v in schema['properties'].items() if k in keep}
        # All branches now describe one action; dropping references to removed
        # optional fields also removes their irrelevant parameter definitions.
        schema['allOf']=[b for b in schema['allOf'] if not any(k in json.dumps(b) for k in ('"revise_selection"',))]
        if actions[0] in ('stop','select'):
            schema['properties']['hypothesis']['description']='Existing claim or closure rationale. No new design hypothesis is requested.'
            schema['$defs']['ResearchDecision']['properties']['hypothesis_id']['description']='Reference an existing hypothesis or the closure rationale identifier; do not invent a new design hypothesis.'
        schema['description']='Submit the selected '+actions[0]+' action. All original Plan validation and evidence admission apply. hypothesis is required; probe completion is not scientific STOP.'
        if actions[0] in ('stop','select'):
            schema['description']+=' Observation/condition fields describe existing evidence and closure criteria; state unmeasured or not applicable where appropriate.'
    needed=set()
    def visit(v):
        if isinstance(v,dict):
            if '$ref' in v:
                name=v['$ref'].rsplit('/',1)[-1]
                if name not in needed:
                    needed.add(name);visit(schema['$defs'][name])
            for x in v.values():visit(x)
        elif isinstance(v,list):
            for x in v:visit(x)
    visit(schema['properties'])
    schema['$defs']={k:v for k,v in schema['$defs'].items() if k in needed}
    if focused and study and study.get('research_decisions',{}).get('tool_schema_policy',{}).get('version') in ('on_demand_tools_v3','research_information_flow_v1'):
        schema=compact_plan_schema(schema,actions[0],study)
    return schema


def compact_plan_schema(schema, action, study):
    """Remove annotations/unreachable branches; bind the actual frozen domain."""
    branches=[]
    for branch in schema.get('allOf',[]):
        condition=branch.get('if',{}).get('properties',{})
        owners=condition.get('action',{}).get('enum')
        if set(condition)=={'action'} and owners is not None:
            if action in owners:branches.append(branch.get('then',{}))
        elif set(condition)=={'action'} and 'not' in condition['action']:
            if action not in condition['action']['not']['enum']:branches.append(branch['then'])
        elif set(condition)=={'action','decision'} and condition['action'].get('const')==action:
            branches.append(dict(properties=dict(decision=dict(
                **{'if':condition['decision']},then=branch['then']['properties']['decision']))))
        else:branches.append(branch)
    # The action is fixed. Keep its constraints on the original properties;
    # official function tools reject composition keywords at the object root.
    schema.pop('allOf',None)
    for branch in branches:
        for name,constraint in branch['properties'].items():
            schema['properties'][name]={'allOf':[schema['properties'][name],constraint]}
    if action=='generate':
        space=study['family_space'];name='GenerationRequestV2' if space['version']=='serial_family_space_v2' else 'GenerationRequest'
        # Plan's legacy union default is v1; do not advertise omission as v2.
        schema['$defs'][name]['required']=[*schema['$defs'][name].get('required',[]),'version']
        properties=schema['$defs'][name]['properties']
        properties['family_space_identity']={'type':'string','const':study['family_space_identity']}
        properties['segment_count']={**properties['segment_count'],'enum':space['executable_segment_counts']}
        lo,hi=space['executable_tendon_count_bounds']
        properties['tendon_count']={**properties['tendon_count'],'minimum':lo,'maximum':hi}
        schema['$defs'][name]['description']='Supply only intended design changes. Omitted optional overrides inherit frozen defaults/prototypes; sections and cells need not be filled. Valid generation does not establish task success.'
        choice=schema['$defs']['SegmentChoiceV2' if name=='GenerationRequestV2' else 'SegmentChoice']['properties']
        choice['sections']['description']='Optional override. Omit unchanged sections; otherwise match the exact count and order of the selected prototype stations shown in generation_inputs.'
        if name=='GenerationRequestV2':
            lo,hi=space['serial_assembly']['cell_count_bounds']
            for branch in choice['cells']['anyOf']:
                if branch.get('type')=='integer':branch.update(minimum=lo,maximum=hi)
            choice['cells']['description']='Optional override within frozen cell_count_bounds; omit to inherit default_cells.'
    def clean(node):
        if isinstance(node,list):return [clean(v) for v in node]
        if not isinstance(node,dict):return node
        result={k:({name:clean(child) for name,child in v.items()} if k in ('properties','$defs') else clean(v))
            for k,v in node.items() if k!='title'}
        if len(result.get('anyOf',[]))==1:
            result={**result.pop('anyOf')[0],**result}
        return result
    return clean(schema)


def evidence_query_schema(study):
    """Project the canonical evidence query through the shared wire adapter."""
    from tools.research.contracts import EvidenceQuery
    from tools.research.provider import provider_schema
    from tools.research.config import bounded_evidence_enabled
    schema=deepcopy(EvidenceQuery.model_json_schema())
    if not bounded_evidence_enabled(study):schema['properties']['view']['enum'].remove('acceptance_certificate')
    else:schema['properties']['view']['description']='acceptance_certificate reads the complete deterministic independent task-acceptance view for SELECT; large raw full reads return bounded navigation without full-read credit.'
    return provider_schema(schema)


def tool_directory(host, registry):
    """Describe the currently admitted native tools without parameter schemas."""
    resources={'research_plan':'Action-specific original budgets and scientific admission.',
        'research_analysis':'Shared mathematical allowance; selected method and original execution admission.',
        'research_rl':'Existing RL stage/worker budgets and owned run identities.',
        'research_investigate':'Accounted Reporter requests when interpretation is needed; no scientific worker.',
        'evidence_read':'One public operation; original full-read rules.',
        'research_recall':'One public operation; Store navigation, no formal evidence credit.',
        'experience_retrieve':'One public operation; procedural guidance only.'}
    rows=[]
    for name,tool in registry.items():
        if name not in resources:continue
        row=dict(tool=name,purpose=tool.tool_spec.get('description','').split('.')[0],
            status='available_for_request_validation',resources=resources[name])
        if name in ('research_plan','research_rl'):
            field='action' if name=='research_plan' else 'operation'
            row['actions']=tool.tool_spec['inputSchema']['json']['properties'][field].get('enum',[])
        rows.append(row)
    return rows


def select_tool_route(host, payload, use_id):
    """Persist Main's selection only; never dispatch or infer a research action."""
    from tools.research.contracts import ResearchRouteQuery
    q=ResearchRouteQuery.model_validate(payload);s=state(host)
    directory=s['pilot'].get('tool_directory',[])
    entry=next((r for r in directory if r['tool']==q.tool),None)
    if entry is None:raise ValueError('TOOL_ROUTE_UNAVAILABLE: choose from the current tool directory')
    if (entry.get('actions') and q.action not in entry['actions']) or (not entry.get('actions') and q.action is not None):
        raise ValueError('TOOL_ROUTE_ACTION_REQUIRED_OR_UNAVAILABLE')
    value=dict(version='selected_tool_route_v1',tool=q.tool,action=q.action,tool_use_id=use_id,
        scientific_execution_started=False,formal_read_credit=False)
    ref=record(host,'research_tool_route',value)
    pilot=deepcopy(s['pilot']);pilot['tool_route']=ref;update(host,pilot=pilot)
    return dict(**value,scope='Selection only. The next request loads this Schema; original validation, authorization and budget checks still apply.')


def load_selected_tool_schema(host, registry, directory):
    """Reuse Strands' registry, keeping only the route and one selected tool."""
    from tools.research.contracts import ResearchRouteQuery
    s=state(host);route_ref=s['pilot'].get('tool_route')
    route=host.store.artifact(route_ref) if route_ref else {};name=route.get('tool')
    from tools.research.scientific_intent import explicit_actions, completed_question_plan, action_entry
    explicit=explicit_actions(s['spec']);diagnosis=completed_question_plan(host) if explicit else None
    if diagnosis:
        events=host.store.events(host.run_id)
        plan_seq=next(e['sequence'] for e in events if diagnosis['plan_reference'] in e['outputs'])
        route_seq=max((e['sequence'] for e in events if route_ref and route_ref in e['outputs']),default=-1)
        if plan_seq>route_seq:
            choice=diagnosis['agent_hypothesis'].get('next_research_action')
            route=action_entry(s['spec'],choice) or {};name=route.get('tool')
    # Frozen legacy interfaces retain their implicit mathematical continuation.
    # v3 uses only a later explicit route or the completed Plan's typed choice.
    if not explicit and (not name or (name=='research_plan' and route.get('action')=='diagnose')) and 'research_analysis' in registry:
        name='research_analysis'
    selected=registry.get(name)
    if selected and name=='research_plan':
        action=route.get('action');entry=next(r for r in directory if r['tool']==name)
        if action not in entry['actions']:selected=None
        else:
            spec=s['spec']
            selected.tool_spec={**selected.tool_spec,'inputSchema':{'json':plan_schema([action],decision_required=True,
                family_version=spec.get('family_space',{}).get('version'),
                diagnose_candidate_required=spec.get('research_decisions',{}).get('analysis_interface')=='bound_scientific_variables_v2',focused=True,study=spec)}}
    elif selected and name=='research_rl':
        schema=deepcopy(selected.tool_spec['inputSchema']['json']);actions=schema['properties']['operation']['enum']
        if route.get('action') not in actions:selected=None
        else:
            schema['properties']['operation']['enum']=[route['action']]
            selected.tool_spec={**selected.tool_spec,'inputSchema':{'json':schema}}
    router=registry['research_route'];schema=ResearchRouteQuery.model_json_schema()
    schema['properties']['tool']['enum']=[r['tool'] for r in directory]
    schema['description']='Choose one tool and its Plan action or RL operation from tool_directory. Selection performs no scientific execution. The loaded tool can be reused; call research_route to switch.'
    router.tool_spec={**router.tool_spec,'inputSchema':{'json':schema}}
    retained={'research_route'}
    if selected:retained.add(name)
    policy=s['spec'].get('research_decisions',{}).get('tool_schema_policy',{}).get('version')
    if policy in ('on_demand_tools_v2','on_demand_tools_v3','research_information_flow_v1'):
        # Retrieval must not unload the already chosen Plan. With no prior Plan,
        # expose an action matching the current owned object, without submitting it.
        plan=registry.get('research_plan')
        entry=next((r for r in directory if r['tool']=='research_plan'),None)
        if plan and entry and not (explicit and diagnosis and not name) and (name!='research_plan' or (selected is None and policy in ('on_demand_tools_v3','research_information_flow_v1'))):
            from tools.research.research_context import tool_continuation
            chosen=tool_continuation(host).get('plan_action')
            action=chosen if chosen in entry['actions'] else ('generate' if 'generate' in entry['actions'] else 'stop')
            from tools.research.config import bounded_evidence_enabled
            if bounded_evidence_enabled(s['spec']) and action not in entry['actions']:action=entry['actions'][0]
            if (chosen not in entry['actions'] and 'diagnose' in entry['actions'] and not protected(host)
                    and 'analysis' in s['spec'].get('capabilities',[])
                    and s['spec']['budgets']['mathematical_evaluations']>s.get('mathematical_evaluations',0)):
                from tools.research.research_context import decision_candidate,research_intent
                from tools.research.task_constraints import mathematical_method_view
                candidate=decision_candidate(host,{},research_intent(host))
                if candidate and any(m['formal_execution_authorized'] and m['planning_status'] not in
                        ('unauthorized','unsupported','insufficient_budget','blocked')
                        for m in mathematical_method_view(host,candidate)['methods'].values()):
                    action='diagnose'
            plan.tool_spec={**plan.tool_spec,'inputSchema':{'json':plan_schema([action],decision_required=True,
                family_version=s['spec'].get('family_space',{}).get('version'),
                diagnose_candidate_required=s['spec'].get('research_decisions',{}).get('analysis_interface')=='bound_scientific_variables_v2',
                focused=True,study=s['spec'])}}
            retained.add('research_plan')
    if policy=='research_information_flow_v1':
        retained.update(k for k in ('evidence_read','research_recall','experience_retrieve','research_investigate') if k in registry)
    for key in list(registry):
        if key not in retained:registry.pop(key)
    return dict(tool=name if selected else None,action=route.get('action') if selected else None,
        **(dict(plan_action=registry['research_plan'].tool_spec['inputSchema']['json']['properties']['action']['enum'][0])
           if 'research_plan' in retained else {}))




def bound_analysis_enabled(spec):
    return spec.get('research_decisions',{}).get('analysis_interface') in ('bound_scientific_variables_v1','bound_scientific_variables_v2')


def selected_analysis_schema(method, detail, *, bound=False):
    """Project the existing AnalysisRequest to one registered method."""
    from tools.research.contracts import AnalysisRequest
    from tools.research.optimal_capability import CONIC,SENSITIVITY
    schema=AnalysisRequest.model_json_schema();operation=detail['operation']
    common={'candidate','operation','model_source','operating_point','saved_state','execution','update_id','protocol','scoring_window_s'}
    extra={
        'native_dynamics_v1':{'native'},'short_input_response_v1':{'native'},
        'fixed_input_structure_v1':{'native','structure_response'},
        'mujoco_direct_control_v1':{'control_optimization'},
        'mujoco_nonlinear_task_capability_v1':{'control_optimization'},
        'mujoco_reoptimized_structure_response_v1':{'nonlinear_response'},
        'tendon_force_capability_v1':{'tendon_force_direction'},
        'design_sensitivity':{'design_sensitivity'},
        'task_capability':{'capability_comparison','capability_method','optimal_sensitivity'},
    }.get(operation,set())
    if operation=='task_capability':
        if method==SENSITIVITY:extra={'capability_method','optimal_sensitivity'}
        elif method==CONIC:extra={'capability_method'}
        else:extra={'capability_comparison'}
    allowed=common|extra
    schema['properties']={k:v for k,v in schema['properties'].items() if k in allowed}
    schema['properties']['operation']={'type':'string','const':operation}
    template=detail.get('request_template',{})
    for key in ('candidate','protocol'):
        if key in template:schema['properties'][key]={'const':deepcopy(template[key]),
            'description':schema['properties'][key]['description']+' Exact frozen value from the selected registered method.'}
    if method in (CONIC,SENSITIVITY):
        schema['properties']['capability_method']={'type':'string','const':CONIC}
        schema['required'].append('capability_method')
    required={'fixed_input_structure_v1':'structure_response','mujoco_direct_control_v1':'control_optimization',
        'mujoco_nonlinear_task_capability_v1':'control_optimization',
        'mujoco_reoptimized_structure_response_v1':'nonlinear_response',
        'tendon_force_capability_v1':'tendon_force_direction','design_sensitivity':'design_sensitivity'}
    if method==SENSITIVITY:schema['required'].append('optimal_sensitivity')
    elif operation in required:schema['required'].append(required[operation])
    if operation in ('linearization','controllability'):schema['required'].append('scoring_window_s')
    if detail.get('request_template',{}).get('model_source')=='mujoco':
        schema['properties']['model_source']={'type':'string','const':'mujoco'}
        schema['required'].append('model_source')
    schema['description']='Selected registered method: '+method+'. Required source and parameter details: '+json.dumps(detail.get('required_parameters',[]),ensure_ascii=False)+'. Exact method query: '+json.dumps(detail.get('detail_query'),ensure_ascii=False)
    if bound:
        for key in ('candidate','protocol','operation','capability_method'):
            schema['properties'].pop(key,None)
        # A native registered operation uniquely selects MuJoCo. Reduced methods
        # retain the controller/GVS/SoRoSim choice; never infer it from a default.
        if template.get('model_source')=='mujoco':schema['properties'].pop('model_source',None)
        else:schema['properties']['model_source']['enum']=['controller','gvs','sorosim']
        schema['required']=[k for k in schema['required'] if k in schema['properties']]
        schema['required']+=['operating_point']+(['model_source'] if 'model_source' in schema['properties'] else [])
        schema['required']=list(dict.fromkeys(schema['required']))
        from tools.research.task_constraints import analysis_operating_points
        points=analysis_operating_points(method,operation)
        schema['properties']['operating_point']={**schema['properties']['operating_point'],'enum':points}
        schema['properties']['operating_point'].pop('default',None)
        if len(points)==1 and points[0]!='saved_state':
            schema['properties'].pop('operating_point')
            schema['required'].remove('operating_point')
        if operation not in ('linearization','controllability'):schema['properties'].pop('scoring_window_s',None)
        schema['allOf']=[{'if':{'properties':{'operating_point':{'const':'saved_state'}},'required':['operating_point']},
            'then':{'oneOf':[{'required':['saved_state'],'properties':{'saved_state':{'$ref':'#/$defs/EvidenceRef'},'execution':{'type':'null'},'update_id':{'type':'null'}}},
                {'required':['execution','update_id'],'properties':{'execution':{'$ref':'#/$defs/EvidenceRef'},'update_id':{'type':'integer','minimum':0},'saved_state':{'type':'null'}}}]},
            'else':{'properties':{k:{'type':'null'} for k in ('saved_state','execution','update_id')}}}]
        if len(points)==1 and points[0]!='saved_state':
            schema.pop('allOf')
            for key in ('saved_state','execution','update_id'):schema['properties'].pop(key,None)
        if 'scoring_window_s' in schema['properties'] and template.get('protocol'):
            windows=template['protocol']['windows_s']
            schema['properties']['scoring_window_s']['anyOf']=[{'type':'number','enum':windows},{'type':'null'}]
            if operation in ('linearization','controllability'):
                schema['properties']['scoring_window_s']={'type':'number','enum':windows,'exclusiveMinimum':0}
        # Initial tendon support and sequence optimization reject free native options.
        if operation in ('tendon_force_capability_v1','mujoco_direct_control_v1','mujoco_nonlinear_task_capability_v1','mujoco_reoptimized_structure_response_v1'):
            schema['properties'].pop('native',None)
        elif operation=='native_dynamics_v1':
            schema['$defs']['NativeAnalysisOptions']['properties']={k:v for k,v in schema['$defs']['NativeAnalysisOptions']['properties'].items() if k=='tensions_n'}
        elif operation=='fixed_input_structure_v1':
            schema['$defs']['NativeAnalysisOptions']['properties'].pop('difference_step_n',None)
            schema['$defs']['NativeAnalysisOptions']['properties'].pop('correction_radius_n',None)
        guide=detail.get('operating_point_guidance',{})
        schema['description']='Selected method '+method+'. Frozen identity and protocol are bound by the program; submit scientific variables only. '+json.dumps(guide,separators=(',',':'),ensure_ascii=False)
    if detail.get('control_input_guidance'):
        schema['description']+=' Control input prerequisites: '+json.dumps(detail['control_input_guidance'],separators=(',',':'),ensure_ascii=False)
    needed=set()
    def visit(value):
        if isinstance(value,dict):
            if '$ref' in value:
                key=value['$ref'].rsplit('/',1)[-1]
                if key not in needed:
                    needed.add(key);visit(schema['$defs'][key])
            for child in value.values():visit(child)
        elif isinstance(value,list):
            for child in value:visit(child)
    visit({k:v for k,v in schema.items() if k!='$defs'})
    schema['$defs']={k:v for k,v in schema['$defs'].items() if k in needed}
    return schema


def bind_selected_analysis_request(host, payload, *, tool_use_id, selection=None, scientific_question=None):
    """One audited boundary from Main variables to the unchanged full contract."""
    from jsonschema import Draft202012Validator
    from tools.research.contracts import AnalysisRequest
    from tools.research.design import verify_candidate
    from tools.research.research_context import research_intent
    selection=selection or selected_analysis(host,None)
    if not selection:raise ValueError('SELECTED_AUTHORIZED_ANALYSIS_METHOD_REQUIRED')
    method,detail=selection
    intent=research_intent(host)['latest_decision']
    candidate=intent['agent_hypothesis']['decision']['selected_candidate']
    verify_candidate(host,candidate)
    schema=selected_analysis_schema(method,detail,bound=True)
    extra=sorted(set(payload)-set(schema['properties']))
    if extra:raise ValueError('SELECTED_ANALYSIS_SCHEMA_MISMATCH: unsupported or frozen fields: '+', '.join(extra))
    spec=state(host)['spec'];template=detail['request_template']
    if template.get('candidate')!=candidate or template.get('protocol')!=spec['analysis_protocol']:
        raise ValueError('SELECTED_ANALYSIS_FROZEN_BINDING_MISMATCH')
    frozen=dict(candidate=deepcopy(candidate),protocol=deepcopy(spec['analysis_protocol']),operation=detail['operation'])
    sources=dict(candidate=dict(reference=intent['plan_reference'],pointer='/original_plan/decision/selected_candidate'),
        protocol=dict(source='frozen Study',study_id=spec['study_id'],freeze=state(host)['freeze'],pointer='/spec/analysis_protocol'),
        operation=dict(source=detail['detail_query'],pointer='/operation'))
    if template.get('model_source')=='mujoco':
        frozen['model_source']='mujoco';sources['model_source']=dict(source=detail['detail_query'],pointer='/request_template/model_source')
    if 'capability_method' in template:
        frozen['capability_method']=template['capability_method'];sources['capability_method']=dict(source=detail['detail_query'],pointer='/request_template/capability_method')
    from tools.research.task_constraints import analysis_operating_points
    points=analysis_operating_points(method,detail['operation'])
    if len(points)==1 and points[0]!='saved_state':
        frozen['operating_point']=points[0]
        sources['operating_point']=dict(source='AnalysisRequest.validate_operating_point',method=method,legal_options=points)
    full={**deepcopy(payload),**frozen}
    audit_input=dict(version=spec['research_decisions']['analysis_interface'],tool_use_id=tool_use_id,
        method=method,raw_main_input=deepcopy(payload),full_request=full,provider_schema=schema,
        field_sources={**{k:dict(source='Main tool request',tool_use_id=tool_use_id,pointer='/'+k) for k in payload},**sources})
    if scientific_question is not None:
        from tools.research.scientific_intent import question_schema
        audit_input.update(raw_main_input=deepcopy(scientific_question),
            provider_schema=question_schema(spec,verify_candidate(host,candidate)),internal_binding_schema=schema,
            compiled_variables=deepcopy(payload))
        audit_input['field_sources'].update({k:dict(source='Deterministic ScientificQuestion compilation',
            tool_use_id=tool_use_id,plan_reference=intent['plan_reference']) for k in payload})
    audit=record(host,'analysis_request_binding',audit_input)
    # Pydantic first preserves exact scientific error codes, even if the compact
    # schema could reject the same point. Neither validator changes Main input.
    AnalysisRequest.model_validate(full)
    Draft202012Validator(schema).validate(payload)
    Draft202012Validator(AnalysisRequest.model_json_schema()).validate(full)
    record(host,'analysis_request_binding_validated',dict(binding=audit,json_schema_valid=True,pydantic_valid=True))
    return full


def selected_analysis(host, brief):
    """Expose only the method in the last settled diagnose decision."""
    from tools.research.research_context import research_intent
    intent=research_intent(host)['latest_decision'] or {}
    decision=(intent.get('agent_hypothesis') or {}).get('decision') or {}
    method=decision.get('selected_method');candidate=intent.get('candidate')
    if (intent.get('action')!='diagnose' or intent.get('execution_status')!='completed' or not method or not candidate
            or (bound_analysis_enabled(state(host)['spec']) and decision.get('selected_candidate')!=candidate)):return None
    from tools.research.task_constraints import mathematical_method_view
    try:detail=mathematical_method_view(host,candidate)['methods'].get(method)
    except (ValueError,KeyError):return None
    if (not detail or not detail.get('formal_execution_authorized')
            or detail.get('planning_status') in ('unauthorized','unsupported','insufficient_budget','blocked')
            or (detail.get('registered') and detail.get('executable') is False)):
        return None
    return method,detail


def validate_selected_analysis_payload(payload, schema, detail):
    """Explain selected-schema binding failures without changing the request."""
    problems=[]
    extra=sorted(set(payload)-set(schema['properties']))
    if extra:problems.append('unsupported fields: '+', '.join(extra))
    if payload.get('operation')!=detail['operation']:
        problems.append('operation must equal '+detail['operation'])
    for key,definition in schema['properties'].items():
        if 'const' not in definition or payload.get(key)==definition['const'] or key=='operation':continue
        if isinstance(definition['const'],dict) and not isinstance(payload.get(key),dict):
            problems.append(key+' must be a JSON object matching the selected schema constant, not a string or null')
        else:
            problems.append(key+' must match the exact selected schema constant')
    if problems:raise ValueError('SELECTED_ANALYSIS_SCHEMA_MISMATCH: '+'; '.join(problems))


def error_feedback(host, use, exc, before):
    """Small correction response; exact rejected payload and traceback stay in Store."""
    import traceback
    from jsonschema.exceptions import ValidationError as SchemaValidationError
    s=state(host)
    full=record(host,'tool_request_error',dict(tool_use=use,error=type(exc).__name__,message=str(exc),traceback=traceback.format_exc()))
    counts=lambda v:tuple(v.get(k,0) for k in ('physical_replay_launches','nmpc_launches','mathematical_evaluations','offline_nlp','bdf_replays','local_solves','admitted_training_stages'))
    message=str(exc);code=message.split(':',1)[0].split('\n',1)[0]
    field=None;expected=message[:300];refs=[];contract=None;issues=[]
    if hasattr(exc,'issues'):
        contract='ScientificStructureSearch';issues=exc.issues
        field=issues[0]['field'];expected=issues[0]['reason'];message=str(exc)
    if hasattr(exc,'errors'):
        errors=exc.errors(include_url=False,include_context=False,include_input=False)
        search=use.get('input',{}).get('search')
        if isinstance(search,dict) and search.get('version')=='family_mixed_search_v1':
            matching=[e for e in errors if any('FamilyMixedSearch' in str(part) for part in e['loc'])]
            if matching:errors=matching
        generation=use.get('input',{}).get('generation')
        if isinstance(generation,dict) and generation.get('version')=='serial_family_generation_v2':
            matching=[e for e in errors if any('GenerationRequestV2' in str(part) for part in e['loc'])]
            if matching:errors=matching
        field='.'.join(map(str,errors[0]['loc'])) or None
        expected='; '.join(e['msg'] for e in errors[:3])[:400]
        code=errors[0]['type']
        from tools.research.structure_intent import contract_issues
        contract,issues=contract_issues(use.get('input',{}),errors)
        message='; '.join(i['field']+': '+i['reason'] for i in issues)
        if contract and issues:
            field=issues[0]['field'];expected=issues[0].get('expected',issues[0]['reason'])
    elif isinstance(exc,SchemaValidationError):
        # Keep the exact validator dump in Store; send a field-specific repair
        # instead of Schema internals on the focused-tool correction turn.
        path=list(exc.absolute_path);message=exc.message
        missing=next((k for k in exc.validator_value if k not in exc.instance),None) if exc.validator=='required' else None
        if missing is not None:path.append(missing)
        field='.'.join(map(str,path)) or None
        code='TOOL_SCHEMA_'+str(exc.validator).upper();expected=exc.message
        if field=='decision.selected_candidate' and use.get('name')=='research_plan' and use.get('input',{}).get('action')=='diagnose':
            code='SELECTED_ANALYSIS_CANDIDATE_REQUIRED';message=code+': '+exc.message
        if (use.get('input',{}).get('search') or {}).get('version')=='scientific_structure_search_v1' or 'research_goal' in (use.get('input',{}).get('search') or {}):
            contract='ScientificStructureSearch'
            issues=[dict(field=field,error_type=str(exc.validator),reason=exc.message)]
    hints={
        'SELECTED_ANALYSIS_CANDIDATE_REQUIRED':('decision.selected_candidate','Choose an exact owned candidate reference from the current candidate index, then resubmit the diagnose Plan with that reference. Method selection is not settled and research_analysis is unavailable until this identity is explicit; no candidate is inferred.'),
        'NATIVE_ANALYSIS_REQUIRES_EXACT_STATE_OR_FROZEN_INITIALIZATION':('operating_point','Native methods use model_source=mujoco and operating_point=standardized_initial_pretension with no saved source, or operating_point=saved_state with saved_state OR execution+update_id. Retrieve method details for source/window requirements.'),
        'DISPOSITION_REQUIRES_EXACT_ACTUAL_READ':('experience_disposition','Keys must identify an actual experience_retrieve operation=read receipt or its exact entry_id@revision. Scientific artifact IDs, invented hypothesis names, search results and SELECT physical evidence are not experience keys. If this Study does not expose legal experience_retrieve, remove the inapplicable experience_disposition field; do not guess IDs.'),
        'explicit evidence_read of this completed evaluation required':('selected_execution','Publicly evidence_read the exact selected_execution with view=full and pointer="" before SELECT; /acceptance alone does not satisfy the whole-result read required here.'),
        'ORDERED_V2_CORRECTION_WINDOW_REQUIRED':('control_search.settings.correction_window_s','0 <= window[0] <= knots[0] < knots[-1] <= window[1] <= task duration'),
        'DECISION_CANDIDATE_MISMATCH':('decision.selected_candidate','Match the exact action candidate (for physical_replay, physical_replay.candidate); source is a control/result reference and must not replace the candidate.'),
        'MUJOCO_REQUIRES_EXPLICIT_NATIVE_METHOD_AND_MODEL_SOURCE':('operation/model_source','Unsupported method-model combination: instantaneous_braking_v1 is not a MuJoCo native method. Choose a registered operation and its supported model_source from mathematical_capabilities; native options cannot make an unsupported combination executable.'),
        'CONTROL_SOURCE_REQUIRES_EXACT_PARENT':('control_seed.parent','When control_seed.source is supplied, supply its exact parent candidate too. For complete measured NMPC input, parent must equal control_seed.candidate; source is the execution result, not the candidate.'),
        'PHYSICAL_REPLAY_CANDIDATE_TASK_MODEL_OR_SEQUENCE_MISMATCH':('source','Use a candidate-bound source; initialize_control explicitly rebinds inherited controls'),
        'UNREGISTERED_RESEARCH_EVIDENCE':('supporting_evidence','Readable does not mean registered. Query working_set /citation_eligibility; use only registered references whose supported_inferences match the claim. Reading does not register evidence.'),
        'REGISTERED_CURRENT_ANALYSIS_REQUIRED':('control_seed.response_evidence','Request input_sensitivity for the selected candidate, then use its registered result reference'),
        'VERIFIED_CANDIDATE_INPUT_SENSITIVITY_REQUIRED':('control_seed.response_evidence','Use computed, numerically verified input_sensitivity bound to this candidate, model, task, operating point and tendon order'),
        'STOP_MUST_CITE_ALL_NEW_EXPERIMENT_RESULTS':('supporting_evidence','Explicitly cite the complete current research.all_fresh_results index and explain the conclusions'),
        'ENGINEERING_TOOL_UNAVAILABLE':('action','Choose an available operation from current packet; engine failure is not scientific infeasibility')}
    from tools.research.config import bounded_evidence_enabled
    if bounded_evidence_enabled(s['spec']):
        formal_hint=('selected_execution','Read acceptance_certificate for this exact independent evaluation. Its complete validated view must reach the next real Provider request before SELECT; a local marker or partial preview is insufficient.')
        hints['explicit evidence_read of this completed evaluation required']=formal_hint
        hints['the Main Agent must receive the complete evidence_read result']=formal_hint
    for marker,(f,hint) in hints.items():
        if marker in message:code=marker;field=f;expected=hint
    if use.get('input',{}).get('action')=='diagnose' and 'selected_candidate' in use.get('input',{}):
        field='selected_candidate';expected='Move this owned candidate reference to decision.selected_candidate; omit the top-level field.'
    if code=='TOOL_ROUTE_ACTION_REQUIRED_OR_UNAVAILABLE':
        entry=next((r for r in s['pilot'].get('tool_directory',[]) if r['tool']==use['input'].get('tool')),None)
        field='action'
        expected=('Supply action from '+json.dumps(entry['actions'])+' for '+entry['tool']+'.'
            if entry and entry.get('actions') else 'Omit action for tools without actions in tool_directory.')
    if 'ACTION_REQUIRES_ONLY_' in message:
        from tools.research.contracts import PLAN_PAYLOADS
        field=PLAN_PAYLOADS.get(use['input'].get('action'),'action')
        expected='Action '+str(use['input'].get('action'))+' requires non-null '+field+' and no other action payload. '+message[message.index('ACTION_REQUIRES_ONLY_'):].split('\n')[0][:160]
        if use['input'].get('action')=='physical_replay':expected+='; put candidate/source inside physical_replay and match decision.selected_candidate to physical_replay.candidate; omit top-level candidate.'
    if hasattr(exc,'errors') and any(e['loc'] and e['loc'][0]=='protocol' and e['type']=='extra_forbidden' for e in errors):
        field='protocol';expected='Use the complete frozen analysis_protocol from the method request_template/protocol in mathematical_capabilities. Do not add protocol fields; holding duration belongs to the frozen task.'
    if hasattr(exc,'errors'):
        setting_error=next((e for e in errors if e['type']=='extra_forbidden' and
            tuple(e['loc'][-2:])==('settings','regularization')),None)
        if setting_error:
            from tools.research.contracts import LocalControlSearchSettings
            field='.'.join(map(str,setting_error['loc']))
            expected=('regularization is not supported. Use only LocalControlSearchSettings fields: '
                +', '.join(LocalControlSearchSettings.model_fields)+'. Plan control_search uses physical replay callbacks; '
                'Native optimization requires research_analysis and the registered request_template. '
                'Do not rename fields or assume zero integration; normal authorization and cost admission still apply.')
    if isinstance(exc,(KeyError,IndexError)) and use.get('name')=='evidence_read':
        code='INVALID_EVIDENCE_POINTER';field='pointer';expected='Read the parent pointer with view=summary to obtain actual child keys'
        if use['input'].get('reference') and not getattr(exc,'evidence_navigation',None):
            refs=[use['input']['reference']]
            try:
                value=host.store.artifact(refs[0]);parent=''
                for part in use['input'].get('pointer','').strip('/').split('/') if use['input'].get('pointer') else []:
                    key=part.replace('~1','/').replace('~0','~')
                    if isinstance(value,dict) and key not in value:break
                    if isinstance(value,list) and (not key.isdigit() or int(key)>=len(value)):break
                    value=value[int(key)] if isinstance(value,list) else value[key];parent+='/'+part
                if isinstance(value,dict):expected='Available children at '+(parent or '/')+': '+', '.join(value)
                elif isinstance(value,list):expected='List at '+(parent or '/')+' has '+str(len(value))+' items; use view=range or an index from 0 through '+str(len(value)-1)
                if use['input'].get('fields'):field='fields'
            except (ValueError,KeyError,IndexError,TypeError):pass
        derived=getattr(exc,'evidence_navigation',{}).get('derived_view_query')
        if derived:
            code='EVIDENCE_VIEW_MISMATCH';field='view'
            expected='Use this exact derived-view query: '+json.dumps(derived,separators=(',',':'))
    if code=='RESEARCH_INTENT_ACTION_MISMATCH':
        from tools.research.contracts import PLAN_RESEARCH_INTENTS
        field='decision.research_intent';action=use['input']['action']
        expected=f'action={action} requires decision.research_intent={PLAN_RESEARCH_INTENTS[action]}'
    if 'EVIDENCE_RANGE_REQUIRES_LIST_POINTER' in message:
        field='pointer';expected='Read the current reference root with view=summary, then use an advertised list read_pointer with view=range'
    if code=='BATCH_REQUEST_EXCEEDS_FROZEN_SHARED_CAPACITY':
        from tools.research.budget import decision_budget
        science=decision_budget(host)['science_budget']
        requested=(use['input'].get('control_search') or {}).get('settings',{}).get('evaluation_requests')
        maximum=s['spec']['budgets']['physical_launches']+1
        field='control_search.settings.evaluation_requests'
        expected=(f'Plan control_search cap {requested} exceeds frozen declared callback maximum {maximum} '
            '(physical_launches + one possibly reusable baseline). Each new callback uses a full physical replay; '
            f'raw remaining shared launches={science["remaining_physical"]}, full replays={science["remaining_full_replays"]}. '
            'These are remaining totals, not permission or a guarantee that a batch fits. Response FD needs a baseline plus '
            'effective coefficient probes and one candidate per completed update. Native optimization instead requires '
            'research_analysis with its registered template and mathematical allowance; internal native rollouts are not independent replay credits.')
    navigation=getattr(exc,'evidence_navigation',{})
    if use['name']=='evidence_read' and 'EVIDENCE_FIELDS_REQUIRES_NONEMPTY_FIELDS' in message:
        code='EVIDENCE_FIELDS_REQUIRES_NONEMPTY_FIELDS';field='fields'
        query={k:use['input'][k] for k in ('reference','pointer') if k in use['input']}
        query['view']='summary'
        expected='Empty fields select no information. Read the object summary, then select at least one advertised child key. Use exact query: '+json.dumps(query,separators=(',',':'))
    if navigation:
        query=navigation['corrected_query']
        if navigation.get('derived_view_query'):code='EVIDENCE_VIEW_MISMATCH';field='view'
        elif use['input'].get('fields'):field='fields'
        else:field='pointer'
        expected='Use exact query: '+json.dumps(query,separators=(',',':'))
    if 'PROTECTED_EVIDENCE_READ_REQUIRES' in message:
        field='reference';expected='Only current result references are readable during closeout; use all_fresh_results and select a fresh pass or STOP'
    citation={}
    if code=='UNREGISTERED_RESEARCH_EVIDENCE' or code.startswith(('INFERENCE_NOT_SUPPORTED','EVIDENCE_TASK_IDENTITY','EVIDENCE_DESIGN_IDENTITY','EVIDENCE_MODEL_SCOPE')):
        from tools.research.evidence_policy import registered_references,citation_inventory,citation_role
        from schemas.platform import EvidenceRef
        known=registered_references(host)
        cited=[plain(EvidenceRef.model_validate(r)) for r in use['input'].get('supporting_evidence',[])]
        refs=[r for r in cited if r not in known or code!='UNREGISTERED_RESEARCH_EVIDENCE']
        anchor=next(iter(known),s.get('family_space_reference'))
        inference=(use['input'].get('decision') or {}).get('claimed_inference','empirical_search')
        inventory=citation_inventory(host)
        candidates=[r for r in inventory if inference=='empirical_search' or inference in r['supported_inferences']]
        citation=dict(rejected_references=refs,registered_count=len({r['artifact_id'] for r in known}),
            citation_errors=[dict(reference=r,role=citation_role(host,r),
                claimed_inference=inference,
                reason=('Reporter reports organize existing results and cannot support formal scientific inference.'
                    if citation_role(host,r)=='reporter_report' else
                    'Not registered for supporting_evidence; reading never changes citation eligibility.' if r not in known else message[:400]),
                correction=('Use result_reference from report findings, then check the inventory for this inference and task scope. '
                    'Exploratory empirical_search may use supporting_evidence=[]; SELECT/STOP keep existing gates.')) for r in refs],
            candidate_registered_results=candidates[-3:],candidate_count=len(candidates),
            inventory_query=dict(reference=anchor,view='working_set',pointer='/citation_eligibility'),
            candidate_scope='Candidates are query leads, not automatic replacements; verify candidate/task/model and formal-read gates.')
    new_analysis=[host.store.artifact(r) for r in s.get('analysis_results',[]) if r not in before.get('analysis_results',[])]
    worker_started=(new_analysis[-1].get('boundary') or {}).get('worker_started') if new_analysis else False if counts(before)==counts(s) else None
    return dict(status='rejected' if counts(before)==counts(s) else 'execution_failed',error_code=code[:100],field=field,
        reason=message[:1000],
        **(dict(contract=contract,issues=issues) if contract else {}),
        worker_started=worker_started,
        charged_method_counts={k:s.get(k,0)-before.get(k,0) for k in ('physical_replay_launches','nmpc_launches','mathematical_evaluations')},
        evidence_navigation=getattr(exc,'evidence_navigation',None),
        expected=expected,input_query=dict(reference=full,view='full',pointer='/tool_use/input'),
        scientific_execution_started=counts(before)!=counts(s),relevant_references=refs,full_error_reference=full,**citation)

def build_harness(host,*,transport,api_key,instructions,model_class,tool_executor,research_tools,configuration_path,session_directory,session_id=None):
    from strands.experimental.context_manager import Offload
    s=state(host)
    provider=s['pilot']['provider']
    model=build_model(provider,api_key=api_key,transport=transport,model_class=model_class)
    # Public offload stores originals for retrieval; no auxiliary model requests.
    compact=bool(s['spec'].get('research_decisions',{}).get('context_limits'))
    context=dict(strategies=[Offload.truncate('tool_results',{'preview_tokens':500 if compact else 1024}).when(threshold=1500 if compact else 4096)])
    storage=session_storage(session_directory)
    from strands.session import SnapshotSessionManager
    manager=SnapshotSessionManager(session_id or s['pilot']['framework_session_id'],storage=storage,save_latest_on='message')
    agent=create_harness(model=model,tools=research_tools,instructions=instructions,
        builtin_tools=[],builtin_plugins=[],background_tasks=False,memory=False,skills=False,
        context_manager=context,session=manager,storage=storage,
        retry_strategy=None,callback_handler=None,caching=False,tool_executor=tool_executor)
    atomic_json(configuration_path,dict(harness='strands-harness==0.2.0',sdk='strands-agents==1.59.0',
        provider=provider,registered_tools=sorted(agent.tool_names),session_id=session_id or s['pilot']['framework_session_id'],
        retry_controllers=0,context='public tool-result offload and retrieval',offload_threshold=1500 if compact else 4096,
        offload_preview_tokens=500 if compact else 1024,
        dynamic_context='request-only tail via public OpenAIModel.format_request; native SDK history unchanged',
        transport='accounted live boundary'))
    return agent

async def wait_training(host):
    """No provider turns or summary snapshots while an owned worker is active."""
    from tools.research.rl import reconcile, dispatch as rl_dispatch
    from tools.rl import run
    while True:
        active=False
        for run_id in state(host).get('rl_runs',{}):
            status=reconcile(host,run_id,lightweight=True)
            active=active or status['worker_alive']
        if not active:
            return
        await asyncio.sleep(2.)

async def deliver_science_before_decision(host,agent,transport,*,max_model_calls=None):
    """Settle L1 only after native results are paired and durably recoverable.

    This is an intra-invocation boundary, not session_handoff.safe_boundary.
    The latter additionally requires a completed invocation and remains unchanged.
    """
    from tools.research.reporter import current_reports, complete_reports
    from tools.research.session_handoff import unmatched
    if pending(host) or state(host)['pilot'].get('unconsumed_response'):
        raise ValueError('SCIENCE_DELIVERY_REQUIRES_CONSUMED_PROVIDER_RESPONSE')
    if not any(v['interpretation_status']=='deferred' for _,v in current_reports(host)):return
    if state(host).get('pending') or unmatched(agent.messages):
        raise ValueError('SCIENCE_DELIVERY_REQUIRES_PAIRED_SETTLED_TOOLS')
    with host.store.connect(True) as db:
        if db.execute('SELECT COUNT(*) FROM calls WHERE run_id=? AND receipt IS NULL',(host.run_id,)).fetchone()[0]:
            raise ValueError('SCIENCE_DELIVERY_REQUIRES_SETTLED_RECEIPTS')
    original={}
    for event in host.store.events(host.run_id):
        if event['kind']=='model_original_tool_feedback':
            value=host.store.artifact(event['outputs'][0]);original[value['tool_use']['toolUseId']]=value['result']
    for message in agent.messages:
        for block in message['content']:
            result=block.get('toolResult')
            # Public SDK offload may replace large evidence-read text with a
            # retrievable preview. Identity/status pairing must survive; original
            # content is already immutable in Store and the SDK stash.
            if result and result['toolUseId'] in original and result['status']!=original[result['toolUseId']]['status']:
                raise ValueError('SCIENCE_DELIVERY_ORIGINAL_TOOL_STATUS_MISMATCH')
    await agent._session_manager.save_snapshot(agent,is_latest=True)
    record(host,'science_delivery_boundary',dict(session_id=agent._session_manager.session_id,
        sdk_message_identity=digest(agent.messages),paired=True,receipts_settled=True))
    await complete_reports(host,transport,max_model_calls=max_model_calls)
    if pending(host) or state(host)['pilot'].get('unconsumed_response') or any(
            v['interpretation_status']=='deferred' for _,v in current_reports(host)):
        raise ValueError('SCIENCE_DELIVERY_INCOMPLETE_BLOCKS_DECISION')


async def pause_completed_invocation(host,agent,completed):
    """Pause only at the existing durable handoff boundary, with delivered reports."""
    from tools.research.session_handoff import safe_boundary, trusted_history
    from tools.research.reporter import current_reports
    await wait_training(host)
    if any(v['interpretation_status']=='deferred' for _,v in current_reports(host)):
        raise ValueError('REPORTER_DELIVERY_REQUIRED_BEFORE_SUPERVISOR_PAUSE')
    await agent._session_manager.save_snapshot(agent,is_latest=True)
    with host.store.connect(True) as db:
        safe_boundary(host,state(host),db,agent.messages)
    trusted_history(host,agent)
    record(host,'supervisor_pause',dict(completed_invocations=completed,
        session_id=agent._session_manager.session_id,sdk_message_identity=digest(agent.messages),
        research_status=state(host)['research_status'],budgets_preserved=True))


async def converse(host,*,session_handoff=None,pause_after_completed_invocations=None,handoff_before_next_request=False,handoff_request_bytes=None,pause_exploration_remaining=None,restore_only=False,recover_incomplete=False,max_new_provider_requests=None,operator_request=None):
    from tools.research.config import conversation_policy, tool_schema_policy
    recent_policy=conversation_policy(state(host)['spec'])
    on_demand=bool(tool_schema_policy(state(host)['spec']))
    if session_handoff is None:session_handoff=bool(recent_policy)
    if pause_after_completed_invocations is not None and (type(pause_after_completed_invocations) is not int or pause_after_completed_invocations<1):
        raise ValueError('POSITIVE_COMPLETED_INVOCATION_COUNT_REQUIRED')
    if max_new_provider_requests is not None and (type(max_new_provider_requests) is not int or max_new_provider_requests<1):
        raise ValueError('POSITIVE_NEW_PROVIDER_REQUEST_LIMIT_REQUIRED')
    max_model_calls=(host.store.remaining()['used']['model_calls']+max_new_provider_requests if max_new_provider_requests is not None else None)
    from tools.research.state import require_authorization
    require_authorization(host)
    if state(host)['spec'].get('initial_structure_strategy'):
        from tools.research.tool_readiness import execution_environment
        if execution_environment(state(host)['spec'])['status']!='ready':
            raise ValueError('HOST_MATH_NMPC_ENVIRONMENT_PREFLIGHT_REQUIRED_BEFORE_PROVIDER')
    from tools.research.core import guard,dispatch,experience,read_evidence,packet
    from tools.research.contracts import Plan,ExperienceQuery,EvidenceQuery,AnalysisRequest,RLRequest
    from tools.research.reporter import InvestigationRequest, investigate, scientific_feedback, complete_reports
    if session_handoff and not state(host)['pilot'].get('session_handoff_live_admitted'):
        raise ValueError('LIVE_PROVIDER_CONTINUATION_UNVERIFIED_HANDOFF_NOT_ADMITTED')
    if handoff_request_bytes is not None and (type(handoff_request_bytes) is not int or handoff_request_bytes<1):
        raise ValueError('POSITIVE_HANDOFF_REQUEST_BYTES_REQUIRED')
    if pause_exploration_remaining is not None and (type(pause_exploration_remaining) is not int or pause_exploration_remaining<0):
        raise ValueError('NONNEGATIVE_EXPLORATION_REVIEW_THRESHOLD_REQUIRED')
    if (bool(recent_policy and session_handoff) or handoff_before_next_request or handoff_request_bytes is not None or pause_exploration_remaining is not None) and (not session_handoff or state(host)['pilot'].get('session_handoff_boundary')!='request_feedback'):
        raise ValueError('REQUEST_FEEDBACK_LIVE_ADMISSION_REQUIRED')
    if state(host)['spec'].get('mode') == 'engineering_numerical':
        raise ValueError('NUMERICAL_MODE_FORBIDS_APPLICATION_MODEL_ENDPOINTS')
    from strands.tools.tools import PythonAgentTool
    from strands.tools.executors import SequentialToolExecutor
    from strands.hooks.events import BeforeModelCallEvent, BeforeToolCallEvent, AfterToolCallEvent
    def feedback_context_references():
        refs=[]
        for event in host.store.events(host.run_id):
            if event['kind']!='model_original_tool_feedback':
                continue
            value=host.store.artifact(event['outputs'][0])
            use=value['tool_use']
            if use['name'] not in ('research_plan','research_rl','research_analysis') or (use['name']=='research_plan' and use['input'].get('action') in ('stop',None)):
                continue
            if value['result']['status']!='success':
                continue
            refs.extend(use['toolUseId']+'_'+str(i) for i,_ in enumerate(value['result'].get('content',[])))
        return refs
    guard(host)
    if pending(host):
        raise ValueError('UNKNOWN_PROVIDER_OUTCOME_RECOVER_BEFORE_SEND')
    provider=state(host)['pilot']['provider']
    credential_path=Path(state(host)['spec']['runtime']['credentials_reference']).expanduser()
    api_key=credential(provider,credential_path)
    class Boundary(LiveBoundary):
        async def handle_async_request(self,request):
            s=state(host)
            if s['research_status']=='stopped' or s['pending']:
                raise ValueError('SEALED_STOP_OR_PENDING_WORK_BLOCKS_SEND')
            if not s['pilot'].get('unconsumed_response'):
                wire=json.loads(request.content)
                if protected(host):
                    definitions={t['function']['name']:t['function'] for t in wire.get('tools',[])}
                    action=definitions.get('research_plan',{}).get('parameters',{}).get('properties',{}).get('action',{})
                    permitted=closeout_operations(host)
                    plan_valid=(not action or (bool(action.get('enum')) and set(action['enum'])<=set(permitted['research_plan']))) if on_demand else action.get('enum')==permitted['research_plan']
                    if not plan_valid or set(definitions)-({'research_plan','research_rl','evidence_read','research_route'} if on_demand else {'research_plan','research_rl','evidence_read','retrieve_context'}):
                        raise ValueError('PROTECTED_SEND_REQUIRES_CLOSEOUT_NATIVE_SCHEMA')
                    rl=definitions.get('research_rl')
                    if rl and (not set(rl['parameters']['properties']['operation'].get('enum',[]))<=set(permitted['research_rl']) if on_demand else rl['parameters']['properties']['operation'].get('enum')!=permitted['research_rl']):
                        raise ValueError('PROTECTED_RL_SEND_REQUIRES_EXISTING_WORK')
                    retrieval=definitions.get('retrieve_context')
                    if retrieval:
                        advertised=retrieval.get('parameters',{}).get('properties',{}).get('reference',{}).get('enum')
                        if advertised is None or not set(advertised)<=set(feedback_context_references()):
                            raise ValueError('PROTECTED_CONTEXT_RETRIEVAL_REQUIRES_EXISTING_FEEDBACK')
            return await super().handle_async_request(request)
    boundary=Boundary(host,max_model_calls=max_model_calls)
    def handler(kind):
        def run(use,**kwargs):
            before=state(host)
            try:
                from tools.research.scientific_intent import enabled as question_enabled
                # The scientific compiler validates its versioned contract and
                # operation semantics before candidate parameter membership.
                if on_demand and kind!='route' and not (kind=='analysis' and question_enabled(before['spec'])):
                    from jsonschema import Draft202012Validator
                    Draft202012Validator(agent.tool_registry.registry[use['name']].tool_spec['inputSchema']['json']).validate(use['input'])
                from tools.research.evidence_policy import english_native
                if kind=='plan':
                    payload=use['input']
                    selection_schema=agent.tool_registry.registry[use['name']].tool_spec['inputSchema']['json']
                    if selection_schema.get('x-research-reference-choices'):
                        from tools.research.object_choices import expand_references,bind_plan_selection
                        payload=bind_plan_selection(host,expand_references(payload,selection_schema))
                    if payload.get('action')=='physical_replay' and 'result_choice' in (payload.get('physical_replay') or {}):
                        from tools.research.object_choices import expand_choice
                        payload,selection=expand_choice(host,payload)
                        record(host,'replay_choice_resolution',dict(tool_use_id=use['toolUseId'],
                            selected_result=selection,expanded_plan=payload,scientific_execution_started=False))
                    if payload!=use['input']:
                        record(host,'plan_choice_resolution',dict(tool_use_id=use['toolUseId'],
                            original_input=use['input'],expanded_plan=payload,scientific_execution_started=False))
                    value=dispatch(host,payload,'native-'+use['toolUseId'])
                elif kind=='analysis':
                    payload=use['input']
                    from tools.research.scientific_intent import enabled as question_enabled, compile_question
                    compilation=compile_question(host,payload,tool_use_id=use['toolUseId']) if question_enabled(before['spec']) else None
                    if compilation is not None:
                        payload=compilation.get('request')
                    elif english_native(before['spec']):
                        selection=selected_analysis(host,None)
                        if not selection:raise ValueError('SELECTED_AUTHORIZED_ANALYSIS_METHOD_REQUIRED')
                        method,detail=selection
                        if bound_analysis_enabled(before['spec']):
                            payload=bind_selected_analysis_request(host,payload,tool_use_id=use['toolUseId'])
                        else:
                            schema=selected_analysis_schema(method,detail)
                            validate_selected_analysis_payload(payload,schema,detail)
                    from tools.research.analysis import dispatch as analysis_dispatch
                    value=compilation if compilation is not None and compilation['status']!='ready' else analysis_dispatch(host,payload,'native-'+use['toolUseId'],guard=guard)
                elif kind=='rl':
                    from tools.research.rl import dispatch as rl_dispatch
                    value=rl_dispatch(host,use['input'],'native-'+use['toolUseId'])
                else:
                    key='native-'+use['toolUseId']
                    row,fresh=host.store.reserve(host.run_id,key,digest(use['input']),host.actor,{**zero(),'tool_calls':1})
                    if not fresh and row['receipt']:
                        value=host.store.artifact(json.loads(row['receipt'])['output'])
                    else:
                        if kind=='experience':
                            value=experience(host,use['input'])
                        elif kind=='investigate':
                            value=investigate(host,use['input'])
                        elif kind=='recall':
                            from tools.research.research_context import research_recall
                            value=research_recall(host,use['input'])
                        elif kind=='route':
                            value=select_tool_route(host,use['input'],use['toolUseId'])
                        else:
                            value=read_tool_evidence(host,use['input'])
                        host.store.complete(row,dict(request_id=key,execution_id=row['execution_id'],caller=host.actor,
                            tool_id='research.core_'+kind,tool_version='1.0.0',execution_status='completed',charged=zero()),value)
                original=value
                if (kind not in ('evidence','investigate','experience','recall','route')
                        and not (kind=='analysis' and compilation is not None and compilation['status']!='ready')
                        and state(host)['spec'].get('research_decisions',{}).get('context_limits')):
                    from tools.research.research_context import tool_feedback
                    value=tool_feedback(host,value)
                if kind in ('plan','analysis','rl') and state(host)['spec'].get('research_decisions'):
                    report=scientific_feedback(host,original,before)
                    if report is not None:value=report
                result=original.get('result',original) if isinstance(original,dict) else {}
                if result.get('execution_feedback'):value['execution_feedback']=result['execution_feedback']
                if isinstance(original,dict) and original.get('inference_assessment'):
                    value['inference_assessment']=original['inference_assessment']
                return dict(toolUseId=use['toolUseId'],status='success',content=[dict(text=json.dumps(value,separators=(',',':')))])
            except Exception as exc:
                key='native-'+use['toolUseId']
                reserved=host.store.lookup(host.run_id,key)
                if reserved and not reserved['receipt']:
                    host.store.complete(reserved,dict(request_id=key,execution_id=reserved['execution_id'],caller=host.actor,
                        tool_id='research.core_'+kind,tool_version='1.0.0',execution_status='failed',error=str(exc),charged=zero()),dict(error=str(exc)))
                from tools.research.feedback import facts
                if state(host)['spec'].get('research_decisions'):
                    return dict(toolUseId=use['toolUseId'],status='error',content=[dict(text=json.dumps(error_feedback(host,use,exc,before)))])
                return dict(toolUseId=use['toolUseId'],status='error',content=[dict(text=json.dumps(dict(
                    error=type(exc).__name__,message=str(exc),decision_facts=facts(host))))])
        def paid_tool(use,**kwargs):
            from tools.research.budget import provider_request_scope
            with provider_request_scope(host,boundary.request_phase):
                return run(use,**kwargs)
        return paid_tool
    rl_mode=enabled(state(host)['spec'],'rl')
    formal=bool(state(host)['spec'].get('capabilities'))
    instructions=state(host)['spec']['execution_instructions']
    from tools.research.evidence_policy import english_native
    if english_native(state(host)['spec']):
        instructions+='\nWrite all research decisions and tool arguments directly in English. Scientific records and reports must originate in English.'
    native=[PythonAgentTool(name,dict(name=name,description=description,inputSchema={'json':schema.model_json_schema()}),handler(kind))
        for name,description,schema,kind in [('research_plan',PLAN_TOOL_DESCRIPTION,Plan,'plan'),
            ('experience_retrieve','Search curated procedural guidance, then execute a result entry read_query exactly. A retrieval receipt artifact ID is not an entry_id. Historical guidance never grants scientific evidence or action permission.',ExperienceQuery,'experience'),
            ('evidence_read','Read a named missing fact using exact evidence and JSON pointer. For ordinary Reporter investigation, use compact findings or view=summary on the report; then use fields/range or interpretation_query for needed detail. Full reads remain available for formal SELECT/STOP requirements. Delegate explanation to research_investigate.',EvidenceQuery,'evidence')]]
    if recent_policy:
        from tools.research.contracts import ResearchRecallQuery
        native.append(PythonAgentTool('research_recall',dict(name='research_recall',
            description='Recall saved research by stable step number, or page through history. Details support precise JSON Pointers. Navigation grants no formal SELECT/STOP evidence credit.',
            inputSchema={'json':ResearchRecallQuery.model_json_schema()}),handler('recall')))
    if on_demand:
        from tools.research.contracts import ResearchRouteQuery
        native.append(PythonAgentTool('research_route',dict(name='research_route',description='Select a tool and action; load its Schema on the next request. No scientific execution or evidence credit.',
            inputSchema={'json':ResearchRouteQuery.model_json_schema()}),handler('route')))
    if formal or rl_mode:
        actions=['propose','stop','diagnose','select','confirm'] if formal and state(host)['spec'].get('mode')!='rl_interface' else ['propose','stop']
        if formal and state(host)['spec'].get('mode')!='rl_interface':
            actions += [a for a,c in [('execute','nmpc'),('search','search'),('mechanics','mathematics'),('replay','replay')] if enabled(state(host)['spec'],c)]
        actions=state(host)['spec'].get('allowed_plan_actions',actions)
        schema=plan_schema(actions,decision_required=bool(state(host)['spec'].get('research_decisions')),
            diagnose_candidate_required=state(host)['spec'].get('research_decisions',{}).get('analysis_interface')=='bound_scientific_variables_v2',study=state(host)['spec'])
        native[0].tool_spec={**native[0].tool_spec,'inputSchema':{'json':schema}}
    if state(host)['spec'].get('nominal_source') or state(host)['spec'].get('start_mode')=='family_space':
        native.append(PythonAgentTool('research_analysis',dict(name='research_analysis',description='Candidate-bound mathematics. model_source selects the reduced provider or native MuJoCo methods independently of control. saved_state or execution plus update_id selects a source-bound state; native methods support standardized_initial_pretension from frozen initialization, or a complete native checkpoint or verified measured prefix. Each calculation charged once; task acceptance unmeasured.',inputSchema={'json':AnalysisRequest.model_json_schema()}),handler('analysis')))
    if rl_mode:
        native.append(PythonAgentTool('research_rl',dict(name='research_rl',description='start initializes; resume recovers original stage; continue creates a new stage from exact parent run_id/checkpoint with supported sparse training/reward changes and additional finite allocation. Query, stop, independently evaluate or diagnose an owned frozen candidate RL run',
            inputSchema={'json':RLRequest.model_json_schema()}),handler('rl')))
    if state(host)['spec'].get('rl_evaluation_source'):
        schema=RLRequest.model_json_schema()
        schema['properties']['operation']['enum']=state(host)['spec']['allowed_rl_operations']
        source=state(host)['spec']['rl_evaluation_source']
        schema['properties']['run_id']['enum']=[source['run_id']]
        schema['properties']['checkpoint']['enum']=[source['checkpoint']]
        native[-1].tool_spec={**native[-1].tool_spec,'inputSchema':{'json':schema}}
    if state(host)['spec'].get('research_decisions') and not state(host)['spec'].get('rl_evaluation_source'):
        native.append(PythonAgentTool('research_investigate',dict(name='research_investigate',
            description='Read-only investigation of saved results: provide a question and result references; exact reads and authorized experience_queries are optional. No candidate is needed to read existing evidence. This does not execute research_plan(diagnose) or candidate-bound research_analysis. Returns compact findings and an interpretation_query; internal reads give no SELECT/STOP credit.',
            inputSchema={'json':InvestigationRequest.model_json_schema()}),handler('investigate')))
    agent=None
    def build_session(session_id=None):
        restored=build_harness(host,transport=boundary,api_key=api_key,instructions=instructions,
            model_class=live_model_class(boundary),tool_executor=SequentialToolExecutor(),research_tools=[t for t in native if t is not native[1]] if state(host)['spec'].get('rl_evaluation_source') else native,
            configuration_path=host.store.root/'framework_configuration.json',session_directory=host.store.root/'framework_sessions',session_id=session_id)
        # Dynamic schemas and removed tools are part of the verified boundary.
        # Recreate that exact registry before snapshot verification, including on
        # process restart. before_model will derive the next legal schema again.
        definitions=None
        if agent is not None:
            from tools.research.session_handoff import schemas
            definitions=schemas(agent)
        else:
            s=state(host)
            for key in ('handoff_preparation','handoff'):
                ref=s['pilot'].get(key)
                saved=host.store.artifact(ref) if ref else {}
                if saved.get('next_session')==(session_id or s['pilot']['framework_session_id']):
                    definitions=saved['tool_schemas'];break
        if definitions is not None:
            registry=restored.tool_registry.registry
            if set(definitions)-set(registry):raise ValueError('SAVED_SESSION_TOOL_IMPLEMENTATION_UNAVAILABLE')
            for name in list(registry):
                if name not in definitions:registry.pop(name)
            for name,spec in definitions.items():registry[name].tool_spec=deepcopy(spec)
        return restored
    agent=build_session()
    rejected_initial=False
    from tools.research.session_handoff import unmatched, recover_feedback, trusted_history, INVOCATION_PROMPT
    try:
        if recover_incomplete:
            from tools.research.session_handoff import recover_confirmed_incomplete
            _,agent=await recover_confirmed_incomplete(host,agent,build_session,host.store.root/'framework_sessions')
        saved=state(host)['pilot'].get('unconsumed_response')
        reporter_saved=bool(saved and (received(host,saved) or {}).get('purpose')=='reporter')
        # An interrupted pre-decision Reporter owns a saved tool-result snapshot,
        # not a completed invocation. Verify its exact Store anchor before using
        # the existing incomplete-history recovery path.
        intra_reporter=False
        if reporter_saved:
            anchors=[host.store.artifact(e['outputs'][0]) for e in host.store.events(host.run_id)
                if e['kind']=='science_delivery_boundary']
            if anchors and anchors[-1]['session_id']==agent._session_manager.session_id:
                intra_reporter=anchors[-1]['sdk_message_identity']==digest(agent.messages)
        if state(host)['pilot'].get('handoff'):
            from tools.research.session_handoff import reconcile
            agent=await reconcile(host,build_session,host.store.root/'framework_sessions',allow_incomplete=not reporter_saved or intra_reporter)
        else:
            rejected_initial=trusted_history(host,agent,allow_incomplete=not reporter_saved or intra_reporter)=='rejected_initial_request'
        await complete_reports(host,boundary.inner,recover_only=True)
        if unmatched(agent.messages):await recover_feedback(host,agent)
        continuation=state(host).get('pending_authorized_continuation')
        if continuation:
            approval=host.store.artifact(continuation)
            prior=host.store.artifact(approval['previous_state'])
            if (not approval.get('user_approval') or prior['research_status']!='stopped'
                    or prior.get('success_gate') or approval['previous_final_disposition']!=prior['final_disposition']):
                raise ValueError('EXPLICIT_NONPASS_STOP_CONTINUATION_REQUIRED')
            guard(host)
            preparation=state(host)['pilot'].get('handoff')
            source=(host.store.artifact(host.store.artifact(preparation)['source_state']) if preparation else {})
            if source.get('pending_authorized_continuation')!=continuation:
                current=decision_packet(host)['research']
                native[0].tool_spec={**native[0].tool_spec,'inputSchema':{'json':plan_schema(current['actions'],
                    decision_required=True,family_version=state(host)['spec'].get('family_space',{}).get('version'),
                    diagnose_candidate_required=state(host)['spec'].get('research_decisions',{}).get('analysis_interface')=='bound_scientific_variables_v2',study=state(host)['spec'])}}
                # Restore the authorized tools removed by the previous closeout.
                for tool in native:
                    if tool is not native[1]:agent.tool_registry.registry[tool.tool_name]=tool
                from tools.research.session_handoff import handoff
                preparation,agent=await handoff(host,agent,build_session,host.store.root/'framework_sessions')
            update(host,pending_authorized_continuation=None)
            record(host,'authorized_continuation_activated',dict(authorization=continuation,
                previous_stop=approval['previous_final_disposition'],handoff=preparation,
                session_id=agent._session_manager.session_id,tools=sorted(agent.tool_registry.registry),next_request_sent=False))
    except BaseException:
        await boundary.aclose()
        raise
    if restore_only:
        record(host,'sdk_restore_verified',dict(session_id=agent._session_manager.session_id,
            sdk_message_identity=digest(agent.messages),unmatched_tool_ids=list(unmatched(agent.messages)),
            next_request_sent=False))
        await boundary.aclose()
        return
    if (state(host)['spec'].get('mode')=='rl_interface' or state(host)['spec'].get('capabilities')) and not state(host).get('live_started_unix'):
        s=state(host);pilot=deepcopy(s['pilot'])
        pilot.update(request_deadline_unix=None,bounded_request_reservation=False)
        update(host,live_started_unix=time.time(),pilot=pilot)
    if state(host)['spec'].get('rl_evaluation_source') or state(host)['spec'].get('mode')=='engineering_investigation':
        agent.tool_registry.registry.pop('retrieve_context',None)
    async def before_model(event):
        s=state(host)
        if max_model_calls is not None and host.store.remaining()['used']['model_calls']>=max_model_calls and not s['pilot'].get('unconsumed_response'):
            if s.get('pending') or pending(host) or unmatched(agent.messages):raise ValueError('REQUEST_LIMIT_REQUIRES_SETTLED_FEEDBACK')
            await agent._session_manager.save_snapshot(agent,is_latest=True)
            raise SupervisorReviewPause('Bounded Provider request limit reached; no further send')
        if s['research_status']=='stopped':
            event.cancel='Accepted native STOP; no additional request'
            return
        if s['pilot'].get('unconsumed_response'):
            saved=s['pilot']['unconsumed_response']
            if (received(host,saved) or {}).get('purpose')=='reporter':
                raise ValueError('REPORTER_RESPONSE_MUST_BE_ARCHIVED_BEFORE_MAIN_DECISION')
            ev=next(e for e in host.store.events(host.run_id) if e['kind']=='r3_request' and e['request_id']==saved)
            original=host.store.artifact(host.store.artifact(ev['outputs'][0])['request'])
            agent.system_prompt=next(m['content'] for m in original['messages'] if m['role']=='system')
            definitions={t['function']['name']:t['function'] for t in original.get('tools',[])}
            registry=agent.tool_registry.registry
            if set(definitions)-set(registry):raise ValueError('SAVED_REQUEST_TOOL_IMPLEMENTATION_UNAVAILABLE')
            for name in list(registry):
                if name not in definitions:registry.pop(name)
            for name,definition in definitions.items():
                parameters=deepcopy(definition['parameters'])
                if name=='research_plan' and parameters.get('$defs',{}).get('EvidenceRef',{}).get('type')=='string':
                    from tools.research.object_choices import reference_choices
                    offered=parameters['$defs']['EvidenceRef']['enum']
                    parameters['x-research-reference-choices']={k:v for k,v in reference_choices(host).items() if k in offered}
                registry[name].tool_spec=dict(name=name,description=definition.get('description',''),
                    inputSchema={'json':parameters})
            return
        remaining=host.store.remaining()['remaining']
        if remaining['model_calls']<1 or remaining['tool_calls']<2:
            engineering_closeout(host,'No remaining provider/public-operation capacity for model closeout')
            event.cancel='Engineering count-budget closure; no fabricated model STOP'
            return
        guard(host)
        if rl_mode:
            await wait_training(host)
        s=state(host)
        if s['research_status']=='stopped':
            event.cancel='Study stopped while waiting'
            return
        guard(host)
        if s['spec'].get('research_decisions'):
            await deliver_science_before_decision(host,agent,boundary.inner,max_model_calls=max_model_calls)
        if on_demand:
            for tool in native:agent.tool_registry.registry[tool.tool_name]=tool
            agent.tool_registry.registry.pop('retrieve_context',None)
        for name,contract in (('evidence_read',EvidenceQuery),('research_investigate',InvestigationRequest)):
            tool=agent.tool_registry.registry.get(name)
            if tool:tool.tool_spec={**tool.tool_spec,'inputSchema':{'json':evidence_query_schema(s['spec']) if name=='evidence_read' else contract.model_json_schema()}}
            from tools.research.config import bounded_evidence_enabled
            if tool and name=='evidence_read' and bounded_evidence_enabled(s['spec']):
                tool.tool_spec['description']='Read exact named facts via fields/range/JSON pointers. Large raw reads return bounded facts/navigation. For formal SELECT read the complete acceptance_certificate of each independently evaluated result; actual delivery and original admission are required. STOP uses the complete fresh result-reference index.'
        current=decision_packet(host)
        from tools.research.experience import knowledge_enabled
        if not knowledge_enabled(s['spec']):agent.tool_registry.registry.pop('experience_retrieve',None)
        from tools.research.evidence_policy import english_native
        if 'research' in current:
            from tools.research.scientific_intent import enabled as question_enabled
            native[0].tool_spec={**native[0].tool_spec,'description':DECISION_PLAN_DESCRIPTION if english_native(s['spec']) else PLAN_TOOL_DESCRIPTION,'inputSchema':{'json':plan_schema(current['research']['actions'],decision_required=bool(s['spec'].get('research_decisions')),
                family_version=s['spec']['family_space']['version'] if s['spec'].get('start_mode')=='family_space' else None,
                diagnose_candidate_required=s['spec'].get('research_decisions',{}).get('analysis_interface')=='bound_scientific_variables_v2',study=s['spec'])}}
            if question_enabled(s['spec']):
                native[0].tool_spec['description']=QUESTION_PLAN_DESCRIPTION
                from tools.research.scientific_intent import explicit_actions
                if explicit_actions(s['spec']):
                    native[0].tool_spec['description']='Record hypothesis and owned candidate in diagnose; optionally choose next_research_action to load its scientific interface. Selection executes nothing. Main chooses variables, effort and subsequent actions. Original Plan and independent acceptance gates apply.'
        if english_native(s['spec']):
            tool=next((t for t in native if t.tool_name=='research_analysis'),None)
            from tools.research.scientific_intent import enabled as question_enabled, completed_question_plan, question_schema
            question_mode=question_enabled(s['spec'])
            selected=selected_analysis(host,current['research']) if not question_mode and tool and enabled(s['spec'],'analysis') else None
            if question_mode and tool and completed_question_plan(host) and enabled(s['spec'],'analysis'):
                tool.tool_spec={**tool.tool_spec,'description':'Submit a scientific question for the candidate and hypothesis in the completed diagnose Plan. Deterministic compilation preserves original execution admission and charges; unsupported semantics are never replaced.',
                    'inputSchema':{'json':question_schema(s['spec'],host.store.artifact(completed_question_plan(host)['candidate']))}}
                agent.tool_registry.registry['research_analysis']=tool
            elif selected:
                method,detail=selected
                tool.tool_spec={**tool.tool_spec,'description':'Execute the selected registered mathematical method. Full backend Study and source admission applies; selection alone performs no calculation.',
                    'inputSchema':{'json':selected_analysis_schema(method,detail,bound=bound_analysis_enabled(s['spec']))}}
                agent.tool_registry.registry['research_analysis']=tool
            else:agent.tool_registry.registry.pop('research_analysis',None)
        if not enabled(s['spec'],'analysis') or s['spec']['budgets']['mathematical_evaluations']<=s.get('mathematical_evaluations',0):
            agent.tool_registry.registry.pop('research_analysis',None)
        # Provider readiness is checked per selected model by analysis.dispatch;
        # unavailable MATLAB must not hide authorized native MuJoCo mathematics.
        if english_native(s['spec']):
            from tools.research.research_context import research_decision_brief_v3
            delivered=dict(study_id=host.run_id,research=research_decision_brief_v3(current['research'],
                complete_interpretations=s['spec'].get('research_decisions',{}).get('role_policy',{}).get('version')=='research_roles_v2'))
        else:delivered=current
        if not on_demand:record(host,'model_decision_packet',delivered)
        agent.system_prompt=instructions
        boundary.research_packet=deepcopy(delivered)
        if (current.get('research',{}).get('budget',{}).get('closeout',{}).get('next_request_will_protect',protected(host)) or
                bounded_evidence_enabled(s['spec']) and protected(host)):
            permitted=closeout_operations(host)
            schema=plan_schema(permitted['research_plan'],decision_required=bool(s['spec'].get('research_decisions')))
            native[0].tool_spec={**native[0].tool_spec,'inputSchema':{'json':schema}}
            agent.tool_registry.registry.pop('experience_retrieve',None)
            agent.tool_registry.registry.pop('research_analysis',None)
            if rl_mode:
                rl_tool=next(t for t in native if t.tool_name=='research_rl')
                schema=deepcopy(rl_tool.tool_spec['inputSchema']['json'])
                schema['properties']['operation']['enum']=permitted['research_rl']
                schema['properties']['run_id']['enum']=list(s.get('rl_runs',{}))
                rl_tool.tool_spec={**rl_tool.tool_spec,'inputSchema':{'json':schema}}
            agent.tool_registry.registry.pop('research_investigate',None)
            if on_demand:agent.tool_registry.registry.pop('research_recall',None)
            schema=evidence_query_schema(s['spec'])
            schema['$defs']['EvidenceRef']['properties']['artifact_id']['enum']=[r['artifact_id'] for r in readable_results(s,host)]
            native[2].tool_spec={**native[2].tool_spec,'inputSchema':{'json':schema}}
            retrieval=agent.tool_registry.registry.get('retrieve_context')
            if retrieval:
                from strands.tools.tools import normalize_tool_spec
                spec=deepcopy(normalize_tool_spec(retrieval.tool_spec))
                spec['inputSchema']['json']['properties']['reference']['enum']=feedback_context_references()
                retrieval.tool_spec=spec
            boundary.research_packet['protected_closeout_rule']='PROTECTED CLOSEOUT: status/stop existing workers, pinned published-policy evaluation, explicit evidence reads, selected passing solution confirmations and truthful STOP. No start/resume/solve/exploration.'
        if on_demand:
            registry=agent.tool_registry.registry;directory=tool_directory(host,registry)
            pilot=deepcopy(state(host)['pilot']);pilot['tool_directory']=directory;update(host,pilot=pilot)
            loaded=load_selected_tool_schema(host,registry,directory)
            boundary.research_packet['research'].update(tool_directory=directory,loaded_tool=loaded,
                tool_loading='Submit an already loaded tool directly. Use research_route only to switch tool/action; direct reads preserve the loaded Plan. Selection alone executes nothing.')
            handoff=boundary.research_packet['research'].get('analysis_handoff')
            if handoff:
                analysis_tool=registry.get('research_analysis')
                schema=analysis_tool.tool_spec['inputSchema']['json'] if analysis_tool else {}
                handoff['remaining_scientific_fields']=schema.get('required',[])
                handoff['conditional_scientific_inputs']=([dict(when=dict(operating_point='saved_state'),
                    exactly_one_of=[['saved_state'],['execution','update_id']],
                    rule='Use an exact candidate-bound state source. Other operating points must omit these sources; a legal point enum does not imply a saved source exists.')]
                    if 'saved_state' in schema.get('properties',{}).get('operating_point',{}).get('enum',[]) else [])
            if tool_schema_policy(s['spec']) in (dict(version='on_demand_tools_v2'),dict(version='on_demand_tools_v3'),dict(version='research_information_flow_v1')) and s.get('family_space_reference'):
                boundary.research_packet['research']['generation_contract']=dict(
                    family_space_identity=s['spec']['family_space_identity'],
                    version='serial_family_generation_v2' if s['spec']['family_space']['version']=='serial_family_space_v2' else 'serial_family_generation_v1',
                    domain_query=dict(reference=s['family_space_reference'],view='full',pointer=''),
                    generation_inputs=current['family_space']['generation_inputs'],
                    scope='Frozen generation inputs and domain query; choose your own legal parameters. No candidate or Plan is submitted.')
            if tool_schema_policy(s['spec']) in (dict(version='on_demand_tools_v3'),dict(version='research_information_flow_v1')):
                from tools.research.research_context import compact_tool_delivery
                compact_tool_delivery(boundary.research_packet['research'])
            from tools.research.config import information_flow_v1
            if information_flow_v1(s['spec']):
                from tools.research.research_context import information_flow_brief
                boundary.research_packet['research']=information_flow_brief(current['research'],boundary.research_packet['research'])
            if enabled(s['spec'],'physical_replay'):
                from tools.research.object_choices import replay_choices,choice_schema
                options=replay_choices(host,current['research'].get('scientific_results') or {})
                boundary.research_packet['saved_replay_choices']=dict(options=options,
                    scope='Bounded saved-result options. Main chooses; no physical execution or acceptance is implied. Other saved results remain queryable from Store.')
                plan=registry.get('research_plan')
                if options and plan and plan.tool_spec['inputSchema']['json']['properties']['action'].get('enum')==['physical_replay']:
                    plan.tool_spec={**plan.tool_spec,'inputSchema':{'json':choice_schema(plan.tool_spec['inputSchema']['json'],options)}}
            plan=registry.get('research_plan')
            if plan:
                from tools.research.object_choices import reference_choices,reference_schema
                choices=reference_choices(host);schema=plan.tool_spec['inputSchema']['json']
                action=schema['properties']['action'].get('enum',[])
                if len(action)==1:
                    plan.tool_spec={**plan.tool_spec,'inputSchema':{'json':reference_schema(schema,choices,action[0])}}
                    from tools.research.research_context import ordered_candidates
                    wanted=[*ordered_candidates(host,s)[-3:],
                        *[r['candidate'] for r in boundary.research_packet.get('saved_replay_choices',{}).get('options',[])],
                        *s.get('results',[]),*s.get('physical_replays',[]),*s.get('rl_evaluations',[])]
                    boundary.research_packet['saved_object_choices']=[dict(choice=k,reference=v,
                        **(host.store.artifact(v,paths=('acceptance','candidate')) if k.startswith('evaluation_') else {}))
                        for k,v in choices.items() if v in wanted]
                    boundary.research_packet['object_choice_rule']='Use short choices for Plan references. Candidate-bearing actions bind decision.selected_candidate automatically. SELECT/CONFIRM/replay bind supporting evidence to the selected result. Independent acceptance, public evidence reads and original budgets are still required.'
            if operator_request:
                boundary.research_packet['operator_request']=dict(reference=operator_request,
                    instruction=host.store.artifact(operator_request))
            # Record the actual L0 after dynamic tool selection; no extra model call.
            record(host,'model_decision_packet',boundary.research_packet)
        token_policy=s['spec'].get('research_decisions',{}).get('handoff_policy')
        paired=bool(agent.messages and agent.messages[-1]['role']=='user'
            and any('toolResult' in b for b in agent.messages[-1]['content']))
        completed=bool((token_policy or recent_policy) and len(agent.messages)>=2 and agent.messages[-1]['role']=='user'
            and agent.messages[-1]['content']==[dict(text=INVOCATION_PROMPT)] and agent.messages[-2]['role']=='assistant')
        if session_handoff and (paired or completed):
            from tools.research.session_handoff import rotation_ready
            if recent_policy and not rotation_ready(host,agent.messages[:-1] if completed else agent.messages):return
            wire=agent.model.format_request(agent.messages,agent.tool_registry.get_all_tool_specs(),agent.system_prompt)
            content=httpx.Request('POST',s['pilot']['provider']['base_url']+'/chat/completions',json=wire).content
            size=len(content)
            provider=s['pilot']['provider'];context=provider['context_guard']
            token_due=False
            if token_policy:
                from tools.research.provider_context import handoff_input_estimate
                estimate=handoff_input_estimate(content,provider)
                token_due=estimate['input_estimate']>=token_policy['input_tokens']
            if completed and (token_due or recent_policy):
                # The just-added invocation prompt has not been sent. The preceding
                # assistant turn is the durable completed boundary.
                with host.store.connect(True) as db:
                    from tools.research.session_handoff import safe_boundary
                    safe_boundary(host,s,db,agent.messages[:-1])
                agent.messages.pop()
                raise CompletedBoundaryHandoff('Verified completed boundary; next model send has not started')
            if not paired or s['pilot'].get('session_handoff_boundary')!='request_feedback':return
            review=(pause_exploration_remaining is not None and not protected(host)
                and current['research']['budget']['provider_budget']['science_capable_main_requests']<=pause_exploration_remaining)
            if review:
                from tools.research.session_handoff import request_feedback_boundary
                await request_feedback_boundary(host,agent)
                raise SupervisorReviewPause('Settled boundary before next request; supervisor budget review required')
            if handoff_before_next_request or recent_policy or token_due or (handoff_request_bytes is not None and size>=handoff_request_bytes) or (not token_policy and size+(provider.get('output_context_reserve_tokens') or provider.get('max_tokens') or 0)+context['framing_headroom_tokens']>context['context_limit_tokens']):
                from tools.research.session_handoff import request_feedback_boundary
                await request_feedback_boundary(host,agent)
                raise RequestBoundaryHandoff('Verified request-feedback boundary; next model send has not started')
    def check_before_tool(event):
        if state(host)['spec'].get('rl_evaluation_source') and event.tool_use['name'] not in ('research_plan','research_rl','evidence_read',*(['research_route'] if on_demand else [])):
            event.cancel_tool='Only declared follow-up evaluation, evidence reads and STOP are permitted.'
        record(host,'model_original_tool_request',dict(tool_use=event.tool_use))
        if protected(host) and event.tool_use['name'] not in ('research_plan','research_rl','evidence_read','retrieve_context',*(['research_route'] if on_demand else [])):
            event.cancel_tool='Protected closeout permits only existing work, evidence and STOP.'
        try:
            admit_closeout(host,event.tool_use['name'],event.tool_use['input'])
        except ValueError as exc:
            event.cancel_tool=str(exc)
        if state(host)['research_status']=='stopped':
            event.cancel_tool='Accepted STOP seals further workflow work.'
        if protected(host) and event.tool_use['name']=='retrieve_context' and event.tool_use['input'].get('reference') not in feedback_context_references():
            event.cancel_tool='Protected closeout permits existing execution feedback only.'
    def before_tool(event):
        from tools.research.budget import provider_request_scope
        with provider_request_scope(host,boundary.request_phase):
            check_before_tool(event)
    def after_tool(event):
        saved=dict(tool_use=event.tool_use,result=event.result)
        if event.tool_use['name']=='evidence_read' and event.tool_use['input'].get('view') in ('working_set','mathematical_capabilities','capabilities'):
            saved['source_state_identity']=digest(state(host))
        record(host,'model_original_tool_feedback',saved)
        key='native-'+event.tool_use['toolUseId']
        if host.store.lookup(host.run_id,key) is None:
            row,_=host.store.reserve(host.run_id,key,digest(event.tool_use),host.actor,{**zero(),'tool_calls':1})
            host.store.complete(row,dict(request_id=key,execution_id=row['execution_id'],caller=host.actor,
                tool_id=event.tool_use['name'],tool_version='1.0.0',execution_status='completed',charged=zero()),event.result)
    agent.hooks.add_callback(BeforeModelCallEvent,before_model)
    agent.hooks.add_callback(BeforeToolCallEvent,before_tool)
    agent.hooks.add_callback(AfterToolCallEvent,after_tool)
    try:
        completed_invocations=0
        while state(host)['research_status']!='stopped':
            if max_model_calls is not None and host.store.remaining()['used']['model_calls']>=max_model_calls:
                record(host,'supervisor_pause',dict(boundary='provider_request_limit',budgets_preserved=True,next_request_sent=False))
                break
            if host.store.remaining()['remaining']['model_calls']<1:
                engineering_closeout(host,'Provider request count exhausted without model STOP/selection')
                break
            try:
                # Public SDK continuation resumes the durable unsent prompt or
                # paired feedback. Adding another prompt would change a saved
                # request's hash and prevent exact response replay.
                resume=bool(rejected_initial or state(host)['pilot'].get('unconsumed_response') or (agent.messages
                    and agent.messages[-1]['role']=='user'
                    and any('toolResult' in b for b in agent.messages[-1]['content'])))
                rejected_initial=False
                result=await agent.invoke_async(None if resume else INVOCATION_PROMPT)
            except Exception as exc:
                cause=exc;seen=set()
                while cause is not None and id(cause) not in seen and not isinstance(cause,RequestBoundaryHandoff):
                    seen.add(id(cause));cause=cause.__cause__
                if not isinstance(cause,RequestBoundaryHandoff):raise
                if isinstance(cause,SupervisorReviewPause):
                    record(host,'supervisor_pause',dict(boundary='request_feedback',session_id=agent._session_manager.session_id,
                        sdk_message_identity=digest(agent.messages),budgets_preserved=True,next_request_sent=False,
                        budget=decision_packet(host)['research']['budget']))
                    break
                record(host,'sdk_invocation_suspended_for_handoff',dict(session_id=agent._session_manager.session_id,
                    sdk_message_identity=digest(agent.messages),invocation_completed=False,
                    boundary_kind='completed_invocation' if isinstance(cause,CompletedBoundaryHandoff) else 'request_feedback',
                    next_request_sent=False))
                from tools.research.session_handoff import handoff
                _,agent=await handoff(host,agent,build_session,host.store.root/'framework_sessions',boundary='completed_invocation' if isinstance(cause,CompletedBoundaryHandoff) else 'request_feedback')
                handoff_before_next_request=False
                agent.hooks.add_callback(BeforeModelCallEvent,before_model)
                agent.hooks.add_callback(BeforeToolCallEvent,before_tool)
                agent.hooks.add_callback(AfterToolCallEvent,after_tool)
                continue
            record(host,'model_original_turn',dict(result=str(result),session_id=agent._session_manager.session_id,
                sdk_message_identity=digest(agent.messages)))
            if state(host)['pending'] or pending(host):
                raise ValueError('PENDING_OUTCOME_REQUIRES_LOCAL_RECOVERY')
            if state(host)['spec'].get('research_decisions'):
                await complete_reports(host,boundary.inner,max_model_calls=max_model_calls)
            completed_invocations+=1
            if (pause_after_completed_invocations is not None and completed_invocations>=pause_after_completed_invocations
                    and state(host)['research_status']!='stopped' and not state(host).get('success_gate')):
                await pause_completed_invocation(host,agent,completed_invocations)
                break
            if session_handoff and not state(host)['spec'].get('research_decisions',{}).get('handoff_policy') and state(host)['research_status']!='stopped' and not state(host).get('success_gate'):
                from tools.research.session_handoff import handoff, reconcile
                previous=agent
                try:_,agent=await handoff(host,agent,build_session,host.store.root/'framework_sessions')
                except Exception as exc:
                    s=state(host)
                    if s['pending'] or pending(host) or s['pilot'].get('unconsumed_response'):raise
                    if s['pilot']['framework_session_id']!=previous._session_manager.session_id:
                        agent=await reconcile(host,build_session,host.store.root/'framework_sessions')
                    else:
                        agent=build_session(previous._session_manager.session_id)
                        if agent.messages!=previous.messages:raise ValueError('OLD_SDK_HISTORY_NOT_DURABLE') from exc
                        record(host,'session_handoff_not_committed',dict(reason=str(exc),old_session_retained=True))
                agent.hooks.add_callback(BeforeModelCallEvent,before_model)
                agent.hooks.add_callback(BeforeToolCallEvent,before_tool)
                agent.hooks.add_callback(AfterToolCallEvent,after_tool)
    finally:
        await boundary.aclose()


def decision_packet(host):
    from tools.research.core import packet
    from tools.research.research_context import ordered_candidates
    if state(host)['spec'].get('research_decisions'):
        from tools.research.research_context import agent_decision_brief,controller_capabilities
        from extensions.tendon_family.family_space import decision_summary
        from tools.research_tasks import task_adapter
        s=state(host);spec=s['spec']
        research=agent_decision_brief(host)
        controller=controller_capabilities(host)
        controller.pop('parameter_schema')
        controller['parameter_schema_query']=dict(reference=research['evidence_access']['reference'],
            view='working_set',pointer='/controller_capabilities/parameter_schema')
        candidates=ordered_candidates(host,s)[-spec.get('research_decisions',{}).get('context_limits',{}).get('candidates',3):]
        bindings=[]
        for ref in candidates:
            identity=host.store.artifact(ref)['profile_identity']
            bindings.append(dict(candidate=ref,profile_identity=identity,
                executable_under_current_profile=identity==s['profile']['identity']))
        return dict(research=research,implementation=s['freeze'],study_id=host.run_id,
            evaluation_profile={k:s['profile'][k] for k in ('identity','version')},
            implementation_migration=s.get('core_repairs',[])[-1] if s.get('core_repairs') else None,
            controller_capabilities=controller,
            candidates=candidates,candidate_profile_bindings=bindings,
            family_space=decision_summary(spec['family_space'],s['family_space_reference'],
                dict(actions=spec['allowed_plan_actions'],capabilities=spec['capabilities'])) if spec.get('start_mode')=='family_space' else None,
            source_relative_design=dict(reference_parameters=spec['reference_parameters'],allowed_parameters=spec['allowed_parameters'],
                length_constraint=spec.get('length_constraint')) if spec.get('start_mode')!='family_space' else None,
            analysis_protocol=spec['analysis_protocol'],
            guidance='Tool results acknowledge execution and saved references; use latest_reports L1 for scientific decisions. Signed score direction, comparison scope and optimality come from structured facts. Use exact evidence refs and a typed decision in every research_plan. evidence_read and research_investigate permit drill-down. Reporter interpretations are hypotheses, never authoritative facts or action choices. Choose the next research method freely. New designs need explicit control adaptation. Do not infer global feasibility/infeasibility. Stop at the first complete task pass; for a multi-condition Study this means every frozen condition on the identical structure. Publicly read each evaluation and select the complete result set. Retrieve the exact stop_result_index before STOP; cite every new result.')
    result=packet(host)
    spec=result.pop('specification')
    result['configuration_identity']=spec['resolved_identity']
    result['study']={k:spec[k] for k in ('study_id','capabilities','allowed_parameters','reference_parameters','analysis_protocol','scoring_window_s','budgets','rl_limits','confirmation','budget_semantics')}
    if 'topology_authorization' in spec:
        result['study']['topology_authorization']=spec['topology_authorization']
    if spec.get('fidelity_policy'):
        result['study'].update(fidelity_policy=spec['fidelity_policy'],final_evaluation_identity=spec['final_evaluation_identity'],
            family_search=spec.get('family_search'),search_contract='family_mixed_search_v1',
            search_usage='research_plan(action=search): select groups, counts, objective, screening_fidelity and finite caps; no fixed robot. Mathematical evidence cannot satisfy final task acceptance.')
    if spec.get('start_mode')=='family_space':
        from extensions.tendon_family.family_space import decision_summary
        result['study'].update(start_mode='family_space',family_space=decision_summary(
            spec['family_space'],state(host)['family_space_reference'],
            dict(actions=spec['allowed_plan_actions'],capabilities=spec['capabilities'])),
            family_space_identity=spec['family_space_identity'],candidate_initialization=spec['candidate_initialization'],
            canonical_task_identity=spec['canonical_task_identity'])
    result['available_actions']=spec['allowed_plan_actions']
    s=state(host)
    result['implementation']=dict(commit=s['freeze'],repairs=s.get('core_repairs',[]),
        counters_preserved=True,prelaunch_failure_rule='A recorded failure before durable launch intent proves no worker started; its charged attempt remains spent. An explicit implementation repair is not a retry of already-executed unchanged science.')
    return result
