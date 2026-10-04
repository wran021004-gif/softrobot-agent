"""Bounded two-checkpoint preview and matched production prediction scoring."""
from copy import deepcopy
import time
import numpy as np
from schemas.platform import SessionInput
from tools.platform_registry import Extension
from tools.platform_store import plain
from tools.state_io import digest
from .milestone5_preview import PreviewRequest
from .diagnostic_evidence import DiagnosticEvidence, measured_motion, BoundReader
from .diagnostic_math import NonlinearModel, charge_units
from .gvs_trajectory import TrajectoryWorkspace
from .control_evidence import ControlEvidence, plan_metrics
from .gvs_profile import execution_scope

CHECKPOINTS=(20,30)
TOLERANCES=dict(position_m=1e-6,speed_m_s=1e-4,input_n=1e-9,time_s=1e-8)


def direction(delta,epsilon):
    return 'improvement' if delta < -epsilon else 'deterioration' if delta > epsilon else 'practically_unchanged'


def speed_change_direction(delta,epsilon=TOLERANCES['speed_m_s']):
    return 'decreasing' if delta < -epsilon else 'increasing' if delta > epsilon else 'approximately_unchanged'


def pairwise_speed_order(rows,key):
    """Only a tolerance-resolved speed order; no overall ranking."""
    if len(rows)==1:return dict(status='not_applicable',order=None,reason='Only one candidate.')
    if len(rows)!=2 or any(not r.get('valid_coverage',True) or r.get(key) is None or not np.isfinite(r[key]) for r in rows):
        return dict(status='unavailable',order=None,reason='Two valid comparable candidate quantities required.')
    delta=rows[1][key]-rows[0][key]
    if abs(delta)<=TOLERANCES['speed_m_s']:
        return dict(status='tie',order=None,difference_m_s=delta,tolerance_m_s=TOLERANCES['speed_m_s'])
    return dict(status='resolved',order=[r['candidate_id'] for r in sorted(rows,key=lambda r:r[key])],difference_m_s=delta,tolerance_m_s=TOLERANCES['speed_m_s'])


def ordering_score(predicted,observed):
    if predicted['status']=='not_applicable':return 'not_applicable'
    if predicted['status']!='resolved' or observed['status']=='unavailable':return 'unresolved'
    return 'correct' if observed['status']=='resolved' and predicted['order']==observed['order'] else 'incorrect'


def aligned_interval(observation, following, period_s):
    p=observation['one_step_prediction']
    if abs(p['time_s']-observation['time_s']-period_s)>TOLERANCES['time_s'] or abs(following['time_s']-p['time_s'])>TOLERANCES['time_s']:
        raise ValueError('PREDICTION_INTERVAL_MISMATCH')
    if max(abs(np.asarray(p['applied_tension_n'])-observation['actual_tension_n']))>TOLERANCES['input_n']:
        raise ValueError('PREDICTION_APPLIED_INPUT_MISMATCH')
    return p


def local_score(prediction,observed):
    predicted_delta=prediction['endpoint_speed_m_s']-prediction['initial_projected_speed_m_s']
    observed_delta=observed['speed_m_s']-prediction['initial_backend_speed_m_s']
    a=speed_change_direction(predicted_delta);b=speed_change_direction(observed_delta)
    return dict(predicted_speed_change_m_s=predicted_delta,observed_speed_change_m_s=observed_delta,
        endpoint_speed_error_m_s=prediction['endpoint_speed_m_s']-observed['speed_m_s'],
        velocity_error_norm_m_s=float(np.linalg.norm(np.asarray(prediction['endpoint_velocity_m_s'])-observed['velocity_m_s'])),
        position_error_norm_m=float(np.linalg.norm(np.asarray(prediction['endpoint_position_m'])-observed['position_m'])),
        observed_endpoint_speed_m_s=observed['speed_m_s'],predicted_direction=a,observed_direction=b,
        direction_verdict='correct' if a==b else 'incorrect',
        endpoint_within_tolerance=abs(prediction['endpoint_speed_m_s']-observed['speed_m_s'])<=TOLERANCES['speed_m_s'])


class ImportedReader(ControlEvidence):
    def __init__(self,store,bindings=None):
        super().__init__(store);self.bindings=bindings or {}

    def resolve(self,execution):
        if execution in self.bindings:return BoundReader(self.store,self.bindings[execution]).resolve(execution)
        return super().resolve(execution)


def diagnose(store,executions,bindings=None):
    reader=ImportedReader(store,bindings);records=[];all_updates=[];all_motion=[]
    for execution in executions:
        source=reader.resolve(execution);updates=reader.read_file(source,'controller_observations.json');motion=measured_motion(reader,source)
        holding=[m for m in motion if m['time_s']>=.3-1e-8];maximum=max(holding,key=lambda m:m['speed_m_s'])
        records.append(dict(execution_id=execution,manifest=source['manifest'],files=source['files'],
            holding_maximum=maximum,updates=[dict(update_id=i,time_s=o['time_s'],selected_iteration=o['optimization_selected_iteration'],
                stop_reason=o['policy_stop_reason'],raw_stop=o['optimization_raw_status'],effective_horizon=o['effective_horizon']) for i,o in enumerate(updates)],
            requested_applied_max_difference_n=max(float(np.max(np.abs(np.asarray(o['requested_tension_n'])-o['actual_tension_n']))) for o in updates),
            projection_residual_max_rad_m=max(o['gvs_projection_residual_max_rad_m'] for o in updates),
            availability=dict(projected_state=True,serial_backend_q_qdot=True,applied_inputs=True,one_step_predictions=True,
                timing=True,historical_warm_plans=False,backend_velocity='J_site(q) qdot reconstruction without stepping')))
        all_updates.append(updates);all_motion.append(motion)
    differences=[]
    for j in (1,2):
        first_command=next((dict(time_s=a['time_s'],max_difference_n=float(np.max(np.abs(np.asarray(a['actual_tension_n'])-b['actual_tension_n']))))
            for a,b in zip(all_updates[0],all_updates[j]) if np.max(np.abs(np.asarray(a['actual_tension_n'])-b['actual_tension_n']))>TOLERANCES['input_n']),None)
        first_position=next((dict(time_s=a['time_s'],difference_m=float(np.linalg.norm(np.asarray(a['position_m'])-b['position_m'])))
            for a,b in zip(all_motion[0],all_motion[j]) if np.linalg.norm(np.asarray(a['position_m'])-b['position_m'])>1e-9),None)
        differences.append(dict(reference_execution=executions[0],candidate_execution=executions[j],first_command=first_command,first_position=first_position))
    return dict(classification='development_data_only',records=records,differences=differences,
        command_tolerance_n=TOLERANCES['input_n'],trajectory_tolerance_m=1e-9,checkpoints=list(CHECKPOINTS),
        observation_rule='0.20 s first command divergence and 0.30 s holding entry; selected before new numerical results.',
        old_snapshot_omissions='0.34 s omitted onset at 0.20 s, active 0.30 s update and earlier holding maxima; only one period remained.',
        warm_start_rule='No saved historical warm plans: intentionally use common cold previous applied input and candidate-specific regenerated states.')


def execute(ctx,args):
    protocol=ctx.artifact(args.protocol)
    if protocol['classification']=='matched_development_fidelity':
        start=time.perf_counter();development=development_fidelity(ctx,protocol)
        return DiagnosticEvidence(detail=dict(development_local_fidelity=development,classification='development data only',
            local_solves=0,prediction_rollouts=0,complete_cost_s=time.perf_counter()-start,
            work='Recorded production predictions and direct projected kinematics; no new solve, integration, or backend step.'))
    if protocol['classification']!='bounded_prediction_validation':raise ValueError('FROZEN_VALIDATION_PROTOCOL_REQUIRED')
    start=time.perf_counter();deadline=start+protocol['limits']['max_wall_s'];rows=[]
    for snapshot in protocol['snapshots']:
        for frozen in protocol['configurations']:
            cfg=ctx.artifact(frozen['configuration'])['effective']
            if digest(execution_scope(cfg))!=frozen['scientific_identity']:raise ValueError('FORECAST_CONFIGURATION_CHANGED')
            inp=SessionInput.model_validate(cfg);parameters=deepcopy(inp.policy.controller.parameters.data['recipe'])
            parameters['horizon']=snapshot['effective_horizon'];x=snapshot['measured_initial_state'];previous=snapshot['previous_input_n']
            if time.perf_counter()+65>deadline:raise RuntimeError('PREVIEW_TIME_ALLOWANCE')
            charge_units(ctx,'local_solves',1)
            ws=TrajectoryWorkspace(inp.task,inp.robot,parameters,x,previous,settling=inp.policy.controller.parameters.data['settling'])
            solved=ws.solve(x,previous,elapsed_s=snapshot['time_s']);checked=ws.solver.evaluate_candidate(ws.problem,solved['result']['optimum'])
            if not solved['accepted'] or not checked['feasible']:raise ValueError('PREVIEW_INDEPENDENT_FEASIBILITY')
            u=solved['tensions'][0];limits=np.asarray(protocol['force_limits_n'])
            if np.any(np.asarray(u)<-1e-8) or np.any(np.asarray(u)>limits+1e-8):raise ValueError('PREVIEW_INPUT_BOUNDS')
            physical=[]
            for k,state in enumerate(solved['states']):
                p,v=ws._motion(state[:ws.n],state[ws.n:]);p=np.asarray(p).ravel();v=np.asarray(v).ravel()
                physical.append(dict(time_s=snapshot['time_s']+k*ws.period/parameters['substeps'],speed_m_s=float(np.linalg.norm(v)),error_m=float(np.linalg.norm(p-ws.target))))
            holding=[p for p in physical if p['time_s']>=.3-1e-8]
            charge_units(ctx,'prediction_evaluations',1)
            model=NonlinearModel(cfg,x,previous,.002);trajectory=model.rollout(x,u,.01,deadline)
            detail=ctx.save_artifact(dict(solved=solved,verification=checked,physical_plan=physical,trajectory=trajectory),'validation_preview_detail')
            rows.append(dict(**frozen,update_id=snapshot['update_id'],time_s=snapshot['time_s'],effective_horizon=parameters['horizon'],
                first_command_n=u,selected_iteration=solved['diagnostics']['selected_feasible_iteration'],stop_reason=solved['diagnostics']['policy_stop_reason'],
                holding_plan_max_speed_m_s=max(p['speed_m_s'] for p in holding),holding_plan_max_error_m=max(p['error_m'] for p in holding),
                endpoint_speed_m_s=trajectory[-1]['speed_m_s'],plan_metrics=plan_metrics(ws,np.asarray(solved['states']),np.asarray(solved['tensions']),snapshot['time_s']),
                projection_speed_difference_m_s=trajectory[0]['speed_m_s']-snapshot['backend_speed_m_s'],
                projection_position_difference_m=float(np.linalg.norm(np.asarray(trajectory[0]['position_m'])-snapshot['backend_position_m'])),detail=plain(detail)))
    reference=next(r for r in rows if r['role']=='reference' and r['update_id']==30)
    forecasts=[]
    for row in rows:
        if row['role']=='reference' or row['update_id']!=30:continue
        forecasts.append(dict(candidate_id=row['candidate_id'],configuration=row['configuration'],scientific_identity=row['scientific_identity'],
            holding_speed_direction=direction(row['holding_plan_max_speed_m_s']-reference['holding_plan_max_speed_m_s'],TOLERANCES['speed_m_s']),
            holding_position_direction=direction(row['holding_plan_max_error_m']-reference['holding_plan_max_error_m'],TOLERANCES['position_m']),
            joint_acceptance='unresolved',qualification='Heuristic full-task direction from common projected holding-entry cold preview; incomplete closed-loop coverage.'))
    # Equality in a cold preview is not evidence of full-task equivalence.
    for f in forecasts:
        for key in ('holding_speed_direction','holding_position_direction'):
            if f[key]=='practically_unchanged':f[key]='unresolved'
    development=(ctx.artifact(protocol['development_fidelity_reference'])['detail']['development_local_fidelity']
        if protocol.get('development_fidelity_reference') else development_fidelity(ctx,protocol))
    candidates=[dict(candidate_id=r['candidate_id'],holding_plan_max_speed_m_s=r['holding_plan_max_speed_m_s'],
        valid_coverage=r['effective_horizon']==5) for r in rows if r['role']!='reference' and r['update_id']==30]
    ordering=pairwise_speed_order(candidates,'holding_plan_max_speed_m_s')
    ordering['mapping']='Cold holding-entry plan max speed order hypothesizes full-task holding max speed order; tie/unavailable implies abstention.'
    return DiagnosticEvidence(detail=dict(protocol=plain(args.protocol),rows=rows,forecasts=forecasts,development_local_fidelity=development,
        predicted_speed_order=ordering['order'],speed_order_forecast=ordering,acceptance_prediction='unresolved',local_solves=len(rows),prediction_rollouts=len(rows),
        complete_cost_s=time.perf_counter()-start,scope='Candidate-specific production-policy cold previews at two development checkpoints; full task hypotheses remain qualified.'))


def development_fidelity(ctx,protocol):
    development=[]
    reader=ImportedReader(ctx.store,protocol['development_bindings'])
    for execution in protocol['development_executions']:
        source=reader.resolve(execution);observations=reader.read_file(source,'controller_observations.json');motion=measured_motion(reader,source)
        for index in CHECKPOINTS:
            o=observations[index];following=motion[index];p=aligned_interval(o,following,.01)
            current=motion[index-1];model=NonlinearModel(source['configuration'],o['measured_initial_state'],o['actual_tension_n'],.01)
            position,velocity,*_=model.acceleration(o['measured_initial_state'],o['actual_tension_n'])
            prediction=dict(endpoint_speed_m_s=float(np.linalg.norm(p['tip_velocity_m_s'])),endpoint_velocity_m_s=p['tip_velocity_m_s'],
                endpoint_position_m=p['tip_position_m'],initial_projected_speed_m_s=float(np.linalg.norm(velocity)),initial_backend_speed_m_s=current['speed_m_s'])
            development.append(dict(execution_id=execution,start_s=o['time_s'],end_s=p['time_s'],applied_input_n=o['actual_tension_n'],
                projection_position_difference_m=float(np.linalg.norm(position-current['position_m'])),
                projection_speed_difference_m_s=float(np.linalg.norm(velocity))-current['speed_m_s'],score=local_score(prediction,following),
                classification='development matched recorded production prediction, not prospective validation',
                state_reference=source['files']['controller_observations.json'],motion_reference=source['files']['trajectory.json.gz']))
    return development


def preflight(inp,args,reg):return dict(cost=dict(wall_s=600.))

DEFINITION=Extension('analysis.milestone5_validation','tool','1.0.0',PreviewRequest,DiagnosticEvidence,
    'extensions.tendon_family.milestone5_validation:execute','Bounded two-checkpoint candidate-specific preview.',
    sources=('extensions/tendon_family/milestone5_validation.py','extensions/tendon_family/diagnostic_math.py',
        'extensions/tendon_family/gvs_trajectory.py','extensions/tendon_family/control_evidence.py'),dependencies=('numpy','scipy','casadi'),
    side_effects='artifact_store',capabilities=dict(backend_solves=0,preflight='extensions.tendon_family.milestone5_validation:preflight'))
