"""Deterministic scientific choices -> existing registered AnalysisRequest.

No optimizer, state machine, source ledger or execution admission lives here.
"""
from tools.research.budget import mathematical_remaining, mathematics_fits
from copy import deepcopy

from tools.platform_store import plain
from tools.research.contracts import ScientificQuestion, ScientificQuestionV2, ScientificQuestionV3, ScientificQuestionV4, ScientificControlV4, MechanismQuestionV2, ScientificControlEffort, LocalControlSearchSettings
from tools.research.state import state, protected
from tools.research.nonlinear_capability import T1, T2

INTERFACE = 'scientific_question_v1'
INTERFACES = (INTERFACE,'scientific_question_v2','scientific_question_v3','scientific_question_v4')
DIRECT = 'mujoco_direct_control_v1'


def control_method_choices(view):
    """Project candidate-bound admission facts; no second method registry."""
    choices=[]
    for key,row in view['methods'].items():
        if key not in (T1,DIRECT):continue
        selectable=bool(row['formal_execution_authorized'] and row['kernel_supported'] and
            row['planning_status'] not in ('unauthorized','unsupported','insufficient_budget','blocked'))
        guide=row.get('control_input_guidance') or {};sources=guide.get('recorded_sources',[])
        readiness=(row['planning_status'] if not selectable else 'requires_control_initialization' if not sources else
            'requires_source_choice' if len(sources)>1 else 'ready_for_scientific_request')
        missing=(row['missing'] if not selectable else
            (['legal_control_source'] if not sources else ['source_selection.control_source'] if len(sources)>1 else [])+
            ['control_scope','control_search_effort'])
        choices.append(dict(method=key,operation=row['operation'],planning_status=row['planning_status'],
            selectable=selectable,scientific_purpose=row['scientific_purpose'],readiness=readiness,
            legal_control_sources=sources,preparation=guide.get('baseline_initialization') if selectable and not sources else None,
            missing=missing,detail_query=row['detail_query'],request_admission='not_checked'))
    return choices


def conic_entry():
    """The existing V4 Conic entry, distinct from Native control search."""
    return dict(tool='research_plan',action='diagnose',next_research_action='mechanism_research',
        then=dict(tool='research_analysis',input=dict(version='scientific_question_v4',domain='structure',
            structure=dict(operation='inspect',effect_semantics='reoptimized_task_capability',target='optimal_task_violation',parameter_paths=[]))),
        scope='Sampled affine Conic minimax at frozen initial pretension; no linearization around a selected Native schedule. After a numerically valid result, initialize_control(method=capability_sequence, response_evidence=result) imports its complete bound sequence; Native evaluation and independent Replay remain separate.')


def explicit_actions(spec):
    return spec.get('research_decisions',{}).get('analysis_interface') in ('scientific_question_v3','scientific_question_v4')


def mechanism_interface(spec):
    # B's historical V2 is disambiguated by its explicit frozen method grant.
    return spec.get('research_decisions',{}).get('analysis_interface')=='scientific_question_v4' or (
        spec.get('research_decisions',{}).get('analysis_interface')=='scientific_question_v2' and
        bool(spec.get('mathematical_methods',{}).get('mechanism_structure_v1')))


def scientific_actions(spec):
    """Small action projection of existing interfaces, never an execution registry."""
    actions=[dict(scientific_goal='structure_control_codesign',tool='research_plan',action='search',
        interface=spec.get('research_decisions',{}).get('structure_search_interface'),available='search' in spec.get('allowed_plan_actions',[]) and
            'search' in spec.get('capabilities',[]) and spec.get('research_decisions',{}).get('structure_search_interface')=='scientific_structure_search_v1',
        scope='Generate new structures and reoptimize control per structure; Main chooses variables and effort.'),
        dict(scientific_goal='single_parameter_effect',tool='research_analysis',
            interface=spec['research_decisions']['analysis_interface'],available='analysis' in spec.get('capabilities',[]),
            scope='One registered continuous physical parameter: fixed-input comparison, or T2 aggregation of comparable saved T1 results. No new T1 or structures.'),
        dict(scientific_goal='control_feasibility',tool='research_analysis',
            interface=spec['research_decisions']['analysis_interface'],available='analysis' in spec.get('capabilities',[]),
            scope='Candidate-registered Native control optimization on the current structure: Reach/Hold T1 or applicable Direct. Conic uses mechanism_research / inspect / reoptimized_task_capability / optimal_task_violation, not this Native control interface. Independent replay establishes acceptance.')]
    if mechanism_interface(spec):
        actions.append(dict(scientific_goal='mechanism_research',domain='structure',tool='research_analysis',
            interface=spec['research_decisions']['analysis_interface'],available='analysis' in spec.get('capabilities',[]),
            scope='inspect / differentiate / optimize / compare instantaneous mechanisms and explicit M1/M2 evidence. Main owns target, direction and adoption.'))
    if spec['research_decisions']['analysis_interface']=='scientific_question_v4':
        actions=[row for row in actions if row['scientific_goal']!='single_parameter_effect']
    for row in actions:
        if spec.get('canonical_task',{}).get('physical_problem') and row['scientific_goal']!='mechanism_research':
            row.update(available=False,scope='This frozen passive assembly has no active control; use mechanism_research. Independent passive Replay is available through research_plan only for a registered dynamic task.')
        elif spec.get('canonical_task',{}).get('physical_problem'):
            row['scope']='Inspect, differentiate, optimize or compare frozen constrained geometry/equilibrium and load responses; Main owns structure adoption.'
        row.setdefault('domain','structure_control' if row['scientific_goal']=='structure_control_codesign' else
            'control' if row['scientific_goal']=='control_feasibility' else 'structure')
    return actions


def action_entry(spec, choice):
    if choice=='single_parameter_effect' and spec['research_decisions']['analysis_interface']=='scientific_question_v4':
        choice='mechanism_research'
    return next((r for r in scientific_actions(spec) if r['scientific_goal']==choice),None)


def parameter_catalog(spec, candidate, group=None, method=None):
    """Project actual authoritative FamilySpace rows, including original admission."""
    from tools.research.optimal_capability import family_analysis_parameters
    if not spec.get('family_space') or not candidate.get('generation_version'):return []
    v4=spec.get('research_decisions',{}).get('analysis_interface')=='scientific_question_v4'
    if v4:
        from tools.research.structure_research import parameters
        actual=parameters(spec,candidate)
    else:actual=family_analysis_parameters(spec,candidate)
    rows=[]
    for row in actual:
        path=row['parameter_id']
        kind=('routing' if row['category']=='routing' else 'lengths' if path.endswith('.length_m') else
            'sections' if '.sections.' in path or path.endswith('.section_angle_rad') else
            'materials' if path.startswith('segments.') and (path.endswith('.young_pa') or '.physical_parameters.' in path) else None)
        if v4:kind=row['category']
        if not kind or group and kind!=group:continue
        legal=row['continuous_perturbation'] and row['effective_in_current_execution'] and '*' not in path
        if v4:legal=legal and row['mechanism_differentiation']['supported']
        methods=row['applicable_mathematical_methods']
        rows.append(dict(parameter_group=kind,parameter_id=path,physical_meaning=path.rsplit('.',1)[-1].replace('_',' '),
            physical_component=row['physical_component'],unit=row['unit'],current_value=row['current_value'],
            effective=row['effective_in_current_execution'],continuous=row['continuous_perturbation'],
            selectable=bool(legal and (method in methods if method else methods)),applicable_methods=methods,
            validity=row['analysis_reason'],study_authorized=row['study_authorized'],
            execution_semantics=row['execution_semantics']))
    return rows


def enabled(spec):
    return spec.get('research_decisions',{}).get('analysis_interface') in INTERFACES


def question_contract(spec):
    if mechanism_interface(spec) and spec['research_decisions']['analysis_interface']=='scientific_question_v2':return MechanismQuestionV2
    return {'scientific_question_v4':ScientificQuestionV4,'scientific_question_v2':ScientificQuestionV2,'scientific_question_v3':ScientificQuestionV3}.get(spec.get('research_decisions',{}).get('analysis_interface'),ScientificQuestion)


def question_schema(spec, candidate=None, action=None, *, control_methods=None):
    schema=question_contract(spec).model_json_schema()
    if question_contract(spec) is ScientificQuestionV4:
        # Reuse the two existing scientific payloads, with a single outer version.
        for name in ('ScientificStructureV4','ScientificControlV4'):
            schema['$defs'][name]['properties'].pop('version',None)
        control=schema['$defs']['ScientificControlV4']['properties']
        for name in ('parameter_paths','search_strategy','requested_budget','parameter_group','parameter_id',
                'fixed_input','tensions_n','response_horizon_s'):control.pop(name,None)
        control['question_type']={'type':'string','const':'control_feasibility'}
        control['effect_semantics']={'type':'string','const':'reoptimized_task_capability'}
        schema['$defs']['ScientificControlV4']['required']=[
            k for k in schema['$defs']['ScientificControlV4']['required'] if k!='question_type']
        if control_methods is not None:
            legal=[r['method'] for r in control_methods if r['selectable']]
            control['numerical_method']={'enum':[None,*legal],
                'description':'Native method identity only; Reach/Hold preserves its default finite T1 semantics. Conic/SOCP uses the separate structure inspect / reoptimized_task_capability / optimal_task_violation entry in analysis_handoff.conic_entry.'}
        sources=schema['$defs']['ScientificSources']['properties']
        for name in ('comparison_candidates','t1_results'):sources.pop(name,None)
        passive=bool((candidate or {}).get('configuration',{}).get('task',{}).get('physical_problem') or spec.get('canonical_task',{}).get('physical_problem'))
        if action in ('mechanism_research','single_parameter_effect','control_feasibility') or passive:
            domain='control' if action=='control_feasibility' and not passive else 'structure'
            schema['properties']['domain']={'type':'string','const':domain}
            schema['properties'].pop('structure' if domain=='control' else 'control')
            schema['properties'][domain].pop('default',None)
            schema['properties'][domain]['anyOf']=[b for b in schema['properties'][domain]['anyOf'] if b.get('type')!='null']
            schema['required'].append(domain)
        target=schema['$defs']['PhysicalMechanismTarget']['properties']['goal']
        target.pop('default',None)
        target['description']='Main explicitly chooses increase or decrease for differentiation or optimization.'
        schema['$defs']['ScientificStructureV4']['allOf']=[dict(
            **{'if':dict(properties=dict(operation=dict(enum=['differentiate','optimize'])),required=['operation'])},
            then=dict(properties=dict(target=dict(required=['goal']))))]
        schema['description']='Structure research uses structure operations inspect/differentiate/optimize/compare; control research uses control feasibility and effort. Joint structure-control search uses the existing research_plan(search) interface. Main owns all scientific choices.'
        if passive:
            problem=((candidate or {}).get('configuration',{}).get('task',{}).get('physical_problem') or spec['canonical_task']['physical_problem'])
            props=schema['$defs']['ScientificStructureV4']['properties']
            for name in ('source_selection','control_scope','search_strategy','tensions_n','saved_state','execution','update_id','response_horizon_s','parameter_group'):
                props.pop(name,None)
            props['physical_problem']={'type':'string','const':problem['mode']}
            props['control_treatment']={'type':'string','const':'no_active_control'}
            props['operating_point']={'type':'string','enum':['re_equilibrated','frozen_task_initial_state']}
            props['load_condition']={'type':'string','enum':[x['name'] for x in problem['loads']]+['all_frozen_conditions']}
            props['comparison_load_conditions']['items']['enum']=[x['name'] for x in problem['loads']]
            props['effect_semantics']={'type':'string','enum':['mechanism_effect','re_equilibrated_passive_response','finite_time_task_response']}
            target_props=schema['$defs']['PhysicalMechanismTarget']['properties']
            for name in ('tendon_channel','direction_generalized'):target_props.pop(name,None)
            target_props['reduction']={'type':'string','enum':['identity','norm','minimum','maximum','directional_norm','directional_component'],'default':'identity'}
            schema['$defs']['ScientificStructureV4']['required']+=['physical_problem','load_condition','requested_budget']
        elif candidate:
            props=schema['$defs']['ScientificStructureV4']['properties']
            for name in ('physical_problem','load_condition','comparison_load_conditions','load_aggregation'):props.pop(name,None)
            props['effect_semantics']={'type':'string','enum':['mechanism_effect','fixed_input_response','reoptimized_task_capability']}
            props['control_treatment']={'type':'string','enum':['fixed_absolute_tensions','reoptimized']}
            props['operating_point']={'type':'string','enum':['frozen_task_initial_state','same_generalized_coordinates','fixed_generalized_pose','saved_native_state']}
            target=schema['$defs']['PhysicalMechanismTarget']['properties']
        from extensions.math_analysis.mechanism_registry import mechanism_ids,PRIMITIVES
        mode='passive_unilateral_equilibrium' if passive else 'active_ideal_tension'
        target=schema['$defs']['PhysicalMechanismTarget']
        target['properties']['quantity']={'type':'string','enum':mechanism_ids(mode),
            'description':'instantaneous_braking is the signed d(speed)/dt range [minimum, maximum], in m/s^2. Strongest deceleration corresponds to the minimum endpoint (more negative); maximum/increase raises the upper speed-up endpoint. No sign inversion or target conversion is automatic.'}
        target.setdefault('allOf',[]).append(dict(
            **{'if':dict(properties=dict(quantity=dict(enum=['constraint_output_row_residual','all_tendon_output_row_residual'])),required=['quantity'])},
            then=dict(required=['projection_world'],properties=dict(projection_world=dict(type='array')))))
        target['allOf'].append({'if':{'anyOf':[
            {'properties':{'quantity':{'enum':['directional_acceleration_bounds','directional_drive','directional_tendon_row_residual','motion_decoupling','directional_material_response']}},'required':['quantity']},
            {'properties':{'reduction':{'enum':['directional_norm','directional_component']}},'required':['reduction']}]},
            'then':{'required':['direction_world'],'properties':{'direction_world':{'type':'array'}}}})
        for reduction,quantities in [('directional_component',['re_equilibrated_position_response']),
                ('directional_norm',[k for k in mechanism_ids(mode) if PRIMITIVES[k]['world_projection']])]:
            target['allOf'].append({'if':{'properties':{'reduction':{'const':reduction}},'required':['reduction']},
                'then':{'properties':{'quantity':{'enum':quantities}}}})
        structure=schema['$defs']['ScientificStructureV4']
        structure['properties']['target']['description']='mechanism_effect requires PhysicalMechanismTarget {quantity, reduction, goal}. fixed_input_response requires a task constraint or tip observable string. reoptimized_task_capability requires a task constraint string, best_found_J (finite Native T1), or optimal_task_violation (affine Conic). Never wrap task metrics in a mechanism object; these values are not interchangeable.'
        if not passive:
            structure['allOf'].append({'oneOf':[
                {'properties':{'saved_state':{'type':'null'},'execution':{'type':'null'},'update_id':{'type':'null'}}},
                {'required':['saved_state'],'properties':{'saved_state':{'$ref':'#/$defs/EvidenceRef'},'execution':{'type':'null'},'update_id':{'type':'null'}}},
                {'required':['execution','update_id'],'properties':{'saved_state':{'type':'null'},'execution':{'$ref':'#/$defs/EvidenceRef'},'update_id':{'type':'integer','minimum':0}}}]})
        if candidate:
            registered=parameter_catalog(spec,candidate)
            groups=sorted({r['parameter_group'] for r in registered if r['selectable']})
            if any(r['selectable'] and r['parameter_id'].endswith('.length_m') for r in registered):groups.append('segment_lengths')
            if not passive:
                for branch in structure['properties']['parameter_group']['anyOf']:
                    if branch.get('type')=='string':branch['enum']=groups
            structure['properties']['parameter_paths']['items']['enum']=[r['parameter_id'] for r in registered if '*' not in r['parameter_id']]
            structure['properties']['parameter_paths']['description']='Choose registered physical parameter IDs from this enum, or a parameter_group. Evidence JSON navigation pointers are not parameter IDs.'
        structure['required']=[k for k in structure['required'] if k not in ('control_treatment','operating_point','physical_problem')]
        structure['description']='Choose operation, effect semantics, target, and parameters. Hypothesis and evaluation cap may reuse the completed diagnose decision. Only uniquely implied execution fields are compiled; distinct working points, sources and scientific methods remain Main choices.'
        from tools.research.structure_research import SCALAR_DIRECTION_TARGETS
        structure['allOf'].append({'if':{'properties':{'operation':{'enum':['differentiate','optimize']},
            'target':{'type':'object'}},'required':['operation','target']},
            'then':{'properties':{'target':{'anyOf':[
                {'properties':{'reduction':{'not':{'const':'identity'}}},'required':['reduction']},
                {'properties':{'quantity':{'enum':list(SCALAR_DIRECTION_TARGETS)}},'required':['quantity']},
                {'properties':{'quantity':{'const':'directional_drive'},'tendon_channel':{'type':'integer'}},
                    'required':['quantity','tendon_channel']}]}}}})
        if not passive:
            from tools.research_tasks import task_adapter
            constraints=([c.constraint_id for c in task_adapter(candidate['configuration']).analysis_requirements({}).constraints]
                if candidate else [])
            for semantics,treatment,target_schema,point in (
                    ('mechanism_effect','fixed_absolute_tensions',{'type':'object'},None),
                    ('fixed_input_response','fixed_absolute_tensions',{'type':'string','enum':[*constraints,'tip_position','tip_velocity']},None),
                    ('reoptimized_task_capability','reoptimized',{'type':'string','enum':[*constraints,'best_found_J','optimal_task_violation']},'frozen_task_initial_state')):
                properties=dict(control_treatment={'const':treatment},target=target_schema)
                if point:properties['operating_point']={'const':point}
                structure['allOf'].append({'if':{'properties':{'effect_semantics':{'const':semantics}},'required':['effect_semantics']},
                    'then':{'properties':properties,**({'required':['operating_point']} if point is None else {})}})
        excluded=[k for k in mechanism_ids(mode) if k not in mechanism_ids(mode,'differentiate')]
        if excluded:
            structure.setdefault('allOf',[]).append({
                'if':{'properties':{'operation':{'enum':['differentiate','optimize']}},'required':['operation']},
                'then':{'properties':{'target':{'properties':{'quantity':{'not':{'enum':excluded}}}}}}})
        if passive:
            structure['allOf'].append({'if':{'properties':{'effect_semantics':{'const':'finite_time_task_response'}},'required':['effect_semantics']},
                'then':{'properties':{'operating_point':{'const':'frozen_task_initial_state'},
                    'target':{'type':'string','const':'finite_time_task_violation'}}},
                'else':{'properties':{'operating_point':{'const':'re_equilibrated'}}}})
        if passive:
            structure['allOf'].append({'if':{'properties':{'operation':{'not':{'const':'compare'}}},'required':['operation']},
                'then':{'properties':{'comparison_load_conditions':{'maxItems':0},'load_aggregation':{'type':'null'}}}})
            structure['allOf'].append({'if':{'properties':{'target':{'type':'object','properties':{'quantity':{'const':'re_equilibrated_position_response'}},'required':['quantity']}},'required':['target']},
                'then':{'properties':{'effect_semantics':{'const':'re_equilibrated_passive_response'}}}})
            structure['allOf'].append({'if':{'properties':{'operation':{'const':'compare'}},'required':['operation']},
                'then':{'oneOf':[{'required':[key],'properties':{key:{'minItems':1}}}
                    for key in ('comparison_candidates','comparison_load_conditions')]}})
            structure['allOf'].append({'if':{'properties':{'load_aggregation':{'enum':['minimum','maximum']}},'required':['load_aggregation']},
                'then':{'required':['comparison_load_conditions'],'properties':{'comparison_load_conditions':{'minItems':1}}}})
    if issubclass(question_contract(spec),ScientificQuestionV2):
        for key in ('search_strategy','requested_budget'):schema['properties'].pop(key)
        schema['$defs']['ScientificControlScope']['properties']['mode']['description']='Choose the full frozen task or a local correction window. control_search_effort selects uniform knots within the frozen Native grant; local corrections require interior knots and zero endpoint corrections. Evaluation always covers the full frozen task.'
    if question_contract(spec) is ScientificQuestionV3:
        schema['properties'].pop('parameter_paths')
        schema['properties']['effect_semantics']['description']='fixed_input_response compares unchanged input; reoptimized_task_capability aggregates already saved comparable T1 results and performs no new control or structure search.'
        if candidate:
            rows=parameter_catalog(spec,candidate)
            schema['properties']['parameter_id']['anyOf'][0]['enum']=[r['parameter_id'] for r in rows if r['selectable']]
    from tools.research.contracts import prune_schema_definitions,compact_schema
    if question_contract(spec) is ScientificQuestionV4:project_control_effort(schema)
    elif 'ScientificControlEffort' in schema.get('$defs',{}):
        schema['$defs']['ScientificControlEffort']['required'].append('method')
    schema=prune_schema_definitions(schema)
    return compact_schema(schema) if question_contract(spec) is ScientificQuestionV4 else schema


def project_control_effort(schema):
    """Provider projection only; historical numerical effort remains readable."""
    effort=schema.get('$defs',{}).get('ScientificControlEffort')
    if effort:
        effort['properties']={k:v for k,v in effort['properties'].items() if k in ('resolution','exploration','evaluation_requests')}
        effort['required']=['resolution','exploration','evaluation_requests']
        for key in ('resolution','exploration'):
            effort['properties'][key]={**next(b for b in effort['properties'][key]['anyOf'] if b.get('type')!='null')}
        effort['description']='Choose temporal freedom, physical exploration scale and a shared finite callback cap. The program binds the numerical method, knots, active coefficients and step sizes; all starts share the cap. Every frozen task constraint remains scored.'
    return schema


def control_settings(spec, effort, *, window=None, channels=None, physical_limit_n=None):
    """Shared v2 effort mapping; original LocalControlSearchSettings is final authority."""
    q=ScientificControlEffort.model_validate(effort)
    duration=spec['analysis_protocol']['duration_s'];a,b=window or (0.,duration)
    if q.resolution is not None or q.exploration is not None:
        if q.resolution is None or q.exploration is None:raise ValueError('SELECT_RESOLUTION_AND_EXPLORATION')
        internal=('method','knot_count','iterations','coefficient_limit_n','initial_radius_n','difference_step_n','minimum_radius_n','active_coefficients')
        if any(k in q.model_fields_set for k in internal):raise ValueError('HIGH_LEVEL_EFFORT_CANNOT_MIX_NUMERICAL_OVERRIDES')
        limit=physical_limit_n
        if limit is None:limit=spec['family_space']['tendon_domains']['force_limit_n']['default']
        if limit<=0:raise ValueError('POSITIVE_PHYSICAL_TENSION_RANGE_REQUIRED')
        n={'coarse':3,'moderate':5,'fine':9}[q.resolution]
        maximum=min(64,spec.get('native_control_limits',{}).get('knots_s',64))
        if n>maximum:raise ValueError('REQUESTED_RESOLUTION_EXCEEDS_FROZEN_KNOT_GRANT')
        period=spec['analysis_protocol']['period_s']
        # Whole-task knots use the actual frozen control samples. An explicit
        # interior window retains its chosen endpoints and zero corrections there.
        grid=[a+(b-a)*i/(n-1) for i in range(n)]
        if window is None:grid=[round(t/period)*period for t in grid]
        if len(set(grid))!=n:raise ValueError('REQUESTED_RESOLUTION_EXCEEDS_FROZEN_TIME_GRID')
        scale=limit*(1. if q.exploration=='broad' else .1)
        numeric=dict(evaluation_requests=q.evaluation_requests,method='response',knot_count=n,
            coefficient_limit_n=scale,initial_radius_n=scale*.25,
            difference_step_n=scale*.01,minimum_radius_n=scale*.0001)
        result=control_settings(spec,numeric,window=window,channels=channels)
        return result.model_copy(update=dict(knots_s=grid))
    if not 0<=a<b<=duration:raise ValueError('LOCAL_WINDOW_MUST_BE_INSIDE_FROZEN_TASK')
    if window is not None and q.knot_count<3:raise ValueError('LOCAL_WINDOW_REQUIRES_INTERIOR_KNOT_AND_ZERO_ENDPOINTS')
    domain=LocalControlSearchSettings.model_json_schema()['properties']
    limits=spec.get('native_control_limits',{})
    iterations=q.iterations if q.iterations is not None else min(q.evaluation_requests,limits.get('iterations',domain['iterations']['maximum']),domain['iterations']['maximum'])
    settings=dict(version='local_control_search_v2',method=q.method,
        knots_s=[a+(b-a)*i/(q.knot_count-1) for i in range(q.knot_count)],
        correction_window_s=[0.,duration],iterations=iterations,evaluation_requests=q.evaluation_requests)
    settings['knots_s'][-1]=b
    for name in ('coefficient_limit_n','initial_radius_n','difference_step_n','minimum_radius_n','active_coefficients'):
        if getattr(q,name) is not None:settings[name]=getattr(q,name)
    if window is not None:
        allowed=set(range(channels,(q.knot_count-1)*channels))
        if q.active_coefficients is not None and not set(q.active_coefficients)<=allowed:
            raise ValueError('LOCAL_WINDOW_ACTIVE_COEFFICIENTS_REQUIRE_INTERIOR_KNOTS')
        settings['active_coefficients']=list(range(channels,(q.knot_count-1)*channels))
        if q.active_coefficients is not None:settings['active_coefficients']=q.active_coefficients
    if channels and any(i>=channels*q.knot_count for i in settings.get('active_coefficients',[])):
        raise ValueError('ACTIVE_COEFFICIENT_OUTSIDE_BOUND_DIMENSIONS')
    result=LocalControlSearchSettings.model_validate(settings)
    for name,limit in limits.items():
        actual=len(result.knots_s) if name=='knots_s' else getattr(result,name)
        if actual>limit:raise ValueError('ORIGINAL_STUDY_NATIVE_CONTROL_LIMIT: '+name)
    return result


def completed_question_plan(host):
    from tools.research.research_context import research_intent
    import json
    s=state(host);references=list(s.get('plans',[]))
    intent = research_intent(host)['latest_decision'] or {}
    # Preparation of the identical object preserves Main's scientific choice.
    # Any other action or condition change ends this carry.
    while (s['spec'].get('research_decisions',{}).get('analysis_interface')=='scientific_question_v4'
            and intent.get('action')=='initialize_control' and intent.get('execution_status')=='completed'):
        saved=host.store.artifact(intent['plan_reference'])
        receipt=json.loads(host.store.lookup(host.run_id,saved['request_id'])['receipt'])
        output=host.store.artifact(receipt['output'])
        actual=output.get('result',output).get('candidate')
        references=references[:references.index(intent['plan_reference'])]
        previous=research_intent(host,plan_references=references)['latest_decision'] or {}
        if not actual or actual!=intent['candidate'] or previous.get('candidate')!=actual:return None
        intent={**previous,'resumed_after_preparation':True}
    decision = (intent.get('agent_hypothesis') or {}).get('decision') or {}
    if (intent.get('action') == 'diagnose' and intent.get('execution_status') == 'completed'
            and intent.get('candidate') and decision.get('selected_candidate') == intent['candidate']):
        return intent
    return None


def expand_v4(spec, payload, candidate=None):
    """Fill only fields uniquely implied by explicit semantics/frozen physics."""
    full=deepcopy(payload);sources={}
    domain=payload.get('domain');body=full.get(domain)
    if not isinstance(body,dict):return full,sources
    def bind(name,value,basis):
        if name not in body:
            body[name]=value;sources[domain+'.'+name]=basis
    if domain=='control':
        bind('question_type','control_feasibility','control domain')
        bind('effect_semantics','reoptimized_task_capability','control feasibility contract')
    if domain=='structure':
        semantics=body.get('effect_semantics')
        passive=((candidate or {}).get('configuration',{}).get('task',{}).get('physical_problem')
            or spec.get('canonical_task',{}).get('physical_problem'))
        if passive:
            bind('physical_problem',passive['mode'],'frozen physical problem')
            bind('control_treatment','no_active_control','frozen passive physical mode')
            if semantics in ('mechanism_effect','re_equilibrated_passive_response','finite_time_task_response'):
                bind('operating_point','frozen_task_initial_state' if semantics=='finite_time_task_response' else 're_equilibrated','selected passive response semantics')
        elif semantics in ('mechanism_effect','fixed_input_response','reoptimized_task_capability'):
            bind('control_treatment','reoptimized' if semantics=='reoptimized_task_capability' else 'fixed_absolute_tensions','selected effect semantics')
            if semantics=='reoptimized_task_capability':bind('operating_point','frozen_task_initial_state','complete frozen-task reoptimization semantics')
    return full,sources


def selected_question_schema(host):
    """One candidate/choice projection for Provider, compiler and binding audit."""
    from tools.research.task_constraints import mathematical_method_view
    intent=completed_question_plan(host)
    if not intent:return None
    return question_schema(state(host)['spec'],host.store.artifact(intent['candidate']),
        intent['agent_hypothesis'].get('next_research_action'),
        control_methods=control_method_choices(mathematical_method_view(host,intent['candidate'])))


def compile_question(host, payload, *, tool_use_id):
    """Version dispatch only; all paths end in original execution and allowance."""
    spec=state(host)['spec'];version=spec.get('research_decisions',{}).get('analysis_interface')
    if version=='scientific_question_v4':
        from pydantic import ValidationError
        if protected(host) or state(host)['research_status']=='stopped':
            return dict(status='blocked',reason='ORIGINAL_PROTECTED_CLOSEOUT_OR_STOP',scientific_execution_started=False)
        intent=completed_question_plan(host)
        candidate=host.store.artifact(intent['candidate']) if intent else None
        choice=(intent or {}).get('agent_hypothesis',{}).get('next_research_action')
        if choice in ('mechanism_research','single_parameter_effect') and payload.get('domain')=='control' or choice=='control_feasibility' and payload.get('domain')=='structure':
            return dict(status='needs_choice',reason='DIAGNOSE_DOMAIN_MISMATCH',scientific_execution_started=False,
                next=dict(tool='research_route',input=dict(tool='research_plan',action='diagnose')),
                then=dict(tool='research_plan',action='diagnose',next_research_action='control_feasibility' if payload['domain']=='control' else 'mechanism_research'),
                explanation='First call research_route with the supplied input to load the diagnose Schema. Then submit your complete candidate-bound diagnose Plan with your own hypothesis and chosen next_research_action before the matching research_analysis domain. The previously loaded Plan Schema may still allow only initialize_control. Route selection performs no scientific execution and does not replace the required diagnose. No Worker or reference-hash entry is required for this handoff.')
        if payload.get('domain')=='control' and (payload.get('control') or {}).get('numerical_method')=='sampled-affine-conic-minimax-v1':
            return dict(status='needs_choice',reason='CONIC_REQUIRES_SEPARATE_AFFINE_TASK_CAPABILITY_ENTRY',
                conic_entry=conic_entry(),scientific_execution_started=False)
        body=payload.get('structure') or {}
        if body.get('effect_semantics')=='reoptimized_task_capability' and isinstance(body.get('target'),dict):
            return dict(status='needs_choice',reason='REOPTIMIZED_TASK_TARGET_REQUIRES_STRING',
                choices=['best_found_J','optimal_task_violation','registered frozen task constraint ID'],
                explanation='A PhysicalMechanismTarget object describes a mechanism quantity. Native best observed value and affine Conic optimum have distinct evidence requirements; Main must choose.',
                scientific_execution_started=False)
        if intent and body.get('saved_state') and (body.get('execution') or body.get('update_id') is not None):
            from tools.research.task_constraints import mathematical_method_view,selected_operating_point_guidance
            detail=mathematical_method_view(host,intent['candidate'])['methods']['mechanism_structure_v1']
            return dict(status='needs_choice',reason='UNAMBIGUOUS_NATIVE_SOURCE_AND_INTERVAL_REQUIRED',
                operating_point_sources=selected_operating_point_guidance(host,intent['candidate'],'mechanism_structure_v1',detail),
                scientific_execution_started=False)
        expanded,field_sources=expand_v4(spec,payload,candidate)
        try:q=ScientificQuestionV4.model_validate(expanded)
        except ValidationError as exc:
            return dict(status='needs_choice',reason='INVALID_SCIENTIFIC_V4_INPUT',issues=[
                dict(field='.'.join(map(str,e['loc'])),reason=e['msg']) for e in exc.errors()],scientific_execution_started=False)
        if q.domain=='structure':
            structure=payload['structure']
            if (q.structure.operation in ('differentiate','optimize') and
                    isinstance(structure.get('target'),dict) and 'goal' not in structure['target']):
                return dict(status='needs_choice',reason='EXPLICIT_MECHANISM_GOAL_REQUIRED',fields=['structure.target.goal'],scientific_execution_started=False)
        if q.domain=='control' and spec.get('canonical_task',{}).get('physical_problem'):
            return dict(status='unsupported',reason='PASSIVE_HAS_NO_ACTIVE_CONTROL_OPTIMIZATION',scientific_execution_started=False)
        if q.domain=='control' and q.control.question_type!='control_feasibility':
            return dict(status='needs_choice',reason='CONTROL_DOMAIN_REQUIRES_CONTROL_FEASIBILITY',scientific_execution_started=False)
        from jsonschema import Draft202012Validator
        schema=selected_question_schema(host) if intent else question_schema(spec,candidate,choice)
        errors=list(Draft202012Validator(schema).iter_errors(payload))
        if errors:
            return dict(status='needs_choice',reason='INVALID_SCIENTIFIC_V4_INPUT',issues=[
                dict(field='.'.join(map(str,e.absolute_path)),reason=e.message) for e in errors],
                scientific_execution_started=False)
        result=(compile_mechanism(host,expanded['structure'],tool_use_id=tool_use_id,v4=True) if q.domain=='structure' else
            compile_v1(host,expanded['control'],tool_use_id=tool_use_id,contract=ScientificControlV4,source_question=payload))
        if result['status']!='ready':return result
        from tools.research.state import save
        result['method_alignment']=method_alignment(intent,payload,result['method'],result['request'])
        result['intent_compilation']=save(host,dict(version='scientific_intent_compilation_v1',
            tool_use_id=tool_use_id,plan_reference=intent['plan_reference'],raw_main_input=deepcopy(payload),
            provider_schema=schema,compiled_question=expanded,deterministic_field_sources=field_sources,
            full_request=result['request'],method_alignment=result['method_alignment'],scientific_execution_started=False),'scientific_intent_compilation')
        return result
    if mechanism_interface(spec):return compile_mechanism(host,payload,tool_use_id=tool_use_id)
    return compile_v1(host,payload,tool_use_id=tool_use_id,contract=question_contract(spec))


def method_alignment(intent,payload,method,request):
    """Compare structured identities; never infer a solver from prose."""
    from tools.research.task_constraints import registered_analysis_method_names
    selected=(intent.get('agent_hypothesis',{}).get('decision') or {}).get('selected_method')
    explicit=(payload.get('control') or {}).get('numerical_method')
    plan_method=selected if selected in registered_analysis_method_names() else None
    declared=explicit or plan_method
    body=payload.get(payload.get('domain')) or {}
    return dict(plan_selected_method=selected,plan_registered_method=plan_method,main_structured_method=declared,
        main_structured_choice={k:body[k] for k in ('operation','effect_semantics','target','numerical_method') if k in body},compiled_method=method,
        compiled_operation=request['operation'],worker_operation=None,
        structured_request_status='not_tested' if declared and declared!=method else 'pending_worker',
        original_hypothesis_status='not_tested' if plan_method and plan_method!=method else 'pending_worker' if plan_method else 'requires_main_review',
        signed_target_semantics=('instantaneous_braking is the signed d(speed)/dt range [minimum, maximum], in m/s^2. Strongest deceleration corresponds to the minimum endpoint (more negative); maximum/increase raises the upper speed-up endpoint. No sign inversion or target conversion is automatic.' if isinstance(body.get('target'),dict) and body['target'].get('quantity')=='instantaneous_braking' else None),
        reason='Only registered structured method identities are compared; free-text Plan method and broader hypothesis require Main review.')


def compile_v1(host, payload, *, tool_use_id, source_question=None, contract=ScientificQuestion):
    """Return actionable preparation/choice feedback or the original full contract."""
    from pydantic import ValidationError
    from tools.research.task_constraints import mathematical_method_view
    from tools.research.agent import bind_selected_analysis_request
    from tools.research.design import verify_candidate
    from tools.research.optimal_capability import family_analysis_parameters
    try:
        question = contract.model_validate(payload)
    except ValidationError as exc:
        return dict(status='needs_choice',reason='INVALID_SCIENTIFIC_INPUT',issues=[
            dict(field='.'.join(map(str,e['loc'])),reason=e['msg']) for e in exc.errors()],scientific_execution_started=False)
    q = question
    def feedback(status, reason, **extra):
        return dict(status=status,reason=reason,question=plain(q),scientific_execution_started=False,**extra)
    s = state(host);spec = s['spec']
    if protected(host) or s['research_status']=='stopped':
        return feedback('blocked','ORIGINAL_PROTECTED_CLOSEOUT_OR_STOP')
    intent = completed_question_plan(host)
    if not intent:
        return feedback('needs_prerequisite','COMPLETED_CANDIDATE_BOUND_DIAGNOSE_REQUIRED',
            preparation=dict(tool='research_plan',action='diagnose',fields=['hypothesis','decision.selected_candidate']))
    candidate = intent['candidate']
    if (q.question_type=='structure_parameter_effect' and
            (q.control_scope or q.search_strategy or getattr(q,'control_search_effort',None) or
             q.source_selection.control_source or q.source_selection.additional_control_sources or q.requested_budget is not None)):
        return feedback('needs_choice','SCIENTIFIC_OPERATION_MISMATCH',
            scientific_result_produced=False,
            explanation='Structural effect analysis reuses fixed input or comparable saved T1 results; it does not search new structures or run new T1 optimization.',
            choices=[dict(scientific_goal='structure_control_codesign',tool='research_plan',action='search'),
                dict(scientific_goal='single_parameter_effect',tool='research_analysis',
                    prerequisites=['registered_parameter','comparable_saved_evidence'])])
    if issubclass(contract,ScientificQuestionV3) and ('parameter_paths' in payload or 'search_strategy' in payload or 'requested_budget' in payload):
        return feedback('needs_choice','USE_VERSIONED_SCIENTIFIC_SELECTION_FIELDS',fields=['parameter_group','parameter_id','control_search_effort'])
    if contract is not ScientificQuestionV3 and q.question_type=='structure_parameter_effect' and not q.parameter_paths and intent['agent_hypothesis']['decision'].get('selected_variables'):
        q = q.model_copy(update={'parameter_paths':intent['agent_hypothesis']['decision']['selected_variables']})
    try:
        c = verify_candidate(host,candidate)
        view = mathematical_method_view(host,candidate)
    except (ValueError,KeyError) as exc:
        return feedback('needs_prerequisite',str(exc))
    if q.question_type=='control_feasibility':
        if q.effect_semantics not in (None,'reoptimized_task_capability'):
            return feedback('unsupported','CONTROL_FEASIBILITY_REQUIRES_CONTROL_REOPTIMIZATION')
        if q.parameter_paths or getattr(q,'parameter_group',None) or getattr(q,'parameter_id',None) or q.fixed_input or q.tensions_n is not None or q.response_horizon_s is not None:
            return feedback('unsupported','STRUCTURAL_OR_FIXED_INPUT_FIELDS_DO_NOT_DESCRIBE_CONTROL_FEASIBILITY')
        method = T1
        if contract is ScientificControlV4:
            choices=control_method_choices(view)
            selected=q.numerical_method
            if selected is not None:
                method=selected
            elif T1 not in view['methods'] or not view['methods'][T1]['kernel_supported']:
                legal=[r['method'] for r in choices if r['selectable']]
                if len(legal)!=1:
                    return feedback('needs_choice' if legal else 'blocked','REGISTERED_CONTROL_METHOD_REQUIRED',choices=choices)
                method=legal[0]
            # Reach/Hold keeps its original T1 result and evidence semantics.
            # A blocked T1 is never silently replaced by a different identity.
    else:
        if not spec.get('family_space') or not c.get('generation_version'):
            return feedback('unsupported','C2_STRUCTURAL_QUESTIONS_REQUIRE_REGISTERED_FAMILYSPACE_PATHS')
        if q.effect_semantics is None:
            return feedback('needs_choice','STRUCTURAL_EFFECT_SEMANTICS_REQUIRED',
                choices=dict(effect_semantics=['fixed_input_response','reoptimized_task_capability']))
        if q.effect_semantics not in ('fixed_input_response','reoptimized_task_capability'):
            return feedback('unsupported','SCIENTIFIC_SEMANTICS_NOT_ADAPTED',
                missing_capability=q.effect_semantics,
                detail_query=dict(reference=candidate,view='mathematical_capabilities',pointer='/capability_inventory'))
        method = 'fixed_input_structure_v1' if q.effect_semantics=='fixed_input_response' else T2
        if contract is ScientificQuestionV3:
            rows=parameter_catalog(spec,c,q.parameter_group,method)
            if q.parameter_group is None:
                return feedback('needs_choice','PARAMETER_GROUP_REQUIRED',choices=dict(parameter_groups=sorted({r['parameter_group'] for r in rows if r['selectable']})))
            if q.parameter_id is None:
                return feedback('needs_choice','REGISTERED_PHYSICAL_PARAMETER_REQUIRED',choices=dict(parameters=rows))
            if not any(r['parameter_id']==q.parameter_id for r in rows):
                return feedback('unsupported','REGISTERED_EFFECTIVE_CONTINUOUS_PARAMETER_REQUIRED',
                    field='parameter_id',choices=dict(parameters=rows))
            q=q.model_copy(update={'parameter_paths':[q.parameter_id]})
        if not q.parameter_paths:
            return feedback('needs_choice','REGISTERED_PARAMETER_PATH_REQUIRED',
                choices=dict(parameter_paths=[r['parameter_id'] for r in family_analysis_parameters(spec,c)
                    if r['continuous_perturbation'] and r['effective_in_current_execution']]))
        if len(q.parameter_paths)!=1:
            return feedback('unsupported','C2_SUPPORTS_ONE_INDEPENDENT_CONTINUOUS_PATH_PER_QUESTION')
        rows = {r['parameter_id']:r for r in family_analysis_parameters(spec,c)}
        row = rows.get(q.parameter_paths[0])
        if not row or not row['continuous_perturbation'] or not row['effective_in_current_execution']:
            return feedback('unsupported','REGISTERED_EFFECTIVE_CONTINUOUS_PARAMETER_REQUIRED',
                field='parameter_paths',parameter=row)
        if method not in row['applicable_mathematical_methods']:
            return feedback('blocked','ORIGINAL_PARAMETER_METHOD_AUTHORIZATION_REQUIRED',parameter=row)
    detail = view['methods'].get(method)
    if not detail:
        return feedback('blocked','ORIGINAL_FROZEN_METHOD_GRANT_REQUIRED',method=method)
    status = detail['planning_status']
    if status in ('unauthorized','insufficient_budget','blocked'):
        return feedback('blocked','ORIGINAL_METHOD_ADMISSION_BLOCKED',method=method,missing=detail['missing'])
    if status=='unsupported':
        return feedback('unsupported','ORIGINAL_METHOD_TASK_OR_MODEL_UNSUPPORTED',method=method,missing=detail['missing'])
    metrics = {r['constraint']['constraint_id'] for r in view['research_opportunities']['metrics'] if r.get('constraint')}
    if q.focus_metric and q.focus_metric not in metrics:
        return feedback('unsupported','FOCUS_MUST_NAME_A_REGISTERED_TASK_CONSTRAINT',
            field='focus_metric',choices=sorted(metrics))
    if method in (T1,DIRECT):
        if q.source_selection.comparison_candidates or q.source_selection.t1_results:
            return feedback('unsupported','CONTROL_SEARCH_REQUIRES_A_CONTROL_SOURCE_NOT_STRUCTURAL_EVIDENCE')
        effort=getattr(q,'control_search_effort',None)
        if isinstance(q,ScientificQuestionV2) and (effort is None or q.search_strategy is not None or q.requested_budget is not None):
            return feedback('needs_choice','USE_CONTROL_SEARCH_EFFORT_WITH_INDEPENDENT_KNOT_ITERATION_AND_CALLBACK_FIELDS',fields=['control_search_effort'])
        plan_budget = intent['agent_hypothesis']['decision'].get('requested_budget',0)
        budget = q.requested_budget if q.requested_budget is not None else plan_budget or None
        if effort:budget=effort.evaluation_requests
        missing = [name for name in ('control_scope',) if getattr(q,name) is None]
        if not effort and q.search_strategy is None:missing.append('search_strategy')
        if budget is None:missing.append('requested_budget')
        if missing:
            return feedback('needs_choice','CONTROL_SEARCH_SCIENTIFIC_CHOICES_REQUIRED',fields=missing,
                choices=dict(control_scope=['full_task','time_window'],search_strategy=['response','pattern']))
        from tools.research.physical_replay import legal_control_sources
        selected = plain(q.source_selection.control_source) if q.source_selection.control_source else None
        legal = legal_control_sources(host,candidate,selected)
        if not legal:
            return feedback('needs_prerequisite','COMPLETE_LEGAL_CONTROL_SOURCE_REQUIRED',
                preparation=dict(tool='research_plan',action='initialize_control',control_seed=dict(candidate=candidate,method='baseline')))
        if len(legal)>1:
            return feedback('needs_choice','SCIENTIFICALLY_DISTINCT_CONTROL_SOURCES',choices=dict(control_source=legal))
        from tools.research.config import frozen_analysis_protocol
        protocol=frozen_analysis_protocol(spec,c)
        duration = protocol['duration_s']
        if q.control_scope.mode=='full_task':
            if q.control_scope.window_s is not None:
                return feedback('needs_choice','FULL_TASK_SCOPE_HAS_NO_LOCAL_WINDOW')
            knots = [0.,duration];active = None
        else:
            window = q.control_scope.window_s
            if q.control_scope.mode in ('reach_phase','holding_phase'):
                if window is not None:return feedback('needs_choice','PHASE_SCOPE_CANNOT_OVERRIDE_FROZEN_PHASE_TIME')
                from tools.research_tasks import task_adapter
                try:options=task_adapter(c['configuration']).control_search_options()
                except (ValueError,NotImplementedError):return feedback('unsupported','FROZEN_TASK_HAS_NO_REACH_HOLD_PHASE')
                start=options.get('holding_start')
                if start is None:return feedback('unsupported','FROZEN_TASK_HAS_NO_REACH_HOLD_PHASE')
                window=(0.,start) if q.control_scope.mode=='reach_phase' else (start,duration)
            if window is None or not 0<=window[0]<window[1]<=duration:
                return feedback('needs_choice','LOCAL_WINDOW_MUST_BE_INSIDE_FROZEN_TASK',task_duration_s=duration)
            a,b = window
            # np.interp extends endpoints. Zero endpoint coefficients and only an
            # active middle knot make the actual correction zero outside [a,b].
            knots = [a,(a+b)/2,b]
            channels = len(c['configuration']['robot']['structure']['data']['tendons'])
            active = list(range(channels,2*channels))
        settings = dict(version='local_control_search_v2',method=q.search_strategy,knots_s=knots,
            correction_window_s=[0.,duration],evaluation_requests=budget)
        if spec['budgets']['mathematical_evaluations'] is None:
            settings['iterations']=min(budget,spec.get('native_control_limits',{}).get('iterations',10000))
        if active is not None:settings['active_coefficients']=active
        if effort:
            try:
                settings=plain(control_settings({**spec,'analysis_protocol':protocol},effort,window=window if q.control_scope.mode!='full_task' else None,
                    channels=len(c['configuration']['robot']['structure']['data']['tendons']),
                    physical_limit_n=max(t['force_limit_n'] for t in c['configuration']['robot']['structure']['data']['tendons'])))
                knots=settings['knots_s']
            except ValueError as exc:
                return feedback('needs_choice','SEARCH_SETTINGS_OUTSIDE_ORIGINAL_CONTRACT',field='control_search_effort',reason_detail=str(exc))
        try:defaults = LocalControlSearchSettings.model_validate(settings)
        except ValidationError as exc:
            return feedback('needs_choice','SEARCH_SETTINGS_OUTSIDE_ORIGINAL_CONTRACT',
                issues=[dict(field='.'.join(map(str,e['loc'])),reason=e['msg']) for e in exc.errors()])
        for name,limit in spec.get('native_control_limits',{}).items():
            actual = len(knots) if name=='knots_s' else getattr(defaults,name)
            if actual>limit:
                return feedback('blocked','ORIGINAL_STUDY_NATIVE_CONTROL_LIMIT',field=name,requested=actual,maximum=limit)
        compiled = dict(control_optimization=dict(source=legal[0],settings=settings))
        if q.source_selection.additional_control_sources:
            additional=[]
            for ref in q.source_selection.additional_control_sources:
                choices=legal_control_sources(host,candidate,plain(ref))
                if len(choices)!=1:
                    return feedback('needs_prerequisite','COMPLETE_LEGAL_ADDITIONAL_CONTROL_SOURCE_REQUIRED',source=plain(ref))
                additional.append(choices[0])
            if budget<len(additional)+1:
                return feedback('needs_choice','CALLBACK_CAP_MUST_COVER_SELECTED_STARTS',required_callbacks=len(additional)+1)
            compiled['control_optimization']['additional_sources']=additional
        if method==DIRECT:compiled['operating_point']='standardized_initial_pretension'
    else:
        if q.control_scope or q.search_strategy or getattr(q,'control_search_effort',None) or q.source_selection.control_source or q.source_selection.additional_control_sources:
            return feedback('unsupported','STRUCTURAL_COMPARISON_REUSES_FIXED_INPUT_OR_SAVED_T1_SETTINGS')
        path = q.parameter_paths[0]
        if method==T2:
            if q.fixed_input or q.tensions_n is not None or q.response_horizon_s is not None or q.source_selection.comparison_candidates:
                return feedback('unsupported','REOPTIMIZED_EFFECT_REQUIRES_SAVED_T1_EVIDENCE_NOT_FIXED_INPUT')
            if q.requested_budget is not None:
                return feedback('unsupported','T2_IS_ONE_AGGREGATION_NOT_A_NEW_SEARCH_BUDGET')
            ready = [r for r in detail.get('ready_requests',[]) if r['nonlinear_response']['variable']==path]
            if q.source_selection.t1_results:
                ready = [r for r in ready if r['nonlinear_response']['t1_results']==[plain(ref) for ref in q.source_selection.t1_results]]
            if not ready:
                return feedback('needs_prerequisite','COMPARABLE_COMPLETED_BASELINE_MINUS_PLUS_T1_REQUIRED',
                    missing=['baseline T1','symmetric minus/plus candidates and T1','same input, search settings, frozen task and initialization'],
                    preparation=detail.get('preparation'),scientific_choices=['parameter step/direction','candidate contrasts','T1 control search choices'],
                    detail_query=detail['detail_query'])
            if len(ready)>1:
                return feedback('needs_choice','MULTIPLE_COMPARABLE_T1_STENCILS',
                    choices=dict(t1_results=[r['nonlinear_response']['t1_results'] for r in ready]))
            compiled = dict(nonlinear_response=deepcopy(ready[0]['nonlinear_response']))
        else:
            if q.source_selection.t1_results or q.requested_budget is not None:
                return feedback('unsupported','FIXED_INPUT_RESPONSE_DOES_NOT_USE_T1_OR_SEARCH_BUDGET')
            missing = [name for name in ('fixed_input','response_horizon_s') if getattr(q,name) is None]
            if missing:
                return feedback('needs_choice','FIXED_INPUT_AND_SHORT_RESPONSE_HORIZON_REQUIRED',fields=missing,
                    choices=dict(fixed_input=['frozen_initial_tensions','constant_tensions']))
            if (q.fixed_input=='constant_tensions') != (q.tensions_n is not None):
                return feedback('needs_choice','CONSTANT_TENSIONS_REQUIRE_AN_EXPLICIT_VECTOR_ONLY')
            from tools.research.native_analysis import structure_context
            from tools.research.contracts import NativeStructureResponse
            selected = [plain(ref) for ref in q.source_selection.comparison_candidates]
            contrasts = []
            for ref in (selected or list(s['candidates'].values())):
                if ref==candidate:continue
                try:
                    other = verify_candidate(host,ref)
                    structure_context(c,[(ref,other)],NativeStructureResponse(variable=path,candidates=[ref]),spec=spec)
                except (ValueError,KeyError,IndexError):continue
                contrasts.append(ref)
            if (selected and contrasts!=selected) or not contrasts:
                return feedback('needs_prerequisite','LEGAL_SAME_TASK_SINGLE_PARAMETER_CONTRAST_REQUIRED',
                    preparation=dict(tool='research_plan',action='generate',parameter_path=path),scientific_choices=['contrast direction and step'])
            if not selected and len(contrasts)>1:
                return feedback('needs_choice','MULTIPLE_STRUCTURAL_CONTRASTS',choices=dict(comparison_candidates=contrasts))
            native = dict(horizon_s=q.response_horizon_s)
            if q.tensions_n is not None:native['tensions_n']=q.tensions_n
            compiled = dict(operating_point='standardized_initial_pretension',native=native,
                structure_response=dict(variable=path,candidates=contrasts))
    if source_question is not None:
        for name in ('saved_state','execution','update_id'):
            if source_question.get(name) is not None:compiled[name]=source_question[name]
        if source_question.get('saved_state') or source_question.get('execution'):compiled['operating_point']='saved_state'
    full = bind_selected_analysis_request(host,compiled,tool_use_id=tool_use_id,selection=(method,detail),scientific_question=source_question or payload)
    return dict(status='ready',method=method,request=full,scientific_execution_started=False,
        execution_admission='Original analysis.dispatch owns final source, applicability, authorization and budget admission.',
        limitations=detail['limitations'],cost_scope=detail['cost_scope'])


def compile_mechanism(host, payload, *, tool_use_id,v4=False):
    """Resolve physical meaning and actual domains; original worker owns execution."""
    from pydantic import ValidationError
    from tools.research.contracts import MechanismQuestionV2,MechanismStudy,ScientificStructureV4
    from tools.research.task_constraints import mathematical_method_view
    from tools.research.design import verify_candidate
    from tools.research.agent import bind_selected_analysis_request
    from tools.research.structure_research import METHOD,parameters,prepare_context,group_matches,MechanismBudgetError
    try:q=(ScientificStructureV4 if v4 else MechanismQuestionV2).model_validate(payload)
    except ValidationError as exc:
        return dict(status='needs_choice',reason='INVALID_SCIENTIFIC_V2_INPUT',issues=[
            dict(field='.'.join(map(str,e['loc'])),reason=e['msg']) for e in exc.errors()],scientific_execution_started=False)
    def feedback(status,reason,**extra):
        return dict(status=status,reason=reason,question=plain(q),scientific_execution_started=False,**extra)
    s=state(host);spec=s['spec']
    if protected(host) or s['research_status']=='stopped':return feedback('blocked','ORIGINAL_PROTECTED_CLOSEOUT_OR_STOP')
    intent=completed_question_plan(host)
    if not intent:return feedback('needs_prerequisite','COMPLETED_CANDIDATE_BOUND_DIAGNOSE_REQUIRED',
        preparation=dict(tool='research_plan',action='diagnose',fields=['hypothesis','decision.selected_candidate']))
    c=verify_candidate(host,intent['candidate'])
    from tools.research_tasks import task_adapter
    capabilities=task_adapter(c['configuration']).physical_capabilities()
    if capabilities['status']=='unsupported':
        return feedback('unsupported','UNSUPPORTED_PHYSICAL_CAPABILITIES',missing=capabilities['missing'])
    if v4 and q.effect_semantics=='finite_time_task_response':
        return compile_dynamic(host,q,payload,intent,tool_use_id=tool_use_id)
    if c['configuration']['task'].get('physical_problem'):
        if not v4:return feedback('unsupported','PASSIVE_REQUIRES_V4_PHYSICAL_SEMANTICS')
        return compile_constrained(host,q,payload,intent,tool_use_id=tool_use_id)
    if v4 and (q.physical_problem or q.load_condition or q.control_treatment=='no_active_control'):
        return feedback('unsupported','FROZEN_PHYSICAL_MODE_MISMATCH')
    if v4 and (q.comparison_load_conditions or q.load_aggregation):return feedback('unsupported','LOAD_COMPARISON_REQUIRES_PASSIVE_ASSEMBLY')
    if q.effect_semantics=='reoptimized_task_capability':
        from extensions.math_analysis.differentiation_router import select_method
        route=select_method(effect_semantics=q.effect_semantics,capabilities=capabilities,
            saved_t1=bool(q.source_selection.t1_results),saved_conic=bool(q.source_selection.model_results))
        result=compile_reoptimized(host,q,payload,tool_use_id=tool_use_id,intent=intent)
        result['method_selection']=route
        return result
    if q.effect_semantics not in ('mechanism_effect','fixed_input_response'):
        return feedback('unsupported','V2_EFFECT_NOT_IMPLEMENTED',detail={
            'closed_loop_performance':'Requires complete feedback execution and independent frozen task evaluation; no closed-loop derivative adapted.',
            're_equilibrated_passive_response':'Requires qualified passive equilibrium, unilateral active set and KKT regularity; no passive adapter.'}[q.effect_semantics])
    if q.control_treatment!='fixed_absolute_tensions':return feedback('unsupported','FIXED_ABSOLUTE_TENSIONS_REQUIRED')
    if q.control_scope or q.search_strategy or any(plain(q.source_selection).values()):
        return feedback('unsupported','M0_AND_SHORT_M1_REQUIRE_POINT_INPUTS_NOT_CONTROL_SEARCH_OR_M2_SOURCES')
    if q.operating_point in ('re_equilibrated','preserved_physical_state'):
        return feedback('unsupported','WORKING_POINT_MAPPING_NOT_IMPLEMENTED')
    saved=bool(q.saved_state or q.execution)
    if q.native_state_selection and not q.saved_state:
        return feedback('needs_choice','NATIVE_TRAJECTORY_SELECTION_REQUIRES_SAVED_NATIVE_RESULT')
    if q.operating_point=='frozen_task_initial_state' and (saved or q.update_id is not None):
        return feedback('needs_choice','FROZEN_INITIAL_STATE_CANNOT_USE_SAVED_STATE_SOURCE')
    if q.operating_point=='saved_native_state' and not saved:
        return feedback('needs_prerequisite','SAVED_NATIVE_POINT_REQUIRES_REAL_OWNED_STATE_SOURCE')
    if (q.execution is None)!=(q.update_id is None) or q.saved_state and q.execution:
        from tools.research.task_constraints import selected_operating_point_guidance
        detail=mathematical_method_view(host,intent['candidate'])['methods'][METHOD]
        return feedback('needs_choice','UNAMBIGUOUS_NATIVE_SOURCE_AND_INTERVAL_REQUIRED',
            alternatives=['saved_state only: exact complete owned checkpoint','execution plus actual update_id only: owned measured trace'],
            operating_point_sources=selected_operating_point_guidance(host,intent['candidate'],METHOD,detail))
    candidate=intent['candidate'];c=verify_candidate(host,candidate);view=mathematical_method_view(host,candidate)
    rows=parameters(spec,c);by_path={r['parameter_id']:r for r in rows}
    paths=q.parameter_paths
    if not paths and (not v4 or q.operation in ('differentiate','optimize')):
        paths=intent['agent_hypothesis']['decision'].get('selected_variables') or []
    if len(paths)>2:return feedback('needs_choice','SELECT_AT_MOST_TWO_PARAMETERS')
    if not paths and q.parameter_group:
        matches=[r['parameter_id'] for r in rows if r['mechanism_differentiation']['supported'] and group_matches(r,q.parameter_group)]
        if 1<=len(matches)<=2:paths=matches
        elif q.operation in ('differentiate','optimize'):
            return feedback('needs_choice','SELECT_UP_TO_TWO_EFFECTIVE_PARAMETERS_FROM_GROUP',choices=dict(parameter_paths=matches))
    if q.operation in ('differentiate','optimize') and not paths:
        return feedback('needs_choice','REGISTERED_PARAMETER_SELECTION_REQUIRED',choices=dict(parameter_paths=[
            r['parameter_id'] for r in rows if r['mechanism_differentiation']['supported']]))
    for path in paths:
        row=by_path.get(path)
        if row is None:return feedback('unsupported','REGISTERED_STRUCTURAL_PARAMETER_REQUIRED',path=path)
        if q.operation!='inspect' and row.get('input_set_changes'):
            return feedback('unsupported','INPUT_FEASIBLE_SET_CHANGE_REQUIRES_SEPARATE_SEMANTICS')
        if q.parameter_group and not group_matches(row,q.parameter_group):return feedback('needs_choice','PARAMETER_PATH_AND_GROUP_DISAGREE')
        if q.operation in ('differentiate','optimize') and not row['mechanism_differentiation']['supported']:
            reason=row['mechanism_differentiation']['reason']
            return feedback('blocked' if reason=='ORIGINAL_FROZEN_PARAMETER_AUTHORIZATION_REQUIRED' else 'unsupported',reason,path=path)
    budget=q.requested_budget or intent['agent_hypothesis']['decision'].get('requested_budget')
    if not budget:return feedback('needs_choice','EXPLICIT_LOCAL_EVALUATION_CAP_REQUIRED')
    point_fields=dict(operating_point='saved_state' if saved else 'standardized_initial_pretension')
    for name in ('saved_state','execution','update_id','native_state_selection'):
        if getattr(q,name) is not None:point_fields[name]=plain(getattr(q,name))
    if q.effect_semantics=='fixed_input_response':
        if not isinstance(q.target,str):return feedback('needs_choice','SHORT_RESPONSE_REQUIRES_REGISTERED_TASK_CONSTRAINT_OR_NATIVE_OBSERVABLE')
        constraints={r['constraint']['constraint_id'] for r in view['research_opportunities']['metrics'] if r.get('constraint')}
        if q.target not in constraints|{'tip_position','tip_velocity'}:return feedback('unsupported','UNREGISTERED_SHORT_RESPONSE_TARGET')
        if q.response_horizon_s is None:return feedback('needs_choice','EXPLICIT_SHORT_RESPONSE_HORIZON_REQUIRED')
        if q.operating_point=='fixed_generalized_pose':return feedback('unsupported','EXISTING_M1_PRESERVES_RECORDED_VELOCITY_NOT_ZERO_POSE_MAPPING')
        if q.operation=='optimize':return feedback('unsupported','SHORT_RESPONSE_DOES_NOT_OPTIMIZE_A_STRUCTURE_OR_CONTROL')
        method='short_input_response_v1' if q.operation=='inspect' else 'fixed_input_structure_v1'
        needed=1 if method=='short_input_response_v1' else 1+max(1,len(q.comparison_candidates))
        if budget<needed or not mathematics_fits(spec,s.get('mathematical_evaluations',0),needed):
            return feedback('blocked','SHARED_MATHEMATICAL_BUDGET_CANNOT_FIT',required_evaluations=needed)
        if method=='fixed_input_structure_v1':
            if len(paths)!=1:return feedback('needs_choice','SHORT_STRUCTURE_RESPONSE_REQUIRES_ONE_REGISTERED_PATH')
            legacy=dict(question_type='structure_parameter_effect',effect_semantics='fixed_input_response',parameter_paths=paths,
                fixed_input='constant_tensions' if q.tensions_n is not None else 'frozen_initial_tensions',
                response_horizon_s=q.response_horizon_s,source_selection=dict(comparison_candidates=plain(q.comparison_candidates)))
            if q.target in constraints:legacy['focus_metric']=q.target
            if q.tensions_n is not None:legacy['tensions_n']=q.tensions_n
            result=compile_v1(host,legacy,tool_use_id=tool_use_id,source_question=payload)
            if result['status']=='ready':result['response_scope']='Existing M1 fixed-input short response only; no full task improvement.'
            return result
        detail=view['methods'][method]
        if detail['planning_status'] in ('unauthorized','blocked','unsupported','insufficient_budget'):
            return feedback('blocked','ORIGINAL_SHORT_RESPONSE_ADMISSION_REQUIRED',missing=detail['missing'])
        compiled={**point_fields,'native':dict(horizon_s=q.response_horizon_s)}
        if q.tensions_n is not None:compiled['native']['tensions_n']=q.tensions_n
        full=bind_selected_analysis_request(host,compiled,tool_use_id=tool_use_id,selection=(method,detail),scientific_question=payload)
        return dict(status='ready',method=method,request=full,scientific_execution_started=False,
            response_scope='Existing legal-tension short input response at two input scales, not structural or full task capability.',required_evaluations=needed)
    if q.response_horizon_s is not None:return feedback('unsupported','INSTANTANEOUS_MECHANISM_HAS_NO_RESPONSE_HORIZON')
    detail=view['methods'].get(METHOD)
    if not detail or detail['planning_status'] in ('unauthorized','blocked','unsupported','insufficient_budget'):
        return feedback('blocked','ORIGINAL_MECHANISM_ADMISSION_REQUIRED',missing=detail['missing'] if detail else ['V2 method grant'])
    if isinstance(q.target,str):
        constraints={r['constraint']['constraint_id'] for r in view['research_opportunities']['metrics'] if r.get('constraint')}
        return feedback('unsupported','TASK_TARGET_REQUIRES_M1_OR_M2_TASK_RESPONSE' if q.target in constraints else 'UNREGISTERED_TARGET')
    study=MechanismStudy(operation=q.operation,target=q.target,parameter_paths=paths,
        point_semantics=q.operating_point,max_evaluations=budget,local_radius_fraction=q.local_radius_fraction,
        comparison_candidates=q.comparison_candidates)
    try:context=prepare_context(spec,c,study,[(plain(r),verify_candidate(host,r)) for r in q.comparison_candidates])
    except MechanismBudgetError as exc:
        return feedback('blocked',str(exc),minimum_evaluations=exc.minimum_evaluations,
            requested_evaluations=budget,remaining_evaluations=mathematical_remaining(spec,s.get('mathematical_evaluations',0)),
            cost_dependencies=exc.cost_dependencies,
            next_choice='Main must reduce the question or choose a legal cap within the remaining budget; no automatic increase.')
    except ValueError as exc:return feedback('blocked' if str(exc).startswith('MECHANISM_QUESTION_BUDGET') else 'unsupported',str(exc))
    needed=context['evaluations']
    if not mathematics_fits(spec,s.get('mathematical_evaluations',0),needed):
        return feedback('blocked','SHARED_MATHEMATICAL_BUDGET_CANNOT_FIT',required_evaluations=needed,
            minimum_evaluations=context['minimum_evaluations'],requested_evaluations=budget,
            remaining_evaluations=mathematical_remaining(spec,s.get('mathematical_evaluations',0)),
            cost_dependencies=context['cost_dependencies'],next_choice='Main must reduce the question to fit the remaining budget.')
    compiled={**point_fields,'mechanism_study':plain(study)}
    if q.tensions_n is not None:compiled['native']=dict(tensions_n=q.tensions_n)
    full=bind_selected_analysis_request(host,compiled,tool_use_id=tool_use_id,selection=(METHOD,detail),scientific_question=payload)
    return dict(status='ready',method=METHOD,request=full,scientific_execution_started=False,
        hypothesis=q.hypothesis or intent['agent_hypothesis'].get('hypothesis'),required_evaluations=needed,
        minimum_evaluations=context['minimum_evaluations'],limitations=detail['limitations'],cost_scope=detail['cost_scope'])


def compile_dynamic(host,q,payload,intent,*,tool_use_id):
    """V4 full-task observation; the original worker and budgets own all execution."""
    from tools.research.contracts import MechanismStudy,PhysicalMechanismTarget
    from tools.research.design import verify_candidate
    from tools.research.structure_research import prepare_context,METHOD
    from tools.research.task_constraints import mathematical_method_view
    from tools.research.agent import bind_selected_analysis_request
    from tools.research_tasks import task_adapter
    from extensions.math_analysis.differentiation_router import select_method
    spec=state(host)['spec'];c=verify_candidate(host,intent['candidate'])
    capabilities=task_adapter(c['configuration']).physical_capabilities()
    route=select_method(effect_semantics=q.effect_semantics,capabilities=capabilities,operation=q.operation,target=q.target)
    def fail(reason):return dict(status='unsupported',reason=reason,method_selection=route,scientific_execution_started=False)
    if route['validity']=='unsupported':return fail('REGISTERED_FINITE_TIME_STRUCTURE_RESPONSE_REQUIRED')
    if (q.target!='finite_time_task_violation' or q.operating_point!='frozen_task_initial_state' or
            q.control_treatment!='no_active_control' or q.physical_problem!=c['configuration']['task']['physical_problem']['mode']):
        return fail('EXPLICIT_COMPLETE_DYNAMIC_TASK_AND_FROZEN_INITIAL_STATE_REQUIRED')
    if q.tensions_n is not None or q.saved_state or q.native_state_selection or q.execution or q.update_id is not None or q.response_horizon_s is not None or q.control_scope or q.search_strategy or any(plain(q.source_selection).values()):
        return fail('DYNAMIC_PASSIVE_RESPONSE_CANNOT_BIND_ACTIVE_CONTROL_OR_SHORT_HORIZON')
    if q.load_condition not in (None,'all_frozen_conditions') or q.comparison_load_conditions or q.load_aggregation:
        return fail('ALL_FROZEN_CONDITIONS_REQUIRED')
    if q.requested_budget is None:return fail('EXPLICIT_LOCAL_EVALUATION_CAP_REQUIRED')
    study=MechanismStudy(operation=q.operation,target=PhysicalMechanismTarget(quantity='finite_time_task_violation',goal='decrease'),
        parameter_paths=q.parameter_paths,point_semantics='frozen_task_initial_state',effect_semantics=q.effect_semantics,
        max_evaluations=q.requested_budget,local_radius_fraction=q.local_radius_fraction,comparison_candidates=q.comparison_candidates)
    try:
        context=prepare_context(spec,c,study,[(plain(r),verify_candidate(host,r)) for r in q.comparison_candidates])
        detail=mathematical_method_view(host,intent['candidate'])['methods'][METHOD]
    except ValueError as exc:return fail(str(exc))
    if detail['planning_status'] in ('unauthorized','blocked','unsupported','insufficient_budget'):return fail('ORIGINAL_MECHANISM_ADMISSION_REQUIRED')
    if not mathematics_fits(spec,state(host)['mathematical_evaluations'],context['evaluations']):
        return fail('SHARED_MATHEMATICAL_BUDGET_CANNOT_FIT')
    from tools.research.budget import backend_capacity
    if backend_capacity(host)<context['dynamic_cost_bound']['episodes']:return fail('SHARED_PHYSICAL_EPISODE_BUDGET_CANNOT_FIT')
    request=bind_selected_analysis_request(host,dict(operating_point='standardized_initial_pretension',mechanism_study=plain(study)),
        tool_use_id=tool_use_id,selection=(METHOD,detail),scientific_question=payload)
    return dict(status='ready',method=METHOD,request=request,method_selection=route,
        required_evaluations=context['evaluations'],dynamic_cost_bound=context['dynamic_cost_bound'],
        task_acceptance='unmeasured',scientific_execution_started=False)


def compile_constrained(host,q,payload,intent,*,tool_use_id):
    """V4 only; frozen physics, original method admission and allowance."""
    from tools.research.design import verify_candidate
    from tools.research.structure_research import parameters,prepare_context,METHOD
    from tools.research.task_constraints import mathematical_method_view
    from tools.research.agent import bind_selected_analysis_request
    from tools.research.contracts import MechanismStudy
    spec=state(host)['spec'];candidate=intent['candidate'];c=verify_candidate(host,candidate)
    problem=c['configuration']['task']['physical_problem']
    def fail(reason):return dict(status='unsupported',reason=reason,scientific_execution_started=False)
    if q.physical_problem!=problem['mode'] or q.control_treatment!='no_active_control' or q.operating_point!='re_equilibrated':
        return fail('PASSIVE_REQUIRES_EXPLICIT_FROZEN_MODE_RE_EQUILIBRATION_AND_NO_ACTIVE_CONTROL')
    if q.effect_semantics not in ('mechanism_effect','re_equilibrated_passive_response'):return fail('UNSUPPORTED_PASSIVE_EFFECT')
    if q.load_condition not in [x['name'] for x in problem['loads']]:return fail('SELECT_FROZEN_LOAD_CONDITION')
    if q.tensions_n is not None or q.saved_state or q.native_state_selection or q.execution or q.update_id is not None or q.control_scope or q.search_strategy or q.response_horizon_s is not None or any(plain(q.source_selection).values()):
        return fail('PASSIVE_STATIC_QUESTION_CANNOT_BIND_ACTIVE_OR_DYNAMIC_CONTROL')
    from extensions.math_analysis.mechanism_registry import PRIMITIVES
    if isinstance(q.target,str) or problem['mode'] not in PRIMITIVES[q.target.quantity]['physical_modes']:return fail('REGISTERED_CONSTRAINED_OBSERVATION_REQUIRED')
    if q.target.quantity=='re_equilibrated_position_response' and q.effect_semantics!='re_equilibrated_passive_response':return fail('RELATIVE_POSITION_REQUIRES_RE_EQUILIBRATED_EFFECT')
    paths=q.parameter_paths
    if q.operation in ('differentiate','optimize') and not paths:return fail('SELECT_REGISTERED_CONTINUOUS_PARAMETERS')
    if q.requested_budget is None:return fail('EXPLICIT_LOCAL_EVALUATION_CAP_REQUIRED')
    study=MechanismStudy(operation=q.operation,target=q.target,parameter_paths=paths,point_semantics='re_equilibrated',
        load_condition=q.load_condition,comparison_load_conditions=q.comparison_load_conditions,load_aggregation=q.load_aggregation,
        effect_semantics=q.effect_semantics,max_evaluations=q.requested_budget,local_radius_fraction=q.local_radius_fraction,comparison_candidates=q.comparison_candidates)
    try:
        context=prepare_context(spec,c,study,[(plain(r),verify_candidate(host,r)) for r in q.comparison_candidates])
        detail=mathematical_method_view(host,candidate)['methods'][METHOD]
    except ValueError as exc:return fail(str(exc))
    if detail['planning_status'] in ('unauthorized','blocked','unsupported','insufficient_budget'):return fail('ORIGINAL_MECHANISM_ADMISSION_REQUIRED')
    if not mathematics_fits(spec,state(host)['mathematical_evaluations'],context['evaluations']):
        return fail('SHARED_MATHEMATICAL_BUDGET_CANNOT_FIT')
    request=bind_selected_analysis_request(host,dict(operating_point='standardized_initial_pretension',mechanism_study=plain(study)),
        tool_use_id=tool_use_id,selection=(METHOD,detail),scientific_question=payload)
    from tools.research_tasks import task_adapter
    return dict(status='ready',method=METHOD,request=request,required_evaluations=context['evaluations'],
        registered_acceptance=task_adapter(c['configuration']).execution_requirements()['registered_acceptance'],scientific_execution_started=False)


def compile_reoptimized(host,q,payload,*,tool_use_id,intent):
    """Select admitted saved Conic/T1 sources; never generate models or run T1."""
    from tools.research.task_constraints import mathematical_method_view
    from tools.research.agent import bind_selected_analysis_request
    from tools.research.optimal_capability import CONIC,SENSITIVITY,family_parameters
    from tools.research.design import verify_candidate,parameter_value
    candidate=intent['candidate'];c=verify_candidate(host,candidate);s=state(host);spec=s['spec']
    view=mathematical_method_view(host,candidate)
    def feedback(status,reason,**extra):
        return dict(status=status,reason=reason,scientific_execution_started=False,**extra)
    if q.control_treatment!='reoptimized':return feedback('needs_choice','M2_REQUIRES_EXPLICIT_REOPTIMIZED_CONTROL_TREATMENT')
    if q.operating_point!='frozen_task_initial_state' or q.saved_state or q.execution or q.update_id is not None:
        return feedback('unsupported','M2_REQUIRES_COMPLETE_FROZEN_INITIAL_TASK_AND_MATCHED_CONTROL_SOURCES')
    if q.tensions_n is not None or q.response_horizon_s is not None or q.comparison_candidates or q.source_selection.comparison_candidates:
        return feedback('unsupported','M2_USES_FULL_TASK_MODEL_OR_SAVED_T1_NOT_SHORT_FIXED_INPUT_FIELDS')
    metrics={r['constraint']['constraint_id'] for r in view['research_opportunities']['metrics'] if r.get('constraint')}
    if not isinstance(q.target,str) or q.target not in metrics|{'best_found_J','optimal_task_violation'}:
        return feedback('needs_choice','M2_REQUIRES_REGISTERED_TASK_CONSTRAINT_OR_TASK_VIOLATION',choices=sorted(metrics))
    paths=(q.parameter_paths if 'parameter_paths' in q.model_fields_set else
        intent['agent_hypothesis']['decision'].get('selected_variables') or [])
    sources=q.source_selection
    if sources.model_results and sources.t1_results:return feedback('needs_choice','SELECT_CONIC_MODELS_OR_NATIVE_T1_NOT_A_MIXED_GRADIENT')
    if q.target=='best_found_J' and sources.model_results or q.target=='optimal_task_violation' and sources.t1_results:
        return feedback('needs_choice','NAMED_VALUE_AND_MODEL_SEMANTICS_DISAGREE',
            target_semantics=dict(best_found_J='Finite-budget Native T1 best observed value; no strict optimum.',
                optimal_task_violation='Sampled affine Conic optimum; not a Native T1 value.'),
            next_choice='Main must choose the intended metric and matching evidence; no automatic target conversion.',
            conic_entry=conic_entry())
    if q.operation=='optimize':
        if q.target=='optimal_task_violation':return feedback('needs_choice','FINITE_NATIVE_SEARCH_DOES_NOT_RETURN_A_CONIC_OPTIMAL_VALUE')
        if paths:return feedback('needs_prerequisite','GENERATE_CONTRAST_THEN_OPTIMIZE_CONTROL_PER_CANDIDATE',
            preparation=dict(tool='research_plan',action='generate'),automatic_T1=False)
        if sources.model_results or sources.t1_results:return feedback('unsupported','CONTROL_OPTIMIZATION_REQUIRES_A_BOUND_CONTROL_SOURCE')
        legacy=dict(question_type='control_feasibility',effect_semantics='reoptimized_task_capability',
            source_selection=dict(control_source=plain(sources.control_source)) if sources.control_source else {})
        for key in ('control_scope','search_strategy','requested_budget'):
            if getattr(q,key) is not None:legacy[key]=plain(getattr(q,key))
        if q.target in metrics:legacy['focus_metric']=q.target
        return compile_v1(host,legacy,tool_use_id=tool_use_id,source_question=payload)
    if q.control_scope or q.search_strategy or sources.control_source or sources.additional_control_sources:
        return feedback('unsupported','SAVED_M2_REUSES_MATCHED_RECORDED_SEARCH_SETTINGS',
            next_choice='Select matched saved T1 results or Conic models only; remove the control source and new search settings. Generate contrasts and run T1 separately when evidence is missing.',
            automatic_T1=False)
    if not paths:
        if q.operation!='inspect':return feedback('needs_choice','M2_STRUCTURAL_PARAMETER_PATH_REQUIRED')
        if q.target=='best_found_J':return feedback('needs_prerequisite','NATIVE_BEST_FOUND_REQUIRES_SAVED_T1_OR_EXPLICIT_CONTROL_SEARCH')
        if sources.model_results or sources.t1_results:return feedback('needs_choice','STRUCTURAL_SOURCES_REQUIRE_A_REGISTERED_PATH')
        return compile_conic(host,payload,tool_use_id=tool_use_id)
    from tools.research.structure_research import parameters,group_matches
    rows={r['parameter_id']:r for r in parameters(spec,c)}
    for path in paths:
        if path not in rows or not rows[path]['mechanism_differentiation']['supported']:
            return feedback('unsupported','M2_REQUIRES_EFFECTIVE_AUTHORIZED_CONTINUOUS_PARAMETER',path=path)
        if q.parameter_group and not group_matches(rows[path],q.parameter_group):return feedback('needs_choice','PARAMETER_PATH_AND_GROUP_DISAGREE')
    conic=view['methods'].get(SENSITIVITY,{});model_choices=[]
    if len(paths)==1 and not sources.t1_results and q.target!='best_found_J':
        for row in conic.get('readiness',{}).get('variables',[]):
            if row['variable']!=paths[0]:continue
            for ready in row.get('ready_stencils',[]):
                request=ready['request']
                if ready['admission']['status']!='admissible':continue
                if sources.model_results and request['optimal_sensitivity']['model_results']!=[plain(ref) for ref in sources.model_results]:continue
                model_choices.append((request,ready['admission']['expected_mathematical_evaluations']))
    method=None;compiled=None;needed=None
    if len(model_choices)>1:
        return feedback('needs_choice','SELECT_COMPARABLE_CONIC_MODEL_STENCIL',choices=[r['optimal_sensitivity'] for r,_ in model_choices])
    if model_choices:
        request,needed=model_choices[0];method=SENSITIVITY
        compiled=dict(model_source='gvs',operating_point=request['operating_point'],optimal_sensitivity=request['optimal_sensitivity'])
    elif sources.model_results or q.target=='optimal_task_violation':
        if conic.get('planning_status') in ('unauthorized','blocked','insufficient_budget','unsupported'):
            return feedback('blocked','ORIGINAL_M2_METHOD_ADMISSION_BLOCKED',missing=conic.get('missing'),method=SENSITIVITY)
        return feedback('needs_prerequisite','ADMITTED_SAVED_CONIC_MODEL_STENCIL_REQUIRED',
            missing=conic.get('missing'),detail_query=conic.get('detail_query'),preparation=conic.get('readiness',{}).get('model_preparation'))
    else:
        detail=view['methods'].get(T2,{})
        if (not detail or detail.get('planning_status')=='unauthorized') and not sources.t1_results and conic.get('formal_execution_authorized'):
            return feedback('needs_prerequisite','ADMITTED_SAVED_CONIC_MODEL_STENCIL_REQUIRED',
                detail_query=conic.get('detail_query'),preparation=conic.get('readiness',{}).get('model_preparation'),automatic_T1=False)
        if not detail or detail.get('planning_status') in ('unauthorized','blocked','insufficient_budget'):
            return feedback('blocked','ORIGINAL_M2_METHOD_ADMISSION_BLOCKED',missing=detail.get('missing',['Native T2 method grant']),method=T2)
        if detail.get('planning_status')=='unsupported':
            return feedback('unsupported','ORIGINAL_NATIVE_T2_TASK_UNSUPPORTED',missing=detail['missing'],
                conic_detail_query=conic.get('detail_query'),task_constraints=sorted(metrics))
        selected=[plain(ref) for ref in sources.t1_results];choices=[]
        for path in paths:
            found=[r for r in detail.get('ready_requests',[]) if r['nonlinear_response']['variable']==path and
                (not selected or r['nonlinear_response']['t1_results'][0]==selected[0] and
                    all(ref in selected for ref in r['nonlinear_response']['t1_results']))]
            if 'local_radius_fraction' in q.model_fields_set:
                row=rows[path];value=row['current_value']
                step=min((row['maximum']-row['minimum'])*q.local_radius_fraction,
                    value-row['minimum'],row['maximum']-value)
                import math
                found=[r for r in found if math.isclose(step,abs(parameter_value(
                    family_parameters(spec,verify_candidate(host,host.store.artifact(r['nonlinear_response']['t1_results'][1])['candidate']),path)[0],path)-value),rel_tol=1e-10)]
            if not found:
                from tools.research.nonlinear_capability import preparation_view
                preparation=preparation_view(host,candidate,paths=paths,step_fraction=q.local_radius_fraction)
                return feedback('needs_prerequisite','COMPARABLE_COMPLETED_BASELINE_MINUS_PLUS_T1_REQUIRED',
                    preparation=preparation,automatic_T1=False)
            if len(found)>1 and not selected:return feedback('needs_choice','MULTIPLE_COMPARABLE_T1_STENCILS',
                choices=[r['nonlinear_response'] for r in found])
            choices.extend(found)
        refs=[ref for r in choices for ref in r['nonlinear_response']['t1_results']]
        if selected and any(ref not in refs for ref in selected):return feedback('needs_choice','SELECTED_T1_SOURCES_NOT_IN_THE_REQUESTED_STENCIL')
        if len({r['nonlinear_response']['t1_results'][0]['artifact_id'] for r in choices})!=1:
            return feedback('needs_choice','M2_PATHS_REQUIRE_ONE_SHARED_MATCHED_BASELINE')
        if len(choices)==1:response=choices[0]['nonlinear_response']
        else:
            directions=[]
            for i,r in enumerate(choices):
                request=r['nonlinear_response'];path=request['variable'];refs=request['t1_results']
                base=host.store.artifact(refs[0]);minus=host.store.artifact(refs[1])
                a=family_parameters(spec,verify_candidate(host,base['candidate']),path)[0]
                b=family_parameters(spec,verify_candidate(host,minus['candidate']),path)[0]
                h=parameter_value(a,path)-parameter_value(b,path)
                directions.append(dict(direction_id=path+'/'+str(i),variables={path:1.},coordinate_unit=request['unit'],
                    coordinates=[0.,-h,h],t1_results=refs))
            response=dict(version='nonlinear_response_v2',directions=directions)
        method=T2;needed=1;compiled=dict(nonlinear_response=response)
    detail=view['methods'][method]
    if detail['planning_status'] in ('unauthorized','blocked','insufficient_budget','unsupported'):
        return feedback('blocked','ORIGINAL_M2_METHOD_ADMISSION_BLOCKED',missing=detail['missing'],method=method)
    if (q.requested_budget is not None and q.requested_budget<needed) or (view['remaining_evaluations'] is not None and view['remaining_evaluations']<needed):
        return feedback('blocked','SHARED_MATHEMATICAL_BUDGET_CANNOT_FIT',required_evaluations=needed)
    full=bind_selected_analysis_request(host,compiled,tool_use_id=tool_use_id,selection=(method,detail),scientific_question=payload)
    return dict(status='ready',method=method,request=full,required_evaluations=needed,scientific_execution_started=False,
        effect_scope='Conditional affine optimal capability sensitivity' if method==SENSITIVITY else
            'Saved matched finite-budget Native structural secants; fixed-control and reoptimized effects remain separate.',
        strict_optimal_value_gradient=False,automatic_T1=False,limitations=detail['limitations'])


def compile_conic(host,payload,*,tool_use_id):
    """B historical M2 inspect compiles to the existing registered Conic path."""
    from tools.research.optimal_capability import CONIC
    from tools.research.task_constraints import mathematical_method_view
    from tools.research.agent import bind_selected_analysis_request
    intent=completed_question_plan(host)
    detail=mathematical_method_view(host,intent['candidate'])['methods'].get(CONIC)
    if not detail or detail['planning_status'] in ('unauthorized','blocked','insufficient_budget','unsupported'):
        return dict(status='blocked',reason='ORIGINAL_CONIC_ADMISSION_REQUIRED',scientific_execution_started=False)
    full=bind_selected_analysis_request(host,dict(model_source='gvs',operating_point='standardized_initial_pretension'),
        tool_use_id=tool_use_id,selection=(CONIC,detail),scientific_question=payload)
    return dict(status='ready',method=CONIC,request=full,scientific_execution_started=False)
