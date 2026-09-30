"""Verify, freeze, run and audit the single Stage 3.35 math-led Route retry."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'): os.environ.setdefault(name,'1')

from examples.gvs_nmpc_route_experiment import inspect as standard_inspect, load_credential
from examples.gvs_stage334 import historical_sources
from extensions.tendon_family.route import create, check_run_eligibility
from schemas.platform import ModelResponse
from schemas.platform_analysis import EndpointTarget, TaskAnalysisProtocol
from tools.platform_host import Host
from tools.platform_models import DeepSeekAdapter, payload_for, provider_name
from tools.platform_store import Store, plain
from tools.runtime_identity import require_softagent_runtime
from tools.state_io import atomic_json, digest, read


SOURCE=Path('runs/stage333_bounded_recovery_independent_lengths_20260929_114923')
VERSIONS={
    'route.advance':'1.0.0','route.inspect':'1.0.0','route.record_analysis':'1.0.0',
    'analysis.linearize_candidate':'1.0.0','analysis.control_metrics':'2.0.0',
    'analysis.bounded_endpoint':'1.0.0','design.screen':'1.0.0','design.optimize_math':'1.0.0',
    'analysis.compare_candidates':'1.0.0','analysis.gvs_candidate_evaluate':'1.0.0',
    'control.profile_describe':'1.0.0','control.profile_report':'1.0.0',
    'diagnostics.saved_trajectory':'2.0.0','evaluation.run':'1.0.0','evidence.read':'1.0.0',
    'session.control':'1.0.0','simulation.run':'1.0.0',
}
VARIABLES={'components/near/length_m':(.15,.17),'components/far/length_m':(.11,.13),
    'design/section_scale':(.95,1.05)}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protocol_and_target(inp):
    task=inp['task'];controller=inp['policy']['controller']['parameters']['data']
    lengths={row['id']:row['length_m'] for row in inp['robot']['structure']['data']['components'] if 'length_m' in row}
    protocol=TaskAnalysisProtocol(baseline_lengths_m=lengths,duration_s=task['timing']['duration_s'],
        period_s=task['timing']['control_period_s'],frequency_rad_s=[.1,1.,10.,100.,1000.],samples_s=[])
    target=EndpointTarget(position_m=tuple(task['goal']['data']['target_m']),
        position_tolerance_m=task['evaluator']['parameters']['data']['tolerance_m'],position_scale_m=.01,
        tip_speed_limit_m_s=controller['settling']['speed_limit_m_s'],
        tip_velocity_scale_m_s=controller['settling']['speed_limit_m_s'])
    return protocol,target


def provider_fixture_call(host,trace,turn,tool,arguments,reason,*,cache='new'):
    """Encode advertised tools, decode native DeepSeek JSON, then invoke Host."""
    payload=payload_for(host,DeepSeekAdapter())
    advertised=next(item for item in payload['tools'] if item['function']['name']==provider_name(tool))
    envelope=dict(arguments=arguments,reason=reason,tool_version=VERSIONS[tool],evidence=[])
    raw=dict(id='offline-stage335-'+str(turn),object='chat.completion',model=payload['model'],
        choices=[dict(index=0,finish_reason='tool_calls',message=dict(role='assistant',content=None,
            tool_calls=[dict(id='offline-call-'+str(turn),type='function',function=dict(
                name=advertised['function']['name'],arguments=json.dumps(envelope,separators=(',',':'))))]))],
        usage=dict(prompt_tokens=0,completion_tokens=0,total_tokens=0))
    decoded=DeepSeekAdapter().decode(ModelResponse(raw=raw),turn,
        host.store.session(host.run_id)['snapshot']['input']['policy']['tool_bindings'])
    decoded['cache']=cache
    receipt=plain(host.invoke(decoded))
    trace.append(dict(turn=turn,tool=tool,advertised_name=advertised['function']['name'],
        advertised_version=advertised['function']['parameters']['properties']['tool_version']['const'],
        response=raw,decoded=decoded,receipt=receipt))
    if receipt['execution_status']!='completed': raise RuntimeError(json.dumps(receipt,indent=2))
    return receipt['output'],host.store.artifact(receipt['output']),payload


def offline(root):
    runtime=require_softagent_runtime();root.mkdir(parents=True,exist_ok=False)
    budget=dict(tool_calls=80,model_calls=0,backend_solves=0,worker_calls=0,wall_s=7200.)
    store=Store(root/'host');store.create(dict(project_id='stage335-offline',grant_id='stage335-offline',
        authorization_source='Deterministic provider-format fixture; zero network/backend/NMPC/worker use.',budget=budget))
    inp=deepcopy(read(SOURCE/'resolved_frozen_input.json'));inp['run_id']='stage335-offline-provider-host'
    protocol,target=protocol_and_target(inp)
    with store.transaction() as db: pref=plain(store.put(db,protocol));tref=plain(store.put(db,target))
    inp['policy'].update(budget=budget,timeout_s=1800.,allowed_tools=[],tool_bindings=VERSIONS)
    inp['policy']['model']['max_turns']=24
    inp['policy']['route']['data'].update(historical_case=None,max_trials=3,analysis_protocol=pref,
        endpoint_target=tref,analysis_required_before_run=True,math_evaluation_limit=8,
        math_selection_required_before_run=True,stop_on_task_success=True,
        guidance='Offline provider-format fixture only: select an exact original optimizer proposal and bind it to the changed build; never execute a backend.')
    create(store.root,inp);host=Host(store.root,inp['run_id'],actor='offline-provider-fixture')
    trace=[];turn=0
    def call(tool,arguments,reason,cache='new'):
        nonlocal turn
        result=provider_fixture_call(host,trace,turn,tool,arguments,reason,cache=cache);turn+=1;return result

    seed_receipt,_,first_payload=call('route.advance',dict(node_id='seed',action='build',
        combination='candidate_gvs_nmpc',candidate_id='unchanged-analysis-seed',changes={},variables={},max_trials=1,
        evidence=[],reason='Build the unchanged configuration only as a mathematical seed.',
        next_step='Obtain candidate-bound shared mathematics.'),'Build the solve-free analysis seed.')
    linear_ref,linear,_=call('analysis.linearize_candidate',dict(source_node='seed',protocol=pref),
        'Linearize the exact owned seed build.')
    metrics_ref,_,_=call('analysis.control_metrics',dict(models=[linear_ref],protocol=pref,implementation='scipy'),
        'Use the returned candidate-linearization envelope through the shared metrics tool.')
    endpoint_ref,_,_=call('analysis.bounded_endpoint',dict(models=[linear_ref],protocol=pref,target=tref),
        'Use the same returned envelope for bounded endpoint analysis.')
    screen_ref,_,_=call('design.screen',dict(source_node='seed',protocol=pref,linearization=linear_ref,
        metrics=metrics_ref,endpoint=endpoint_ref),'Create the advisory seed screen from returned references.')
    optimize_ref,optimized,_=call('design.optimize_math',dict(source_node='seed',protocol=pref,target=tref,
        variables=VARIABLES,material_scenarios=['compliant','stiff'],max_evaluations=6,
        objective='controller_start_local_endpoint_lexicographic_v1'),
        'Run the bounded position-only local proxy and retain its original seed provenance.')
    repeat_ref,repeated,_=call('design.optimize_math',dict(source_node='seed',protocol=pref,target=tref,
        variables=VARIABLES,material_scenarios=['compliant','stiff'],max_evaluations=2,
        objective='controller_start_local_endpoint_lexicographic_v1'),
        'Verify cumulative accounting and effective-scientific-identity cache reuse.')
    proposal=optimized['proposals'][0]
    changes={**proposal['parameters'],'design/material_scenario':proposal['material_scenario']}
    changed_receipt,changed_route,_=call('route.advance',dict(node_id='selected-build',action='build',
        combination='candidate_gvs_nmpc',candidate_id='offline-selected-proposal',changes=changes,variables={},max_trials=1,
        evidence=[seed_receipt],reason='Select the exact optimizer proposal '+proposal['candidate_id']+'.',
        next_step='Obtain candidate-bound analysis before testing the run gate.'),
        'Build the exact scripted proposal for integration verification only.')
    changed_linear,_,_=call('analysis.linearize_candidate',dict(source_node='selected-build',protocol=pref),
        'Linearize the selected changed build.')
    changed_metrics,_,_=call('analysis.control_metrics',dict(models=[changed_linear],protocol=pref,implementation='scipy'),
        'Compute changed-build local metrics from its returned envelope.')
    changed_endpoint,_,_=call('analysis.bounded_endpoint',dict(models=[changed_linear],protocol=pref,target=tref),
        'Compute changed-build endpoint evidence from its returned envelope.')
    changed_screen,_,_=call('design.screen',dict(source_node='selected-build',protocol=pref,
        linearization=changed_linear,metrics=changed_metrics,endpoint=changed_endpoint),
        'Create the candidate-bound advisory screen.')
    report_ref,report,_=call('route.record_analysis',dict(node_id='selected-report',source_node='selected-build',
        evidence=[changed_route['detail']['result'],optimize_ref],linearization=changed_linear,metrics=changed_metrics,
        endpoint=changed_endpoint,screen=changed_screen,math_optimization=optimize_ref,
        selected_optimizer_candidate_id=proposal['candidate_id'],validation_disposition='recommended',
        reason='The exact original proposal is linked; local evidence is advisory for backend spending.',
        next_step='Verify execution eligibility without executing.'),'Bind the original optimizer proposal to the changed build.')
    eligible=check_run_eligibility(host,'selected-build','offline-selected-proposal')
    usage=store.remaining(host.run_id);ledger=store.session(host.run_id)['state']['route']['math_evaluations']
    advertised={item['function']['description'].split('@',1)[0]:item for item in first_payload['tools']}
    record_tool=advertised['route.record_analysis']['function']
    verification=dict(actual_provider_schema_contains_record_analysis='route.record_analysis' in advertised,
        provider_name_agrees=record_tool['name']==provider_name('route.record_analysis'),
        provider_version_agrees=record_tool['parameters']['properties']['tool_version']['const']=='1.0.0',
        decoder_and_host_completed=all(item['receipt']['execution_status']=='completed' for item in trace),
        envelope_metrics_and_endpoint_completed=True,original_optimizer_retained=report['detail']['summary']['math_optimization']==optimize_ref,
        exact_selected_proposal=report['detail']['summary']['math_selection_trace']['optimizer_candidate_id']==proposal['candidate_id'],
        proposal_matches_changed_build=report['detail']['summary']['math_selection_trace']['matches_proposal'],
        execution_gate_passed_without_run=eligible['eligible'],cumulative_math_used=ledger['used'],
        cumulative_math_remaining=ledger['remaining'],cache_reuse_observed=repeated['provenance']['cache_hits_this_call']>0,
        no_provider_backend_worker=all(usage['used'][key]==0 for key in ('model_calls','backend_solves','worker_calls')),
        no_physical_run=store.session(host.run_id)['state']['route']['incumbent'] is None,
        scripted_selection_not_llm_evidence=True)
    verification['passed']=all(value for key,value in verification.items() if isinstance(value,bool) and key!='scripted_selection_not_llm_evidence')
    for name,value in (('runtime_identity',runtime),('provider_tools',first_payload['tools']),('provider_fixture_trace',trace),
            ('optimizer_original',optimized),('optimizer_repeat',repeated),('selected_proposal',proposal),
            ('route_report',report),('execution_eligibility',eligible),('usage',usage),('verification',verification)):
        atomic_json(root/(name+'.json'),value)
    if not verification['passed'] or ledger['used']>8: raise RuntimeError(json.dumps(verification,indent=2))
    print('Offline provider-to-Host verification passed: '+str(root),flush=True)
    return verification


def recover_offline(root):
    """Resume the preserved citation-fixture failure without new mathematics."""
    runtime=require_softagent_runtime();host=Host(root/'host','stage335-offline-provider-host',actor='offline-provider-fixture')
    trace=[];events=host.store.events(host.run_id)
    reserved={event['request_id']:event for event in events if event['kind']=='tool' and event['status']=='reserved'}
    with host.store.connect(True) as db:
        rows=list(db.execute('SELECT request_id,receipt FROM calls WHERE run_id=? ORDER BY rowid',(host.run_id,)))
    for turn,row in enumerate(rows):
        request=host.store.artifact(reserved[row['request_id']]['inputs'][0]);payload=payload_for(host,DeepSeekAdapter())
        advertised=next(item for item in payload['tools'] if item['function']['name']==provider_name(request['tool_id']))
        envelope={key:request[key] for key in ('arguments','reason','evidence','tool_version')}
        raw=dict(id='offline-stage335-replay-'+str(turn),object='chat.completion',model=payload['model'],
            choices=[dict(index=0,finish_reason='tool_calls',message=dict(role='assistant',content=None,
                tool_calls=[dict(id='offline-replay-'+str(turn),type='function',function=dict(name=advertised['function']['name'],
                    arguments=json.dumps(envelope,separators=(',',':'))))]))],usage=dict(prompt_tokens=0,completion_tokens=0,total_tokens=0))
        decoded=DeepSeekAdapter().decode(ModelResponse(raw=raw),turn,
            host.store.session(host.run_id)['snapshot']['input']['policy']['tool_bindings']);decoded['cache']=request['cache']
        receipt=plain(host.invoke(decoded))
        trace.append(dict(turn=turn,tool=request['tool_id'],advertised_name=advertised['function']['name'],
            advertised_version=advertised['function']['parameters']['properties']['tool_version']['const'],
            response=raw,decoded=decoded,receipt=receipt,replayed_sealed_request=True))
    def output(turn):
        import json as json_module
        return json_module.loads(host.store.lookup(host.run_id,'model-'+str(turn)+'-tool')['receipt'])['output']
    optimize_ref=output(5);optimized=host.store.artifact(optimize_ref);repeat_ref=output(6);repeated=host.store.artifact(repeat_ref)
    proposal=optimized['proposals'][0];changed_route=host.store.artifact(output(7));changed_node=changed_route['detail']['result']
    changed_linear,changed_metrics,changed_endpoint,changed_screen=(output(i) for i in range(8,12))
    completed_report=next((item for item in trace if item['tool']=='route.record_analysis'
        and item['receipt']['execution_status']=='completed'),None)
    if completed_report:
        report_ref=completed_report['receipt']['output'];report=host.store.artifact(report_ref);payload=payload_for(host,DeepSeekAdapter())
    else:
        report_ref,report,payload=provider_fixture_call(host,trace,len(rows),'route.record_analysis',dict(
            node_id='selected-report-corrected',source_node='selected-build',evidence=[changed_node,optimize_ref],
            linearization=changed_linear,metrics=changed_metrics,endpoint=changed_endpoint,screen=changed_screen,
            math_optimization=optimize_ref,selected_optimizer_candidate_id=proposal['candidate_id'],
            validation_disposition='recommended',reason='The exact original proposal is linked; local evidence is advisory for backend spending.',
            next_step='Verify execution eligibility without executing.'),'Correct the node-result citation while preserving the original optimizer result.')
    eligible=check_run_eligibility(host,'selected-build','offline-selected-proposal')
    usage=host.store.remaining(host.run_id);ledger=host.store.session(host.run_id)['state']['route']['math_evaluations']
    advertised={item['function']['description'].split('@',1)[0]:item for item in payload['tools']};record_tool=advertised['route.record_analysis']['function']
    verification=dict(actual_provider_schema_contains_record_analysis='route.record_analysis' in advertised,
        provider_name_agrees=record_tool['name']==provider_name('route.record_analysis'),
        provider_version_agrees=record_tool['parameters']['properties']['tool_version']['const']=='1.0.0',
        decoder_and_host_completed_after_preserved_correction=trace[-1]['receipt']['execution_status']=='completed',
        preserved_citation_failure=any(item['receipt']['execution_status']=='failed' and
            'ROUTE_EVIDENCE_REQUIRED' in (item['receipt'].get('error') or '') for item in trace),
        original_optimizer_retained=report['detail']['summary']['math_optimization']==optimize_ref,
        exact_selected_proposal=report['detail']['summary']['math_selection_trace']['optimizer_candidate_id']==proposal['candidate_id'],
        proposal_matches_changed_build=report['detail']['summary']['math_selection_trace']['matches_proposal'],
        execution_gate_passed_without_run=eligible['eligible'],cumulative_math_used=ledger['used'],
        cumulative_math_remaining=ledger['remaining'],cache_reuse_observed=repeated['provenance']['cache_hits_this_call']>0,
        no_provider_backend_worker=all(usage['used'][key]==0 for key in ('model_calls','backend_solves','worker_calls')),
        no_physical_run=host.store.session(host.run_id)['state']['route']['incumbent'] is None,
        scripted_selection_not_llm_evidence=True)
    verification['passed']=all(value for key,value in verification.items() if isinstance(value,bool) and key!='scripted_selection_not_llm_evidence')
    for name,value in (('runtime_identity',runtime),('provider_tools',payload['tools']),('provider_fixture_trace',trace),
            ('optimizer_original',optimized),('optimizer_repeat',repeated),('selected_proposal',proposal),
            ('route_report',report),('execution_eligibility',eligible),('usage',usage),('verification',verification)):
        atomic_json(root/(name+'.json'),value)
    if not verification['passed'] or ledger['used']>8: raise RuntimeError(json.dumps(verification,indent=2))
    print('Recovered offline provider-to-Host verification without new math: '+str(root),flush=True)
    return verification


def package_offline(source,destination):
    """Create compact tracked review evidence; the SQLite store remains local-only."""
    require_softagent_runtime();destination.mkdir(parents=True,exist_ok=True)
    original=read(source/'optimizer_original.json');repeat=read(source/'optimizer_repeat.json')
    summary=dict(stage='3.35',scope='offline scripted provider-format integration; not LLM reasoning or robot performance',
        source=str(source),runtime=read(source/'runtime_identity.json'),verification=read(source/'verification.json'),
        usage=read(source/'usage.json'),execution_eligibility=read(source/'execution_eligibility.json'),
        selected_proposal=read(source/'selected_proposal.json'),route_report=read(source/'route_report.json'),
        optimizer_original={key:original[key] for key in ('objective','proposals','provenance','limitations')},
        optimizer_repeat={key:repeat[key] for key in ('objective','proposals','provenance','limitations')},
        preserved_failure='The first record_analysis fixture call cited the provider result wrapper instead of the Route build node result. Its failed receipt is retained; the same store was resumed with the correct returned node reference and no new mathematical evaluation.')
    atomic_json(destination/'offline_verification.json',summary)
    for name in ('provider_tools.json','provider_fixture_trace.json','runtime_identity.json'):
        atomic_json(destination/name,read(source/name))
    retained=[]
    for path in (Path('evidence/stage334_math_led_design_20260930/matlab_scipy_endpoint_comparison.json'),
                 Path('evidence/stage334_math_led_design_20260930/representative_endpoint_matrices.npz'),
                 Path('evidence/stage334_math_led_design_20260930/report.md')):
        retained.append(dict(path=str(path).replace('\\','/'),size=path.stat().st_size,sha256=sha256(path)))
    atomic_json(destination/'retained_evidence.json',dict(previous_stage_commit='d67dd2c37128f0109fe40307d84175cc558353b8',
        retained_matlab_scipy_not_repeated=True,files=retained))
    local=[]
    for path in sorted((source/'host').rglob('*')):
        if path.is_file(): local.append(dict(path=str(path.resolve()),size=path.stat().st_size,sha256=sha256(path)))
    atomic_json(destination/'local_only_artifacts.json',dict(remotely_available=False,
        note='Hashes identify local raw storage; they do not make it remotely available.',files=local))
    files=[path for path in destination.iterdir() if path.is_file() and path.name!='offline_manifest.json']
    atomic_json(destination/'offline_manifest.json',dict(files={path.name:dict(size=path.stat().st_size,sha256=sha256(path))
        for path in files},provider_requests=0,backend_attempts=0,nmpc_solves=0,workers=0,math_evaluations=8))
    print('Packaged offline evidence: '+str(destination),flush=True)


def package_blocked_live(source,destination):
    """Retain a frozen live launch that an external platform gate rejected pre-process."""
    require_softagent_runtime();destination.mkdir(parents=True,exist_ok=True)
    for name in ('freeze_manifest.json','workflow.json','frozen_input.json','analysis_protocol.json',
            'endpoint_target.json','experiment_prompt.json','provider_tools.json','provider_configuration.json',
            'runtime_identity.json','behavior_audit.json','math_influence_audit.json'):
        atomic_json(destination/('live_'+name),read(source/name))
    blocker=dict(stage='3.35',run_id=read(source/'workflow.json')['run_id'],launch_process_started=False,
        provider_request_submitted=False,provider_responses=0,tool_calls=0,live_math_evaluations=0,
        backend_attempts=0,nmpc_solves=0,workers=0,charged_wall_s=0.,
        platform_rejection=('This executes a paid external DeepSeek workflow using configured credentials and may export '
            'repository-derived data, but trusted user authorization for this exact destination, payload, and spend is not established.'),
        handling='No retry, workaround, indirect execution, counter reset, or second live experiment was attempted.',
        acceptance_a_math_influenced_executed_design=False,
        acceptance_b_robot_outcomes=dict(valid_execution='unavailable',official_reach='unavailable',
            sampled_settling='unavailable',complete_update_real_time='unavailable'),
        push_status=dict(pushed=False,local_commit=read(source/'workflow.json')['implementation_commit'],
            platform_rejection='External origin push rejected because trust and authorization for the specific payload/destination were not established.'))
    atomic_json(destination/'live_blocker.json',blocker)
    local=[]
    for path in sorted(source.rglob('*')):
        if path.is_file(): local.append(dict(path=str(path.resolve()),size=path.stat().st_size,sha256=sha256(path)))
    atomic_json(destination/'live_local_only_artifacts.json',dict(remotely_available=False,
        note='The prepared raw store has no provider response or trajectory. Hashes do not make local files remotely available.',files=local))
    files=[path for path in destination.iterdir() if path.is_file() and path.name!='delivery_manifest.json']
    atomic_json(destination/'delivery_manifest.json',dict(files={path.name:dict(size=path.stat().st_size,sha256=sha256(path))
        for path in files},implementation_commit=blocker['push_status']['local_commit'],live_launch='blocked_before_process',
        provider_requests=0,tool_calls=0,math_evaluations=dict(offline=8,live=0,total=8),backend_attempts=0,workers=0))
    print('Packaged blocked live freeze: '+str(destination),flush=True)


def package_live_result(source,destination):
    """Package the completed one-shot live audit without mutating its raw store."""
    runtime=require_softagent_runtime();destination.mkdir(parents=True,exist_ok=True)
    workflow=read(source/'workflow.json');run_id=workflow['run_id'];store=Store(source)
    audit=read(source/'behavior_audit.json');math=read(source/'math_influence_audit.json')
    freeze=read(source/'freeze_manifest.json');session=store.session(run_id);route=session['state']['route']
    frozen_files=freeze['files'];hashes={name:sha256(source/name) for name in frozen_files}
    prelaunch=read(destination/'live_behavior_audit.json')
    freeze_verification=dict(run_id=run_id,verified_before_launch=True,
        verification_basis=('The retained prepared session and all frozen-file digests were checked immediately before '
            'the single launch; this post-run package recomputes those immutable file digests and retains the original '
            'zero-use prelaunch audit separately.'),
        implementation_commit=freeze['implementation_commit'],implementation_dirty=freeze['implementation_dirty'],
        runtime=runtime,runtime_matches_frozen=runtime==read(source/'runtime_identity.json'),
        frozen_file_hashes_match=hashes==frozen_files,
        files={name:dict(expected=frozen_files[name],actual=hashes[name],matches=hashes[name]==frozen_files[name])
            for name in frozen_files},limits=freeze['limits'],live_math_evaluation_limit=freeze['live_math_evaluation_limit'],
        total_offline_plus_live_limit=freeze['total_offline_plus_live_limit'],
        retained_prelaunch_counts={key:prelaunch[key] for key in ('real_model_requests','tool_calls','backend_executions')},
        retained_prelaunch_status=prelaunch['status'])
    if not freeze_verification['frozen_file_hashes_match'] or not freeze_verification['runtime_matches_frozen']:
        raise RuntimeError('LIVE_FREEZE_CHANGED')

    optimizer_ref=json.loads(store.lookup(run_id,'model-5-tool')['receipt'])['output']
    optimizer=store.artifact(optimizer_ref);proposals=optimizer['proposals'];selected=proposals[0];other=proposals[1]
    build=next(node for node in route['nodes'] if node.get('action')=='build' and node.get('selection',{}).get('changes'))
    failed_report=next(node for node in route['nodes'] if node.get('action')=='analyze')
    report_call=store.lookup(run_id,'model-21-tool');report_receipt=json.loads(report_call['receipt'])
    changed=build['selection']['changes'];selected_parameters={**selected['parameters'],
        'design/material_scenario':selected['material_scenario']}
    exact_parameters_match=changed==selected_parameters
    primary_tied=selected['objective']['position_residual_upper_bound_ratio']==other['objective']['position_residual_upper_bound_ratio']
    lower_secondary=selected['objective']['feasible_witness_normalized_input_energy'] < other['objective']['feasible_witness_normalized_input_energy']
    attempted_id=failed_report['selection']['selected_optimizer_candidate_id']
    cited_refs={key:failed_report['selection'][key] for key in
        ('linearization','metrics','endpoint','screen','math_optimization')}
    cited_refs['build_result']=build['result']
    cited_artifacts={key:store.artifact(ref) for key,ref in cited_refs.items()}
    binding_summary={key:dict(candidate_id=value['bindings'][0]['candidate_id'],
        source_node=value['bindings'][0]['source_node'],
        scientific_configuration_identity=value['bindings'][0]['scientific_configuration_identity'])
        for key,value in cited_artifacts.items() if key in ('linearization','metrics','endpoint','screen')}
    candidate_bound_consistent=all(value['candidate_id']==build['selection']['candidate_id']
        and value['source_node']==build['node_id']
        and value['scientific_configuration_identity'].startswith(selected['candidate_id'].rsplit('-',1)[-1])
        for value in binding_summary.values())
    selection_review=dict(run_id=run_id,
        model_selection=dict(actual_optimizer_candidate_id=selected['candidate_id'],
            model_build_candidate_label=build['selection']['candidate_id'],selected_parameters=selected_parameters,
            exact_parameters_match=exact_parameters_match,model_build_reason=build['selection']['reason'],
            rationale_supported=primary_tied and lower_secondary,
            rationale_evidence=dict(primary_ratio=selected['objective']['position_residual_upper_bound_ratio'],
                candidate_residual_m=selected['objective']['candidate_residual_m'],
                selected_secondary_energy=selected['objective']['feasible_witness_normalized_input_energy'],
                alternate_candidate_id=other['candidate_id'],
                alternate_secondary_energy=other['objective']['feasible_witness_normalized_input_energy'],
                matrix_evidence=selected['objective']['matrix_evidence'],
                objective_id=optimizer['objective']['objective_id'],
                applicability=selected['objective']['applicability'],limitations=optimizer['limitations'])),
        citation_review=dict(optimizer_artifact=optimizer_ref,optimizer_artifact_cited_accurately=True,
            exact_parameters_cited_accurately=exact_parameters_match,primary_and_secondary_cited_accurately=primary_tied and lower_secondary,
            scope_and_limitations_cited_accurately=True,
            cited_candidate_bound_artifacts=cited_refs,candidate_bound_bindings=binding_summary,
            cited_candidate_bound_artifacts_exist=True,candidate_bound_artifacts_consistent=candidate_bound_consistent,
            actual_optimizer_candidate_id=selected['candidate_id'],attempted_report_candidate_id=attempted_id,
            optimizer_candidate_id_cited_accurately=attempted_id==selected['candidate_id'],
            finding=('The model chose and built the exact returned compliant configuration, but renamed the proposal '
                'when binding the report; the build label is not the optimizer candidate_id.')),
        automatic_report_linkage=dict(completed=False,node_id=failed_report['node_id'],status=failed_report['status'],
            receipt=report_receipt,route_rejection=report_receipt['error'],
            correction_received=False,following_provider_request_error='DEEPSEEK_NETWORK_ERROR'),
        backend_spending_decision=dict(model_recommended_one_backend_validation=True,
            decision_text=failed_report['selection']['next_step'],backend_attempted=False),
        acceptance_a_math_influenced_executed_design=False)
    if not exact_parameters_match or not primary_tied or not lower_secondary or not candidate_bound_consistent:
        raise RuntimeError('LIVE_SELECTION_REVIEW_MISMATCH')

    turns=[]
    for item in audit['actions']:
        provider=item['receipt'];decision=item['decision'];row=dict(request_id=item['request_id'],provider_receipt=provider,
            decision=decision)
        tool_request=decision.get('request_id') if isinstance(decision,dict) else None
        if tool_request:
            call=store.lookup(run_id,tool_request)
            row['tool_receipt']=None if call is None else json.loads(call['receipt'])
        turns.append(row)
    route_nodes=[dict(node_id=node['node_id'],action=node['action'],status=node['status'],result=node.get('result'),
        selection=node.get('selection')) for node in route['nodes']]
    outcomes=dict(run_id=run_id,valid_backend_execution=dict(status='unavailable',backend_executions=0),
        official_reach=dict(status='unavailable',reason='No backend execution occurred.'),
        sampled_settling_0p05_s=dict(status='unavailable',reason='No trajectory or official evaluation exists.'),
        complete_update_real_time=dict(status='unavailable',reason='No control profile report exists.'),
        interpretation='The run stopped in report linkage/provider transport; this is not a robot-performance failure.')
    raw_files=[]
    for path in sorted(source.iterdir()):
        if path.is_file(): raw_files.append(dict(path=str(path.resolve()),size=path.stat().st_size,sha256=sha256(path)))
    local=dict(remotely_available=False,
        note='Hashes identify the untouched local raw store and supporting files; they do not make those raw files remotely available.',
        files=raw_files)

    for name,value in (('actual_live_freeze_verification',freeze_verification),
            ('actual_live_behavior_audit',audit),('actual_live_math_influence_audit',math),
            ('actual_live_workflow',workflow),('actual_live_optimizer',{key:optimizer[key]
                for key in ('objective','proposals','provenance','limitations')}),
            ('actual_live_provider_turn_extract',dict(run_id=run_id,turns=turns)),
            ('actual_live_route_nodes',dict(run_id=run_id,nodes=route_nodes)),
            ('actual_live_selection_review',selection_review),('actual_live_outcomes',outcomes),
            ('actual_live_local_only_artifacts',local)):
        atomic_json(destination/(name+'.json'),value)
    files=sorted(path for path in destination.glob('actual_live_*.json') if path.name!='actual_live_manifest.json')
    manifest=dict(run_id=run_id,status=audit['status'],stop_reason=audit['stop_reason'],
        implementation_commit=freeze['implementation_commit'],single_live_launch=True,no_retry=True,
        files={path.name:dict(size=path.stat().st_size,sha256=sha256(path)) for path in files},
        usage=dict(provider_requests=audit['real_model_requests'],tool_calls=audit['tool_calls'],
            math_evaluations=dict(offline=freeze['offline_math_evaluations'],live=math['math_ledger']['used'],
                total=freeze['offline_math_evaluations']+math['math_ledger']['used']),
            backend_attempts=audit['backend_executions'],workers=math['usage']['worker_calls'],
            charged_wall_s=math['usage']['wall_s']),
        automatic_report_linkage=False,qualifying_math_led_execution=False,
        original_blocked_launch_record=dict(path='live_blocker.json',preserved=True,
            sha256=sha256(destination/'live_blocker.json')))
    atomic_json(destination/'actual_live_manifest.json',manifest)
    print('Packaged actual live result: '+str(destination),flush=True)


def live_guidance():
    return (
        'Conduct the one bounded Stage 3.35 math-led retry on the frozen reach task. The mathematical tools are local proxies: they use a controller-start frozen local affine exact-ZOH position model, not the nonlinear backend. The primary objective is the official-tolerance-normalized position residual upper bound; normalized input energy of a position-feasible witness is secondary. Terminal braking and other sampled configurations are not objective terms. The prior evidence found a zero world-x position-control mapping row at the straight start, equal primary residuals across compliant/stiff scenarios and tested section scales, and length-dominated primary values. This can favor geometric alignment; it does not predict nonlinear bending, closed-loop reach, settling, real-time performance, causality or global optimality. Screening is advisory. '
        'Build the unchanged baseline only as a solve-free analysis seed and never execute it. Invoke the candidate-bound shared analysis and design.screen. Invoke design.optimize_math once with exactly near [0.15,0.17] m, far [0.11,0.13] m, common section scale [0.95,1.05], compliant and stiff scenarios, the configured protocol and target, and at most 16 cumulative evaluations. Read the structured result, select one exact returned proposal yourself, and cite its candidate_id, objective, applicability, matrix evidence and limitations. Do not replay any excluded historical evaluated configuration. '
        'Build the selected exact near/far/scale/material values as a changed candidate. Analyze and screen that changed build. Call route.record_analysis with the ORIGINAL optimizer result, selected_optimizer_candidate_id, candidate-bound evidence, and both the changed build result and optimizer result in arguments.evidence. Do not rerun optimization at the selected build. Decide yourself whether the advisory evidence justifies a backend attempt. The first executed candidate must pass the Route gate. '
        'Call exactly one tool per response and wait for its receipt. At most three backend attempts include failures/retries; stop physical search after a qualifying changed reach pass. After each execution read the actual official evaluation and control.profile_report. Report official reach, sampled 0.05 s settling, and complete-update real-time feasibility separately and honestly; never replace unavailable measurements with estimates. On finish copy candidate_facts into design_statement and factual_result into result_statement exactly. Use English and retain exact candidate/evidence identities.')


def prepare(root):
    runtime=require_softagent_runtime()
    if (root/'workflow.json').is_file(): return Host(root,read(root/'workflow.json')['run_id'])
    dirty=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)
    if dirty: raise RuntimeError('LIVE_FREEZE_REQUIRES_CLEAN_WORKTREE: commit the reviewed code/evidence first')
    root.mkdir(parents=True,exist_ok=False)
    inp=deepcopy(read(SOURCE/'resolved_frozen_input.json'));run_id='gvs-stage335-'+os.urandom(6).hex();inp['run_id']=run_id
    budget=dict(model_calls=24,tool_calls=160,backend_solves=3,worker_calls=0,wall_s=7200.)
    inp['policy'].update(budget=budget,timeout_s=1800.,allowed_tools=[],tool_bindings=VERSIONS)
    inp['policy']['model']['max_turns']=24
    store=Store(root);store.create(dict(project_id=run_id,grant_id=run_id,
        authorization_source='User-authorized single Stage 3.35 live DeepSeek math-led retry.',budget=budget))
    protocol,target=protocol_and_target(inp)
    with store.transaction() as db: pref=plain(store.put(db,protocol));tref=plain(store.put(db,target))
    from extensions.tendon_family.historical_failure import bind_sources
    sources=historical_sources();prior=bind_sources(sources,inp,store)
    with store.transaction() as db: href=plain(store.put(db,prior))
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    guidance=live_guidance()
    inp['policy']['route']['data'].update(source='Stage 3.35 frozen single retry; implementation commit '+commit,
        historical_case=href,max_trials=3,analysis_protocol=pref,endpoint_target=tref,
        analysis_required_before_run=True,math_evaluation_limit=16,math_selection_required_before_run=True,
        stop_on_task_success=True,guidance=guidance)
    create(root,inp);host=Host(root,run_id)
    payload=payload_for(host,DeepSeekAdapter())
    for name,value in (('frozen_input',inp),('analysis_protocol',plain(protocol)),('endpoint_target',plain(target)),
            ('historical_sources',sources),('historical_case',dict(reference=href,bindings=prior['cases'])),
            ('runtime_identity',runtime),('experiment_prompt',dict(guidance=guidance)),
            ('provider_tools',payload['tools']),('provider_configuration',inp['policy']['model'])):
        atomic_json(root/(name+'.json'),value)
    frozen_files=['frozen_input.json','analysis_protocol.json','endpoint_target.json','historical_sources.json',
        'historical_case.json','runtime_identity.json','experiment_prompt.json','provider_tools.json','provider_configuration.json']
    freeze=dict(run_id=run_id,implementation_commit=commit,implementation_dirty=False,input_identity=digest(inp),
        protocol=pref,target=tref,historical_case=href,limits=budget,offline_math_evaluations=8,
        live_math_evaluation_limit=16,total_offline_plus_live_limit=24,
        provider_configuration=inp['policy']['model'],files={name:sha256(root/name) for name in frozen_files},
        status='prepared')
    atomic_json(root/'freeze_manifest.json',freeze);atomic_json(root/'workflow.json',freeze)
    print('Prepared '+run_id+' at '+commit+'; no provider/backend calls.',flush=True)
    return host


def math_audit(host):
    route=host.store.session(host.run_id)['state']['route'];nodes=route['nodes'];reports=[];executions=[]
    for node in nodes:
        if node.get('status')!='completed' or not node.get('result'): continue
        out=host.store.artifact(node['result'])
        if node['action']=='analyze': reports.append(dict(node_id=node['node_id'],source_node=out['source_node'],
            screen=out['screen'],math_optimization=out.get('math_optimization'),selection_trace=out.get('math_selection_trace')))
        if node['action']=='run':
            build=next(item for item in nodes if item['node_id']==node['selection']['source_node'])
            linked=next((row for row in reports if row['source_node']==build['node_id'] and
                row['selection_trace']['matches_proposal']),None)
            executions.append(dict(node_id=node['node_id'],build_node=build['node_id'],candidate_id=out['candidate_id'],
                configuration=out['build_configuration'],math_report=linked,factual_result=out.get('factual_result'),
                evaluation=out['evaluation'],profile_report=out.get('profile_report')))
    ledger=route.get('math_evaluations',{});used=host.store.remaining()['used'];final=route.get('final')
    audit=dict(run_id=host.run_id,math_ledger={k:v for k,v in ledger.items() if k!='cache'},reports=reports,
        executions=executions,qualifying_math_led_execution=any(row['math_report'] is not None for row in executions),
        provider_authored_finish=bool(final and final.get('explicit_delivery')),final_candidate_id=None if not final else final.get('candidate_id'),
        usage=used,within_limits=used['model_calls']<=24 and used['tool_calls']<=160 and used['backend_solves']<=3
            and used['worker_calls']==0 and used['wall_s']<=7200 and ledger.get('used',0)<=16)
    atomic_json(host.store.root/'math_influence_audit.json',audit);return audit


def inspect(host):
    standard=standard_inspect(host);audit=math_audit(host);workflow=read(host.store.root/'workflow.json')
    workflow['status']=standard['status'];workflow['final_audit']=audit;atomic_json(host.store.root/'workflow.json',workflow)
    print(json.dumps(dict(math_led=audit['qualifying_math_led_execution'],usage=audit['usage'],
        math_evaluations=audit['math_ledger'].get('used'),final_candidate=audit['final_candidate_id']),indent=2),flush=True)
    return standard,audit


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['offline','offline-recover','package-offline','package-blocked-live','package-live-result','prepare','run','inspect'])
    parser.add_argument('--output',type=Path,default=Path('runs')/('stage335_math_route_retry_'+datetime.now().strftime('%Y%m%d_%H%M%S')))
    parser.add_argument('--source',type=Path)
    parser.add_argument('--credential-file',type=Path,default=Path.home()/'.codex/.env');args=parser.parse_args()
    root=args.output.resolve()
    if args.action=='offline': offline(root);return
    if args.action=='offline-recover': recover_offline(root);return
    if args.action=='package-offline':
        if args.source is None: raise ValueError('--source is required for package-offline')
        package_offline(args.source.resolve(),root);return
    if args.action=='package-blocked-live':
        if args.source is None: raise ValueError('--source is required for package-blocked-live')
        package_blocked_live(args.source.resolve(),root);return
    if args.action=='package-live-result':
        if args.source is None: raise ValueError('--source is required for package-live-result')
        package_live_result(args.source.resolve(),root);return
    host=prepare(root) if args.action in ('prepare','run') else Host(root,read(root/'workflow.json')['run_id'])
    require_softagent_runtime()
    if args.action=='run':
        load_credential(args.credential_file);print('Starting the single bounded Stage 3.35 DeepSeek retry.',flush=True)
        host.run();inspect(host)
    elif args.action=='inspect': inspect(host)


if __name__=='__main__': main()
