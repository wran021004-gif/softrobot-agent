"""One authorized sequential design/diagnosis/control verification experiment."""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
from tools.platform_store import Store,plain,encode
from tools.platform_host import Host
from tools.platform_models import tool_naming_policy,READABLE_TOOL_NAMING
from tools.platform_diagnosis_coordinator import configure_role,transfer_recovery,run_until_handoff,bind_diagnostic_grant
from tools.runtime_identity import require_softagent_runtime
from tools.state_io import read,atomic_json,digest
from extensions.tendon_family.control_evidence import ControlEvidence,ExecutionComparison
from extensions.tendon_family.diagnostic_evidence import import_execution,BoundReader

OUTPUT=ROOT/'runs/stage342_diagnostic_cycle_20261001'
COMPACT=ROOT/'evidence/stage342_diagnostic_cycle_20261001'
SOURCE=ROOT/'runs/stage341_autonomous_20261001'
EXECUTION='5991de53e82747439e87ba8569667e1b'
LIMITS=dict(model_calls=24,tool_calls=60,backend_solves=3,worker_calls=0,wall_s=3600.)
SUBLIMITS=dict(local_solves=6,prediction_evaluations=24)
DESIGN={n:'1.0.0' for n in ('diagnosis.request','design.respond_diagnosis','design.review_verification','evidence.read')}
DIAGNOSTIC={n:'1.0.0' for n in ('diagnosis.inspect_evidence','diagnosis.check_request','diagnosis.submit','evidence.read')}
EXECUTOR={n:'1.0.0' for n in ('diagnosis.inspect_evidence','diagnosis.saved_state_check','simulation.run','evaluation.run','control.profile_report','evidence.read')}


def invoke(host,tool,args,request,required=True):
    host.resume()
    receipt=host.invoke(dict(request_id=request,tool_id=tool,tool_version='1.0.0',arguments=args,
        reason='User-authorized bounded diagnostic cycle under the frozen shared project allocation.',cache='new'))
    atomic_json(OUTPUT/(request+'_receipt.json'),receipt)
    if required and receipt['execution_status']!='completed':raise RuntimeError(str(receipt))
    return receipt


def save(store,value):
    with store.transaction() as db:return plain(store.put(db,value))


def input_for_role(configuration,run,tools):
    inp=deepcopy(configuration);inp['run_id']=run
    inp['policy'].update(route=None,budget=LIMITS,timeout_s=900.,allowed_tools=[],tool_bindings=tools)
    inp['policy']['model'].update(max_turns=24,tool_naming=tool_naming_policy(tools,READABLE_TOOL_NAMING))
    return inp


def source_profile(reader,source):
    for event in reversed(reader.store.events(source['owner'])):
        for ref in event['outputs']:
            if ref['media_type']!='application/json':continue
            value=reader.store.artifact(ref)
            if isinstance(value,dict) and value.get('detail',{}).get('execution_id')==EXECUTION and 'sampled_settling' in value['detail']:
                return ref,value['detail']
    raise ValueError('SEALED_SOURCE_PROFILE_REQUIRED')


def prepare():
    runtime=require_softagent_runtime()
    if (OUTPUT/'freeze.json').exists():return read(OUTPUT/'freeze.json')
    reader=ControlEvidence(Store(SOURCE));source=reader.resolve(EXECUTION)
    pref,profile=source_profile(reader,source)
    project='gvs-stage342-'+os.urandom(6).hex();store=Store(OUTPUT)
    store.create(dict(project_id=project,grant_id=project,budget=LIMITS,
        authorization_source='User explicitly authorized Stage 3.42: sequential paid DeepSeek design/diagnosis handoff and one bounded fixed-design improvement cycle; no push.'))
    hosts={}
    for role,tools in [('design',DESIGN),('diagnostic',DIAGNOSTIC),('executor',EXECUTOR)]:
        host=Host(OUTPUT,project+'-'+role);host.create(input_for_role(source['configuration'],host.run_id,tools));hosts[role]=host
    binding=import_execution(reader,EXECUTION,store,hosts['executor'].run_id,source['manifest'])
    with store.transaction() as db:
        # Copy the official profile and its referenced evidence without inventing ownership.
        def copy_refs(value):
            if isinstance(value,dict):
                if set(value)=={'artifact_id','media_type'}:
                    try:body=reader.store.artifact(value,raw=True)
                    except ValueError:return
                    store.put(db,body,value['media_type'])
                else:
                    for v in value.values():copy_refs(v)
            elif isinstance(value,list):
                for v in value:copy_refs(v)
        copy_refs(profile);store.put(db,reader.store.artifact(pref,raw=True),pref['media_type'])
        db.execute("INSERT INTO meta VALUES ('diagnostic_work',?)",(encode(dict(limits=SUBLIMITS,used={k:0 for k in SUBLIMITS})),))
    evidence=invoke(hosts['executor'],'diagnosis.inspect_evidence',dict(binding=binding,view='summary'),'baseline-summary')
    public=store.artifact(binding)
    identities={k:public[k] for k in ('candidate_id','execution_id','task_identity','controller_identity','evidence_manifest','configuration','owner_run_id')}
    protocol=dict(hypothesis='To be selected by diagnostic and design roles from saved evidence before experimental execution.',
        single_factor='One existing controller recipe parameter; physical design, task, evaluator and solver limits fixed.',
        allowed_parameters={'terminal_tip_speed_weight':[.0001,1.],'holding_tip_speed_weight':[.0001,1.]},
        reach=dict(tolerance_m=.01,evaluator=source['configuration']['task']['evaluator']),
        sampled_settling=profile['sampled_settling'],
        improvement=dict(late_max_speed_reduction_fraction=.2,terminal_speed_increase_fraction_max=.1,
            late_max_error_increase_fraction_max=.1,mean_update_increase_fraction_max=.25,
            reach_must_pass=True,force_violation_n=0.,solver_errors=0),
        allocations=dict(provider_attempts_total=24,tool_calls_total=60,full_backend_attempts_total=3,
            recording_attempts_at_most=1,variant_attempts_at_most=1,unused_backend_reserve=1,
            local_solves_total=6,short_prediction_braking_evaluations_total=24,charged_wall_s=3600.,workers=0),
        initial_plan=dict(recording=0,local_pairs=1,operating_points=['holding_window_entry','last_update'],
            braking_inputs_per_point=2,backend_variant=1),
        stop='No repeated tuning, no tolerance/solve-budget changes, no new design search. Retain failures. A model may defer unsupported improvement.',
        local_seed='New constant previous-applied-input seed regenerated with candidate dynamics; no historical optimizer replay.',
        descriptor_policy='Advisory only; no screening/exclusion/ranking change without multiple comparable cases.')
    configure_role(hosts['design'],'design',
        'Inspect the supplied factual baseline summary and official profile if needed. Request diagnosis of the secondary-performance failures '
        'through diagnosis.request using the exact supplied identities and binding. Ask an open evidence-based question; no predetermined cause. '
        'The coordinator then hands control to a separate diagnostic context. Supply a bounded budget within project limits.',
        binding=binding,identities=identities,summary=evidence['output'],official_profile=pref,
        diagnostic_tools=list(DIAGNOSTIC),protocol=protocol)
    freeze=dict(project_id=project,hosts={k:v.run_id for k,v in hosts.items()},binding=binding,identities=identities,
        baseline_profile=profile,baseline_profile_ref=pref,summary=evidence['output'],protocol=protocol,
        limits=LIMITS,sublimits=SUBLIMITS,runtime=runtime,source_manifest=source['manifest'],
        source_configuration=source['metadata']['candidate_input'],source_store=str(SOURCE),
        implementation_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        implementation_files={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path(__file__),ROOT/'tools/platform_diagnosis_coordinator.py',ROOT/'tools/platform_handoff.py',
                ROOT/'extensions/tendon_family/diagnostic_evidence.py',ROOT/'extensions/tendon_family/diagnostic_math.py']})
    atomic_json(OUTPUT/'freeze.json',freeze)
    print('PREPARED',project,flush=True);return freeze


def run():
    freeze=prepare();store=Store(OUTPUT)
    if (OUTPUT/'live_attempt.json').exists():raise RuntimeError('ONE_LIVE_CYCLE_ALREADY_ATTEMPTED')
    for path,expected in freeze['implementation_files'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=expected:raise RuntimeError('FROZEN_IMPLEMENTATION_CHANGED')
    hosts={k:Host(OUTPUT,v) for k,v in freeze['hosts'].items()}
    if not all(h.compatibility()['compatible'] for h in hosts.values()):raise RuntimeError('FROZEN_DEPENDENCIES_CHANGED')
    atomic_json(OUTPUT/'live_attempt.json',dict(at=datetime.now(timezone.utc).isoformat(),provider='https://api.deepseek.com',
        authorization='User-authorized bounded experiment. Credentials loaded privately using existing loader.'))
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path.home()/'.codex/.env')
    design,diagnostic,executor=(hosts[k] for k in ('design','diagnostic','executor'))
    print('ROLE design request',flush=True)
    request=run_until_handoff(design,'diagnosis_request');atomic_json(OUTPUT/'diagnosis_request.json',store.artifact(request))
    bind_diagnostic_grant(diagnostic,request)
    transfer_recovery(design,diagnostic)
    configure_role(diagnostic,'diagnostic',
        'Independently choose saved-evidence queries using diagnosis.inspect_evidence (summary, motion, prediction, plans), '
        'and evidence.read for exact selectors. Read at least one prediction and one motion or plans view. '
        'Assess competing hypotheses; do not force a unique cause. Missing full warm starts/optimizer iterations remain missing. '
        'If a discriminating numerical check is useful, submit diagnosis.check_request with the exact recorded state/input selectors '
        'from source_selectors or the raw controller-observation artifact; this is advisory and does not execute it. '
        'Submit diagnosis.submit with DiagnosticReport source equal to the binding. Each fact needs fact_selectors with reference, '
        'JSON pointer and exact value matching its evidence. Prefer a few concise facts. Recommendations identify a configuration_scope '
        'equal to the supplied original configuration reference. If justified, propose exactly one existing allowed controller parameter '
        'and a concrete value within the protocol. Otherwise recommend defer. Treat control cost omission as a hypothesis, not a proven cause. '
        'The coordinator can perform fresh matched local solves using a declared cold seed; historical full snapshots are unavailable.',
        request=request,binding=freeze['binding'],identities=freeze['identities'],summary=freeze['summary'],
        official_profile=freeze['baseline_profile_ref'],protocol=freeze['protocol'])
    print('ROLE diagnostic evidence and submission',flush=True)
    report=run_until_handoff(diagnostic,'diagnosis_report');atomic_json(OUTPUT/'diagnosis_report.json',store.artifact(report))
    transfer_recovery(diagnostic,design)
    configure_role(design,'design',
        'Read the diagnostic report through evidence.read, then explicitly adopt, defer or reject using design.respond_diagnosis. '
        'Adopt means authorize one bounded verification of the selected recommendation, not incorporation into the successful baseline. '
        'Select the single control factor only if its model-scoped test is justified. No physical design change or repeated tuning.',
        report=report,binding=freeze['binding'],protocol=freeze['protocol'])
    print('ROLE design response',flush=True)
    response=run_until_handoff(design,'design_response');atomic_json(OUTPUT/'design_response.json',store.artifact(response))
    decision=store.artifact(response)
    if decision['next_action']=='stop':
        verification=save(store,dict(improvement_gate_passed=False,reason='Design role deferred or rejected further experimentation',backend_attempts=0))
    else:
        submission=store.artifact(report)
        recommendation=next(r for r in submission['recommendations'] if r['recommendation_id']==decision['recommendation_id'])
        verification=experiment(executor,freeze,recommendation,response,report)
    configure_role(design,'design',
        'Read the verification evidence through evidence.read and finish with design.review_verification. '
        'Judge the predeclared improvement gate; report reach, sampled settling and timing separately. '
        'A failed experimental variant cannot replace the successful baseline. Distinguish completed workflow from physical improvement. '
        'List remaining gaps and the next physical design parameter group with prerequisites, without opening it.',
        response=response,verification=verification,report=report,protocol=freeze['protocol'])
    print('ROLE design final review',flush=True)
    review=run_until_handoff(design,'final_review');atomic_json(OUTPUT/'final_review.json',store.artifact(review))
    export();print('CYCLE_COMPLETE',flush=True)


def refreeze_prelaunch():
    """Explicit prelaunch migration; retain old sessions and the original freeze."""
    freeze=read(OUTPUT/'freeze.json');store=Store(OUTPUT)
    usage=store.remaining()['used']
    if usage['model_calls'] or usage['backend_solves'] or (OUTPUT/'live_attempt.json').exists():
        raise ValueError('PREFLIGHT_MIGRATION_ONLY_BEFORE_LIVE_WORK')
    with store.connect(True) as db:
        work=json.loads(db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone()[0])
    if any(work['used'].values()):raise ValueError('PREFLIGHT_MIGRATION_ONLY_BEFORE_NUMERICAL_WORK')
    identity=digest({p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in freeze['implementation_files']})[:8]
    archive=OUTPUT/('prelaunch_freeze_before_'+identity+'.json')
    if archive.exists():raise ValueError('PREFLIGHT_REVISION_ALREADY_RECORDED')
    archive.write_bytes((OUTPUT/'freeze.json').read_bytes())
    old=deepcopy(freeze['hosts'])
    for role,run_id in old.items():
        prior=store.session(run_id);inp=deepcopy(prior['snapshot']['input']);inp['run_id']=run_id+'-'+identity
        host=Host(OUTPUT,inp['run_id']);host.create(inp);freeze['hosts'][role]=host.run_id
        if prior['state'].get('role_context'):
            with store.transaction() as db:
                state=store.session(host.run_id,db)['state'];state['role_context']=prior['state']['role_context'];store.update_state(db,host.run_id,state)
    freeze['implementation_files']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in freeze['implementation_files']}
    freeze['prelaunch_revision']=dict(prior_freeze=archive.name,prior_hosts=old,reason='Preserve selected evidence views across separate provider turns; compact query views and explicit comparable-case inspection. No paid or numerical work preceded this migration.',limits_unchanged=True)
    atomic_json(OUTPUT/'freeze.json',freeze);print('PRELAUNCH_REBOUND',identity,flush=True)


def experiment(executor,freeze,recommendation,response,report):
    store=executor.store;parameter=recommendation['parameter'];value=recommendation['value']
    allowed=freeze['protocol']['allowed_parameters']
    if recommendation['action']!='control_parameter' or parameter not in allowed or value is None or not allowed[parameter][0]<=value<=allowed[parameter][1]:
        raise ValueError('MODEL_RECOMMENDATION_OUTSIDE_FROZEN_SCOPE')
    reader=BoundReader(store,freeze['binding']);source=reader.resolve(EXECUTION)
    configuration=deepcopy(source['configuration']);configuration['policy']['controller']['parameters']['data']['recipe'][parameter]=value
    baseline=deepcopy(source['configuration']);changed=deepcopy(configuration)
    changed['policy']['controller']['parameters']['data']['recipe'][parameter]=baseline['policy']['controller']['parameters']['data']['recipe'][parameter]
    if baseline!=changed:raise ValueError('EXPERIMENT_MUST_CHANGE_ONE_FACTOR')
    task=baseline['task'];updates=reader.read_file(source,'controller_observations.json')
    start=task['timing']['duration_s']-baseline['policy']['controller']['parameters']['data']['settling']['window_s']
    entry=min(range(len(updates)),key=lambda i:abs(updates[i]['time_s']-start));last=len(updates)-1
    protocol=dict(frozen=freeze['protocol'],hypothesis=recommendation['rationale'],changed_parameter=parameter,
        baseline_value=baseline['policy']['controller']['parameters']['data']['recipe'][parameter],variant_value=value,
        baseline_configuration=freeze['source_configuration'],variant_scientific_identity=digest(dict(robot=configuration['robot'],task=configuration['task'],controller=configuration['policy']['controller'])),
        design_response=response,diagnosis_report=report,selected_update_ids=[entry,last])
    atomic_json(OUTPUT/'experimental_protocol.json',protocol);protocol_ref=save(store,protocol)
    local=[]
    comparable=invoke(executor,'diagnosis.inspect_evidence',dict(binding=freeze['binding'],view='comparable'),'comparable-saved-cases')
    for index in [entry,last]:
        print('BRAKING saved update',index,flush=True)
        result=invoke(executor,'diagnosis.saved_state_check',dict(binding=freeze['binding'],update_id=index,operation='prediction_braking'),f'braking-{index}',False)
        local.append(result)
    print('LOCAL paired comparison',entry,parameter,value,flush=True)
    pair=invoke(executor,'diagnosis.saved_state_check',dict(binding=freeze['binding'],update_id=entry,operation='local_comparison',
        changed_parameter=parameter,changed_value=value,max_wall_s=300.),'local-pair',False);local.append(pair)
    # Exactly one verification, even when a valid local comparison finds a tradeoff.
    # Local model output is advisory; the backend determines the actual outcome.
    variant=Host(OUTPUT,freeze['project_id']+'-variant');inp=input_for_role(configuration,variant.run_id,EXECUTOR)
    variant.create(inp)
    atomic_json(OUTPUT/'variant_input.json',inp)
    print('BACKEND single fixed-design variant',flush=True)
    sim=invoke(variant,'simulation.run',dict(candidate_id='diagnosis-control-variant',changes={}),'variant-simulation',False)
    if sim['execution_status']!='completed':
        result=dict(improvement_gate_passed=False,protocol=protocol_ref,local_checks=local,simulation=sim,reason='Backend attempt failed; no retry')
    else:
        ev=invoke(variant,'evaluation.run',dict(result=sim['output'],execution_id=sim['execution_id']),'variant-evaluation')
        prof=invoke(variant,'control.profile_report',dict(simulation_request_id='variant-simulation',evaluation_request_id='variant-evaluation'),'variant-profile')
        detail=store.artifact(prof['output'])['detail'];a=freeze['baseline_profile'];b=detail
        gates=dict(valid_complete=b['valid_complete_execution'],reach=b['official_task_success'],
            late_speed_reduced_20_percent=b['sampled_settling']['max_speed_m_s']<=a['sampled_settling']['max_speed_m_s']*.8,
            terminal_speed_tradeoff=b['terminal_tip_speed_m_s']<=a['terminal_tip_speed_m_s']*1.1,
            late_position_tradeoff=b['sampled_settling']['max_error_m']<=a['sampled_settling']['max_error_m']*1.1,
            timing_tradeoff=b['mean_update_s']<=a['mean_update_s']*1.25,
            bounded_forces=b['force_bound_violation_n']==0.,no_solver_errors=b['solver_error_count']==0)
        comparison=reader.compare(ExecutionComparison(baseline_execution_id=EXECUTION,variant_execution_id=sim['execution_id'],changed_factor='controller'),ControlEvidence(store))
        result=dict(improvement_gate_passed=all(gates.values()),gates=gates,protocol=protocol_ref,local_checks=local,
            baseline={k:a[k] for k in ('execution_id','terminal_error_m','terminal_tip_speed_m_s','sampled_settling','mean_update_s','deadline_misses','official_task_success','real_time_demonstrated')},
            variant={k:b[k] for k in ('execution_id','terminal_error_m','terminal_tip_speed_m_s','sampled_settling','mean_update_s','deadline_misses','official_task_success','real_time_demonstrated','force_bound_violation_n','solver_error_count')},
            simulation=sim,evaluation=ev['output'],profile=prof['output'],comparison=comparison,
            change=dict(parameter=parameter,value=value),baseline_unchanged=True)
    ref=save(store,result);atomic_json(OUTPUT/'verification.json',result)
    # Provisional descriptors from actual trajectory points; no ranking dataset or screening mutation.
    descriptors=dict(source_execution=EXECUTION,operating_points=[entry,last],references=[r.get('output') for r in local],
        classification='provisional model-scoped descriptors; ranking/exclusion unchanged',
        comparable_cases=comparable['output'],
        missing='No replicated closed-loop braking evidence or multiple comparable physical designs.')
    atomic_json(OUTPUT/'advisory_descriptors.json',descriptors)
    return ref


def export():
    freeze=read(OUTPUT/'freeze.json');store=Store(OUTPUT);COMPACT.mkdir(parents=True,exist_ok=True)
    decisions=[];transitions=[];raw=[];tool_calls=[]
    with store.connect(True) as db:run_ids=[r[0] for r in db.execute('SELECT run_id FROM sessions')];work=json.loads(db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone()[0])
    for run in run_ids:
        for e in store.events(run):
            if e['kind']=='model_decision':decisions.append(dict(run_id=run,decision=store.artifact(e['outputs'][0]),reference=e['outputs'][0]))
            if e['kind'] in ('role_transition','role_context','model_protocol_correction','tool_argument_correction'):transitions.append(e)
            if e['kind'] in ('model_raw_response','model_request','context_delivery'):raw.append(e)
        with store.connect(True) as db:
            tool_calls.extend(dict(run_id=run,receipt=json.loads(r[0])) for r in db.execute('SELECT receipt FROM calls WHERE run_id=? AND receipt IS NOT NULL',(run,)))
    usage=dict(project=store.remaining(),numerical=work)
    diagnostic=store.session(freeze['hosts']['diagnostic']);design=store.session(freeze['hosts']['design'])
    request=read(OUTPUT/'diagnosis_request.json') if (OUTPUT/'diagnosis_request.json').exists() else None
    diagnostic_used=store.remaining(freeze['hosts']['diagnostic'])['used']
    handoffs={**design['state'].get('handoffs',{}),**diagnostic['state'].get('handoffs',{})}
    original=ControlEvidence(Store(SOURCE)).resolve(EXECUTION)
    if original['manifest']!=freeze['source_manifest'] or original['metadata']['candidate_input']!=freeze['source_configuration']:
        raise ValueError('ORIGINAL_SOURCE_BINDING_CHANGED')
    baseline=freeze['baseline_profile']
    outcome=dict(status='completed' if 'final_review' in handoffs else 'incomplete',
        stop_reason=diagnostic['state'].get('stop_reason'),project_id=freeze['project_id'],
        completed_handoffs=handoffs,diagnostic_report_submitted='diagnosis_report' in handoffs,
        design_response_submitted='design_response' in handoffs,model_authored_final_review='final_review' in handoffs,
        improvement_adopted=read(OUTPUT/'final_review.json')['adopt_into_baseline'] if (OUTPUT/'final_review.json').exists() else False,
        usage=usage,diagnostic_request_budget=None if request is None else request['budget'],diagnostic_actual_usage=diagnostic_used,
        diagnostic_subgrant_respected=None if request is None else all(diagnostic_used[k]<=v+1e-9 for k,v in request['budget'].items()),
        protocol_corrections_used=diagnostic['state'].get('protocol_corrections_used',0),
        protocol_limits=diagnostic['snapshot']['input']['policy']['model']['protocol_recovery'],
        baseline={k:baseline[k] for k in ('execution_id','terminal_error_m','official_task_success','terminal_tip_speed_m_s',
            'sampled_settling','mean_update_s','deadline_misses','real_time_demonstrated','force_bound_violation_n','solver_error_count')},
        source_preservation=dict(original_manifest_verified=True,original_configuration_verified=True,
            execution_owner=original['owner'],live_source_snapshot='runs/stage342_diagnostic_cycle_20261001/live_source_snapshot/manifest.json'),
        numerical_validation='No new scientific numerical evaluations. Mathematical helper unit tests are not robot validation.' if not any(work['used'].values()) else 'See charged numerical receipts.',
        next_parameter_group='tendon routing and guide lever arms',
        prerequisites=['valid live diagnostic report and explicit design response','matched controller verification','model-scoped braking checks at multiple recorded poses'],
        ranking_changed=False,physical_design_changed=False)
    atomic_json(OUTPUT/'outcome.json',outcome)
    for name in ('freeze','diagnosis_request','diagnosis_report','design_response','experimental_protocol','verification','final_review','advisory_descriptors',
                 'outcome','workflow_failure','focused_checks','post_live_repairs'):
        path=OUTPUT/(name+'.json')
        if path.exists():atomic_json(COMPACT/(name+'.json'),read(path))
    for name,value in [('usage',usage),('model_decisions',decisions),('role_transitions',transitions),('raw_artifact_manifest',raw),('receipts',tool_calls)]:atomic_json(COMPACT/(name+'.json'),value)
    live_source=OUTPUT/'live_source_snapshot/manifest.json'
    if live_source.exists():atomic_json(COMPACT/'live_source_sha256.json',read(live_source))
    for item in tool_calls:
        r=item['receipt']
        if item['run_id']==freeze['hosts']['diagnostic'] and r['request_id']=='model-1-tool' and r.get('output'):
            atomic_json(COMPACT/'live_prediction_view.json',store.artifact(r['output']))
    # Compact numerical results retain exact references to local full snapshots.
    for receipt in tool_calls:
        r=receipt['receipt']
        if (r['tool_id']=='diagnosis.saved_state_check' or r['request_id']=='comparable-saved-cases') and r.get('output'):
            atomic_json(COMPACT/(r['request_id']+'.json'),store.artifact(r['output']))
    atomic_json(COMPACT/'sha256_manifest.json',dict(scope='Exact UTF-8 working bytes, excluding this manifest; git attributes keep these bytes stable.',
        files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(COMPACT.glob('*.json')) if p.name!='sha256_manifest.json'}))
    print('USAGE',usage,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','refreeze-prelaunch','run','export']);a=p.parse_args()
    try: {'prepare':prepare,'refreeze-prelaunch':refreeze_prelaunch,'run':run,'export':export}[a.action]()
    except BaseException:
        if (OUTPUT/'freeze.json').exists():
            if not (OUTPUT/'workflow_failure.json').exists():
                atomic_json(OUTPUT/'workflow_failure.json',dict(exception_type=sys.exc_info()[0].__name__,message=str(sys.exc_info()[1]),
                    classification='Workflow failure; no fabricated diagnostic report or adoption.',automatic_retry=False))
            export()
        raise
