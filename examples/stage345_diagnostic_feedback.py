"""One bounded live design/diagnosis handoff and saved-state feedback cycle."""
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
from tools.platform_diagnosis_coordinator import configure_role,transfer_recovery,run_until_handoff,bind_diagnostic_grant,execute_check_feedback,adopted_check_parameter
from tools.runtime_identity import require_softagent_runtime
from tools.state_io import read,atomic_json,digest
from extensions.tendon_family.control_evidence import ControlEvidence,ExecutionComparison
from extensions.tendon_family.diagnostic_evidence import import_execution,BoundReader

OUTPUT=ROOT/'runs/stage345_diagnostic_cycle_20261002'
COMPACT=ROOT/'evidence/stage345_diagnostic_cycle_20261002'
SOURCE=ROOT/'runs/stage341_autonomous_20261001'
EXECUTION='5991de53e82747439e87ba8569667e1b'
LIMITS=dict(model_calls=24,tool_calls=60,backend_solves=0,worker_calls=0,wall_s=3600.)
SUBLIMITS=dict(local_solves=6,prediction_evaluations=24)
DESIGN={n:'1.0.0' for n in ('diagnosis.request','design.respond_diagnosis','evidence.read')}
DIAGNOSTIC={n:'1.0.0' for n in ('diagnosis.inspect_evidence','diagnosis.check_request','diagnosis.submit','evidence.read')}
EXECUTOR={n:'1.0.0' for n in ('diagnosis.inspect_evidence','diagnosis.saved_state_check','evidence.read')}


# Reserves are lower bounds retained for downstream phases, in all three resources.
PHASES={
    'request':dict(limit=dict(model_calls=3,tool_calls=7,wall_s=600.),protect_role=dict(model_calls=7,tool_calls=7,wall_s=600.),
        protect_project=dict(model_calls=21,tool_calls=40,wall_s=2100.)),
    'initial':dict(limit=dict(model_calls=4),protect_role=dict(model_calls=6,tool_calls=10,wall_s=600.),
        protect_project=dict(model_calls=13,tool_calls=18,wall_s=1500.)),
    'response_initial':dict(limit=dict(model_calls=3,tool_calls=3,wall_s=300.),protect_role=dict(model_calls=4,tool_calls=4,wall_s=300.),
        protect_project=dict(model_calls=10,tool_calls=15,wall_s=1200.)),
    'check_revision':dict(limit=dict(model_calls=10),protect_role=dict(model_calls=3,tool_calls=3,wall_s=240.),
        protect_project=dict(model_calls=7,tool_calls=8,wall_s=840.)),
    'after_feedback':dict(protect_role={},protect_project=dict(model_calls=4,tool_calls=4,wall_s=300.)),
    'executor_check':dict(limit=dict(tool_calls=1,wall_s=300.),protect_project=dict(model_calls=7,tool_calls=7,wall_s=540.)),
    'response_final':dict(limit=dict(model_calls=4,tool_calls=4,wall_s=300.)),
}

SAVED_STATE_SCOPE=dict(operations=['prediction_braking','local_comparison'],model='model.gvs@1.0.0',
    horizon_s=.01,integration='implicit_euler',integration_step_s=.002,max_wall_s=300.,max_checks=1,
    numerical_limits=SUBLIMITS,configuration_scope='saved_state_or_temporary_analysis')


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
    project='gvs-stage345-'+os.urandom(6).hex();store=Store(OUTPUT)
    store.create(dict(project_id=project,grant_id=project,budget=LIMITS,
        authorization_source='User explicitly authorized Stage 3.45: sequential paid DeepSeek design/diagnosis handoff and one saved-state check with model feedback; no backend simulation; no push.'))
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
    protocol=dict(scope='One saved-state check; no full backend simulation, controller tuning or physical change.',
        saved_state_check=SAVED_STATE_SCOPE,
        operations=['prediction_braking','local_comparison'],max_checks=1,
        numerical_limits=SUBLIMITS,backend_attempts=0,workers=0,
        allowed_parameters={'terminal_tip_speed_weight':[.0001,1.],'holding_tip_speed_weight':[.0001,1.]},
        completion=['model request','initial report','initial design response','model check selection',
                    'check receipt and feedback','revised report citing feedback','second design response'],
        acceptance_criteria=[
            'Model-authored request explicitly grants retained reads and one bounded saved-state numerical check.',
            'Initial report separates exact selected facts, hypotheses and evidence gaps; design records a legal disposition.',
            'Model chooses unresolved question, saved state/input, operation, model, horizon and bounded work; executor validates request scope before execution.',
            'Revised report links previous report and feedback, cites exact numerical result selectors when available, and explains support/weakening/unresolved with model and horizon limits.',
            'Final design response links the revised report; no subsequent comparison or physical improvement is evaluated.'],
        phases=PHASES,phase_permissions=dict(request=['evidence.read','diagnosis.request'],
            initial=['diagnosis.inspect_evidence','evidence.read','diagnosis.submit'],
            check=['diagnosis.inspect_evidence','evidence.read','diagnosis.check_request'],
            revision=['diagnosis.submit'],response=['design.respond_diagnosis']),
        reading='At most two successful read turns per evidence phase; a sequential batch counts once, each tool is charged. Corrections count as attempts, not reads.')
    configure_role(hosts['design'],'design',
        'Inspect the supplied factual baseline summary and official profile if needed. Request diagnosis of the secondary-performance failures '
        'through diagnosis.request using the exact supplied identities and binding. Ask an open evidence-based question; no predetermined cause. '
        'Author scope distinguishing (1) retained-evidence reading, (2) one bounded numerical saved-state check using the supplied saved_state_check grant, '
        '(3) excluded production controller changes and full backend execution. Include saved_state_check from protocol in your request; the later check must satisfy it. '
        'The probe uses the identified execution saved state or a temporary analysis configuration, never modifies production or baseline. '
        'local_comparison requires later adoption of the exact parameter/value; deferral cannot authorize it. '
        'The coordinator then hands control to a separate diagnostic context. Use the supplied diagnostic_allocation maximum as the realistic grant, or narrow within its minimum. Reserve the supplied capacity for subsequent design response and second response. Do not prewrite a cause.',
        binding=binding,identities=identities,summary=evidence['output'],summary_content=store.artifact(evidence['output']),official_profile=pref,
        diagnostic_tools=list(DIAGNOSTIC),protocol=protocol,evidence_turn_limit=2,phase_budget=PHASES['request'],
        diagnostic_allocation=dict(maximum=dict(model_calls=14,tool_calls=32,backend_solves=0,worker_calls=0,wall_s=1200.),
            minimum=dict(model_calls=10,tool_calls=18,wall_s=900.),reserved_for_design=dict(model_calls=7,tool_calls=7,wall_s=600.)))
    freeze=dict(project_id=project,hosts={k:v.run_id for k,v in hosts.items()},binding=binding,identities=identities,
        baseline_profile=profile,baseline_profile_ref=pref,summary=evidence['output'],protocol=protocol,
        limits=LIMITS,sublimits=SUBLIMITS,phases=PHASES,provider_configuration=hosts['design'].store.session(hosts['design'].run_id)['snapshot']['input']['policy']['model'],runtime=runtime,source_manifest=source['manifest'],
        source_configuration=source['metadata']['candidate_input'],source_store=str(SOURCE),
        implementation_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        implementation_files={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path(__file__),ROOT/'tools/platform_diagnosis_coordinator.py',ROOT/'tools/platform_handoff.py',
                ROOT/'extensions/tendon_family/diagnostic_evidence.py',ROOT/'extensions/tendon_family/diagnostic_math.py',
                ROOT/'tools/platform_models.py',ROOT/'tools/platform_store.py',ROOT/'tools/platform_host.py',ROOT/'schemas/platform.py',ROOT/'schemas/platform_handoff.py',
                ROOT/'tools/model_transports/deepseek.py',ROOT/'extensions/platform/manifest.py']})
    atomic_json(OUTPUT/'freeze.json',freeze)
    print('PREPARED',project,flush=True);return freeze


def design_response(design, diagnostic, freeze, report, label):
    transfer_recovery(diagnostic,design)
    configure_role(design,'design',
        'Read the supplied diagnostic report, then explicitly adopt, defer or reject using design.respond_diagnosis. '
        'A recommendation for future matched verification will be recorded only; no backend comparison is authorized in this stage. '
        'Choose a single recommendation only when justified. A saved-evidence response is followed by a diagnostic check phase; '
        'a recommendation may be deferred pending that check. No physical design changes or tuning.',
        report=report,report_content=design.store.artifact(report),binding=freeze['binding'],protocol=freeze['protocol'],evidence_turn_limit=0,phase_budget=PHASES['response_initial' if label=='saved_design_response' else 'response_final'])
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
        authorization='User-authorized new Stage 3.45 bounded experiment; preserved Stage 3.42 through Stage 3.44 attempts remain unchanged.'))
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path.home()/'.codex/.env')
    design,diagnostic,executor=(hosts[k] for k in ('design','diagnostic','executor'))
    print('ROLE design request',flush=True)
    request=run_until_handoff(design,'diagnosis_request');atomic_json(OUTPUT/'diagnosis_request.json',store.artifact(request))
    bind_diagnostic_grant(diagnostic,request);transfer_recovery(design,diagnostic)
    configure_role(diagnostic,'diagnostic',
        'First complete the saved-evidence handoff. Independently select at least one prediction view and one motion or plans view. '
        'The request separates retained-evidence reads from one numerical saved-state check under saved_state_check. Production controller changes and backend simulation are excluded. '
        'Numerical probes operate only on the saved projected state or a temporary analysis configuration, never the successful baseline. '
        'Use diagnosis.inspect_evidence with the exact imported binding, never with a query result as binding. '
        'You have at most four provider attempts including corrections and two successful reading turns. Read prediction plus motion/plans in one legal batch if useful. After reading closes only submit is allowed. Submit supported facts and explicit gaps; defer uncertain recommendations. Submit a concise diagnosis.submit report (2-4 facts) with exact reference/pointer/value selectors from the returned query artifact. '
        'Use /detail/summary/... or /detail/evidence/... as appropriate. Competing hypotheses and missing evidence remain explicit. '
        'Set report.source to binding; configuration_scope to identities.configuration. Do not request numerical work yet. '
        'You may recommend defer pending a necessary check, or one existing parameter within protocol bounds if supported. '
        'The same diagnostic context will continue after design responds; do not infer a causal answer from the role instructions.',
        phase_tools=['diagnosis.inspect_evidence','evidence.read','diagnosis.submit'],
        phase_budget=PHASES['initial'],evidence_turn_limit=2,require_initial_views=True,
        request=request,request_content=store.artifact(request),binding=freeze['binding'],identities=freeze['identities'],summary=freeze['summary'],summary_content=store.artifact(freeze['summary']),protocol=freeze['protocol'],
        scheduling=dict(source='extensions/tendon_family/backends.py',semantics='Synchronous controller command completes before fixed-count mj_step calls. Wall-clock deadline misses do not inject physical delay into simulated time.'))
    print('ROLE diagnostic saved report',flush=True)
    report=run_until_handoff(diagnostic,'diagnosis_report');atomic_json(OUTPUT/'saved_diagnosis_report.json',store.artifact(report))
    response=design_response(design,diagnostic,freeze,report,'saved_design_response')
    # Both validated artifacts now exist before any numerical work.
    atomic_json(OUTPUT/'saved_handoff_validated.json',dict(request=request,report=report,response=response))
    export()  # Persist both model submissions before any numerical work.
    prior_role=store.session(diagnostic.run_id)['state']['role_context']
    transfer_recovery(design,diagnostic)
    # stop declines recommendation verification; the independent check continues.
    adopted=adopted_check_parameter(store,report,response)
    configure_role(diagnostic,'diagnostic',
        'Continue the saved-evidence diagnosis. Select one necessary saved-state check first, using diagnosis.check_request. '
        'Choose the update and operation from your hypotheses, not a preset window. The supported operations are prediction_braking '
        '(two held-input predictions: current applied input and instantaneous braking box solution), or local_comparison only for the adopted_parameter. '
        'Read the exact /{update_id}/measured_initial_state and input values from source_selectors.state_file using evidence.read. '
        'For prediction_braking use /{update_id}/actual_tension_n; for a local pair use /{update_id-1}/actual_tension_n. '
        'Set check_id, operation, update_id, model=model.gvs@1.0.0, integration=implicit_euler, horizon_s=0.01, integration_step_s=0.002, '
        'work_limits.wall_s up to 180 (300 for a local pair). State hypotheses, fixed conditions, metrics and acceptance criteria. '
        'Set work_limits.prediction_evaluations=2 for prediction_braking or work_limits.local_solves=2 for a local pair. '
        'Stay within request.saved_state_check and frozen numerical limits. A local pair also requires the saved effective plan horizon to equal the declared horizon. '
        'The coordinator executes the selected operation and returns feedback here. Consume it before finalizing a revised report. '
        'Set previous_report to the supplied reference. All existing counters and grant usage persist. '
        'Choose the check to clarify one unresolved model-scoped question; a failed or inconclusive result must be reported honestly. '
        'Exactly one check is authorized. After at most two successful reading turns only check_request is available; after feedback only submit is available. '
        'Do not run all tools. Missing full historical warm plans stay missing; local pairs are regenerated cold-seed comparisons.',
        request=request,request_content=store.artifact(request),binding=freeze['binding'],identities=freeze['identities'],protocol=freeze['protocol'],
        phase_budget=PHASES['check_revision'],phase_tools=['diagnosis.inspect_evidence','evidence.read','diagnosis.check_request'],evidence_turn_limit=2,max_checks=1,
        after_feedback_reservations=PHASES['after_feedback'],
        summary_content=store.artifact(freeze['summary']),
        previous_report=report,previous_report_content=store.artifact(report),design_response=response,design_response_content=store.artifact(response),adopted_parameter=adopted,
        evidence_views=prior_role.get('evidence_views',[]),check_execution_enabled=True,check_feedback=[],
        scheduling=prior_role['scheduling'])
    print('ROLE diagnostic check selection',flush=True)
    check=run_until_handoff(diagnostic,'diagnostic_check')
    atomic_json(OUTPUT/'selected_check.json',store.artifact(check))
    print('CHECK coordinator execution',store.artifact(check)['check_id'],flush=True)
    configure_role(executor,'executor','Execute the one saved-state check',phase_budget=PHASES['executor_check'])
    feedback=execute_check_feedback(diagnostic,executor,check)
    atomic_json(OUTPUT/'check_feedback.json',store.artifact(feedback))
    print('ROLE diagnostic feedback/revision',flush=True)
    revised=run_until_handoff(diagnostic,'diagnosis_report')
    if revised==report:raise RuntimeError('DIAGNOSTIC_REPORT_NOT_REVISED')
    atomic_json(OUTPUT/'diagnosis_report.json',store.artifact(revised))
    response=design_response(design,diagnostic,freeze,revised,'design_response')
    atomic_json(OUTPUT/'completed_chain.json',dict(request=request,initial_report=report,
        initial_response=read(OUTPUT/'saved_handoff_validated.json')['response'],check=check,
        feedback=feedback,revised_report=revised,final_response=response,
        stopping_reason='All eight workflow steps completed; one-check scope exhausted. No backend or physical improvement evaluated.'))
    export();print('CYCLE_COMPLETE',flush=True)


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
    complete=(OUTPUT/'completed_chain.json').exists()
    feedback=read(OUTPUT/'check_feedback.json') if (OUTPUT/'check_feedback.json').exists() else None
    outcome=dict(status='completed' if complete else 'incomplete',
        initial_live_handoff_completed=(OUTPUT/'saved_handoff_validated.json').exists(),
        check_selected=(OUTPUT/'selected_check.json').exists(),
        check_executed=(OUTPUT/'check_feedback.json').exists(),
        check_execution_status=None if feedback is None else feedback['receipt']['execution_status'],
        feedback_consumed=(OUTPUT/'diagnosis_report.json').exists(),
        revised_report_validated=(OUTPUT/'diagnosis_report.json').exists(),
        design_responded_to_revision=complete,physical_improvement='not evaluated',
        stop_reason='Completed authorized eight-step chain; no further execution authorized' if complete else next((store.session(r)['state'].get('stop_reason') for r in run_ids if store.session(r)['state'].get('stop_reason')),
            read(OUTPUT/'workflow_failure.json')['message'] if (OUTPUT/'workflow_failure.json').exists() else 'Workflow in progress'),project_id=freeze['project_id'],
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
            execution_owner=original['owner'],live_source_snapshot='runs/stage345_diagnostic_cycle_20261002/live_source_snapshot/manifest.json'),
        numerical_validation='No new scientific numerical evaluations. Mathematical helper unit tests are not robot validation.' if not any(work['used'].values()) else 'See charged numerical receipts.',
        future_comparison='Proposal only, to be assessed from the revised report and final response; no subsequent comparison executed.',
        ranking_changed=False,physical_design_changed=False)
    atomic_json(OUTPUT/'outcome.json',outcome)
    for name in ('saved_handoff_validated','saved_diagnosis_report','saved_design_response','freeze','diagnosis_request','diagnosis_report','design_response','experimental_protocol','verification','final_review','advisory_descriptors',
                 'outcome','workflow_failure','focused_checks','post_live_repairs','completed_chain','selected_check','check_feedback'):
        path=OUTPUT/(name+'.json')
        if path.exists():atomic_json(COMPACT/(name+'.json'),read(path))
    for name,value in [('usage',usage),('model_decisions',decisions),('role_transitions',transitions),('raw_artifact_manifest',raw),('receipts',tool_calls)]:atomic_json(COMPACT/(name+'.json'),value)
    atomic_json(COMPACT/'role_usage.json',{role:store.remaining(run) for role,run in freeze['hosts'].items()})
    # Persist raw transport/tool evidence in a portable artifact bundle, without credentials.
    artifact_dir=COMPACT/'artifacts';artifact_dir.mkdir(exist_ok=True)
    refs=[]
    for event in raw+transitions:
        refs.extend(event['inputs']+event['outputs'])
    for item in tool_calls:
        if item['receipt'].get('output'):refs.append(item['receipt']['output'])
    for ref in refs:
        if ref['media_type']=='application/json':
            (artifact_dir/(ref['artifact_id']+'.json')).write_bytes(store.artifact(ref,raw=True))
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
        files={p.relative_to(COMPACT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(COMPACT.rglob('*.json')) if p.name!='sha256_manifest.json'}))
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
