"""Fixed mathematical workflow; shared candidates, Host, adapters and acceptance.

This prepares the future study and runs only a separately capped integration
smoke by default. No provider chooses directions or interprets numerical results.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
from schemas.platform import SessionInput
from tools.platform_store import Store, plain
from tools.platform_host import Host
from tools.platform_registry import registry
from tools.platform_tools import _candidate
from tools.state_io import atomic_json, digest, read
from tools.optimization_interfaces import ParameterSpace, coordinate_proposal
from tools.research_spec import load_spec, map_initial_state, ROOT
from tools.parameter_catalog import effective_catalog
from tools.research_tasks import (task_adapter, assemble_acceptance, aggregate_acceptance,
                                  compare_acceptance, stop_interpretation)

VERSION = 'fixed_coordinate_reach_hold@1.1.0'


def pool(spec):
    catalog = effective_catalog(spec['execution_template'])
    if catalog['version'] != spec['parameter_pool_version']:
        raise ValueError('FROZEN_POOL_VERSION_CHANGED')
    return catalog


def proposed_edits(spec, variables, centre):
    """Use existing numeric kernel; categorical materials are explicitly enumerated."""
    domains = spec['parameter_grants']
    numeric = [p for p in variables if isinstance(domains[p][0], (int, float))]
    if numeric:
        space = ParameterSpace(numeric, {p:domains[p] for p in numeric})
        for k in range(2 * len(numeric)):
            step = coordinate_proposal(dict(best=space.encode(centre),iteration=k,
                                            step=spec['fixed_baseline']['normalized_step']))
            yield dict(centre, **space.decode(step['x']))
    for p in variables:
        if p in numeric: continue
        for choice in domains[p]:
            if choice != centre[p]: yield dict(centre, **{p:choice})


def initial_values(spec, variables):
    from tools.candidate_parameters import parameter_value
    return {p:parameter_value(spec['execution_template'],p) for p in variables}


def baseline_plan(spec):
    pool(spec)
    config = spec['fixed_baseline']
    structural = config['structural_variables']; controls = config['control_variables']
    start = initial_values(spec,structural)
    if config['version']!=VERSION:
        raise ValueError('SUPERSEDED_BASELINE_POLICY: use the version 1.1 study specification')
    proposals=[dict(start,**slot['changes']) for slot in config['structure_slots']]
    control_start=initial_values(spec,controls)
    search=[]
    for i,point in enumerate(proposals):
        path=config['extra_control_variables'][i]
        extra=next(p for p in proposed_edits(spec,[path],{path:control_start[path]}) if p[path]!=control_start[path])
        for j,pair in enumerate((control_start,dict(control_start,**extra))):
            changes={p:v for p,v in {**point,**pair}.items() if v!=initial_values(spec,[p])[p]}
            search.append(dict(structure_slot=i,control_slot=j,changes=changes,case_id='nominal',seed=17,repetition=1))
    return dict(version=VERSION,specification_identity=digest(spec),parameter_pool_version=spec['parameter_pool_version'],
        structural_proposal_order=proposals,control_initial=control_start,search_schedule=search,
        validation_schedule=schedule(spec),allocation=config['allocation'],
        planned_coverage=coverage(spec,search),
        policy=config,full_budget=spec['formal_budget_per_group'],
        integration_budget=spec['integration_validation'],
        launch_status='prepared_only',llm_calls=0)


def schedule(spec):
    return [dict(case_id=c['case_id'],repetition=i+1,seed=seed)
            for c in spec['cases'] for i,seed in enumerate(spec['repetitions']['seeds'])]


def _call(host, tool, request_id, arguments, reason):
    receipt = host.invoke(dict(tool_id=tool,tool_version='1.0.0',request_id=request_id,
        arguments=arguments,reason=reason,evidence=[],cache='new'))
    atomic_json(host.folder/(request_id+'_receipt.json'),receipt)
    return receipt


def prepare_candidate(spec, *, candidate_id, changes, case_id, seed):
    """Freeze the actual candidate as the session input for owned reporting."""
    case = next(c for c in spec['cases'] if c['case_id']==case_id)
    from tools.candidate_parameters import project_planning_configuration
    from tools.platform_search import parameter_search
    source=project_planning_configuration(spec['starting_configuration']['effective'],spec['execution_template']['policy'])
    source['run_id'] = candidate_id
    if changes:
        variables={p:spec['parameter_grants'][p] if isinstance(spec['parameter_grants'][p][0],(int,float)) else
                   dict(kind='discrete',choices=spec['parameter_grants'][p]) for p in changes}
        algorithm=parameter_search(source,'search.family_explicit@1.0.0',variables,candidates=[changes])
        changes=algorithm.propose()
    inp = plain(_candidate(SessionInput.model_validate(source),changes,registry()))
    initial = map_initial_state(inp,case)
    inp['task']['initializer']['parameters']['data'] = initial
    inp['seed'] = seed; inp['task']['sampling']['seeds'] = [seed]
    inp['policy']['budget'] = dict(tool_calls=3,model_calls=0,backend_solves=1,worker_calls=0,wall_s=990.)
    inp['policy']['model'] = deepcopy(spec['comparison_groups']['model_configuration'])
    inp['policy']['allowed_tools'] = ['simulation.run','evaluation.run','control.profile_report']
    inp['policy']['tool_bindings'] = {p:'1.0.0' for p in inp['policy']['allowed_tools']}
    # Per-operation ceilings are the retained policy; they do not alter solver stopping.
    inp['policy']['operation_allowances'] = dict(
        **{'simulation.run':dict(timeout_s=900.,reserve_s=900.),
           'evaluation.run':dict(timeout_s=30.,reserve_s=30.),
           'control.profile_report':dict(timeout_s=60.,reserve_s=60.)})
    return inp, initial


def evaluate_candidate(store, spec, *, candidate_id, changes, case_id, seed, repetition, purpose):
    """One fresh complete pipeline, retaining partial failures without retries."""
    inp, initial = prepare_candidate(spec,candidate_id=candidate_id,changes=changes,case_id=case_id,seed=seed)
    host = Host(store.root,candidate_id,actor='fixed-mathematical-workflow')
    # An existing session means an already scheduled attempt; never reinitialize it.
    with store.connect(True) as db:
        if db.execute('SELECT 1 FROM sessions WHERE run_id=?',(candidate_id,)).fetchone():
            raise ValueError('ATTEMPT_ALREADY_SCHEDULED_NO_REPLAY')
    host.create(inp)
    entry = dict(candidate_id=candidate_id,changes=changes,case_id=case_id,seed=seed,repetition=repetition,
        purpose=purpose,status='pending',initial_state=initial,
        shared_preparation_version='shared.parameter_search@1.1.0',adaptation_allocation=dict(
            controller='controller.gvs_nmpc@7.0.0',embedded_updates_scheduled=35,
            control_pair={p:changes.get(p,initial_values(spec,spec['fixed_baseline']['control_variables'])[p])
                          for p in spec['fixed_baseline']['control_variables']}),receipts=[])
    atomic_json(host.folder/'research_entry.json',entry)
    simulation = _call(host,'simulation.run','simulation',dict(candidate_id=candidate_id,changes={}),
        'Predeclared fresh study execution; regenerate candidate warm states from both measured position and velocity.')
    entry['receipt'] = simulation; entry['receipts'].append(simulation)
    entry['status'] = simulation['execution_status']
    if simulation['execution_status']=='completed' and simulation.get('output'):
        evaluation = _call(host,'evaluation.run','evaluation',dict(result=simulation['output'],execution_id=simulation['execution_id']),
            'Retain official terminal reach evaluator unchanged.')
        entry['receipts'].append(evaluation)
        if evaluation['execution_status']=='completed':
            profile = _call(host,'control.profile_report','profile',dict(simulation_request_id='simulation',evaluation_request_id='evaluation'),
                'Read execution-owned holding samples, applied force bounds and complete computation costs.')
            entry['receipts'].append(profile)
            if profile['execution_status']=='completed':
                state = store.session(candidate_id)['state']
                configuration = state['result_executions'][simulation['execution_id']]['candidate_input']
                effective = store.artifact(configuration)['effective']
                report = store.artifact(profile['output'])
                detail = report['detail']; motion = store.artifact(detail['motion']) if detail.get('motion') else None
                # This one result object is consumed by ranking, stopping and reporting.
                entry.update(configuration=configuration,evaluation=evaluation['output'],profile=profile['output'],
                    acceptance=assemble_acceptance(effective,store.artifact(evaluation['output']),report,
                        evaluation_reference=evaluation['output'],profile_reference=profile['output'],motion=motion),
                    status='completed',profile_summary={k:v for k,v in detail.items() if k not in ('motion','one_step_prediction_evidence','numerical_preparation')})
                entry['adaptation_allocation'].update(embedded_updates_completed=detail['updates'],
                    accepted_noninitialization_plans=detail['accepted_noninitialization_plans'],
                    measured_wall_s=simulation['charged']['wall_s'])
    entry['structural_infeasibility_proven'] = False
    entry['cost'] = {k:sum(r.get('charged',{}).get(k,0) for r in entry['receipts'])
                     for k in ('tool_calls','model_calls','backend_solves','worker_calls','wall_s')}
    atomic_json(host.folder/'research_entry.json',entry)
    with store.transaction() as db:
        ref = store.put(db,entry)
        store.event(db,candidate_id,'fixed_baseline_result',entry['status'],outputs=[ref],version=VERSION)
        state = store.session(candidate_id,db)['state']; state['research_result']=plain(ref)
        store.update_state(db,candidate_id,state,status='stopped')
    return entry


def _project(directory, spec, mode):
    store = Store(directory)
    if store.db.exists():
        raise ValueError('EXISTING_RESEARCH_RUN: inspect sealed results; no automatic repetition or budget reset')
    budget = spec['integration_validation']['budget'] if mode=='smoke' else spec['formal_budget_per_group']
    store.create(dict(project_id='research-first-study-'+mode,grant_id='research-first-study-'+mode+'-'+digest(str(store.root))[:16],
        authorization_source='Independent operator authorization for this new integration execution; no transfer of the earlier smoke grant.' if mode=='smoke' else 'Explicit invocation of the prepared fixed baseline study by the operator; separate comparison allocation.',
        budget=budget,exclusive_resources={'mujoco':1}))
    return store


def run_smoke(directory, spec):
    """Next independently authorized shared-path development execution, one attempt."""
    store = _project(directory,spec,'smoke'); frozen = spec['integration_validation']
    plan = baseline_plan(spec)
    plan.update(launch_status='smoke_scheduled',schedule=[{k:frozen[k] for k in ('case_id','seed','repetition','changes')}])
    atomic_json(store.root/'fixed_plan.json',plan)
    with store.transaction() as db: store.put(db,dict(specification=spec,plan=plan))
    result = evaluate_candidate(store,spec,candidate_id='shared-path-v11-near-section-096-near-z-plus',
        changes=frozen['changes'],case_id=frozen['case_id'],seed=frozen['seed'],repetition=frozen['repetition'],purpose='integration_smoke')
    acceptance = result.get('acceptance')
    aggregation = aggregate_acceptance([result],1,schedule=plan['schedule'])
    delivery = dict(version=VERSION,specification_identity=digest(spec),mode='integration_smoke',
        status='complete_integration' if result['status']=='completed' else 'integration_incomplete',
        result=result,acceptance=aggregation,stop=stop_interpretation(aggregation,'completed_schedule',remaining_work=0),
        historical_comparison=dict(source=spec['source']['candidate'],
            matched_conditions=False,reason='New section scale and nonzero initial bend/rate; historical nominal result is source context, not a matched robustness baseline.'),
        budget=store.remaining(),formal_campaign_launched=False,model_calls=0,
        development_case=True,previously_exposed=True,
        claims='Shared source projection, catalog mappings and finite ask/tell preparation feed the actual receipt executor. Native planner role/evidence ledger is separate; no robustness or research superiority established.')
    atomic_json(store.root/'delivery.json',delivery)
    return delivery


def _prefer(new, old):
    known=lambda row: row.get('acceptance',{}).get('status') in ('accepted','valid_failure')
    if not known(new): return False
    if not known(old): return True
    return compare_acceptance(new['acceptance'],old['acceptance'])['relation']=='improved'


def coverage(spec, rows):
    """Actual distinct edited values; availability is separate from optimization."""
    start=initial_values(spec,list(spec['parameter_grants']))
    result={p:dict(values=[],attempts=0,complete_results=0) for p in start}
    for row in rows:
        for path,value in row['changes'].items():
            if value==start[path]: continue
            cell=result[path]
            if value not in cell['values']: cell['values'].append(value)
            cell['attempts']+=1
            if row.get('status')=='completed' and row.get('acceptance',{}).get('status') in ('accepted','valid_failure'):
                cell['complete_results']+=1
    return dict(variables=result,changed_variables=[p for p,r in result.items() if r['attempts']],
        unvisited_variables=[p for p,r in result.items() if not r['attempts']],
        interpretation='Finite proposals and observed coverage, not exhaustive optimization of the exposed eight-variable pool.')


def select_candidate(rows):
    """One novel, fresh nominal joint pass; nondominance then frozen order."""
    eligible=[r for r in rows if r['changes'] and r.get('acceptance',{}).get('status')=='accepted'
              and r.get('receipt',{}).get('cache_hit') is False
              and r['receipt'].get('charged',{}).get('backend_solves')==1
              and r['receipt'].get('tool_id')=='simulation.run'
              and r['receipt'].get('execution_id')==r['acceptance'].get('execution_id')
              and r['receipt'].get('original_execution_id') in (None,r['receipt']['execution_id'])]
    return next((r for r in eligible if not any(other is not r and _prefer(other,r) for other in eligible)),None)


def can_reserve(remaining, executions):
    return all(remaining[k]>=executions*amount for k,amount in
               dict(backend_solves=1,tool_calls=3,wall_s=990.).items())


def run_study(directory, spec):
    """Eight search slots, unchanged incumbent and one frozen matched challenger."""
    plan=baseline_plan(spec);store=_project(directory,spec,'study')
    atomic_json(store.root/'fixed_plan.json',plan)
    with store.transaction() as db: store.put(db,spec)
    search=[];all_results=[]
    for n,slot in enumerate(plan['search_schedule']):
        # Twenty complete validation executions remain protected during search.
        if not can_reserve(store.remaining()['remaining'],21): break
        row=evaluate_candidate(store,spec,candidate_id=f'search-{n}',changes=slot['changes'],
            case_id=slot['case_id'],seed=slot['seed'],repetition=slot['repetition'],purpose='search_adaptation')
        row.update(structure_slot=slot['structure_slot'],control_slot=slot['control_slot'])
        search.append(row);all_results.append(row)
    chosen=select_candidate(search)
    # Freeze the challenger before observing any matched validation outcome.
    frozen=dict(candidate_id=chosen['candidate_id'],configuration=chosen['configuration'],changes=deepcopy(chosen['changes'])) if chosen else None
    groups=[dict(role='unchanged_incumbent',candidate=spec['source']['candidate'],changes={},records=[])]
    if frozen: groups.append(dict(role='selected_candidate',candidate=frozen,changes=frozen['changes'],records=[]))
    scheduled=schedule(spec)
    validation_plan=dict(schedule=scheduled,groups=[{k:v for k,v in g.items() if k!='records'} for g in groups],
        selected_candidate=frozen,candidate_validation_scheduled=bool(frozen),
        unused_candidate_allocation=0 if frozen else 10)
    atomic_json(store.root/'matched_validation_schedule.json',validation_plan)
    blocked=False
    # Each case/repetition is paired in order; every execution is fresh.
    for slot in scheduled:
        if not can_reserve(store.remaining()['remaining'],len(groups)):
            blocked=True;break
        for group in groups:
            row=evaluate_candidate(store,spec,candidate_id=f'validate-{group["role"]}-{slot["case_id"]}-rep-{slot["repetition"]}',
                changes=group['changes'],purpose='matched_validation_'+group['role'],**slot)
            group['records'].append(row);all_results.append(row)
    robustness=[dict(role=g['role'],candidate=g['candidate'],changes=g['changes'],
        acceptance=aggregate_acceptance(g['records'],10,schedule=scheduled)) for g in groups]
    complete=lambda g,a: len(g['records'])==10 and all(
        e['fresh_execution'] and e['acceptance_execution_matches'] and e['status'] in ('accepted','valid_failure') for e in a['entries'])
    comparison=(compare_acceptance(robustness[1]['acceptance'],robustness[0]['acceptance'])
                if frozen else dict(relation='unavailable',reason='No eligible new candidate'))
    promote=frozen is not None and comparison['relation']=='improved'
    outstanding=sum(r['acceptance']['unrecorded'] for r in robustness)
    reason='predeclared_policy' if not frozen or outstanding or blocked else 'completed_schedule'
    delivered_index=1 if promote else 0
    stop=stop_interpretation(robustness[delivered_index]['acceptance'],reason,remaining_work=outstanding)
    stop['success_claim_supported']=complete(groups[delivered_index],robustness[delivered_index]['acceptance']) and robustness[delivered_index]['acceptance']['all_scheduled_accepted']
    delivery=dict(version=VERSION,specification_identity=digest(spec),results=all_results,robustness=robustness,
        selected_candidate=frozen,selection_outcome='eligible_candidate_frozen' if frozen else 'no_eligible_new_candidate',
        delivered_candidate=frozen if promote else spec['source']['candidate'],candidate_promoted=promote,
        matched_comparison=comparison,improvement_claim_supported=promote,
        budget=store.remaining(),llm_calls=0,launch_status='fixed_baseline_schedule_finished' if not blocked else 'fixed_baseline_incomplete',
        allocation=plan['allocation'],search_attempts=len(search),actual_search_coverage=coverage(spec,search),
        search_slots_unperformed=len(plan['search_schedule'])-len(search),validation_plan=validation_plan,
        structural_infeasibility_proven=False,adaptation_is_not_replication=True,stop=stop)
    atomic_json(store.root/'delivery.json',delivery)
    return delivery


def export_evidence(directory, destination):
    """Portable immutable artifacts, including raw sealed backend exports."""
    store=Store(directory);destination=Path(destination); destination.mkdir(parents=True,exist_ok=True)
    manifest=[]
    with store.connect(True) as db:
        for row in db.execute('SELECT id,media,body FROM artifacts ORDER BY id'):
            suffix='.json' if row['media']=='application/json' else '.bin'
            path=destination/'artifacts'/(row['id']+suffix);path.parent.mkdir(parents=True,exist_ok=True)
            body=bytes(row['body']);path.write_bytes(body)
            manifest.append(dict(reference=dict(artifact_id=row['id'],media_type=row['media']),
                path=path.relative_to(destination).as_posix(),size_bytes=len(body),sha256=hashlib.sha256(body).hexdigest()))
    for name in ('fixed_plan.json','delivery.json'):
        atomic_json(destination/name,read(store.root/name))
    atomic_json(destination/'artifact_manifest.json',dict(store_root=store.root.relative_to(ROOT).as_posix(),artifacts=manifest))
    return manifest
