"""Two conditional ranking-only batches using the existing native store and tools."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import os
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from examples import milestone5_predictor_campaign as development
from examples.milestone5_future_validation import configuration,candidate_preparation,SimpleContext
from tools.platform_store import Store,plain,encode,zero
from tools.platform_host import Host
from tools.state_io import read,atomic_json,digest
from tools.batch_budget import batch_requirement
from tools.execution_completion import complete_execution,EXECUTION_ALLOWANCES
from tools.runtime_identity import require_softagent_runtime
from extensions.tendon_family.control_evidence import PRE_STEP_OBSERVER,ControlEvidence
from extensions.tendon_family.diagnostic_evidence import BoundReader,measured_motion
from extensions.tendon_family.diagnostic_math import charge_units
from extensions.tendon_family.gvs_profile import execution_scope
from extensions.tendon_family.milestone5_preparation import RESEARCH
from extensions.tendon_family.milestone5_protocol import pair_decision,assess_local,assess_screening
from extensions.tendon_family.milestone5_campaign_predictor import SerialMechanics,VERSION,GRIDS,history
from extensions.tendon_family.milestone5_campaign_local import LOCAL_VERSION,diagnose


def folder(batch):return ROOT/f'runs/milestone5_predictor_campaign_validation{batch}_20261005'
def evidence(batch):return ROOT/f'evidence/milestone5_predictor_campaign_validation{batch}_20261005'


def freeze_protocol(protocol,assessment,freeze):
    path=development.RUN/'prospective_protocol.json'
    if path.exists():return read(path)
    assert protocol['accepted_research_judgment']['readiness'].startswith('GO_EXPERIMENT_RANKING_ONLY')
    assert assessment['economics']['positive_net_saving']
    p=deepcopy(protocol)
    p.update(status='frozen_ranking_only_before_prospective_forecasts',ready_for_bounded_prospective_experiment=True,
        preview_version=VERSION,local_version=LOCAL_VERSION,
        role=dict(name='ranking_only',safety_authority=False,eligibility_authority=False,
            quantitative_local_accuracy=False,original_failures=assessment['local_counts']),
        hypothesis='On each registered reset-clock episode, the unchanged seven-replan predictor correctly resolves the pair order of sampled maximum holding speed at the unchanged 1e-4 m/s margin. Both candidates receive full evaluation.',
        local_checkpoints=[20,30],local_grids=GRIDS,local_attempt_ceiling=12,
        original_accuracy_tolerances=dict(position_m=1e-6,vector_m_s=1e-4,speed_m_s=1e-4),
        economics_rule='Fresh pair workflow receipts plus required native decision receipts versus ONE rejected candidate complete evaluation. Subtract measured local observer instrumentation from evaluation cost; both candidates evaluated means actual savings zero.',
        continuation=freeze['conditional_validation']['continuation'],
        continuation_checks=['both evaluations valid and complete','all four local numerical checks pass','no local holding or full-history false-safe',
            'resolved correct ranking','positive counterfactual net saving including required research receipts','accepted native CONTINUE_BATCH2'],
        accepted_development_economics=assessment['economics'],
        operational_next_action='execute_first_registered_batch')
    # These files are frozen before either prospective history or backend outcome.
    for name in ['examples/milestone5_campaign_validation.py','extensions/tendon_family/milestone5_campaign_local.py']:
        p['implementation_identity']['files'][name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    for b in p['reservations'].values():
        if isinstance(b,dict) and 'admitted' in b:b.update(admitted=True,grant_materialized=False)
    atomic_json(path,p)
    atomic_json(development.RUN/'prospective_protocol_seal.json',dict(identity=digest(p),
        sealed_before_prospective_forecasts=True,accepted_interpretation=p['research_decisions']['interpretation']))
    return p


def check_protocol(p):
    development.check_previous()
    assert p['preview_version']==VERSION and p['local_version']==LOCAL_VERSION
    assert p['role']['name']=='ranking_only' and not p['role']['safety_authority'] and not p['role']['eligibility_authority']
    assert p['local_checkpoints']==[20,30] and p['local_grids']==list(GRIDS)
    assert p['ready_for_bounded_prospective_experiment']
    assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==sha for n,sha in p['implementation_identity']['files'].items()),'FROZEN_IMPLEMENTATION_CHANGED'
    current=batch_requirement(2,planning=dict(model_calls=0,tool_calls=0,wall_s=0.),preparation_reserve_s=5.)
    assert current==p['reservations']['batch1']['public_base'],'PUBLIC_RESERVATION_CHANGED'
    assert all(p['reservations']['batch1']['complete_requirement'][k]<=development.VALIDATION_LIMITS[k] for k in development.VALIDATION_LIMITS)


def static_model(cfg):
    # Only unchanged robot mechanics are reused, never a prospective trajectory.
    store=Store(development.RUN);r=BoundReader(store,read(development.RUN/'freeze.json')['source_binding'])
    s=r.resolve(r.binding['execution_id']);assert cfg['robot']==s['configuration']['robot'],'ROBOT_IDENTITY'
    return SerialMechanics(cfg,r.read_file(s,'resolved_physics.json'),r.read_file(s,'compiled_physics.json'),
        store.artifact(s['files']['robot.xml'],raw=True).decode('utf8'))


def preview(h,cfg,scenario):
    prior=h.store.lookup(h.run_id,'campaign-preview')
    if prior:
        assert prior['receipt'],'UNRESOLVED_PREVIEW_NO_REPLAY'
        receipt=json.loads(prior['receipt']);assert receipt['execution_status']=='completed','FAILED_PREVIEW_NO_REPLAY'
        return h.store.artifact(receipt['output'])
    row,_=h.store.reserve(h.run_id,'campaign-preview',digest(dict(configuration=cfg,scenario=scenario)),h.actor,
        {**zero(),'tool_calls':1,'wall_s':1200.})
    ctx=SimpleContext(h,row);start=time.monotonic();charge_units(ctx,'preview_attempts',1)
    try:
        model=static_model(cfg)
        result=history(cfg,scenario['reduced_initial_state'],model,lambda:charge_units(ctx,'local_solves',1),
            deadline=time.perf_counter()+1100.,save_update=lambda r:ctx.save_artifact(r,'campaign_preview_update'))
        result.update(scenario_id=scenario['scenario_id'],scientific_identity=digest(execution_scope(cfg)),configuration=cfg,
            serial_setup_s=model.setup_s,classification='Prospective complete own-history forecast before either backend',
            supported_use='Frozen experimental ranking only; no safety or eligibility authority')
        receipt=h.store.complete(row,dict(request_id='campaign-preview',execution_id=row['execution_id'],caller=h.actor,
            tool_id='analysis.milestone5_campaign_assessment',tool_version='1.0.0',execution_status='completed',charged=zero()),result,time.monotonic()-start)
    except Exception as exc:
        receipt=h.store.complete(row,dict(request_id='campaign-preview',execution_id=row['execution_id'],caller=h.actor,
            tool_id='analysis.milestone5_campaign_assessment',tool_version='1.0.0',execution_status='failed',charged=zero(),
            error=dict(type=type(exc).__name__,message=str(exc))),dict(error=str(exc),complete=False),time.monotonic()-start)
        atomic_json(h.store.root/(h.run_id+'_preview_receipt.json'),receipt);raise
    atomic_json(h.store.root/(h.run_id+'_preview_receipt.json'),receipt)
    return h.store.artifact(receipt['output'])


def seal_pair(store,run_id,p,scenario,forecasts):
    if len(forecasts)!=2 or {f['recipe_id'] for f in forecasts}!={r['recipe_id'] for r in p['recipes']}:
        raise ValueError('BOTH_CANDIDATE_FORECASTS_REQUIRED')
    for f in forecasts:
        recipe=next(r for r in p['recipes'] if r['recipe_id']==f['recipe_id'])
        cfg=deepcopy(recipe['configuration']);cfg['task']['initializer']=deepcopy(scenario['configuration']['task']['initializer'])
        if f['version']!=VERSION or not f['complete'] or len(f['rows'])!=35 or f['scenario_id']!=scenario['scenario_id']:
            raise ValueError('FORECAST_SCOPE_OR_COVERAGE')
        if f['scientific_identity']!=digest(execution_scope(cfg)):raise ValueError('FORECAST_CONFIGURATION_BINDING')
    value=dict(protocol_identity=digest(p),scenario_identity=digest(scenario),forecasts=forecasts,pair_decision=pair_decision(forecasts),
        predictor_version=VERSION,role=p['role'],classification='Sealed before either backend')
    with store.transaction() as db:
        if db.execute("SELECT COUNT(*) FROM calls WHERE request_id='complete-simulation'").fetchone()[0]:raise ValueError('BACKEND_ALREADY_STARTED')
        state=store.session(run_id,db)['state'];prior=state.get('m5_pair_seal')
        if prior:
            if store.artifact(prior)!=value:raise ValueError('PAIR_SEAL_IMMUTABLE')
            return prior
        ref=store.put(db,value);state['m5_pair_seal']=plain(ref);store.update_state(db,run_id,state)
        store.event(db,run_id,'m5_pair_forecast','sealed_before_either_backend',outputs=[ref])
    return plain(ref)


def checkpoint_observer(h,cfg,seal,p):
    def capture(update_id,t,controller,geometry,velocity,actual):
        if update_id not in p['local_checkpoints']:return
        if abs(t-update_id*.01)>1e-9:raise ValueError('CHECKPOINT_CLOCK')
        command=np.asarray(controller.last['desired_tension_n'])
        if np.max(abs(command-actual))>1e-9:raise ValueError('CAUSAL_COMMAND_MAPPING_MISMATCH')
        with h.store.connect(True) as db:
            calls=list(db.execute("SELECT * FROM calls WHERE run_id=? AND request_id='complete-simulation' AND status='running'",(h.run_id,)))
        if len(calls)!=1:raise ValueError('ACTIVE_BACKEND_CALL_REQUIRED')
        ctx=SimpleContext(h,calls[0]);start=time.perf_counter()
        state=controller.observations[-1]['measured_initial_state'];model=static_model(cfg)
        prediction=diagnose(model,state,command,t,charge=lambda:charge_units(ctx,'prediction_evaluations',1),
            save_result=lambda r:ctx.save_artifact(dict(update_id=update_id,result=r),'campaign_local_resolution'),deadline=start+40.)
        prediction.update(initial_backend_speed_m_s=float(np.linalg.norm(velocity)),initial_backend_velocity_m_s=np.asarray(velocity).tolist(),
            initial_backend_position_m=np.asarray(geometry['tip']).tolist(),initial_state=list(state),pair_seal=seal,
            configuration_identity=digest(cfg),execution_id=calls[0]['execution_id'],update_id=update_id)
        with h.store.transaction() as db:
            if h.store.session(h.run_id,db)['state'].get('m5_pair_seal')!=seal:raise ValueError('PAIR_SEAL_REQUIRED')
            ref=h.store.put(db,prediction)
            h.store.event(db,h.run_id,'m5_local_prediction','sealed_before_step',request=calls[0]['request_id'],
                execution=calls[0]['execution_id'],inputs=[seal],outputs=[ref])
        # This includes local setup, all integrations and sealing; charged within
        # the outer simulation, subtracted only for counterfactual evaluation cost.
        with h.store.transaction() as db:
            ref=h.store.put(db,dict(update_id=update_id,cost_s=time.perf_counter()-start,prediction=plain(ref)))
            h.store.event(db,h.run_id,'local_instrumentation','completed_before_step',request=calls[0]['request_id'],outputs=[ref])
    return capture


def assess(batch):
    store=Store(folder(batch));p=read(folder(batch)/'protocol.json');hosts=[Host(folder(batch),f'm5campaign-b{batch}-r{i}') for i in (1,2)]
    seal=store.session(hosts[0].run_id)['state']['m5_pair_seal'];sealed=store.artifact(seal)
    outcomes=[];local=[];evaluation_costs={};updates=[]
    for h,recipe in zip(hosts,p['recipes']):
        cfg=store.session(h.run_id)['snapshot']['input'];result=read(folder(batch)/(h.run_id+'_result.json'))
        assert result['status']=='evaluated';feedback=result['structured_feedback']
        assert feedback['holding']['coverage_complete'] and not feedback['missing_data'],'COMPLETE_OUTCOME_REQUIRED'
        reader=ControlEvidence(store);source=reader.resolve(result['execution_id']);motion=measured_motion(reader,source)
        update_count=len(reader.read_file(source,'controller_observations.json'));updates.append(update_count)
        assert update_count==35,'PRODUCTION_UPDATE_COVERAGE'
        outcomes.append(dict(candidate_id=h.run_id,holding_weight=recipe['holding_weight'],holding_max_speed_m_s=feedback['holding']['max_speed_m_s'],
            holding_max_error_m=feedback['holding']['max_position_error_m'],joint_acceptance=feedback['joint_reach_holding_success'],
            terminal_error_m=feedback['terminal']['error_m'],deadline_misses=feedback['deadline_misses']))
        events=store.events(h.run_id);instrumentation=sum(store.artifact(e['outputs'][0])['cost_s'] for e in events if e['kind']=='local_instrumentation')
        costs=sum(r['charged']['wall_s'] for r in result['receipts'].values())
        evaluation_costs[h.run_id]=dict(actual_instrumented_s=costs,local_validation_instrumentation_s=instrumentation,operational_s=costs-instrumentation)
        for event in events:
            if event['kind']!='m5_local_prediction':continue
            prediction=store.artifact(event['outputs'][0]);observed=deepcopy(next(m for m in motion if abs(m['time_s']-prediction['end_s'])<1e-9))
            observed['target_m']=cfg['task']['goal']['data']['target_m']
            score=assess_local(prediction,observed,prediction['numerical_uncertainty']['speed_m_s'])
            score['position_within_tolerance']=score['position_error_norm_m']<=1e-6
            local.append(dict(candidate_id=h.run_id,prediction=prediction,score=score,seal_sequence=event['sequence'],prediction_reference=event['outputs'][0]))
    assert len(local)==4,'LOCAL_CHECKPOINT_COVERAGE'
    with store.connect(True) as db:
        receipts=[json.loads(r[0]) for r in db.execute('SELECT receipt FROM calls WHERE receipt IS NOT NULL')]
    preview_s=sum(r['charged']['wall_s'] for r in receipts if r['request_id']=='campaign-preview')
    research_s=sum(r['charged']['wall_s'] for r in receipts if r['tool_id'] in ('model.deepseek',RESEARCH.extension_id,'evidence.read'))
    research_ref=store.session(hosts[0].run_id)['state'].get('handoffs',{}).get('m5_interpretation')
    judgment=store.artifact(research_ref) if research_ref else None
    decision=sealed['pair_decision'];rejected=decision['hypothetical_rejection']
    avoided=evaluation_costs[rejected]['operational_s'] if rejected else 0.
    incremental=preview_s+research_s
    screening=assess_screening(decision,outcomes,incremental,sum(c['operational_s'] for c in evaluation_costs.values()))
    screening.update(sealed_decision=decision)
    resolved=sum(r['score']['direction_verdict']!='unresolved' for r in local)
    conditions=dict(both_evaluations_complete=True,numerical=all(r['prediction']['numerical_stable'] for r in local),
        no_false_safe=not screening['predicted_safe_observed_violating'] and not any(r['score']['physical_holding_false_safe'] for r in local),
        resolved_correct_ranking=screening['pairwise_order_verdict']=='correct',positive_net=avoided>incremental,
        accepted_research_continuation=judgment is not None and judgment['readiness'].startswith('CONTINUE_BATCH2'))
    a=dict(protocol_identity=digest(p),batch=batch,scenario_id=p['scenarios'][batch-1]['scenario_id'],pair_seal=seal,
        local=local,screening=screening,outcomes=outcomes,evaluation_costs=evaluation_costs,
        economics=dict(pair_forecast_s=preview_s,required_research_s=research_s,incremental_screening_s=incremental,
            one_skipped_evaluation_s=avoided,counterfactual_net_savings_s=avoided-incremental,
            final_research_receipted=research_ref is not None,actual_validation_savings_s=0.,actual_evaluations_avoided=0),
        preview_controller_solves=sum(f['solves'] for f in sealed['forecasts']),backend_controller_updates=sum(updates),
        continuation_conditions=conditions,continue_batch2=batch==1 and all(conditions.values()),
        local_summary=dict(distinct_intervals=4,resolved=resolved,resolved_coverage=resolved/4,
            direction_accuracy_among_resolved=None if not resolved else sum(r['score']['direction_verdict']=='correct' for r in local)/resolved,
            numerical_passes=sum(r['prediction']['numerical_stable'] for r in local),
            position_passes=sum(r['score']['position_within_tolerance'] for r in local),
            speed_passes=sum(r['score']['endpoint_within_tolerance'] for r in local),vector_passes=sum(r['score']['vector_within_tolerance'] for r in local),
            holding_false_safe=sum(r['score']['physical_holding_false_safe'] for r in local)),
        research_reference=research_ref,research_judgment=judgment,incumbent_retained=True,milestone5='open',safety_authority=False)
    atomic_json(folder(batch)/'assessment.json',a);return a


def execute(batch):
    require_softagent_runtime();p=read(development.RUN/'prospective_protocol.json');check_protocol(p)
    assert batch in (1,2)
    if batch==2:
        prior=read(folder(1)/'assessment.json');assert prior['continue_batch2'] and prior['protocol_identity']==digest(p),'FROZEN_CONTINUATION_STOP'
    store=Store(folder(batch));new=not store.db.exists()
    grant=dict(grant_id=f'm5campaign-validation-{batch}',batch=batch,protocol_identity=digest(p),budget=development.VALIDATION_LIMITS,
        authorization_source=development.AUTHORIZATION,direct_authorization=read(development.RUN/'direct_chat_authorization.json'),
        future_execution_authorized=True,deepseek_payload_authorized=True)
    if new:
        store.create(dict(project_id=grant['grant_id'],grant_id=grant['grant_id'],budget=grant['budget'],authorization_source=json.dumps(grant['authorization_source'])))
        with store.transaction() as db:
            limits=dict(local_solves=70,prediction_evaluations=12,preview_attempts=2)
            db.execute("INSERT INTO meta VALUES ('diagnostic_work',?)",(encode(dict(limits=limits,used={k:0 for k in limits})),))
        atomic_json(folder(batch)/'grant.json',grant);atomic_json(folder(batch)/'protocol.json',p)
    else:assert read(folder(batch)/'protocol.json')==p and read(folder(batch)/'grant.json')==grant,'VALIDATION_FREEZE_CHANGED'
    hosts=[];configs=[];scenario=p['scenarios'][batch-1]
    provider=deepcopy(read(development.previous.RUN/'freeze.json')['provider_configuration']);provider['protocol_recovery']=dict(max_total=3,max_consecutive=2)
    for i,recipe in enumerate(p['recipes'],1):
        cfg=configuration(p,batch,recipe);cfg['run_id']=f'm5campaign-b{batch}-r{i}'
        cfg['policy'].update(budget=grant['budget'],route=None,allowed_tools=[],tool_bindings={
            'simulation.run':'1.0.0','evaluation.run':'1.0.0','control.profile_report':'1.0.0',RESEARCH.extension_id:RESEARCH.version,'evidence.read':'1.0.0'},
            timeout_s=900.,operation_allowances=EXECUTION_ALLOWANCES,model=deepcopy(provider))
        from tools.platform_models import tool_naming_policy,READABLE_TOOL_NAMING
        cfg['policy']['model']['tool_naming']=tool_naming_policy(cfg['policy']['tool_bindings'],READABLE_TOOL_NAMING)
        h=Host(folder(batch),cfg['run_id']);hosts.append(h);configs.append(cfg)
        with store.connect(True) as db:exists=db.execute('SELECT 1 FROM sessions WHERE run_id=?',(h.run_id,)).fetchone()
        if not exists:h.create(cfg)
        candidate_preparation(h,cfg)
    seal=store.session(hosts[0].run_id)['state'].get('m5_pair_seal')
    if seal is None:
        forecasts=[]
        for i,(h,cfg,recipe) in enumerate(zip(hosts,configs,p['recipes'])):
            if not store.lookup(h.run_id,'campaign-preview'):
                downstream=1980.+600.+180.+60.+1200.*(2-i)
                assert store.remaining()['remaining']['wall_s']>=downstream,'PREVIEW_DOWNSTREAM_RESERVE'
            f=preview(h,cfg,scenario);f['recipe_id']=recipe['recipe_id'];forecasts.append(f)
        seal=seal_pair(store,hosts[0].run_id,p,scenario,forecasts)
    assert store.artifact(seal)['protocol_identity']==digest(p),'SEALED_PROTOCOL_BINDING'
    for h in hosts:
        with store.transaction() as db:
            state=store.session(h.run_id,db)['state'];state['m5_pair_seal']=seal;store.update_state(db,h.run_id,state)
    atomic_json(folder(batch)/'pair_seal.json',dict(reference=seal,decision=store.artifact(seal)['pair_decision']))
    print(json.dumps(dict(batch=batch,phase='both_forecasts_sealed',decision=store.artifact(seal)['pair_decision']['status'])),flush=True)
    for i,(h,cfg) in enumerate(zip(hosts,configs)):
        if not store.lookup(h.run_id,'complete-simulation'):
            assert store.remaining()['remaining']['wall_s']>=990.*(2-i)+600.+90.*(2-i)+60.,'BACKEND_FINALIZATION_RESERVE'
        token=PRE_STEP_OBSERVER.set(checkpoint_observer(h,cfg,seal,p))
        try:result=complete_execution(h,scenario['configuration'],h.run_id)
        finally:PRE_STEP_OBSERVER.reset(token)
        atomic_json(folder(batch)/(h.run_id+'_result.json'),result)
        if result['status']!='evaluated':raise ValueError('INCOMPLETE_EVALUATION_NO_REPLAY')
        print(json.dumps(dict(batch=batch,candidate=h.run_id,phase='evaluated')),flush=True)
    a=assess(batch);h=hosts[0]
    existing=store.session(h.run_id)['state'].get('handoffs',{}).get('m5_interpretation')
    if not existing:
        from tools.platform_diagnosis_coordinator import configure_role,run_until_handoff
        from tools.platform_models import payload_for
        from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
        from examples.gvs_nmpc_route_experiment import load_credential
        prepared=folder(batch)/'interpretation_handoff.json'
        if not prepared.exists():
            with store.transaction() as db:
                state=store.session(h.run_id,db)['state'];state.setdefault('fact_scope',dict(project=store.config()['project_id'],binding=seal));state.setdefault('fact_catalog',{});store.update_state(db,h.run_id,state)
            instructions=('Interpret this completed sealed ranking-only prospective batch. Keep .075/.15 and incumbent unchanged. '
                'Report local direction coverage/correctness, numerical passes and ORIGINAL quantitative errors/tolerances separately (position1e-6 m, vector/speed1e-4 m/s; residual1e-5). '
                'Report ranking coverage/order/false rejection, eligibility errors including false-safe/false-unsafe, exact forecast cost and counterfactual net savings versus ONE rejected complete evaluation. '
                'The economic packet has all receipts so far; this actual native interpretation and any corrections also count and will be reconciled after return. Never invent their future runtime. Actual validation savings are ZERO because both candidates were evaluated. '
                'Batch2 is allowed only after valid complete Batch1, no local holding or full-history false-safe, resolved correct rank, all local numerical checks pass, positive net saving including final research cost, and your explicit CONTINUE_BATCH2. Otherwise readiness must start STOP. Batch2 always ends STOP. '
                'Judge supported diagnostic uses, screening useful/experimental/deferred, when complete evaluation is needed, whether another experiment is justified, and remaining original M5 accuracy/repeatability/real-time failures. '
                'If stopping, give one precise bounded falsifiable next investigation as a recommendation only. No tuning, promotion, milestone closure or reliability claim. '
                'Return one native research.milestone5_preparation call, phase interpretation, holding_weights [.075,.15], rationale, readiness starting STOP or CONTINUE_BATCH2, limitations, next_action finish_stop. About650 words.')
            configure_role(h,'design',instructions,phase='interpretation',delivery_tool=RESEARCH.extension_id,native_store_root=str(folder(batch)),memory_identity=h.run_id,
                native_fixed={},binding=seal,decision_packet=dict(assessment=a,protocol_role=p['role'],hypothesis=p['hypothesis'],
                    continuation=p['continuation_checks'],development_failures=p['role']['original_failures'],batch=batch),
                phase_budget=dict(limit=dict(model_calls=4,tool_calls=4,wall_s=600.),protect_project=dict(wall_s=60.)))
            atomic_json(prepared,payload_for(h,EvidenceDrivenAdapter()))
        load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
        existing=run_until_handoff(h,'m5_interpretation')
    atomic_json(folder(batch)/'interpretation.json',store.artifact(existing));a=assess(batch)
    with store.transaction() as db:
        for h in hosts:
            state=store.session(h.run_id,db)['state'];state['batch_finished']=True;store.update_state(db,h.run_id,state,'stopped')
    atomic_json(folder(batch)/'delivery.json',dict(status='completed_stopped',continue_batch2=a['continue_batch2'],milestone5='open'))
    export(batch)
    print(json.dumps(dict(batch=batch,status='completed_stopped',continue_batch2=a['continue_batch2'],economics=a['economics'],usage=store.remaining()['used'])),flush=True)


def export(batch):
    store=Store(folder(batch))
    if not store.db.exists():return
    dest=evidence(batch);dest.mkdir(parents=True,exist_ok=True)
    with store.connect(True) as db:
        ids=[r[0] for r in db.execute('SELECT run_id FROM sessions')]
        receipts=[json.loads(r[0]) for r in db.execute('SELECT receipt FROM calls WHERE receipt IS NOT NULL')]
        work=json.loads(db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone()[0])
    events=[e for run_id in ids for e in store.events(run_id)];usage=store.remaining()
    sums={k:sum(r['charged'][k] for r in receipts) for k in usage['used']}
    assert all(abs(sums[k]-usage['used'][k])<1e-7 for k in sums)
    atomic_json(folder(batch)/'accounting.json',dict(**usage,numerical_work=work,receipt_charge_sum=sums,
        local_instrumentation_charged='Included once inside simulation receipts',workers=0,subagents=0))
    atomic_json(folder(batch)/'receipts.json',receipts);atomic_json(folder(batch)/'events.json',events)
    for path in folder(batch).glob('*.json'):(dest/path.name).write_bytes(path.read_bytes())
    seen=set()
    def copy(value):
        if isinstance(value,dict):
            if set(value)=={'artifact_id','media_type'} and all(isinstance(v,str) for v in value.values()):
                key=value['artifact_id']
                if key in seen:return
                seen.add(key)
                try:body=store.artifact(value,raw=True)
                except ValueError:return
                target=dest/'artifacts'/(key+('.json' if value['media_type']=='application/json' else '.bin'))
                target.parent.mkdir(exist_ok=True);target.write_bytes(body)
                if value['media_type']=='application/json':copy(json.loads(body))
            else:
                for child in value.values():copy(child)
        elif isinstance(value,list):
            for child in value:copy(child)
    copy(events);copy(receipts)
    (dest/'.gitattributes').write_text('* -text\nartifacts/*.bin -diff\n',encoding='utf8')
    atomic_json(dest/'sha256_manifest.json',{p.relative_to(dest).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(dest.rglob('*')) if p.is_file() and p.name!='sha256_manifest.json'})
    development.check_previous()


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--batch',type=int,choices=(1,2),required=True)
    parser.add_argument('--export',action='store_true');args=parser.parse_args()
    if args.export:export(args.batch)
    else:
        try:execute(args.batch)
        finally:export(args.batch)
