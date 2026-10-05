"""Linked first-interval/handoff stage, with no simulation or complete-preview entry point."""
from copy import deepcopy
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from examples import milestone5_recovery as previous
from examples import milestone5_preparation as preparation
from tools.platform_store import Store,encode,plain
from tools.platform_host import Host
from tools.platform_registry import registry,dependency_identity
from tools.state_io import read,atomic_json,digest
from tools.runtime_identity import require_softagent_runtime
from tools.diagnostic_workflow import save
from tools.platform_diagnosis_coordinator import configure_role,run_until_handoff
from tools.platform_models import payload_for,tool_naming_policy,READABLE_TOOL_NAMING
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from extensions.tendon_family.milestone5_preparation import RESEARCH
from extensions.tendon_family.milestone5_first_interval import DEFINITION,STEPS
from extensions.tendon_family.diagnostic_evidence import BoundReader,import_execution

RUN=ROOT/'runs/milestone5_first_interval_20261005'
EVIDENCE=ROOT/'evidence/milestone5_first_interval_20261005'
LIMITS=dict(model_calls=6,tool_calls=20,backend_solves=0,worker_calls=0,wall_s=1800.)
NUMERICAL=dict(local_solves=0,prediction_evaluations=6,preview_attempts=0)
AUTHORIZATION=dict(source='User message attachment 81550312-c87d-421b-b023-6a8081d8e041, 2026-10-05; specifically authorizes previously rejected project-evidence transmission',
    destination='https://api.deepseek.com',model='deepseek-flash',credentials='Normal authentication from Join-Path $HOME .codex/.env; never included in evidence or messages',
    data='Relevant configurations, compact preparation/recovery evidence, aligned trajectories, controlled comparisons, preview outcomes/costs/limits, new bounded .00-.01 results, schemas/instructions/budgets/corrections',
    limits=LIMITS,numerical_limits=NUMERICAL,backend_steps=0,complete_previews=0,subagents=0,local_commit=True,push=True,
    push_remote='origin',push_destination='https://github.com/wran021004-gif/softrobot-agent',push_branch='feat/gvs-dynamics',force_push=False)


def reg():
    r=registry();r.add(DEFINITION);return r


def host(name):
    names=read(RUN/'session_revision.json') if (RUN/'session_revision.json').exists() else {}
    return Host(RUN,names.get(name,'m5first-'+name),reg=reg())


def predecessor_snapshot():
    snapshots={}
    for name,folder,evidence in [('recovery',previous.RUN,previous.EVIDENCE),('preparation',preparation.RUN,preparation.EVIDENCE)]:
        store=Store(folder)
        with store.connect(True) as db:
            snapshots[name]=dict(usage=store.remaining(),sessions=[dict(row) for row in db.execute('SELECT * FROM sessions ORDER BY run_id')],
                calls=[dict(row) for row in db.execute('SELECT * FROM calls ORDER BY run_id,request_id')],
                files={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in evidence.rglob('*') if p.is_file()})
    return snapshots


def check_previous():assert predecessor_snapshot()==read(RUN/'freeze.json')['predecessors'],'SEALED_PREDECESSOR_CHANGED'


def prepare():
    require_softagent_runtime()
    if (RUN/'freeze.json').exists():check_previous();return
    store=Store(RUN)
    if not store.db.exists():store.create(dict(project_id='m5-first-interval-20261005',grant_id='m5-first-interval-20261005',budget=LIMITS,authorization_source=json.dumps(AUTHORIZATION)))
    else:
        assert store.config()['grant_id']=='m5-first-interval-20261005' and store.config()['budget']==LIMITS,'EXISTING_STAGE_GRANT_MISMATCH'
    old=Store(previous.RUN);inp=deepcopy(old.session(previous.host('research').run_id)['snapshot']['input'])
    bindings={DEFINITION.extension_id:DEFINITION.version,RESEARCH.extension_id:RESEARCH.version,'evidence.read':'1.0.0'}
    provider=deepcopy(read(previous.RUN/'freeze.json')['provider_configuration']);provider['tool_naming']=tool_naming_policy(bindings,READABLE_TOOL_NAMING)
    provider['protocol_recovery']=dict(max_total=3,max_consecutive=2)
    inp['policy'].update(budget=LIMITS,allowed_tools=[],tool_bindings=bindings,model=provider,timeout_s=600.,operation_allowances={DEFINITION.extension_id:dict(timeout_s=500.,reserve_s=500.),
        RESEARCH.extension_id:dict(timeout_s=10.,reserve_s=5.),'evidence.read':dict(timeout_s=10.,reserve_s=5.)})
    for name in ('research','compute'):
        h=host(name);cfg=deepcopy(inp);cfg['run_id']=h.run_id
        with store.connect(True) as db:exists=db.execute('SELECT 1 FROM sessions WHERE run_id=?',(h.run_id,)).fetchone()
        if not exists:h.create(cfg)
    with store.transaction() as db:db.execute("INSERT OR IGNORE INTO meta VALUES ('diagnostic_work',?)",(encode(dict(limits=NUMERICAL,used={k:0 for k in NUMERICAL})),))
    imported=[]
    for binding in read(previous.RUN/'freeze.json')['bindings']:
        r=BoundReader(old,binding);imported.append(import_execution(r,r.binding['execution_id'],store,host('compute').run_id))
    # Exact source_store from the preparation freeze owns this incumbent binding.
    prior_freeze=read(preparation.RUN/'freeze.json');original=Store(prior_freeze['source_store'])
    reader=BoundReader(original,prior_freeze['source_binding'])
    source_binding=import_execution(reader,reader.binding['execution_id'],store,host('research').run_id)
    frozen=dict(authorization=AUTHORIZATION,predecessors=predecessor_snapshot(),provider_configuration=provider,bindings=imported,source_binding=source_binding,
        incumbent=read(previous.RUN/'freeze.json')['incumbent'],budgets=LIMITS,numerical_limits=NUMERICAL)
    atomic_json(RUN/'authorization.json',AUTHORIZATION);atomic_json(RUN/'freeze.json',frozen)
    atomic_json(RUN/'admission.json',dict(outstanding=['initial research judgment','one shared first-interval calculation','final interpretation/export'],
        completed_work_reused=dict(holding_integrations=14,preparation_reference_integrations=6,complete_previews=2),
        repeated_numerical_work=0,numerical_reserve_s=500.,protected_final_interpretation_export_s=665.,initial_provider_reserve_s=600.,initial_native_handoff_reserve_s=5.,
        total_nominal_reservation_s=1770.,ceiling_s=1800.,passed=True))


def bind():
    prepare();path=RUN/'specification.json'
    if path.exists():return read(path)
    import mujoco
    import numpy as np
    from schemas.platform import SessionInput
    from extensions.tendon_family.gvs_basis import resolve_basis
    from extensions.tendon_family.gvs_projection import project
    store=Store(RUN);cases=[];signatures=[];reference=None
    aligned=read(previous.RUN/'align.json')['result']['cases']
    for binding,alignment in zip(read(RUN/'freeze.json')['bindings'],aligned):
        r=BoundReader(store,binding);s=r.resolve(r.binding['execution_id']);cfg=s['configuration'];inp=SessionInput.model_validate(cfg)
        physics=r.read_file(s,'resolved_physics.json');compiled=r.read_file(s,'compiled_physics.json');scene=r.read_file(s,'experiment_scene.json')
        observations=r.read_file(s,'controller_observations.json');trajectory=r.read_file(s,'trajectory.json.gz');o=observations[0];end=trajectory[0];saved=alignment['rows'][0]
        q,v=scene['qpos_rad'],scene['qvel_rad_s'];basis=resolve_basis(inp.robot.structure.data,inp.policy.controller.parameters.data['recipe']['basis'])
        z=project(physics,basis,q,v);state=z['q_gvs']+z['qdot_gvs'];ze=project(physics,basis,end['qpos_rad'],end['qvel_rad_s']);endpoint_state=ze['q_gvs']+ze['qdot_gvs']
        assert state==o['measured_initial_state']==saved['preview_start_state'],'FIRST_START_STATE'
        assert saved['preview_input_n']==o['actual_tension_n']==o['desired_tension_n']==o['requested_tension_n']==end['tension_n'],'FIRST_HELD_IDEAL_INPUT'
        assert compiled['tension_execution_mode']=='ideal_tension' and cfg['task']['timing']['control_period_s']==.01
        assert o['time_s']==saved['start_s']==0. and abs(end['time_s']-.01)<1e-12 and end['solver_time_s']==0.
        assert o['one_step_prediction']['frame']=='world' and o['one_step_prediction']['applied_tension_n']==o['actual_tension_n']
        order=[t['id'] for t in cfg['robot']['structure']['data']['tendons']];assert order==[t['entity'] for t in physics['tendons']]
        backend=mujoco.MjModel.from_xml_string(store.artifact(s['files']['robot.xml'],raw=True).decode('utf8'));data=mujoco.MjData(backend)
        data.qpos[compiled['qpos_indices']]=q;data.qvel[compiled['qvel_indices']]=v;mujoco.mj_forward(backend,data)
        def backend_motion():
            J=np.zeros((3,backend.nv));Jr=np.zeros_like(J);mujoco.mj_jacSite(backend,data,J,Jr,backend.site('tip_site').id);velocity=J@data.qvel
            return dict(position_m=data.site_xpos[backend.site('tip_site').id].tolist(),velocity_m_s=velocity.tolist(),speed_m_s=float(np.linalg.norm(velocity)))
        initial=backend_motion();assert np.max(abs(np.asarray(initial['position_m'])-o['tip_position_m']))<1e-12
        initial_full=dict(qpos=data.qpos.tolist(),qvel=data.qvel.tolist(),act=data.act.tolist(),time_s=float(data.time),ctrl=data.ctrl.tolist(),
            provenance='Original saved experiment_scene initializer reconstructed in fresh MjData using the historical backend initialization path. Physical coordinates/velocities are exact; a historical integration-cache snapshot was not retained.')
        data.qpos[compiled['qpos_indices']]=end['qpos_rad'];data.qvel[compiled['qvel_indices']]=end['qvel_rad_s'];mujoco.mj_forward(backend,data);observed=backend_motion()
        for k in ('position_m','velocity_m_s'):assert np.max(abs(np.asarray(observed[k])-saved['observed_endpoint'][k]))<1e-12
        assert np.max(abs(np.asarray(observed['position_m'])-end['tip_m']))<1e-12
        signature=dict(robot=cfg['robot'],environment=cfg['task']['environment'],initializer=cfg['task']['initializer'],seed=cfg['seed'],
            basis=inp.policy.controller.parameters.data['recipe']['basis'],xml=s['files']['robot.xml'],physics=s['files']['resolved_physics.json'],compiled=s['files']['compiled_physics.json'],
            full_initial=initial_full,state=state,input_n=o['actual_tension_n'],interval_s=[0.,.01],tendon_order=order,tip=physics['tip'],
            endpoint_qpos=end['qpos_rad'],endpoint_qvel=end['qvel_rad_s'],observed=observed,saved_coarse_state=saved['preview_end_state'],saved_coarse_endpoint=saved['preview_endpoint'])
        signatures.append(digest(signature));cases.append(dict(candidate_id=r.binding['candidate_id'],execution_id=s['execution_id'],holding_weight=cfg['policy']['controller']['parameters']['data']['recipe']['holding_tip_speed_weight'],
            manifest=s['manifest'],files=s['files'],configuration=r.binding['configuration'],observation_pointer='/0',trajectory_pointer='/0',preview=saved['sources']['preview'],preview_pointer='/result/rows/0',shared_identity=signatures[-1]))
        if reference is None:reference=dict(configuration=cfg,state=state,observed_projected_state=endpoint_state,input_n=o['actual_tension_n'],observed=observed,initial_backend_motion=initial,
            full_initial_backend_state=initial_full,tendon_order=order,projection_at_start=z,projection_at_endpoint=ze,saved_coarse=dict(state=saved['preview_end_state'],**saved['preview_endpoint']))
    if len(set(signatures))!=1:raise ValueError('FIRST_INTERVAL_NOT_SHARED_STOP')
    spec=dict(**reference,cases=cases,shared=True,shared_identity=signatures[0],interval_s=[0.,.01],time_origin_s=0.,steps_s=list(STEPS),
        rule='Original historical first interval before any state/input history substitution. One computation referenced by both cases; objective weights do not enter fixed-input dynamics.',
        numerical_stability_rule='Two last successive fine-resolution vector AND speed differences <=1e-4 m/s. Stop after four attempts if supported; remaining two only for unresolved stability. No proven error bound.',
        stop_rules=['Coarse state max discrepancy >1e-7, vector >1e-8 or position >1e-9 -> stop before finer propagation','Nonfinite or scaled residual >1e-5 -> stop','At most six attempts and 320 substeps, unchanged .01 interval','Always protect 665 s for final interpretation/handoff/export'],
        input_semantics='Recorded direct ideal applied tension available before interval advancement, held constant; no measured future average',
        output_definition='World tip_site position and J_site(q) @ qdot for backend; unchanged model tip and its analytic world-frame Jacobian for reduced outputs',backend_advances=0)
    spec['identity']=digest(spec);atomic_json(path,spec);save(store,spec);check_previous();return spec


def research(phase,packet,instruction,*,revision=False):
    h=host('research');path=RUN/(phase+'_response.json');prior=h.store.session(h.run_id)['state'].get('handoffs',{}).get('m5_'+phase)
    if prior and not revision:
        result=h.store.artifact(prior);atomic_json(path,result);return result
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
    with h.store.transaction() as db:
        state=h.store.session(h.run_id,db)['state'];state.setdefault('fact_scope',dict(project='m5-first-interval-20261005',binding=read(RUN/'freeze.json')['source_binding']));state.setdefault('fact_catalog',{})
        h.store.update_state(db,h.run_id,state)
    instruction+=' Return exactly one native research.milestone5_preparation call with phase='+phase+', holding_weights, rationale, readiness, limitations, next_action=finish_stop. No printed JSON substitute. Retain incumbent, M2-4 closed/M5 open; zero backend/full previews/controller attempts.'
    protection=dict(model_calls=3,tool_calls=3,wall_s=1165.) if phase=='selection' else dict(wall_s=60.)
    configure_role(h,'design',instruction,phase=phase,delivery_tool=RESEARCH.extension_id,native_store_root=str(RUN),memory_identity=h.run_id,native_fixed={},
        binding=read(RUN/'freeze.json')['source_binding'],decision_packet=packet,decision_packet_reference=save(h.store,packet),
        phase_budget=dict(limit=dict(model_calls=3,tool_calls=8,wall_s=600.),protect_project=protection))
    atomic_json(RUN/(phase+'_serialized_handoff.json'),payload_for(h,EvidenceDrivenAdapter()))
    ref=run_until_handoff(h,'m5_'+phase);result=h.store.artifact(ref);atomic_json(path,result);check_previous();return result


def initial():
    prepare();spec=bind();alignment=read(previous.RUN/'align.json')['result'];comp=read(previous.RUN/'compare.json')['result']
    packet=dict(authorization=AUTHORIZATION,incumbent=read(RUN/'freeze.json')['incumbent'],earlier_reference=read(preparation.RUN/'reference.json'),
        complete_preview_summary=read(preparation.RUN/'preview_summary.json'),holding_entry_decomposition=comp,
        first_error_timeline=[c['summary'] for c in alignment['cases']],first_interval_specification={k:v for k,v in spec.items() if k not in ('configuration','full_initial_backend_state')},
        future_registration=dict(scenarios=[{k:s[k] for k in ('scenario_id','source_time_s','task_origin_s','controller_initialization','state_policy','prospective_outcome')} for s in read(preparation.RUN/'registration.json')['scenarios']],provisional_weights=[.075,.15],terminal=.05),
        prior_rejections=[read(previous.RUN/'platform_rejection.json'),read(preparation.RUN/'platform_rejection.json')],remaining=Store(RUN).remaining()['remaining'])
    research('selection',packet,'Finish the blocked research judgment from SAVED evidence. Explicitly: (1) what existing local references, false-safe holding prediction, abstention at unchanged 1e-4 ranking margin and adverse cost support; (2) distinguish shared-input .01 endpoint error, own-history command separation at .02, and weight-preview separation at .20; (3) judge informativeness of the one SHARED original .00-.01 fixed-input refinement; (4) retain or revise a concrete supported conditional future pair, or defer screening execution honestly; (5) research judgment is not validated screening capability. Choose two distinct holding weights in [.0001,1], terminal .05, explaining conditional status, reset-clock scenarios versus historical warm continuation. Do not rubber-stamp readiness. About 450 words.')


def calculate():
    spec=bind();h=host('compute');prior=h.store.lookup(h.run_id,'shared-first-interval')
    if prior:
        if not prior['receipt']:raise ValueError('UNRESOLVED_FIRST_INTERVAL_NO_REPLAY')
        receipt=json.loads(prior['receipt'])
        reservation=next(e for e in h.store.events(h.run_id) if e['request_id']=='shared-first-interval' and e['status']=='reserved')
        request=h.store.artifact(reservation['inputs'][0]);saved=h.store.artifact(request['arguments']['protocol'])
        if saved!=spec:raise ValueError('SAVED_FIRST_INTERVAL_SPECIFICATION_MISMATCH')
    else:
        if h.store.remaining()['remaining']['wall_s']<1165.:raise ValueError('PROTECTED_FINAL_INTERPRETATION_EXPORT')
        h.resume();receipt=h.invoke(dict(request_id='shared-first-interval',tool_id=DEFINITION.extension_id,tool_version=DEFINITION.version,
            arguments=dict(protocol=save(h.store,spec)),reason='Authorized shared first interval only; unchanged original dynamics/state/input; no backend step',cache='new'))
    atomic_json(RUN/'calculation_receipt.json',receipt)
    if receipt['execution_status']!='completed':raise ValueError(str(receipt.get('error')))
    result=h.store.artifact(receipt['output'])['detail'];atomic_json(RUN/'calculation.json',result);check_previous();return result


def interpret():
    prepare();result=read(RUN/'calculation.json');selection=read(RUN/'selection_response.json')
    packet=dict(authorization=AUTHORIZATION,selected_weights=selection['holding_weights'],initial_research_judgment=selection,first_interval=result,
        actual_backend_endpoint=read(RUN/'specification.json')['observed'],saved_coarse_preview=read(RUN/'specification.json')['saved_coarse'],
        initial_semantic_review=read(RUN/'initial_semantic_review.json'),
        earlier_preview_summary=read(preparation.RUN/'preview_summary.json'),holding_decomposition=read(previous.RUN/'compare.json')['result'],
        incumbent=read(RUN/'freeze.json')['incumbent'],remaining=Store(RUN).remaining()['remaining'])
    research('interpretation',packet,'Answer specifically: Under the SAME starting physical condition and held input, did numerical refinement substantially reduce the earliest velocity-vector discrepancy, and what remains unresolved? Correct the initial response using initial_semantic_review: no 1e-6 m scatter; actual first .01 error is .0540802 m/s and .414378 mm. Own-backend command separation .02 s and inter-weight preview separation .20 s are distinct. Quantify coarse reproduction, fine successive vector/speed differences, backend vector-error change (absolute/relative), speed and position error, instantaneous projected observed output vs actual backend, and remaining evolution discrepancy. Interpret vector cancellation and decomposition order without causal percentages or an automatic projection-bug claim. Distinguish local numerical stability from backend agreement and full-history screening; report costs and uncertainty. Select exactly ONE next direction explicitly in rationale: A if refinement materially helps, propose narrow simulated-plant propagation investigation; B if a stable fine result retains substantial error, propose one specific model/representation/output-mapping investigation supported by decomposition; C if stability/alignment unresolved, name that prerequisite and stop. Give a concrete falsification test and fixed conditions for the ONE investigation. It remains unexecuted. No weight experiment, full preview, backend validation, output-definition change, scalar correction or parameter fit. Keep selected holding_weights unchanged, retain local diagnosis/deferred screening as warranted. About 600 words.' + (' Numerical stability is unresolved in the supplied result: select C under the user rule, while reporting the material observed error reduction. The finest tested endpoint is not a supported reference; do not call its residual a stabilized physical error.' if not result['numerical_stability_supported'] else ''))


def correct_interpretation():
    """One focused semantic correction using saved results, not another calculation."""
    original=read(RUN/'interpretation_response.json');result=read(RUN/'calculation.json');spec=read(RUN/'specification.json')
    atomic_json(RUN/'interpretation_response_v1.json',original)
    correction=dict(classification='Factual/scientific review of an accepted native response; original artifact/receipt preserved',
        issues=['The first final response mislabeled the saved coarse preview position/speed as the actual backend endpoint.',
            'It reported the coarse evolution term without distinguishing the finest decomposition.',
            'Near-two refinement ratios do not imply non-asymptotic or step-dominated residual behavior.',
            'Its proposed future step range was already computed, and backend error monotonicity was incorrectly part of numerical stability.'],
        actual_backend_endpoint=spec['observed'],projected_observed_output=result['observed_projected_output'],
        finest_tested_endpoint=result['results'][-1],finest_accounting=result['endpoint_accounting'][-1],
        required_next_direction='C: establish local numerical stability, independently of backend agreement; next unexecuted data must extend beyond the tested finest step under separate authorization',
        new_integrations=0,semantic_corrections=1)
    atomic_json(RUN/'semantic_correction.json',correction)
    research('interpretation',dict(authorization=AUTHORIZATION,selected_weights=original['holding_weights'],prior_accepted_interpretation=original,
        correction=correction,first_interval=result,initial_semantic_review=read(RUN/'initial_semantic_review.json')),
        'Correct the accepted final interpretation using the explicitly labeled data in correction. The actual backend endpoint has speed .2819050808123714, position [.2979194519722485,.001318325730051994,.15133566194286324]; .22794196889585266 and [.2978981618,.0015026661,.1517061674] are COARSE PREVIEW values. At the finest step report the THREE velocity vectors evolution, projection/output, total, their norms .0391120411/.0340705821/.0100556261, and exact cancellation identity. Projection position discrepancy is .000251437 m, while finest total position discrepancy is .0000504529 m. Near-two halving ratios are consistent with first-order asymptotic scaling but do not establish the reporting tolerance; do not claim they imply non-asymptotic behavior or that the finest residual is step-dominated. Keep the material 81.406% vector-error reduction and unresolved stability (.000247710 vector/.000244941 speed last differences >1e-4). Select only direction C: local reference stability remains the prerequisite. State ONE precise UNEXECUTED follow-up that does not rerun the already tested .0005 through .00003125 s sequence: finer than the tested finest step, same .01 duration/original zero state/held direct input/model/output, separately authorized with its own cap/budget. Numeric self-consistency requires successive vector AND speed differences <=1e-4, finite root/residual <=1e-5; backend error reduction or monotonicity is a separate accuracy question, never a stability gate. A falsifying result is persistent resolution sensitivity/nonfinite roots or residual failure, not worsening backend agreement alone. No current follow-up execution. Keep .075/.15 and deferred screening, incumbent retained/M2-4 closed/M5 open. Preserve distinctions among numerical stability, physical agreement, instantaneous representation and complete-history screening. About 650 words.',revision=True)


def export():
    check_previous();store=Store(RUN);selection=read(RUN/'selection_response.json') if (RUN/'selection_response.json').exists() else None
    interpretation=read(RUN/'interpretation_response.json') if (RUN/'interpretation_response.json').exists() else None
    state=store.session(host('research').run_id)['state'];refs=state.get('handoffs',{});decisions={p:refs['m5_'+p] for p in ('selection','interpretation') if 'm5_'+p in refs}
    provisional=selection or dict(holding_weights=[.075,.15],rationale='Provisional historical pair; no accepted new-stage research selection')
    p=preparation.protocol(read(preparation.RUN/'registration.json'),provisional,read(preparation.RUN/'reference.json'),research_store=store,decision_refs=decisions,
        supersedes=dict(protocol='evidence/milestone5_recovery_20261005/protocol.json',seal=read(previous.RUN/'protocol_seal.json'),previous_rejections=['evidence/milestone5_recovery_20261005/platform_rejection.json','evidence/milestone5_preparation_20261005/platform_rejection.json']))
    p.update(version='milestone5_first_interval_protocol@1.0.0',status='completed_local_diagnosis_screening_deferred' if interpretation else 'local_complete_research_handoff_blocked',
        accepted_research_judgment=interpretation,first_interval_specification='specification.json',first_interval_result='calculation.json',
        scope='Original shared .00-.01 s retrospective evidence only; no future forecast or execution grant',operational_next_action='finish_stop')
    p['reservations']['previous_preparation']=p['reservations'].pop('development');p['reservations']['first_interval_stage']=dict(ceiling=LIMITS,numerical_ceiling=NUMERICAL,admission='admission.json',actual_accounting='accounting.json')
    p['implementation_identity']['files'].update({n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ('examples/milestone5_first_interval.py','extensions/tendon_family/milestone5_first_interval.py')})
    p['commands']=dict(status='python examples/milestone5_first_interval.py --check',operational_next_action='finish_stop')
    atomic_json(RUN/'protocol.json',p);ref=save(store,p);atomic_json(RUN/'protocol_seal.json',dict(protocol_reference=ref,protocol_identity=digest(p),supersedes=p['supersedes'],forecast_generated=False,backend_authorized=False))
    result=read(RUN/'calculation.json') if (RUN/'calculation.json').exists() else None
    from examples.milestone5_future_validation import readiness
    ready=readiness(p);ready['dimensions']=dict(research_handoff_complete=bool(selection and interpretation),first_interval_computation_complete=result is not None,
        numerical_stability_supported=False if result is None else result['numerical_stability_supported'],physical_agreement='See calculation; no physical validation claim',
        next_investigation_selected=bool(interpretation),screening_readiness=False,milestone_acceptance=False)
    ready['numerical_reference_stable_scope']='The inherited readiness check concerns earlier registered holding-entry references; current first-interval stability is reported separately in dimensions.'
    if result:
        ready['dimensions']['physical_agreement']=dict(vector_error_reduced=result['vector_error_change']['absolute_reduction_m_s']>0,
            finest_tested_vector_error_m_s=result['vector_error_change']['finest_tested_error_m_s'],
            quantitative_endpoint_accuracy_demonstrated=result['numerical_stability_supported'] and result['results'][-1]['velocity_error_norm_m_s']<=1e-4 and abs(result['results'][-1]['speed_error_m_s'])<=1e-4,
            classification='Retrospective agreement improved relative to coarse; finest tested only unless local stability supported')
    atomic_json(RUN/'readiness.json',ready)
    with store.transaction() as db:
        store.event(db,host('research').run_id,'first_interval_stage','finish_stop',outputs=[ref])
        for row in db.execute('SELECT run_id FROM sessions').fetchall():
            session=store.session(row[0],db);session['state']['first_interval_stage_finished']=True;store.update_state(db,row[0],session['state'],'stopped')
    with store.connect(True) as db:
        receipts=[json.loads(row[0]) for row in db.execute('SELECT receipt FROM calls WHERE receipt IS NOT NULL')]
        work=json.loads(db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone()[0]);ids=[row[0] for row in db.execute('SELECT run_id FROM sessions')]
    used=store.remaining()['used'];historical=read(previous.RUN/'accounting.json')['cumulative'];charges={k:sum(r['charged'][k] for r in receipts) for k in used}
    assert all(abs(used[k]-charges[k])<1e-7 for k in used)
    atomic_json(RUN/'accounting.json',dict(historical=historical,new_stage=used,cumulative={k:historical[k]+used[k] for k in historical},limits=LIMITS,numerical_work=work,
        receipt_charge_sum=charges,occupied=store.remaining().get('occupied',{}),cumulative_numerical_work=dict(controller_solves=79,standalone_reduced_rollouts=35+work['used']['prediction_evaluations'],historical_backend_controller_updates=210,new_backend_updates=0),
        corrections=dict(total=state.get('protocol_corrections_used',0),consecutive=state.get('protocol_corrections_consecutive',0),business=state.get('business_failures_total',0),
            semantic_provider_corrections=1 if (RUN/'semantic_correction.json').exists() else 0,
            deterministic_initial_annotations=1 if (RUN/'initial_semantic_review.json').exists() else 0,
            native_handoff_reservation_repairs=1 if (RUN/'handoff_reservation_repair.json').exists() else 0),
        reused=dict(holding_integrations=14,preparation_reference_integrations=6,complete_previews=2,recomputation_charge=0),
        convention='Nested model construction/integration charged once in outer receipt. Reading/editing/export/testing follow existing offline engineering accounting. One shared calculation referenced by both candidates.'))
    atomic_json(RUN/'receipts.json',receipts);events=[e for run_id in ids for e in store.events(run_id)];atomic_json(RUN/'events.json',events)
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    for file in RUN.glob('*.json'):(EVIDENCE/file.name).write_bytes(file.read_bytes())
    seen=set()
    def copy(value):
        if isinstance(value,dict):
            if set(value)=={'artifact_id','media_type'} and isinstance(value['artifact_id'],str) and isinstance(value['media_type'],str):
                key=value['artifact_id']
                if key in seen:return
                seen.add(key)
                try:body=store.artifact(value,raw=True)
                except (ValueError,KeyError):return
                target=EVIDENCE/'artifacts'/(key+('.json' if value['media_type']=='application/json' else '.bin'));target.parent.mkdir(exist_ok=True);target.write_bytes(body)
                if value['media_type']=='application/json':copy(json.loads(body))
            else:
                for child in value.values():copy(child)
        elif isinstance(value,list):
            for child in value:copy(child)
    copy(events);copy(receipts)
    for name in ('examples/milestone5_first_interval.py','extensions/tendon_family/milestone5_first_interval.py','tests/test_milestone5_first_interval.py'):
        target=EVIDENCE/'implementation'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/name).read_bytes())
    atomic_json(EVIDENCE/'delivery.json',dict(status=p['status'],research_handoff_complete=bool(selection and interpretation),accepted_decision_references=decisions,
        computation_complete=result is not None,numerical_stability_supported=False if result is None else result['numerical_stability_supported'],
        next_direction='C: unresolved local numerical stability prerequisite',follow_up_executed=False,
        incumbent=read(RUN/'freeze.json')['incumbent'],milestone2='closed',milestone3='closed',milestone4='closed',milestone5='open',
        screening_ready=False,backend_attempts=0,backend_steps=0,complete_previews=0,controller_attempts=0,workers=0,subagents=0,operational_next_action='finish_stop',
        report='docs/milestone5_first_interval.md',accounting='accounting.json',protocol='protocol.json',verification='verification.json',push_status='Authorized; recorded separately after commit, not a computation grant'))
    atomic_json(EVIDENCE/'sha256_manifest.json',{file.relative_to(EVIDENCE).as_posix():hashlib.sha256(file.read_bytes()).hexdigest() for file in sorted(EVIDENCE.rglob('*')) if file.is_file() and file.name!='sha256_manifest.json'})
    print(json.dumps(dict(status=p['status'],usage=used,numerical=work),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['prepare','initial','calculate','interpret','correct','export']);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    if args.check:
        from examples.milestone5_future_validation import readiness
        print(json.dumps(readiness(read(EVIDENCE/'protocol.json')),indent=2))
    elif args.phase=='prepare':bind()
    elif args.phase=='initial':initial()
    elif args.phase=='calculate':calculate()
    elif args.phase=='interpret':interpret()
    elif args.phase=='correct':correct_interpretation()
    elif args.phase=='export':export()
    else:parser.error('Choose a phase; no backend or complete-preview path exists.')
