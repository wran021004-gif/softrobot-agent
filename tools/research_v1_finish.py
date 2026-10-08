"""New bounded A/B/C activity; existing Host/Store execution, no historical revival."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import threading
import time
from uuid import uuid4

from tools.state_io import read, atomic_json, digest
from tools.platform_store import Store, plain, zero, now, encode
from tools.platform_host import Host
from tools.research_execution import invoke
from tools.research_investigations import InvestigationOrder, InvestigationDispatcher
from tools.research_mainline3 import configuration, SOURCE, import_historical_provenance, fixed_pipeline
from tools.research_v1_delivery import model_configuration, FIXED_TOOLS
from tools.research_single_validation import sha, stop
from tools.research_validation_activity import export
from tools.research_metric_view import build as metric_view
from tools.context_assembly import _no_secrets

ROOT = Path(__file__).resolve().parents[1]
BASE = '6b4f7d85e4ae937ba6117afde1e47cd9fcc6a36c'
OUT = ROOT/'evidence/research_mainline3_v1_finish_20261008'
OLD = ROOT/'evidence/research_v1_completion_20261008/stages'


def start():
    if OUT.exists(): raise ValueError('FRESH_ACTIVITY_REQUIRED')
    subprocess.check_call(['git','merge-base','--is-ancestor',BASE,'HEAD'],cwd=ROOT)
    OUT.mkdir(parents=True)
    began = 1791457028.0  # First task-start UTC clock: 2026-10-08 10:57:08.
    atomic_json(OUT/'activity_start.json',dict(activity_id='mainline3-v1-finish-'+uuid4().hex[:12],
        started_unix=began, deadline_unix=began+36000, execution_cutoff_unix=began+34200,
        includes='Preparation, pauses, repairs, reviews, execution and delivery',known_base=BASE,
        observed_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        observed_branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
        original_worktree=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)))
    atomic_json(OUT/'authorization.json',dict(source='User message 2026-10-08; new bounded activity, corrected full Stage C path',
        recipient='https://api.deepseek.com',model='deepseek-flash',thinking='enabled',reasoning_effort='high',tool_choice='auto',max_tokens=32768,
        data_scope='Task-scoped non-secret research/configuration/results/reports/source identifiers and sanitized failures. Existing credential loader only.',
        ordinary_push=dict(repository='https://github.com/wran021004-gif/softrobot-agent.git',branch='feat/gvs-dynamics'),
        total_model_attempts=48,total_paid_corrections=10,implementation_repairs_after_freeze=6,
        continuous_failed_correction_limit=3,absolute_deadline_hours=10,protected_delivery_minutes=30,
        stages=dict(A=dict(model_calls=12,tool_calls=128,wall_s=5000,paid_corrections=4,node_evidence=24,node_elapsed_s=3600),
                    B=dict(model_calls=36,tool_calls=512,wall_s=12000,paid_corrections=6,protected_principal_corrections=3,node_models=12,node_evidence=16,node_elapsed_s=2400,investigator_concurrency=2),
                    C=dict(tool_calls=28,wall_s=6000,backend_attempts=2,second_backend='Only engineering-incomplete/invalid, repaired with unchanged science')),
        old_records='Sealed; no revival, quota transfer, reservation release or historical new-node attribution',automatic_transport_retries=0))
    # Hash read-only evidence and original databases, including the last failed activity.
    paths = [ROOT/'runs/stage336_manual_20261001_090616/platform.sqlite']
    for name in ('research_v1_completion_20261008','research_v1_resume_20261008','research_disposition_facts_20261008'):
        paths += [p for p in (ROOT/'evidence'/name).rglob('*') if p.is_file()]
    prior=read(ROOT/'evidence/research_disposition_facts_20261008/stages/validation_manifest.json')
    paths += [ROOT/v['output']/'platform.sqlite' for v in prior['phases'].values() if (ROOT/v['output']/'platform.sqlite').exists()]
    atomic_json(OUT/'sealed_history.json',{p.relative_to(ROOT).as_posix():sha(p) for p in paths})
    previous=Store(ROOT/prior['phases']['reuse']['output'])
    atomic_json(OUT/'old_activity_accounting.json',dict(project=previous.config(),ledger=previous.remaining(),
        sessions={k:previous.session(k)['status'] for k in ('mainline3-reuse','mainline3-reuse-repair1','mainline3-reuse-repair2')}))
    historical=Store(ROOT/'runs/stage336_manual_20261001_090616')
    facts=read(ROOT/'runs/stage336_manual_20261001_090616/stage336_audit.json')['execution']['factual_result']
    atomic_json(OUT/'historical_metric_view.json',metric_view(facts,historical.artifact))
    atomic_json(OUT/'fixed_identity_check.json',fixed_identity())


def fixed_identity():
    manifest_path=SOURCE.parent.parent/'sha256_manifest.json'; original=read(SOURCE)
    listed=read(manifest_path)['artifacts/'+SOURCE.name]
    if listed != SOURCE.stem or sha(SOURCE) != listed: raise ValueError('FIXED_SOURCE_MANIFEST_MISMATCH')
    cfg=configuration()
    if cfg['policy']['candidate_builder']['version']!='1.2.0' or cfg['policy']['controller']['version']!='9.0.0': raise ValueError('FIXED_EXTENSION_VERSION')
    # Only explicit envelope promotions relative to the archived starting input.
    if cfg['task']!=original['effective']['task'] or cfg['robot']!=original['effective']['robot'] or cfg['seed']!=original['effective']['seed']: raise ValueError('FIXED_TASK_STRUCTURE_OR_SEED_CHANGED')
    recipe=original['effective']['policy']['controller']['parameters']
    if cfg['policy']['controller']['parameters']!=recipe: raise ValueError('FIXED_V7_SOLVING_RULE_CHANGED')
    return dict(source=SOURCE.relative_to(ROOT).as_posix(),source_artifact=SOURCE.stem,manifest=manifest_path.relative_to(ROOT).as_posix(),
        file_sha256=listed,source_candidate=original['candidate_id'],source_builder=original['builder'],source_builder_version=original['builder_version'],
        source_controller_version=original['effective']['policy']['controller']['version'],candidate_builder='candidate.family@1.2.0',controller='controller.gvs_nmpc@9.0.0',
        task_robot_seed_and_v7_recipe_unchanged=True,changes={'design/near_routing_radius_scale':1.01,'design/far_routing_radius_scale':.99})


def freeze():
    if (OUT/'validation_manifest.json').exists():raise ValueError('ALREADY_FROZEN')
    cfg=model_configuration(configuration())
    cfg['policy']['model'].update(adapter_version='8.0.0',parameters=dict(investigation_contract='selectable_facts_v3'),timeout_s=600.)
    tools={k:'1.0.0' for k in ('research.investigate','research.investigation_status','research.investigation_read','research.investigation_disposition','research.investigation_handoff')}
    phases={}
    for name,models,ops,wall,node_models,node_ops,node_wall,count,corrections in [('reuse',12,128,5000.,12,24,3600.,1,4),('coordinated',36,512,12000.,12,16,2400.,5,6)]:
        node={**zero(), 'model_calls':node_models,'tool_calls':node_ops,'wall_s':node_wall}
        phases[name]=dict(project_budget={**zero(),'model_calls':models,'tool_calls':ops,'wall_s':wall},
            node_budget=node,total_node_budget={**zero(),'model_calls':models,'tool_calls':node_ops*count,'wall_s':node_wall*count},node_count=count,
            node_timeout_s=node_wall,tool_bindings=tools,operation_allowances={t:dict(reserve_s=5.,timeout_s=30.) for t in tools},
            protocol_correction_limit=corrections,protocol_correction_role_limits=dict(principal=4 if name=='reuse' else 3,other=0 if name=='reuse' else 3))
    fixed_tools={**FIXED_TOOLS,'research.task_acceptance':'1.0.0'}
    reserves=dict(zip(fixed_tools,(30.,700.,150.,500.,4400.,30.,60.,30.)))
    phases['fixed']=dict(project_budget={**zero(),'tool_calls':28,'backend_solves':2,'wall_s':6000.},tool_bindings=fixed_tools,
        operation_allowances={t:dict(reserve_s=v,timeout_s=v) for t,v in reserves.items()})
    identity=read(OUT/'activity_start.json')['activity_id']
    for name,p in phases.items():
        grant=dict(project_id=identity+'-'+name,grant_id=identity+'-'+name,budget=p['project_budget'],authorization_source=(OUT/'authorization.json').relative_to(ROOT).as_posix()+'; '+name)
        atomic_json(OUT/(name+'_grant.json'),grant);p.update(output='runs/'+identity+'-'+name,grant_identity=digest(grant))
    paths=subprocess.check_output(['git','ls-files','tools','schemas','extensions','configs'],cwd=ROOT,text=True).splitlines()
    paths+=['tools/research_v1_finish.py','tools/research_metric_view.py','tools/research_error_routing.py','tools/research_v1_finish_gate.py','tools/research_v1_finish_preflight.py','tools/research_joint_evaluation.py']
    m=dict(activity_id=identity,code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        code_identity={p:sha(ROOT/p) for p in sorted(set(paths))},configuration_identity=digest(cfg),phases=phases,
        frozen_at=now(),implementation_repairs_used=0,implementation_repair_ceiling=6,total_model_attempts=48,total_paid_corrections=10,
        continuous_correction_limit=3,fixed_changes=fixed_identity()['changes'],fixed_identity=fixed_identity(),
        gates=dict(A='Actual provider, necessary native read delivered to subsequent request, deterministic selection/source/visibility/public receipts, separate material review',
                   B='New coordinator plan, two distinct new investigators with native query followup, coordinator synthesis, principal formal decisions and separate material review',
                   C='Eight public scientific components complete/valid, original frozen configuration and joint acceptance; valid physical failure does not block interface completion'),
        material_review='Independent Codex review of exact claims, support/unknown reasons and consequences. No paid model judge; accepts/defer/reject all legitimate. Wording alone does not block.',
        review_version='material_components@2.0.0',automatic_transport_retries=0)
    _no_secrets(cfg);atomic_json(OUT/'frozen_configuration.json',cfg);atomic_json(OUT/'validation_manifest.json',m)


def check():
    clock=read(OUT/'activity_start.json')
    if time.time()>=clock['execution_cutoff_unix']:raise ValueError('PROTECTED_DELIVERY_CUTOFF')
    m=read(OUT/'validation_manifest.json');cfg=read(OUT/'frozen_configuration.json')
    if digest(cfg)!=m['configuration_identity'] or any(sha(ROOT/p)!=v for p,v in m['code_identity'].items()):raise ValueError('FROZEN_IMPLEMENTATION_CHANGED')
    if any(sha(ROOT/p)!=v for p,v in read(OUT/'sealed_history.json').items()):raise ValueError('SEALED_HISTORY_CHANGED')
    return m,cfg


def grant_evidence(host, stage):
    facts=read(ROOT/'runs/stage336_manual_20261001_090616/stage336_audit.json')['execution']['factual_result']
    import_historical_provenance(host.store,facts)
    import_historical_provenance(host.store,read(OUT/'historical_metric_view.json'))
    with host.store.transaction() as db:
        raw=plain(host.store.put(db,facts));view=plain(host.store.put(db,read(OUT/'historical_metric_view.json')))
        scope=[raw,view,facts['evaluation'],facts['configuration'],facts['report']['reference']]
        ig=dict(max_count=stage['node_count'],max_concurrency=2,allowed_tools=['evidence.read'],evidence=scope,
            include_completed_reports=True,per_node_budget=stage['node_budget'],total_budget=stage['total_node_budget'],output_bytes=65536,
            deadline_unix=min(read(OUT/'activity_start.json')['execution_cutoff_unix'],time.time()+stage['project_budget']['wall_s']),
            protocol_correction_limit=stage['protocol_correction_limit'],protocol_correction_role_limits=stage['protocol_correction_role_limits'],protocol_correction_per_node=3,
            inspected_supplemental_catalog=True)
        state=host.store.session(host.run_id,db)['state'];state.update(role_context=dict(role='principal',investigation_grant=ig),investigation_grant_identity=digest(ig))
        host.store.update_state(db,host.run_id,state)
    return raw,view,scope


def order(stage,key,role,question,evidence,queries=None,models=None,ops=None):
    budget=deepcopy(stage['node_budget'])
    if models is not None:budget['model_calls']=models
    if ops is not None:budget['tool_calls']=ops
    return plain(InvestigationOrder(investigation_id=key,role=role,question=question,evidence=evidence,queries=queries or [],
        budget=budget,timeout_s=stage['node_timeout_s'],output_bytes=65536,stop_conditions=[
            'Only scoped archived data; zero science, worker and transport retry permissions.',
            'All paid corrections and reads share original node clock and counters; no quota refunds.',
            'Use exact values and separate official records, recomputation and unknown material.']))


def collect(host, submitted):
    if submitted['execution_status']!='completed':raise ValueError('PUBLIC_SUBMISSION_FAILED')
    value=host.store.artifact(submitted['output']);key=value['investigation_id']
    node=host.store.session(host.run_id)['state']['investigations'][key]
    thread=next((t for t in threading.enumerate() if t.name=='investigation-'+key),None)
    if thread:thread.join(max(0,node['order']['timeout_s']-(time.time()-node['started_unix']))+5.)
    receipt=invoke(host,'research.investigation_status',dict(investigation_id=key),request_id='collect-'+key)
    if receipt['execution_status']!='completed':raise ValueError('PUBLIC_COLLECTION_FAILED')
    result=host.store.artifact(receipt['output'])
    if result['status']!='completed':raise ValueError('MODEL_NODE_'+result['status'].upper())
    return result['result']


def inspect(host, refs):
    for i,ref in enumerate(refs):
        receipt=invoke(host,'research.investigation_read',dict(reference=ref,pointer='',limit=100,byte_limit=8192),request_id='principal-source-'+str(i))
        if receipt['execution_status']!='completed' or host.store.artifact(receipt['output'])['kind']!='content':raise ValueError('PUBLIC_PRINCIPAL_INSPECTION_REQUIRED')


def historical_handoff(host):
    original=read(OLD/'direct_bundle.json');oldm=read(OLD/'validation_manifest.json');store=Store(ROOT/oldm['phases']['direct']['output'])
    descriptors=[];targets=[]
    with host.store.transaction() as db:
        for key in ('reach-question','timing-question'):
            node=original['state']['investigations'][key]
            if plain(host.store.put(db,store.artifact(node['result'])))!=node['result']:raise ValueError('OLD_REPORT_CHANGED')
            validation=plain(host.store.put(db,dict(historical_node_identity=digest(node),original_gate=read(OLD/'direct_gate.json')['gates'],old_report_valid=True,
                old_formal_disposition_succeeded=False,review_revision=(OUT/'previous_material_review_revision.json').relative_to(ROOT).as_posix())))
            descriptors.append(dict(source_directory=oldm['phases']['direct']['output'],source_run_id='mainline3-direct-repair1',source_project_id=original['project']['project_id'],
                source_database_sha256=sha(store.db),source_node=key,report=node['result'],historical_validation=validation))
            targets.append(dict(investigation_id=key,report=node['result']))
        state=host.store.session(host.run_id,db)['state'];ig=state['role_context']['investigation_grant'];ig['historical_handoffs']=descriptors
        state['investigation_grant_identity']=digest(ig);host.store.update_state(db,host.run_id,state)
    for i,d in enumerate(descriptors):
        if invoke(host,'research.investigation_handoff',d,request_id='old-report-'+str(i))['execution_status']!='completed':raise ValueError('PUBLIC_OLD_HANDOFF_FAILED')
    return targets


def principal(host,stage,key,targets,raw,view,extra=None,models=None,ops=None):
    sources=host.store.session(host.run_id)['state']['role_context']['investigation_grant']['evidence']
    evidence=[*sources,*[t['report'] for t in targets],*(extra or [])]
    question=('Independently decide exactly one accept/defer/reject disposition for each of '+', '.join(t['investigation_id'] for t in targets)+
        '. Read their complete reports through evidence_read before deciding; catalog values do not expose complete interpretations/unknowns. '
        'Two independently inspected sources are already presented. Evaluate individual supported claims, not entire report endorsement. '
        'The metric view is a new deterministic interpretation of old original configuration/evaluator/profile, not a new simulation or child-report fact. '
        'Separate recorded official overall result, terminal reach component, holding position/speed, and independent recomputation availability. '
        'Overall failure alone does not identify component failure. One-step predictions do not prove reach/holding. '
        'Use report handles only for supporting_facts, principal supplemental handles for additional_support, and per-source applicability scope. '
        'You may adopt a small supported subset, defer or reject with concrete reasons and missing materials. No mandatory conclusion. '
        'At most four concise claims per report avoids duplicating whole objects. Scientific causality, global optimality and real-robot timing are not established. '
        'Return formal selectable dispositions via investigation_return; all report/source identities refer to historical Stage336 execution 494deb38d6374deb8f741e96f2430826.')
    if extra:
        question+=' Also read the complete coordinator-summary report from the directory; use it as synthesis context, not an extra disposition target or child-fact attribution.'
    value=order(stage,key,'principal',question,evidence,models=models,ops=ops)
    value['disposition_ids']=[t['investigation_id'] for t in targets]
    atomic_json(OUT/(key+'_order.json'),value)
    report=collect(host,invoke(host,'research.investigate',value,request_id=key))
    # Review and any correction occur in this process with the original clock.
    for iteration in range(4):
        current=host.store.artifact(report)
        atomic_json(OUT/(key+f'_pending_review_{iteration}.json'),dict(report=report,body=current,targets=targets,
            node=host.store.session(host.run_id)['state']['investigations'][key],no_provider_judge=True))
        review_path=OUT/(key+f'_review_{iteration}.json')
        while not review_path.exists():
            node=host.store.session(host.run_id)['state']['investigations'][key]
            if time.time()-node['started_unix']>=node['order']['timeout_s'] or time.time()>=read(OUT/'activity_start.json')['execution_cutoff_unix']:raise ValueError('ORIGINAL_REVIEW_NODE_DEADLINE')
            time.sleep(1.)
        review=read(review_path)
        if review['report']!=report:raise ValueError('MATERIAL_REVIEW_REPORT_IDENTITY')
        if review['material_correctness']=='pass':break
        if iteration>=3:raise ValueError('MATERIAL_CONTINUOUS_CORRECTION_LIMIT')
        report=correct_material(host,key,review)
    decisions=host.store.artifact(report)['dispositions'];expected={t['investigation_id']:t['report'] for t in targets}
    if len(decisions)!=len(expected) or {d['investigation_id'] for d in decisions}!=set(expected):raise ValueError('EXACTLY_TWO_FORMAL_DECISIONS_REQUIRED')
    rows=[]
    for d in decisions:
        if d['report']!=expected[d['investigation_id']]:raise ValueError('MODEL_REPORT_BINDING_MISMATCH')
        r=invoke(host,'research.investigation_disposition',d,request_id='dispose-'+d['investigation_id']);rows.append(r)
        if r['execution_status']!='completed':raise ValueError('PUBLIC_DISPOSITION_FAILED')
    return dict(status='formal_dispositions_recorded',report=report,receipts=rows,material_review=review,targets=targets)


def correct_material(host,key,review):
    node=host.store.session(host.run_id)['state']['investigations'][key];o=InvestigationOrder.model_validate(node['order'])
    dispatcher=InvestigationDispatcher(host)
    exc=ValueError('MATERIAL_INSUFFICIENT_SUPPORT')
    exc.issue=dict(issues=review['blocking_issues'],queries=review.get('queries',[]),requirement='Choose your own revised support, clarification, deferred or rejected conclusion; no required scientific verdict.')
    feedback=dispatcher._protocol_feedback(o,exc)
    if feedback is None:raise ValueError('MATERIAL_PAID_CORRECTION_BUDGET_EXHAUSTED')
    remaining=o.timeout_s-(time.time()-node['started_unix'])
    budget={k:max(0,plain(o.budget)[k]-node['usage'][k]) for k in zero()};budget['wall_s']=remaining
    number=host.store.session(host.run_id)['state']['investigations'][key]['protocol_corrections_used']
    request='investigation-'+key+'-material-'+str(number)
    row,fresh=host.store.reserve(host.run_id,request,digest(dict(review=review,original_node=key)),'investigation-dispatcher',budget,kind='investigation')
    if not fresh:raise ValueError('NO_CORRECTION_REDISPATCH')
    previous=host.store.artifact(node['provider_response_refs'][-1])
    context=dict(kind='explicit_material_correction_same_logical_node',feedback=feedback,
        received_native_calls=previous['choices'][0]['message']['tool_calls'],previous_response=node['provider_response_refs'][-1],
        followup_reads=node['reads'],original_deadline_unix=node['started_unix']+o.timeout_s,
        omitted='Prior thinking archive-only, queryable through evidence_read of previous_response /choices/0/message/reasoning_content; all original reports and read feedback retained.')
    dispatcher._state(key,status='pending',active_request_id=request)
    dispatcher._execute(o,row,reuse_saved_reads=True,correction_context=context)
    current=host.store.session(host.run_id)['state']['investigations'][key]
    if current['status']!='completed':raise ValueError('MATERIAL_CORRECTION_DID_NOT_COMPLETE')
    return current['result']


def stage_a(host,p):
    raw,view,scope=grant_evidence(host,p);targets=historical_handoff(host);inspect(host,[raw,view])
    return principal(host,p,'principal-historical-v2',targets,raw,view,models=12,ops=22)


def stage_b(host,p):
    raw,view,scope=grant_evidence(host,p)
    # Evidence scope intentionally narrower than original provenance archive.
    evidence=[raw,view]
    planning=order(p,'coordinator-plan','coordinator',
        'Plan exactly two distinct investigator children: one on historical reach/holding interpretation, one on timing/integrity limits. Inspect directory/source as needed. Children must actually query sources, not rely on coordinator prose. parent_id=coordinator-plan, role investigator, no child delegation. Each child model_calls<=8, tool_calls<=16, timeout_s<=2400, wall_s<=2400, output_bytes<=65536; backend_solves/worker_calls=0. Preserve finite scope. No scientific execution or principal disposition. Suggestions confer no authority.',evidence,models=8)
    ref=collect(host,invoke(host,'research.investigate',planning,request_id='coordinator-plan'))
    children=host.store.artifact(ref)['children']
    if len(children)!=2 or len({c['investigation_id'] for c in children})!=2 or len({c['question'] for c in children})!=2:raise ValueError('TWO_DISTINCT_NEW_CHILDREN_REQUIRED')
    if any(c['budget']['model_calls']>8 for c in children):raise ValueError('CHILD_INITIAL_PERMISSION_OR_NATIVE_READ_PLAN')
    submitted=[invoke(host,'research.investigate',c,request_id='child-'+str(i)) for i,c in enumerate(children)]
    reports=[collect(host,r) for r in submitted]
    queries=[dict(reference=r,pointer='',limit=100,byte_limit=65536) for r in reports]
    synthesis=order(p,'coordinator-summary','coordinator',
        'Synthesize the two new investigator reports and their scoped uncertainties. Do not create children or principal dispositions. Compare reach/holding components and recorded timing without claiming dominant causes, optimality or real-robot deployment. Return a concise sourced synthesis, counterevidence and unknowns. Report facts may cite the exact inspected report fields; no new computation.',[raw,view,*reports],queries=queries,models=2)
    combined=collect(host,invoke(host,'research.investigate',synthesis,request_id='coordinator-summary'))
    inspect(host,[raw,view])
    targets=[dict(investigation_id=c['investigation_id'],report=r) for c,r in zip(children,reports)]
    result=principal(host,p,'principal-coordinated-v2',targets,raw,view,extra=[combined],models=10,ops=14)
    result.update(coordinator_plan=ref,coordinator_synthesis=combined,new_investigators=targets)
    return result


def execute(mode):
    m,cfg=check();p=m['phases'][mode]
    prior={'coordinated':'reuse','fixed':'coordinated'}.get(mode)
    if prior and not read(OUT/(prior+'_gate.json'))['passed']:raise ValueError('DEPENDENT_FROZEN_GATE_FAILED')
    root=ROOT/p['output']
    if root.exists():raise ValueError('NO_RESTART_OR_NEW_BUDGET')
    grant=read(OUT/(mode+'_grant.json'))
    if digest(grant)!=p['grant_identity']:raise ValueError('PHASE_GRANT_CHANGED')
    store=Store(root);store.create(grant);cfg['run_id']='mainline3-'+mode
    cfg['policy'].update(route=None,budget=p['project_budget'],allowed_tools=list(p['tool_bindings']),tool_bindings=p['tool_bindings'],
        operation_allowances=p['operation_allowances'],timeout_s=p['project_budget']['wall_s'])
    host=Host(root,cfg['run_id']);host.create(cfg);host.resume();began=time.monotonic()
    atomic_json(OUT/(mode+'_launch.json'),dict(timestamp=now(),started_unix=time.time(),frozen_commit=m['code_commit'],new_activity=True))
    try:
        if mode!='fixed':
            from examples.gvs_nmpc_route_experiment import load_credential
            load_credential(Path.home()/'.codex/.env')
            result=stage_a(host,p) if mode=='reuse' else stage_b(host,p)
        else:
            from schemas.platform_analysis import TaskAnalysisProtocol,EndpointTarget
            source=cfg['policy']['candidate_builder']['parameters']['data']['semantic_source']
            protocol=TaskAnalysisProtocol(baseline_lengths_m={c['id']:c['length_m'] for c in source['components'] if c['kind']=='flexible_segment'},duration_s=cfg['task']['timing']['duration_s'],period_s=cfg['task']['timing']['control_period_s'],frequency_rad_s=[.1,1.,10.])
            target=EndpointTarget(position_m=cfg['task']['goal']['data']['target_m'],position_tolerance_m=cfg['task']['evaluator']['parameters']['data']['tolerance_m'],position_scale_m=.01)
            with store.transaction() as db:pr=plain(store.put(db,protocol));tr=plain(store.put(db,target))
            result=fixed_pipeline(host,changes=m['fixed_changes'],protocol=pr,target=tr,execute_backend=True)
            sim=result['receipts'][4];ev=result['receipts'][5];prof=result['receipts'][6]
            config_ref=store.artifact(prof['output'])['detail']['configuration']
            joint=invoke(host,'research.task_acceptance',dict(configuration=config_ref,evaluation=ev['output'],profile=prof['output']),request_id='fixed-joint-acceptance')
            result['receipts'].append(joint)
            if joint['execution_status']!='completed':raise ValueError('PUBLIC_JOINT_ACCEPTANCE_FAILED')
            result['joint_acceptance']=store.artifact(joint['output'])['detail']
        atomic_json(OUT/(mode+'_result.json'),result)
    except Exception as exc:
        from tools.research_error_routing import classify
        atomic_json(OUT/(mode+'_application_failure.json'),dict(timestamp=now(),type=type(exc).__name__,code=str(exc).split(':',1)[0][:160],routing=classify(exc),automatic_retry=False))
        raise
    finally:
        for t in [t for t in threading.enumerate() if t.name.startswith('investigation-')]:
            n=store.session(host.run_id)['state']['investigations'][t.name[14:]]
            t.join(max(0,n['order']['timeout_s']-(time.time()-n['started_unix']))+5)
        stop(host,'NEW_BOUNDED_STAGE_TERMINAL; no old STOP revival')
        atomic_json(OUT/(mode+'_lifecycle.json'),dict(application_wall_s=time.monotonic()-began,ended_at=now(),unknown_reservations=store.remaining()['occupied']))
        export(OUT,mode);bundle=read(OUT/(mode+'_bundle.json'));bundle['session_status']='stopped';atomic_json(OUT/(mode+'_bundle.json'),bundle)


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['start','freeze','execute']);p.add_argument('--mode',choices=['reuse','coordinated','fixed'],default='reuse');a=p.parse_args()
    if a.action=='start':start()
    elif a.action=='freeze':freeze()
    else:execute(a.mode)


if __name__=='__main__':main()
