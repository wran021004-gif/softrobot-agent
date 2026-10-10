"""Owned archived baseline, aligned holding diagnosis and bounded weight tests."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tarfile
import time
import numpy as np
from schemas.platform import SessionInput, EvidenceRef
from schemas.casadi_feedback import SettlingPlan, Result
from tools.platform_store import plain
from tools.state_io import atomic_json, read, digest
from tools.spec_tools import ROOT
from extensions.tendon_family.control_evidence import ControlEvidence, EvidenceQuery
from extensions.tendon_family.diagnostic_evidence import BoundReader, import_execution, add_velocity_comparisons

SOURCE=ROOT/'evidence/nmpc_feasibility_20261011'
OUT=ROOT/'evidence/nmpc_settling_20261011'
WEIGHTS=('holding_tip_speed_weight','terminal_tip_speed_weight')
INSTRUCTIONS='''You are the sole existing DeepSeek research principal for a fresh bounded recovery-enabled holding-speed follow-up. Codex supplies engineering, archived evidence and factual arithmetic, not your hypothesis, chosen weight or conclusions. This is task-supplied evidence context, not autonomous memory retrieval. The only baseline is the latest recovery-enabled execution; do not use the earlier recovery-disabled state. Native research_plan choices: diagnose (read-only), saved_state_comparison (optional ONE saved update 1..34, ONE speed weight in .025.. .10, baseline and variant total TWO local NLP attempts/300s), control_revision (ONE development closed loop changing EXACTLY ONE speed weight from .05/.10), control_confirmation (optional independent launch with EXACT same candidate/scientific configuration/seed/initial state/acceptance as the development result; preceding_execution must be that development reference), stop. Every scientific action declares hypothesis, supporting_evidence, changed factor/value, fixed_conditions, expected_observation, weakening_observation, revision_or_stop_rule. Consume actual results before choosing another scientific step. evidence_read and inspect_execution may read existing immutable data. The packet supplies aligned .25-.32s diagnosis and .24s preceding prediction, archived full snapshot at .20s, terminal predictions and actual objective formulas. Missing historical full vectors/iterates/intermediate horizons/cost decompositions are UNKNOWN. New local cold initialization is the SAME reconstructed seed in both arms; no historical replay claim. Local raw objectives have different definitions and must not rank arms. Local speed improvement is not closed-loop improvement. No mandatory experiments; STOP is allowed immediately if evidence points outside scope. Do not predetermine increase; choose either permitted weight and actual value. Keep recover_returned_tensions True, feasible-return15s, CPU30s, iteration120, minimum5s/relative improvement.1, substeps1, horizon and all timing/physics/task/initializer/evaluation unchanged. control.candidate is packet.candidate; development preceding_execution is packet.baseline_execution_reference. control.record_update_ids fixed [29,30] for detailed new evidence only; cannot change scientific settings for confirmation. No new brake lead, solver time, grid, hard speed constraints, old offline trajectory, structure search, BDF, other research models or hardware. Max2 MuJoCo launches including failed starts: ONE development, ONE explicitly chosen exact confirmation, never a second tuning trial. Each1800s simulation/30s evaluation/60s analysis; total all preparation/numerics/failures3600s; atomically reserved. Provider16 actual sends including retries/auxiliary with LAST4 protected for result consumption/correction/STOP; public64;6h total including engineering/final30min protected. Ceilings are not quotas. Keep original failed samples; .01m position/.02m/s inclusive final.05s unchanged. Baseline predicted overspeed at .30/.31s already exceeds actual and hold is active; do not explain as underestimated speed or absent holding penalty. Soft penalty is not a hard speed constraint. Initialization selected may carry prior changed actions; inspect source/content. Numerical .2N is not equilibrium; synchronous slow wall clock did not skip virtual control actions. Preserve raw solver, recovery candidate, delivered plan and actual action identities. Report sampled joint acceptance, confirmation status, repetition versus robustness, model contribution and limits distinctly. STOP must cite ALL new feedback references and bind latest execution IDs plus actual used/remaining budget, distinguishing inherited evidence and new work. Facts supported by ledger/references may be corrected by returning concrete feedback before accepting STOP; never replace your wording with Codex conclusions. For STOP, set final_accounting to the EXACT final_accounting_template in the latest CURRENT_RESEARCH_PACKET; its budget_basis explicitly states the before-send accounting timestamp. Do not relabel remaining as used or count repeated evidence references as executions. Accepted native STOP forbids additional sends. No unique-cause, robustness, real-time, continuous-time, hardware or LLM superiority claims.'''


class ArchiveStore:
    def __init__(self):
        self.root=SOURCE;self.values={}
        manifest=read(SOURCE/'archive_manifest.json');path=SOURCE/'immutable_artifacts.tar.gz'
        if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['archive_sha256']:raise ValueError('SOURCE_ARCHIVE_HASH_MISMATCH')
        with tarfile.open(path,'r:gz') as archive:
            for member in manifest['members']:
                body=archive.extractfile(member['name']).read()
                if hashlib.sha256(body).hexdigest()!=member['sha256']:raise ValueError('SOURCE_MEMBER_HASH_MISMATCH')
                self.values[member['sha256']]=body
    def artifact(self,ref,raw=False):
        ref=plain(ref);body=self.values[ref['artifact_id']]
        return body if raw or ref['media_type']!='application/json' else json.loads(body)
    def config(self):return dict(project_id=read(SOURCE/'activity.json')['activity_id'])


class ArchiveReader(ControlEvidence):
    def resolve(self,execution_id):
        row=latest_source_row();v=self.store.artifact(row['reference']);refs=v['execution_references']
        if execution_id!=refs['execution_id']:raise ValueError('LATEST_RECOVERY_EXECUTION_REQUIRED')
        sim=refs['receipts']['simulation'];candidate=self.store.artifact(refs['executed_configuration']);matches=[]
        for aid,body in self.store.values.items():
            try:value=json.loads(body)
            except (ValueError,UnicodeDecodeError):continue
            if isinstance(value,dict) and value.get('result')==sim['output'] and 'files' in value:
                matches.append((dict(artifact_id=aid,media_type='application/json'),value))
        if len(matches)!=1:raise ValueError('UNIQUE_OWNED_EXPORT_REQUIRED')
        manifest,bundle=matches[0]
        cfg=candidate['effective'];p=cfg['policy']['controller']['parameters']['data']['recipe']
        if (p['recover_returned_tensions'],p[WEIGHTS[0]],p[WEIGHTS[1]])!=(True,.05,.10):raise ValueError('LATEST_RECOVERY_BASELINE_REQUIRED')
        if refs['owner_run_id']!=row['owner_run_id'] or bundle['result']!=sim['output']:raise ValueError('SOURCE_OWNER_MISMATCH')
        return dict(owner=refs['owner_run_id'],execution_id=execution_id,manifest=manifest,
            metadata=dict(artifact_id=sim['output']['artifact_id'],candidate=candidate['candidate_id'],candidate_input=refs['executed_configuration']),
            files={f['filename']:f['reference'] for f in bundle['files']},configuration=cfg)


def latest_source_row():
    return next(r for r in reversed(read(SOURCE/'state.json')['results']) if r['operation']=='closed_loop' and not r.get('imported'))


def baseline_configuration():
    # Full immutable executed configuration, not a manual reconstruction.
    archive=ArchiveStore();v=archive.artifact(latest_source_row()['reference'])
    return archive.artifact(v['execution_references']['executed_configuration'])['effective']


def activity_configuration(policy):
    from tools.casadi_feedback_service import ACTIVITY
    cfg=baseline_configuration();cfg['run_id']=ACTIVITY
    scientific=('controller','backend','dynamics_model','discretization','candidate_builder','editable','search')
    saved={k:deepcopy(cfg['policy'][k]) for k in scientific}
    cfg['policy']=deepcopy(policy);cfg['policy'].update(saved)
    return cfg


def scientific_scope(cfg):
    from extensions.tendon_family.gvs_profile import execution_scope
    return execution_scope(cfg)


def verify_configuration(store,state,cfg,choice,action):
    choice=plain(choice);baseline=store.artifact(state['source_binding'])['source']['configuration']
    expected=deepcopy(baseline)
    p=expected['policy']['controller']['parameters']['data']['recipe']
    for k in WEIGHTS:p[k]=choice[k]
    a=scientific_scope(cfg);b=scientific_scope(expected)
    if a!=b:raise ValueError('FROZEN_FULL_SCIENTIFIC_CONFIGURATION_MISMATCH: '+str([k for k in a if a[k]!=b[k]]))
    if cfg['policy']['candidate_builder']!=baseline['policy']['candidate_builder']:raise ValueError('FROZEN_CANDIDATE_BUILDER_MISMATCH')
    identity=digest(a)
    if action=='control_confirmation':
        preceding=store.artifact(choice['preceding_execution']);old=store.artifact(preceding['resolved_configuration'])
        if scientific_scope(old)!=a or digest(scientific_scope(old))!=identity:raise ValueError('EXACT_CONFIRMATION_CONFIGURATION_IDENTITY_MISMATCH')
    return dict(identity=identity,baseline_identity=digest(scientific_scope(baseline)),
        changed_weights={k:dict(before=baseline['policy']['controller']['parameters']['data']['recipe'][k],after=choice[k]) for k in WEIGHTS if p[k]!=baseline['policy']['controller']['parameters']['data']['recipe'][k]},
        action=action,full_scope_verified=True,recovery_enabled=True)


def validate_plan(store,state,args):
    SettlingPlan.model_validate(plain(args))
    if args.action=='stop':
        packets=[e for e in store.events(store.config()['project_id']) if e['kind']=='model_decision_packet']
        if not packets:raise ValueError('FINAL_STOP_REQUIRES_REAL_DECISION_PACKET')
        expected=store.artifact(packets[-1]['outputs'][0])['final_accounting_template']
        if args.final_accounting!=expected:
            raise ValueError('FINAL_ACCOUNTING_CORRECTION_REQUIRED: copy the latest packet final_accounting_template exactly: '+json.dumps(expected))
    if args.comparison:
        c=args.comparison
        if state.get('local_pair_reserved'):raise ValueError('ONE_LOCAL_PAIR_ONLY')
        p=store.artifact(state['source_binding'])['source']['configuration']['policy']['controller']['parameters']['data']['recipe']
        if p[c.changed_parameter]==c.changed_value:raise ValueError('LOCAL_FACTOR_MUST_CHANGE')
        rows=store.artifact(state['diagnostic_reference'])['available_saved_update_ids']
        if c.update_id not in rows:raise ValueError('OWNED_RECOVERY_ENABLED_SAVED_STATE_REQUIRED')
    if args.control:
        c=args.control
        if plain(c.candidate)!=state['fixed_candidate']:raise ValueError('EXACT_FIXED_CANDIDATE_REQUIRED')
        if (c.recover_returned_tensions,c.feasible_return_budget_s,c.substeps,c.record_update_ids)!=(True,15.,1,[29,30]):
            raise ValueError('RECOVERY_AND_FIXED_RECIPE_RECORDING_REQUIRED')
        runs=[r for r in state['results'] if r['operation']=='closed_loop' and not r.get('imported')]
        if args.action=='control_revision':
            if runs or any(r['action']=='control_revision' for r in state['plans']):raise ValueError('ONE_DEVELOPMENT_ONLY')
            if plain(c.preceding_execution)!=state['source_baseline_reference']:raise ValueError('LATEST_RECOVERY_BASELINE_REFERENCE_REQUIRED')
            if sum(getattr(c,k)!=v for k,v in zip(WEIGHTS,(.05,.10)))!=1:raise ValueError('EXACTLY_ONE_SPEED_WEIGHT_CHANGE')
        elif args.action=='control_confirmation':
            if len(runs)!=1 or any(r['action']=='control_confirmation' for r in state['plans']):raise ValueError('ONE_CONFIRMATION_AFTER_DEVELOPMENT_ONLY')
            if plain(c.preceding_execution)!=runs[0]['reference']:raise ValueError('CONFIRMATION_MUST_CITE_DEVELOPMENT_EXECUTION')
            old=store.artifact(c.preceding_execution)
            if old['status']!='evaluated':raise ValueError('CONFIRMATION_REQUIRES_COMPLETED_DEVELOPMENT_FEEDBACK')
            before={k:v for k,v in old['control'].items() if k!='preceding_execution'}
            after={k:v for k,v in plain(c).items() if k!='preceding_execution'}
            if before!=after:raise ValueError('EXACT_CONFIRMATION_CONTROL_IDENTITY_REQUIRED')


def diagnostic_packet(reader,source,motion):
    from extensions.tendon_family.control_evidence import aligned_interval_predictions
    updates=reader.read_file(source,'controller_observations.json',[])
    trajectory=reader.read_file(source,'trajectory.json.gz',[]);commands=reader.read_file(source,'actual_commands.json',[])
    selected=list(range(24,33))
    aligned,missing=aligned_interval_predictions(trajectory,updates,commands,.01,source['configuration']['task']['goal']['data']['target_m'],selected)
    simple=[dict(time_s=m['time_s'],velocity_m_s=m['tip_velocity_m_s']) for m in motion]
    add_velocity_comparisons(aligned,updates,simple)
    target=np.array(source['configuration']['task']['goal']['data']['target_m']);rows=[]
    p=source['configuration']['policy']['controller']['parameters']['data']['recipe']
    for i in selected:
        u=updates[i];previous=updates[i-1]['actual_tension_n'];actual=u['actual_tension_n'];t=u['time_s']
        m=next(m for m in motion if abs(m['time_s']-t)<1e-8)
        preceding=next((v for v in aligned if abs(v['end_s']-t)<1e-8),None)
        prediction=u['one_step_prediction'];timing=u['prediction_timing'];v=np.array(prediction['tip_velocity_m_s'])
        active=timing['holding_active'][0]
        rows.append(dict(update_id=i,time_s=t,measured=m,preceding_aligned_prediction=preceding,
            next_prediction=prediction,next_aligned_prediction=next((v for v in aligned if v['update_id']==i),None),
            actual_tension_n=actual,change_from_previous_actual_n=(np.array(actual)-previous).tolist(),
            lower_bound_hit=[x<=1e-8 for x in actual],upper_bound_hit=[x>=8-1e-8 for x in actual],
            actuator_saturation=u['force_limit_saturated'],prediction_timing=timing,effective_horizon=u['effective_horizon'],
            first_node_hold_active=bool(active),plan_source=u['plan_source'],selected_iteration=u['optimization_selected_iteration'],
            stop_reason=u['policy_stop_reason'],raw_status=u['optimization_raw_status'],recovery=u['feasibility_recovery'],
            terminal_predictions=u['feedback'],
            saved_first_node_costs=dict(running_position=.01*p['tracking_weight']*float(np.sum((np.array(prediction['tip_position_m'])-target)**2/.01**2)),
                holding_tip_speed=.01*p[WEIGHTS[0]]*active*float(np.sum(v**2/p['tip_speed_scale_m_s']**2)),
                tension=.01*p['tension_weight']*float(np.sum(np.array(actual)**2)),
                variation=.01*p['variation_weight']*float(np.sum((np.array(actual)-previous)**2))),
            full_horizon_cost_breakdown=None,full_iteration_trace=None,unrecorded_intermediate_nodes=None))
    checks=[]
    for i,predicted,actual in [(29,.026699,.020494),(30,.031330,.024643)]:
        a=next(v for v in aligned if v['update_id']==i)
        velocity=a['velocity']
        checks.append(dict(update_id=i,target_sample_s=a['end_s'],predicted_speed_m_s=velocity['predicted_speed_m_s'],
            measured_speed_m_s=velocity['measured_speed_m_s'],expected_rounded=dict(predicted=predicted,measured=actual),
            matches_rounded=abs(velocity['predicted_speed_m_s']-predicted)<.00000051 and abs(velocity['measured_speed_m_s']-actual)<.00000051,
            prediction_exceeds_measurement=velocity['predicted_speed_m_s']>velocity['measured_speed_m_s'],holding_active=bool(updates[i]['prediction_timing']['holding_active'][0])))
    snapshots=reader.read_file(source,'control_snapshots.json',[])
    return dict(source_execution=source['execution_id'],source_owner=source['owner'],manifest=source['manifest'],configuration_identity=digest(scientific_scope(source['configuration'])),
        files=source['files'],rows=rows,aligned=aligned,alignment_missing=missing,known_observation_checks=checks,
        available_saved_update_ids=list(range(1,len(updates))),snapshot_updates=[v['update_id'] for v in snapshots],
        saved_full_plan_summaries=[dict(update_id=s['update_id'],plans={k:{a:v[a] for a in ('metrics','objective_components','verification')} for k,v in s['plans'].items()}) for s in snapshots],
        objective=dict(parameters=p,definitions=dict(running_position='h * tracking_weight * ||(tip-target)/position_scale||^2',
            holding_speed='h * holding_tip_speed_weight * active_at_absolute_node_time * ||v_tip/0.02||^2',
            terminal_speed='terminal_tip_speed_weight * ||v_tip(horizon_end)/0.02||^2; no h factor',
            tension='dt * tension_weight * sum(||u_k||^2)',variation='dt * variation_weight * sum(||u_k-u_previous||^2)',
            terminal_position='terminal_weight * ||(tip(horizon_end)-target)/position_scale||^2; no h',
            curvature_rate='h * velocity_weight * sum(||qdot||^2) plus terminal_velocity_weight * ||qdot_end||^2'),
            dt_s=.01,h_s=.01,position_scale_m=.01,source='extensions/tendon_family/gvs_trajectory.py: GVSTrajectoryAssembler.assemble',
            hard_constraints=['measured initial state','scaled implicit dynamics equalities','six tension bounds0..8N'],
            soft_costs=['position','holding and terminal speed','curvature rates','tensions and changes'],
            independent_acceptance='terminal/holding position<=.01m; inclusive .30-.35s sampled speed<=.02m/s; soft costs do not enforce acceptance'),
        corrections=['Both first predicted nodes already activate holding cost and overpredict actual overspeed.',
            'Historical warm initializations at32..34 carry previous changed actions; selection alone is not ineffective action.',
            'Weights cannot be ranked by raw coefficient size; running h factor, normalization and actual state matter.'],
        unknowns=['Complete cost breakdown, all optimization vectors/iterations and intermediate prediction nodes at late updates were not saved.',
            'No unique cause or counterfactual weight effect established by archived observations alone.'],
        new_nlp_attempts=0,new_simulation_launches=0)


def prepare_evidence(h):
    if h.store.session(h.run_id)['state'].get('settling_prepared'):return
    start=time.perf_counter();OUT.mkdir(parents=True,exist_ok=True)
    from tools.nmpc_feasibility import import_archive
    with h.store.transaction() as db:import_archive(h.store,db,SOURCE)
    archive=ArchiveStore();row=latest_source_row();base=archive.artifact(row['reference']);execution=base['execution_references']['execution_id']
    binding=import_execution(ArchiveReader(archive),execution,h.store,h.run_id)
    reader=BoundReader(h.store,EvidenceRef.model_validate(binding));source=reader.resolve(execution)
    motion=h.store.artifact(base['profile']['motion']);diagnosis=diagnostic_packet(reader,source,motion)
    old=read(SOURCE/'state.json')
    with h.store.transaction() as db:
        state=h.store.session(h.run_id,db)['state'];ref=plain(h.store.put(db,diagnosis));prior={}
        names=['docs/nmpc_feasibility_completion.md','docs/nmpc_feasibility_runbook.md','docs/nmpc_feasibility_procedure.md','memory/nmpc_feasibility_case_draft.json']
        for name in names:prior[name]=plain(h.store.put(db,(ROOT/name).read_bytes(),'text/plain'))
        for name in ['scientific_summary','configuration_comparison','post_stop_factual_correction','plan_00_reintegrate_saved_tensions','plan_01_control_revision','plan_02_stop']:
            prior[name]=plain(h.store.put(db,read(SOURCE/(name+'.json'))))
        state.update(settling_followup=True,source_binding=binding,source_baseline_reference=row['reference'],
            fixed_candidate=base['candidate'],candidate_sources=old['candidate_sources'],diagnostic_reference=ref,
            prior_context_references=prior,local_pair_reserved=False,new_local_nlp_attempts=0,local_nlp_cost_s=0.,
            results=[dict(row,imported=True,source_activity=old['pilot']['activity_id']),dict(operation='archived_holding_diagnosis',reference=ref)],
            supplied_prior_context='Task-supplied archived facts and case/procedure context; not autonomous memory retrieval.',settling_prepared=True)
        h.store.update_state(db,h.run_id,state)
    atomic_json(OUT/'diagnostic_timeline.json',diagnosis);atomic_json(OUT/'source_binding.json',h.store.artifact(binding))
    atomic_json(OUT/'baseline_configuration.json',source['configuration'])
    atomic_json(OUT/'source_verification.json',dict(source_commit='f31a926ee741fcc859853d851ab255b2bf4e1409',
        archive_manifest=read(SOURCE/'archive_manifest.json'),binding=binding,baseline_result=row['reference'],
        execution=execution,owner=source['owner'],full_scientific_identity=diagnosis['configuration_identity'],baseline_not_rerun=True))
    with h.store.transaction() as db:
        state=h.store.session(h.run_id,db)['state'];elapsed=time.perf_counter()-start
        state['numerical_s']+=elapsed;state.setdefault('preparation_costs_s',[]).append(elapsed);h.store.update_state(db,h.run_id,state)


def compact(value):
    result={k:v for k,v in value.items() if k not in ('arms','numerical_results')}
    if 'arms' in value:result['arms']=[{k:v for k,v in arm.items() if k not in ('snapshot','numerical','independent_verification')} for arm in value['arms']]
    return result


def compact_diagnosis(d):
    value={k:v for k,v in d.items() if k not in ('rows','aligned','saved_full_plan_summaries')}
    value['rows']=[]
    for r in d['rows']:
        row={k:v for k,v in r.items() if k not in ('preceding_aligned_prediction','next_aligned_prediction','next_prediction','recovery')}
        pred=r['next_prediction']
        row['next_prediction']={k:pred[k] for k in ('time_s','tip_position_m','tip_velocity_m_s','applied_tension_n')}
        aligned=r['preceding_aligned_prediction']
        row['same_time_prediction']=None if aligned is None else dict(update_id=aligned['update_id'],start_s=aligned['start_s'],end_s=aligned['end_s'],velocity=aligned['velocity'])
        row['recovery']={k:r['recovery'].get(k) for k in ('enabled','attempted','selected','source','parent_iteration','root_solve_attempts')}
        value['rows'].append(row)
    value['saved_full_plan_summaries']=[dict(update_id=s['update_id'],plans={k:dict(objective_components=v['objective_components'],
        terminal=v['metrics']['terminal'],first_step=v['metrics']['first_step'],verification=v['verification']) for k,v in s['plans'].items()}) for s in d['saved_full_plan_summaries']]
    return value


def packet(h):
    from tools.casadi_feedback_service import SPEC,budget
    from tools.research_casadi_feedback import compact_result
    state=h.store.session(h.run_id)['state'];base=h.store.artifact(state['source_baseline_reference'])
    remaining=dict(**budget(h.store),local_nlp_attempts=2-state['new_local_nlp_attempts'],
        local_pair_available=not state['local_pair_reserved'],local_nlp_s=300-state['local_nlp_cost_s'])
    used=dict(project=h.store.remaining()['used'],scientific_s=state['numerical_s'],local_nlp_attempts=state['new_local_nlp_attempts'])
    accounting=dict(budget_basis='Latest decision packet before this provider send and its tool calls; final ledger separately records their actual charges',
        inherited_execution_id=base['execution_references']['execution_id'],
        new_execution_ids=[h.store.artifact(r['reference'])['execution_references']['execution_id'] for r in state['results'] if r['operation']=='closed_loop' and not r.get('imported')],
        latest_feedback_reference=state['results'][-1]['reference'],used_budget=used,remaining_budget=remaining)
    return dict(frozen_specification=SPEC,candidate=state['fixed_candidate'],baseline_execution_reference=state['source_baseline_reference'],
        source_binding=state['source_binding'],baseline_execution=compact_result(base),
        supplied_prior_context=state['supplied_prior_context'],prior_context_references=state['prior_context_references'],
        historical_factual_correction=h.store.artifact(state['prior_context_references']['post_stop_factual_correction']),
        diagnostic_reference=state['diagnostic_reference'],diagnostic_packet=compact_diagnosis(h.store.artifact(state['diagnostic_reference'])),
        results=[dict(operation=r['operation'],reference=r['reference'],imported=bool(r.get('imported')),
            summary=compact_result(h.store.artifact(r['reference']))) for r in state['results'] if r['operation']!='archived_holding_diagnosis'],
        remaining_budget=remaining,used_budget=used,final_accounting_template=accounting,
        capabilities=dict(saved_state_comparison='Optional one new common cold-seed baseline/one-weight pair; latest source only; recovery stays True',
            control_revision='One development changing exactly one speed weight; control.record_update_ids [29,30]',
            control_confirmation='One unchanged scientific configuration, own new execution, preceding_execution is development feedback',
            diagnose='Read-only evidence synthesis',stop='Allowed without experiment; cite diagnostic and every new result, used/remaining budget'))


def preflight(inp,args,reg):return dict(cost=dict(wall_s=args.choice.max_wall_s))


def verify_pair_seed(common,seed,timing,recorded_timing):
    if common is not None and seed!=common:raise ValueError('PAIRED_INITIALIZATION_MISMATCH')
    if timing!=recorded_timing:raise ValueError('PAIRED_ABSOLUTE_TIMING_MISMATCH')
    return seed if common is None else common


def numeric_pair(request,output):
    from extensions.tendon_family.gvs_trajectory import TrajectoryWorkspace
    from extensions.tendon_family.control_evidence import capture_snapshot
    inp=SessionInput.model_validate(request['configuration']);u=request['update'];previous=request['previous_input'];choice=request['choice']
    base=inp.policy.controller.parameters.data['recipe'];start=time.perf_counter();arms=[];attempts=0
    common=None
    result=dict(settling_operation='saved_state_comparison',status='partial',update_id=u['update_id'],time_s=u['time_s'],
        changed_factor=choice['changed_parameter'],baseline_value=base[choice['changed_parameter']],variant_value=choice['changed_value'],
        source_binding=request['binding'],source_state_reference=request['state_reference'],
        measured_state=u['measured_initial_state'],previous_actual_input_n=previous,effective_horizon=u['effective_horizon'],
        seed='Same new constant previous-applied-input seed; states regenerated by unchanged dynamics; not historical warm replay',
        objective_comparison='Different objective definitions; compare physical position/speed/tensions/feasibility/stop/cost, not scalar totals',
        actual_executed_input_n=None,closed_loop_validated=False)
    try:
        for label in ('baseline','variant'):
            if time.perf_counter()-start+65>choice['max_wall_s']:raise RuntimeError('PAIR_TOTAL_TIME_ALLOWANCE')
            p=deepcopy(base);p['horizon']=u['effective_horizon']
            if label=='variant':p[choice['changed_parameter']]=choice['changed_value']
            attempts+=1;result.update(new_nlp_attempts=attempts,arms=arms,active_arm=label);atomic_json(output,result)
            wall=time.perf_counter();ws=TrajectoryWorkspace(inp.task,inp.robot,p,u['measured_initial_state'],previous,settling=inp.policy.controller.parameters.data['settling'])
            ws.solver.diagnostic_trace=True
            solved=ws.solve(u['measured_initial_state'],previous,elapsed_s=u['time_s'])
            atomic_json(Path(output).with_name('pair_'+label+'_numerical.json'),solved)
            snap=capture_snapshot(ws,solved,u['update_id'],u['time_s'],solved['tensions'][0],{'gvs_projection':{}})
            seed=dict(states=snap['plans']['initial']['states'],tensions=snap['plans']['initial']['tensions'])
            timing=solved['prediction_timing']
            common=verify_pair_seed(common,seed,timing,u['prediction_timing'])
            arms.append(dict(label=label,parameters=p,common_seed_identity=digest(seed),prediction_timing=timing,
                plans={k:{a:v[a] for a in ('metrics','verification','objective_components')} for k,v in snap['plans'].items()},
                original_solver=dict(status=solved['diagnostics']['return_status'],policy_stop=solved['diagnostics']['policy_stop_reason'],iterations=solved['result']['iterations']),
                recovery={k:v for k,v in solved['recovery'].items() if k!='candidate_optimum'},
                delivered_metrics=snap['plans']['delivered']['metrics'],snapshot=snap,
                costs_s=dict(complete=time.perf_counter()-wall,solve=solved['total_s'])))
            result.update(arms=arms,active_arm=None,new_nlp_attempts=attempts,costs_s=dict(total=time.perf_counter()-start));atomic_json(output,result)
        result.update(status='completed',same_initialization_verified=True)
    except Exception as exc:result.update(status='failed',error=type(exc).__name__+': '+str(exc))
    finally:
        result.update(arms=arms,new_nlp_attempts=attempts,costs_s=dict(total=time.perf_counter()-start));atomic_json(output,result)


def check_tool(ctx,args):
    from tools.casadi_feedback_service import CEILINGS
    start=time.perf_counter();state=ctx.store.session(ctx.run_id)['state'];choice=plain(args.choice)
    accepted=ctx.artifact(args.plan_reference)
    if accepted['action']!='saved_state_comparison' or accepted['comparison']!=choice:raise ValueError('LOCAL_OPERATION_MUST_MATCH_ACCEPTED_PLAN')
    reader=BoundReader(ctx.store,EvidenceRef.model_validate(state['source_binding']));s=reader.resolve(reader.binding['execution_id'])
    updates=reader.read_file(s,'controller_observations.json');i=choice['update_id'];u=dict(updates[i],update_id=i)
    request=dict(configuration=s['configuration'],update=u,previous_input=updates[i-1]['actual_tension_n'],choice=choice,
        binding=state['source_binding'],state_reference=dict(reference=s['files']['controller_observations.json'],pointer=f'/{i}/measured_initial_state'))
    with ctx.store.transaction() as db:
        current=ctx.store.session(ctx.run_id,db)['state']
        if current['local_pair_reserved'] or current['numerical_s']+choice['max_wall_s']>CEILINGS['total_numerical_s']:raise ValueError('PAIR_ATOMIC_BUDGET_RESERVATION_REJECTED')
        current['local_pair_reserved']=True;current['local_reserved_attempts']=2
        current['pending']=dict(operation='local_pair',folder=str(ctx.folder),started_unix=time.time())
        ctx.store.update_state(db,ctx.run_id,current)
    inp=ctx.folder/'pair_input.json';out=ctx.folder/'pair_feedback.json';atomic_json(inp,request)
    env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    try:
        try:
            process=subprocess.run([state['python'],'-m','tools.nmpc_settling',str(inp),str(out)],cwd=ROOT,env=env,
                stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=max(.01,choice['max_wall_s']-(time.perf_counter()-start)-2))
            log=process.stdout
        except subprocess.TimeoutExpired as exc:log=exc.stdout or b''
        value=read(out) if out.exists() else dict(settling_operation='saved_state_comparison',status='unknown',new_nlp_attempts=None,error='No sealed worker outcome; do not redispatch')
        sealed={}
        for file in ctx.folder.glob('pair_*_numerical.json'):sealed[file.name]=plain(ctx.save_artifact(read(file),file.stem))
        value['numerical_references']=sealed;value['worker_log_reference']=plain(ctx.save_artifact(dict(text=log.decode('utf8',errors='replace')),'pair_worker_log'))
        value['charged_function_wall_s']=time.perf_counter()-start;ref=ctx.save_artifact(value,'pair_feedback')
        with ctx.store.transaction() as db:
            current=ctx.store.session(ctx.run_id,db)['state'];current['new_local_nlp_attempts']=value['new_nlp_attempts'] if value['new_nlp_attempts'] is not None else 2
            current['results'].append(dict(operation='saved_state_comparison',reference=plain(ref)));current.pop('pending',None)
            if value['status']!='completed':current['engineering_pause']=dict(reference=plain(ref),reason='Inspect sealed local outcome; no numerical retry.')
            ctx.store.update_state(db,ctx.run_id,current)
        atomic_json(OUT/'local_pair_feedback.json',value)
        return Result(detail=dict(**compact(value),evidence_reference=plain(ref)))
    finally:
        with ctx.store.transaction() as db:
            current=ctx.store.session(ctx.run_id,db)['state'];elapsed=time.perf_counter()-start
            current['numerical_s']+=elapsed;current['local_nlp_cost_s']+=elapsed;ctx.store.update_state(db,ctx.run_id,current)


def run_pair(h,choice,reference,key):
    from tools.research_execution import invoke
    receipt=invoke(h,'math.nmpc_settling_check',dict(choice=plain(choice),plan_reference=reference),request_id=key)
    return dict(receipt=receipt,feedback=h.store.artifact(receipt['output']) if receipt.get('output') else None)


def execution_feedback(store,detail):
    reader=ControlEvidence(store);s=reader.resolve(detail['execution_references']['execution_id']);p=detail['profile']
    updates=reader.read_file(s,'controller_observations.json');motion=store.artifact(p['motion']);diagnosis=diagnostic_packet(reader,s,motion)
    ref=None
    with store.transaction() as db:ref=plain(store.put(db,diagnosis))
    return dict(execution_id=s['execution_id'],owner=s['owner'],configuration_identity=digest(scientific_scope(s['configuration'])),
        diagnostic_reference=ref,holding_samples=detail['holding_motion'],
        speed_exceedance_times_s=[m['time_s'] for m in detail['holding_motion'] if m['tip_speed_m_s']>.02],
        position_exceedance_times_s=[m['time_s'] for m in detail['holding_motion'] if m['tip_error_m']>.01],
        actual_tension_bounds_n=p['tension_range_n'],plan_source_counts={k:sum(u['plan_source']==k for u in updates) for k in {u['plan_source'] for u in updates}},
        recovery=dict(attempts=p['recovery_attempts'],selected=p['recovered_plans'],failures=p['recovery_failures'],root_solves=p['recovery_root_solves']),
        stops=p['policy_stop_reason_counts'],raw_stops=p['raw_termination_counts'],prediction_summary=p['one_step_prediction_summary'],
        all35_updates_executed=p['applied_control_updates']==35,wall_clock_real_time=p['real_time_demonstrated'],deadline_misses=p['deadline_misses'],
        joint_acceptance=detail['acceptance'])


if __name__=='__main__':
    import sys
    numeric_pair(read(sys.argv[1]),Path(sys.argv[2]))
