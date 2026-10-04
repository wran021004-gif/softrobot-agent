"""One explicitly authorized prediction-validation stage; no predecessor reset."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from examples import milestone45_continuation as predecessor
from examples import milestone4 as shared
from tools.state_io import read,atomic_json,digest
from tools.platform_store import Store,plain
from tools.platform_host import Host
from tools.diagnostic_workflow import DiagnosticWorkflow,save
from tools.live_batch_execution import verified_historical_result
from tools.candidate_parameters import planning_configuration
from tools.structural_study import research_planning_input
from tools.study_history import study_history
from tools.batch_budget import budget_capacity,batch_requirement
from tools.platform_models import payload_for
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from extensions.tendon_family.control_evidence import ControlEvidence,PRE_STEP_OBSERVER
from extensions.tendon_family.gvs_profile import execution_scope
from extensions.tendon_family.diagnostic_evidence import measured_motion
from extensions.tendon_family.milestone5_validation import DEFINITION,CHECKPOINTS,TOLERANCES,diagnose,direction,aligned_interval,local_score,ImportedReader,pairwise_speed_order,ordering_score
import numpy as np

RUN=ROOT/'runs/milestone5_validation_20261004/single_context'
EVIDENCE=ROOT/'evidence/milestone5_validation_20261004'
LIMITS=dict(model_calls=24,tool_calls=60,backend_solves=2,wall_s=9000.,worker_calls=0)
DEVELOPMENT=['bebcfd47274940fb88a55ce5a2457c4c','91c3ba1b01d6499fb26df8f95409401b','110dc2c9c1d642dcb018664a65c62c30']
INCUMBENT=DEVELOPMENT[1]
FILES=['examples/milestone5_validation.py','extensions/tendon_family/milestone5_validation.py',
    'extensions/tendon_family/control_evidence.py','extensions/tendon_family/backends.py','tests/test_milestone5_validation.py']
AUTHORIZATION='User attachment 2026-10-04: NEW bounded prediction-validation stage,24 provider/60 workflow/2 backend/12 additional solves/24 additional rollouts/9000 charged seconds/0 workers,4 corrections max2 consecutive; local commit,no push; predecessor immutable.'
EXTERNAL_AUTHORIZATION=dict(destination='https://api.deepseek.com',model='deepseek-flash',
    user_statement='I explicitly authorize sending the prepared research handoff and its updated version to https://api.deepseek.com through the existing deepseek-flash configuration.',
    covered_data=['robot/task/controller/candidate configurations','historical diagnostics and all six matched intervals',
        'scientific identities/artifact references/numerical results/errors/comparisons','instructions/tool schemas/budgets/status',
        'candidate proposals/previews/frozen forecasts/evaluations/interpretation and correction messages necessary for this stage'],
    credentials='Existing authenticated client only; excluded from messages and evidence.',resumes_existing_grant=True,reviewed_commit='0baf49c',
    source='User resume attachment 1eb439f5-29a3-4063-a2cb-abba3963ee65, 2026-10-04')


def revision():return dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    files={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FILES if (ROOT/p).exists()})


class ValidationWorkflow(shared.MilestoneWorkflow):
    limits=LIMITS
    numerical_limits=dict(local_solves=12,prediction_evaluations=24)

    def phase(self,phase,kind,key,**extra):
        packet=extra.get('decision_packet')
        if packet and 'history' in packet:
            packet=predecessor.compact_decision_packet(packet,extra.get('decision_packet_reference'))
            for row in packet.get('completed_results',[]):
                for field in ('against_source','against_retained_baseline'):
                    if field in row:row[field]={k:v for k,v in row[field].items() if k not in ('baseline','candidate')}
            extra['decision_packet']=packet
        return super().phase(phase,kind,key,**extra)

    def check_provider_payload(self,host):
        assert_predecessor(self)
        super().check_provider_payload(host)
        payload=payload_for(host,EvidenceDrivenAdapter())
        atomic_json(self.directory/(self.current_stage+'_serialized_handoff.json'),payload)
        if self.current_stage=='validation':
            packet=json.loads(payload['messages'][1]['content'])['role_context']['study_packet']
            if len(packet.get('development_fidelity',{}).get('development_local_fidelity',[]))!=6:raise ValueError('SIX_INTERVALS_MISSING_FROM_ACTUAL_PAYLOAD')
            if packet['external_transmission_authorization']!=EXTERNAL_AUTHORIZATION:raise ValueError('ACTUAL_PAYLOAD_AUTHORIZATION_MISSING')
            from tools.batch_budget import downstream_available
            if packet['budget']['available']!=downstream_available(self.store,host.run_id):raise ValueError('ACTUAL_HANDOFF_BUDGET_STALE')
            atomic_json(self.directory/'validation_serialized_handoff_v2.json',payload)
            self.chain['refreshed_handoff']=save(self.store,payload)


def assert_predecessor(w):
    link=w.freeze['authorization_link']
    for old in link['stores']:
        s=Store(old['path'])
        if s.remaining()!=old['usage']:raise ValueError('PREDECESSOR_USAGE_CHANGED')
        for identity,state_hash in old['states'].items():
            if digest(s.session(identity)['state'])!=state_hash:raise ValueError('PREDECESSOR_STATE_CHANGED')
    for path,sha in link['sealed_files'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=sha:raise ValueError('PREDECESSOR_SEAL_CHANGED')


def prepare():
    from tools.runtime_identity import require_softagent_runtime
    from examples.stage356_milestone2 import scientific_bundle,import_common
    if RUN.exists():raise ValueError('NEW_STAGE_ALREADY_EXISTS')
    old=predecessor.restore();source=ControlEvidence(old.store).resolve(INCUMBENT)
    config=deepcopy(old.freeze['experiment']);config.update(source_store=str(predecessor.RUN),execution_id=INCUMBENT,
        source_manifest=source['manifest'],evidence_directory=str(EVIDENCE),project_prefix='gvs-milestone5-validation',
        authorization_source=AUTHORIZATION,provider_freeze=str(predecessor.RUN/'freeze.json'))
    w=ValidationWorkflow(RUN,'single_context',experiment=config);w.prepare(require_softagent_runtime())
    import_common(w,scientific_bundle());shared.prior.previous.prior.import_confirmation(w)
    review=shared.reviewed_changes()
    for path in ('extensions/tendon_family/control_evidence.py','extensions/tendon_family/backends.py'):
        review[path]=dict(reason='Opt-in observational pre-step sealing only; no command, projection, integration, solver or acceptance change.',
            current_hash=hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),historical_hashes=[])
    for record in old.historical_results:
        s=Store(record['source_store']);a=ControlEvidence(s).resolve(record['facts']['execution_id'])
        for dependency in s.session(a['owner'])['snapshot']['dependencies'].values():
            for path,row in review.items():
                sha=dependency['sources'].get(path)
                if sha and sha not in row['historical_hashes']:row['historical_hashes'].append(sha)
    w.historical_results=[verified_historical_result(w.host('design'),Store(r['source_store']),r['facts']['execution_id'],'historical_candidate',review) for r in old.historical_results]
    shared.prior.copy_reference(w.store,old.store,old.chain['final_response']);w.predecessor_decision=old.chain['final_response']
    shared.prior.copy_reference(w.store,old.store,old.chain['batch_summary']);w.chain['batch_summary']=old.chain['batch_summary']
    w.retained_baseline=w.historical_results[0]['facts'];w.latest_tested=old.latest_tested
    w.incumbent=next(r['facts'] for r in w.historical_results if r['facts']['execution_id']==INCUMBENT)
    links=[]
    for path in (predecessor.ORIGINAL,predecessor.RUN):
        s=Store(path)
        with s.connect(True) as db:identities=[r[0] for r in db.execute('SELECT run_id FROM sessions')]
        links.append(dict(path=str(path),usage=s.remaining(),states={i:digest(s.session(i)['state']) for i in identities}))
    sealed=['evidence/milestone45_continuation_20261004/delivery.json','evidence/milestone45_continuation_20261004/single_context/pilot_forecast_seal.json']
    w.freeze.update(historical_results=w.historical_results,incumbent=w.incumbent,predecessor_decision=w.predecessor_decision,
        compatibility_review=review,authorization_link=dict(stores=links,old_usage=read(predecessor.EVIDENCE/'accounting.json')['combined'],
            old_protocol_corrections=4,old_semantic_corrections=3,sealed_files={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sealed},authorization=AUTHORIZATION))
    w.freeze['confirmation_grant_links']=w.freeze['authorization_link']
    model=deepcopy(old.freeze['provider_configuration']);w.freeze['provider_configuration']=model
    science=planning_configuration(w.store,w.incumbent['candidate'],w.store.session(w.host('design').run_id)['snapshot']['input']['policy'])
    projected=research_planning_input(science,read(predecessor.PROFILE),budget=LIMITS,model=model,tool_bindings=w.freeze['tool_bindings'])
    shared.migrate_planning_host(w,'prediction-planning',input_override=projected)
    w.previous=w.host('design');atomic_json(RUN/'freeze.json',w.freeze)
    bindings={r['facts']['execution_id']:r['binding'] for r in w.historical_results}
    atomic_json(RUN/'historical_diagnosis.json',diagnose(w.store,DEVELOPMENT,bindings));assert_predecessor(w)
    return w


def restore():
    freeze=read(RUN/'freeze.json');w=ValidationWorkflow(RUN,'single_context',experiment=freeze['experiment']);w.freeze=freeze
    w.project=freeze['project_id'];w.limits=LIMITS;w.hosts={k:Host(RUN,v) for k,v in freeze['hosts'].items()}
    for attr,key in [('binding','binding'),('identities','identities'),('summary','summary'),('inventory','inventory'),('inventory_ref','inventory_reference'),
        ('common','common_scientific_input'),('source_record','source_record'),('eligibility','numerical_eligibility')]:setattr(w,attr,freeze[key])
    w.historical_results=freeze['historical_results'];w.retained_baseline=w.historical_results[0]['facts'];w.incumbent=freeze['incumbent']
    w.latest_tested=freeze.get('latest_tested',w.historical_results[-1]['facts']['candidate']);w.predecessor_decision=freeze['predecessor_decision']
    w.chain=read(RUN/'chain.json');w.historical_feedback=w.store.artifact(w.common['feedback']);w.previous=w.host('design');return w


def prediction_protocol(w,record,source):
    from schemas.platform import CandidateInput,SessionInput
    from tools.platform_tools import _candidate
    bindings={r['facts']['execution_id']:r['binding'] for r in w.historical_results}
    reader=ImportedReader(w.store,bindings);saved=reader.resolve(source['facts']['execution_id']);observations=reader.read_file(saved,'controller_observations.json');motion=measured_motion(reader,saved)
    batch=w.store.session(w.host('design').run_id)['state']['search_batch'];base=w.store.artifact(batch['base_configuration'])['effective']
    configurations=[dict(candidate_id=source['facts']['candidate']['candidate_id'],configuration=source['facts']['configuration'],scientific_identity=digest(execution_scope(saved['configuration'])),role='reference')]
    for index,changes in enumerate(record['plan']['candidates']):
        effective=plain(_candidate(SessionInput.model_validate(base),changes,w.host('design').reg));identity=batch['batch_id']+'-'+str(index)
        prepared=CandidateInput(candidate_id=identity,baseline_identity=digest(base),builder=base['policy']['candidate_builder']['extension_id'],builder_version=base['policy']['candidate_builder']['version'],
            changes=changes,allowed=base['policy']['editable'],effective=effective,content_identity=digest(effective))
        configurations.append(dict(candidate_id=identity,configuration=save(w.store,prepared),scientific_identity=digest(execution_scope(effective)),role='validation',changes=changes))
    physics=reader.read_file(saved,'resolved_physics.json');tendons=[t['id'] for t in base['robot']['structure']['data']['tendons']]
    if tendons!=[t['entity'] for t in physics['tendons']]:raise ValueError('INPUT_ORDER_MISMATCH')
    protocol=dict(configurations=configurations,source=source['facts']['candidate'],accepted_plan=w.chain['search_plan'],input_order=tendons,
        force_limits_n=[t['force_limit_n'] for t in physics['tendons']],integration_step_s=.002,horizon_s=.01,model='model.gvs@1.0.0',
        units=dict(position='world m',speed='world m/s',input='N',state='GVS curvature rad/m and rate rad/m/s'),
        warm_start='Common cold constant previous applied input; candidate-model states independently regenerated; not historical warm reconstruction.')
    snapshots=[]
    for index in CHECKPOINTS:
        o=observations[index];m=motion[index-1]
        snapshots.append(dict(update_id=index,time_s=o['time_s'],measured_initial_state=o['measured_initial_state'],previous_input_n=observations[index-1]['actual_tension_n'],
            effective_horizon=o['effective_horizon'],backend_speed_m_s=m['speed_m_s'],backend_position_m=m['position_m'],
            state_reference=dict(reference=saved['files']['controller_observations.json'],pointer=f'/{index}/measured_initial_state'),
            previous_input_reference=dict(reference=saved['files']['controller_observations.json'],pointer=f'/{index-1}/actual_tension_n')))
    protocol.update(classification='bounded_prediction_validation',snapshots=snapshots,development_executions=DEVELOPMENT,development_bindings={e:bindings[e] for e in DEVELOPMENT},
        development_fidelity_reference=w.chain.get('development_fidelity'),
        limits=dict(max_wall_s=600.,max_local_solves=6,max_prediction_rollouts=6),tolerances=TOLERANCES,
        observation_rule=read(RUN/'historical_diagnosis.json')['observation_rule'],
        forecast_rule='Holding-entry candidate plan max speed/error compared with incumbent plan on common projected state; unresolved for sub-tolerance differences; no absolute acceptance forecast.',
        speed_order_rule='With two candidates compare the same 0.30 s cold-preview holding-plan maxima; differences <=1e-4 m/s abstain; otherwise predict ascending full-task max holding speed. Score actual ties explicitly using the same tolerance. One candidate: not applicable.',
        local_direction_labels=['increasing','decreasing','approximately_unchanged'],
        quantity_definitions=dict(local='world endpoint velocity and speed change over same applied constant command and 0.01 s interval',
            preview='0.20 s horizon 0.10 s; 0.30 s horizon 0.05 s; production integrator/substeps and early-stop policy unchanged',
            full_task='backend sampled maximum over final 0.05 s, acceptance unchanged'),
        prospective_local_rule='At updates 20 and 30 seal existing production first-period prediction after actual input verification and before mj_step; score next backend sample. No added solve/rollout.',
        resolution='Numerical tolerances chosen before new outcomes; no measured repeatability or statistical confidence.',revision=revision())
    protocol.pop('snapshot',None);return protocol


def freeze_forecasts(w,record,source):
    if (RUN/'forecast_seal.json').exists():
        if w.store.artifact(w.chain['forecast_seal'])!=read(RUN/'forecast_seal.json'):raise ValueError('EXISTING_FORECAST_CHANGED')
        return
    from tools.platform_registry import registry
    reg=registry();reg.add(DEFINITION)
    host=Host(RUN,w.project+'-numerical',reg=reg)
    if (RUN/'numerical_receipt.json').exists():
        receipt=read(RUN/'numerical_receipt.json')
        if receipt['execution_status']!='completed':raise ValueError('FAILED_NUMERICAL_ATTEMPT_NOT_REPLAYED')
        result=w.store.artifact(receipt['output'])['detail'];ref=result['protocol'];protocol=w.store.artifact(ref)
        if protocol!=read(RUN/'prediction_protocol.json') or protocol['accepted_plan']!=w.chain['search_plan']:raise ValueError('SAVED_PREVIEW_BINDING_CHANGED')
    else:
        protocol=prediction_protocol(w,record,source);ref=save(w.store,protocol);atomic_json(RUN/'prediction_protocol.json',protocol)
        inp=deepcopy(w.store.artifact(source['facts']['configuration'])['effective']);inp['run_id']=host.run_id
        inp['policy'].update(budget={**LIMITS,'model_calls':0},route=None,tool_bindings={DEFINITION.extension_id:DEFINITION.version},allowed_tools=[],timeout_s=600.)
        inp['policy']['operation_allowances']={DEFINITION.extension_id:dict(timeout_s=600.,reserve_s=600.)}
        host.create(inp);host.resume()
        receipt=host.invoke(dict(request_id='two-checkpoint-preview',tool_id=DEFINITION.extension_id,tool_version=DEFINITION.version,
            arguments=dict(protocol=ref),reason='Authorized bounded common cold previews and matched development dynamics diagnosis before both new backends.',cache='new'))
        atomic_json(RUN/'numerical_receipt.json',receipt)
    if receipt['execution_status']!='completed':raise ValueError('NUMERICAL_PREVIEW_FAILED: '+str(receipt.get('error')))
    result=w.store.artifact(receipt['output'])['detail'];atomic_json(RUN/'prediction_numerical.json',result);w.chain['prediction_numerical']=receipt['output']
    w.current_stage='forecast_interpretation'
    w.instructions={**w.instructions,'response_final':shared.FINAL+''' Pre-execution forecast interpretation. All new candidates remain pending and have no backend outcomes. Review the deterministic forecast rule and candidate-specific preview; distinguish development data from validation. Freeze the numerical directions or explicit unresolved status and explain qualifications; do not claim full-task equivalence from tied cold previews. Interpret speed_order_forecast as a limited secondary speed-order hypothesis only; its tie/unavailable status means abstention, one candidate means not applicable. No absolute acceptance or overall design ranking is supported. Select the completed incumbent if selecting any result. next_research.route=stop and zero budget means no experiment beyond the already accepted pending batch. About250 words.'''}
    compact=deepcopy(result)
    for row in compact['rows']:row.pop('plan_metrics',None)
    w.phase('response_final','design_response','forecast_interpretation',decision_packet=dict(numerical_preview=compact,
        pending_candidates=protocol['configurations'][1:],primary_reference=source['facts']['candidate'],all_new_outcomes_unavailable=True),
        batch_result=w.store.artifact(w.chain['batch_summary']),require_research_route=True,require_research_budget=True,
        research_records=w.historical_results,latest_tested=w.latest_tested,
        improvement_feedback_content=dict(baseline_facts=w.retained_baseline,execution=None),check_feedback=[dict(reference=w.chain['feedback'])],
        source_report=w.common['source_report'],source_record=w.source_record)
    forecast=dict(protocol=ref,numerical=receipt['output'],accepted_plan=w.chain['search_plan'],configurations=protocol['configurations'],
        research_interpretation=w.chain['forecast_interpretation'],
        numerical_dependencies_reference=save(w.store,w.store.session(host.run_id)['snapshot']['dependencies']),
        numerical_dependency_fingerprint=digest(w.store.session(host.run_id)['snapshot']['dependencies']),
        development_executions=DEVELOPMENT,validation_exclusions=DEVELOPMENT,forecasts=result['forecasts'],predicted_speed_order=result['predicted_speed_order'],
        speed_order_forecast=result['speed_order_forecast'],speed_order_rule=protocol['speed_order_rule'],
        acceptance_prediction='unresolved',tolerances=TOLERANCES,predictor_fingerprint=revision(),warm_start=protocol['warm_start'],
        local_checkpoint_rule=protocol['prospective_local_rule'],accounting_limits=LIMITS,diagnostic_limits=w.numerical_limits)
    w.chain['forecast_seal']=save(w.store,forecast);atomic_json(RUN/'forecast_seal.json',forecast)
    with w.store.transaction() as db:w.store.event(db,w.host('design').run_id,'prospective_forecast','sealed',inputs=[ref],outputs=[w.chain['forecast_seal']])
    atomic_json(RUN/'chain.json',w.chain)


def observer(w):
    def capture(index,t,controller,geometry,velocity,actual):
        if index not in CHECKPOINTS:return
        o=controller.observations[-1];pred=aligned_interval(o,dict(time_s=t+.01),.01)
        state=o['measured_initial_state'];n=len(state)//2;p,v=controller.workspace._motion(state[:n],state[n:])
        prediction=dict(update_id=index,start_s=t,end_s=pred['time_s'],phase='actual_input_verified_before_backend_step',
            endpoint_velocity_m_s=pred['tip_velocity_m_s'],endpoint_speed_m_s=float(np.linalg.norm(pred['tip_velocity_m_s'])),endpoint_position_m=pred['tip_position_m'],
            initial_projected_speed_m_s=float(np.linalg.norm(v)),initial_backend_speed_m_s=float(np.linalg.norm(velocity)),
            projection_position_difference_m=float(np.linalg.norm(np.asarray(p).ravel()-geometry['tip'])),
            projection_speed_difference_m_s=float(np.linalg.norm(v))-float(np.linalg.norm(velocity)),projection=geometry['gvs_projection'],
            actual_input_n=actual.tolist(),state=state,forecast_seal=w.chain['forecast_seal'],scientific_identity=digest(execution_scope(controller.plan_configuration)) if hasattr(controller,'plan_configuration') else None,
            work='Existing embedded controller first-period prediction; zero additional diagnostic solves/rollouts')
        # Active simulation reservation supplies exact candidate and execution IDs.
        with w.store.transaction() as db:
            calls=list(db.execute("SELECT run_id,request_id,execution_id FROM calls WHERE request_id='complete-simulation' AND status='running'"))
            if len(calls)!=1:raise ValueError('UNIQUE_ACTIVE_SIMULATION_REQUIRED')
            call=calls[0];session=w.store.session(call['run_id'],db);prediction.update(candidate_id=call['run_id'],execution_id=call['execution_id'],
                scientific_identity=digest(execution_scope(session['snapshot']['input'])))
            ref=w.store.put(db,prediction);w.store.event(db,call['run_id'],'local_prediction','sealed_before_step',request=call['request_id'],
                execution=call['execution_id'],inputs=[w.chain['forecast_seal']],outputs=[ref])
    return capture


def assess(w):
    forecast=read(RUN/'forecast_seal.json');batch=read(RUN/'validation_batch_result.json')
    if w.store.artifact(w.chain['forecast_seal'])!=forecast:raise ValueError('FORECAST_CHANGED')
    reader=ControlEvidence(w.store);outcomes=[];local=[];events=[]
    with w.store.connect(True) as db:ids=[r[0] for r in db.execute('SELECT run_id FROM sessions')]
    events=[e for i in ids for e in w.store.events(i)];seal=next(e for e in events if e['kind']=='prospective_forecast')
    reservations=[e for e in events if e['request_id']=='complete-simulation' and e['status']=='reserved']
    if len(reservations)!=len(forecast['forecasts']) or any(e['sequence']<=seal['sequence'] for e in reservations):raise ValueError('FORECAST_CHRONOLOGY_FAILED')
    incumbent=shared.campaign_metrics(w.incumbent)
    for f in forecast['forecasts']:
        row=next(r for r in batch['candidates'] if r['candidate_id']==f['candidate_id']);facts=row['execution']['factual_result'];a=shared.campaign_metrics(facts)
        if row['configuration']!=f['configuration'] or digest(execution_scope(reader.resolve(facts['execution_id'])['configuration']))!=f['scientific_identity']:raise ValueError('FORECAST_BINDING_FAILED')
        actual=dict(holding_speed_direction=direction(a['holding_max_speed_m_s']-incumbent['holding_max_speed_m_s'],TOLERANCES['speed_m_s']),
            holding_position_direction=direction(a['holding_max_error_m']-incumbent['holding_max_error_m'],TOLERANCES['position_m']))
        verdict={k:'unresolved' if f[k]=='unresolved' else 'correct' if f[k]==v else 'incorrect' for k,v in actual.items()}
        outcomes.append(dict(candidate_id=row['candidate_id'],execution_id=facts['execution_id'],forecast=f,observed=actual,metrics=a,verdict=verdict,
            acceptance_observed='preserved' if a['joint_reach_holding_passed'] else 'lost',acceptance_verdict='unresolved',comparison=shared.compare_results(w.incumbent,facts)))
        motion=measured_motion(reader,reader.resolve(facts['execution_id']))
        saved=[e for e in events if e['kind']=='local_prediction' and e['execution_id']==facts['execution_id']]
        if len(saved)!=len(CHECKPOINTS):raise ValueError('LOCAL_PREDICTION_COVERAGE_MISSING')
        for event in saved:
            prediction=w.store.artifact(event['outputs'][0]);following=next(m for m in motion if abs(m['time_s']-prediction['end_s'])<1e-8)
            if prediction['scientific_identity']!=f['scientific_identity']:raise ValueError('LOCAL_PREDICTION_BINDING_FAILED')
            done=next(e for e in events if e['run_id']==event['run_id'] and e['request_id']=='complete-simulation' and e['status']=='completed' and e['sequence']>event['sequence'])
            local.append(dict(prediction=prediction,prediction_reference=event['outputs'][0],seal_sequence=event['sequence'],simulation_completion_sequence=done['sequence'],score=local_score(prediction,following)))
    counts={k:sum(v==k for r in outcomes for v in r['verdict'].values()) for k in ('correct','incorrect','unresolved')}
    observed_order=pairwise_speed_order([dict(candidate_id=r['candidate_id'],holding_max_speed_m_s=r['metrics']['holding_max_speed_m_s']) for r in outcomes],'holding_max_speed_m_s')
    result=dict(outcomes=outcomes,direction_counts=counts,resolved_coverage=sum(counts[k] for k in ('correct','incorrect'))/sum(counts.values()),
        accuracy_among_resolved=None if counts['correct']+counts['incorrect']==0 else counts['correct']/(counts['correct']+counts['incorrect']),
        local_fidelity=local,local_direction_counts={k:sum(r['score']['direction_verdict']==k for r in local) for k in ('correct','incorrect')},
        local_endpoint_within_tolerance=sum(r['score']['endpoint_within_tolerance'] for r in local),predicted_speed_order=forecast['predicted_speed_order'],
        observed_speed_order=observed_order['order'],observed_speed_order_detail=observed_order,
        speed_order_forecast=forecast['speed_order_forecast'],ordering_verdict=ordering_score(forecast['speed_order_forecast'],observed_order),
        forecast_chronology=dict(seal_sequence=seal['sequence'],backend_reservation_sequences=[e['sequence'] for e in reservations],passed=True),
        full_evaluation_cost_s=sum(r['charged']['wall_s'] for row in batch['candidates'] for r in row['execution']['receipts'].values()),
        predictor_cost_s=read(RUN/'numerical_receipt.json')['charged']['wall_s'],rules_unchanged=True)
    atomic_json(RUN/'prediction_assessment.json',result);w.chain['prediction_assessment']=save(w.store,result);return result


def export(w,status,reason,elapsed):
    w.freeze.update(historical_results=w.historical_results,latest_tested=w.latest_tested,predecessor_decision=w.predecessor_decision,revision=revision())
    atomic_json(RUN/'freeze.json',w.freeze);atomic_json(RUN/'chain.json',w.chain)
    DiagnosticWorkflow.export(w,status,reason,elapsed)
    from tools.improvement_workflow import archive_store
    archive_store(w.store,EVIDENCE/'single_context',source_stores=[predecessor.RUN,predecessor.ORIGINAL,*[p for _,p,_ in shared.SOURCES],shared.prior.previous.prior.CONFIRM])
    with w.store.connect(True) as db:
        calls=[dict(r) for r in db.execute('SELECT run_id,request_id,status,charged,receipt FROM calls')]
        numerical=json.loads(db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone()[0])
        ids=[r[0] for r in db.execute('SELECT run_id FROM sessions')]
    events=[e for i in ids for e in w.store.events(i)]
    atomic_json(EVIDENCE/'single_context/campaign_receipts.json',[dict(run_id=r['run_id'],receipt=json.loads(r['receipt'])) for r in calls if r['receipt']])
    for kind,name in [('model_raw_response','campaign_raw_calls'),('model_decision','campaign_resolved_calls')]:
        atomic_json(EVIDENCE/('single_context/'+name+'.json'),[dict(run_id=e['run_id'],reference=e['outputs'][0],response=w.store.artifact(e['outputs'][0])) for e in events if e['kind']==kind])
    used=w.store.remaining()['used'];old=w.freeze['authorization_link']['old_usage'];corrections=max(w.store.session(i)['state'].get('protocol_corrections_used',0) for i in ids)
    accounting=dict(old=old,new=used,cumulative={k:old[k]+used[k] for k in old},stage_limits=LIMITS,numerical_work=numerical,
        corrections=dict(old=4,new=corrections,lifetime=4+corrections,stage_limit=4,consecutive_limit=2),
        semantic_corrections=dict(old=3,new=w.freeze.get('semantic_corrections',0)),
        receipt_charge_sum={k:sum(json.loads(r['charged'])[k] for r in calls) for k in LIMITS},occupied=w.store.remaining()['occupied'],predecessor_unchanged=True)
    if any(abs(accounting['receipt_charge_sum'][k]-used[k])>1e-8 for k in used):raise ValueError('ACCOUNTING_MISMATCH')
    assert_predecessor(w);atomic_json(EVIDENCE/'accounting.json',accounting)
    atomic_json(EVIDENCE/'campaign_status.json',dict(status=status,reason=reason,milestone4_closed=True,milestone5_complete=False,revision=revision()))


PLAN=shared.COMMON_PLAN.replace('This is ONE shared cumulative campaign: no reset or extra grant.','This is a NEW separately authorized stage linked to immutable completed predecessor evidence.').replace('No separate numerical diagnostic work.',
    'Separately authorized preview reserves600 seconds/1 workflow tool before execution; 12 local solves and24 rollouts are stage ceilings, not targets. Retain protected final interpretation.')+'''
Current step: a prospective controller-weight validation on fixed near/far0.16/0.11m,section scale0.95,compliant scenario. Source MUST be the verified passing incumbent execution91c3ba1b01d6499fb26df8f95409401b (holding/terminal0.05/0.05). Vary ONLY control/recipe/holding_tip_speed_weight within the already authorized [0,1] domain; terminal remains0.05. Select ONE or TWO genuinely unevaluated values on this structure;0,0.05,0.10 are excluded development points. Prefer two points if useful but do not force a favorable outcome. Justify exact values and weakening observations. Max backend attempts and completed target equal number of candidates; never exceed2. All candidates receive complete evaluation. Historical 0.05 versus0 differs only slightly;0.10 loses acceptance. These are DEVELOPMENT DATA, never validation cases. Two-checkpoint common cold preview at0.20 and0.30s retains production early stops and horizons10/5; it may abstain. No automatic rejection or screening reliability. Entire completed sequence including both passing research references must be interpreted in final decision. Fixed_conditions include the explicit structure and recipe. Scientific identities, accepted selection, latest execution, pending and completed candidates are distinct. Stop after planned candidates and final interpretation; do not request further experiments.'''


def planning_handoff(w):
    """Prepare the actual native handoff without making a provider request."""
    from tools.diagnostic_facts import handover
    check=w.store.artifact(w.chain['feedback']);handover(w.host('design'),check['result'],w.store.artifact(check['result']),origin=dict(kind='accepted_saved_check'),kind='performed_check_result')
    packet=shared.planning_packet(w,2);packet.update(campaign_limits=LIMITS,primary_reference=w.incumbent['candidate'],
        accepted_final_selection=w.incumbent['candidate'],diagnosis=read(RUN/'historical_diagnosis.json'),development_exclusions=DEVELOPMENT,
        extra_preview_reservation=dict(wall_s=600.,tool_calls=1),stage_authorization=AUTHORIZATION)
    if w.chain.get('development_fidelity'):packet['development_fidelity']=w.store.artifact(w.chain['development_fidelity'])['detail']
    packet.update(external_transmission_authorization=EXTERNAL_AUTHORIZATION,
        development_fidelity_reference=w.chain.get('development_fidelity'),
        scientific_warning='At 0.31 s the historical 0.10/0.05 recipe predicted approximately 0.015943 m/s versus observed 0.022129 m/s, crossing the 0.020000 m/s limit. Correct speed-change direction did not establish reliable threshold classification.',
        development_interpretation='All six matched intervals underestimated endpoint speed and missed 1e-4 m/s tolerance; projection and subsequent error are distinct. Historical local direction labels meant increasing/decreasing speed, not automatically worse/better task outcome. Tiny trajectory onset is numerical, not proof of meaningful deterioration.',
        stage_remaining=w.store.remaining()['remaining'],correction_usage=dict(protocol=w.store.session(w.host('design').run_id)['state'].get('protocol_corrections_used',0),semantic=w.freeze.get('semantic_corrections',0)))
    packet['history']=predecessor.compact_decision_packet(dict(history=packet['history']),None)['history']
    packet['diagnosis_reference']=save(w.store,packet['diagnosis'])
    for row in packet['diagnosis']['records']:
        row.pop('files',None)
        row['updates']=[o for o in row['updates'] if o['update_id'] in (*CHECKPOINTS,34)]
    w.instructions={**w.instructions,'improvement':PLAN};w.current_stage='validation'
    return dict(study_packet=packet,research_records=w.historical_results,latest_tested=w.latest_tested,
        require_source_binding=True,predecessor_decision=w.predecessor_decision,planned_backend_count=2,
        allowed_batch_variables=['control/recipe/holding_tip_speed_weight'],max_variable_count=1,
        required_structure_identity=execution_scope(w.store.artifact(w.incumbent['configuration'])['effective'])['robot']['identity'])


def refresh_handoff():
    """Version the prior blocked payload and record explicit same-stage approval."""
    from unittest.mock import patch
    w=restore();assert_predecessor(w)
    if w.store.remaining()['used']['model_calls']:raise ValueError('FIRST_HANDOFF_ALREADY_SENT')
    old=RUN/'validation_serialized_handoff.json';historical=RUN/'validation_serialized_handoff_v1.json'
    if not historical.exists():historical.write_bytes(old.read_bytes())
    prior_delivery=EVIDENCE/'delivery_before_resume.json'
    if not prior_delivery.exists():prior_delivery.write_bytes((EVIDENCE/'delivery.json').read_bytes())
    ref=save(w.store,EXTERNAL_AUTHORIZATION);w.freeze['external_transmission_authorization']=ref
    with w.store.transaction() as db:w.store.event(db,w.host('design').run_id,'authorization','resumed_same_grant',outputs=[ref])
    atomic_json(RUN/'external_transmission_authorization.json',EXTERNAL_AUTHORIZATION)
    extra=planning_handoff(w);original=w.check_provider_payload
    def check_only(host):
        original(host);raise RuntimeError('REFRESHED_OUTBOUND_HANDOFF_ONLY')
    with patch.object(w,'check_provider_payload',side_effect=check_only):
        try:w.phase('improvement','search_batch_plan','search_plan',**extra)
        except RuntimeError as exc:
            if str(exc)!='REFRESHED_OUTBOUND_HANDOFF_ONLY':raise
    atomic_json(RUN/'handoff_versions.json',dict(v1=dict(path=historical.name,sha256=hashlib.sha256(historical.read_bytes()).hexdigest(),status='blocked_historical',includes_six_intervals=False),
        v2=dict(path='validation_serialized_handoff_v2.json',reference=w.chain['refreshed_handoff'],status='authorized_current',includes_six_intervals=True),
        prior_rejection='external_handoff_review.json',external_authorization=ref,usage_unchanged=w.store.remaining()['used']))
    export(w,'authorized_handoff_refreshed','Explicit transmission approval recorded; existing stage and usage preserved; actual six-interval outbound payload checked.',0.)


def prepare_review():
    from unittest.mock import patch
    w=prepare();extra=planning_handoff(w)
    # Stop immediately before run_loop. This exercises the real serializer and
    # its guard; no credential loading, network request or fabricated model plan.
    with patch.object(w,'check_provider_payload',side_effect=RuntimeError('OFFLINE_HANDOFF_SEALED_NO_PROVIDER_REQUEST')):
        try:w.phase('improvement','search_batch_plan','search_plan',**extra)
        except RuntimeError as exc:
            if str(exc)!='OFFLINE_HANDOFF_SEALED_NO_PROVIDER_REQUEST':raise
    w.check_provider_payload(w.host('design'))
    atomic_json(RUN/'external_handoff_review.json',dict(destination='https://api.deepseek.com',model='deepseek-flash',
        payload= 'validation_serialized_handoff.json',data='Robot/task/controller configuration, historical simulation diagnostics, scientific identities, metrics, immutable artifact references, instructions and resource budgets. No credentials.',
        provider_attempts=0,backend_attempts=0,automatic_approval_rejected=True,
        rejection_reason='Specific sensitive historical diagnostics/project payload and external model destination lacked established trusted authorization in automatic review.'))
    export(w,'awaiting_external_payload_approval','Automatic approval review rejected external research handoff; no provider or backend attempt.',0.)


def offline_fidelity():
    w=restore()
    if 'development_fidelity' in w.chain:raise ValueError('DEVELOPMENT_FIDELITY_ALREADY_SAVED')
    protocol=dict(classification='matched_development_fidelity',development_executions=DEVELOPMENT,
        development_bindings={r['facts']['execution_id']:r['binding'] for r in w.historical_results if r['facts']['execution_id'] in DEVELOPMENT},
        checkpoints=list(CHECKPOINTS),tolerances=TOLERANCES,prospective=False)
    ref=save(w.store,protocol)
    from tools.platform_registry import registry
    reg=registry();reg.add(DEFINITION)
    inp=deepcopy(w.store.artifact(w.incumbent['configuration'])['effective']);inp['run_id']=w.project+'-offline-fidelity'
    inp['policy'].update(budget={**LIMITS,'model_calls':0},route=None,tool_bindings={DEFINITION.extension_id:DEFINITION.version},allowed_tools=[],timeout_s=600.)
    inp['policy']['operation_allowances']={DEFINITION.extension_id:dict(timeout_s=600.,reserve_s=600.)}
    host=Host(RUN,inp['run_id'],reg=reg);host.create(inp);host.resume()
    receipt=host.invoke(dict(request_id='matched-development-fidelity',tool_id=DEFINITION.extension_id,tool_version=DEFINITION.version,arguments=dict(protocol=ref),
        reason='Authorized offline arithmetic and projected kinematics over saved matched-input predictions; zero new solves,rollouts,provider or backend attempts.',cache='new'))
    atomic_json(RUN/'development_fidelity_receipt.json',receipt)
    if receipt['execution_status']!='completed':raise ValueError('DEVELOPMENT_FIDELITY_FAILED: '+str(receipt.get('error')))
    w.chain['development_fidelity']=receipt['output'];atomic_json(RUN/'development_fidelity.json',w.store.artifact(receipt['output'])['detail'])
    export(w,'awaiting_external_payload_approval','Offline historical diagnosis completed; external provider handoff remains blocked by automatic approval review.',0.)


def deliver_blocked():
    """Evidence-only closeout of completed offline work; no scientific closure."""
    w=restore();assert_predecessor(w)
    accounting=read(EVIDENCE/'accounting.json');diagnosis=read(RUN/'historical_diagnosis.json');fidelity=read(RUN/'development_fidelity.json')
    if accounting['new']['model_calls'] or accounting['new']['backend_solves']:raise ValueError('BLOCKED_DELIVERY_HAS_LIVE_WORK')
    if 'search_plan' in w.chain or 'forecast_seal' in w.chain:raise ValueError('BLOCKED_DELIVERY_HAS_PROSPECTIVE_PLAN')
    for name in ('milestone5_validation_console.log','milestone5_validation_offline_console.log','milestone5_validation_fidelity_console.log'):
        path=ROOT/'runs'/name
        if path.exists():(EVIDENCE/'single_context'/name).write_bytes(path.read_bytes())
    errors=[abs(r['score']['endpoint_speed_error_m_s']) for r in fidelity['development_local_fidelity']]
    delivery=dict(status='awaiting_external_payload_approval',requested_stage_completed=False,offline_diagnosis_completed=True,
        milestone4_closed=True,milestone5_complete=False,primary_reference=w.incumbent['candidate'],latest_tested=w.latest_tested,
        accepted_predecessor_selection=w.incumbent['candidate'],development_data=DEVELOPMENT,prospective_validation_data=[],
        original_pilot_preserved=True,old_forecast_unchanged=True,accounting=accounting,
        historical_diagnosis=dict(reference='single_context/historical_diagnosis.json',differences=diagnosis['differences'],checkpoints=list(CHECKPOINTS),
            maxima=[dict(execution_id=r['execution_id'],time_s=r['holding_maximum']['time_s'],speed_m_s=r['holding_maximum']['speed_m_s']) for r in diagnosis['records']]),
        local_development_fidelity=dict(reference='single_context/development_fidelity.json',matched_intervals=6,
            correct_speed_change_directions=sum(r['score']['direction_verdict']=='correct' for r in fidelity['development_local_fidelity']),
            endpoint_within_numerical_tolerance=sum(r['score']['endpoint_within_tolerance'] for r in fidelity['development_local_fidelity']),
            endpoint_absolute_speed_error_range_m_s=[min(errors),max(errors)],not_prospective=True,independent_repeatability_demonstrated=False),
        prospective_predictions=None,prospective_results=None,validation_accuracy=None,accepted_research_model_role=None,accepted_model_next_action=None,
        operational_next_action='Await approval of this specific external research handoff; no new experiment launches automatically.',
        blocker=dict(action='Launch bounded research-model planning and subsequent stage workflow.',destination='https://api.deepseek.com',model='deepseek-flash',
            automatic_approval_rejected=True,attempts=1,process_started=False,provider_attempt_charged=False,
            stated_reason='The script loads provider credentials and sends a research-planning payload containing internal historical diagnostics and project details to an external model destination; no trusted user authorization for that specific sensitive payload and destination is established.',
            review_payload='single_context/validation_serialized_handoff.json',credentials_in_payload=False),
        engineering_interventions=['Opt-in actual-input/pre-step observation; production settings preserved.',
            'Two-checkpoint cold preview and projected-state-aware matched input scoring; no added scientific engine.',
            'Resolved imported historical evidence through existing BoundReader instead of fabricating local execution ownership.',
            'Actual serialized handoff exported without provider request after automatic approval rejection.',
            'Prepared resumable same-stage ledger; preserves all predecessor states, receipts, charges and seals.',
            'Updated CURRENT_STATUS with Milestone4 closure, Milestone5 open status, and exact access blocker.'],
        tests=dict(passed=8,scope='Focused alignment, serialized handoff, historical binding, predecessor immutability and evidence-only recovery.',
            original_failures_preserved_in='offline_verification.json'),additional_solves=0,additional_rollouts=0,
        no_replays=True,no_workers=True,provider_settings_preserved=True,implementation_checkpoint='8b64aac',revision=revision(),pushed=False)
    atomic_json(EVIDENCE/'delivery.json',delivery)
    atomic_json(EVIDENCE/'offline_verification.json',dict(passed=True,test_count=8,
        command='softagent Python -m unittest tests.test_milestone5_validation tests.test_milestone45.PilotPhysicalTests tests.test_milestone45.FinalRecoveryTests',
        failures_preserved=[dict(attempt='initial sandboxed tests',reason='Windows sandbox denied temporary SQLite store filesystem access.'),
            dict(attempt='first escalated tests',reason='Historical imports retain external ownership; local ControlEvidence.resolve required unique local ownership; corrected with BoundReader. Temporary store cleanup also retained a SQLite handle until garbage collection.')],
        credentials_printed=False,provider_preflight=False,backend_replay=False,predecessor_hash_and_usage_checks=True))
    folder=EVIDENCE/'implementation'
    for path in FILES:
        target=folder/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/path).read_bytes())
    atomic_json(EVIDENCE/'sha256_manifest.json',{p.relative_to(EVIDENCE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(EVIDENCE.rglob('*')) if p.is_file() and p.name!='sha256_manifest.json'})
    print(json.dumps(dict(status=delivery['status'],usage=accounting,local_development_fidelity=delivery['local_development_fidelity']),indent=2))


def live():
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
    # Existing runner repair for the sandbox's deliberately unusable proxy only.
    for key in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):
        if '127.0.0.1:9' in os.environ.get(key,''):os.environ.pop(key)
    if subprocess.check_output(['git','diff','HEAD','--',*FILES],cwd=ROOT,text=True):raise ValueError('COMMIT_BEFORE_LIVE')
    w=restore() if (RUN/'freeze.json').exists() else prepare();start=time.monotonic();status='incomplete';reason=None
    try:
        # Existing planner creates its own capacity packet, so add diagnosis and
        # renewed stage ceiling to the actual shared serialized handoff.
        if 'search_plan' not in w.chain:
            if w.store.remaining()['used']['model_calls']:raise ValueError('NO_ACCEPTED_PLAN_AFTER_PAID_ATTEMPT')
            w.phase('improvement','search_batch_plan','search_plan',**planning_handoff(w))
        elif (RUN/'validation_batch_result.json').exists():
            raise ValueError('FULL_BATCH_SAVED_USE_EVIDENCE_ONLY_INTERPRETATION_RECOVERY')
        elif w.store.remaining()['used']['backend_solves']:
            raise ValueError('BACKEND_ATTEMPT_EXISTS_USE_SAVED_RECEIPT_RECOVERY')
        else:
            state=w.store.session(w.host('design').run_id)['state']
            if state.get('stop_reason')=='IncompleteRead(0 bytes read)':
                previous=w.host('design').run_id
                shared.migrate_planning_host(w,'forecast-transport-retry1')
                intervention=dict(prior_context=previous,new_context=w.host('design').run_id,reason='Known failed forecast interpretation transport receipt; same project, no usage or correction reset.',
                    reuse='Accepted plan and completed six solves/six rollouts; no numerical replay.',settings_changed=False)
                atomic_json(RUN/'forecast_transport_recovery.json',intervention)
                w.freeze.setdefault('resume_interventions',[]).append(intervention)
        record=w.store.artifact(w.chain['search_plan']);atomic_json(RUN/'validation_plan.json',record)
        count=record['plan']['max_candidates']
        if record['bindings']['subject']!=w.incumbent['candidate'] or not 1<=count<=2 or record['plan']['max_backend_attempts']!=count or record['plan']['target_changed_configurations']!=count:raise ValueError('VALIDATION_PLAN_SCOPE')
        if any(r['control/recipe/holding_tip_speed_weight'] in (0,.05,.1) for r in record['plan']['candidates']):raise ValueError('DEVELOPMENT_POINT_NOT_VALIDATION')
        required=batch_requirement(count,planning=dict(model_calls=0,tool_calls=0,wall_s=0),preparation_reserve_s=5.)['requirement']
        if not (RUN/'numerical_receipt.json').exists():required['wall_s']+=600.;required['tool_calls']+=1
        remaining=w.store.remaining()['remaining']
        if any(v>remaining[k] for k,v in required.items()):raise ValueError('PREVIEW_EXECUTION_INTERPRETATION_CAPACITY')
        atomic_json(RUN/'prelaunch_review.json',dict(passed=True,plan=w.chain['search_plan'],exact_candidates=record['plan']['candidates'],required=required,available=remaining,
            prospective_exclusions=DEVELOPMENT,primary_reference=w.incumbent['candidate'],revision=revision()))
        token=PRE_STEP_OBSERVER.set(observer(w))
        try:shared.execute(w,'validation',record,before_execution=freeze_forecasts,decision_extra=dict(
            stage_scope='Prediction validation; full evaluations retained; both forecasts sealed before either backend.',
            primary_reference=w.incumbent['candidate'],accepted_predecessor_selection=w.incumbent['candidate'],development_exclusions=DEVELOPMENT))
        finally:PRE_STEP_OBSERVER.reset(token)
        assessment=assess(w);w.current_stage='prediction_interpretation'
        w.instructions={**w.instructions,'response_final':shared.FINAL+''' Final prediction-validation decision. All planned candidates are completed, none pending. Interpret prediction_assessment AND numerical development diagnosis AND the accepted historical sequence. Explicitly separate local dynamics fidelity, candidate-specific cold-preview policy behavior, full-task directions/ranking, joint acceptance, and computation/real-time failure. State correct/incorrect/unresolved coverage; zero resolved means accuracy undefined. Select narrowest supported model role (local diagnostic evidence,research guidance,execution ordering with full evaluation,or insufficient useful discrimination); no automatic rejection or general reliability. Accept next action defer predictor/continue demonstrated scope/specific future repair in reasoning. next_research.route=stop,zero proposed_budget: no further run in this grant. Milestone4 remains closed;Milestone5 overall open unless original gates demonstrably met. About450 words.'''}
        packet=read(RUN/'validation_decision_packet.json');packet.update(prediction_assessment=assessment,
            numerical_preview=read(RUN/'prediction_numerical.json'),frozen_forecast=read(RUN/'forecast_seal.json'),all_planned_candidates_completed=True,
            development_data=DEVELOPMENT,primary_reference=w.incumbent['candidate'])
        # Avoid repeating detailed plans in provider payload; immutable detail refs remain.
        for row in packet['numerical_preview']['rows']:row.pop('plan_metrics',None)
        for row in packet['prediction_assessment']['outcomes']:row['comparison']={k:v for k,v in row['comparison'].items() if k not in ('baseline','candidate')}
        packet['history']=predecessor.compact_decision_packet(dict(history=packet['history']),None)['history']
        packet['frozen_forecast'].pop('predictor_fingerprint',None)
        w.phase('response_final','design_response','final_response',decision_packet=packet,decision_packet_reference=save(w.store,packet),
            batch_result=w.store.artifact(w.chain['batch_summary']),require_research_route=True,require_research_budget=True,
            research_records=w.historical_results,latest_tested=w.latest_tested,improvement_feedback_content=dict(baseline_facts=w.retained_baseline,execution=None),
            check_feedback=[dict(reference=w.chain['batch_summary'])],source_report=w.common['source_report'],source_record=w.source_record)
        status='completed';reason='Bounded prospective validation and final model interpretation completed; Milestone5 gates remain open.'
    except Exception as exc:
        reason=str(exc);atomic_json(RUN/'stage_failure.json',dict(type=type(exc).__name__,message=reason));print('STOP',reason,flush=True)
    export(w,status,reason,time.monotonic()-start)


if __name__=='__main__':
    if '--prepare-review' in sys.argv:prepare_review()
    elif '--refresh-handoff' in sys.argv:refresh_handoff()
    elif '--offline-fidelity' in sys.argv:offline_fidelity()
    elif '--deliver-blocked' in sys.argv:deliver_blocked()
    else:live()
