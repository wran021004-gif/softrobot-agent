"""Explicit cross-session imports and compact saved evidence, without a solve."""
from copy import deepcopy
import json
import numpy as np
from pydantic import Field
from schemas.common import Contract
from schemas.platform import EvidenceRef
from tools.platform_store import plain
from tools.state_io import digest
from .control_evidence import ControlEvidence, EvidenceQuery


class BoundQuery(Contract):
    binding: EvidenceRef
    view: str = Field(description='summary, motion, prediction, plans, or comparable')
    update_ids: list[int] = Field(default_factory=list,max_length=8)


class DiagnosticEvidence(Contract):
    detail: dict


def import_execution(reader, execution_id, destination, run_id, expected_manifest=None):
    source=reader.resolve(execution_id)
    if expected_manifest is not None and plain(expected_manifest)!=source['manifest']:
        raise ValueError('EXECUTION_MANIFEST_OWNERSHIP_MISMATCH')
    cfg=source['configuration']
    refs=[source['manifest'],source['metadata']['candidate_input'],
        dict(artifact_id=source['metadata']['artifact_id'],media_type='application/json'),*source['files'].values()]
    with destination.transaction() as db:
        for ref in refs:
            copied=destination.put(db,reader.store.artifact(ref,raw=True),ref['media_type'])
            if plain(copied)!=ref: raise ValueError('IMPORT_HASH_MISMATCH')
        binding=dict(schema_version='1.0.0',execution_id=execution_id,owner_run_id=source['owner'],
            source_project_id=reader.store.config()['project_id'],source_store=str(reader.store.root),
            candidate_id=source['metadata']['candidate'],configuration=source['metadata']['candidate_input'],
            evidence_manifest=source['manifest'],task_identity=digest(cfg['task']),controller_identity=digest(cfg['policy']['controller']),
            source=source,classification='Imported immutable evidence; original execution ownership is unchanged')
        ref=destination.put(db,binding)
        destination.event(db,run_id,'cross_session_evidence','bound',inputs=[source['manifest']],outputs=[ref])
    return plain(ref)


class BoundReader(ControlEvidence):
    def __init__(self,store,binding):
        super().__init__(store);self.binding=store.artifact(binding)
        required={'execution_id','owner_run_id','configuration','evidence_manifest','source','task_identity','controller_identity'}
        if not isinstance(self.binding,dict) or not required<=self.binding.keys():
            raise ValueError('EXPLICIT_EXECUTION_BINDING_REQUIRED: pass the imported binding, not a query result reference')
    def resolve(self,execution_id):
        b=self.binding;s=deepcopy(b['source'])
        if (execution_id!=b['execution_id'] or s['execution_id']!=execution_id or s['owner']!=b['owner_run_id']
                or s['manifest']!=b['evidence_manifest'] or s['metadata']['candidate']!=b['candidate_id']
                or s['metadata']['candidate_input']!=b['configuration']):
            raise ValueError('BOUND_EXECUTION_IDENTITY_MISMATCH')
        bundle=self.store.artifact(s['manifest'])
        if bundle['result']['artifact_id']!=s['metadata']['artifact_id'] or {f['filename']:f['reference'] for f in bundle['files']}!=s['files']:
            raise ValueError('BOUND_MANIFEST_CONTENT_MISMATCH')
        effective=self.store.artifact(b['configuration'])['effective']
        if effective!=s['configuration'] or digest(effective['task'])!=b['task_identity'] or digest(effective['policy']['controller'])!=b['controller_identity']:
            raise ValueError('BOUND_CONFIGURATION_MISMATCH')
        return s


def measured_motion(reader,source):
    """World Jacobian at recorded serial backend q, qdot. No stepping/solver."""
    import mujoco
    rows=reader.read_file(source,'trajectory.json.gz',[])
    physics=reader.read_file(source,'resolved_physics.json')
    model=mujoco.MjModel.from_xml_string(reader.store.artifact(source['files']['robot.xml'],raw=True).decode('utf8'))
    data=mujoco.MjData(model)
    ids=[model.joint(j).id for j in physics['dofs']]
    qi=model.jnt_qposadr[ids];vi=model.jnt_dofadr[ids]
    target=np.array(source['configuration']['task']['goal']['data']['target_m'])
    motion=[]
    for row in rows:
        data.qpos[qi]=row['qpos_rad'];data.qvel[vi]=row['qvel_rad_s'];mujoco.mj_forward(model,data)
        J=np.zeros((3,model.nv));Jr=np.zeros_like(J)
        mujoco.mj_jacSite(model,data,J,Jr,model.site('tip_site').id)
        velocity=J@data.qvel
        motion.append(dict(time_s=row['time_s'],position_m=row['tip_m'],
            velocity_m_s=velocity.tolist(),speed_m_s=float(np.linalg.norm(velocity)),
            error_m=float(np.linalg.norm(np.array(row['tip_m'])-target)),
            reconstructed_position_difference_m=float(np.linalg.norm(data.site_xpos[model.site('tip_site').id]-row['tip_m']))))
    return motion


def add_velocity_comparisons(comparisons,updates,motion):
    for row in comparisons:
        predicted=updates[row['update_id']]['one_step_prediction'].get('tip_velocity_m_s')
        actual=[m for m in motion if abs(m['time_s']-row['end_s'])<1e-8]
        if predicted is None or len(actual)!=1:
            row['velocity']=dict(status='missing',reason='one-step vector or matched backend state unavailable');continue
        measured=actual[0]['velocity_m_s']
        row['velocity']=dict(status='aligned',frame='world',predicted_m_s=predicted,measured_m_s=measured,
            vector_difference_norm_m_s=float(np.linalg.norm(np.array(predicted)-measured)),
            predicted_speed_m_s=float(np.linalg.norm(predicted)),measured_speed_m_s=float(np.linalg.norm(measured)),
            prediction_method='directly recorded accepted first-step endpoint velocity',
            measurement_method='deterministically reconstructed J_site(q_backend) @ qdot_backend using sealed robot.xml and recorded serial joint order',
            scope='Matched next timestamp and applied input; projected GVS prediction versus full serial-backend endpoint, not full state agreement')
    return comparisons


def inspect(reader,binding,args):
    b=reader.binding;s=reader.resolve(b['execution_id']);cfg=s['configuration'];task=cfg['task']
    updates=reader.read_file(s,'controller_observations.json',[])
    motion=measured_motion(reader,s)
    settling=cfg['policy']['controller']['parameters']['data']['settling']
    late=[m for m in motion if m['time_s']>=task['timing']['duration_s']-settling['window_s']-1e-8]
    selected=args.update_ids or list(dict.fromkeys([min(range(len(updates)),key=lambda i:abs(updates[i]['time_s']-late[0]['time_s'])),len(updates)-1]))
    summary=dict(execution_id=b['execution_id'],owner_run_id=b['owner_run_id'],binding=plain(binding),
        configuration=b['configuration'],manifest=b['evidence_manifest'],controller=cfg['policy']['controller'],
        complete=abs(motion[-1]['time_s']-task['timing']['duration_s'])<1e-8,
        terminal_error_m=motion[-1]['error_m'],reach_tolerance_m=task['evaluator']['parameters']['data']['tolerance_m'],
        terminal_speed_m_s=motion[-1]['speed_m_s'],late_max_error_m=max(m['error_m'] for m in late),
        late_max_speed_m_s=max(m['speed_m_s'] for m in late),settling_criteria=settling,
        mean_update_s=float(np.mean([u['update_wall_s'] for u in updates])),control_period_s=task['timing']['control_period_s'],
        deadline_misses=sum(u['deadline_missed'] for u in updates),
        initialization_selected=sum(u['optimization_selected_iteration'] in (-1,0) for u in updates),
        noninitialization_selected=sum(u['optimization_selected_iteration'] not in (-1,0,None) for u in updates),
        full_snapshots_available='control_snapshots.json' in s['files'],
        stopping_counts={k:sum(u['optimization_raw_status']==k for u in updates) for k in sorted({u['optimization_raw_status'] for u in updates})})
    summary['reach_passed']=summary['complete'] and summary['terminal_error_m']<=summary['reach_tolerance_m']
    summary['sampled_settling_passed']=summary['late_max_error_m']<=settling['position_limit_m'] and summary['late_max_speed_m_s']<=settling['speed_limit_m_s']
    detail=dict(summary=summary,source_selectors=dict(state_file=s['files']['controller_observations.json'],
        state_pointer_template='/{update_id}/measured_initial_state',input_pointer_template='/{update_id}/actual_tension_n'),
        limitations=['No historical optimizer iterations or full warm plans are reconstructed.',
            'Single execution and model comparisons do not establish a dominant cause.'])
    if args.view=='motion':detail['late_motion']=late
    elif args.view in ('plans','prediction'):
        evidence=plain(reader.query(EvidenceQuery(execution_id=b['execution_id'],operation='prediction' if args.view=='prediction' else 'plans',update_ids=selected)))
        if args.view=='prediction':
            add_velocity_comparisons(evidence['observations']['aligned_intervals'],updates,motion)
        for item in evidence['observations']['updates']:
            u=updates[item['update_id']]
            item.update(requested_input_n=u.get('requested_tension_n'),returned_constraint_violation=u.get('optimization_returned_violation'),
                selected_constraint_violation=u.get('optimization_constraint_violation'),effective_horizon=u.get('effective_horizon'))
        detail['evidence']={k:evidence[k] for k in ('observations','capabilities','ownership')}
        # The exact controller is already in the summary view and configuration.
        # Keep a default two-update prediction directly readable in the 8 KiB
        # Host observation envelope, without dropping measured velocity vectors.
        detail['summary']={k:v for k,v in summary.items() if k!='controller'}
    elif args.view=='comparable':
        from tools.spec_tools import ROOT
        from tools.platform_store import Store
        from tools.state_io import read
        from .control_evidence import ExecutionComparison
        cases=[]
        for entry in read(ROOT/'evidence/control_evidence_catalog.json')['sources']:
            other=Store(ROOT/entry['store'])
            if not other.db.is_file():continue
            with other.connect(True) as db:
                ids=[eid for r in db.execute('SELECT state FROM sessions') for eid in json.loads(r['state']).get('result_executions',{})]
            for eid in ids[-2:]:
                if eid==b['execution_id']:continue
                candidate=ControlEvidence(other)
                comparison=reader.compare(ExecutionComparison(baseline_execution_id=b['execution_id'],variant_execution_id=eid,changed_factor='controller'),candidate)
                cases.append(dict(source_store=entry['store'],comparison=comparison))
        detail['saved_case_comparisons']=cases
        detail['screening_policy']='No ranking/exclusion changes. Controller or physical-design mismatches prevent treating these cases as a matched design-ranking dataset.'
    elif args.view!='summary':raise ValueError('UNKNOWN_EVIDENCE_VIEW')
    return DiagnosticEvidence(detail=detail)


def inspect_tool(ctx,args):
    result=inspect(BoundReader(ctx.store,args.binding),args.binding,args)
    with ctx.store.transaction() as db:
        state=ctx.store.session(ctx.run_id,db)['state']
        if state.get('role_context'):
            ref=ctx.store.put(db,result)
            views=state['role_context'].setdefault('evidence_views',[])
            views.append(dict(view=args.view,update_ids=args.update_ids,reference=plain(ref),summary=result.detail['summary']))
            state['role_context']['evidence_views']=views[-8:]
            ctx.store.update_state(db,ctx.run_id,state)
    return result
