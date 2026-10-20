"""Read-only scientific audit; additive summaries only, no Provider or worker launch."""
from collections import defaultdict
import json
from pathlib import Path
import numpy as np
from tools.platform_host import Host
from tools.research.config import ROOT
from tools.research.state import state
from tools.research.feedback import task_gap
from tools.research.research_context import context, decision_brief, physical_diagnostic, read_coverage
from tools.research.rl import compatible_references
from tools.research_tasks import task_adapter
from tools.research.control_correction import constraint_vectors, corrected_tensions, correction_basis
from tools.research.numerics import archived
from tools.state_io import atomic_json, digest, read
from tests.research.s12_audit import verify_nmpc


def study(name):return Host(ROOT/'runs/research'/name,name,actor='unified-research')


def local_response_audit(h):
    s=state(h);ref=s['control_search_results'][0];search=h.store.artifact(ref)
    plan=next(h.store.artifact(r)['original_plan'] for r in s['plans'] if h.store.artifact(r)['original_plan']['action']=='control_search')
    settings=plan['control_search']['settings'];rows=search['candidates'];by_ref={r['reference']['artifact_id']:r for r in rows}
    cfg=h.store.artifact(search['candidate'])['configuration'];adapter=task_adapter(cfg);limits=adapter.ranking_limits()
    options=dict(target=cfg['task']['goal']['data']['target_m'],holding_start=adapter.holding_start_s(),
        position_limit=limits['holding_max_error_m'],terminal_position_limit=limits['terminal_error_m'],speed_limit=limits['holding_max_speed_m_s'])
    groups=defaultdict(list)
    for r in rows:
        if r['label']=='finite_difference':groups[r['prediction_base']['artifact_id']].append(r)
    rebuilt=[]
    for index,(base_id,probes) in enumerate(groups.items()):
        base=by_ref[base_id];y=constraint_vectors(base['outputs'],**options);columns=[]
        for probe in probes:
            delta=np.asarray(probe['coefficients_n'])-base['coefficients_n'];changed=np.flatnonzero(delta)
            assert len(changed)==1
            columns.append((constraint_vectors(probe['outputs'],**options)-y)/delta[changed[0]])
        jac=np.stack(columns,axis=-1).reshape(-1,len(columns));singular=np.linalg.svd(jac,compute_uv=False)
        original=search['local_responses'][index]
        assert np.allclose(singular,original['singular_values'],rtol=1e-12,atol=1e-12)
        assert np.linalg.matrix_rank(jac)==original['response_rank']
        rebuilt.append(dict(base=base['reference'],probe_references=[r['reference'] for r in probes],
            response_rank=int(np.linalg.matrix_rank(jac)),columns=len(columns),singular_values_equal=True))
    start=h.store.artifact(search['source'])['trajectory'];channels=len(start['tendon_order'])
    upper=[t['force_limit_n'] for t in cfg['robot']['structure']['data']['tendons']]
    for row in rows:
        expected=corrected_tensions(start['tensions_n'],start['times_s'][:-1],settings['knots_s'],row['coefficients_n'],upper,settings.get('correction_window_s'))
        actual=h.store.artifact(row['source'])['trajectory']['tensions_n']
        assert np.array_equal(expected,actual)
    basis=correction_basis(start['times_s'][:-1],settings['knots_s'],channels,settings.get('correction_window_s'))
    support=[dict(coefficient=j,first_s=float(np.asarray(start['times_s'][:-1])[np.flatnonzero(basis[:,j])[0]//channels]),
        last_s=float(np.asarray(start['times_s'][:-1])[np.flatnonzero(basis[:,j])[-1]//channels])) for j in range(basis.shape[1]) if np.any(basis[:,j])]
    return dict(reference=ref,source_study=h.run_id,baseline=rows[0]['reference'],baseline_gap=rows[0]['task_gap'],
        best=search['best']['reference'],best_gap=search['best']['task_gap'],original_acceptance_passed=search['best']['original_acceptance']['accepted'],
        saved_callback_jacobians=rebuilt,all_saved_schedules_reproduced=True,coefficient_time_support=support,
        local_responses_query=dict(reference=ref,pointer='/local_responses'),cost_feedback=search['cost_feedback'],
        scope='Historical positive control in its own frozen task. Local finite differences and one passing case establish no global method ranking or controllability theorem.')


def main():
    out=ROOT/'evidence/s127_working_set';out.mkdir(parents=True,exist_ok=True)
    h=study('s126-cold-live-20261020');before=digest(state(h));ledger=h.store.remaining();event_count=len(h.store.events(h.run_id))
    c=context(h);ws=c['evidence_working_set'];coverage=read_coverage(h);s=state(h)
    diagnostics=[physical_diagnostic(h,r) for r in [*s['physical_replays'],*s['results']]]
    atomic_json(out/'projection.json',ws)
    atomic_json(out/'physical_diagnostics.json',dict(source_study=h.run_id,records=diagnostics,simulation_steps=0,
        scope='Saved measurements only. Incomplete execution is not a valid scientific failure. No causal mechanism is inferred.'))
    # Reuse original evaluator/profile audit; any bulky temporary exports stay in ignored runs.
    temporary=ROOT/'runs/s127_saved_nmpc_audit';temporary.mkdir(parents=True,exist_ok=True)
    independently_verified=verify_nmpc(h,temporary)
    atomic_json(out/'audit.json',dict(source_study=h.run_id,source_state_identity=before,
        working_set_bytes=len(json.dumps(ws,ensure_ascii=False,separators=(',',':')).encode('utf8')),
        decision_brief_bytes=len(json.dumps(decision_brief(c),ensure_ascii=False,separators=(',',':')).encode('utf8')),
        successful_read_feedbacks=len(coverage),actually_delivered_reads=sum(r['successfully_provided'] for r in coverage),
        full_or_partial_data_deliveries=sum(r['complete_data'] for r in coverage),read_counts=ws['read_counts'],
        repeat_interpretation='Query identity and overlap only; necessity and model understanding cannot be inferred.',
        scientific_results=len(ws['all_fresh_results']),physical_records=len(diagnostics),
        complete_physical=sum(d['valid_complete'] for d in diagnostics),incomplete_physical=sum(not d['valid_complete'] for d in diagnostics),
        independent_nmpc_reverification=[{k:r[k] for k in ('reference','execution_id','accepted','original_evaluator_and_full_acceptance_equal',
            'saved_state_motion_and_profile_equal','trajectory_samples','controller_updates','metrics')} for r in independently_verified],
        existing_residual_references=[{k:r[k] for k in ('candidate','source','source_kind','available','reason') if k in r}
            for r in compatible_references(h,publish=False)],new_provider_requests=0,new_scientific_executions=0,new_training_actions=0,
        actual_new_prompt_tokens=None,actual_new_completion_tokens=None,actual_new_cache_tokens=None,
        real_model_decision_comparison='not_run: independent scope, budget and external-transfer authorization required'))
    assert before==digest(state(h)) and ledger==h.store.remaining() and event_count==len(h.store.events(h.run_id))
    positive=study('s12-mirror-live-20261020');positive_before=digest(state(positive));response=local_response_audit(positive)
    p1=read(ROOT/'evidence/control_search_p1/summary.json');methods=[]
    for method in p1['methods']:
        best=method['best'];value=archived('evidence/control_search_p1/study',best['reference'])
        assert task_gap(value)==best['task_gap']
        methods.append(dict(method=method['algorithm'],source_folder='evidence/control_search_p1/study',
            baseline=method['candidates'][0]['reference'],baseline_gap=method['candidates'][0]['task_gap'],
            best=best['reference'],best_gap=best['task_gap'],recorded_callbacks=len(method['candidates']),
            local_solver=best.get('local_solver'),stop_reason=method['stop_reason']))
    method_out=ROOT/'evidence/s127_method_validation';method_out.mkdir(parents=True,exist_ok=True)
    atomic_json(method_out/'saved_evidence.json',dict(s12_positive_control=response,p1_methods=methods,
        prior_audits=['evidence/control_search_p0/summary.json','evidence/control_search_p2/saved_evidence_views.json'],
        new_physics=0,new_training=0,new_provider_requests=0,
        failure_classification=dict(input_bounds='Measured saturation is observed, not proof that all feasible controls fail.',
            representation='Time support is reconstructed exactly; adequacy outside the tested basis is unverified.',
            numerical_method='P1 predicted near-zero violation but its actual best still failed; the positive S12 case passed independently.',
            physical_capability='S12.6 failures do not prove structural infeasibility.'),
        limitation='Different tasks, structures, budgets and bases prevent general method-superiority claims. No new engineering Study was necessary for these saved-data questions.'))
    assert positive_before==digest(state(positive))
    print(json.dumps(dict(status='passed',working_set_bytes=len(json.dumps(ws,separators=(',',':'))),
        complete_physical=sum(d['valid_complete'] for d in diagnostics),nmpc_verified=len(independently_verified),
        local_jacobians_rebuilt=len(response['saved_callback_jacobians']),new_provider_requests=0,new_science=0)))


if __name__=='__main__':main()
