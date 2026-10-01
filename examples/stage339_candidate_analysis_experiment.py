"""Freeze, run, audit and package one bounded candidate-analysis autonomous experiment."""
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
from examples.stage337_autonomous_design_experiment import (SOURCE,VARIABLES,bind_current_case,
    diagnostic_evidence,protocol_and_target)
from extensions.tendon_family.historical_failure import bind_sources
from extensions.tendon_family.route import create,trial_facts
from extensions.tendon_family.delivery_facts import bound_result_facts
from tools.platform_host import Host
from tools.platform_models import READABLE_TOOL_NAMING,ReadableDeepSeekAdapter,payload_for,tool_naming_policy
from tools.platform_store import Store,plain
from tools.runtime_identity import require_softagent_runtime
from tools.state_io import atomic_json,digest,read


ENTRYPOINT=Path(__file__).resolve()
TOOLS={'route.advance':'1.0.0','route.inspect':'1.0.0','route.record_analysis':'2.0.0',
    'design.build_proposal':'1.0.0','analysis.prepare_candidate':'1.0.0',
    'analysis.linearize_candidate':'1.0.0','analysis.control_metrics':'2.0.0',
    'analysis.bounded_endpoint':'1.0.0','design.screen':'1.0.0','design.optimize_math':'1.0.0',
    'analysis.compare_candidates':'1.0.0','analysis.gvs_candidate_evaluate':'1.0.0',
    'control.profile_describe':'1.0.0','control.profile_report':'1.0.0',
    'diagnostics.saved_trajectory':'2.0.0','evaluation.run':'1.0.0','evidence.read':'1.0.0',
    'session.control':'1.0.0','simulation.run':'1.0.0'}


def sha256(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def guidance(diagnostic_ref):
    return (
        'Conduct one fresh, bounded, genuinely model-led multi-parameter design experiment on the frozen free-reach task. '
        'You choose the near length in [0.15,0.17] m, far length in [0.11,0.13] m, common section scale in [0.95,1.05], '
        'and compliant or stiff numerical material scenario; no candidate values or engineering conclusion have been selected for you. '
        'Preserve every other input. A covered design changes at least one length by 0.001 m from the 0.16/0.12 m baseline, section '
        'scale by at least 0.01 from 1.0, and uses a nonbaseline material scenario. Do not execute the unchanged baseline or any supplied '
        'historical configuration. An unchanged baseline may be a solve-free mathematical seed only. '
        f'Before selecting, read compact reconstructed NMPC evidence {diagnostic_ref["artifact_id"]} with evidence.read and use the compact '
        'prior-case context. The diagnostics support no controller change and do not prove intrinsic design infeasibility. '
        'Choose a completed starting build when needed, invoke design.optimize_math within the declared bounds, inspect its proposals, and '
        'construct one exact selected proposal through design.build_proposal. For that proposal build call analysis.prepare_candidate exactly '
        'once; it deterministically completes or reuses the linearization, metrics, endpoint analysis and screen under the frozen protocol. '
        'Do not repeat the individual analysis chain merely to recover references. Register the returned bundle with route.record_analysis@2.0.0, '
        'cite the source build result, and rely on inherited optimizer provenance. Decide whether backend validation is warranted, execute only '
        'through route.advance, and read official evaluation and control-profile results. Revise within the remaining budget or finish honestly. '
        'The local screen is advisory: a residual above tolerance or degenerate straight-start world-x map is not by itself a global infeasibility '
        'claim or reason to skip all physical validation. Stop further physical search after a qualifying fresh reach pass. A scientifically valid '
        'failed reach may also be delivered. Workflow completion, reach success, sampled settling and real-time performance are separate outcomes. '
        'At most 24 provider attempts, 60 charged tool calls, 16 new mathematical design evaluations, 3 backend attempts, zero workers and 3600 '
        'charged seconds. Reserve evaluation, profile reading and a normal model-authored finish. Copy exact candidate_facts and factual_result '
        'through route.advance action=finish. Ideal-tension execution omits actuator travel/speed and tendon-length servo dynamics.')


def configure(root,run_id,budget,created_by):
    inp=deepcopy(read(SOURCE));inp['run_id']=run_id
    inp['policy']['budget']=budget;inp['policy']['timeout_s']=1800.;inp['policy']['allowed_tools']=[]
    inp['policy']['tool_bindings']=dict(TOOLS);inp['policy']['model']['max_turns']=24
    inp['policy']['model']['adapter_version']='2.0.0'
    inp['policy']['model']['tool_naming']=tool_naming_policy(TOOLS,READABLE_TOOL_NAMING)
    store=Store(root);store.create(dict(project_id=run_id,grant_id=run_id,authorization_source=created_by,budget=budget))
    protocol,target=protocol_and_target(inp);diagnostic=diagnostic_evidence()
    with store.transaction() as db:
        pref=plain(store.put(db,protocol));tref=plain(store.put(db,target));dref=plain(store.put(db,diagnostic))
    prior=bind_sources(historical_sources(),inp,store);prior['cases'].append(bind_current_case(inp,store,dref))
    with store.transaction() as db:href=plain(store.put(db,prior))
    inp['policy']['route']['data'].update(source=created_by,historical_case=href,historical_math=None,max_trials=3,
        analysis_protocol=pref,endpoint_target=tref,analysis_required_before_run=True,math_evaluation_limit=16,
        math_selection_required_before_run=True,stop_on_task_success=True,guidance=guidance(dref))
    create(root,inp)
    return Host(root,run_id),protocol,target,diagnostic,dref,prior,href


def executable_identity(host):
    snapshot=host.store.session(host.run_id)['snapshot']
    return dict(session_dependencies_sha256=digest(snapshot['dependencies']),dependency_count=len(snapshot['dependencies']),
        entrypoint=str(ENTRYPOINT.relative_to(ROOT)),entrypoint_sha256=sha256(ENTRYPOINT))


def prepare(root):
    runtime=require_softagent_runtime()
    if (root/'workflow.json').is_file():return Host(root,read(root/'workflow.json')['run_id'])
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True):
        raise RuntimeError('LIVE_FREEZE_REQUIRES_CLEAN_WORKTREE')
    run_id='gvs-stage339-'+os.urandom(6).hex();budget=dict(model_calls=24,tool_calls=60,backend_solves=3,worker_calls=0,wall_s=3600.)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    host,protocol,target,diagnostic,dref,prior,href=configure(root,run_id,budget,
        'User-authorized Stage 3.39 candidate-analysis autonomous DeepSeek experiment at '+commit+'.')
    inp=host.store.session(run_id)['snapshot']['input'];payload=payload_for(host,ReadableDeepSeekAdapter())
    values=dict(frozen_input=inp,analysis_protocol=plain(protocol),endpoint_target=plain(target),
        diagnostic_evidence=diagnostic,historical_case=dict(reference=href,content=prior),runtime_identity=runtime,
        experiment_prompt=dict(guidance=inp['policy']['route']['data']['guidance']),provider_tools=payload['tools'],
        actual_provider_payload=payload,provider_configuration=inp['policy']['model'],project_configuration=host.store.config())
    for name,value in values.items():atomic_json(root/(name+'.json'),value)
    names=[name+'.json' for name in values];snapshot=host.store.session(run_id)['snapshot']
    freeze=dict(run_id=run_id,stage='Stage 3.39 candidate-specific analysis autonomous design',
        implementation_commit=commit,implementation_dirty=False,limits=budget,provider_request_limit=24,
        new_math_limit=16,backend_attempt_limit=3,workers_limit=0,diagnostic_evidence=dref,
        session_input_identity=snapshot['input_identity'],project_configuration_identity=digest(host.store.config()),
        executable_identity=executable_identity(host),provider_configuration=inp['policy']['model'],
        files={name:sha256(root/name) for name in names},status='prepared')
    atomic_json(root/'freeze_manifest.json',freeze);atomic_json(root/'workflow.json',freeze)
    standard_inspect(host);print('Prepared '+run_id+' at '+commit+'; no provider/backend/math calls in live session.',flush=True)
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
    result=dict(kind='stage339_prelaunch_verification',checked_at=datetime.now().astimezone().isoformat(),
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
        nodes.append({key:node[key] for key in ('node_id','action','status','result','error','selection') if key in node})
        if node.get('action')=='run' and node.get('status')=='completed' and node.get('result'):
            value=host.store.artifact(node['result']);facts=value.get('factual_result')
            if facts is None:
                candidate=trial_facts(host.store,session['snapshot']['input'],value);facts=bound_result_facts(host.store,value,candidate)
            runs.append(dict(node_id=node['node_id'],result=node['result'],candidate_id=value['candidate_id'],
                candidate_facts=value.get('candidate_facts'),factual_result=facts,profile_report=value.get('profile_report'),
                profile_report_summary=value.get('profile_report_summary')))
    usage=host.store.remaining(host.run_id)['used'];ledger=route.get('math_evaluations',{})
    result=dict(run_id=host.run_id,status=standard['status'],stop_reason=standard['stop_reason'],route_nodes=nodes,
        candidate_analysis_status=host.context()['route'].get('candidate_analysis_status',[]),evaluated_candidates=runs,
        final=route.get('final'),usage=usage,math_evaluations_new=ledger.get('used',0),
        within_limits=usage['model_calls']<=24 and usage['tool_calls']<=60 and usage['backend_solves']<=3
            and usage['worker_calls']==0 and usage['wall_s']<=3600 and ledger.get('used',0)<=16)
    atomic_json(host.store.root/'stage339_audit.json',result);workflow=read(host.store.root/'workflow.json')
    workflow.update(status=standard['status'],stop_reason=standard['stop_reason'],actual_usage=usage,
        math_evaluations_new=ledger.get('used',0));atomic_json(host.store.root/'workflow.json',workflow)
    return result


def outcome(audit_value):
    final=audit_value.get('final') or {};evaluated=audit_value.get('evaluated_candidates',[])
    selected=next((row for row in reversed(evaluated) if row.get('candidate_id')==final.get('candidate_id')),None)
    if selected is None and evaluated:selected=evaluated[-1]
    facts=(selected or {}).get('factual_result');profile=(selected or {}).get('profile_report_summary') or {}
    selected_candidate=(selected or {}).get('candidate_id') or final.get('candidate_id')
    analysis=next((row for row in reversed(audit_value.get('candidate_analysis_status',[]))
        if row.get('source_node')==final.get('source_build_node') or row.get('build_candidate_id')==selected_candidate),None)
    return dict(run_id=audit_value['run_id'],status=audit_value['status'],stop_reason=audit_value['stop_reason'],
        model_selected_candidate=None if selected is None else dict(candidate_id=selected['candidate_id'],candidate_facts=selected.get('candidate_facts')),
        candidate_analysis=analysis,backend_execution_and_evaluation_occurred=bool(selected),official_reach=facts,
        sampled_settling=profile.get('sampled_settling'),complete_update_timing=None if not profile else dict(
            deadline_misses=profile.get('deadline_misses'),updates=profile.get('updates'),
            mean_complete_update_s=profile.get('mean_update_s'),real_time_demonstrated=profile.get('real_time_demonstrated')),
        model_authored_finish=dict(completed=bool(final),explicit_delivery=final.get('explicit_delivery'),delivery_status=final.get('delivery_status')),
        usage=audit_value['usage'],math_evaluations_new=audit_value['math_evaluations_new'],within_limits=audit_value['within_limits'])


def package(source,destination):
    destination.mkdir(parents=True,exist_ok=True);host=Host(source,read(source/'workflow.json')['run_id'])
    result=audit(host);behavior=read(source/'behavior_audit.json');freeze=read(source/'freeze_manifest.json');decisions=[]
    for action in behavior['actions']:
        decision=action.get('decision') or {};arguments=decision.get('arguments',{})
        decisions.append(dict(request_id=action['request_id'],tool_id=decision.get('tool_id'),reason=decision.get('reason'),
            arguments={key:arguments.get(key) for key in ('node_id','action','source_node','candidate_id','optimizer_candidate_id',
                'candidate_analysis_bundle','selected_optimizer_candidate_id','validation_disposition','reason','next_step') if key in arguments},
            receipt=action.get('receipt')))
    local=[];paths=[source/'platform.sqlite',source/'actual_provider_payload.json']
    for pattern in ('sessions/*/executions/*/backend/trajectory.json.gz','sessions/*/executions/*/backend/controller_observations.json',
            'sessions/*/executions/*/backend/nmpc_updates.json'):
        paths.extend(source.glob(pattern))
    for path in paths:
        if path.is_file():local.append(dict(path=str(path.resolve()),size_bytes=path.stat().st_size,sha256=sha256(path)))
    outputs=dict(actual_freeze_manifest=freeze,actual_prelaunch_verification=read(source/'prelaunch_verification.json'),
        actual_workflow=read(source/'workflow.json'),actual_stage339_audit=result,
        actual_model_decisions=dict(run_id=host.run_id,decisions=decisions),outcome_summary=outcome(result),
        actual_usage=dict(provider_attempts=behavior['real_model_requests'],tool_calls=behavior['tool_calls'],
            backend_attempts=behavior['backend_executions'],math_evaluations=result['math_evaluations_new'],
            workers=result['usage']['worker_calls'],charged_wall_s=result['usage']['wall_s']),
        actual_local_only_artifacts=dict(remotely_available=False,files=local))
    for name,value in outputs.items():atomic_json(destination/(name+'.json'),value)
    files=sorted(destination.glob('actual_*.json'))+[destination/'outcome_summary.json']
    atomic_json(destination/'actual_manifest.json',dict(run_id=host.run_id,status=result['status'],
        stop_reason=result['stop_reason'],implementation_commit=freeze['implementation_commit'],
        files={path.name:dict(size_bytes=path.stat().st_size,sha256=sha256(path)) for path in files},usage=outputs['actual_usage']))
    print(json.dumps(outputs['outcome_summary'],indent=2),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','verify','run','inspect','package'])
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--source',type=Path)
    parser.add_argument('--credential-file',type=Path,default=Path.home()/'.codex/.env');args=parser.parse_args();root=args.output.resolve()
    if args.action=='package':
        if args.source is None:raise ValueError('--source is required')
        package(args.source.resolve(),root);return
    host=prepare(root) if args.action in ('prepare','run') else Host(root,read(root/'workflow.json')['run_id'])
    if args.action=='run':
        verify_prelaunch(root,host);load_credential(args.credential_file)
        print('Starting the one Stage 3.39 autonomous DeepSeek experiment.',flush=True);host.run();audit(host)
    elif args.action=='verify':print(json.dumps(verify_prelaunch(root,host),indent=2),flush=True)
    elif args.action=='inspect':print(json.dumps(audit(host),indent=2),flush=True)


if __name__=='__main__':main()
