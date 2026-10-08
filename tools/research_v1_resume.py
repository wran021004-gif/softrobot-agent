"""New authorized bounded v1 campaign. Reuses reports, never old activity budget."""
import argparse
from copy import deepcopy
from pathlib import Path
import subprocess
import threading
import time
from uuid import uuid4
from tools.state_io import read, atomic_json, digest
from tools.platform_store import Store, plain, zero, now, encode
from tools.platform_host import Host
from tools.research_execution import invoke
from tools.research_investigations import InvestigationOrder
from tools.research_mainline3 import configuration, SOURCE, fixed_pipeline, live_interface_scenario, direct_validation_plan
from tools.research_mainline3 import import_historical_provenance
from tools.research_v1_delivery import model_configuration, FIXED_TOOLS
from tools.research_single_validation import sha, stop
from tools.research_validation_activity import export
from tools.research_validation_gate import generate
from tools.context_assembly import _no_secrets

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'evidence/research_v1_completion_20261008/stages'
AUTH=Path(r'C:\Users\gugugaga\.codex\attachments\392df48d-f18e-4e83-aa0b-5d0f2993f4a8\goal-objective.md')


def history():
    # Include all old stopped campaigns, evidence and unresolved reservations.
    from tools.research_direct_validation import history as older
    manifest=read(OLD/'validation_manifest.json')
    store=Store(ROOT/manifest['phases']['direct']['output'])
    return dict(older=older(),last=dict(db_sha256=sha(store.db),ledger=store.remaining(),
        sessions={key:store.session(key)['status'] for key in ('mainline3-direct','mainline3-direct-repair1')},
        files={p.relative_to(ROOT).as_posix():sha(p) for p in (OLD.parent).rglob('*') if p.is_file()}))


def prepare(out):
    if out.exists():raise ValueError('NEW_AUTHORIZATION_DIRECTORY_REQUIRED')
    cfg=model_configuration(configuration())
    cfg['policy']['model']['parameters']['investigation_contract']='business_fields_v2'
    cfg['policy']['model']['adapter_version']='7.0.0'
    cfg['policy']['model']['timeout_s']=900.
    identity='mainline3-v1-resume-'+uuid4().hex[:12]
    node={**zero(),'model_calls':8,'tool_calls':12,'wall_s':900.}
    bindings={key:'1.0.0' for key in ('research.investigate','research.investigation_status','research.investigation_read','research.investigation_disposition')}
    phases={}
    for mode,count,models,tools,wall,corrections in [('reuse',1,8,128,2400.,2),('coordinated',4,32,512,8000.,4)]:
        phase=dict(project_budget={**zero(),'model_calls':models,'tool_calls':tools,'wall_s':wall},
            node_count=count,node_budget=node,total_node_budget={k:v*count for k,v in node.items()},
            node_timeout_s=900.,output_bytes=65536,tool_bindings=dict(bindings),
            operation_allowances={k:dict(reserve_s=5.,timeout_s=30.) for k in bindings},
            protocol_correction_limit=corrections,protocol_correction_role_limits=dict(principal=2,other=0 if mode=='reuse' else 2))
        if mode=='reuse':
            phase['tool_bindings']['research.investigation_handoff']='1.0.0'
            phase['operation_allowances']['research.investigation_handoff']=dict(reserve_s=5.,timeout_s=30.)
        phases[mode]=phase
    reserves=dict(zip(FIXED_TOOLS,(30.,700.,150.,500.,4400.,15.,30.)))
    phases['fixed']=dict(project_budget={**zero(),'tool_calls':14,'backend_solves':2,'wall_s':6000.},
        tool_bindings=FIXED_TOOLS,operation_allowances={k:dict(reserve_s=v,timeout_s=v) for k,v in reserves.items()},
        maximum_attempts=dict(linearization=2,metrics=2,endpoint=2,backend=2),
        retry_condition='Only incomplete/invalid engineering failure after targeted repair; valid physical failure is terminal.')
    out.mkdir(parents=True)
    atomic_json(out/'authorization.json',dict(text=AUTH.read_text(encoding='utf-8-sig'),sha256=sha(AUTH),
        recipient='https://api.deepseek.com',model='deepseek-flash',new_authorization=True))
    atomic_json(out/'frozen_configuration.json',cfg)
    for mode,phase in phases.items():
        grant=dict(project_id=identity+'-'+mode,grant_id=identity+'-'+mode,budget=phase['project_budget'],
            authorization_source=out.relative_to(ROOT).as_posix()+'/authorization.json; phase '+mode)
        atomic_json(out/(mode+'_grant.json'),grant)
        phase.update(output='runs/'+identity+'-'+mode,grant_identity=digest(grant))
    paths=subprocess.check_output(['git','ls-files','tools','schemas','extensions','configs'],cwd=ROOT,text=True).splitlines()
    paths += ['tools/research_v1_resume.py','tools/investigation_contract.py','tools/investigation_handoff.py',SOURCE.relative_to(ROOT).as_posix()]
    manifest=dict(activity_id=identity,created_at=now(),branch='feat/gvs-dynamics',
        code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        code_identity={p:sha(ROOT/p) for p in sorted(set(paths)) if (ROOT/p).is_file()},
        configuration_identity=digest(cfg),phases=phases,implementation_repairs_used=0,implementation_repair_ceiling=4,
        planned_interface_change=True,paid_protocol_correction_ceiling=6,automatic_transport_retries=0,
        fixed_source=SOURCE.relative_to(ROOT).as_posix(),fixed_source_sha256=sha(SOURCE),
        fixed_changes={'design/near_routing_radius_scale':1.01,'design/far_routing_radius_scale':.99},
        historical_campaign='mainline3-v1-e7e730716bab',historical_reports_are_new_nodes=False,
        stopping='Only real stage gates permit dependent work; all submitted nodes drained; no Version 2.')
    atomic_json(out/'historical_before.json',history())
    atomic_json(out/'validation_manifest.json',manifest)
    print(encode(dict(prepared=identity,model_requests=0)),flush=True)


def check(out):
    m=read(out/'validation_manifest.json');cfg=read(out/'frozen_configuration.json')
    if digest(cfg)!=m['configuration_identity'] or any(sha(ROOT/p)!=v for p,v in m['code_identity'].items()):raise ValueError('FROZEN_CODE_OR_CONFIGURATION_CHANGED')
    if history()!=read(out/'historical_before.json'):raise ValueError('OLD_SEALED_HISTORY_CHANGED')
    return m,cfg


def collect(host, receipt):
    if receipt['execution_status']!='completed':raise ValueError('PUBLIC_SUBMISSION_FAILED')
    result=host.store.artifact(receipt['output']);key=result['investigation_id']
    node=host.store.session(host.run_id)['state']['investigations'][key]
    thread=next((t for t in threading.enumerate() if t.name=='investigation-'+key),None)
    if thread:thread.join(max(0,node['order']['timeout_s']-(time.time()-node['started_unix']))+5.)
    receipt=invoke(host,'research.investigation_status',dict(investigation_id=key),request_id='collect-'+key)
    if receipt['execution_status']!='completed':raise ValueError('PUBLIC_COLLECTION_FAILED')
    return host.store.artifact(receipt['output'])


def reuse(host,out):
    original=read(OLD/'direct_bundle.json');old_manifest=read(OLD/'validation_manifest.json')
    old_store=Store(ROOT/old_manifest['phases']['direct']['output'])
    source_value=read(ROOT/'runs/stage336_manual_20261001_090616/stage336_audit.json')['execution']['factual_result']
    import_historical_provenance(host.store,source_value)
    descriptors=[];reports=[]
    # Import immutable originals into this Store, not as model observations.
    with host.store.transaction() as db:
        source=plain(host.store.put(db,source_value))
        for key in ('reach-question','timing-question'):
            node=original['state']['investigations'][key];reports.append(node['result'])
            if plain(host.store.put(db,old_store.artifact(node['result'])))!=node['result']:raise ValueError('ORIGINAL_REPORT_CHANGED')
            validation=plain(host.store.put(db,dict(historical_node_identity=digest(node),
                original_gate=read(OLD/'direct_gate.json')['gates'],old_report_valid=True,
                old_formal_disposition_succeeded=False,old_material_review=read(OLD/'direct_material_review.json'))))
            descriptors.append(dict(source_directory=old_manifest['phases']['direct']['output'],source_run_id='mainline3-direct-repair1',
                source_project_id=original['project']['project_id'],source_database_sha256=sha(old_store.db),
                source_node=key,report=node['result'],historical_validation=validation))
        intervention=plain(host.store.put(db,dict(kind='human_engineering_review',
            source='evidence/research_v1_completion_20261008/stages/direct_material_review.json',
            original=read(OLD/'direct_material_review.json'),
            instruction='Independently check the reports against original evidence; this review is not authority to force a disposition.')))
        state=host.store.session(host.run_id,db)['state'];grant=state['role_context']['investigation_grant']
        grant['evidence']=[source,intervention];grant['historical_handoffs']=descriptors
        state['investigation_grant_identity']=digest(grant);host.store.update_state(db,host.run_id,state)
    for index,descriptor in enumerate(descriptors):
        receipt=invoke(host,'research.investigation_handoff',descriptor,request_id='historical-handoff-'+str(index))
        if receipt['execution_status']!='completed':raise ValueError('PUBLIC_HISTORICAL_HANDOFF_FAILED')
    # Independently inspected complete original page (ordinary source fits 8192).
    receipt=invoke(host,'research.investigation_read',dict(reference=source,pointer='',limit=100,byte_limit=8192),request_id='principal-original-inspection')
    if receipt['execution_status']!='completed':raise ValueError('PRINCIPAL_SOURCE_INSPECTION_FAILED')
    stage=read(out/'validation_manifest.json')['phases']['reuse']
    order=plain(InvestigationOrder(investigation_id='principal-historical-disposition',role='principal',
        question='Independently review the two complete historical investigator reports and the original public inspection. Return exactly one structured disposition for reach-question and timing-question, each bound to its report. Evaluate factual and interpretive support separately; accept only specifically supported portions with adopted_claims, exact supporting report facts and inspected scope fields, or defer/reject with concrete rationale. Review the supplied independent engineering objections and their provenance without assuming agreement. Distinguish seconds units from clock definition, sampled window maximum from internal trajectory, execution completeness from optimization convergence, and missing independent reach criteria from the recorded official task_accepted=false. Historical scope is only Stage336 proposal-build execution 494deb38d6374deb8f741e96f2430826; this is new disposition verification of reused historical reports, no new investigator execution or scientific computation.',
        evidence=[source,intervention,*reports],queries=[dict(reference=r,pointer='',limit=100,byte_limit=65536) for r in reports]+[
            dict(reference=intervention,pointer='',limit=100,byte_limit=8192)],
        budget={**stage['node_budget'],'tool_calls':11},timeout_s=900.,output_bytes=65536,
        stop_conditions=['At most eight model attempts and two paid unexecuted protocol corrections',
            'Exact original source scope; no delegation, science or automatic transport retries']))
    atomic_json(out/'reuse_order.json',order)
    result=collect(host,invoke(host,'research.investigate',order,request_id='principal-disposition-submit'))
    if result['status']!='completed':return dict(status=result['status'],result=result)
    decisions=host.store.artifact(result['result'])['dispositions'];expected=dict(zip(('reach-question','timing-question'),reports))
    if len(decisions)!=2 or {d['investigation_id'] for d in decisions}!=set(expected):return dict(status='incomplete',reason='Two explicit dispositions required')
    rows=[]
    for decision in decisions:
        if decision['report']!=expected[decision['investigation_id']]:raise ValueError('MODEL_REPORT_BINDING_MISMATCH')
        rows.append(invoke(host,'research.investigation_disposition',decision,request_id='dispose-'+decision['investigation_id']))
    return dict(status='formal_dispositions_recorded' if all(r['execution_status']=='completed' for r in rows) else 'failed',receipts=rows)


def continue_preparation_repair(out,*,correction=False):
    """Same logical node, clock, permissions, old reads and project charges."""
    from tools.research_investigations import InvestigationDispatcher
    m,cfg=check(out);stage=m['phases']['reuse'];store=Store(ROOT/stage['output'])
    number=3 if correction else 2
    if (out/(f'repair{number}_launch.json')).exists():raise ValueError('NO_REPEATED_CONTINUATION')
    parent='mainline3-reuse-repair2' if correction else 'mainline3-reuse'
    old=store.session(parent);key='principal-historical-disposition';node=old['state']['investigations'][key]
    if old['status']!='stopped' or node['status']!='failed':raise ValueError('SEALED_FAILURE_REQUIRED')
    if not correction and (node['usage']['model_calls'] or node['progress']['transport_callable_invocations']):raise ValueError('PREPARATION_ONLY_FAILURE_REQUIRED')
    context=None
    if correction:
        previous=read(out/'reuse_bundle.json');events=[e for e in previous['events'] if e['run_id']==parent]
        response=[e for e in events if e['kind']=='investigation_provider_response'][-1]
        feedback=[e for e in events if e['kind']=='investigation_protocol_correction'][-1]
        raw=previous['artifacts'][response['outputs'][0]['artifact_id']]
        if raw['choices'][0]['finish_reason']!='tool_calls' or not node.get('protocol_correction_used') or node['progress']['received_responses']!=node['progress']['transport_callable_invocations']:raise ValueError('CONFIRMED_RECEIVED_INVALID_NATIVE_RETURN_REQUIRED')
        msg=raw['choices'][0]['message']
        context=dict(kind='explicit_received_return_correction_turn',previous_response=response['outputs'][0],
            received_native_calls=msg['tool_calls'],received_assistant_content=msg.get('content'),
            feedback=previous['artifacts'][feedback['outputs'][0]['artifact_id']],
            retained_followup_reads=node['reads'][len(node['order']['queries']):],
            history_presentation='Original complete provider responses, including thinking text, remain archived. This new correction user turn presents the full invalid native call unchanged, all complete original reports and evidence in the main packet, all follow-up pages, and exact feedback. Prior thinking text is not evidence and is archive-only in this turn. No report was edited or treated as successful; counters, permissions and original node clock remain unchanged.')
    if store.remaining()['occupied']:raise ValueError('INFLIGHT_OPERATIONS_MUST_BE_RECONCILED')
    remaining=node['order']['timeout_s']-(time.time()-node['started_unix'])
    if remaining<=0:raise ValueError('ORIGINAL_LOGICAL_NODE_DEADLINE_EXPIRED')
    run_id=f'mainline3-reuse-repair{number}';cfg['run_id']=run_id
    cfg['policy'].update(route=None,budget=stage['project_budget'],allowed_tools=list(stage['tool_bindings']),tool_bindings=stage['tool_bindings'],
        timeout_s=stage['project_budget']['wall_s'],operation_allowances=stage['operation_allowances'])
    host=Host(store.root,run_id);host.create(cfg,parent_run_id=parent);host.resume()
    with store.transaction() as db:
        state=deepcopy(old['state']);state.pop('stop_reason',None)
        state['investigations'][key].update(status='pending',request_run_id=run_id,continuation_of=node['failure_record'])
        store.update_state(db,run_id,state)
    import_historical_provenance(store,read(ROOT/'runs/stage336_manual_20261001_090616/stage336_audit.json')['execution']['factual_result'])
    reserve={k:node['order']['budget'][k]-node['usage'][k] for k in zero()};reserve['wall_s']=remaining
    row,fresh=store.reserve(run_id,'investigation-'+key,digest(dict(original_execution=node['failure_record'],repair=number)),
        'investigation-dispatcher',reserve,kind='investigation')
    if not fresh:raise ValueError('NO_REDISPATCH')
    atomic_json(out/(f'repair{number}_launch.json'),dict(timestamp=now(),same_project=store.config()['project_id'],
        original_run_id=parent,run_id=run_id,remaining_original_clock_s=remaining,original_node_started_unix=node['started_unix'],
        logical_usage_before=node['usage'],reserve=reserve,reuse_original_prefetch=True,original_charges_preserved=True))
    started=time.monotonic()
    try:
        from examples.gvs_nmpc_route_experiment import load_credential
        load_credential(Path.home()/'.codex/.env')
        dispatcher=InvestigationDispatcher(host)
        dispatcher._execute(InvestigationOrder.model_validate(node['order']),row,reuse_saved_reads=True,correction_context=context)
        result=invoke(host,'research.investigation_status',dict(investigation_id=key),request_id='collect-recovered-principal')
        returned=store.artifact(result['output'])
        if returned['status']!='completed':atomic_json(out/'reuse_result.json',returned);return
        decisions=store.artifact(returned['result'])['dispositions']
        expected={k:n['result'] for k,n in old['state']['historical_investigations'].items()}
        if len(decisions)!=2 or {d['investigation_id'] for d in decisions}!=set(expected):raise ValueError('TWO_MODEL_DISPOSITIONS_REQUIRED')
        rows=[]
        for d in decisions:
            if d['report']!=expected[d['investigation_id']]:raise ValueError('MODEL_REPORT_BINDING_MISMATCH')
            rows.append(invoke(host,'research.investigation_disposition',d,request_id='dispose-'+d['investigation_id']))
        atomic_json(out/'reuse_result.json',dict(status='formal_dispositions_recorded' if all(r['execution_status']=='completed' for r in rows) else 'failed',receipts=rows))
    finally:
        stop(host,'REPAIRED_PREPARATION_CONTINUATION_TERMINAL; original clock and project usage preserved')
        export(out,'reuse',run_id=run_id);b=read(out/'reuse_bundle.json');b['session_status']='stopped';atomic_json(out/'reuse_bundle.json',b)
        prior=read(out/'reuse_lifecycle.json')
        atomic_json(out/(f'reuse_repair{number}_lifecycle.json'),dict(timestamp=now(),application_wall_s=time.monotonic()-started,all_submitted_nodes_drained=True))
        atomic_json(out/'historical_after.json',dict(unchanged=history()==read(out/'historical_before.json')))


def execute(out,mode):
    m,cfg=check(out);stage=m['phases'][mode]
    prior=dict(coordinated='reuse',fixed='coordinated').get(mode)
    if prior and not read(out/(prior+'_gate.json'))['passed']:raise ValueError('DEPENDENT_GATE_NOT_PASSED')
    root=ROOT/stage['output']
    recovery=m.get('preflight_recovery',{}).get(mode)
    if (out/(mode+'_launch.json')).exists() or (root.exists() and not recovery):raise ValueError('NO_STAGE_RESTART_OR_COUNTER_RESET')
    grant=read(out/(mode+'_grant.json'))
    if digest(grant)!=stage['grant_identity']:raise ValueError('FROZEN_GRANT_CHANGED')
    cfg['run_id']='mainline3-'+mode
    cfg['policy'].update(route=None,budget=stage['project_budget'],allowed_tools=list(stage['tool_bindings']),
        tool_bindings=stage['tool_bindings'],timeout_s=stage['project_budget']['wall_s'],operation_allowances=stage['operation_allowances'])
    store=Store(root)
    if root.exists():
        with store.connect(True) as db:
            if db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] or db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]:raise ValueError('PREFLIGHT_RECOVERY_REQUIRES_NO_STARTED_SESSION_OR_OPERATION')
        if store.config()['project_id']!=grant['project_id'] or any(store.remaining()['used'].values()) or store.remaining()['occupied']:raise ValueError('PREFLIGHT_RECOVERY_IDENTITY_OR_LEDGER_MISMATCH')
    else:store.create(grant)
    host=Host(root,cfg['run_id']);host.create(cfg);host.resume()
    began=time.monotonic();atomic_json(out/(mode+'_launch.json'),dict(timestamp=now(),code_commit=m['code_commit'],model_requests_before=0))
    try:
        if mode!='fixed':
            from examples.gvs_nmpc_route_experiment import load_credential
            load_credential(Path.home()/'.codex/.env')
            with store.transaction() as db:
                source=plain(store.put(db,read(ROOT/'runs/stage336_manual_20261001_090616/stage336_audit.json')['execution']['factual_result']))
                ig=dict(max_count=stage['node_count'],max_concurrency=2,allowed_tools=['evidence.read'],evidence=[source],
                    include_completed_reports=True,per_node_budget=stage['node_budget'],total_budget=stage['total_node_budget'],
                    output_bytes=65536,deadline_unix=time.time()+stage['project_budget']['wall_s'],
                    protocol_correction_limit=stage['protocol_correction_limit'],protocol_correction_role_limits=stage['protocol_correction_role_limits'],protocol_correction_per_node=2)
                state=store.session(host.run_id,db)['state'];state.update(role_context=dict(role='principal',investigation_grant=ig),investigation_grant_identity=digest(ig))
                store.update_state(db,host.run_id,state)
            if mode=='reuse':result=reuse(host,out)
            else:
                plan=direct_validation_plan(source,expanded=True,mode='coordinated')
                plan['proposal']=stage;plan['principal_budget']={**stage['node_budget'],'tool_calls':11}
                atomic_json(out/'coordinated_plan.json',plan)
                result=live_interface_scenario(host,'coordinated',plan=plan)
        else:
            from schemas.platform_analysis import TaskAnalysisProtocol,EndpointTarget
            source=cfg['policy']['candidate_builder']['parameters']['data']['semantic_source']
            protocol=TaskAnalysisProtocol(baseline_lengths_m={c['id']:c['length_m'] for c in source['components'] if c['kind']=='flexible_segment'},
                duration_s=cfg['task']['timing']['duration_s'],period_s=cfg['task']['timing']['control_period_s'],frequency_rad_s=[.1,1.,10.])
            target=EndpointTarget(position_m=cfg['task']['goal']['data']['target_m'],position_tolerance_m=cfg['task']['evaluator']['parameters']['data']['tolerance_m'],position_scale_m=.01)
            with store.transaction() as db:p=plain(store.put(db,protocol));t=plain(store.put(db,target))
            result=fixed_pipeline(host,changes=m['fixed_changes'],protocol=p,target=t,execute_backend=True)
        atomic_json(out/(mode+'_result.json'),result)
    except Exception as exc:
        atomic_json(out/(mode+'_application_failure.json'),dict(timestamp=now(),type=type(exc).__name__,automatic_retry=False))
        raise
    finally:
        for thread in [t for t in threading.enumerate() if t.name.startswith('investigation-')]:
            node=store.session(host.run_id)['state'].get('investigations',{}).get(thread.name[14:],{})
            thread.join(max(0,node.get('order',{}).get('timeout_s',900)-(time.time()-node.get('started_unix',time.time())))+5)
        active=[t.name for t in threading.enumerate() if t.name.startswith('investigation-')]
        stop(host,'NEW_AUTHORIZED_STAGE_COLLECTED; dependent phases require actual gate')
        atomic_json(out/(mode+'_lifecycle.json'),dict(timestamp=now(),application_wall_s=time.monotonic()-began,active_threads=active,all_submitted_nodes_drained=not active))
        export(out,mode);bundle=read(out/(mode+'_bundle.json'));bundle['session_status']='stopped';atomic_json(out/(mode+'_bundle.json'),bundle)
        atomic_json(out/'historical_after.json',dict(unchanged=history()==read(out/'historical_before.json')))
        if mode=='coordinated':atomic_json(out/'coordinated_gate.json',generate(bundle))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','execute','continue-preparation-repair','continue-correction-repair']);parser.add_argument('directory',type=Path)
    parser.add_argument('--mode',choices=['reuse','coordinated','fixed'],default='reuse');args=parser.parse_args()
    if args.action=='prepare':prepare(args.directory.resolve())
    elif args.action=='continue-preparation-repair':continue_preparation_repair(args.directory.resolve())
    elif args.action=='continue-correction-repair':continue_preparation_repair(args.directory.resolve(),correction=True)
    else:execute(args.directory.resolve(),args.mode)


if __name__=='__main__':main()
