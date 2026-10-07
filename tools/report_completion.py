"""Report-only continuation of a completed campaign, over its original ledger.

The v2 finish entry point remains historical. This bounded replacement archives
new projections and responses separately; it cannot dispatch research actions.
"""
from copy import deepcopy
from pathlib import Path
import csv
import hashlib
import json
import subprocess
import time
from tools.state_io import read, atomic_json, digest
from tools.platform_store import zero, plain
from tools.bound_reporting import authoritative_metrics, PROJECTION_VERSION
from tools.context_assembly import (ROOT, EvidenceArchive, assemble_request,
    request_facts, retrieve_fact, assemble_context, _no_secrets)

D = ROOT/'runs/research_native_development_v3_20261007'
OLD = ROOT/'evidence/research_native_development_v3_20261007/structural_continuation_20261007'
OUT = ROOT/'evidence/research_native_development_v3_20261007/report_completion_20261007'
START = D/'report_completion_start.json'
VERSION = 'completed_verification_report@1.0.0'
ALLOWED = ('tools/bound_reporting.py','tools/context_assembly.py',
           'tools/report_completion.py','examples/research_campaign_v3.py')


def workspace():
    from examples import research_model_v1 as pilot
    return pilot.restore(D.resolve())


def receipt(row, tool, status='completed'):
    return dict(request_id=row['request_id'], execution_id=row['execution_id'],
        caller=row['caller'], tool_id=tool, tool_version='1.0.0',
        execution_status=status, charged=zero())


def begin(started_unix):
    if START.exists(): raise ValueError('CONTINUATION_ALREADY_STARTED_NO_RESET')
    w=workspace(); settled=read(D/'structural_final_settled_costs.json')
    if w.store.remaining()!=settled['usage'] or w.repairs!=7:
        raise ValueError('LOCAL_SETTLEMENT_OR_REPAIR_BOUNDARY_CHANGED')
    with w.store.connect(True) as db:
        if list(db.execute('SELECT request_id FROM calls WHERE receipt IS NULL')):
            raise ValueError('UNSETTLED_CALLS_REQUIRE_RECONCILIATION')
    blocker=read(OLD/'final_report_blocker_review.json')
    failed=ROOT/blocker['original_request_snapshot']
    if hashlib.sha256(failed.read_bytes()).hexdigest()!=blocker['snapshot_sha256']:
        raise ValueError('SEALED_FAILURE_CHANGED')
    attachment=Path('C:/Users/gugugaga/.codex/attachments/da43daec-e064-42d0-ba7d-30276c43d87c/已粘贴的文本.txt')
    auth=dict(version=VERSION, source_attachment=str(attachment),
        source_sha256=hashlib.sha256(attachment.read_bytes()).hexdigest(),
        same_campaign=w.store.config()['project_id'],same_session=w.host.run_id,
        original_clock=read(D/'live_clock.json'),original_grant=digest(w.store.config()),
        started_unix=started_unix, baseline=settled['usage'], previous_repairs=7,
        cumulative_material_repairs=8, allowed_files=list(ALLOWED),
        prior_failure=blocker, scientific_stop=deepcopy(w.working['authority']['stop']),
        provider_config=deepcopy(w.store.session(w.host.run_id)['snapshot']['input']['policy']['model']),
        additional_limits=dict(model_calls=3,tool_calls=12,wall_s=1800,backend_solves=0,worker_calls=0),
        scientific_execution_authorized=False,standalone_numerical_operations=0)
    OUT.mkdir(parents=True,exist_ok=True)
    with w.store.transaction() as db:
        authref=plain(w.store.put(db,auth))
        w.store.event(db,w.host.run_id,'report_continuation_authorization','completed',outputs=[authref],version=VERSION)
    # One delivery reservation accounts all setup/check/review/publication time,
    # less separately settled model transport time. It is not a new grant.
    row,fresh=w.store.reserve(w.host.run_id,'report-completion-engineering',digest(auth),'engineering',
        {**zero(),'tool_calls':1,'wall_s':1800})
    if not fresh:raise ValueError('DELIVERY_RESERVATION_ALREADY_EXISTS')
    atomic_json(START,dict(authorization=auth,authorization_reference=authref,reservation=row))
    atomic_json(OUT/'continuation_authorization.json',dict(authorization=auth,authorization_reference=authref))
    print(json.dumps(dict(started_unix=started_unix,baseline=settled['usage']['used'],repairs=8)))


def guard(w, provider=False):
    start=read(START);a=start['authorization']; now=time.time()
    if (digest(w.store.config())!=a['original_grant'] or read(D/'live_clock.json')!=a['original_clock'] or
        w.store.session(w.host.run_id)['snapshot']['input']['policy']['model']!=a['provider_config'] or
        w.working['authority']['stop']!=a['scientific_stop']):
        raise ValueError('ORIGINAL_AUTHORITY_OR_SEALED_STOP_CHANGED')
    used=w.store.remaining()['used'];base=a['baseline']['used']
    if used['backend_solves']!=base['backend_solves'] or used['worker_calls']!=base['worker_calls']:
        raise ValueError('SCIENTIFIC_EXECUTION_FORBIDDEN')
    if used['model_calls']-base['model_calls']>3 or used['tool_calls']-base['tool_calls']>12:
        raise ValueError('ADDITIONAL_ATTEMPT_LIMIT')
    if now-a['started_unix']>=1800:raise ValueError('ADDITIONAL_WALL_LIMIT')
    if provider:
        if now>=a['original_clock']['deadline_unix']:raise ValueError('ORIGINAL_DEADLINE_EXPIRED')
        # Keep configured timeout unchanged and protect five minutes of delivery.
        if now-a['started_unix']+a['provider_config']['timeout_s']+300>1800:
            raise ValueError('DELIVERY_CAPACITY_RESERVED_NO_FURTHER_PROVIDER')
        if used['model_calls']-base['model_calls']>=3:raise ValueError('PROVIDER_ATTEMPT_CEILING')
    return start


def frozen_results(w):
    from tools.fixed_research import schedule
    from tools.research_spec import load_spec,apply_frozen_case
    from tools.research_tasks import aggregate_acceptance,compare_acceptance
    from tools.study_history import reporting_scientific_scope
    spec=load_spec();v=read(D/'verification.json');prior=read(OLD/'independent_results_review.json')
    selected=read(OLD/'final_frozen_selection.json')
    source_robot=w.store.artifact(selected['model_selected_at_research_stop']['configuration'])['effective']['robot']
    assert v['complete'] and [g['role'] for g in v['groups']]==['unchanged_incumbent','selected_candidate']
    assert v['plan']['schedule']==schedule(spec)
    table=[];facts={};supersessions=[];manifest=[];seen=set()
    for g in v['groups']:
        expected=(w.store.artifact(v['plan']['selected_candidate']['configuration'])['effective']
            if g['role']=='selected_candidate' else spec['starting_configuration']['effective'])
        slots=set()
        for r in g['records']:
            eid=r['receipt']['execution_id'];assert eid not in seen;seen.add(eid)
            slot=(r['case_id'],r['seed'],r['repetition']);assert slot not in slots;slots.add(slot)
            assert r['verification_role']==g['role'] and r['candidate_id']==f'v2-verify-{g["role"]}-{r["case_id"]}-rep{r["repetition"]}'
            cfg=w.store.artifact(r['configuration'])['effective']; ev=w.store.artifact(r['evaluation']); p=w.store.artifact(r['profile'])['detail']
            expected_case=apply_frozen_case(expected,r['case_id'],r['seed'],spec['cases'])
            # Legacy shared selectors and current disjoint selectors have
            # different builder annotations. Compare every physical field;
            # retain the original hashes and record this representation boundary.
            physical_source=deepcopy(source_robot);physical_actual=deepcopy(cfg['robot'])
            for robot in (physical_source,physical_actual):
                robot['structure']['data']['metadata'].pop('design_decisions',None)
            assert cfg['task']==expected_case['task'] and physical_actual==physical_source
            assert all(cfg['policy'][k]==expected_case['policy'][k] for k in ('controller','backend','dynamics_model','discretization'))
            assert r['receipt']['execution_status']=='completed' and not r['receipt']['cache_hit'] and r['receipt']['charged']['backend_solves']==1
            assert ev['validity']=='valid' and p['complete'] and p['valid_complete_execution']
            assert ev['source']==p['simulation'] and p['configuration']==r['configuration']
            assert r['acceptance']['execution_id']==eid
            motion=w.store.artifact(p['motion']);s=p['sampled_settling']; duration=cfg['task']['timing']['duration_s'];period=cfg['task']['timing']['sample_period_s']
            samples=[x for x in motion if duration-s['window_s']-1e-9<=x['time_s']<=duration+1e-9]
            assert len(samples)==6 and all(abs(x['time_s']-(duration-s['window_s']+i*period))<1e-8 for i,x in enumerate(samples))
            assert max(x['tip_error_m'] for x in samples)==s['max_error_m'] and max(x['tip_speed_m_s'] for x in samples)==s['max_speed_m_s']
            row=dict(execution_id=eid,structure_identity=digest(cfg['robot']),
                scientific_configuration_identity=digest(reporting_scientific_scope(cfg)),
                sources=dict(evaluation=r['evaluation'],profile=r['profile']),
                legacy_metrics=dict(terminal_error_m=p['terminal_error_m'],holding_max_error_m=s['max_error_m'],holding_max_speed_m_s=s['max_speed_m_s']))
            projection=authoritative_metrics(row,w.store.artifact); facts.update(projection['facts']);supersessions+=projection['supersessions']
            metrics={f['metric']:f['value'] for f in projection['facts'].values()}
            assert metrics==r['acceptance']['metrics']
            accepted=(ev['task_success'] is True and p['solver_error_count']==0 and 0<=p['force_bound_violation_n']<=1e-8 and s['max_error_m']<=s['position_limit_m'] and s['max_speed_m_s']<=s['speed_limit_m_s'])
            assert accepted==r['acceptance']['accepted']
            recipe=cfg['policy']['controller']['parameters']['data']['recipe']
            table.append(dict(role=g['role'],case_id=r['case_id'],seed=r['seed'],repetition=r['repetition'],
                execution_id=eid,candidate_id=r['candidate_id'],configuration=r['configuration'],
                task_identity=digest(cfg['task']),structure_identity=row['structure_identity'],
                scientific_configuration_identity=row['scientific_configuration_identity'],
                terminal_speed_weight=recipe['terminal_tip_speed_weight'],holding_speed_weight=recipe['holding_tip_speed_weight'],
                validity=ev['validity'],complete=True,official_reach_pass=ev['task_success'],joint_pass=accepted,
                holding_samples=len(samples),**metrics,force_bound_violation_n=p['force_bound_violation_n'],
                solver_errors=p['solver_error_count'],deadline_misses=p['deadline_misses'],control_updates=p['updates'],
                mean_update_s=p['mean_update_s'],mean_update_source=dict(reference=r['profile'],pointer='/detail/mean_update_s'),
                costs=r['cost'],cost_source='verification.json/groups/'+str(v['groups'].index(g))+'/records/'+str(g['records'].index(r))+'/cost',
                fact_ids={f['metric']:ref for ref,f in projection['facts'].items()}))
            for kind,ref in dict(evaluation=r['evaluation'],profile=r['profile'],motion=p['motion'],configuration=r['configuration']).items():
                path=OLD/'store/artifacts'/f'{ref["artifact_id"]}.json'
                assert path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==ref['artifact_id']
                manifest.append(dict(execution_id=eid,kind=kind,reference=ref,path=path.relative_to(ROOT).as_posix(),sha256=ref['artifact_id']))
        assert slots=={(x['case_id'],x['seed'],x['repetition']) for x in schedule(spec)}
    assert len(seen)==20 and len({r['structure_identity'] for r in table})==1
    aggregates=[aggregate_acceptance(g['records'],10,schedule=schedule(spec)) for g in v['groups']]
    comparison=compare_acceptance(aggregates[1],aggregates[0]);assert [a['accepted'] for a in aggregates]==[6,7]
    assert comparison['relation']=='improved'
    per_case=[]
    for case in dict.fromkeys(r['case_id'] for r in table):
        per_case.append(dict(case_id=case,roles={role:dict(joint_passes=sum(r['joint_pass'] for r in table if r['role']==role and r['case_id']==case),total=2,
            maxima={k:max(r[k] for r in table if r['role']==role and r['case_id']==case) for k in ('terminal_error_m','holding_max_error_m','holding_max_speed_m_s')},
            failing_seeds=[r['seed'] for r in table if r['role']==role and r['case_id']==case and not r['joint_pass']]) for role in ('unchanged_incumbent','selected_candidate')}))
    summary=dict(complete=True,unique_executions=20,roles={g['role']:dict(joint_passes=a['accepted'],total=a['scheduled'],
        maxima=a['metrics']) for g,a in zip(v['groups'],aggregates)},comparison=comparison,
        full_suite_pass=False,physical_structure_unchanged=True,selected_control_change={'terminal_tip_speed_weight':[0.05,0.10],'holding_tip_speed_weight':[0.05,0.05]},
        per_case=per_case,all_official_reach_pass=all(r['official_reach_pass'] for r in table),
        real_time=dict(demonstrated=False,deadline_misses=sum(r['deadline_misses'] for r in table),updates=sum(r['control_updates'] for r in table),
            mean_update_range_s=[min(r['mean_update_s'] for r in table),max(r['mean_update_s'] for r in table)],control_period_s=0.01),
        failures=[{k:r[k] for k in ('role','case_id','seed','execution_id','holding_max_speed_m_s')} for r in table if not r['joint_pass']],
        original_incumbent=selected['model_selected_at_research_stop'],selected_configuration=v['plan']['selected_candidate'],
        frozen_selection_outcome=selected['outcome'] if 'outcome' in selected else 'promote_frozen_candidate',
        limitations=['Fixed deterministic observations, not population probability or general robustness.','No continuous-time guarantee, global optimality, mathematical convergence or LLM superiority proof.','Real time was not a suite acceptance condition.'])
    atomic_json(OUT/'all_execution_results.json',table);atomic_json(OUT/'per_case_results.json',per_case)
    atomic_json(OUT/'aggregate_results.json',summary);atomic_json(OUT/'original_evidence_manifest.json',manifest)
    atomic_json(OUT/'corrected_fact_projection.json',dict(version=PROJECTION_VERSION,bound_facts=facts,supersessions=supersessions,legacy_snapshots_unchanged=True))
    with (OUT/'all_execution_results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        fields=['role','case_id','seed','repetition','execution_id','validity','complete','joint_pass','terminal_error_m','holding_max_error_m','holding_max_speed_m_s','holding_samples','mean_update_s','deadline_misses']
        writer=csv.DictWriter(f,fields,extrasaction='ignore');writer.writeheader();writer.writerows(table)
    return summary,facts,table,prior


def prepare():
    from tools.current_research_authority import accounting_binding
    from examples.research_campaign_v2 import search_rows
    w=workspace();start=guard(w);summary,facts,table,prior=frozen_results(w)
    searches=search_rows(w)
    researched=[]
    for r in searches:
        researched.append({k:r[k] for k in ('candidate_id','execution_id','changes','case_id','seed') if k in r} |
            dict(metrics=r['acceptance']['metrics'],joint_pass=r['acceptance']['accepted']))
    assert len(researched)==6
    auth=deepcopy(start['authorization']);current=accounting_binding(w.store,w.host.run_id)
    authority=dict(question='Evidence-backed LLM-organized design completing the declared task; global optimization is not required.',
        legal_actions={'report':{'execution_authorized':False}},prefetched_report_only=True,
        stop=auth['scientific_stop'],remaining_budget=w.store.remaining()['remaining'],
        experiment_permissions=dict(backend_solves=0,numerical_operations=0,workers=0,read_calls=0),
        accounting_binding=current, campaign_clock=auth['original_clock'],
        continuation_authorization=start['authorization_reference'])
    packet=dict(version=VERSION,summary=summary,research_executions=researched,bound_facts=facts,
        prior_review=dict(path=(OLD/'independent_results_review.json').relative_to(ROOT).as_posix(),sha256=hashlib.sha256((OLD/'independent_results_review.json').read_bytes()).hexdigest()),
        exact_result_tables='all_execution_results.json and per_case_results.json; complete set computed before any display filtering',
        chronology_and_risks=[
            'Three executed research batches, six executions: control weights .10 and .025; near section 1.00 and 1.05; far section 1.00 and 1.05. No other research batches ran.',
            'Near batch was an execution-only resumption of already accepted plan acf51de37cc32112a06a22a12491109a917367a4518ec01bf2f811db2d8b1e98, not a new provider proposal. Both near candidates kept terminal/holding .05/.05; near1.05 failed holding speed, near1.00 passed.',
            'Near feedback led model6 to accepted far-only batch plan d86d193aa1860270c38c622e9de256d55ffa3548848236c12e74c6689fdbf63a; both far candidates ran and passed their fresh nominal joint criterion, without establishing structural superiority.',
            'Model7 multi-variable length plan rejected for EXPLICIT_CANDIDATE_PATHS_MISMATCH. Model8 far-length plan rejected for PLAN_TOTAL_CAPACITY_INSUFFICIENT: planned budget 2000 seconds, required 2590; planned shortfall 590, available shortfall zero. No length experiments executed.',
            'Model9 STOP wrongly read zero shortfall as zero available capacity; retain as voluntary stop, not proven budget exhaustion, global optimum or optimal stopping.',
            'Historical implicit-zero initializer and current explicit-zero initializer have different raw task identities. Historical comparisons are descriptive; only the matched twenty verification executions share the current frozen protocol.',
            'Incumbent was not the only historical passing configuration; section batches also had passing nominal configurations. Historical and current suite memberships differ.',
            'Final selected result changes terminal-speed weight .05 to .10, with holding .05 and identical physics. Neither role passes the entire old fixed suite. Global optimization is not required by the user, but this does not change the old acceptance protocol.',
            'Frozen selection primary criterion is joint acceptance count. Componentwise comparison applies when counts tie, not a new requirement that all metrics improve.',
            'Earlier index3 final_model_interpretation is historical engineering delivery, not this report. Original STOP/failed report and raw records remain sealed.',
            'No mathematical optimization/convergence proof, new numerical experiments, generalization, causal attribution or LLM-versus-baseline superiority comparison was performed.'],
        version_boundary=dict(previous_commit='d5cc14da80574ebd7913cdbb8b745a3d93477f0e',repair=8,
            projection=PROJECTION_VERSION,scientific_implementation_unchanged=True,
            failed_request=start['authorization']['prior_failure']))
    schema=dict(type='object',additionalProperties=False,properties={
        'verification_execution_count':{'type':'integer'},'incumbent_joint_passes':{'type':'integer'},'candidate_joint_passes':{'type':'integer'},
        'entire_suite_passed':{'type':'boolean'},'physical_structure_changed':{'type':'boolean'},
        'selection':{'type':'string','enum':['promote_frozen_candidate','retain_incumbent','undecided']},
        **{k:{'type':'string'} for k in ('executed_research','feedback_and_choices','verification_and_tradeoffs','failing_conditions','scope_and_unverified','next_task')},
        'evidence_execution_ids':{'type':'array','items':{'type':'string'}}},required=[
        'verification_execution_count','incumbent_joint_passes','candidate_joint_passes','entire_suite_passed','physical_structure_changed','selection',
        'executed_research','feedback_and_choices','verification_and_tradeoffs','failing_conditions','scope_and_unverified','next_task','evidence_execution_ids'])
    config=auth['provider_config']
    payload=dict(model=config['model'],max_tokens=config['max_tokens'],stream=False,
        thinking={'type':config['thinking']},reasoning_effort=config['reasoning_effort'],
        messages=[dict(role='system',content='Produce a concise Chinese current final research interpretation by calling research_final_report exactly once. This is a report sink only: no action dispatch, scientific execution or model-callable retrieval. All necessary evidence is prefetched. Explain the executed six research and twenty matched verification executions, feedback, frozen selection, failures, tradeoffs, and uncertainty. Do not copy the full result table. Reference execution IDs for claims. Distinguish observed evidence from inference; do not assume favorable outcomes or generalization. Preserve every known counterexample and version boundary. Return the complete object required by the function schema; no tool envelope is needed for this report-only sink.'),dict(role='user',content='')],
        tools=[dict(type='function',function=dict(name='research_final_report',description='Record a bounded interpretation; no execution is authorized.',parameters=schema))])
    archive=EvidenceArchive(OUT/'context_assembly',scope=dict(context_id=w.host.run_id,role='report_only',authorization=start['authorization_reference']),stores=(w.store,))
    payload,audit=assemble_request(payload,config,'final_report',packet,archive=archive,authority=authority)
    request=dict(payload=payload,context_assembly_audit=audit,authority=authority,report_schema=schema)
    atomic_json(OUT/'prepared_report_request.json',request)
    assert request_facts(request)==facts
    restored=read(OUT/'prepared_report_request.json');drift=deepcopy(facts);next(iter(drift.values()))['value']=999
    assert request_facts(restored)==facts and request_facts(restored)!=drift
    checks=[]
    rows=read(OUT/'corrected_fact_projection.json')['supersessions']
    for c in start['authorization']['prior_failure']['conflicts']:
        found=[r for r in rows if r['legacy_fact_id']==c['source_fact']]
        assert len(found)==1 and found[0]['canonical_value']==c['verification_value'] and found[0]['legacy_value']==c['bound_value']
    assembly=assemble_context('final_report',packet,archive=archive,authority=authority)
    fid=next(iter(facts));fact=facts[fid]
    for key,bad in [('execution_id','foreign'),('unit','N'),('metric','foreign'),('source_artifact',table[1]['configuration'])]:
        try:retrieve_fact(assembly,fid,archive=archive,expected={key:bad})
        except ValueError as e:assert 'CROSS_EXECUTION' in str(e);checks.append(key)
        else:raise AssertionError('WRONG_BINDING_NOT_REJECTED')
    wrong=dict(execution_id='foreign',sources=dict(evaluation=table[0]['configuration'],profile=table[0]['configuration']),structure_identity='',scientific_configuration_identity='',legacy_metrics={})
    try:authoritative_metrics(wrong,w.store.artifact)
    except (ValueError,KeyError):checks.append('foreign_source_projection')
    else:raise AssertionError('WRONG_SOURCE_NOT_REJECTED')
    changed={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ALLOWED}
    gate=dict(passed=True,actual_saved_executions=20,all_sources_exact=True,holding_grid_samples=6,
        joint_counts=[6,7],wrong_bindings_rejected=checks,restored_facts_frozen=True,
        measurement=audit['measurement'],permissions=authority['experiment_permissions'],current_accounting=current,
        implementation_files=changed,grant_unchanged=True,clock_unchanged=True,scientific_stop_unchanged=True)
    atomic_json(OUT/'offline_acceptance.json',gate)
    with w.store.transaction() as db:
        ref=plain(w.store.put(db,dict(version=VERSION,authorization=start['authorization_reference'],gate=gate,previous_repairs=7,cumulative_material_repairs=8)))
        w.store.event(db,w.host.run_id,'report_projection_repair','completed',outputs=[ref],version=VERSION)
        state=w.store.session(w.host.run_id,db)['state'];state['report_completion_repair']=ref;w.store.update_state(db,w.host.run_id,state)
    # Do not replace scientific freeze, working state, rounds or original STOP.
    print(json.dumps(dict(gate=True,measurement=gate['measurement'],research_executions=len(researched),joint_counts=[6,7])))


def attempt(number=0, correction=None):
    from examples.gvs_nmpc_route_experiment import load_credential
    from tools.platform_models import DeepSeekAdapter
    w=workspace();start=guard(w,provider=True);request=read(OUT/'prepared_report_request.json');gate=read(OUT/'offline_acceptance.json')
    assert gate['passed'] and all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in gate['implementation_files'].items())
    payload=deepcopy(request['payload']);config=start['authorization']['provider_config']
    if correction:
        payload['messages'].append(dict(role='user',content='Independent factual/protocol discrepancies only; revise the complete report without assuming a favorable conclusion: '+json.dumps(correction,ensure_ascii=False)))
    from tools.context_assembly import measure_input
    assert measure_input(payload,config,'final_report')['passed']
    key=f'report-completion-model-{number}'
    if w.store.lookup(w.host.run_id,key):raise ValueError('EXISTING_ATTEMPT_NO_AUTOMATIC_RESEND')
    if number:
        prev=read(OUT/f'model_attempt_{number-1}.json')
        earlier=[read(OUT/f'model_attempt_{i}.json') for i in range(number)]
        if correction and any(r.get('request_kind')=='correction' for r in earlier):
            raise ValueError('ONLY_ONE_CORRECTION_AUTHORIZED')
        if not correction:
            assert prev['status']=='failed' and not prev.get('raw_response') and prev.get('transport_retry_eligible') is True
            assert not any(r.get('request_kind')=='transport_retry' for r in earlier)
            previous_id=f'report-completion-model-{number-1}'
            previous_call=w.store.lookup(w.host.run_id,previous_id)
            assert previous_call['receipt'] and previous_call['status']=='failed'
            assert not any(e['kind']=='model_raw_response' and e['status']=='completed' and e.get('request_id')==previous_id for e in w.store.events(w.host.run_id))
            assert not any(r.get('status')=='completed' for r in earlier)
            atomic_json(OUT/'transport_retry_review.json',dict(previous_request_id=previous_id,
                receipt=prev['receipt'],complete_response=False,accepted_report_or_scientific_action=False,
                one_retry_authorized=True,usage=prev['usage']))
    load_credential(Path.home()/'.codex/.env')
    with w.store.transaction() as db:
        ref=plain(w.store.put(db,payload));cref=plain(w.store.put(db,config))
    row,fresh=w.store.reserve(w.host.run_id,key,digest(payload),'model-transport',
        {**zero(),'model_calls':1,'wall_s':config['timeout_s']},inputs=[ref,cref],kind='model_request',version='6.0.0')
    assert fresh
    atomic_json(OUT/f'outgoing_request_{number}.json',dict(payload=payload,context_assembly_audit=request['context_assembly_audit'],measurement=measure_input(payload,config,'final_report')))
    adapter=DeepSeekAdapter();adapter.timeout_s=config['timeout_s'];adapter.base_url=config['base_url']
    then=time.monotonic();raw=None
    try:
        raw=adapter.respond(payload,number);_no_secrets(raw)
        atomic_json(OUT/f'raw_provider_response_{number}.json',raw)
        with w.store.transaction() as db:
            rawref=plain(w.store.put(db,dict(raw=raw,status='completed')))
            w.store.event(db,w.host.run_id,'model_raw_response','completed',parent=row['parent_id'],request=key,execution=row['execution_id'],inputs=[ref],outputs=[rawref],version='6.0.0')
        choice=raw['choices'][0];assert choice['finish_reason']!='length'
        calls=choice['message']['tool_calls'];assert len(calls)==1 and calls[0]['function']['name']=='research_final_report'
        report=json.loads(calls[0]['function']['arguments'])
        schema=request['report_schema']
        if not isinstance(report,dict) or set(report)!=set(schema['required']):
            raise ValueError('REPORT_FIELDS_MISMATCH')
        kinds={'integer':int,'boolean':bool,'string':str,'array':list}
        for field,spec in schema['properties'].items():
            value=report[field]
            if type(value)!=kinds[spec['type']] or ('enum' in spec and value not in spec['enum']):
                raise ValueError('REPORT_FIELD_TYPE_OR_ENUM: '+field)
            if spec['type']=='array' and any(not isinstance(x,str) for x in value):
                raise ValueError('REPORT_EXECUTION_ID_TYPE')
        result=dict(status='completed',interpretation=report,raw_response=rawref,usage=raw.get('usage'),
            report_binding=digest(read(OUT/'all_execution_results.json')),verification_executions=20,scientific_action_dispatched=False)
        charged=w.store.complete(row,receipt(row,'model.deepseek','completed'),result,time.monotonic()-then,kind='model_response')
    except Exception as e:
        details=getattr(e,'provider_response',None)
        result=dict(status='failed',error=str(e),provider_failure=details,raw_response=raw is not None,
            usage=raw.get('usage') if isinstance(raw,dict) else None,transport_retry_eligible=raw is None and details is not None and details.get('failure_details',{}).get('category') in ('connection','dns','proxy'))
        charged=w.store.complete(row,receipt(row,'model.deepseek','failed'),result,time.monotonic()-then,kind='model_response')
    result['receipt']=charged
    result['request_kind']='correction' if correction else 'transport_retry' if number else 'interpretation'
    atomic_json(OUT/f'model_attempt_{number}.json',result)
    print(json.dumps(result,ensure_ascii=False))


def settle(remote_sha):
    w=workspace();start=read(START);guard(w);head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert head==remote_sha
    baseline=start['authorization']['baseline']['used'];used=w.store.remaining()['used']
    model_wall=used['wall_s']-baseline['wall_s']-1800
    elapsed=time.time()-start['authorization']['started_unix']
    assert 0<=elapsed<=1800
    result=dict(elapsed_s=elapsed,separately_charged_provider_s=model_wall,verified_remote_sha=remote_sha,repairs=8,
        original_clock=start['authorization']['original_clock'],standalone_numerical_operations=0)
    rec=w.store.complete(start['reservation'],receipt(start['reservation'],'engineering.report_completion'),result,max(0,elapsed-model_wall))
    usage=w.store.remaining();result.update(status='settled_local_authoritative',receipt=rec,usage=usage,
        incremental={k:usage['used'][k]-baseline[k] for k in baseline},remote_snapshot_has_delivery_reservation=True)
    assert result['incremental']['wall_s']<=1800 and result['incremental']['model_calls']<=3 and result['incremental']['tool_calls']<=12
    atomic_json(D/'report_completion_settled_costs.json',result);print(json.dumps(result))


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['begin','prepare','attempt','settle']);p.add_argument('--started-unix',type=float);p.add_argument('--number',type=int,default=0);p.add_argument('--remote-sha');p.add_argument('--correction',type=Path)
    a=p.parse_args()
    if a.mode=='begin':begin(a.started_unix)
    elif a.mode=='prepare':prepare()
    elif a.mode=='attempt':attempt(a.number,read(a.correction) if a.correction else None)
    else:settle(a.remote_sha)

if __name__=='__main__':main()
