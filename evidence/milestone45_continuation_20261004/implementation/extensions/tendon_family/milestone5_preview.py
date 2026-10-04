"""Receipt-backed, candidate-bound pilot using existing local GVS numerics."""
from copy import deepcopy
import time
import numpy as np
from schemas.common import Contract
from schemas.platform import EvidenceRef, SessionInput
from tools.platform_store import plain
from tools.state_io import digest
from tools.platform_registry import Extension
from .diagnostic_evidence import DiagnosticEvidence
from .diagnostic_math import NonlinearModel, charge_units
from .gvs_trajectory import TrajectoryWorkspace
from .control_evidence import plan_metrics
from .gvs_profile import execution_scope


class PreviewRequest(Contract):
    protocol: EvidenceRef


def physical_direction(delta,epsilon=1e-6):
    return 'improvement' if delta < -epsilon else 'worsening' if delta > epsilon else 'unresolved'


def execute(ctx,args):
    protocol=ctx.artifact(args.protocol)
    if protocol['classification']!='prospective_same_structure_control_pilot':raise ValueError('FROZEN_PILOT_PROTOCOL_REQUIRED')
    start=time.perf_counter();snapshot=protocol['snapshot'];x=snapshot['measured_initial_state'];previous=snapshot['previous_input_n'];rows=[]
    limits=protocol['limits'];deadline=start+limits['max_wall_s']
    for frozen in protocol['configurations']:
        if time.perf_counter()+65>deadline:raise RuntimeError('PILOT_TIME_ALLOWANCE')
        cfg=ctx.artifact(frozen['configuration'])['effective']
        if digest(execution_scope(cfg))!=frozen['scientific_identity']:raise ValueError('PILOT_CONFIGURATION_CHANGED')
        inp=SessionInput.model_validate(cfg);p=deepcopy(inp.policy.controller.parameters.data['recipe'])
        p['horizon']=snapshot['effective_horizon']
        charge_units(ctx,'local_solves',1);wall=time.perf_counter()
        ws=TrajectoryWorkspace(inp.task,inp.robot,p,x,previous,settling=inp.policy.controller.parameters.data['settling'])
        # Identical cold seed from the saved previous input, with model states
        # regenerated independently. Each weight configuration gets a new solve.
        solved=ws.solve(x,previous,elapsed_s=snapshot['time_s'])
        checked=ws.solver.evaluate_candidate(ws.problem,solved['result']['optimum'])
        u=np.asarray(solved['tensions'][0]);force_limits=np.asarray(protocol['force_limits_n'])
        bounded=bool(np.all(u>=-1e-8) and np.all(u<=force_limits+1e-8))
        if not checked['feasible'] or not bounded:raise ValueError('PILOT_LOCAL_COMMAND_NOT_INDEPENDENTLY_FEASIBLE')
        local=plan_metrics(ws,np.asarray(solved['states']),np.asarray(solved['tensions']),snapshot['time_s'])
        detail=ctx.save_artifact(dict(configuration=frozen,parameters=p,states=solved['states'],tensions=solved['tensions'],
            verification=checked,selected_iteration=solved['diagnostics']['selected_feasible_iteration'],
            stop_reason=solved['diagnostics']['policy_stop_reason'],local_metrics=local),'pilot_local_solve')
        charge_units(ctx,'prediction_evaluations',1)
        model=NonlinearModel(cfg,x,previous,protocol['integration_step_s'])
        trajectory=model.rollout(x,u,protocol['horizon_s'],deadline)
        rows.append(dict(**frozen,first_command_n=u.tolist(),independent_verification=checked,input_bounds_satisfied=bounded,
            plan_metrics=local,trajectory=trajectory,speed_change_m_s=trajectory[-1]['speed_m_s']-trajectory[0]['speed_m_s'],
            endpoint_speed_m_s=trajectory[-1]['speed_m_s'],position_drift_m=trajectory[-1]['displacement_m'],
            endpoint_error_m=trajectory[-1]['error_m'],calculation_s=time.perf_counter()-wall,detail=plain(detail)))
    reference=rows[0]
    for row in rows[1:]:
        row['local_candidate_minus_reference']=dict(endpoint_speed_m_s=row['endpoint_speed_m_s']-reference['endpoint_speed_m_s'],
            endpoint_error_m=row['endpoint_error_m']-reference['endpoint_error_m'],position_drift_m=row['position_drift_m']-reference['position_drift_m'])
        row['full_task_hypothesis']=dict(holding_speed_direction=physical_direction(row['local_candidate_minus_reference']['endpoint_speed_m_s']),
            holding_position_direction=physical_direction(row['local_candidate_minus_reference']['endpoint_error_m']),
            joint_acceptance='unknown',qualification='Directional extrapolation only; local endpoint is not full-task holding maximum.')
    ordering=sorted(rows[1:],key=lambda r:r['endpoint_speed_m_s'])
    resolved=len(ordering)>1 and all(abs(a['endpoint_speed_m_s']-b['endpoint_speed_m_s'])>1e-6 for a,b in zip(ordering,ordering[1:]))
    return DiagnosticEvidence(detail=dict(protocol=plain(args.protocol),model='model.gvs@1.0.0',rows=rows,
        predicted_speed_order=[r['candidate_id'] for r in ordering] if resolved else None,
        predicted_physical_order=None,physical_order_reason='Joint acceptance remains unknown; speed ordering alone cannot predict overall superiority.',
        complete_cost_s=time.perf_counter()-start,local_solves=len(rows),prediction_rollouts=len(rows),
        local_scope='Saved projected observation state; 0.01 s held candidate-specific first command after independent weight-specific solve.',
        limitations=['Common cold seed differs from full-task retained warm policy.', 'One-step local endpoint differs from complete-task maximum holding metrics.',
            'Projected GVS state and model omit backend degrees of freedom.', 'No absolute acceptance forecast or automatic screening.']))


def preflight(inp,args,reg):
    return dict(cost=dict(wall_s=300.))


DEFINITION=Extension('analysis.milestone5_preview','tool','1.0.0',PreviewRequest,DiagnosticEvidence,
    'extensions.tendon_family.milestone5_preview:execute','Bounded prospective candidate control comparison from one sealed observation snapshot.',
    sources=('extensions/tendon_family/milestone5_preview.py','extensions/tendon_family/diagnostic_math.py',
        'extensions/tendon_family/gvs_trajectory.py','extensions/tendon_family/control_evidence.py'),
    dependencies=('numpy','scipy','casadi'),side_effects='artifact_store',
    capabilities=dict(backend_solves=0,preflight='extensions.tendon_family.milestone5_preview:preflight'))
