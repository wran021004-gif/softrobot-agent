"""Bounded native first-study pilot. Historical campaigns are read-only sources."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import argparse
import hashlib
import json
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.state_io import read,atomic_json,digest
from tools.platform_store import Store,plain,zero
from tools.platform_host import Host
from tools.diagnostic_workflow import save
from tools.diagnostic_facts import handover
from tools.diagnostic_revision import ensure_aliases
from tools.platform_diagnosis_coordinator import configure_role
from tools.platform_models import payload_for,run_loop,tool_naming_policy,READABLE_TOOL_NAMING
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from tools.research_scheduler import capabilities
from tools.research_spec import load_spec
from tools.parameter_catalog import effective_catalog
from tools.research_tasks import assemble_acceptance
from tools.acceptance_definitions import resolve_acceptance
from tools.study_history import study_history,execution_chronology
from tools.context_assembly import (EvidenceArchive,research_authority,create_working_state,
    update_working_state,persist_working_state,assemble_working_context)
from extensions.tendon_family.gvs_profile import execution_scope
from examples import milestone4_autonomous as reusable

CONFIG=read(ROOT/'configs/research/native_pilot_v1.json')
VERSION=CONFIG['version']
CAMPAIGN=CONFIG['campaign_id']
DEFAULT=ROOT/'runs'/CAMPAIGN
EXPORT=ROOT/'evidence'/CAMPAIGN
LIMITS=CONFIG['limits']
FILES=('examples/research_model_v1.py','examples/milestone4_autonomous.py',
    'configs/research/native_pilot_v1.json',
    'tools/research_scheduler.py','tools/platform_search.py','tools/live_batch_execution.py',
    'tools/context_assembly.py','tools/diagnostic_reference_adapter.py')
INSTRUCTIONS=reusable.SUCCESSOR_INSTRUCTIONS+'''
This is a new first-study pilot. research_packet.study overrides old example domains/background: select only from its frozen eight-variable catalog. structure_search accepts any joint structural/control subset with at least one structural variable; all selected values form one candidate per proposal and ONE v7 closed-loop execution. No inner control search. control_search selects control variables only. Coordinate generates numerical continuous proposals; explicit evaluates your own finite sequence and is required for material choices. Material scenarios are numerical Young-modulus choices, not commercial materials.
The coding agent has frozen nominal seed17 development BEFORE outcomes; other four cases remain specified but unavailable for execution in this pilot. Exposed near_z_plus evidence is a subsequent event, never pending and never a matched nominal reference. Keep exact common starting point; use exact source_candidate identities from history. You author hypothesis, variables, method, values/allocation and subsequent decisions. Explain applicable mathematical support (or its absence/limitations), what outcomes weaken the judgment, allocation and exit conditions. Existing ask/tell algorithms generate candidate values, not a proof of physical feasibility or mathematical sensitivity. M5 negative prediction findings prohibit using those forecasts to exclude candidates; no new standalone calculation is installed. Retained prediction/plans/motion READS are available within two total diagnosis decisions.
Use authoritative research.task_acceptance in outcome aliases: terminal reach, holding position, holding MAXIMUM speed and full coverage, applied input bounds, valid complete execution, zero solver errors. Missing/incomplete/invalid is unknown, not physical failure. Computation/deadlines are separate; offline acceptance does not require real time. Historical evidence keeps its original labels. No robust improvement, fixed-baseline superiority or compression benefit follows from this pilot. Keep the incumbent on unsupported superiority; you may stop early without another batch. After new results, cite current feedback before proposing any later plan. STOP also supplies your final bounded interpretation; a separate report model is not installed. At most two attempts per batch, four TOTAL including references/repetitions/failures. No retries to pass. Preserve capacity for feedback and a final decision. Use full exact observed values in observations; concise conditional prose.
'''


def revision():
    return dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        files={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FILES},
        stable_controller=reusable.revision()['stable_controller'])


def archive(w):
    if not hasattr(w,'context_archive'):
        scope=dict(context_id=w.host.run_id,role='design',binding=w.freeze['binding'])
        saved=w.directory/'working_state.json'
        w.context_archive=(EvidenceArchive.from_manifest(ROOT/read(saved)['source_manifest'],scope=scope,stores=(w.store,))
            if saved.exists() else EvidenceArchive(w.directory/'context_assembly',scope=scope,stores=(w.store,)))
    return w.context_archive


def copy_references(source,destination,value,seen=None):
    seen=set() if seen is None else seen
    if isinstance(value,dict):
        if set(value)=={'artifact_id','media_type'} and isinstance(value['artifact_id'],str) and isinstance(value['media_type'],str):
            if value['artifact_id'] in seen:return
            seen.add(value['artifact_id'])
            try:body=source.artifact(value,raw=True)
            except ValueError:
                destination.artifact(value);return
            with destination.transaction() as db:
                if plain(destination.put(db,body,value['media_type']))!=value:raise ValueError('IMPORT_CHANGED_BYTES')
            if value['media_type']=='application/json':copy_references(source,destination,json.loads(body),seen)
        else:
            for v in value.values():copy_references(source,destination,v,seen)
    elif isinstance(value,list):
        for v in value:copy_references(source,destination,v,seen)


def historical(w,root,eid,role):
    from extensions.tendon_family.control_evidence import ControlEvidence
    from extensions.tendon_family.diagnostic_evidence import import_execution
    from extensions.tendon_family.delivery_facts import bound_result_facts
    source=Store(ROOT/root);reader=ControlEvidence(source);owned=reader.resolve(eid)
    imported=import_execution(reader,eid,w.store,w.host.run_id,owned['manifest'])
    receipts={}
    with source.connect(True) as db:
        for row in db.execute('SELECT receipt FROM calls WHERE receipt IS NOT NULL'):
            r=json.loads(row[0]);stage={'simulation.run':'simulation','evaluation.run':'evaluation','control.profile_report':'profile'}.get(r['tool_id'])
            if not stage or not r.get('output'):continue
            data=source.artifact(r['output']);detail=data.get('detail',data)
            linked=r['execution_id'] if stage=='simulation' else detail.get('source_execution_id' if stage=='evaluation' else 'execution_id')
            if linked==eid:
                if stage in receipts:raise ValueError('NONUNIQUE_HISTORICAL_RECEIPT')
                receipts[stage]=r
    if set(receipts)!={'simulation','evaluation','profile'} or any(r['execution_status']!='completed' for r in receipts.values()):
        raise ValueError('HISTORICAL_COMPLETE_RECEIPTS_REQUIRED')
    profile=source.artifact(receipts['profile']['output']);detail=profile['detail'];cfg=detail['configuration']
    candidate=dict(candidate_id=source.artifact(receipts['evaluation']['output'])['candidate_id'],
        owner_run_id=owned['owner'],execution_id=eid,configuration=cfg)
    binding=dict(reference=receipts['profile']['output'],owner_run_id=owned['owner'],execution_id=eid,
        request_id=receipts['profile']['request_id'])
    facts=bound_result_facts(source,dict(profile_report=binding,evaluation=receipts['evaluation']['output'],simulation=receipts['simulation']),candidate)
    for value in (facts,profile,cfg):copy_references(source,w.store,value)
    effective=w.store.artifact(cfg)['effective']
    acceptance=assemble_acceptance(effective,source.artifact(receipts['evaluation']['output']),profile,
        evaluation_reference=receipts['evaluation']['output'],profile_reference=receipts['profile']['output'],motion=source.artifact(detail['motion']))
    return dict(role=role,facts=facts,acceptance=acceptance,execution_id=eid,owner_run_id=owned['owner'],
        execution_scope=execution_scope(effective),source_store=str(source.root),binding=imported,receipts=receipts,
        reuse_reason='Exact archived observation; original implementation/charges retained. Not a fresh matched reference.',
        implementation=dict(commit=source.session(owned['owner'])['snapshot']['project_commit'],
            dependencies={k:digest(v) for k,v in source.session(owned['owner'])['snapshot']['dependencies'].items()}))


RELEVANT_HISTORY = {
    '91c3ba1b01d6499fb26df8f95409401b':'retained_baseline',
    'e3876a1d289f41f08d46c96202f1da0c':'matching_holding_075_failure',
    '110dc2c9c1d642dcb018664a65c62c30':'matching_holding_100_failure',
    'bebcfd47274940fb88a55ce5a2457c4c':'zero_holding_weight_passing_counterexample',
    '312ef97407b34ff28905e883a947f475':'lower_holding_weight_failure_counterexample',
    '148a2a290daa440f9b966f4d5cee4b5f':'joint_weights_passing_confounded_counterexample',
    '1ffdcbc4f93f4dc4bb16a807c7b4056b':'intermediate_holding_weight_failure',
}


def relevant_history(w):
    """Bounded explicit evidence selection; no recency or success-only filter."""
    manifest='runs/milestone4_autonomous_20261006/scheduler_state.json'
    candidates=read(ROOT/manifest)['records']; selected=[]; considered=[]
    for r in candidates:
        eid=r['execution_id']; role=RELEVANT_HISTORY.get(eid)
        considered.append(dict(execution_id=eid,source_store=r['source_store'],selected=bool(role),
            reason=role or 'Outside bounded nominal same-robot weight neighborhood; not evidence of absence'))
        if role:selected.append(historical(w,r['source_store'],eid,role))
    if {r['execution_id'] for r in selected}!=set(RELEVANT_HISTORY):raise ValueError('RELEVANT_HISTORY_UNRESOLVED')
    selected.sort(key=lambda r:(r['role']!='retained_baseline',r['execution_id']))
    return selected,dict(selection_version='native_history_coverage@1.1.0',source_manifest=manifest,
        considered=considered,selected_execution_ids=[r['execution_id'] for r in selected],
        limitations=['Targeted saved manifest only; no full repository audit or exhaustive history claim.',
            'Imported executions retain original source event chronology; presentation order is not chronology.',
            'Builder/implementation boundaries do not turn scientific overlap into result-reuse eligibility.'])


def persist(w):
    reusable.persist(w)
    if getattr(w,'working',None) is not None:
        ref=persist_working_state(w.working,store=Store(w.directory/'working_archive'),archive=archive(w))
        atomic_json(w.directory/'working_state.json',dict(reference=ref,state=w.working,source_manifest=archive(w).manifest()))


def restore(directory):
    directory=Path(directory);freeze=read(directory/'freeze.json')
    w=SimpleNamespace(directory=directory,store=Store(directory),freeze=freeze,host=Host(directory,freeze['research_host']))
    for k,v in read(directory/'scheduler_state.json').items():setattr(w,k,v)
    if (directory/'working_state.json').exists():
        from tools.context_assembly import restore_working_state
        scope=dict(context_id=w.host.run_id,role='design',binding=w.freeze['binding'])
        w.working,w.context_archive=restore_working_state(read(directory/'working_state.json')['reference'],
            store=Store(directory/'working_archive'),scope=scope,stores=(w.store,))
    else:w.working=None
    return w


def prepare(directory=DEFAULT, *, offline_fixture=False):
    spec=load_spec();directory=Path(directory)
    store=Store(directory)
    if store.db.exists():raise ValueError('EXISTING_CAMPAIGN_NO_RESET')
    # A single assignment identity cannot be minted again by choosing another directory.
    grant=CAMPAIGN if not offline_fixture else 'engineering-native-fixture-'+digest(str(directory.resolve()))[:16]
    budget=LIMITS if not offline_fixture else {**LIMITS,'model_calls':0,'backend_solves':0}
    store.create(dict(project_id=grant,grant_id=grant,budget=budget,
        authorization_source='User attachment ddf1f248, 2026-10-06: one new cumulative native pilot, <=4 backend attempts, real configured model, commit and normal push.',exclusive_resources={'mujoco':1}))
    model=deepcopy(spec['comparison_groups']['model_configuration'])
    bindings={'research.decide':'1.0.0','diagnosis.inspect_evidence':'1.0.0'}
    model['tool_naming']=tool_naming_policy(bindings,READABLE_TOOL_NAMING)
    inp=deepcopy(spec['execution_template']);inp['run_id']=CAMPAIGN+'-research'
    inp['policy'].update(budget=LIMITS,model=model,route=None,allowed_tools=[],tool_bindings=bindings)
    host=Host(directory,inp['run_id']);host.create(inp)
    w=SimpleNamespace(directory=directory,store=store,host=host,working=None,rounds=[],repairs=0,
        status='prepared',stop_reason=None,batch_source=None,current_case='nominal',sealed_cases=[])
    reservation,_=store.reserve(host.run_id,'pilot-preparation',digest(spec),'preparation',{**zero(), 'tool_calls':1,'wall_s':120.})
    started=time.monotonic()
    retained=read(ROOT/spec['source']['store_root']/'scheduler_state.json')
    original=next(r for r in retained['records'] if r['facts']['candidate']==spec['source']['candidate'])
    incumbent=historical(w,original['source_store'],spec['source']['candidate']['execution_id'],'retained_baseline')
    if incumbent['facts']['candidate']!=spec['source']['candidate']:raise ValueError('EXACT_INCUMBENT_MISMATCH')
    with store.transaction() as db:
        state=store.session(host.run_id,db)['state'];state['fact_scope']=dict(project=grant,binding=incumbent['binding'])
        store.update_state(db,host.run_id,state)
    final=historical(w,'runs/research_shared_path_v11_approval_20261006','8b8ce2691fc24b3392ff5e7fa4905ba4','subsequent_development_event')
    w.records,coverage=relevant_history(w)
    w.baseline=incumbent['facts'];w.latest=None;w.selected=spec['source']['candidate']
    source_ref=save(store,dict(specification_identity=digest(spec),incumbent=spec['source']['candidate']))
    w.previous_decision=source_ref
    w.freeze=dict(version=VERSION,project_id=grant,research_host=host.run_id,limits=budget,offline_fixture=offline_fixture,
        primary=w.selected,incumbent=w.selected,binding=incumbent['binding'],source_report=source_ref,
        provider_configuration=model,implementation=revision(),parameter_catalog=effective_catalog(inp),
        specification_identity=digest(spec),spec_path='configs/research/reach_hold_v1_1.json',
        profile=spec['boundaries'],max_batch_backends=CONFIG['max_batch_backends'],
        standalone_numerical_limit=CONFIG['standalone_numerical_operations'],diagnosis_limit=CONFIG['retained_query_decisions'],
        allocation=dict(execution_case='nominal',seed=17,available_development_cases=['nominal'],
            deferred_cases=[c['case_id'] for c in spec['cases'] if c['case_id']!='nominal'],
            rationale='Nominal source task permits existing native source-bound batch execution without modifying its scientific settings. Four attempts cannot complete the ten-slot matched suite. Exposed near_z_plus outcome supplied as a subsequent event.',
            comparison='Fresh references/repetitions consume the same four slots; no unmatched robustness/superiority claim.'),
        budget_derivation=dict(backend='4*(900 simulation+30 evaluation+60 profile+5 apply)=3980 seconds; 16 operations',
            native='12 request ceiling covers initial, feedback decisions, two retained-read decisions, cumulative four protocol corrections, one length recovery and delivery capacity; each reserves configured timeout, at most 900s on length recovery',
            preparation='1 operation /120s',diagnosis='<=2 reads /180s each',
            delivery='existing batch requirement protects 4 requests/4 operations/600s; full request reservations still apply',
            total='3980 +12*900 +120 +2*180 =15260 <16000; 16+12+2+1+4=35 <40'),
        correction_policy=model['protocol_recovery'],length_recovery=model['length_recovery'],
        formal_allocation_untouched=True,protected_M5_budget_transferred=False,workers=0,subagents=0,
        termination=['voluntary model STOP','material/unknown execution failure','insufficient complete reservation','cumulative request/correction ceiling'],
        task_acceptance=spec['acceptance'],study_question=spec['question'],frozen_cases=spec['cases'],
        initial_state_mapping=spec['initial_state_mapping'],common_scientific_input=dict(acceptance=resolve_acceptance(inp)),
        subsequent_event=final,
        history_coverage=coverage,
        m5_feedback=dict(source='docs/milestone5_control_successor.md',text=(ROOT/'docs/milestone5_control_successor.md').read_text(encoding='utf8'),
            scope='Sealed negative controller/prediction evidence; no screening authority, no v8 adoption or protected allocation.'),
        experiment=dict(evidence_directory=str(EXPORT)))
    reusable.feedback(w,dict(status='prepared',incumbent=dict(candidate=w.selected,acceptance=incumbent['acceptance']),
        subsequent_event=dict(candidate=final['facts']['candidate'],acceptance=final['acceptance'],implementation=final['implementation'],
            case_id='near_z_plus',seed=17,matched_nominal_reference=False,completed=True),
        question=spec['question'],limitations=spec['uncertainty']), 'frozen_study_and_subsequent_event')
    store.complete(reservation,dict(request_id='pilot-preparation',execution_id=reservation['execution_id'],caller='preparation',
        tool_id='engineering.research_preparation',tool_version='1.0.0',execution_status='completed',charged=zero()),
        dict(source=source_ref,exact_incumbent=True,subsequent_event_completed=True),time.monotonic()-started)
    configure(w);persist(w)
    atomic_json(directory/'freeze_seal.json',dict(identity=digest(w.freeze),before_first_live_request=True))
    return w


def configure(w):
    if w.freeze.get('decision_only'):
        with w.store.transaction() as db:
            state=w.store.session(w.host.run_id,db)['state']
            state.setdefault('role_context',{}).update(decision_only=True)
            w.store.update_state(db,w.host.run_id,state)
    cap=capabilities(w.store,w.host.run_id,w.records)
    if sum(r['decision']['decision']['action']=='diagnosis' for r in w.rounds)>=w.freeze['diagnosis_limit']:
        cap['legal'].pop('diagnosis',None);cap['unavailable']['diagnosis']='Frozen two-read diagnostic ceiling reached'
    state=w.store.session(w.host.run_id)['state'];aliases=ensure_aliases(state)['aliases'];catalog=state.get('fact_catalog',{})
    ref=w.store.artifact(w.feedback)['result']
    def alias_view(reference):
        return {a:dict(pointer=catalog[h]['selector']['pointer'],value=catalog[h]['value'])
            for a,h in aliases.items() if catalog[h]['selector']['reference']==reference}
    chronology=execution_chronology(w.store,w.records);w.latest=chronology['latest_complete_result']
    history=study_history(w.store,w.records,retained_baseline=w.baseline['candidate'],latest_tested=w.latest,
        selection=w.selected,selected_source=w.batch_source)
    packet=dict(history=history,primary=w.freeze['primary'],incumbent=w.freeze['incumbent'],chronology=chronology,
        current_batch_source=w.batch_source,predecessor_decision=w.previous_decision,
        current_feedback=dict(reference=ref,content=w.store.artifact(ref),aliases=alias_view(ref)),
        capabilities=cap,scope=w.freeze['profile'],acceptance=w.freeze['common_scientific_input']['acceptance'],
        case_id='nominal',case=dict(question=w.freeze['study_question'],evidence_execution_ids=[w.freeze['incumbent']['execution_id']],
            stopping_criteria=w.freeze['termination']),sealed_cases=w.sealed_cases,
        study={k:w.freeze[k] for k in ('version','specification_identity','parameter_catalog','task_acceptance',
            'allocation','frozen_cases','initial_state_mapping','m5_feedback')},
        engineering_coverage=dict(completed_search_batches=sum(r.get('kind')=='search' and r.get('complete') for r in w.rounds)),
        performed_batch_evidence=[dict(reference=r['feedback_result'],aliases=alias_view(r['feedback_result']))
            for r in w.rounds if r.get('feedback_result')],
        corrections=dict(total=state.get('protocol_corrections_used',0),consecutive=state.get('protocol_corrections_consecutive',0)))
    packet['execution_version_boundary']=w.freeze.get('repair_boundary')
    packet['history_coverage']=w.freeze.get('history_coverage')
    boundary=w.freeze.get('recovery_boundary')
    packet['decision_recovery']=({k:v for k,v in boundary.items() if not k.endswith('_seal') and k!='old_implementation'}
        | dict(old_implementation_commit=boundary['old_implementation']['commit'])) if boundary else None
    if boundary:
        original=boundary['original_action'];plan=original.get('plan') or {}
        packet['decision_recovery']['original_action']=dict(action=original['action'],reasoning=original['reasoning'],
            plan={k:plan.get(k) for k in ('source_candidate','variables','method','candidates','replication_reason',
                'hypothesis','scientific_promise','stop_criteria')},
            complete_original_decision=boundary['first_decision'])
    event=w.freeze['subsequent_event']
    packet['study']['subsequent_event']=dict(candidate=event['facts']['candidate'],case_id='near_z_plus',seed=17,
        acceptance=event['acceptance'],implementation=event['implementation'],completed=True,matched_nominal_reference=False)
    authority=research_authority(packet,new_execution_ids=w.freeze.get('original_pilot_execution_ids',
        [r['execution_id'] for r in w.records if r['source_store']==str(w.directory)]),
        replication_pairs=[(c['replication_of']['execution_id'],c['execution_id']) for r in w.rounds if r.get('result')
            for c in w.store.artifact(r['result']).get('candidates',[]) if c.get('replication_of') and c.get('execution_id')])
    authority.update(stop=dict(status=w.status,reason=w.stop_reason,sealed_cases=w.sealed_cases),
        budget_accounting=w.store.remaining(),experiment_permissions=w.freeze['allocation'])
    if w.rounds:
        last=w.rounds[-1]['decision'];authority.update(hypotheses=last['model_interpretations'],unresolved=last['unresolved_uncertainties'])
        if w.freeze.get('decision_only'):
            authority['hypotheses']=[dict(statement=h['statement'],scope=h['scope'],uncertainty=h['uncertainty'],
                original_decision=w.rounds[-1]['accepted_decision'],bound_evidence=last['interpretation_bindings'][i])
                for i,h in enumerate(last['model_interpretations'])]
            authority['experiment_permissions']=dict(decision_only=True,backend_solves=0,numerical_operations=0,
                workers=0,proposals_require_separate_authorization=True)
    experiments=[dict(experiment_id=r['execution_id'],status='completed',candidate=r['facts']['candidate'],
        case_id='nominal',seed=17,task_identity=r['acceptance']['task_identity'],structure_identity=digest(w.store.artifact(r['facts']['configuration'])['effective']['robot']),
        implementation=r.get('implementation',w.freeze['implementation']),observed_metrics=r['acceptance'],
        receipt=r['receipts']['simulation'],cache_hit=r['receipts']['simulation'].get('cache_hit')) for r in w.records if r.get('acceptance')]
    claims=[dict(claim_id=f'round{r["index"]}-interpretation-{i}',statement=h['statement'],
        supporting_evidence=r['decision']['interpretation_bindings'][i].get('support',[]),
        counterexamples=r['decision']['interpretation_bindings'][i].get('contradiction',[]),
        evidence_aliases=dict(support=h['supporting_evidence'],contradiction=h['contradicting_evidence']),
        scope=h['scope'],uncertainty=h['uncertainty']) for r in w.rounds[-1:] for i,h in enumerate(r['decision']['model_interpretations'])]
    a=archive(w)
    if w.working is None:
        w.working=create_working_state(packet,authority=authority,archive=a,experiments=experiments)
    else:
        w.working=update_working_state(w.working,archive=a,evidence_packet=packet,authority=authority,
            experiment_updates=experiments,claim_revisions=claims)
    configure_role(w.host,'design',w.freeze.get('recovery_instructions',INSTRUCTIONS),phase='research',delivery_tool='research.decide',
        phase_budget=dict(protect_project=dict(tool_calls=1,wall_s=60.),protect_role=dict(tool_calls=1,wall_s=60.)) if w.freeze.get('decision_only') else {},
        decision_only=w.freeze.get('decision_only',False),decision_recovery_policy=w.freeze.get('recovery_policy'),
        fact_separation=True,autonomous_scheduling=True,research_packet=packet,context_authority=authority,
        research_working_state=w.working,research_working_manifest=a.manifest(),research_records=w.records,result_feedback=w.feedback,
        diagnosis_remaining=max(0,w.freeze['diagnosis_limit']-sum(r['decision']['decision']['action']=='diagnosis' for r in w.rounds)),
        predecessor_decision=w.previous_decision,latest_tested=w.latest,require_source_binding=True,max_batch_backends=2,
        source_report=w.freeze['source_report'],improvement_feedback_content=dict(baseline_facts=w.baseline,execution=None),
        native_store_root=str(w.store.root),native_fixed={},memory_identity=w.host.run_id,binding=w.freeze['binding'])
    return packet


def decision(w):
    packet=configure(w);adapter=EvidenceDrivenAdapter();payload=payload_for(w.host,adapter)
    if list(adapter.advertised.values())!=['research.decide']:raise ValueError('UNEXPECTED_NATIVE_TOOLS')
    index=len(w.rounds);atomic_json(w.directory/f'round{index}_request.json',dict(payload=payload,context_assembly_audit=adapter.context_assembly_audit))
    before=w.store.session(w.host.run_id)['state'].get('handoffs',{}).get('research_decision')
    persist(w);run_loop(w.host,adapter)
    state=w.store.session(w.host.run_id)['state'];ref=state.get('handoffs',{}).get('research_decision')
    if not ref or ref==before:raise RuntimeError('RESEARCH_DECISION_INCOMPLETE: '+str(state.get('stop_reason')))
    result=w.store.artifact(ref);w.previous_decision=ref
    row=dict(index=index,case_id='nominal',kind=result['decision']['action'],accepted_decision=ref,decision=result,
        request=save(w.store,payload),usage_after_decision=w.store.remaining())
    w.rounds.append(row);persist(w);return row


def export(w):
    import shutil
    from tools.improvement_workflow import archive_store
    out=Path(w.freeze['experiment']['evidence_directory']);out.mkdir(parents=True,exist_ok=True)
    for path in w.directory.glob('*.json'):(out/path.name).write_bytes(path.read_bytes())
    archive_store(w.store,out/'store')
    # Same working facts serve the final report view, even after a voluntary STOP.
    final=assemble_working_context('final_report',w.working,archive=archive(w))
    shutil.copytree(w.directory/'context_assembly',out/'context_assembly',dirs_exist_ok=True)
    atomic_json(out/'final_working_context.json',final)
    atomic_json(out/'delivery.json',dict(version=VERSION,status=w.status,stop_reason=w.stop_reason,
        selected_candidate=w.selected,rounds=w.rounds,usage=w.store.remaining(),
        standalone_numerical_operations=0,workers=0,subagents=0,
        outcomes=[dict(candidate=r['facts']['candidate'],case_id='nominal',seed=17,acceptance=r['acceptance'],
            receipts=r['receipts'],implementation=r['implementation'],
            execution_checkout_commit=w.store.session(r['owner_run_id'])['snapshot']['project_commit'])
            for r in w.records if r['source_store']==str(w.directory)],
        limitations=['No ten-slot matched robustness suite','No formal baseline/three-group comparison',
            'No causal/screening/compression-benefit claim','Mainline 3 integration backlog remains in frozen catalog'],
        final_fact_identity=digest(final['canonical_facts']),working_fact_identity=digest(w.working['current_facts'])))


def live(directory=DEFAULT):
    from examples.gvs_nmpc_route_experiment import load_credential
    w=restore(directory)
    if w.status!='prepared' or w.freeze.get('offline_fixture'):raise ValueError('NO_RESET_OR_AUTOMATIC_REPLAY_OF_LIVE_CAMPAIGN')
    current=revision();frozen=w.freeze['implementation']
    if any(current[k]!=frozen[k] for k in ('files','stable_controller')):
        raise ValueError('FROZEN_IMPLEMENTATION_CHANGED')
    load_credential(Path.home()/'.codex/.env')
    started=time.monotonic();w.status='running'
    try:
        while w.status=='running':
            row=decision(w);reusable.execute(w,row)
            for r in w.records:
                if r['source_store']!=str(w.directory):continue
                c=next(c for c in w.store.artifact(row['result'])['candidates'] if c.get('execution_id')==r['execution_id']) if row.get('result') else None
                if c:r['acceptance']=c['execution']['acceptance'];r['implementation']=w.freeze['implementation']
            configure(w);persist(w)
    except Exception as exc:
        w.status='failed';w.stop_reason=str(exc)
        atomic_json(w.directory/'failure.json',dict(type=type(exc).__name__,message=str(exc),usage=w.store.remaining()))
        print('STOP',w.stop_reason,flush=True)
        persist(w)
        configure(w)
    persist(w);atomic_json(w.directory/'engineering_wall.json',dict(elapsed_s=time.monotonic()-started,not_added_twice=True))
    export(w)
    print(json.dumps(dict(status=w.status,usage=w.store.remaining())),flush=True)


def repair_feedback(directory=DEFAULT):
    """Explicit one-time recovery of the observed completed-feedback bridge fault.

    No decision, candidate or execution is replayed. The failed boundary remains
    sealed and the existing assignment ledger remains the only budget authority.
    """
    w=restore(directory);failure=read(w.directory/'failure.json')
    if failure['type']!='KeyError' or failure['message']!="'baseline'" or w.freeze.get('repair_boundary'):
        raise ValueError('ONLY_OBSERVED_SINGLE_FEEDBACK_REPAIR_AUTHORIZED')
    if w.status not in ('running','failed') or not w.rounds[-1].get('complete'):
        raise ValueError('COMPLETE_BATCH_BOUNDARY_REQUIRED')
    with w.store.connect(True) as db:
        if any(r['status']!='completed' or not r['receipt'] for r in db.execute('SELECT status,receipt FROM calls')):
            raise ValueError('UNSETTLED_OPERATION_NO_REPLAY')
    old=deepcopy(w.freeze)
    result=w.store.artifact(w.rounds[-1]['result'])
    for r in w.records:
        if r['source_store']!=str(w.directory):continue
        candidate=next(c for c in result['candidates'] if c.get('execution_id')==r['execution_id'])
        r['acceptance']=candidate['execution']['acceptance'];r['implementation']=old['implementation']
    reservation,_=w.store.reserve(w.host.run_id,'feedback-bridge-version3',digest(old),'engineering',
        {**zero(),'tool_calls':1,'wall_s':120.})
    started=time.monotonic()
    atomic_json(w.directory/'pre_feedback_repair_freeze.json',old)
    w.freeze['implementation']=revision()
    w.freeze['repair_boundary']=dict(kind='engineering_feedback_bridge',failure=failure,
        failed_evidence='evidence/research_native_v1_failure_20261006',
        old_implementation=old['implementation'],new_implementation=w.freeze['implementation'],
        backend_attempts_before_repair=w.store.remaining()['used']['backend_solves'],
        replayed_operations=0,scientific_settings_changed=False,
        rationale='Accept the unified acceptance relation while retaining exact baseline/source identities in next input.')
    w.status='prepared';w.stop_reason=None;w.repairs+=1
    w.store.complete(reservation,dict(request_id='feedback-bridge-version3',execution_id=reservation['execution_id'],
        caller='engineering',tool_id='engineering.feedback_bridge',tool_version='1.0.0',
        execution_status='completed',charged=zero()),w.freeze['repair_boundary'],time.monotonic()-started)
    configure(w);persist(w)
    atomic_json(w.directory/'feedback_repair_boundary.json',w.freeze['repair_boundary'])
    print(json.dumps(dict(status=w.status,usage=w.store.remaining())),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['prepare','live','export','repair-feedback']);parser.add_argument('--output',type=Path,default=DEFAULT)
    args=parser.parse_args()
    if args.mode=='prepare':prepare(args.output)
    elif args.mode=='live':live(args.output)
    elif args.mode=='repair-feedback':repair_feedback(args.output)
    else:export(restore(args.output))
