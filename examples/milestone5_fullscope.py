"""Separately authorized full-scope M5 campaign, linked to stopped predecessors."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from examples import milestone5_predictor_campaign as prior
from examples import milestone5_campaign_validation as previous_validation
from tools.platform_store import Store,encode,zero
from tools.platform_host import Host
from tools.state_io import read,atomic_json,digest
from tools.diagnostic_workflow import save
from tools.platform_models import tool_naming_policy,READABLE_TOOL_NAMING
from extensions.tendon_family.control_evidence import ControlEvidence,objective_components
from extensions.tendon_family.diagnostic_evidence import BoundReader
from extensions.tendon_family.diagnostic_math import charge_units
from extensions.tendon_family.milestone5_preparation import RESEARCH
from examples.milestone5_future_validation import SimpleContext

RUN=ROOT/'runs/milestone5_fullscope_20261005'
EVIDENCE=ROOT/'evidence/milestone5_fullscope_20261005'
TOTAL=dict(model_calls=20,tool_calls=160,backend_solves=6,worker_calls=0,wall_s=30000.)
DEVELOPMENT=dict(model_calls=8,tool_calls=100,backend_solves=0,worker_calls=0,wall_s=12000.)
BATCH=dict(model_calls=4,tool_calls=20,backend_solves=2,worker_calls=0,wall_s=6000.)
NUMERICAL=dict(local_solves=300,prediction_evaluations=48,preview_attempts=8)


def predecessor_hashes():
    roots=[prior.RUN,prior.EVIDENCE,previous_validation.folder(1),previous_validation.evidence(1)]
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for root in roots for p in root.rglob('*')
        if p.is_file() and not p.name.endswith(('-wal','-shm'))}


def check_previous():
    prior.check_previous()
    assert predecessor_hashes()==read(RUN/'plan.json')['predecessors'],'STOPPED_PREDECESSOR_CHANGED'


def source(name):
    if name.startswith('reset'):
        store=Store(previous_validation.folder(1));r=ControlEvidence(store)
        result=read(previous_validation.folder(1)/('m5campaign-b1-r'+('1' if name=='reset075' else '2')+'_result.json'))
        return r,r.resolve(result['execution_id'])
    store=Store(prior.RUN);binding=read(prior.RUN/'freeze.json')['bindings'][0 if name=='original075' else 1]
    r=BoundReader(store,binding);return r,r.resolve(r.binding['execution_id'])


def session(name):
    h=Host(RUN,'m5full-'+name)
    with h.store.connect(True) as db:exists=db.execute('SELECT 1 FROM sessions WHERE run_id=?',(h.run_id,)).fetchone()
    if exists:return h
    _,s=source('reset075');cfg=deepcopy(s['configuration']);cfg['run_id']=h.run_id
    provider=deepcopy(read(prior.previous.RUN/'freeze.json')['provider_configuration'])
    bindings={RESEARCH.extension_id:RESEARCH.version,'evidence.read':'1.0.0'}
    provider['protocol_recovery']=dict(max_total=4,max_consecutive=2)
    provider['tool_naming']=tool_naming_policy(bindings,READABLE_TOOL_NAMING)
    cfg['policy'].update(budget=DEVELOPMENT,route=None,allowed_tools=[],tool_bindings=bindings,model=provider,
        timeout_s=600.,operation_allowances={k:dict(timeout_s=10.,reserve_s=5.) for k in bindings})
    h.create(cfg);return h


def prepare():
    from tools.runtime_identity import require_softagent_runtime
    require_softagent_runtime()
    if (RUN/'plan.json').exists():check_previous();return
    store=Store(RUN);store.create(dict(project_id='m5-fullscope-20261005',grant_id='m5-fullscope-development-20261005',
        budget=DEVELOPMENT,authorization_source='Direct user task attachment 640511c9-9216-436f-81ff-1429e0d8966e; full development and conditional validation, DeepSeek and normal origin push authorized.'))
    with store.transaction() as db:db.execute("INSERT INTO meta VALUES ('diagnostic_work',?)",(encode(dict(limits=NUMERICAL,used={k:0 for k in NUMERICAL})),))
    plan=dict(version='m5_fullscope_acceptance@1.0.0',starting_commit='a1f8f5d71f199ab32c86e9464ec5fe11ee94f057',
        predecessor_cumulative=read(prior.RUN/'accounting.json')['cumulative'],predecessors=predecessor_hashes(),
        predecessor_STOP_immutable=True,incumbent=read(prior.RUN/'freeze.json')['incumbent'],
        original_sources=['docs/milestone5.md','docs/milestone5_prediction_validation.md',
            'extensions/tendon_family/milestone5_protocol.py:RULES','extensions/tendon_family/gvs_nmpc.py:DeadlineReachNMPCController.command'],
        thresholds=dict(scaled_residual=1e-5,position_error_m=1e-6,speed_error_m_s=1e-4,vector_error_m_s=1e-4,
            direction_neutral_m_s=1e-4,ranking_gap_m_s=1e-4,task_position_m=.01,holding_speed_m_s=.02,complete_control_update_deadline_s=.01),
        development_cases=[dict(case=n,source=src,update_id=i) for n,src,i in (
            ('shared_first','original075',0),('early_original075','original075',1),
            ('holding_original075','original075',30),('holding_original15','original15',30),
            ('reset_early_shared','reset075',20),('reset_holding_shared','reset075',30))],
        deduplication='Six distinct development state/input/time cases. Reset .075/.15 checkpoints share states and input and count once.',
        admission=dict(numerical='Two successive local resolution comparisons, finite solutions and scaled residual <=1e-5; output vector/speed differences <=1e-4.',
            quantitative='All six declared distinct development cases pass position, speed AND vector thresholds; no ranking-only bypass.',
            direction_threshold='Report resolved coverage/correctness, neutral/indeterminate and both false-safe/false-unsafe. Require 6/6 correct resolved development directions and no threshold errors for a quantitative/threshold claim.',
            discrimination='At least one resolved correct development pair with both predicted and observed position feasibility under original pair_decision. Failed reset pair remains reported, never promoted by raw speed.',
            economics='Fresh independent two-candidate forecast plus all required native decision/correction receipts < ONE evaluation selected for omission; abstention avoids zero.',
            research='Accepted native interpretation of actual concrete results, followed by unchanged public reservation checks.'),
        validation_acceptance=dict(series='Two distinct untouched scenario/recipe combinations plus one preregistered independent repeat; at most three pairs and six complete backends.',
            local='All registered unique local cases pass original quantitative tolerances, numerical checks, direction and threshold rules; duplicates counted separately as observations only.',
            ranking='All three pairs resolved correctly under original feasibility policy; report all abstentions/exclusions and reject any wrong exclusion.',
            economics='Positive all-in counterfactual benefit in each pair and repeat; actual validation savings zero.',
            repeatability='Designated repeat uses same frozen scenario/recipes and independent fresh execution; same acceptance/ranking decisions and metric differences <= original reporting tolerances. Report wall-time differences and require positive economics and deadline pass on both.',
            realtime='Complete command update wall time <=.01 s for every registered production update (35/candidate); includes runtime graph construction and all solve/preparation/validation overhead. Cold setup also reported separately; no hidden compilation.',
            stopping='After a valid pair complete both candidates even if predictions poor. Any numerical, accuracy, direction/threshold, ranking, economics or required timing failure stops further validation; no replacement cases. Accepted research continuation also required.'),
        limits=dict(aggregate=TOTAL,development=DEVELOPMENT,validation_per_batch=BATCH,maximum_batches=3,maximum_predictor_revisions=2,numerical=NUMERICAL),
        protected_finalization_s=1265.,
        workload=dict(initial_matched_solves=2,local_per_revision='6 cases x 3 resolutions =18; at most two revisions',
            forecasts_per_revision='At most four own-history forecasts, initial historical pair and failed reset pair; <=35 controller attempts each. No replays.',
            finalization='At most8 development provider attempts; research and export protected before each expensive operation.'),
        validation_registration='Only after development admission. Unused .30 reset possible; register second untouched case and repeat before any new forecasts/outcomes.',
        physical_scope='No physical parameter changes. Full-order predictor work, if selected, is explicitly labeled and charged, never called reduced or free.',
        cost_allocation='All cold setup, own-history controllers/propagation/output/serialization and required research included. Development reference/diagnostics separate. Validation-only local observer cost measured and excluded only from avoided operational comparator, never from total ledger.',
        performance_workstream='Saved decomposition plus the initial two measured original solves separate cold graph, warm regeneration, optimizer/validation. Select only an evidence-backed bounded performance change; unchanged incumbent preserved. A measured obstruction keeps realtime open.',
        new_campaign_authorized=True,workers=0,subagents=0)
    atomic_json(RUN/'plan.json',plan);atomic_json(RUN/'plan_seal.json',dict(identity=digest(plan),before_new_expensive_work=True))
    atomic_json(RUN/'linked_ledgers.json',dict(aggregate_ceiling=TOTAL,predecessor=plan['predecessor_cumulative'],development=str(RUN),
        conditional_validation=[dict(batch=i,ceiling=BATCH,grant_materialized=False) for i in (1,2,3)]))
    session('diagnostic');print('Acceptance and aggregate allocations frozen before numerical work.')


def run_calculation(name,operation,reserve_s):
    prepare();h=session(name);old=h.store.lookup(h.run_id,name)
    if old:
        assert old['receipt'],'UNRESOLVED_NO_REPLAY'
        receipt=json.loads(old['receipt']);assert receipt['execution_status']=='completed','FAILED_ATTEMPT_NO_REPLAY'
        return h.store.artifact(receipt['output'])
    assert h.store.remaining()['remaining']['wall_s']>=reserve_s+1265.,'FINALIZATION_PROTECTED'
    row,_=h.store.reserve(h.run_id,name,digest(dict(operation=name,plan=digest(read(RUN/'plan.json')))),h.actor,
        {**zero(),'tool_calls':1,'wall_s':reserve_s})
    ctx=SimpleContext(h,row);started=time.monotonic()
    try:
        result=operation(ctx)
        receipt=h.store.complete(row,dict(request_id=name,execution_id=row['execution_id'],caller=h.actor,
            tool_id='analysis.milestone5_fullscope',tool_version='1.0.0',execution_status='completed',charged=zero()),result,time.monotonic()-started)
    except Exception as exc:
        receipt=h.store.complete(row,dict(request_id=name,execution_id=row['execution_id'],caller=h.actor,
            tool_id='analysis.milestone5_fullscope',tool_version='1.0.0',execution_status='failed',charged=zero(),
            error=dict(type=type(exc).__name__,message=str(exc))),dict(error=str(exc)),time.monotonic()-started)
        atomic_json(RUN/(name+'_receipt.json'),receipt);raise
    atomic_json(RUN/(name+'_receipt.json'),receipt);atomic_json(RUN/(name+'.json'),result);check_previous()
    print(json.dumps(dict(operation=name,charged=receipt['charged'])),flush=True);return result


def matched(ctx):
    from schemas.platform import SessionInput
    from extensions.tendon_family.gvs_trajectory import TrajectoryWorkspace
    from extensions.tendon_family.gvs_profile import reach_numerical
    reader,s=source('reset075');observations=reader.read_file(s,'controller_observations.json');o=observations[32]
    state=o['measured_initial_state'];previous=observations[31]['actual_tension_n'];results=[]
    base=deepcopy(s['configuration']);assert o['effective_horizon']==3
    for weight in (.075,.15):
        cfg=deepcopy(base);cfg['policy']['controller']['parameters']['data']['recipe']['holding_tip_speed_weight']=weight
        inp=SessionInput.model_validate(cfg);p=inp.policy.controller.parameters.data['recipe'];num=reach_numerical(inp)
        charge_units(ctx,'local_solves',1);start=time.perf_counter()
        ws=TrajectoryWorkspace(inp.task,inp.robot,{**p,'horizon':3},[*num['nominal']['q0'],*([0.]*(len(state)//2))],num['nominal']['u0'],settling=inp.policy.controller.parameters.data['settling'])
        construction=time.perf_counter()-start
        solved=ws.solve(state,previous,warm=None,elapsed_s=.32)
        checked=ws.solver.evaluate_candidate(ws.problem,solved['result']['optimum'])
        components=objective_components(ws,np.asarray(solved['states']),np.asarray(solved['tensions']),np.asarray(previous))
        result=dict(weight=weight,configuration=cfg,configuration_identity=digest(cfg),common_state=state,previous_input_n=previous,
            elapsed_s=.32,horizon=3,initialization='Common cold constant previous-input seed, original regenerate_warm_states and acceptance policy; not a reconstruction of historical warm plans.',
            selected_plan=solved,first_input_n=solved['tensions'][0],independent_validation=checked,objective_components=components,
            cold_construction_s=construction,complete_cold_s=time.perf_counter()-start,update_s=solved['update_wall_s'],
            warm_preparation_s=solved['warm_start']['preparation_s'],optimizer_and_validation_s=solved['total_s'],deadline_s=.01,
            deadline_missed=solved['update_wall_s']>.01)
        ctx.save_artifact(result,'matched_controller_completed');results.append(result)
    gap=float(np.max(abs(np.asarray(results[0]['first_input_n'])-results[1]['first_input_n'])))
    supported=all(r['selected_plan']['accepted'] and r['independent_validation']['feasible'] for r in results) and gap>1e-9
    return dict(results=results,max_command_separation_n=gap,matched_state_hypothesis_supported=supported,
        source_execution=s['execution_id'],source_manifest=s['manifest'],controller_version='controller.gvs_nmpc@7.0.0',
        controller_attempts=2,backend_attempts=0,inference_scope='One common saved state and cold initialization only; not full-history discrimination, position feasibility or realtime proof.')


def freeze_revision1():
    prepare();path=RUN/'revision1_plan.json'
    if path.exists():return read(path)
    matched_result=read(RUN/'matched.json')
    plan=dict(version='full_serial_continuous@1.0.0',revision=1,
        evidence=['matched.json','../milestone5_predictor_campaign_20261005/localization-r1.json'],
        hypothesis='Discarded serial modes account for instantaneous mapping and much propagation error; retaining all 48 angles and 48 rates removes that representation loss without changing physics.',
        expected_improvement='Zero full-state initial output error and lower local endpoint errors; continuous integration may retain backend discretization error.',
        decisive_comparison='Six preregistered distinct cases, three Radau resolutions each, all original physical/numerical thresholds; future endpoints read for scoring only after each forecast is saved.',
        controller_response=dict(matched_hypothesis=matched_result['matched_state_hypothesis_supported'],
            proposed_causal_rule='Replan every control update during the configured holding window; retain five-interval replanning outside holding. This uses configured task phase, never an observed divergence timestamp.',
            validation='Complete candidate forecasts conditional on local accuracy; no claim from two matched solves.'),
        bounded_work=dict(local_integrations=18,reservation_s=1800.,complete_forecasts=0),
        scope='Full-order continuous serial physics using non-advancing point evaluations. Not reduced, not free backend validation. No production change.')
    atomic_json(path,plan);atomic_json(RUN/'revision1_seal.json',dict(identity=digest(plan),before_revision_evaluation=True));return plan


def freeze_revision2():
    prepare();path=RUN/'revision2_plan.json'
    if path.exists():return read(path)
    first=read(RUN/'revision1_local.json');assert not first['local_admission']
    plan=dict(version='full_serial_discrete@2.0.0',revision=2,evidence=['revision1_local.json','matched.json'],
        hypothesis='After restoring all modes, continuous Radau remains inaccurate against the backend despite refinement. Backend implicitfast finite-step dynamics are the next specific cause.',
        expected_improvement='The saved backend .0005 s implicit-damping recurrence should reproduce local endpoints; decreasing its step may instead converge toward the inaccurate-against-backend continuous prediction.',
        implementation='Full 96-state independent recurrence: (M+h*C)*a=f, v_next=v+h*a, q_next=q+h*v_next, hinge-only ideal tension with joint damping. No mj_step or hidden evaluation.',
        decisive_comparison='Primary prediction is frozen at the actual backend step .0005, independent of outcomes. Also .00025 and .000125: two successive original numerical comparisons. No relabeling backend reproduction as converged continuous physics; admission still requires numerical AND primary quantitative passes.',
        primary_grid_index=0,work=dict(local_integrations=18,reservation_s=1800.,
            optional_complete_forecasts=4,forecast_question='Does causal holding-window replanning plus complete state restore position-feasible discrimination, and what is all-in cost? Development only, even if numerical gate fails.'),
        causal_replan_rule='Every control update in configured holding window; every five intervals before it. Exactly 11 solves for this task, independent of observed divergence time.',
        performance='Reuse one immutable compiled point model across each candidate. All setup charged. Do not alter production solver/early acceptance; measure saved preparation/optimization obstruction.',
        documentation='https://mujoco.readthedocs.io/en/3.9.0/computation/index.html#numerical-integration',
        scope='Full-order backend-equivalent physics emulation, counted as such; no cheap reduced-model claim. Backend outcomes still independent complete evaluations.')
    atomic_json(path,plan);atomic_json(RUN/'revision2_seal.json',dict(identity=digest(plan),before_revision_evaluation=True));return plan


def local_accuracy(ctx,revision=1):
    from extensions.tendon_family.milestone5_fullstate import FullState,DiscreteFullState
    from extensions.tendon_family.milestone5_campaign_predictor import GRIDS
    from extensions.tendon_family.milestone5_first_interval import differences
    from extensions.tendon_family.milestone5_campaign_assessment import score
    cases=[];start=time.perf_counter()
    for case in read(RUN/'plan.json')['development_cases']:
        r,s=source(case['source']);i=case['update_id'];cfg=s['configuration']
        physics=r.read_file(s,'resolved_physics.json');compiled=r.read_file(s,'compiled_physics.json')
        xml=r.store.artifact(s['files']['robot.xml'],raw=True).decode('utf8')
        model=(FullState if revision==1 else DiscreteFullState)(cfg,physics,compiled,xml)
        # Reader supplies the current state and current selected input only.
        trajectory=r.read_file(s,'trajectory.json.gz')
        current=r.read_file(s,'experiment_scene.json') if i==0 else trajectory[i-1]
        observation=r.read_file(s,'controller_observations.json')[i]
        x=np.r_[current['qpos_rad'],current['qvel_rad_s']];u=observation['actual_tension_n']
        initial=model.motion(x);represented=super(FullState,model).motion(observation['measured_initial_state'])
        results=[]
        for grid in GRIDS:
            charge_units(ctx,'prediction_evaluations',1)
            result=model.propagate(x,u,grid=grid,deadline=start+1700.)
            ctx.save_artifact(dict(case=case,result=result,input_n=u,initial_state=x.tolist()),'fullstate_local_prediction_sealed');results.append(result)
        # Future observed endpoint enters only the scorer, never propagate().
        end=trajectory[i];actual=model.motion(np.r_[end['qpos_rad'],end['qvel_rad_s']])
        delta=differences(results)
        valid=len(delta)==2 and all(d['velocity_m_s']<=1e-4 and d['speed_m_s']<=1e-4 for d in delta)
        primary=results[-1] if revision==1 else results[0]
        scored=score(primary,initial,actual,initial,i*.01,valid,max(d['speed_m_s'] for d in delta))
        scored['raw_direction_correct']=scored['predicted_speed_change_m_s']*scored['observed_speed_change_m_s']>0
        scored['speed_false_unsafe']=primary['speed_m_s']>.02 and actual['speed_m_s']<=.02
        scored['holding_false_unsafe']=i>=30 and scored['speed_false_unsafe']
        cases.append(dict(**case,source_manifest=s['manifest'],initial_state=x.tolist(),input_n=u,
            initial=initial,observed_endpoint=actual,results=results,numerical_differences=delta,numerical_pass=valid,score=scored,
            primary_grid_index=(-1 if revision==1 else 0),
            initial_reduced_position_error_m=float(np.linalg.norm(np.asarray(initial['position_m'])-represented['position_m'])),
            initial_reduced_vector_error_m_s=float(np.linalg.norm(np.asarray(initial['velocity_m_s'])-represented['velocity_m_s'])),
            initial_fullstate_output_error_m=0.,backend_timestep_s=float(model.model.opt.timestep),backend_integrator=int(model.model.opt.integrator)))
        atomic_json(RUN/f'revision{revision}_local_progress.json',dict(cases=cases))
        print(json.dumps(dict(case=case['case'],revision=revision,numerical=valid,score=scored)),flush=True)
    counts={k:sum(c['score'][k] for c in cases) for k in ('position_pass','speed_pass','vector_pass','direction_resolved','direction_correct','speed_false_safe','speed_false_unsafe','holding_false_safe','holding_false_unsafe')}
    counts.update(distinct_cases=len(cases),numerical_pass=sum(c['numerical_pass'] for c in cases))
    return dict(revision=revision,cases=cases,counts=counts,integrations=18,backend_steps=0,complete_cost_s=time.perf_counter()-start,
        local_admission=all(counts[k]==6 for k in ('position_pass','speed_pass','vector_pass','direction_correct','numerical_pass')) and not counts['speed_false_safe'] and not counts['speed_false_unsafe'])


def forecast(ctx,name):
    from extensions.tendon_family.milestone5_fullstate import DiscreteFullState,history
    r,s=source(name);scene=r.read_file(s,'experiment_scene.json');start=time.perf_counter()
    physics=r.read_file(s,'resolved_physics.json')
    model=DiscreteFullState(s['configuration'],physics,r.read_file(s,'compiled_physics.json'),r.store.artifact(s['files']['robot.xml'],raw=True).decode('utf8'))
    cfg=deepcopy(s['configuration']);cfg['run_id']=name
    charge_units(ctx,'preview_attempts',1)
    result=history(cfg,scene['qpos_rad']+scene['qvel_rad_s'],model,physics,lambda:charge_units(ctx,'local_solves',1),deadline=start+1080.,
        save_update=lambda row:ctx.save_artifact(dict(candidate=name,row=row),'fullstate_preview_update_completed'))
    result.update(source_manifest=s['manifest'],serial_setup_s=model.setup_s,outer_cost_s=time.perf_counter()-start)
    return result


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--phase',required=True);args=parser.parse_args()
    if args.phase=='prepare':prepare()
    elif args.phase=='matched':run_calculation('matched',matched,600.)
    elif args.phase=='revision1':
        freeze_revision1();run_calculation('revision1_local',local_accuracy,1800.)
    elif args.phase=='revision2':
        freeze_revision2();run_calculation('revision2_local',lambda ctx:local_accuracy(ctx,2),1800.)
    elif args.phase.startswith('forecast_'):
        name=args.phase.removeprefix('forecast_');assert name in ('original075','original15','reset075','reset15')
        run_calculation(args.phase,lambda ctx:forecast(ctx,name),1100.)
    else:raise ValueError('Unsupported phase')
