"""New bounded supplement; one shared model context, existing batch execution."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from examples import milestone4 as prior
from examples import milestone45_continuation as continuation
from tools.state_io import read,atomic_json,digest
from tools.platform_store import Store,plain,encode
from tools.platform_host import Host
from tools.diagnostic_workflow import save
from tools.diagnostic_facts import handover
from tools.diagnostic_revision import ensure_aliases
from tools.platform_diagnosis_coordinator import configure_role
from tools.platform_models import payload_for,run_loop,tool_naming_policy,READABLE_TOOL_NAMING
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from tools.research_scheduler import capabilities
from tools.platform_search import prepare_offline_batch,run_live_batch
from tools.live_batch_execution import verified_historical_result
from tools.study_history import study_history,execution_chronology
from tools.structural_study import research_planning_input
from tools.settling_campaign import campaign_metrics,compare_results
from extensions.tendon_family.gvs_profile import execution_scope

RUN=ROOT/'runs/milestone4_autonomous_20261005'
EVIDENCE=ROOT/'evidence/milestone4_autonomous_20261005'
PREDECESSOR_RUN=RUN
SUCCESSOR_RUN=ROOT/'runs/milestone4_autonomous_20261006'
SUCCESSOR_EVIDENCE=ROOT/'evidence/milestone4_autonomous_20261006'
LIMITS=dict(model_calls=24,tool_calls=60,backend_solves=4,worker_calls=0,wall_s=9000.)
FILES=('examples/milestone4_autonomous.py','tools/research_scheduler.py','tools/platform_search.py',
    'tools/structural_study.py','tools/diagnostic_reference_adapter.py','tools/platform_models.py',
    'schemas/platform_handoff.py','extensions/platform/manifest.py','tests/test_research_scheduler.py','tools/study_history.py')
INSTRUCTIONS='''Choose control_search,structure_search,diagnosis,or stop yourself from research_packet.capabilities. No stage or round forces a route. The research question concerns the observed holding-speed acceptance loss at holding weight .10 versus the known passing .05/.05 incumbent on near .16/far .11/scale .95/compliant, and whether affordable further control or structural evidence is useful. The incumbent is already successful. You may retain it and stop. Engineering multibatch coverage is measured separately and must not force scientific continuation. Explain actual feedback and cite current F aliases, including a latest-feedback alias. Select any verified complete source from history; primary is a starting question, not a forced source. After a search result explain which new observations support your next action. Citation validity does not certify a causal explanation.
Use exactly one research.decide native tool with ordinary structured fields. For search embed ONE SearchBatchPlan object. Use exact source_candidate and predecessor_decision from packet; evidence uses F aliases including current feedback. Allowed variables are the current builder paths shown in capabilities; keep undeclared fields fixed. Both installed search.family_explicit@1.0.0 and search.family_coordinate@1.0.0 are legal. Explicit method has null step and candidates containing precisely variables; coordinate has step and null candidates. Source values must lie in declared domains. Weights zero or >=.0001 through 1; structural domains use the frozen controller-7 profile; material choices require explicit enumeration. fixed_controller=controller.gvs_nmpc@7.0.0; fixed_conditions include robot,task,acceptance,controller_implementation,other_numerical_settings. Objectives joint_reach_holding_acceptance,terminal_error_m,holding_max_error_m,holding_max_speed_m_s (optional complete_update_s); constraints frozen_acceptance,force_bounds,finite_valid_execution; verification candidate.apply,simulation.run,evaluation.run,control.profile_report,bound_comparison,diagnostic_revision. Declare hypothesis,rationale,weakening observations,fidelity limits and exit conditions. max_backend_attempts and target_changed_configurations explicit, at most two backend attempts per batch (frozen allocation preserving feedback/delivery capacity). max_candidates may include a reused start. planned_budget covers computed complete execution plus delivery requirement, within remaining totals; backend_solves equals batch cap,workers=0. No automatic extra control adaptation after a structure change.
For diagnosis identify competing hypotheses,existing evidence,missing observation,outcome_actions,max_wall_s and exit_condition. Only retained prediction/plans/motion queries are executable here. Numerical saved-state work has an explicit capability gap; do not request unsupported computations. Duplicate queries return prior evidence without execution unless replication_reason justifies a changed hypothesis or repeated measurement. For stop provide stop_reason,reasoning,evidence and selected_candidate as an exact complete identity or null. No physical,hardware,realtime,global-optimum or causal success claim follows merely from acceptance. Keep interpretation concise.'''
SUCCESSOR_INSTRUCTIONS=INSTRUCTIONS[INSTRUCTIONS.index('Use exactly one research.decide'):]+'''
Choose among all currently legal actions yourself. The current case's question, verified starting observations, counterexamples, known passing incumbents and frozen stopping criteria are in research_packet.case. The purpose is resolving a control-response uncertainty or judging the value of further evidence, not just finding an already-known passing configuration. No next values, structural change or sequence are required. Voluntary stop remains legal under uncertainty and unused capacity. Coverage targets do not require two batches. A sealed case is never reopened; any fallback is a separately frozen case.
Separate observations, interpretations and the action. observations entries bind one exact current F alias and copied value (operation=recorded, comparison_evidence=null), or a deterministic difference/less_than/greater_than/equal operation with two exact aliases. Use full supplied values rather than rounded prose numbers. interpretations entries state a hypothesis or judgment, supporting_evidence, contradicting_evidence, scope and uncertainty. An empty interpretations list is legal; list unresolved_uncertainties explicitly. Numerical bindings are checked; free scientific explanations are not certified. Referencing a passing sample cannot prove optimality or a passing interval. An unavailable route is a factual capability claim; distinguish it from a judgment that further spending has little value. Existing configurations are reused unless the search plan provides replication_reason; deliberate replication is a new execution, not a novel design. One execution per configuration per batch; source values may be repeated only for explicit replication. Keep free-text interpretations concise and conditional.'''


def revision():
    return dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        files={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FILES if (ROOT/p).exists()},
        stable_controller={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
            ('extensions/tendon_family/gvs_nmpc.py','extensions/tendon_family/gvs_trajectory.py','extensions/tendon_family/gvs_profile.py')})


def compact_history(w):
    history=study_history(w.store,w.records,retained_baseline=w.baseline['candidate'],latest_tested=w.latest,
        selection=w.selected,selected_source=getattr(w,'batch_source',None))
    for row in history['rows']:
        row.pop('physical_structure',None);row.pop('references',None)
    return history


def feedback(w,value,kind):
    ref=save(w.store,value);envelope=save(w.store,dict(result=ref,kind=kind))
    handover(w.host,ref,value,origin=dict(kind=kind),kind='performed_check_result')
    w.feedback=envelope;return ref


def prepare(directory=None,*,successor=False):
    from tools.runtime_identity import require_softagent_runtime
    from examples.stage356_milestone2 import scientific_bundle,import_common
    directory=Path(directory or (SUCCESSOR_RUN if successor else RUN))
    if (directory/'scheduler_state.json').exists():raise ValueError('EXISTING_CAMPAIGN_USE_RESUME_NO_RESET')
    old=Store(continuation.RUN);old_freeze=read(continuation.RUN/'freeze.json')
    config=deepcopy(old_freeze['experiment']);config.update(evidence_directory=str(SUCCESSOR_EVIDENCE if successor else EVIDENCE),
        project_prefix='gvs-m4-autonomous',provider_freeze=str(continuation.RUN/'freeze.json'),adapter_version='6.0.0',
        authorization_source='User 2026-10-05 attachment c93a3290: new M4 supplement 24 provider/60 workflow/4 backend/9000 charged seconds/12 standalone numerical operations/0 workers and subagents; live DeepSeek,simulations,one narrow repair,resume,commit/push authorized. Historical STOP/NO_GO preserved.')
    if successor:config.update(project_prefix='gvs-m4-autonomous-successor',
        authorization_source='User 2026-10-06 attachment e46020d6 and direct continuation: new linked 24/60/4/9000 campaign,12 standalone diagnostics,zero workers/subagents; real configured DeepSeek,backend,one narrow repair,non-secret evidence publication and normal push authorized. Predecessor stop is sealed.')
    w=prior.MilestoneWorkflow(directory,'single_context',experiment=config)
    w.tools={**w.tools,'research.decide':'1.0.0'}
    if (directory/'freeze.json').exists():
        w.freeze=read(directory/'freeze.json');w.project=w.freeze['project_id']
        w.hosts={k:Host(directory,v) for k,v in w.freeze['hosts'].items()}
        for attr,key in [('binding','binding'),('identities','identities'),('summary','summary'),('inventory','inventory'),('inventory_ref','inventory_reference')]:
            setattr(w,attr,w.freeze[key])
        w.chain=read(directory/'chain.json') if (directory/'chain.json').exists() else {}
        if 'common_scientific_input' in w.freeze:
            w.common=w.freeze['common_scientific_input'];w.source_record=w.freeze['source_record']
        else:import_common(w,scientific_bundle())
    else:
        w.prepare(require_softagent_runtime());import_common(w,scientific_bundle())
    if successor:
        from tools.platform_store import zero
        prep_owner=w.host('design').run_id
        prep_row,_=w.store.reserve(prep_owner,'successor-preparation',digest(dict(successor=True)),
            'preparation',{**zero(),'tool_calls':1,'wall_s':120.})
        prep_started=time.monotonic();prep_charge_start=w.store.remaining()['used']['wall_s']
    prior.prior.previous.prior.import_confirmation(w)
    review=deepcopy(old_freeze['compatibility_review'])
    # Transport-only schema/receipt changes have no altered production equations.
    for path,row in review.items():
        previous_hash=row['current_hash'];row['current_hash']=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
        if previous_hash!=row['current_hash'] and previous_hash not in row['historical_hashes']:
            row['historical_hashes'].append(previous_hash)
    compatibility_notes={
        'extensions/tendon_family/backends.py':'Optional PRE_STEP_OBSERVER is None in stable execution; no observer invoked or equations/input semantics changed.',
        'extensions/tendon_family/control_evidence.py':'Optional pre-step evidence capture context; production not entered by this supplement.',
        'extensions/tendon_family/gvs_trajectory.py':'ContextVar function provider defaults to None; native provider never installed in stable supplement.'}
    sources=[(Store(r['source_store']),r['execution_id']) for r in old_freeze['historical_results']]
    for stage in ('structure','adaptation'):
        sources.extend((old,row['execution']['factual_result']['execution_id']) for row in read(continuation.RUN/(stage+'_batch_result.json'))['candidates'] if row.get('execution'))
    predecessor=restore(PREDECESSOR_RUN) if successor else None
    if successor:
        sources.extend((predecessor.store,eid) for eid in ('e3876a1d289f41f08d46c96202f1da0c','1ffdcbc4f93f4dc4bb16a807c7b4056b'))
    from extensions.tendon_family.control_evidence import ControlEvidence
    for path,note in compatibility_notes.items():
        review.setdefault(path,dict(current_hash=hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),historical_hashes=[],reason=note))
    if successor:
        review['tools/platform_search.py']['reason']='Receipt-derived chronology metadata and opt-in deliberate replication; default historical reuse, candidate reconstruction, task/evaluator and controller equations unchanged.'
    for path,row in review.items():
        for store,eid in sources:
            snapshot=store.session(ControlEvidence(store).resolve(eid)['owner'])['snapshot']
            for dep in snapshot['dependencies'].values():
                h=dep['sources'].get(path)
                if h and h not in row['historical_hashes']:row['historical_hashes'].append(h)
    w.freeze['compatibility_review']=review
    w.records=[]
    for record in old_freeze['historical_results']:
        w.records.append(verified_historical_result(w.host('design'),Store(record['source_store']),
            record['execution_id'],record['role'],review))
    for stage in ('structure','adaptation'):
        for row in read(continuation.RUN/(stage+'_batch_result.json'))['candidates']:
            if row.get('execution'):
                eid=row['execution']['factual_result']['execution_id']
                if not any(r['execution_id']==eid for r in w.records):
                    w.records.append(verified_historical_result(w.host('design'),old,eid,'historical_candidate',review))
    if successor:
        for source,eid in sources[-2:]:
            w.records.append(verified_historical_result(w.host('design'),source,eid,'historical_candidate',review))
    primary=next(r for r in w.records if r['execution_id']==('1ffdcbc4f93f4dc4bb16a807c7b4056b' if successor else '110dc2c9c1d642dcb018664a65c62c30'))
    incumbent=next(r for r in w.records if r['execution_id']=='91c3ba1b01d6499fb26df8f95409401b')
    w.baseline=w.records[0]['facts'];w.latest=primary['facts']['candidate'];w.selected=incumbent['facts']['candidate']
    w.previous_decision=save(w.store,read(continuation.RUN/'adaptation_final_response.json'))
    model=deepcopy(old_freeze['provider_configuration']);model['protocol_recovery']=dict(max_total=4,max_consecutive=2)
    bindings={'research.decide':'1.0.0','diagnosis.inspect_evidence':'1.0.0'}
    model['tool_naming']=tool_naming_policy(bindings,READABLE_TOOL_NAMING)
    inp=research_planning_input(w.store.artifact(primary['facts']['configuration'])['effective'],read(continuation.PROFILE),
        budget=LIMITS,model=model,tool_bindings=bindings)
    inp['run_id']=w.project+'-research';inp['policy'].update(route=None,allowed_tools=[])
    host=Host(directory,inp['run_id']);host.create(inp);w.host=host
    with w.store.transaction() as db:
        state=w.store.session(host.run_id,db)['state'];state['fact_scope']=dict(project=w.project,binding=primary['binding'])
        w.store.update_state(db,host.run_id,state)
    w.rounds=[];w.repairs=0;w.status='prepared';w.stop_reason=None
    w.batch_source=None;w.current_case='primary';w.sealed_cases=[]
    w.freeze.update(limits=LIMITS,research_host=host.run_id,provider_configuration=model,profile=read(continuation.PROFILE),
        primary=primary['facts']['candidate'],incumbent=incumbent['facts']['candidate'],fallback=None,
        unresolved_question='Why the observed .10 holding weight loses speed acceptance against .05, and which further bounded control/structural evidence is useful.',
        implementation=revision(),max_batch_backends=2,standalone_numerical_limit=12,
        accounting_mapping=dict(provider_attempts='calls charged.model_calls, including failed/correction/transport requests',
            workflow_calls='calls charged.tool_calls, including preparation,decisions,apply,simulation,evaluation,profile and diagnosis',
            backend_attempts='calls charged.backend_solves, complete simulation attempts including failures',
            charged_execution_seconds='sum charged.wall_s; preparation reads/builds/provider/backend/failures charged once; editing,focused checks,export use established offline engineering convention and separate wall receipt',
            standalone_diagnostics='diagnostic_work local_solves+prediction_evaluations; retained queries are workflow calls; embedded 35 controller updates/backend recorded separately'),
        correction_policy=dict(max_total=4,max_consecutive=2,cumulative_across_restore=True),
        termination=['voluntary model stop','material/unknown backend failure','insufficient complete delivery reservation',
            'provider/correction ceilings','finished scoped delivery; do not spend unused budgets'],
        historical_links=dict(m4=str(prior.RUN),m45=str(continuation.RUN),m5A='evidence/milestone5_successor_20261005/acceptance_audit.json'),
        historical_stops_preserved=True,protected_M5_budget_transferred=False,workers=0,subagents=0)
    if successor:
        fallback=next(r for r in w.records if r['execution_id']=='44dbf3bc2964402e9f6af6a93c0f8d7d')
        w.freeze.update(fact_separation=True,predecessor_campaign=str(PREDECESSOR_RUN),
            predecessor_stop=predecessor.rounds[-1]['accepted_decision'],
            cases=dict(primary=dict(candidate=primary['facts']['candidate'],
                question='What affordable evidence could distinguish observed holding-response differences on the shortened compliant geometry from solver-plan selection, weight interaction or structural sensitivity? The saved .075/.09/.10 holding values all fail speed with decreasing maxima; 0/.05 and .05/.05 both pass. Sparse samples do not establish a boundary, monotonicity, repetition or a dominant cause.',
                evidence_execution_ids=['bebcfd47274940fb88a55ce5a2457c4c','91c3ba1b01d6499fb26df8f95409401b','110dc2c9c1d642dcb018664a65c62c30','e3876a1d289f41f08d46c96202f1da0c','1ffdcbc4f93f4dc4bb16a807c7b4056b'],
                stopping_criteria=w.freeze['termination']),
                fallback=dict(candidate=fallback['facts']['candidate'],
                    question='On the original geometry, terminal-only .05 and .10 both fail holding speed despite passing position, while joint .05/.05 passes. What further control/structure or retained-plan evidence is worth collecting about interaction or structure dependence? The shorter compliant geometry has counterexamples; comparisons changing several fields do not isolate one cause. A passing incumbent is disclosed; finding any passing point is not the sole research purpose.',
                    evidence_execution_ids=['50618bf23b31464ba4f84c55cd26d1ca','44dbf3bc2964402e9f6af6a93c0f8d7d','a8382f8a4c6e4ebe921fb72f821b2188','bebcfd47274940fb88a55ce5a2457c4c'],
                    stopping_criteria=w.freeze['termination'])),
            fallback=dict(case_id='fallback',activation='Only after valid voluntary primary stop with fewer than two real batches and capacity for two complete executions plus shared delivery; never after material/unknown/provider failure or reopening a stopped case.',
                minimum_backend_capacity=2),
            research_instructions=SUCCESSOR_INSTRUCTIONS)
        w.previous_decision=save(w.store,dict(predecessor_campaign=str(PREDECESSOR_RUN),sealed_decision=predecessor.rounds[-1]['decision']))
    feedback(w,dict(primary=primary['facts']['candidate'],metrics=campaign_metrics(primary['facts']),
        comparison_to_incumbent=compare_results(incumbent['facts'],primary['facts']),source_profile=primary['facts']['report']), 'verified_primary_feedback')
    if successor:case_feedback(w)
    if successor:
        elapsed=time.monotonic()-prep_started
        other_charge=w.store.remaining()['used']['wall_s']-prep_charge_start
        w.store.complete(prep_row,dict(request_id='successor-preparation',execution_id=prep_row['execution_id'],
            caller='preparation',tool_id='engineering.research_preparation',tool_version='1.0.0',execution_status='completed',charged=zero()),
            dict(verified_history=len(w.records),scientific_replay=False,preparation_wall_s=elapsed,other_nested_charged_s=other_charge),max(0.,elapsed-other_charge))
    persist(w);atomic_json(directory/'freeze_seal.json',dict(identity=digest(w.freeze),before_first_live_request=True))
    return w


def persist(w):
    atomic_json(w.directory/'freeze.json',w.freeze)
    atomic_json(w.directory/'scheduler_state.json',dict(records=w.records,baseline=w.baseline,latest=w.latest,selected=w.selected,
        previous_decision=w.previous_decision,feedback=w.feedback,rounds=w.rounds,repairs=w.repairs,status=w.status,stop_reason=w.stop_reason,
        batch_source=getattr(w,'batch_source',None),current_case=getattr(w,'current_case','primary'),sealed_cases=getattr(w,'sealed_cases',[])))


def restore(directory=None):
    directory=Path(directory or RUN)
    freeze=read(Path(directory)/'freeze.json');w=prior.MilestoneWorkflow(directory,'single_context',experiment=freeze['experiment'])
    w.freeze=freeze;w.host=Host(directory,freeze['research_host']);w.project=freeze['project_id']
    for k,v in read(Path(directory)/'scheduler_state.json').items():setattr(w,k,v)
    return w


def case_feedback(w):
    case=w.freeze['cases'][w.current_case];rows=[]
    for eid in case['evidence_execution_ids']:
        f=next(r['facts'] for r in w.records if r['execution_id']==eid)
        profile=w.store.artifact(f['report']['reference'])['detail']
        rows.append(dict(candidate=f['candidate'],metrics=campaign_metrics(f),profile=f['report']['reference'],
            observed_plan_behavior={k:profile[k] for k in ('initialization_selected','accepted_noninitialization_plans',
                'converged_updates','optimization_status_counts','one_step_prediction_summary')}))
    feedback(w,dict(case_id=w.current_case,question=case['question'],source=case['candidate'],observations=rows,
        known_passing_incumbent=w.freeze['incumbent'],limits='Historical measurements, not causal proofs or new executions'), 'verified_case_start')


def fallback_eligible(w):
    from tools.batch_budget import budget_capacity,PREPARATION_RESERVE_S
    policy=w.freeze.get('fallback')
    if not policy or w.current_case!='primary' or w.status!='model_stopped':return False
    searches=[r for r in w.rounds if r.get('case_id','primary')=='primary' and r.get('kind')=='search' and r.get('complete')]
    return len(searches)<2 and budget_capacity(policy['minimum_backend_capacity'],
        w.store.remaining()['remaining'],preparation_reserve_s=PREPARATION_RESERVE_S)['sufficient']


def seal_case(w):
    if any(c['case_id']==w.current_case for c in w.sealed_cases):return
    w.sealed_cases.append(dict(case_id=w.current_case,status=w.status,stop_reason=w.stop_reason,
        final_decision=w.previous_decision,selected_candidate=w.selected,usage=w.store.remaining()))


def activate_fallback(w):
    if not fallback_eligible(w):return False
    seal_case(w);w.current_case='fallback';case=w.freeze['cases']['fallback']
    w.batch_source=None;w.status='running';w.stop_reason=None
    case_feedback(w)
    with w.store.transaction() as db:
        w.store.event(db,w.host.run_id,'frozen_fallback','activated',inputs=[w.previous_decision],
            outputs=[w.store.put(db,dict(case=case,policy=w.freeze['fallback'],budget_reset=False,
                corrections_carried=w.store.session(w.host.run_id,db)['state'].get('protocol_corrections_used',0)))])
    persist(w);return True


def configure(w):
    active=w.store.session(w.host.run_id)['state'].get('search_batch',{})
    chronology=execution_chronology(w.store,[*w.records,*active.get('configurations',{}).values()])
    w.latest=chronology['latest_complete_result']
    cap=capabilities(w.store,w.host.run_id,w.records);state=w.store.session(w.host.run_id)['state']
    context_ref=None
    if w.freeze.get('fact_separation'):
        value=dict(legal_actions={k:k in cap['legal'] for k in ('control_search','structure_search','diagnosis','stop')},
            unavailable=cap['unavailable'],remaining=cap['remaining'],chronology=chronology,
            convention='Capacity before this provider attempt; interpretation text remains model judgment')
        context_ref=save(w.store,value);handover(w.host,context_ref,value,origin=dict(kind='verified_context'),kind='verified_context')
        state=w.store.session(w.host.run_id)['state']
    aliases=ensure_aliases(state)['aliases'];catalog=state.get('fact_catalog',{})
    latest_ref=w.store.artifact(w.feedback)['result']
    current={a:dict(pointer=catalog[h]['selector']['pointer'],value=catalog[h]['value']) for a,h in aliases.items()
        if catalog[h]['selector']['reference']==latest_ref}
    packet=dict(history=compact_history(w),primary=w.freeze['primary'],incumbent=w.freeze['incumbent'],
        chronology=chronology,current_batch_source=getattr(w,'batch_source',None),
        current_feedback=dict(reference=latest_ref,content=w.store.artifact(latest_ref),aliases=current),
        predecessor_decision=w.previous_decision,capabilities=cap,scope=w.freeze['profile'],
        engineering_coverage=dict(completed_search_batches=sum(r.get('case_id','primary')==getattr(w,'current_case','primary') and r.get('kind')=='search' and r.get('complete') for r in w.rounds),
            target='Two separate real search batches, later plan explicitly referencing actual first-batch evidence. This does not override voluntary stopping.'),
        corrections=dict(total=state.get('protocol_corrections_used',0),consecutive=state.get('protocol_corrections_consecutive',0)))
    if context_ref:packet.update(case_id=w.current_case,case=w.freeze['cases'][w.current_case],sealed_cases=w.sealed_cases,
        context_observation_reference=context_ref,context_observation_aliases={a:dict(pointer=catalog[h]['selector']['pointer'],value=catalog[h]['value'])
            for a,h in aliases.items() if catalog[h]['selector']['reference']==context_ref})
    packet['performed_batch_evidence']=[dict(reference=r['feedback_result'],aliases={a:dict(pointer=catalog[h]['selector']['pointer'],value=catalog[h]['value'])
        for a,h in aliases.items() if catalog[h]['selector']['reference']==r['feedback_result']})
        for r in w.rounds if r.get('kind')=='search' and r.get('feedback_result') and r.get('case_id','primary')==getattr(w,'current_case','primary')]
    configure_role(w.host,'design',w.freeze.get('research_instructions',INSTRUCTIONS),phase='research',delivery_tool='research.decide',phase_budget={},
        fact_separation=w.freeze.get('fact_separation',False),
        autonomous_scheduling=True,research_packet=packet,research_records=w.records,result_feedback=w.feedback,
        predecessor_decision=w.previous_decision,latest_tested=w.latest,require_source_binding=True,
        max_batch_backends=2,source_report=w.freeze['common_scientific_input']['source_report'],
        improvement_feedback_content=dict(baseline_facts=w.baseline,execution=None),
        native_store_root=str(w.directory),native_fixed={},memory_identity=w.host.run_id,binding=w.freeze['binding'])
    return packet


def decision(w):
    packet=configure(w);adapter=EvidenceDrivenAdapter();payload=payload_for(w.host,adapter)
    native=[adapter.advertised[t['function']['name']] for t in payload['tools']]
    if native!=['research.decide']:raise ValueError('ACTUAL_NATIVE_SCHEDULING_SCHEMA_NOT_EXPOSED: '+str(native))
    index=len(w.rounds);atomic_json(w.directory/f'round{index}_request.json',dict(packet=packet,payload=payload))
    before=w.store.session(w.host.run_id)['state'].get('handoffs',{}).get('research_decision')
    run_loop(w.host,adapter)
    state=w.store.session(w.host.run_id)['state'];ref=state.get('handoffs',{}).get('research_decision')
    if not ref or ref==before:raise RuntimeError('RESEARCH_DECISION_INCOMPLETE: '+str(state.get('stop_reason')))
    result=w.store.artifact(ref);w.previous_decision=ref
    row=dict(index=index,case_id=getattr(w,'current_case','primary'),kind=result['decision']['action'],request=save(w.store,dict(packet=packet,payload=payload)),
        accepted_decision=ref,decision=result,usage_after_decision=w.store.remaining())
    w.rounds.append(row);persist(w);return row


def execute(w,row):
    d=row['decision']['decision'];action=d['action']
    if d['selected_candidate'] is not None:w.selected=d['selected_candidate']
    if action=='stop':w.status='model_stopped';w.stop_reason=d['stop_reason'];seal_case(w);persist(w);return
    if action in ('control_search','structure_search'):
        plan=row['decision']['search_plan'];record=w.store.artifact(plan)
        source=next(r for r in w.records if r['facts']['candidate']==record['bindings']['subject'])
        w.batch_source=source['facts']['candidate']
        configure_role(w.host,'executor','Execute the accepted immutable research batch only.',phase_budget={});w.host.resume()
        prepare_offline_batch(w.host,plan,mode='live',starting_facts=source['facts'],retained_baseline=w.baseline,historical_results=w.records)
        result=run_live_batch(w.host);ref=save(w.store,result);row.update(kind='search',route=action,result=ref,
            complete=result['status']=='completed' and result.get('fully_evaluated_new_executions',result['fully_evaluated_distinct_changed_configurations'])>0)
        compact=[]
        for candidate in result['candidates']:
            if not candidate.get('execution'):continue
            facts=candidate['execution']['factual_result'];cfg=w.store.artifact(facts['configuration'])['effective']
            if not any(r['facts']['candidate']==facts['candidate'] for r in w.records):
                w.records.append(dict(role='historical_candidate',facts=facts,execution_id=facts['execution_id'],
                    owner_run_id=facts['candidate']['owner_run_id'],execution_scope=execution_scope(cfg),source_store=str(w.directory),
                    receipts=candidate['execution']['receipts'],reuse_reason='New complete feedback-driven supplement evaluation'))
            compact.append(dict(candidate=facts['candidate'],metrics=campaign_metrics(facts),
                source_comparison=compare_results(source['facts'],facts),baseline_comparison=compare_results(w.baseline,facts),
                profile=facts['report']))
        w.latest=result['execution_chronology']['latest_complete_result']
        row['feedback_result']=feedback(w,dict(batch_result=ref,plan=plan,source=source['facts']['candidate'],
            outcomes=compact,chronology=result['execution_chronology'],status=result['status'],stop_reason=result['stop_reason']), 'new_complete_batch_feedback')
        # Archive immutable batch before opening a subsequent model-authored batch.
        with w.store.transaction() as db:
            state=w.store.session(w.host.run_id,db)['state'];batch=state.pop('search_batch',None)
            w.store.event(db,w.host.run_id,'research_batch_archived',result['status'],outputs=[w.store.put(db,batch)])
            w.store.update_state(db,w.host.run_id,state)
        if not row['complete']:w.status='execution_stopped';w.stop_reason=result['stop_reason']
    else:
        request=d['diagnosis'];prior_result=row['decision'].get('prior_diagnostic')
        if row['decision']['duplicate_without_replication']:
            row['feedback_result']=feedback(w,dict(duplicate=True,prior_result=prior_result,
                message='Prior result returned without execution. A new query requires explicit replication justification.'),'duplicate_diagnosis_feedback')
        else:
            source=next(r for r in w.records if r['facts']['candidate']==request['source_candidate'])
            binding=source.get('binding')
            if binding is None:
                from extensions.tendon_family.control_evidence import ControlEvidence
                from extensions.tendon_family.diagnostic_evidence import import_execution
                reader=ControlEvidence(w.store);saved=reader.resolve(source['execution_id'])
                binding=import_execution(reader,source['execution_id'],w.store,w.host.run_id,saved['manifest'])
            configure_role(w.host,'executor','Execute the accepted retained evidence query.',phase_budget={});w.host.resume()
            args=dict(binding=binding,view=request['view'])
            if request['update_ids']:args['update_ids']=request['update_ids']
            receipt=w.host.invoke(dict(request_id=f"research-diagnosis-{row['index']}",tool_id='diagnosis.inspect_evidence',
                tool_version='1.0.0',arguments=args,reason=request['missing_observation'],cache='new'))
            row['diagnosis_receipt']=receipt
            if receipt['execution_status']!='completed':raise RuntimeError('RETAINED_DIAGNOSIS_FAILED: '+str(receipt['error']))
            row['feedback_result']=feedback(w,dict(request=request,result=receipt['output'],
                content=w.store.artifact(receipt['output']),replication_of=prior_result),'retained_diagnosis_feedback')
            with w.store.transaction() as db:
                state=w.store.session(w.host.run_id,db)['state'];state.setdefault('research_diagnostics',{})[row['decision']['diagnostic_key']]=receipt['output']
                w.store.update_state(db,w.host.run_id,state)
    row['usage_after_execution']=w.store.remaining();persist(w)


def export(w):
    from tools.improvement_workflow import archive_store
    EVIDENCE=Path(w.freeze['experiment']['evidence_directory'])
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    for path in w.directory.glob('*.json'):(EVIDENCE/path.name).write_bytes(path.read_bytes())
    archive_store(w.store,EVIDENCE/'store',source_stores=[Path(r['source_store']) for r in w.records if r['source_store']!=str(w.directory)])
    searches=[r for r in w.rounds if r.get('kind')=='search' and r.get('complete')]
    cases=[]
    for case_id in sorted({r.get('case_id','primary') for r in w.rounds}):
        steps=[r for r in searches if r.get('case_id','primary')==case_id];binding=False
        if len(steps)>=2:
            first=steps[0]['feedback_result'];second=steps[1]['decision']['batch_plan']
            binding=any(s['reference']==first for s in second['bindings']['evidence_selectors'])
        stopped=any(r.get('case_id','primary')==case_id and r['decision']['decision']['action']=='stop' for r in w.rounds)
        cases.append(dict(case_id=case_id,real_search_batches=len(steps),feedback_bound_to_second_plan=binding,
            final_model_stop=stopped,core_multibatch_acceptance=len(steps)>=2 and binding and stopped))
    chronology=execution_chronology(w.store,w.records)
    embedded=sum(r['facts']['control_updates'] for r in w.records if r['execution_id'] in
        {a['candidate']['execution_id'] for a in chronology['attempts']})
    state=w.store.session(w.host.run_id)['state']
    review_path=w.directory/'acceptance_audit.json'
    review=read(review_path) if review_path.exists() else {}
    core=any(c['core_multibatch_acceptance'] for c in cases)
    factual_review=review.get('factual_interpretations_consistent')
    accepted=core and (not w.freeze.get('fact_separation') or factual_review is True)
    supplement_status=('closed' if accepted else 'open_factual_reasoning_errors' if core and factual_review is False
        else 'open_review_pending' if core else 'open_incomplete_autonomy_coverage')
    delivery=dict(status=w.status,stop_reason=w.stop_reason,implementation_checks='see focused_checks.json',
        real_search_batches=len(searches),cases=cases,sealed_cases=w.sealed_cases,
        core_multibatch_acceptance=core,factual_interpretations_consistent=factual_review,
        overall_supplement_acceptance=accepted,acceptance_review='acceptance_audit.json' if review else None,
        feedback_bound_to_second_plan=any(c['feedback_bound_to_second_plan'] for c in cases),
        selected_candidate=w.selected,latest_execution=chronology['latest_execution'],
        latest_completed_evaluation=chronology['latest_completed_evaluation'],latest_complete_result=chronology['latest_complete_result'],
        execution_chronology=chronology,current_batch_source=getattr(w,'batch_source',None),
        retained_baseline=w.baseline['candidate'],usage=w.store.remaining(),
        corrections=dict(total=state.get('protocol_corrections_used',0),consecutive=state.get('protocol_corrections_consecutive',0)),
        standalone_numerical_operations=0,embedded_controller_updates=embedded,
        attempts_without_complete_update_count=[a['candidate']['execution_id'] for a in chronology['attempts'] if not any(r['execution_id']==a['candidate']['execution_id'] for r in w.records)],
        engineering_interventions=w.repairs,
        physical_improvement='Individual new sealed profiles; no required superiority criterion' if searches else 'Not evaluated: zero new complete search evaluations',
        realtime='No realtime success established',
        model_reasoning='Citations validated; causal explanations remain subject to evidence review' if w.rounds else 'None: no accepted live model decision',
        selection_role='Model-selected complete deliverable' if w.status=='model_stopped' else 'Retained historical incumbent; no new final model selection',
        milestones=dict(M4_historical='closed',M4_supplement=supplement_status,M5='open'),revision=revision())
    atomic_json(EVIDENCE/'delivery.json',delivery)
    atomic_json(EVIDENCE/'sha256_manifest.json',{p.relative_to(EVIDENCE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in EVIDENCE.rglob('*') if p.is_file() and p.name!='sha256_manifest.json'})
    print(json.dumps(delivery),flush=True)


def live():
    from examples.gvs_nmpc_route_experiment import load_credential
    w=restore();frozen=w.freeze['implementation']
    if revision()['files']!=frozen['files'] or revision()['stable_controller']!=frozen['stable_controller']:
        raise ValueError('FROZEN_IMPLEMENTATION_CHANGED_REGISTER_REPAIR_BEFORE_RESUME')
    if w.status in ('model_stopped','execution_stopped'):raise ValueError('FROZEN_STOP_NO_CONTINUATION')
    load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
    start=time.monotonic();w.status='running'
    try:
        while True:
            while w.status=='running':
                row=decision(w);execute(w,row)
            if not activate_fallback(w):break
    except Exception as exc:
        w.status='failed';w.stop_reason=str(exc)
        atomic_json(w.directory/'failure.json',dict(type=type(exc).__name__,message=str(exc),usage=w.store.remaining()))
        print('STOP',w.stop_reason,flush=True)
    persist(w);atomic_json(w.directory/'engineering_wall.json',dict(live_orchestration_elapsed_s=time.monotonic()-start,
        convention='Execution time already charged in receipts; this wall measurement is not added twice'))
    export(w)


def repair_projection():
    """Refresh stale administrative dependencies through the existing migration."""
    from tools.platform_store import zero
    w=restore();old=w.host;failure=read(RUN/'failure.json')
    if w.repairs or w.rounds or w.store.remaining()['used']['model_calls']:
        raise ValueError('ONE_PRE_REQUEST_REPAIR_ONLY_NO_RESET')
    if not failure['message'].startswith('DEPENDENCIES_CHANGED:'):
        raise ValueError('REPAIR_REQUIRES_DEMONSTRATED_PROJECTION_DEFECT')
    atomic_json(RUN/'pre_repair_freeze.json',w.freeze)
    snapshot=w.store.session(old.run_id)['snapshot'];inp=deepcopy(snapshot['input'])
    reservation,_=w.store.reserve(old.run_id,'research-projection-repair1',digest(failure),'engineering',
        {**zero(),'tool_calls':1,'wall_s':60.})
    started=time.monotonic()
    # Restore the inherited workflow host selector for the shared migration.
    del w.host;w.hosts={'shared':old}
    new=prior.migrate_planning_host(w,'research-projection-repair1',input_override=inp);w.host=new
    if execution_scope(inp)!=execution_scope(w.store.session(new.run_id)['snapshot']['input']):
        raise ValueError('REPAIR_CHANGED_SCIENCE')
    configure(w);payload=payload_for(new,EvidenceDrivenAdapter());new.resume()
    change=dict(failure=failure,previous_host=old.run_id,new_host=new.run_id,scientific_conditions_changed=False,
        budget_reset=False,provider_attempts_before=0,backend_attempts_before=0,completed_backend_replayed=False,
        remedy='Existing migrate_planning_host creates a current immutable dependency snapshot and carries aliases, role state and cumulative recovery in the same project.',
        serialized_payload_identity=digest(payload),revision=revision())
    receipt=w.store.complete(reservation,dict(request_id='research-projection-repair1',execution_id=reservation['execution_id'],
        caller='engineering',tool_id='engineering.research_projection',tool_version='1.0.0',execution_status='completed',charged=zero()),change,time.monotonic()-started)
    w.repairs=1;w.status='prepared_after_repair';w.stop_reason=None
    w.freeze.update(research_host=new.run_id,implementation=revision())
    persist(w);atomic_json(RUN/'engineering_intervention1.json',dict(change=change,receipt=receipt))
    print(json.dumps(dict(repair='completed',charge=receipt['charged'],science_unchanged=True)),flush=True)


if __name__=='__main__':
    successor='--successor' in sys.argv
    if successor:RUN=SUCCESSOR_RUN;EVIDENCE=SUCCESSOR_EVIDENCE
    if sys.argv[1]=='prepare':prepare(RUN,successor=successor)
    elif sys.argv[1]=='live':live()
    elif sys.argv[1]=='export':export(restore())
    elif sys.argv[1]=='repair-projection':repair_projection()
    elif sys.argv[1]=='seal':
        w=restore()
        if w.store.remaining()['used']['model_calls'] or w.rounds:raise ValueError('CANNOT_RESEAL_AFTER_LIVE_DECISION')
        w.freeze['implementation']=revision();persist(w)
        atomic_json(RUN/'freeze_seal.json',dict(identity=digest(w.freeze),before_first_live_request=True))
