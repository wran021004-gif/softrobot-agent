"""Freeze, verify, run, audit, and package one bounded Stage 3.37 design experiment."""
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
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'

from examples.gvs_nmpc_route_experiment import inspect as standard_inspect,load_credential
from examples.gvs_stage334 import historical_sources
from extensions.tendon_family.historical_failure import bind_failure,bind_sources
from extensions.tendon_family.route import check_run_eligibility,create
from schemas.platform import ModelResponse
from schemas.platform_analysis import EndpointTarget,TaskAnalysisProtocol
from tools.platform_host import Host
from tools.platform_models import (READABLE_TOOL_NAMING,ReadableDeepSeekAdapter,payload_for,
    provider_name_map,tool_naming_policy)
from tools.platform_store import Store,plain
from tools.runtime_identity import require_softagent_runtime
from tools.state_io import atomic_json,digest,read


SOURCE=ROOT/'runs/stage333_bounded_recovery_independent_lengths_20260929_114923/resolved_frozen_input.json'
CURRENT_ROOT=ROOT/'runs/stage336_manual_20261001_090616'
CURRENT_RUN='gvs-stage336-b3097f85c72a'
CURRENT_OWNER='gvs-stage336-b3097f85c72a-fc9e6c1d6d1f4c7a'
CURRENT_EXECUTION='494deb38d6374deb8f741e96f2430826'
CURRENT_CONFIGURATION='803e8fb2cda1fa2035f18c2051cb2cb83c4dabf26b13f9391c2a49e1cc1b4f5c'
DIAGNOSTIC_ROOT=ROOT/'runs/stage337_bounded_nmpc_diagnostics_20261001'
ENTRYPOINT=Path(__file__).resolve()
VARIABLES={'components/near/length_m':(.15,.17),'components/far/length_m':(.11,.13),
    'design/section_scale':(.95,1.05)}
TOOLS={'route.advance':'1.0.0','route.inspect':'1.0.0','route.record_analysis':'1.0.0',
    'design.build_proposal':'1.0.0','analysis.linearize_candidate':'1.0.0',
    'analysis.control_metrics':'2.0.0','analysis.bounded_endpoint':'1.0.0',
    'design.screen':'1.0.0','design.optimize_math':'1.0.0',
    'analysis.compare_candidates':'1.0.0','analysis.gvs_candidate_evaluate':'1.0.0',
    'control.profile_describe':'1.0.0','control.profile_report':'1.0.0',
    'diagnostics.saved_trajectory':'2.0.0','evaluation.run':'1.0.0','evidence.read':'1.0.0',
    'session.control':'1.0.0','simulation.run':'1.0.0'}


def sha256(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def protocol_and_target(inp):
    task=inp['task'];control=inp['policy']['controller']['parameters']['data']
    lengths={row['id']:row['length_m'] for row in inp['robot']['structure']['data']['components'] if 'length_m' in row}
    return (TaskAnalysisProtocol(baseline_lengths_m=lengths,duration_s=task['timing']['duration_s'],
        period_s=task['timing']['control_period_s'],frequency_rad_s=[.1,1.,10.,100.,1000.],samples_s=[]),
        EndpointTarget(position_m=tuple(task['goal']['data']['target_m']),
            position_tolerance_m=task['evaluator']['parameters']['data']['tolerance_m'],position_scale_m=.01,
            tip_speed_limit_m_s=control['settling']['speed_limit_m_s'],
            tip_velocity_scale_m_s=control['settling']['speed_limit_m_s']))


def diagnostic_evidence():
    rows=[]
    for name in ('current_failed_t0p00','current_failed_t0p23','historical_passing_t0p23'):
        value=read(DIAGNOSTIC_ROOT/(name+'.json'))
        points=[]
        for point in value['retained_points']:
            points.append({key:point[key] for key in ('label','roles','iteration','elapsed_s','objective',
                'scaled_violation','feasible_at_1e_5','first_tension_command_n','named_residuals','objective_components')})
        d=value['solver_diagnostics']
        rows.append(dict(label=value['label'],classification=value['classification'],
            reconstruction_limit=value['reconstruction_limit'],source=value['source'],
            result={key:value['result'][key] for key in ('status','objective_value','constraint_violation','iterations')},
            retained_points=points,iteration_trace=value['iteration_trace'],timing_s=value['timing_s'],
            solver=dict(return_status=d['return_status'],iterations=d['iterations'],policy_stop_reason=d['policy_stop_reason'],
                policy_stop_s=d['policy_stop_s'],returned_iterate_objective=d['returned_iterate_objective'],
                returned_iterate_constraint_violation=d['returned_iterate_constraint_violation'],
                function_statistics=d['function_statistics'])))
    return dict(kind='bounded_reconstructed_local_nmpc_diagnostics',cases=rows,
        findings=[
            'All three initial reconstructed plans were dynamically consistent and feasible at 1e-5; initial-state and variable-bound residuals were zero.',
            'Every solve substantially lowered objective only on iterates whose dynamics equalities remained above 1e-5; variable bounds and initial-state consistency did not prevent delivery.',
            'The current 0.23 s least-infeasible noninitialization checkpoint had scaled dynamics residual 0.0003215983575130185, still over 32 times the delivery threshold.',
            'The reconstructed historical 0.23 s solve did not reproduce the saved historical iteration-19 plan because the historical warm horizon was not retained; this is an applicability limit, not contrary execution evidence.',
            'Exact Jacobian work dominated numerical time; all cases stopped through the unchanged approximately 15 s budget_best_feasible policy with User_Requested_Stop.'
        ],control_decision=dict(outcome='B',controller_changed=False,paired_verification_solves=0,
            reason='No execution-invalidating defect or isolated policy lever is established. Keep controller.gvs_nmpc@6.0.0 unchanged and retain the warm-start/finite-budget applicability limitation.'),
        scope='Three reconstructed single updates only; no backend rollout, causal attribution, global infeasibility, or claim of bitwise historical reproduction.',
        usage=dict(local_nmpc_solves=3,retries=0,provider_requests=0,backend_rollouts=0,workers=0))


def bind_current_case(inp,destination,diagnostic_ref):
    audit=read(CURRENT_ROOT/'stage336_audit.json');source=Store(CURRENT_ROOT)
    report=audit['execution']['profile_report'];configuration=dict(
        artifact_id=CURRENT_CONFIGURATION,media_type='application/json')
    index=dict(live_session=CURRENT_RUN,
        configuration=configuration,candidate_id='proposal-build',profile_report=report,
        evaluation=audit['execution']['evaluation'])
    case=bind_failure(CURRENT_ROOT,inp,index,source,allow_success=False)
    detail=dict(source_session_id=CURRENT_RUN,owner_run_id=CURRENT_OWNER,source_directory=str(CURRENT_ROOT),
        configuration=source.artifact(configuration),
        report=source.artifact(report['reference']),evaluation=source.artifact(audit['execution']['evaluation']),
        diagnostic_evidence=diagnostic_ref,source_bindings=index)
    with destination.transaction() as db:case['detail_export']=plain(destination.put(db,detail))
    case['motion_summary']=audit['execution']['profile_report_summary']['motion_summary']
    return case


def guidance(diagnostic_ref):
    return (
        'Conduct one fresh, bounded, genuinely model-led multi-parameter design experiment on the frozen free-reach task. '
        'You choose the actual near length in [0.15,0.17] m, far length in [0.11,0.13] m, common section scale in [0.95,1.05], '
        'and compliant or stiff numerical material scenario; no candidate values have been selected for you. Preserve every other input. '
        'A covered design changes at least one length by 0.001 m from the 0.16/0.12 m baseline, section scale by at least 0.01 from 1.0, '
        'and uses a nonbaseline material scenario. Do not execute the unchanged baseline or any configuration in supplied historical cases. '
        f'Before selecting, read compact reconstructed NMPC evidence {diagnostic_ref["artifact_id"]} with evidence.read and use the compact prior-case context. '
        'The diagnostics show objective improvement on infeasible iterates with dynamics equalities, not initial-state or bound violations; '
        'they support no controller change and do not prove intrinsic design infeasibility. The historical 0.23 s diagnostic is reconstructed '
        'without its unsaved warm horizon and is not a bitwise replay. Distinguish accepted initialization from useful optimizer progress. '
        'Use the available local mathematical tools as advisory screening. Their controller-start affine endpoint witnesses do not predict '
        'nonlinear closed-loop error, settling, real-time performance, or global reachability. When you choose an optimizer proposal, construct '
        'it through design.build_proposal so exact values and provenance are automatic; attach candidate-bound analysis before any run. '
        'Decide yourself whether each backend attempt is warranted, read official evaluation and control-profile facts after execution, and revise '
        'from actual evidence while a complete evaluation and delivery remain affordable. Stop immediately after a qualifying fresh reach pass. '
        'At most 24 provider attempts, 60 charged tool calls, 3 backend attempts, 16 new mathematical design evaluations, zero workers, and 3600 charged seconds. '
        'Reserve resources for evaluation/report reading and a normal provider-authored finish. A failed solver-limited pipeline result is not proof '
        'of design infeasibility. The ideal-tension execution bypasses actuator travel/speed and tendon-length servo dynamics. Report endpoint reach, '
        'sampled settling, and complete-update timing separately, and copy exact candidate_facts and factual_result through the normal finish path.')


def configure(root,run_id,budget,created_by,*,include_prior=True):
    inp=deepcopy(read(SOURCE));inp['run_id']=run_id
    inp['policy']['budget']=budget;inp['policy']['timeout_s']=1800.;inp['policy']['allowed_tools']=[]
    inp['policy']['tool_bindings']=dict(TOOLS);inp['policy']['model']['max_turns']=24
    inp['policy']['model']['adapter_version']='2.0.0'
    inp['policy']['model']['tool_naming']=tool_naming_policy(TOOLS,READABLE_TOOL_NAMING)
    store=Store(root);store.create(dict(project_id=run_id,grant_id=run_id,authorization_source=created_by,budget=budget))
    protocol,target=protocol_and_target(inp)
    diagnostic=diagnostic_evidence()
    with store.transaction() as db:
        pref=plain(store.put(db,protocol));tref=plain(store.put(db,target));dref=plain(store.put(db,diagnostic))
    prior=None;href=None
    if include_prior:
        prior=bind_sources(historical_sources(),inp,store)
        prior['cases'].append(bind_current_case(inp,store,dref))
        with store.transaction() as db:href=plain(store.put(db,prior))
    inp['policy']['route']['data'].update(source=created_by,historical_case=href,max_trials=3,
        analysis_protocol=pref,endpoint_target=tref,analysis_required_before_run=True,
        math_evaluation_limit=16,math_selection_required_before_run=True,stop_on_task_success=True,
        guidance=guidance(dref))
    create(root,inp)
    return Host(root,run_id),protocol,target,diagnostic,dref,prior,href


def fixture_call(host,turn,tool,arguments):
    adapter=ReadableDeepSeekAdapter();payload=payload_for(host,adapter)
    bindings=host.store.session(host.run_id)['snapshot']['input']['policy']['tool_bindings']
    names=provider_name_map(bindings,READABLE_TOOL_NAMING)
    advertised=next(row['function'] for row in payload['tools'] if row['function']['name']==names[tool])
    raw=dict(choices=[dict(index=0,finish_reason='tool_calls',message=dict(role='assistant',content=None,
        tool_calls=[dict(id='fixture-'+str(turn),type='function',function=dict(name=advertised['name'],
            arguments=json.dumps(dict(arguments=arguments,reason='Offline schema/linkage fixture only.',tool_version=bindings[tool]))))]))])
    decoded=adapter.decode(ModelResponse(raw=raw),turn,bindings,payload['tools'])
    return host.invoke(decoded),payload


def offline(root,evidence):
    runtime=require_softagent_runtime();run_id='stage337-offline-'+os.urandom(6).hex()
    budget=dict(model_calls=0,tool_calls=30,backend_solves=0,worker_calls=0,wall_s=3600.)
    host,protocol,target,diagnostic,dref,_,_=configure(root,run_id,budget,'Offline production schema/linkage fixture.',include_prior=False)
    frozen=host.store.session(run_id)['snapshot']['input'];route_policy=frozen['policy']['route']['data']
    pref=route_policy['analysis_protocol'];tref=route_policy['endpoint_target']
    receipts=[];turn=0
    def call(tool,args):
        nonlocal turn
        receipt,payload=fixture_call(host,turn,tool,args);turn+=1;receipts.append(receipt)
        if receipt['execution_status']!='completed':raise RuntimeError(json.dumps(receipt,indent=2))
        return receipt['output'],host.store.artifact(receipt['output']),payload
    seed_ref,seed,_=call('route.advance',dict(node_id='fixture-seed',action='build',combination='candidate_gvs_nmpc',
        changes={},variables={},max_trials=1,source_node=None,candidate_id='fixture-seed',evidence=[],
        reason='Fixture-only unchanged mathematical seed.',next_step='Exercise mathematical proposal linkage.',
        design_statement=None,result_statement=None))
    optimized_ref,optimized,_=call('design.optimize_math',dict(source_node='fixture-seed',
        protocol=pref,target=tref,variables=VARIABLES,material_scenarios=['compliant','stiff'],
        max_evaluations=2,objective='controller_start_local_endpoint_lexicographic_v1'))
    proposal=optimized['proposals'][0]
    build_ref,build,payload=call('design.build_proposal',dict(node_id='fixture-proposal',optimizer_result=optimized_ref,
        optimizer_candidate_id=proposal['candidate_id'],reason='Exercise automatic proposal binding only.',
        next_step='Exercise candidate-bound analysis linkage.'))
    build_result=build['detail']['result']
    linear,_,_=call('analysis.linearize_candidate',dict(source_node='fixture-proposal',protocol=pref))
    metrics,_,_=call('analysis.control_metrics',dict(models=[linear],protocol=pref,implementation='scipy'))
    endpoint,_,_=call('analysis.bounded_endpoint',dict(models=[linear],protocol=pref,target=tref))
    screen,_,_=call('design.screen',dict(source_node='fixture-proposal',protocol=pref,linearization=linear,
        metrics=metrics,endpoint=endpoint))
    report_ref,report,_=call('route.record_analysis',dict(node_id='fixture-report',source_node='fixture-proposal',
        evidence=[build_result,optimized_ref],linearization=linear,metrics=metrics,endpoint=endpoint,screen=screen,
        math_optimization=optimized_ref,selected_optimizer_candidate_id=proposal['candidate_id'],
        validation_disposition='recommended',reason='Fixture confirms exact proposal linkage; no live choice is implied.',
        next_step='Check the run gate without executing.'))
    report_value=host.store.artifact(host.store.artifact(report_ref)['detail']['result'])
    gate=check_run_eligibility(host,'fixture-proposal')
    advertised={row['function']['name'] for row in payload['tools']}
    result=dict(status='passed',runtime=runtime,scripted_fixture_not_live_model_choice=True,
        diagnostic_reference=dref,public_schemas_present=all(provider_name_map(TOOLS,READABLE_TOOL_NAMING)[name] in advertised for name in
            ('design.optimize_math','design.build_proposal','route.record_analysis','route.advance')),
        automatic_proposal_binding=report_value['math_selection_trace']['matches_proposal'],
        optimizer_candidate_id=proposal['candidate_id'],gate=gate,usage=host.store.remaining(host.run_id)['used'],
        limits=dict(provider_requests=0,backend_attempts=0,workers=0,mathematical_evaluations=2))
    if not all((result['public_schemas_present'],result['automatic_proposal_binding'],gate['eligible'])):
        raise RuntimeError(json.dumps(result,indent=2))
    evidence.mkdir(parents=True,exist_ok=True);atomic_json(evidence/'offline_linkage_fixture.json',result)
    atomic_json(root/'offline_linkage_fixture.json',result)
    print(json.dumps(result,indent=2),flush=True)


def executable_identity(host):
    snapshot=host.store.session(host.run_id)['snapshot']
    return dict(session_dependencies_sha256=digest(snapshot['dependencies']),dependency_count=len(snapshot['dependencies']),
        entrypoint=str(ENTRYPOINT.relative_to(ROOT)),entrypoint_sha256=sha256(ENTRYPOINT))


def prepare(root):
    runtime=require_softagent_runtime()
    if (root/'workflow.json').is_file():return Host(root,read(root/'workflow.json')['run_id'])
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True):
        raise RuntimeError('LIVE_FREEZE_REQUIRES_CLEAN_WORKTREE')
    run_id='gvs-stage337-'+os.urandom(6).hex();budget=dict(model_calls=24,tool_calls=60,backend_solves=3,worker_calls=0,wall_s=3600.)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    host,protocol,target,diagnostic,dref,prior,href=configure(root,run_id,budget,
        'User-authorized one fresh Stage 3.37 bounded autonomous DeepSeek multi-parameter design experiment at '+commit+'.')
    inp=host.store.session(run_id)['snapshot']['input'];payload=payload_for(host,ReadableDeepSeekAdapter())
    values=dict(frozen_input=inp,analysis_protocol=plain(protocol),endpoint_target=plain(target),
        diagnostic_evidence=diagnostic,historical_case=dict(reference=href,content=prior),runtime_identity=runtime,
        experiment_prompt=dict(guidance=inp['policy']['route']['data']['guidance']),provider_tools=payload['tools'],
        actual_provider_payload=payload,provider_configuration=inp['policy']['model'],project_configuration=host.store.config())
    for name,value in values.items():atomic_json(root/(name+'.json'),value)
    names=[name+'.json' for name in values];snapshot=host.store.session(run_id)['snapshot']
    freeze=dict(run_id=run_id,stage='Stage 3.37 bounded autonomous multi-parameter design',
        implementation_commit=commit,implementation_dirty=False,limits=budget,provider_request_limit=24,
        new_math_limit=16,backend_attempt_limit=3,workers_limit=0,diagnostic_evidence=dref,
        session_input_identity=snapshot['input_identity'],project_configuration_identity=digest(host.store.config()),
        executable_identity=executable_identity(host),provider_configuration=inp['policy']['model'],
        files={name:sha256(root/name) for name in names},status='prepared')
    atomic_json(root/'freeze_manifest.json',freeze);atomic_json(root/'workflow.json',freeze)
    standard_inspect(host)
    print('Prepared '+run_id+' at '+commit+'; no provider/backend/math calls in the live session.',flush=True)
    return host


def verify_prelaunch(root,host):
    runtime=require_softagent_runtime();freeze=read(root/'freeze_manifest.json');failures=[];actual={}
    for name,expected in freeze['files'].items():
        actual[name]=sha256(root/name) if (root/name).is_file() else None
        if actual[name]!=expected:failures.append('frozen_file:'+name)
    snapshot=host.store.session(host.run_id)['snapshot'];payload=payload_for(host,ReadableDeepSeekAdapter())
    checks=dict(run_id=freeze['run_id']==host.run_id,runtime=runtime==read(root/'runtime_identity.json'),
        session_input=snapshot['input']==read(root/'frozen_input.json'),
        session_input_identity=snapshot['input_identity']==digest(snapshot['input'])==freeze['session_input_identity'],
        project_configuration=host.store.config()==read(root/'project_configuration.json'),
        executable_identity=executable_identity(host)==freeze['executable_identity'],
        compatibility=host.compatibility()['compatible'],provider_payload=payload==read(root/'actual_provider_payload.json'),
        frozen_files=not failures)
    failures.extend(name for name,value in checks.items() if not value)
    result=dict(kind='stage337_prelaunch_verification',checked_at=datetime.now().astimezone().isoformat(),
        checked_before_credentials=True,checked_before_provider=True,checked_before_backend=True,
        status='passed' if not failures else 'rejected',checks=checks,failures=failures,
        frozen_file_hashes={name:dict(expected=freeze['files'][name],actual=value,
            matches=value==freeze['files'][name]) for name,value in actual.items()})
    atomic_json(root/'prelaunch_verification.json',result)
    if failures:raise RuntimeError('LIVE_PRELAUNCH_VERIFICATION_FAILED: '+','.join(failures))
    return result


def audit(host):
    standard=standard_inspect(host);session=host.store.session(host.run_id);route=session['state']['route'];nodes=[];runs=[]
    for node in route['nodes']:
        item={key:node[key] for key in ('node_id','action','status','result','error','selection') if key in node};nodes.append(item)
        if node.get('action')=='run' and node.get('status')=='completed' and node.get('result'):
            value=host.store.artifact(node['result']);facts=value.get('factual_result')
            if facts is None:
                from extensions.tendon_family.route import trial_facts
                from extensions.tendon_family.delivery_facts import bound_result_facts
                candidate=trial_facts(host.store,session['snapshot']['input'],value);facts=bound_result_facts(host.store,value,candidate)
            runs.append(dict(node_id=node['node_id'],result=node['result'],candidate_id=value['candidate_id'],
                candidate_facts=value.get('candidate_facts'),factual_result=facts,
                profile_report=value.get('profile_report'),profile_report_summary=value.get('profile_report_summary')))
    usage=host.store.remaining(host.run_id)['used'];ledger=route.get('math_evaluations',{})
    result=dict(run_id=host.run_id,status=standard['status'],stop_reason=standard['stop_reason'],route_nodes=nodes,
        evaluated_candidates=runs,final=route.get('final'),usage=usage,math_evaluations_new=ledger.get('used',0),
        within_limits=usage['model_calls']<=24 and usage['tool_calls']<=60 and usage['backend_solves']<=3
            and usage['worker_calls']==0 and usage['wall_s']<=3600 and ledger.get('used',0)<=16)
    atomic_json(host.store.root/'stage337_audit.json',result);workflow=read(host.store.root/'workflow.json')
    workflow.update(status=standard['status'],stop_reason=standard['stop_reason'],actual_usage=usage,
        math_evaluations_new=ledger.get('used',0));atomic_json(host.store.root/'workflow.json',workflow)
    return result


def package(source,destination):
    destination.mkdir(parents=True,exist_ok=True);host=Host(source,read(source/'workflow.json')['run_id'])
    result=audit(host);behavior=read(source/'behavior_audit.json');freeze=read(source/'freeze_manifest.json')
    decisions=[]
    for action in behavior['actions']:
        decision=action.get('decision') or {};arguments=decision.get('arguments',{})
        decisions.append(dict(request_id=action['request_id'],tool_id=decision.get('tool_id'),reason=decision.get('reason'),
            arguments={key:arguments.get(key) for key in ('node_id','action','source_node','candidate_id','optimizer_candidate_id',
                'selected_optimizer_candidate_id','validation_disposition','reason','next_step') if key in arguments},receipt=action.get('receipt')))
    local=[]
    paths=[source/'platform.sqlite',source/'actual_provider_payload.json']
    paths.extend(source.glob('sessions/*/executions/*/backend/trajectory.json.gz'))
    paths.extend(source.glob('sessions/*/executions/*/backend/controller_observations.json'))
    paths.extend(source.glob('sessions/*/executions/*/backend/nmpc_updates.json'))
    for path in paths:
        if path.is_file():local.append(dict(path=str(path.resolve()),size_bytes=path.stat().st_size,sha256=sha256(path)))
    outputs=dict(actual_freeze_manifest=freeze,actual_prelaunch_verification=read(source/'prelaunch_verification.json'),
        actual_workflow=read(source/'workflow.json'),actual_stage337_audit=result,
        actual_model_decisions=dict(run_id=host.run_id,decisions=decisions),
        actual_diagnostic_evidence=read(source/'diagnostic_evidence.json'),
        actual_usage=dict(provider_attempts=behavior['real_model_requests'],tool_calls=behavior['tool_calls'],
            backend_attempts=behavior['backend_executions'],math_evaluations=result['math_evaluations_new'],
            workers=result['usage']['worker_calls'],charged_wall_s=result['usage']['wall_s']),
        actual_local_only_artifacts=dict(remotely_available=False,files=local))
    for name,value in outputs.items():atomic_json(destination/(name+'.json'),value)
    files=[path for path in destination.glob('actual_*.json')]
    atomic_json(destination/'actual_manifest.json',dict(run_id=host.run_id,status=result['status'],
        stop_reason=result['stop_reason'],implementation_commit=freeze['implementation_commit'],
        files={path.name:dict(size_bytes=path.stat().st_size,sha256=sha256(path)) for path in sorted(files)},
        usage=outputs['actual_usage']))
    print(json.dumps(dict(status=result['status'],stop_reason=result['stop_reason'],
        attempts=len(result['evaluated_candidates']),usage=outputs['actual_usage']),indent=2),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['offline','prepare','verify','run','inspect','package'])
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--evidence',type=Path)
    parser.add_argument('--source',type=Path);parser.add_argument('--credential-file',type=Path,default=Path.home()/'.codex/.env')
    args=parser.parse_args();root=args.output.resolve()
    if args.action=='offline':
        if args.evidence is None:raise ValueError('--evidence is required')
        offline(root,args.evidence.resolve());return
    if args.action=='package':
        if args.source is None:raise ValueError('--source is required')
        package(args.source.resolve(),root);return
    host=prepare(root) if args.action in ('prepare','run') else Host(root,read(root/'workflow.json')['run_id'])
    if args.action=='run':
        verify_prelaunch(root,host);load_credential(args.credential_file)
        print('Starting the one Stage 3.37 autonomous DeepSeek experiment.',flush=True);host.run();audit(host)
    elif args.action=='verify':print(json.dumps(verify_prelaunch(root,host),indent=2),flush=True)
    elif args.action=='inspect':print(json.dumps(audit(host),indent=2),flush=True)


if __name__=='__main__':main()
