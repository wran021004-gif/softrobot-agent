"""Bounded Milestone 4 stages on the existing shared planner and receipt executor."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from examples import stage359_live_continuation as prior
from examples import stage359_continuation as history
from tools.platform_store import Store,plain
from tools.platform_host import Host
from tools.state_io import read,atomic_json,digest
from tools.diagnostic_workflow import save,implementation
from tools.diagnostic_facts import handover
from tools.diagnostic_revision import ensure_aliases
from tools.platform_diagnosis_coordinator import configure_role,transfer_recovery
from tools.platform_models import payload_for
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from tools.platform_search import prepare_offline_batch,run_live_batch
from tools.live_batch_execution import verified_historical_result
from tools.study_history import study_history
from tools.batch_budget import budget_capacity,batch_requirement
from tools.settling_campaign import compare_results,campaign_metrics
from extensions.tendon_family.control_evidence import ControlEvidence

RUN=ROOT/'runs/milestone4_20261004/single_context'
EVIDENCE=ROOT/'evidence/milestone4_20261004'
SOURCES=(*history.SOURCES,('historical_candidate',prior.RUN,'44dbf3bc2964402e9f6af6a93c0f8d7d'))
GRANT=dict(model_calls=24,tool_calls=60,backend_solves=4,worker_calls=0,wall_s=9000.)
COMMON_PLAN='''Author one NEW immutable SearchBatchPlan. Copy the exact verified source_candidate identity from study_packet.history.rows; select the source yourself, separately from retained baseline and latest tested. Copy predecessor_decision from study_packet. Cite exact F aliases from study_packet.evidence_aliases, including a performed-check result alias. State a testable hypothesis, rationale, weakening observations, tested-point limits and stopping conditions. fixed_controller=controller.gvs_nmpc@7.0.0. Use search.family_explicit@1.0.0 for exact values: candidates contain precisely variables paths; max_candidates=list length; step=null. Numeric variables use bounds including source and points; source/point weights must be zero or >=0.0001 through 1. Fixed_conditions include robot,task,acceptance,controller_implementation,other_numerical_settings; robot means all undeclared structural fields. objectives include joint_reach_holding_acceptance,terminal_error_m,holding_max_error_m,holding_max_speed_m_s; constraints frozen_acceptance,force_bounds,finite_valid_execution; verification candidate.apply,simulation.run,evaluation.run,control.profile_report,bound_comparison,diagnostic_revision. Use max_backend_attempts and target_changed_configurations explicitly. planned_budget backend_solves is that phase cap; other resource limits can use study_packet.budget.available but must cover study_packet.budget.requirement. This is ONE shared cumulative campaign: no reset or extra grant. Stop on unknown/material failure/insufficient delivery capacity and at the declared completed-result target. Completed physical failure remains usable evidence. No separate numerical diagnostic work. Preserve task, actuation, implementation, initializer, timing, solver, horizon and all undeclared fields.'''
CONTROL_PLAN=COMMON_PLAN+''' Current step: ONE new control point, at most one backend attempt and target_changed_configurations=1. All SIX completed historical configurations are visible, including holding-only positive tests. The untested branch is joint positive. A supported available point is holding 0.05 / terminal 0.05 from the 0/0.05 source execution 50618bf23b31464ba4f84c55cd26d1ca: vary ONLY holding, terminal is fixed 0.05. Confirm or justify another previously unevaluated control point in the same scope. Only the two existing speed-weight paths are permitted now. Choose the scientific hypothesis and weakening observations; the suggested point is not a prescribed scientific conclusion.'''
FINAL='''Interpret EVERY completed result in decision_packet, using the program-computed comparisons with the declared source and retained baseline (and original research source when supplied). State separate terminal reach, holding position, holding speed and measured complete-update timing outcomes. Never turn a tradeoff or guidance score into automatic promotion. hypothesis_assessment is supported,weakened,rejected,or unresolved. disposition addresses only a diagnostic recommendation: use defer with recommendation_id=null if you are only assessing the study hypothesis; do not invent IDs or conflate hypothesis rejection with recommendation rejection. Candidate adoption/retention/deferment is independent. next_action=finish closes this substage. selected_candidate=baseline,none,or exact complete candidate_id. Author exactly one next_research route with bounded_check,source evidence,varied/fixed conditions,weakening/supporting observations, budget and stop conditions. This next action is a proposal; the subsequent model-authored immutable plan is separately validated before execution. No causal,global,continuous-time,hardware or real-time success claims. Physical failure does not establish physical impossibility. Keep concise, about 350 words.'''


def revision():
    paths=[*implementation()['files'],'examples/milestone4.py','tools/study_history.py','tools/batch_budget.py',
        'tools/candidate_parameters.py','tools/parameter_impacts.py','schemas/diagnostic_revision.py','tests/test_milestone4.py']
    return dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        files={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in dict.fromkeys(paths) if (ROOT/p).exists()})


def reviewed_changes():
    review=history.reviewed_changes()
    for _,directory,execution in SOURCES:
        old=Store(directory);source=ControlEvidence(old).resolve(execution)
        for dep in old.session(source['owner'])['snapshot']['dependencies'].values():
            for path,row in review.items():
                old_hash=dep['sources'].get(path)
                if old_hash and old_hash not in row['historical_hashes']:row['historical_hashes'].append(old_hash)
    return review


class MilestoneWorkflow(prior.ContinuationWorkflow):
    limits=GRANT
    phases={**prior.ContinuationWorkflow.phases,'improvement':dict(limit=dict(model_calls=6),protect_project=dict(model_calls=4,tool_calls=8,wall_s=1590.)),
        'response_final':dict(limit=dict(model_calls=6))}
    instructions={**prior.ContinuationWorkflow.instructions,'improvement':CONTROL_PLAN,'response_final':FINAL}

    def check_provider_payload(self,host):
        role=host.store.session(host.run_id)['state']['role_context']
        if role['phase']=='response_final':
            for field in ('improvement_feedback_content','check_feedback','report','native_fixed'):
                if field not in role:raise ValueError('FINAL_HOST_CONTEXT_MISSING: '+field)
        payload=payload_for(host,EvidenceDrivenAdapter());view=json.loads(payload['messages'][1]['content'])['role_context']
        assert view['instructions'] and ('study_packet' in view or 'decision_packet' in view)
        assert len(json.dumps(payload).encode())<100000
        phase=self.current_stage+'_'+view['phase']
        atomic_json(self.directory/(phase+'_provider_payload_offline.json'),payload)


def prepare(directory=RUN):
    from tools.runtime_identity import require_softagent_runtime
    from examples.stage356_milestone2 import scientific_bundle,import_common
    source=ControlEvidence(Store(prior.RUN)).resolve(SOURCES[-1][2])
    config=deepcopy(read(prior.RUN/'freeze.json')['experiment'])
    config.update(source_store=str(prior.RUN),execution_id=SOURCES[-1][2],source_manifest=source['manifest'],
        evidence_directory=str(EVIDENCE),project_prefix='gvs-milestone4',
        authorization_source='User authorized one cumulative Milestone 4 development campaign: 24 provider attempts,60 workflow tools,4 full backend attempts,9000 charged seconds,0 workers; four sequential gates,configured provider requests and local simulations; local coherent commits,no push. Historical campaigns remain closed.')
    w=MilestoneWorkflow(directory,'single_context',experiment=config)
    w.prepare(require_softagent_runtime());import_common(w,scientific_bundle());prior.previous.prior.import_confirmation(w)
    w.historical_results=[verified_historical_result(w.host('design'),Store(p),e,r,reviewed_changes()) for r,p,e in SOURCES]
    prior.copy_reference(w.store,Store(prior.RUN),read(prior.RUN/'chain.json')['final_response'])
    w.predecessor_decision=read(prior.RUN/'chain.json')['final_response']
    w.latest_tested=w.historical_results[-1]['facts']['candidate']
    w.retained_baseline=w.historical_results[0]['facts']
    w.freeze.update(historical_results=w.historical_results,compatibility_review=reviewed_changes(),
        historical_unknown_reservation_s=900.,budgets_transferred=False,milestones2_and3_closed=True)
    w.freeze['confirmation_grant_links']=dict(historical_unknown_reservation_s=900.,budgets_transferred=False)
    # Configured recovery is narrowed to the user's explicit campaign ceiling.
    # Keep all transport/model/reasoning/token/TLS settings from the source freeze.
    for name,host in w.hosts.items():
        model=w.store.session(host.run_id)['snapshot']['input']['policy']['model']
        if model.get('protocol_recovery')!=dict(max_total=4,max_consecutive=2):
            # Host snapshots are immutable: create a new identity with just this configured recovery allowance.
            inp=deepcopy(w.store.session(host.run_id)['snapshot']['input']);inp['run_id']=host.run_id+'-m4'
            inp['policy']['model']['protocol_recovery']=dict(max_total=4,max_consecutive=2)
            replacement=Host(w.directory,inp['run_id']);replacement.create(inp)
            # Public products are imported via chain/handover; only the ledger recovery state is transferred.
            transfer_recovery(host,replacement);w.hosts[name]=replacement
            w.freeze['hosts'][name]=replacement.run_id;w.freeze['host_provider_configurations'][name]=inp['policy']['model']
    w.freeze['provider_configuration']=w.store.session(w.host('design').run_id)['snapshot']['input']['policy']['model']
    w.freeze['implementation']=implementation();w.freeze['milestone4_revision']=revision()
    atomic_json(w.directory/'freeze.json',w.freeze)
    atomic_json(w.directory/'history_initial.json',study_history(w.store,w.historical_results,
        retained_baseline=w.retained_baseline['candidate'],latest_tested=w.latest_tested))
    return w


def planning_packet(w,count):
    host=w.host('design');state=w.store.session(host.run_id)['state']
    aliases=ensure_aliases(state)['aliases'];result=w.store.artifact(w.chain['feedback'])['result']
    required=[a for a,h in aliases.items() if state['fact_catalog'][h]['selector']['reference']==result]
    packet=dict(history=study_history(w.store,w.historical_results,retained_baseline=w.retained_baseline['candidate'],latest_tested=w.latest_tested),
        predecessor_decision=w.predecessor_decision,
        predecessor_interpretation=w.store.artifact(w.predecessor_decision),
        budget=budget_capacity(count,w.store.spendable(host.run_id)['remaining']),
        evidence_aliases=dict(performed_check_result=required[:3]),
        campaign_limits=GRANT,correction_limits=dict(max_total=4,max_consecutive=2))
    return packet


def plan(w,stage,count,instructions):
    w.current_stage=stage
    host=w.host('design')
    # Install the accepted check result in this fresh planning context, with public aliases.
    check=w.store.artifact(w.chain['feedback']);handover(host,check['result'],w.store.artifact(check['result']),origin=dict(kind='accepted_saved_check'),kind='performed_check_result')
    packet=planning_packet(w,count)
    w.instructions={**w.instructions,'improvement':instructions};w.freeze['stage_instructions']=w.instructions
    w.phase('improvement','search_batch_plan','search_plan',study_packet=packet,research_records=w.historical_results,
        latest_tested=w.latest_tested,require_source_binding=True,predecessor_decision=w.predecessor_decision,
        planned_backend_count=count)
    record=w.store.artifact(w.chain['search_plan']);p=record['plan']
    if p['max_backend_attempts']!=count or p['target_changed_configurations']!=count or any(p['planned_budget'][k]>v for k,v in packet['budget']['available'].items()):
        raise ValueError('MILESTONE_PHASE_CAP_OR_CUMULATIVE_BUDGET_MISMATCH')
    atomic_json(w.directory/(stage+'_plan.json'),record)
    w.freeze['stage_instructions']=w.instructions
    return record


def execute(w,stage,record):
    host=w.host('design');source=next(r for r in w.historical_results if r['facts']['candidate']==record['bindings']['subject'])
    configure_role(host,'executor','Execute only this immutable model-authored batch.',phase_budget={});host.resume()
    prepare_offline_batch(host,w.chain['search_plan'],mode='live',starting_facts=source['facts'],retained_baseline=w.retained_baseline,historical_results=w.historical_results)
    atomic_json(w.directory/(stage+'_bound_batch.json'),w.store.session(host.run_id)['state']['search_batch'])
    result=run_live_batch(host);w.chain['batch_result']=save(w.store,result)
    atomic_json(w.directory/(stage+'_batch_result.json'),result)
    for row in result['candidates']:
        if not row.get('execution'):continue
        facts=row['execution']['factual_result'];configuration=w.store.artifact(facts['configuration'])['effective']
        from extensions.tendon_family.gvs_profile import execution_scope
        w.historical_results.append(dict(role='historical_candidate',facts=facts,execution_scope=execution_scope(configuration),
            source_store=str(w.directory),owner_run_id=facts['candidate']['owner_run_id'],execution_id=facts['execution_id'],receipts=row['execution']['receipts'],
            reuse_reason='New sealed complete candidate in this cumulative campaign.'))
        w.latest_tested=facts['candidate']
    if result['fully_evaluated_distinct_changed_configurations']!=record['plan']['target_changed_configurations'] or result['status']!='completed':
        raise ValueError('MILESTONE_BATCH_INCOMPLETE: '+str(result['stop_reason']))
    summary=prior.previous.compact_summary(w,result);w.chain['batch_summary']=save(w.store,summary)
    rows=[dict(candidate_id=r['candidate_id'],changes=r['changes'],metrics=campaign_metrics(r['execution']['factual_result']),
        against_source=compare_results(source['facts'],r['execution']['factual_result']),
        against_retained_baseline=compare_results(w.retained_baseline,r['execution']['factual_result']))
        for r in result['candidates'] if r.get('execution')]
    packet=dict(source_plan=w.chain['search_plan'],hypothesis=record['plan']['hypothesis'],source=source['facts']['candidate'],
        retained_baseline=campaign_metrics(w.retained_baseline),completed_results=rows,
        history=study_history(w.store,w.historical_results,retained_baseline=w.retained_baseline['candidate'],selected_source=source['facts']['candidate'],latest_tested=w.latest_tested),
        budget=budget_capacity(1,w.store.remaining()['remaining']),usage=w.store.remaining(),
        acceptance=read(prior.repair.EVIDENCE/'decision_packet.json')['acceptance'],substage=stage,
        next_required_step='structure_change' if stage=='control' else 'controller_adaptation' if stage=='structure' else 'final_decision',
        further_execution_requires_separate_model_authored_plan=True)
    packet_ref=save(w.store,packet);atomic_json(w.directory/(stage+'_decision_packet.json'),packet)
    w.phase('response_final','design_response','final_response',decision_packet=packet,decision_packet_reference=packet_ref,
        batch_result=summary,require_research_route=True,research_records=w.historical_results,latest_tested=w.latest_tested,
        improvement_feedback_content=dict(baseline_facts=w.retained_baseline,execution=None),check_feedback=[dict(reference=w.chain['batch_summary'])],
        source_report=w.common['source_report'],source_record=w.source_record)
    response=w.store.artifact(w.chain['final_response']);atomic_json(w.directory/(stage+'_final_response.json'),response)
    w.predecessor_decision=w.chain['final_response']
    atomic_json(w.directory/(stage+'_checkpoint.json'),dict(plan=w.chain['search_plan'],result=w.chain['batch_result'],decision=w.predecessor_decision,usage=w.store.remaining(),revision=revision()))
    return result,response


def export(w,status,reason,elapsed):
    w.export(status,reason,elapsed)
    outcome=read(w.directory/'outcome.json')
    outcome.update(physical_improvement='Evaluated by sealed current-campaign profiles and separate source/baseline physical vectors; see stage decision packets.',
        numerical_check_status='Historical performed-check reference only; zero new separate local solves or prediction evaluations.')
    atomic_json(w.directory/'outcome.json',outcome)
    atomic_json(EVIDENCE/'single_context/outcome.json',outcome)
    from tools.improvement_workflow import archive_store
    archive_store(w.store,EVIDENCE/'single_context',source_stores=[prior.previous.prior.CONFIRM,*[p for _,p,_ in SOURCES]])
    atomic_json(EVIDENCE/'campaign_status.json',dict(status=status,reason=reason,usage=w.store.remaining(),
        history=study_history(w.store,w.historical_results,retained_baseline=w.retained_baseline['candidate'],latest_tested=w.latest_tested),
        milestones2_and3_closed=True,milestone4_closed=False,live_organization='single_context',paired_comparison=False,
        revision=revision()))


def restore():
    """Continue only this ledger, retaining every charge and recovery counter."""
    freeze=read(RUN/'freeze.json');outcome=read(RUN/'outcome.json')
    w=MilestoneWorkflow(RUN,freeze['mode'],experiment=freeze['experiment']);w.freeze=freeze
    w.project=freeze['project_id'];w.hosts={k:Host(RUN,v) for k,v in freeze['hosts'].items()}
    w.binding=freeze['binding'];w.identities=freeze['identities'];w.summary=freeze['summary']
    w.inventory=freeze['inventory'];w.inventory_ref=freeze['inventory_reference']
    w.common=freeze['common_scientific_input'];w.source_record=freeze['source_record'];w.eligibility=freeze['numerical_eligibility']
    w.chain=outcome['chain'];w.historical_feedback=w.store.artifact(w.common['feedback'])
    w.historical_results=freeze['historical_results']
    for stage in ('control','structure','adaptation'):
        path=RUN/(stage+'_batch_result.json')
        if not path.exists():continue
        for row in read(path)['candidates']:
            if not row.get('execution'):continue
            facts=row['execution']['factual_result'];cfg=w.store.artifact(facts['configuration'])['effective']
            from extensions.tendon_family.gvs_profile import execution_scope
            w.historical_results.append(dict(role='historical_candidate',facts=facts,execution_scope=execution_scope(cfg),source_store=str(RUN),
                owner_run_id=facts['candidate']['owner_run_id'],execution_id=facts['execution_id'],receipts=row['execution']['receipts'],reuse_reason='Sealed current-campaign result.'))
    w.retained_baseline=w.historical_results[0]['facts'];w.latest_tested=w.historical_results[-1]['facts']['candidate']
    w.predecessor_decision=w.chain.get('final_response') or read(prior.RUN/'chain.json')['final_response']
    w.previous=w.host('design');return w


def migrate_planning_host(w,suffix):
    """Explicit engineering continuation after changed planner dependencies, same project."""
    old=w.host('design');inp=deepcopy(w.store.session(old.run_id)['snapshot']['input']);inp['run_id']=w.project+'-'+suffix
    new=Host(RUN,inp['run_id']);new.create(inp);transfer_recovery(old,new)
    old_state=w.store.session(old.run_id)['state']
    with w.store.transaction() as db:
        state=w.store.session(new.run_id,db)['state']
        for field in ('role_context','fact_scope','fact_catalog','reference_interface','read_ledger'):
            if field in old_state:state[field]=deepcopy(old_state[field])
        w.store.update_state(db,new.run_id,state)
        w.store.event(db,new.run_id,'engineering_continuation','same_campaign',outputs=[w.store.put(db,dict(
            source_context=old.run_id,project=w.store.config()['project_id'],budgets_reset=False,
            preserved_corrections=old_state.get('protocol_corrections_used',0),preserved_business_failures=old_state.get('business_failures_total',0),revision=revision()))])
    w.hosts['shared']=new;w.previous=new;w.freeze['hosts']['shared']=new.run_id
    w.freeze['host_provider_configurations']['shared']=inp['policy']['model']
    return new


def repair_control():
    """Revalidate the exact saved model-1 proposal after fixing host accounting."""
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path.home()/'.codex/.env')
    for name in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):
        if '127.0.0.1:9' in os.environ.get(name,''):os.environ.pop(name)
    w=restore();atomic_json(RUN/'control_pre_repair_freeze.json',w.freeze)
    w.current_stage='control';host=migrate_planning_host(w,'control-engineering1')
    w.freeze['implementation']=implementation();w.freeze['milestone4_revision']=revision()
    (RUN/'executed_control_repair_runner.py').write_bytes(Path(__file__).read_bytes())
    if (RUN/'control_batch_result.json').exists():raise ValueError('DO_NOT_REPLAY_CONTROL_EXECUTION')
    saved=next(r for r in read(EVIDENCE/'single_context/resolved_calls.json') if r['invocation']['request_id']=='model-1-tool')
    invocation=deepcopy(saved['invocation']);invocation.update(request_id='revalidate-sealed-model-1-plan',cache='new',
        reason='Exact unchanged model-authored scientific proposal; revalidate after correcting downstream capacity calculation; prior rejected receipts and charges preserved.')
    host.resume();receipt=host.invoke(invocation)
    if receipt['execution_status']!='completed':raise ValueError('REVALIDATION_FAILED: '+str(receipt.get('error')))
    w.chain['search_plan']=w.store.artifact(receipt['output'])['reference'];record=w.store.artifact(w.chain['search_plan'])
    atomic_json(RUN/'control_plan.json',record)
    atomic_json(RUN/'control_prelaunch_review.json',dict(passed=True,model_response=saved['reference'],plan=w.chain['search_plan'],
        review_method='Shared program validation plus direct agent source/semantic review; no judge service.',
        exact_point=record['plan']['candidates'],source=record['bindings']['subject'],
        baseline=w.retained_baseline['candidate'],actual_differences=record['actual_differences'],
        budget=record['available_capacity'],hypothesis_scoped_to_one_point=True,history_interpretation_accurate=True,
        earlier_model_statement_bytes_preserved=True))
    atomic_json(RUN/'control_engineering_intervention.json',dict(source_model_response=saved['reference'],
        scientific_arguments_unchanged=True,ledger_reset=False,
        repairs=['Correct downstream budget check to use project/session capacity rather than planning-phase capacity.'],
        rejected_later_response=dict(reference=read(EVIDENCE/'single_context/resolved_calls.json')[-1]['reference'],
            reason='Rationale incorrectly says all holding-only positive points fail official reach; 0.05/0 passed. Completed physical failure is usable comparison evidence.'),revision=revision()))
    # A successfully revalidated business call resets consecutive failure state,
    # as in the existing provider loop; total failures/corrections stay intact.
    with w.store.transaction() as db:
        state=w.store.session(host.run_id,db)['state'];state['repairs']=0;state['protocol_corrections_consecutive']=0
        state.pop('business_feedback',None);w.store.update_state(db,host.run_id,state)
    start=time.monotonic();status='incomplete';reason=None
    try:
        execute(w,'control',record);status='control_complete';reason='One control result complete; structural stage follows within the original ledger.'
    except Exception as exc:
        reason=str(exc);atomic_json(RUN/'control_repair_failure.json',dict(type=type(exc).__name__,message=reason));print('STOP',reason,flush=True)
    atomic_json(RUN/'freeze.json',w.freeze);export(w,status,reason,time.monotonic()-start)


def repair_interpretation():
    """Fix host feedback, seal the unchanged draft, then request scientific correction."""
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path.home()/'.codex/.env')
    for name in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):
        if '127.0.0.1:9' in os.environ.get(name,''):os.environ.pop(name)
    w=restore();w.current_stage='control';host=w.host('design');state=w.store.session(host.run_id)['state']
    draft=deepcopy(state['unaccepted_draft']);atomic_json(RUN/'control_original_interpretation_draft.json',draft)
    if (RUN/'control_checkpoint.json').exists():raise ValueError('CONTROL_INTERPRETATION_ALREADY_COMPLETE')
    with w.store.transaction() as db:
        state=w.store.session(host.run_id,db)['state']
        state['role_context'].update(improvement_feedback_content=dict(baseline_facts=w.retained_baseline,execution=None),
            check_feedback=[dict(reference=w.chain['batch_summary'])])
        w.store.update_state(db,host.run_id,state)
    adapter=EvidenceDrivenAdapter();payload_for(host,adapter)
    arguments=adapter.resolve_business('design.respond_diagnosis',draft['arguments']);arguments.update(adapter.fixed['design.respond_diagnosis'])
    host.resume();receipt=host.invoke(dict(request_id='seal-saved-interpretation-after-context-repair',tool_id='design.respond_diagnosis',tool_version='3.0.0',
        arguments=arguments,reason='Seal the unchanged saved model draft after host-only context repair; semantic next-proposal rejection retained separately.',cache='new'))
    if receipt['execution_status']!='completed':raise ValueError('INTERPRETATION_REVALIDATION_FAILED: '+str(receipt.get('error')))
    saved=w.store.artifact(receipt['output'])['reference']
    atomic_json(RUN/'control_rejected_next_proposal_review.json',dict(response=saved,current_result_interpretation_passed=True,
        next_proposal_passed=False,issues=['1500 seconds/5 tools/1 model for two complete evaluations is below computed execution and interpretation reservations.',
        'Variable identifiers must use supported canonical builder paths; the first live structural study varies one length only.'],
        host_context_repaired=True,scientific_draft_unchanged=True,backend_replayed=False))
    with w.store.transaction() as db:
        state=w.store.session(host.run_id,db)['state'];state['protocol_corrections_consecutive']=0
        state.pop('protocol_correction',None);state.pop('unaccepted_draft',None);w.store.update_state(db,host.run_id,state)
    packet=read(RUN/'control_decision_packet.json');packet.update(prior_response=saved,
        correction_review=read(RUN/'control_rejected_next_proposal_review.json'),
        permitted_next_study=dict(max_backend_attempts=1,variables=['components/near/length_m','components/far/length_m'],
            domains={'components/near/length_m':[.15,.17],'components/far/length_m':[.11,.13]},
            rule='Choose exactly one length for the later separately validated immutable plan. Freeze controller recipe. Then adapt controller weights on the changed structure; physical failure remains usable evidence.'),
        budget=budget_capacity(1,w.store.remaining()['remaining']))
    instructions=FINAL+' Correct the prior next proposal using correction_review and permitted_next_study. Its two-evaluation 1500-second budget is insufficient; use the computed one-result requirement and available capacity. Propose exactly one canonical LENGTH path with a bounded value, not undeclared section/modulus paths. Keep current-result interpretation accurate and adoption independent. Record a next structural question, supporting and weakening observations; this is a research direction, not a physical success claim.'
    w.instructions={**w.instructions,'response_final':instructions};w.freeze['stage_instructions']=w.instructions
    start=time.monotonic();status='incomplete';reason=None
    try:
        w.phase('response_final','design_response','final_response',decision_packet=packet,decision_packet_reference=save(w.store,packet),
            batch_result=w.store.artifact(w.chain['batch_summary']),require_research_route=True,
            improvement_feedback_content=dict(baseline_facts=w.retained_baseline,execution=None),check_feedback=[dict(reference=w.chain['batch_summary'])],
            source_report=w.common['source_report'],source_record=w.source_record,research_records=w.historical_results,latest_tested=w.latest_tested)
        response=w.store.artifact(w.chain['final_response']);atomic_json(RUN/'control_final_response.json',response)
        atomic_json(RUN/'control_checkpoint.json',dict(plan=w.chain['search_plan'],result=w.chain['batch_result'],decision=w.chain['final_response'],usage=w.store.remaining(),revision=revision()))
        status='control_complete';reason='One complete control result and corrected model interpretation; structural stage follows within same grant.'
    except Exception as exc:
        reason=str(exc);atomic_json(RUN/'interpretation_repair_failure.json',dict(type=type(exc).__name__,message=reason));print('STOP',reason,flush=True)
    atomic_json(RUN/'freeze.json',w.freeze);export(w,status,reason,time.monotonic()-start)


def control_live():
    if RUN.exists():raise ValueError('PRESERVE_EXISTING_CAMPAIGN_NO_REPLACEMENT')
    if subprocess.check_output(['git','diff','HEAD','--',*revision()['files']],cwd=ROOT,text=True):raise ValueError('COMMIT_BEFORE_LIVE')
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path.home()/'.codex/.env')
    for name in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):
        if '127.0.0.1:9' in os.environ.get(name,''):os.environ.pop(name)
    w=prepare();start=time.monotonic();status='incomplete';reason=None
    atomic_json(RUN/'live_attempt.json',dict(revision=revision(),tls_verification=True));(RUN/'executed_control_runner.py').write_bytes(Path(__file__).read_bytes())
    try:
        record=plan(w,'control',1,CONTROL_PLAN)
        if set(record['plan']['variables'])-set(('control/recipe/holding_tip_speed_weight','control/recipe/terminal_tip_speed_weight')):
            raise ValueError('CONTROL_STAGE_VARIABLE_SCOPE')
        execute(w,'control',record);status='control_complete';reason='Control-only substage closed; structural interface stage follows within the same campaign.'
    except Exception as exc:
        reason=str(exc);atomic_json(RUN/'workflow_failure.json',dict(type=type(exc).__name__,message=reason));print('STOP',reason,flush=True)
    export(w,status,reason,time.monotonic()-start)


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='repair-control':repair_control()
    elif len(sys.argv)>1 and sys.argv[1]=='repair-interpretation':repair_interpretation()
    else:control_live()
