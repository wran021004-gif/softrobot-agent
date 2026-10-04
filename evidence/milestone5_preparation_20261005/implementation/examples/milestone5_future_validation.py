"""Focused two-batch handoff. Default/check paths never compute future forecasts."""
from copy import deepcopy
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from examples import milestone5_preparation as development
from tools.platform_store import Store,plain,encode,zero
from tools.platform_host import Host
from tools.state_io import read,atomic_json,digest
from tools.diagnostic_workflow import save
from tools.batch_budget import batch_requirement,budget_capacity
from tools.execution_completion import complete_execution,EXECUTION_ALLOWANCES
from tools.runtime_identity import require_softagent_runtime
from extensions.tendon_family.control_evidence import PRE_STEP_OBSERVER,ControlEvidence
from extensions.tendon_family.diagnostic_evidence import measured_motion
from extensions.tendon_family.gvs_profile import execution_scope
from extensions.tendon_family.milestone5_preparation import DEFINITION,RESEARCH,history,grid
from extensions.tendon_family.diagnostic_math import charge_units
from extensions.tendon_family.milestone5_protocol import seal_pair,checkpoint_observer,assess_local,assess_screening


def configuration(protocol,batch,recipe):
    scenario=protocol['scenarios'][batch-1];cfg=deepcopy(recipe['configuration'])
    cfg['task']['initializer']=deepcopy(scenario['configuration']['task']['initializer'])
    return cfg


def readiness(protocol):
    from schemas.platform import SessionInput
    current=batch_requirement(2,planning=dict(model_calls=0,tool_calls=0,wall_s=0.),preparation_reserve_s=5.)
    checks=dict(concrete_scenarios=len(protocol['scenarios'])==2,concrete_recipes=len(protocol['recipes'])==2,
        public_reservations_unchanged=current==protocol['reservations']['batch1']['public_base'],
        numerical_reference_stable=protocol['local_reference_stable'],
        research_pair_selected=protocol.get('research_pair_selected',True),
        production_controller=True,grid_alignment=True,
        implementation_identity=all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha for name,sha in protocol['implementation_identity']['files'].items()))
    for batch in (1,2):
        for recipe in protocol['recipes']:
            cfg=configuration(protocol,batch,recipe);inp=SessionInput.model_validate(cfg)
            checks['production_controller'] &= inp.policy.controller.version=='7.0.0'
            checks['grid_alignment'] &= len(grid(cfg))==35 and inp.task.timing.control_period_s==.01
    return dict(checks=checks,passed=all(checks.values()),backend_evaluations=0,backend_steps=0,
        prospective_forecasts_generated=0,classification='static no-execution readiness, not scientific validation')


def candidate_preparation(host,cfg):
    """Same public candidate.apply reservation pattern used by platform_search."""
    request='prepare-candidate';old=host.store.lookup(host.run_id,request)
    if old:
        if not old['receipt']:raise ValueError('UNRESOLVED_PREPARATION_NO_REPLAY')
        return json.loads(old['receipt'])
    reservation,_=host.store.reserve(host.run_id,request,digest(cfg),host.actor,{**zero(),'tool_calls':1,'wall_s':5.})
    start=time.monotonic()
    from schemas.platform import SessionInput,CandidateInput
    from tools.platform_tools import _candidate
    inp=SessionInput.model_validate(cfg);effective=_candidate(inp,{},host.reg)
    prepared=CandidateInput(candidate_id=host.run_id,baseline_identity=digest(cfg),builder=inp.policy.candidate_builder.extension_id,
        builder_version=inp.policy.candidate_builder.version,changes={},allowed=inp.policy.editable,effective=effective,content_identity=digest(plain(effective)))
    return host.store.complete(reservation,dict(request_id=request,execution_id=reservation['execution_id'],caller=host.actor,
        tool_id='candidate.apply',tool_version='1.0.0',execution_status='completed',charged=zero()),
        dict(configuration=plain(prepared),classification='frozen candidate preparation'),time.monotonic()-start)


def future_preview(host,cfg,scenario):
    path=host.store.root/(host.run_id+'_preview_receipt.json');old=host.store.lookup(host.run_id,'future-preview')
    if old:
        if not old['receipt']:raise ValueError('UNRESOLVED_PREVIEW_NO_REPLAY')
        receipt=json.loads(old['receipt'])
        if receipt['execution_status']!='completed':raise ValueError('FAILED_PREVIEW_NO_REPLAY')
        return host.store.artifact(receipt['output'])
    reservation,_=host.store.reserve(host.run_id,'future-preview',digest(dict(configuration=cfg,scenario=scenario['scenario_id'])),host.actor,
        {**zero(),'tool_calls':1,'wall_s':1500.})
    context=SimpleContext(host,reservation);charge_units(context,'preview_attempts',1);start=time.monotonic()
    try:
        result=history(cfg,scenario['reduced_initial_state'],lambda:charge_units(context,'local_solves',1),deadline=time.perf_counter()+1500.,
            save_update=lambda row:context.save_artifact(row,'future_preview_update_completed'))
        result.update(classification='prospective pre-execution own-history forecast',scenario_id=scenario['scenario_id'],candidate_id=host.run_id,
            scientific_identity=digest(execution_scope(cfg)),configuration=cfg)
        receipt=host.store.complete(reservation,dict(request_id='future-preview',execution_id=reservation['execution_id'],caller=host.actor,
            tool_id='analysis.milestone5_preparation',tool_version='1.0.0',execution_status='completed',charged=zero()),result,time.monotonic()-start)
        atomic_json(path,receipt);return host.store.artifact(receipt['output'])
    except Exception as exc:
        receipt=host.store.complete(reservation,dict(request_id='future-preview',execution_id=reservation['execution_id'],caller=host.actor,
            tool_id='analysis.milestone5_preparation',tool_version='1.0.0',execution_status='failed',error=dict(type=type(exc).__name__,message=str(exc)),charged=zero()),
            dict(error=str(exc),complete=False),time.monotonic()-start)
        atomic_json(path,receipt);raise


class SimpleContext:
    """Only the fields required by existing charge_units; no additional workflow."""
    def __init__(self,host,row):self.host=host;self.store=host.store;self.run_id=host.run_id;self.row=row
    def save_artifact(self,value,kind):
        with self.store.transaction() as db:
            ref=self.store.put(db,value);self.store.event(db,self.run_id,kind,'saved',request=self.row['request_id'],outputs=[ref]);return ref


def execute(protocol,batch,grant_path):
    require_softagent_runtime();check=readiness(protocol)
    if not check['passed']:raise ValueError('NOT_READY: '+str(check['checks']))
    grant=read(grant_path)
    if not grant.get('future_execution_authorized') or grant.get('protocol_identity')!=digest(protocol) or grant.get('batch')!=batch:
        raise ValueError('SEPARATE_MATCHING_FUTURE_AUTHORIZATION_REQUIRED')
    if not grant.get('deepseek_payload_authorized'):raise ValueError('FUTURE_INTERPRETATION_TRANSMISSION_AUTHORIZATION_REQUIRED')
    required=protocol['reservations']['batch'+str(batch)]['complete_requirement']
    if any(grant['budget'].get(k,0)<v for k,v in required.items()):raise ValueError('BATCH_RESERVATION_SHORTFALL')
    if batch==2:
        prior=read(ROOT/'evidence/milestone5_future_batch1/assessment.json')
        if not prior['continue_batch2'] or prior['protocol_identity']!=digest(protocol):raise ValueError('FROZEN_CONTINUATION_STOP')
    folder=ROOT/('runs/milestone5_future_batch'+str(batch));evidence=ROOT/('evidence/milestone5_future_batch'+str(batch));evidence.mkdir(parents=True,exist_ok=True)
    store=Store(folder);new=not store.db.exists()
    if new:
        store.create(dict(project_id='m5-future-batch'+str(batch),grant_id=grant['grant_id'],budget=grant['budget'],authorization_source=grant['authorization_source']))
        with store.transaction() as db:db.execute("INSERT INTO meta VALUES ('diagnostic_work',?)",(encode(dict(limits=dict(local_solves=70,prediction_evaluations=0,preview_attempts=2),used=dict(local_solves=0,prediction_evaluations=0,preview_attempts=0))),))
        atomic_json(folder/'grant.json',grant);atomic_json(folder/'protocol.json',protocol)
    elif read(folder/'grant.json')!=grant or read(folder/'protocol.json')!=protocol:raise ValueError('FUTURE_STAGE_FREEZE_CHANGED')
    scenario=protocol['scenarios'][batch-1];hosts=[];configs=[];forecasts=[]
    for i,recipe in enumerate(protocol['recipes']):
        cfg=configuration(protocol,batch,recipe);cfg['run_id']='m5future-b'+str(batch)+'-r'+str(i+1)
        cfg['policy'].update(budget=grant['budget'],route=None,allowed_tools=[],tool_bindings={
            'simulation.run':'1.0.0','evaluation.run':'1.0.0','control.profile_report':'1.0.0',RESEARCH.extension_id:RESEARCH.version,'evidence.read':'1.0.0'},
            timeout_s=900.,operation_allowances=EXECUTION_ALLOWANCES,model=deepcopy(read(development.RUN/'freeze.json')['provider_configuration']))
        from tools.platform_models import tool_naming_policy,READABLE_TOOL_NAMING
        cfg['policy']['model']['tool_naming']=tool_naming_policy(cfg['policy']['tool_bindings'],READABLE_TOOL_NAMING)
        h=Host(folder,cfg['run_id']);hosts.append(h);configs.append(cfg)
        if new:h.create(cfg)
        candidate_preparation(h,cfg)
    seal=store.session(hosts[0].run_id)['state'].get('m5_pair_seal')
    if not seal:
        # Complete two previews before either backend; reserve downstream using authoritative floors.
        need=batch_requirement(2,planning=dict(model_calls=0,tool_calls=0,wall_s=0.),preparation_reserve_s=0.)['requirement']['wall_s']+180+60
        for h,cfg,recipe in zip(hosts,configs,protocol['recipes']):
            if store.remaining()['remaining']['wall_s']<1500+need:raise ValueError('PREVIEW_DOWNSTREAM_RESERVE_SHORTFALL')
            f=future_preview(h,cfg,scenario);f['recipe_id']=recipe['recipe_id'];forecasts.append(f)
        seal=seal_pair(store,hosts[0].run_id,protocol,scenario,forecasts)
        for h in hosts[1:]:
            with store.transaction() as db:
                state=store.session(h.run_id,db)['state'];state['m5_pair_seal']=seal;store.update_state(db,h.run_id,state)
    sealed=store.artifact(seal);outcomes=[];local=[];backend_updates=[];complete_cost=0.
    if sealed['protocol_identity']!=digest(protocol):raise ValueError('SEALED_PROTOCOL_BINDING')
    for h,cfg in zip(hosts,configs):
        if not store.lookup(h.run_id,'complete-simulation') and store.remaining()['remaining']['wall_s']<990+600+60:raise ValueError('BACKEND_EXPORT_RESERVE_SHORTFALL')
        token=PRE_STEP_OBSERVER.set(checkpoint_observer(store,h.run_id,cfg,seal,protocol))
        try:result=complete_execution(h,protocol['scenarios'][batch-1]['configuration'],h.run_id)
        finally:PRE_STEP_OBSERVER.reset(token)
        atomic_json(folder/(h.run_id+'_result.json'),result)
        if result['status']!='evaluated':raise ValueError('INCOMPLETE_EVALUATION_NO_REPLAY')
        feedback=result['structured_feedback'];outcomes.append(dict(candidate_id=h.run_id,holding_max_speed_m_s=feedback['holding']['max_speed_m_s'],
            holding_max_error_m=feedback['holding']['max_position_error_m'],joint_acceptance=feedback['joint_reach_holding_success']))
        complete_cost+=sum(r['charged']['wall_s'] for r in result['receipts'].values())
        reader=ControlEvidence(store);source=reader.resolve(result['execution_id']);motion=measured_motion(reader,source)
        backend_updates.append(len(reader.read_file(source,'controller_observations.json')))
        for event in store.events(h.run_id):
            if event['kind']!='m5_local_prediction':continue
            prediction=store.artifact(event['outputs'][0]);observed=next(m for m in motion if abs(m['time_s']-prediction['end_s'])<1e-9)
            observed['target_m']=cfg['task']['goal']['data']['target_m']
            uncertainty=prediction['numerical_uncertainty']['speed_m_s']
            local.append(dict(candidate_id=h.run_id,prediction=prediction,score=assess_local(prediction,observed,uncertainty),seal_sequence=event['sequence']))
    if len(local)!=4:raise ValueError('LOCAL_CHECKPOINT_COVERAGE_INCOMPLETE')
    preview_cost=sum(f['complete_cost_s'] for f in sealed['forecasts']);screening=assess_screening(sealed['pair_decision'],outcomes,preview_cost,complete_cost)
    assessment=dict(protocol_identity=digest(protocol),batch=batch,local=local,screening=screening,outcomes=outcomes,
        preview_controller_solves=70,backend_controller_solves=sum(backend_updates),total_controller_attempts=70+sum(backend_updates),
        continue_batch2=not screening['predicted_safe_observed_violating'] and not any(r['score']['physical_holding_false_safe'] for r in local)
            and all(r['prediction']['numerical_stable'] for r in local))
    resolved=sum(r['score']['direction_verdict']!='unresolved' for r in local)
    assessment['local_summary']=dict(planned=4,resolved=resolved,resolved_coverage=resolved/4,
        direction_accuracy_among_resolved=None if not resolved else sum(r['score']['direction_verdict']=='correct' for r in local)/resolved,
        speed_endpoint_passes=sum(r['score']['endpoint_within_tolerance'] for r in local),
        vector_endpoint_passes=sum(r['score']['vector_within_tolerance'] for r in local),
        physical_holding_false_safe=sum(r['score']['physical_holding_false_safe'] for r in local),
        separate_threshold_diagnostics=[dict(start_s=r['prediction']['start_s'],scope=r['score']['threshold_scope'],speed_false_safe=r['score']['speed_false_safe'],position_false_safe=r['score']['position_false_safe']) for r in local],
        accuracy_is_not_screening_usefulness=True)
    atomic_json(evidence/'assessment.json',assessment)
    # One actual interpretation request plus protected correction/recovery slots; no planning request here.
    from tools.platform_diagnosis_coordinator import configure_role,run_until_handoff
    from tools.platform_models import payload_for
    from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']));h=hosts[0]
    with store.transaction() as db:
        state=store.session(h.run_id,db)['state'];state.setdefault('fact_scope',dict(project=store.config()['project_id'],binding=seal));state.setdefault('fact_catalog',{});store.update_state(db,h.run_id,state)
    configure_role(h,'design','Interpret the completed sealed local and screening evidence. Keep the two frozen weights, incumbent and acceptance unchanged. State coverage, errors, false-safe/false-rejection, abstention, cost and limitations. Return research.milestone5_preparation with phase=interpretation, readiness, rationale, limitations and next_action=finish_stop. Do not tune Batch2 or claim M5 closure.',
        phase='interpretation',delivery_tool=RESEARCH.extension_id,native_store_root=str(folder),memory_identity=h.run_id,native_fixed={},binding=seal,
        decision_packet={**assessment,'selected_weights':[r['holding_weight'] for r in protocol['recipes']]},phase_budget=dict(limit=dict(model_calls=4,tool_calls=4,wall_s=600.)))
    atomic_json(evidence/'interpretation_handoff.json',payload_for(h,EvidenceDrivenAdapter()))
    previous=store.session(h.run_id)['state'].get('handoffs',{}).get('m5_interpretation')
    ref=previous or run_until_handoff(h,'m5_interpretation');atomic_json(evidence/'interpretation.json',store.artifact(ref))
    atomic_json(evidence/'accounting.json',store.remaining())
    for p in folder.glob('*.json'):(evidence/p.name).write_bytes(p.read_bytes())
    print(json.dumps(dict(status='completed_stopped',batch=batch,continue_batch2=assessment['continue_batch2'],usage=store.remaining()['used']),indent=2))


def export_future(batch):
    """Receipt recovery exports completed work even when interpretation/next work fails."""
    folder=ROOT/('runs/milestone5_future_batch'+str(batch));store=Store(folder)
    if not store.db.exists():return
    evidence=ROOT/('evidence/milestone5_future_batch'+str(batch));evidence.mkdir(parents=True,exist_ok=True)
    with store.connect(True) as db:
        ids=[r[0] for r in db.execute('SELECT run_id FROM sessions')]
        receipts=[json.loads(r[0]) for r in db.execute('SELECT receipt FROM calls WHERE receipt IS NOT NULL')]
    events=[e for run in ids for e in store.events(run)]
    atomic_json(evidence/'events.json',events);atomic_json(evidence/'receipts.json',receipts);atomic_json(evidence/'accounting.json',store.remaining())
    refs={}
    def collect(value):
        if isinstance(value,dict):
            if set(value)=={'artifact_id','media_type'}:refs[value['artifact_id']]=value
            else:
                for child in value.values():collect(child)
        elif isinstance(value,list):
            for child in value:collect(child)
    collect(events);collect(receipts);artifacts=evidence/'artifacts';artifacts.mkdir(parents=True,exist_ok=True)
    for sha,ref in refs.items():(artifacts/(sha+('.json' if ref['media_type']=='application/json' else '.bin'))).write_bytes(store.artifact(ref,raw=True))
    for p in folder.glob('*.json'):(evidence/p.name).write_bytes(p.read_bytes())
    atomic_json(evidence/'sha256_manifest.json',{p.relative_to(evidence).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(evidence.rglob('*')) if p.is_file() and p.name!='sha256_manifest.json'})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--protocol',type=Path,default=development.EVIDENCE/'protocol.json');parser.add_argument('--batch',type=int,choices=(1,2),default=1)
    parser.add_argument('--check',action='store_true');parser.add_argument('--execute',action='store_true');parser.add_argument('--grant',type=Path)
    args=parser.parse_args();protocol=read(args.protocol)
    if args.execute:
        if args.grant is None:parser.error('--execute requires a separately authorized --grant file')
        try:execute(protocol,args.batch,args.grant)
        finally:export_future(args.batch)
    else:print(json.dumps(readiness(protocol),indent=2))
