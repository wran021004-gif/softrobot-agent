"""New linked diagnostic grant. Numerical and interpretation recovery reuse receipts."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from examples import milestone5_validation as previous
from tools.diagnostic_workflow import DiagnosticWorkflow, save
from tools.platform_host import Host
from tools.platform_store import Store, plain
from tools.state_io import read, atomic_json, digest
from tools.runtime_identity import require_softagent_runtime
from tools.platform_registry import registry
from tools.platform_diagnosis_coordinator import configure_role, run_until_handoff
from tools.platform_models import payload_for
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from extensions.tendon_family.control_evidence import ControlEvidence
from extensions.tendon_family.diagnostic_evidence import import_execution
from extensions.tendon_family.milestone5_diagnostic import DEFINITION

RUN=ROOT/'runs/milestone5_diagnostic_20261005/single_context'
EVIDENCE=ROOT/'evidence/milestone5_diagnostic_20261005'
LIMITS=dict(model_calls=8,tool_calls=30,backend_solves=0,worker_calls=0,wall_s=1800.)
EXECUTIONS=['2413ff2a56de422dac47b7fd78717563','9865f1636266479c93817cad42a65353']
AUTHORIZATION=dict(source='User attachment f275d000-9975-4e2d-9a19-444a8e36850f, 2026-10-05',
    stage='NEW bounded diagnostic stage linked to completed prediction-validation; predecessor not reopened',
    destination='https://api.deepseek.com',model='deepseek-flash',
    covered_data=['robot/task/model/controller/candidate configurations','saved historical and prospective results and trajectories',
        'compact diagnostics/numerical comparisons/artifact references/implementation details','instructions/tool schemas/budgets/proposals/interpretation and necessary corrections'],
    credentials='Normal authentication only via Join-Path $HOME .codex/.env; excluded from evidence',
    limits=LIMITS,numerical_limits=dict(local_solves=6,prediction_evaluations=8),backend_stepping_replay=0,
    protocol_corrections=dict(max_total=4,max_consecutive=2),workers_subagents=0,local_commit=True,push=False)


class Workflow(DiagnosticWorkflow):
    limits=LIMITS
    numerical_limits=dict(local_solves=6,prediction_evaluations=8)
    tools={'design.respond_diagnosis':'4.0.0','evidence.read':'1.0.0'}


def sealed_state(store):
    with store.connect(True) as db:ids=[r[0] for r in db.execute('SELECT run_id FROM sessions')]
    return dict(usage=store.remaining(),states={i:digest(store.session(i)['state']) for i in ids})


def assert_previous(w):
    link=w.freeze['predecessor']
    assert sealed_state(Store(previous.RUN))==link['state']
    for p,sha in link['files'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha,p


def prepare():
    old=previous.restore();reader=ControlEvidence(Store(previous.predecessor.RUN));source=reader.resolve(previous.INCUMBENT)
    cfg=deepcopy(old.freeze['experiment']);cfg.update(source_store=str(previous.predecessor.RUN),execution_id=previous.INCUMBENT,
        source_manifest=source['manifest'],evidence_directory=str(EVIDENCE),project_prefix='gvs-milestone5-diagnostic',
        authorization_source=json.dumps(AUTHORIZATION),provider_freeze=str(previous.RUN/'freeze.json'))
    if (RUN/'freeze.json').exists():
        frozen=read(RUN/'freeze.json')
        if 'predecessor' in frozen:raise ValueError('PREPARATION_ALREADY_COMPLETED')
        w=Workflow(RUN,'single_context',experiment=frozen['experiment']);w.freeze=frozen;w.project=frozen['project_id']
        w.hosts={k:Host(RUN,v) for k,v in frozen['hosts'].items()}
        for attr,key in [('binding','binding'),('identities','identities'),('summary','summary'),('inventory','inventory'),('inventory_ref','inventory_reference')]:setattr(w,attr,frozen[key])
        atomic_json(RUN/'preparation_recovery.json',dict(error='Historical artifact-shaped selector contained nested identity; old recursive helper treated it as EvidenceRef.',
            recovery='Typed reference check; reuse existing stage, source summary receipt and grant; no reset or repeated calculation.',provider_attempts=0,numerical_attempts=0))
    else:
        w=Workflow(RUN,'single_context',experiment=cfg);w.prepare(require_softagent_runtime())
    refs={}
    seen=set()
    def copy(value):
        if isinstance(value,dict):
            if set(value)=={'artifact_id','media_type'} and isinstance(value['artifact_id'],str) and isinstance(value['media_type'],str):
                if value['artifact_id'] in seen:return
                seen.add(value['artifact_id']);body=old.store.artifact(value,raw=True)
                with w.store.transaction() as db:assert plain(w.store.put(db,body,value['media_type']))==value
                if value['media_type']=='application/json':copy(json.loads(body))
            else:
                for child in value.values():copy(child)
        elif isinstance(value,list):
            for child in value:copy(child)
    for name in ('revised_report','prediction_numerical','forecast_seal','final_response','prediction_assessment'):
        copy(old.chain[name]);refs[name]=old.chain[name]
    w.chain={};w.freeze.update(authorization=AUTHORIZATION,predecessor=dict(store=str(previous.RUN),state=sealed_state(old.store),
        files={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in previous.EVIDENCE.rglob('*') if p.is_file()}),
        predecessor_refs=refs,incumbent=old.incumbent,original_baseline=old.retained_baseline,
        primary_reference=old.incumbent['candidate'],latest_tested=old.latest_tested,
        selected_deliverable=old.incumbent['candidate'],development_executions=EXECUTIONS,
        original_reference=next(r['facts']['candidate'] for r in old.historical_results if r['facts']['execution_id']==previous.DEVELOPMENT[0]))
    bindings=[import_execution(ControlEvidence(old.store),e,w.store,w.hosts['executor'].run_id) for e in EXECUTIONS]
    protocol=read(previous.RUN/'prediction_protocol.json');protocol_ref=save(w.store,protocol)
    w.freeze['diagnostic_protocol']=save(w.store,dict(bindings=bindings,incumbent_binding=w.binding,numerical=refs['prediction_numerical'],preview_protocol=protocol_ref))
    atomic_json(RUN/'authorization.json',AUTHORIZATION);atomic_json(RUN/'freeze.json',w.freeze);atomic_json(RUN/'chain.json',w.chain)
    return w


def restore():
    frozen=read(RUN/'freeze.json');w=Workflow(RUN,'single_context',experiment=frozen['experiment']);w.freeze=frozen
    w.project=frozen['project_id'];w.hosts={k:Host(RUN,v) for k,v in frozen['hosts'].items()};w.binding=frozen['binding'];w.identities=frozen['identities']
    w.summary=frozen['summary'];w.inventory=frozen['inventory'];w.inventory_ref=frozen['inventory_reference'];w.chain=read(RUN/'chain.json')
    return w


def calculate(w,operation):
    receipt_path=RUN/(operation+'_receipt.json')
    if receipt_path.exists():
        receipt=read(receipt_path)
        if receipt['execution_status']!='completed':raise ValueError('FAILED_NUMERICAL_ATTEMPT_REQUIRES_REVIEW')
        w.chain[operation]=receipt['output'];return
    reg=registry();reg.add(DEFINITION)
    inp=deepcopy(w.store.session(w.hosts['executor'].run_id)['snapshot']['input']);run_id=w.project+'-'+operation
    inp['run_id']=run_id;inp['policy'].update(tool_bindings={DEFINITION.extension_id:DEFINITION.version},allowed_tools=[],timeout_s=600.,
        operation_allowances={DEFINITION.extension_id:dict(timeout_s=600.,reserve_s=600.)})
    host=Host(RUN,run_id,reg=reg);host.create(inp);host.resume();w.hosts[operation]=host
    w.freeze['hosts'][operation]=run_id;atomic_json(RUN/'freeze.json',w.freeze)
    protocol={**w.store.artifact(w.freeze['diagnostic_protocol']), 'operation':operation}
    receipt=host.invoke(dict(request_id='saved-'+operation,tool_id=DEFINITION.extension_id,tool_version=DEFINITION.version,
        arguments=dict(protocol=save(w.store,protocol)),reason='Authorized saved-evidence diagnosis; zero backend steps, zero controller weight experiments.',cache='new'))
    atomic_json(receipt_path,receipt)
    if receipt['execution_status']!='completed':raise ValueError(str(receipt.get('error')))
    w.chain[operation]=receipt['output'];atomic_json(RUN/(operation+'.json'),w.store.artifact(receipt['output'])['detail']);atomic_json(RUN/'chain.json',w.chain)


def compact(w):
    rows=w.store.artifact(w.chain['intervals'])['detail']['result'];preview=w.store.artifact(w.chain['preview'])['detail']['result']
    intervals=[]
    for r in rows:
        item={k:v for k,v in r.items() if k not in ('files','integration','state')}
        item['integration']=[{k:v for k,v in row.items() if k!='trajectory'} for row in r['integration']]
        intervals.append(item)
    production=[{k:v for k,v in r.items() if k!='state'} for r in preview['production']]
    packet=dict(evidence_type='current retrospective diagnostic calculation; .075/.15 are development data',
        intervals=intervals,preview={**preview,'production':production},
        predecessor_results=dict(local_direction_correct=4,local_numerical_pass=0,full_task_resolved=0,full_task_unresolved=4,ordering='abstained',accuracy_among_resolved=None,immutable=True),
        original_baseline=w.freeze['original_baseline']['candidate'],primary_reference=w.freeze['primary_reference'],
        passing_pre_adaptation_reference=w.freeze['original_reference'],latest_tested=w.freeze['latest_tested'],selected_deliverable=w.freeze['selected_deliverable'],
        incumbent=w.freeze['incumbent'],authorization=AUTHORIZATION,remaining=w.store.remaining()['remaining'],
        prior_costs=dict(preview_s=73.31299999984913,two_full_evaluations_s=605.936999999918),
        choices=dict(A='Improve local prediction integration if numerical error materially contributes.',B='Specific defect repair only if identified; otherwise targeted investigation.',
            C='Candidate-specific generated history preview only if supported; cannot use unseen future backend state.',D='Retain local diagnosis only and defer run-ahead screening.'),
        next_validation='Prepare only; no execution. Independent evidence required; .075/.15 cannot be fresh validation.',milestone4='closed',milestone5='open')
    ref=save(w.store,packet);atomic_json(RUN/'diagnostic_handoff.json',packet);return packet,ref


def interpret(w):
    if 'final_response' in w.chain:return
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
    for key in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):
        if '127.0.0.1:9' in os.environ.get(key,''):os.environ.pop(key)
    packet,ref=compact(w);host=w.host('design');report=w.freeze['predecessor_refs']['revised_report']
    instruction='''Interpret current compact diagnostic evidence yourself. Choose exactly ONE primary A/B/C/D action and narrowest supported role; say it explicitly in reasoning. Quantify coarse production reproduction, initial/vector/change errors, refinement contributions, fine-step differences and unresolved causes. Do not call a speed-norm match a vector match or claim convergence from a single finer value. Explain the .30 settled-seed thresholds, feasibility, weight-independent checks and iteration zero acceptance. Production history,state,input,solver paths also differ; historical warm plans absent. No broad causal claim, promotion or new experiment. Retain exact incumbent batch-ebbeadbdaca10732-0 execution 91c3ba1b01d6499fb26df8f95409401b; selected_candidate=baseline, candidate_disposition=retain_baseline. disposition=defer,recommendation_id=null. next_action=finish,next_research.route=stop and zero proposed_budget: this grant stops. In reasoning propose ONE precise future falsification/validation protocol, clearly unexecuted, with independent data, quantity/scope, direction/error/order/abstention/threshold-crossing reporting, cost and bounded proposed future budget. This future budget is prose only and separate from zero operational next_research budget. Distinguish sealed prior prospective results from development and retrospective calculations. M4 closed,M5 open. Preserve 1e-4 m/s numerical reporting tolerance and real-time acceptance. About 650 words.'''
    configure_role(host,'design',instruction,phase='response_final',memory_identity=host.run_id,native_store_root=str(RUN),
        binding=w.binding,identities=w.identities,report=report,report_content=w.store.artifact(report),final_response=True,
        phase_budget=dict(limit=LIMITS),phase_tools=['design.respond_diagnosis'],delivery_tool='design.respond_diagnosis',
        native_fixed={'design.respond_diagnosis':dict(report=report)},decision_packet=packet,decision_packet_reference=ref,
        improvement_feedback_content=dict(baseline_facts=w.freeze['incumbent'],execution=None),
        check_feedback=[dict(reference=w.chain['intervals'])],require_research_route=True,require_research_budget=True)
    payload=payload_for(host,EvidenceDrivenAdapter());atomic_json(RUN/'final_serialized_handoff.json',payload)
    assert json.dumps(AUTHORIZATION,sort_keys=True) in json.dumps(json.loads(payload['messages'][1]['content']),sort_keys=True)
    atomic_json(RUN/'provider_attempt_guard.json',dict(authorization=AUTHORIZATION,previous_usage=w.store.remaining()['used']))
    w.chain['final_response']=run_until_handoff(host,'design_response');atomic_json(RUN/'final_response.json',w.store.artifact(w.chain['final_response']));atomic_json(RUN/'chain.json',w.chain)


def export(w,status,reason):
    assert_previous(w)
    DiagnosticWorkflow.export(w,status,reason,0.)
    used=w.store.remaining()['used'];old=read(previous.EVIDENCE/'delivery.json')['accounting']['cumulative']
    with w.store.connect(True) as db:
        calls=list(db.execute('SELECT charged FROM calls WHERE charged IS NOT NULL'));work=json.loads(db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone()[0])
    sums={k:sum(json.loads(r[0])[k] for r in calls) for k in LIMITS};assert sums==used
    corrections=max(w.store.session(h.run_id)['state'].get('protocol_corrections_used',0) for h in w.hosts.values())
    accounting=dict(old=old,new=used,cumulative={k:old[k]+used[k] for k in old},stage_limits=LIMITS,receipt_charge_sum=sums,numerical_work=work,
        cumulative_numerical_work=dict(local_solves=9+work['used']['local_solves'],prediction_evaluations=9+work['used']['prediction_evaluations'],embedded_controller_updates=210),
        corrections=dict(old=6,new=corrections,cumulative=6+corrections),semantic_corrections=dict(old=5,new=0,cumulative=5),occupied=w.store.remaining()['occupied'])
    atomic_json(EVIDENCE/'accounting.json',accounting)
    atomic_json(EVIDENCE/'delivery.json',dict(status=status,reason=reason,predecessor_preserved=True,milestone4_closed=True,milestone5_complete=False,
        selected_deliverable=w.freeze['selected_deliverable'],primary_reference=w.freeze['primary_reference'],latest_tested=w.freeze['latest_tested'],
        original_baseline=w.freeze['original_baseline']['candidate'],passing_pre_adaptation_reference=w.freeze['original_reference'],
        accounting=accounting,authorization=AUTHORIZATION,final_response=w.chain.get('final_response'),next_validation_executed=False,
        backend_stepping_replay=0,no_workers=True,no_subagents=True,pushed=False))


def main():
    ready=(RUN/'freeze.json').exists() and 'predecessor' in read(RUN/'freeze.json')
    w=restore() if ready else prepare();assert_previous(w)
    try:
        if '--prepare' not in sys.argv:
            calculate(w,'intervals');calculate(w,'preview')
            if '--calculate' not in sys.argv:interpret(w)
        export(w,'completed' if 'final_response' in w.chain else 'diagnostics_prepared','Saved-evidence diagnostic stage; no future protocol executed.')
    except Exception as exc:
        atomic_json(RUN/'stage_failure.json',dict(type=type(exc).__name__,message=str(exc)));export(w,'incomplete',str(exc));raise


if __name__=='__main__':main()
