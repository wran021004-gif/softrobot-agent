"""Read sealed measurements, interpret under original rules, export checkpoint."""
from pathlib import Path
from copy import deepcopy
import json
import shutil
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from examples import milestone45_checkpoint as stage
from tools.state_io import read,atomic_json,digest
from tools.platform_store import Store,zero


def receipt_accounting(root):
    store=Store(root)
    with store.connect(True) as db:
        calls=[dict(r) for r in db.execute('SELECT * FROM calls')]
        numerical=db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone()
    receipts=[json.loads(r['receipt']) for r in calls if r['receipt']]
    pending=[dict(run_id=r['run_id'],request_id=r['request_id'],reserved=json.loads(r['reserved'])) for r in calls if not r['receipt']]
    total={k:sum(r['charged'][k] for r in receipts) for k in zero()}
    return dict(actual=total,remaining=store.remaining()['remaining'],receipts=receipts,pending=pending,
        numerical_work=json.loads(numerical[0]) if numerical else None)


def accounting():
    four=receipt_accounting(stage.M4);five=receipt_accounting(stage.M5)
    successor=read(ROOT/'evidence/milestone5_successor_20261005/accounting.json')
    bases=dict(m5_predecessor_lifetime=successor['prior_lifetime_accounting']['cumulative'],
        m5_successor=successor['successor_actual'],
        m4_autonomous_predecessor=read(ROOT/'evidence/milestone4_autonomous_20261005/acceptance_audit.json')['budget']['used'],
        m4_autonomous_successor=read(stage.OLD4/'acceptance_audit.json')['usage']['used'])
    base={k:sum(v[k] for v in bases.values()) for k in zero()}
    lifetime={k:base[k]+four['actual'][k]+five['actual'][k] for k in zero()}
    updates=sum(read(p)['factual_result']['control_updates'] for p in stage.M5.glob('backend_original*.json'))
    result=dict(m4_reporting=four,m5_development=five,linked_lifetime_bases=bases,lifetime_before_this_checkpoint=base,
        lifetime_with_new_scopes=lifetime,base_sources=['evidence/milestone5_successor_20261005/accounting.json',
            'evidence/milestone4_autonomous_20261005/acceptance_audit.json','evidence/milestone4_autonomous_20261006/acceptance_audit.json'],
        protected_validation=successor['protected_validation'],protected_backend_slots_remaining=6,
        new_embedded_backend_controller_updates=updates,
        new_standalone_controller_attempts=(five['numerical_work'] or {}).get('used',{}).get('local_solves',0),
        new_full_forecast_emulated_physics_steps=sum(read(p)['emulated_physics_steps'] for p in stage.M5.glob('forecast_original*.json') if not p.name.endswith(('_pending.json','_receipt.json'))),
        new_targeted_diagnostic_emulated_physics_steps=160 if (stage.M5/'fixed_diagnostics.json').exists() else 0,
        actual_avoided_evaluations=0,actual_screening_savings_s=0.,workers=0,subagents=0,
        convention='Outer numerical/provider/tool receipts charge actual elapsed once. Embedded backend updates are recorded separately and not debited as standalone work. Existing offline inspection/edit/test/export convention retained. These are separate grants, not withdrawals from protected or old stopped scopes.')
    atomic_json(stage.M5/'accounting.json',result);return result


def dist(values):
    values=[float(x) for x in values if x is not None]
    if not values:return None
    return dict(count=len(values),min_s=min(values),median_s=float(np.median(values)),mean_s=float(np.mean(values)),
        p95_s=float(np.quantile(values,.95)),max_s=max(values),deadline_misses=sum(x>.01 for x in values),
        worst_case_guarantee=False)


def delta(a,b):
    return dict(position_m=float(np.linalg.norm(np.asarray(a['position_m'])-b['position_m'])),
        vector_m_s=float(np.linalg.norm(np.asarray(a['velocity_m_s'])-b['velocity_m_s'])),
        speed_m_s=abs(a['speed_m_s']-b['speed_m_s']))


def settle_pair_boundary():
    """Charge measured wrapper gaps once, without replaying calculations."""
    from datetime import datetime
    h=stage.host(stage.M5,stage.M5.name+'-report');store=h.store
    old=store.lookup(h.run_id,'pair_boundary_settlement')
    if old:return store.artifact(json.loads(old['receipt'])['output'])
    with store.connect(True) as db:
        events=[json.loads(r[0]) for r in db.execute('SELECT body FROM events ORDER BY seq')]
        calls=[dict(r) for r in db.execute('SELECT * FROM calls')]
    def event(request,status):
        found=[e for e in events if e['request_id']==request and e['status']==status]
        if len(found)!=1:raise ValueError('UNIQUE_BOUNDARY_EVENT_REQUIRED')
        return found[0]
    def span(a,b):return (datetime.fromisoformat(b['timestamp'])-datetime.fromisoformat(a['timestamp'])).total_seconds()
    first=event('forecast_original075','reserved');seal=event('pair_seal','completed');end=event('backend_summary_original15','completed')
    covered=[]
    for call in calls:
        reserved=next(e for e in events if e['event_id']==call['parent_id'])
        if first['sequence']<=reserved['sequence']<=end['sequence']:
            if not call['receipt']:raise ValueError('UNSEALED_PAIR_CHARGE')
            covered.append(dict(call=call,reservation=reserved,receipt=json.loads(call['receipt'])))
    nested=sum(c['receipt']['charged']['wall_s'] for c in covered);total=span(first,end);extra=max(0.,total-nested)
    forecast_span=span(first,seal);forecasts_nested=sum(c['receipt']['charged']['wall_s'] for c in covered if c['reservation']['sequence']<=seal['sequence'])
    backend_costs={};previous=seal
    for name in ('original075','original15'):
        completed=event('backend_summary_'+name,'completed');backend_costs[name]=span(previous,completed);previous=completed
    result=dict(boundary='First forecast reservation to final paired backend-summary completion; Store UTC event wall span, not a hardware measurement.',
        start_event=first,end_event=end,total_pair_wall_span_s=total,already_charged_nested_s=nested,
        additional_wrapper_overhead_s=extra,forecast_and_pair_seal_operational_s=forecast_span,
        nested_forecast_and_pair_seal_s=forecasts_nested,corresponding_complete_backend_costs_s=backend_costs,
        assumption='No system UTC clock adjustment during this recorded interval; individual component timers use monotonic perf_counter.',
        excluded='Offline protocol registration, interpreter launch and first report-host registration before the first numerical reservation; follows the existing engineering convention. Native/model/controller setup is metered inside the forecasts.',
        no_numerical_replay=True,no_double_charge=True)
    row,_=store.reserve(h.run_id,'pair_boundary_settlement',digest(result),h.actor,{**zero(),'tool_calls':1,'wall_s':max(30.,extra)})
    receipt=store.complete(row,dict(request_id='pair_boundary_settlement',execution_id=row['execution_id'],caller=h.actor,
        tool_id='accounting.pair_boundary',tool_version='1.0.0',execution_status='completed',charged=zero()),result,extra)
    atomic_json(stage.M5/'pair_boundary_settlement.json',result);atomic_json(stage.M5/'pair_boundary_settlement_receipt.json',receipt)
    return result


def operational_assessment():
    a=deepcopy(read(stage.M5/'assessment.json'));b=settle_pair_boundary();economics=a['economics']
    model_s=sum(r['charged']['wall_s'] for r in receipt_accounting(stage.M5)['receipts'] if r['tool_id']=='model.deepseek')
    rejected=a['predicted_pair_decision']['hypothetical_rejection'];avoided=b['corresponding_complete_backend_costs_s'][rejected] if rejected else 0.
    economics.update(operational_pair_reuse_s=b['forecast_and_pair_seal_operational_s']+model_s,
        required_interpretation_s=model_s,counterfactual_one_evaluation_cost_s=avoided,
        counterfactual_net_s=avoided-b['forecast_and_pair_seal_operational_s']-model_s,
        corresponding_measured_backend_costs_s=b['corresponding_complete_backend_costs_s'],
        metered_pair_boundary=b,own_pending_model_request_cost='Added after its receipt; not known by the model while generating that response.')
    a['original_assessment_identity']=digest(read(stage.M5/'assessment.json'))
    atomic_json(stage.M5/'operational_assessment.json',a);return a


def assessment(ctx):
    from extensions.tendon_family.milestone5_protocol import pair_decision
    p=read(stage.M5/'protocol.json');seal=read(stage.M5/'pair_seal.json');cases=[];actual_histories=[]
    for c in p['candidates']:
        name=c['name'];forecast=read(stage.M5/('forecast_'+name+'.json'));actual=read(stage.M5/('backend_summary_'+name+'.json'))
        if forecast['implementation_identity']!=actual['implementation_identity']:raise ValueError('MATCHED_IMPLEMENTATION_REQUIRED')
        if len(forecast['rows'])!=len(actual['motion']) or len(actual['updates'])!=35:raise ValueError('FULL_TRAJECTORY_COVERAGE')
        changes={k:forecast['metrics'][k]-actual['metrics'][k] for k in forecast['metrics']}
        predicted=forecast['classification'];observed=stage.classification(actual['metrics'])
        comparison=[];first_output=None;first_command=None;first_state=None;first_selection=None
        initial=np.asarray(c['initial_full_state']);previous_command=forecast['rows'][0]['previous_input_n']
        for i,(f,a,u,full,capture) in enumerate(zip(forecast['rows'],actual['motion'],actual['updates'],actual['full_states'],actual['command_plan_capture'])):
            if abs(f['endpoint_s']-a['time_s'])>1e-8:raise ValueError('OUTPUT_CLOCK_MISMATCH')
            dif=delta(f,a);command=float(np.max(abs(np.asarray(f['input_n'])-u['actual_tension_n'])))
            current=initial if i==0 else np.asarray(actual['full_states'][i-1]['state'])
            full_current=float(np.max(abs(np.asarray(f['initial_full_state'])-current)))
            reduced=float(np.max(abs(np.r_[f['projected_current_state']['q_gvs'],f['projected_current_state']['qdot_gvs']]-u['measured_initial_state'])))
            receipt=f['command_receipt'];selection=receipt.get('optimization_selected_iteration')!=u.get('optimization_selected_iteration')
            row=dict(update_id=i,time_s=f['time_s'],endpoint_s=f['endpoint_s'],output_error=dif,
                full_current_state_linf=full_current,projected_current_state_linf=reduced,command_linf_n=command,
                forecast_selection_iteration=receipt.get('optimization_selected_iteration'),backend_selection_iteration=u.get('optimization_selected_iteration'),
                forecast_status=receipt.get('optimization_status'),backend_status=u.get('optimization_status'),
                forecast_initialization_selected=receipt.get('optimization_selected_iteration') in (-1,0),
                backend_initialization_selected=u.get('optimization_selected_iteration') in (-1,0),
                selected_plan_equal=f['plan_identity']==capture['plan_identity'],
                previous_input_difference_n=float(np.max(abs(np.asarray(f['previous_input_n'])-previous_command))))
            comparison.append(row)
            if first_output is None and max(dif['position_m']/1e-6,dif['vector_m_s']/1e-4,dif['speed_m_s']/1e-4)>1:first_output=row
            if first_command is None and command>1e-9:first_command=row
            if first_state is None and max(full_current,reduced)>1e-10:first_state=row
            if first_selection is None and selection:first_selection=row
            previous_command=u['actual_tension_n']
        timing_keys=('warm_preparation_s','optimization_solve_s','plan_validation_s','graph_construction_s','solver_construction_s')
        ft={key:dist(r['command_receipt'].get(key) for r in forecast['rows']) for key in timing_keys}
        bt={key:dist(r.get(key) for r in actual['updates']) for key in timing_keys}
        ft.update(software_input_to_command=dist(r['software_input_to_command_s'] for r in forecast['rows']),
            command=dist(r['complete_command_s'] for r in forecast['rows']),observation=dist(r['observation_s'] for r in forecast['rows']),
            packaging=dist(r['command_packaging_s'] for r in forecast['rows']),propagation=dist(r['propagation_s'] for r in forecast['rows']))
        bt.update(software_update=dist(r['update_wall_s'] for r in actual['updates']),
            observation=dist(r.get('state_preparation_s') for r in actual['updates']),
            controller_boundary=dist(r.get('controller_boundary_wall_s') for r in actual['updates']))
        actual_histories.append(dict(candidate_id=name,complete=True,rows=[dict(accepted=True) for _ in actual['motion']],metrics=actual['metrics']))
        cases.append(dict(candidate=name,forecast_complete=forecast['complete'],forecast_updates=len(forecast['rows']),
            backend_complete=True,backend_execution_id=actual['execution_id'],implementation_identity=actual['implementation_identity'],
            predicted_metrics=forecast['metrics'],actual_metrics=actual['metrics'],signed_metric_differences=changes,
            metric_accuracy=dict(terminal_position=abs(changes['terminal_error_m'])<=1e-6,
                holding_position=abs(changes['holding_max_error_m'])<=1e-6,holding_speed=abs(changes['holding_max_speed_m_s'])<=1e-4),
            trajectory_accuracy=dict(position_passes=sum(r['output_error']['position_m']<=1e-6 for r in comparison),
                vector_passes=sum(r['output_error']['vector_m_s']<=1e-4 for r in comparison),
                speed_passes=sum(r['output_error']['speed_m_s']<=1e-4 for r in comparison),samples=len(comparison),
                maximum_position_m=max(r['output_error']['position_m'] for r in comparison),maximum_vector_m_s=max(r['output_error']['vector_m_s'] for r in comparison),
                maximum_speed_m_s=max(r['output_error']['speed_m_s'] for r in comparison)),
            predicted_classification=predicted,actual_classification=observed,
            false_feasible={k:bool(predicted[k] and not observed[k]) for k in predicted},
            false_infeasible={k:bool(observed[k] and not predicted[k]) for k in predicted},
            earliest_observable=dict(output_threshold_failure=first_output,command_divergence=first_command,current_state_divergence=first_state,selected_iteration_difference=first_selection),
            per_update_comparison=comparison,forecast_timing=ft,backend_timing=bt,
            cold_setup=dict(native_loading_s=forecast['native_loading_s'],model_setup_s=forecast['model_setup_s'],controller_setup_s=forecast['setup_s']),
            forecast_receipt_s=read(stage.M5/('forecast_'+name+'_receipt.json'))['charged']['wall_s'],
            backend_evaluation_profile_cost_s=actual['backend_cost_s'],backend_preparation_s=actual['preparation_cost_s']))
    observed_decision=pair_decision(actual_histories);predicted_decision=seal['pair_decision']
    numerical=read(stage.M5/'fixed_diagnostics.json') if (stage.M5/'fixed_diagnostics.json').exists() else None
    all_accuracy=all(all(c['metric_accuracy'].values()) and all(c['trajectory_accuracy'][k]==35 for k in ('position_passes','vector_passes','speed_passes')) for c in cases)
    totals={k:sum(c['forecast_timing'][k]['mean_s']*c['forecast_timing'][k]['count'] for c in cases if c['forecast_timing'][k]) for k in ('warm_preparation_s','optimization_solve_s','plan_validation_s')}
    dominant=max(totals,key=totals.get)
    research_receipts=receipt_accounting(stage.M5)['receipts']
    interpretation_s=sum(r['charged']['wall_s'] for r in research_receipts if r['tool_id']=='model.deepseek')
    pair_forecast_s=sum(c['forecast_receipt_s'] for c in cases)
    matched_costs={c['candidate']:c['backend_evaluation_profile_cost_s']+c['backend_preparation_s']+read(stage.M5/('backend_loading_'+c['candidate']+'_receipt.json'))['charged']['wall_s'] for c in cases}
    rejected=predicted_decision['hypothetical_rejection'];avoided=matched_costs[rejected] if rejected else 0.
    result=dict(version='m5_matched_assessment@1.0.0',cases=cases,predicted_pair_decision=predicted_decision,
        actual_pair_decision=observed_decision,ranking=dict(resolved=predicted_decision['status']=='resolved',
            correct=predicted_decision['status']=='resolved' and predicted_decision['order']==observed_decision['order'],
            useful=predicted_decision['status']=='resolved' and predicted_decision['order']==observed_decision['order'] and all_accuracy,
            abstention=predicted_decision['status']=='abstain'),
        accuracy_passed=all_accuracy,fixed_local_diagnostics=numerical,
        economics=dict(forecast_pair_s=pair_forecast_s,required_interpretation_s=interpretation_s,
            operational_pair_reuse_s=pair_forecast_s+interpretation_s,
            counterfactual_one_evaluation_cost_s=avoided,
            counterfactual_net_s=avoided-pair_forecast_s-interpretation_s,
            corresponding_measured_backend_costs_s=matched_costs,actual_avoided_evaluations=0,actual_savings_s=0.,
            cold_compile_increment_s=p['implementation']['kernel']['compile_s'],
            cold_start_scope='Same exact robot structure and physical function; historic compile time is a measured scenario increment, not a new charge or universal compile cost.',
            operational_use_qualified=False),
        bottleneck=dict(component=dominant,measured_pair_component_totals_s=totals,
            semantic_constraint='Original feasible-return minimum_s and budget_s retained; native evaluation acceleration changes timed iteration selection. No hidden stopping-policy change permitted.',
            action='Stop this development route at checkpoint; no revision/rerun. Current seconds-scale latency and timed closed-loop mismatch do not justify another same-policy pair.',
            next_specific_objective='Develop and separately authorize a controller algorithm/termination rule whose complete measured input-to-command latency meets 10 ms, then repeat paired forecast/reference accuracy and feasibility tests. The current wall-time policy cannot provide that guarantee.'),
        realtime=dict(deadline_s=.01,demonstrated=False,
            forecast_deadline_misses=sum(c['forecast_timing']['software_input_to_command']['deadline_misses'] for c in cases),
            backend_deadline_misses=sum(c['backend_timing']['software_update']['deadline_misses'] for c in cases),
            boundary=read(stage.M5/'protocol.json')['costs'],hardware_guarantee=False),
        implementation_revision=None,original_numerical_protocol=read(stage.M5/'protocol.json')['local_numerical_protocol']['version'],
        historical_continuous_and_step_refinement_failures_preserved=True,
        formal_validation_admitted=False,protected_backend_slots_remaining=6,milestone5='open',incumbent_unchanged=True,
        limitations=['Timed optimizer stopping can produce different selected trajectories even under identical controller code/settings.',
            'Temporal order alone cannot identify a unique cause of divergence.',
            'Full-order point-mechanics emulation is expensive diagnostic work; it is not independent backend validation or hardware evidence.',
            'Six historical local checks and these development references cannot replace untouched prospective pairs or an independent repeat.'])
    return result


def fixed_diagnostics(ctx):
    from extensions.tendon_family.milestone5_fullstate import DiscreteFullState
    from extensions.tendon_family.milestone5_fixed_transition import predict
    from extensions.tendon_family.diagnostic_math import charge_units
    p=read(stage.M5/'protocol.json');rows=[]
    for name,i in (('original075',0),('original075',1),('original075',30),('original15',30)):
        c=next(c for c in p['candidates'] if c['name']==name);a=read(stage.M5/('backend_summary_'+name+'.json'))
        x=c['initial_full_state'] if i==0 else a['full_states'][i-1]['state'];u=a['updates'][i]['actual_tension_n']
        model=DiscreteFullState(c['configuration'],c['physics'],c['compiled'],c['xml'])
        charge_units(ctx,'component_evaluations',2);charge_units(ctx,'prediction_evaluations',1)
        lu=model.propagate(x,u,grid=dict(max_step_s=.0005),deadline=time.perf_counter()+30.)
        independent=predict(model,x,u,deadline=time.perf_counter()+30.)
        differences=delta(lu,independent);backend=delta(lu,a['motion'][i])
        rows.append(dict(candidate=name,update_id=i,initial_state_identity=digest(x),command=u,
            independent_cholesky_vs_lu=differences,lu_vs_new_backend=backend,
            max_scaled_residual=max(r['scaled_residual'] for r in independent['rows']),
            max_backward_error=max(r['backward_error'] for r in independent['rows']),
            max_condition_estimate=max(r['condition_estimate_inf'] for r in independent['rows']),
            passed=max(differences['position_m'],backend['position_m'])<=1e-6 and
                max(differences['speed_m_s'],differences['vector_m_s'],backend['speed_m_s'],backend['vector_m_s'])<=1e-4,
            scope='Post-outcome fixed-input propagation diagnostic, never fed to the sealed full forecast.'))
    return dict(protocol=p['local_numerical_protocol']['version'],cases=rows,passed=all(r['passed'] for r in rows),
        component_evaluations=8,local_intervals=4,controller_updates=0,backend_attempts=0)


def interpret(attempt=0):
    a=operational_assessment()
    packet=deepcopy(a)
    for c in packet['cases']:c.pop('per_update_comparison')
    packet['accounting']=accounting()
    packet['legal_options']=['Stop at explicit development checkpoint','Recommend separately bounded diagnostic work',
        'Recommend separately authorized substantive controller/termination development; no hidden solver/physics/threshold/stopping change']
    return stage.provider(stage.M5,'interpretation'+str(attempt),packet,
        'Interpret the actual new paired full-history forecasts and matching experimental-controller backend references. Use exact gates and costs. Separate trajectory/aggregate accuracy, pass/fail classification, feasibility-qualified ordering, operational economics and realtime. Both backends were run so actual savings zero. Fixed-input diagnostics are post-outcome and cannot repair a sealed failed history. Local numerical checks target the registered fixed 0.5 ms map only. Do not conflate historical production outcomes with these new experimental outcomes or claim unique causality. Assess observed earliest divergences and measured computational bottleneck; full software timing remains seconds and 10 ms requirement unchanged. Recommend continuation/use or stopping based on measured evidence. Original protected six validation slots untouched, incumbent unchanged, M5 remains open. One coherent next decision only, no executable scientific tool actions in this reporting handoff. Submit report_interpretation once.')


def correct_interpretation(attempt=1):
    a=operational_assessment();packet=deepcopy(a)
    for c in packet['cases']:c.pop('per_update_comparison')
    checks=a['fixed_local_diagnostics']['cases']
    corrections=dict(original_response=read(stage.M5/'interpretation0.json')['interpretation'],
        contradictions=[
            'The first response calls original075 terminal error matched although its 8.88121998851273e-6 m discrepancy exceeds the unchanged 1e-6 m accuracy tolerance. Both candidates fail every aggregate metric gate; task-position classification can nevertheless be correct.',
            'The first response explains useful=false by the lower-speed candidate being predicted-safe. original15 is also actually safe. The defects are the failed quantitative gates and original075 false-feasible holding-speed/joint classification, not the correct original15 classification.',
            'The first response gives unsupported approximate residual/backward-error ranges. Use the supplied exact maxima below or omit those approximate ranges. Fixed-input agreement does not repair complete closed-loop error.'],
        exact_fixed_diagnostic_maxima=dict(scaled_residual=max(c['max_scaled_residual'] for c in checks),
            backward_error=max(c['max_backward_error'] for c in checks),condition_estimate=max(c['max_condition_estimate'] for c in checks),
            independent_endpoint_position=max(c['independent_cholesky_vs_lu']['position_m'] for c in checks),
            independent_endpoint_vector=max(c['independent_cholesky_vs_lu']['vector_m_s'] for c in checks),
            new_backend_endpoint_vector=max(c['lu_vs_new_backend']['vector_m_s'] for c in checks)))
    packet.update(factual_correction=corrections,accounting=accounting(),legal_options=['Stop checkpoint','Separate bounded diagnostic proposal','Separately authorize substantive algorithm/termination development'])
    atomic_json(stage.M5/'interpretation_review0.json',dict(accepted=False,contradictions=corrections,
        scientific_recommendation_not_overridden=True,original_response_preserved=True))
    return stage.provider(stage.M5,'interpretation'+str(attempt),packet,
        'Correct only the factual contradictions listed in factual_correction using the exact measurement packet. Provide a compact standalone full interpretation, about 400 words. Do not call a metric matched when its accuracy gate fails. Keep actual pass/fail classification separate from quantitative accuracy. Explain correct-but-not-useful ordering from failed accuracy/false-feasible original075, while original15 joint classification is correct. Copy exact numerical maxima or omit uncertain rounding. Costs now include the first required interpretation receipt; the current request own cost is pending and will be added after return. Both backends ran, actual savings zero. Preserve M5 open, 10 ms requirement, six protected slots, incumbent, no unique causality, no formal admission. Recommend continuation/use or stop freely from actual evidence and legal options; do not prescribe a physical explanation or execute new science. Submit report_interpretation once.')


def export():
    for root,destination in ((stage.M4,stage.E4),(stage.M5,stage.E5)):
        destination.mkdir(parents=True,exist_ok=True)
        for path in root.glob('*.json'):
            if not path.name.endswith('_pending.json'):shutil.copy2(path,destination/path.name)
        atomic_json(destination/'receipt_accounting.json',receipt_accounting(root))
        if (root/'implementation').exists():
            shutil.copytree(root/'implementation',destination/'implementation',dirs_exist_ok=True)
        # Selected update histories and receipt outputs already exported as JSON.
        # Export backend manifests and non-secret source artifacts once, preserving bytes.
        store=Store(root)
        if root==stage.M5:
            from extensions.tendon_family.control_evidence import ControlEvidence
            reader=ControlEvidence(store)
            refs=[]
            for result_path in root.glob('backend_original*.json'):
                result=read(result_path)
                if result.get('status')!='evaluated':continue
                s=reader.resolve(result['execution_id']);refs.extend([s['manifest'],s['metadata']['candidate_input'],*s['files'].values()])
                refs.extend(r['output'] for r in result['receipts'].values() if r.get('output'))
            artifacts=destination/'artifacts';artifacts.mkdir(exist_ok=True)
            for ref in {r['artifact_id']:r for r in refs}.values():(artifacts/ref['artifact_id']).write_bytes(store.artifact(ref,raw=True))
        manifest=stage.hashes([p for p in destination.rglob('*') if p.is_file() and p.name!='sha256_manifest.json'])
        atomic_json(destination/'sha256_manifest.json',manifest)
    return accounting()


def documents():
    a=operational_assessment();cost=accounting();lines=[]
    lines += ['# M5 full feedback trajectory development checkpoint — 2026-10-06','',
        '**Milestone 5 remains open.** Two complete forecasts and two new independent',
        'development backend executions used the same scoped native experimental',
        'controller. Accuracy and holding-speed classification failed; correct pair',
        'ordering did not establish useful or economical screening. No revision or',
        'same-policy rerun was justified. The incumbent and all six protected formal',
        'validation slots remain unchanged.','',
        '## Frozen comparison and execution','',
        'The existing development cases `original075` and `original15` retain their',
        'exact saved robot, task, full initializer, controller weights and numerical',
        'settings. Their historical source executions are respectively',
        '`2413ff2a56de422dac47b7fd78717563` and `9865f1636266479c93817cad42a65353`.',
        'Those historical outcomes are not acceptance results for this new controller.',
        'The [protocol](../evidence/milestone5_matched_20261006/protocol.json) identifies',
        'the physical and numerical settings, full state, mappings, .5 ms physical',
        'step, .01 s replanning period, output times and unchanged quantitative rules.','',
        'The hash-checked local `gvs_native_chunked_kernel@2.0.0` DLL was reused.',
        'No compiler experiment, package change, solver migration, skipped replan or',
        'stopping-policy change occurred. The provider ContextVar was active only',
        'within these experimental executions. Default production functions were',
        'unchanged. Both forecasts evolve their own full state, previous command and',
        'plan; each command is retained before emulated propagation.','',
        'Both 35-update forecasts, component classifications and feasibility-qualified',
        'ordering were [sealed together](../evidence/milestone5_matched_20261006/pair_seal.json)',
        'before either new backend reservation. The actual matching executions are',
        '`95a801287a2646bbab73416a19c38dcc` and `5e34c91605904d5fae877c465b963cf7`.',
        'Each completed its existing official evaluation and profile. Emulation was',
        'not substituted for either backend.','',
        '## Prediction and classification','',
        '| Candidate | Terminal error, predicted / actual (mm) | Holding max error, predicted / actual (mm) | Holding max speed, predicted / actual (m/s) | Joint pass, predicted / actual |',
        '| --- | ---: | ---: | ---: | --- |']
    for c in a['cases']:
        f=c['predicted_metrics'];b=c['actual_metrics']
        lines.append(f"| {c['candidate']} | {f['terminal_error_m']*1000:.6f} / {b['terminal_error_m']*1000:.6f} | {f['holding_max_error_m']*1000:.6f} / {b['holding_max_error_m']*1000:.6f} | {f['holding_max_speed_m_s']:.9f} / {b['holding_max_speed_m_s']:.9f} | {c['predicted_classification']['joint']} / {c['actual_classification']['joint']} |")
    lines += ['',
        'Both candidates pass actual and predicted terminal/holding-position task',
        'classification. `original075` falsely predicts holding-speed and joint',
        'feasibility; `original15` classifies all task components correctly. There are',
        'no false-infeasible classifications. This does not establish quantitative',
        'accuracy: both candidates fail every aggregate accuracy gate under the',
        'original 1 micrometre position and .0001 m/s speed/vector tolerances.',
        'Only 2/35 and 6/35 samples respectively pass each trajectory output gate.',
        'The .15 holding-position aggregate discrepancy is 1.009776 micrometres,',
        'slightly above the unchanged 1 micrometre threshold.','',
        'Predicted and observed position-qualified speed ordering both resolve to',
        '`original15`, then `original075`; there is no abstention or wrong exclusion.',
        'One correct development order, failed accuracy and a false-feasible speed',
        'classification do not establish reliable screening, superiority or safety.','',
        '## Discrepancy localization and numerical support','',
        'For .075, the first meaningful command and output discrepancy occurs at',
        'update 2, time .02 s. Current full/projected state differences are only',
        '1.33e-15 / 8.53e-14 and previous input differs by 1.11e-15 N, yet selected',
        'iterations are 5 versus 10 and commands differ by .047479 N. Current states',
        'separate at update 3. For .15, small command/projection differences appear',
        'at update 4; accuracy first fails at update 6, with selected iterations 4',
        'versus 10. This is consistent with timed iteration selection sensitivity.',
        'Temporal order does not isolate a unique cause; floating-point state',
        'differences, evolving warm plans and later feedback remain relevant.','',
        'Four post-outcome fixed-input diagnostics at .075 updates 0/1/30 and .15',
        'update 30 used eight LU/independent-Cholesky component evaluations. All pass',
        '`fixed_backend_transition_validation@2.0.0`, including comparison against',
        'the new matched backend endpoints. They support those fixed .5 ms maps,',
        'not the accuracy of sealed closed-loop histories or continuous/hardware',
        'dynamics. The six existing local checks are reused; historical continuous',
        'solution and step-refinement failures remain preserved. Diagnostic outcomes',
        'were never supplied to either sealed forecast.','',
        '## Cost, latency and decision','']
    e=a['economics'];r=cost['m5_development']['actual'];component=a['bottleneck']['measured_pair_component_totals_s']
    lines += [f"Forecast receipts total **{e['forecast_pair_s']:.3f} s**. The metered forecast",
        f"plus pair-seal boundary and both required model interpretations cost **{e['operational_pair_reuse_s']:.3f} s**.",
        f"The corresponding complete .075 backend boundary costs **{e['counterfactual_one_evaluation_cost_s']:.3f} s**;",
        f"counterfactual net saving is **{e['counterfactual_net_s']:.3f} s**. Both backends ran, so",
        'actual avoided evaluations and actual screening savings are **zero**.',
        'This method is more expensive than the work its sealed order could omit.','',
        'The reuse boundary includes configuration/model/native loading, controller',
        'setup, observation/projection, graph/warm preparation, optimization,',
        'validation, command packaging, emulated propagation, seal/export overhead',
        'and required model interpretation/correction. Store event spans settle',
        'wrapper gaps once, without replay or double charging. Static protocol',
        'registration and first harness registration before the initial reservation',
        'follow the existing offline engineering convention. These are software',
        'cost boundaries, not end-to-end hardware measurements.','',
        'Cold compilation for this exact structure would add the historical measured',
        '599.757 s; it was not charged again or assumed free for other structures.',
        'Fresh structures need their own loading/compilation assessment. Development',
        'diagnostics and matched backends are separate from operational screening cost.','',
        '| Candidate | Forecast software interval mean / median / max (s) | Backend software update mean / median / max (s) | Deadline misses, forecast + backend |',
        '| --- | ---: | ---: | ---: |']
    for c in a['cases']:
        f=c['forecast_timing']['software_input_to_command'];b=c['backend_timing']['software_update']
        lines.append(f"| {c['candidate']} | {f['mean_s']:.6f} / {f['median_s']:.6f} / {f['max_s']:.6f} | {b['mean_s']:.6f} / {b['median_s']:.6f} / {b['max_s']:.6f} | 35 + 35 |")
    lines += ['',
        'Forecast input-to-command intervals are directly measured from supplied',
        'full state through projection/output preparation and packaged command.',
        'Backend intervals include current observation/projection and controller',
        'computation. Applying the command to simulated actuators and physical',
        'propagation are outside that command boundary and included in full backend',
        'cost. Forecast propagation is separately measured. Sensor/network/hardware',
        'delivery latency is not measured. Individual component distributions and',
        'one-time setup are retained; no small-sample worst-case guarantee is claimed.','',
        f"Optimization is the measured dominant component: **{component['optimization_solve_s']:.3f} s**",
        f"across the forecast pair, versus **{component['warm_preparation_s']:.3f} s** warm preparation",
        f"and **{component['plan_validation_s']:.3f} s** validation. All 140 command updates miss",
        'the original **10 ms** requirement. No coherent equation-preserving revision',
        'was justified by these accuracy, cost and latency results, so the chosen',
        'action is to stop this route at the development checkpoint.','',
        'A genuine DeepSeek interpretation and one neutral factual correction assess',
        'these measurements. The original response, numerical decisions and failed',
        'factual review are preserved. Model readiness language cannot override a',
        'failed numerical, classification, cost or realtime gate.','',
        'The next technical objective requires a separately explicit substantive',
        'controller/termination design that meets the full software 10 ms deadline,',
        'followed by new matched accuracy/classification studies. Formal admission',
        'still requires original local/trajectory accuracy, useful position-qualified',
        'ordering, positive complete economics, realtime and accepted factual research',
        'interpretation before the two untouched pairs and registered independent',
        'repeat. None of those protected cases ran here.','',
        f"New M5 charges: **{r['model_calls']} provider / {r['tool_calls']} workflow / {r['backend_solves']} backend / {r['wall_s']:.3f} s**.",
        'There are 70 standalone forecast controller updates, 70 separately recorded',
        'embedded backend updates, 2 complete forecasts, 1,400 forecast-emulated steps',
        'and 160 additional diagnostic-emulated steps. Eight component evaluations',
        'form four diagnostic intervals; these are not another set of controller',
        'solves. Unused new M5 allocations and linked lifetime receipts are in',
        '[accounting](../evidence/milestone5_matched_20261006/accounting.json). Zero',
        'workers or subagents ran; all six protected backend slots remain available.','',
        'Evidence: [final operational assessment](../evidence/milestone5_matched_20261006/operational_assessment.json),',
        '[initial assessment](../evidence/milestone5_matched_20261006/assessment.json),',
        '[fixed-input diagnostics](../evidence/milestone5_matched_20261006/fixed_diagnostics.json),',
        '[focused checks](../evidence/milestone5_matched_20261006/focused_checks.json),',
        '[pair cost boundary](../evidence/milestone5_matched_20261006/pair_boundary_settlement.json).','',
        'The initial protocol, prelaunch wrapper amendment and later reporting-only',
        'transport correction have separate recorded identities. Controller, native',
        'kernel, equations, numerical tolerances and stopping semantics stayed fixed',
        'through both forecasts and both backend executions.']
    (ROOT/'docs/milestone5_matched_development.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    return a


def focused_checks():
    p=read(stage.M5/'protocol.json');seal=read(stage.M5/'pair_seal.json');s=Store(stage.M5)
    with s.connect(True) as db:
        events=[json.loads(r[0]) for r in db.execute('SELECT body FROM events ORDER BY seq')]
        rows=[dict(r) for r in db.execute("SELECT * FROM calls WHERE request_id='complete-simulation'")]
    seal_events=[e for e in events if e['request_id']=='pair_seal' and e['status']=='completed']
    assert len(seal_events)==1
    reserve={e['event_id']:e for e in events}
    assert all(reserve[r['parent_id']]['sequence']>seal_events[0]['sequence'] for r in rows)
    names=[]
    for c in p['candidates']:
        f=read(stage.M5/('forecast_'+c['name']+'.json'));b=read(stage.M5/('backend_summary_'+c['name']+'.json'))
        assert f['implementation_identity']==b['implementation_identity']==p['implementation_identity']
        assert seal['forecasts'][c['name']]['identity']==digest(f)
        assert f['initial_state']==c['initial_full_state']
        for a,n in zip(f['rows'],f['rows'][1:]):
            assert n['initial_full_state']==a['state']
            assert n['previous_input_n']==a['input_n']
            assert n['warm_before_command']==a['selected_plan']
        assert len(f['rows'])==35 and all(r['replanned'] for r in f['rows'])
        assert len(f['holding_sample_times_s'])==6
        assert all(r['software_input_to_command_s']>=r['complete_command_s'] for r in f['rows'])
        names.append(c['name'])
    from extensions.tendon_family.gvs_trajectory import _FUNCTION_PROVIDER
    assert _FUNCTION_PROVIDER.get() is None
    for n,h in p['implementation']['files'].items():
        if n=='examples/milestone45_checkpoint.py':continue
        assert stage.hashes([ROOT/n])[n]==h
    a=accounting();assert not a['m5_development']['pending']
    assert a['new_standalone_controller_attempts']==70
    assert a['new_embedded_backend_controller_updates']==70
    assert a['m5_development']['actual']['backend_solves']==2
    assert a['protected_backend_slots_remaining']==6
    result=dict(passed=True,candidates=names,pair_seal_before_either_backend=True,
        candidate_specific_causal_state_input_and_plan=True,matching_experimental_identity=True,
        default_provider_absent=True,production_code_unchanged=True,timing_boundaries_checked=True,
        standalone_and_embedded_accounting_separate=True,protected_slots=6,
        static_prelaunch_checks='Four existing successor checks passed before launch; these checks verify the new sealed evidence without numerical replay.')
    atomic_json(stage.M5/'focused_checks.json',result);return result


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--phase',required=True);p.add_argument('--attempt',type=int,default=0);args=p.parse_args()
    if args.phase=='diagnostics':stage.operation(stage.M5,'fixed_diagnostics',fixed_diagnostics,60.)
    elif args.phase=='assessment':stage.operation(stage.M5,'assessment',assessment,60.)
    elif args.phase=='interpret':interpret(args.attempt)
    elif args.phase=='export':export()
    elif args.phase=='checks':focused_checks()
    elif args.phase=='settle':settle_pair_boundary();operational_assessment()
    elif args.phase=='correct':correct_interpretation(args.attempt or 1)
    elif args.phase=='documents':documents()
