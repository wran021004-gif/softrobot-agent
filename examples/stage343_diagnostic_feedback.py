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
from tools.platform_diagnosis_coordinator import configure_role,transfer_recovery,run_until_handoff,bind_diagnostic_grant,execute_check_feedback
from tools.runtime_identity import require_softagent_runtime
from tools.state_io import read,atomic_json,digest
from extensions.tendon_family.control_evidence import ControlEvidence,ExecutionComparison
from extensions.tendon_family.diagnostic_evidence import import_execution,BoundReader

OUTPUT=ROOT/'runs/stage343_diagnostic_cycle_20261001'
COMPACT=ROOT/'evidence/stage343_diagnostic_cycle_20261001'
SOURCE=ROOT/'runs/stage341_autonomous_20261001'
EXECUTION='5991de53e82747439e87ba8569667e1b'
LIMITS=dict(model_calls=24,tool_calls=60,backend_solves=2,worker_calls=0,wall_s=3600.)
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
    inp['policy'].update(route=None,budget=LIMITS,timeout_s=900. if tools==EXECUTOR else 30.,allowed_tools=[],tool_bindings=tools)
    inp['policy']['budget']={**LIMITS,'model_calls':14 if tools==DIAGNOSTIC else (10 if tools==DESIGN else 0)}
    inp['policy']['model'].update(max_turns=24,readonly_batch_limit=3,tool_naming=tool_naming_policy(tools,READABLE_TOOL_NAMING))
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
    project='gvs-stage343-'+os.urandom(6).hex();store=Store(OUTPUT)
    store.create(dict(project_id=project,grant_id=project,budget=LIMITS,
        authorization_source='User explicitly authorized Stage 3.43: sequential paid DeepSeek design/diagnosis handoff and one bounded fixed-design improvement cycle; no push.'))
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
        allocations=dict(provider_attempts_total=24,tool_calls_total=60,full_backend_attempts_total=2,
            recording_attempts_at_most=1,variant_attempts_at_most=1,unused_backend_reserve=0,
            local_solves_total=6,short_prediction_braking_evaluations_total=24,charged_wall_s=3600.,workers=0),
        initial_plan=dict(recording=0,local_pairs_at_most=1,diagnostic_checks_at_most=2,operating_points='model selected',backend_variant_at_most=1),
        stop='No repeated tuning, no tolerance/solve-budget changes, no new design search. Retain failures. A model may defer unsupported improvement.',
        local_seed='New constant previous-applied-input seed regenerated with candidate dynamics; no historical optimizer replay.',
        descriptor_policy='Advisory only; no screening/exclusion/ranking change without multiple comparable cases.')
    configure_role(hosts['design'],'design',
        'Inspect the supplied factual baseline summary and official profile if needed. Request diagnosis of the secondary-performance failures '
        'through diagnosis.request using the exact supplied identities and binding. Ask an open evidence-based question; no predetermined cause. '
        'The coordinator then hands control to a separate diagnostic context. Use the supplied diagnostic_allocation maximum as the realistic grant, or narrow within its minimum. Reserve the supplied capacity for subsequent design response and final review. Do not prewrite a cause.',
        binding=binding,identities=identities,summary=evidence['output'],summary_content=store.artifact(evidence['output']),official_profile=pref,
        diagnostic_tools=list(DIAGNOSTIC),protocol=protocol,evidence_turn_limit=2,
        diagnostic_allocation=dict(maximum=dict(model_calls=14,tool_calls=32,backend_solves=0,worker_calls=0,wall_s=1200.),
            minimum=dict(model_calls=10,tool_calls=14,wall_s=600.),reserved_for_design=dict(model_calls=6,tool_calls=8,wall_s=300.)))
    freeze=dict(project_id=project,hosts={k:v.run_id for k,v in hosts.items()},binding=binding,identities=identities,
        baseline_profile=profile,baseline_profile_ref=pref,summary=evidence['output'],protocol=protocol,
        limits=LIMITS,sublimits=SUBLIMITS,runtime=runtime,source_manifest=source['manifest'],
        source_configuration=source['metadata']['candidate_input'],source_store=str(SOURCE),
        implementation_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        implementation_files={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path(__file__),ROOT/'tools/platform_diagnosis_coordinator.py',ROOT/'tools/platform_handoff.py',
                ROOT/'extensions/tendon_family/diagnostic_evidence.py',ROOT/'extensions/tendon_family/diagnostic_math.py',
                ROOT/'tools/platform_models.py',ROOT/'tools/platform_host.py',ROOT/'schemas/platform.py',ROOT/'schemas/platform_handoff.py',
                ROOT/'tools/model_transports/deepseek.py',ROOT/'extensions/platform/manifest.py']})
    atomic_json(OUTPUT/'freeze.json',freeze)
    print('PREPARED',project,flush=True);return freeze


def design_response(design, diagnostic, freeze, report, label):
    transfer_recovery(diagnostic,design)
    configure_role(design,'design',
        'Read the supplied diagnostic report, then explicitly adopt, defer or reject using design.respond_diagnosis. '
        'Adoption authorizes one bounded matched verification, not incorporation into the baseline. '
        'Choose a single recommendation only when justified. A saved-evidence response is followed by a diagnostic check phase; '
        'a recommendation may be deferred pending that check. No physical design changes or tuning.',
        report=report,report_content=design.store.artifact(report),binding=freeze['binding'],protocol=freeze['protocol'],evidence_turn_limit=0)
    response=run_until_handoff(design,'design_response')
    atomic_json(OUTPUT/(label+'.json'),design.store.artifact(response))
    return response


def run():
    freeze=prepare();store=Store(OUTPUT)
    if (OUTPUT/'live_attempt.json').exists():raise RuntimeError('ONE_LIVE_CYCLE_ALREADY_ATTEMPTED')
    for path,expected in freeze['implementation_files'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=expected:raise RuntimeError('FROZEN_IMPLEMENTATION_CHANGED')
    hosts={k:Host(OUTPUT,v) for k,v in freeze['hosts'].items()}
    if not all(h.compatibility()['compatible'] for h in hosts.values()):raise RuntimeError('FROZEN_DEPENDENCIES_CHANGED')
    snapshot=OUTPUT/'live_source_snapshot';snapshot.mkdir(parents=True,exist_ok=True)
    for path in freeze['implementation_files']:
        target=snapshot/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/path).read_bytes())
    atomic_json(snapshot/'manifest.json',freeze['implementation_files'])
    atomic_json(OUTPUT/'live_attempt.json',dict(at=datetime.now(timezone.utc).isoformat(),provider='https://api.deepseek.com',
        authorization='User-authorized new Stage 3.43 bounded experiment; independent of the preserved failed Stage 3.42.'))
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path.home()/'.codex/.env')
    design,diagnostic,executor=(hosts[k] for k in ('design','diagnostic','executor'))
    print('ROLE design request',flush=True)
    request=run_until_handoff(design,'diagnosis_request');atomic_json(OUTPUT/'diagnosis_request.json',store.artifact(request))
    bind_diagnostic_grant(diagnostic,request);transfer_recovery(design,diagnostic)
    configure_role(diagnostic,'diagnostic',
        'First complete the saved-evidence handoff. Independently select at least one prediction view and one motion or plans view. '
        'Use diagnosis.inspect_evidence with the exact imported binding, never with a query result as binding. '
        'Submit a concise diagnosis.submit report (2-4 facts) with exact reference/pointer/value selectors from the returned query artifact. '
        'Use /detail/summary/... or /detail/evidence/... as appropriate. Competing hypotheses and missing evidence remain explicit. '
        'Set report.source to binding; configuration_scope to identities.configuration. Do not request numerical work yet. '
        'You may recommend defer pending a necessary check, or one existing parameter within protocol bounds if supported. '
        'The same diagnostic context will continue after design responds; do not infer a causal answer from the role instructions.',
        phase_tools=['diagnosis.inspect_evidence','evidence.read','diagnosis.submit'],
        request=request,binding=freeze['binding'],identities=freeze['identities'],summary=freeze['summary'],protocol=freeze['protocol'],
        scheduling=dict(source='extensions/tendon_family/backends.py',semantics='Synchronous controller command completes before fixed-count mj_step calls. Wall-clock deadline misses do not inject physical delay into simulated time.'))
    print('ROLE diagnostic saved report',flush=True)
    report=run_until_handoff(diagnostic,'diagnosis_report');atomic_json(OUTPUT/'saved_diagnosis_report.json',store.artifact(report))
    response=design_response(design,diagnostic,freeze,report,'saved_design_response')
    # Both validated artifacts now exist before any numerical work.
    atomic_json(OUTPUT/'saved_handoff_validated.json',dict(request=request,report=report,response=response))
    prior_role=store.session(diagnostic.run_id)['state']['role_context']
    transfer_recovery(design,diagnostic)
    decision=store.artifact(response);adopted=None
    if decision['next_action']=='bounded_verification':
        rec=next(r for r in store.artifact(report)['recommendations'] if r['recommendation_id']==decision['recommendation_id'])
        adopted=dict(parameter=rec['parameter'],value=rec['value'])
    configure_role(diagnostic,'diagnostic',
        'Continue the saved-evidence diagnosis. Select one necessary saved-state check first, using diagnosis.check_request. '
        'Choose the update and operation from your hypotheses, not a preset window. The supported operations are prediction_braking '
        '(two held-input predictions: current applied input and instantaneous braking box solution), or local_comparison only for the adopted_parameter. '
        'Read the exact /{update_id}/measured_initial_state and input values from source_selectors.state_file using evidence.read. '
        'For prediction_braking use /{update_id}/actual_tension_n; for a local pair use /{update_id-1}/actual_tension_n. '
        'Set check_id, operation, update_id, model=model.gvs@1.0.0, integration=implicit_euler, horizon_s=0.01, integration_step_s=0.002, '
        'work_limits.wall_s up to 180 (300 for a local pair). State hypotheses, fixed conditions, metrics and acceptance criteria. '
        'The coordinator executes the selected operation and returns feedback here. Consume it before finalizing a revised report. '
        'Set previous_report to the supplied reference. All existing counters and grant usage persist. '
        'If no check can distinguish a material hypothesis, submit a revised report explaining that evidence-supported deferral. '
        'A second check requires prior_result equal to the first feedback reference and additional_need explaining the specific unresolved issue. '
        'Do not run all tools. Missing full historical warm plans stay missing; local pairs are regenerated cold-seed comparisons.',
        request=request,binding=freeze['binding'],identities=freeze['identities'],protocol=freeze['protocol'],
        previous_report=report,previous_report_content=store.artifact(report),design_response=response,adopted_parameter=adopted,
        evidence_views=prior_role.get('evidence_views',[]),check_execution_enabled=True,check_feedback=[],
        scheduling=prior_role['scheduling'])
    from tools.platform_models import run_loop
    for _ in range(3):
        print('ROLE diagnostic check/feedback/revision',flush=True)
        old=store.session(diagnostic.run_id)['state'].get('handoffs',{}).copy()
        run_loop(diagnostic)
        current=store.session(diagnostic.run_id)['state'].get('handoffs',{})
        if current.get('diagnosis_report')!=old.get('diagnosis_report'):
            report=current['diagnosis_report'];break
        check=current.get('diagnostic_check')
        if not check or check==old.get('diagnostic_check'):raise RuntimeError('DIAGNOSTIC_CONTINUATION_STOPPED: '+str(store.session(diagnostic.run_id)['state'].get('stop_reason')))
        print('CHECK coordinator execution',store.artifact(check)['check_id'],flush=True)
        execute_check_feedback(diagnostic,executor,check)
    else:raise RuntimeError('DIAGNOSTIC_REPORT_NOT_REVISED')
    atomic_json(OUTPUT/'diagnosis_report.json',store.artifact(report))
    response=design_response(design,diagnostic,freeze,report,'design_response')
    decision=store.artifact(response)
    if decision['next_action']=='stop':
        result=dict(improvement_gate_passed=False,reason='Design role deferred or rejected further experimentation',backend_attempts=0,
            report=report,response=response,baseline_unchanged=True)
        verification=save(store,result);atomic_json(OUTPUT/'verification.json',result)
    else:
        recommendation=next(r for r in store.artifact(report)['recommendations'] if r['recommendation_id']==decision['recommendation_id'])
        verification=experiment(executor,freeze,recommendation,response,report)
    configure_role(design,'design',
        'Read the verification evidence and finish with design.review_verification. Judge the predeclared gate. '
        'Report reach, sampled settling and computation separately. A failed variant cannot replace the successful baseline. '
        'Distinguish completed workflow, mathematical validation and physical improvement. List unresolved gaps and prerequisites.',
        response=response,verification=verification,verification_content=store.artifact(verification),report=report,protocol=freeze['protocol'],evidence_turn_limit=0)
    print('ROLE design final review',flush=True)
    review=run_until_handoff(design,'final_review');atomic_json(OUTPUT/'final_review.json',store.artifact(review))
    export();print('CYCLE_COMPLETE',flush=True)


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
    feedback=store.session(freeze['hosts']['diagnostic'])['state']['role_context'].get('check_feedback',[])
    if not feedback:raise ValueError('SUPPORTED_VARIANT_REQUIRES_MODEL_SELECTED_CHECK')
    entry=feedback[-1]['protocol']['update_id']
    protocol=dict(frozen=freeze['protocol'],hypothesis=recommendation['rationale'],changed_parameter=parameter,
        baseline_value=baseline['policy']['controller']['parameters']['data']['recipe'][parameter],variant_value=value,
        baseline_configuration=freeze['source_configuration'],variant_scientific_identity=digest(dict(robot=configuration['robot'],task=configuration['task'],controller=configuration['policy']['controller'])),
        design_response=response,diagnosis_report=report,selected_update_ids=[entry])
    atomic_json(OUTPUT/'experimental_protocol.json',protocol);protocol_ref=save(store,protocol)
    local=[f['receipt'] for f in feedback]
    matching=[f for f in feedback if f['protocol']['operation']=='local_comparison' and
        f['protocol']['changed_parameter']==parameter and f['protocol']['changed_value']==value]
    if not matching:
        print('LOCAL matched pair at model-selected update',entry,parameter,value,flush=True)
        pair=invoke(executor,'diagnosis.saved_state_check',dict(binding=freeze['binding'],update_id=entry,operation='local_comparison',
            changed_parameter=parameter,changed_value=value,max_wall_s=300.),'local-pair',False);local.append(pair)
        if pair['execution_status']!='completed':
            result=dict(improvement_gate_passed=False,protocol=protocol_ref,local_checks=local,reason='Matched comparison failed; preserve baseline and defer backend.')
            ref=save(store,result);atomic_json(OUTPUT/'verification.json',result);return ref
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
    descriptors=dict(source_execution=EXECUTION,operating_points=[entry],references=[r.get('output') for r in local],
        classification='provisional model-scoped descriptors; ranking/exclusion unchanged',
        comparable_cases='No new saved-case sweep',
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
            if e['kind'] in ('role_transition','role_context','model_protocol_correction','tool_argument_correction','check_feedback'):transitions.append(e)
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
        stop_reason=next((store.session(r)['state'].get('stop_reason') for r in run_ids if store.session(r)['state'].get('stop_reason')),None),project_id=freeze['project_id'],
        completed_handoffs=handoffs,diagnostic_report_submitted='diagnosis_report' in handoffs,
        design_response_submitted='design_response' in handoffs,model_authored_final_review='final_review' in handoffs,
        improvement_adopted=read(OUTPUT/'final_review.json')['adopt_into_baseline'] if (OUTPUT/'final_review.json').exists() else False,
        usage=usage,diagnostic_request_budget=None if request is None else request['budget'],diagnostic_actual_usage=diagnostic_used,
        diagnostic_subgrant_respected=None if request is None else all(diagnostic_used[k]<=v+1e-9 for k,v in request['budget'].items()),
        protocol_corrections_used=max(store.session(r)['state'].get('protocol_corrections_used',0) for r in run_ids),
        protocol_limits=diagnostic['snapshot']['input']['policy']['model']['protocol_recovery'],
        baseline={k:baseline[k] for k in ('execution_id','terminal_error_m','official_task_success','terminal_tip_speed_m_s',
            'sampled_settling','mean_update_s','deadline_misses','real_time_demonstrated','force_bound_violation_n','solver_error_count')},
        source_preservation=dict(original_manifest_verified=True,original_configuration_verified=True,
            execution_owner=original['owner'],live_source_snapshot='runs/stage343_diagnostic_cycle_20261001/live_source_snapshot/manifest.json'),
        numerical_validation='No new scientific numerical evaluations. Mathematical helper unit tests are not robot validation.' if not any(work['used'].values()) else 'See charged numerical receipts.',
        next_parameter_group='tendon routing and guide lever arms',
        prerequisites=['valid live diagnostic report and explicit design response','matched controller verification','model-scoped braking checks at multiple recorded poses'],
        ranking_changed=False,physical_design_changed=False)
    atomic_json(OUTPUT/'outcome.json',outcome)
    for name in ('saved_handoff_validated','saved_diagnosis_report','saved_design_response','freeze','diagnosis_request','diagnosis_report','design_response','experimental_protocol','verification','final_review','advisory_descriptors',
                 'outcome','workflow_failure','focused_checks','post_live_repairs'):
        path=OUTPUT/(name+'.json')
        if path.exists():atomic_json(COMPACT/(name+'.json'),read(path))
    for name,value in [('usage',usage),('model_decisions',decisions),('role_transitions',transitions),('raw_artifact_manifest',raw),('receipts',tool_calls)]:atomic_json(COMPACT/(name+'.json'),value)
    live_source=OUTPUT/'live_source_snapshot/manifest.json'
    if live_source.exists():atomic_json(COMPACT/'live_source_sha256.json',read(live_source))
    for item in tool_calls:
        r=item['receipt']
        if item['run_id']==freeze['hosts']['diagnostic'] and r['tool_id']=='diagnosis.inspect_evidence' and r.get('output'):
            content=store.artifact(r['output'])
            if content.get('detail',{}).get('evidence',{}).get('observations',{}).get('aligned_intervals'):
                atomic_json(COMPACT/'live_prediction_view.json',content)
    # Compact numerical results retain exact references to local full snapshots.
    for receipt in tool_calls:
        r=receipt['receipt']
        if (r['tool_id']=='diagnosis.saved_state_check' or r['request_id']=='comparable-saved-cases') and r.get('output'):
            atomic_json(COMPACT/(r['request_id']+'.json'),store.artifact(r['output']))
    atomic_json(COMPACT/'sha256_manifest.json',dict(scope='Exact UTF-8 working bytes, excluding this manifest; git attributes keep these bytes stable.',
        files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(COMPACT.glob('*.json')) if p.name!='sha256_manifest.json'}))
    print('USAGE',usage,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','run','export']);a=p.parse_args()
    try: {'prepare':prepare,'run':run,'export':export}[a.action]()
    except BaseException:
        if (OUTPUT/'freeze.json').exists():
            if not (OUTPUT/'workflow_failure.json').exists():
                atomic_json(OUTPUT/'workflow_failure.json',dict(exception_type=sys.exc_info()[0].__name__,message=str(sys.exc_info()[1]),
                    classification='Workflow failure; no fabricated diagnostic report or adoption.',automatic_retry=False))
            export()
        raise
