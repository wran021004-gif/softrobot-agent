"""Assessment, accepted native research handoff and linked campaign export."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from examples import milestone5_predictor_campaign as stage
from examples import milestone5_predictor_development as previous
from examples import milestone5_first_interval as first
from examples import milestone5_preparation as preparation
from tools.platform_store import Store
from tools.state_io import read,atomic_json,digest
from tools.diagnostic_workflow import save
from extensions.tendon_family.milestone5_preparation import RESEARCH
from extensions.tendon_family.milestone5_campaign_predictor import VERSION
from extensions.tendon_family.milestone5_protocol import pair_decision,assess_screening


def assessment():
    stage.check_previous();accuracy=read(stage.RUN/'accuracy.json')
    forecasts=[read(stage.RUN/(name+'.json')) for name in ('history075','history15')]
    decision=pair_decision(forecasts)
    old=read(previous.RUN/'assessment.json');outcomes=[c['outcome'] for c in old['cases']]
    costs=previous.historical_backend_costs()
    forecast_cost=sum(read(stage.RUN/(name+'_receipt.json'))['charged']['wall_s'] for name in ('history075','history15'))
    store=Store(stage.RUN)
    with store.connect(True) as db:
        receipts=[json.loads(r[0]) for r in db.execute("SELECT receipt FROM calls WHERE run_id='m5campaign-research' AND receipt IS NOT NULL")]
    research_cost=sum(r['charged']['wall_s'] for r in receipts)
    operational_cost=forecast_cost+research_cost
    skipped=decision['hypothetical_rejection'];avoided=0. if skipped is None else costs[skipped]
    scored=assess_screening(decision,outcomes,operational_cost,sum(costs.values()))
    align=read(stage.ROOT/'runs/milestone5_recovery_20261005/align.json')['result']['cases']
    detailed=[]
    for f,a in zip(forecasts,align):
        vectors=[float(np.linalg.norm(np.asarray(r['velocity_m_s'])-o['observed_endpoint']['velocity_m_s'])) for r,o in zip(f['rows'],a['rows'])]
        positions=[float(np.linalg.norm(np.asarray(r['position_m'])-o['observed_endpoint']['position_m'])) for r,o in zip(f['rows'],a['rows'])]
        inputs=[float(np.linalg.norm(np.asarray(r['input_n'])-o['actual_input_n'])) for r,o in zip(f['rows'],a['rows'])]
        detailed.append(dict(candidate_id=f['candidate_id'],complete=f['complete'],metrics=f['metrics'],solves=f['solves'],
            max_history_vector_error_m_s=max(vectors),max_history_position_error_m=max(positions),
            max_input_error_norm_n=max(inputs),controller_s=sum(r['controller_s'] for r in f['rows']),
            setup_s=f['setup_s']+f['serial_setup_s'],graph_reconstruction_s=sum(r['graph_construction_s'] for r in f['rows']),
            propagation_output_s=sum(r['propagation_output_s'] for r in f['rows']),
            maximum_residual=max(r['max_scaled_residual'] for r in f['rows']),
            history_identity=digest(f),controller_response_note='Scoring accesses saved outcomes only after this independent complete forecast is recorded.'))
    rows=[c['score'] for c in accuracy['cases']]
    from extensions.tendon_family.milestone5_campaign_local import report
    local_reports=[dict(case=c['case'],**report(c['prediction']['initial'],c['results'],c['prediction']['input_n'],c['interval_s'][0])) for c in accuracy['cases']]
    counts=dict(distinct_intervals=len(rows),numerical_passes=accuracy['numerical_supported_count'],
        position_passes=sum(r['position_pass'] for r in rows),speed_passes=sum(r['speed_pass'] for r in rows),
        vector_passes=sum(r['vector_pass'] for r in rows),direction_resolved=sum(r['direction_resolved'] for r in rows),
        direction_correct=sum(r['direction_correct'] for r in rows),holding_false_safe=sum(r['holding_false_safe'] for r in rows))
    result=dict(version=VERSION,local_counts=counts,local_reports=local_reports,local_cases=[{k:v for k,v in c.items() if k!='results'} for c in accuracy['cases']],
        reference_assessments={k:({z:w for z,w in v.items() if z!='outputs'} if isinstance(v,dict) else v)
            for k,v in accuracy['reference_assessments'].items()},
        screening=dict(decision=decision,score=scored,forecasts=detailed,outcomes=outcomes,
            complete_history_numerical_reference=False,
            coverage_note='Complete forecasts cover all 35 intervals; local resolution tests do not establish complete-history numerical accuracy.'),
        economics=dict(previous_pair_forecast_s=old['economics']['per_pair_forecast_cost_s'],
            new_pair_forecast_receipt_s=forecast_cost,required_research_decision_s=research_cost,
            research_overhead_complete=bool(receipts),incremental_screening_cost_s=operational_cost,
            complete_evaluation_costs_s=costs,one_skipped_upper_bound_s=max(costs.values()),
            selected_skipped_evaluation_s=avoided,counterfactual_net_savings_s=avoided-operational_cost,
            positive_net_saving=bool(receipts) and avoided>operational_cost,
            net_saving_is_upper_bound=not bool(receipts),
            forecast_fraction_reduction=1-forecast_cost/old['economics']['per_pair_forecast_cost_s'],
            actual_validation_savings_s=0.,actual_operational_evaluations_avoided=0,
            convention='Fresh pair receipts include model/graph setup, all embedded controller solves, propagation, output and serialization. Actual native research workflow receipts are added once as conservative per-decision overhead. Reference, localization and isolated probes are development-only.'),
        physical_correction='Consistent represented serial mass/force pullback; discarded modes remain excluded.',
        cost_strategy='Five-interval predictor replanning, seven solves each; not exact production control.',
        production_changes=0,prospective_outcomes_observed=False,backend_attempts=0,backend_steps=0,
        limitations=['Four intervals and one historical pair cannot establish statistical reliability or family-wide transfer',
            'Observed state projection discards modes; fine numerical integration does not restore them',
            'Complete evaluation is required unless a separately validated screening role exists',
            'Incumbent retained; Milestone 5 remains open; real-time 35/35 misses unchanged'])
    atomic_json(stage.RUN/'assessment.json',result)
    return result


def interpretation(*,send=True):
    from tools.platform_diagnosis_coordinator import configure_role,run_until_handoff
    from tools.platform_models import payload_for
    from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
    from examples.gvs_nmpc_route_experiment import load_credential
    stage.prepare();h=stage.create_session('research');path=stage.RUN/'interpretation_response.json'
    prior=h.store.session(h.run_id)['state'].get('handoffs',{}).get('m5_interpretation')
    if prior:atomic_json(path,h.store.artifact(prior));return
    if send:load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
    prepared=stage.RUN/'interpretation_serialized_handoff.json'
    if send and prepared.exists():
        # Resume the concrete packet reviewed for authorization; do not silently
        # rebuild it from later reporting-only additions or reset phase usage.
        proof=stage.RUN/'authorization_review_evidence.json'
        if proof.exists():
            assert hashlib.sha256(prepared.read_bytes()).hexdigest()==read(proof)['payload_sha256'],'REVIEWED_PAYLOAD_CHANGED'
        decision=run_until_handoff(h,'m5_interpretation')
        atomic_json(path,h.store.artifact(decision));stage.check_previous();return
    a=assessment();f=read(stage.RUN/'freeze.json');local=read(stage.RUN/'localization-r1.json');probe=read(stage.RUN/'cost_probe.json')
    packet=dict(authorization=stage.AUTHORIZATION,selected_weights=f['accepted_selection']['holding_weights'],
        acceptance=f['criteria'],incumbent=f['incumbent'],method=read(stage.RUN/'method_freeze.json'),
        reference={k:v for k,v in read(stage.RUN/'reference.json').items() if k!='results'},
        localization=[dict(case=c['case'],projection_rate_fd=c['projection_rate_fd_norm'],projection_roundtrip=c['projection_roundtrip_norm'],
            discarded_rate_norm=c['discarded_rate_norm_rad_s'],instantaneous_position_error=c['instantaneous_serial_position_error_m'],
            mechanics_relative_differences={k:v['relative_frobenius_difference'] for k,v in c['terms'].items()}) for c in local['cases']],
        saved_cost_profile=[{k:v for k,v in c.items() if k!='receipt'} for c in local['cost_profile']],
        controller_approximation_probe=dict(cost_s=probe['complete_cost_s'],comparison=probe['saved_production_comparison'],scope=probe['scope']),
        assessment=a,conditional_validation=f['conditional_validation'],remaining=h.store.remaining()['remaining'],
        predecessor_usage=read(previous.RUN/'accounting.json')['cumulative'])
    with h.store.transaction() as db:
        state=h.store.session(h.run_id,db)['state'];state.setdefault('fact_scope',dict(project='m5-predictor-campaign-20261005',binding=f['source_binding']));state.setdefault('fact_catalog',{})
        h.store.update_state(db,h.run_id,state)
    instruction=('Assess this completed bounded development campaign, with accuracy and economics SEPARATE. Reuse the accepted .075/.15 selection; do not restart handoffs. '
        'The original shared reference was completed once with repaired 800s guard and eight reused grids; its continuous and serial maps have separate two-successive comparisons. '
        'New mechanics use 24-dimensional reduced serial virtual-work pullback, no backend steps; physical parameters and production NMPC unchanged. New local implicit-Radau resolution checks are for the changed model, not interchangeable with old continuum references. '
        'Identify implementation versus representation/dynamics/numerical limits. Report four unique local intervals, directional coverage/correctness, ALL original vector/speed/position passes and threshold failures. Do not call numerical self-consistency physical accuracy. '
        'A measured seven-replan controller-response approximation targets the dominant cost; its first command matches production but subsequent frozen plan commands can diverge. Two new independent complete own-history forecasts were generated; compare their resolved ranking and errors to saved outcomes. '
        'Judge screening economics against ONE evaluation actually avoided; abstention avoids zero. Forecast receipts are the lower bound before this actual model-call overhead, which export will add. No savings can be inferred from lower forecast runtime alone. '
        'Readiness for experiment is not reliability. Require the frozen admission conditions and justify any narrowed ranking-only role before validation, with safety/eligibility authority withheld; it cannot erase failed original accuracy. '
        'Return readiness beginning NO_GO or GO_EXPERIMENT_RANKING_ONLY or GO_EXPERIMENT_FULL, followed by concrete reasons. For GO identify a specific independent reset-clock hypothesis and support all gates. For NO_GO name the precise remaining accuracy/cost obstruction and one bounded falsifiable next action, without doing it. '
        'State supported diagnostic uses, screening useful/experimental/deferred, when complete evaluation is required, whether another experiment is justified, and which original M5 criteria remain unmet. No candidate promotion, M5 closure, real-time claim, family-wide reliability or statistical inference. '
        'Return exactly one native research.milestone5_preparation tool call: phase interpretation, holding_weights [.075,.15], rationale, readiness, limitations, next_action finish_stop. About 650 words. Printed JSON is not a handoff.')
    configure_role(h,'design',instruction,phase='interpretation',delivery_tool=RESEARCH.extension_id,native_store_root=str(stage.RUN),memory_identity=h.run_id,
        native_fixed={},binding=f['source_binding'],decision_packet=packet,decision_packet_reference=save(h.store,packet),
        phase_budget=dict(limit=dict(model_calls=6,tool_calls=12,wall_s=1200.),protect_project=dict(wall_s=65.)))
    atomic_json(stage.RUN/'interpretation_serialized_handoff.json',payload_for(h,EvidenceDrivenAdapter()))
    if not send:
        print('Native research payload prepared offline; no credential read or provider call.')
        return
    decision=run_until_handoff(h,'m5_interpretation');atomic_json(path,h.store.artifact(decision));stage.check_previous()


def export():
    a=assessment();f=read(stage.RUN/'freeze.json');store=Store(stage.RUN)
    decision=read(stage.RUN/'interpretation_response.json') if (stage.RUN/'interpretation_response.json').exists() else None
    state=store.session('m5campaign-research')['state']
    old=Store(first.RUN);selection=old.session(first.host('research').run_id)['state']['handoffs']['m5_selection']
    refs=dict(selection=selection)
    if decision is not None:
        refs['interpretation']=state['handoffs']['m5_interpretation']
        assert store.artifact(refs['interpretation'])==decision,'RESEARCH_BINDING'
    p=preparation.protocol(read(preparation.RUN/'registration.json'),f['accepted_selection'],read(preparation.RUN/'reference.json'))
    p=preparation.finalize_protocol(p,research_store=store,decision_refs=refs,decision_stores=dict(selection=old),
        supersedes=dict(protocol='evidence/milestone5_predictor_development_20261005/protocol.json',seal=read(previous.RUN/'protocol_seal.json')))
    checks=dict(causal_implementation=True,supported_original_reference=all(a['reference_assessments'][k]['passed'] for k in ('continuous','represented_serial')),
        changed_model_local_numerical_support=a['local_counts']['numerical_passes']==4,
        evidence_backed_physical_correction=True,measured_dominant_cost_strategy=True,
        original_quantitative_accuracy=all(a['local_counts'][k]==4 for k in ('position_passes','vector_passes','speed_passes')),
        useful_historical_discrimination=a['screening']['score']['pairwise_order_verdict']=='correct',
        known_false_safe_resolved=a['local_counts']['holding_false_safe']==0 and not a['screening']['score']['predicted_safe_observed_violating'],
        positive_operational_net_saving=a['economics']['positive_net_saving'],
        accepted_research_interpretation=p['research_interpretation_complete'],
        research_admits_experiment=decision is not None and decision['readiness'].startswith('GO_EXPERIMENT'))
    # A proposed narrowed role must be reviewed as a concrete separate protocol;
    # it must never cause a missing accepted judgment to default to admission.
    if checks['research_admits_experiment']:
        atomic_json(stage.RUN/'development_entry_checks.json',checks)
        raise ValueError('ACCEPTED_GO_REQUIRES_CONCRETE_FROZEN_VALIDATION_IMPLEMENTATION')
    from tools.batch_budget import batch_requirement
    base=batch_requirement(2,planning=dict(model_calls=0,tool_calls=0,wall_s=0.),preparation_reserve_s=5.)
    required=deepcopy(base['requirement']);required['tool_calls']+=4;required['wall_s']+=2400.+180.+60.
    status='not_ready_no_validation_launched' if decision is not None else 'development_completed_research_blocked'
    next_action='finish_stop' if decision is not None else 'await_direct_chat_authorization_then_resume_saved_research_packet'
    p.update(version=VERSION,status=status,preview_version=VERSION,local_version=VERSION,
        predictor_method=read(stage.RUN/'method_freeze.json'),development_entry_checks=checks,
        accepted_research_judgment=decision,ready_for_bounded_prospective_experiment=False,
        conditional_authorization=stage.AUTHORIZATION,continuation=f['conditional_validation']['continuation'],
        local_reference_stable=checks['changed_model_local_numerical_support'],reference_scope=a['reference_assessments'],
        numerical_results_provenance='reference.json and accuracy.json in this campaign, exact receipts; local reference only',
        prospective_outcomes_observed=False,prospective_forecasts_generated=False,operational_next_action=next_action)
    p['authorization_in_current_stage']='Two conditional batches authorized by current user; prerequisites failed so no grants materialized'
    p['model']='Predictor represented_serial_mechanics@1.0.0; production controller retains model.gvs@1.0.0'
    p['local_step_s']=.000125
    p['reservations']=dict(development=dict(ceiling=stage.LIMITS,numerical=stage.NUMERICAL),
        **{'batch'+str(i):dict(public_base=base,complete_requirement=required,ceiling=stage.VALIDATION_LIMITS,
            preview_reserve_s=2400.,local_overhead_s=180.,export_s=60.,fits=all(required[k]<=stage.VALIDATION_LIMITS[k] for k in required),
            controller_attempts=dict(preview_ceiling=70,expected_this_method=14,production_expected=70,combined_ceiling=140),
            admitted=False,grant_materialized=False) for i in (1,2)})
    p['commands']=dict(export='python examples/milestone5_campaign_delivery.py --phase export',
        execution='No validation launch: development prerequisites fail. Historical numerical work must not be rerun.')
    files=['examples/milestone5_predictor_campaign.py','examples/milestone5_campaign_delivery.py',
        'extensions/tendon_family/milestone5_campaign_reference.py','extensions/tendon_family/milestone5_campaign_localization.py',
        'extensions/tendon_family/milestone5_campaign_predictor.py','extensions/tendon_family/milestone5_campaign_assessment.py',
        'extensions/tendon_family/milestone5_campaign_local.py']
    p['implementation_identity']['files'].update({n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in files})
    atomic_json(stage.RUN/'protocol.json',p);seal=save(store,p)
    atomic_json(stage.RUN/'protocol_seal.json',dict(protocol_reference=seal,identity=digest(p),backend_grant_materialized=False,prospective_forecasts_sealed=False))
    atomic_json(stage.RUN/'readiness.json',dict(passed=False,checks=checks,failed=[k for k,v in checks.items() if not v],
        backend_attempts=0,backend_steps=0,validation_grants=0,milestone5='open',incumbent_retained=True,
        research_status='accepted_no_go' if decision else 'missing_no_default_acceptance',realtime='Unmet; production unchanged'))
    with store.transaction() as db:
        running=db.execute("SELECT COUNT(*) FROM calls WHERE status='running'").fetchone()[0]
        assert running==0,'UNRESOLVED_CALLS_CANNOT_FINISH'
        ids=[r[0] for r in db.execute('SELECT run_id FROM sessions')]
        for run_id in ids:
            if decision is None and run_id=='m5campaign-research':continue
            session=store.session(run_id,db);session['state']['development_calculations_finished']=True
            session['state']['campaign_finished']=decision is not None
            store.update_state(db,run_id,session['state'],'stopped')
        store.event(db,'m5campaign-research','campaign','finish_stop' if decision is not None else 'export_pending_research',outputs=[seal])
    with store.connect(True) as db:
        receipts=[json.loads(r[0]) for r in db.execute('SELECT receipt FROM calls WHERE receipt IS NOT NULL')]
        work=json.loads(db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone()[0])
    used=store.remaining()['used'];prior=read(previous.RUN/'accounting.json')['cumulative']
    sums={k:sum(r['charged'][k] for r in receipts) for k in used}
    assert all(abs(sums[k]-used[k])<1e-7 for k in used),'RECEIPT_ACCOUNTING_MISMATCH'
    corrections=dict(protocol_total=state.get('protocol_corrections_used',0),protocol_consecutive=state.get('protocol_corrections_consecutive',0),
        semantic_total=read(stage.RUN/'interventions.json').get('semantic_provider_corrections',0))
    assert corrections['protocol_total']+corrections['semantic_total']<=4
    accounting=dict(historical=prior,development=used,validation={k:0 for k in used},
        cumulative={k:prior[k]+used[k] for k in prior},receipt_charge_sum=sums,development_limits=stage.LIMITS,
        validation_per_batch_limits=stage.VALIDATION_LIMITS,numerical_work=work,
        cumulative_numerical_work=dict(controller_attempts=79+work['used']['local_solves'],
            standalone_integrations=44+work['used']['reference_integrations']+work['used']['prediction_evaluations'],
            historical_backend_controller_updates=210,new_backend_controller_updates=0),corrections=corrections,
        numerical_details=dict(reference_attempts=1,reference_completions=1,local_integrations=work['used']['prediction_evaluations'],
            complete_previews=work['used']['preview_attempts'],embedded_preview_controller_attempts=sum(x['solves'] for x in a['screening']['forecasts']),
            isolated_controller_probe_attempts=1),
        nested_time='Embedded solver, propagation, point mechanics, serialization and all failures charged once in outer workflow receipts.',
        engineering='Editing, read-only inspection, focused verification and export use preserved offline engineering convention.',workers=0,subagents=0)
    atomic_json(stage.RUN/'accounting.json',accounting);atomic_json(stage.RUN/'receipts.json',receipts)
    events=[e for run_id in ids for e in store.events(run_id)];atomic_json(stage.RUN/'events.json',events)
    delivery=dict(status=p['status'],research_interpretation_accepted=decision is not None,incumbent=f['incumbent'],
        milestone2='closed',milestone3='closed',milestone4='closed',milestone5='open',backend_attempts=0,backend_steps=0,
        prospective_outcomes=None,conditional_validation='Not admitted; both linked grants remain unmaterialized',
        report='docs/milestone5_predictor_campaign.md',accounting='accounting.json',readiness='readiness.json',
        remaining_failures=[k for k,v in checks.items() if not v],operational_next_action=next_action,
        incomplete_work=[] if decision is not None else ['accepted development go/no-go','conditional prospective validation if admitted','final accepted capability judgment'])
    atomic_json(stage.RUN/'delivery.json',delivery);stage.EVIDENCE.mkdir(parents=True,exist_ok=True)
    for fpath in stage.RUN.glob('*.json'):(stage.EVIDENCE/fpath.name).write_bytes(fpath.read_bytes())
    seen=set()
    def copy(value):
        if isinstance(value,dict):
            if set(value)=={'artifact_id','media_type'} and isinstance(value['artifact_id'],str) and isinstance(value['media_type'],str):
                key=value['artifact_id']
                if key in seen:return
                seen.add(key)
                try:body=store.artifact(value,raw=True)
                except (KeyError,ValueError):return
                dest=stage.EVIDENCE/'artifacts'/(key+('.json' if value['media_type']=='application/json' else '.bin'))
                dest.parent.mkdir(exist_ok=True);dest.write_bytes(body)
                if value['media_type']=='application/json':copy(json.loads(body))
            else:
                for child in value.values():copy(child)
        elif isinstance(value,list):
            for child in value:copy(child)
    copy(events);copy(receipts)
    for name in files+['tests/test_milestone5_campaign.py']:
        if not (ROOT/name).exists():continue
        dest=stage.EVIDENCE/'implementation'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/name).read_bytes())
    atomic_json(stage.EVIDENCE/'sha256_manifest.json',{p.relative_to(stage.EVIDENCE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(stage.EVIDENCE.rglob('*')) if p.is_file() and p.name!='sha256_manifest.json'})
    stage.check_previous();print(json.dumps(dict(status=delivery['status'],usage=used,numerical=work)))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--phase',required=True);args=p.parse_args()
    if args.phase=='assessment':print(json.dumps(assessment()['local_counts']))
    elif args.phase=='interpret':interpretation()
    elif args.phase=='prepare-research':interpretation(send=False)
    elif args.phase=='export':export()
    else:raise ValueError('Unknown phase')
