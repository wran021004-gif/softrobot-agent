"""Bounded S4.5 study: import sealed S4 controls, cross replay, then restore feasibility."""
import hashlib
import json
import math
from pathlib import Path
import tarfile

from tools.platform_store import plain
from tools.research import core
from tools.research.design import verify_candidate, numerical_binding
from tools.research.state import save, state
from tools.state_io import atomic_json, digest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'evidence/sorosim_s4b/recovered_pilot'
STUDY = ROOT/'configs/research/study_sorosim_s45.json'


def plan(action, **data):
    return dict(action=action,
        hypothesis='The transferred tension history and feasibility restoration may meet the original sampled task.',
        expected_observation='Independent target-model dynamics and all original sampled margins.',
        weakening_observation='A sampled violation, failed integration, or incomplete optimizer convergence.',
        fixed_conditions='Frozen task, target candidate model, tendon order, time grid and input limits.',
        stopping_condition='Two cross replays and at most two complete mathematical optimizations.',
        interpretation='Local mathematical evidence; no physical acceptance or global optimum.', **data)


def import_history(host):
    summary_path=SOURCE/'summary.json'
    data=summary_path.read_bytes()
    summary=json.loads(data)
    archive=tarfile.open(SOURCE/'immutable_artifacts.tar.gz')
    rows=[]
    for i,row in enumerate(summary['rows']):
        old_ref=row['candidate']
        original=json.load(archive.extractfile('artifacts/'+old_ref['artifact_id']+'.json'))
        if digest(original)!=old_ref['artifact_id']:
            raise ValueError('S45_SEALED_CANDIDATE_HASH_MISMATCH')
        generated=core.dispatch(host,plan('generate',generation=original['parameters']),
            f"s45-generate-v{state(host)['profile']['version']}-{i}")['result']
        candidate=verify_candidate(host,generated['candidate'])
        physical=numerical_binding(candidate['configuration'],state(host)['spec'])['physical_design_identity']
        if physical!=row['physical_design_identity']:
            raise ValueError('S45_GENERATED_DESIGN_DIFFERS_FROM_SEALED_S4')
        trajectory=row['solve']['trajectory']
        if trajectory['task_identity']!=row['solve']['task_requirements']['binding']['task_identity']:
            raise ValueError('S45_HISTORICAL_TASK_IDENTITY_MISMATCH')
        source=save(host,dict(source_kind='historical_mathematical_trajectory',
            source_commit=summary['source_commit'],source_file=str(summary_path.relative_to(ROOT)),
            source_file_sha256=hashlib.sha256(data).hexdigest(),source_candidate=old_ref,
            source_solve=row['solve']['reference'],source_replay=row['replay']['reference'],
            trajectory=trajectory,original_task_passed=row['replay']['replay']['task']['original_sampled_requirements_satisfied']),
            'imported_sealed_mathematical_source')
        rows.append(dict(candidate=generated['candidate'],source=source,original=row))
    return rows


def historical_margins():
    path=SOURCE/'summary.json'
    summary=json.loads(path.read_bytes())
    reports=[]
    for row in summary['rows']:
        solve=row['solve'];replay=row['replay']['replay']
        requirements=solve['task_requirements']
        limits=requirements['physical_inputs']
        trajectory=solve['trajectory']
        declared=[(c['constraint_id'],i,requirements['time_grid_s'][i],c['radius'])
            for c in requirements['constraints'] for i in c['indices']]
        observed=replay['task']
        if len(declared)!=len(observed['squared_normalized_excess']):
            raise ValueError('S45_HISTORICAL_CONSTRAINT_COVERAGE_MISMATCH')
        samples=[]
        for (constraint_id,index,time_s,radius),name,t,gap in zip(declared,observed['constraint_ids'],
                observed['times_s'],observed['squared_normalized_excess']):
            if constraint_id!=name or abs(time_s-t)>1e-12:
                raise ValueError('S45_HISTORICAL_CONSTRAINT_ORDER_MISMATCH')
            value=radius*math.sqrt(max(0.,1.+gap))
            samples.append(dict(constraint_id=name,index=index,time_s=time_s,limit=radius,
                observed_norm=value,signed_margin=radius-value,normalized_signed_margin=1.-value/radius,
                squared_normalized_excess=gap))
        u=trajectory['tensions_n']
        if (len(u)!=35 or len(trajectory['times_s'])!=36 or
            any(len(command)!=len(limits['upper']) for command in u)):
            raise ValueError('S45_HISTORICAL_TRAJECTORY_INCOMPLETE')
        bounds_ok=all(lo<=value<=hi for command in u for value,lo,hi in zip(command,limits['lower'],limits['upper']))
        reports.append(dict(length_m=row['length_m'],source_solve=solve['reference'],source_replay=row['replay']['reference'],
            design_identity=trajectory['design_identity'],task_identity=trajectory['task_identity'],
            samples=samples,max_original_normalized_violation=max(0.,*[-v['normalized_signed_margin'] for v in samples]),
            terminal_position_error_m=samples[0]['observed_norm'],
            holding_max_position_error_m=max(v['observed_norm'] for v in samples if v['constraint_id']=='holding_max_error_m'),
            holding_max_speed_m_s=max(v['observed_norm'] for v in samples if v['constraint_id']=='holding_max_speed_m_s'),
            input_min_n=min(map(min,u)),input_max_n=max(map(max,u)),input_bounds_pass=bounds_ok,
            time_grid_complete=all(abs(t-i*requirements['sample_period_s'])<1e-12 for i,t in enumerate(trajectory['times_s'])),
            solver_converged=solve['mathematical_facts']['converged'],solver_exitflag=solve['mathematical_facts']['exitflag'],
            relaxed_feasible=solve['mathematical_facts']['relaxed_feasible'],
            independent_replay_passed=replay['passed'],independent_scaled_violation=replay['independent_scaled_violation'],
            reintegrated_scaled_state_error=replay['reintegrated_scaled_state_error'],
            force_residual_max_nm2=replay['force_residual_max_nm2'],
            original_sampled_requirements_pass=all(v['signed_margin']>=0 for v in samples),
            physical_acceptance='unmeasured'))
    return dict(source_file=str(path.relative_to(ROOT)),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        method='Independent arithmetic from immutable replay squared-normalized excess and frozen translated radii; no new integration',
        reports=reports)


def check_derivatives():
    from extensions.tendon_family.sorosim_codesign import calculate
    summary=json.loads((SOURCE/'summary.json').read_bytes())
    row=summary['rows'][1]
    with tarfile.open(SOURCE/'immutable_artifacts.tar.gz') as archive:
        candidate=json.load(archive.extractfile('artifacts/'+row['candidate']['artifact_id']+'.json'))
    request=dict(configuration=candidate['configuration'],design_candidate=row['candidate'],operation='solve',
        warm_trajectory=row['solve']['trajectory'],check_only=True,
        arguments=dict(substeps=1,initialization='saved_candidate_trajectory',
            objective_mode='maximum_original_violation',position_weight=1.,speed_weight=1.,secondary_coefficient=0.))
    result=calculate(request)
    if result['objective_relative_error']>=2e-4 or result['constraint_relative_error']>=2e-4:
        raise ValueError('S45_FEASIBILITY_DERIVATIVE_CHECK_FAILED')
    atomic_json(ROOT/'evidence/sorosim_s45/derivative_checks.json',result)
    return result


def run(directory):
    host=core.prepare(STUDY,directory)
    if 'freeze' not in state(host):core.bind(host)
    margins=historical_margins()
    margin_ref=save(host,margins,'s45_historical_original_margins')
    atomic_json(ROOT/'evidence/sorosim_s45/historical_margins.json',margins)
    rows=import_history(host)
    results=[]
    for target,source,label in ((0,1,'A_with_U_B'),(1,0,'B_with_U_A')):
        key='s45-cross-'+label
        prior=host.store.lookup(host.run_id,key)
        if prior and prior['receipt']:
            result=host.store.artifact(json.loads(prior['receipt'])['output'])['result']
        else:
            result=core.dispatch(host,plan('cross_replay',cross_replay=dict(
                candidate=rows[target]['candidate'],source=rows[source]['source']),
                supporting_evidence=[rows[source]['source']]),key)['result']
        results.append(dict(label=label,target=result.get('design_candidate',rows[target]['candidate']),
            source=result.get('source_reference',rows[source]['source']),result=result))
        print(label,result.get('replay',{}).get('task',{}).get('original_sampled_requirements_satisfied'),flush=True)
    optimize=core.dispatch(host,plan('mechanics',mechanics=dict(candidate=rows[1]['candidate'],
        warm_source=rows[1]['source'],initialization='saved_candidate_trajectory',substeps=1,
        objective_mode='maximum_original_violation',position_weight=1.,speed_weight=1.,secondary_coefficient=0.),
        supporting_evidence=[rows[1]['source']]),'s45-restore-B')['result']
    replay=None
    if optimize.get('trajectory'):
        replay=core.dispatch(host,plan('replay',mechanics_source=optimize['reference'],
            supporting_evidence=[optimize['reference']]),'s45-restore-B-replay')['result']
    original_feasible=bool(replay and replay.get('replay',{}).get('passed') and
        replay['replay']['task']['original_sampled_requirements_satisfied'])
    summary=dict(stage='S4.5',historical_source=str(SOURCE.relative_to(ROOT)),historical_margins=margin_ref,cross_replays=results,
        feasibility_solve=optimize,independent_replay=replay,
        counts={k:state(host).get(k,0) for k in ('offline_nlp','bdf_replays','numerical_s')},
        original_mathematical_feasibility='verified' if original_feasible else 'feasibility_unresolved',
        physical_acceptance='unmeasured')
    summary_ref=save(host,summary,'s45_stage_summary')
    if original_feasible:
        citations=[r['result']['reference'] for r in results]+[optimize['reference'],replay['reference']]
        core.dispatch(host,plan('stop',supporting_evidence=citations+[summary_ref]),'s45-stop')
    export=core.export(host,ROOT/'evidence/sorosim_s45/attempt01')
    atomic_json(ROOT/'evidence/sorosim_s45/summary.json',summary)
    return export


if __name__=='__main__':
    import sys
    print(check_derivatives() if sys.argv[1]=='--check' else run(Path(sys.argv[1])))
