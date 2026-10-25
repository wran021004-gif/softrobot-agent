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
def read_evidence(host, query, *, record_read=True):
    """Use the existing evidence boundary; internal reads may omit read markers."""
    q = EvidenceQuery.model_validate(query)
    s = state(host)
    value = host.store.artifact(q.reference,raw=True) if q.reference.media_type in ('application/gzip','application/octet-stream') else host.store.artifact(q.reference)
    if isinstance(value,bytes):
        try:
            if value.startswith(b'\x1f\x8b'):
                import gzip
                value=gzip.decompress(value)
            value=json.loads(value)
        except (ValueError,UnicodeError) as exc:raise ValueError('EVIDENCE_NOT_JSON: select a saved JSON measurement artifact') from exc
    if protected(host) and plain(q.reference) not in readable_results(s,host):
        raise ValueError('PROTECTED_EVIDENCE_READ_REQUIRES_NEW_RESULT_OR_TRAINING_SUMMARY')
    if q.view=='working_set':
        from tools.research.evidence_policy import registered_references
        from tools.research.research_context import context
        if plain(q.reference) not in [s.get('family_space_reference'),*registered_references(host)]:raise ValueError('REGISTERED_WORKING_SET_ANCHOR_REQUIRED')
        value=dict(context(host)['evidence_working_set'],source_state_identity=digest(s),
            authoritative_scientific_evidence=False)
    elif q.view=='mathematical_capabilities':
        from tools.research.task_constraints import mathematical_method_view
        value=mathematical_method_view(host,plain(q.reference))
    root_value=value
    def navigation(exc,node,path):
        from tools.research.evidence_views import data_access
        details=dict(reference=plain(q.reference),view=q.view,failed_pointer=q.pointer,
            parent_pointer=path,available_fields=list(node) if isinstance(node,dict) else None,
            list_length=len(node) if isinstance(node,list) else None,
            parent_query=dict(reference=plain(q.reference),view=q.view if q.view in ('working_set','mathematical_capabilities') else 'summary',pointer=path),
            data_access=data_access(host,plain(q.reference),root_value))
        if q.view!='working_set' and q.pointer and q.pointer.split('/')[1] in ('candidate_index','control_result_links','control_comparisons','citation_eligibility'):
            details['derived_view_query']=dict(reference=plain(q.reference),view='working_set',pointer=q.pointer)
        if q.view=='fields' and not q.pointer:
            derived=next((k for k in q.fields if k in ('candidate_index','control_result_links','control_comparisons','citation_eligibility','eligible_methods','read_coverage')),None)
            if derived:details['derived_view_query']=dict(reference=plain(q.reference),view='working_set',pointer='/'+derived)
        if isinstance(root_value,dict) and root_value.get('acceptance') and ('task_passed' in (q.fields or []) or q.pointer=='/task_passed'):
            details['acceptance_query']=dict(reference=plain(q.reference),view='full',pointer='/acceptance')
        exc.evidence_navigation=details
        return exc
    if q.pointer and not q.pointer.startswith('/'):
        raise ValueError('INVALID_EVIDENCE_POINTER: use an absolute JSON pointer or empty root')
    parent=''
    for part in q.pointer[1:].split('/') if q.pointer else []:
        part = part.replace('~1', '/').replace('~0', '~')
        if isinstance(value,list) and (not part.isdecimal() or int(part)>=len(value)):
            raise navigation(IndexError('List index must be in [0, '+str(len(value))+')'),value,parent)
        if not isinstance(value,(list,dict)) or (isinstance(value,dict) and part not in value):
            raise navigation(KeyError(part),value,parent)
        value = value[int(part)] if isinstance(value, list) else value[part]
        parent+='/'+part.replace('~','~0').replace('/','~1')
    if q.view=='capabilities':
        from extensions.tendon_family.family_space import parameter_capabilities
        if q.pointer or 'parameters' not in value:raise ValueError('CAPABILITIES_VIEW_REQUIRES_WHOLE_CANDIDATE')
        value=parameter_capabilities(s['spec']['family_space'],value['parameters'])
    elif q.view=='summary':
        from tools.research.research_context import compact_evidence
        value=compact_evidence(value,plain(q.reference),q.pointer)
        from tools.research.evidence_views import data_access
        value['data_access']=data_access(host,plain(q.reference),root_value)
    elif q.view=='fields':
        if not isinstance(value,dict):raise ValueError('EVIDENCE_FIELDS_REQUIRES_OBJECT_POINTER')
        missing=[key for key in q.fields if key not in value]
        if missing:raise navigation(KeyError(missing[0]),value,q.pointer)
        value={key:value[key] for key in q.fields}
    elif q.view=='range':
        if not isinstance(value,list):raise ValueError('EVIDENCE_RANGE_REQUIRES_LIST_POINTER')
        if q.start>len(value):raise ValueError('EVIDENCE_RANGE_START_OUTSIDE_LIST: length='+str(len(value)))
        value=dict(total=len(value),start=q.start,items=value[q.start:q.start+q.count])
    if q.view=='working_set' or not record_read:return value
    if not q.pointer and plain(q.reference) in [s.get('holding_diagnostic_reference'),*s.get('task_math_references',[])]:
        update(host,guidance_reads=[*s.get('guidance_reads',[]),plain(q.reference)])
    if plain(q.reference) in [*s.get('results', []),*s.get('physical_replays', []),*s.get('rl_evaluations', []), *s.get('rl_training_summaries', [])]:
        if q.pointer in ('','/acceptance','/episodes') and q.view in ('full','summary'):
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
        if not state(h).get('reference_candidate') and spec.get('start_mode')!='family_space':
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
        results=[], physical_replays=[], matched_state_results=[], matched_state_probes=0,
        candidates={}, plans=[], retrievals=[], searches={}, pending=None,
        offline_nlp=0, bdf_replays=0, mechanics_results=[], handoffs=[], historical_diagnostic_sources=[],
        research_status='ready', selected=None,
        pilot=dict(provider=model,live_model_requests=0,framework_session_id=run_id,
            request_deadline_unix=None))
    if spec.get('nominal_source'):
        update(h,nominal_configuration=nominal['configuration'],nominal_provenance=nominal['provenance'],mathematical_evaluations=0,analysis_results=[],analysis_costs=[],search_results=[],assignment_started_unix=time.time(),accounting_scope='Cumulative assignment includes engineering preflight; never reset at live start')
    update(h,scoped_context=[save(h,read(ROOT/path),'supplied_scoped_context') for path in spec.get('supplied_evidence',[])])
    if spec.get('start_mode')=='family_space':
        from tools.research.research_context import public_prior_manifest
        update(h,reference_candidate=None,mathematical_evaluations=0,analysis_results=[],analysis_costs=[],search_results=[],
            family_space_reference=save(h,spec['family_space'],'frozen_family_space'),
            public_prior_manifest=save(h,public_prior_manifest(spec),'public_prior_manifest'),
            compatibility_preparation_s=time.perf_counter()-start)
        if enabled(spec,'rl'):
            update(h,rl_task=save(h,spec['canonical_task'],'rl_frozen_task'),
                rl_runs={},rl_evaluations=[],rl_evidence_reads=[])
        atomic_json(directory/'resolved_configuration.json',spec)
        atomic_json(directory/'activity.json',spec)
        return h
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
    if changed and s['spec'].get('start_mode')!='family_space':
        ref=construct(host,s['spec']['reference_parameters'],dict(origin='new_version_reference_required'))
        update(host,reference_candidate=ref,selected=None)
    atomic_json(host.store.root/'implementation_freeze.json',dict(commit=commit,profile=profile))
    atomic_json(host.store.root/'resolved_configuration.json',state(host)['spec'])
    if s['spec'].get('research_decisions'):
        from tools.research.research_context import import_history
        if changed:update(host,research_history_imported=False)
        import_history(host)


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
        if s['spec'].get('start_mode') == 'family_space':
            return family_claims(host, s, progress)
        changed=bool(s.get('selected') and host.store.artifact(host.store.artifact(s['selected'])['candidate'])['configuration']['robot']!=s.get('nominal_configuration',{}).get('robot'))
        search_rows=[host.store.artifact(r) for r in s.get('search_results',[])]
        return dict(selected=s.get('selected'),model_selected_structure_search_evaluations=len({row['evidence']['analysis']['artifact_id'] for search in search_rows for row in search['result']['evaluated'] if row['evidence'].get('analysis') and host.store.artifact(row['evidence']['candidate'])['configuration']['robot']!=s.get('nominal_configuration',{}).get('robot')}),selected_structurally_new=changed,new_design_and_control_confirmed=bool(changed and progress['confirmed']),independent_confirmation_count=progress['required_total']-progress['remaining'],
            required_confirmations=progress['required_total'],confirmation_failures=progress['failures'],
            confirmation_progress=progress,limited_repeat_supported_acceptance=progress['confirmed'],task_passed=bool(s.get('selected') and __import__('tools.research.feedback',fromlist=['result_view']).result_view(host,s['selected'])['passed']),required_extra_confirmations=progress['required_total'],executed_extra_confirmations=progress['current_study_confirmations'],confirmation_status='not_required' if progress['required_total']==0 else 'passed' if progress['confirmed'] else 'pending',reproducibility_assessed=progress['confirmed'],
            parameter_improvement_attribution_permitted=False,
            interface_evaluations=sum(bool(host.store.artifact(r).get('independent_evaluation_executed')) for r in s.get('rl_evaluations',[])))


def family_claims(host, s, progress):
    """No reference-based improvement can be attributed in family-only studies."""
    from tools.research.feedback import result_view
    candidates = [(ref,host.store.artifact(ref)) for ref in s['candidates'].values()]
    designs = {}
    for ref, candidate in candidates:
        designs.setdefault(candidate.get('physical_design_identity',digest(candidate['configuration']['robot']['structure'])),ref)
    refs = list(designs.values())
    selected = host.store.artifact(s['selected']) if s.get('selected') else None
    adaptations=[]
    if s['spec'].get('research_decisions'):
        for ref in s.get('control_search_results',[]):
            row=host.store.artifact(ref);parent=row.get('adaptation_from')
            if parent and any(not r['cache_hit'] for r in row['candidates']) and host.store.artifact(row['candidate'])['configuration']['robot']!=host.store.artifact(parent)['configuration']['robot']:
                adaptations.append(ref)
    extra=dict(explicit_structure_control_adaptations=adaptations,local_control_search_results=s.get('control_search_results',[])) if s['spec'].get('research_decisions') else {}
    return dict(claim_version='bounded_research_claims_v1' if s['spec'].get('research_decisions') else 'family_space_claims_v1',selected=s.get('selected'),
        selected_candidate=selected['candidate'] if selected else None,
        candidate_generated_from_family_space=bool(candidates),
        physically_constructed_and_validated_candidates=[ref for ref,c in candidates if c.get('physical_validation')=='compiled'],
        design_changes_between_candidates=[dict(before=a,after=b) for a,b in zip(refs,refs[1:])],
        distinct_generated_designs=len(designs),
        structure_control_search_performed=bool(adaptations) or any(host.store.artifact(r)['result'].get('evaluated') for r in s.get('search_results',[])),
        optimizer_feedback_decisions=[row['lineage'] for r in s.get('search_results',[]) for row in host.store.artifact(r)['result'].get('evaluated',[])
            if row.get('lineage',{}).get('previous_candidate_ref') and row['lineage'].get('evidence_used')],
        selected_structurally_new=None,model_selected_structure_search_evaluations=None,
        new_design_and_control_confirmed=None,reference_comparison='not_applicable_no_reference_design',
        task_passed=bool(s.get('selected') and result_view(host,s['selected'])['passed']),
        independent_task_acceptance=result_view(host,s['selected']) if selected else None,
        confirmation_progress=progress,limited_repeat_supported_acceptance=progress['confirmed'],
        confirmation_status='not_required' if progress['required_total']==0 else 'passed' if progress['confirmed'] else 'pending',
        reproducibility_assessed=progress['confirmed'],parameter_improvement_attribution_permitted=False,**extra)


def resource_use(host):
    """Ledger-only reporting; never rebuild candidate or evaluation history."""
    s=state(host);cap=s['spec']['budgets']['numerical_s']
    return dict(shared_ledger=host.store.remaining(),numerical_s=s['numerical_s'],
        numerical_reserved_s=s['numerical_reserved_s'],
        remaining_numerical_s=None if cap is None else cap-s['numerical_s']-s['numerical_reserved_s'],
        charged_starts=s.get('charged_starts',0),shared_start_limit=s['spec'].get('shared_start_limit'),
        elapsed_s=max(0,s.get('closed_unix',time.time())-s['started_unix']))


def packet(host):
    from tools.research.analysis import decision_result
    from tools.research.sorosim_s55_feedback import scoped_feedback
    s=state(host)
    if s['spec'].get('capabilities'):
        from tools.research.feedback import result_view, eligibility, facts, search_feedback
        from tools.research.rl import packet as rl_packet
        return dict(decision_facts=facts(host),specification=s['spec'],scoped_context=s.get('scoped_context',[]),
            scientific_feedback=scoped_feedback(host,s.get('scoped_context',[])),
            stage_context=s.get('stage_context',[]),frozen_task=plain(s['spec'].get('canonical_task',s['base_configuration']['task'])),reference_candidate=s.get('reference_candidate'),
            candidates=[r for r in s['candidates'].values() if host.store.artifact(r)['profile_identity']==s['profile']['identity']],results=[dict(reference=r,**result_view(host,r),confirmation=eligibility(host,r)) for r in [*s['results'],*s.get('rl_evaluations',[])]],
            analysis_results=[decision_result(host.store.artifact(r),r) for r in s.get('analysis_results',[])],
            search_results=s.get('search_results',[]),
            search_feedback=[search_feedback(host,r) for r in s.get('search_results',[])],
            mathematical_accounting=dict(evaluations=s.get('mathematical_evaluations',0),costs=s.get('analysis_costs',[]),engineering_preflight_s=sum(c['numerical_s'] for c in s.get('analysis_costs',[]) if c['origin']=='engineering_preflight'),cumulative_costs_preserved=True),
            mechanics_results=[dict(reference=r,**{k:host.store.artifact(r).get(k) for k in (
                'status','operation','trajectory_reference','objective_definition','original_task_feasible',
                'relaxed_nlp_feasible','original_task_gaps','trajectory_metrics','charged_numerical_s',
                'checkpoint_reference','source_reference','substeps','complete','original_task_satisfied',
                'terminal_position_error_m','holding_max_position_error_m','holding_max_speed_m_s',
                'time_localized_task_violations','root_count','reason','source_identity',
                'tension_sequence_sha256')},
                kkt={key:((host.store.artifact(r).get('mathematical_facts') or {}).get('kkt') or {}).get(key)
                    for key in ('solver_exitflag','primal_inf','stationarity_inf','dual_violation',
                        'complementarity_inf','same_as_selected_trajectory','conditioning')})
                for r in s.get('mechanics_results',[])],
            matched_state_results=[dict(reference=r,status=(v:=host.store.artifact(r)).get('status'),
                checkpoint_indices=v.get('checkpoint_indices'),physical_steps=v.get('physical_steps'),
                physical_probe_count=v.get('physical_probe_count'),
                comparisons=[dict(time_s=row['time_s'],following_command_index=row['following_command_index'],
                    resolutions={k:{field:record.get(field) for field in ('status','complete','position','velocity')}
                        for k,record in row['sorosim'].items()}) for row in v.get('checkpoints',[])],
                charged_numerical_s=v.get('charged_numerical_s'))
                for r in s.get('matched_state_results',[])],
            physical_replays=[dict(reference=r,**result_view(host,r),confirmation=eligibility(host,r)) for r in s.get('physical_replays',[])],
            handoffs=[dict(reference=r,**host.store.artifact(r)) for r in s.get('handoffs',[])],
            rl=rl_packet(host) if enabled(s['spec'],'rl') else None,
            nmpc_admission=[dict(candidate=r,**nmpc_timing(host,r),remaining_phase_admission=capacity(host,1,candidate=r)) for r in s['candidates'].values() if host.store.artifact(r)['profile_identity']==s['profile']['identity']] if enabled(s['spec'],'nmpc') else None,
            research_context=__import__('tools.research.research_context',fromlist=['context']).context(host) if s['spec'].get('research_decisions') else None,
            resource_use=resource_use(host),
            claims=claims(host),research_status=s['research_status'])


def initial_structure_action(host):
    """One existing-state gate, shared by execution, L0 and the advertised Schema."""
    s=state(host);strategy=s['spec'].get('initial_structure_strategy')
    if strategy=='heuristic_generate' and not s.get('candidates'):return 'generate'
    if strategy=='math_search' and not any(host.store.artifact(r).get('result',{}).get('best_mathematical_candidate') for r in s.get('search_results',[])):return 'search'


def dispatch(host, value, request_id, origin='model'):
    """Native plan acceptance and internal batch use the same project Store."""
    if state(host)['spec'].get('mode') == 'engineering_numerical':
        origin='engineering'
    plan=Plan.model_validate(value)
    if state(host)['spec'].get('allowed_plan_actions') is not None and plan.action not in state(host)['spec']['allowed_plan_actions']:
        raise ValueError('Operation outside declared follow-up scope')
    capability={'initialize_control':'control_correction','control_search':'control_search','execute':'nmpc','search':'search','mechanics':'mathematics','replay':'replay','cross_replay':'replay','refine':'replay',
        'physical_replay':'physical_replay','matched_state':'physical_replay','nmpc_prediction_diagnostic':'prediction_diagnostic'}.get(plan.action)
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
    from tools.research.tool_readiness import require
    require(host,plan.action)
    from tools.research.evidence_policy import admit_decision
    try:
        decision_admission=admit_decision(host,plan)
    except ValueError as exc:
        save(host,dict(origin=origin,request_id=request_id,plan=plain(plan),reason=str(exc)),
            'research_decision_rejected')
        raise
    admit_closeout(host,'research_plan',plain(plan))
    guard(host,plan.action in ('initialize_control','control_search','generate','propose','execute','search','mechanics','replay','cross_replay','refine','nmpc_prediction_diagnostic','physical_replay','matched_state') or plan.diagnostic is not None)
    s=state(host)
    initial=initial_structure_action(host)
    if initial and plan.action not in ('stop','diagnose'):
        if plan.action!=initial:raise ValueError('FIRST_STRUCTURE_REQUIRES_'+initial.upper())
        if initial=='search' and (getattr(plan.search,'version',None)!='family_mixed_search_v1' or plan.search.objective!='task_violation'):
            raise ValueError('FIRST_STRUCTURE_REQUIRES_FAMILY_MIXED_TASK_VIOLATION_SEARCH')
    for r in plan.supporting_evidence:
        host.store.artifact(r)
    from tools.research.experience import disposition_bindings
    experience_bindings=disposition_bindings(host,plan.experience_disposition)
    if plan.action=='stop':
        missing=[r for r in [*s['results'],*s.get('mechanics_results',[]),*s.get('physical_replays',[]),*s.get('matched_state_results',[]),*s.get('rl_evaluations',[]),*s.get('analysis_results',[])] if r not in [plain(v) for v in plan.supporting_evidence]]
        if missing:
            raise ValueError('STOP_MUST_CITE_ALL_NEW_EXPERIMENT_RESULTS: missing_supporting_evidence='+json.dumps(missing,sort_keys=True))
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
    scientific_preflight=None
    if plan.action in ('mechanics','replay','refine'):
        from tools.research.budget import require_guidance
        require_guidance(host,plan.hypothesis)
    if plan.action in ('execute','physical_replay'):
        from tools.research.budget import require_guidance
        require_guidance(host,plan.hypothesis)
        from tools.research.feedback import experiment_preflight
        from tools.research.design import verify_candidate
        candidate=plan.candidate if plan.action=='execute' else plan.physical_replay.candidate
        verify_candidate(host,candidate)
        scientific_preflight=experiment_preflight(host,candidate,
            'nmpc' if plan.action=='execute' else 'fixed_tension',
            source_ref=plan.physical_replay.source if plan.action=='physical_replay' else None)
        if not scientific_preflight['admitted']:
            raise ValueError('EQUIVALENT_SCIENTIFIC_EXPERIMENT_REQUIRES_EXPLICIT_REPLICATION_GRANT: '
                +json.dumps(scientific_preflight,sort_keys=True))
    if plan.action=='select':
        admission=dict(scope='selection without execution or numerical reservation')
    elif plan.action=='search' and getattr(plan.search,'evaluation_mode','mathematical_proxy')=='mathematical_proxy':
        from tools.research.analysis import admission as mathematical_admission
        admission=mathematical_admission(host,plan.search.max_evaluations)
    else:
        from tools.research.feedback import result_view
        route='nmpc'
        if plan.action=='physical_replay':route='fixed_tension'
        elif plan.action=='confirm':route=result_view(host,plan.selected_execution)['controller_route']
        admission=capacity(host,plan.search.max_evaluations if plan.search else 1,plan.action=='confirm',root_operation=True,candidate=plan.candidate,route=route)
    if plan.action=='execute' and s['spec'].get('nmpc_execution_cap_s'):
        timing=nmpc_timing(host,plan.candidate)
        if not timing['available']:
            raise ValueError(timing['reason'])
    if plan.action in ('execute','physical_replay') and admission['admitted']<1:
        raise ValueError('CANDIDATE_PLUS_DECLARED_CONFIRMATIONS_CANNOT_FIT')
    row,_=host.store.reserve(host.run_id,request_id,digest(plain(plan)),host.actor,{**zero(),'tool_calls':1})
    ref=save(host,dict(origin=origin,request_id=request_id,original_plan=plain(plan),admission=admission,
        scientific_preflight=scientific_preflight,
        decision_admission=decision_admission,
        experience_read_bindings=experience_bindings),'original_research_plan')
    update(host,plans=[*state(host)['plans'],ref])
    try:
        if plan.action=='initialize_control':
            from tools.research.physical_replay import seed_control
            result=seed_control(host,plan.control_seed,request_id,plan)
        elif plan.action=='generate':
            from tools.research.design import generate_candidate
            result=generate_candidate(host,plan.generation,dict(origin=origin,plan=ref))
        elif plan.action=='propose':
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
        elif plan.action=='control_search':
            from tools.research.local_control_search import dispatch as control_dispatch
            result=control_dispatch(host,plan,request_id,origin=origin)
        elif plan.action in ('mechanics','replay','cross_replay','refine','nmpc_prediction_diagnostic'):
            from tools.research.mechanics import dispatch as mechanics_dispatch
            result=mechanics_dispatch(host,{'mechanics':'solve','replay':'replay','cross_replay':'cross_replay','refine':'refine','nmpc_prediction_diagnostic':'nmpc_prediction_diagnostic'}[plan.action],
                {'mechanics':plan.mechanics,'replay':plan.mechanics_source,'cross_replay':plan.cross_replay,
                 'refine':plan.refinement,'nmpc_prediction_diagnostic':plan.nmpc_prediction_diagnostic}[plan.action],request_id)
        elif plan.action=='physical_replay':
            from tools.research.physical_replay import dispatch as physical_dispatch
            result=physical_dispatch(host,plan.physical_replay,request_id)
        elif plan.action=='matched_state':
            from tools.research.matched_state import dispatch as matched_dispatch
            result=matched_dispatch(host,plan.matched_state,request_id)
        elif plan.action=='diagnose':
            result=diagnose(host,[plain(r) for r in plan.supporting_evidence])
            if plan.diagnostic:
                result['local_comparison']=local_diagnostic(host,plan.diagnostic,request_id)
        elif plan.action in ('select','confirm'):
            from tools.research.feedback import eligibility, result_view, confirmation_progress
            choice=eligibility(host,plan.selected_execution,revise_selection=plan.revise_selection,selection=plan.action=='select',root_operation=False)
            if not choice['eligible']:
                raise ValueError('; '.join(choice['reasons']))
            selected=result_view(host,plan.selected_execution)
            if plan.action=='confirm' and s.get('selected')!=plain(plan.selected_execution):
                raise ValueError('CONFIRM_REQUIRES_PRIOR_FORMAL_SELECT')
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
            elif selected['controller_route']=='fixed_tension':
                from tools.research.physical_replay import dispatch as replay_dispatch
                from tools.research.contracts import PhysicalReplayRequest
                result=replay_dispatch(host,PhysicalReplayRequest(candidate=selected['candidate'],
                    source=host.store.artifact(plan.selected_execution)['source_reference']),request_id,
                    role='confirmation',selected=plain(plan.selected_execution))
            else:
                result=execute(host,selected['candidate'],request_id,role='confirmation',selected=plain(plan.selected_execution))
            if confirmation_progress(host)['confirmed']:
                update(host,research_status='stopped',final_disposition=ref,closed_unix=time.time())
        else:
            update(host,research_status='stopped',final_disposition=ref,closed_unix=time.time())
            result=dict(accepted_stop=True,claims=claims(host))
        from tools.research.reporter import RESULT_KEYS
        after=state(host)
        scientific_results=[r for key in RESULT_KEYS for r in after.get(key,[]) if r not in s.get(key,[])]
        output=dict(plan=ref,result=result,scientific_results=scientific_results,scientific_preflight=scientific_preflight,
            resource_use=resource_use(host))
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
    from tools.research.feedback import result_view,confirmation_progress
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
    if p and p.get('kind')=='matched_state':
        from tools.research.matched_state import recover as matched_recover
        recovered=matched_recover(host)
    elif p and p.get('kind')=='physical_replay':
        from tools.research.physical_replay import recover as physical_recover
        recovered=physical_recover(host)
    elif p and p.get('kind')=='mechanics':
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
        if plan.action=='initialize_control':
            matches=[e for e in s.get('control_initializations',[]) if host.store.artifact(e['source'])['provenance'].get('operation_key')==key]
            if len(matches)!=1:raise ValueError('RECOVER_REQUIRES_UNIQUE_CONTROL_INITIALIZATION')
            result=matches[0]
        elif plan.action=='control_search':
            refs=[r for r in s.get('physical_replays',[]) if host.store.artifact(
                host.store.artifact(r)['source_reference']).get('provenance',{}).get('batch_request')==key]
            result=dict(status='interrupted_control_search',saved_results=refs,
                optimizer_state_restored=False,new_launches=0,
                reason='Existing physical outputs settled; a new bounded Plan is required for further search')
        elif plan.action=='search':
            result=dict(status='search_execution_incomplete',saved_checkpoint=s['searches'].get(key),
                attempted_executions=[r for r in s['results'] if host.store.artifact(r)['operation_key'].startswith(key+':')],
                reason='Recovery packages existing evidence only; further proposals require a new model-requested search')
        elif plan.action=='physical_replay' or (plan.action=='confirm' and
                result_view(host,plan.selected_execution)['controller_route']=='fixed_tension'):
            worker=host.store.lookup(host.run_id,key+'-physical')
            if not worker or not worker['receipt']:raise ValueError('RECOVER_PHYSICAL_PLAYBACK_NO_RELAUNCH')
            output_ref=json.loads(worker['receipt'])['output']
            if output_ref not in state(host).get('physical_replays',[]):raise ValueError('RECOVER_REQUIRES_OWNED_PHYSICAL_PLAYBACK_RESULT')
            result=dict(reference=output_ref,**host.store.artifact(output_ref),recovered_without_repeating_completed_outputs=True)
            if plan.action=='confirm' and confirmation_progress(host)['confirmed']:
                update(host,research_status='stopped',final_disposition=ref,closed_unix=time.time())
        elif plan.action in ('execute','confirm'):
            matches=[r for r in state(host)['results'] if host.store.artifact(r)['operation_key']==key]
            if len(matches)!=1:
                raise ValueError('RECOVERY_REQUIRES_UNIQUE_SEALED_RESULT_NO_NEW_LAUNCH')
            result=dict(reference=matches[0],**compact_result(host.store.artifact(matches[0])))
        elif plan.action in ('mechanics','replay','cross_replay','refine','nmpc_prediction_diagnostic'):
            result=recovered
            if not result:
                worker=host.store.lookup(host.run_id,key+'-mechanics')
                if not worker or not worker['receipt']:
                    raise ValueError('RECOVER_MECHANICS_NO_SECOND_SOLVE')
                receipt=json.loads(worker['receipt'])
                value=host.store.artifact(receipt['output'])
                ref=next(r for r in state(host)['mechanics_results'] if host.store.artifact(r)['execution_id']==worker['execution_id'])
                result=dict(reference=ref,status=value['status'],recovered_without_repeating_completed_outputs=True)
        elif plan.action=='matched_state':
            result=recovered
            if not result:
                worker=host.store.lookup(host.run_id,key+'-matched')
                if not worker or not worker['receipt']:
                    raise ValueError('RECOVER_MATCHED_STATE_NO_RELAUNCH')
                matches=[r for r in state(host).get('matched_state_results',[])
                    if host.store.artifact(r).get('source_reference')==plain(plan.matched_state.source)
                    and host.store.artifact(r).get('candidate')==plain(plan.matched_state.candidate)]
                if len(matches)!=1:
                    raise ValueError('RECOVER_REQUIRES_UNIQUE_MATCHED_STATE_RESULT')
                result=dict(reference=matches[0],status=host.store.artifact(matches[0])['status'],
                    recovered_without_repeating_completed_outputs=True)
        else:
            raise ValueError('INSPECT_UNSEALED_NONEXECUTION_OPERATION')
        output=dict(plan=ref,result=result,resource_use=resource_use(host),recovered_without_repeating_completed_outputs=True)
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
    s=state(host)
    if s['spec'].get('budget_semantics',{}).get('mode')=='count':
        from tools.research.rl import packet as rl_packet
        current=dict(resource_use=resource_use(host),rl=rl_packet(host) if enabled(s['spec'],'rl') else None)
    else:
        current=packet(host) or dict(resource_use=resource_use(host))
    if s['spec'].get('budget_semantics',{}).get('mode')=='count':
        disposition={key:s.get(key) for key in ('research_status','freeze','selected','selected_solution','success_gate','final_disposition','validation_extensions','closed_unix')}
        disposition.update(study_id=host.run_id,claims=claims(host),resource_use=current['resource_use'],
            stage_usage=(current.get('rl') or {}).get('allocation_feedback'),
            evidence=dict(results=s['results'],physical_replays=s.get('physical_replays',[]),
                matched_state_results=s.get('matched_state_results',[]),
                rl_evaluations=s.get('rl_evaluations',[]),analyses=s.get('analysis_results',[])))
        values=[('configuration',s['spec']),('disposition',disposition),('calls',calls),('ledger',host.store.remaining())]
    else:
        values=[('state',s),('events',host.store.events(host.run_id)),('calls',calls),('final_packet',current),('ledger',host.store.remaining())]
    for name,value in values:
        atomic_json(out/(name+'.json'),value)
    atomic_json(out/'archive_manifest.json',dict(members=members,archive_sha256=hashlib.sha256((out/'immutable_artifacts.tar.gz').read_bytes()).hexdigest()))
    if s['spec'].get('research_decisions',{}).get('context_limits'):
        from tools.research.feedback import task_gap
        from tools.research.candidate_portfolio import ranking_key
        rows=[dict(reference=r,**host.store.artifact(r),task_gap=task_gap(host.store.artifact(r)))
            for r in [*s['results'],*s.get('physical_replays',[]),*s.get('rl_evaluations',[])]]
        valid=[r for r in rows if r['task_gap']['valid_complete']]
        best=next((r for r in valid if r['reference']==s.get('selected')),min(valid,key=ranking_key) if valid else None)
        package=dict(version='robot_design_delivery_v1',study_id=host.run_id,implementation=s.get('freeze'),
            frozen_study_identity=s['spec']['resolved_identity'],canonical_task=s['spec'].get('canonical_task'),
            accepted=bool(best and best['reference']==s.get('selected') and best['task_gap']['accepted']),
            status='accepted_solution' if best and best['reference']==s.get('selected') and best['task_gap']['accepted'] else 'best_valid_candidate' if best else 'no_valid_candidate',
            ledger=host.store.remaining(),stop=s.get('final_disposition'),
            archive_manifest='archive_manifest.json',scope='Frozen nominal sampled task only; optimality, robustness, hardware and repeatability unassessed')
        if best:
            candidate=host.store.artifact(best['candidate'])
            package.update(candidate=best['candidate'],design_parameters=candidate['parameters'],
                configuration=candidate['configuration'],acceptance=best.get('acceptance'),
                evaluation=best['reference'],raw_reference=best.get('raw_reference'),
                control=host.store.artifact(best['source_reference']) if best.get('source_reference') else None,
                original_result=best,solution_identity=(s.get('success_gate') or {}).get('solution_identity'))
        package['content_identity']=digest(package)
        atomic_json(out/'design_package.json',package)
    return dict(destination=str(out),results=len(state(host)['results']),claims=claims(host),resources=current['resource_use'])


