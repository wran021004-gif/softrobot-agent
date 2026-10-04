"""Linked preparation/development grant. Future batches require a separate grant."""
from copy import deepcopy
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from examples import milestone5_diagnostic as predecessor
from examples import milestone5_validation as validation
from tools.platform_store import Store, plain, encode
from tools.platform_host import Host
from tools.platform_registry import registry
from tools.state_io import read, atomic_json, digest
from tools.runtime_identity import require_softagent_runtime
from tools.diagnostic_workflow import save
from tools.platform_diagnosis_coordinator import configure_role, run_until_handoff
from tools.platform_models import payload_for, tool_naming_policy, READABLE_TOOL_NAMING
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from tools.batch_budget import batch_requirement
from extensions.tendon_family.diagnostic_evidence import BoundReader
from extensions.tendon_family.milestone5_preparation import DEFINITION,RESEARCH,grid,PREVIEW_VERSION,LOCAL_VERSION

RUN=ROOT/'runs/milestone5_preparation_20261005'
EVIDENCE=ROOT/'evidence/milestone5_preparation_20261005'
LIMITS=dict(model_calls=8,tool_calls=40,backend_solves=0,worker_calls=0,wall_s=3600.)
NUMERICAL=dict(local_solves=80,prediction_evaluations=8,preview_attempts=2)
AUTHORIZATION=dict(source='User attachment af376585-dba7-4da7-865d-c594fddbc711, 2026-10-05',
    destination='https://api.deepseek.com',model='deepseek-flash',scope='Both M5 capabilities: preparation and bounded development only',
    data='Relevant configurations, compact saved evidence, calculations, implementation, tools and research interpretation',
    limits=LIMITS,numerical_limits=NUMERICAL,backend_steps=0,subagents=0,commit_local=True,push=False)


def reg():
    return registry()


def immutable():
    w=predecessor.restore()
    return dict(usage=w.store.remaining(),state=predecessor.sealed_state(w.store),
        files={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in predecessor.EVIDENCE.rglob('*') if p.is_file()})


def check_previous(frozen):
    assert immutable()==frozen['predecessor'], 'PREDECESSOR_CHANGED'


def host(name):return Host(RUN,'m5prep-'+name+'-registered',reg=reg())


def inventory_record(store,facts):
    cfg=store.artifact(facts['configuration'])['effective'];control=cfg['policy']['controller'];recipe=control['parameters']['data']['recipe']
    structure=cfg['robot']['structure']['data'];settling=facts.get('sampled_settling',{})
    return dict(candidate=facts['candidate'],execution_id=facts['execution_id'],configuration=facts['configuration'],
        holding_weight=recipe['holding_tip_speed_weight'],terminal_weight=recipe['terminal_tip_speed_weight'],
        controller=dict(extension_id=control['extension_id'],version=control['version']),
        component_lengths_m={c['id']:c.get('length_m') for c in structure['components'] if c['id'] in ('near','far')},
        physical_selections=structure.get('metadata',{}).get('semantic_resolved',{}).get('selections',{}),
        terminal_error_m=facts['terminal_error_m'],sampled_settling=settling,
        mean_update_s=facts['mean_complete_update_s'],classification='Historical development inventory; no new evaluation')


def prepare():
    require_softagent_runtime()
    if (RUN/'freeze.json').exists():return read(RUN/'freeze.json')
    old=predecessor.restore();p=old.store.artifact(old.freeze['diagnostic_protocol'])
    reader=BoundReader(old.store,p['incumbent_binding']);source=reader.resolve(reader.binding['execution_id'])
    store=Store(RUN);store.create(dict(project_id='m5-preparation-20261005',grant_id='m5-preparation-20261005',budget=LIMITS,
        authorization_source=json.dumps(AUTHORIZATION)))
    bindings={DEFINITION.extension_id:DEFINITION.version,RESEARCH.extension_id:RESEARCH.version,'evidence.read':'1.0.0'}
    inp=deepcopy(old.store.session(old.hosts['executor'].run_id)['snapshot']['input'])
    inp['policy'].update(budget=LIMITS,allowed_tools=[],tool_bindings=bindings,timeout_s=1500.,
        operation_allowances={DEFINITION.extension_id:dict(timeout_s=1500.,reserve_s=1500.)})
    provider=deepcopy(old.freeze['provider_configuration']);provider['tool_naming']=tool_naming_policy(bindings,READABLE_TOOL_NAMING)
    inp['policy']['model']=provider
    for name in ('research','reference','history075','history15'):
        h=host(name);current=deepcopy(inp);current['run_id']=h.run_id;h.create(current)
    with store.transaction() as db:
        db.execute("INSERT INTO meta VALUES ('diagnostic_work',?)",(encode(dict(limits=NUMERICAL,used={k:0 for k in NUMERICAL})),))
    # Copy only exact references needed by the diagnostic calculations.
    for row in read(predecessor.RUN/'intervals.json')['result']:
        ref=row['configuration']
        with store.transaction() as db:assert plain(store.put(db,old.store.artifact(ref,raw=True),ref['media_type']))==ref
    frozen=dict(authorization=AUTHORIZATION,predecessor=immutable(),provider_configuration=provider,
        source_binding=p['incumbent_binding'],source_store=str(predecessor.RUN),base_configuration=source['configuration'],
        incumbent=old.freeze['incumbent'],limits=LIMITS,numerical_limits=NUMERICAL)
    atomic_json(RUN/'freeze.json',frozen);atomic_json(RUN/'authorization.json',AUTHORIZATION)
    return frozen


def register(frozen):
    path=RUN/'registration.json'
    if path.exists():return read(path)
    import mujoco
    import numpy as np
    from schemas.platform import SessionInput
    from extensions.tendon_family.gvs_projection import project
    from extensions.tendon_family.gvs_basis import resolve_basis
    from extensions.tendon_family.gvs_profile import reach_numerical
    old=predecessor.restore();r=BoundReader(old.store,frozen['source_binding']);s=r.resolve(r.binding['execution_id'])
    physics=r.read_file(s,'resolved_physics.json');compiled=r.read_file(s,'compiled_physics.json');control=r.read_file(s,'control_spec.json')
    trajectory=r.read_file(s,'trajectory.json.gz');updates=r.read_file(s,'controller_observations.json')
    xml=old.store.artifact(s['files']['robot.xml'],raw=True).decode('utf8');model=mujoco.MjModel.from_xml_string(xml)
    assert model.na==0 and model.nmocap==0 and model.nq==len(physics['dofs']) and model.nv==len(physics['dofs'])
    scenarios=[]
    for t in (.20,.30):
        index=next(i for i,row in enumerate(trajectory) if abs(row['time_s']-t)<1e-9);row=trajectory[index]
        cfg=deepcopy(s['configuration']);cfg['task']['initializer']['parameters']['data']=dict(
            qpos_rad=dict(zip(physics['dofs'],row['qpos_rad'])),qvel_rad_s=dict(zip(physics['dofs'],row['qvel_rad_s'])),unspecified='zero')
        data=mujoco.MjData(model);data.qpos[compiled['qpos_indices']]=row['qpos_rad'];data.qvel[compiled['qvel_indices']]=row['qvel_rad_s']
        data.time=0.;mujoco.mj_forward(model,data) # authorized kinematics only
        state_spec=mujoco.mjtState.mjSTATE_INTEGRATION;full=np.zeros(mujoco.mj_stateSize(model,state_spec));mujoco.mj_getState(model,data,full,state_spec)
        restored=mujoco.MjData(model);mujoco.mj_setState(model,restored,full,state_spec);mujoco.mj_forward(model,restored)
        assert restored.time==0 and np.array_equal(restored.qpos,data.qpos) and np.array_equal(restored.qvel,data.qvel)
        basis=resolve_basis(SessionInput.model_validate(cfg).robot.structure.data,control['effective_parameters']['basis'])
        projection=project(physics,basis,row['qpos_rad'],row['qvel_rad_s']);numerical=reach_numerical(SessionInput.model_validate(cfg))
        item=dict(scenario_id='incumbent_checkpoint_'+str(round(t*100))+'_new_clock',configuration=cfg,
            robot_identity=digest(cfg['robot']),task_identity=digest(cfg['task']),backend_model='mujoco_serial_bending_v1',reduced_model='model.gvs@1.0.0',
            source_execution=s['execution_id'],source_manifest=s['manifest'],source_trajectory=s['files']['trajectory.json.gz'],source_pointer='/'+str(index),
            xml=s['files']['robot.xml'],compiled_physics=s['files']['compiled_physics.json'],source_time_s=t,
            backend_initial_time_s=0.,controller_initial_time_s=0.,task_origin_s=0.,interval_s=[0.,.35],
            full_restorable_new_episode_state=dict(spec='mjSTATE_INTEGRATION',spec_value=int(state_spec),values=full.tolist(),identity=digest(full.tolist())),
            state_policy='Historical named qpos/qvel loaded by initialize.family; new MjData resets integrator caches, applied forces, control, time and actuator state. This is NOT an exact historical integrator continuation.',
            state_compatibility=dict(nq=model.nq,nv=model.nv,na=model.na,nmocap=model.nmocap,roundtrip=True,backend_advanced=False),
            source_previous_input_n=row['tension_n'],new_controller_previous_input_n=numerical['nominal']['u0'],
            actuator_policy='No dynamic activation state (na=0). Reset ctrl/applied forces; first command overwrites direct-tension ctrl.',
            controller_initialization='Production reach_numerical bundled_guess: historical initial tensions only; placeholder states regenerated with current candidate model. Reset observation count, last plan and failure count.',
            warm_guess_identity=digest(numerical['warm_guess']),historical_warm_plan_available=False,
            reduced_initial_state=projection['q_gvs']+projection['qdot_gvs'],projection=projection,
            available_history=dict(classification='historical development only',trajectory_through_index=index,controller_updates_through_time_s=t,
                allowed_for_forecast='Source state and configuration only; no historical future values or plans are fed into preview.'),
            prospective_outcome='Two recipes starting from this named state with a new .35 s task and controller reset; no such complete scenario/recipe outcome has been evaluated.',
            independence='Two distinct historical states; new scenario/recipe outcomes are prospective, not independent random trials.')
        scenarios.append(item)
    previous=validation.restore();inventory=[]
    # Compact inventory read once from the accepted predecessor record, not experiment discovery.
    for record in previous.historical_results:
        facts=record['facts'];inventory.append(inventory_record(previous.store,facts))
    inventory.extend(dict(candidate_id=row['candidate_id'],execution_id=row['execution_id'],holding_weight=weight,classification='historical development')
        for row,weight in zip(read(predecessor.RUN/'intervals.json')['result'],(.075,.15)))
    registration=dict(scenarios=scenarios,inventory=inventory,development_configuration=s['configuration'],
        development_initial_state=updates[0]['measured_initial_state'],development_update_timing_s=[o['update_wall_s'] for o in updates],
        input_semantics=dict(source='backends.py: interval-start mj_forward then -actuator_force before mj_step',
            actual_input='Direct applied tendon force available before advance, not sampled future average',
            preview_input='Clipped commanded direct force held for .01 s; same ideal mapping, reduced dynamics approximate full-order backend'),
        source_files=s['files'])
    atomic_json(path,registration);return registration


def research(phase,packet):
    result_path=RUN/(phase+'_response.json')
    if result_path.exists():return read(result_path)
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
    h=host('research')
    with h.store.transaction() as db:
        state=h.store.session(h.run_id,db)['state'];state.setdefault('fact_scope',dict(project='m5-preparation-20261005',binding=read(RUN/'freeze.json')['source_binding']));state.setdefault('fact_catalog',{})
        h.store.update_state(db,h.run_id,state)
    instructions=('Select TWO exact holding weights within [.0001,1], terminal .05 fixed. Inspect the supplied compact inventory and choose a justified pair; new scenario/recipe combinations may use previously tested weights. Do not run them to select favorable results. Exact future outcomes are unobserved. '
        if phase=='selection' else 'Interpret the compact measured development results and the frozen future protocol. Keep selected weights unchanged. Distinguish implementation/registration, numerical reference stability, physical accuracy, preview discrimination, cost and execution readiness. Do not infer safety or usefulness from differing forecasts or cheaper cost. ')
    instructions+='Return exactly one research.milestone5_preparation tool call with phase='+phase+', two holding_weights, rationale, readiness, limitations, next_action=finish_stop. M2-4 closed, M5 open; incumbent unchanged. No backend execution, promotion or comparison of model orchestration. About 400 words.'
    configure_role(h,'design',instructions,phase=phase,delivery_tool=RESEARCH.extension_id,
        native_store_root=str(RUN),memory_identity=h.run_id,native_fixed={},binding=read(RUN/'freeze.json')['source_binding'],
        decision_packet=packet,decision_packet_reference=save(h.store,packet),phase_budget=dict(limit=dict(model_calls=4,tool_calls=10,wall_s=600.)))
    payload=payload_for(h,EvidenceDrivenAdapter());atomic_json(RUN/(phase+'_serialized_handoff.json'),payload)
    ref=run_until_handoff(h,'m5_'+phase);result=h.store.artifact(ref);atomic_json(result_path,result);return result


def completed_calculation(name,protocol):
    """Admit saved work only after checking its original request and receipt."""
    h=host(name);prior=h.store.lookup(h.run_id,'calculate-'+name)
    if prior is None:return None
    if not prior['receipt']:raise ValueError('UNRESOLVED_CALCULATION_NO_REPLAY')
    receipt=json.loads(prior['receipt'])
    if receipt['execution_status']!='completed':raise ValueError('CALCULATION_FAILED_NO_REPLAY')
    requests=[e for e in h.store.events(h.run_id) if e['request_id']=='calculate-'+name and e['status']=='reserved']
    if len(requests)!=1:raise ValueError('SAVED_CALCULATION_REQUEST_BINDING')
    request=h.store.artifact(requests[0]['inputs'][0]);saved=h.store.artifact(request['arguments']['protocol'])
    if saved!=protocol:raise ValueError('SAVED_CALCULATION_PROTOCOL_MISMATCH')
    path=RUN/(name+'_receipt.json')
    if path.exists() and read(path)!=receipt:raise ValueError('SAVED_CALCULATION_RECEIPT_MISMATCH')
    return h.store.artifact(receipt['output'])['detail']


def recovery_admission(registration,completed,remaining,work):
    outstanding=[n for n in ('history075','history15') if n not in completed]
    solves=len(outstanding)*len(grid(registration['development_configuration']))
    required=len(outstanding)*1200.+660.
    return dict(completed=sorted(completed),outstanding=outstanding,required_solves=solves,
        preview_reserve_each_s=1200.,finalization_reserve_s=660.,required_wall_s=required,
        available=remaining,solve_ceiling=work['limits']['local_solves'],
        passed=work['used']['local_solves']+solves<=work['limits']['local_solves'] and required<=remaining['wall_s'])


def calculate(name,protocol):
    h=host(name);path=RUN/(name+'_receipt.json');prior=h.store.lookup(h.run_id,'calculate-'+name)
    receipt=read(path) if path.exists() else json.loads(prior['receipt']) if prior and prior['receipt'] else None
    if prior and not receipt:raise ValueError('UNRESOLVED_CALCULATION_NO_REPLAY')
    if receipt is None:
        h.resume();receipt=h.invoke(dict(request_id='calculate-'+name,tool_id=DEFINITION.extension_id,tool_version=DEFINITION.version,
            arguments=dict(protocol=save(h.store,protocol)),reason='Authorized M5 development only; no backend advancement',cache='new'))
        atomic_json(path,receipt)
    if receipt['execution_status']!='completed':raise ValueError('CALCULATION_FAILED_NO_REPLAY: '+str(receipt.get('error')))
    result=h.store.artifact(receipt['output'])['detail'];atomic_json(RUN/(name+'.json'),result);return result


def reservations():
    base=batch_requirement(2,planning=dict(model_calls=0,tool_calls=0,wall_s=0.),preparation_reserve_s=5.)
    requirement=deepcopy(base['requirement']);requirement['wall_s']+=3000+180+60
    requirement['tool_calls']+=4 # two previews, pair assessment and export
    return dict(public_base=base,complete_requirement=requirement,extra=dict(candidate_previews=2,embedded_preview_solves=70,
        preview_reserve_s=3000.,local_checkpoints=4,local_integration_reserve_s=180.,export_reserve_s=60.),
        backend_embedded_updates=70,all_controller_attempt_ceiling=140,
        provider_sequence=dict(planning_requests=0,interpretation_requests=1,correction_or_length_recovery_slots=3,ceiling=4,
            explanation='Recipes/protocol planned in completed development; future batch uses frozen plan. Public interpretation protects four slots, not four nominal requests plus another planning request.'),
        per_batch_wall_ceiling_s=6000.,corrections_total=3,corrections_consecutive=2,
        grouping='Each batch reserves its own interpretation: backend/preparation floors total 5180 s for four evaluations, versus 4580 s with one shared interpretation.')


def protocol(registration,selection,reference_result,*,research_store=None,decision_refs=None,supersedes=None):
    recipes=[]
    for i,weight in enumerate(selection['holding_weights']):
        cfg=deepcopy(registration['development_configuration']);cfg['policy']['controller']['parameters']['data']['recipe']['holding_tip_speed_weight']=weight
        recipes.append(dict(recipe_id='future_recipe_'+str(i+1),holding_weight=weight,terminal_weight=.05,configuration=cfg,
            selection_rationale=selection['rationale'],novelty='Scenario/recipe combinations untested; weight itself may be historical.'))
    from extensions.tendon_family.milestone5_protocol import RULES
    ready_reference=reference_result['result']['numerical_reference_established']
    p=dict(version='milestone5_two_capabilities@2.0.0',predecessor_protocol='evidence/milestone5_diagnostic_20261005/next_validation_protocol.json',
        status='prepared_not_executed_future_authorization_required',scenarios=registration['scenarios'],recipes=recipes,
        controller='controller.gvs_nmpc@7.0.0',model='model.gvs@1.0.0',preview_version=PREVIEW_VERSION,local_version=LOCAL_VERSION,
        local_step_s=.000125,local_reference_stable=ready_reference,numerical_reference_results=reference_result,rules=RULES,
        local_intervals_s=[[.20,.21],[.30,.31]],task_interval_s=[0.,.35],holding_interval_s=[.30,.35],
        batches=[dict(batch=1,scenario_id=registration['scenarios'][0]['scenario_id'],recipes=[r['recipe_id'] for r in recipes],complete_backend_evaluations=2),
            dict(batch=2,scenario_id=registration['scenarios'][1]['scenario_id'],recipes=[r['recipe_id'] for r in recipes],complete_backend_evaluations=2)],
        sealing_order=['Prepare both configurations','Generate both independent complete candidate previews','Seal both forecasts plus pair decision in one immutable store artifact/event','Only then start either complete evaluation','At .20/.30 observe state and available clipped direct input; seal local prediction; then backend advances','Both complete evaluations, including hypothetically rejected candidate','Assess both capabilities separately','Interpret/export/stop'],
        local_causality='Constant clipped command available pre-step in ideal_tension mode; no subsequent measured input permitted. Later measured-input replay is retrospective and separate.',
        continuation='Batch1 completes both candidates even on screening rejection or false-safe result. Batch2 unchanged method/recipes; stop for implementation defect, invalid alignment, resource shortfall, incomplete execution, or any false-safe constraint prediction in Batch1. A method change reclassifies Batch1 as development for the changed version.',
        reservations=dict(batch1=reservations(),batch2=reservations()),actual_backend_savings=0,
        limits='Two scenarios/two recipes do not establish family-wide generalization, statistical safety bounds, real-time capability or M5 closure.',
        authorization_in_current_stage=dict(backend_evaluations=0,backend_steps=0,future_forecasts=0))
    return finalize_protocol(p,research_store=research_store,decision_refs=decision_refs,supersedes=supersedes)


def finalize_protocol(p,*,research_store=None,decision_refs=None,supersedes=None):
    """One finalization path for normal, blocked and linked recovered protocols."""
    p=deepcopy(p);accepted={}
    for phase,ref in (decision_refs or {}).items():
        if research_store is None:raise ValueError('ACCEPTED_RESEARCH_STORE_REQUIRED')
        with research_store.connect(True) as db:
            receipts=[json.loads(r[0]) for r in db.execute("SELECT receipt FROM calls WHERE receipt IS NOT NULL AND status='completed'")]
        if not any(r['execution_status']=='completed' and r['tool_id']==RESEARCH.extension_id and research_store.artifact(r['output']).get('reference')==ref for r in receipts):
            raise ValueError('ACCEPTED_RESEARCH_RECEIPT_REQUIRED')
        decision=research_store.artifact(ref)
        if decision['phase']!=phase or decision['holding_weights']!=[r['holding_weight'] for r in p['recipes']]:
            raise ValueError('RESEARCH_DECISION_BINDING_MISMATCH')
        accepted[phase]=ref
    p['research_decisions']=accepted
    p['research_pair_selected']='selection' in accepted
    p['research_interpretation_complete']='interpretation' in accepted
    p['ready_for_bounded_prospective_experiment']=False
    p['numerical_results_provenance']='evidence/milestone5_preparation_20261005/reference.json and original completed receipts; reused without charge'
    p['supersedes']=supersedes
    p['reservations']['development']=dict(ceiling=LIMITS,numerical_ceiling=NUMERICAL,preview_grid_updates=35,
        admission='development_admission.json',protected_finalization_s=660.,actual_accounting='accounting.json')
    p['commands']=dict(readiness="& 'C:\\Users\\gugugaga\\miniconda3\\envs\\softagent\\python.exe' examples/milestone5_future_validation.py --check",
        batch1="& 'C:\\Users\\gugugaga\\miniconda3\\envs\\softagent\\python.exe' examples/milestone5_future_validation.py --batch 1 --execute --grant evidence/milestone5_preparation_20261005/future_batch1_grant.json",
        batch2="& 'C:\\Users\\gugugaga\\miniconda3\\envs\\softagent\\python.exe' examples/milestone5_future_validation.py --batch 2 --execute --grant evidence/milestone5_preparation_20261005/future_batch2_grant.json",
        prerequisite='The grant files do not exist and must be created under separate future execution authorization. The current blocked protocol fails readiness before forecasts/backend work.')
    p['capabilities']=dict(local=dict(start='Currently observed state and information available at checkpoint',scope='Declared next .01 s interval',
        reports=['world velocity vector','speed magnitude','direction including neutral/indeterminate','numerical resolution difference','position and speed threshold-crossing errors'],
        supported_role='Directional diagnosis under test; quantitative accuracy and constraint reliability remain unmet'),
        screening=dict(start='Before either candidate backend execution',scope='Own predicted state/input/plan history over complete .0-.35 s task',
        reports=['resolved coverage','conditional accuracy','pairwise ordering error','false rejection','false-safe','abstention','cost'],
        supported_role='Implemented testable forecasts; no useful screening established'),
        orchestration='Both single-model and dual-model orchestration use the same tools, registration, seals and budgets. No orchestration comparison ran.')
    p['reservation_semantics']='Local checkpoint work is nested in simulation receipts, with separate telemetry. The 180 s allocation protects incremental overhead; actual nested wall time is charged once. Public per-simulation 900 s timeout remains unchanged.'
    from tools.platform_registry import dependency_identity
    p['implementation_identity']=dict(files={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in (
        'extensions/tendon_family/milestone5_preparation.py','extensions/tendon_family/milestone5_protocol.py','examples/milestone5_future_validation.py')},
        controller=dependency_identity(reg().get('controller.gvs_nmpc','7.0.0')),
        model=dependency_identity(reg().get('model.gvs','1.0.0')))
    return p


def develop():
    frozen=prepare();check_previous(frozen);registration=register(frozen)
    selection=research('selection',dict(authorization=AUTHORIZATION,
        scenarios=[{k:v for k,v in s.items() if k not in ('configuration','full_restorable_new_episode_state','projection')} for s in registration['scenarios']],
        inventory=registration['inventory'],baseline=dict(holding=.05,terminal=.05,structure='near/far .16/.11, scale .95, compliant'),
        development_only_weights=[.075,.15],future_candidate_execution_prohibited=True))
    saved=read(predecessor.RUN/'intervals.json')['result']
    reference_protocol=dict(operation='reference',intervals=saved)
    reference_result=completed_calculation('reference',reference_protocol)
    if reference_result is None:reference_result=calculate('reference',reference_protocol)
    p=protocol(registration,selection,reference_result);atomic_json(RUN/'protocol.json',p)
    store=Store(RUN);completed=[];protocols={}
    for name,weight in [('history075',.075),('history15',.15)]:
        cfg=deepcopy(registration['development_configuration']);cfg['policy']['controller']['parameters']['data']['recipe']['holding_tip_speed_weight']=weight
        protocols[name]=dict(operation='history',configuration=cfg,initial_state=registration['development_initial_state'],allowance_s=1200.)
        if completed_calculation(name,protocols[name]) is not None:completed.append(name)
    with store.connect(True) as db:work=json.loads(db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone()[0])
    admission=recovery_admission(registration,completed,store.remaining()['remaining'],work)
    atomic_json(RUN/'development_admission.json',admission)
    if not admission['passed']:raise ValueError('COMPLETE_PREVIEW_BUDGET_ADMISSION_FAILED')
    for name,weight in [('history075',.075),('history15',.15)]:
        if name in completed:continue
        with store.connect(True) as db:work=json.loads(db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone()[0])
        remaining=store.remaining()['remaining']
        if work['used']['local_solves']+len(grid(registration['development_configuration']))>80 or remaining['wall_s']<1860.:
            raise ValueError('COMPLETE_PREVIEW_RESERVE_SHORTFALL')
        calculate(name,protocols[name])
    preview_summary=summarize_previews()
    research('interpretation',dict(authorization=AUTHORIZATION,selected_weights=selection['holding_weights'],reference=reference_result,
        previews=preview_summary,protocol={k:v for k,v in p.items() if k not in ('scenarios','recipes')},
        incumbent=frozen['incumbent'],remaining=store.remaining()['remaining']))
    refs=store.session(host('research').run_id)['state']['handoffs']
    atomic_json(RUN/'protocol.json',protocol(registration,selection,reference_result,research_store=store,
        decision_refs={phase:refs['m5_'+phase] for phase in ('selection','interpretation')}))
    export(frozen)


def summarize_previews():
    from extensions.tendon_family.milestone5_protocol import pair_decision
    histories=[read(RUN/(name+'.json'))['result'] for name in ('history075','history15')]
    ordering=pair_decision([dict(candidate_id=name,**h) for name,h in zip(('history075','history15'),histories)])
    preview_summary=dict(predicted=ordering,metrics=[h['metrics'] for h in histories],cost_s=sum(h['complete_cost_s'] for h in histories),
        independent_histories=True,first_commands=[h['rows'][0]['input_n'] for h in histories],
        iteration_zero_counts=[sum(r['selected_iteration']==0 for r in h['rows']) for h in histories],
        first_command_difference_update=next((i for i,(a,b) in enumerate(zip(histories[0]['rows'],histories[1]['rows'])) if max(abs(x-y) for x,y in zip(a['input_n'],b['input_n']))>1e-9),None),
        historical_observed_order=['history15','history075'],
        historical_max_speeds_m_s=[.023285947509969908,.012939],
        ordering_verdict='unresolved' if ordering['order'] is None else 'correct' if ordering['order']==['history15','history075'] else 'incorrect',
        qualification='Retrospective original-initializer comparison only. Future saved-checkpoint episodes are not calculated here.')
    # Replace compact approximate speed with exact artifact maximum.
    intervals=read(predecessor.RUN/'intervals.json')['result'];old=predecessor.restore();dp=old.store.artifact(old.freeze['diagnostic_protocol'])
    from extensions.tendon_family.diagnostic_evidence import measured_motion
    preview_summary['historical_max_speeds_m_s']=[max(m['speed_m_s'] for m in measured_motion(BoundReader(old.store,b),BoundReader(old.store,b).resolve(BoundReader(old.store,b).binding['execution_id'])) if m['time_s']>=.3-1e-9) for b in dp['bindings']]
    from extensions.tendon_family.milestone5_protocol import assess_screening
    preview_summary['retrospective_screening_assessment']=assess_screening(ordering,
        [dict(candidate_id=name,holding_max_speed_m_s=speed,joint_acceptance=speed<=.02) for name,speed in zip(('history075','history15'),preview_summary['historical_max_speeds_m_s'])],
        preview_summary['cost_s'],605.936999999918)
    atomic_json(RUN/'preview_summary.json',preview_summary)
    return preview_summary


def finalize_local():
    """Complete unaffected work after a preserved external handoff rejection."""
    frozen=read(RUN/'freeze.json');check_previous(frozen);registration=read(RUN/'registration.json')
    if any('facts' in row for row in registration['inventory']):
        # Repair the already captured inventory through its exact configuration refs; no rediscovery.
        atomic_json(RUN/'inventory_before_compaction.json',registration['inventory']);old=validation.restore()
        registration['inventory']=[inventory_record(old.store,row['facts']) if 'facts' in row else row for row in registration['inventory']]
        atomic_json(RUN/'registration.json',registration)
        atomic_json(RUN/'inventory_correction.json',dict(reason='Weights reside in referenced effective configurations, not result facts. Extract exact saved configuration references and compact displayed metrics.',
            source_rediscovery=False,provider_attempts=0,numerical_attempts=0,original_attempt_payload_preserved=True))
    summary=summarize_previews()
    selection=dict(holding_weights=[.075,.15],
        rationale='Concrete provisional pair inherited from the predecessor research-model selection. Same historical weights provide a planned matched scenario comparison from two reset saved checkpoints, not new numerical weights. New-stage model selection and interpretation are blocked; this engineering registration does not replace them.')
    p=protocol(registration,selection,read(RUN/'reference.json'))
    p.update(research_pair_selected=False,status='registered_not_ready_external_research_handoff_blocked',
        unresolved_prerequisite='Configured research model must select/justify this new scenario pair and interpret readiness after automatic-review approval. No future execution authorization exists.')
    atomic_json(RUN/'protocol.json',p)
    review=dict(classification='Engineering assessment only; no substituted research-model response',
        selected_weights=selection['holding_weights'],pair_selection='Provisional inherited historical model pair; new-stage selection unresolved',
        implementation='Both numerical interfaces and sealing points implemented',protocol_registration='Concrete states, clocks, recipes, rules and budgets registered',
        numerical_reference='Successive-resolution stability at 1e-4 m/s on both development intervals only; not a proven error bound',
        backend_accuracy='Unmet. Finest scalar errors about -.00448445/-.00398404 m/s; .075 remains false-safe; .15 vector error worsens.',
        preview_summary=summary,readiness='Not ready for prospective execution: required new-stage research selection/interpretation blocked; screening usefulness unvalidated',
        operational_next_action='finish_stop',future_executed=False)
    atomic_json(RUN/'final_local_review.json',review)
    atomic_json(RUN/'platform_rejection.json',dict(action='Escalated existing development runner with DeepSeek payload transmission',process_started=False,
        automatic_approval_rejected=True,provider_attempt_charged=False,
        stated_reason='The command transmits project evidence to an external DeepSeek endpoint, but trusted user content does not authorize that specific payload and destination.',
        no_bypass=True,approval_question_pending=True,offline_work_completed=True))
    from examples.milestone5_future_validation import readiness
    atomic_json(RUN/'readiness.json',readiness(p))
    atomic_json(RUN/'verification.json',dict(focused_tests=6,passed=True,
        command='softagent Python -m unittest tests.test_milestone5_preparation',
        checks=['Independent candidate state/input/warm histories','Task clock and horizon alignment','Causal current command only',
            'Both forecasts required; configuration binding; immutable seal before backend reservation','Local seal before advance',
            'Abstention and false-safe scoring','Real Store schema compatibility','Completed receipt reuse without numerical replay'],
        static_readiness='readiness.json',backend_evaluations=0,backend_steps=0,prospective_numerical_forecasts=0,
        test_environment_intervention='Sandbox denied temporary SQLite fixture access. Focused local tests passed under normal filesystem permissions; no network or backend work.',
        production_default_files_unchanged=['gvs_nmpc.py','gvs_trajectory.py','control_evidence.py','diagnostic_math.py','extensions/optimization/ipopt.py','tools/batch_budget.py']))
    store=Store(RUN)
    with store.transaction() as db:
        ref=store.put(db,p);store.event(db,host('research').run_id,'prepared_protocol','sealed_not_executed',outputs=[ref])
        for row in db.execute('SELECT run_id FROM sessions').fetchall():
            session=store.session(row[0],db)
            if session['status']!='failed':
                state=session['state'];state['development_stage_finished']=True
                store.update_state(db,row[0],state,'stopped')
    atomic_json(RUN/'protocol_seal.json',dict(protocol_reference=plain(ref),protocol_identity=digest(p),classification='Registered preparation only; not a prospective forecast seal',
        future_forecasts_generated=0,future_backend_execution_authorized=False))
    export(frozen)


def export(frozen):
    check_previous(frozen);store=Store(RUN)
    blocked=(RUN/'platform_rejection.json').exists() and not ((RUN/'selection_response.json').exists() and (RUN/'interpretation_response.json').exists())
    with store.connect(True) as db:
        work=json.loads(db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone()[0]);ids=[r[0] for r in db.execute('SELECT run_id FROM sessions')]
        receipts=[json.loads(r[0]) for r in db.execute('SELECT receipt FROM calls WHERE receipt IS NOT NULL')]
    used=store.remaining()['used'];historical=read(predecessor.EVIDENCE/'accounting.json')['cumulative']
    accounting=dict(historical=historical,new_stage=used,cumulative={k:historical[k]+used[k] for k in historical},
        limits=LIMITS,numerical_work=work,occupied=store.remaining().get('occupied',{}),
        nested_time='Controller optimization, warm preparation and preview propagation are included in outer receipt wall time; not added again.',
        offline_engineering='Read/edit/export/test time follows predecessor convention and is not provider/workflow receipt time.')
    charges={k:sum(r['charged'][k] for r in receipts) for k in used}
    assert all(abs(charges[k]-used[k])<1e-7 for k in used),'RECEIPT_ACCOUNTING_MISMATCH'
    accounting['receipt_charge_sum']=charges
    accounting['cumulative_numerical_work']=dict(controller_solves=9+work['used']['local_solves'],standalone_reduced_rollouts=15+work['used']['prediction_evaluations'],
        historical_backend_controller_updates=210,new_backend_controller_updates=0,new_preview_controller_updates=work['used']['local_solves'])
    accounting['corrections']=dict(protocol_new_stage=0,consecutive_new_stage=0,semantic_model_new_stage=0,historical_protocol=7,historical_semantic=8)
    atomic_json(RUN/'accounting.json',accounting);atomic_json(RUN/'receipts.json',receipts)
    events=[e for i in ids for e in store.events(i)];atomic_json(RUN/'events.json',events)
    refs={}
    def collect(value):
        if isinstance(value,dict):
            if set(value)=={'artifact_id','media_type'}:refs[value['artifact_id']]=value
            else:
                for child in value.values():collect(child)
        elif isinstance(value,list):
            for child in value:collect(child)
    collect(events);collect(receipts)
    artifacts=EVIDENCE/'artifacts';artifacts.mkdir(parents=True,exist_ok=True)
    for key,ref in refs.items():(artifacts/(key+('.json' if ref['media_type']=='application/json' else '.bin'))).write_bytes(store.artifact(ref,raw=True))
    for p in RUN.glob('*.json'):(EVIDENCE/p.name).write_bytes(p.read_bytes())
    for name in ('examples/milestone5_preparation.py','examples/milestone5_future_validation.py',
            'extensions/tendon_family/milestone5_preparation.py','extensions/tendon_family/milestone5_protocol.py','tests/test_milestone5_preparation.py'):
        target=EVIDENCE/'implementation'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/name).read_bytes())
    reference_result=read(RUN/'reference.json')['result'];summary=read(RUN/'preview_summary.json');final_protocol=read(RUN/'protocol.json')
    delivery=dict(status='completed_stopped_with_blocked_research_handoff' if blocked else 'completed_stopped',protocol='protocol.json',accounting='accounting.json',
        implementation_complete=True,protocol_registration_complete=True,numerical_reference_established=reference_result['numerical_reference_established'],
        preview_discrimination_established=summary['predicted']['order'] is not None,retrospective_ordering=summary['ordering_verdict'],
        budget_admission=read(RUN/'development_admission.json')['passed'],future_execution_authorized=False,future_executed=False,
        readiness='Not ready: new-stage research pair selection and interpretation blocked by automatic approval review.' if blocked else 'Prepared for a bounded falsification study subject to separate authorization and no-execution checks; screening not validated.',
        milestone2='closed',milestone3='closed',milestone4='closed',milestone5='open',incumbent=frozen['incumbent'],
        no_backend_steps=True,no_subagents=True,pushed=False,operational_next_action='finish_stop',
        scientific_limits=['Local numerical stability is not backend accuracy','Useful prospective screening remains unvalidated','No real-time or family-wide reliability claim'],
        interpretation='final_local_review.json' if blocked else 'interpretation_response.json',
        research_model_selection_complete=(RUN/'selection_response.json').exists(),research_model_interpretation_complete=(RUN/'interpretation_response.json').exists(),
        ready_for_prospective_execution=(not blocked and final_protocol.get('ready_for_bounded_prospective_experiment',False)),
        blockers=['Automatic approval review rejected DeepSeek payload transmission; direct trusted approval required for new-stage research selection and final interpretation.'] if blocked else [])
    atomic_json(EVIDENCE/'delivery.json',delivery)
    atomic_json(EVIDENCE/'sha256_manifest.json',{p.relative_to(EVIDENCE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(EVIDENCE.rglob('*')) if p.is_file() and p.name!='sha256_manifest.json'})
    print(json.dumps(dict(status=delivery['status'],usage=used,numerical=work),indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');parser.add_argument('--develop',action='store_true');parser.add_argument('--export',action='store_true');parser.add_argument('--finalize-local',action='store_true')
    args=parser.parse_args()
    if args.prepare:register(prepare())
    elif args.develop:develop()
    elif args.export:export(read(RUN/'freeze.json'))
    elif args.finalize_local:finalize_local()
    else:parser.error('Choose --prepare, --develop or --export; none starts a backend.')
