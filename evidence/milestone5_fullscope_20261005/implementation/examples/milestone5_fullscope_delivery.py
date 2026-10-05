"""Receipt-based acceptance and delivery for the separately authorized campaign."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from examples import milestone5_fullscope as stage
from tools.platform_store import Store,zero
from tools.state_io import read,atomic_json,digest


def records():
    store=Store(stage.RUN)
    with store.connect(True) as db:
        receipts=[json.loads(r[0]) for r in db.execute('SELECT receipt FROM calls WHERE receipt IS NOT NULL')]
        work=json.loads(db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone()[0])
        ids=[r[0] for r in db.execute('SELECT run_id FROM sessions')]
    return store,receipts,work,[e for name in ids for e in store.events(name)]


def assessment():
    from extensions.tendon_family.diagnostic_evidence import measured_motion
    from extensions.tendon_family.milestone5_protocol import pair_decision,assess_screening
    from examples.milestone5_predictor_development import historical_backend_costs
    stage.check_previous();store,receipts,work,events=records()
    # Use the database run binding, not the actor's display name.
    with store.connect(True) as db:
        research=sum(json.loads(r[0])['charged']['wall_s'] for r in db.execute("SELECT receipt FROM calls WHERE run_id='m5full-research' AND receipt IS NOT NULL"))
    local=[]
    for revision in (1,2):
        a=read(stage.RUN/f'revision{revision}_local.json');cases=[]
        for c in a['cases']:
            r,s=stage.source(c['source']);target=np.asarray(s['configuration']['task']['goal']['data']['target_m'])
            p=c['results'][-1 if revision==1 else c['primary_grid_index']];o=c['observed_endpoint']
            predicted_position_error=float(np.linalg.norm(np.asarray(p['position_m'])-target));observed_position_error=float(np.linalg.norm(np.asarray(o['position_m'])-target))
            cases.append(dict(case=c['case'],score=c['score'],numerical_pass=c['numerical_pass'],numerical_differences=c['numerical_differences'],
                initial_reduced_position_error_m=c['initial_reduced_position_error_m'],initial_reduced_vector_error_m_s=c['initial_reduced_vector_error_m_s'],
                initial_fullstate_output_error_m=c['initial_fullstate_output_error_m'],
                predicted_task_position_error_m=predicted_position_error,observed_task_position_error_m=observed_position_error,
                position_false_safe=predicted_position_error<=.01<observed_position_error,
                position_false_unsafe=observed_position_error<=.01<predicted_position_error))
        local.append(dict(revision=revision,counts=a['counts'],local_admission=a['local_admission'],cases=cases,
            cost_s=read(stage.RUN/f'revision{revision}_local_receipt.json')['charged']['wall_s'],
            position_false_safe=sum(c['position_false_safe'] for c in cases),position_false_unsafe=sum(c['position_false_unsafe'] for c in cases)))
    pairs=[];historical=historical_backend_costs();old=read(stage.previous_validation.folder(1)/'assessment.json')
    reset_costs=old['evaluation_costs']
    for names in (('original075','original15'),('reset075','reset15')):
        if not all((stage.RUN/f'forecast_{n}.json').exists() for n in names):continue
        forecasts=[read(stage.RUN/f'forecast_{n}.json') for n in names];outcomes=[];costs={};details=[]
        for n,h in zip(names,forecasts):
            r,s=stage.source(n);motion=measured_motion(r,s);holding=[m for m in motion if m['time_s']>=.3-1e-8]
            speed=max(m['speed_m_s'] for m in holding);position=max(m['error_m'] for m in holding)
            outcomes.append(dict(candidate_id=n,holding_max_speed_m_s=speed,holding_max_error_m=position,terminal_error_m=motion[-1]['error_m'],
                joint_acceptance=position<=.01 and motion[-1]['error_m']<=.01 and speed<=.02))
            if n.startswith('original'):costs[n]=historical['history'+n.removeprefix('original')]
            else:
                idx=0 if n=='reset075' else 1
                item=reset_costs['m5campaign-b1-r'+str(idx+1)]
                costs[n]=item['operational_s']
            observations=r.read_file(s,'controller_observations.json')
            input_errors=[float(np.max(abs(np.asarray(row['input_n'])-o['actual_tension_n']))) for row,o in zip(h['rows'],observations)]
            position_errors=[float(np.linalg.norm(np.asarray(row['position_m'])-o['position_m'])) for row,o in zip(h['rows'],motion)]
            vector_errors=[float(np.linalg.norm(np.asarray(row['velocity_m_s'])-o['velocity_m_s'])) for row,o in zip(h['rows'],motion)]
            details.append(dict(candidate=n,metrics=h['metrics'],solves=h['solves'],complete=h['complete'],
                setup_s=h['setup_s']+h['serial_setup_s'],controller_s=sum(r['controller_s'] for r in h['rows']),
                graph_reconstruction_s=sum(r['graph_construction_s'] for r in h['rows']),
                propagation_s=sum(r['propagation_output_s'] for r in h['rows']),
                all_replan_updates=[r['update_id'] for r in h['rows'] if r['replanned']],
                emulated_physics_steps=h['emulated_physics_steps'],history_identity=digest(h),
                first_command_divergence_s=next((row['time_s'] for row,e in zip(h['rows'],input_errors) if e>1e-9),None),
                first_position_accuracy_failure_s=next((row['endpoint_s'] for row,e in zip(h['rows'],position_errors) if e>1e-6),None),
                maximum_command_error_n=max(input_errors),maximum_position_error_m=max(position_errors),maximum_vector_error_m_s=max(vector_errors),
                raw_speed_false_safe=h['metrics']['holding_max_speed_m_s']<=.02<speed,
                raw_speed_false_unsafe=speed<=.02<h['metrics']['holding_max_speed_m_s'],
                raw_position_false_safe=h['metrics']['holding_max_error_m']<=.01<position,
                raw_position_false_unsafe=position<=.01<h['metrics']['holding_max_error_m']))
        decision=pair_decision(forecasts);forecast_cost=sum(read(stage.RUN/f'forecast_{n}_receipt.json')['charged']['wall_s'] for n in names)
        operational=forecast_cost+research;avoided=costs.get(decision['hypothetical_rejection'],0.)
        scored=assess_screening(decision,outcomes,operational,sum(costs.values()))
        observed_position_feasible=all(o['holding_max_error_m']<=.01 and o['terminal_error_m']<=.01 for o in outcomes)
        pairs.append(dict(candidates=list(names),forecasts=details,decision=decision,outcomes=outcomes,score=scored,
            observed_pair_position_feasible=observed_position_feasible,
            useful=decision['status']=='resolved' and scored['pairwise_order_verdict']=='correct' and observed_position_feasible,
            economics=dict(forecast_receipts_s=forecast_cost,required_research_s=research,all_in_screening_s=operational,
                per_evaluation_costs_s=costs,avoided_one_evaluation_s=avoided,counterfactual_net_savings_s=avoided-operational,
                actual_savings_s=0.,positive=avoided>operational,research_receipted=research>0.),
            full_order_physical_emulations=2,independent_backend_evaluations=0,classification='Retrospective development; outcomes consumed previously.'))
    matched=read(stage.RUN/'matched.json');timing=[]
    for r in matched['results']:
        d=r['selected_plan']['diagnostics'];tails=r['selected_plan']['warm_start']['tail_initialization']
        timing.append(dict(weight=r['weight'],cold_construction_s=r['cold_construction_s'],complete_cold_s=r['complete_cold_s'],
            update_s=r['update_s'],warm_preparation_s=r['warm_preparation_s'],optimizer_and_validation_s=r['optimizer_and_validation_s'],
            optimizer_construction_s=d['construction_s'],optimizer_solve_s=d['solve_s'],validation_s=d['validation_s'],
            tail_construction_s=sum(t['construction_s'] for t in tails),tail_integration_s=sum(t['integration_s'] for t in tails),
            policy_stop_reason=d['policy_stop_reason'],selected_iteration=d['selected_feasible_iteration'],
            update_deadline_s=.01,deadline_missed=r['complete_cold_s']>.01))
    checks=dict(numerical=local[-1]['counts']['numerical_pass']==6,quantitative=all(local[-1]['counts'][k]==6 for k in ('position_pass','speed_pass','vector_pass')),
        reliable_direction=local[-1]['counts']['direction_correct']==6,
        no_local_threshold_errors=not any(local[-1]['counts'][k] for k in ('speed_false_safe','speed_false_unsafe')) and not local[-1]['position_false_safe'] and not local[-1]['position_false_unsafe'],
        no_full_history_raw_threshold_errors=bool(pairs) and not any(f[k] for p in pairs for f in p['forecasts'] for k in ('raw_speed_false_safe','raw_speed_false_unsafe','raw_position_false_safe','raw_position_false_unsafe')),
        useful_retrospective_discrimination=any(p['useful'] for p in pairs),
        positive_operational_economics=any(p['economics']['positive'] and p['economics']['research_receipted'] for p in pairs),
        real_time=all(not t['deadline_missed'] for t in timing),prospective_evidence=False,repeatability=False)
    result=dict(version='m5_fullscope_assessment@1.0.0',matched=dict(command_gap_n=matched['max_command_separation_n'],supported=matched['matched_state_hypothesis_supported'],scope=matched['inference_scope']),
        local=local,pairs=pairs,performance=dict(matched_timings=timing,original_update_deadline_s=.01,
            measured_obstruction='Original accepted solves need seconds of warm regeneration and optimization. Removing all measured graph/model construction alone still exceeds .01 s. Original early acceptance and incumbent are preserved; no new production implementation is claimed.',
            bounded_improvement='One point model per candidate, reused transient controller graph, causal every-update holding replans. Local propagation and complete screening are separately charged.',
            new_real_backend_deadlines='Not measured: no new real backend admitted; prior incumbent 35/35 and failed batch 70/70 misses retained.'),
        checks=checks,scientific_development_admission=all(checks[k] for k in ('numerical','quantitative','reliable_direction','no_local_threshold_errors','useful_retrospective_discrimination','positive_operational_economics')),
        validation_launched=False,repeatability='Untested; conditional two untouched pairs and designated repeat not admitted. No substitute for a prospective series.',
        milestone5='open',incumbent=read(stage.RUN/'plan.json')['incumbent'],incumbent_retained=True,
        future_domain='Original ideal-tension hinge-only plant with current full serial state available; contacts, actuator dynamics and missing full observation unsupported.',
        allowance_exhausted=False,revision_allowance_consumed=2,
        limitation='Both revisions are development only. Full-state backend-step reproduction is distinct from convergence and physical-world validation. No family-wide claim, promotion or safety authority.')
    atomic_json(stage.RUN/'assessment.json',result);return result


def interpretation(send=True):
    from tools.platform_diagnosis_coordinator import configure_role,run_until_handoff
    from tools.platform_models import payload_for
    from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
    from tools.diagnostic_workflow import save
    from examples.gvs_nmpc_route_experiment import load_credential
    h=stage.session('research');path=stage.RUN/'interpretation.json'
    existing=h.store.session(h.run_id)['state'].get('handoffs',{}).get('m5_interpretation')
    if existing:atomic_json(path,h.store.artifact(existing));return
    prepared=stage.RUN/'research_payload.json'
    if not prepared.exists():
        a=assessment();assert len(a['pairs'])==2,'FOUR_PREDECLARED_FORECASTS_REQUIRED'
        binding=read(stage.prior.RUN/'freeze.json')['source_binding']
        with h.store.transaction() as db:
            state=h.store.session(h.run_id,db)['state']
            state.setdefault('fact_scope',dict(project='m5-fullscope-20261005',binding=binding));state.setdefault('fact_catalog',{})
            h.store.update_state(db,h.run_id,state)
        packet=dict(selected_weights=[.075,.15],direct_authorization='User attachment 640511c9 explicitly permits DeepSeek compact evidence and final native judgment.',
            plan={k:v for k,v in read(stage.RUN/'plan.json').items() if k!='predecessors'},assessment=a,
            revisions=[read(stage.RUN/f'revision{i}_plan.json') for i in (1,2)],
            remaining=h.store.remaining()['remaining'],historical_usage=read(stage.RUN/'plan.json')['predecessor_cumulative'])
        instruction=('Assess the actual separately authorized two-revision M5 development campaign. The previous campaign STOP stays immutable. '
            'Use the exact frozen criteria: local quantitative AND numerical support, resolved correct directions, useful position-feasible ranking, positive all-in economics before any new backend validation. No ranking-only bypass. '
            'Distinguish R1 continuous full-state accuracy versus R2 fixed-backend-step reproduction. R2 primary is the preregistered .0005 step; finer grids test original numerical criterion and cannot be suppressed because primary matches endpoints. '
            'Full-order serial emulation is honestly labeled, costs charged; it is not a cheap reduced model or independent backend validation. Complete forecasts use candidate own histories and every update during configured holding. '
            'Judge position feasibility independently of raw speed order. Abstention omits zero. All required research receipts will be charged to each operational pair conservatively; current costs before this call are lower bounds. '
            'Keep scientific failure separate from missing prospective/repeatability evidence and resource exhaustion. Real-time complete update deadline remains .01 s including graph/preparation/validation; use measured cost components, do not claim offline speed solves it. '
            'Return readiness beginning NO_GO or GO_EXPERIMENT_FULL, with precise evidence and remaining technical steps. No new computation requested. Milestone5 can close only if all original requirements pass; retain incumbent/M2-4. '
            'Return exactly one native research.milestone5_preparation tool call, phase interpretation, holding_weights [.075,.15], rationale, readiness, limitations, next_action finish_stop. About 650 words. Printed JSON is not an accepted handoff.')
        configure_role(h,'design',instruction,phase='interpretation',delivery_tool=stage.RESEARCH.extension_id,native_store_root=str(stage.RUN),memory_identity=h.run_id,
            native_fixed={},binding=binding,decision_packet=packet,decision_packet_reference=save(h.store,packet),
            phase_budget=dict(limit=dict(model_calls=8,tool_calls=20,wall_s=1200.),protect_project=dict(wall_s=65.)))
        atomic_json(prepared,payload_for(h,EvidenceDrivenAdapter()))
    if not send:print('Concrete native packet ready; no provider call.');return
    load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
    ref=run_until_handoff(h,'m5_interpretation');atomic_json(path,h.store.artifact(ref));stage.check_previous()


def correct_interpretation(number=1):
    """At most two factual corrections; original phase counters/replies preserved."""
    from tools.platform_store import plain
    from tools.platform_diagnosis_coordinator import run_until_handoff
    from tools.platform_models import payload_for
    from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
    from examples.gvs_nmpc_route_experiment import load_credential
    assert number in (1,2)
    h=stage.session('research');path=stage.RUN/('research_correction.json' if number==1 else 'research_correction2.json')
    state=h.store.session(h.run_id)['state'];current=state['handoffs']['m5_interpretation']
    if path.exists():
        if current!=read(path)['superseded_reference']:
            atomic_json(stage.RUN/'interpretation.json',h.store.artifact(current));return
    else:
        first=h.store.artifact(current);atomic_json(stage.RUN/f'interpretation_v{number}.json',first)
        budget=deepcopy(state['role_context']['phase_budget']);a=assessment()
        correction=dict(superseded_reference=current,phase_budget_before=budget,usage_before=h.store.remaining()['used'],
            correction_number=number,
            facts=['R1 LOCAL position error is 2.183626e-6 to 3.601895e-5 m, against LOCAL 1e-6 m tolerance. About .0495 m is R2 COMPLETE-HISTORY holding target error, against TASK .01 m limit. These cannot be interchanged.',
                'R2 holding_original075 first refinement vector .0001107665 and speed .0001062932 FAIL; second refinement vector .0000562890 and speed .0000540305 PASS. Its overall two-comparison criterion still fails. shared_first and early_original075 both comparisons fail. All scaled force residuals pass 1e-5; residual is distinct from 1e-4 m/s output resolution.',
                'Positive operational arithmetic and useful feasibility-qualified screening are separate. Reset pair resolves the raw speed order correctly and has positive counterfactual savings, but BOTH predicted holding positions are falsely feasible against observed outcomes, so useful position-feasible discrimination is absent. Original pair abstains. Neither pair provides prospective validation.',
                'The assessment now includes your first actual research receipt. A reporting-only economics flag now reports positive arithmetic separately from the unchanged usefulness gate. Final export adds this correction receipt too; no forecast/outcome/tolerance changed. Local diagnostic receipts are already complete; only screening decision overhead grows.',
                'R1 is continuous full-order physics; only R2 emulates the backend discrete step. Neither is physical-world validation.'])
        if number==2:
            correction['facts']=[
                'The corrected response still calls 496.079 s all-in. That is FORECAST-ONLY original-pair cost. Current all-in costs are in assessment.pairs[*].economics and grow by this pending call. Do not quote pending final all-in values; export will reconcile receipts.',
                'The corrected limitations still label BOTH revisions backend-step reproduction. Only R2 is discrete backend-step reproduction; R1 is continuous full-order serial dynamics. Your main rationale already makes this distinction correctly.',
                '1e-6 m is LOCAL POSITION ERROR, not a residual. Scaled force residual is dimensionless with 1e-5 threshold. Local diagnostic costs are completed fixed receipts; required screening decision overhead is what grows.',
                'The two NO_GO judgments are preserved. No numerical run, threshold, method, forecast or outcome changed. This is the second and final factual follow-up within the unchanged phase budget.']
        packet=deepcopy(state['role_context']['decision_packet']);packet.update(assessment=a,first_interpretation=first,factual_correction=correction)
        instruction=('Correct only these demonstrable factual errors while independently reassessing the unchanged frozen gates. '
            'Preserve the first response and do not change thresholds or turn arithmetic savings into useful position-feasible screening. '
            'Report exact R1/R2 local pass counts, correct refinement/residual distinctions, full-history threshold failures, one raw-resolved correct pair and one abstention, and positive reset arithmetic separately from unsupported screening usefulness. '
            'Include measured real-time obstruction and unperformed prospective/repeatability series. No new numerical work, revised method or backend launch. '
            'Final economics will include BOTH your receipts and native tools; do not invent this pending receipt. '
            'Return exactly one native research.milestone5_preparation call, phase interpretation, holding_weights [.075,.15], readiness starting NO_GO or GO_EXPERIMENT_FULL, rationale, limitations, next_action finish_stop. About 500 words.')
        if number==2:
            instruction=('Provide a fresh concise final judgment using the actual assessment and the four factual corrections, not copied limitations. '
                'Keep numerical stability, local position error, task feasibility, raw ranking and economics distinct. R1 is continuous full-order physics; R2 alone emulates discrete backend stepping. '
                'Only quote pair FORECAST receipt costs 496.079 and 337.641 s; explicitly defer final ALL-IN costs to export after this pending call. Prior decisions and receipts remain preserved. '
                'Judge NO_GO or GO_EXPERIMENT_FULL against the unchanged gates and name remaining failures. No additional numerical work, validation, promotion or milestone closure absent evidence. '
                'Return exactly one native research.milestone5_preparation call: phase interpretation, holding_weights [.075,.15], readiness, rationale, limitations, next_action finish_stop. Maximum 250 words; write new limitations instead of retaining erroneous prior wording.')
        with h.store.transaction() as db:
            state=h.store.session(h.run_id,db)['state'];role=state['role_context']
            role.update(instructions=instruction,decision_packet=packet,decision_packet_reference=plain(h.store.put(db,packet)),phase_started_turn=state.get('turn',0))
            assert role['phase_budget']==budget
            h.store.update_state(db,h.run_id,state)
            h.store.event(db,h.run_id,'semantic_correction','prepared',inputs=[current],outputs=[h.store.put(db,correction),h.store.put(db,role)])
        atomic_json(path,correction);atomic_json(stage.RUN/f'research_correction{number}_payload.json',payload_for(h,EvidenceDrivenAdapter()))
    load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
    ref=run_until_handoff(h,'m5_interpretation');atomic_json(stage.RUN/'interpretation.json',h.store.artifact(ref));stage.check_previous()


def export():
    a=assessment();store,receipts,work,events=records();used=store.remaining()['used'];sums=zero()
    for r in receipts:
        for k,v in r['charged'].items():sums[k]+=v
    assert all(abs(sums[k]-used[k])<1e-7 for k in sums),'OUTSTANDING_OR_UNRECONCILED_CALL'
    predecessor=read(stage.RUN/'plan.json')['predecessor_cumulative'];previous_work=read(stage.prior.RUN/'accounting.json')['cumulative_numerical_work']
    decision=read(stage.RUN/'interpretation.json');state=store.session('m5full-research')['state'];ref=state['handoffs']['m5_interpretation']
    assert store.artifact(ref)==decision
    assert not a['scientific_development_admission'],'POSITIVE_RESULT_REQUIRES_CONDITIONAL_VALIDATION'
    accounting=dict(predecessor=predecessor,new_campaign=used,cumulative={k:predecessor[k]+used[k] for k in used},
        receipt_sum=sums,aggregate_limit=stage.TOTAL,development_limit=stage.DEVELOPMENT,numerical_work=work,
        cumulative_numerical=dict(controller_attempts=previous_work['controller_attempts']+work['used']['local_solves'],
            standalone_integrations=previous_work['standalone_integrations']+work['used']['prediction_evaluations'],backend_controller_updates=280),
        full_order_complete_forecasts=work['used']['preview_attempts'],emulated_physics_steps=sum(p['forecasts'][i]['emulated_physics_steps'] for p in a['pairs'] for i in (0,1)),
        actual_backend_attempts=0,workers=0,subagents=0,
        charge_convention='All numerical, full-order emulation, construction, failed attempts and provider/native tool costs included once in outer receipts. Editing, focused checks and export follow existing offline engineering convention. No independent backend evaluation was substituted by emulation.')
    audit=dict(status='development_completed_not_admitted',milestone5='open',milestone2='closed',milestone3='closed',milestone4='closed',
        checks=a['checks'],failed_requirements=[k for k,v in a['checks'].items() if not v],research_reference=ref,research_accepted=True,
        research_readiness=decision['readiness'],incumbent_retained=True,prior_STOP_immutable=True,
        validation_grants_created=0,validation_backend_attempts=0,prospective_repeat_unperformed=True,
        work_complete=True,incomplete_authorized_work=[],next_action='finish_stop',
        reason='Two evidence-backed revisions and bounded accuracy/controller-response/cost/performance work completed. Failed development gates prohibit validation; budget was not exhausted.',
        authorization='Direct user authorization remains valid; the research NO_GO is a scientific admission failure, not missing permission.',
        engineering_repairs=['Offline assessment now handles the original R1 result without the later explicit primary-grid field.',
            'Offline native packet construction initializes the required fact scope before serialization.',
            'Artifact export distinguishes schema declarations from string-valued artifact references. No numerical or provider work was replayed.'],
        report='docs/milestone5_fullscope_campaign.md')
    for name,value in [('accounting',accounting),('acceptance_audit',audit),('receipts',receipts),('events',events)]:atomic_json(stage.RUN/(name+'.json'),value)
    stage.EVIDENCE.mkdir(parents=True,exist_ok=True)
    (stage.EVIDENCE/'.gitattributes').write_bytes(b'* -text\nartifacts/*.bin -diff\n')
    for p in stage.RUN.glob('*.json'):(stage.EVIDENCE/p.name).write_bytes(p.read_bytes())
    seen=set()
    def copy(value):
        if isinstance(value,dict):
            if set(value)=={'artifact_id','media_type'} and isinstance(value['artifact_id'],str) and isinstance(value['media_type'],str):
                key=value['artifact_id']
                if key in seen:return
                seen.add(key)
                try:body=store.artifact(value,raw=True)
                except (KeyError,ValueError):return
                path=stage.EVIDENCE/'artifacts'/(key+('.json' if value['media_type']=='application/json' else '.bin'))
                path.parent.mkdir(exist_ok=True);path.write_bytes(body)
                if value['media_type']=='application/json':copy(json.loads(body))
            else:
                for child in value.values():copy(child)
        elif isinstance(value,list):
            for child in value:copy(child)
    copy(events);copy(receipts);copy(ref)
    for name in ('examples/milestone5_fullscope.py','examples/milestone5_fullscope_delivery.py','extensions/tendon_family/milestone5_fullstate.py','tests/test_milestone5_fullscope.py'):
        p=ROOT/name
        if p.exists():
            dest=stage.EVIDENCE/'implementation'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
    atomic_json(stage.EVIDENCE/'sha256_manifest.json',{p.relative_to(stage.EVIDENCE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(stage.EVIDENCE.rglob('*')) if p.is_file() and p.name!='sha256_manifest.json'})
    stage.check_previous();print(json.dumps(dict(usage=used,checks=a['checks'],judgment=decision['readiness'])))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--phase',required=True);args=parser.parse_args()
    if args.phase=='assessment':print(json.dumps(assessment()['checks']))
    elif args.phase=='prepare-research':interpretation(False)
    elif args.phase=='interpret':interpretation()
    elif args.phase=='correct-interpretation':correct_interpretation()
    elif args.phase=='clarify-final-report':correct_interpretation(2)
    elif args.phase=='export':export()
    else:raise ValueError('Unsupported phase')
