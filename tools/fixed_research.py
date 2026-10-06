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

VERSION = 'fixed_coordinate_reach_hold@1.0.0'


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
    proposals = [start]
    for point in proposed_edits(spec,structural,start):
        if point not in proposals: proposals.append(point)
    return dict(version=VERSION,specification_identity=digest(spec),parameter_pool_version=spec['parameter_pool_version'],
        structural_proposal_order=proposals,control_initial=initial_values(spec,controls),
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
    source = deepcopy(spec['execution_template']); source['run_id'] = candidate_id
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
        purpose=purpose,status='pending',initial_state=initial,adaptation_allocation=dict(
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
        authorization_source='User goal attachment dated 2026-10-06; integration cap independent of all old milestone grants.' if mode=='smoke' else 'Explicit invocation of the prepared fixed baseline study by the operator; separate comparison allocation.',
        budget=budget,exclusive_resources={'mujoco':1}))
    return store


def run_smoke(directory, spec):
    """One changed candidate under pre-frozen two-attempt engineering cap."""
    store = _project(directory,spec,'smoke'); frozen = spec['integration_validation']
    plan = baseline_plan(spec)
    plan.update(launch_status='smoke_scheduled',schedule=[{k:frozen[k] for k in ('case_id','seed','repetition','changes')}])
    atomic_json(store.root/'fixed_plan.json',plan)
    with store.transaction() as db: store.put(db,dict(specification=spec,plan=plan))
    result = evaluate_candidate(store,spec,candidate_id='smoke-near-section-096-near-z-plus',
        changes=frozen['changes'],case_id=frozen['case_id'],seed=frozen['seed'],repetition=frozen['repetition'],purpose='integration_smoke')
    acceptance = result.get('acceptance')
    aggregation = aggregate_acceptance([result],1,schedule=plan['schedule'])
    delivery = dict(version=VERSION,specification_identity=digest(spec),mode='integration_smoke',
        status='complete_integration' if result['status']=='completed' else 'integration_incomplete',
        result=result,acceptance=aggregation,stop=stop_interpretation(aggregation,'completed_schedule',remaining_work=0),
        historical_comparison=dict(source=spec['source']['candidate'],
            matched_conditions=False,reason='New section scale and nonzero initial bend/rate; historical nominal result is source context, not a matched robustness baseline.'),
        budget=store.remaining(),formal_campaign_launched=False,model_calls=0,
        claims='Complete execution of shared pipeline only; no robustness or research superiority established.')
    atomic_json(store.root/'delivery.json',delivery)
    return delivery


def _prefer(new, old):
    known=lambda row: row.get('acceptance',{}).get('status') in ('accepted','valid_failure')
    if not known(new): return False
    if not known(old): return True
    return compare_acceptance(new['acceptance'],old['acceptance'])['relation']=='improved'


def run_study(directory, spec):
    """Prepared future workflow; this assignment does not invoke it."""
    store = _project(directory,spec,'study')
    atomic_json(store.root/'fixed_plan.json',baseline_plan(spec))
    with store.transaction() as db: store.put(db,spec)
    policy = spec['fixed_baseline']; structural = policy['structural_variables']; controls=policy['control_variables']
    centre = initial_values(spec,structural); original=deepcopy(centre); seen=set(); adapted=[]; all_results=[]
    incumbent=None
    for i in range(policy['max_structures']):
        candidates = [original] if i==0 else list(proposed_edits(spec,structural,centre))
        point = next((p for p in candidates if digest(p) not in seen),None)
        if point is None: break
        seen.add(digest(point)); control_centre=initial_values(spec,controls); best=None
        for j in range(policy['control_evaluations_per_structure']):
            if j:
                control_centre=next(proposed_edits(spec,controls,control_centre))
            if store.remaining()['remaining']['backend_solves'] < 1 or store.remaining()['remaining']['wall_s'] < 990.:
                break
            row = evaluate_candidate(store,spec,candidate_id=f'adapt-structure-{i}-control-{j}',
                changes={**point,**control_centre},case_id='nominal',seed=17,repetition=1,purpose='nominal_control_adaptation')
            all_results.append(row)
            if best is None or _prefer(row,best): best=row
            if best.get('acceptance'):
                control_centre={p:best['changes'][p] for p in controls}
        if best is None: break
        best['structure_adaptation_allocations']=[r['adaptation_allocation'] for r in all_results if r['candidate_id'].startswith(f'adapt-structure-{i}-')]
        adapted.append(best)
        if incumbent is None or _prefer(best,incumbent):
            incumbent=best; centre={p:best['changes'][p] for p in structural}
    # Pairwise dominance retains tradeoffs; deterministic proposal order handles ties.
    finalists = [r for r in adapted if r.get('acceptance',{}).get('status') in ('accepted','valid_failure') and not any(
        other is not r and _prefer(other,r) for other in adapted)][:policy['max_finalists']]
    scheduled=schedule(spec); robustness=[]
    for n, finalist in enumerate(finalists):
        validation=[]
        atomic_json(store.root/f'finalist_{n}_schedule.json',dict(candidate=finalist['configuration'],schedule=scheduled))
        for slot in scheduled:
            if store.remaining()['remaining']['backend_solves'] < 1 or store.remaining()['remaining']['wall_s'] < 990.: break
            row=evaluate_candidate(store,spec,candidate_id=f'finalist-{n}-{slot["case_id"]}-rep-{slot["repetition"]}',
                changes=finalist['changes'],purpose='frozen_robustness_validation',**slot)
            validation.append(row);all_results.append(row)
        robustness.append(dict(candidate=finalist['configuration'],changes=finalist['changes'],
            acceptance=aggregate_acceptance(validation,len(scheduled),schedule=scheduled)))
    selected=None
    for row in robustness:
        if selected is None or compare_acceptance(row['acceptance'],selected['acceptance'])['relation']=='improved':selected=row
    outstanding=sum(r['acceptance']['unrecorded'] for r in robustness)
    stop=(stop_interpretation(selected['acceptance'],'completed_schedule',remaining_work=0) if selected and not outstanding else
          stop_interpretation(selected['acceptance'],'predeclared_policy',remaining_work=outstanding) if selected else
          dict(legal=True,reason='predeclared_policy',success_claim_supported=False,optimality='not_assessed'))
    delivery=dict(version=VERSION,specification_identity=digest(spec),results=all_results,robustness=robustness,
        selected=selected,budget=store.remaining(),llm_calls=0,launch_status='fixed_baseline_complete',
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
