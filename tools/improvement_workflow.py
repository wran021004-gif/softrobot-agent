"""Complete-execution continuation of the existing sequential diagnostic phases."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import time
from pathlib import Path

from schemas.platform import SessionInput
from tools.diagnostic_workflow import DiagnosticWorkflow, ROOT, TOOLS, INSTRUCTIONS, PHASES, PERMISSIONS, save, implementation
from tools.diagnostic_improvement import prepare_improvement, transfer_accepted_report, complete_execution
from tools.platform_diagnosis_coordinator import configure_role
from tools.platform_host import Host
from tools.platform_store import plain
from tools.state_io import read, atomic_json
from extensions.tendon_family.gvs_profile import execution_scope

EXECUTION_TOOLS={name:'1.0.0' for name in ('simulation.run','evaluation.run','control.profile_report')}
MODE_LIMITS=dict(model_calls=24,tool_calls=60,wall_s=3600.,backend_solves=1,worker_calls=0)
BASELINE_LIMITS=dict(model_calls=0,tool_calls=10,wall_s=3600.,backend_solves=1,worker_calls=0)


def execution_host(store, run_id, effective, limits, *, parent=None):
    inp=deepcopy(plain(effective));inp['run_id']=run_id
    inp['policy'].update(route=None,search=None,budget=limits,timeout_s=900.,allowed_tools=[],tool_bindings=EXECUTION_TOOLS)
    if execution_scope(inp)!=execution_scope(effective):raise ValueError('EXECUTION_SCIENTIFIC_SCOPE_CHANGED')
    host=Host(store.root,run_id,actor='improvement-executor')
    host.create(inp,parent_run_id=parent)
    return host


class ImprovementWorkflow(DiagnosticWorkflow):
    limits=MODE_LIMITS
    numerical_limits=dict(local_solves=0,prediction_evaluations=0)
    tools={**TOOLS,'design.decide_improvement':'1.0.0'}
    scope={}
    capabilities=dict(complete_execution='One geometry candidate through the existing backend, fixed task evaluation and sampled holding/profile report. No search or additional local checks. Defer/reject leaves the execution allowance unused.')
    instructions={**INSTRUCTIONS,
        'request':'Inspect the common baseline replay inventory and summary. Formulate an open diagnostic question about terminal reach, sampled holding position/speed, and computation. This request authorizes evidence reading and reports only; a separate later improvement decision may select one geometry delta under the preserved grant. No saved-state checks in this pilot. Do not assume the baseline passed.',
        'initial':INSTRUCTIONS['initial']+' Diagnose this baseline replay. Geometry recommendations can be described in recommended_actions; schema recommendations may use defer when no authorized change is justified. Controller weights are outside the physical grant.',
        'improvement':'Read the accepted diagnosis. Make a separate native ImprovementDecision: adopt with an explicit justified delta, or defer/reject with empty changes. Use only the supplied original three-variable geometry grant. Controller weights, materials, force limits and task changes are not authorized. Do not force a geometry change to consume the allowance. State expected measurable effects separately for reach, sampled holding, and computation; uncertainty is allowed. The decision records intent only; the host subsequently validates/builds and may execute exactly one candidate. Unsupported recommendations remain specific future grant/integration work.',
        'revision':'Revise the accepted initial diagnosis using the actual improvement_feedback_content and any sealed complete-execution feedback. If a candidate executed, cite a relevant numeric handle from its actual profile result and compare it with the baseline. If no candidate executed, report the recorded decision or exact validation failure without inventing measurements. Separate reach, sampled holding position/speed, computation and workflow completion. No further candidate or saved-state check is authorized. Explain unresolved mechanisms and specific grant gaps.',
        'response_final':'Read the revised report and actual improvement feedback. Choose final recommendation disposition and finish. Adoption here accepts a report recommendation; it never replaces the baseline or launches work. Claim physical improvement only from a complete accepted evaluation compared with the replayed baseline; reach-plus-holding requires both frozen conditions. Defer/reject without execution is a completed decision workflow, not a successful design.'}
    permissions={**PERMISSIONS,'improvement':['design.decide_improvement']}
    phases={**PHASES,'improvement':dict(limit=dict(model_calls=3,wall_s=300.),protect_project=dict(model_calls=7,tool_calls=10,wall_s=1600.))}

    def fixed(self,phase):
        fixed=super().fixed(phase)
        if phase=='request':
            fixed['diagnosis.request'].update(saved_state_check=None,budget={**self.limits,'backend_solves':0},
                permitted_tools=['diagnosis.inspect_evidence','diagnosis.submit','evidence.read'])
        return fixed

    def run(self):
        started=time.monotonic();status='incomplete';reason=None
        guard=self.directory/'live_attempt.json'
        if guard.exists():raise RuntimeError('LIVE_ATTEMPT_ALREADY_STARTED')
        if implementation()['files']!=self.freeze['implementation']['files']:raise ValueError('FROZEN_IMPLEMENTATION_CHANGED')
        self.validate_frozen_configuration()
        atomic_json(guard,dict(started=datetime.now(timezone.utc).isoformat()))
        self.preparation=None;self.complete_result=None;self.validation_gap=None
        try:
            self.phase('request','diagnosis_request','request')
            self.phase('initial','diagnosis_report','initial_report',require_initial_views=True,
                scheduling='Synchronous calls finish before fixed backend steps. Wall-clock misses do not inject simulated delay.')
            report=self.chain['initial_report'];transfer_accepted_report(self.host('diagnostic'),self.host('design'),report)
            source=self.store.artifact(self.store.artifact(report)['report']['source'])
            baseline=SessionInput.model_validate(self.store.artifact(source['configuration'])['effective'])
            grant=plain(baseline.policy.candidate_builder.parameters)['data']
            self.phase('improvement','improvement_decision','improvement_decision',report=report,report_content=self.store.artifact(report),
                delivery_tool='design.decide_improvement',editable_scope=dict(editable=plain(baseline.policy.editable),candidate_builder=grant),
                previous_report=report,previous_report_content=self.store.artifact(report))
            intent=self.store.artifact(self.chain['improvement_decision'])
            try:self.preparation=prepare_improvement(self.host('design'),report,intent['decision'])
            except ValueError as exc:self.validation_gap=dict(status='delta_rejected',reason=str(exc),intent=intent)
            if self.preparation:
                self.chain['preparation']=save(self.store,self.preparation)
                if self.preparation.status=='prepared_no_execution':
                    candidate=self.store.artifact(self.preparation.configuration)
                    executor=execution_host(self.store,self.project+'-candidate',candidate['effective'],
                        dict(model_calls=0,tool_calls=10,wall_s=1600.,backend_solves=1,worker_calls=0))
                    self.hosts['candidate_executor']=executor
                    configure_role(executor,'executor','One complete candidate and fixed evaluation/profile',
                        phase_budget=dict(limit=dict(tool_calls=3,wall_s=1600.),protect_project=dict(model_calls=7,tool_calls=7,wall_s=600.)))
                    self.complete_result=complete_execution(executor,baseline,self.preparation.candidate_id)
            result=self.complete_result
            feedback=dict(kind='complete_improvement_feedback',source_report=report,source_execution=source['execution_id'],
                decision=self.chain['improvement_decision'],preparation=self.chain.get('preparation'),validation_gap=self.validation_gap,
                execution=result,baseline_facts=self.experiment['baseline_facts'],
                status=result['status'] if result else ('delta_rejected' if self.validation_gap else 'no_change_selected'),
                result=result['receipts']['profile']['output'] if result and result['status']=='evaluated' else None,
                receipt=result['receipts'].get('profile') if result else None)
            self.chain['feedback']=save(self.store,feedback)
            atomic_json(self.directory/'feedback.json',feedback)
            retained=[]
            if feedback['result']:
                retained=[dict(reference=self.chain['feedback'],result=feedback['result'],receipt=feedback['receipt'],
                    result_content=self.store.artifact(feedback['result']))]
            self.phase('revision','diagnosis_report','revised_report',previous_report=report,previous_report_content=self.store.artifact(report),
                check_feedback=retained,improvement_feedback_content=feedback)
            self.phase('response_final','design_response','final_response',check_feedback=retained,improvement_feedback_content=feedback)
            status='completed';reason='Separate improvement decision, actual disposition/execution feedback, accepted revision and final delivery.'
        except Exception as exc:
            reason=str(exc);atomic_json(self.directory/'workflow_failure.json',dict(type=type(exc).__name__,message=reason));print('STOP',reason,flush=True)
        self.export(status,reason,time.monotonic()-started)
        return read(self.directory/'outcome.json')

    def export(self,status,reason,elapsed):
        super().export(status,reason,elapsed)
        outcome=read(self.directory/'outcome.json')
        outcome.update(classification='fresh physical improvement integration pilot',
            feedback_complete=all(k in self.chain for k in ('improvement_decision','feedback','revised_report','final_response')),
            numerical_check_status=None,physical_improvement=dict(preparation=plain(self.preparation) if self.preparation else None,
                validation_gap=self.validation_gap,complete_execution=self.complete_result,
                baseline_facts=self.experiment['baseline_facts'],candidate_executed=self.complete_result is not None))
        atomic_json(self.directory/'outcome.json',outcome)
        destination=self.export_root/self.directory.name;atomic_json(destination/'outcome.json',outcome)
        # Include complete receipts, raw backend exports and every causal JSON artifact.
        archive_store(self.store,destination)


def archive_store(store,destination):
    """Portable sealed evidence, including execution blobs, without rewriting products."""
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    with store.connect(True) as db:ids=[r[0] for r in db.execute('SELECT run_id FROM sessions')]
    events=[event for run in ids for event in store.events(run)]
    refs={};external={}
    def collect(ref):
        ref=plain(ref)
        if ref['artifact_id'] in refs:return
        if ref['artifact_id'] in external:return
        try:body=store.artifact(ref,raw=True)
        except (FileNotFoundError,KeyError) as exc:
            external[ref['artifact_id']]=dict(reference=ref,reason=str(exc));return
        refs[ref['artifact_id']]=(ref,body)
        if ref['media_type']=='application/json':
            import json
            walk(json.loads(body))
    def walk(value):
        if isinstance(value,dict):
            if set(value)=={'artifact_id','media_type'} and isinstance(value['artifact_id'],str) and isinstance(value['media_type'],str):collect(value)
            else:
                for child in value.values():walk(child)
        elif isinstance(value,list):
            for child in value:walk(child)
    for event in events:
        for ref in event['inputs']+event['outputs']:collect(ref)
    folder=destination/'artifacts';folder.mkdir(exist_ok=True)
    for key,(ref,body) in refs.items():
        (folder/(key+('.json' if ref['media_type']=='application/json' else '.blob'))).write_bytes(body)
    atomic_json(destination/'events.json',events)
    atomic_json(destination/'external_references.json',list(external.values()))
    atomic_json(destination/'sha256_manifest.json',{p.relative_to(destination).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(destination.rglob('*')) if p.is_file() and p.name!='sha256_manifest.json'})
