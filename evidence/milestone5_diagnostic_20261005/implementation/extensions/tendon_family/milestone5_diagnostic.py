"""Saved-evidence diagnostics only; no controller changes or backend advancement."""
import time
import numpy as np
from tools.platform_registry import Extension
from tools.platform_store import plain
from .milestone5_preview import PreviewRequest
from .diagnostic_evidence import BoundReader, DiagnosticEvidence, measured_motion
from .diagnostic_math import NonlinearModel, charge_units
from .milestone5_validation import aligned_interval


def difference(a, b):
    return (np.asarray(a)-np.asarray(b)).tolist()


def decomposition(initial, predicted, observed):
    """Vector identity and a separate norm identity, both predicted minus observed."""
    result={}
    for quantity in ('position_m', 'velocity_m_s'):
        a=np.asarray(initial['projected'][quantity]);b=np.asarray(initial['backend'][quantity])
        p=np.asarray(predicted[quantity]);o=np.asarray(observed[quantity])
        projection=a-b;change=(p-a)-(o-b);endpoint=p-o
        result[quantity]=dict(initial_projection_error=projection.tolist(),
            predicted_change=(p-a).tolist(),observed_change=(o-b).tolist(),
            change_error=change.tolist(),endpoint_error=endpoint.tolist(),
            initial_error_norm=float(np.linalg.norm(projection)),change_error_norm=float(np.linalg.norm(change)),
            endpoint_error_norm=float(np.linalg.norm(endpoint)),identity_residual=float(np.max(abs(endpoint-projection-change))))
    a=np.linalg.norm(initial['projected']['velocity_m_s']);b=np.linalg.norm(initial['backend']['velocity_m_s'])
    p=np.linalg.norm(predicted['velocity_m_s']);o=np.linalg.norm(observed['velocity_m_s'])
    result['speed_m_s']=dict(initial_projected=float(a),initial_backend=float(b),predicted_endpoint=float(p),observed_endpoint=float(o),
        initial_projection_error=float(a-b),predicted_change=float(p-a),observed_change=float(o-b),
        change_error=float((p-a)-(o-b)),endpoint_error=float(p-o),identity_residual=float((p-o)-(a-b)-((p-a)-(o-b))))
    return result


def intervals(ctx, protocol):
    rows=[]
    for binding in protocol['bindings']:
        reader=BoundReader(ctx.store,binding);source=reader.resolve(reader.binding['execution_id'])
        updates=reader.read_file(source,'controller_observations.json');motion=measured_motion(reader,source)
        o=updates[30];current=next(m for m in motion if abs(m['time_s']-o['time_s'])<1e-8)
        following=next(m for m in motion if abs(m['time_s']-o['one_step_prediction']['time_s'])<1e-8)
        duration=following['time_s']-current['time_s'];p=aligned_interval(o,following,duration)
        assert abs(duration-.01)<1e-12 and p['substeps']==1
        x=o['measured_initial_state'];u=o['actual_tension_n'];cfg=source['configuration']
        integration=[];model=None
        for h in (.01,.002,.001):
            # Charge before construction or evaluation, including failed attempts.
            charge_units(ctx,'prediction_evaluations',1);start=time.perf_counter()
            model=NonlinearModel(cfg,x,u,h)
            trajectory=model.rollout(x,u,duration,time.perf_counter()+180.)
            residuals=[r['next_step_max_scaled_residual'] for r in trajectory[:-1]]
            end=trajectory[-1]
            integration.append(dict(step_s=h,step_count=len(trajectory)-1,trajectory=trajectory,
                endpoint=end,max_scaled_residual=max(residuals),status='root_residual_verified',
                complete_cost_s=time.perf_counter()-start,
                endpoint_speed_error_m_s=end['speed_m_s']-following['speed_m_s'],
                endpoint_velocity_error_m_s=difference(end['velocity_m_s'],following['velocity_m_s']),
                endpoint_velocity_error_norm_m_s=float(np.linalg.norm(np.asarray(end['velocity_m_s'])-following['velocity_m_s'])),
                endpoint_position_error_norm_m=float(np.linalg.norm(np.asarray(end['position_m'])-following['position_m']))))
        pos,vel,*_=model.motion(np.asarray(x[:model.n]),np.asarray(x[model.n:]))
        initial=dict(projected=dict(position_m=np.asarray(pos).ravel().tolist(),velocity_m_s=np.asarray(vel).ravel().tolist()),backend=current)
        predicted=dict(position_m=p['tip_position_m'],velocity_m_s=p['tip_velocity_m_s'])
        coarse=integration[0]['endpoint']
        saved_residual=float(np.max(abs(np.asarray(NonlinearModel(cfg,x,u,.01).residual(x,p['state'],u)))))
        rows.append(dict(evidence_type='current retrospective diagnostic calculation',
            saved_prediction_type='previously sealed prospective result, now development data',
            execution_id=source['execution_id'],candidate_id=reader.binding['candidate_id'],configuration=reader.binding['configuration'],
            manifest=source['manifest'],files=source['files'],checkpoint_s=o['time_s'],interval_s=[o['time_s'],following['time_s']],duration_s=duration,
            state=x,input_n=u,input_policy='recorded actual applied tensions held for exact interval',initialization='recorded projected state; Newton initial guess previous reduced state',
            comparison_reference=dict(trajectory=source['files']['trajectory.json.gz'],xml=source['files']['robot.xml'],velocity='J_site(q) @ qdot; no backend step'),
            initial=initial,predicted=predicted,observed=following,decomposition=decomposition(initial,predicted,following),
            saved_selected_scaled_violation=o['optimization_constraint_violation'],saved_first_step_max_scaled_residual=saved_residual,
            coarse_reproduction=dict(speed_difference_m_s=coarse['speed_m_s']-float(np.linalg.norm(p['tip_velocity_m_s'])),
                position_difference_m=float(np.linalg.norm(np.asarray(coarse['position_m'])-p['tip_position_m'])),
                velocity_difference_norm_m_s=float(np.linalg.norm(np.asarray(coarse['velocity_m_s'])-p['tip_velocity_m_s'])),
                saved_state_speed_consistency_m_s=float(np.linalg.norm(np.asarray(model.motion(p['state'][:model.n],p['state'][model.n:])[1])))-float(np.linalg.norm(p['tip_velocity_m_s']))),
            integration=integration,
            fine_difference=dict(speed_m_s=integration[2]['endpoint']['speed_m_s']-integration[1]['endpoint']['speed_m_s'],
                velocity_norm_m_s=float(np.linalg.norm(np.asarray(integration[2]['endpoint']['velocity_m_s'])-integration[1]['endpoint']['velocity_m_s'])),
                position_norm_m=float(np.linalg.norm(np.asarray(integration[2]['endpoint']['position_m'])-integration[1]['endpoint']['position_m']))),
            caution='Change error includes projection, omitted modes, transcription and integration; it is not an isolated physical dynamics error. Finer is not automatically converged.'))
    return rows


def preview(ctx, protocol):
    numerical=ctx.artifact(protocol['numerical'])['detail'];frozen=ctx.artifact(protocol['preview_protocol']);rows=[]
    for row in numerical['rows']:
        detail=ctx.artifact(row['detail']);solved=detail['solved'];cfg=ctx.artifact(row['configuration'])['effective']
        recipe=cfg['policy']['controller']['parameters']['data']['recipe']
        from .contracts import GVSTrajectoryParameters
        p=GVSTrajectoryParameters.model_validate(recipe)
        tolerance=cfg['task']['evaluator']['parameters']['data']['tolerance_m']
        physical=detail['physical_plan'];seed=solved['warm_start']
        rows.append(dict(evidence_type='historical development',candidate_id=row['candidate_id'],configuration=row['configuration'],detail=row['detail'],
            checkpoint_s=row['time_s'],horizon=row['effective_horizon'],selected_iteration=row['selected_iteration'],stop_reason=row['stop_reason'],
            first_command_n=row['first_command_n'],previous_input_n=solved['previous_tensions_n'],
            position_threshold_m=p.seed_position_tolerance_fraction*tolerance,speed_threshold_m_s=p.seed_speed_limit_m_s,
            maximum_selected_plan_error_m=max(r['error_m'] for r in physical),maximum_selected_plan_speed_m_s=max(r['speed_m_s'] for r in physical),
            selected_plan_is_seed=row['selected_iteration']==0,seed_settled=seed['seed_settled'],feasibility=detail['verification'],
            initial_scaled_violation=solved['diagnostics']['initial_scaled_violation'],
            holding_weight=p.holding_tip_speed_weight,terminal_weight=p.terminal_tip_speed_weight,
            optimized_before_acceptance=row['selected_iteration']!=0,
            checks_depend_on_weights=False,
            input_policy=frozen['warm_start']))
    production=[]
    for binding in [protocol['incumbent_binding'],*protocol['bindings']]:
        reader=BoundReader(ctx.store,binding);source=reader.resolve(reader.binding['execution_id']);updates=reader.read_file(source,'controller_observations.json')
        # Inspect the exact manifest once; never search other experiments for missing plans.
        availability={name:name in source['files'] for name in ('control_snapshots.json','control_plans.json','optimizer_snapshots.json')}
        for index in (20,30):
            o=updates[index];snap=next(s for s in frozen['snapshots'] if s['update_id']==index)
            production.append(dict(evidence_type='historical development',execution_id=source['execution_id'],candidate_id=reader.binding['candidate_id'],
                configuration=reader.binding['configuration'],manifest=source['manifest'],state_reference=source['files']['controller_observations.json'],checkpoint_s=o['time_s'],
                state=o['measured_initial_state'],previous_input_n=updates[index-1]['actual_tension_n'],applied_command_n=o['actual_tension_n'],
                state_difference_from_common_preview_norm=float(np.linalg.norm(np.asarray(o['measured_initial_state'])-snap['measured_initial_state'])),
                previous_input_difference_from_common_preview_max_n=float(np.max(abs(np.asarray(updates[index-1]['actual_tension_n'])-snap['previous_input_n']))),
                selected_iteration=o['optimization_selected_iteration'],stop_reason=o['policy_stop_reason'],raw_stop=o['optimization_raw_status'],
                selected_scaled_violation=o['optimization_constraint_violation'],warm_preparation_s=o['warm_preparation_s'],
                historical_plan_availability=availability,historical_warm_plan_available=False,
                warm_policy='production workspace retains/shifts its own selected plan; exact historical warm vectors were not saved'))
    return dict(rows=rows,production=production,
        supported_inference='At .30 s common feasible regenerated cold seed satisfies weight-independent position/speed checks; callback stops at iteration zero before a weight-dependent update. No evidence that cold equality implies full-task equivalence.',
        uncertainty='Production states, previous inputs and optimizer paths differ too. Exact historical warm plans unavailable; no warm-start-only attribution.',
        additional_solves=0,additional_rollouts=0,paired_comparison_needed=False)


def execute(ctx,args):
    protocol=ctx.artifact(args.protocol);start=time.perf_counter()
    result=intervals(ctx,protocol) if protocol['operation']=='intervals' else preview(ctx,protocol)
    return DiagnosticEvidence(detail=dict(operation=protocol['operation'],result=result,complete_cost_s=time.perf_counter()-start))


def preflight(inp,args,reg):return dict(cost=dict(wall_s=600.))


DEFINITION=Extension('analysis.milestone5_diagnostic','tool','1.0.0',PreviewRequest,DiagnosticEvidence,
    'extensions.tendon_family.milestone5_diagnostic:execute','Bounded saved-evidence speed decomposition and resolution comparison.',
    sources=('extensions/tendon_family/milestone5_diagnostic.py','extensions/tendon_family/diagnostic_math.py','extensions/tendon_family/gvs_trajectory.py'),
    capabilities={'preflight':'extensions.tendon_family.milestone5_diagnostic:preflight'})
