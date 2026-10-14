"""Candidate-bound mathematics, persistence and cumulative execution accounting."""
from copy import deepcopy
import json
import math
from pathlib import Path
import subprocess
import time
from schemas.research_core import AnalysisRequest
from schemas.platform import SessionInput
from schemas.platform_analysis import TaskAnalysisProtocol, EndpointLinearizedModel, EndpointTarget
from tools.platform_store import plain, zero
from tools.state_io import digest, atomic_json, read
from tools.research.design import state, update, save, verify_candidate, source_lengths


def calculate(configuration,binding,query,exact_point=None):
    """No Host, Route, session, persistence or cost ownership at this boundary."""
    from extensions.tendon_family.math_analysis import calculate_candidate_configuration
    from extensions.math_analysis.tools import calculate_control_metrics
    from extensions.math_analysis.kernels import bounded_endpoint, LIMITATIONS
    import numpy as np
    q=AnalysisRequest.model_validate(query);p=q.protocol;inp=SessionInput.model_validate(configuration)
    if q.operation=='equilibrium' and q.operating_point!='target_equilibrium':raise ValueError('EQUILIBRIUM_REQUIRES_TARGET_POINT')
    envelope=plain(calculate_candidate_configuration(inp,binding,p,binding['configuration'],
        operating_points=[q.operating_point],exact_point=exact_point))
    rows=envelope['records'][1:];row=rows[0];construction=row.get('construction') or {}
    internal=[]
    if construction.get('solver'):internal.append(dict(solver=construction['solver'],purpose='operating_point_construction',
        iterations=construction.get('iterations'),function_evaluations=construction.get('function_evaluations'),status=construction.get('status')))
    result=dict(status='computed',operation=q.operation,binding=binding,protocol=plain(p),
        operating_point=row.get('point',dict(name=row.get('name'),construction=construction)),
        construction=construction,local_model_constraints=dict(status='unmeasured'),
        task_acceptance='unmeasured',proxy_values={},raw=envelope,internal_calculations=internal,
        limitations=LIMITATIONS+['Local mathematics does not establish nonlinear backend acceptance, holding-window compliance, or design sensitivity.'])
    if q.operation=='equilibrium':
        result['proxy_values']['target_equilibrium_residual']=construction.get('position_residual_m')
        result['local_model_constraints']=dict(status='satisfied' if row.get('model') else 'unsatisfied_in_this_attempt',
            position_residual_m=construction.get('position_residual_m'),static_residual_inf=construction.get('static_residual_inf'),
            equilibrium_available=bool(row.get('model')),global_infeasibility_proven=False)
        result['units']=dict(position_residual='m',tension='N',static_residual='raw GVS generalized-force residual; coordinate/input units and scaling recorded in model/protocol')
        tensions=construction.get('computed_tensions_n')
        if tensions is not None:
            limits=binding['tension_limits_n'];result['tension_margins_n']=dict(lower=tensions,upper=[a-b for a,b in zip(limits,tensions)],
                interpretation='Computed attempt tensions; equilibrium validity remains separately reported')
        return result
    if not row.get('model'):
        result.update(status='unavailable',unavailable_reason=row.get('reason','Operating point unavailable'))
        return result
    model=EndpointLinearizedModel.model_validate(row['model']);result['model']=plain(model)
    result['operating_point']=model.operating_point
    if q.operation in ('linearization','controllability'):
        metrics=calculate_control_metrics(model,p);result['metrics']=metrics
        score=metrics['windows'][-1]['held']['output']['eigenvalues'][0]
        result['proxy_values']['held_position_min_eigenvalue']=float(score)
        result['units']=metrics['units'];internal.append(dict(purpose='local_linearization_and_gramian',solver='CasADi AD / SciPy scaled Van Loan and ZOH',windows_s=p.windows_s))
    else:
        target=EndpointTarget(position_m=inp.task.goal.data['target_m'],position_tolerance_m=inp.task.evaluator.parameters.data['tolerance_m'],
            position_scale_m=p.output_scale_m,tip_speed_limit_m_s=inp.policy.controller.parameters.data['settling']['speed_limit_m_s'])
        endpoint=bounded_endpoint(model,p,target,braking=q.operation=='braking')
        result['endpoint']=endpoint;result['local_model_constraints']=dict(status=endpoint['status'],checks=endpoint.get('checks'))
        if endpoint.get('solver'):
            internal.append(dict(purpose='endpoint_witness',**endpoint['solver']))
            for purpose,certificate in endpoint['independent_residual_problems'].items():
                internal.append(dict(purpose=purpose+'_box_residual_certificate',solver=certificate['solver'],success=certificate['solver_success']))
        result['units']=dict(position='m',speed='m/s',tension='N')
    result['tension_margins_n']=dict(lower=model.u0,upper=(np.asarray(binding['tension_limits_n'])-model.u0).tolist())
    return result


def admission(host,requested=1,engineering=False):
    s=state(host);cap=s['spec']['analysis_cap_s'];b=s['spec']['budgets']
    protection=0. if engineering else s['spec']['confirmation']['fresh_independent_repetitions']*s['spec']['nmpc_execution_cap_s']
    remaining=min(b['numerical_s']-s['numerical_s']-s['numerical_reserved_s']-protection,s['cutoff_unix']-time.time())
    count=max(0,min(requested,b['mathematical_evaluations']-s.get('mathematical_evaluations',0),math.floor(remaining/cap)))
    return dict(admitted=count,requested=requested,reservation_s=cap,remaining_numerical_s=remaining,confirmation_reserve_s=protection)


def dispatch(host,query,key,*,guard,origin='model'):
    q=AnalysisRequest.model_validate(query);request_id=key+'-analysis';identity=digest(plain(q))
    old=host.store.lookup(host.run_id,request_id)
    if old:
        if old['request_hash']!=identity:raise ValueError('ANALYSIS_OPERATION_ID_COLLISION')
        if not old['receipt']:raise ValueError('PENDING_ANALYSIS_RECOVER_WITHOUT_RECOMPUTATION')
        ref=json.loads(old['receipt'])['output']
        return dict(reference=ref,operation_reuse=dict(additional_numerical_s=0,additional_analysis_evaluations=0))
    guard(host,origin!='engineering_preflight');c=verify_candidate(host,q.candidate);s=state(host)
    protocol=plain(q.protocol)
    if protocol!=s['spec']['analysis_protocol']:raise ValueError('ANALYSIS_REQUIRES_DECLARED_FROZEN_PROTOCOL')
    fit=admission(host,engineering=origin=='engineering_preflight')
    if not fit['admitted']:raise ValueError('ANALYSIS_AND_CONFIRMATION_BUDGET_CANNOT_FIT')
    cfg=c['configuration'];design=cfg['robot']['structure']['data']
    from extensions.tendon_family.gvs_basis import resolve_basis
    basis=cfg['policy']['controller']['parameters']['data']['recipe']['basis']
    binding=dict(candidate_id=c['candidate_id'],candidate=plain(q.candidate),configuration=c['configuration_reference'],
        effective_configuration_identity=digest(cfg),task_identity=digest(cfg['task']),basis=basis,
        coordinate_order=list(resolve_basis(design,basis).coordinate_order),tendon_order=[t['id'] for t in design['tendons']],
        tension_limits_n=[t['force_limit_n'] for t in design['tendons']],tension_bounds_n=[[0.,t['force_limit_n']] for t in design['tendons']],
        target_m=cfg['task']['goal']['data']['target_m'],source_identity=c['source_identity'])
    point=None
    if q.saved_state:
        point=deepcopy(host.store.artifact(q.saved_state))
        if point.get('candidate')!=plain(q.candidate) or point.get('configuration_identity')!=digest(cfg):raise ValueError('EXACT_SAVED_STATE_CANDIDATE_MISMATCH')
        if len(point['x'])!=2*len(binding['coordinate_order']) or len(point['u'])!=6 or not point.get('phase'):
            raise ValueError('EXACT_SAVED_STATE_ORDER_AND_PHASE_REQUIRED')
        point.update(name='saved_state',available=True,construction=dict(method='exact immutable saved state',state=q.saved_state))
    reserve=fit['reservation_s']
    def charge(db):
        current=host.store.session(host.run_id,db)['state']
        current['mathematical_evaluations']=current.get('mathematical_evaluations',0)+1
        current['numerical_reserved_s']+=reserve
        host.store.update_state(db,host.run_id,current)
    row,_=host.store.reserve(host.run_id,request_id,identity,host.actor,{**zero(),'wall_s':reserve},kind='candidate_analysis',guard=charge)
    folder=host.store.root/'analyses'/row['execution_id'];folder.mkdir(parents=True,exist_ok=True)
    request=dict(kind='candidate_analysis',configuration=cfg,binding=binding,query=plain(q),exact_point=point)
    atomic_json(folder/'request.json',request)
    pending=dict(kind='candidate_analysis',worker_request_id=request_id,reserved_s=reserve,folder=str(folder),
        request=plain(q),origin=origin,implementation=s['freeze'],started_unix=time.time())
    update(host,pending=pending)
    from tools.service_execution import _run_contained
    from sys import executable
    started=time.perf_counter()
    try:
        with (folder/'worker.log').open('w',encoding='utf8') as log:
            done=_run_contained([executable,'-m','tools.research.execution_worker',str(folder/'request.json')],log,reserve)
        boundary=dict(termination_confirmed=True,returncode=done.returncode,timed_out=False)
    except subprocess.TimeoutExpired as exc:
        boundary=dict(termination_confirmed=getattr(exc,'termination_confirmed',False),timed_out=True)
    except Exception as exc:boundary=dict(termination_confirmed=False,error=str(exc))
    boundary['elapsed_s']=time.perf_counter()-started;atomic_json(folder/'boundary.json',boundary)
    return recover(host)


def recover(host):
    s=state(host);p=s['pending'];folder=Path(p['folder'])
    if not (folder/'boundary.json').exists() or not read(folder/'boundary.json')['termination_confirmed']:
        raise ValueError('UNKNOWN_ANALYSIS_TERMINATION_RETAINS_RESERVATION; NO_RELAUNCH')
    boundary=read(folder/'boundary.json');elapsed=boundary['elapsed_s']
    value=read(folder/'result.json') if (folder/'result.json').exists() else dict(status='incomplete',task_acceptance='unmeasured',boundary=boundary)
    value.update(candidate=p['request']['candidate'],requested_operation=p['request'],operation_key=p['worker_request_id'],
        owning_study=host.run_id,origin=p['origin'],implementation=p['implementation'],charged_numerical_s=elapsed,
        charged_analysis_evaluations=1,boundary=boundary,worker_log=save(host,dict(text=(folder/'worker.log').read_text(encoding='utf8',errors='replace')),'analysis_worker_log'))
    if value['status'] not in ('computed','unavailable'):
        value['internal_calculations']=dict(status='partial_or_unavailable',reason='Worker failed before complete calculation records were published; reservation and analysis attempt remain charged')
    ref=save(host,value,'candidate_analysis_result');row=host.store.lookup(host.run_id,p['worker_request_id'])
    with host.store.transaction() as db:
        current=host.store.session(host.run_id,db)['state']
        current['numerical_s']+=elapsed;current['numerical_reserved_s']-=p['reserved_s'];current['pending']=None
        current.setdefault('analysis_results',[]).append(ref)
        current.setdefault('analysis_costs',[]).append(dict(reference=ref,origin=p['origin'],numerical_s=elapsed,
            mathematical_evaluations=1,internal_calculations=value.get('internal_calculations',[])))
        host.store.update_state(db,host.run_id,current)
        host.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=host.actor,
            tool_id='research.candidate_analysis',tool_version='1.0.0',execution_status='completed',charged=zero()),value,elapsed=elapsed,db=db)
    return dict(reference=ref,status=value['status'],proxy_values=value.get('proxy_values',{}),
        task_acceptance='unmeasured',charged_numerical_s=elapsed,internal_calculations=value.get('internal_calculations',[]),
        local_model_constraints=value.get('local_model_constraints'))
