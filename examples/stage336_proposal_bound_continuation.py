"""Offline replay, freeze, one live Stage 3.36 continuation, and compact audit."""
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
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ.setdefault(name,'1')

from examples.gvs_nmpc_route_experiment import inspect as standard_inspect,load_credential
from extensions.tendon_family.candidate_analysis import scientific_configuration
from extensions.tendon_family.route import check_run_eligibility,create
from schemas.platform import ModelResponse
from tools.platform_host import Host
from tools.platform_models import DeepSeekAdapter,payload_for,provider_name
from tools.platform_store import Store,plain
from tools.runtime_identity import require_softagent_runtime
from tools.state_io import atomic_json,digest,read


PARENT_ROOT=ROOT/'runs/stage335_math_route_retry_20260930_live'
FALLBACK_ROOT=ROOT/'runs/stage333_bounded_recovery_independent_lengths_20260929_114923/live'
HISTORICAL_ROOTS=[
    ROOT/'runs/stage331_autonomous_revision_execution_20260929_014645/live',
    ROOT/'runs/stage332_evidence_guided_design_exploration_20260929_090221/live_network',
    FALLBACK_ROOT,
]
PARENT_EVIDENCE=ROOT/'evidence/stage335_math_route_retry_20260930'
PARENT_RUN='gvs-stage335-81350ebec934'
OPTIMIZER={'artifact_id':'9e408e81d706b22246e1d856d122bdcffaa605308ed975cbfa0ade0c563c7245','media_type':'application/json'}
PROPOSAL_ID='math-compliant-4795c8184616'
OLD_BUILD_LABEL='mathsel_c1_n0p15_f0p11_s0p95_compliant'
NAMED={
    'linearization':{'artifact_id':'fecccc31a1f81a66e76ed3484e80cf2ecbf74fd27875bb25ea445460ca370cf5','media_type':'application/json'},
    'metrics':{'artifact_id':'c95db3eb25e6286562329cd8a8ad51419347177391f1a2150635beead37a1e9b','media_type':'application/json'},
    'endpoint':{'artifact_id':'bcae2da3662e176688a48f8b94a93d6abbc7e02b78e076ca2c294d1dc96c8085','media_type':'application/json'},
    'screen':{'artifact_id':'73bef851229f297f586e3c9c42e08eaeb02be61e57e356a6aec531f2b50ba890','media_type':'application/json'},
}
TOOLS={'route.advance':'1.0.0','route.inspect':'1.0.0','route.record_analysis':'1.0.0',
    'design.build_proposal':'1.0.0','analysis.bind_historical_math':'1.0.0',
    'control.profile_describe':'1.0.0','control.profile_report':'1.0.0',
    'evaluation.run':'1.0.0','evidence.read':'1.0.0','session.control':'1.0.0','simulation.run':'1.0.0'}


def sha256(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_stores():return [Store(PARENT_ROOT),*(Store(path) for path in HISTORICAL_ROOTS)]


def import_tree(sources,destination,roots):
    seen={};missing=[]
    def visit(ref,path):
        key=(ref['artifact_id'],ref.get('media_type','application/json'))
        if key in seen:return
        raw=None;source_root=None
        for source in sources:
            try:raw=source.artifact(dict(artifact_id=key[0],media_type=key[1]),raw=True);source_root=str(source.root);break
            except ValueError:pass
        if raw is None:
            missing.append(dict(reference=dict(artifact_id=key[0],media_type=key[1]),path=path));return
        with destination.transaction() as db:saved=destination.put(db,raw,key[1])
        if plain(saved)!=dict(artifact_id=key[0],media_type=key[1]):raise RuntimeError('HISTORICAL_IMPORT_IDENTITY_CHANGED')
        seen[key]=source_root
        if key[1]=='application/json':
            value=json.loads(raw)
            def scan(item,pointer):
                if isinstance(item,dict):
                    if set(item)=={'artifact_id','media_type'}:visit(item,pointer)
                    else:
                        for name,child in item.items():scan(child,pointer+'/'+str(name))
                elif isinstance(item,list):
                    for index,child in enumerate(item):scan(child,pointer+'/'+str(index))
            scan(value,path)
    for name,ref in roots.items():visit(ref,name)
    if missing:raise RuntimeError('ESSENTIAL_HISTORICAL_ARTIFACTS_MISSING: '+repr(missing))
    return dict(imported_artifact_count=len(seen),sources={root:sum(v==root for v in seen.values()) for root in set(seen.values())},missing=[])


def import_manifest(store,inp,created_by):
    parent_manifest=read(PARENT_EVIDENCE/'actual_live_local_only_artifacts.json')
    expected=next(row for row in parent_manifest['files'] if Path(row['path']).name=='platform.sqlite')
    if sha256(PARENT_ROOT/'platform.sqlite')!=expected['sha256']:
        raise RuntimeError('PARENT_STAGE335_STORE_HASH_MISMATCH')
    optimizer=source_stores()[0].artifact(OPTIMIZER)
    proposal=next(row for row in optimizer['proposals'] if row['candidate_id']==PROPOSAL_ID)
    roots={'optimizer_result':OPTIMIZER,'proposal_configuration':proposal['configuration'],**NAMED,
        'analysis_protocol':inp['policy']['route']['data']['analysis_protocol'],
        'endpoint_target':inp['policy']['route']['data']['endpoint_target']}
    if inp['policy']['route']['data'].get('historical_case'):
        roots['historical_case']=inp['policy']['route']['data']['historical_case']
    imported=import_tree(source_stores(),store,roots)
    supporting=[]
    for source_root in HISTORICAL_ROOTS:
        path=source_root/'platform.sqlite'
        supporting.append(dict(path=str(path.resolve()),size=path.stat().st_size,sha256=sha256(path),
            reason='Supplies retained historical-case artifacts or the historical_source referenced by candidate mathematics.'))
    value=dict(kind='historical_math_import_manifest',historical_computation=True,
        source_stage='Stage 3.35',source_run_id=PARENT_RUN,
        source_implementation_commit=read(PARENT_EVIDENCE/'actual_live_manifest.json')['implementation_commit'],
        source_store=dict(path=str((PARENT_ROOT/'platform.sqlite').resolve()),size=(PARENT_ROOT/'platform.sqlite').stat().st_size,
            sha256=sha256(PARENT_ROOT/'platform.sqlite'),remotely_available=False),
        supporting_source_stores=supporting,
        parent_evidence_manifest=dict(path='evidence/stage335_math_route_retry_20260930/actual_live_manifest.json',
            sha256=sha256(PARENT_EVIDENCE/'actual_live_manifest.json')),
        import_created_by=created_by,optimizer_tool_version='1.0.0',optimizer_result=OPTIMIZER,
        optimizer_candidate_id=PROPOSAL_ID,proposal_configuration=proposal['configuration'],
        scientific_configuration_identity='',
        source_build_node='b_mathsel_c1_n0p15_f0p11_s0p95_compliant',protocol=optimizer['protocol'],target=optimizer['target'],
        historical_mathematical_evaluations=16,historical_offline_study_evaluations=8,
        references={name:dict(reference=ref,tool_id={'linearization':'analysis.linearize_candidate',
            'metrics':'analysis.control_metrics','endpoint':'analysis.bounded_endpoint','screen':'design.screen'}[name],
            tool_version='2.0.0' if name=='metrics' else '1.0.0') for name,ref in NAMED.items()},
        import_summary=imported,applicability=optimizer['limitations'])
    # Derive, rather than trust, the full identity from the saved proposal configuration.
    from extensions.tendon_family.candidate_analysis import scientific_configuration_identity
    value['scientific_configuration_identity']=scientific_configuration_identity(store.artifact(proposal['configuration']))
    with store.transaction() as db:reference=plain(store.put(db,value))
    return value,reference


def guidance(manifest_ref):
    refs=', '.join(name+'='+value['artifact_id'] for name,value in NAMED.items())
    return (
        'Conduct ONE explicitly separate Stage 3.36 proposal-bound continuation of Stage 3.35. The Stage 3.35 model selected '
        f'{PROPOSAL_ID} (near 0.15 m, far 0.11 m, common section scale 0.95, compliant) because compliant and stiff tied on '
        'the primary controller-start local residual (about 0.002 m, 0.2 of the 0.01 m tolerance) while compliant had lower '
        'secondary normalized input energy (4.367701514792259e-05 versus 8.463648352583415e-05). Attribute that selection and '
        'reason to Stage 3.35; do not claim a new selection or new mathematics. The local proxy has a zero world-x position-control '
        'row at the straight start and does not predict nonlinear bending, closed-loop reach, sampled settling, real-time feasibility, '
        'causality, or global optimality. Screening is advisory. '
        f'The exact optimizer result is {OPTIMIZER["artifact_id"]}; the frozen historical import manifest is {manifest_ref["artifact_id"]}; '
        f'named historical references are {refs}. Invoke design.build_proposal with the exact optimizer result and candidate_id '
        f'{PROPOSAL_ID}; never retype its parameters and never use the old build label as an optimizer ID. Then invoke '
        'analysis.bind_historical_math and route.record_analysis through historical_math_binding. No fresh optimizer, linearization, '
        'Gramian/frequency, endpoint, screen, MATLAB, or retrospective-study tools are authorized. Decide yourself, from the original '
        'selection evidence and its limitations, whether one backend validation is warranted. Do not fabricate the decision. If yes, '
        'execute only the proposal-bound saved build through route.advance action=run, read the official evaluation/profile evidence, '
        'then finish accurately. There is no second backend attempt. If no, stop with the evidence-based reason and report robot outcomes '
        'as unavailable. Report official reach, existing sampled settling, and complete-update real-time feasibility separately. This '
        'continuation does not retroactively complete or alter the original Stage 3.35 experiment. Use English and exact identities.')


def configure(root,run_id,budget,created_by,timeout_s=1800.):
    inp=deepcopy(read(PARENT_ROOT/'frozen_input.json'));inp['run_id']=run_id
    inp['policy']['budget']=budget;inp['policy']['timeout_s']=timeout_s;inp['policy']['allowed_tools']=[]
    inp['policy']['tool_bindings']=dict(TOOLS);inp['policy']['model']['max_turns']=16
    store=Store(root);store.create(dict(project_id=run_id,grant_id=run_id,authorization_source=created_by,budget=budget))
    manifest,manifest_ref=import_manifest(store,inp,created_by)
    inp['policy']['route']['data'].update(source=created_by,historical_math=manifest_ref,max_trials=1,
        analysis_required_before_run=True,math_evaluation_limit=0,math_selection_required_before_run=True,
        stop_on_task_success=True,guidance=guidance(manifest_ref))
    create(root,inp)
    return Host(root,run_id),inp,manifest,manifest_ref


def fixture_call(host,turn,tool,arguments):
    payload=payload_for(host,DeepSeekAdapter());bindings=host.store.session(host.run_id)['snapshot']['input']['policy']['tool_bindings']
    advertised=next(row['function'] for row in payload['tools'] if row['function']['name']==provider_name(tool))
    raw=dict(choices=[dict(index=0,finish_reason='tool_calls',message=dict(role='assistant',content=None,tool_calls=[dict(
        id='offline-'+str(turn),type='function',function=dict(name=advertised['name'],arguments=json.dumps(dict(
            arguments=arguments,reason='Offline provider-format replay.',tool_version=bindings[tool]))))]))])
    decoded=DeepSeekAdapter().decode(ModelResponse(raw=raw),turn,bindings)
    return host.invoke(decoded),payload


def offline(root,evidence):
    runtime=require_softagent_runtime();run_id='stage336-offline-'+os.urandom(6).hex()
    budget=dict(model_calls=1,tool_calls=20,backend_solves=1,worker_calls=1,wall_s=300.)
    host,inp,manifest,manifest_ref=configure(root,run_id,budget,'Stage 3.36 offline production-boundary replay.',30.)
    receipts=[]
    wrong,payload=fixture_call(host,0,'design.build_proposal',dict(node_id='wrong-build',optimizer_result=OPTIMIZER,
        optimizer_candidate_id=OLD_BUILD_LABEL,reason='Replay the exact Stage 3.35 identifier error.',next_step='Correct the identifier.'));receipts.append(wrong)
    built,_=fixture_call(host,1,'design.build_proposal',dict(node_id='proposal-build',optimizer_result=OPTIMIZER,
        optimizer_candidate_id=PROPOSAL_ID,reason='Build the exact previously selected proposal.',next_step='Bind historical evidence.'));receipts.append(built)
    built_detail=host.store.artifact(built['output'])['detail'];build=host.store.artifact(built_detail['result'])
    bound,_=fixture_call(host,2,'analysis.bind_historical_math',dict(source_node='proposal-build',import_manifest=manifest_ref));receipts.append(bound)
    conflict,_=fixture_call(host,3,'route.record_analysis',dict(node_id='conflicting-report',source_node='proposal-build',
        evidence=[built_detail['result']],historical_math_binding=bound['output'],selected_optimizer_candidate_id='math-stiff-cccc020c6300',
        validation_disposition='recommended',reason='Deliberate provenance conflict.',next_step='Reject.'));receipts.append(conflict)
    report,_=fixture_call(host,4,'route.record_analysis',dict(node_id='proposal-report',source_node='proposal-build',
        evidence=[built_detail['result']],historical_math_binding=bound['output'],validation_disposition='recommended',
        reason='Reuse the exact historical candidate-bound evidence.',next_step='Decide whether to execute.'));receipts.append(report)
    report_detail=host.store.artifact(report['output'])['detail'];report_value=host.store.artifact(report_detail['result'])
    altered,_=fixture_call(host,5,'route.advance',dict(node_id='altered-build',action='build',combination='candidate_gvs_nmpc',
        changes={'components/near/length_m':.17},variables={},max_trials=1,source_node=None,candidate_id='altered',
        evidence=[report_detail['result']],reason='Deliberately alter science.',next_step='Reject historical linkage.',
        design_statement=None,result_statement=None));receipts.append(altered)
    altered_bind,_=fixture_call(host,6,'analysis.bind_historical_math',dict(source_node='altered-build',import_manifest=manifest_ref));receipts.append(altered_bind)
    gate=check_run_eligibility(host,'proposal-build')
    proposal=host.store.artifact(build['proposal_configuration']);effective=host.store.artifact(build['configuration'])
    result=dict(run_id=run_id,runtime=runtime,production_decoder='DeepSeekAdapter.decode',host_boundary=True,
        public_tools_present=all(provider_name(name) in {row['function']['name'] for row in payload['tools']}
            for name in ('design.build_proposal','analysis.bind_historical_math','route.record_analysis')),
        wrong_identifier=dict(submitted=OLD_BUILD_LABEL,status=wrong['execution_status'],error=wrong['error']),
        correct_build=dict(status=built['execution_status'],build_candidate_id=build['build_candidate_id'],
            optimizer_candidate_id=build['optimizer_candidate_id'],source_build_node=build['source_build_node'],
            optimizer_result=build['optimizer_result'],proposal_configuration=build['proposal_configuration'],
            scientific_configuration_identity=build['scientific_configuration_identity'],
            complete_scientific_configuration_equal=scientific_configuration(effective)==scientific_configuration(proposal)),
        historical_binding=dict(status=bound['execution_status'],reference=bound['output'],usage=host.store.artifact(bound['output'])['usage']),
        conflicting_identifier=dict(status=conflict['execution_status'],error=conflict['error']),
        altered_configuration=dict(status=altered_bind['execution_status'],error=altered_bind['error']),
        report=dict(status=report['execution_status'],reference=report_detail['result'],references=report_value['references'],
            selection_trace=report_value['math_selection_trace']),execution_gate=gate,
        usage=host.store.remaining(host.run_id)['used'],math_ledger=host.store.session(host.run_id)['state']['route']['math_evaluations'],
        limits=dict(paid_provider_requests=0,new_mathematical_evaluations=0,backend_executions=0,nmpc_solves=0,workers=0))
    evidence.mkdir(parents=True,exist_ok=True)
    for name,value in (('offline_replay',result),('offline_provider_tools',payload['tools']),
            ('historical_import_manifest',manifest),('runtime_identity',runtime)):
        atomic_json(evidence/(name+'.json'),value)
    atomic_json(root/'offline_replay.json',result)
    files=[path for path in evidence.iterdir() if path.is_file() and path.name!='sha256_manifest.json']
    atomic_json(evidence/'sha256_manifest.json',{path.name:dict(size=path.stat().st_size,sha256=sha256(path)) for path in sorted(files)})
    print(json.dumps(dict(status='passed',wrong_error=wrong['error'],gate=gate,usage=result['usage']),indent=2),flush=True)


def prepare(root):
    runtime=require_softagent_runtime()
    if (root/'workflow.json').is_file():return Host(root,read(root/'workflow.json')['run_id'])
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True):
        raise RuntimeError('LIVE_FREEZE_REQUIRES_CLEAN_WORKTREE')
    run_id='gvs-stage336-'+os.urandom(6).hex();budget=dict(model_calls=16,tool_calls=60,backend_solves=1,worker_calls=0,wall_s=3600.)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    host,inp,manifest,manifest_ref=configure(root,run_id,budget,
        'User-authorized one separate Stage 3.36 proposal-bound DeepSeek continuation at implementation commit '+commit+'.')
    payload=payload_for(host,DeepSeekAdapter())
    values=dict(frozen_input=inp,historical_import_manifest=manifest,runtime_identity=runtime,
        experiment_prompt=dict(guidance=inp['policy']['route']['data']['guidance']),provider_tools=payload['tools'],
        actual_provider_payload=payload,provider_configuration=inp['policy']['model'],parent_stage=dict(
            stage='Stage 3.35',run_id=PARENT_RUN,evidence_manifest='evidence/stage335_math_route_retry_20260930/actual_live_manifest.json',
            evidence_manifest_sha256=sha256(PARENT_EVIDENCE/'actual_live_manifest.json'),optimizer_result=OPTIMIZER,
            optimizer_candidate_id=PROPOSAL_ID,named_references=NAMED))
    for name,value in values.items():atomic_json(root/(name+'.json'),value)
    names=[name+'.json' for name in values]
    freeze=dict(run_id=run_id,stage='Stage 3.36 proposal-bound continuation',implementation_commit=commit,
        implementation_dirty=False,parent_run_id=PARENT_RUN,historical_import=manifest_ref,limits=budget,new_math_limit=0,
        backend_attempt_limit=1,provider_request_limit=16,workers_limit=0,provider_configuration=inp['policy']['model'],
        scientific_configuration_identity=manifest['scientific_configuration_identity'],files={name:sha256(root/name) for name in names},status='prepared')
    atomic_json(root/'freeze_manifest.json',freeze);atomic_json(root/'workflow.json',freeze)
    standard_inspect(host)
    print('Prepared '+run_id+' at '+commit+'; no provider, backend, math, NMPC, or worker calls.',flush=True)
    return host


def audit(host):
    standard=standard_inspect(host);session=host.store.session(host.run_id);route=session['state']['route']
    nodes=[];execution=None;report=None;build=None
    for node in route['nodes']:
        item={key:node[key] for key in ('node_id','action','status','result','error','selection') if key in node}
        nodes.append(item)
        if node.get('status')=='completed' and node.get('result'):
            value=host.store.artifact(node['result'])
            if node['action']=='build' and value.get('proposal_provenance'):build=value
            elif node['action']=='analyze':report=value
            elif node['action']=='run':execution=value
    usage=host.store.remaining(host.run_id)['used'];ledger=route.get('math_evaluations',{})
    result=dict(run_id=host.run_id,status=standard['status'],stop_reason=standard['stop_reason'],route_nodes=nodes,
        proposal_build=None if build is None else {key:build.get(key) for key in ('candidate_id','build_candidate_id','optimizer_candidate_id',
            'source_build_node','optimizer_result','proposal_configuration','scientific_configuration_identity','configuration')},
        analysis_report=None if report is None else {key:report.get(key) for key in ('source_build_node','build_candidate_id',
            'optimizer_candidate_id','references','math_selection_trace','historical_math_binding','validation_disposition','disposition_reason')},
        execution=None if execution is None else {key:execution.get(key) for key in ('status','candidate_id','build_configuration',
            'simulation','evaluation','evaluation_data','task_success','factual_result','profile_report','profile_report_summary','actual_solves')},
        usage=usage,math_evaluations_new=ledger.get('used',0),within_limits=usage['model_calls']<=16 and usage['tool_calls']<=60
            and usage['backend_solves']<=1 and usage['worker_calls']==0 and usage['wall_s']<=3600 and ledger.get('used',0)==0)
    atomic_json(host.store.root/'stage336_audit.json',result);workflow=read(host.store.root/'workflow.json')
    workflow.update(status=standard['status'],stop_reason=standard['stop_reason'],actual_usage=usage);atomic_json(host.store.root/'workflow.json',workflow)
    return result


def package(source,destination,blocker=None):
    runtime=require_softagent_runtime();destination.mkdir(parents=True,exist_ok=True)
    workflow=read(source/'workflow.json');freeze=read(source/'freeze_manifest.json');host=Host(source,workflow['run_id'])
    result=audit(host);behavior=read(source/'behavior_audit.json')
    actual_hashes={name:sha256(source/name) for name in freeze['files']}
    verification=dict(run_id=host.run_id,runtime=runtime,runtime_matches_frozen=runtime==read(source/'runtime_identity.json'),
        implementation_commit=freeze['implementation_commit'],frozen_file_hashes_match=actual_hashes==freeze['files'],
        files={name:dict(expected=value,actual=actual_hashes[name],matches=value==actual_hashes[name]) for name,value in freeze['files'].items()})
    if not verification['runtime_matches_frozen'] or not verification['frozen_file_hashes_match']:raise RuntimeError('LIVE_FREEZE_CHANGED')
    decisions=[]
    for action in behavior['actions']:
        decision=action.get('decision') or {};arguments=decision.get('arguments',{})
        decisions.append(dict(request_id=action['request_id'],tool_id=decision.get('tool_id'),reason=decision.get('reason'),
            node_id=arguments.get('node_id'),action=arguments.get('action'),source_node=arguments.get('source_node'),
            optimizer_candidate_id=arguments.get('optimizer_candidate_id') or arguments.get('selected_optimizer_candidate_id'),
            validation_disposition=arguments.get('validation_disposition'),nested_reason=arguments.get('reason'),
            next_step=arguments.get('next_step'),receipt=action.get('receipt')))
    execution=result['execution'];profile=None if execution is None else execution.get('profile_report_summary')
    facts=None if execution is None else execution.get('factual_result')
    robot=dict(candidate_executed=execution is not None,valid_backend_execution=bool(execution and execution.get('status')=='valid'),
        official_reach=None if facts is None else dict(task_accepted=facts.get('task_accepted'),terminal_error_m=facts.get('terminal_error_m'),
            tolerance_m=facts.get('tolerance_m')),sampled_settling=None if profile is None else profile.get('settling'),
        complete_update_real_time=None if profile is None else {key:profile.get(key) for key in ('deadline_misses','real_time_demonstrated','delivery_cost')},
        interpretation='Unavailable fields mean no valid measured evidence was produced; local mathematics is never substituted.')
    if execution is not None:
        gate=dict(eligible=True,basis='The actual route.advance run passed the same Route gate before backend execution.')
    elif result['proposal_build'] is not None:
        try:gate=check_run_eligibility(host,result['proposal_build']['source_build_node'])
        except Exception as exc:gate=dict(eligible=False,error=str(exc))
    else:gate=dict(eligible=False,error='No proposal-bound build exists.')
    acceptance=dict(interface_and_provenance=dict(proposal_build=result['proposal_build'],analysis_report=result['analysis_report'],
        gate_accepted=gate),
        llm_behavior=dict(stage335_selection_attribution='Inspect actual_model_decisions.json; this field is not inferred from automatic linkage.',
            decisions=decisions,executed=execution is not None),robot_performance=robot)
    local=[]
    for path in sorted(source.iterdir()):
        if path.is_file():local.append(dict(path=str(path.resolve()),size=path.stat().st_size,sha256=sha256(path)))
    usage=dict(stage335=dict(provider_requests=23,tool_calls=18,live_math_evaluations=16,backend_attempts=0,charged_wall_s=846.3290000001434),
        historical_offline_study_math_evaluations=8,new_continuation=dict(provider_requests=behavior['real_model_requests'],
            tool_calls=behavior['tool_calls'],math_evaluations=result['math_evaluations_new'],backend_attempts=behavior['backend_executions'],
            workers=result['usage']['worker_calls'],charged_wall_s=result['usage']['wall_s']),
        cumulative_math_evaluations=24+result['math_evaluations_new'])
    outputs=dict(actual_freeze_verification=verification,actual_workflow=workflow,actual_stage336_audit=result,
        actual_model_decisions=dict(run_id=host.run_id,decisions=decisions),actual_acceptance=acceptance,
        actual_robot_outcomes=robot,actual_usage=usage,actual_tool_inventory=read(source/'provider_tools.json'),
        actual_parent_import=read(source/'historical_import_manifest.json'),actual_local_only_artifacts=dict(remotely_available=False,files=local))
    blocked=read(blocker) if blocker is not None else None
    if blocked is not None:outputs['actual_live_launch_rejection']=blocked
    for name,value in outputs.items():atomic_json(destination/(name+'.json'),value)
    files=[path for path in destination.glob('actual_*.json') if path.name!='actual_manifest.json']
    atomic_json(destination/'actual_manifest.json',dict(run_id=host.run_id,
        status='blocked_before_process' if blocked is not None else result['status'],
        stop_reason='PLATFORM_APPROVAL_REJECTION_BEFORE_PROCESS' if blocked is not None else result['stop_reason'],
        implementation_commit=freeze['implementation_commit'],single_live_continuation_launched=blocked is None,no_retry=True,
        files={path.name:dict(size=path.stat().st_size,sha256=sha256(path)) for path in sorted(files)},usage=usage))
    manifest_files=[path for path in destination.iterdir() if path.is_file() and path.name!='sha256_manifest.json']
    atomic_json(destination/'sha256_manifest.json',{
        path.name:dict(size=path.stat().st_size,sha256=sha256(path)) for path in sorted(manifest_files)})
    print(json.dumps(dict(status=result['status'],stop_reason=result['stop_reason'],usage=usage,robot=robot),indent=2),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['offline','prepare','run','inspect','package'])
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--evidence',type=Path)
    parser.add_argument('--source',type=Path);parser.add_argument('--blocker',type=Path)
    parser.add_argument('--credential-file',type=Path,default=Path.home()/'.codex/.env')
    args=parser.parse_args();root=args.output.resolve()
    if args.action=='offline':
        if args.evidence is None:raise ValueError('--evidence is required')
        offline(root,args.evidence.resolve());return
    if args.action=='package':
        if args.source is None:raise ValueError('--source is required')
        package(args.source.resolve(),root,args.blocker.resolve() if args.blocker else None);return
    host=prepare(root) if args.action in ('prepare','run') else Host(root,read(root/'workflow.json')['run_id'])
    require_softagent_runtime()
    if args.action=='run':
        load_credential(args.credential_file);print('Starting the one Stage 3.36 DeepSeek continuation.',flush=True);host.run();audit(host)
    elif args.action=='inspect':print(json.dumps(audit(host),indent=2),flush=True)


if __name__=='__main__':main()
