"""Receipt-based successor accounting and native research; no computation replay."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from examples import milestone5_successor as stage
from tools.platform_store import Store,zero
from tools.state_io import read,atomic_json,digest


def accounting():
    store=Store(stage.RUN)
    with store.connect(True) as db:
        receipts=[json.loads(r[0]) for r in db.execute('SELECT receipt FROM calls WHERE receipt IS NOT NULL')]
        pending=[dict(r) for r in db.execute('SELECT request_id,reserved FROM calls WHERE receipt IS NULL')]
        work=json.loads(db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone()[0])
    actual={k:sum(r['charged'][k] for r in receipts) for k in zero()}
    shared={k:stage.PAST[k]+actual[k] for k in zero()}
    prior=read(stage.previous.RUN/'accounting.json')
    result=dict(successor_actual=actual,fullscope_actual=stage.PAST,shared_actual=shared,
        shared_limit=stage.previous.TOTAL,remaining_shared={k:stage.previous.TOTAL[k]-shared[k] for k in zero()},
        development_limit=stage.DEVELOPMENT,development_remaining=store.remaining()['remaining'],
        protected_validation=read(stage.RUN/'plan.json')['protected_validation'],numerical_work=work,
        pending_reservations=pending,receipt_count=len(receipts),
        prior_lifetime_accounting=prior,lifetime_rule='Add successor actual to prior lifetime totals; shared envelope includes only fullscope plus successor, never prior lifetime costs.',
        convention='Compilation, failed attempts, numerical work and providers charged; engineering inspection/edit/test/export follows predecessor convention. Full-order emulated steps are not new independent backend attempts.')
    atomic_json(stage.RUN/'accounting.json',result);return result


def assessment():
    stage.check_previous();fixed=read(stage.RUN/'fixed_target.json');old=read(stage.previous.RUN/'revision2_local.json');local=[]
    for case,prior in zip(fixed['cases'],old['cases']):
        _,s=stage.previous.source(prior['source']);target=np.asarray(s['configuration']['task']['goal']['data']['target_m'])
        prediction=case['result'];truth=prior['observed_endpoint']
        p=float(np.linalg.norm(np.asarray(prediction['position_m'])-target));o=float(np.linalg.norm(np.asarray(truth['position_m'])-target))
        local.append(dict(case=case['case'],score=case['score'],numerical_pass=case['numerical_pass'],
            predicted_task_position_error_m=p,observed_task_position_error_m=o,
            position_false_safe=p<=.01<o,position_false_unsafe=o<=.01<p,
            maximum_scaled_residual=max(r['scaled_residual'] for r in prediction['rows']),
            maximum_backward_error=max(r['backward_error'] for r in prediction['rows']),
            independent_solver_difference=case['independent_solver_difference']))
    kernels=[]
    for name in ('kernel_probe','native_probe','native_o0','native_o1','native_reverse','native_reverse_o0','native_reverse_optimized',
                 'native_mixed','native_split','native_shared','native_chunked','native_chunked_repair1','mass_form','native_full_chunked'):
        if (stage.RUN/(name+'_receipt.json')).exists():
            result=read(stage.RUN/(name+'.json'));receipt=read(stage.RUN/(name+'_receipt.json'))
            kernels.append(dict(name=name,status=receipt['execution_status'],charged_s=receipt['charged']['wall_s'],
                all_equivalent=result.get('all_equivalent'),median_speedup=result.get('median_speedup'),error=result.get('error'),
                measured_evaluation_s=[c['result']['evaluation_s'] for c in result.get('cases',[]) if 'result' in c]))
    component=read(stage.RUN/'feedback_component.json') if (stage.RUN/'feedback_component.json').exists() else None
    result=dict(version='milestone5_successor_assessment@1.0.0',status='active_development',milestone5='open',
        approved_local_protocol=read(stage.RUN/'fixed_target_protocol.json'),local_counts=fixed['counts'],numerical_passes=fixed['numerical_passes'],local=local,
        position_false_safe=sum(r['position_false_safe'] for r in local),position_false_unsafe=sum(r['position_false_unsafe'] for r in local),
        discretization_bias=read(stage.RUN/'numerical_targets.json'),kernel_experiments=kernels,
        earliest_feedback=read(stage.RUN/'feedback_audit.json'),complete_update_component=component,
        historical_full_history=read(stage.previous.RUN/'assessment.json')['pairs'],
        historical_result_scope='Preserved development failures, not results for the experimental native controller.',
        selected_deliverable='No new controller/predictor admitted yet',incumbent=read(stage.RUN/'plan.json')['incumbent'],
        validation_launched=False,new_backend_attempts=0,prospective_outcomes=None,independent_repeat=None,
        actual_avoided_evaluations=0,actual_savings_s=0.,accounting=accounting())
    atomic_json(stage.RUN/'assessment.json',result);return result


def runtime_research():
    import os
    from tools.platform_diagnosis_coordinator import configure_role,run_until_handoff
    from tools.platform_models import payload_for
    from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
    from tools.diagnostic_workflow import save
    from examples.gvs_nmpc_route_experiment import load_credential
    h=stage.session('runtime-research');path=stage.RUN/'runtime_research.json'
    old=h.store.session(h.run_id)['state'].get('handoffs',{}).get('m5_interpretation')
    if old:atomic_json(path,h.store.artifact(old));return
    prepared=stage.RUN/'runtime_research_payload.json'
    if not prepared.exists():
        a=assessment();binding=read(stage.previous.prior.RUN/'freeze.json')['source_binding']
        with h.store.transaction() as db:
            state=h.store.session(h.run_id,db)['state']
            state.setdefault('fact_scope',dict(project='m5-successor-20261005',binding=binding));state.setdefault('fact_catalog',{})
            h.store.update_state(db,h.run_id,state)
        packet=dict(selected_weights=[.075,.15],direct_authorization='User attachment 8ce90352 authorizes compact task evidence to existing DeepSeek runner; no workers or changed provider.',
            numerical_target_approval=a['approved_local_protocol'],local_counts=a['local_counts'],local_numerical_passes=a['numerical_passes'],
            local_position_threshold_errors=dict(false_safe=a['position_false_safe'],false_unsafe=a['position_false_unsafe']),
            kernels=a['kernel_experiments'],prior_complete_update_seconds=[17.8897,19.5298],deadline_s=.01,
            prior_jacobian_per_call_seconds=[.21245,.21287],prior_warm_preparation_seconds=[6.61,6.63],
            earliest_divergence=[dict(candidate=c['candidate'],update=c['first_divergence_update'],reason='Same current state and previous input, predictor did not replan while production did.') for c in a['earliest_feedback']['cases']],
            feedback_implementation='Scoped exact native force provider + actual v7 command boundary on every configured update, own full-state history, commands sealed before emulated advance. Not yet measured or promoted; native kernel must first demonstrate acceleration.',
            wall_clock_policy=dict(minimum_s=5.,budget_s=15.,relative_improvement=.1),
            current_bounded_work='One optimized 16 MB scalar reverse AD C build with explicit 900 s cap, all failed compilation work retained; six same-state equivalence/speed evaluations. No new backend.',
            outstanding=['Complete feedback/position classification on original and reset pairs','Feasibility-qualified useful ranking','All operational decision costs including research; abstention avoids zero','Complete .01 s production update','Two untouched pairs and designated independent repeat after admission'],
            shared_remaining=a['accounting']['remaining_shared'],development_remaining=a['accounting']['development_remaining'],
            protected_validation=a['accounting']['protected_validation'],scope='Native handoff finishes this analysis request only, never the active campaign. NO_GO blocks validation of this revision but does not cancel affordable development.')
        instructions=('Assess the concrete M5 successor state and recommend one decisive affordable next runtime/feedback experiment. '
            'User explicitly approved fixed .5 ms transition reference and independent Cholesky residual/backward-error checks instead of fictitious two-tolerance direct solves; six local cases now pass, but this is not continuous accuracy, independent backend validation or milestone completion. '
            'Scalar expansion and O0 native variants were slower; optimized builds have not yet completed. Do not invent a successful speedup or claim compilation failures prove all methods impossible. '
            'Original and failed reset histories remain development. Timed optimizer stopping can change response when accelerated, so version it and require fresh comparisons; never use old backend outcomes as validation of altered controller response. '
            'Preserve physical model, objective, constraints and all thresholds. Experimental stopping/implementation changes are authorized with distinct identity. Complete deadline is .01 s including all preparation/optimization/validation, cold setup separately explicit. '
            'Give a precise measured gate for the next experiment and explain when not to purchase complete forecasts/backends. The current budget protects all six prospective backends and final interpretation. No provider migration or workers. '
            'Return exactly one native research.milestone5_preparation tool call, phase interpretation, holding_weights [.075,.15], rationale, readiness beginning NO_GO or GO_EXPERIMENT_FULL, limitations, next_action finish_stop. About 450 words. This handoff finishes this advisory request only; campaign stays active.')
        configure_role(h,'design',instructions,phase='interpretation',delivery_tool=stage.previous.RESEARCH.extension_id,
            native_store_root=str(stage.RUN),memory_identity=h.run_id,native_fixed={},binding=binding,decision_packet=packet,
            decision_packet_reference=save(h.store,packet),phase_budget=dict(limit=dict(model_calls=2,tool_calls=4,wall_s=180.),protect_project=dict(wall_s=1265.)))
        atomic_json(prepared,payload_for(h,EvidenceDrivenAdapter()))
    load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
    ref=run_until_handoff(h,'m5_interpretation');atomic_json(path,h.store.artifact(ref));stage.check_previous()


def correct_runtime_research():
    import os
    from copy import deepcopy
    from tools.platform_store import plain
    from tools.platform_diagnosis_coordinator import run_until_handoff
    from tools.platform_models import payload_for
    from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
    from examples.gvs_nmpc_route_experiment import load_credential
    h=stage.session('runtime-research');state=h.store.session(h.run_id)['state'];path=stage.RUN/'runtime_research_correction.json'
    current=state['handoffs']['m5_interpretation']
    if path.exists() and current!=read(path)['superseded_reference']:
        atomic_json(stage.RUN/'runtime_research.json',h.store.artifact(current));return
    if not path.exists():
        original=h.store.artifact(current);atomic_json(stage.RUN/'runtime_research_v1.json',original)
        budget=deepcopy(state['role_context']['phase_budget'])
        correction=dict(superseded_reference=current,phase_budget_before=budget,facts=[
            'Local propagation fixed_target.json passes position/speed/vector/direction and independent Cholesky checks in all six cases. Kernel probes are different experiments: force residual and exact full argument Jacobian at current state/input/zero acceleration. Kernel equivalence is not endpoint accuracy or direction testing.',
            'Measured median speedups: scalar MX-to-SX kernel_probe 0.5563646; full-Jacobian native_o0 about 0.5204320; scalar reverse native_reverse_o0 about 0.3175721. All are slower. Failed compile attempts are compiler timeouts, not numerical optimizer timeouts.',
            'The optimized reverse build is pending; its 900 s cap and all costs are registered. No timing success is known. Kernel gate is residual difference <=1e-10 and relative Jacobian difference <=1e-8 at all six points, plus median speedup strictly >1. These thresholds are distinct from the approved local trajectory thresholds.',
            'After a useful equivalent kernel result, next is ONLY five actual complete command updates: original075 first three, reset075 first two, with own causal full-state history. No full forecasts or backends merely because a kernel is faster. Complete .01 s update, useful full-history classification/ranking and all-in economics remain open.'])
        packet=deepcopy(state['role_context']['decision_packet']);packet.update(first_judgment=original,factual_correction=correction)
        instruction=('Correct the four factual conflations in factual_correction. Keep local propagation results separate from force/Jacobian kernel equivalence, compiler failures separate from numerical optimizer behavior, and kernel speedup separate from complete controller latency. '
            'Use the registered pending optimized build then five-command component as the next affordable work. No milestone admission or validation yet. Campaign remains active after this advisory handoff. '
            'Return exactly one native research.milestone5_preparation call, phase interpretation, holding_weights [.075,.15], readiness starting NO_GO, rationale, new accurate limitations, next_action finish_stop. Maximum 230 words.')
        with h.store.transaction() as db:
            state=h.store.session(h.run_id,db)['state'];role=state['role_context']
            role.update(instructions=instruction,decision_packet=packet,decision_packet_reference=plain(h.store.put(db,packet)),phase_started_turn=state.get('turn',0))
            assert role['phase_budget']==budget
            h.store.update_state(db,h.run_id,state);h.store.event(db,h.run_id,'semantic_correction','prepared',inputs=[current],outputs=[h.store.put(db,correction)])
        atomic_json(path,correction);atomic_json(stage.RUN/'runtime_research_correction_payload.json',payload_for(h,EvidenceDrivenAdapter()))
    load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
    ref=run_until_handoff(h,'m5_interpretation');atomic_json(stage.RUN/'runtime_research.json',h.store.artifact(ref));stage.check_previous()


def export_checkpoint():
    """User-requested checkpoint, not campaign completion or admission."""
    import hashlib
    a=assessment();store=Store(stage.RUN)
    with store.connect(True) as db:
        receipts=[json.loads(r[0]) for r in db.execute('SELECT receipt FROM calls WHERE receipt IS NOT NULL')]
        ids=[r[0] for r in db.execute('SELECT run_id FROM sessions')]
    events=[e for name in ids for e in store.events(name)]
    assert not a['accounting']['pending_reservations'],'UNSETTLED_CALLS'
    assert all(abs(a['accounting']['successor_actual'][k]-store.remaining()['used'][k])<1e-6 for k in zero())
    native=read(stage.RUN/'native_full_chunked.json')
    audit=dict(status='user_requested_progress_checkpoint',milestone5='open',campaign_complete=False,
        local_fixed_target_passed=all(c['numerical_pass'] and all(c['score'][k] for k in ('position_pass','speed_pass','vector_pass','direction_correct')) for c in a['local']),
        native_kernel_equivalent=native['all_equivalent'],native_kernel_median_speedup=native['median_speedup'],
        complete_update_measured=False,full_history_repair_validated=False,validation_launched=False,new_backend_attempts=0,
        incumbent_retained=True,historical_NO_GO_unchanged=True,actual_savings_s=0.,
        research_scope='Two native research calls, including a factual correction, concern earlier unaccelerated revisions. They do not judge the subsequently completed full-Jacobian chunked kernel.',
        remaining=['Check nonzero-acceleration equivalence and five complete causal controller updates.',
            'Repair full-history position classification on both development pairs; establish useful feasibility-qualified ranking and full operational economics.',
            'Meet the complete .01 s control-update deadline; kernel speedup alone is insufficient.',
            'Obtain current native admission judgment; freeze and perform two untouched pairs plus a fresh designated independent repeat only after all development gates pass.'],
        next_command='python examples/milestone5_successor.py --phase feedback-component-full-chunked',
        next_command_scope='Existing verified local RUN and compiled DLL; identity checked before reuse. No new experiment was started after the commit/push request.',
        excluded_generated_files='Portable compiler archive/toolchain, huge generated C/object files and DLLs stay in ignored runs; source hashes, exact compiler commands, versions, recipes and measured results are exported.',
        report='docs/milestone5_successor_campaign.md')
    if a['complete_update_component'] is not None:
        component=a['complete_update_component']; receipt=read(stage.RUN/'feedback_component_receipt.json')
        audit.update(status='limited_5A_component_checkpoint_sealed',complete_update_measured=True,
            component_status=receipt['execution_status'],component_charge=receipt['charged'],
            nonzero_acceleration_checks=component.get('nonzero_acceleration_checks',[]),
            task_A_stopped=True,task_A_full_forecasts=0,task_A_provider_attempts=0,
            next_command=None,next_command_scope='Task A stopped. No further M5 execution in this authorization.')
        audit['remaining']=audit['remaining'][1:]
    for name,value in (('acceptance_audit',audit),('receipts',receipts),('events',events)):
        atomic_json(stage.RUN/(name+'.json'),value)
    stage.EVIDENCE.mkdir(parents=True,exist_ok=True)
    (stage.EVIDENCE/'.gitattributes').write_bytes(b'* -text\nartifacts/*.bin -diff\nimplementation/** whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol\n')
    for path in stage.RUN.glob('*.json'):(stage.EVIDENCE/path.name).write_bytes(path.read_bytes())
    seen=set()
    def copy_references(value):
        if isinstance(value,dict):
            if set(value)=={'artifact_id','media_type'} and all(isinstance(v,str) for v in value.values()):
                key=value['artifact_id']
                if key in seen:return
                seen.add(key)
                try:body=store.artifact(value,raw=True)
                except (KeyError,ValueError):return
                path=stage.EVIDENCE/'artifacts'/(key+('.json' if value['media_type']=='application/json' else '.bin'))
                path.parent.mkdir(exist_ok=True);path.write_bytes(body)
                if value['media_type']=='application/json':copy_references(json.loads(body))
            else:
                for child in value.values():copy_references(child)
        elif isinstance(value,list):
            for child in value:copy_references(child)
    copy_references(events);copy_references(receipts)
    for name in ('examples/milestone5_successor.py','examples/milestone5_successor_delivery.py',
        'extensions/tendon_family/milestone5_fast_kernel.py','extensions/tendon_family/milestone5_feedback_runtime.py',
        'extensions/tendon_family/milestone5_fixed_transition.py','extensions/tendon_family/gvs_trajectory.py','tests/test_milestone5_successor.py'):
        path=stage.EVIDENCE/'implementation'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((ROOT/name).read_bytes())
    atomic_json(stage.EVIDENCE/'sha256_manifest.json',{p.relative_to(stage.EVIDENCE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(stage.EVIDENCE.rglob('*')) if p.is_file() and p.name!='sha256_manifest.json'})
    stage.check_previous();print(json.dumps(dict(audit=audit,usage=a['accounting']['successor_actual'],remaining=a['accounting']['remaining_shared'])))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--phase',default='assessment');args=parser.parse_args()
    if args.phase=='runtime-research':runtime_research()
    elif args.phase=='correct-runtime-research':correct_runtime_research()
    elif args.phase=='export-checkpoint':export_checkpoint()
    else:assessment();print('Updated receipt-based active development assessment; no computations replayed.')
