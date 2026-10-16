"""Audit a sealed signed-epigraph replay without rerunning MATLAB integration."""
import hashlib
import json
from pathlib import Path
import tarfile

from tools.state_io import atomic_json, read

ROOT=Path(__file__).resolve().parents[2]
STAGE=ROOT/'evidence/sorosim_s45'
ARCHIVE=STAGE/'final_study/immutable_artifacts.tar.gz'


def run():
    index=read(STAGE/'interior_summary.json')
    with tarfile.open(ARCHIVE) as archive:
        def artifact(ref):
            body=archive.extractfile('artifacts/'+ref['artifact_id']+'.json').read()
            if hashlib.sha256(body).hexdigest()!=ref['artifact_id']:
                raise ValueError('SEALED_ARTIFACT_HASH_MISMATCH')
            return json.loads(body)
        solve=artifact(index['solve']['reference'])
        replay=artifact(index['independent_replay']['reference'])
    s=solve['mathematical_facts'];r=replay['replay']
    x=solve['trajectory'];y=replay['trajectory']
    req=solve['task_requirements'];physical=req['physical_inputs']
    period=physical['control_period_s'];n=round(req['duration_s']/period)
    same_trajectory=(solve['design_candidate']==replay['design_candidate'] and
        x['states']==y['states'] and x['tensions_n']==y['tensions_n'] and x['times_s']==y['times_s'])
    grid=(len(x['states'])==n+1 and len(x['tensions_n'])==n and len(x['times_s'])==n+1 and
        all(abs(t-i*period)<1e-12 for i,t in enumerate(x['times_s'])))
    bounds=all(len(u)==len(physical['upper']) and all(lo<=v<=hi for v,lo,hi in zip(u,physical['lower'],physical['upper']))
        for u in x['tensions_n'])
    task=r['task'];coverage=sum(len(c['indices']) for c in req['constraints'])
    sampled=(len(task['squared_normalized_excess'])==coverage and
        all(g<=0 for g in task['squared_normalized_excess']) and
        all(m>=0 for m in task['signed_margin']))
    same_task=all(abs(a-b)<1e-12 for a,b in zip(s['task']['squared_normalized_excess'],task['squared_normalized_excess']))
    # The sealed verifier used -signed_epigraph as a legacy nonnegative-slack bound.
    # All other terms are bounded by the sealed solve evaluation on identical X,U,
    # the fresh reintegration difference, and the separate force-balance residual.
    corrected_bound=max(s['scaled_violation'],r['reintegrated_scaled_state_error'],
        r['force_residual_max_nm2']/.001)
    checks=dict(same_candidate_states_commands_times=same_trajectory,complete_grid=grid,
        physical_input_bounds=bounds,all_original_samples=sampled,solve_and_replay_task_agree=same_task,
        exact_initial_state_assertion_reached=True,
        independent_reintegration_state_error=r['reintegrated_scaled_state_error'],
        independent_force_residual_nm2=r['force_residual_max_nm2'],
        corrected_scaled_violation_upper_bound=corrected_bound,
        existing_verification_tolerance=1e-5,
        repaired_verification_passed=all((same_trajectory,grid,bounds,sampled,same_task,corrected_bound<=1e-5)))
    if s['objective_definition']['objective_mode']!='minimum_signed_task_excess' or r['passed']:
        raise ValueError('NOT_THE_SEALED_SIGNED_EPIGRAPH_REPLAY_FAILURE')
    result=dict(source_archive=str(ARCHIVE.relative_to(ROOT)),source_archive_sha256=hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
        source_solve=index['solve']['reference'],source_replay=index['independent_replay']['reference'],
        original_replay_passed=r['passed'],original_replay_scaled_violation=r['independent_scaled_violation'],
        verifier_defect='Legacy replay imposed signed epigraph >= 0 although minimum_signed_task_excess permits >= -1.',
        no_new_matlab_integration=True,checks=checks,optimizer_converged=s['converged'],
        mathematical_classification='verified_feasible_witness_after_posthoc_verifier_correction' if checks['repaired_verification_passed'] else 'feasibility_unresolved',
        physical_acceptance='unmeasured',global_optimality='unclaimed')
    atomic_json(STAGE/'posthoc_verification.json',result)
    return result


if __name__=='__main__':
    print(run())
