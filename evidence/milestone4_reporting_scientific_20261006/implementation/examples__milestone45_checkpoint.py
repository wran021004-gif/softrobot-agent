"""Separately granted M4 factual correction and M5 matched development study.

Never resumes a stopped scientific campaign or spends formal validation slots.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import os
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from tools.state_io import read,atomic_json,digest
from tools.platform_store import Store,zero,encode
from tools.platform_host import Host
from examples.milestone5_future_validation import SimpleContext

AUTH='User goal-objective.md attachment 055b3f5e-16ac-41ac-85e9-b98f7a6624f0, 2026-10-06; separate bounded M4 reporting and M5 development grants, real DeepSeek/numerical/backend execution and normal publication authorized.'
M4=ROOT/'runs/milestone4_reporting_20261006';M5=ROOT/'runs/milestone5_matched_20261006'
E4=ROOT/'evidence/milestone4_reporting_20261006';E5=ROOT/'evidence/milestone5_matched_20261006'
OLD4=ROOT/'evidence/milestone4_autonomous_20261006'
LIMIT4=dict(model_calls=3,tool_calls=12,backend_solves=0,worker_calls=0,wall_s=1200.)
LIMIT5=dict(model_calls=8,tool_calls=60,backend_solves=4,worker_calls=0,wall_s=12000.)


def hashes(paths):return {str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def scope(root):
    limit=LIMIT4 if root==M4 else LIMIT5
    store=Store(root)
    if not store.db.exists():
        store.create(dict(project_id=root.name,grant_id=root.name,budget=limit,authorization_source=AUTH))
        if root==M5:
            with store.transaction() as db:db.execute("INSERT INTO meta VALUES ('diagnostic_work',?)",(encode(dict(
                limits=dict(local_solves=160,preview_attempts=4,component_evaluations=12,prediction_evaluations=12),
                used=dict(local_solves=0,preview_attempts=0,component_evaluations=0,prediction_evaluations=0))),))
    return store


def host(root,name,cfg=None):
    from examples.milestone5_fullscope import source
    from tools.execution_completion import EXECUTION_ALLOWANCES
    store=scope(root);h=Host(root,name)
    with store.connect(True) as db:exists=db.execute('SELECT 1 FROM sessions WHERE run_id=?',(name,)).fetchone()
    if not exists:
        cfg=deepcopy(cfg or source('original075')[1]['configuration']);cfg['run_id']=name
        cfg['policy'].update(budget=LIMIT4 if root==M4 else LIMIT5,route=None,allowed_tools=[],
            tool_bindings={k:'1.0.0' for k in EXECUTION_ALLOWANCES},timeout_s=1200.,
            operation_allowances={**EXECUTION_ALLOWANCES,'simulation.run':dict(timeout_s=1200.,reserve_s=1200.)})
        h.create(cfg)
    return h


def operation(root,name,fn,reserve_s,model=False):
    h=host(root,root.name+'-report');old=h.store.lookup(h.run_id,name)
    if old:
        if not old['receipt']:raise ValueError('PENDING_NO_REPLAY')
        receipt=json.loads(old['receipt'])
        if receipt['execution_status']!='completed':raise ValueError('FAILED_ATTEMPT_NO_REPLAY')
        return h.store.artifact(receipt['output'])
    if (root/'checkpoint_seal.json').exists():raise ValueError('CHECKPOINT_SEALED_NO_NEW_WORK')
    if root==M5 and h.store.remaining()['remaining']['wall_s']<reserve_s+1200.:raise ValueError('FINAL_DELIVERY_RESERVED')
    row,_=h.store.reserve(h.run_id,name,digest(dict(operation=name)),h.actor,
        {**zero(),('model_calls' if model else 'tool_calls'):1,'wall_s':reserve_s})
    started=time.monotonic();error=None
    try:result=fn(SimpleContext(h,row));status='completed'
    except Exception as exc:
        status='failed';error=dict(type=type(exc).__name__,message=str(exc));result=dict(error=error,
            provider_response=getattr(exc,'provider_response',None))
    elapsed=time.monotonic()-started
    atomic_json(root/(name+'_pending.json'),dict(result=result,status=status,error=error,elapsed_s=elapsed))
    receipt=h.store.complete(row,dict(request_id=name,execution_id=row['execution_id'],caller=h.actor,
        tool_id='model.deepseek' if model else 'analysis.matched_checkpoint',tool_version='1.0.0',
        execution_status=status,charged=zero(),error=json.dumps(error) if error else None),result,elapsed)
    atomic_json(root/(name+'.json'),result);atomic_json(root/(name+'_receipt.json'),receipt)
    print(json.dumps(dict(operation=name,status=status,charged=receipt['charged'])),flush=True)
    if error:raise RuntimeError(error)
    return result


def reporting_payload(config,packet,instructions):
    """The already successful thinking-enabled reporting client parameters."""
    payload=dict(model=config['model'],max_tokens=config['max_tokens'],thinking={'type':config['thinking']},
        reasoning_effort=config['reasoning_effort'],messages=[dict(role='system',content=instructions),
            dict(role='user',content=json.dumps(packet,ensure_ascii=False))],
        tools=[dict(type='function',function=dict(name='report_interpretation',description='Submit the evidence-grounded report, with no scientific execution action.',
            parameters=dict(type='object',properties=dict(report=dict(type='string'),recommendation=dict(type='string'),
                unresolved=dict(type='array',items=dict(type='string'))),required=['report','recommendation','unresolved'],additionalProperties=False)))],
        stream=False)
    if len(encode(payload).encode())>config['context_bytes']:raise ValueError('CONTEXT_BYTES_LIMIT')
    if len(encode(payload).encode())+config['max_tokens']+config['context_guard']['framing_headroom_tokens']>config['context_guard']['context_limit_tokens']:
        raise ValueError('CONTEXT_TOKEN_GUARD')
    return payload


def provider(root,name,packet,instructions):
    from examples.gvs_nmpc_route_experiment import load_credential
    from tools.model_transports.deepseek import request_completion
    config=read(OLD4/'freeze.json')['provider_configuration']
    payload=reporting_payload(config,packet,instructions)
    atomic_json(root/(name+'_request.json'),dict(provider_configuration=config,payload=payload))
    def call(ctx):
        load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
        raw=request_completion(config,payload,os.environ['DEEPSEEK_API_KEY'])
        atomic_json(root/(name+'_raw.json'),raw)
        choice=raw['choices'][0]
        if choice.get('finish_reason')=='length':raise ValueError('MODEL_RESPONSE_LENGTH_TRUNCATED')
        calls=choice['message'].get('tool_calls',[])
        if len(calls)!=1 or calls[0]['function']['name']!='report_interpretation':raise ValueError('ONE_REPORT_TOOL_REQUIRED')
        report=json.loads(calls[0]['function']['arguments'])
        if set(report)!={'report','recommendation','unresolved'}:raise ValueError('REPORT_FIELDS_REQUIRED')
        return dict(model_authored=True,interpretation=report,raw=raw,request_identity=digest(payload))
    return operation(root,name,call,config['timeout_s'],model=True)


def m4_summary(ctx):
    from tools.study_history import reporting_summary
    a=read(OLD4/'acceptance_audit.json');s=read(OLD4/'scheduler_state.json');request=read(OLD4/'round2_request.json')
    p=request['packet'];ids=[r['candidate']['execution_id'] for r in p['history']['rows'][-4:]]
    summary=reporting_summary(p['history'],new_execution_ids=ids,
        replication_pairs=[('1ffdcbc4f93f4dc4bb16a807c7b4056b','9af9c7a3d6d84751ab0c1ebacd73d0f8')],
        selected=s['selected'],latest=s['latest'],usage=a['usage'],stop=dict(status=s['status'],reason=s['stop_reason'],sealed=True))
    summary['batch_count']=len(a['cases']['primary']['batches']) if isinstance(a['cases'],dict) and 'batches' in a['cases'].get('primary',{}) else 2
    original_store=Store(ROOT/'runs/milestone4_autonomous_20261006')
    with original_store.connect(True) as db:row=db.execute("SELECT * FROM calls WHERE request_id='model-2'").fetchone()
    original=original_store.artifact(json.loads(row['receipt'])['output'])
    # Inspect the actually sent serialized payload, not a reconstructed context.
    text=json.dumps(request['payload'],ensure_ascii=False)
    members=[r for r in p['history']['rows'] if r['candidate']['execution_id'] in ('1ffdcbc4f93f4dc4bb16a807c7b4056b','9af9c7a3d6d84751ab0c1ebacd73d0f8')]
    support=dict(both_execution_ids_present=all(r['candidate']['execution_id'] in text for r in members),
        both_metric_triples_present=all(str(r['metrics'][k]) in text for r in members for k in ('terminal_error_m','holding_max_error_m','holding_max_speed_m_s')),
        explicit_replication_label_present='replicat' in text.lower(),payload_identity=digest(request['payload']),
        diagnosis='Saved final request includes both execution identities and their exact measured triples. The denial contradicts available context; this record cannot establish the model internal cause. A compact explicit comparison removes reporting ambiguity.')
    return dict(summary=summary,original_response=original,request_inspection=support,
        original_sealed_hashes=hashes([OLD4/'acceptance_audit.json',OLD4/'scheduler_state.json',OLD4/'round2_request.json']),
        contradictions=a['interpretation_review'],supersedes_only='final factual interpretation; not original stop, selection or audit')


def m4():
    packet=operation(M4,'factual_summary',m4_summary,30.)
    if os.environ.get('CHECKPOINT_PROVIDER_RETRY'):
        return provider(M4,'correction'+os.environ['CHECKPOINT_PROVIDER_RETRY'],packet,read(M4/'correction0_request.json')['payload']['messages'][0]['content'])
    provider(M4,'correction0',packet,'You are the configured research model correcting a stopped campaign final factual report. Produce a compact evidence-grounded interpretation. Explicitly acknowledge the one matching .09/.05 replication and distinguish it from broad repeatability/variance/full-trajectory/timing claims. Correct the frozen historical passing configurations 0/.05 and .05/.05 on shortened geometry. Describe the new .09/.10 pass as improved holding speed but worsened position against the retained incumbent. Separate observations from solver/dynamics hypotheses. Preserve selected execution and latest distinction. Four-backend capacity is exhausted; final reporting remains affordable. Preserve the original STOP; request or advertise no new scientific actions. Do not claim realtime, general superiority or unique causality. Your correction is post-run intervention, never retroactive first-pass success. Use report_interpretation once.')


def freeze():
    from examples.milestone5_fullscope import source
    from examples.milestone5_successor import RUN as successor
    from extensions.tendon_family.gvs_profile import execution_scope
    from extensions.tendon_family.milestone5_protocol import RULES
    scope(M5)
    path=M5/'protocol.json'
    if path.exists():return read(path)
    cases=[]
    for name in ('original075','original15'):
        r,s=source(name);cfg=s['configuration'];scene=r.read_file(s,'experiment_scene.json')
        cases.append(dict(name=name,source_execution_id=s['execution_id'],source_manifest=s['manifest'],
            configuration=cfg,scientific_identity=digest(execution_scope(cfg)),
            initial_full_state=scene['qpos_rad']+scene['qvel_rad_s'],initial_time_s=0.,
            physics=r.read_file(s,'resolved_physics.json'),compiled=r.read_file(s,'compiled_physics.json'),
            xml=r.store.artifact(s['files']['robot.xml'],raw=True).decode('utf8')))
    kernel=read(successor/'native_full_chunked.json')['kernel']
    if not Path(kernel['library']).exists():raise ValueError('MISSING_NATIVE_LIBRARY_EXACT_REBUILD_REQUIRED')
    if hashlib.sha256(Path(kernel['library']).read_bytes()).hexdigest()!=kernel['library_sha256']:raise ValueError('NATIVE_LIBRARY_HASH_MISMATCH')
    paths=[ROOT/p for p in ('examples/milestone45_checkpoint.py','extensions/tendon_family/milestone5_feedback_runtime.py',
        'extensions/tendon_family/gvs_nmpc.py','extensions/tendon_family/gvs_trajectory.py','extensions/tendon_family/backends.py',
        'extensions/tendon_family/milestone5_fullstate.py','extensions/tendon_family/milestone5_fixed_transition.py')]
    implementation=dict(version='native_exact_every_update_matched@1.0.0',kernel=kernel,files=hashes(paths),
        default_controller_unchanged=True,provider_scope='Only with use_trajectory_functions(provider) in these development executions')
    plan=dict(version='m5_full_trajectory_matched@1.0.0',authorization=AUTH,allocation=LIMIT5,
        numerical_limits=dict(standalone_controller_attempts=160,complete_forecasts=4,component_evaluations=12),
        candidates=cases,implementation=implementation,implementation_identity=digest(implementation),
        original_rules=RULES,thresholds=read(successor/'plan.json')['thresholds'],
        local_numerical_protocol=read(successor/'fixed_target_protocol.json'),
        local_numerical_support=dict(source=str(successor/'fixed_target.json'),identity=digest(read(successor/'fixed_target.json')),
            scope='Six existing development local cases passed fixed_backend_transition_validation@2.0.0. Not a full-trajectory error bound.',
            historical_continuous_and_step_refinement_failures_preserved=True),
        comparison=dict(time_origin_s=0.,duration_s=.35,update_period_s=.01,physical_step_s=.0005,
            output_timestamps=[i*.01 for i in range(1,36)],holding_timestamps=[i*.01 for i in range(30,36)],
            projection='Same gvs_projection.project structural_linear map in forecast and backend; full 48 joint positions/rates retained by propagation.',
            output='World tip site position; Jacobian times full serial joint rates for translational velocity.',
            initialization='Same declared candidate full state; prepare_execution compatible historical tensions only; regenerate states, own previous input and plan; no future state/commands/stopping iterations.',
            replanning='Every update; same DeadlineReachNMPCController and provider, full unchanged objective/constraints/tolerances/timed stop.',
            seal='Both complete forecasts, classifications and pair decision before ANY new backend reservation or result read.',
            accuracy='Original absolute 1e-6 m position and 1e-4 m/s speed/vector tolerances, per sample and terminal/holding aggregates; original feasibility and ranking rules unchanged.',
            caveat='Wall-time stopping can select different iterations; no deterministic stopping replacement.'),
        costs=dict(forecast='Outer receipts include preparation/native loading/controller configure/every observation, solve, packaging, evidence export and propagation.',
            software_interval='Direct perf_counter from forecast full-state projection/output preparation through packaged command; full state already supplied. Software only, no sensor/hardware guarantee.',
            backend_interval='Existing direct update timer begins before current() and projection, ends after controller.command; actuator application and physics timed separately through total backend cost. No claim of hardware end-to-end timing.',
            cold='Reuse identity-checked installed DLL, no compilation now. Cold compile increment uses measured 599.7569169001654 s for THIS exact structure only.',
            economics='Forecast pair plus required model interpretation/corrections compared with one corresponding measured backend evaluation/profile. Both backends executed so actual savings/exclusions zero.'),
        protected_validation=read(ROOT/'evidence/milestone5_successor_20261005/accounting.json')['protected_validation'],
        incumbent=read(successor/'plan.json')['incumbent'],engineering_repair_episodes=0,workers=0,subagents=0)
    atomic_json(path,plan);atomic_json(M5/'protocol_seal.json',dict(identity=digest(plan),before_forecasts_and_backends=True))
    return plan


def native_provider():
    from examples.milestone5_successor import reference_functions
    from extensions.tendon_family.milestone5_feedback_runtime import NativeFunctions
    start=time.perf_counter();p=read(M5/'protocol.json');k=p['implementation']['kernel']
    provider=NativeFunctions(reference_functions(),k['library'],library_sha256=k['library_sha256'])
    return provider,time.perf_counter()-start


def forecast(name):
    p=read(M5/'protocol.json');case=next(c for c in p['candidates'] if c['name']==name)
    def calculate(ctx):
        from extensions.tendon_family.milestone5_feedback_runtime import history
        from extensions.tendon_family.milestone5_fullstate import DiscreteFullState
        from extensions.tendon_family.diagnostic_math import charge_units
        charge_units(ctx,'preview_attempts',1);start=time.perf_counter();provider,loading=native_provider()
        model=DiscreteFullState(case['configuration'],case['physics'],case['compiled'],case['xml'])
        model_setup=model.setup_s
        def save(row):
            ctx.save_artifact(dict(candidate=name,**row),'matched_forecast_update')
            if row['phase']=='emulated_endpoint':print(json.dumps(dict(candidate=name,update=row['update_id'],command_s=row['complete_command_s'],error_m=row['error_m'])),flush=True)
        result=history(case['configuration'],case['initial_full_state'],model,case['physics'],ctx,
            provider=provider,count=35,deadline=time.perf_counter()+1100.,save_update=save)
        holding=[r for r in result['rows'] if .3-1e-9<=r['endpoint_s']<=.35+1e-9]
        result.update(candidate_id=name,implementation_identity=p['implementation_identity'],
            scientific_identity=case['scientific_identity'],native_loading_s=loading,model_setup_s=model_setup,
            metrics=dict(terminal_error_m=result['rows'][-1]['error_m'],holding_max_error_m=max(r['error_m'] for r in holding),
                holding_max_speed_m_s=max(r['speed_m_s'] for r in holding)),
            holding_sample_times_s=[r['endpoint_s'] for r in holding],outer_total_s=time.perf_counter()-start)
        result['classification']=classification(result['metrics'])
        return result
    return operation(M5,'forecast_'+name,calculate,1200.)


def classification(m):
    terminal=m['terminal_error_m']<=.01;position=m['holding_max_error_m']<=.01;speed=m['holding_max_speed_m_s']<=.02
    return dict(terminal_position=terminal,holding_position=position,holding_speed=speed,joint=terminal and position and speed)


def seal_forecasts():
    from extensions.tendon_family.milestone5_protocol import pair_decision
    def seal(ctx):
        p=read(M5/'protocol.json');forecasts=[read(M5/('forecast_'+c['name']+'.json')) for c in p['candidates']]
        if not all(f['complete'] and f['implementation_identity']==p['implementation_identity'] and len(f['rows'])==35 for f in forecasts):raise ValueError('BOTH_COMPLETE_MATCHED_FORECASTS_REQUIRED')
        with ctx.store.connect(True) as db:
            if db.execute("SELECT COUNT(*) FROM calls WHERE request_id='complete-simulation'").fetchone()[0]:raise ValueError('BACKEND_BEFORE_PAIR_SEAL')
        return dict(protocol_identity=digest(p),implementation_identity=p['implementation_identity'],
            forecasts={f['candidate_id']:dict(identity=digest(f),metrics=f['metrics'],classification=f['classification']) for f in forecasts},
            pair_decision=pair_decision(forecasts),sealed_before_either_backend=True)
    return operation(M5,'pair_seal',seal,30.)


def backend(name):
    from tools.execution_completion import complete_execution
    from examples.milestone5_future_validation import candidate_preparation
    from extensions.tendon_family.gvs_trajectory import use_trajectory_functions
    from extensions.tendon_family.control_evidence import ControlEvidence
    p=read(M5/'protocol.json');seal=read(M5/'pair_seal.json');case=next(c for c in p['candidates'] if c['name']==name)
    saved=M5/('backend_'+name+'.json')
    if saved.exists():
        value=read(saved)
        if value['status']=='evaluated' and value['implementation_identity']==p['implementation_identity']:
            return value
        raise ValueError('RETAINED_BACKEND_ATTEMPT_NO_REPLAY')
    if seal['protocol_identity']!=digest(p):raise ValueError('PAIR_SEAL_SCOPE')
    for other in p['candidates']:
        if seal['forecasts'][other['name']]['identity']!=digest(read(M5/('forecast_'+other['name']+'.json'))):raise ValueError('FORECAST_CHANGED_AFTER_SEAL')
    cfg=deepcopy(case['configuration']);h=host(M5,'matched-'+name,cfg)
    candidate_preparation(h,h.store.session(h.run_id)['snapshot']['input'])
    holder={}
    def load(ctx):
        holder['provider'],loading=native_provider()
        return dict(native_loading_s=loading,implementation_identity=p['implementation_identity'])
    loading_record=operation(M5,'backend_loading_'+name,load,30.)
    if 'provider' not in holder:
        loading_record=operation(M5,'backend_resume_loading_'+name,load,30.)
    provider=holder['provider'];loading=loading_record['native_loading_s']
    start=time.perf_counter()
    from extensions.tendon_family.control_evidence import PRE_STEP_OBSERVER
    captured=[]
    def capture(i,t,controller,geometry,velocity,actual):
        selected=controller.workspace.last
        captured.append(dict(update_id=i,time_s=t,input_n=list(actual),
            projected_current_state=controller.observations[-1]['measured_initial_state'],
            selected_plan={k:deepcopy(selected[k]) for k in ('states','tensions')},
            plan_identity=digest({k:selected[k] for k in ('states','tensions')})))
        if i%5==0:print(json.dumps(dict(candidate=name,backend_update=i)),flush=True)
    token=PRE_STEP_OBSERVER.set(capture)
    try:
        with use_trajectory_functions(provider):result=complete_execution(h,case['configuration'],h.run_id)
    finally:PRE_STEP_OBSERVER.reset(token)
    result.update(candidate=name,implementation_identity=p['implementation_identity'],pair_seal_identity=digest(seal),native_loading_s=loading,
        completion_wrapper_s=time.perf_counter()-start)
    atomic_json(M5/('backend_'+name+'.json'),result)
    if result['status']!='evaluated':raise ValueError('BACKEND_INCOMPLETE_CHECKPOINT')
    reader=ControlEvidence(h.store);source=reader.resolve(result['execution_id'])
    updates=reader.read_file(source,'controller_observations.json');traj=reader.read_file(source,'trajectory.json.gz')
    from extensions.tendon_family.diagnostic_evidence import measured_motion
    def summarize(ctx):
        motion=measured_motion(reader,source)
        return dict(candidate=name,execution_id=result['execution_id'],implementation_identity=p['implementation_identity'],
            updates=updates,motion=motion,command_plan_capture=captured,
            full_states=[dict(time_s=r['time_s'],state=r['qpos_rad']+r['qvel_rad_s']) for r in traj],
            metrics=dict(terminal_error_m=result['factual_result']['terminal_error_m'],holding_max_error_m=result['factual_result']['sampled_settling']['max_error_m'],
                holding_max_speed_m_s=result['factual_result']['sampled_settling']['max_speed_m_s']),
            backend_cost_s=sum(r['charged']['wall_s'] for r in result['receipts'].values()),
            preparation_cost_s=json.loads(h.store.lookup(h.run_id,'prepare-candidate')['receipt'])['charged']['wall_s'],
            source_manifest=source['manifest'])
    operation(M5,'backend_summary_'+name,summarize,30.)
    print(json.dumps(dict(candidate=name,backend_execution=result['execution_id'],terminal_m=result['factual_result']['terminal_error_m'])),flush=True)


def prelaunch():
    p=freeze();from tools.platform_models import DeepSeekAdapter
    from extensions.tendon_family.gvs_trajectory import _FUNCTION_PROVIDER
    assert _FUNCTION_PROVIDER.get() is None
    assert p['local_numerical_protocol']['version']=='fixed_backend_transition_validation@2.0.0'
    for c in p['candidates']:
        assert c['configuration']['policy']['controller']['version']=='7.0.0'
        assert len(c['initial_full_state'])==96
        assert c['configuration']['task']['timing']['duration_s']==.35
    atomic_json(M5/'prelaunch.json',dict(passed=True,protocol_identity=digest(p),default_provider_absent=True,
        original_local_support_reused=True,protected_slots=6,provider_probe_purchased=False))


def run_pair():
    freeze()
    for name in ('original075','original15'):forecast(name)
    seal_forecasts()
    for name in ('original075','original15'):backend(name)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--phase',required=True);args=p.parse_args()
    if args.phase=='m4':m4()
    elif args.phase=='prelaunch':prelaunch()
    elif args.phase=='pair':run_pair()
