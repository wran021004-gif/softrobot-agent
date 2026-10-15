from tools.research.state import (state, update, save, readable_results, protected,
    closeout_operations, admit_closeout, charge_start, enabled, confirmation_count,
    science_hashes, core_hashes, limits, allowance, repetition_reserve, nmpc_timing,
    capacity, guard)
"""Reusable reach-and-hold research with immutable candidates and one shared ledger.

Numerical business services remain the established complete-execution and mixed
design services. Strands owns the conversation and session recovery.
"""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import time

from schemas.platform import ProjectConfig, SessionInput
from tools.research.contracts import Plan, EvidenceQuery
from tools.platform_host import Host
from tools.platform_store import plain, zero
from tools.state_io import atomic_json, read, digest

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC = ROOT/'configs/research/study.json'
def read_evidence(host, query):
    q = EvidenceQuery.model_validate(query)
    s = state(host)
    value = host.store.artifact(q.reference)
    if protected(host) and plain(q.reference) not in readable_results(s,host):
        raise ValueError('PROTECTED_EVIDENCE_READ_REQUIRES_NEW_RESULT_OR_TRAINING_SUMMARY')
    for part in q.pointer.strip('/').split('/') if q.pointer else []:
        part = part.replace('~1', '/').replace('~0', '~')
        value = value[int(part)] if isinstance(value, list) else value[part]
    if plain(q.reference) in [*s.get('results', []),*s.get('rl_evaluations', []), *s.get('rl_training_summaries', [])]:
        if q.pointer in ('','/acceptance','/episodes'):
            update(host,evaluation_reads=[*s.get('evaluation_reads',[]),plain(q.reference)])
        update(host, rl_evidence_reads=[*s.get('rl_evidence_reads', []), plain(q.reference)])
    return value


def prepare(spec_path=DEFAULT_SPEC, directory=None, profile=None):
    from tools.research.config import resolve
    spec = resolve(spec_path, profile=profile)
    run_id = spec['study_id']
    directory = Path(directory or ROOT/'runs/research'/run_id)
    h = Host(directory, run_id, actor='unified-research')
    if h.store.db.exists() and h.store.connect(True).execute('SELECT COUNT(*) FROM sessions WHERE run_id=?',(run_id,)).fetchone()[0]:
        if state(h)['spec'] != spec:
            raise ValueError('STUDY_SPEC_CHANGED_USE_EXPLICIT_MIGRATION')
        if not state(h).get('reference_candidate'):
            started=time.perf_counter()
            candidate=construct(h,spec['reference_parameters'],dict(origin='initialization_recovery_no_scientific_dispatch'))
            update(h,reference_candidate=candidate,numerical_s=state(h)['numerical_s']+time.perf_counter()-started)
            if enabled(spec,'rl'):
                update(h,rl_task=save(h,h.store.artifact(candidate)['configuration']['task'],'rl_frozen_task'),rl_runs={},rl_evaluations=[],rl_evidence_reads=[])
        return h
    start = time.perf_counter()
    cfg=deepcopy(spec['configuration'])
    nominal=dict(configuration=deepcopy(cfg),provenance=spec['source_provenance'])
    model = deepcopy(cfg['policy']['model'])
    if not h.store.db.exists():
        h.store.create(ProjectConfig(project_id=run_id, grant_id=run_id+'-authorized',
            authorization_source=spec['authorization'], budget=limits(spec),
            exclusive_resources={'provider_request':1,'backend.family_mujoco':1}))
    h.create(cfg)
    h.resume()
    recipe = deepcopy(cfg['policy']['controller']['parameters']['data']['recipe'])
    profile = dict(adapter='unified_recovery_profile_v1',version=spec['evaluation_version'],
        configuration=full_science(cfg), recipe=recipe, science_hashes=science_hashes(),
        recording=dict(complete_update_inputs=spec['complete_update_inputs'],update_ids=spec['record_update_ids']),
        acceptance=__import__('tools.research_tasks',fromlist=['task_adapter']).task_adapter(cfg).describe(),
        confirmation=spec['confirmation'])
    profile['execution_environment']=deepcopy(spec.get('numerical_environment',{}))
    profile['identity'] = digest(profile)
    update(h, spec=spec, base_configuration=cfg, profile=profile, profile_history=[profile],
        started_unix=time.time(), cutoff_unix=None,
        numerical_s=0., numerical_reserved_s=0., local_solves=0, local_solve_s=0.,
        results=[], candidates={}, plans=[], retrievals=[], searches={}, pending=None,
        offline_nlp=0, bdf_replays=0, mechanics_results=[], handoffs=[], historical_diagnostic_sources=[],
        research_status='ready', selected=None,
        pilot=dict(provider=model,live_model_requests=0,framework_session_id=run_id,
            request_deadline_unix=None))
    if spec.get('nominal_source'):
        update(h,nominal_configuration=nominal['configuration'],nominal_provenance=nominal['provenance'],mathematical_evaluations=0,analysis_results=[],analysis_costs=[],search_results=[],assignment_started_unix=time.time(),accounting_scope='Cumulative assignment includes engineering preflight; never reset at live start')
    update(h,scoped_context=[save(h,read(ROOT/path),'supplied_scoped_context') for path in spec.get('supplied_evidence',[])])
    candidate = construct(h, spec['reference_parameters'], dict(origin='initial_controller_reference', historical_result_ownership='sealed source activity'))
    update(h, reference_candidate=candidate, numerical_s=max(state(h)['numerical_s'],time.perf_counter()-start))
    if enabled(spec,'rl'):
        from extensions.tendon_family.backends import physics_for
        from extensions.tendon_family.scene import assemble
        inp=SessionInput.model_validate(h.store.artifact(candidate)['configuration'])
        if assemble(inp,physics_for(inp))['control']['tension_execution_mode']!='ideal_tension':
            raise ValueError('EXPLICIT_IDEAL_TENSION_REQUIRED')
        update(h,rl_task=save(h,plain(inp.task),'rl_frozen_task'),rl_runs={},rl_evaluations=[],rl_evidence_reads=[])
    atomic_json(directory/'resolved_configuration.json',spec)
    atomic_json(directory/'activity.json',spec)
    return h


from tools.research.design import configuration_for, construct, verify_candidate, full_science


def bind(host, reason=None, specification=None):
    from tools.platform_tasks import compile_input
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise ValueError('COMMIT_BEFORE_BIND_OR_MIGRATION')
    s=state(host)
    if s['pending']:
        raise ValueError('PENDING_OUTCOME_BLOCKS_MIGRATION')
    with host.store.connect(True) as db:
        if db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]:
            raise ValueError('UNSEALED_RESERVATION_BLOCKS_BIND')
    if specification is not None and specification!=s['spec']:
        raise ValueError('IMPLEMENTATION_MIGRATION_CANNOT_CHANGE_FROZEN_STUDY_CONFIGURATION')
    old=host.store.session(host.run_id)['snapshot']
    input_configuration=deepcopy(old['input'])
    input_configuration['policy']['model']=deepcopy(s['spec']['runtime']['provider'])
    snapshot=compile_input(input_configuration,host.reg)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    profile=deepcopy(s['profile'])
    science_prefixes=('backend.','candidate.','controller.','evaluate.','initialize.','model.','solver.','task.')
    changed_dependencies=[name for name,value in snapshot['dependencies'].items()
        if name.startswith(science_prefixes) and old['dependencies'].get(name)!=value]
    selected_environment=s['spec'].get('numerical_environment',{})
    changed=science_hashes()!=profile['science_hashes'] or bool(changed_dependencies) or profile.get('execution_environment',{})!=selected_environment
    if 'freeze' in s and not reason:
        raise ValueError('MIGRATION_REASON_REQUIRED')
    if changed:
        profile.pop('identity')
        profile['version']+=1
        profile['science_hashes']=science_hashes()
        profile['execution_environment']=deepcopy(selected_environment)
        profile['identity']=digest(profile)
    snapshot.update(project_commit=commit,worktree_dirty=False)
    with host.store.transaction() as db:
        ref=host.store.put(db,snapshot)
        db.execute('UPDATE sessions SET snapshot=? WHERE run_id=?',(ref.artifact_id,host.run_id))
        current=host.store.session(host.run_id,db)['state']
        current.update(freeze=commit,profile=profile,core_hashes=core_hashes(),
            validation_extension_pending_binding=False,
            scientific_dependencies={k:v for k,v in snapshot['dependencies'].items() if k.startswith(science_prefixes)})
        if changed:
            current['profile_history'].append(profile)
        if reason:
            current.setdefault('core_repairs',[]).append(dict(reason=reason,previous_commit=s.get('freeze'),commit=commit,
                evaluation_version=profile['version'],material_behavior_change=changed,
                changed_scientific_dependencies=changed_dependencies,
                old_results_and_costs_retained=True,improvement_requires_new_comparable_reference=changed))
        host.store.update_state(db,host.run_id,current)
        host.store.event(db,host.run_id,'implementation_binding','committed',outputs=[ref])
    if changed:
        ref=construct(host,s['spec']['reference_parameters'],dict(origin='new_version_reference_required'))
        update(host,reference_candidate=ref,selected=None)
    atomic_json(host.store.root/'implementation_freeze.json',dict(commit=commit,profile=profile))
    atomic_json(host.store.root/'resolved_configuration.json',state(host)['spec'])


from tools.research.execution import execute, finish_execution, compact_result


def search_problem(host,query,count):
    from tools.research.search import search_problem as build
    return build(host,query,count)


def run_search(host,query,key):
    from tools.research.search import run_search as search
    return search(host,query,key,guard=guard,execute=execute,capacity=capacity)


def experience(host, query):
    from tools.research.experience import retrieve
    return retrieve(host,query)


from tools.research.diagnostic import diagnose, local_diagnostic


def claims(host):
    if state(host)['spec'].get('capabilities'):
        from tools.research.feedback import confirmation_progress
        s=state(host)
        progress=confirmation_progress(host)
        changed=bool(s.get('selected') and host.store.artifact(host.store.artifact(s['selected'])['candidate'])['configuration']['robot']!=s.get('nominal_configuration',{}).get('robot'))
        search_rows=[host.store.artifact(r) for r in s.get('search_results',[])]
        return dict(selected=s.get('selected'),model_selected_structure_search_evaluations=len({row['evidence']['analysis']['artifact_id'] for search in search_rows for row in search['result']['evaluated'] if row['evidence'].get('analysis') and host.store.artifact(row['evidence']['candidate'])['configuration']['robot']!=s.get('nominal_configuration',{}).get('robot')}),selected_structurally_new=changed,new_design_and_control_confirmed=bool(changed and progress['confirmed']),independent_confirmation_count=progress['required_total']-progress['remaining'],
            required_confirmations=progress['required_total'],confirmation_failures=progress['failures'],
            confirmation_progress=progress,limited_repeat_supported_acceptance=progress['confirmed'],task_passed=bool(s.get('selected') and __import__('tools.research.feedback',fromlist=['result_view']).result_view(host,s['selected'])['passed']),required_extra_confirmations=progress['required_total'],executed_extra_confirmations=progress['current_study_confirmations'],confirmation_status='not_required' if progress['required_total']==0 else 'passed' if progress['confirmed'] else 'pending',reproducibility_assessed=progress['confirmed'],
            parameter_improvement_attribution_permitted=False,
            interface_evaluations=sum(bool(host.store.artifact(r).get('independent_evaluation_executed')) for r in s.get('rl_evaluations',[])))


def packet(host):
    from tools.research.analysis import compact_result
    s=state(host)
    if s['spec'].get('capabilities'):
        from tools.research.feedback import result_view, eligibility, facts
        from tools.research.rl import packet as rl_packet
        return dict(decision_facts=facts(host),specification=s['spec'],scoped_context=s.get('scoped_context',[]),frozen_task=plain(s['base_configuration']['task']),reference_candidate=s['reference_candidate'],
            candidates=[r for r in s['candidates'].values() if host.store.artifact(r)['profile_identity']==s['profile']['identity']],results=[dict(reference=r,**result_view(host,r),confirmation=eligibility(host,r)) for r in [*s['results'],*s.get('rl_evaluations',[])]],
            analysis_results=[compact_result(host.store.artifact(r),r) for r in s.get('analysis_results',[])],
            search_results=s.get('search_results',[]),
            mathematical_accounting=dict(evaluations=s.get('mathematical_evaluations',0),costs=s.get('analysis_costs',[]),engineering_preflight_s=sum(c['numerical_s'] for c in s.get('analysis_costs',[]) if c['origin']=='engineering_preflight'),cumulative_costs_preserved=True),
            mechanics_results=[dict(reference=r,**{k:host.store.artifact(r).get(k) for k in ('status','operation','trajectory_reference','objective_definition','original_task_feasible','relaxed_nlp_feasible','original_task_gaps','trajectory_metrics','charged_numerical_s','checkpoint_reference')}) for r in s.get('mechanics_results',[])],
            handoffs=[dict(reference=r,**host.store.artifact(r)) for r in s.get('handoffs',[])],
            rl=rl_packet(host) if enabled(s['spec'],'rl') else None,
            nmpc_admission=[dict(candidate=r,**nmpc_timing(host,r),remaining_phase_admission=capacity(host,1,candidate=r)) for r in s['candidates'].values() if host.store.artifact(r)['profile_identity']==s['profile']['identity']] if enabled(s['spec'],'nmpc') else None,
            resource_use=dict(shared_ledger=host.store.remaining(),numerical_s=s['numerical_s'],numerical_reserved_s=s['numerical_reserved_s'],remaining_numerical_s=None if s['spec']['budgets']['numerical_s'] is None else s['spec']['budgets']['numerical_s']-s['numerical_s']-s['numerical_reserved_s'],charged_starts=s.get('charged_starts',0),shared_start_limit=s['spec'].get('shared_start_limit'),elapsed_s=max(0,s.get('closed_unix',time.time())-s['started_unix'])),
            claims=claims(host),research_status=s['research_status'])


def dispatch(host, value, request_id, origin='model'):
    """Native plan acceptance and internal batch use the same project Store."""
    if state(host)['spec'].get('mode') == 'engineering_numerical':
        origin='engineering'
    plan=Plan.model_validate(value)
    if state(host)['spec'].get('allowed_plan_actions') is not None and plan.action not in state(host)['spec']['allowed_plan_actions']:
        raise ValueError('Operation outside declared follow-up scope')
    capability={'execute':'nmpc','search':'search','mechanics':'mathematics','replay':'replay'}.get(plan.action)
    if capability and not enabled(state(host)['spec'],capability):
        raise ValueError('Undeclared capability: '+capability)
    old=host.store.lookup(host.run_id,request_id)
    if old:
        if old['request_hash']!=digest(plain(plan)):
            raise ValueError('OPERATION_ID_COLLISION')
        if old['receipt']:
            from tools.research.feedback import cached
            return cached(host.store.artifact(json.loads(old['receipt'])['output']))
        raise ValueError('RECOVER_EXISTING_OPERATION_NO_NEW_EXECUTION')
    admit_closeout(host,'research_plan',plain(plan))
    guard(host,plan.action in ('propose','execute','search','mechanics','replay') or plan.diagnostic is not None)
    s=state(host)
    for r in plan.supporting_evidence:
        host.store.artifact(r)
    from tools.research.experience import disposition_bindings
    experience_bindings=disposition_bindings(host,plan.experience_disposition)
    if plan.action=='stop' and any(r not in [plain(v) for v in plan.supporting_evidence] for r in [*s['results'],*s.get('mechanics_results',[]),*s.get('rl_evaluations',[]),*s.get('analysis_results',[])]):
        raise ValueError('STOP_MUST_CITE_ALL_NEW_EXPERIMENT_RESULTS')
    if enabled(s['spec'],'rl') and plan.action=='stop' and s.get('rl_runs'):
        evaluations=s.get('rl_evaluations',[])
        if s['spec'].get('rl_evaluation_source') and not evaluations:
            raise ValueError('RL_STOP_REQUIRES_EVALUATION_AND_NEXT_STEP_DECISION')
        if not plan.next_step:
            raise ValueError('RL_STOP_REQUIRES_NEXT_STEP_DECISION')
        for entry in s['rl_runs'].values():
            summary_ref=entry.get('training_summary')
            if summary_ref not in s.get('rl_evidence_reads',[]) or summary_ref not in [plain(v) for v in plan.supporting_evidence]:
                raise ValueError('RL_STOP_REQUIRES_PUBLIC_TRAINING_SUMMARY_READ_AND_CITATION')
            summary=host.store.artifact(summary_ref)
            if summary.get('checkpoint') and summary['checkpoint']['policy_present'] and not any(host.store.artifact(r).get('run_id')==summary['run_id'] for r in evaluations):
                raise ValueError('RL_STOP_REQUIRES_USABLE_CHECKPOINT_EVALUATION')
        if any(r not in [plain(v) for v in plan.supporting_evidence] for r in evaluations):
            raise ValueError('RL_STOP_MUST_CITE_NEW_EVALUATION')
        if any(r not in s.get('rl_evidence_reads',[]) for r in evaluations):
            raise ValueError('RL_STOP_REQUIRES_PUBLIC_EXPLICIT_EVIDENCE_READ')
        if any(e.get('status',{}).get('worker_alive',True) for e in s['rl_runs'].values()):
            raise ValueError('RL_STOP_REQUIRES_TERMINAL_STATUS_QUERY')
    admission=dict(scope='selection without execution or numerical reservation') if plan.action=='select' else capacity(host,plan.search.max_evaluations if plan.search else 1,plan.action=='confirm',root_operation=True,candidate=plan.candidate)
    if plan.action=='execute' and s['spec'].get('nmpc_execution_cap_s'):
        timing=nmpc_timing(host,plan.candidate)
        if not timing['available']:
            raise ValueError(timing['reason'])
    if plan.action=='execute' and admission['admitted']<1:
        raise ValueError('CANDIDATE_PLUS_DECLARED_CONFIRMATIONS_CANNOT_FIT')
    row,_=host.store.reserve(host.run_id,request_id,digest(plain(plan)),host.actor,{**zero(),'tool_calls':1})
    ref=save(host,dict(origin=origin,request_id=request_id,original_plan=plain(plan),admission=admission,
        experience_read_bindings=experience_bindings),'original_research_plan')
    update(host,plans=[*state(host)['plans'],ref])
    try:
        if plan.action=='propose':
            if plan.mechanics_source:
                from tools.research.mechanics import handoff
                relation=handoff(host,plan.mechanics_source,plain(plan.parameters),dict(origin=origin,plan=ref))
                result=dict(candidate=relation['candidate'],handoff=relation)
            else:
                result=dict(candidate=construct(host,plan.parameters,dict(origin=origin,plan=ref)))
        elif plan.action=='execute':
            result=execute(host,plain(plan.candidate),request_id)
        elif plan.action=='search':
            result=run_search(host,plan.search,request_id)
        elif plan.action in ('mechanics','replay'):
            from tools.research.mechanics import dispatch as mechanics_dispatch
            result=mechanics_dispatch(host,'solve' if plan.action=='mechanics' else 'replay',
                plan.mechanics if plan.action=='mechanics' else plan.mechanics_source,request_id)
        elif plan.action=='diagnose':
            result=diagnose(host,[plain(r) for r in plan.supporting_evidence])
            if plan.diagnostic:
                result['local_comparison']=local_diagnostic(host,plan.diagnostic,request_id)
        elif plan.action in ('select','confirm'):
            from tools.research.feedback import eligibility, result_view, confirmation_progress
            choice=eligibility(host,plan.selected_execution,revise_selection=plan.revise_selection,selection=plan.action=='select')
            if not choice['eligible']:
                raise ValueError('; '.join(choice['reasons']))
            selected=result_view(host,plan.selected_execution)
            if plan.revise_selection:
                transition=dict(previous_selection=s['selected'],selected_execution=plain(plan.selected_execution),
                    previous_progress=confirmation_progress(host),solution_identity=selected['solution_identity'],
                    plan=ref,confirmation_reservation=choice['confirmation_reservation'])
                update(host,selection_history=[*s.get('selection_history',[]),transition],selected=plain(plan.selected_execution))
            else:
                update(host,selected=plain(plan.selected_execution))
            if plan.action=='select':
                update(host,selected_solution=save(host,dict(evaluation=plain(plan.selected_execution),solution_identity=selected['solution_identity'],candidate=selected['candidate'],configuration=host.store.artifact(selected['candidate'])['configuration']),'frozen_selected_solution'))
                result=dict(selected=True,task_passed=True,required_extra_confirmations=confirmation_count(s),executed_extra_confirmations=0,confirmation_status='not_required' if confirmation_count(s)==0 else 'pending',reproducibility_assessed=False)
                if state(host).get('success_gate'):
                    update(host,success_gate={**state(host)['success_gate'],'model_selection_complete':True})
                if confirmation_count(s)==0:
                    update(host,research_status='stopped',final_disposition=ref,closed_unix=time.time())
            elif selected['controller_route']=='rl':
                from tools.research.rl import confirm
                result=confirm(host,plan.selected_execution,request_id+'-rl-confirm')
            else:
                result=execute(host,selected['candidate'],request_id,role='confirmation',selected=plain(plan.selected_execution))
            if confirmation_progress(host)['confirmed']:
                update(host,research_status='stopped',final_disposition=ref,closed_unix=time.time())
        else:
            update(host,research_status='stopped',final_disposition=ref,closed_unix=time.time())
            result=dict(accepted_stop=True,claims=claims(host))
        output=dict(plan=ref,result=result,resource_use=packet(host)['resource_use'])
        host.store.complete(row,dict(request_id=request_id,execution_id=row['execution_id'],caller=host.actor,
            tool_id='research.core_plan',tool_version='1.0.0',execution_status='completed',charged=zero()),output)
        return output
    except Exception as exc:
        failure=dict(error=type(exc).__name__,message=str(exc),pending=state(host)['pending'])
        if state(host)['pending']:
            save(host,failure,'pending_operation_failure')
        else:
            host.store.complete(row,dict(request_id=request_id,execution_id=row['execution_id'],caller=host.actor,
                tool_id='research.core_plan',tool_version='1.0.0',execution_status='failed',error=str(exc),charged=zero()),failure)
        raise


def recover(host):
    if (state(host).get('pending') or {}).get('kind')=='candidate_analysis':
        from tools.research.analysis import recover as recover_analysis
        recover_analysis(host)  # Seal only existing output, then reconcile the owning workflow below.
    if (state(host).get('pending') or {}).get('kind') == 'local_diagnostic':
        from tools.research.diagnostic import recover_local
        return recover_local(host)
    from tools.research.agent import pending as provider_pending, received, settle
    for row in provider_pending(host):
        response=received(host,row['request_id'])
        if response:
            settle(host,row,response)
        else:
            raise ValueError('UNKNOWN_PROVIDER_SEND_INSPECT_BEFORE_REPEAT')
    p=state(host)['pending']
    if p and p.get('kind')=='mechanics':
        from tools.research.mechanics import recover as mechanics_recover
        recovered=mechanics_recover(host)
    else:
        recovered=finish_execution(host,recovery=True) if p else None
    s=state(host)
    completed=[]
    for ref in s['plans']:
        original=host.store.artifact(ref)
        key=original['request_id']
        row=host.store.lookup(host.run_id,key)
        if not row or row['receipt']:
            continue
        plan=Plan.model_validate(original['original_plan'])
        if plan.action=='search':
            result=dict(status='search_execution_incomplete',saved_checkpoint=s['searches'].get(key),
                attempted_executions=[r for r in s['results'] if host.store.artifact(r)['operation_key'].startswith(key+':')],
                reason='Recovery packages existing evidence only; further proposals require a new model-requested search')
        elif plan.action in ('execute','confirm'):
            matches=[r for r in state(host)['results'] if host.store.artifact(r)['operation_key']==key]
            if len(matches)!=1:
                raise ValueError('RECOVERY_REQUIRES_UNIQUE_SEALED_RESULT_NO_NEW_LAUNCH')
            result=dict(reference=matches[0],**compact_result(host.store.artifact(matches[0])))
        elif plan.action in ('mechanics','replay'):
            result=recovered
            if not result:
                worker=host.store.lookup(host.run_id,key+'-mechanics')
                if not worker or not worker['receipt']:
                    raise ValueError('RECOVER_MECHANICS_NO_SECOND_SOLVE')
                receipt=json.loads(worker['receipt'])
                value=host.store.artifact(receipt['output'])
                ref=next(r for r in state(host)['mechanics_results'] if host.store.artifact(r)['execution_id']==worker['execution_id'])
                result=dict(reference=ref,status=value['status'],recovered_without_repeating_completed_outputs=True)
        else:
            raise ValueError('INSPECT_UNSEALED_NONEXECUTION_OPERATION')
        output=dict(plan=ref,result=result,resource_use=packet(host)['resource_use'],recovered_without_repeating_completed_outputs=True)
        host.store.complete(row,dict(request_id=key,execution_id=row['execution_id'],caller=host.actor,
            tool_id='research.core_plan',tool_version='1.0.0',execution_status='completed',charged=zero()),output)
        completed.append(key)
    return dict(execution=recovered,sealed_workflows=completed,provider_outcomes='known')


def export(host, destination=None):
    """Archive original evidence once; count-mode exports avoid parallel full reports."""
    out=Path(destination or ROOT/state(host)['spec']['evidence_destination'])
    out.mkdir(parents=True,exist_ok=True)
    members=[]
    with host.store.connect(True) as db, tarfile.open(out/'immutable_artifacts.tar.gz','w:gz') as archive:
        for row in db.execute('SELECT id,media,body FROM artifacts ORDER BY id'):
            name='artifacts/'+row['id']+('.json' if row['media']=='application/json' else '.bin')
            info=tarfile.TarInfo(name)
            info.size=len(row['body'])
            archive.addfile(info,io.BytesIO(row['body']))
            members.append(dict(name=name,sha256=row['id'],bytes=info.size,media=row['media']))
        calls=[dict(r) for r in db.execute('SELECT * FROM calls ORDER BY rowid')]
        if state(host)['spec'].get('budget_semantics',{}).get('mode')=='count':
            snapshot=dict(session=host.store.session(host.run_id),events=host.store.events(host.run_id),calls=calls,
                ledger=host.store.remaining())
            body=json.dumps(snapshot,sort_keys=True,ensure_ascii=False,allow_nan=False).encode('utf8')
            identity=hashlib.sha256(body).hexdigest()
            name='snapshot/'+identity+'.json'
            info=tarfile.TarInfo(name)
            info.size=len(body)
            archive.addfile(info,io.BytesIO(body))
            members.append(dict(name=name,sha256=identity,bytes=info.size,media='application/json'))
    current=packet(host)
    s=state(host)
    if s['spec'].get('budget_semantics',{}).get('mode')=='count':
        disposition={key:s.get(key) for key in ('research_status','freeze','selected','selected_solution','success_gate','final_disposition','validation_extensions','closed_unix')}
        disposition.update(study_id=host.run_id,claims=claims(host),resource_use=current['resource_use'],
            stage_usage=(current.get('rl') or {}).get('allocation_feedback'),
            evidence=dict(results=s['results'],rl_evaluations=s.get('rl_evaluations',[]),analyses=s.get('analysis_results',[])))
        values=[('configuration',s['spec']),('disposition',disposition),('calls',calls),('ledger',host.store.remaining())]
    else:
        values=[('state',s),('events',host.store.events(host.run_id)),('calls',calls),('final_packet',current),('ledger',host.store.remaining())]
    for name,value in values:
        atomic_json(out/(name+'.json'),value)
    atomic_json(out/'archive_manifest.json',dict(members=members,archive_sha256=hashlib.sha256((out/'immutable_artifacts.tar.gz').read_bytes()).hexdigest()))
    return dict(destination=str(out),results=len(state(host)['results']),claims=claims(host),resources=current['resource_use'])


