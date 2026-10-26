"""Zero-integration B2 delivery audit and nonduplicating cost summary."""
import sys
import numpy as np
import scipy
import mujoco

from examples.b2_math_decision_benchmark import OUT, read, ARCHIVE, options, task_measure
from tools.state_io import atomic_json


def main():
    files={p.stem:read(p) for p in OUT.glob('*.json')}
    ledger=[dict(file=name+'.json',**row['new_cost']) for name,row in files.items() if 'new_cost' in row]
    summed={key:sum(row.get(key,0) for row in ledger) for key in
        ['physics_steps','rollouts','model_builds','forward_evaluations','solver_calls','solver_iterations','solver_s','wall_s']}
    assert summed['physics_steps']<=500000
    s=files['decision_input'];h=files['paired_historical_validation']
    rebuilt=files['a4_control_probes']['search']['candidates'][0]['outputs']
    archived=s['targets']['up_z']['best_outputs']
    b1_baseline_difference=max(float(np.max(np.abs(np.asarray(rebuilt[field])-archived[field])))
        for field in ['tip_positions_m','tip_velocities_m_s'])
    assert b1_baseline_difference<1e-10
    assert h['prefix_identical'] and h['group_with_retained_original_targets']
    assert files['decision_C']['action']=='Same paired continuation as A/B.'
    correction=files['a4_control_independent'];assert correction['acceptance']['accepted']
    assert files['a4_control_holdout_plan']['coefficient_index']==files['a4_control_validation']['coefficient_index']
    benchmarks=[]
    frozen=files['benchmark_frozen'];baseline_task=frozen['configuration']['task']
    for name in ['neutral','soft','stiff','length_exchange']:
        r=files['benchmark_'+name];ind=files['benchmark_'+name+'_independent']
        assert r['configuration']['task']==baseline_task
        assert r['schedule']['provenance']['initialization']=='cold_constant_0.2_N'
        assert r['search']['algorithm']=='response'
        assert all(abs(v)<1e-15 for field in ['qpos_rad','qvel_rad_s']
            for v in r['configuration']['task']['initializer']['parameters']['data'][field].values())
        u=np.asarray(r['schedule']['trajectory']['tensions_n']);assert u.shape==(35,6)
        assert u.min()>=0. and u.max()<=8.
        candidates=r['search']['candidates']
        if candidates:assert np.max(np.abs(candidates[0]['coefficients_n']))==0.
        accepted=None if ind['acceptance'] is None else ind['acceptance']['accepted']
        if accepted:
            actual=task_measure(r['best_outputs'],**options(r['configuration']))
            assert actual['signed_maximum_excess']<=0.
            assert max(np.linalg.norm(np.asarray(r['best_outputs']['tip_positions_m'])-
                [v['tip_m'] for v in ind['raw']['samples']],axis=1))<1e-10
        first=next((i+1 for i,c in enumerate(candidates) if c['measure']['signed_maximum_excess']<=0),None)
        prefix={n:min(c['measure']['signed_maximum_excess'] for c in candidates[:n])
            for n in [51,76,101,102,126] if len(candidates)>=n}
        benchmarks.append(dict(name=name,accepted=accepted,best=None if r['search']['best'] is None else r['search']['best']['measure'],
            first_native_nonpositive_callback=first,prefix_best_J=prefix,stop=r['search']['stop_reason'],
            cost=r['new_cost'],independent_cost=ind['new_cost']))
    assert all(r['error_m']<1e-7 for r in files['benchmark_geometry']['results'])
    control=files['a4_control_validation'];radius=files['a4_radius']['sensitivities']
    a=np.array(radius[0]['fixed_control']['finite_difference_per_unit'])
    b=np.array(radius[1]['fixed_control']['finite_difference_per_unit'])
    summary=dict(environment=dict(python=sys.version,numpy=np.__version__,scipy=scipy.__version__,mujoco=mujoco.__version__,
            environment_path='D:/softrobot-agent/.f3-prestudy-env',thread_environment='inherited, no forced thread-count claim'),
        audit=dict(passed=True,physics_integration_performed=0,b1_baseline_maximum_difference=b1_baseline_difference,
            checks=['budget sum without duplicate summaries','B1 original sequence reproduces original stored outputs',
            'paired exact input prefix','same frozen task across structures','cold source and zero states',
            'six channels and physical input bounds','nonlinear geometry','original acceptance and Native/full-backend trajectory alignment',
            'secondary control independent pass','held-out coefficient selection']),
        cost_ledger=ledger,conservative_new_cost=summed,
        step_accounting=dict(persisted_confirmed_steps=summed['physics_steps']-7000-700,
            completed_radius_steps_reconstructed_from_control_flow=7000,
            original_unlogged_soft_attempt_step_range=[0,700],
            known_or_reconstructed_steps=summed['physics_steps']-700,
            conservative_upper_steps=summed['physics_steps'],failed_backend_step_calls=1,
            failed_call_internal_progress='unknown; one extra failed mj_step call, not silently counted as zero',
            interpretation='Conservative ledger charges 700 for the unlogged partial soft attempt. Repeated runs are additionally charged.'),
        shared_history=dict(search=s['historical_common_cost'],independent=s['historical_common_validation_cost']),
        paired_historical_validation=dict(acquisition=h['historical_acquisition_cost'],suffix=h['historical_separable_suffix_cost'],
            independent=h['historical_independent_cost'],before=h['before'],after=h['after']),
        a4=dict(diagnostic_steps=sum(files[k]['new_cost'].get('physics_steps',0) for k in
                ['a4_control_probes','a4_control_validation','a4_radius_raw','engineering_failure_01']),
            secondary_validation_steps=1400,control_coefficient=control['coefficient_index'],
            control_two_scale_difference=control['two_scale_relative_difference'],control_holdout=control['validation'],
            radius_two_scale_difference=float(np.linalg.norm(a-b)/np.linalg.norm(b)),
            radius_holdout=radius[1]['fixed_control']['validation'][0],
            independent_control_metrics=correction['acceptance']['metrics']),
        benchmarks=benchmarks,
        decisions=dict(prediction_accuracy='Radius locally validated; control direction useful but strict all-sample relative-error check unresolved.',
            experiment_selection='A/B/C same continuation; secondary math probe provides a concrete control correction.',
            total_net_benefit='Not demonstrated. Added math did not replace the frozen continuation or save subsequent experiments.',
            benchmark_structure_discrimination='Weak: all three fully optimized valid candidates pass; soft baseline is unsupported/numerically invalid, not an infeasibility example.'),
        recommendation=dict(priority='B3 six-tendon 0.35 s v1 as an executable conditional follow-up, not an established structure-essential benchmark.',
            task='tasks/b2_b3_six_tendon_035_v1.json',independent_witnesses=['neutral','stiff','length_exchange'],
            formal_structure_benchmark_ready=False,
            next='Verify equal optimization opportunities and control parameterization quality before any structural claim; if neutral remains readily feasible, retire this condition from structure-necessity evaluation. Do not tighten targets post hoc.'),
        tests=dict(existing_native_task_sensitivity='6 tests passed, exit 0; no integration',full_repository_suite=False),
        limitations=['No blinded prospective trial or statistical causality.','Historical and fresh wall times are separate measurements.',
            'Kernel times exclude process launch, export and some failed/recovery preparation; no end-to-end speedup ratio.',
            'No global optimum, structural impossibility, hardware or GVS fast-trajectory validity claim.'])
    # This derived delivery summary can be refreshed; immutable experiment files
    # and prior content-addressed Store artifacts remain untouched.
    reference=ARCHIVE.put_context_checkpoint(summary)
    atomic_json(OUT/'summary.json',summary)
    print(dict(summary_reference=reference))
    print({k:summary[k] for k in ['conservative_new_cost','step_accounting','recommendation']})


if __name__=='__main__':main()
