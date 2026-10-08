"""Authorized Mainline 3 v1 stages over the existing Host, Store and gates.

Preparation is offline. execute starts one frozen stage once; review is a
separate human/Codex material assessment, never another provider call.
"""
import argparse
from copy import deepcopy
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import threading
import time
from uuid import uuid4

from tools.state_io import atomic_json,read,digest
from tools.platform_store import Store,plain,zero,now,encode
from tools.platform_host import Host
from tools.context_assembly import _no_secrets
from tools.research_mainline3 import configuration,interface_proposal,direct_validation_plan,live_interface_scenario,fixed_pipeline,SOURCE
from tools.research_direct_validation import history
from tools.research_single_validation import sha,stop
from tools.research_validation_activity import export
from tools.research_validation_gate import generate

ROOT=Path(__file__).resolve().parents[1]
BASE='9a96094e38108e820175b817eaff946b21f80f6c'
FIXED_TOOLS={'research.prepare_candidate':'1.0.0','analysis.linearize_configuration':'1.0.0',
    'analysis.control_metrics':'2.0.0','analysis.bounded_endpoint':'1.0.0',
    'simulation.run':'1.0.0','evaluation.run':'1.0.0','control.profile_report':'1.0.0'}

def model_configuration(cfg):
    cfg=deepcopy(cfg)
    cfg['policy']['model'].update(max_tokens=32768,investigation_max_tokens=32768,timeout_s=600.,
        length_recovery=None,protocol_recovery=dict(max_total=2,max_consecutive=1),readonly_batch_limit=None)
    return cfg

def prepare(out,authorization):
    if out.exists():raise ValueError('FRESH_AUTHORIZATION_DIRECTORY_REQUIRED')
    subprocess.check_call(['git','merge-base','--is-ancestor',BASE,'HEAD'],cwd=ROOT)
    cfg=model_configuration(configuration());_no_secrets(cfg)
    model=cfg['policy']['model']
    assert (model['base_url'],model['model'],model['thinking'],model['reasoning_effort'])==('https://api.deepseek.com','deepseek-flash','enabled','high')
    identity='mainline3-v1-'+uuid4().hex[:12]
    out.mkdir(parents=True)
    atomic_json(out/'authorization.json',dict(text=authorization.read_text(encoding='utf-8-sig'),
        recipient=model['base_url'],model=model['model'],data_scope='Task-scoped non-secret saved research evidence and results only; existing credential loader, no secret archival'))
    atomic_json(out/'frozen_configuration.json',cfg)
    phases={mode:interface_proposal(mode,expanded=True) for mode in ('direct','coordinated')}
    reserves=dict(zip(FIXED_TOOLS,(30.,500.,100.,300.,3000.,15.,30.)))
    phases['fixed']=dict(project_budget={**zero(),'tool_calls':7,'backend_solves':1,'wall_s':4000.},tool_bindings=FIXED_TOOLS,
        operation_allowances={tool:dict(reserve_s=value,timeout_s=value) for tool,value in reserves.items()},
        protected_total_reservation_s=sum(reserves.values()))
    for mode,proposal in phases.items():
        grant=dict(project_id=identity+'-'+mode,grant_id=identity+'-'+mode,budget=proposal['project_budget'],
            authorization_source='goal-objective.md user 2026-10-08; '+out.relative_to(ROOT).as_posix()+'/authorization.json; '+mode)
        atomic_json(out/(mode+'_grant.json'),grant)
        proposal.update(output='runs/'+identity+'-'+mode,grant_identity=digest(grant))
    tracked=subprocess.check_output(['git','ls-files','tools','schemas','extensions','configs'],cwd=ROOT,text=True).splitlines()
    tracked=list(dict.fromkeys([*tracked,'tools/research_v1_delivery.py',SOURCE.relative_to(ROOT).as_posix(),
        'runs/stage336_manual_20261001_090616/stage336_audit.json','runs/stage336_manual_20261001_090616/platform.sqlite']))
    manifest=dict(activity_id=identity,branch='feat/gvs-dynamics',created_at=now(),
        code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        relevant_files_sha256={p:sha(ROOT/p) for p in tracked if (ROOT/p).is_file()},
        dependencies={p:importlib.metadata.version(p) for p in ('pydantic','numpy','scipy','casadi','mujoco')},
        configuration_identity=digest(cfg),phases=phases,protocol_correction_limit=2,repair_ceiling=2,repairs_used=0,
        fixed_source=SOURCE.relative_to(ROOT).as_posix(),fixed_source_identity=sha(SOURCE),
        fixed_changes={'design/near_routing_radius_scale':1.01,'design/far_routing_radius_scale':.99},
        capacity=dict(generation_tokens=32768,report_serialized_utf8_bytes=65536,report_rule='Administrative serialized-byte limit, not a token conversion.',
            parent_input_budget_tokens=160000,context_limit_tokens=model['context_guard']['context_limit_tokens'],
            input_estimator='Existing conservative UTF-8 byte upper estimate plus 8192 framing; provider usage separately archived.',
            guard='Exact final wire includes all messages, native definitions, reports, results and 32768 output reservation plus 8192 interaction reserve.',
            report_access='Complete Store report and original pointers; principal report pages allow 65536 content bytes with 2048 envelope headroom. Ordinary pages stay bounded at 6000. Oversized views advertise continuation and callable evidence.read; no silent tail truncation.'),
        endpoint_support=dict(source='https://api-docs.deepseek.com/api/create-chat-completion/',verified_date='2026-10-08',documented_max_tokens=393216,probe_calls=0),
        stopping=['Real direct and material gates before coordination; coordinated gates before fixed',
            'No automatic transport retries; unknown original requests retain escrow',
            'No budget transfers, no scientific tuning, exactly one backend attempt maximum',
            'At most two paid protocol corrections total and one continuous error per node',
            'Drain every submitted node before stopping; no Version 2 implementation'])
    atomic_json(out/'historical_before.json',history())
    atomic_json(out/'validation_manifest.json',manifest)
    atomic_json(out/'engineering_clock.json',dict(frozen_at=now(),preparation_started_at=read(out.parent/'engineering_start.json')['timestamp'] if (out.parent/'engineering_start.json').exists() else None))
    print(encode(dict(prepared=True,activity=identity,provider_calls=0,phases={k:v['project_budget'] for k,v in phases.items()})))

def check_freeze(out):
    manifest=read(out/'validation_manifest.json');cfg=read(out/'frozen_configuration.json')
    if digest(cfg)!=manifest['configuration_identity']:raise ValueError('FROZEN_CONFIGURATION_CHANGED')
    if any(sha(ROOT/p)!=value for p,value in manifest['relevant_files_sha256'].items()):raise ValueError('FROZEN_CODE_OR_INPUT_CHANGED')
    if {p:importlib.metadata.version(p) for p in manifest['dependencies']}!=manifest['dependencies']:raise ValueError('FROZEN_DEPENDENCIES_CHANGED')
    if history()!=read(out/'historical_before.json'):raise ValueError('HISTORICAL_SEALED_ACTIVITY_CHANGED')
    return manifest,cfg

def execute(out,mode,*,live=True):
    manifest,cfg=check_freeze(out)
    prior={'coordinated':'direct','fixed':'coordinated'}.get(mode)
    if prior and not read(out/(prior+'_gate.json'))['passed']:raise ValueError('DEPENDENT_PHASE_GATE_NOT_PASSED')
    stage=manifest['phases'][mode];root=ROOT/stage['output']
    if root.exists() or (out/(mode+'_launch.json')).exists():raise ValueError('NO_REPEATED_STAGE_OR_BUDGET_RESET')
    grant=read(out/(mode+'_grant.json'))
    if digest(grant)!=stage['grant_identity']:raise ValueError('FROZEN_STAGE_GRANT_CHANGED')
    store=Store(root);store.create(grant)
    cfg['run_id']='mainline3-'+mode
    cfg['policy'].update(route=None,budget=stage['project_budget'],allowed_tools=list(stage['tool_bindings']),
        tool_bindings=stage['tool_bindings'],timeout_s=4000. if mode=='fixed' else stage['project_budget']['wall_s'],
        operation_allowances=stage.get('operation_allowances',{}))
    host=Host(root,cfg['run_id']);host.create(cfg);host.resume()
    began=time.monotonic();inherited=0
    if prior:inherited=read(out/(prior+'_bundle.json'))['state'].get('investigation_protocol_corrections_used',0)
    atomic_json(out/(mode+'_launch.json'),dict(timestamp=now(),live=live,code_commit=manifest['code_commit'],inherited_corrections=inherited,
        environment=dict(python=platform.python_version(),platform=platform.platform(),processor=platform.processor(),dependencies=manifest['dependencies']),
        backend_parallel_heavy_work=False if mode=='fixed' else None))
    try:
        if mode=='fixed':
            from schemas.platform_analysis import TaskAnalysisProtocol,EndpointTarget
            source=cfg['policy']['candidate_builder']['parameters']['data']['semantic_source']
            protocol=TaskAnalysisProtocol(baseline_lengths_m={c['id']:c['length_m'] for c in source['components'] if c['kind']=='flexible_segment'},
                duration_s=cfg['task']['timing']['duration_s'],period_s=cfg['task']['timing']['control_period_s'],frequency_rad_s=[.1,1.,10.])
            target=EndpointTarget(position_m=cfg['task']['goal']['data']['target_m'],position_tolerance_m=cfg['task']['evaluator']['parameters']['data']['tolerance_m'],position_scale_m=.01)
            with store.transaction() as db:protocol_ref=plain(store.put(db,protocol));target_ref=plain(store.put(db,target))
            result=fixed_pipeline(host,changes=manifest['fixed_changes'],protocol=protocol_ref,target=target_ref,execute_backend=True)
        else:
            if live:
                from examples.gvs_nmpc_route_experiment import load_credential
                load_credential(Path.home()/'.codex/.env')
            with store.transaction() as db:
                factual=read(ROOT/'runs/stage336_manual_20261001_090616/stage336_audit.json')['execution']['factual_result']
                ref=plain(store.put(db,factual));state=store.session(host.run_id,db)['state']
                ig=dict(max_count=stage['node_count'],max_concurrency=2,allowed_tools=['evidence.read'],evidence=[ref],include_completed_reports=True,
                    per_node_budget=stage['node_budget'],total_budget=stage['total_node_budget'],output_bytes=stage['output_bytes'],
                    deadline_unix=time.time()+stage['project_budget']['wall_s']-(time.monotonic()-began),protocol_correction_limit=2)
                state.update(role_context=dict(role='principal',investigation_grant=ig),investigation_grant_identity=digest(ig),
                    investigation_protocol_corrections_used=inherited)
                store.update_state(db,host.run_id,state)
            plan=direct_validation_plan(ref,expanded=True,mode=mode)
            atomic_json(out/(mode+'_plan.json'),plan)
            result=live_interface_scenario(host,mode,plan=plan)
        atomic_json(out/(mode+'_result.json'),result)
    except Exception as exc:
        atomic_json(out/(mode+'_application_failure.json'),dict(timestamp=now(),exception_type=type(exc).__name__,
            elapsed_s=time.monotonic()-began,no_retry=True,reason='Inspect original sealed operation failure; no assumed billing or success'))
        raise
    finally:
        # Keep authority alive until submitted nodes finish; siblings survive failure.
        threads=[t for t in threading.enumerate() if t.name.startswith('investigation-')]
        for thread in threads:
            node=store.session(host.run_id)['state'].get('investigations',{}).get(thread.name[len('investigation-'):],{})
            remaining=max(0,node.get('order',{}).get('timeout_s',600)-(time.time()-node.get('started_unix',time.time())))
            thread.join(remaining+5)
        active=[t.name for t in threads if t.is_alive()]
        stop(host,'V1_STAGE_TERMINAL_COLLECTED; dependent stages require saved gate')
        atomic_json(out/(mode+'_lifecycle.json'),dict(timestamp=now(),application_wall_s=time.monotonic()-began,
            thread_active_at_close=active,all_submitted_threads_collected=not active,unknown_reservations_retained=True))
        export(out,mode)
        bundle=read(out/(mode+'_bundle.json'));bundle.update(session_status='stopped',transport='real_configured_deepseek' if live else 'deterministic_offline_substitute')
        atomic_json(out/(mode+'_bundle.json'),bundle)
        atomic_json(out/'historical_after.json',dict(unchanged=history()==read(out/'historical_before.json')))
        if mode!='fixed':atomic_json(out/(mode+'_gate.json'),generate(bundle))

def review(out,mode,review_file):
    bundle=read(out/(mode+'_bundle.json'));assessment=read(review_file)
    if assessment['bundle_identity']!=digest(bundle):raise ValueError('REVIEW_WRONG_BUNDLE')
    atomic_json(out/(mode+'_material_review.json'),assessment)
    gate=generate(bundle,assessment);atomic_json(out/(mode+'_gate.json'),gate)
    print(encode(dict(mode=mode,passed=gate['passed'],gates=gate['gates'])))

def continue_report_repair(out,*,live=True):
    """One bounded continuation on the SAME project and original node clock.

    Original receipts stay sealed. A child session explicitly migrates code
    dependencies; its supplemental reservation charges only the remaining
    allowance, while logical-node usage and public inspection limits persist.
    """
    from tools.research_investigations import InvestigationDispatcher,InvestigationOrder
    from tools.platform_models import DeepSeekAdapter,effective_config
    manifest,cfg=check_freeze(out);stage=manifest['phases']['direct'];root=ROOT/stage['output']
    if (out/'repair1_launch.json').exists():raise ValueError('NO_REPEATED_REPAIR_CONTINUATION')
    previous=read(out/'direct_bundle_before_repair1.json');key='reach-question'
    node=previous['state']['investigations'][key]
    assert node['status']=='failed' and node['usage']['model_calls']==5
    assert previous['state']['investigations']['timing-question']['status']=='completed'
    assert not read(out/'direct_lifecycle.json')['thread_active_at_close']
    remaining=node['order']['timeout_s']-(time.time()-node['started_unix'])
    if remaining<=20:raise ValueError('ORIGINAL_NODE_DEADLINE_CANNOT_FUND_CORRECTION')
    store=Store(root);run_id='mainline3-direct-repair1'
    cfg['run_id']=run_id;cfg['policy'].update(route=None,budget=stage['project_budget'],allowed_tools=list(stage['tool_bindings']),
        tool_bindings=stage['tool_bindings'],timeout_s=stage['project_budget']['wall_s'],operation_allowances=stage['operation_allowances'])
    host=Host(root,run_id);host.create(cfg,parent_run_id='mainline3-direct');host.resume()
    with store.transaction() as db:
        state=deepcopy(previous['state'])
        for k,n in state['investigations'].items():n['request_run_id']='mainline3-direct'
        state['investigations'][key]['request_run_id']=run_id
        store.update_state(db,run_id,state)
    dispatcher=InvestigationDispatcher(host);order=InvestigationOrder.model_validate(node['order'])
    original_events=[e for e in previous['events'] if e.get('request_id')=='investigation-'+key]
    response_event=[e for e in original_events if e['kind']=='investigation_provider_response'][-1]
    raw=previous['artifacts'][response_event['outputs'][0]['artifact_id']]
    if raw['choices'][0]['finish_reason']=='length':raise ValueError('TRUNCATION_CORRECTION_NOT_AUTHORIZED')
    report=dispatcher._decode(raw)
    try:dispatcher._validate_return(order,report,node['reads'])
    except ValueError as exc:feedback=dispatcher._protocol_feedback(order,exc)
    else:raise ValueError('REPAIR_REQUIRES_INVALID_UNEXECUTED_REPORT')
    if feedback is None:raise ValueError('NO_ORIGINAL_PROTOCOL_CORRECTION_ALLOWANCE')
    wire=deepcopy(previous['artifacts'][[e for e in original_events if e['kind']=='investigation_provider_attempt'][-1]['outputs'][0]['artifact_id']]['payload'])
    message=raw['choices'][0]['message'];calls=message['tool_calls']
    assistant=dict(role='assistant',content=message.get('content'),tool_calls=calls)
    if 'reasoning_content' in message:assistant['reasoning_content']=message['reasoning_content']
    wire['messages'].extend([assistant,dict(role='tool',tool_call_id=calls[0]['id'],content=encode(feedback))])
    reserve={**zero(),'model_calls':1,'tool_calls':order.budget.tool_calls-node['usage']['tool_calls'],'wall_s':remaining}
    row,fresh=store.reserve(run_id,'investigation-'+key,digest(dict(original_execution=node['progress'],repair='single pointer feedback')),
        'investigation-dispatcher',reserve,kind='investigation')
    if not fresh:raise ValueError('NO_REDISPATCH_OF_REPAIR')
    atomic_json(out/'repair1_launch.json',dict(timestamp=now(),same_project=store.config()['project_id'],parent_run_id='mainline3-direct',run_id=run_id,
        original_node_started_unix=node['started_unix'],remaining_original_node_s=remaining,reserve=reserve,
        original_charges_preserved=True,only_remaining_attempt=True))
    started=time.monotonic();baseline=deepcopy(node['usage']);progress=dispatcher._initial_progress()
    try:
        if live:
            from examples.gvs_nmpc_route_experiment import load_credential
            load_credential(Path.home()/'.codex/.env')
        adapter=DeepSeekAdapter();adapter.request_host=host
        def transport(payload):
            adapter.request_config=effective_config(host)
            adapter.request_config['timeout_s']=max(.001,order.timeout_s-(time.time()-node['started_unix']))
            return adapter.respond(payload,0)
        dispatcher._state(key,status='running',continuation_of=node.get('failure_record'))
        report=dispatcher._interact(order,row,wire,transport,started,progress)
        dispatcher._validate_return(order,report,node['reads'])
        usage=store.session(run_id)['state']['investigations'][key]['usage']
        delta={k:usage[k]-baseline[k] for k in usage}
        sealed=store.complete(row,dispatcher._receipt(row,'completed'),plain(report),elapsed=time.monotonic()-started,actual_cost=delta)
        dispatcher._state(key,status='completed' if report.completion=='complete' else 'incomplete',result=sealed['output'],
            progress=dict(progress,elapsed_s=node['progress']['elapsed_s']+time.monotonic()-started,total_node_wall_s=time.time()-node['started_unix'],settlement_completed=True))
        if report.completion!='complete':raise ValueError('CORRECTION_INCOMPLETE')
        # Collect both reports through the SAME public status/inspection/
        # principal/disposition path; do not re-dispatch the completed nodes.
        from tools.research_mainline3 import live_interface_scenario,direct_validation_plan
        ref=store.session(run_id)['state']['role_context']['investigation_grant']['evidence'][0]
        plan=direct_validation_plan(ref,expanded=True);plan['collect_existing']=True
        result=live_interface_scenario(host,'direct',plan=plan)
        atomic_json(out/'direct_result.json',result)
    except Exception as exc:
        current=store.lookup(run_id,row['request_id'])
        if not current['receipt']:
            usage=store.session(run_id)['state']['investigations'][key]['usage']
            # Existing failure accounting charges the continuation delta once.
            dispatcher._state(key,usage={k:usage[k]-baseline[k] for k in usage})
            dispatcher._handle_failure(order,row,progress,exc,started)
            dispatcher._state(key,usage=usage)
        atomic_json(out/'repair1_failure.json',dict(timestamp=now(),exception_type=type(exc).__name__,no_retry=True))
        raise
    finally:
        stop(host,'V1_REPAIR_CONTINUATION_TERMINAL_NO_BUDGET_RESET')
        export(out,'direct',run_id=run_id)
        bundle=read(out/'direct_bundle.json');bundle['session_status']='stopped';atomic_json(out/'direct_bundle.json',bundle)
        atomic_json(out/'direct_gate.json',generate(bundle))
        atomic_json(out/'direct_repair_lifecycle.json',dict(timestamp=now(),application_wall_s=time.monotonic()-started,
            all_submitted_threads_collected=not any(t.name.startswith('investigation-') for t in threading.enumerate())))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','execute','review','continue-report-repair'])
    parser.add_argument('directory',type=Path);parser.add_argument('--mode',choices=['direct','coordinated','fixed'],default='direct')
    parser.add_argument('--authorization',type=Path);parser.add_argument('--review-file',type=Path)
    args=parser.parse_args();out=args.directory.resolve()
    if not out.is_relative_to(ROOT/'evidence'):raise ValueError('TASK_EVIDENCE_DIRECTORY_REQUIRED')
    if args.action=='prepare':prepare(out,args.authorization)
    elif args.action=='execute':execute(out,args.mode)
    elif args.action=='review':review(out,args.mode,args.review_file)
    else:continue_report_repair(out)

if __name__=='__main__':main()
