"""New bounded B grant, preserved A, fixed C; existing Host/Store/public tools."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import threading
import time
from uuid import uuid4

from tools.state_io import read,atomic_json,digest
from tools.platform_store import Store,plain,zero,now,encode
from tools.platform_host import Host
from tools.research_execution import invoke
from tools.research_investigations import InvestigationDispatcher,InvestigationOrder,InvestigationReturn
from tools.research_mainline3 import configuration,import_historical_provenance,fixed_pipeline
from tools.research_v1_delivery import model_configuration,FIXED_TOOLS
from tools.research_v1_finish import fixed_identity
from tools.research_single_validation import sha,stop
from tools.research_validation_activity import export
from tools.context_assembly import _no_secrets

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'evidence/research_mainline3_v1_finish_20261008'
OUT=ROOT/'evidence/research_mainline3_v1_continue_20261008'
TOOLS={k:'1.0.0' for k in ('research.investigate','research.investigation_status','research.investigation_read','research.investigation_disposition','research.investigation_handoff')}
PRIOR_FAILED=[
 'tests.test_research_investigation_closeout.InvestigationCloseoutTests.test_paginated_original_pointer_binding',
 'tests.test_research_investigation_closeout.InvestigationCloseoutTests.test_principal_claim_links_values_identities_scope_and_defer',
 'tests.test_research_investigation_closeout.InvestigationCloseoutTests.test_scope_budget_and_complete_outgoing_overflow',
 'tests.test_research_mainline3.Mainline3EngineeringTests.test_unconfirmed_recovery_no_redispatch_and_confirmed_failure']

def start():
    if OUT.exists():raise ValueError('NEW_ACTIVITY_ALREADY_EXISTS')
    OUT.mkdir()
    # First user task turn, including preparation and tool approval wait.
    began=1791466212.0
    atomic_json(OUT/'activity_start.json',dict(activity_id='mainline3-v1-continue-'+uuid4().hex[:12],started_unix=began,
        deadline_unix=began+36000,execution_cutoff_unix=began+34200,started_at='2026-10-08T13:30:12Z',
        reviewed_baseline='f6f3b766785e23b46ef8231805911bd4eddfa06d',observed_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        remote_fetch='Target branch fetched once successfully; no advancement; initial sandbox FETCH_HEAD denial resolved by authorized escalation',
        includes='Preparation, repairs, pauses, offline review, live execution and delivery'))
    atomic_json(OUT/'authorization.json',dict(source='User attachment 1e15c71a-9fda-4cfa-bb98-b859881de2fc/pasted-text-1.txt',
        recipient='https://api.deepseek.com',model='deepseek-flash',thinking='enabled',reasoning_effort='high',tool_choice='auto',max_tokens=32768,
        data_scope='Only non-secret task-scoped research data through existing credential loader',A_new_requests=0,B_new_requests=40,
        paid_corrections=6,protected_principal_corrections=3,other_corrections=3,consecutive_corrections=2,probes=2,
        post_freeze_repairs=4,same_defect_repair_cycles=2,B_tools=512,B_wall_s=12000,C_tools=28,C_wall_s=6000,
        C_models=0,C_backend_executions=2,C_second_execution='Engineering invalid/incomplete only, unchanged science',
        deadline_hours=10,delivery_protection_minutes=30,ordinary_push_branch='feat/gvs-dynamics',
        forbidden='Parameter optimization, paid A rerun, extra scientific cases, V2 experiments, force push, uncertain request retransmission'))
    oldmanifest=read(OLD/'validation_manifest.json');old=Store(ROOT/oldmanifest['phases']['coordinated']['output'])
    paths=[p for p in OLD.rglob('*') if p.is_file()]
    paths.extend([old.db,ROOT/oldmanifest['phases']['reuse']['output']/'platform.sqlite',ROOT/'runs/stage336_manual_20261001_090616/platform.sqlite'])
    atomic_json(OUT/'sealed_history.json',{p.relative_to(ROOT).as_posix():sha(p) for p in paths})
    with old.connect(True) as db:
        node=old.session('mainline3-coordinated',db)['state']['investigations']['timing-integrity-limits']
        events=old.events('mainline3-coordinated');request='investigation-timing-integrity-limits'
        receptions=[e for e in events if e.get('request_id')==request and e['kind']=='investigation_provider_response']
        refs=node.get('provider_response_refs',[])
        bodies=[dict(reference=r,available=isinstance(old.artifact(r,db=db),dict)) for r in refs]
        call=old.lookup('mainline3-coordinated',request,db)
        candidates=[p for p in (old.root/'investigation_context'/'timing-integrity-limits').rglob('*') if p.is_file()]
        atomic_json(OUT/'historical_timing_inspection.json',dict(inspection='One bounded read-only inspection of original Store, events, references, receipt and local recovery directory',
            status='received, full body unrecoverable',received_responses=node['progress']['received_responses'],saved_responses=len(receptions),
            saved_body_references=bodies,local_recovery_files=[p.relative_to(ROOT).as_posix() for p in candidates],
            last_received_body_available=False,last_saved_body_is_response=7,original_call={k:call[k] for k in ('request_id','execution_id','status','reserved','charged','receipt')},
            known='Eighth response HTTP 200/full body received, no complete durable body found. Original unknown reservation retained.',
            unknown=['body contents','valid report presence','precise persistence cause','provider tokens and monetary charge for response 8'],
            accounting=old.remaining(),no_old_write=True,no_automatic_retransmission=True))
    atomic_json(OUT/'A_preserved.json',dict(source=(OLD/'reuse_gate.json').relative_to(ROOT).as_posix(),gate=read(OLD/'reuse_gate.json'),
        coverage='Historical investigator reports reused; new principal dispositions in prior activity. No new A model/investigator/scientific work.',
        new_requests=0,accepted=True))
    atomic_json(OUT/'prior_failed_checks.json',dict(source=(OLD/'regression_tests.log').relative_to(ROOT).as_posix(),exact_names=PRIOR_FAILED))

def allocation(models,protected):
    return dict(budget={**zero(),'model_calls':models,'tool_calls':16,'wall_s':2400.},exploration_requests=models-protected,protected_delivery_requests=protected)

def config():
    cfg=model_configuration(configuration())
    cfg['policy']['model'].update(adapter_version='8.0.0',parameters=dict(investigation_contract='selectable_facts_v3'),timeout_s=600.)
    return cfg

def freeze():
    if (OUT/'validation_manifest.json').exists():raise ValueError('ALREADY_FROZEN')
    cfg=config();_no_secrets(cfg)
    b=read(OLD/'coordinated_bundle.json');parent=b['state']['investigations']['coordinator-plan']
    if parent['status']!='completed':raise ValueError('VALID_HISTORICAL_PLAN_REQUIRED')
    InvestigationReturn.model_validate(b['artifacts'][parent['result']['artifact_id']])
    children=deepcopy(parent['children'])
    for child in children:child['budget']=allocation(12,4)['budget']
    allocations={c['investigation_id']:allocation(12,4) for c in children}
    allocations.update({'coordinator-summary':allocation(6,3),'principal-coordinated-v2':allocation(10,4)})
    activity=read(OUT/'activity_start.json')['activity_id']
    phases=dict(coordinated=dict(project_budget={**zero(),'model_calls':40,'tool_calls':512,'wall_s':12000.},
        node_budget=allocation(12,4)['budget'],total_node_budget={**zero(),'model_calls':40,'tool_calls':64,'wall_s':9600.},
        node_count=4,node_timeout_s=2400.,tool_bindings=TOOLS,operation_allowances={t:dict(reserve_s=5.,timeout_s=30.) for t in TOOLS},
        allocations=allocations,authorized_children=children),fixed=dict(project_budget={**zero(),'tool_calls':28,'backend_solves':2,'wall_s':6000.},
        tool_bindings={**FIXED_TOOLS,'research.task_acceptance':'1.0.0'}))
    reserves=(30.,700.,150.,500.,4400.,30.,60.,30.)
    phases['fixed']['operation_allowances']={k:dict(reserve_s=v,timeout_s=v) for k,v in zip(phases['fixed']['tool_bindings'],reserves)}
    for name,p in phases.items():
        grant=dict(project_id=activity+'-'+name,grant_id=activity+'-'+name,budget=p['project_budget'],authorization_source=(OUT/'authorization.json').relative_to(ROOT).as_posix()+'; '+name)
        atomic_json(OUT/(name+'_grant.json'),grant);p.update(output='runs/'+activity+'-'+name,grant_identity=digest(grant))
    probes=dict(configurations=[dict(name='default',reasoning_effort='high',max_tokens=32768,supported=True),
        dict(name='probe1',reasoning_effort='low',max_tokens=32768,supported=True),dict(name='probe2',reasoning_effort='high',max_tokens=65536,supported=True)],
        support_source=['https://api-docs.deepseek.com/api/create-chat-completion/','https://api-docs.deepseek.com/guides/thinking_mode/'],
        verified_date='2026-10-08',live_support_probe_requests=0,
        trigger='Reasoning-only length or truncated formal return after local faults excluded; no partial fields executed',
        selection='First blocking case uses probe1, next blocking case probe2; at most two total. Role may continue its selected supported setting only after valid delivery. No other combinations.',
        subsequent='Original role ceiling, correction allowance and full actual request guard remain mandatory; evidence comparison retains valid delivery, material audit, usage and elapsed.')
    paths=subprocess.check_output(['git','ls-files','tools','schemas','extensions','configs'],text=True).splitlines()
    paths+=['tools/research_v1_continue.py','tools/research_v1_continue_gate.py']
    manifest=dict(activity_id=activity,code_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        code_identity={p:sha(ROOT/p) for p in sorted(set(paths)) if (ROOT/p).is_file()},configuration_identity=digest(cfg),phases=phases,
        frozen_at=now(),implementation_repairs_used=0,implementation_repair_ceiling=4,same_defect_repair_ceiling=2,
        conditional_length_recovery=probes,historical_parent=parent,historical_bundle_identity=digest(b),
        fixed_identity=fixed_identity(),fixed_changes=fixed_identity()['changes'],total_new_provider_requests=40,
        gates=dict(B='Two new valid reports, actual synthesis, two public principal dispositions, original evidence inspections, receipts and separate coding-agent material audit',
            C='Eight public components, changed-geometry identities, complete valid execution; physical failure is legitimate completion'),
        executability=dict(B_node_reservations=dict(model_calls=40,tool_calls=64,wall_s=9600),B_public_overhead_max=dict(tool_calls=30,wall_s=150),
            B_project=dict(model_calls=40,tool_calls=512,wall_s=12000),concurrency=2,collector='Owned application joins all submitted investigator threads before terminal close',
            C_primary_reserved_wall_s=sum(reserves),C_second='Only after engineering-invalid first; sufficient residual original grant required',
            all_role_limits_exact=True,coordinator_planning_new_inference_allowance=0),no_automatic_provider_retries=True)
    if not read(OUT/'offline_gate.json')['passed']:raise ValueError('OFFLINE_GATE_REQUIRED')
    atomic_json(OUT/'frozen_configuration.json',cfg);atomic_json(OUT/'validation_manifest.json',manifest)

def check():
    clock=read(OUT/'activity_start.json')
    if time.time()>=clock['execution_cutoff_unix']:raise ValueError('PROTECTED_DELIVERY_CUTOFF')
    m=read(OUT/'validation_manifest.json');cfg=read(OUT/'frozen_configuration.json')
    if digest(cfg)!=m['configuration_identity'] or any(sha(ROOT/p)!=h for p,h in m['code_identity'].items()):raise ValueError('FROZEN_CODE_OR_CONFIGURATION_CHANGED')
    if any(sha(ROOT/p)!=h for p,h in read(OUT/'sealed_history.json').items()):raise ValueError('SEALED_HISTORY_CHANGED')
    return m,cfg

def host_for(mode,create=False):
    m,cfg=check();p=m['phases'][mode];root=ROOT/p['output']
    if create:
        if root.exists():raise ValueError('NO_RESTART_OR_REPLACEMENT_GRANT')
        grant=read(OUT/(mode+'_grant.json'))
        if digest(grant)!=p['grant_identity']:raise ValueError('GRANT_IDENTITY_CHANGED')
        Store(root).create(grant)
        cfg['run_id']='mainline3-'+mode
        cfg['policy'].update(route=None,budget=p['project_budget'],allowed_tools=list(p['tool_bindings']),tool_bindings=p['tool_bindings'],operation_allowances=p['operation_allowances'],timeout_s=p['project_budget']['wall_s'])
        host=Host(root,cfg['run_id']);host.create(cfg);host.resume()
        atomic_json(OUT/(mode+'_launch.json'),dict(timestamp=now(),started_unix=time.time(),code_commit=m['code_commit'],manifest_identity=digest(m)))
    else:host=Host(root,'mainline3-'+mode)
    return host,m,p

def bind_sources(host,m,p):
    historical=read(OLD/'coordinated_bundle.json');parent=m['historical_parent'];oldmanifest=read(OLD/'validation_manifest.json')
    old=Store(ROOT/oldmanifest['phases']['coordinated']['output'])
    sources=parent['order']['evidence']
    for ref in sources:import_historical_provenance(host.store,historical['artifacts'][ref['artifact_id']])
    with host.store.transaction() as db:
        for ref in sources:
            if plain(host.store.put(db,historical['artifacts'][ref['artifact_id']]))!=ref:raise ValueError('SOURCE_IDENTITY_MISMATCH')
        if plain(host.store.put(db,historical['artifacts'][parent['result']['artifact_id']]))!=parent['result']:raise ValueError('PLAN_IDENTITY_MISMATCH')
        validation=plain(host.store.put(db,dict(historical_node_identity=digest(parent),old_report_valid=True,original_gate=read(OLD/'coordinated_gate.json')['gates'])))
        descriptor=dict(source_directory=oldmanifest['phases']['coordinated']['output'],source_run_id='mainline3-coordinated',source_project_id=historical['project']['project_id'],
            source_database_sha256=sha(old.db),source_node='coordinator-plan',report=parent['result'],historical_validation=validation)
        binding=dict(report=parent['result'],proposed_children=parent['children'],authorized_children=p['authorized_children'],
            delegation_per_node_budget=p['node_budget'],own_inference_allowance=0,original_budget_preserved=parent['order']['budget'])
        grant=dict(max_count=4,max_concurrency=2,allowed_tools=['evidence.read'],evidence=sources,include_completed_reports=True,
            per_node_budget=p['node_budget'],total_budget=p['total_node_budget'],output_bytes=65536,deadline_unix=read(OUT/'activity_start.json')['execution_cutoff_unix'],
            protocol_correction_limit=6,protocol_correction_role_limits=dict(principal=3,other=3),protocol_correction_per_node=3,protocol_correction_per_decision=2,
            inspected_supplemental_catalog=True,delivery_allocations=p['allocations'],conditional_length_recovery=m['conditional_length_recovery'],
            historical_handoffs=[descriptor],historical_execution_bindings={'coordinator-plan':binding})
        state=host.store.session(host.run_id,db)['state'];state.update(role_context=dict(role='principal',investigation_grant=grant),investigation_grant_identity=digest(grant))
        host.store.update_state(db,host.run_id,state)
    receipt=invoke(host,'research.investigation_handoff',descriptor,request_id='import-coordinator-plan')
    if receipt['execution_status']!='completed':raise ValueError('PUBLIC_COORDINATOR_IMPORT_FAILED: '+str(receipt.get('error')))
    atomic_json(OUT/'coordinator_import.json',dict(receipt=receipt,original_proposals=parent['children'],new_host_binding=binding,new_planning_requests=0,
        source_import_is_role_inspection=False,scope_preserved=True))
    return sources

def collect(host,key):
    node=host.store.session(host.run_id)['state']['investigations'][key]
    t=next((t for t in threading.enumerate() if t.name=='investigation-'+key),None)
    if t:t.join(max(0,node['order']['timeout_s']-(time.time()-node['started_unix']))+5)
    r=invoke(host,'research.investigation_status',dict(investigation_id=key),request_id='collect-'+key)
    if r['execution_status']!='completed':raise ValueError('PUBLIC_COLLECTION_FAILED')
    result=host.store.artifact(r['output'])
    if result['status']!='completed':
        failure=host.store.artifact(result['failure_record']) if result.get('failure_record') else None
        atomic_json(OUT/(key+'_collection_failure.json'),dict(result=result,failure=failure))
        raise ValueError('MODEL_NODE_'+result['status'].upper()+': '+encode(failure))
    atomic_json(OUT/(key+'_completed.json'),dict(result=result,receipt=r))
    return result['result']

def submit(host,order):
    r=invoke(host,'research.investigate',order,request_id='submit-'+order['investigation_id'])
    if r['execution_status']!='completed':raise ValueError('PUBLIC_SUBMISSION_FAILED: '+str(r.get('error')))
    atomic_json(OUT/(order['investigation_id']+'_submission.json'),r)
    return r

def root_order(p,key,role,question,evidence,queries):
    return plain(InvestigationOrder(investigation_id=key,role=role,question=question,evidence=evidence,queries=queries,
        budget=p['allocations'][key]['budget'],timeout_s=2400,output_bytes=65536,
        stop_conditions=['Scoped saved evidence only; zero scientific execution and retries.',
            'Exact source values and original source identities; explicit uncertainty.','Protect frozen report delivery capacity; evidence insufficiency is a valid report.']))

def stage_b(host,m,p,transport=None):
    sources=bind_sources(host,m,p)
    children=p['authorized_children']
    if transport is None:
        from examples.gvs_nmpc_route_experiment import load_credential
        load_credential(Path.home()/'.codex/.env')
    for child in children:submit(host,child)
    reports=[collect(host,c['investigation_id']) for c in children]
    targets=[dict(investigation_id=c['investigation_id'],report=r) for c,r in zip(children,reports)]
    queries=[dict(reference=r,pointer='',limit=100,byte_limit=65536) for r in reports]
    synthesis=root_order(p,'coordinator-summary','coordinator',
        'Actually synthesize both new investigator reports, including counterevidence and unknowns. Return a concise sourced investigation_return. Distinguish official historical reach and sampled settling from timing and integrity. Do not delegate, dispose, infer a dominant cause, or conduct new science. Facts may cite exact inspected report fields; scientific conclusions remain your own.',[*sources,*reports],queries)
    submit(host,synthesis);combined=collect(host,'coordinator-summary')
    # These prefetches are role-attributable operations inside the principal node reservation.
    original_queries=[dict(reference=sources[0],pointer='',offset=i,limit=15,byte_limit=4096) for i in (0,15,30)]
    original_queries.append(dict(reference=sources[1],pointer='/limitations',limit=100,byte_limit=4096))
    principal=root_order(p,'principal-coordinated-v2','principal',
        'Read the two complete new investigator reports, actual coordinator synthesis, and necessary original evidence now present in your prefetched pages. Submit exactly one formal accept/defer/reject disposition per declared report through investigation_return. Select catalog handles for report-linked support, explicit additional_support and per-source scope. Independently evaluate material claims and explicit unknowns. Official historical failure remains recorded; limited recomputation does not erase it. One-step predictions do not establish reach, settling, causality or real-robot feasibility. Adopt only supported portions, or defer/reject with precise reasons. No desired scientific conclusion is mandated.',
        [*sources,*reports,combined],[*queries,dict(reference=combined,pointer='',limit=100,byte_limit=65536),*original_queries])
    principal['disposition_ids']=[t['investigation_id'] for t in targets]
    submit(host,principal);report=collect(host,'principal-coordinated-v2')
    result=dict(status='material_audit_pending',report=report,targets=targets,coordinator_synthesis=combined,coordinator_plan=m['historical_parent']['result'],
        receipts=[],reused_planning=True,new_planning_requests=0,code_commit=m['code_commit'])
    atomic_json(OUT/'coordinated_result.json',result)
    export(OUT,'coordinated')
    return result

def close_b():
    host,m,p=host_for('coordinated');result=read(OUT/'coordinated_result.json');audit=read(OUT/'material_audit.json')
    if audit['report']!=result['report'] or audit['material_correctness']!='pass':raise ValueError('SEPARATE_MATERIAL_AUDIT_FAILED')
    decisions=host.store.artifact(result['report'])['dispositions']
    expected={t['investigation_id']:t['report'] for t in result['targets']}
    if len(decisions)!=2 or {d['investigation_id']:d['report'] for d in decisions}!=expected:raise ValueError('FORMAL_DISPOSITION_TARGETS')
    for d in decisions:
        key='dispose-'+d['investigation_id']
        # Public receipt idempotence preserves completed dispositions on incremental recovery.
        r=invoke(host,'research.investigation_disposition',d,request_id=key)
        if r['execution_status']!='completed':raise ValueError('PUBLIC_DISPOSITION_FAILED')
        if not any(x['request_id']==r['request_id'] for x in result['receipts']):result['receipts'].append(r)
        atomic_json(OUT/'coordinated_result.json',result)
    result.update(status='formal_dispositions_recorded',material_review=audit);atomic_json(OUT/'coordinated_result.json',result)
    stop(host,'NEW B GRANT COMPLETE; no historical node reopened')
    export(OUT,'coordinated')
    from tools.research_v1_continue_gate import generate_b
    gate=generate_b();atomic_json(OUT/'coordinated_gate.json',gate)
    if not gate['passed']:raise ValueError('B_GATE_FAILED')
    return execute_c()

def execute_c():
    if not read(OUT/'coordinated_gate.json')['passed']:raise ValueError('B_GATE_REQUIRED')
    host,m,p=host_for('fixed',create=True);cfg=host.store.session(host.run_id)['snapshot']['input']
    from schemas.platform_analysis import TaskAnalysisProtocol,EndpointTarget
    source=cfg['policy']['candidate_builder']['parameters']['data']['semantic_source']
    protocol=TaskAnalysisProtocol(baseline_lengths_m={c['id']:c['length_m'] for c in source['components'] if c['kind']=='flexible_segment'},duration_s=cfg['task']['timing']['duration_s'],period_s=cfg['task']['timing']['control_period_s'],frequency_rad_s=[.1,1.,10.])
    target=EndpointTarget(position_m=cfg['task']['goal']['data']['target_m'],position_tolerance_m=cfg['task']['evaluator']['parameters']['data']['tolerance_m'],position_scale_m=.01)
    with host.store.transaction() as db:pr=plain(host.store.put(db,protocol));tr=plain(host.store.put(db,target))
    try:
        result=fixed_pipeline(host,changes=m['fixed_changes'],protocol=pr,target=tr,execute_backend=True)
        evaluation=result['receipts'][5];profile=result['receipts'][6]
        configuration_ref=host.store.artifact(profile['output'])['detail']['configuration']
        joint=invoke(host,'research.task_acceptance',dict(configuration=configuration_ref,evaluation=evaluation['output'],profile=profile['output']),request_id='fixed-joint-acceptance')
        result['receipts'].append(joint)
        if joint['execution_status']!='completed':raise ValueError('PUBLIC_JOINT_ACCEPTANCE_FAILED')
        result.update(joint_acceptance=host.store.artifact(joint['output'])['detail'],code_commit=m['code_commit'])
        atomic_json(OUT/'fixed_result.json',result)
    finally:
        stop(host,'FIXED C TERMINAL; physical failure never authorizes tuning or improved-result rerun')
        export(OUT,'fixed')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['start','freeze','execute-b','close-b','check']);args=parser.parse_args()
    if args.action=='start':start()
    elif args.action=='freeze':freeze()
    elif args.action=='check':check()
    elif args.action=='close-b':close_b()
    else:
        host,m,p=host_for('coordinated',create=True)
        try:stage_b(host,m,p)
        except Exception:
            for t in [t for t in threading.enumerate() if t.name.startswith('investigation-')]:t.join(2405)
            stop(host,'NEW B BLOCKED; preserve partial results and uncertain reservations');export(OUT,'coordinated');raise

if __name__=='__main__':main()
