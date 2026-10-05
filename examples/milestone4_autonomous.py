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
from tools.study_history import study_history
from tools.structural_study import research_planning_input
from tools.settling_campaign import campaign_metrics,compare_results
from extensions.tendon_family.gvs_profile import execution_scope

RUN=ROOT/'runs/milestone4_autonomous_20261005'
EVIDENCE=ROOT/'evidence/milestone4_autonomous_20261005'
LIMITS=dict(model_calls=24,tool_calls=60,backend_solves=4,worker_calls=0,wall_s=9000.)
FILES=('examples/milestone4_autonomous.py','tools/research_scheduler.py','tools/platform_search.py',
    'tools/structural_study.py','tools/diagnostic_reference_adapter.py','tools/platform_models.py',
    'schemas/platform_handoff.py','extensions/platform/manifest.py','tests/test_research_scheduler.py')
INSTRUCTIONS='''Choose control_search,structure_search,diagnosis,or stop yourself from research_packet.capabilities. No stage or round forces a route. The research question concerns the observed holding-speed acceptance loss at holding weight .10 versus the known passing .05/.05 incumbent on near .16/far .11/scale .95/compliant, and whether affordable further control or structural evidence is useful. The incumbent is already successful. You may retain it and stop. Engineering multibatch coverage is measured separately and must not force scientific continuation. Explain actual feedback and cite current F aliases, including a latest-feedback alias. Select any verified complete source from history; primary is a starting question, not a forced source. After a search result explain which new observations support your next action. Citation validity does not certify a causal explanation.
Use exactly one research.decide native tool with ordinary structured fields. For search embed ONE SearchBatchPlan object. Use exact source_candidate and predecessor_decision from packet; evidence uses F aliases including current feedback. Allowed variables are the current builder paths shown in capabilities; keep undeclared fields fixed. Both installed search.family_explicit@1.0.0 and search.family_coordinate@1.0.0 are legal. Explicit method has null step and candidates containing precisely variables; coordinate has step and null candidates. Source values must lie in declared domains. Weights zero or >=.0001 through 1; structural domains use the frozen controller-7 profile; material choices require explicit enumeration. fixed_controller=controller.gvs_nmpc@7.0.0; fixed_conditions include robot,task,acceptance,controller_implementation,other_numerical_settings. Objectives joint_reach_holding_acceptance,terminal_error_m,holding_max_error_m,holding_max_speed_m_s (optional complete_update_s); constraints frozen_acceptance,force_bounds,finite_valid_execution; verification candidate.apply,simulation.run,evaluation.run,control.profile_report,bound_comparison,diagnostic_revision. Declare hypothesis,rationale,weakening observations,fidelity limits and exit conditions. max_backend_attempts and target_changed_configurations explicit, at most two backend attempts per batch (frozen allocation preserving feedback/delivery capacity). max_candidates may include a reused start. planned_budget covers computed complete execution plus delivery requirement, within remaining totals; backend_solves equals batch cap,workers=0. No automatic extra control adaptation after a structure change.
For diagnosis identify competing hypotheses,existing evidence,missing observation,outcome_actions,max_wall_s and exit_condition. Only retained prediction/plans/motion queries are executable here. Numerical saved-state work has an explicit capability gap; do not request unsupported computations. Duplicate queries return prior evidence without execution unless replication_reason justifies a changed hypothesis or repeated measurement. For stop provide stop_reason,reasoning,evidence and selected_candidate as an exact complete identity or null. No physical,hardware,realtime,global-optimum or causal success claim follows merely from acceptance. Keep interpretation concise.'''


def revision():
    return dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        files={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FILES if (ROOT/p).exists()},
        stable_controller={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
            ('extensions/tendon_family/gvs_nmpc.py','extensions/tendon_family/gvs_trajectory.py','extensions/tendon_family/gvs_profile.py')})


def compact_history(w):
    history=study_history(w.store,w.records,retained_baseline=w.baseline['candidate'],latest_tested=w.latest,
        selection=w.selected)
    for row in history['rows']:
        row.pop('physical_structure',None);row.pop('references',None)
    return history


def feedback(w,value,kind):
    ref=save(w.store,value);envelope=save(w.store,dict(result=ref,kind=kind))
    handover(w.host,ref,value,origin=dict(kind=kind),kind='performed_check_result')
    w.feedback=envelope;return ref


def prepare(directory=RUN):
    from tools.runtime_identity import require_softagent_runtime
    from examples.stage356_milestone2 import scientific_bundle,import_common
    directory=Path(directory)
    if (directory/'scheduler_state.json').exists():raise ValueError('EXISTING_CAMPAIGN_USE_RESUME_NO_RESET')
    old=Store(continuation.RUN);old_freeze=read(continuation.RUN/'freeze.json')
    config=deepcopy(old_freeze['experiment']);config.update(evidence_directory=str(EVIDENCE),
        project_prefix='gvs-m4-autonomous',provider_freeze=str(continuation.RUN/'freeze.json'),adapter_version='6.0.0',
        authorization_source='User 2026-10-05 attachment c93a3290: new M4 supplement 24 provider/60 workflow/4 backend/9000 charged seconds/12 standalone numerical operations/0 workers and subagents; live DeepSeek,simulations,one narrow repair,resume,commit/push authorized. Historical STOP/NO_GO preserved.')
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
    from extensions.tendon_family.control_evidence import ControlEvidence
    for path,note in compatibility_notes.items():
        row=review.setdefault(path,dict(current_hash=hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),historical_hashes=[],reason=note))
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
    primary=next(r for r in w.records if r['execution_id'].startswith('110dc2c9'))
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
    feedback(w,dict(primary=primary['facts']['candidate'],metrics=campaign_metrics(primary['facts']),
        comparison_to_incumbent=compare_results(incumbent['facts'],primary['facts']),source_profile=primary['facts']['report']), 'verified_primary_feedback')
    persist(w);atomic_json(directory/'freeze_seal.json',dict(identity=digest(w.freeze),before_first_live_request=True))
    return w


def persist(w):
    atomic_json(w.directory/'freeze.json',w.freeze)
    atomic_json(w.directory/'scheduler_state.json',dict(records=w.records,baseline=w.baseline,latest=w.latest,selected=w.selected,
        previous_decision=w.previous_decision,feedback=w.feedback,rounds=w.rounds,repairs=w.repairs,status=w.status,stop_reason=w.stop_reason))


def restore(directory=RUN):
    freeze=read(Path(directory)/'freeze.json');w=prior.MilestoneWorkflow(directory,'single_context',experiment=freeze['experiment'])
    w.freeze=freeze;w.host=Host(directory,freeze['research_host']);w.project=freeze['project_id']
    for k,v in read(Path(directory)/'scheduler_state.json').items():setattr(w,k,v)
    return w


def configure(w):
    cap=capabilities(w.store,w.host.run_id,w.records);state=w.store.session(w.host.run_id)['state']
    aliases=ensure_aliases(state)['aliases'];catalog=state.get('fact_catalog',{})
    latest_ref=w.store.artifact(w.feedback)['result']
    current={a:dict(pointer=catalog[h]['selector']['pointer'],value=catalog[h]['value']) for a,h in aliases.items()
        if catalog[h]['selector']['reference']==latest_ref}
    packet=dict(history=compact_history(w),primary=w.freeze['primary'],incumbent=w.freeze['incumbent'],
        current_feedback=dict(reference=latest_ref,content=w.store.artifact(latest_ref),aliases=current),
        predecessor_decision=w.previous_decision,capabilities=cap,scope=w.freeze['profile'],
        engineering_coverage=dict(completed_search_batches=sum(r.get('kind')=='search' and r.get('complete') for r in w.rounds),
            target='Two separate real search batches, later plan explicitly referencing actual first-batch evidence. This does not override voluntary stopping.'),
        corrections=dict(total=state.get('protocol_corrections_used',0),consecutive=state.get('protocol_corrections_consecutive',0)))
    configure_role(w.host,'design',INSTRUCTIONS,phase='research',delivery_tool='research.decide',phase_budget={},
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
    row=dict(index=index,kind=result['decision']['action'],request=save(w.store,dict(packet=packet,payload=payload)),
        accepted_decision=ref,decision=result,usage_after_decision=w.store.remaining())
    w.rounds.append(row);persist(w);return row


def execute(w,row):
    d=row['decision']['decision'];action=d['action']
    if d['selected_candidate'] is not None:w.selected=d['selected_candidate']
    if action=='stop':w.status='model_stopped';w.stop_reason=d['stop_reason'];persist(w);return
    if action in ('control_search','structure_search'):
        plan=row['decision']['search_plan'];record=w.store.artifact(plan)
        source=next(r for r in w.records if r['facts']['candidate']==record['bindings']['subject'])
        configure_role(w.host,'executor','Execute the accepted immutable research batch only.',phase_budget={});w.host.resume()
        prepare_offline_batch(w.host,plan,mode='live',starting_facts=source['facts'],retained_baseline=w.baseline,historical_results=w.records)
        result=run_live_batch(w.host);ref=save(w.store,result);row.update(kind='search',route=action,result=ref,
            complete=result['status']=='completed' and result['fully_evaluated_distinct_changed_configurations']>0)
        compact=[]
        for candidate in result['candidates']:
            if not candidate.get('execution'):continue
            facts=candidate['execution']['factual_result'];cfg=w.store.artifact(facts['configuration'])['effective']
            if not any(r['facts']['candidate']==facts['candidate'] for r in w.records):
                w.records.append(dict(role='historical_candidate',facts=facts,execution_id=facts['execution_id'],
                    owner_run_id=facts['candidate']['owner_run_id'],execution_scope=execution_scope(cfg),source_store=str(w.directory),
                    receipts=candidate['execution']['receipts'],reuse_reason='New complete feedback-driven supplement evaluation'))
            w.latest=facts['candidate'];compact.append(dict(candidate=facts['candidate'],metrics=campaign_metrics(facts),
                source_comparison=compare_results(source['facts'],facts),baseline_comparison=compare_results(w.baseline,facts),
                profile=facts['report']))
        row['feedback_result']=feedback(w,dict(batch_result=ref,plan=plan,source=source['facts']['candidate'],
            outcomes=compact,status=result['status'],stop_reason=result['stop_reason']), 'new_complete_batch_feedback')
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
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    for path in w.directory.glob('*.json'):(EVIDENCE/path.name).write_bytes(path.read_bytes())
    archive_store(w.store,EVIDENCE/'store',source_stores=[Path(r['source_store']) for r in w.records if r['source_store']!=str(w.directory)])
    searches=[r for r in w.rounds if r.get('kind')=='search' and r.get('complete')]
    binding=False
    if len(searches)>=2:
        first=searches[0]['feedback_result'];second=searches[1]['decision']['batch_plan']
        binding=any(s['reference']==first for s in second['bindings']['evidence_selectors'])
    state=w.store.session(w.host.run_id)['state']
    delivery=dict(status=w.status,stop_reason=w.stop_reason,implementation_checks='see focused_checks.json',
        real_search_batches=len(searches),core_multibatch_acceptance=len(searches)>=2 and binding and w.status=='model_stopped',
        feedback_bound_to_second_plan=binding,selected_candidate=w.selected,latest_execution=w.latest,
        retained_baseline=w.baseline['candidate'],usage=w.store.remaining(),
        corrections=dict(total=state.get('protocol_corrections_used',0),consecutive=state.get('protocol_corrections_consecutive',0)),
        standalone_numerical_operations=0,embedded_controller_updates=35*w.store.remaining()['used']['backend_solves'],
        engineering_interventions=w.repairs,physical_improvement='Individual sealed profiles; no required superiority criterion',
        realtime='No realtime success established',model_reasoning='Citations validated; causal explanations remain subject to evidence review',
        milestones=dict(M4_historical='closed',M4_supplement='separate acceptance',M5='open'),revision=revision())
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
        while w.status=='running':
            row=decision(w);execute(w,row)
    except Exception as exc:
        w.status='failed';w.stop_reason=str(exc)
        atomic_json(w.directory/'failure.json',dict(type=type(exc).__name__,message=str(exc),usage=w.store.remaining()))
        print('STOP',w.stop_reason,flush=True)
    persist(w);atomic_json(w.directory/'engineering_wall.json',dict(live_orchestration_elapsed_s=time.monotonic()-start,
        convention='Execution time already charged in receipts; this wall measurement is not added twice'))
    export(w)


if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='live':live()
    elif sys.argv[1]=='export':export(restore())
    elif sys.argv[1]=='seal':
        w=restore()
        if w.store.remaining()['used']['model_calls'] or w.rounds:raise ValueError('CANNOT_RESEAL_AFTER_LIVE_DECISION')
        w.freeze['implementation']=revision();persist(w)
        atomic_json(RUN/'freeze_seal.json',dict(identity=digest(w.freeze),before_first_live_request=True))
