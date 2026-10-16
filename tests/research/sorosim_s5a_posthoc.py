"""Join sealed S5-A output samples without additional dynamics or physical steps."""
import hashlib
import json
from pathlib import Path
import tarfile

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'evidence/sorosim_s5a'


def run():
    summary=json.loads((BASE/'summary.json').read_text(encoding='utf8'))
    archive_path=BASE/'study/immutable_artifacts.tar.gz'
    def get(archive,ref):
        body=archive.extractfile('artifacts/'+ref['artifact_id']+'.json').read()
        if hashlib.sha256(body).hexdigest()!=ref['artifact_id']:
            raise ValueError('SEALED_ARTIFACT_HASH_MISMATCH')
        return json.loads(body)
    with tarfile.open(archive_path) as archive:
        result=get(archive,summary['result'])
        raw=get(archive,result['raw_reference'])
        source=get(archive,summary['source'])
        candidate=get(archive,summary['candidate'])
    samples=raw['samples'];math=source['mathematical_outputs'];u=source['trajectory']['tensions_n']
    task=result['profile']['task'];target=np.asarray(task['goal']['data']['target_m'])
    limits=result['acceptance']['components']
    timing=task['timing'];intervals=round(timing['duration_s']/timing['control_period_s'])
    substeps=round(timing['control_period_s']/timing['timestep_s'])
    holding_start=timing['duration_s']-candidate['configuration']['policy']['controller']['parameters']['data']['settling']['window_s']
    assert len(samples)==intervals+1 and raw['physics_steps']==intervals*substeps and len(u)==intervals
    assert result['comparison']['aligned'] and result['acceptance']==summary['acceptance']
    rows=[]
    for i,physical in enumerate(samples):
        pm=np.asarray(physical['tip_m']);vm=np.asarray(physical['tip_velocity_m_s'])
        ps=np.asarray(math['tip_positions_m'][i]);vs=np.asarray(math['tip_velocities_m_s'][i])
        expected=None if i==0 else np.asarray(u[i-1]);actual=None if i==0 else np.asarray(physical['actual_tension_n'])
        row=dict(time_s=physical['time_s'],mathematical_tip_m=ps.tolist(),physical_tip_m=pm.tolist(),
            mathematical_velocity_m_s=vs.tolist(),physical_velocity_m_s=vm.tolist(),
            mathematical_speed_m_s=float(np.linalg.norm(vs)),physical_speed_m_s=float(np.linalg.norm(vm)),
            position_difference_m=(pm-ps).tolist(),position_difference_norm_m=float(np.linalg.norm(pm-ps)),
            velocity_difference_m_s=(vm-vs).tolist(),velocity_difference_norm_m_s=float(np.linalg.norm(vm-vs)),
            expected_tension_n=None if expected is None else expected.tolist(),
            actual_tension_n=None if actual is None else actual.tolist(),
            applied_tension_error_n=None if actual is None else (actual-expected).tolist())
        if physical['time_s']>=holding_start-1e-12:
            row['holding_margins']=dict(mathematical_position_m=limits['holding_position']['limit']-float(np.linalg.norm(ps-target)),
                physical_position_m=limits['holding_position']['limit']-float(np.linalg.norm(pm-target)),
                mathematical_speed_m_s=limits['holding_speed']['limit']-float(np.linalg.norm(vs)),
                physical_speed_m_s=limits['holding_speed']['limit']-float(np.linalg.norm(vm)))
        if i:
            previous=rows[-1]
            row['divergent_start_interval_displacement_difference_m']=(
                (pm-np.asarray(previous['physical_tip_m']))-(ps-np.asarray(previous['mathematical_tip_m']))).tolist()
        rows.append(row)
    output=dict(stage='S5-A',source_result=summary['result'],source_archive_sha256=hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        status=result['status'],acceptance=result['acceptance']['status'],accepted=result['acceptance']['accepted'],
        exact_grid=True,physical_steps=raw['physics_steps'],full_samples=len(rows),
        max_applied_tension_error_n=max(float(np.max(np.abs(row['applied_tension_error_n']))) for row in rows[1:]),
        matched_one_step=dict(available=False,reason='No declared MuJoCo-to-SoRoSim state projection and matched initial-state integration in this open-loop study; interval increments start from divergent states'),
        comparison_scope='Common world tip outputs and identical applied controls; no cross-model state subtraction or causal mismatch attribution',
        samples=rows)
    from tools.state_io import atomic_json
    atomic_json(BASE/'comparison_detail.json',output)
    return output


if __name__=='__main__':
    print({k:v for k,v in run().items() if k!='samples'})
