"""Small adapters for a bounded, model-directed initialization diagnosis."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import tarfile
import time
import numpy as np
from schemas.platform import EvidenceRef
from tools.platform_store import Store,plain,encode
from tools.state_io import atomic_json,read
from tools.spec_tools import ROOT
from extensions.tendon_family.control_evidence import ControlEvidence
from extensions.tendon_family.diagnostic_evidence import import_execution,BoundReader,measured_motion
from extensions.tendon_family.diagnostic_math import changed_recipe,recipe_value

SOURCE=ROOT/'evidence/casadi_nmpc_research_20261010'
EXECUTION='21b607607bf442a6b6d9494dda897ea8'
CANDIDATE='0e16077e9183ebcd64729eb982aa5a73e5eb03e111d5d7ed402552ca16db345b'
INSTRUCTIONS='''You are the sole research principal. Diagnose initialization-dominated NMPC with the supplied factual packet. Codex supplies interfaces and arithmetic; you choose hypotheses, saved states, comparisons and whether a targeted closed-loop revision is justified. Native research_plan actions: diagnose (read-only synthesis), saved_state_comparison (comparison.update_id 1..34, changed_parameter and changed_value, max_wall_s <=300), control_revision (same immutable candidate, preceding_execution is imported baseline reference, explain the observed mechanism, one changed factor), stop. inspect_execution reads selected saved evidence; evidence_read reads immutable JSON pointers. At most two representative saved states total, two pairs/four local NLP attempts, one new simulation. All pairs use a new common constant-previous-input seed with regenerated model states; historical warm plans are missing. Local comparison factors: feasible_return.budget_s 15..30 (baseline15); either existing speed weight .025.. .10 individually; substeps1->2 only with discretization evidence. CPU30s, iteration120, relative improvement .1, minimum5s and all other recipe settings remain fixed. If another condition stops a solve before the feasible-return budget triggers, report the actual reason and do not conclude extending the budget is ineffective. Never automatically lift another limit. Local feasibility is not success; never select infeasible plans. The old simulation is synchronous: slow computation did not skip virtual actions. Initial .2N is a numerical guess, not equilibrium. Holding first appears in the horizon at .20s; shortening starts .26s, changed action .30s. Do not predetermine weights/optimizer/model/structure as cause. Every experiment needs hypothesis, supporting evidence, expected and weakening observations, fixed conditions, explicit factor/state, budget and revision_or_stop_rule. Consume each actual result before deciding another experiment. A closed-loop revision needs observed supporting mechanism and control.record_update_ids up to two already selected diagnostic states, with ordinary observations all35. Budget ceilings not quotas: pairs300s each including preparation and validation, simulation1800s/evaluation30/profile60, total scientific/check/recovery3600s,16 actual provider sends last4 protected,64 public calls,6h total final30min delivery,zero full-horizon codesign/BDF/hardware/additional models. Fixed physical problem and acceptance are in specification. A useful local result is not closed-loop improvement. STOP must cite all new results; optional early STOP is allowed. Distinguish numerical feasibility, optimizer progress, plan selection, projection disagreement, prediction disagreement, task acceptance, engineering failures and missing history. No unique cause, structural impossibility or LLM superiority claim. Original model decisions stay separate from factual corrections. STOP seals further sends.'''


class ArchiveStore:
    """Read committed immutable blobs; never reconstruct a simulation."""
    def __init__(self):
        manifest=read(SOURCE/'archive_manifest.json')
        body=(SOURCE/'immutable_artifacts.tar.gz').read_bytes()
        if hashlib.sha256(body).hexdigest()!=manifest['archive_sha256']:raise ValueError('ARCHIVE_HASH_MISMATCH')
        self.root=SOURCE;self.values={}
        with tarfile.open(SOURCE/'immutable_artifacts.tar.gz','r:gz') as archive:
            for member in manifest['members']:
                raw=archive.extractfile(member['name']).read()
                if hashlib.sha256(raw).hexdigest()!=member['sha256']:raise ValueError('ARCHIVE_MEMBER_HASH_MISMATCH')
                self.values[member['sha256']]=raw
    def artifact(self,ref,raw=False):
        ref=plain(ref);value=self.values[ref['artifact_id']]
        return value if raw or ref['media_type']!='application/json' else json.loads(value)
    def config(self):return {'project_id':'casadi-nmpc-research-20261010'}


class ArchiveReader(ControlEvidence):
    def resolve(self,execution_id):
        if execution_id!=EXECUTION:raise ValueError('ORIGINAL_EXECUTION_REQUIRED')
        state=read(SOURCE/'state.json');row=next(r for r in state['results'] if r['operation']=='closed_loop')
        result=self.store.artifact(row['reference']);refs=result['execution_references'];sim=refs['receipts']['simulation']
        candidate_input=refs['executed_configuration'];candidate=self.store.artifact(candidate_input)
        manifests=[]
        for aid,body in self.store.values.items():
            try:value=json.loads(body)
            except (ValueError,UnicodeDecodeError):continue
            if isinstance(value,dict) and value.get('result')==sim['output'] and 'files' in value:
                manifests.append((dict(artifact_id=aid,media_type='application/json'),value))
        if len(manifests)!=1:raise ValueError('UNIQUE_ARCHIVED_EXPORT_REQUIRED')
        ref,bundle=manifests[0]
        return dict(owner=refs['owner_run_id'],execution_id=EXECUTION,
            metadata=dict(artifact_id=sim['output']['artifact_id'],candidate=candidate['candidate_id'],candidate_input=candidate_input),
            manifest=ref,files={f['filename']:f['reference'] for f in bundle['files']},configuration=candidate['effective'])


def prepare_evidence(h):
    if h.store.session(h.run_id)['state'].get('initialization_diagnosis'):return
    start=time.perf_counter()
    try:return _prepare_evidence(h)
    finally:
        with h.store.transaction() as db:
            state=h.store.session(h.run_id,db)['state'];elapsed=time.perf_counter()-start
            state['numerical_s']+=elapsed
            state.setdefault('evidence_preparation_costs_s',[]).append(elapsed)
            h.store.update_state(db,h.run_id,state)


def _prepare_evidence(h):
    start=time.perf_counter()
    state=h.store.session(h.run_id)['state']
    if state.get('initialization_diagnosis'):return
    old=read(SOURCE/'state.json')
    archive=ArchiveStore()
    # Import all source blobs by hash, including plans, corrections and candidate provenance.
    with h.store.transaction() as db:
        for item in read(SOURCE/'archive_manifest.json')['members']:
            copied=h.store.put(db,archive.values[item['sha256']],item['media'])
            if copied.artifact_id!=item['sha256']:raise ValueError('IMPORT_HASH_MISMATCH')
    local=ROOT.parent/'casadi-nmpc-research/runs/casadi-nmpc-research-20261010'
    reader=ControlEvidence(Store(local)) if (local/'platform.sqlite').is_file() else ArchiveReader(archive)
    binding=import_execution(reader,EXECUTION,h.store,h.run_id)
    bound=BoundReader(h.store,EvidenceRef.model_validate(binding));source=bound.resolve(EXECUTION)
    timeline=make_timeline(bound,source)
    baseline=next(r for r in old['results'] if r['operation']=='closed_loop')
    correction=read(SOURCE/'post_stop_correction.json')
    with h.store.transaction() as db:
        state=h.store.session(h.run_id,db)['state']
        state.update(initialization_diagnosis=True,source_binding=binding,selected_states=[],paired_comparisons=0,
            factual_packet_reference=plain(h.store.put(db,timeline)),
            source_correction_reference=plain(h.store.put(db,correction)),
            source_baseline_reference=baseline['reference'])
        state['results'].append(dict(baseline,imported=True,source_activity=old['pilot']['activity_id']))
        state['candidate_sources']=deepcopy(old['candidate_sources'])
        h.store.update_state(db,h.run_id,state)
        db.execute("INSERT INTO meta VALUES ('diagnostic_work',?)",(encode(dict(limits=dict(local_solves=4,prediction_evaluations=0),used=dict(local_solves=0,prediction_evaluations=0))),))
    atomic_json(ROOT/'evidence/nmpc_initialization_20261010/saved_timeline.json',timeline)
    atomic_json(ROOT/'evidence/nmpc_initialization_20261010/source_binding.json',h.store.artifact(binding))


def make_timeline(reader,source):
    from extensions.tendon_family.gvs_reporting import aligned_predictions
    updates=reader.read_file(source,'controller_observations.json',[])
    trajectory=reader.read_file(source,'trajectory.json.gz',[])
    measured=measured_motion(reader,source)
    motion=[dict(time_s=m['time_s'],tip_velocity_m_s=m['velocity_m_s']) for m in measured]
    comparisons,missing=aligned_predictions(trajectory,updates,motion)
    snapshots=reader.read_file(source,'control_snapshots.json',[]);rows=[]
    for i,u in enumerate(updates):
        m=next((m for m in measured if abs(m['time_s']-u['time_s'])<1e-8),None)
        if m is None:
            initial=source['configuration']['task']['initializer']['parameters']['data']
            if i!=0 or u['time_s']!=0 or any(initial['qvel_rad_s'].values()):raise ValueError('SAVED_SAME_TIME_MOTION_REQUIRED')
            m=dict(error_m=float(np.linalg.norm(np.asarray(u['tip_position_m'])-source['configuration']['task']['goal']['data']['target_m'])),
                speed_m_s=0.,source='Recorded time-zero tip and named zero physical initial velocities; post-step trajectory starts at .01s')
        a=next((a for a in comparisons if abs(a['start_s']-u['time_s'])<1e-8),None)
        snapshot=next((s for s in snapshots if s['update_id']==i),None)
        timing=u.get('prediction_timing') or {}
        rows.append(dict(update_id=i,time_s=u['time_s'],effective_horizon=u.get('effective_horizon'),
            node_times_s=timing.get('node_times_s'),holding_active=timing.get('holding_active'),
            first_holding_node_s=next((t for t,w in zip(timing.get('node_times_s',[]),timing.get('holding_active',[])) if w),None),
            plans=None if snapshot is None else {k:v['verification'] for k,v in snapshot['plans'].items()},
            historical_warm_recorded=snapshot is not None,iterations=u.get('optimization_iterations'),
            selected_iteration=u.get('optimization_selected_iteration'),solver_status=u.get('optimization_status'),
            raw_status=u.get('optimization_raw_status'),policy_stop_reason=u.get('policy_stop_reason'),
            selected_violation=u.get('optimization_constraint_violation'),returned_violation=u.get('optimization_returned_violation'),
            objectives=None if snapshot is None else {k:v['objective_components'] for k,v in snapshot['plans'].items()},
            requested_tension_n=u.get('requested_tension_n'),applied_tension_n=u.get('actual_tension_n'),
            position_error_m=m['error_m'],tip_speed_m_s=m['speed_m_s'],aligned_prediction=a,
            costs_s={k:u.get(k) for k in ('state_preparation_s','warm_preparation_s','optimization_solve_s','plan_validation_s','update_wall_s','deadline_horizon_preparation_s','snapshot_capture_wall_s')},
            projection_residual_rad_m=u.get('gvs_projection_residual_max_rad_m')))
    return dict(source_execution=source['execution_id'],owner=source['owner'],manifest=source['manifest'],files=source['files'],rows=rows,
        landmarks=dict(first_holding_visible_s=next((r['time_s'] for r in rows if r['first_holding_node_s'] is not None),None),
            first_shortened_horizon_s=next((r['time_s'] for r in rows if r['effective_horizon']<rows[0]['effective_horizon']),None),
            first_changed_input_s=next((r['time_s'] for r in rows if r['applied_tension_n'] is not None and max(abs(v-.2) for v in r['applied_tension_n'])>1e-6),None)),
        missing=['Historical complete warm starts, raw/initial plan vectors, rejected iterates, scalar objectives and iteration counts were not recorded.' ] if not snapshots else [],
        aligned_prediction_missing=missing,projection_checks=[],
        corrections=['Synchronous wall-clock latency did not skip virtual-time control actions.',
            'Initialization selection is distinct from exception fallback.',
            'Numerical feasibility is distinct from task acceptance.',
            'Untested weights or longer solves cannot be declared ineffective.',
            'Curvature residual in rad/m is not a tip error in metres.'])


def revision_comparison(h,detail):
    reader=ControlEvidence(h.store);source=reader.resolve(detail['execution_references']['execution_id'])
    timeline=make_timeline(reader,source);state=h.store.session(h.run_id)['state']
    old=h.store.artifact(state['factual_packet_reference']);baseline=h.store.artifact(state['source_baseline_reference'])
    def metrics(value,profile):
        rows=value['rows'];first=value['landmarks']['first_changed_input_s']
        changed=next((r for r in rows if r['time_s']==first),None)
        inputs=np.asarray([r['applied_tension_n'] for r in rows if r['applied_tension_n'] is not None])
        return dict(first_changed_input_s=first,landmarks=value['landmarks'],
            position_error_at_first_change_m=None if changed is None else changed['position_error_m'],
            subsequent_measured_errors=[dict(time_s=r['time_s'],error_m=r['position_error_m']) for r in rows if first is not None and r['time_s']>=first],
            initialization_selected=profile['initialization_selected'],solver_status_counts=profile['optimization_status_counts'],
            policy_reason_counts=profile['policy_stop_reason_counts'],holding=profile['sampled_settling'],
            terminal_error_m=profile['terminal_error_m'],drive_utilization=profile['drive_utilization'],
            total_input_variation_n=np.abs(np.diff(inputs,axis=0)).sum(axis=0).tolist(),
            aligned_prediction=profile['one_step_prediction_summary'],
            mean_update_s=profile['mean_update_s'],snapshot_cost_s=sum(r['costs_s'].get('snapshot_capture_wall_s') or 0 for r in rows))
    with h.store.transaction() as db:ref=h.store.put(db,timeline)
    return dict(baseline=metrics(old,baseline['profile']),revision=metrics(timeline,detail['profile']),
        revised_timeline_reference=plain(ref),baseline_reference=state['source_baseline_reference'],
        acceptance=detail['acceptance'],interpretation='Earlier changed actions alone are not improvement; compare measured error/holding and unchanged acceptance.')


def validate_plan(store,state,args):
    from schemas.casadi_feedback import InitializationPlan
    InitializationPlan.model_validate(plain(args))
    if args.comparison:
        c=args.comparison
        if state['paired_comparisons']>=2:raise ValueError('TWO_PAIR_CEILING')
        ids=set(state['selected_states'])|{c.update_id}
        if len(ids)>2:raise ValueError('TWO_REPRESENTATIVE_STATE_CEILING')
        source=BoundReader(store,EvidenceRef.model_validate(state['source_binding'])).resolve(EXECUTION)
        p=source['configuration']['policy']['controller']['parameters']['data']['recipe']
        changed_recipe(p,c.changed_parameter,c.changed_value)
        if recipe_value(p,c.changed_parameter)==c.changed_value:raise ValueError('DECLARED_FACTOR_MUST_CHANGE')
    if args.control:
        if args.control.candidate.artifact_id!=CANDIDATE:raise ValueError('FIXED_CANDIDATE_REQUIRED')
        if plain(args.control.preceding_execution)!=state['source_baseline_reference']:raise ValueError('IMPORTED_BASELINE_REQUIRED')
        factors=sum((args.control.holding_tip_speed_weight!=.05,args.control.terminal_tip_speed_weight!=.1,
            args.control.feasible_return_budget_s!=15.,args.control.substeps!=1))
        if factors!=1:raise ValueError('ONE_TARGETED_REVISION_FACTOR_REQUIRED')
        if not args.control.record_update_ids or not set(args.control.record_update_ids)<=set(state['selected_states']):
            raise ValueError('RECORD_SELECTED_DIAGNOSTIC_UPDATES_REQUIRED')
        if not any(r['operation']=='saved_state_comparison' and not r.get('imported') for r in state['results']):
            raise ValueError('OBSERVED_DIAGNOSTIC_MECHANISM_REQUIRED')


def projection_check(h,index):
    """Evaluate reduced kinematics at the saved projected state, no rollout."""
    from extensions.tendon_family.gvs import GVSModel
    from extensions.tendon_family.contracts import GVSModelParameters
    from extensions.tendon_family.gvs_casadi import expression_from_system,functions_for
    from schemas.platform import SessionInput
    from schemas.platform_math import SystemContext
    from extensions.tendon_family.pcc import quaternion_wxyz_to_rotation
    import casadi as ca
    state=h.store.session(h.run_id)['state'];reader=BoundReader(h.store,EvidenceRef.model_validate(state['source_binding']))
    source=reader.resolve(EXECUTION);updates=reader.read_file(source,'controller_observations.json')
    u=updates[index];x=np.asarray(u['measured_initial_state']);n=len(x)//2
    inp=SessionInput.model_validate(source['configuration']);p=GVSModelParameters(basis=inp.policy.controller.parameters.data['recipe']['basis'])
    system=GVSModel(p).build_system(inp.robot,p,None,SystemContext(x0=x.tolist(),u0=u['actual_tension_n'],scene=inp.task.environment))
    f=functions_for(expression_from_system(system));q=f.q_symbol;v=ca.MX.sym('projected_rate',n)
    mount=inp.task.environment.data['mount'];tip=ca.DM(quaternion_wxyz_to_rotation(mount['quaternion_wxyz']))@f.tip_position_expression+ca.DM(mount['position_m'])
    motion=ca.Function('same_time_projection',[q,v],[tip,ca.jacobian(tip,q)@v]);pos,vel=motion(x[:n],x[n:])
    pos=np.asarray(pos).ravel();vel=np.asarray(vel).ravel();m=next(m for m in measured_motion(reader,source) if abs(m['time_s']-u['time_s'])<1e-8)
    return dict(update_id=index,time_s=u['time_s'],full_simulator=m,reduced_position_m=pos.tolist(),reduced_velocity_m_s=vel.tolist(),
        same_time_tip_difference_m=float(np.linalg.norm(pos-m['position_m'])),
        same_time_velocity_difference_m_s=float(np.linalg.norm(vel-m['velocity_m_s'])),
        source_state=dict(reference=source['files']['controller_observations.json'],pointer=f'/{index}/measured_initial_state'),
        scope='Same-time kinematics/Jacobian at saved projected state; no simulation or optimizer; distinct from next-step prediction error.')


def compact_pair(value):
    keys=('update_id','time_s','changed_factor','baseline_value','variant_value','seed','complete_cost_s','applicability','projection_check','protocol')
    result={k:value[k] for k in keys if k in value}
    result['rows']=[{k:r[k] for k in ('label','metrics','plans','verification','reference','selected_iteration','stop_reason','termination','complete_cost_s')} for r in value['rows']]
    return result


def run_pair(h,choice,key):
    from tools.research_execution import invoke
    start=time.perf_counter();state=h.store.session(h.run_id)['state'];index=choice.update_id
    with h.store.transaction() as db:
        state=h.store.session(h.run_id,db)['state'];state['paired_comparisons']+=1
        if index not in state['selected_states']:state['selected_states'].append(index)
        h.store.update_state(db,h.run_id,state)
    projection=None
    try:
        existing=state.get('projection_checks',{}).get(str(index))
        projection=h.store.artifact(existing) if existing else projection_check(h,index)
        with h.store.transaction() as db:
            state=h.store.session(h.run_id,db)['state']
            state.setdefault('projection_checks',{})[str(index)]=plain(h.store.put(db,projection))
            h.store.update_state(db,h.run_id,state)
        allowance=choice.max_wall_s-(time.perf_counter()-start)
        args=dict(plain(choice),binding=state['source_binding'],operation='local_comparison',max_wall_s=allowance)
        # max_wall_s appears once and includes projection/preparation in the pair ceiling.
        receipt=invoke(h,'diagnosis.saved_state_check',args,request_id=key)
        feedback=h.store.artifact(receipt['output']) if receipt.get('output') else None
        if receipt['execution_status']!='completed':raise ValueError('PAIRED_INTERFACE_FAILURE: '+str(receipt.get('error')))
        detail=feedback['detail'];detail['projection_check']=projection
        with h.store.transaction() as db:
            ref=h.store.put(db,detail);state=h.store.session(h.run_id,db)['state']
            state['results'].append(dict(operation='saved_state_comparison',reference=plain(ref)))
            h.store.update_state(db,h.run_id,state)
        return dict(receipt=receipt,feedback=compact_pair(detail),evidence_reference=plain(ref))
    except Exception as exc:
        with h.store.transaction() as db:
            state=h.store.session(h.run_id,db)['state'];error=dict(status='engineering_error',reason=str(exc),projection=projection)
            ref=h.store.put(db,error);state['engineering_pause']=dict(reference=plain(ref),reason=str(exc))
            h.store.update_state(db,h.run_id,state)
        return dict(feedback=error,evidence_reference=plain(ref))
    finally:
        with h.store.transaction() as db:
            state=h.store.session(h.run_id,db)['state'];state['numerical_s']+=time.perf_counter()-start
            h.store.update_state(db,h.run_id,state)


def packet(h):
    from tools.casadi_feedback_service import SPEC,budget
    from tools.research_casadi_feedback import compact_result
    state=h.store.session(h.run_id)['state'];facts=h.store.artifact(state['factual_packet_reference'])
    results=[]
    for r in state['results']:
        if r.get('imported') and r['operation']!='closed_loop':continue
        results.append(dict(operation=r['operation'],reference=r['reference'],imported=r.get('imported',False),**compact_result(h.store.artifact(r['reference']))))
    return dict(frozen_specification=SPEC,source_binding=state['source_binding'],
        candidate=dict(artifact_id=CANDIDATE,media_type='application/json'),baseline_execution_reference=state['source_baseline_reference'],
        factual_packet_reference=state['factual_packet_reference'],source_correction_reference=state['source_correction_reference'],
        factual_packet=facts,results=results,remaining_budget=budget(h.store),
        selected_states=state['selected_states'],paired_comparisons=state['paired_comparisons'],
        capabilities=dict(inspect_execution='BoundQuery(binding,view,update_ids up to8), read-only',
            saved_state_comparison='New common-seed paired solves, one factor; not a historical warm replay',
            control_revision='At most one launch against imported baseline, one factor, snapshots at selected states',
            stop='Optional early stop, citing all new results'))


def add_inspection_tool(h,tools):
    from strands.tools.tools import PythonAgentTool
    from tools.research_execution import invoke
    definition=h.reg.get('diagnosis.inspect_evidence')
    def handler(use,**kwargs):
        if h.store.remaining()['remaining']['model_calls']<=4:
            return dict(toolUseId=use['toolUseId'],status='error',content=[dict(text='Protected closeout: use supplied new feedback and STOP.')])
        if use['input']['binding']!=h.store.session(h.run_id)['state']['source_binding']:
            return dict(toolUseId=use['toolUseId'],status='error',content=[dict(text='Original source binding required.')])
        receipt=invoke(h,'diagnosis.inspect_evidence',use['input'],request_id='native-'+use['toolUseId'])
        value=h.store.artifact(receipt['output']) if receipt.get('output') else receipt.get('error')
        return dict(toolUseId=use['toolUseId'],status='success' if receipt['execution_status']=='completed' else 'error',content=[dict(text=json.dumps(value))])
    tools.append(PythonAgentTool('inspect_execution',dict(name='inspect_execution',description=definition.description,inputSchema={'json':definition.input_schema.model_json_schema()}),handler))
