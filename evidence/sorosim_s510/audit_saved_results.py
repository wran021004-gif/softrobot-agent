"""Read-only reproduction of delivered rankings, directions and execution counts.

Reads only immutable archives and saved arrays. No solver or simulation imports.
"""
from pathlib import Path
import math
import json
import numpy as np
from tools.research.numerics import archived
from tools.state_io import read,atomic_json

ROOT=Path(__file__).resolve().parents[2]
DEST=Path(__file__).resolve().parent


def main():
    summary=read(DEST/'summary.json');mathematics=read(DEST/'mathematics.json')
    progress=read(DEST/'progress.json')['candidates'];folder='evidence/sorosim_s510/study'
    physics_steps=roots=0;identities=set();direction=[];steps=[];incumbent=None
    base=progress[0]['measure'];xml=None;initial=None
    for row in progress:
        assert row['sequence_identity'] not in identities;identities.add(row['sequence_identity'])
        result=archived(folder,row['reference']);source=archived(folder,row['source'])
        raw=archived(folder,result['raw_reference']);u=np.asarray(source['trajectory']['tensions_n'])
        assert u.shape==(35,4) and np.isfinite(u).all() and np.all((u>=0)&(u<=8))
        assert np.max(np.abs(row['coefficients_n']))<=2.
        assert raw['physics_timestep_s']==.0005
        current_initial={k:raw['samples'][0][k] for k in ('qpos_rad','qvel_rad_s')}
        if xml is None:xml=raw['xml_sha256'];initial=current_initial
        assert raw['xml_sha256']==xml and current_initial==initial
        physics_steps+=raw['physics_steps']
        if row['valid']:
            assert raw['physics_steps']==700 and len(raw['samples'])==36
            samples=raw['samples'];hold=[v for v in samples if .3-1e-12<=v['time_s']<=.35+1e-12]
            assert len(hold)==6
            actual=np.array([samples[-1]['position_error_m'],max(v['position_error_m'] for v in hold),max(v['speed_m_s'] for v in hold)])
            expected=np.array([row['measure'][k] for k in ('terminal_position_error_m','holding_max_position_error_m','holding_max_speed_m_s')])
            np.testing.assert_allclose(actual,expected,rtol=1e-13,atol=1e-14)
            np.testing.assert_allclose(max(0.,max(actual/np.array([.01,.01,.02])-1)),row['registered_task_gap']['normalized_gap'],atol=1e-12)
        predicted=row.get('predicted_measure')
        if predicted and row['valid']:
            bm=mathematics['reference-32']['measure']['normalized_gap']
            p=bm-predicted['normalized_gap'];a=base['normalized_gap']-row['measure']['normalized_gap']
            direction.append(dict(reference=row['reference'],label=row['label'],
                prediction_was_available_before_execution=True,predicted_improvement=p,
                observed_improvement=a,direction_agrees=bool(p*a>0) if p and a else None,
                within_original_guided_step_domain=bool(np.max(np.abs(row['coefficients_n']))<=.1),
                scope='Local affine heuristic; outside .1 N is explicit extrapolation, not a guaranteed direction'))
            previous_prediction=incumbent.get('predicted_measure') if incumbent else None
            if incumbent is progress[0]:previous_prediction=mathematics['reference-32']['measure']
            if incumbent and previous_prediction:
                pi=previous_prediction['normalized_gap']-predicted['normalized_gap']
                ai=incumbent['measure']['normalized_gap']-row['measure']['normalized_gap']
                steps.append(dict(reference=row['reference'],incumbent_before=incumbent['reference'],
                    label=row['label'],predicted_incremental_improvement=pi,observed_incremental_improvement=ai,
                    direction_agrees=bool(pi*ai>0) if pi and ai else None,
                    predicted_to_improve=pi>0,actually_improved=ai>0))
        if row['valid'] and (incumbent is None or
                (row['measure']['normalized_gap'],row['measure']['sum_normalized_excess'])<
                (incumbent['measure']['normalized_gap'],incumbent['measure']['sum_normalized_excess'])):
            incumbent=row
    for value in mathematics.values():
        result=archived(folder,value['reference'])
        assert result['complete'] and result['root_count']==35*value['substeps']
        residuals=np.asarray(result['raw']['roots'],dtype=float)[:,2]
        assert np.isfinite(residuals).all() and max(residuals)<1e-9
        roots+=result['root_count']
    calls=read(DEST/'study/calls.json');ledger=read(DEST/'study/ledger.json')
    assert ledger['used']['backend_solves']==len(progress)<=192
    assert ledger['used']['model_calls']==0
    assert len(mathematics)==summary['mathematical_replays']<=18
    assert all(row['receipt'] for row in calls)
    ranking=sorted((r for r in progress if r['valid']),key=lambda r:(not r['accepted'],r['measure']['normalized_gap'],r['measure']['sum_normalized_excess']))
    assert [r['reference'] for r in ranking]==[r['reference'] for r in summary['ranked_candidates']]
    if ranking:
        best=ranking[0];source=archived(folder,best['source'])['trajectory']
        result=archived(folder,best['reference']);raw=archived(folder,result['raw_reference'])
        candidate=archived(folder,summary['candidate']);cfg=candidate['configuration']
        atomic_json(DEST/'best_control.json',dict(version='s510_review_control_v1',
            original_task_passed=best['accepted'],evaluation=best['reference'],candidate=summary['candidate'],
            candidate_parameters=candidate['parameters'],robot=cfg['robot'],task=cfg['task'],
            discretization=cfg['policy']['discretization'],backend=cfg['policy']['backend'],
            control_times_s=source['times_s'][:-1],tendon_order=source['tendon_order'],
            requested_tensions_n=source['tensions_n'],actual_tensions_n=[v['actual_tension_n'] for v in raw['samples'][1:]],
            execution_mode='ideal_tension',correction_coefficients_n=best['coefficients_n'],
            measure=best['measure'],registered_acceptance=result['acceptance'],
            numerical_implementation=result['implementation'],scope='Exact evaluated schedule for this frozen initial task; no hardware or repeatability claim'))
    if summary['original_task_passed']:
        assert progress[-1]['accepted'] and not any(r['accepted'] for r in progress[:-1])
    audit=dict(unique_complete_or_failed_evaluations=len(progress),physics_steps=physics_steps,
        mathematical_integrations=len(mathematics),implicit_roots=roots,provider_requests=0,
        ranked_results_consistent=True,all_receipts_terminal=True,
        first_pass_immediate_stop_check=True if summary['original_task_passed'] else 'not_applicable_no_pass',
        prospective_regional_bound_established=False,new_dynamics_integrations=0,
        new_physics_steps=0,new_optimizer_calls=0,
        final_resource_use=ledger['used'],summary_resource_use_before_final_closeout=summary['used'],
        failed_public_receipts=[dict(request_id=r['request_id'],error=json.loads(r['receipt']).get('error'))
            for r in calls if json.loads(r['receipt']).get('execution_status')=='failed'])
    atomic_json(DEST/'direction_validation.json',dict(comparisons=direction,
        agreement_count=sum(v['direction_agrees'] is True for v in direction),
        disagreement_count=sum(v['direction_agrees'] is False for v in direction),
        incumbent_step_comparisons=steps,
        incremental_agreement_count=sum(v['direction_agrees'] is True for v in steps),
        incremental_disagreement_count=sum(v['direction_agrees'] is False for v in steps),
        scope='One explicit mathematical recommendation; later points are simulator-driven trials/probes with logged affine predictions, not independent mathematical recommendations.',
        exact_32_substep_comparisons=summary['exact_paired_direction_checks']))
    paired=summary['paired_error_budgets'];bounds=[]
    for value in paired.values():
        model=archived(folder,value['mathematical']);physical=archived(folder,value['physical'])
        a=archived(folder,model['source_reference'])['trajectory']
        b=archived(folder,physical['source_reference'])['trajectory']
        assert all(a[k]==b[k] for k in ('model_identity','design_identity','task_identity','tendon_order','times_s','tensions_n'))
    if 'reference-32' in paired:
        a=paired['reference-32'];ma=a['model_measure'];sa=a['simulation_measure']
        reference_bias=sa['normalized_gap']-ma['normalized_gap']
        for label,b in paired.items():
            if label=='reference-32':continue
            mb=b['model_measure'];sb=b['simulation_measure']
            # Use outward intervals on G, rather than treating rounded reported
            # scalar objectives as exact. These remain evaluated-endpoint bounds.
            ml,mu=ma['returned_array_gap_interval'];sl,su=sa['returned_array_gap_interval']
            nl,nu=mb['returned_array_gap_interval'];tl,tu=sb['returned_array_gap_interval']
            da=[math.nextafter(sl-mu,-math.inf),math.nextafter(su-ml,math.inf)]
            db=[math.nextafter(tl-nu,-math.inf),math.nextafter(tu-nl,math.inf)]
            change=[math.nextafter(db[0]-da[1],-math.inf),math.nextafter(db[1]-da[0],math.inf)]
            variation=max(abs(v) for v in change)
            decrease=math.nextafter(ml-nu,-math.inf)
            lower=math.nextafter(decrease-variation,-math.inf)
            bounds.append(dict(candidate=label,reference_scalar_bias=reference_bias,
                candidate_scalar_bias=sb['normalized_gap']-mb['normalized_gap'],
                discrepancy_change_interval=change,observed_absolute_bias_change_upper=variation,
                paired_variation_improvement_lower_bound=lower,condition_met=lower>0,
                prospective_certified=False))
        atomic_json(DEST/'bound_investigation.json',dict(
            baseline_absolute_error_bound=a['error_budget']['epsilon'],
            largest_possible_absolute_bound_lower_bound=ma['returned_array_gap_interval'][1]-a['error_budget']['epsilon'],
            interpretation='Since G_math(new)>=0 and epsilon_new>=0, a negative value rules out this particular symmetric sufficient test from this baseline, not task feasibility.',
            discrepancy_variation_checks=bounds,
            prospective_alternative='If |D(z_new)-D(z_base)| <= L_D*norm(z_new-z_base) is independently valid on the region, predicted improvement greater than that term guarantees sampled simulation improvement, where D=G_sim-G_math.',
            missing_proof='No verified regional derivative/interval enclosure for D; sampled secants cannot supply an upper Lipschitz bound. No integration bound to exact rod solutions or hardware.',
            new_model_evaluations=0,new_physics_steps=0,new_optimizer_calls=0))
    atomic_json(DEST/'delivery_audit.json',audit)
    print(json.dumps(audit,indent=2))


if __name__=='__main__':main()
