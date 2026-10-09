"""One nominal V2 research activity; native decisions, ask/tell, sealed recovery.

No historical campaign entry point or historical grant is executed.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import argparse
import hashlib
import json
import shutil
import time

from schemas.platform import ProjectConfig, SessionInput
from tools.platform_store import Store, plain, zero
from tools.platform_host import Host
from tools.state_io import read, atomic_json, digest
from tools.research_v2 import native_configuration
from tools.research_execution import invoke
from tools.platform_diagnosis_coordinator import configure_role
from tools.diagnostic_facts import handover
from tools.diagnostic_revision import ensure_aliases
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from tools.platform_models import payload_for, run_loop
from tools.research_scheduler import capabilities
from tools.platform_search import prepare_offline_batch, run_live_batch
from tools.study_history import study_history, execution_chronology
from tools.settling_campaign import campaign_metrics
from extensions.tendon_family.gvs_profile import execution_scope

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'runs/mainline4-20261009'
OUT=ROOT/'evidence/research_mainline4_20261009'
STARTED=1791533202.
LIMITS=dict(model_calls=60,tool_calls=1024,backend_solves=10,worker_calls=0,wall_s=43200.)
NATIVE={'research.decide':'1.0.0','research.prepare_candidate':'1.0.0',
    'research.capability_catalog':'1.0.0','research.candidate_dimensions':'1.0.0',
    'analysis.linearize_configuration':'1.0.0','analysis.control_metrics':'2.0.0',
    'analysis.bounded_endpoint':'1.0.0','evidence.read':'1.0.0'}
TOOLS={**NATIVE,'diagnosis.inspect_evidence':'1.0.0',
    **{t:'1.0.0' for t in ('simulation.run','evaluation.run','control.profile_report','research.task_acceptance')}}
INSTRUCTIONS='''Implement one bounded nominal reach-and-hold study. You own the source, hypothesis, small variable subset, mathematical method, next action, and final selection. T1 is the supplied entry, not a winner; T0 is the retained historical comparison, not automatically your source. Choose among T0-T3 complete evidence. Controller implementation controller.gvs_nmpc@10.0.0 is fixed and inherits V7; historical T0 executed version9 and remains version9 evidence. Do not claim selection among controller families. Control-only research is legitimate. No global incumbent promotion.
Source, latest-tested and retained-reference are distinct roles and MAY refer to the SAME configuration. T0 and T1 are available research sources; neither is excluded. T2 has THREE flexible segments (near/middle/far), seven total components and six tendons; its saved V2 execution used controller10. Only historical T0 used controller9. terminal_tip_speed_weight already starts at its 0.1 upper bound; it cannot be increased beyond that bound. A positive local affine witness does not rule out a nonlinear physical reachability limitation.
Records owned by batch-* in this Mainline4 Store are NEW controller10 executions, not historical controller9 background. study.development_used and the cumulative ledger count the whole activity; an empty phase-specific performed_batch_evidence list does not erase prior batches. Both supported speed weights can decrease within their domains; terminal's upper bound prevents an increase, not every legal change. The method's max_candidates includes its initial source proposal even when that result is reused; use actual saved proposals rather than predicting a different ordering.
selected_candidate must copy an existing canonical reference EXACTLY, with ONLY candidate_id, configuration (artifact_id/media_type), execution_id, owner_run_id. Put all claim/metric/verification metadata in reasoning or interpretations, never inside this reference object.
Use native tools with ordinary business fields, one call per response. You can prepare an owned configuration, linearize it, compute control_metrics and bounded_endpoint; their schemas and protocol/target references are supplied. research.prepare_candidate returns a wrapper: use its nested configuration for downstream calls. The mathematical receipt results and aliases will be delivered on the next request; evidence.read can inspect omitted fields. Reuse historical local mathematical evidence when relevant; state original ownership and limits. A mathematical result should inform your decision. A genuine search.family_coordinate@1.0.0 batch should produce evaluated continuous proposals; explicit is model-authored enumeration, not numerical optimization. These are demonstration objectives, not a requirement to continue after you judge stopping warranted.
For search call research.decide with one SearchBatchPlan. Bind exact source_candidate and predecessor_decision from the packet, and current feedback F aliases. Include hypothesis, supporting evidence, weakening observations, variables/fixed conditions, method, joint objective, constraints, budget, verification and stopping conditions. Normally one to three continuous variables and at most two NEW backend attempts per batch; up to four if the method needs it and you justify allocation. Coordinate step is fractional domain width; candidates=null. Explicit step=null, supply an exact ordered enumeration. Source values must be within the domain. max_candidates includes numerical method initial proposals and known-result reuse. Declare max_backend_attempts and target_changed_configurations. planned_budget must cover execution and interpretation; minimum per new evaluation 990 seconds/4 tools, plus 4 provider calls/4 tools/600 seconds delivery; use realistic conservative reservations. backend_solves equals batch cap; worker_calls=0. This study has six total development executions, two protected exact verification slots, two technical replacements after an identified repair, ten attempts overall, 60 requests, 48 mathematical operations. Stop and deliver before the execution cutoff.
Required fixed_conditions identifiers: robot,task,acceptance,controller_implementation,other_numerical_settings (robot means all fields other than declared variables). objectives: joint_reach_holding_acceptance,terminal_error_m,holding_max_error_m,holding_max_speed_m_s. constraints: frozen_acceptance,force_bounds,finite_valid_execution. verification: candidate.apply,simulation.run,evaluation.run,control.profile_report,bound_comparison,diagnostic_revision. No diagnostic submodel is needed. diagnosis reads retained prediction/plans/motion, never changes production.
Template-specific bounds in the source catalog apply; union catalog bounds are not universal. Scales are relative to each selected V2 template; 1/baseline preserves it. Do not reapply old routing scales. Ideal tension only; motor travel/velocity/transmission/servo bypassed. All task conditions, zero initialization mapped by each template, seed17, target, mount, gravity, force bounds, period, physics step, duration, holding window and solver recipe remain frozen. Different independent force capacity, split guide/routing and tension guess sources confound cross-template attribution. Curvature projection residuals are rad/m, never metres. Frequent initialization plans and feasible returns are clues, not unique causes. Local affine witnesses are not nonlinear certificates; unavailable/undetermined is not physical impossibility.
After each batch consume actual completed joint acceptance and feedback; complete valid failures do not trigger retry-to-success. Numerical scores guide search, while actual three physical metrics, full valid execution and force bounds support claims. You may change hypothesis, narrow, switch supported source/variables, investigate, retain or stop. Repeating a known scientific configuration requires replication_reason, including coordinate initialization when historical implementation prevents exact reuse. Such repetition counts against development capacity. No ceremonial rerun is needed if retaining history. If selecting a NEW candidate for joint acceptance or material improvement, identify the claim: the launcher performs one exact fresh verification; a second contemporary reference only when needed for a comparative claim. Report limited same-condition evidence, no robustness/statistical/real-time claim. STOP includes final bounded interpretation, acceptance, selection, verification need and a specific Mainline5 question. Keep source, latest tested, retained reference and selected deliverable distinct. Preserve original conclusions; facts do not certify causality.'''


def save(store,value):
    with store.transaction() as db:return plain(store.put(db,value))


def configuration(run_id='mainline4-research'):
    cfg=native_configuration(run_id)
    model=cfg['policy']['model']
    model.update(max_turns=60,max_repairs=10,protocol_recovery=dict(max_total=60,max_consecutive=60))
    cfg['policy'].update(model=model,budget=deepcopy(LIMITS),allowed_tools=list(TOOLS),tool_bindings=TOOLS,
        operation_allowances={t:dict(timeout_s=36000. if t.startswith('analysis.') else 900. if t=='simulation.run' else 600.,
            reserve_s=1200. if t=='analysis.linearize_configuration' else 900. if t=='simulation.run' else 60.) for t in TOOLS})
    return SessionInput.model_validate(cfg).model_dump(mode='json')


def restore(directory=RUN):
    directory=Path(directory);w=SimpleNamespace(directory=directory,store=Store(directory))
    w.host=Host(directory,'mainline4-research')
    for k,v in read(directory/'study_state.json').items():setattr(w,k,v)
    return w


def persist(w):
    atomic_json(w.directory/'study_state.json',{k:getattr(w,k) for k in
        ('spec','records','baseline','latest','selected','source','previous_decision','feedback','rounds','status','stop_reason','imported_ids','verification')})


def feedback(w,value,kind):
    ref=save(w.store,value)
    handover(w.host,ref,value,origin='mainline4:'+kind,kind=kind)
    w.feedback=save(w.store,dict(result=ref,content=value))
    return ref


def prepare(directory=RUN,*,offline=False):
    directory=Path(directory)
    if (directory/'study_state.json').exists():return restore(directory)
    directory.mkdir(parents=True,exist_ok=True)
    store=Store(directory);cfg=configuration()
    fixture_suffix='-offline-'+digest(str(directory))[:12] if offline else ''
    store.create(ProjectConfig(project_id='mainline4-20261009'+fixture_suffix,
        grant_id='mainline4-original-grant'+fixture_suffix,budget=LIMITS,
        authorization_source='118f6547-3b8c-4c4b-b47c-1d21efb0b572/pasted-text-1.txt: bounded Mainline4; no inherited grants',
        exclusive_resources={'backend.family_mujoco':1}))
    host=Host(directory,cfg['run_id']);host.create(cfg);host.resume()
    w=SimpleNamespace(directory=directory,store=store,host=host,records=[],rounds=[],previous_decision=None,
        selected=None,source=None,status='prepared',stop_reason=None,verification=[])
    started=time.time() if offline else STARTED  # Test fixtures never reopen the real activity clock.
    w.spec=dict(activity_id='mainline4-20261009',started_unix=started,deadline_unix=started+43200,
        execution_cutoff_unix=started+41400,limits=LIMITS,mathematical_operations=48,
        development_backend_limit=6,verification_backend_limit=2,technical_replacement_limit=2,
        nominal=deepcopy(cfg['task']),seed=17,controller=cfg['policy']['controller'],
        entry_template='T1',retained_reference='historical T0',offline=offline,
        scientific_versions=dict(builder='candidate.family@2.0.0',controller='controller.gvs_nmpc@10.0.0'),
        scope='One nominal condition; ideal tension; no robustness, realtime or controller-family selection',
        history_links=['evidence/research_mainline3_v2_20261009/completion.json',
            'evidence/research_mainline3_v1_handoff_20261009/fixed_result.json'],engineering_interventions=[])
    with store.transaction() as db:
        state=store.session(host.run_id,db)['state'];state['fact_scope']=dict(project='mainline4-20261009',binding='historical-T0-T3',context=host.run_id)
        store.update_state(db,host.run_id,state)
    # Reuse the existing provenance-preserving import function only. Its old
    # launcher, campaign setup, grants and reservations are never invoked.
    from examples.research_model_v1 import historical,copy_references
    from extensions.tendon_family.finite_templates import catalog
    w.records.append(historical(w,'runs/mainline3-v1-complete-218a188f9f6f-fixed',catalog()['t0_backend_execution'],'T0_historical_reference'))
    for key in ('T1','T2','T3'):
        summary=read(ROOT/f'evidence/research_mainline3_v2_20261009/{key}_summary.json')
        r=historical(w,'runs/mainline3-v2-20261009',summary['execution_id'],key+'_historical')
        r['mathematical_summary']={k:summary['mathematical_preparation'][k] for k in ('operating_points','bounded_endpoint_status','interpretation')}
        r['mathematical_references']={t:receipt['output'] for t,receipt in summary['receipts'].items() if t.startswith('analysis.')}
        for ref in r['mathematical_references'].values():copy_references(Store(ROOT/'runs/mainline3-v2-20261009'),store,ref)
        w.records.append(r)
    w.baseline=w.records[0]['facts'];w.latest=w.records[1]['facts']['candidate']
    w.source=w.latest
    historical_ids=set()
    for path in {r['source_store'] for r in w.records}:
        with Store(ROOT/path).connect(True) as db:historical_ids.update(r[0] for r in db.execute('SELECT id FROM artifacts'))
    with store.connect(True) as db:w.imported_ids=[r[0] for r in db.execute('SELECT id FROM artifacts') if r[0] in historical_ids]
    feedback(w,dict(status='initial_evidence',entry_template='T1',retained_reference=w.baseline['candidate'],
        cases=[dict(template='T'+str(i),candidate=r['facts']['candidate'],acceptance=r['acceptance'],
            mathematical_summary=r.get('mathematical_summary'),mathematical_references=r.get('mathematical_references')) for i,r in enumerate(w.records)]),'initial')
    atomic_json(directory/'study_specification.json',w.spec);atomic_json(directory/'configuration.json',cfg)
    atomic_json(directory/'grant.json',plain(store.config()));persist(w)
    return w


def bind(w):
    """Freeze finished integration before first paid/scientific dispatch."""
    from tools.platform_tasks import compile_input
    import subprocess
    with w.store.connect(True) as db:
        if db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]:raise ValueError('MAINLINE4_BIND_REQUIRES_ZERO_CALLS')
    before=w.store.session(w.host.run_id)['snapshot'];after=compile_input(before['input'],w.host.reg)
    after.update(project_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),worktree_dirty=True)
    if after['instance_identity']!=before['instance_identity']:raise ValueError('MAINLINE4_BIND_CHANGED_INPUT')
    with w.store.transaction() as db:
        ref=w.store.put(db,after);db.execute('UPDATE sessions SET snapshot=? WHERE run_id=?',(ref.artifact_id,w.host.run_id))
        w.store.event(db,w.host.run_id,'pre_dispatch_binding','integration_frozen',outputs=[w.store.put(db,dict(before=before,after=after))])
    elapsed=time.time()-w.spec['started_unix']
    row,_=w.store.reserve(w.host.run_id,'mainline4-initial-engineering',digest(w.spec),w.host.actor,{**zero(),'wall_s':elapsed},kind='engineering')
    w.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=w.host.actor,
        tool_id='engineering.mainline4',tool_version='1.0.0',execution_status='completed',charged=zero()),
        dict(scope='Preparation and focused integration checks; no scientific behavior changed',elapsed_s=elapsed),elapsed=elapsed,kind='engineering')
    atomic_json(w.directory/'implementation_freeze.json',dict(dependencies=after['dependencies'],project_commit=after['project_commit']))


def import_t0_math(w):
    from examples.research_model_v1 import copy_references
    summary=read(ROOT/'evidence/research_mainline3_v1_handoff_20261009/mathematical_summary.json')
    record=w.records[0]
    record['mathematical_references']={v['receipt']['tool_id']:v['receipt']['output'] for v in summary['operations'].values()}
    record['mathematical_summary']=dict(status=summary['status'],bounded_endpoint_status=[dict(point=r['operating_point'],
        position=r['position_only']['status'],position_and_braking=r['position_and_braking']['status']) for r in summary['operations']['fixed-endpoint']['records']],
        interpretation='Historical controller9 candidate-local evidence; not nonlinear certification or evidence for a changed candidate.')
    source=Store(ROOT/'runs/mainline3-v1-complete-218a188f9f6f-fixed')
    with w.store.connect(True) as db:before={r[0] for r in db.execute('SELECT id FROM artifacts')}
    for ref in record['mathematical_references'].values():copy_references(source,w.store,ref)
    with w.store.connect(True) as db:after={r[0] for r in db.execute('SELECT id FROM artifacts')}
    w.imported_ids=sorted(set(w.imported_ids)|(after-before));persist(w)


def historical_math_packet(w):
    results=[]
    for r in w.records[:4]:
        content=dict(candidate=r['facts']['candidate'],summary=r.get('mathematical_summary'),references=r.get('mathematical_references'),
            scope='Original candidate-local mathematical evidence, never rebound to a changed candidate.')
        ref=save(w.store,content);handover(w.host,ref,content,origin='original-mathematical-artifacts',kind='historical_math_summary')
        results.append(dict(reference=ref,**content,aliases=aliases(w,ref)))
    return results


def aliases(w,ref):
    state=w.store.session(w.host.run_id)['state'];mapping=ensure_aliases(state)['aliases']
    return {a:dict(pointer=state['fact_catalog'][h]['selector']['pointer'],**{k:state['fact_catalog'][h][k] for k in ('field','value','units')})
        for a,h in mapping.items() if state['fact_catalog'][h]['selector']['reference']==ref}


def operation_results(w):
    rows=[]
    with w.store.connect(True) as db:calls=[dict(r) for r in db.execute('SELECT * FROM calls WHERE run_id=? AND receipt IS NOT NULL',(w.host.run_id,))]
    for c in calls:
        r=json.loads(c['receipt'])
        if r['tool_id'] not in NATIVE or r['tool_id']=='research.decide' or not r.get('output') or r['execution_status']!='completed':continue
        value=w.store.artifact(r['output']);handover(w.host,r['output'],value,origin='mainline4-native-receipt',kind='native_result')
        shown=aliases(w,r['output'])
        if r['tool_id'].startswith('analysis.'):
            shown={a:v for a,v in shown.items() if any(v['pointer'].endswith('/'+k) for k in
                ('status','available','name','kind','classification','rank','rank_C','rank_B','condition_number','normalized_residual','max_absolute_error','passed','tip_speed_m_s','normalized_tip_error','normalized_tip_velocity','solver_success'))}
        rows.append(dict(tool=r['tool_id'],receipt=r,aliases=shown,
            content=value if r['tool_id']=='research.prepare_candidate' else None))
    return rows


def configure(w):
    recent=operation_results(w);w.host.resume()
    # Bind the same bounded policy before measuring capacity/accounting, even
    # when the preceding role was an executor rather than a model session.
    with w.store.transaction() as db:
        state=w.store.session(w.host.run_id,db)['state']
        state.setdefault('role_context',{})['campaign_permissions']=dict(phase_budget_policy='bounded_mainline4@1.0.0',elapsed_deadline_unix=w.spec['execution_cutoff_unix'])
        w.store.update_state(db,w.host.run_id,state)
    accounting_time=time.time()
    cap=capabilities(w.store,w.host.run_id,w.records,as_of_unix=accounting_time)
    with w.store.connect(True) as db:
        calls=[dict(r) for r in db.execute('SELECT run_id,charged,receipt FROM calls')]
    development=sum(json.loads(c['charged'])['backend_solves'] for c in calls if 'verification' not in c['run_id'])
    mathematical_used=sum(json.loads(c['receipt'])['tool_id'].startswith('analysis.') for c in calls if c['receipt'])+sum(bool(r.get('result')) for r in w.rounds)
    if development>=6 or time.time()>=w.spec['execution_cutoff_unix']:
        for action in ('control_search','structure_search'):cap['legal'].pop(action,None)
    current=w.store.artifact(w.feedback);history=study_history(w.store,w.records,retained_baseline=w.baseline['candidate'],selected_source=w.source,latest_tested=w.latest,selection=w.selected)
    packet=dict(history=history,chronology=execution_chronology(w.store,w.records),primary=w.records[1]['facts']['candidate'],
        incumbent=w.baseline['candidate'],current_batch_source=w.source,predecessor_decision=w.previous_decision,
        current_feedback=dict(reference=current['result'],content=current['content'],aliases=aliases(w,current['result'])),
        capabilities=cap,scope=w.spec,acceptance=w.store.artifact(w.baseline['configuration'])['effective']['policy']['controller']['parameters']['data']['settling'],
        case_id='nominal',case=dict(question='Can supported structural or speed-weight adaptation attain joint nominal reach and hold?',stopping_criteria=['model voluntary stop','budget or deadline']),
        study=dict(specification=w.spec,development_used=development,verification=w.verification),
        mathematical_evidence=historical_math_packet(w),
        native_results=recent,
        source_catalogs={r['role']:source_catalog(w,r) for r in w.records})
    # Supply standard protocol objects without prescribing which analyses to do.
    from schemas.platform_analysis import TaskAnalysisProtocol,EndpointTarget
    from extensions.tendon_family.finite_templates import catalog
    packet['analysis_protocols']={k:save(w.store,TaskAnalysisProtocol(baseline_lengths_m={c['id']:c['length_m'] for c in t['design']['components'] if c['kind']=='flexible_segment'},frequency_rad_s=[.1,1.,10.])) for k,t in catalog()['templates'].items()}
    packet['endpoint_target']=save(w.store,EndpointTarget(position_m=(.29,.035,.19),position_tolerance_m=.01,position_scale_m=.01))
    from tools.context_assembly import EvidenceArchive,research_authority,create_working_state,update_working_state
    archive=EvidenceArchive(w.directory/'context_assembly',scope=dict(context_id=w.host.run_id,role='design',binding='historical-T0-T3'),stores=(w.store,))
    authority=research_authority(packet)
    from tools.current_research_authority import accounting_binding
    authority.update(budget_accounting=w.store.remaining(),experiment_permissions=dict(development_remaining=max(0,6-development),verification_slots=2,technical_replacements=2),
        stop=dict(status=w.status,reason=w.stop_reason,sealed_cases=[]),accounting_binding=accounting_binding(w.store,w.host.run_id,as_of_unix=accounting_time))
    working_path=w.directory/'research_working_state.json'
    working=(update_working_state(read(working_path),archive=archive,evidence_packet=packet,authority=authority)
        if working_path.exists() else create_working_state(packet,authority=authority,archive=archive))
    atomic_json(working_path,working)
    final_reporting=w.status=='verification_reporting'
    instructions=INSTRUCTIONS+(' Research trajectory is sealed. Only stop is legal now; interpret the exact fresh verification feedback, retain or reject the previously selected candidate, and state the bounded Mainline5 question. No new plan or analysis.' if final_reporting else '')
    configure_role(w.host,'design',instructions,phase='research',delivery_tool='research.decide',phase_budget={},
        fact_separation=True,autonomous_scheduling=True,research_packet=packet,research_records=w.records,
        result_feedback=w.feedback,diagnosis_remaining=60,predecessor_decision=w.previous_decision,
        latest_tested=w.latest,require_source_binding=True,max_batch_backends=min(4,max(0,6-development)),
        max_variable_count=3,source_report=w.feedback,improvement_feedback_content=dict(baseline_facts=w.baseline,execution=None),
        native_store_root=str(w.store.root),native_fixed={},memory_identity=w.host.run_id,binding='historical-T0-T3',
        research_working_state=working,research_working_manifest=archive.manifest(),context_authority=authority,research_final_reporting=final_reporting,
        campaign_permissions=dict(phase_budget_policy='bounded_mainline4@1.0.0',elapsed_deadline_unix=w.spec['execution_cutoff_unix']),development_backend_remaining=max(0,6-development),mathematical_operations_remaining=max(0,48-mathematical_used))
    with w.store.transaction() as db:
        state=w.store.session(w.host.run_id,db)['state'];state['role_context']['phase_tools']=['research.decide','evidence.read'] if final_reporting else list(NATIVE)
        if mathematical_used>=48:state['role_context']['phase_tools']=[t for t in state['role_context']['phase_tools'] if not t.startswith('analysis.')]
        w.store.update_state(db,w.host.run_id,state)
    return packet


def source_catalog(w,record):
    from tools.parameter_catalog import effective_catalog
    from tools.candidate_parameters import planning_configuration
    cfg=planning_configuration(w.store,record['facts']['candidate'],configuration()['policy'])
    return {r['id']:dict(value=r['current_value'],domain=r['experiment_granted_domain']) for r in effective_catalog(cfg)['parameters'] if r['study_permission']['permitted'] and r['technical_support']['supported']}


class ResearchAdapter(EvidenceDrivenAdapter):
    def __init__(self,w):super().__init__();self.w=w
    def encode(self,model_input,config):
        # Include newly sealed public analysis/preparation results before
        # refreshing current authority. Keep the refreshed stamp intact.
        configure(self.w)
        from tools.current_research_authority import refresh
        refresh(self.w.host)
        model_input=model_input.model_copy(deep=True)
        model_input.context['role_context']=self.w.store.session(self.w.host.run_id)['state']['role_context']
        allowed=model_input.context['role_context']['phase_tools']
        model_input=model_input.model_copy(update={'tools':[d for d in model_input.tools if d['extension_id'] in allowed]})
        payload=super().encode(model_input,config)
        # Advertise the exact reference shape already required by select_source;
        # the generic ResearchDecision dict otherwise suggests arbitrary fields.
        for tool in payload['tools']:
            if self.advertised[tool['function']['name']]!='research.decide':continue
            ref=dict(type='object',additionalProperties=False,
                required=['candidate_id','configuration','execution_id','owner_run_id'],
                properties={k:dict(type='string') for k in ('candidate_id','execution_id','owner_run_id')})
            ref['properties']['configuration']=dict(type='object',additionalProperties=False,
                required=['artifact_id','media_type'],properties={k:dict(type='string') for k in ('artifact_id','media_type')})
            tool['function']['parameters']['anyOf'][0]['properties']['selected_candidate']=dict(
                anyOf=[dict(type='null'),ref],description='Copy a supplied verified reference exactly. Claims belong in reasoning.')
        return payload
    def respond(self,payload,turn):
        if time.time()>=self.w.spec['execution_cutoff_unix']:raise ValueError('MAINLINE4_DELIVERY_RESERVE_REACHED')
        return super().respond(payload,turn)


def verify_selection(w):
    """One fresh exact execution for a consequential new selection, no tuning."""
    if not w.selected or not any(r['facts']['candidate']==w.selected and r['source_store']==str(w.directory) for r in w.records):return
    if w.verification:return
    if time.time()>=w.spec['execution_cutoff_unix']:raise ValueError('VERIFICATION_BLOCKED_BY_DELIVERY_RESERVE')
    source=next(r for r in w.records if r['facts']['candidate']==w.selected)
    cfg=deepcopy(w.store.artifact(source['facts']['configuration'])['effective'])
    from tools.execution_completion import complete_execution,EXECUTION_ALLOWANCES
    host=Host(w.directory,'mainline4-verification-selected')
    cfg['run_id']=host.run_id;cfg['policy'].update(budget={**LIMITS,'model_calls':0},allowed_tools=[],
        tool_bindings={t:'1.0.0' for t in EXECUTION_ALLOWANCES},operation_allowances=EXECUTION_ALLOWANCES)
    if not host.folder.exists():host.create(cfg)
    host.resume();result=complete_execution(host,cfg,'mainline4-verification-selected')
    if result['status']!='evaluated':raise ValueError('MAINLINE4_VERIFICATION_INCOMPLETE: '+str(result.get('reason')))
    from tools.research_tasks import assemble_acceptance
    profile=w.store.artifact(result['profile_report']['reference'])
    actual=w.store.artifact(result['configuration'])['effective']
    if execution_scope(actual)!=execution_scope(cfg):raise ValueError('VERIFICATION_CHANGED_EXACT_CONFIGURATION')
    acceptance=assemble_acceptance(actual,result['evaluation_data'],profile,evaluation_reference=result['factual_result']['evaluation'],
        profile_reference=result['profile_report']['reference'],motion=w.store.artifact(profile['detail']['motion']))
    w.verification.append(dict(kind='fresh_exact_selected_configuration',source=w.selected,result=save(w.store,result),acceptance=acceptance))
    feedback(w,dict(status='verification_completed',selected=w.selected,verification=w.verification,
        original_final_decision=w.rounds[-1]['accepted_decision']),'verification');persist(w)


def decision(w):
    configure(w);adapter=ResearchAdapter(w);payload=payload_for(w.host,adapter)
    atomic_json(w.directory/f'round{len(w.rounds)}_request.json',dict(payload=payload,context_assembly_audit=adapter.context_assembly_audit))
    before=w.store.session(w.host.run_id)['state'].get('handoffs',{}).get('research_decision')
    run_loop(w.host,adapter)
    ref=w.store.session(w.host.run_id)['state'].get('handoffs',{}).get('research_decision')
    if not ref or ref==before:raise ValueError('MAINLINE4_DECISION_INCOMPLETE: '+str(w.store.session(w.host.run_id)['state'].get('stop_reason')))
    row=dict(index=len(w.rounds),accepted_decision=ref,decision=w.store.artifact(ref));w.rounds.append(row);w.previous_decision=ref;persist(w)
    return row


def batch_outcomes(w,result):
    """Present executed and exactly reused facts with their original ownership."""
    outcomes=[]
    for c in result['candidates']:
        execution=c.get('execution')
        retained=c.get('historical_source') or next((r for r in w.records
            if r['facts']['candidate']['candidate_id']==c['candidate_id']),None)
        facts=execution['factual_result'] if execution else retained['facts'] if retained else None
        if facts is None:raise ValueError('MAINLINE4_BATCH_OUTCOME_FACTS_MISSING')
        acceptance=execution['acceptance'] if execution else retained['acceptance']
        cfg=w.store.artifact(facts['configuration'])['effective']
        recipe=cfg['policy']['controller']['parameters']['data']['recipe']
        outcomes.append(dict(candidate=facts['candidate'],acceptance=acceptance,metrics=campaign_metrics(facts),
            feedback=c['feedback'],retained_comparison=c['retained_baseline_comparison'],reused=bool(c.get('reused')),
            controller=cfg['policy']['controller']['version'],applied_values={k:recipe[k] for k in
                ('holding_tip_speed_weight','terminal_tip_speed_weight')}))
    return outcomes


def execute(w,row):
    d=row['decision']['decision'];action=d['action']
    if d['selected_candidate'] is not None:w.selected=d['selected_candidate']
    if action=='stop':w.status='model_stopped';w.stop_reason=d['stop_reason'];persist(w);return
    configure_role(w.host,'executor','Execute only the accepted immutable Mainline4 operation.',phase_budget={},
        campaign_permissions=dict(phase_budget_policy='bounded_mainline4@1.0.0',elapsed_deadline_unix=w.spec['execution_cutoff_unix']));w.host.resume()
    if action in ('control_search','structure_search'):
        plan=row['decision']['search_plan'];record=w.store.artifact(plan)
        source=next(r for r in w.records if r['facts']['candidate']==record['bindings']['subject']);w.source=source['facts']['candidate']
        prepare_offline_batch(w.host,plan,mode='live',starting_facts=source['facts'],retained_baseline=w.baseline,historical_results=w.records)
        result=run_live_batch(w.host);ref=save(w.store,result);row['result']=ref
        for c in result['candidates']:
            if not c.get('execution'):continue
            e=c['execution'];f=e['factual_result'];cfg=w.store.artifact(f['configuration'])['effective']
            if not any(r['execution_id']==f['execution_id'] for r in w.records):
                w.records.append(dict(role='new-'+c['candidate_id'],facts=f,acceptance=e['acceptance'],
                    execution_id=f['execution_id'],owner_run_id=f['candidate']['owner_run_id'],execution_scope=execution_scope(cfg),
                    source_store=str(w.directory),receipts=e['receipts'],implementation=w.store.session(f['candidate']['owner_run_id'])['snapshot']))
                w.records[-1]['reuse_reason']='Complete result from this Mainline4 Store; exact reuse remains subject to scientific-identity and implementation checks.'
        outcomes=batch_outcomes(w,result)
        digest_results=[dict(candidate=r['facts']['candidate'],controller=w.store.artifact(r['facts']['configuration'])['effective']['policy']['controller']['version'],
            status=r['acceptance']['status'],accepted=r['acceptance']['accepted'],metrics=r['acceptance']['metrics'])
            for r in w.records if r['source_store']==str(w.directory)]
        w.latest=result['execution_chronology']['latest_complete_result'] or w.latest
        row['feedback_result']=feedback(w,dict(status=result['status'],stop_reason=result['stop_reason'],batch_result=ref,source=w.source,outcomes=outcomes,
            completed_mainline4_results=digest_results),'completed_batch')
        with w.store.transaction() as db:
            state=w.store.session(w.host.run_id,db)['state'];batch=state.pop('search_batch',None)
            w.store.event(db,w.host.run_id,'research_batch_archived',result['status'],outputs=[w.store.put(db,batch)]);w.store.update_state(db,w.host.run_id,state)
        if result['status']!='completed' and result['stop_reason']!='known_scientific_point_requires_repetition_purpose':
            w.status='execution_stopped';w.stop_reason=result['stop_reason']
    else:
        request=d['diagnosis'];source=next(r for r in w.records if r['facts']['candidate']==request['source_candidate'])
        if not source.get('binding'):
            from extensions.tendon_family.control_evidence import ControlEvidence
            from extensions.tendon_family.diagnostic_evidence import import_execution
            reader=ControlEvidence(w.store);owned=reader.resolve(source['execution_id'])
            source['binding']=import_execution(reader,source['execution_id'],w.store,w.host.run_id,owned['manifest'])
        receipt=invoke(w.host,'diagnosis.inspect_evidence',dict(binding=source['binding'],view=request['view'],**({'update_ids':request['update_ids']} if request['update_ids'] else {})),request_id=f"mainline4-diagnosis-{row['index']}")
        row['diagnosis_receipt']=receipt
        if receipt['execution_status']!='completed':raise ValueError(str(receipt['error']))
        row['feedback_result']=feedback(w,dict(status='completed_diagnosis',request=request,result=receipt['output'],content=w.store.artifact(receipt['output'])),'retained_diagnosis')
    persist(w)


def export(w,destination=OUT):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    for path in w.directory.glob('*.json'):shutil.copyfile(path,destination/path.name)
    with w.store.connect(True) as db:
        atomic_json(destination/'cumulative_ledger.json',dict(config=plain(w.store.config()),usage=w.store.remaining(),
            calls=[dict(r) for r in db.execute('SELECT * FROM calls')],elapsed_s=time.time()-w.spec['started_unix']))
        artifacts=[dict(r) for r in db.execute('SELECT id,media FROM artifacts')]
        sessions=[w.store.session(r[0]) for r in db.execute('SELECT run_id FROM sessions')]
    atomic_json(destination/'sessions.json',sessions)
    folder=destination/'store/artifacts';folder.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for a in artifacts:
        ref=dict(artifact_id=a['id'],media_type=a['media'])
        if a['id'] in w.imported_ids:manifest.append(dict(reference=ref,imported_historical=True));continue
        body=w.store.artifact(ref,raw=True);path=folder/(a['id']+('.json' if a['media']=='application/json' else '.blob'))
        if not path.exists() or path.read_bytes()!=body:path.write_bytes(body)
        manifest.append(dict(reference=ref,path=path.relative_to(destination).as_posix(),sha256=hashlib.sha256(body).hexdigest()))
    atomic_json(destination/'store_manifest.json',dict(artifacts=manifest,history_links=w.spec['history_links'],original_owners_preserved=True))
    atomic_json(destination/'events.json',[e for s in sessions for e in w.store.events(s['run_id'])])
    # Backend files include exact controller inputs, online updates and the
    # compressed trajectory. Preserve new executions alongside Store outputs;
    # historical execution directories remain linked in their original bundle.
    execution_files=[]
    for source in (w.directory/'sessions').glob('*/executions/*/backend/*'):
        if not source.is_file():continue
        relative=source.relative_to(w.directory/'sessions')
        target=destination/'executions'/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists() or target.read_bytes()!=source.read_bytes():shutil.copyfile(source,target)
        execution_files.append(dict(path=target.relative_to(destination).as_posix(),
            sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bytes=target.stat().st_size))
    atomic_json(destination/'execution_files.json',execution_files)


def report_verified_selection(w):
    """Finish interpretation from a sealed verification without replaying it."""
    w.status='verification_reporting';persist(w)
    current=w.store.artifact(w.feedback)['result'];row=w.rounds[-1]
    sealed=(row['decision']['decision']['action']=='stop' and
        any(s['reference']==current for s in row['decision']['evidence_selectors']))
    if not sealed:row=decision(w)
    execute(w,row)


def live(directory=RUN):
    from examples.gvs_nmpc_route_experiment import load_credential
    w=restore(directory)
    if w.spec['offline']:raise ValueError('OFFLINE_FIXTURE_CANNOT_RUN_PAID_WORK')
    if w.status in ('model_stopped','complete'):export(w);return
    load_credential(Path.home()/'.codex/.env');w.status='running';persist(w)
    try:
        if w.verification:
            # Reporting recovery consumes the sealed fresh verification. It
            # cannot reopen exploration or repeat its successful simulation.
            report_verified_selection(w);persist(w);export(w);return
        # Recover accepted decisions and sealed backend receipts before another
        # model request. Never replay a completed simulation to repair reporting.
        if w.rounds and not w.rounds[-1].get('feedback_result') and w.rounds[-1]['decision']['decision']['action']!='stop':execute(w,w.rounds[-1])
        while w.status=='running':
            row=decision(w);print('MODEL decision',row['decision']['decision']['action'],flush=True);execute(w,row)
        if w.status=='model_stopped':
            verify_selection(w)
            if w.verification:
                report_verified_selection(w)
    except Exception as exc:
        w.status='engineering_stopped';w.stop_reason=str(exc)
        atomic_json(w.directory/'failure.json',dict(type=type(exc).__name__,message=str(exc),usage=w.store.remaining()))
        persist(w);export(w);raise
    persist(w);export(w)


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','bind','run','recover','export']);p.add_argument('--directory',type=Path,default=RUN);args=p.parse_args()
    if args.action=='prepare':w=prepare(args.directory);print(json.dumps(dict(status=w.status,directory=str(w.directory))))
    elif args.action=='bind':w=restore(args.directory);import_t0_math(w);bind(w)
    elif args.action in ('run','recover'):live(args.directory)
    else:export(restore(args.directory))


if __name__=='__main__':main()
