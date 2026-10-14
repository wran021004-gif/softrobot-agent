"""Small mechanics adapter using the current core's evidence and shared budget."""
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import subprocess
import time
from tools.state_io import atomic_json, read, digest
from tools.platform_store import plain, zero


def source(host, reference):
    from tools.research.core import state
    if plain(reference) not in [*state(host).get('mechanics_results', []), *state(host).get('imported_mechanics_sources', [])]:
        raise ValueError('OWNED_CURRENT_STUDY_MECHANICS_RESULT_REQUIRED')
    value = host.store.artifact(reference)
    if value['operation'] != 'solve' or not value.get('candidate'):
        raise ValueError('MECHANICS_SOLVE_WITH_RETURNED_SCHEDULE_REQUIRED')
    return value


def handoff(host, reference, parameters=None, provenance=None):
    from tools.research.core import construct, state, update, save
    v = source(host, reference); c = v['candidate']; d = c['d']
    if not math.isfinite(d) or not -1.-1e-8 <= d <= 1.+1e-8:
        raise ValueError('RETURNED_STRUCTURE_OUTSIDE_AUTHORIZED_DOMAIN')
    d = min(1., max(-1., d))
    current=state(host)
    if current['spec'].get('nominal_source'):
        if not v.get('solved_candidate'):raise ValueError('EXACT_SOLVED_CONFIGURATION_BINDING_REQUIRED')
        solved=host.store.artifact(v['solved_candidate']);p=deepcopy(solved['parameters'])
        if parameters is not None:
            parameters=plain(parameters)
            for name,value in parameters.items():
                if name not in ('holding_tip_speed_weight','terminal_tip_speed_weight') and value!=p[name]:
                    raise ValueError('HANDOFF_STRUCTURE_MUST_MATCH_MECHANICS_SOURCE')
            p.update(parameters)
    else:p = dict(parameters or current['spec']['reference_parameters'])
    if not current['spec'].get('nominal_source') and parameters is not None and abs(p['d']-d) > 1e-10:
        raise ValueError('HANDOFF_STRUCTURE_MUST_MATCH_MECHANICS_SOURCE')
    if not current['spec'].get('nominal_source'):p['d'] = d
    candidate = construct(host, p, dict(origin='mechanics_handoff', mechanics_attempt=plain(reference)))
    relation = dict(candidate=candidate, mechanics_attempt=plain(reference),
        offline_trajectory=v['trajectory_reference'], structure=dict(legacy_d=d,lengths_m=[.16+.0055*d,.11-.0055*d]),
        solved_configuration=v.get('solved_configuration'),
        original_task_feasible=v.get('original_task_feasible',False), relaxed_nlp_feasible=v.get('relaxed_nlp_feasible',False),
        objective=v.get('objective_definition'), relaxation=v.get('original_task_gaps'),
        evaluation_mode='controller unselected; mathematical trajectory is evidence, not MuJoCo acceptance',
        exploratory=True, provenance=provenance)
    ref = save(host,relation,'mechanics_candidate_handoff')
    update(host,handoffs=[*state(host).get('handoffs',[]),ref])
    return dict(reference=ref,**relation)


def dispatch(host, operation, arguments, key):
    from tools.research import core as core
    core.guard(host,True); s = core.state(host); b = s['spec']['budgets']
    reserve = s['spec']['mechanics_allowances'][operation+'_s']; counter = 'offline_nlp' if operation=='solve' else None if operation=='inspect' else 'bdf_replays'
    validation=s.get('validation_reservation')
    source_ref=plain(arguments).get('source') if operation in ('integrate','inspect') else plain(arguments) if operation=='replay' else None
    uses_validation=bool(validation and source_ref==validation.get('source') and counter=='bdf_replays')
    protected_job=int(bool(validation) and not uses_validation and counter=='bdf_replays')
    if counter and s.get(counter,0)+protected_job >= b[counter]: raise ValueError('MECHANICS_RESOURCE_CEILING: '+counter)
    numerical_available=b['numerical_s']-s['numerical_s']-s['numerical_reserved_s']
    if uses_validation:numerical_available+=validation['seconds']
    available = min(numerical_available,s['cutoff_unix']-time.time(),host.store.remaining()['remaining']['wall_s'])
    protection=core.repetition_reserve(s)*core.allowance(s)
    if core.enabled(s['spec'],'rl'):
        protection=core.repetition_reserve(s)*s['spec'].get('rl_evaluation_allowance_s',150.)
    protection+=b.get('delivery_numerical_s',0.)
    downstream=s['spec'].get('downstream_reserve',{})
    if downstream:
        protection=max(protection,max(0,downstream['passing_executions']-sum(bool((host.store.artifact(r).get('acceptance') or {}).get('accepted')) for r in s['results']))*core.allowance(s))
        future_jobs=max(0,downstream['fixed_verifications']-s.get('fixed_validation_jobs',0))
        if operation in ('integrate','inspect') and not uses_validation:
            protection+=future_jobs*s['spec']['mechanics_allowances']['replay_s']
        if counter=='bdf_replays' and s.get(counter,0)+1+max(0,future_jobs-int(uses_validation))>b[counter]:
            raise ValueError('DOWNSTREAM_FIXED_VERIFICATION_JOBS_PROTECTED')
        if operation=='solve':
            lo,hi=plain(arguments)['design_bounds']
            if lo!=hi:
                from tools.numerical_repair import length_admission
                if not length_admission(host)['passed']:raise ValueError('LENGTH_DESIGN_REQUIRES_NEW_OFFLINE_AND_TWO_PASSING_EXECUTIONS')
                if s.get('length_design_started'):raise ValueError('ONE_CONDITIONAL_LENGTH_ATTEMPT_MAXIMUM')
            elif s.get('fixed_offline_attempts',0)>=2:raise ValueError('TWO_FIXED_OFFLINE_ATTEMPTS_MAXIMUM')
    if operation=='solve' and s['spec'].get('mode')=='engineering_numerical':
        verification=s['spec']['mechanics_allowances']['replay_s']
        if s.get('bdf_replays',0)+1>b['bdf_replays'] or available < reserve+verification+protection:
            raise ValueError('REFINEMENT_AND_INDEPENDENT_INTEGRATION_RESERVE_CANNOT_FIT')
    if available < reserve+protection: raise ValueError('MECHANICS_AND_REPETITION_RESERVE_CANNOT_FIT')
    selected_candidate=None
    if s['spec'].get('nominal_source'):
        selected_candidate=plain(arguments).get('design_candidate') if operation=='solve' else source(host,source_ref).get('solved_candidate')
        if not selected_candidate:raise ValueError('LEGACY_MECHANICS_REQUIRES_EXACT_DESIGN_CANDIDATE')
        cfg=deepcopy(core.verify_candidate(host,selected_candidate)['configuration'])
        legacy_compatible(cfg,s['nominal_configuration'])
        if operation=='solve':
            a=plain(arguments);length=next(c['length_m'] for c in cfg['robot']['structure']['data']['components'] if c['id']=='near')
            if abs(length-(.16+.0055*a['design_initial']))>1e-10:raise ValueError('LEGACY_INITIAL_MUST_MATCH_REQUESTED_CANDIDATE')
    else:cfg,_ = core.configuration_for(host,s['spec']['reference_parameters'],host.run_id)
    request = dict(study_id=host.run_id,store_root=str(host.store.root),request_id=key+'-mechanics',
        operation=operation,configuration=cfg,implementation=s['freeze'],science_hashes=s['profile']['science_hashes'])
    if operation=='solve':
        request['arguments']=plain(arguments)
        request['arguments'].pop('design_candidate',None)
        request['design_candidate']=selected_candidate
        request['offline_solver_s']=s['spec'].get('offline_solver_s',570.)
        request['offline_stopping_policy']=s['spec'].get('offline_stopping_policy','historical_timed_v1')
        if request['arguments'].get('source_candidate'):
            request['saved_tensions']=source(host,request['arguments']['source_candidate'])['candidate']['tensions_n']
    else:
        parameters=plain(arguments) if operation in ('integrate','inspect') else {}
        v=source(host,parameters['source'] if parameters else arguments); c=deepcopy(v['candidate'])
        import numpy as np
        u=np.asarray(c['tensions_n']); clipped=np.clip(u,0.,8.)
        if u.shape!=(35,6) or not np.isfinite(u).all() or np.max(abs(u-clipped))>1e-5:
            raise ValueError('FINITE_BOUNDED_RETURNED_SCHEDULE_REQUIRED')
        if operation in ('integrate','inspect'):
            c.update(frozen_input_identity=digest(c['tensions_n']),input_bound_tolerance_n=1e-5)
        else:c.update(tensions_n=clipped.tolist(),replay_input_clip_max_n=float(np.max(abs(u-clipped))))
        request.update(candidate=c,source_mechanics=parameters.get('source',plain(arguments)),diagnostic_parameters=parameters)
    old=host.store.lookup(host.run_id,request['request_id'])
    if old:
        if old['request_hash']!=digest(request):raise ValueError('NUMERICAL_OPERATION_ID_COLLISION')
        if not old['receipt']:raise ValueError('UNKNOWN_NUMERICAL_OUTCOME_RECOVER_NO_REPEAT')
        reference=json.loads(old['receipt'])['output'];value=host.store.artifact(reference)
        return dict(reference=reference,status=value.get('status'),operation=operation,
            operation_reuse=dict(additional_numerical_s=0.,additional_scientific_executions=0),
            original_charged_numerical_s=value['charged_numerical_s'])
    def charge(db):
        current=host.store.session(host.run_id,db)['state'];core.charge_start(current)
        if counter:current[counter]=current.get(counter,0)+1
        if downstream and operation=='solve' and request['arguments']['design_bounds'][0]==request['arguments']['design_bounds'][1]:
            current['fixed_offline_attempts']=current.get('fixed_offline_attempts',0)+1
        elif downstream and operation=='solve':current['length_design_started']=True
        if downstream and uses_validation:
            current['fixed_validation_jobs']=current.get('fixed_validation_jobs',0)+1
        if uses_validation:
            current['numerical_reserved_s']-=validation['seconds'];current['validation_reservation']=None
        if operation=='solve' and s['spec'].get('mode')=='engineering_numerical':
            current['validation_reservation']=dict(seconds=verification,jobs=1,source=None)
            current['numerical_reserved_s']+=verification
        current['numerical_reserved_s']+=reserve
        host.store.update_state(db,host.run_id,current)
    row,_=host.store.reserve(host.run_id,request['request_id'],digest(request),host.actor,
        {**zero(),'wall_s':reserve},kind='mechanics',guard=charge)
    folder=host.store.root/'mechanics'/row['execution_id']; folder.mkdir(parents=True,exist_ok=True)
    inp,out,progress=folder/'input.json',folder/'output.json',folder/'progress.json'
    request['progress']=str(progress); atomic_json(inp,request)
    pending=dict(kind='mechanics',worker_request_id=request['request_id'],operation_key=key,operation=operation,
        original_request=request,
        input=str(inp),output=str(out),progress=str(progress),reserved_s=reserve,started_unix=time.time())
    core.update(host,pending=pending)
    return run_and_settle(host,row,request,pending)


def run_and_settle(host,row,request,pending,recovery=False):
    from tools.research import core as core
    reserve=pending['reserved_s']; started=time.perf_counter()
    env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    log=b''; out=Path(pending['output']); progress=Path(pending['progress'])
    def worker(req,seconds):
        inp=Path(pending['input']); atomic_json(inp,req)
        return subprocess.run([str(core.PYTHON),'-m','tools.research.mechanics_worker',str(inp),str(out)],
            cwd=core.ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=seconds)
    if recovery:
        if out.exists(): value=read(out)
        elif progress.exists() and read(progress).get('phase')=='solver_returned':
            process=worker(dict(request,operation='recover'),reserve); log=process.stdout;value=read(out)
        else: raise ValueError('UNKNOWN_MECHANICS_OUTCOME_RETAINS_RESERVATION; NO_SECOND_SOLVE')
    else:
        try:
            process=worker(request,reserve);log=process.stdout
            value=read(out) if out.exists() else dict(status='worker_no_output',returncode=process.returncode)
        except subprocess.TimeoutExpired as exc:
            log=exc.stdout or b'';value=dict(status='known_killed_waited_timeout',timeout_s=reserve)
    checkpoint=read(progress) if progress.exists() else None
    checkpoint_ref=core.save(host,checkpoint,'mechanics_checkpoint') if checkpoint else None
    if checkpoint and checkpoint.get('phase')=='solver_returned' and not value.get('candidate'):
        failure=deepcopy(value);remaining=reserve-(time.perf_counter()-started)
        if remaining>0:
            try:
                process=worker(dict(request,operation='recover'),remaining);log+=process.stdout;value=read(out)
            except subprocess.TimeoutExpired: value=dict(status='checkpoint_packaging_timeout')
        value.update(original_packaging_failure=failure,checkpoint_preserved=True)
    elapsed=time.perf_counter()-started
    # Recovery of a previously unknown outcome charges its original reservation,
    # plus measured packaging time; counters and clocks are never reset.
    charged=elapsed+(reserve if recovery else 0.)
    trajectory=core.save(host,value['candidate'],'offline_state_tension_trajectory') if value.get('candidate') else None
    if value.get('candidate') and core.state(host)['spec'].get('nominal_source'):
        original=host.store.artifact(request['design_candidate']);params=deepcopy(original['parameters']);d=value['candidate']['d']
        params.update(near_length_m=.16+.0055*d,distal1_length_m=.11-.0055*d)
        solved=core.construct(host,params,dict(origin='legacy_offline_solved_configuration',request_id=row['request_id']))
        value.update(solved_candidate=solved,solved_configuration=host.store.artifact(solved)['configuration_reference'])
    value.update(operation=request['operation'],execution_id=row['execution_id'],owning_study=host.run_id,
        original_request=core.save(host,request,'mechanics_original_request'),source_mechanics=request.get('source_mechanics'),
        checkpoint_reference=checkpoint_ref,trajectory_reference=trajectory,
        log_reference=core.save(host,dict(text=log.decode('utf8',errors='replace')),'mechanics_worker_log'),
        implementation=request['implementation'],charged_numerical_s=charged,process_elapsed_s=elapsed,
        physical_validation='not_run; BDF is independent integration of the model, not physical validation',
        objective_definition=request.get('arguments'), variable_order=(checkpoint or {}).get('variable_order'))
    ref=core.save(host,value,'mechanics_'+request['operation'])
    with host.store.transaction() as db:
        current=host.store.session(host.run_id,db)['state']
        current['numerical_s']+=charged;current['numerical_reserved_s']-=reserve;current['pending']=None
        current['mechanics_results']=[*current.get('mechanics_results',[]),ref]
        if request['operation']=='solve' and current.get('validation_reservation'):
            if value.get('candidate'):current['validation_reservation']['source']=ref
            else:
                current['numerical_reserved_s']-=current['validation_reservation']['seconds'];current['validation_reservation']=None
        host.store.update_state(db,host.run_id,current)
        host.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=host.actor,
            tool_id='research.core_mechanics',tool_version='1.0.0',execution_status='completed',charged=zero()),value,elapsed=charged,db=db)
    result=dict(reference=ref,**{k:value.get(k) for k in ('status','operation','execution_id','owning_study','termination_reason',
        'trajectory_reference','checkpoint_reference','relaxed_nlp_feasible','original_task_feasible','hard_max_normalized_violation',
        'trajectory_metrics','original_task_gaps','charged_numerical_s','costs_s','replay','physical_validation')})
    from tools.research.numerics import compact_numerics
    result['numerical_diagnostics']=compact_numerics(value)
    if value.get('candidate'):
        try:result['handoff']=handoff(host,ref)
        except ValueError as exc: result['handoff_failure']=str(exc)
    return result


def recover(host):
    from tools.research import core as core
    p=core.state(host)['pending'];row=host.store.lookup(host.run_id,p['worker_request_id'])
    return run_and_settle(host,row,p['original_request'],p,recovery=True)


def legacy_configuration_for(host, parameters, owner):
    from tools.design_optimization import resolved_input
    from schemas.design_optimization import DesignOptimizationProblem
    from tools.research.core import state, ROOT, enabled
    from types import SimpleNamespace
    s = state(host); p = SimpleNamespace(**{**dict(d=0.,holding_tip_speed_weight=.1,terminal_tip_speed_weight=.1),**plain(parameters)}); base = s['base_configuration']
    problem = DesignOptimizationProblem.model_validate(read(ROOT/'examples/casadi_codesign/case_A.json')['physical_source'])
    data = plain(problem); data['task'] = deepcopy(base['task'])
    data['execution']['recipe'] = deepcopy(s['profile']['recipe'])
    data['execution']['settling'] = deepcopy(base['policy']['controller']['parameters']['data']['settling'])
    problem = DesignOptimizationProblem.model_validate(data)
    fixed = deepcopy(base['robot']['structure']['data']['metadata']['recipe'])
    fixed.update(lengths_m=[.16+.0055*p.d,.11-.0055*p.d],
        holding_tip_speed_weight=p.holding_tip_speed_weight,terminal_tip_speed_weight=p.terminal_tip_speed_weight)
    cfg = resolved_input(problem, fixed, owner, deepcopy(base['policy']))
    if enabled(s['spec'],'rl'):
        # generated_serial's existing GVS source already declares ideal tension.
        # Keep that verified declaration; no actuator rewriting after construction.
        if s['spec']['tension_execution_mode']!='ideal_tension': raise ValueError('IDEAL_TENSION_STUDY_REQUIRED')
    # Freeze every binding not regenerated by the declared length coordinate.
    for k in ('backend','dynamics_model'): cfg['policy'][k] = deepcopy(base['policy'][k])
    return cfg, fixed


def legacy_compatible(configuration,nominal):
    """The legacy symbolic coordinate represents only its .27m length family."""
    def physical(cfg):
        robot=deepcopy(cfg['robot']['structure']['data']);robot.pop('metadata',None);robot.pop('id',None)
        parts=[c for c in robot['components'] if c['kind']=='flexible_segment']
        if [c['id'] for c in parts]!=['near','distal1']:raise ValueError('LEGACY_SEGMENT_IDENTITIES_UNSUPPORTED')
        lengths=[c['length_m'] for c in parts]
        for part,length in zip(parts,[.16,.11]):part['length_m']=length
        return robot,lengths
    robot,lengths=physical(configuration);base,_=physical(nominal)
    d=(lengths[0]-.16)/.0055
    if robot!=base or not -1.-1e-10<=d<=1.+1e-10 or abs(lengths[1]-(.11-.0055*d))>1e-10:
        raise ValueError('LEGACY_CODESIGN_UNAVAILABLE_FOR_THIS_CONFIGURATION; retain exact candidate for analysis, direct RL or NMPC')
    return d




# Explicit historical co-design adapter contracts; current native design never uses d.
from pydantic import Field, FiniteFloat, model_validator
from schemas.common import Contract
from schemas.research_core import Plan as CurrentPlan
from schemas.platform import EvidenceRef
from extensions.tendon_family.generated_serial import SUPPORTED_NUMERIC


class LegacyParameters(Contract):
    d: FiniteFloat = Field(default=0.,ge=-1,le=1)
    holding_tip_speed_weight: FiniteFloat = Field(default=.1,ge=SUPPORTED_NUMERIC['holding_tip_speed_weight'][0],le=SUPPORTED_NUMERIC['holding_tip_speed_weight'][1])
    terminal_tip_speed_weight: FiniteFloat = Field(default=.1,ge=SUPPORTED_NUMERIC['terminal_tip_speed_weight'][0],le=SUPPORTED_NUMERIC['terminal_tip_speed_weight'][1])


class LegacySearch(Contract):
    variables: list[str] = Field(min_length=1)
    bounds: dict[str,tuple[FiniteFloat,FiniteFloat]]
    fixed: LegacyParameters = Field(default_factory=LegacyParameters)
    max_evaluations: int = Field(default=3,ge=1,le=8,strict=True)
    step: FiniteFloat = Field(default=.25,gt=0,le=.5)
    ranking: str = 'feasible_then_max_normalized_violation_then_sum_v1'
    mechanics_source: EvidenceRef | None = None

    @model_validator(mode='after')
    def domain(self):
        if len(set(self.variables))!=len(self.variables) or set(self.bounds)!=set(self.variables):raise ValueError('LEGACY_SEARCH_BOUNDS')
        for name,(a,b) in self.bounds.items():
            domain=(-1.,1.) if name=='d' else SUPPORTED_NUMERIC.get(name)
            if domain is None or not domain[0]<=a<b<=domain[1] or not a<=getattr(self.fixed,name)<=b:raise ValueError('LEGACY_SEARCH_DOMAIN')
        return self


class LegacyPlan(CurrentPlan):
    parameters: LegacyParameters | None = None
    search: LegacySearch | None = None


def legacy_search_problem(host, search, admitted):
    from tools.research import core
    ROOT=core.ROOT
    from schemas.design_optimization import DesignOptimizationProblem
    s=core.state(host); base=s['base_configuration']; q=LegacySearch.model_validate(search)
    p=read(ROOT/'examples/casadi_codesign/case_A.json')['physical_source']
    p['study_id']=host.run_id; p['task']=deepcopy(base['task'])
    p['execution']['recipe']=deepcopy(s['profile']['recipe'])
    p['execution']['settling']=deepcopy(base['policy']['controller']['parameters']['data']['settling'])
    fixed=deepcopy(base['robot']['structure']['data']['metadata']['recipe'])
    fixed.pop('lengths_m'); fixed.pop('family',None); fixed.update({k:v for k,v in plain(q.fixed).items() if k!='d'})
    p['variables']={k:dict(kind='fixed',value=v) for k,v in fixed.items()}
    for k in q.variables:
        if k!='d': p['variables'][k]=dict(kind='continuous',bounds=list(q.bounds[k]),initial=getattr(q.fixed,k))
    free='d' in q.variables
    # The public +/-5% bound refers to the physical nominal design, not the
    # optimizer's chosen initial point. Use the closest nominal feasible point
    # for allocation validation; pass the requested initialization separately.
    baseline_d=min(max(0.,q.bounds['d'][0]),q.bounds['d'][1]) if free else q.fixed.d
    lengths=[.16+.0055*baseline_d,.11-.0055*baseline_d]
    bounds=[[.16+.0055*q.bounds['d'][0],.16+.0055*q.bounds['d'][1]],
        [.11-.0055*q.bounds['d'][1],.11-.0055*q.bounds['d'][0]]] if free else [[v,v] for v in lengths]
    p['lengths']=dict(free=free,total_flexible_length_m=.27,baseline_by_count={'2':lengths},bounds_by_count={'2':bounds})
    p['fixed_tendon_count']=6; p['fixed_actuator_count']=6
    p['budget']=dict(max_evaluations=admitted,wall_s=admitted*core.allowance(s))
    p['objective']=dict(ranking=q.ranking,accepted_resource_preference='none')
    p['method']=dict(name='hierarchical_coordinate_v1_1',step=q.step,initial_structures=[],stop_on_acceptance=False)
    return DesignOptimizationProblem.model_validate(p)


def legacy_run_search(host, query, key):
    from tools.research import core
    from tools.design_optimization import solve, continuous_space, structures
    core.guard(host,True); q=LegacySearch.model_validate(query); admission=core.capacity(host,q.max_evaluations)
    if q.mechanics_source:
        from tools.research.mechanics import handoff
        if 'd' in q.variables: raise ValueError('MECHANICS_CONTROL_SEARCH_REQUIRES_FIXED_STRUCTURE')
        handoff(host,q.mechanics_source,plain(q.fixed),dict(operation_key=key,origin='control_search'))
    if not admission['admitted']: return dict(status='budget_limited',admission=admission,evaluated=[])
    problem=legacy_search_problem(host,q,admission['admitted']); s=core.state(host)
    if s['searches'].get(key):
        from schemas.design_optimization import DesignOptimizationProblem
        problem=DesignOptimizationProblem.model_validate(s['searches'][key]['problem'])
    def evaluator(problem,values,proposal_id):
        if core.capacity(host,1)['admitted']<1: return dict(status='shared_budget_exhausted',evidence={})
        params=dict(d=(values['lengths_m'][0]-.16)/.0055,**{k:values[k] for k in ('holding_tip_speed_weight','terminal_tip_speed_weight')})
        ref=core.construct(host,params,dict(origin='mathematical_search',plan_key=key,proposal_id=proposal_id))
        if q.mechanics_source:
            handoff(host,q.mechanics_source,params,dict(operation_key=key,proposal_id=proposal_id))
        c=core.verify_candidate(host,ref)
        completed=[host.store.artifact(r) for r in core.state(host)['results']]
        old=next((r for r in completed if r['operation_key']==key+':'+proposal_id),None)
        if old is None:
            feedback=core.execute(host,ref,key+':'+proposal_id,role='search')
            if feedback['status']!='evaluated': return dict(status=feedback['status'],evidence=feedback)
            old=host.store.artifact(feedback['reference'])
        execution_ref=next(r for r in core.state(host)['results'] if host.store.artifact(r)['operation_key']==key+':'+proposal_id)
        return dict(status=old['status'],acceptance=old['acceptance'],evidence=dict(result=execution_ref,execution_id=old['execution_id']),
            configuration=c['configuration'],candidate_id=c['candidate_id'],scientific_identity=c['identity'])
    def checkpoint(value):
        searches=core.state(host)['searches']; searches[key]=deepcopy(value); core.update(host,searches=searches)
        return core.save(host,value,'search_checkpoint')
    initial_latents=None
    if 'd' in q.variables:
        structure=structures(problem)[0];allocation,latent=continuous_space(problem,structure)
        latent.update(allocation.encode([.16+.0055*q.fixed.d,.11-.0055*q.fixed.d]))
        initial_latents={digest(structure):latent}
    result=plain(solve(problem,evaluator=evaluator,state=s['searches'].get(key),save_state=checkpoint,
        evaluation_profile=s['profile'],initial_latents=initial_latents))
    explored={k:sorted({r['resolved']['parameters'][k] for r in result['evaluated']}) for k in q.variables if k!='d'}
    if 'd' in q.variables: explored['d']=sorted({(r['resolved']['parameters']['lengths_m'][0]-.16)/.0055 for r in result['evaluated']})
    attempted=[dict(reference=r,parameters=host.store.artifact(host.store.artifact(r)['candidate'])['parameters'],
        **core.compact_result(host.store.artifact(r))) for r in core.state(host)['results']
        if host.store.artifact(r)['operation_key'].startswith(key+':')]
    return dict(result=result,admission=admission,actually_explored=explored,attempted_executions=attempted,
        failed_or_incomplete_executions=[r['reference'] for r in attempted if r['status']!='evaluated' or not (r['acceptance'] or {}).get('accepted')],
        requested_variables=q.variables, fixed_parameters=plain(q.fixed), mechanics_source=plain(q.mechanics_source),
        distinct_configurations=len({r['scientific_identity'] for r in result['evaluated']}),
        not_explored=[k for k,v in explored.items() if len(v)<2],
        batch_shrunk=admission['admitted']<q.max_evaluations)
