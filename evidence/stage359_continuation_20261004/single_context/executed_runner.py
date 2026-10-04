"""One bounded continuation; immutable model plan and shared receipt executor."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from examples import stage359_continuation as preparation
from examples import stage358_confirmation as previous
from examples import stage358_interpretation_repair as repair
from tools.platform_store import Store,plain
from tools.state_io import read,atomic_json
from tools.diagnostic_workflow import save,implementation
from tools.diagnostic_facts import handover
from tools.platform_diagnosis_coordinator import configure_role
from tools.platform_search import prepare_offline_batch,run_live_batch,offline_batch_result
from tools.platform_models import payload_for
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from tools.settling_campaign import campaign_metrics,compare_results
from extensions.tendon_family.control_evidence import ControlEvidence

RUN=ROOT/'runs/stage359_continuation_20261004/single_context'
EVIDENCE=preparation.EVIDENCE
PLAN_INSTRUCTIONS='''Author a NEW immutable SearchBatchPlan, linked in rationale to predecessor_decision and predecessor_plan, under the separate unused Stage 3.59 grant (8 provider,20 tools,4200 s,4 proposals including starts/duplicates,2 new backends,0 workers/local solves/prediction evaluations). Follow the accepted model decision: Route A terminal weight varies, holding stays zero, immediate predecessor 0/0.05, retained baseline 0/0. The justified one-point 0.10 check is acceptable: choose and justify the intended complete new result count before launch; do not force two.
For exact points use search.family_explicit@1.0.0 with candidates=[{full varied builder path: exact value}], max_candidates equal list length, step=null. Feedback ranks results but NEVER changes this ordered sequence. Initial source value is 0.05 and domain bounds must contain it and every point. For coordinate search instead use search.family_coordinate@1.0.0, candidates=null, actual domain/start/normalized step and feedback behavior; first proposal is the known start and later points follow clipped +/- steps about best score, not prose values.
Only control/recipe/terminal_tip_speed_weight may vary, zero or >=0.0001 through 1. Fixed holding=0. Keep robot,material,task,evaluator,controller.gvs_nmpc@7.0.0,timing,solver budget,horizon and initialization/warm-start policy unchanged. This is a complete backend run using the Task initializer, not a saved-state local check. All five supplied completed records remain references; only identical fixed science AND exact proposed execution scope may reuse a result. No unknown replay.
Use bare fixed_conditions robot,task,acceptance,controller_implementation,other_numerical_settings. objectives joint_reach_holding_acceptance,terminal_error_m,holding_max_error_m,holding_max_speed_m_s. constraints frozen_acceptance,force_bounds,finite_valid_execution. verification candidate.apply,simulation.run,evaluation.run,control.profile_report,bound_comparison,diagnostic_revision. Evidence is current F aliases including a performed-check result alias. State hypothesis, weakening observations, scientific promise, rationale and tested-point fidelity limits. No paid queries or new diagnostics.
Use max_backend_attempts and target_changed_configurations explicitly. planned_budget includes planning/recovery/execution/interpretation/delivery: one backend requires >=990 s reservations (900 simulation,30 evaluation,60 profile) PLUS >=600 s interpretation capacity and planning costs; at least 4 provider and 4 tool slots remain before execution. The predecessor's advisory 1200 s allocation is insufficient as a total workflow budget; choose a coherent total within 4200/8/20. Operational plan checks require model_calls>=5, tool_calls>=4*max_backend_attempts+7, wall_s>=990*max_backend_attempts+600, backend_solves=max_backend_attempts and workers=0. Budgeting the entire separate 8/20/4200 grant is permitted; no need to minimize declared capacity. Full new results each cost 4 execution tools. Stop normally at target count, otherwise finite proposal limit; stop on material failure/unknown or insufficient delivery capacity. No mid-run early reach stop exists; acceptance is checked after complete evaluation/profile. Do not claim any physical improvement from plan submission. Keep concise.'''
FINAL_INSTRUCTIONS='''Use decision_packet numerical facts to interpret EVERY completed new result against BOTH retained baseline and immediate predecessor. About 350 words across prose fields; cite rows instead of copying all numbers. Address the hypothesis with supported/weakened/untested qualifications, movement versus acceptance, tested-point scope, independent recommendation disposition and candidate decision. next_action=finish. selected_candidate is baseline, none, or exact completed candidate_id. Propose EXACTLY ONE next_research route with question,evidence,bounded_check,explicit varied paths/values,fixed conditions,supporting/weakening observations,coherent proposed budget and stopping conditions. Execute nothing further. No causal,continuous-time,global,real-time or hardware claim. Small one-step position error does not certify holding-speed prediction. Late horizon shortening alone identifies no cause. Program facts and named candidate-minus-reference differences are authoritative; any stated numeric approximation must agree. Omitted unrelated historical details do not fail a concise decision.'''


class ContinuationWorkflow(previous.ConfirmationWorkflow):
    limits=preparation.GRANT
    phases={**previous.ConfirmationWorkflow.phases,
        'improvement':dict(limit=dict(model_calls=4),protect_project=dict(model_calls=4,tool_calls=8,wall_s=1590.)),
        'response_final':dict(limit=dict(model_calls=4))}
    instructions={**previous.ConfirmationWorkflow.instructions,'improvement':PLAN_INSTRUCTIONS,'response_final':FINAL_INSTRUCTIONS}

    def check_provider_payload(self,host):
        payload=payload_for(host,EvidenceDrivenAdapter())
        view=json.loads(payload['messages'][1]['content'])['role_context']
        phase=view['phase'];raw=json.dumps(payload,ensure_ascii=False).encode()
        assert view['instructions']
        if phase=='response_final':
            assert view['decision_packet']==host.store.session(host.run_id)['state']['role_context']['decision_packet']
            assert 'reference_view' not in view and len(raw)<40000
        else:assert len(raw)<400000
        atomic_json(self.directory/(phase+'_provider_payload_offline.json'),payload)
        atomic_json(self.directory/(phase+'_payload_check.json'),dict(passed=True,payload_bytes=len(raw),required_instructions_direct=True,max_tokens=payload['max_tokens']))


def copy_reference(target,source,ref,seen=None):
    seen=set() if seen is None else seen
    sources=[target,source,Store(previous.prior.CONFIRM),*[Store(p) for _,p,_ in preparation.SOURCES]]
    def visit(value):
        if isinstance(value,dict):
            if set(value)=={'artifact_id','media_type'}:
                if value['artifact_id'] in seen:return
                seen.add(value['artifact_id'])
                for available in sources:
                    with available.connect(True) as db:
                        exists=db.execute('SELECT 1 FROM artifacts WHERE id=?',(value['artifact_id'],)).fetchone()
                    if exists:
                        body=available.artifact(value,raw=True);break
                else:raise ValueError('CONTINUATION_LINKED_ARTIFACT_UNAVAILABLE: '+value['artifact_id'])
                with target.transaction() as db:
                    assert plain(target.put(db,body,value['media_type']))==value
                if value['media_type']=='application/json':visit(json.loads(body))
            else:
                for v in value.values():visit(v)
        elif isinstance(value,list):
            for v in value:visit(v)
    visit(ref)


def prepare(directory=RUN,evidence=EVIDENCE):
    preparation.require_interpretation_gate()
    from tools.runtime_identity import require_softagent_runtime
    from examples.stage356_milestone2 import scientific_bundle,import_common
    runtime=require_softagent_runtime()
    source=ControlEvidence(Store(previous.RUN)).resolve(preparation.SOURCES[-1][2])
    config=deepcopy(read(previous.RUN/'freeze.json')['experiment'])
    config.update(source_store=str(previous.RUN),execution_id=source['execution_id'] if 'execution_id' in source else preparation.SOURCES[-1][2],
        source_manifest=source['manifest'],evidence_directory=str(evidence),project_prefix='gvs-stage359',
        authorization_source='User explicitly authorizes ONE Stage 3.59 cross-batch single-variable continuation after accepted Stage 3.58 interpretation: 8 provider/20 workflow tools/4200 charged s/4 proposals/2 new backend attempts/zero workers/local solves/prediction evaluations; necessary evidence/configuration transfer to https://api.deepseek.com; no push or replacement campaign.')
    w=ContinuationWorkflow(directory,'single_context',experiment=config)
    w.prepare(runtime);import_common(w,scientific_bundle());previous.prior.import_confirmation(w)
    history,review=preparation.import_references(w.host('design'));w.historical_results=history
    old_batch=read(previous.RUN/'batch_result.json')
    execution=next(r['execution'] for r in old_batch['candidates'] if r.get('execution_id')==preparation.SOURCES[-1][2])
    w.historical_feedback=dict(baseline_facts=history[0]['facts'],execution=execution,
        comparison=compare_results(history[0]['facts'],history[-1]['facts']))
    current_feedback=save(w.store,w.historical_feedback)
    w.common=deepcopy(w.common);w.common.update(feedback=current_feedback,subject=history[-1]['facts']['candidate'])
    decision=read(previous.RUN/'superseding_interpretation.json')
    copy_reference(w.store,Store(previous.RUN),decision)
    packet=read(repair.EVIDENCE/'decision_packet.json')
    planning=dict(configurations=packet['configurations'],comparisons=packet['comparisons'],diagnostics=packet['diagnostics'],
        predecessor_decision=decision['response'],accepted_interpretation=w.store.artifact(decision['response']),
        predecessor_review=w.store.artifact(decision['review']),scope=packet['current_scope'],
        operation_reservations_s=dict(simulation=900,evaluation=30,profile=60),interpretation_reserve_s=600)
    ref=save(w.store,planning)
    handover(w.host('design'),ref,planning,origin=dict(kind='accepted_source_bound_predecessor'),kind='continuation_start')
    links=dict(predecessor_decision=decision,predecessor_plan=read(previous.RUN/'chain.json')['search_plan'],
        predecessor_project_usage=Store(previous.RUN).remaining(),historical_unknown_reservation_s=900.,budgets_transferred=False)
    w.freeze.update(confirmation_grant_links=links,historical_results=history,compatibility_review=review,current_factual_audit=ref,
        continuation_limits=dict(proposals=4,backends=2,target='model-selected',interpretation_reserve_s=600))
    w.validate_frozen_configuration();atomic_json(Path(directory)/'freeze.json',w.freeze)
    return w,planning


def final_packet(w,result,summary):
    references={r['role']:r for r in w.historical_results if r['role']=='retained_baseline'}
    baseline=w.historical_results[0]['facts'];start=w.historical_results[-1]['facts']
    rows=[]
    for row in result['candidates']:
        if not row.get('execution'):continue
        facts=row['execution']['factual_result']
        rows.append(dict(candidate_id=row['candidate_id'],changes=row['changes'],metrics=campaign_metrics(facts),
            against_retained_baseline=compare_results(baseline,facts),against_immediate_predecessor=compare_results(start,facts)))
    counts=[]
    for item in summary['current_update_facts']:
        it=item['selected_iterations'];counts.append(dict(execution_id=item['execution_id'],
            initialization=it.get('iteration_zero',{}).get('count',0)+it.get('synthetic_initialization',{}).get('count',0),
            positive_iteration=it['positive_iteration']['count']))
    return dict(source_batch_summary=w.chain['batch_summary'],source_plan=w.chain['search_plan'],
        hypothesis=w.store.artifact(w.chain['search_plan'])['plan']['hypothesis'],
        retained_baseline=campaign_metrics(baseline),immediate_predecessor=campaign_metrics(start),
        completed_results=rows,counts=counts,acceptance=read(repair.EVIDENCE/'decision_packet.json')['acceptance'],
        accounting=result['accounting'],current_project_usage=w.store.remaining(),
        joint_positive_weight_tested=False,further_execution_authorized=False,
        raw_evidence='Sealed store artifacts and receipts remain available by source reference.')


def live():
    preparation.require_interpretation_gate()
    checked=read(EVIDENCE/'verification_current.json')
    if not checked['passed'] or checked['implementation']['files']!=implementation()['files']:raise ValueError('CURRENT_VERIFICATION_REQUIRED')
    if subprocess.check_output(['git','diff','HEAD','--',*implementation()['files']],cwd=ROOT,text=True):raise ValueError('COMMIT_BEFORE_LAUNCH')
    if RUN.exists():raise ValueError('PRESERVE_PRIOR_CONTINUATION_NO_REPLACEMENT')
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path.home()/'.codex/.env')
    for name in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):
        if '127.0.0.1:9' in os.environ.get(name,''):os.environ.pop(name)
    w,planning=prepare();started=time.monotonic();status='incomplete';reason=None;result=None
    atomic_json(RUN/'live_attempt.json',dict(implementation=implementation(),tls_verification=True))
    (RUN/'executed_runner.py').write_bytes(Path(__file__).read_bytes())
    try:
        w.phase('improvement','search_batch_plan','search_plan',planning_packet=planning,
            predecessor_decision=planning['predecessor_decision'],predecessor_plan=w.freeze['confirmation_grant_links']['predecessor_plan'])
        host=w.host('design');plan=w.store.artifact(w.chain['search_plan'])['plan']
        if (set(plan['variables'])!={'control/recipe/terminal_tip_speed_weight'} or plan['max_candidates']>4
            or plan['max_backend_attempts'] not in (1,2) or plan['target_changed_configurations'] not in (1,2)
            or any(plan['planned_budget'][k]>v for k,v in w.limits.items())
            or plan['planned_budget']['wall_s']<990*plan['max_backend_attempts']+600
            or plan['planned_budget']['model_calls']<5 or plan['planned_budget']['tool_calls']<4*plan['max_backend_attempts']+7):
            raise ValueError('PLAN_EXCEEDS_GRANT_OR_OMITS_EXECUTION_DELIVERY_CAPACITY')
        if implementation()!=w.freeze['implementation']:raise ValueError('FROZEN_IMPLEMENTATION_CHANGED')
        w.validate_frozen_configuration()
        intended=plan['target_changed_configurations']
        atomic_json(RUN/'prelaunch.json',dict(plan=w.chain['search_plan'],intended_new_complete_results=intended,
            reservations_s=dict(simulation=900,evaluation=30,profile=60,interpretation=600),method=plan['method'],candidates=plan.get('candidates')))
        print('PRELAUNCH intended new complete results:',intended,'method:',plan['method'],flush=True)
        configure_role(host,'executor','Execute this immutable accepted single-variable plan only.',phase_budget={});host.resume()
        prepare_offline_batch(host,w.chain['search_plan'],mode='live',starting_facts=w.historical_feedback['execution']['factual_result'],
            retained_baseline=w.historical_feedback['baseline_facts'],historical_results=w.historical_results)
        atomic_json(RUN/'bound_batch.json',host.store.session(host.run_id)['state']['search_batch'])
        result=run_live_batch(host);w.chain['batch_result']=save(w.store,result);atomic_json(RUN/'batch_result.json',result)
        summary=previous.compact_summary(w,result);w.chain['batch_summary']=save(w.store,summary);atomic_json(RUN/'batch_summary.json',summary)
        packet=final_packet(w,result,summary);packet_ref=save(w.store,packet);atomic_json(RUN/'decision_packet.json',packet)
        w.phase('response_final','design_response','final_response',batch_result=summary,experiment_plan=w.chain['search_plan'],
            improvement_feedback_content=dict(baseline_facts=w.historical_feedback['baseline_facts'],execution=None),
            check_feedback=[dict(reference=w.chain['batch_summary'])],require_research_route=True,
            decision_packet=packet,decision_packet_reference=packet_ref,source_report=w.common['source_report'],source_record=w.source_record)
        status='completed' if result['fully_evaluated_distinct_changed_configurations']==intended and result['stop_reason']=='pilot_target_complete' else 'incomplete'
        reason=result['stop_reason']
    except Exception as exc:
        reason=str(exc);atomic_json(RUN/'workflow_failure.json',dict(type=type(exc).__name__,message=reason));print('STOP',reason,flush=True)
        if w.store.session(w.host('design').run_id)['state'].get('search_batch'):
            result=offline_batch_result(w.host('design'));atomic_json(RUN/'batch_result_at_failure.json',result)
    w.export(status,reason,time.monotonic()-started)
    from tools.improvement_workflow import archive_store
    archive_store(w.store,EVIDENCE/'single_context',source_stores=[previous.prior.CONFIRM,*[p for _,p,_ in preparation.SOURCES],previous.RUN])
    atomic_json(EVIDENCE/'continuation_acceptance.json',dict(execution_completed=status=='completed',semantic_review_pending=True,
        stop_reason=reason,completed_new_results=(result or {}).get('fully_evaluated_distinct_changed_configurations',0),
        final_response=w.chain.get('final_response'),no_subsequent_direction_executed=True))
    print('CONTINUATION',status,reason,flush=True)


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='verify':
        from unittest.mock import patch
        from examples import stage357_live_pilot as verifier
        with patch.object(verifier,'EVIDENCE',EVIDENCE):verifier.verify(sys.argv[2:])
    else:live()
