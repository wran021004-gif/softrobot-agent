"""Deterministic, owned control evidence. Inspection never starts a solver."""
from __future__ import annotations

import gzip
import json
from contextvars import ContextVar
from typing import Literal

import numpy as np
from pydantic import Field
from schemas.common import Contract
from schemas.platform import EvidenceRef
from tools.platform_store import plain
from tools.state_io import digest

RECORD_UPDATE_IDS = ContextVar('control_evidence_update_ids', default=())
# Optional evidence capture after actuator application and before backend stepping.
# The observer cannot supply a command or alter controller selection.
PRE_STEP_OBSERVER = ContextVar('control_evidence_pre_step_observer', default=None)


class EvidenceQuery(Contract):
    execution_id: str
    operation: Literal['inspect', 'plans', 'prediction'] = 'inspect'
    update_ids: list[int] = Field(default_factory=list, max_length=8)
    snapshot_id: str | None = None
    export_manifest: EvidenceRef | None = Field(default=None,description='Optional exact immutable simulation export reference; checked against execution ownership.')


class EvidenceSummary(Contract):
    schema_version: str = '1.0.0'
    ownership: dict
    identities: dict
    observations: dict
    references: dict
    capabilities: dict
    comparability: dict
    classification: str = 'recorded quantities summarized; no new solve or reconstructed history'


class ExecutionComparison(Contract):
    baseline_execution_id: str
    variant_execution_id: str
    changed_factor: Literal['recording', 'controller', 'design']


def decode_plan(workspace, vector, order):
    values = dict(zip(order, vector)); n = workspace.n
    steps = workspace.parameters.horizon * workspace.parameters.substeps
    states = np.array([[values[f'x/{k}/{j}'] * workspace.state_scales[j]
        for j in range(2*n)] for k in range(steps+1)])
    tensions = np.array([[values[f'u/{k}/{t}'] for t in workspace.tendons]
        for k in range(workspace.parameters.horizon)])
    previous = np.array([values['previous_u/'+t] for t in workspace.tendons])
    return states, tensions, previous


def objective_components(ws, states, tensions, previous):
    p=ws.parameters; h=ws.period/p.substeps
    scale=p.position_error_scale_m or ws.goal_tolerance
    result=dict(running_position=0., running_curvature_rate=0., running_tension=0.,
        running_tension_variation=0., terminal_position=0., terminal_curvature_rate=0.,
        terminal_tip_speed=0., holding_tip_speed=0.)
    for k,state in enumerate(states[1:],1):
        tip,speed=ws._motion(state[:ws.n],state[ws.n:])
        result['running_position']+=h*p.tracking_weight*float(np.sum((np.asarray(tip).ravel()-ws.target)**2/scale**2))
        result['running_curvature_rate']+=h*p.velocity_weight*float(np.sum(state[ws.n:]**2))
        if p.holding_tip_speed_weight:
            active=ws.problem.initial_guess[f'holding/{k}']
            result['holding_tip_speed']+=h*p.holding_tip_speed_weight*active*float(np.sum(np.asarray(speed)**2/p.tip_speed_scale_m_s**2))
    for k,u in enumerate(tensions):
        result['running_tension']+=ws.period*p.tension_weight*float(np.sum(u**2))
        result['running_tension_variation']+=ws.period*p.variation_weight*float(np.sum((u-(previous if k==0 else tensions[k-1]))**2))
    terminal=states[-1];tip,speed=ws._motion(terminal[:ws.n],terminal[ws.n:])
    result['terminal_position']=p.terminal_weight*float(np.sum((np.asarray(tip).ravel()-ws.target)**2/scale**2))
    result['terminal_curvature_rate']=p.terminal_velocity_weight*float(np.sum(terminal[ws.n:]**2))
    result['terminal_tip_speed']=p.terminal_tip_speed_weight*float(np.sum(np.asarray(speed)**2/p.tip_speed_scale_m_s**2))
    result['total']=sum(result.values())
    return result


def plan_metrics(ws, states, tensions, time_s):
    times=time_s+np.arange(len(states))*ws.period/ws.parameters.substeps
    motion=[]
    for t,x in zip(times,states):
        tip,velocity=ws._motion(x[:ws.n],x[ws.n:]);tip=np.asarray(tip).ravel();velocity=np.asarray(velocity).ravel()
        motion.append(dict(time_s=float(t), position_error_m=float(np.linalg.norm(tip-ws.target)),
            tip_position_m=tip.tolist(),
            tip_velocity_m_s=velocity.tolist(),tip_speed_m_s=float(np.linalg.norm(velocity))))
    deadline=next((m for m in motion if abs(m['time_s']-ws.duration)<1e-8),None)
    return dict(deadline=deadline, deadline_status='within_recorded_horizon' if deadline else 'outside_recorded_horizon',
        terminal=motion[-1], first_step=motion[ws.parameters.substeps],
        horizon_interval_s=[float(times[0]),float(times[-1])],
        first_input_n=tensions[0].tolist(),input_min_n=tensions.min(axis=0).tolist(),input_max_n=tensions.max(axis=0).tolist())


def capture_snapshot(ws, solved, update_id, time_s, command, geometry):
    """Runs after selection; bounded trace retains <=5 vectors, not every iterate."""
    from copy import deepcopy
    d=solved['diagnostics'];plans={}
    for point in d['retained_diagnostic_points']:
        states,tensions,previous=decode_plan(ws,point['vector'],d['variable_order'])
        components=objective_components(ws,states,tensions,previous)
        plans[point['label']]=dict(states=states.tolist(),tensions=tensions.tolist(),
            metrics=plan_metrics(ws,states,tensions,time_s),
            verification={k:v for k,v in point.items() if k!='vector'},
            objective_components=components,objective_component_difference=components['total']-point['objective'])
    recovery=solved.get('recovery',{})
    def add_plan(label,values):
        states,tensions,previous=decode_plan(ws,[values[k] for k in d['variable_order']],d['variable_order'])
        check=ws.solver.evaluate_candidate(ws.problem,values)
        plans[label]=dict(states=states.tolist(),tensions=tensions.tolist(),
            metrics=plan_metrics(ws,states,tensions,time_s),verification={k:v for k,v in check.items() if k!='constraint_values'},
            objective_components=objective_components(ws,states,tensions,previous))
    if recovery.get('candidate_optimum'):add_plan('regenerated',recovery['candidate_optimum'])
    add_plan('delivered',solved['result']['optimum'])
    value=dict(schema_version='1.0.0',update_id=update_id,time_s=float(time_s),
        classification='new recorded control snapshot',measured_initial_state=solved['measured_initial_state'],
        previous_applied_input_n=solved['previous_tensions_n'],warm=solved['recording'],plans=plans,
        selection=dict(accepted=solved['accepted'],selected_iteration=None if recovery.get('selected') else d['selected_feasible_iteration'],
            ipopt_selected_iteration=d['selected_feasible_iteration'],delivered_plan='delivered',
            source='reintegrated_returned_iterate' if recovery.get('selected') else 'ipopt_selected',
            reason=d['policy_stop_reason'],raw_stop=d['return_status']),
        actual_executed_input_n=list(command),iteration_trace=deepcopy(d['iteration_trace']),
        numerical_parameters=ws.parameters.model_dump(mode='json'),prediction_timing=solved['prediction_timing'],
        model=dict(id='model.gvs@1.0.0',basis=plain(ws.parameters.basis),
            integration=solved['integration'],period_s=ws.period,substeps=ws.parameters.substeps),
        residual_definitions=dict(feasible_max_scaled=1e-5,initial='(x - measured)/decision_state_scale',
            kinematic='(q_next-q_previous-h*qdot_next)/10 rad/m',
            dynamic='implicit mass/force residual / 0.001 N*m^2/rad',
            input_bounds='tension residual / 1 N',state_scales=ws.state_scales.tolist(),
            physical_conversion='multiply each scaled residual by its stated denominator'),
        projection=deepcopy(geometry['gvs_projection']),
        timing_s=dict(preparation=solved['warm_start']['preparation_s'],solver=d['solve_s'],
            validation=d['validation_s'],solver_construction=d['construction_s'],
            snapshot_verification=d.get('diagnostic_verification_s',0.),
            callback_recording=d.get('diagnostic_callback_s',0.),workspace_update=solved['update_wall_s']),
        function_statistics=d['function_statistics'])
    value['snapshot_id']=digest(value)
    return value


class ControlEvidence:
    """Uses sealed simulation export manifests and immutable artifact references."""
    def __init__(self, store):
        self.store=store

    def resolve(self, execution_id):
        matches=[]
        with self.store.connect(True) as db:
            for row in db.execute('SELECT run_id,state FROM sessions'):
                state=json.loads(row['state']);metadata=state.get('result_executions',{}).get(execution_id)
                if metadata:matches.append((row['run_id'],metadata))
        if len(matches)!=1:raise ValueError('UNIQUE_OWNED_EXECUTION_REQUIRED')
        owner,metadata=matches[0];bundle=None;bundle_ref=None
        for event in self.store.events(owner):
            if event['kind']=='simulation' and event['execution_id']==execution_id:
                for ref in event['outputs']:
                    if ref['media_type']=='application/json':
                        value=self.store.artifact(ref)
                        if isinstance(value,dict) and 'files' in value and value.get('result',{}).get('artifact_id')==metadata['artifact_id']:
                            bundle=value;bundle_ref=ref
        if bundle is None:raise ValueError('SEALED_SIMULATION_EXPORT_MANIFEST_REQUIRED')
        files={f['filename']:f['reference'] for f in bundle['files']}
        config=self.store.artifact(metadata['candidate_input'])['effective']
        return dict(owner=owner,execution_id=execution_id,metadata=metadata,files=files,
            manifest=bundle_ref,configuration=config)

    def read_file(self, source, name, default=None):
        ref=source['files'].get(name)
        if ref is None:return default
        body=self.store.artifact(ref,raw=True)
        return json.loads(gzip.decompress(body) if name.endswith('.gz') else body)

    def query(self, query: EvidenceQuery) -> EvidenceSummary:
        s=self.resolve(query.execution_id);cfg=s['configuration'];p=cfg['policy'];task=cfg['task']
        if query.export_manifest is not None and plain(query.export_manifest)!=s['manifest']:
            raise ValueError('EXECUTION_MANIFEST_OWNERSHIP_MISMATCH')
        updates=self.read_file(s,'controller_observations.json',[])
        selected=(query.update_ids or list(dict.fromkeys([0,len(updates)-1]))) if updates else query.update_ids
        snapshots=self.read_file(s,'control_snapshots.json',[])
        if query.snapshot_id:
            found=[r for r in snapshots if r['snapshot_id']==query.snapshot_id]
            if len(found)!=1:raise ValueError('OWNED_SNAPSHOT_NOT_FOUND')
            selected=[found[0]['update_id']]
        records=[];missing=[]
        for index in selected:
            if index<0 or index>=len(updates):missing.append(f'update:{index}');continue
            row=updates[index];snap=next((v for v in snapshots if v['update_id']==index),None)
            item=dict(update_id=index,time_s=row['time_s'],
                selection={k:row.get(k) for k in ('plan_accepted','optimization_selected_iteration','optimization_raw_status','policy_stop_reason')},
                timing_s={k:row.get(k) for k in ('update_wall_s','state_preparation_s','warm_preparation_s','optimization_solve_s','plan_validation_s','snapshot_capture_wall_s')},
                projection_residual_rad_m=row.get('gvs_projection_residual_max_rad_m'),
                actual_input_n=row.get('actual_tension_n'),snapshot_id=None if snap is None else snap['snapshot_id'])
            if snap:
                item['plans']={role:{k:v for k,v in value.items() if k not in ('states','tensions')}
                    for role,value in snap['plans'].items() if role in ('initial','selected','returned','regenerated','delivered')}
                item['additional_checkpoint_roles']=[role for role in snap['plans'] if role.startswith('checkpoint')]
                item['residual_definitions']=snap['residual_definitions']
                item['first_command_change_from_initialization_n']=float(np.max(np.abs(
                    np.asarray(snap['plans'].get('delivered',snap['plans']['selected'])['metrics']['first_input_n'])-snap['plans']['initial']['metrics']['first_input_n'])))
            else:missing.append(f'update:{index}:complete_warm_and_plans')
            records.append(item)
        observations=dict(updates=records,total_updates=len(updates),initialization_selected=sum(
            r.get('optimization_selected_iteration') in (-1,0) for r in updates))
        if query.operation=='prediction':
            rows=self.read_file(s,'trajectory.json.gz',[])
            commands=self.read_file(s,'actual_commands.json',[])
            comparisons,alignment_missing=aligned_interval_predictions(rows,updates,commands,
                task['timing']['control_period_s'],task['goal']['data']['target_m'],selected)
            observations['aligned_intervals']=comparisons;missing.extend(alignment_missing)
            for row in comparisons:
                prediction=updates[row['update_id']]['one_step_prediction']
                following=next((u for u in updates if abs(u['time_s']-row['end_s'])<1e-8),None)
                state=prediction.get('state')
                if following is not None and state is not None:
                    actual=following['measured_initial_state'];n=len(state)//2
                    row['projected_state_difference']=dict(curvature_linf_rad_m=float(np.max(np.abs(np.asarray(state[:n])-actual[:n]))),
                        rate_linf_rad_m_s=float(np.max(np.abs(np.asarray(state[n:])-actual[n:]))),
                        classification='recorded projected states, not full backend-state error')
                else:row['projected_state_difference']=dict(status='missing',reason='next projected state unavailable; endpoint comparison remains available')
        from .gvs_profile import execution_scope
        return EvidenceSummary(ownership=dict(execution_id=query.execution_id,owner_run_id=s['owner'],candidate_id=s['metadata']['candidate']),
            identities=dict(execution_scope=execution_scope(cfg),configuration=s['metadata']['candidate_input']),
            observations=observations,references=dict(manifest=s['manifest'],files=s['files']),
            capabilities=dict(available=['saved_execution','selected_update','aligned_one_step']+(['complete_plans'] if snapshots else []),
                missing=missing,unsupported=['causal_identification','historical_unrecorded_horizons']),
            comparability=dict(frame='world',prediction='same update, next sample, same actually executed input only',
                deadline_s=task['timing']['duration_s'],full_state='Projected GVS state; endpoint and projection residuals are separate'))

    def compare(self, request: ExecutionComparison, variant_reader=None):
        from .gvs_profile import execution_scope
        variant_reader=variant_reader or self
        a=self.resolve(request.baseline_execution_id);b=variant_reader.resolve(request.variant_execution_id)
        scopes=[execution_scope(s['configuration']) for s in (a,b)]
        mismatches=[key for key in scopes[0] if scopes[0][key]!=scopes[1][key]]
        allowed={'recording':set(),'controller':{'controller'},'design':{'robot'}}[request.changed_factor]
        unexpected=[key for key in mismatches if key not in allowed]
        def metrics(reader,s):
            rows=reader.read_file(s,'trajectory.json.gz',[]);updates=reader.read_file(s,'nmpc_updates.json',[])
            task=s['configuration']['task'];target=task['goal']['data']['target_m']
            complete=bool(rows and abs(rows[-1]['time_s']-task['timing']['duration_s'])<1e-8)
            return dict(complete=complete,terminal_error_m=float(np.linalg.norm(np.asarray(rows[-1]['tip_m'])-target)) if complete else None,
                mean_complete_update_s=float(np.mean([u['update_wall_s'] for u in updates])) if updates else None)
        return dict(schema_version='1.0.0',classification='recorded cross-execution comparison; no causal or repeatability claim',
            ownership=[dict(execution_id=s['execution_id'],owner_run_id=s['owner']) for s in (a,b)],
            declared_changed_factor=request.changed_factor,matching_conditions=scopes,
            material_mismatches=mismatches,unexpected_mismatches=unexpected,comparable=not unexpected,
            baseline=metrics(self,a),variant=metrics(variant_reader,b),references=[s['manifest'] for s in (a,b)])


def aligned_interval_predictions(rows, updates, commands, period, target, selected):
    """Fail closed on timestamps, phase, or commands; never compare old distant endpoints."""
    from .gvs_reporting import aligned_predictions
    good=[];missing=[]
    comparisons,absent=aligned_predictions(rows,updates)
    for i in selected:
        if i<0 or i>=len(updates):continue
        o=updates[i];t=o['time_s'];pred=o.get('one_step_prediction')
        cmd=[c for c in commands if abs(c['time_s']-t)<1e-8]
        reason=None
        if o.get('phase')!='current_state_before_integration':reason='unsupported initial phase'
        elif pred is None or abs(pred['time_s']-t-period)>1e-8:reason='one-update prediction timestamp missing/mismatch'
        elif len(cmd)!=1 or o.get('actual_tension_n') is None:reason='actual command missing/ambiguous'
        elif not np.allclose(cmd[0]['desired_tension_n'],o['actual_tension_n'],rtol=0,atol=1e-8):reason='command record mismatch'
        elif o.get('requested_tension_n') is not None and not np.allclose(o['requested_tension_n'],o['actual_tension_n'],rtol=0,atol=1e-8):reason='proposed prediction input differs from executed input'
        if reason:missing.append(dict(update_id=i,reason=reason));continue
        match=next((r for r in comparisons if abs(r['start_s']-t)<1e-8),None)
        if match is None:
            missing.extend(dict(update_id=i,**r) for r in absent if abs(r['time_s']-t)<1e-8);continue
        start_error=float(np.linalg.norm(np.asarray(o['tip_position_m'])-target))
        match.update(update_id=i,start_error_m=start_error,
            predicted_next_error_m=float(np.linalg.norm(np.asarray(match['predicted_tip_m'])-target)),
            actual_next_error_m=float(np.linalg.norm(np.asarray(match['measured_tip_m'])-target)),
            actual_error_change_m=float(np.linalg.norm(np.asarray(match['measured_tip_m'])-target))-start_error,
            definition='Euclidean world-tip difference at t+period under matching recorded interval input; negative error change is progress')
        good.append(match)
    return good,missing


def inspect_tool(ctx,args):
    return ControlEvidence(ctx.store).query(args)


def inspection_preflight(inp,args,reg):
    return dict(cost=dict(wall_s=30.))


def compare_tool(ctx,args):
    from .gvs_profile import ProfileOutput
    return ProfileOutput(detail=ControlEvidence(ctx.store).compare(args))
