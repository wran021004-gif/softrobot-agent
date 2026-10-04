"""M5 development-only prediction tools; production controller defaults are untouched."""
from copy import deepcopy
from typing import Literal
import time
import numpy as np
from pydantic import Field
from schemas.common import Contract
from schemas.platform import SessionInput
from schemas.platform_handoff import HandoffResult
from tools.platform_registry import Extension
from tools.platform_store import plain
from tools.state_io import digest
from .diagnostic_evidence import DiagnosticEvidence
from .diagnostic_math import NonlinearModel, charge_units
from .milestone5_preview import PreviewRequest
from .gvs_nmpc import deadline_horizon
from .gvs_trajectory import TrajectoryWorkspace

PREVIEW_VERSION='candidate_history@1.0.0'
LOCAL_VERSION='local_fixed_command@2.0.0'
REFERENCE_STEPS=(.0005,.00025,.000125)


def grid(configuration):
    t=configuration['task']['timing'];n=round(t['duration_s']/t['control_period_s'])
    if abs(n*t['control_period_s']-t['duration_s'])>1e-10:raise ValueError('UNALIGNED_TASK')
    return [i*t['control_period_s'] for i in range(n)]


def fixed_input(model,state,input_n,duration,deadline):
    """Finer diagnostic integration, separate from bounded production helpers."""
    count=round(duration/model.step_s)
    if not 1<=count<=80 or abs(count*model.step_s-duration)>1e-10:raise ValueError('REFERENCE_GRID')
    x=np.asarray(state).copy();residual=0.;start=time.perf_counter()
    for _ in range(count):
        if time.perf_counter()>deadline:raise RuntimeError('REFERENCE_DEADLINE')
        new=np.asarray(model.step(x/model.scales,x,input_n)).ravel()*model.scales
        r=float(np.max(abs(np.asarray(model.residual(x,new,input_n)))))
        if not np.isfinite(new).all() or r>1e-5:raise ValueError('REFERENCE_RESIDUAL')
        residual=max(residual,r);x=new
    p,v,*_=model.motion(x[:model.n],x[model.n:]);p=np.asarray(p).ravel();v=np.asarray(v).ravel()
    return dict(state=x.tolist(),position_m=p.tolist(),velocity_m_s=v.tolist(),speed_m_s=float(np.linalg.norm(v)),
        step_count=count,max_scaled_residual=residual,integration_s=time.perf_counter()-start)


def reference(ctx,protocol):
    rows=[]
    for saved in protocol['intervals']:
        cfg=ctx.artifact(saved['configuration'])['effective'];results=[]
        for h in REFERENCE_STEPS:
            charge_units(ctx,'prediction_evaluations',1);start=time.perf_counter()
            model=NonlinearModel(cfg,saved['state'],saved['input_n'],h)
            end=fixed_input(model,saved['state'],saved['input_n'],saved['duration_s'],time.perf_counter()+90)
            end.update(step_s=h,complete_cost_s=time.perf_counter()-start,
                position_error_norm_m=float(np.linalg.norm(np.asarray(end['position_m'])-saved['observed']['position_m'])),
                velocity_error_norm_m_s=float(np.linalg.norm(np.asarray(end['velocity_m_s'])-saved['observed']['velocity_m_s'])),
                speed_error_m_s=end['speed_m_s']-saved['observed']['speed_m_s'])
            results.append(end)
        differences=[]
        for a,b in zip(results,results[1:]):
            differences.append(dict(coarse_s=a['step_s'],fine_s=b['step_s'],
                position_norm_m=float(np.linalg.norm(np.asarray(b['position_m'])-a['position_m'])),
                velocity_norm_m_s=float(np.linalg.norm(np.asarray(b['velocity_m_s'])-a['velocity_m_s'])),
                speed_m_s=abs(b['speed_m_s']-a['speed_m_s'])))
        stable=all(d['velocity_norm_m_s']<=1e-4 and d['speed_m_s']<=1e-4 for d in differences)
        rows.append(dict(execution_id=saved['execution_id'],candidate_id=saved['candidate_id'],
            input_policy=saved['input_policy'],interval_s=saved['interval_s'],results=results,differences=differences,
            numerical_reference_established=stable,measured_numerical_uncertainty=differences[-1],
            tolerance_m_s=1e-4,qualification='Successive-resolution stability on two development intervals only; not a proven error bound or backend accuracy.'))
        ctx.save_artifact(rows[-1],'reference_interval_completed')
    return dict(rows=rows,standalone_integrations=6,reused_predecessor_integrations=6,
        numerical_reference_established=all(r['numerical_reference_established'] for r in rows))


def history(configuration,initial_state,charge,*,deadline,save_update=lambda row:None,workspace_factory=TrajectoryWorkspace):
    """Candidate owns workspace, states, previous input and last plan. No outcome reader."""
    from .gvs_profile import reach_numerical
    inp=SessionInput.model_validate(configuration);p=inp.policy.controller.parameters.data['recipe']
    numerical=reach_numerical(inp);previous=np.asarray(numerical['nominal']['u0']).copy()
    x=np.asarray(initial_state).copy();seed=deepcopy(numerical['warm_guess']);ws=None;rows=[];unusable=0
    limits=np.array([t['force_limit_n'] for t in inp.robot.structure.data['tendons']]);period=inp.task.timing.control_period_s
    start=time.perf_counter()
    for i,t in enumerate(grid(configuration)):
        if time.perf_counter()>deadline:raise RuntimeError('PREVIEW_DEADLINE_NO_COMPLETE_CLAIM')
        construction=time.perf_counter();horizon=deadline_horizon(inp.task.timing.duration_s,t,period,p['horizon'])
        if ws is None or ws.parameters.horizon!=horizon:
            if ws is not None:
                source=seed if seed is not None else ws.last;shift=0 if seed is not None else p['substeps']
                seed=None if source is None else dict(states=source['states'][shift:shift+horizon*p['substeps']+1],
                    tensions=source['tensions'][int(bool(shift)):int(bool(shift))+horizon])
            ws=workspace_factory(inp.task,inp.robot,{**p,'horizon':horizon},
                [*numerical['nominal']['q0'],*([0.]*(len(x)//2))],numerical['nominal']['u0'],
                settling=inp.policy.controller.parameters.data['settling'])
            ws.last=seed
        construction_s=time.perf_counter()-construction
        initial=x.copy();previous_before=previous.copy();explicit=seed is not None
        charge();solve_start=time.perf_counter();solved=None;error=None
        try:
            solved=ws.solve(x,previous,warm=seed,elapsed_s=t)
            accepted=solved['accepted']
            checked=ws.solver.evaluate_candidate(ws.problem,solved['result']['optimum'])
            accepted=accepted and checked['feasible']
        except (RuntimeError,ValueError) as exc:accepted=False;error=str(exc);checked=None
        solve_wall_s=time.perf_counter()-solve_start;seed=None
        unusable=0 if accepted else unusable+1
        if unusable>=p['max_unusable_updates']:raise RuntimeError('NMPC_SUSTAINED_UNUSABLE_REPLANNING')
        requested=np.asarray(solved['tensions'][0]) if accepted else previous.copy()
        command=np.clip(requested,0,limits);previous=command.copy()
        # Propagate independently through the very same implicit transcription, even on held inputs.
        integration_start=time.perf_counter();tails=[]
        for _ in range(p['substeps']):
            x,telemetry=ws._extend_tail(x,command);tails.append(telemetry)
        pos,vel=ws._motion(x[:ws.n],x[ws.n:]);pos=np.asarray(pos).ravel();vel=np.asarray(vel).ravel()
        diagnostics={} if solved is None else solved['diagnostics']
        row=dict(update_id=i,time_s=t,endpoint_s=t+period,initial_state=initial.tolist(),state=x.tolist(),
            previous_input_n=previous_before.tolist(),input_n=command.tolist(),
            position_m=pos.tolist(),velocity_m_s=vel.tolist(),speed_m_s=float(np.linalg.norm(vel)),
            error_m=float(np.linalg.norm(pos-ws.target)),effective_horizon=horizon,accepted=bool(accepted),
            feasibility=checked,solver_error=error,selected_iteration=diagnostics.get('selected_feasible_iteration'),
            stop_reason=diagnostics.get('policy_stop_reason'),raw_stop=diagnostics.get('return_status'),
            initialization='explicit_bundled_guess' if i==0 else 'candidate_previous_selected_shifted',
            explicit_warm=explicit,warm_start=None if solved is None else solved['warm_start'],
            plan_identity=None if solved is None else digest(dict(states=solved['states'],tensions=solved['tensions'])),
            graph_construction_s=construction_s,controller_s=solve_wall_s,
            propagation_s=time.perf_counter()-integration_start,internal_propagation=tails)
        rows.append(row);save_update(row)
    holding=[r for r in rows if r['endpoint_s']>=inp.task.timing.duration_s-inp.policy.controller.parameters.data['settling']['window_s']-1e-9]
    return dict(version=PREVIEW_VERSION,configuration_identity=digest(configuration),classification='development' ,
        complete=len(rows)==len(grid(configuration)),interval_s=[0.,inp.task.timing.duration_s],rows=rows,
        metrics=dict(holding_max_speed_m_s=max(r['speed_m_s'] for r in holding),holding_max_error_m=max(r['error_m'] for r in holding),terminal_error_m=rows[-1]['error_m']),
        solves=len(rows),complete_cost_s=time.perf_counter()-start,
        initialization=numerical['provenance'],actuator_mapping='Bounded direct ideal tensions, held for the control interval; matches backend ideal_tension mapping, omits full-order state and contacts.')


def execute(ctx,args):
    protocol=ctx.artifact(args.protocol);start=time.perf_counter()
    if protocol['operation']=='reference':result=reference(ctx,protocol)
    elif protocol['operation']=='history':
        charge_units(ctx,'preview_attempts',1)
        result=history(protocol['configuration'],protocol['initial_state'],lambda:charge_units(ctx,'local_solves',1),
            deadline=time.perf_counter()+protocol['allowance_s'],save_update=lambda row:ctx.save_artifact(row,'preview_update_completed'))
        result['classification']='retrospective development; original initializer and historical recipe; reduced own-history forecast is not a backend replay'
    else:raise ValueError('UNKNOWN_DEVELOPMENT_OPERATION')
    return DiagnosticEvidence(detail=dict(result=result,complete_cost_s=time.perf_counter()-start))


class ResearchDecision(Contract):
    phase: Literal['selection','interpretation']
    holding_weights: list[float] = Field(min_length=2,max_length=2)
    rationale: str = Field(min_length=20)
    readiness: str
    limitations: list[str]
    next_action: Literal['finish_stop']


def research(ctx,args):
    if args.holding_weights[0]==args.holding_weights[1] or any(not .0001<=v<=1 for v in args.holding_weights):
        raise ValueError('TWO_DISTINCT_SUPPORTED_HOLDING_WEIGHTS_REQUIRED')
    role=ctx.store.session(ctx.run_id)['state']['role_context']
    if args.phase!=role['phase']:raise ValueError('RESEARCH_PHASE')
    if args.phase=='interpretation' and args.holding_weights!=role['decision_packet']['selected_weights']:
        raise ValueError('FUTURE_RECIPES_ALREADY_FROZEN')
    from tools.platform_handoff import transition
    return transition(ctx,'m5_'+args.phase,args)


def preflight(inp,args,reg):
    return dict(cost=dict(wall_s=1500.))


DEFINITION=Extension('analysis.milestone5_preparation','tool','1.0.0',PreviewRequest,DiagnosticEvidence,
    'extensions.tendon_family.milestone5_preparation:execute','Bounded M5 reference and complete own-history development preview.',
    sources=('extensions/tendon_family/milestone5_preparation.py',),side_effects='artifact_store',
    capabilities=dict(preflight='extensions.tendon_family.milestone5_preparation:preflight'))
RESEARCH=Extension('research.milestone5_preparation','tool','1.0.0',ResearchDecision,HandoffResult,
    'extensions.tendon_family.milestone5_preparation:research','Select two future recipes or interpret fixed development evidence; finish/stop only.',
    sources=('extensions/tendon_family/milestone5_preparation.py',),side_effects='artifact_store')
