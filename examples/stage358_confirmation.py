"""One separately granted Milestone 3 confirmation; historical runs are read only."""
import argparse
from contextlib import closing
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from examples import stage357_live_pilot as prior
from examples.stage356_milestone2 import scientific_bundle,import_common,HISTORY,BASELINE
from tools.diagnostic_workflow import implementation,save
from tools.platform_store import Store,plain
from tools.state_io import read,atomic_json,digest
from tools.diagnostic_facts import handover
from tools.diagnostic_summary import update_facts
from tools.platform_search import prepare_offline_batch,run_live_batch,offline_batch_result
from tools.live_batch_execution import verified_historical_result
from tools.platform_diagnosis_coordinator import configure_role
from tools.runtime_identity import require_softagent_runtime
from extensions.tendon_family.control_evidence import ControlEvidence

EVIDENCE=ROOT/'evidence/stage358_confirmation_20261004'
RUN=ROOT/'runs/stage358_confirmation_20261004/single_context'
PILOT=prior.RUN
PILOT_EVIDENCE=ROOT/'evidence/stage357_pilot_20261004'
SOURCES=(('retained_baseline',BASELINE,'cf997605885642759ee33920e2c9e2ef'),
    ('historical_start',HISTORY,'087adee8e8a24fe88e5c85fe89e638c8'),
    ('historical_candidate',PILOT,'25e26708480848d79bad378b669915e3'))
REVIEW_REASONS={
    'schemas/platform.py':'Optional provider context guard and per-operation reservations; physical contracts unchanged.',
    'tools/platform_host.py':'Per-operation reservations/timeouts, sealed accounting, working-state presentation; no physical equations changed.',
    'tools/platform_store.py':'Operation/phase ledger accounting and protected capacity; sealed source result bytes unchanged.',
    'tools/platform_tools.py':'Use the invocation timeout rather than global timeout; completed source results are retained.',
    'tools/platform_search.py':'Ask/tell scheduling, physical feedback, explicit verified reuse and duplicate normalization; execution/controller equations unchanged.',
    'extensions/tendon_family/gvs_reporting.py':'Receipt resolution and imported-manifest fallback; metric calculation and evaluator remain unchanged.'}


class ConfirmationWorkflow(prior.PilotWorkflow):
    instructions={**prior.PilotWorkflow.instructions,
        'improvement':prior.PilotWorkflow.instructions['improvement']+
            ' This is Stage 3.58 under a NEW separate grant linked to the stopped Stage 3.57 pilot. Author a new plan, explicitly link the predecessor plan in rationale, and incorporate the supplied complete 0.30/0 result. Its lower speed with worse positions and lost reach weakens reach-preserving improvement at that tested point, not the entire range. All THREE permitted complete historical configurations are verified reusable, including 0.30/0. Do not repeat known points expecting new evidence. The optimizer selects individual points. Hypothesis, weakening observations, domains/step, fixed conditions, physical objectives, caps and target, reserve/stop rules and limitations must be explicit. Max proposals <=6, max_backend_attempts <=3, target_changed_configurations exactly 2. Plan budget cannot exceed the grant.',
        'response_final':prior.PilotWorkflow.instructions['response_final']+
            ' Required next_research selects ONE route: continue_weight_combinations, initialization_selection, prediction_backend_disagreement, holding_control_arrangements, or a justified defer. State unresolved_question, evidence, bounded_check, fixed_conditions, proposed_variables, expected_observations with what each supports/weakens, proposed_budget (model_calls/tool_calls/backend_solves/worker_calls/wall_s), stopping_conditions, and limitations. This is a proposed next-stage check only; execute nothing. Explain the effect on the CURRENT plan hypothesis and address EVERY newly tested point with both references. The prior interrupted attempt STARTED and has no sealed complete result. Zero force violation does not exclude near-bound loading; near-bound loading alone establishes no cause. Archived dual queried coverage is eight updates, distinct from handoffs. Source-bound numbers in the batch summary are the factual authority. Lower guidance score cannot promote a candidate. Recommendation disposition, candidate disposition and next research action are separate.'}

    def export(self,status,reason,elapsed):
        # Include the real candidate child sessions, not only the model hosts.
        state=self.store.session(self.host('design').run_id)['state']
        from tools.platform_host import Host
        for row in state.get('search_batch',{}).get('configurations',{}).values():
            if not row['reused']:
                try:self.store.session(row['candidate_id'])
                except ValueError:continue
                self.hosts['candidate_'+row['candidate_id']]=Host(self.directory,row['candidate_id'])
        super().export(status,reason,elapsed)
        outcome=read(self.directory/'outcome.json')
        batch=offline_batch_result(self.host('design')) if state.get('search_batch') else None
        outcome['classification']='One separately granted engineering confirmation; predecessor results and costs retained.'
        outcome['physical_improvement']=dict(evaluated=batch is not None,new_complete_configurations=(batch or {}).get('fully_evaluated_distinct_changed_configurations',0),
            comparisons='See source-bound batch result; workflow completion does not require physical improvement.')
        outcome['confirmation_grant_links']=self.freeze['confirmation_grant_links']
        atomic_json(self.directory/'outcome.json',outcome)
        atomic_json(self.export_root/self.directory.name/'outcome.json',outcome)


def reviewed_changes():
    """Pin reviewed nonphysical migrations to exact old/new file hashes."""
    record={p:dict(reason=reason,current_hash=hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),historical_hashes=[])
        for p,reason in REVIEW_REASONS.items()}
    for _,path,eid in SOURCES:
        store=Store(path);source=ControlEvidence(store).resolve(eid)
        for dep in store.session(source['owner'])['snapshot']['dependencies'].values():
            for p in record:
                if p in dep['sources'] and dep['sources'][p] not in record[p]['historical_hashes']:
                    record[p]['historical_hashes'].append(dep['sources'][p])
    return record


def prepare():
    bundle=scientific_bundle();runtime=require_softagent_runtime()
    config=deepcopy(read(prior.CONFIRM/'freeze.json')['experiment'])
    config.update(evidence_directory=str(EVIDENCE),project_prefix='gvs-stage358',
        authorization_source='Current explicit user authorization: ONE separately linked Stage 3.58 Milestone 3 confirmation; repository evidence transmission to https://api.deepseek.com via existing credential loader; 16 provider attempts/60 workflow tools/7200 charged seconds/6 optimizer proposals/3 backend attempts/zero workers. Two distinct NEW complete changed configurations. No probes, baseline reruns, screening, replacement campaigns or push.')
    workflow=ConfirmationWorkflow(RUN,'single_context',experiment=config)
    workflow.prepare(runtime);import_common(workflow,bundle);prior.import_confirmation(workflow)
    review=read(EVIDENCE/'compatibility_review.json')
    historical=[verified_historical_result(workflow.host('design'),Store(path),eid,role,review) for role,path,eid in SOURCES]
    workflow.historical_results=historical
    feedback=workflow.historical_feedback
    if historical[0]['facts']!=feedback['baseline_facts'] or historical[1]['facts']!=feedback['execution']['factual_result']:
        raise ValueError('VERIFIED_REFERENCE_FACTS_CHANGED')
    old_batch=read(PILOT/'batch_result.json');outcome=read(PILOT/'outcome.json')
    audit=prior.archived_audit()
    audit.update(prior_batch=dict(plan=read(PILOT/'chain.json')['search_plan'],accounting=old_batch['accounting'],
        fully_evaluated_distinct_changed_configurations=old_batch['fully_evaluated_distinct_changed_configurations'],
        status=outcome['status'],stop_reason=outcome['stop_reason'],usage=outcome['usage'],
        scheduler_failure=read(PILOT_EVIDENCE/'scheduler_failure.json'),decision=read(PILOT/'final_response.json')),
        interpretation_corrections=read(PILOT_EVIDENCE/'model_decision_audit.json')['corrections'],
        historical_results=[dict(role=r['role'],source_store=r['source_store'],execution_id=r['execution_id'],facts=r['facts']) for r in historical],
        prior_candidate_update_facts=update_facts(ControlEvidence(Store(PILOT)),ControlEvidence(Store(PILOT)).resolve(SOURCES[2][2])),
        reference_policy='Keep retained baseline and historical search start as separate fixed comparisons; prior candidate is additional evidence only.',
        scientific_scope='Only the two declared weights may vary. Retained failures and their costs are immutable. No claim of organizational superiority.')
    ref=save(workflow.store,audit)
    handover(workflow.host('design'),ref,audit,origin=dict(kind='verified_prior_results_and_factual_audits'),kind='confirmation_starting_evidence')
    links=dict(predecessor_milestone2_gate=str(prior.GATE),predecessor_pilot=str(PILOT_EVIDENCE),
        predecessor_pilot_usage=outcome['usage'],unusable_interrupted_execution='d06d23180c19424faf5ac6618c779173',
        predecessor_unresolved_reservation_s=900.,budgets_transferred=False,current_authorization=config['authorization_source'])
    workflow.freeze.update(confirmation_grant_links=links,current_factual_audit=ref,historical_results=historical,
        confirmation_limits=dict(proposals=6,backend_attempts=3,target_changed_configurations=2,
            reservation_s=dict(simulation=900,evaluation=30,profile=60,delivery=600)),compatibility_review=review)
    workflow.validate_frozen_configuration()
    atomic_json(RUN/'freeze.json',workflow.freeze);atomic_json(EVIDENCE/'factual_audit.json',audit)
    atomic_json(EVIDENCE/'grant_links.json',links)
    return workflow


def compact_summary(workflow,result):
    candidates=[]
    for row in result['candidates']:
        execution=row.get('execution');history=row.get('historical_source')
        facts=execution['factual_result'] if execution else history['facts'] if history else None
        candidates.append(dict(candidate_id=row['candidate_id'],changes=row['changes'],configuration=row['configuration'],
            reused=row['reused'],source_execution_id=facts['execution_id'] if facts else None,
            stages={k:{f:v for f,v in s.items() if f in ('execution_status','execution_id','charged','output','error')} for k,s in row['stages'].items()},
            feedback=row.get('feedback'),retained_baseline_comparison=row.get('retained_baseline_comparison'),
            execution=dict(factual_result=facts) if facts else None))
    current_facts=[]
    for row in result['candidates']:
        if not row['reused'] and row.get('execution'):
            reader=ControlEvidence(workflow.store);source=reader.resolve(row['execution']['execution_id'])
            current_facts.append(update_facts(reader,source))
    with closing(workflow.store.connect(True)) as db:
        unresolved=[dict(run_id=r['run_id'],request_id=r['request_id'],execution_id=r['execution_id'],reservation=json.loads(r['charged']))
            for r in db.execute('SELECT run_id,request_id,execution_id,charged FROM calls WHERE receipt IS NULL')]
    return dict(contract=result['contract'],version=result['version'],mode=result['mode'],plan=result['plan'],
        batch_id=result['batch_id'],status=result['status'],stop_reason=result['stop_reason'],pending=result['pending'],
        proposals=result['proposals'],candidates=candidates,accounting=result['accounting'],
        completed_evaluations=result['completed_evaluations'],completed_profiles=result['completed_profiles'],
        fully_evaluated_distinct_changed_configurations=result['fully_evaluated_distinct_changed_configurations'],
        plan_hypothesis=workflow.store.artifact(result['plan'])['plan']['hypothesis'],
        retained_references=[dict(role=r['role'],execution_id=r['execution_id'],facts=r['facts']) for r in workflow.historical_results],
        current_update_facts=current_facts,current_project_usage=workflow.store.remaining(),unresolved_current_reservations=unresolved,
        historical_cost_links=workflow.freeze['confirmation_grant_links'],
        interpretation_limits=['Tested points only; full guidance vector and both comparisons govern interpretation.',
            'Zero force violation does not exclude operation at the limit; proximity alone identifies no cause.',
            'The prior interrupted attempt started with partial work; it is excluded from complete physical evidence.',
            'Initialization selections apply control; synchronous wall overruns are distinct from simulated delays.'])


def verify(names):
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    atomic_json(EVIDENCE/'compatibility_review.json',reviewed_changes())
    with patch.object(prior,'EVIDENCE',EVIDENCE):prior.verify(names)


def live():
    checked=read(EVIDENCE/'verification_current.json')
    if not checked['passed'] or checked['implementation']['files']!=implementation()['files']:raise ValueError('CURRENT_VERIFICATION_REQUIRED')
    if subprocess.check_output(['git','diff','HEAD','--',*implementation()['files']],cwd=ROOT,text=True):raise ValueError('COMMIT_BEFORE_CONFIRMATION')
    if RUN.exists() or (EVIDENCE/'acceptance.json').exists():raise ValueError('PRESERVE_PRIOR_CONFIRMATION_NO_REPLACEMENT_GRANT')
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path.home()/'.codex/.env')
    removed=[]
    for name in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):
        if '127.0.0.1:9' in os.environ.get(name,''):os.environ.pop(name);removed.append(name)
    workflow=prepare();started=time.monotonic();status='incomplete';reason=None;result=None
    atomic_json(RUN/'live_attempt.json',dict(implementation=implementation(),tls_verification=True,removed_dead_proxy_variable_names=removed))
    try:
        workflow.phase('improvement','search_batch_plan','search_plan',predecessor_plan=read(PILOT/'chain.json')['search_plan'],
            factual_audit=workflow.store.artifact(workflow.freeze['current_factual_audit']))
        host=workflow.host('design');plan=workflow.store.artifact(workflow.chain['search_plan'])['plan']
        if (plan['max_candidates']>6 or plan['max_backend_attempts'] is None or plan['max_backend_attempts']>3
                or plan['target_changed_configurations']!=2 or any(plan['planned_budget'][k]>v for k,v in workflow.limits.items())):
            raise ValueError('PLAN_EXCEEDS_CONFIRMATION_GRANT_OR_TARGET')
        if implementation()!=workflow.freeze['implementation']:raise ValueError('FROZEN_IMPLEMENTATION_CHANGED')
        workflow.validate_frozen_configuration()
        configure_role(host,'executor','Execute this current accepted bounded plan only.',phase_budget={});host.resume()
        feedback=workflow.historical_feedback
        prepare_offline_batch(host,workflow.chain['search_plan'],mode='live',starting_facts=feedback['execution']['factual_result'],
            retained_baseline=feedback['baseline_facts'],historical_results=workflow.historical_results)
        atomic_json(RUN/'bound_batch.json',host.store.session(host.run_id)['state']['search_batch'])
        print('BATCH starting; target two new complete changed configurations',flush=True)
        result=run_live_batch(host);raw_ref=save(workflow.store,result);workflow.chain['batch_result']=raw_ref
        atomic_json(RUN/'batch_result.json',result)
        summary=compact_summary(workflow,result);ref=save(workflow.store,summary);workflow.chain['batch_summary']=ref
        atomic_json(RUN/'batch_summary.json',summary)
        handover(host,ref,summary,origin=dict(kind='sealed_live_confirmation',full_result=raw_ref),kind='batch_result')
        workflow.phase('response_final','design_response','final_response',batch_result=summary,experiment_plan=workflow.chain['search_plan'],
            improvement_feedback_content=dict(baseline_facts=feedback['baseline_facts'],execution=None),check_feedback=[dict(reference=ref)],
            require_research_route=True,source_report=workflow.common['source_report'],source_record=workflow.source_record)
        target=result['fully_evaluated_distinct_changed_configurations']==2
        status='completed' if target and result['stop_reason']=='pilot_target_complete' else 'incomplete';reason=result['stop_reason']
    except Exception as exc:
        reason=str(exc);atomic_json(RUN/'workflow_failure.json',dict(type=type(exc).__name__,message=reason));print('STOP',reason,flush=True)
        state=workflow.store.session(workflow.host('design').run_id)['state']
        if state.get('search_batch'):
            result=offline_batch_result(workflow.host('design'));atomic_json(RUN/'batch_result_at_failure.json',result)
    workflow.export(status,reason,time.monotonic()-started)
    from tools.improvement_workflow import archive_store
    archive_store(workflow.store,EVIDENCE/'single_context',source_stores=[prior.CONFIRM,HISTORY,BASELINE,PILOT])
    atomic_json(EVIDENCE/'acceptance.json',dict(passed=status=='completed',stop_reason=reason,
        current_model_plan_present='search_plan' in workflow.chain,model_consumed_batch='final_response' in workflow.chain,
        target=2,completed_new_configurations=(result or {}).get('fully_evaluated_distinct_changed_configurations',0),
        implementation=implementation(),offline_verification=str(EVIDENCE/'verification_current.json')))
    print('CONFIRMATION',status,reason,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['verify','live']);parser.add_argument('tests',nargs='*');args=parser.parse_args()
    if args.action=='verify':verify(args.tests)
    else:live()
