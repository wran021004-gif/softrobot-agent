"""Recover the saved native interpretation; never rerun forecasts or backends."""
from copy import deepcopy
from pathlib import Path
import json
import os
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from examples import milestone5_campaign_validation as validation
from tools.platform_host import Host
from tools.platform_store import plain
from tools.state_io import read,atomic_json,digest

BATCH=1
RUN=validation.folder(BATCH)
REVISED='m5campaign-b1-r1-interpretation-repair'


def recover():
    old=Host(RUN,'m5campaign-b1-r1');store=old.store;before=store.remaining()['used']
    with store.connect(True) as db:
        assert not db.execute("SELECT 1 FROM calls WHERE status IN ('running','unknown')").fetchone(),'UNRESOLVED_WRITER'
        exists=db.execute('SELECT 1 FROM sessions WHERE run_id=?',(REVISED,)).fetchone()
    h=Host(RUN,REVISED)
    if not exists:
        source=store.session(old.run_id);inp=deepcopy(source['snapshot']['input']);inp['run_id']=REVISED
        inp['policy']['operation_allowances'].update({validation.RESEARCH.extension_id:dict(timeout_s=10.,reserve_s=5.),
            'evidence.read':dict(timeout_s=10.,reserve_s=5.)})
        # Same project grant and provider settings; a sequential session revision,
        # not a worker or a new allocation. Preserve all consumed phase usage.
        h.create(inp)
        with store.transaction() as db:
            state=deepcopy(source['state']);phase=state['role_context']['phase_budget'];old_used=store.remaining(old.run_id,db)['used']
            state.pop('result_executions',None);state.pop('execution_completion',None)
            phase['started_usage']={k:phase['started_usage'][k]-old_used[k] for k in old_used}
            state['role_context']['memory_identity']=REVISED
            state['role_context']['decision_packet']['selected_weights']=[r['holding_weight'] for r in read(RUN/'protocol.json')['recipes']]
            store.update_state(db,REVISED,state,'stopped')
            store.update_state(db,old.run_id,source['state'],'stopped')
            record=dict(source_run=old.run_id,revised_run=REVISED,usage_before=before,
                reason='Research handoff inherited simulation timeout/reservation 900s, exceeding the protected 600s research phase. Supply the existing 10s/5s research allowance; also bind the required selected_weights packet field to the frozen recipes.',
                frozen_scientific_protocol_unchanged=True,phase_usage_preserved=store.phase_remaining(REVISED,db),
                provider_settings_unchanged=True,new_grant=False,numerical_replays=0)
            store.event(db,REVISED,'interpretation_recovery','same_grant_preserved_phase',outputs=[store.put(db,record)])
        atomic_json(RUN/'interpretation_recovery.json',record)
        assert store.remaining()['used']==before
    # Scientific executions retain their original owner. A research-only revision
    # must not duplicate the parent's backend lookup cache.
    with store.transaction() as db:
        state=store.session(REVISED,db)['state']
        if 'result_executions' in state or 'execution_completion' in state:
            state.pop('result_executions',None);state.pop('execution_completion',None)
            store.update_state(db,REVISED,state)
            store.event(db,REVISED,'interpretation_recovery','original_execution_ownership_preserved')
    current=store.session(REVISED)['state'].get('handoffs',{}).get('m5_interpretation')
    if current:return h
    source_receipt=json.loads(store.lookup(old.run_id,'model-0')['receipt'])
    invocation=deepcopy(store.artifact(source_receipt['output']))
    original_arguments=deepcopy(invocation['arguments'])
    invocation.update(request_id='recover-saved-model-0-tool',cache='new',
        reason='Dispatch exact saved native model arguments after correcting interpretation-only reservation and packet binding; no provider resend or numerical replay.')
    h.resume();model_host=Host(RUN,REVISED,actor='model')
    receipt=model_host.invoke(invocation)
    atomic_json(RUN/'interpretation_recovery_receipt.json',receipt)
    assert receipt['execution_status']=='completed',receipt.get('error')
    ref=store.session(REVISED)['state']['handoffs']['m5_interpretation']
    assert store.artifact(ref)==original_arguments,'EXACT_MODEL_ARGUMENTS_REQUIRED'
    atomic_json(RUN/'interpretation_v1.json',store.artifact(ref))
    with store.transaction() as db:
        state=store.session(REVISED,db)['state'];state['repairs']=0;state.pop('business_feedback',None)
        store.update_state(db,REVISED,state,'stopped')
        store.event(db,REVISED,'native_response_recovered','accepted_without_provider_replay',inputs=[source_receipt['output']],outputs=[ref])
    return h


def assessment():
    a=validation.assess(BATCH);store=Host(RUN,REVISED).store
    ref=store.session(REVISED)['state'].get('handoffs',{}).get('m5_interpretation')
    a.update(research_reference=ref,research_judgment=store.artifact(ref) if ref else None)
    a['economics']['final_research_receipted']=ref is not None
    a['continuation_conditions']['accepted_research_continuation']=ref is not None and a['research_judgment']['readiness'].startswith('CONTINUE_BATCH2')
    a['continue_batch2']=all(a['continuation_conditions'].values())
    atomic_json(RUN/'assessment.json',a);return a


def correct():
    h=recover();store=h.store;path=RUN/'factual_correction.json'
    current=store.session(REVISED)['state']['handoffs']['m5_interpretation']
    if path.exists():
        correction=read(path)
        if current!=correction['superseded_reference']:return finish()
    else:
        a=assessment();state=store.session(REVISED)['state'];phase=deepcopy(state['role_context']['phase_budget'])
        assert state.get('protocol_corrections_used',0)+1<=3
        packet=dict(assessment=a,selected_weights=[.075,.15],prior_interpretation=store.artifact(current),
            frozen_continuation=read(RUN/'protocol.json')['continuation_checks'],
            factual_notes=[
                'Local errors are indexed by TIME, not candidate: BOTH candidates have position/vector/speed errors .000153927/.008491293/-.004733323 at .20-.21, and .000184246/.009501082/-.006631540 at .30-.31. Four candidate checkpoints but only two distinct state/input/time cases: not four independent successes or failures.',
                'Both forecast complete histories are numerically identical. Predicted holding/terminal position .039132747 exceeds .01, so the frozen position gate abstains; raw predicted speed difference is zero as well. Actual sampled speed order is .15 then .075, gap .241738958, but BOTH violate the frozen position-feasibility condition, so do not claim an eligible winner.',
                'No candidate is rejected by this sealed decision. The avoided cost is exactly zero. Use all actual forecast and required research receipts so far, plus this correction when receipted. Instrumented evaluation costs may not be used as an inflated saving comparator.',
                'The first native tool submission was rejected before execution due to an engineering reservation/packet defect. Exact model-authored fields were recovered through the actual native tool in the same grant, without a second provider call. This semantic correction is separate and charged.',
                'A zero-held-step comparison cannot falsify a nonzero-interval speed-direction error. Replace that recommendation with one bounded, coherent investigation and explicit pass/fail criterion based on saved evidence; specify untouched fresh evidence needed after any new method version. Do not execute it.',
                'The original documented milestone requires accurate local prediction, useful prospective full-task discrimination, broader repeatability and real-time feasibility. Do not turn a finished ranking-only experiment into a passed ranking capability or M5 closure.'],
            saved_controller_comparison=read(RUN/'saved_controller_comparison.json'))
        instruction=('Make ONE factual correction of the preserved Batch1 interpretation; do not seek a favorable verdict. '
            'Correct time/candidate indexing, account for the identical candidate checkpoint cases and conditional ranking scope, '
            'and replace the physically undefined zero-held-step recommendation. Use actual costs so far without guessing the future cost of this call. '
            'Reassess the unchanged continuation gates. Report numerical support separately from direction, quantitative accuracy, threshold reliability, ranking and economics. '
            'State experimental/unsupported uses, complete evaluation requirements, remaining original M5 failures and ONE concrete next objective with a falsifiable criterion and fresh prospective evidence requirement. '
            'No new computation, method tuning, candidate promotion, broad reliability or milestone closure. Return exactly one native research.milestone5_preparation call, '
            'phase interpretation, holding_weights [.075,.15], rationale, readiness beginning STOP or CONTINUE_BATCH2, limitations, next_action finish_stop. About650 words.')
        correction=dict(superseded_reference=current,semantic_corrections=1,protocol_corrections=state.get('protocol_corrections_used',0),
            original_phase_budget=phase,usage_before=store.remaining()['used'],notes=packet['factual_notes'])
        with store.transaction() as db:
            state=store.session(REVISED,db)['state'];state['role_context'].update(instructions=instruction,decision_packet=packet,
                decision_packet_reference=plain(store.put(db,packet)),phase_started_turn=state.get('turn',0))
            assert state['role_context']['phase_budget']==phase
            store.update_state(db,REVISED,state)
            store.event(db,REVISED,'semantic_correction','prepared',inputs=[current],outputs=[store.put(db,packet)])
        from tools.platform_models import payload_for
        from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
        atomic_json(RUN/'factual_correction_handoff.json',payload_for(h,EvidenceDrivenAdapter()))
        atomic_json(path,correction)
    from examples.gvs_nmpc_route_experiment import load_credential
    from tools.platform_diagnosis_coordinator import run_until_handoff
    load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
    ref=run_until_handoff(h,'m5_interpretation');atomic_json(RUN/'interpretation.json',store.artifact(ref))
    finish()


def finish():
    a=assessment();assert a['research_reference'] is not None
    assert not a['continue_batch2'],'THIS_CLOSEOUT_CANNOT_LAUNCH_ANOTHER_BATCH'
    store=Host(RUN,REVISED).store
    with store.transaction() as db:
        assert not db.execute("SELECT 1 FROM calls WHERE status IN ('running','unknown')").fetchone()
        for row in db.execute('SELECT run_id FROM sessions').fetchall():
            state=store.session(row[0],db)['state'];state['batch_finished']=True;store.update_state(db,row[0],state,'stopped')
    atomic_json(RUN/'interpretation.json',a['research_judgment'])
    atomic_json(RUN/'delivery.json',dict(status='completed_stopped',continue_batch2=False,milestone5='open',
        research_reference=a['research_reference'],research_session=REVISED,stop_conditions=[k for k,v in a['continuation_conditions'].items() if not v]))
    validation.export(BATCH)
    print(json.dumps(dict(status='completed_stopped',economics=a['economics'],usage=store.remaining()['used'])))


def correct_cost():
    """Final bounded correction of demonstrably stale cost figures only."""
    h=Host(RUN,REVISED);store=h.store;path=RUN/'cost_correction.json'
    current=store.session(REVISED)['state']['handoffs']['m5_interpretation']
    if path.exists():
        if current!=read(path)['superseded_reference']:return finish()
    else:
        a=assessment();atomic_json(RUN/'interpretation_v2.json',store.artifact(current))
        state=store.session(REVISED)['state'];phase=deepcopy(state['role_context']['phase_budget'])
        assert state.get('protocol_corrections_used',0)+2<=3
        packet=dict(selected_weights=[.075,.15],actual_receipted_economics=a['economics'],
            local_summary=a['local_summary'],continuation_conditions=a['continuation_conditions'],
            frozen_status='STOP; ranking abstains and avoided evaluation cost is zero. No Batch2.',
            next_objective='Investigate the five-interval controller approximation at the saved first production command divergence, new-clock .32 s. In a separately authorized bounded investigation, compare two unchanged production-controller solves (.075/.15) at one identical saved observed reduced state, available previous input and common initialization. Pass this diagnostic hypothesis only if command separation >1e-9 N is reproduced without changing early acceptance; otherwise reject the claimed lost-feedback mechanism. No backend replay now. Any subsequent predictor revision needs fresh, untouched reset-clock pairs, original accuracy/ranking/constraint thresholds and positive all-in screening economics; the used Batch1 becomes development evidence.')
        instruction=('Your latest response repeated superseded required_research_s=0 and -328.594 as current totals despite the updated packet. '
            'This is the second and final factual correction, not a request for a favorable decision. '
            'CURRENT RECEIPTS: pair forecasts 328.594 s; required native research overhead 42.376 s INCLUDING prior provider calls and accepted recovered/corrected tool calls; incremental screening 370.970 s; avoided evaluation 0; net -370.970 s BEFORE THIS FINAL CORRECTION. '
            'State that the final correction receipt will be ADDED and make net more negative; do not guess its runtime or call the cost final. Do not state required_research_s=0 or -328.594 as current economics. '
            'Keep STOP, no Batch2, incumbent unchanged, M5 open. Concisely preserve 4 checkpoint observations / 2 unique state-input-time cases, direction2/4, numerical4/4, quantitative0/4, ranking abstention, no threshold authority. '
            'State one precise next objective from the packet as a recommendation only, with no current execution or promised success. Return exactly one native research.milestone5_preparation, phase interpretation, holding_weights [.075,.15], rationale, readiness STOP, limitations, next_action finish_stop. About300 words.')
        with store.transaction() as db:
            state=store.session(REVISED,db)['state'];state['role_context'].update(instructions=instruction,decision_packet=packet,
                decision_packet_reference=plain(store.put(db,packet)),phase_started_turn=state.get('turn',0))
            assert state['role_context']['phase_budget']==phase
            store.update_state(db,REVISED,state)
            store.event(db,REVISED,'semantic_correction','stale_economics_final_correction',inputs=[current],outputs=[store.put(db,packet)])
        from tools.platform_models import payload_for
        from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
        atomic_json(RUN/'cost_correction_handoff.json',payload_for(h,EvidenceDrivenAdapter()))
        atomic_json(path,dict(superseded_reference=current,semantic_corrections=2,original_phase_budget=phase,usage_before=store.remaining()['used']))
    from examples.gvs_nmpc_route_experiment import load_credential
    from tools.platform_diagnosis_coordinator import run_until_handoff
    load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
    ref=run_until_handoff(h,'m5_interpretation');atomic_json(RUN/'interpretation.json',store.artifact(ref));finish()


def finalize_delivery():
    """Separate past experiment admission from final capability acceptance."""
    import hashlib
    from examples import milestone5_campaign_delivery as delivery
    from tools.diagnostic_workflow import save
    stage=validation.development
    validation.export(BATCH);delivery.export()
    a=read(RUN/'assessment.json');audit=read(stage.RUN/'acceptance_audit.json')
    assert not a['continue_batch2'] and a['research_judgment']['readiness'].startswith('STOP')
    p=read(stage.RUN/'protocol.json');p.update(development_admission_passed=True,
        ready_for_bounded_prospective_experiment=False,operational_next_action='finish_stop',
        accepted_final_research_judgment=a['research_judgment'],final_research_reference=a['research_reference'],
        final_research_store=RUN.relative_to(ROOT).as_posix(),capability_acceptance='acceptance_audit.json')
    p['commands']['execution']='Completed and stopped; Batch2 barred by frozen continuation. No numerical or backend replay.'
    p['commands']['export']='python examples/milestone5_campaign_closeout.py --phase export'
    atomic_json(stage.RUN/'protocol.json',p);store=Host(stage.RUN,'m5campaign-research').store
    ref=save(store,p)
    atomic_json(stage.RUN/'protocol_seal.json',dict(protocol_reference=ref,identity=digest(p),backend_grant_materialized=True,
        prospective_forecasts_sealed=True,immutable_prospective_protocol_identity=a['protocol_identity']))
    ready=read(stage.RUN/'readiness.json');ready.update(passed=False,development_admission_passed=True,
        final_status='prospective_screening_not_useful',accepted_final_research='STOP',further_validation_permitted=False,
        final_failed_conditions=[k for k,v in a['continuation_conditions'].items() if not v])
    atomic_json(stage.RUN/'readiness.json',ready)
    d=read(stage.RUN/'delivery.json');d.update(accepted_final_research=a['research_reference'],
        research_store=RUN.relative_to(ROOT).as_posix(),batch1='completed',batch2='stopped_before_grant',
        capability_acceptance='acceptance_audit.json',ranking_substage=audit['ranking_substage'],
        final_failed_conditions=ready['final_failed_conditions'],incomplete_work=[])
    atomic_json(stage.RUN/'delivery.json',d)
    accounting=read(stage.RUN/'accounting.json');accounting['validation_corrections']=read(RUN/'interventions.json')
    accounting['corrections']['scope']='development only; validation corrections recorded separately'
    atomic_json(stage.RUN/'accounting.json',accounting)
    source=Path(__file__);name=source.relative_to(ROOT)
    atomic_json(stage.RUN/'closeout_implementation_identity.json',dict(phase='post-outcome native recovery and truthful export only',
        frozen_validation_implementation_unchanged=True,file=name.as_posix(),sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
    for dest in (stage.EVIDENCE/'implementation'/name,validation.evidence(BATCH)/'implementation'/name):
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(source.read_bytes())
    with store.transaction() as db:
        store.event(db,'m5campaign-research','campaign_delivery','completed_stopped',outputs=[ref])
        ids=[r[0] for r in db.execute('SELECT run_id FROM sessions')]
    atomic_json(stage.RUN/'events.json',[e for run in ids for e in store.events(run)])
    (stage.EVIDENCE/'artifacts'/(ref['artifact_id']+'.json')).write_bytes(store.artifact(ref,raw=True))
    for path in stage.RUN.glob('*.json'):(stage.EVIDENCE/path.name).write_bytes(path.read_bytes())
    for dest in (stage.EVIDENCE,validation.evidence(BATCH)):
        atomic_json(dest/'sha256_manifest.json',{p.relative_to(dest).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(dest.rglob('*')) if p.is_file() and p.name!='sha256_manifest.json'})
    stage.check_previous()


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('recover','correct','correct-cost','finish','export'),required=True);args=parser.parse_args()
    if args.phase=='recover':recover();validation.export(BATCH)
    elif args.phase=='correct':correct()
    elif args.phase=='correct-cost':correct_cost()
    elif args.phase=='export':finalize_delivery()
    else:finish()
