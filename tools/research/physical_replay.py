"""One candidate-bound fixed-tension MuJoCo rollout and existing task settlement."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import time

import numpy as np

from schemas.platform import BackendResult, Payload, Signal, SessionInput
from tools.platform_store import plain, zero, Store
from tools.state_io import atomic_json, digest, read
from tools.research.state import state, update, save, guard
from tools.research.design import verify_candidate


def numerically_verified_source(value):
    """Keep legacy witness meaning; explicitly version complete failing controls."""
    if value.get('source_kind')=='independently_integrated_control_v1':
        proof=value['integration_verification'];trajectory=value['trajectory']
        return (proof['complete'] and proof['maximum_root_residual_inf']<1e-9 and
            proof['root_count']==len(trajectory['tensions_n'])*trajectory['integration_substeps'])
    proof=value.get('posthoc_verification',{})
    return (value.get('source_kind')=='verified_mathematical_trajectory' and
        proof.get('checks',{}).get('repaired_verification_passed',False) and
        proof.get('original_task_satisfied') is not False)


def explicit_control_source(value):
    """An executable schedule carries no mathematical feasibility assertion."""
    return (value.get('source_kind')=='explicit_control_schedule_v1'
        and value.get('task_acceptance')=='unmeasured'
        and bool(value.get('provenance')))


def schedule_identity(configuration, trajectory):
    """Exact executed inputs plus physical/task binding, independent of provenance."""
    bound={k:trajectory[k] for k in ('times_s','tensions_n','tendon_order','task_identity','model_identity','design_identity')}
    # Adding a zero correction turns -0.0 into +0.0; this is the same physical input.
    bound['tensions_n']=[[0. if u==0 else u for u in row] for row in trajectory['tensions_n']]
    return digest(dict(robot=configuration['robot'],task=configuration['task'],seed=configuration['seed'],
        physics={k:configuration['policy'][k] for k in ('backend','discretization','dynamics_model')},
        trajectory=bound))


def evaluate_schedule(host, candidate, source, plan_factory, *, origin='engineering'):
    """Reuse completed Store results, including settlement before a driver crash.

    There is no second cache or budget: the Store owns durable receipts and
    cumulative costs. An unfinished request must be recovered, never relaunched.
    """
    from tools.research import core
    cfg=verify_candidate(host,candidate)['configuration']
    binding(cfg,source['trajectory'])
    identity=schedule_identity(cfg,source['trajectory'])
    for ref in state(host).get('physical_replays',[]):
        result=host.store.artifact(ref);previous=host.store.artifact(result['source_reference'])
        prior_cfg=host.store.artifact(result['candidate'])['configuration']
        if schedule_identity(prior_cfg,previous['trajectory'])==identity:
            return dict(reference=ref,**result),True
    if host.store.remaining()['remaining']['backend_solves']<1:
        raise ValueError('PHYSICAL_REPLAY_LAUNCH_BUDGET_EXHAUSTED')
    source_ref=save(host,source,'bound_applied_control_schedule')
    result=core.dispatch(host,plan_factory('physical_replay',physical_replay=dict(candidate=candidate,source=source_ref)),
        'schedule-'+identity,origin=origin)['result']
    return result,False


def model_context(configuration):
    from extensions.tendon_family.sorosim_control import checked_control
    from extensions.tendon_family.sorosim_spec import SorosimModel
    from extensions.tendon_family.backends import physics_for
    from extensions.tendon_family.scene import assemble

    inp=SessionInput.model_validate(configuration)
    if inp.policy.controller.extension_id=='controller.gvs_nmpc':
        from extensions.tendon_family.gvs_basis import resolve_basis
        physics=physics_for(inp);scene=assemble(inp,physics)
        # Use the existing physical execution identity, never the affine model hash.
        spec=dict(identity=scene['experiment_spec']['dynamics_model_identity'],design_identity=physics['design_identity'],
            coordinate_order=list(resolve_basis(inp.robot.structure.data,inp.policy.controller.parameters.data['recipe']['basis']).coordinate_order),
            tendon_order=[t['entity'] for t in physics['tendons']])
        return inp,physics,scene,spec
    control=checked_control(inp)
    spec=SorosimModel(dict(basis=control.recipe.basis,
        gauss_per_interval=control.solver.gauss_per_interval)).convert(
        inp.robot.structure.data,inp.policy.discretization.data,inp.task.environment.data,solver=control.solver)
    physics=physics_for(inp);scene=assemble(inp,physics)
    return inp,physics,scene,spec


def initialize_schedule(configuration, source, parent):
    """Explicit same-channel initialization for a new design; no acceptance transfer."""
    from copy import deepcopy
    inp,physics,scene,spec=model_context(configuration)
    tr=deepcopy(source['trajectory']);order=[t['entity'] for t in physics['tendons']]
    if tr['tendon_order']!=order:raise ValueError('UNSUPPORTED_CROSS_TOPOLOGY_CONTROL_INITIALIZATION')
    tr.update(model_identity=spec['identity'],design_identity=spec['design_identity'],task_identity=digest(plain(inp.task)))
    binding(configuration,tr)
    return dict(source_kind='explicit_control_schedule_v1',task_acceptance='unmeasured',trajectory=tr,
        provenance=dict(control_initialization='same_channels_new_candidate_binding_v1',parent=plain(parent),
            inherited_acceptance=False,source_provenance=source['provenance']))


def seed_control(host, request, operation_key=None, plan=None):
    """Candidate-owned bounded inputs; explicit ZOH time/channel transfer or pretension."""
    started=time.perf_counter()
    try:
        if request.method=='capability_sequence':return capability_seed(host,request,operation_key)
        if request.method!='baseline':return guided_seed(host,request,operation_key,plan)
        return _seed_control(host,request,operation_key)
    finally:
        elapsed=time.perf_counter()-started;s=state(host)
        update(host,numerical_s=s['numerical_s']+elapsed,
            control_initialization_s=s.get('control_initialization_s',0.)+elapsed)


def _seed_control(host,request,operation_key):
    cfg=verify_candidate(host,request.candidate)['configuration']
    inp,physics,scene,spec=model_context(cfg)
    period=inp.task.timing.control_period_s
    count=round(inp.task.timing.duration_s/period)
    order=[t['entity'] for t in physics['tendons']]
    tendons={t['id']:t for t in cfg['robot']['structure']['data']['tendons']}
    inputs=np.tile([tendons[t]['pretension_n'] for t in order],(count,1))
    provenance=dict(control_initialization='bounded_candidate_control_v1',inherited_acceptance=False,
        parent=plain(request.parent),source=plain(request.source),channel_map=request.channel_map,operation_key=operation_key,
        time_rule='zero-order hold; hold last input beyond source horizon; new channels use candidate pretension')
    if request.source:
        parent=host.store.artifact(request.parent)
        source=host.store.artifact(request.source)
        if source.get('execution_id') and not source.get('trajectory'):
            from tools.research.rl import measured_nmpc_trajectory
            if plain(request.parent)!=plain(request.candidate) or source.get('candidate')!=plain(request.candidate) or request.channel_map is not None:
                raise ValueError('EXACT_NMPC_CANDIDATE_WITHOUT_CHANNEL_MAPPING_REQUIRED')
            trajectory,origin=measured_nmpc_trajectory(host,request.source)
            source=dict(trajectory=trajectory)
            provenance.update(source_kind='measured_nmpc_execution_v1',**origin)
        binding(parent['configuration'],source['trajectory'])
        old=source['trajectory'];old_order=old['tendon_order']
        mapping=request.channel_map
        if mapping is None:
            # Unequal topology gets a new baseline, never an implicit channel copy.
            mapping=dict(zip(order,old_order)) if order==old_order else {}
        if set(mapping)-set(order) or set(mapping.values())-set(old_order):
            raise ValueError('CONTROL_CHANNEL_MAP_OUTSIDE_CANDIDATES')
        indices=np.clip(np.searchsorted(old['times_s'],np.arange(count)*period+1e-12,side='right')-1,
            0,len(old['tensions_n'])-1)
        for name,original in mapping.items():
            inputs[:,order.index(name)]=np.asarray(old['tensions_n'])[indices,old_order.index(original)]
        provenance['effective_channel_map']=mapping
    elif request.tensions_n is not None:
        inputs=np.asarray(request.tensions_n,dtype=float)
        if inputs.shape==(1,len(order)):inputs=np.repeat(inputs,count,axis=0)
    trajectory=dict(times_s=[i*period for i in range(count+1)],tensions_n=inputs.tolist(),
        tendon_order=order,model_identity=spec['identity'],design_identity=spec['design_identity'],
        task_identity=digest(plain(inp.task)))
    binding(cfg,trajectory)  # Reject bounds, dimensions and ineffective execution modes.
    source=save(host,dict(source_kind='explicit_control_schedule_v1',task_acceptance='unmeasured',
        trajectory=trajectory,provenance=provenance),'candidate_control_initialization')
    entry=dict(candidate=plain(request.candidate),source=source,task_acceptance='unmeasured')
    update(host,control_initializations=[*state(host).get('control_initializations',[]),entry])
    return entry


def capability_seed(host,request,operation_key=None):
    """Registered SOCP witness -> existing ZOH schedule; no solve or physical launch."""
    from schemas.platform_analysis import EndpointLinearizedModel, TaskAnalysisProtocol, TaskAnalysisRequirement
    from extensions.math_analysis.trajectory import prepare_trajectory, verify_witness
    from tools.research.optimal_capability import CONIC
    from tools.research.task_constraints import describe_analysis_requirements
    s=state(host);reference=plain(request.response_evidence)
    if reference not in s.get('analysis_results',[]):raise ValueError('REGISTERED_CURRENT_ANALYSIS_REQUIRED')
    candidate=verify_candidate(host,request.candidate);cfg=candidate['configuration'];raw=host.store.artifact(reference)
    tr=raw.get('trajectory') or {}
    if (raw.get('candidate')!=plain(request.candidate) or raw.get('implementation')!=s['freeze']
            or raw.get('status')!='computed' or raw.get('operation')!='task_capability'
            or tr.get('method_version')!=CONIC or raw.get('optimal_sensitivity')
            or raw.get('requested_operation',{}).get('capability_method')!=CONIC):
        raise ValueError('CURRENT_CANDIDATE_FROZEN_SOCP_RESULT_REQUIRED')
    m=EndpointLinearizedModel.model_validate(raw['model']);p=TaskAnalysisProtocol.model_validate(raw['protocol'])
    req=TaskAnalysisRequirement.model_validate(raw['task_analysis']);outer=raw['binding']
    inp,physics,scene,execution=model_context(cfg)
    expected=dict(candidate=plain(request.candidate),candidate_id=candidate['candidate_id'],
        effective_configuration_identity=digest(cfg),task_identity=digest(cfg['task']),
        source_identity=candidate['source_identity'],tendon_order=execution['tendon_order'],
        coordinate_order=execution['coordinate_order'])
    if (any(outer.get(k)!=v or m.binding.get(k)!=v for k,v in expected.items())
            or plain(p)!=s['spec']['analysis_protocol'] or m.protocol_identity!=digest(plain(p))
            or m.binding.get('analysis_protocol_identity')!=m.protocol_identity
            or plain(req)!=plain(describe_analysis_requirements(inp,outer))
            or raw['operating_point']!=m.operating_point
            or raw['requested_operation'].get('operating_point') not in ('controller_start_input','standardized_initial_pretension')
            or any(v.units!='N' or v.dimension!=1 for v in m.input_definition)
            or [v.entity for v in m.input_definition]!=execution['tendon_order']):
        raise ValueError('SOCP_MODEL_TASK_INPUT_OR_OPERATING_POINT_MISMATCH')
    provenance=tr.get('provenance',{})
    if any(provenance.get(k)!=digest(v) for k,v in (
            ('model_identity',plain(m)),('requirement_identity',plain(req)),('protocol_identity',plain(p)))):
        raise ValueError('SOCP_NUMERICAL_PROVENANCE_MISMATCH')
    info=dict(coverage=[])
    scope,dynamics,initial,rows,lower,upper,_=prepare_trajectory(m,req,p,info,tr.get('initial_delta_state'))
    timing=inp.task.timing;count=round(timing.duration_s/timing.control_period_s)
    delta=np.asarray(tr.get('delta_input_n'),dtype=float);applied=np.asarray(tr.get('applied_input_n'),dtype=float)
    if (scope['start_time_s']!=0 or scope['step_count']!=count or p.period_s!=timing.control_period_s
            or p.duration_s!=timing.duration_s or tr.get('horizon')!=json.loads(json.dumps(scope))
            or np.any(initial!=0) or delta.shape!=(count,len(m.u0)) or applied.shape!=delta.shape
            or not np.isfinite(delta).all() or not np.isfinite(applied).all()
            or not np.allclose(applied,delta+np.asarray(m.u0),rtol=0,atol=1e-12)
            or np.any(delta.ravel()<lower) or np.any(delta.ravel()>upper)):
        raise ValueError('COMPLETE_ALIGNED_FINITE_BOUNDED_SOCP_SEQUENCE_REQUIRED')
    replay=verify_witness(m,dynamics,initial,delta,rows,scope,p.endpoint_check_atol)
    if (not tr.get('replay',{}).get('numerically_valid') or not replay.get('finite') or not rows
            or len(replay['records'])!=len(rows) or replay['max_prediction_replay_error']>p.endpoint_check_atol):
        raise ValueError('INDEPENDENT_SOCP_REPLAY_REQUIRED')
    trajectory=dict(times_s=[i*timing.control_period_s for i in range(count+1)],tensions_n=applied.tolist(),
        tendon_order=execution['tendon_order'],model_identity=execution['identity'],
        design_identity=execution['design_identity'],task_identity=digest(cfg['task']))
    binding(cfg,trajectory)
    source=save(host,dict(source_kind='explicit_control_schedule_v1',task_acceptance='unmeasured',inherited_acceptance=False,
        trajectory=trajectory,provenance=dict(control_initialization='capability_sequence_v1',operation_key=operation_key,
            mathematical_result=reference,local_model_identity=digest(plain(m)),
            mathematical_model_identity=m.binding['model_identity'],execution_model_identity=execution['identity'],
            input_identity=digest(applied.tolist()),independent_replay=replay,
            numerical_task_passed=replay['passed'],diagnostic_only=not replay['passed'],
            optimality_status=tr.get('optimality_status'),inherited_acceptance=False,
            time_rule='Complete original ZOH grid; no interpolation, truncation, padding or channel transfer')),
        'candidate_control_initialization')
    entry=dict(candidate=plain(request.candidate),source=source,task_acceptance='unmeasured')
    update(host,control_initializations=[*state(host).get('control_initializations',[]),entry])
    return entry


def verified_input_response(host,candidate,reference):
    """Side-effect-free handoff admission, shared by display and seed execution."""
    if plain(reference) not in state(host).get('analysis_results',[]):
        raise ValueError('REGISTERED_CURRENT_ANALYSIS_REQUIRED')
    cfg=verify_candidate(host,candidate)['configuration']
    if cfg['task']['family']!='task.reach':raise ValueError('NOT_APPLICABLE_SEED_REQUIRES_ENDPOINT_TARGET')
    analysis=host.store.artifact(reference);model=analysis.get('model') or {}
    bound=model.get('binding') or {};outer=analysis.get('binding') or {}
    inp,physics,scene,spec=model_context(cfg)
    expected=dict(candidate=plain(candidate),task_identity=digest(cfg['task']),
        effective_configuration_identity=digest(cfg),tendon_order=spec['tendon_order'])
    if (analysis.get('status')!='computed' or analysis.get('operation')!='input_sensitivity'
            or analysis.get('candidate')!=plain(candidate)
            or analysis.get('sensitivity',{}).get('verification',{}).get('passed') is not True
            or any(bound.get(k)!=v or outer.get(k)!=v for k,v in expected.items())
            or bound.get('model_identity')!=spec['identity']
            or model.get('operating_point')!=analysis.get('operating_point')
            or model.get('protocol_identity')!=digest(state(host)['spec']['analysis_protocol'])
            or bound.get('coordinate_order')!=spec['coordinate_order']):
        raise ValueError('VERIFIED_CANDIDATE_INPUT_SENSITIVITY_REQUIRED')
    return analysis


def guided_seed(host,request,key,plan):
    """Resolve trusted local evidence or charge complete public MuJoCo probes."""
    from copy import deepcopy
    from tools.research.control_seed import directed_inputs
    from tools.research.feedback import task_gap
    from tools.research.budget import backend_capacity, protected
    cfg=verify_candidate(host,request.candidate)['configuration']
    if cfg['task']['family']!='task.reach':raise ValueError('NOT_APPLICABLE_SEED_REQUIRES_ENDPOINT_TARGET')
    inp,physics,scene,spec=model_context(cfg);order=spec['tendon_order']
    channels=request.channels or order
    if not set(channels)<=set(order):raise ValueError('SEED_CHANNEL_OUTSIDE_CANDIDATE')
    indices=[order.index(c) for c in channels]
    if request.method=='mathematical_response':
        analysis=verified_input_response(host,request.candidate,request.response_evidence)
    else:
        required=len(indices)+1
        if required>request.evaluation_requests or required>backend_capacity(host):raise ValueError('INSUFFICIENT_SHARED_BUDGET_FOR_SEED_RESPONSE')
        if plan is None:raise ValueError('PHYSICAL_RESPONSE_REQUIRES_PUBLIC_PLAN')
    baseline=_seed_control(host,request.model_copy(update={'method':'baseline'}),key)
    source=host.store.artifact(baseline['source']);tr=source['trajectory']
    limits=np.array([{t['id']:t['force_limit_n'] for t in cfg['robot']['structure']['data']['tendons']}[c] for c in order])
    u=np.asarray(tr['tensions_n']);evidence=[];calls=[]
    if request.method=='mathematical_response':
        sensitivity=analysis['sensitivity'];model=analysis['model']
        u=np.tile(model['u0'],(len(u),1));position=np.asarray(model['y0']);response=np.asarray(sensitivity['dp_du'])
        evidence=[plain(request.response_evidence)]
    else:
        def factory(action,**payload):
            value={k:getattr(plan,k) for k in ('hypothesis','supporting_evidence','expected_observation','weakening_observation','fixed_conditions','stopping_condition','interpretation')}
            decision=plain(plan.decision);decision.update(research_intent='PHYSICAL_VALIDATION',requested_budget=1)
            return dict(value,action=action,decision=decision,**payload)
        response=np.zeros((3,len(order)))
        for j in [None,*indices]:
            if protected(host):raise ValueError('PROTECTED_BUDGET_BLOCKS_SEED_PROBES')
            trial=deepcopy(source)
            if j is not None:
                h=min(request.difference_step_n,float(np.min(limits[j]-u[:,j])))
                if h<1e-10:h=-min(request.difference_step_n,float(np.min(u[:,j])))
                if abs(h)<1e-10:return dict(status='no_input_room',candidate=plain(request.candidate),source=baseline['source'])
                moved=u.copy();moved[:,j]+=h;trial['trajectory']['tensions_n']=moved.tolist()
            result,cached=evaluate_schedule(host,request.candidate,trial,factory,origin='model')
            evidence.append(result['reference']);calls.append(dict(reference=result['reference'],cache_hit=cached))
            gap=task_gap(result)
            if gap['accepted']:return dict(status='first_original_task_pass',evaluation=result['reference'],candidate=plain(request.candidate),source=result['source_reference'])
            if not gap['valid_complete']:return dict(status='invalid_physical_response',evidence=evidence)
            raw=host.store.artifact(result['raw_reference']);endpoint=np.asarray(raw['samples'][-1]['tip_m'])
            if j is None:position=endpoint
            else:response[:,j]=(endpoint-position)/h
    fit=directed_inputs(u[:,indices],response[:,indices],np.asarray(cfg['task']['goal']['data']['target_m'])-position,
        limits[indices],request.trust_radius_n,request.regularization)
    provenance=dict(control_initialization=request.method,candidate=plain(request.candidate),evidence=evidence,
        task_identity=tr['task_identity'],model_identity=tr['model_identity'],operating_position_m=position.tolist(),
        channel_order=channels,settings=plain(request),response_diagnostic={k:v for k,v in fit.items() if k!='inputs'},
        physical_requests=calls,new_physical_evaluations=sum(not c['cache_hit'] for c in calls),
        limitations='Local constant input response; static mathematics and terminal physics do not certify dynamic holding constraints',
        inherited_acceptance=False,operation_key=key)
    diagnostic=save(host,provenance,'control_seed_response_diagnostic')
    if fit['status']!='generated':return dict(status=fit['status'],diagnostic=diagnostic,candidate=plain(request.candidate))
    u[:,indices]=fit['inputs'];source['trajectory']['tensions_n']=u.tolist();source['provenance']=provenance
    binding(cfg,source['trajectory'])
    source_ref=save(host,source,'candidate_directed_initialization')
    entry=dict(candidate=plain(request.candidate),source=source_ref,task_acceptance='unmeasured',diagnostic=diagnostic,method=request.method)
    update(host,control_initializations=[*state(host).get('control_initializations',[]),entry])
    return entry


def binding(configuration, trajectory, *, mathematical_outputs=None):
    inp,physics,scene,spec=model_context(configuration)
    timing=inp.task.timing;count=round(timing.duration_s/timing.control_period_s)
    order=[t['entity'] for t in physics['tendons']]
    u=np.asarray(trajectory['tensions_n'],dtype=float)
    configured_limits={t['id']:t['force_limit_n'] for t in configuration['robot']['structure']['data']['tendons']}
    limits=np.asarray([configured_limits[name] for name in order])
    if (trajectory['model_identity']!=spec['identity'] or trajectory['design_identity']!=spec['design_identity']
            or trajectory['task_identity']!=digest(plain(inp.task)) or trajectory['tendon_order']!=order
            or u.shape!=(count,len(order)) or not np.isfinite(u).all() or np.any(u<0) or np.any(u>limits)
            or len(trajectory['times_s'])!=count+1 or
            not np.isfinite(trajectory['times_s']).all() or
            any(abs(t-k*timing.control_period_s)>1e-12 for k,t in enumerate(trajectory['times_s']))
            or scene['control']['tension_execution_mode']!='ideal_tension'):
        raise ValueError('PHYSICAL_REPLAY_CANDIDATE_TASK_MODEL_OR_SEQUENCE_MISMATCH')
    if mathematical_outputs is not None:
        outputs=mathematical_outputs
        if (outputs['model_identity']!=trajectory['model_identity'] or
                outputs['times_s']!=trajectory['times_s'] or outputs['samples']!=count+1 or
                np.asarray(outputs['tip_positions_m']).shape!=(count+1,3) or
                np.asarray(outputs['tip_velocities_m_s']).shape!=(count+1,3)):
            raise ValueError('MATHEMATICAL_OUTPUT_BINDING_MISMATCH')
    return inp,physics,scene


def calculate(request,folder):
    from extensions.tendon_family.backends import playback_tensions
    store=Store(request['store_root'])
    current=store.session(request['study_id'])['state']
    pending=current.get('pending') or {}
    row=store.lookup(request['study_id'],request['request_id'])
    if (not row or row['receipt'] or row['request_hash']!=digest(request)
            or pending.get('kind')!='physical_replay' or pending.get('worker_request_id')!=request['request_id']
            or Path(pending['folder']).resolve()!=Path(folder).resolve()):
        raise ValueError('OWNED_ACTIVE_PHYSICAL_REPLAY_RESERVATION_REQUIRED')
    inp,physics,scene=binding(request['configuration'],request['trajectory'])
    result=playback_tensions(inp,physics,scene,request['trajectory']['tensions_n'],folder)
    result.update(candidate=request['candidate'],source_reference=request['source_reference'],
        task_identity=digest(plain(inp.task)),mathematical_model_identity=request['trajectory']['model_identity'])
    source=store.artifact(request['source_reference'])
    if source.get('provenance',{}).get('control_initialization')=='capability_sequence_v1':
        result.update(execution_model_identity=request['trajectory']['model_identity'],
            mathematical_model_identity=source['provenance']['mathematical_model_identity'],
            local_model_identity=source['provenance']['local_model_identity'])
    return result


def dispatch(host,arguments,key,*,role='development',selected=None):
    confirmation=role=='confirmation'
    guard(host,not confirmation)
    s=state(host)
    if s['spec'].get('research_decisions') and 'physical_replay' not in s['spec']['capabilities']:
        raise ValueError('PHYSICAL_REPLAY_CAPABILITY_REQUIRED')
    replay_limit=s['spec'].get('physical_replay_limit')
    if s.get('physical_replay_launches',0)>=(s['spec']['budgets']['physical_launches'] if replay_limit is None else replay_limit):
        raise ValueError('PHYSICAL_REPLAY_LAUNCH_BUDGET_EXHAUSTED')
    candidate=plain(arguments.candidate)
    cfg=verify_candidate(host,candidate)['configuration']
    source_ref=plain(arguments.source)
    source=host.store.artifact(source_ref)
    if explicit_control_source(source) and 'control_correction' not in s['spec']['capabilities']:
        raise ValueError('EXPLICIT_CONTROL_SCHEDULE_CAPABILITY_REQUIRED')
    if not (numerically_verified_source(source) or explicit_control_source(source)):
        raise ValueError('VERIFIED_OR_EXPLICIT_DIAGNOSTIC_MATHEMATICAL_SOURCE_REQUIRED')
    binding(cfg,source['trajectory'],mathematical_outputs=source.get('mathematical_outputs'))
    from tools.research.feedback import experiment_preflight,eligibility
    if confirmation:
        if s.get('selected')!=plain(selected):raise ValueError('CONFIRM_REQUIRES_PRIOR_FORMAL_SELECT')
        old=host.store.artifact(selected)
        if old['candidate']!=candidate or old.get('source_reference')!=source_ref:
            raise ValueError('CONFIRMATION_REQUIRES_EXACT_SELECTED_CONTROL_SOURCE')
        choice=eligibility(host,selected,selection=False,root_operation=False)
        if not choice['eligible']:raise ValueError('; '.join(choice['reasons']))
    from tools.research.budget import capacity
    if capacity(host,1,confirmation,route='fixed_tension')['admitted']<1:
        raise ValueError('PHYSICAL_REPLAY_AND_CONFIRMATION_RESERVE_CANNOT_FIT')
    novelty=experiment_preflight(host,candidate,'fixed_tension',source_ref=source_ref,repeat=confirmation)
    if not novelty['admitted']:
        raise ValueError('EQUIVALENT_SCIENTIFIC_EXPERIMENT_REQUIRES_EXPLICIT_REPLICATION_GRANT: '
            +json.dumps(novelty,sort_keys=True))
    request=dict(kind='physical_replay',implementation=s['freeze'],study_id=host.run_id,
        store_root=str(host.store.root),request_id=key+'-physical',candidate=candidate,
        source_reference=source_ref,configuration=cfg,trajectory=source['trajectory'],
        role=role,selected_execution=plain(selected),operation_key=key)
    worker_key=request['request_id']
    old=host.store.lookup(host.run_id,worker_key)
    if old:
        if old['request_hash']!=digest(request):raise ValueError('PHYSICAL_REPLAY_OPERATION_COLLISION')
        if not old['receipt']:raise ValueError('RECOVER_PHYSICAL_REPLAY_NO_RELAUNCH')
        return dict(reference=json.loads(old['receipt'])['output'],additional_physical_launches=0)
    def charge(db):
        current=host.store.session(host.run_id,db)['state']
        from tools.research.budget import backend_capacity
        if backend_capacity(host,db)<1:raise ValueError('BACKEND_CAPACITY_PROTECTS_RESERVED_RL_EVALUATIONS')
        current['physical_replay_launches']=current.get('physical_replay_launches',0)+1
        host.store.update_state(db,host.run_id,current)
    row,_=host.store.reserve(host.run_id,worker_key,digest(request),host.actor,
        {**zero(),'backend_solves':1},resources=('backend.family_mujoco',),guard=charge)
    folder=host.store.root/'physical_replay'/row['execution_id']
    folder.mkdir(parents=True,exist_ok=True)
    atomic_json(folder/'request.json',request)
    update(host,pending=dict(kind='physical_replay',worker_request_id=worker_key,folder=str(folder),
        implementation=s['freeze'],candidate=candidate,source_reference=source_ref,
        role=role,selected_execution=plain(selected),operation_key=key))
    from tools.service_execution import _run_contained
    started=time.perf_counter()
    try:
        with (folder/'worker.log').open('w',encoding='utf8') as log:
            done=_run_contained([s['spec']['runtime']['research_python'],'-m','tools.research.execution_worker',
                str(folder/'request.json')],log,None)
        boundary=dict(termination_confirmed=True,returncode=done.returncode)
    except subprocess.TimeoutExpired as exc:
        boundary=dict(termination_confirmed=getattr(exc,'termination_confirmed',False),timed_out=True)
    boundary['elapsed_s']=time.perf_counter()-started
    atomic_json(folder/'boundary.json',boundary)
    return recover(host)


def playback_profile(inp,raw,evaluation):
    """Task-layer diagnostics from physical samples; no integration or solver."""
    from tools.research_tasks import task_adapter
    adapter=task_adapter(inp)
    samples=raw.get('samples',[])
    timing=inp.task.timing;intervals=round(timing.duration_s/timing.control_period_s)
    substeps=round(timing.control_period_s/timing.timestep_s)
    complete=raw.get('status')=='completed' and len(samples)==intervals+1 and raw.get('physics_steps')==intervals*substeps
    configured_limits={t['id']:t['force_limit_n'] for t in inp.robot.structure.data['tendons']}
    tendon_limits=[configured_limits[name] for name in raw.get('tendon_order',list(configured_limits))]
    force_violation=max((max(0.,-v,v-hi) for row in samples[1:]
        for v,hi in zip(row['actual_tension_n'],tendon_limits)),default=0.)
    profile=dict(complete=complete,task=plain(inp.task),official_task_success=evaluation.task_success,
        solver_error_count=0 if complete else 1,force_bound_violation_n=force_violation)
    if inp.task.family=='task.tracking':
        # Motion is post-step; each sample's actual tension was applied during
        # the preceding interval. Verify both grids without scheduling the path.
        profile['tracking_sampling_complete']=bool(complete and
            all(abs(row['time_s']-k*timing.sample_period_s)<=1e-12 for k,row in enumerate(samples)) and
            all(np.asarray(row['actual_tension_n']).shape==(len(tendon_limits),) for row in samples[1:]))
    else:
        limits=adapter.ranking_limits();settling=inp.policy.controller.parameters.data['settling']
        hold=[v for v in samples if v['time_s']>=adapter.holding_start_s()-1e-12]
        expected_hold=round(settling['window_s']/timing.sample_period_s)+1
        covered=complete and len(hold)==expected_hold
        reference,_=adapter.reference_at([v['time_s'] for v in hold])
        max_error=max((float(np.linalg.norm(np.asarray(v['tip_m'])-r)) for v,r in zip(hold,reference)),default=None)
        max_speed=max((v['speed_m_s'] for v in hold),default=None)
        profile['sampled_settling']=dict(window_s=settling['window_s'],
            position_limit_m=limits['holding_max_error_m'],speed_limit_m_s=limits['holding_max_speed_m_s'],
            available=covered,max_error_m=max_error,max_speed_m_s=max_speed,
            passed=bool(covered and max_error<=limits['holding_max_error_m'] and max_speed<=limits['holding_max_speed_m_s']))
    return profile


def recover(host):
    from tools.platform_registry import registry
    from tools.research_tasks import assemble_acceptance

    p=state(host)['pending'];folder=Path(p['folder'])
    boundary=read(folder/'boundary.json')
    if not boundary['termination_confirmed']:
        raise ValueError('UNKNOWN_PHYSICAL_REPLAY_OUTCOME_RETAINS_RESERVATION')
    raw=read(folder/'result.json') if (folder/'result.json').exists() else dict(status='incomplete',reason='worker_result_missing')
    if raw.get('status')!='completed' and (folder/'samples.json').exists():
        raw['samples']=read(folder/'samples.json')
    raw.update(boundary=boundary,implementation=p['implementation'])
    raw_ref=save(host,raw,'physical_playback_raw')
    source=host.store.artifact(p['source_reference'])
    candidate=verify_candidate(host,p['candidate']);cfg=candidate['configuration']
    inp=SessionInput.model_validate(cfg)
    samples=raw.get('samples',[])
    signal=next(v for v in inp.task.observations if v.name=='tip_position' and v.phase=='post_step')
    result=BackendResult(solver_status='completed' if raw.get('status')=='completed' else 'failed',
        backend_id='backend.family_mujoco',model_id='mujoco_serial_bending_v1',
        signals=[Signal(spec=signal,times_s=[v['time_s'] for v in samples[1:]],
            values=[v['tip_m'] for v in samples[1:]])],
        data=Payload(contract='family.backend_data',data=dict(physical_replay=True)),
        limitations=['Ideal direct tendon tension; no hardware or robustness claim'],
        initial_state=inp.task.initializer.parameters,seed=inp.seed)
    evaluator=registry().get(inp.task.evaluator.extension_id,inp.task.evaluator.version,'evaluator').resolve()
    evaluation=evaluator(inp.task,result,raw_ref,registry(),digest(dict(candidate=p['candidate'],source=p['source_reference'])))
    evaluation_ref=save(host,plain(evaluation),'physical_playback_endpoint_evaluation')
    profile=playback_profile(inp,raw,evaluation)
    profile.update(execution_id=folder.name,simulation=raw_ref,evaluation=evaluation_ref)
    complete=profile['complete']
    acceptance=assemble_acceptance(cfg,evaluation,profile,evaluation_reference=evaluation_ref,
        profile_reference=None,motion=[dict(time_s=v['time_s']) for v in samples])
    predicted=source.get('mathematical_outputs')
    aligned=bool(predicted and len(samples)==len(predicted['times_s']) and
        all(abs(v['time_s']-t)<1e-12 for v,t in zip(samples,predicted['times_s'])))
    differences=[dict(time_s=v['time_s'],position_m=(np.asarray(v['tip_m'])-predicted['tip_positions_m'][i]).tolist(),
        position_norm_m=float(np.linalg.norm(np.asarray(v['tip_m'])-predicted['tip_positions_m'][i])),
        velocity_m_s=(np.asarray(v['tip_velocity_m_s'])-predicted['tip_velocities_m_s'][i]).tolist(),
        velocity_norm_m_s=float(np.linalg.norm(np.asarray(v['tip_velocity_m_s'])-predicted['tip_velocities_m_s'][i])))
        for i,v in enumerate(samples)] if aligned else []
    comparison=dict(aligned=aligned and complete,available_samples=len(differences),
        initial_position_offset_m=differences[0]['position_norm_m'] if differences else None,
        max_position_difference_m=max((v['position_norm_m'] for v in differences),default=None),
        max_velocity_difference_m_s=max((v['velocity_norm_m_s'] for v in differences),default=None),
        samples=differences)
    log_bytes=(folder/'worker.log').read_bytes()
    log_ref=save(host,dict(raw_base64=base64.b64encode(log_bytes).decode('ascii'),
        raw_sha256=hashlib.sha256(log_bytes).hexdigest(),text=log_bytes.decode('utf8',errors='replace')),
        'physical_playback_log')
    final=dict(status='evaluated' if complete else 'execution_incomplete',candidate=p['candidate'],
        role=p.get('role','development'),selected_execution=p.get('selected_execution'),operation_key=p.get('operation_key',p['worker_request_id']),
        scientific_configuration=candidate['scientific_configuration'],profile_identity=candidate['profile_identity'],
        model_identity=source['trajectory']['model_identity'],design_identity=source['trajectory']['design_identity'],
        owning_study=host.run_id,execution_id=p['worker_request_id'],
        source_reference=p['source_reference'],raw_reference=raw_ref,evaluation_reference=evaluation_ref,
        acceptance=acceptance,comparison=comparison,profile=profile,boundary=boundary,
        charged_numerical_s=boundary['elapsed_s'],implementation=p['implementation'],log_reference=log_ref,
        physical_launches=1,mathematical_reintegrations=0,rl_actions=0,nmpc_updates=0)
    ref=save(host,final,'physical_playback_result')
    row=host.store.lookup(host.run_id,p['worker_request_id'])
    with host.store.transaction() as db:
        current=host.store.session(host.run_id,db)['state']
        if current.get('pending')!=p:raise ValueError('ALREADY_SETTLED_PHYSICAL_REPLAY')
        current['numerical_s']+=boundary['elapsed_s']
        current['pending']=None
        current.setdefault('physical_replays',[]).append(ref)
        host.store.update_state(db,host.run_id,current)
        host.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],
            caller=host.actor,tool_id='research.physical_replay',tool_version='1.0.0',
            execution_status='completed',charged=zero()),final,elapsed=boundary['elapsed_s'],db=db)
    from tools.research.budget import observe_pass
    observe_pass(host,ref)
    return dict(reference=ref,**final)
