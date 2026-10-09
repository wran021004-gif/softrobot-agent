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
REUSE=ROOT/'evidence/research_mainline3_v1_complete_20261009'
OUT=ROOT/'evidence/research_mainline3_v1_closeout_20261009'
REACH_REUSE=ROOT/'evidence/research_mainline3_v1_closeout_20261009'

def reuse_both():
    path=OUT/'authorization.json'
    return path.exists() and read(path).get('reuse_both_reports',False)

def administrative_policy():
    return dict(version='mainline3.shared_completion@2.0.0',input_estimate_ceiling=950000,
        context_limit_tokens=1000000,output_reservation=32768,interaction_reservation=8192,
        context_bytes=4194304,report_bytes=1048576,request_timeout_s=600.,
        node_lifetime='Remaining overall activity time less 6000 seconds for C and 1800 for delivery',
        provider_requests=40,investigator_requests=0,planning_requests=0,A_reruns=0,
        correction_rule='Shared request budget; actionable corrections only, stop unchanged failures',
        historical_activity='mainline3-v1-complete-fedcd7c1a3a9',historical_records_unchanged=True)
TOOLS={k:'1.0.0' for k in ('research.investigate','research.investigation_status','research.investigation_read','research.investigation_disposition','research.investigation_handoff')}
PRIOR_FAILED=[
 'tests.test_research_investigation_closeout.InvestigationCloseoutTests.test_paginated_original_pointer_binding',
 'tests.test_research_investigation_closeout.InvestigationCloseoutTests.test_principal_claim_links_values_identities_scope_and_defer',
 'tests.test_research_investigation_closeout.InvestigationCloseoutTests.test_scope_budget_and_complete_outgoing_overflow',
 'tests.test_research_mainline3.Mainline3EngineeringTests.test_unconfirmed_recovery_no_redispatch_and_confirmed_failure']

def task_allocations():
    if reuse_both():
        seconds=max(1.,read(OUT/'activity_start.json')['started_unix']+28200-read(OUT/'activity_start.json')['started_unix'])
        return {key:dict(budget={**zero(),'model_calls':40,'tool_calls':128,'wall_s':seconds},
            exploration_requests=32,protected_delivery_requests=1,timeout_s=seconds)
            for key in ('coordinator-summary','principal-coordinated-v2')}
    # Purpose remains accounting metadata; only the task ceiling limits calls.
    limits={'reach-holding-interpretation':(12,16,3600.,4,2),
        'timing-integrity-limits':(4,8,1200.,1,2),
        'coordinator-summary':(6,12,1800.,3,2),
        'principal-coordinated-v2':(18,24,3600.,4,14)}
    return {key:dict(budget={**zero(),'model_calls':calls,'tool_calls':ops,'wall_s':seconds},
        exploration_requests=reads,protected_delivery_requests=protected,
        timeout_s=seconds) for key,(calls,ops,seconds,protected,reads) in limits.items()}

def correction_policy():
    if reuse_both():
        return dict(version='mainline3.shared_completion@2.0.0',planned=2,maximum=40,
            extension='Concrete actionable correction under shared budget; unchanged failure and feedback stop',
            targets={key:dict(report='report:'+key,dispositions={t:'disposition:'+t for t in
                ('reach-holding-interpretation','timing-integrity-limits')} if key.startswith('principal') else {})
                for key in task_allocations()},accounting='New project ledger; shared 40 requests without role or purpose partitions')
    return dict(version='mainline3.target_corrections@1.0.0',planned=2,maximum=4,
        extension='Latest saved output and precise actionable feedback; unchanged failing field and feedback stop; no cosmetic extensions',
        targets={key:dict(report='report:'+key,dispositions={target:'disposition:'+target
            for target in ('reach-holding-interpretation','timing-integrity-limits')} if key=='principal-coordinated-v2' else {})
            for key in task_allocations()},
        accounting='Project ledger; stable targets exclude report versions, session and dispatch IDs; engineering recovery is separate')

def start(authorization=None, started_unix=None, *, reuse_both_reports=False):
    if OUT.exists():raise ValueError('NEW_ACTIVITY_ALREADY_EXISTS')
    OUT.mkdir(parents=True)
    # First user task turn, including preparation and tool approval wait.
    began=time.time() if started_unix is None else started_unix
    from datetime import datetime,timezone
    atomic_json(OUT/'activity_start.json',dict(activity_id='mainline3-v1-complete-'+uuid4().hex[:12],started_unix=began,
        deadline_unix=began+36000,execution_cutoff_unix=began+34200,started_at=datetime.fromtimestamp(began,timezone.utc).isoformat(),
        reviewed_baseline='e89712c6b8a07df4e712711bc2edb2836f93f953',observed_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        remote_fetch='Target branch fetched once; inspect any advancement and preserve completed work',
        includes='Preparation, repairs, pauses, offline review, live execution and delivery'))
    atomic_json(OUT/'authorization.json',dict(source=str(authorization) if authorization else 'Offline fixture',
        text=Path(authorization).read_text(encoding='utf-8-sig') if authorization else 'Offline fixture only',
        recipient='https://api.deepseek.com',model='deepseek-flash',thinking='enabled',reasoning_effort='high',tool_choice='auto',max_tokens=32768,
        data_scope='Only non-secret task-scoped research data through existing credential loader',A_new_requests=0,B_new_requests=40,
        task_allocations=task_allocations(),correction_policy=correction_policy(),probes=2,
        post_freeze_repairs=4,same_defect_repair_cycles=2,B_tools=512,B_wall_s=12000,C_tools=28,C_wall_s=6000,
        C_models=0,C_backend_executions=2,C_second_execution='Engineering invalid/incomplete only, unchanged science',
        deadline_hours=10,delivery_protection_minutes=30,investigator_concurrency=1,ordinary_push_branch='feat/gvs-dynamics',
        forbidden='Parameter optimization, paid A rerun, extra scientific cases, V2 experiments, force push, uncertain request retransmission'))
    if reuse_both_reports:
        auth=read(OUT/'authorization.json');auth.update(reuse_both_reports=True,administrative_policy=administrative_policy(),
            post_freeze_repairs='Scoped automatic repairs under cumulative overall budget',same_defect_repair_cycles='Stop unchanged feedback',
            B_wall_s=28200.,C_tools=28,probes=0)
        atomic_json(OUT/'authorization.json',auth)
        auth.update(task_allocations=task_allocations(),correction_policy=correction_policy())
        atomic_json(OUT/'authorization.json',auth)
        atomic_json(OUT/'administrative_policy.json',administrative_policy())
    previous=ROOT/'evidence/research_mainline3_v1_continue_20261008'
    paths=[ROOT/'runs/stage336_manual_20261001_090616/platform.sqlite']
    for olddir in (OLD,previous,REUSE,REACH_REUSE) if reuse_both_reports else (OLD,previous,REUSE):
        paths.extend(p for p in olddir.rglob('*') if p.is_file())
        oldmanifest=read(olddir/'validation_manifest.json')
        paths.extend(ROOT/p['output']/'platform.sqlite' for p in oldmanifest['phases'].values() if (ROOT/p['output']/'platform.sqlite').exists())
    atomic_json(OUT/'sealed_history.json',{p.relative_to(ROOT).as_posix():sha(p) for p in paths})
    facts=read(previous/'delivery_facts.json')
    atomic_json(OUT/'historical_uncertainties.json',dict(previous_delivery=(REUSE/'delivery_facts.json').relative_to(ROOT).as_posix(),
        sealed_delivery=read(REUSE/'delivery_facts.json'),
        no_old_nodes_reopened=True,no_search_for_missing_bodies=True))
    atomic_json(OUT/'A_preserved.json',dict(source=(previous/'A_preserved.json').relative_to(ROOT).as_posix(),gate=read(previous/'A_preserved.json'),
        coverage='Historical investigator reports reused; new principal dispositions in prior activity. No new A model/investigator/scientific work.',
        new_requests=0,accepted=True))
    atomic_json(OUT/'prior_failed_checks.json',dict(source=(previous/'delivery_facts.json').relative_to(ROOT).as_posix(),records=facts['prior_failed_checks'],exact_names=PRIOR_FAILED))

def allocation(ordinary,correction,recovery,protected):
    total=ordinary+correction+recovery
    return dict(budget={**zero(),'model_calls':total,'tool_calls':16,'wall_s':2400.},
        request_purposes=dict(ordinary=ordinary,model_correction=correction,engineering_recovery=recovery),
        exploration_requests=min(ordinary-1,total-protected),protected_delivery_requests=protected,first_submission_ordinary_reserve=1)

def config():
    cfg=model_configuration(configuration())
    cfg['policy']['model'].update(adapter_version='8.0.0',parameters=dict(investigation_contract='selected_reports_v4'),timeout_s=600.)
    if reuse_both():cfg['policy']['model']['context_bytes']=4194304
    return cfg


def sequential_reservation_plan(preparation_s):
    if reuse_both():
        return dict(version='mainline3.shared_completion@2.0.0',preparation_s=preparation_s,public_overhead_protected_s=150.,
            nodes={'coordinator-summary':dict(reserve_s=28200.,minimum_dispatch_s=600.,protected_s=0.,downstream=['principal-coordinated-v2']),
                'principal-coordinated-v2':dict(reserve_s=28200.,minimum_dispatch_s=600.,protected_s=1200.,downstream=[])})
    # Maximum task allowances remain unchanged; dormant timing is not reserved.
    nodes={
        'reach-holding-interpretation':dict(reserve_s=1800.,minimum_dispatch_s=600.,protected_s=600.,downstream=['coordinator-summary','principal-coordinated-v2']),
        'timing-integrity-limits':dict(reserve_s=1200.,minimum_dispatch_s=300.,protected_s=0.,downstream=['coordinator-summary','principal-coordinated-v2'],dormant=True),
        'coordinator-summary':dict(reserve_s=1200.,minimum_dispatch_s=600.,protected_s=600.,downstream=['principal-coordinated-v2']),
        'principal-coordinated-v2':dict(reserve_s=2400.,minimum_dispatch_s=1200.,protected_s=1200.,downstream=[])}
    minimum=sum(n['minimum_dispatch_s'] for n in nodes.values() if not n.get('dormant'))+150.
    if preparation_s+minimum>12000:raise ValueError('B_PREPARATION_AND_PROTECTED_REMAINING_WORK_INSUFFICIENT: '+encode(dict(preparation_s=preparation_s,minimum_remaining_s=minimum,ceiling_s=12000.)))
    return dict(version='mainline3.sequential_reservations@1.0.0',nodes=nodes,public_overhead_protected_s=150.,
        preparation_s=preparation_s,preparation_charged_once=True,maximum_node_allowances_s=10200.,
        initial_mandatory_reservations_s=5400.,minimum_remaining_s=minimum,
        rationale='Reserve at actual sequential dispatch from existing ledger remaining capacity, protect downstream delivery, release unused confirmed reservations on settlement. Optional timing needs a concrete necessary revision. No transfer of request allocations or previous activity allowances.')

def freeze():
    if (OUT/'validation_manifest.json').exists():raise ValueError('ALREADY_FROZEN')
    cfg=config();_no_secrets(cfg)
    b=read(OLD/'coordinated_bundle.json');parent=b['state']['investigations']['coordinator-plan']
    if parent['status']!='completed':raise ValueError('VALID_HISTORICAL_PLAN_REQUIRED')
    InvestigationReturn.model_validate(b['artifacts'][parent['result']['artifact_id']])
    children=deepcopy(parent['children'])
    allocations=task_allocations()
    for child in children:
        if not reuse_both():
            child['budget']=allocations[child['investigation_id']]['budget']
            child['timeout_s']=allocations[child['investigation_id']]['timeout_s']
    activity=read(OUT/'activity_start.json')['activity_id']
    phases=dict(coordinated=dict(project_budget={**zero(),'model_calls':40,'tool_calls':512,'wall_s':12000.},
        node_budget={**zero(),'model_calls':18,'tool_calls':24,'wall_s':3600.},total_node_budget={**zero(),'model_calls':40,'tool_calls':60,'wall_s':10200.},
        node_count=4,node_timeout_s=3600.,correction_policy=correction_policy(),tool_bindings=TOOLS,operation_allowances={t:dict(reserve_s=5.,timeout_s=30.) for t in TOOLS},
        allocations=allocations,authorized_children=children),fixed=dict(project_budget={**zero(),'tool_calls':28,'backend_solves':2,'wall_s':6000.},
        tool_bindings={**FIXED_TOOLS,'research.task_acceptance':'1.0.0'}))
    reserves=(30.,700.,150.,500.,4400.,30.,60.,30.)
    if reuse_both():
        shared={**zero(),'model_calls':40,'tool_calls':256,'wall_s':28200.}
        phases['coordinated'].update(project_budget={**shared,'tool_calls':512},node_budget=allocations['coordinator-summary']['budget'],
            total_node_budget=shared,node_count=2,node_timeout_s=28200.)
    phases['fixed']['operation_allowances']={k:dict(reserve_s=v,timeout_s=v) for k,v in zip(phases['fixed']['tool_bindings'],reserves)}
    for name,p in phases.items():
        grant=dict(project_id=activity+'-'+name,grant_id=activity+'-'+name,budget=p['project_budget'],authorization_source=(OUT/'authorization.json').relative_to(ROOT).as_posix()+'; '+name)
        atomic_json(OUT/(name+'_grant.json'),grant);p.update(output='runs/'+activity+'-'+name,grant_identity=digest(grant))
    probes=dict(configurations=[dict(name='default',reasoning_effort='high',max_tokens=32768,supported=True),
        dict(name='probe1',reasoning_effort='low',max_tokens=32768,supported=True),dict(name='probe2',reasoning_effort='high',max_tokens=65536,supported=True)],
        support_source=['https://api-docs.deepseek.com/api/create-chat-completion/','https://api-docs.deepseek.com/guides/thinking_mode/'],
        verified_date='2026-10-09',live_support_probe_requests=0,
        trigger='Reasoning-only length or truncated formal return after local faults excluded; no partial fields executed',
        selection='First blocking case uses probe1, next blocking case probe2; at most two total. Role may continue its selected supported setting only after valid delivery. No other combinations.',
        subsequent='Original role ceiling, correction allowance and full actual request guard remain mandatory; evidence comparison retains valid delivery, material audit, usage and elapsed.')
    if reuse_both():probes.update(configurations=probes['configurations'][:1],trigger='No configuration probes authorized; preserve high effort and 32768 output')
    paths=subprocess.check_output(['git','ls-files','tools','schemas','extensions','configs'],text=True).splitlines()
    paths+=['tools/research_v1_continue.py','tools/research_v1_continue_gate.py']
    manifest=dict(activity_id=activity,code_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        code_identity={p:sha(ROOT/p) for p in sorted(set(paths)) if (ROOT/p).is_file()},configuration_identity=digest(cfg),phases=phases,
        frozen_at=now(),implementation_repairs_used=0,implementation_repair_ceiling=4,same_defect_repair_ceiling=2,
        conditional_length_recovery=probes,historical_parent=parent,historical_bundle_identity=digest(b),
        fixed_identity=fixed_identity(),fixed_changes=fixed_identity()['changes'],total_new_provider_requests=40,
        gates=dict(B='One new valid reach report, imported valid historical timing report or explicitly necessary revision, actual synthesis of selected versions, two public principal dispositions, original evidence inspections, receipts and separate coding-agent material audit',
            C='Eight public components, changed-geometry identities, complete valid execution; physical failure is legitimate completion'),
        executability=dict(B_node_reservations=dict(model_calls=40,tool_calls=60,wall_s=10200),B_public_overhead_max=dict(tool_calls=30,wall_s=150),
            B_project=dict(model_calls=40,tool_calls=512,wall_s=12000),concurrency=1,collector='Sequential submission and collection; deadlines start at actual dispatch',
            C_primary_reserved_wall_s=sum(reserves),C_second='Only after engineering-invalid first; sufficient residual original grant required',
            all_role_limits_exact=True,coordinator_planning_new_inference_allowance=0),no_automatic_provider_retries=True)
    if not read(OUT/'offline_gate.json')['passed']:raise ValueError('OFFLINE_GATE_REQUIRED')
    from tools.research_v1_continue_gate import correction_consistency
    if not correction_consistency(read(OUT/'authorization.json'),phases['coordinated'],orders=children)['passed']:
        raise ValueError('CORRECTION_POLICY_CONSISTENCY_REQUIRED')
    manifest['preparation_wall_s']=max(0,time.time()-read(OUT/'activity_start.json')['started_unix'])
    phases['coordinated']['sequential_reservations']=sequential_reservation_plan(manifest['preparation_wall_s'])
    manifest['executability']['B_node_reservations']=dict(maximum_allowances=manifest['executability']['B_node_reservations'],
        actual_dispatch_plan=phases['coordinated']['sequential_reservations'])
    manifest['timing_reuse']=dict(directory=REUSE.relative_to(ROOT).as_posix(),report=read(REUSE/'coordinated_bundle.json')['state']['investigations']['timing-integrity-limits']['result'],
        material_audit_identity=digest(read(REUSE/'timing_material_audit.json')),new_timing_request_required=False)
    if reuse_both():
        manifest.update(administrative_policy=administrative_policy(),linked_stopped_activity=read(REACH_REUSE/'activity_start.json')['activity_id'],
            implementation_repair_ceiling=None,same_defect_repair_ceiling=None)
        manifest['reach_reuse']=dict(directory=REACH_REUSE.relative_to(ROOT).as_posix(),
            report=read(REACH_REUSE/'coordinated_bundle.json')['state']['investigations']['reach-holding-interpretation']['result'],
            material_audit_identity=digest(read(REACH_REUSE/'reach_material_audit.json')),new_reach_request_required=False)
        manifest['gates']['B']='Verified reuse of both completed reports, actual fresh synthesis, two formal principal dispositions and material review'
        manifest['executability'].update(B_project=phases['coordinated']['project_budget'],
            B_node_reservations=dict(shared_request_ceiling=40,node_envelope=phases['coordinated']['node_budget'],actual_dispatch_plan=phases['coordinated']['sequential_reservations']))
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
        if mode=='coordinated':
            elapsed=m['preparation_wall_s'];cost={**zero(),'wall_s':elapsed}
            row,fresh=host.store.reserve(host.run_id,'offline-preparation',digest(dict(manifest=digest(m),elapsed=elapsed)),'coding-agent-preparation',cost,kind='engineering_preparation')
            if fresh:host.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],tool_id='engineering.preparation',tool_version='1.0.0',execution_status='completed',caller='coding-agent-preparation',charged=zero(),cache_hit=False),dict(coverage='Conservative entire pre-freeze interval, including offline checks, review and approval wait; shell operations are engineering, not public evidence reads'),elapsed=elapsed,actual_cost=cost,kind='engineering_preparation')
        atomic_json(OUT/(mode+'_launch.json'),dict(timestamp=now(),started_unix=time.time(),code_commit=m['code_commit'],manifest_identity=digest(m)))
    else:host=Host(root,p.get('active_run_id','mainline3-'+mode))
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
        grant=dict(max_count=p['node_count'],max_concurrency=1,allowed_tools=['evidence.read'],evidence=list(sources),include_completed_reports=True,
            per_node_budget=p['node_budget'],total_budget=p['total_node_budget'],output_bytes=65536,deadline_unix=read(OUT/'activity_start.json')['execution_cutoff_unix'],
            correction_policy=p['correction_policy'],
            sequential_reservations=p['sequential_reservations'],
            inspected_supplemental_catalog=True,delivery_allocations=p['allocations'],conditional_length_recovery=m['conditional_length_recovery'],
            historical_handoffs=[descriptor],historical_execution_bindings={'coordinator-plan':binding})
        if reuse_both():grant.update(output_bytes=1048576,deadline_unix=read(OUT/'activity_start.json')['started_unix']+28200.)
        prior=read(REUSE/'coordinated_bundle.json')
        grant['imported_query_results']={}
        for key in (c['investigation_id'] for c in p['authorized_children']):
            pages=[]
            for r in prior['state']['investigations'][key]['reads']:
                if r.get('metadata_only') or r['reference'] not in sources or 'query' not in r:continue
                if any(x['query']==r['query'] for x in pages):continue
                pages.append(dict(r,imported_from=dict(activity=prior['project']['project_id'],run='mainline3-coordinated-repair1',investigation_id=key)))
            grant['imported_query_results'][key]=pages
        from tools.research_v1_continue_gate import correction_consistency
        consistency=correction_consistency(read(OUT/'authorization.json'),p,grant=grant,orders=p['authorized_children'])
        if not consistency['passed']:raise ValueError('CORRECTION_POLICY_CONSISTENCY_REQUIRED')
        state=host.store.session(host.run_id,db)['state'];state.update(role_context=dict(role='principal',investigation_grant=grant),investigation_grant_identity=digest(grant))
        host.store.update_state(db,host.run_id,state)
    receipt=invoke(host,'research.investigation_handoff',descriptor,request_id='import-coordinator-plan')
    if receipt['execution_status']!='completed':raise ValueError('PUBLIC_COORDINATOR_IMPORT_FAILED: '+str(receipt.get('error')))
    atomic_json(OUT/'coordinator_import.json',dict(receipt=receipt,original_proposals=parent['children'],new_host_binding=binding,new_planning_requests=0,
        source_import_is_role_inspection=False,scope_preserved=True))
    import_timing(host,m)
    if reuse_both():import_report(host,m,'reach-holding-interpretation',REACH_REUSE,'reach_reuse','reach')
    return sources


def import_timing(host,m):
    if reuse_both():return import_report(host,m,'timing-integrity-limits',REUSE,'timing_reuse','timing')
    bundle=read(REUSE/'coordinated_bundle.json');manifest=read(REUSE/'validation_manifest.json');phase=manifest['phases']['coordinated']
    run=phase.get('active_run_id','mainline3-coordinated');old=Store(ROOT/phase['output'])
    node=old.session(run)['state']['investigations']['timing-integrity-limits'];report=node['result']
    if report!=m['timing_reuse']['report'] or node['status']!='completed':raise ValueError('TIMING_REUSE_VERSION_CHANGED')
    with host.store.transaction() as db:
        if plain(host.store.put(db,old.artifact(report)))!=report:raise ValueError('TIMING_REUSE_IDENTITY_CHANGED')
        validation=plain(host.store.put(db,dict(historical_node_identity=digest(node),formal_valid=True,material_audit=read(REUSE/'timing_material_audit.json'),unqualified_adoption_supported=False)))
        descriptor=dict(source_directory=phase['output'],source_run_id=run,source_project_id=bundle['project']['project_id'],source_database_sha256=sha(old.db),source_node='timing-integrity-limits',report=report,historical_validation=validation)
        state=host.store.session(host.run_id,db)['state'];grant=state['role_context']['investigation_grant']
        grant['historical_handoffs'].append(descriptor)
        # Audit is supplied as limitations, with original identity and provenance.
        grant['evidence'].append(validation);state['investigation_grant_identity']=digest(grant)
        host.store.update_state(db,host.run_id,state)
    receipt=invoke(host,'research.investigation_handoff',descriptor,request_id='import-timing-report')
    if receipt['execution_status']!='completed':raise ValueError('PUBLIC_TIMING_IMPORT_FAILED: '+str(receipt.get('error')))
    atomic_json(OUT/'timing_import.json',dict(receipt=receipt,report=report,provenance=descriptor,limitations=validation,new_provider_requests=0,source_inspection_not_implied=True))
    return report

def import_report(host,m,key,directory,manifest_key,label):
    manifest=read(directory/'validation_manifest.json');phase=manifest['phases']['coordinated']
    run=phase.get('active_run_id','mainline3-coordinated');old=Store(ROOT/phase['output'])
    node=old.session(run)['state']['investigations'][key];report=node['result']
    if report!=m[manifest_key]['report'] or node['status']!='completed':raise ValueError('REUSE_VERSION_CHANGED')
    for ref in node['order']['evidence']:import_historical_provenance(host.store,old.artifact(ref))
    with host.store.transaction() as db:
        if plain(host.store.put(db,old.artifact(report)))!=report:raise ValueError('REUSE_IDENTITY_CHANGED')
        for ref in node['order']['evidence']:
            body=old.artifact(ref)
            if plain(host.store.put(db,body))!=ref:raise ValueError('REUSE_SOURCE_IDENTITY_CHANGED')
        validation=plain(host.store.put(db,dict(historical_node_identity=digest(node),formal_valid=True,
            material_audit=read(directory/(label+'_material_audit.json')),unqualified_adoption_supported=False)))
        descriptor=dict(source_directory=phase['output'],source_run_id=run,source_project_id=old.config()['project_id'],
            source_database_sha256=sha(old.db),source_node=key,report=report,historical_validation=validation)
        state=host.store.session(host.run_id,db)['state'];grant=state['role_context']['investigation_grant']
        grant['historical_handoffs'].append(descriptor);grant['evidence'].append(validation)
        state['investigation_grant_identity']=digest(grant);host.store.update_state(db,host.run_id,state)
    receipt=invoke(host,'research.investigation_handoff',descriptor,request_id='import-'+label+'-report')
    if receipt['execution_status']!='completed':raise ValueError('PUBLIC_REPORT_IMPORT_FAILED: '+str(receipt.get('error')))
    atomic_json(OUT/(label+'_import.json'),dict(receipt=receipt,report=report,provenance=descriptor,
        limitations=validation,new_provider_requests=0,source_inspection_not_implied=True))
    return report

def collect(host,key):
    node=host.store.session(host.run_id)['state']['investigations'][key]
    t=next((t for t in threading.enumerate() if t.name=='investigation-'+key),None)
    if t:t.join(max(0,node.get('execution_deadline_unix',node['started_unix']+node['order']['timeout_s'])-time.time())+5)
    r=invoke(host,'research.investigation_status',dict(investigation_id=key),request_id='collect-'+key)
    if r['execution_status']!='completed':raise ValueError('PUBLIC_COLLECTION_FAILED: '+str(r.get('error')))
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
        budget=p['allocations'][key]['budget'],timeout_s=p['allocations'][key].get('timeout_s',2400),output_bytes=1048576 if reuse_both() else 65536,
        stop_conditions=['Scoped saved evidence only; zero scientific execution and retries.',
            'Exact source values and original source identities; explicit uncertainty.','Protect frozen report delivery capacity; evidence insufficiency is a valid report.']))

def stage_b(host,m,p,transport=None):
    session=host.store.session(host.run_id)
    sources=m['historical_parent']['order']['evidence'] if 'coordinator-plan' in session['state'].get('historical_investigations',{}) else bind_sources(host,m,p)
    children=p['authorized_children']
    if transport is None:
        from examples.gvs_nmpc_route_experiment import load_credential
        load_credential(Path.home()/'.codex/.env')
    reports=[]
    for child in children:
        if reuse_both():
            label='reach' if child['investigation_id'].startswith('reach') else 'timing'
            reports.append(read(OUT/(label+'_import.json'))['report']);continue
        if child['investigation_id']=='timing-integrity-limits':
            reports.append(read(OUT/'timing_import.json')['report']);continue
        if child['investigation_id'] not in host.store.session(host.run_id)['state'].get('investigations',{}):submit(host,child)
        reports.append(collect(host,child['investigation_id']))
    targets=[dict(investigation_id=c['investigation_id'],report=r) for c,r in zip(children,reports)]
    queries=[dict(reference=r,pointer='',limit=100,byte_limit=1048576 if reuse_both() else 65536) for r in reports]
    limitations=[read(OUT/(label+'_import.json'))['limitations'] for label in ('reach','timing')] if reuse_both() else []
    synthesis=root_order(p,'coordinator-summary','coordinator',
        'Actually synthesize the new reach report and imported historical timing report, including counterevidence and unknowns. Cite inspected fields from BOTH selected report versions. Timing material audit identifies false-as-unavailable and absent /official field interpretations; use archived recomputation presentation to distinguish available failed results. Do not silently adopt these incorrect claims. Return a concise sourced investigation_return with supported observations and unresolved causes. Do not delegate, dispose, or conduct science.',[*sources,*reports],queries)
    if reuse_both():
        synthesis['question']='Read both complete reused reports and their material audits. Synthesize supported Stage 3.36 observations, agreements/conflicts, erroneous interpretations excluded, and unknown causes/implications. Available recomputations with value false record failed criteria; they are not missing computations. /official lacks recomputation fields. Reach audit also flags unnecessary proposed rechecking of known failures. These historical observations do not describe the promoted candidate or future C. Cite inspected fields of BOTH reports; original citations require inspecting the original relevant content via evidence_read first. Return investigation_return, with concise prose preferred but no prose-length cap. No delegation, dispositions or scientific execution.'
        synthesis['evidence'].extend(limitations)
        synthesis['queries'].extend(dict(reference=r,pointer='/material_audit',limit=100,byte_limit=4096) for r in limitations)
    if 'coordinator-summary' not in host.store.session(host.run_id)['state'].get('investigations',{}):submit(host,synthesis)
    combined=collect(host,'coordinator-summary')
    # These prefetches are role-attributable operations inside the principal node reservation.
    original_queries=[dict(reference=r,pointer='',limit=100,byte_limit=65536) for r in sources]
    timing_limitations=read(OUT/'timing_import.json')['limitations']
    original_queries.append(dict(reference=timing_limitations,pointer='/material_audit/defects',limit=100,byte_limit=4096))
    principal=root_order(p,'principal-coordinated-v2','principal',
        'Read the complete new reach report, imported historical timing report, actual synthesis and original sources in prefetched pages. Submit exactly one formal accept/defer/reject disposition per declared report. Timing audit identifies false-as-unavailable and absent /official recomputation-field errors: evaluate these and adopt only supported portions or defer/reject. Use catalog handles, explicit additional_support and separate scope for EVERY source cited in each adopted claim. Historical reach/holding failure remains recorded; predictions do not establish acceptance, causality or real-robot feasibility. Select conclusions independently. No new science.',
        [*sources,*reports,combined,timing_limitations],[*queries,dict(reference=combined,pointer='',limit=100,byte_limit=1048576 if reuse_both() else 65536),*original_queries])
    principal['disposition_ids']=[t['investigation_id'] for t in targets]
    if reuse_both():
        principal['question']='Inspect both complete reused reports, synthesis, audits and key original evidence. Return exactly one formal accept/defer/reject disposition per declared report version. Partial adoption is valid; explicitly exclude erroneous interpretations (false recomputation means available failed criterion, not missing evidence; /official lacks recomputation fields; known failed criteria need no rerun to establish failure). Explain supported observations and remaining unknown causes. All original observations are Stage 3.36, not promoted candidate or future C. Use catalog handles with exact supporting report facts, additional_support for original evidence, and separate inspected scope for EVERY cited source. No forced acceptance, new science or whole-report investigator rewrites. Concise prose preferred.'
        reach_limitations=read(OUT/'reach_import.json')['limitations']
        principal['evidence'].append(reach_limitations)
        principal['queries'].append(dict(reference=reach_limitations,pointer='/material_audit',limit=100,byte_limit=4096))
    if 'principal-coordinated-v2' not in host.store.session(host.run_id)['state'].get('investigations',{}):submit(host,principal)
    report=collect(host,'principal-coordinated-v2')
    result=dict(status='material_audit_pending',report=report,targets=targets,coordinator_synthesis=combined,coordinator_plan=m['historical_parent']['result'],
        receipts=[],reused_planning=True,new_planning_requests=0,code_commit=m['code_commit'])
    atomic_json(OUT/'coordinated_result.json',result)
    export(OUT,'coordinated',run_id=host.run_id)
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
    export(OUT,'coordinated',run_id=host.run_id)
    from tools.research_v1_continue_gate import generate_b
    gate=generate_b();atomic_json(OUT/'coordinated_gate.json',gate)
    if not gate['passed']:raise ValueError('B_GATE_FAILED')
    return execute_c()

def execute_c():
    if not read(OUT/'coordinated_gate.json')['passed']:raise ValueError('B_GATE_REQUIRED')
    manifest=read(OUT/'validation_manifest.json')
    host,m,p=host_for('fixed',create=not (ROOT/manifest['phases']['fixed']['output']).exists());cfg=host.store.session(host.run_id)['snapshot']['input']
    if (OUT/'fixed_result.json').exists():return read(OUT/'fixed_result.json')
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

def bind_repair(record=None):
    """One explicit version migration in the original grant; no STOP revival."""
    m=read(OUT/'validation_manifest.json');p=m['phases']['coordinated'];old_run=p.get('active_run_id','mainline3-coordinated')
    if p.get('sequential_reservations'):
        if not record:raise ValueError('CONCRETE_REPAIR_RECORD_REQUIRED')
        return bind_current_repair(m,p,old_run,record)
    store=Store(ROOT/p['output']);old=store.session(old_run)
    if old['status']!='stopped' or m['implementation_repairs_used']>=4:raise ValueError('BOUNDED_STOPPED_REPAIR_REQUIRED')
    saved=read(OUT/'coordinated_bundle.json');atomic_json(OUT/'coordinated_bundle_before_repair1.json',saved)
    # Full reception and original cumulative usage, not body reconstruction, establish
    # that this NEW request ended in a local admission failure. Supplier billing stays unknown.
    timing=old['state']['investigations']['timing-integrity-limits']
    row=store.lookup(old_run,'investigation-timing-integrity-limits')
    failure=store.artifact(timing['failure_record'])
    reception=[e for e in store.events(old_run) if e['kind']=='investigation_reception' and e.get('request_id')==row['request_id']
        and store.artifact(e['outputs'][0]).get('complete_body_received') is True]
    omitted=[e for e in reception if store.artifact(e['outputs'][0]).get('omission_reason')=='sensitive_response_text; original body not retained']
    if not omitted or failure['progress']['transport_callable_invocations']!=timing['usage']['model_calls'] or failure['progress']['response_body_received'] is not True:
        raise ValueError('ORIGINAL_REQUEST_UNCONFIRMED_NO_RETRANSMISSION')
    d=InvestigationDispatcher(Host(store.root,old_run))
    if not row['receipt']:
        receipt=store.complete(row,d._receipt(row,'failed','CONFIRMED_FULL_RECEPTION_BODY_OMITTED; contents and supplier usage unknown'),
            elapsed=failure['elapsed_s'],actual_cost=timing['usage'],kind='investigation')
        with store.transaction() as db:
            ref=store.put(db,dict(original_request=row['request_id'],original_execution=row['execution_id'],original_failure=timing['failure_record'],
                reception_event=omitted[-1]['event_id'],known_complete_reception=True,body_unavailable=True,provider_charge_unknown=True,receipt=receipt,
                determination='Confirmed local admission failure; actual local requests/reads/time settle. No body recovered and no zero-cost claim.'))
            store.event(db,old_run,'investigation_request_reconciliation','confirmed_local_failure',request=row['request_id'],execution=row['execution_id'],outputs=[ref])
        atomic_json(OUT/'new_timing_reconciliation.json',store.artifact(ref))
    if any(c['status'] in ('running','unknown') for c in saved['calls'] if c['request_id']!='investigation-timing-integrity-limits'):
        raise ValueError('OTHER_UNCONFIRMED_REQUEST_NO_REPAIR_DISPATCH')
    new_run='mainline3-coordinated-repair1'
    cfg=deepcopy(old['snapshot']['input']);cfg['run_id']=new_run
    host=Host(store.root,new_run);host.create(cfg);host.resume()
    state=deepcopy(old['state'])
    state['original_stopped_run']=old_run
    state['repair_binding']=dict(kind='explicit_code_revision_original_grant',original_run=old_run,original_project=store.config()['project_id'],
        counters_and_original_node_deadlines_preserved=True,new_node_or_grant_capacity=0)
    with store.transaction() as db:store.update_state(db,new_run,state)
    previous=deepcopy(m);atomic_json(OUT/'validation_manifest_before_repair1.json',previous)
    affected=['tools/research_investigations.py','tools/model_transports/deepseek.py','tools/disposition_facts.py','tools/research_v1_continue.py','tools/research_v1_continue_gate.py']
    revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in affected:m['code_identity'][path]=sha(ROOT/path)
    m.update(code_commit=revision,implementation_repairs_used=1)
    m['phases']['coordinated']['active_run_id']=new_run
    record=dict(repair=1,defects=['Multi-call rejection feedback omitted required tool replies, causing documented HTTP 400',
        'Complete safe reception admission failure was incorrectly treated as unconfirmed transport; local settlement now uses the actual durable reception and original usage',
        'Reception flags carried across turns; reset per request. Future omitted-body usage captured before body admission.'],
        affected_paths=affected,code_revision=revision,checks='repair1_checks.log',original_manifest_identity=digest(previous),
        unchanged_model_allowances=True,unchanged_deadline=True,original_stopped_run_preserved=True,historical_lost_response_untouched=True,
        paid_recovery_branches=['Repair and continue the safely archived reach conversation with all tool replies',
            'Explicit replacement timing submission after confirmed admission failure; omitted body is unrecoverable, not successfully recovered'])
    m.setdefault('repairs',[]).append(record);atomic_json(OUT/'repair1.json',record);atomic_json(OUT/'validation_manifest.json',m)
    repair_start=1791468491.0  # First live blocker inspection, 14:08:11 UTC.
    elapsed=max(0,time.time()-repair_start)
    cost={**zero(),'wall_s':elapsed}
    r,fresh=store.reserve(new_run,'engineering-repair1',digest(record),'coding-agent-repair',cost,kind='engineering_repair')
    if fresh:store.complete(r,dict(request_id=r['request_id'],execution_id=r['execution_id'],tool_id='engineering.repair',tool_version='1.0.0',execution_status='completed',caller='coding-agent-repair',charged=zero(),cache_hit=False),record,elapsed=elapsed,actual_cost=cost,kind='engineering_repair')
    atomic_json(OUT/'repair1_accounting.json',dict(repair_wall_s=elapsed,project_ledger=store.remaining(),coding_operations='Bounded patch, source/receipt inspection, affected offline checks, ordinary commit and version binding; shell operations are engineering, not fabricated public source reads.'))

def bind_current_repair(m,p,old_run,record):
    """Targeted current-activity migration; ledger/counters/clocks are unchanged."""
    if not reuse_both() and m['implementation_repairs_used']>=4:raise ValueError('POST_FREEZE_REPAIR_CEILING')
    prior=[r for r in m.get('repairs',[]) if r['defect_id']==record['defect_id']]
    if not reuse_both() and len(prior)>=2:raise ValueError('SAME_DEFECT_REPAIR_CEILING')
    clock=read(OUT/'activity_start.json')
    if time.time()>=clock['execution_cutoff_unix']:raise ValueError('PROTECTED_DELIVERY_CUTOFF')
    if not read(OUT/record['verification'])['passed']:raise ValueError('FOCUSED_REPAIR_VERIFICATION_REQUIRED')
    store=Store(ROOT/p['output']);old=store.session(old_run)
    if any(t.name.startswith('investigation-') for t in threading.enumerate()):raise ValueError('ACTIVE_INVESTIGATION_NO_REPAIR_MIGRATION')
    index=m['implementation_repairs_used']+1;new_run='mainline3-coordinated-repair'+str(index)
    cfg=deepcopy(old['snapshot']['input']);cfg['run_id']=new_run
    host=Host(store.root,new_run);host.create(cfg);host.resume()
    state=deepcopy(old['state']);state['original_stopped_run']=old_run
    for key,node in state.get('investigations',{}).items():
        node.setdefault('request_run_id',old_run)
        if key in record.get('restore_authoritative_node_deadlines',[]):
            node['prior_reservation_guard_unix']=node.get('execution_deadline_unix')
            node['execution_deadline_unix']=node['started_unix']+node['order']['timeout_s']
        for field,origin in [('fact_catalog','catalog_origin_run_id'),('source_fact_catalog','source_catalog_origin_run_id')]:
            if node.get(field):node.setdefault(origin,store.artifact(node[field])['activity_run_id'])
    with store.transaction() as db:store.update_state(db,new_run,state)
    atomic_json(OUT/('validation_manifest_before_repair'+str(index)+'.json'),m)
    for path in record['affected_paths']:m['code_identity'][path]=sha(ROOT/path)
    record=dict(record,repair=index,same_defect_cycle=len(prior)+1,new_run=new_run,original_run=old_run,
        code_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),unchanged_authority=True,new_grant_capacity=0)
    m.update(code_commit=record['code_revision'],implementation_repairs_used=index);p['active_run_id']=new_run
    m.setdefault('repairs',[]).append(record);atomic_json(OUT/'validation_manifest.json',m)
    elapsed=max(0,time.time()-record['started_unix']);cost={**zero(),'wall_s':elapsed}
    row,fresh=store.reserve(new_run,'engineering-repair'+str(index),digest(record),'coding-agent-repair',cost,kind='engineering_repair')
    if fresh:store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],tool_id='engineering.repair',tool_version='1.0.0',execution_status='completed',caller='coding-agent-repair',charged=zero(),cache_hit=False),record,elapsed=elapsed,actual_cost=cost,kind='engineering_repair')
    atomic_json(OUT/('repair'+str(index)+'.json'),record)
    return host


def continue_repair():
    host,m,p=host_for('coordinated');store=host.store;d=InvestigationDispatcher(host)
    if p.get('sequential_reservations'):
        # First replay complete saved outputs locally. This sends zero requests.
        for key,node in store.session(host.run_id)['state'].get('investigations',{}).items():
            if node['status']!='completed':d.recover(key)
        return stage_b(host,m,p)
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path.home()/'.codex/.env')
    for key in ('reach-holding-interpretation','timing-integrity-limits'):
        node=store.session(host.run_id)['state']['investigations'][key]
        if node['status']=='completed':continue
        original_run=store.session(host.run_id)['state']['original_stopped_run']
        original=store.lookup(original_run,'investigation-'+key)
        if not original['receipt'] or json.loads(original['receipt'])['execution_status']!='failed':raise ValueError('CONFIRMED_ORIGINAL_FAILURE_REQUIRED')
        order=InvestigationOrder.model_validate(node['order'])
        remaining_s=order.timeout_s-(time.time()-node['started_unix'])
        if remaining_s<=0:raise ValueError('ORIGINAL_NODE_DEADLINE_EXPIRED')
        reservation={k:v-node['usage'][k] for k,v in plain(order.budget).items()};reservation['wall_s']=remaining_s
        request='investigation-'+key+'-repair1'
        # This explicitly paid recovery is separate from genuine model corrections.
        with store.transaction() as db:
            state=store.session(host.run_id,db)['state'];g=state['role_context']['investigation_grant'];used=state.get('investigation_protocol_corrections_used',0);other=state.get('investigation_corrections_by_role',{}).get('other',0)
            if not g.get('correction_policy'):
                if used>=g['protocol_correction_limit'] or other>=3:raise ValueError('PAID_RECOVERY_ALLOWANCE_EXHAUSTED')
                state['investigation_protocol_corrections_used']=used+1;state.setdefault('investigation_corrections_by_role',{})['other']=other+1
            state['investigations'][key].setdefault('request_history',[]).append(dict(run_id=original_run,request_id=original['request_id'],execution_id=original['execution_id'],usage=deepcopy(node['usage'])))
            state['investigations'][key].update(request_run_id=host.run_id,active_request_id=request,status='pending')
            if g.get('correction_policy'):
                state['investigations'][key].update(next_request_purpose='engineering_recovery',next_request_reason='Confirmed engineering defect repaired locally')
            store.update_state(db,host.run_id,state);store.event(db,host.run_id,'investigation_paid_recovery','authorized',request=request,outputs=[store.put(db,dict(branch='program_history_repair' if key.startswith('reach') else 'new_replacement_after_body_omission',logical_node=key,original_receipt=json.loads(original['receipt']),cumulative_node_usage=node['usage'],same_node_deadline=node['started_unix']+order.timeout_s))])
        row,fresh=store.reserve(host.run_id,request,digest(dict(original_execution=original['execution_id'],repair=1)),'investigation-dispatcher',reservation,kind='investigation')
        if not fresh:raise ValueError('NO_REPAIR_REQUEST_REDISPATCH')
        if key.startswith('reach'):
            events=[e for e in store.events(original_run) if e['kind']=='investigation_provider_attempt' and e.get('request_id')==original['request_id']]
            payload=store.artifact(events[-1]['outputs'][0])['payload']
            # Fix the actual rejected wire locally; retain every assistant reasoning field.
            fixed=[]
            for message in payload['messages']:
                fixed.append(message)
                if message.get('role')=='assistant' and len(message.get('tool_calls',[]))>1:
                    fixed.extend(dict(role='tool',tool_call_id=c['id'],content=encode(dict(error='EXACTLY_ONE_NATIVE_TOOL_CALL_REQUIRED',executed=False,requirement='Submit exactly one native call next.'))) for c in message['tool_calls'])
            payload['messages']=fixed;context=None
            payload['messages'].append(dict(role='user',content='Report source_identity may be empty. If provided, copy only fields actually present at the original source root; nested candidate_id/owner_run_id are not root identities. Exact scoped values, conclusions and unknowns remain your responsibility.'))
        else:
            payload=None;context=dict(kind='explicit_new_replacement_submission_same_authorized_node',
                prior_confirmed_reads=node['reads'],prior_response_body='Received in full but omitted by mandatory secret admission; unrecoverable. No content or judgment inferred.',
                scientific_instruction='Continue the original question using the safe evidence actually supplied here. Submit your strongest supported report with explicit missing evidence; no desired conclusion.',
                source_identity_rule='Use source_identity={} unless copying actual source-root fields. Never promote nested candidate_id or owner_run_id to source-root identity.',
                historical_uncertainty='The older activity eighth response remains separately unrecoverable and reserved.')
        from tools.workbench import owner
        def run(order=order,row=row,payload=payload,context=context):
            with owner(host.folder,'.investigation-'+order.investigation_id+'.lock'):
                d._execute(order,row,resume_payload=payload,correction_context=context,reuse_saved_reads=True)
        threading.Thread(target=run,name='investigation-'+key,daemon=True).start()
    try:stage_b(host,m,p,transport=True)
    except Exception:
        for t in [t for t in threading.enumerate() if t.name.startswith('investigation-')]:t.join(2405)
        export(OUT,'coordinated',run_id=host.run_id);raise

def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['start','freeze','execute-b','close-b','execute-c','check','bind-repair','continue-repair'])
    parser.add_argument('--reuse-both-reports',action='store_true')
    parser.add_argument('--directory',type=Path);parser.add_argument('--authorization',type=Path);parser.add_argument('--started-unix',type=float)
    parser.add_argument('--repair-record',type=Path)
    args=parser.parse_args()
    if args.directory:OUT=args.directory.resolve()
    if not OUT.is_relative_to(ROOT/'evidence'):raise ValueError('ACTIVITY_DIRECTORY_OUTSIDE_EVIDENCE')
    if args.action=='start':start(args.authorization,args.started_unix,reuse_both_reports=args.reuse_both_reports)
    elif args.action=='freeze':freeze()
    elif args.action=='check':check()
    elif args.action=='bind-repair':bind_repair(read(args.repair_record) if args.repair_record else None)
    elif args.action=='continue-repair':continue_repair()
    elif args.action=='close-b':close_b()
    elif args.action=='execute-c':execute_c()
    else:
        host,m,p=host_for('coordinated',create=True)
        try:stage_b(host,m,p)
        except Exception:
            for t in [t for t in threading.enumerate() if t.name.startswith('investigation-')]:t.join(2405)
            stop(host,'NEW B BLOCKED; preserve partial results and uncertain reservations');export(OUT,'coordinated');raise

if __name__=='__main__':
    # Gate imports must share the CLI's selected activity directory and policy.
    import sys
    sys.modules['tools.research_v1_continue']=sys.modules[__name__]
    main()
