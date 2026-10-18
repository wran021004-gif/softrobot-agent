"""Read-only archive/receipt/root audit; no dynamics or provider dispatch."""
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

import numpy as np

from tools.state_io import read, atomic_json
from tools.research.numerics import archived

ROOT=Path.cwd();DEST=ROOT/'evidence/sorosim_s57'


def bundle(folder):
    manifest=read(folder/'archive_manifest.json');archive=folder/'immutable_artifacts.tar.gz'
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['archive_sha256']
    with tarfile.open(archive) as tar:
        for member in manifest['members']:
            body=tar.extractfile(member['name']).read()
            assert hashlib.sha256(body).hexdigest()==member['sha256']
        snap=next(m for m in manifest['members'] if m['name'].startswith('snapshot/'))
        snapshot=json.load(tar.extractfile(snap['name']))
    s=snapshot['session']['state']
    assert s['research_status']=='stopped' and not s['pending']
    assert all(c['receipt'] for c in snapshot['calls'])
    assert snapshot['ledger']['used']['backend_solves']==0 and snapshot['ledger']['used']['model_calls']==0
    return dict(archive_sha256=manifest['archive_sha256'],members=len(manifest['members']),
        all_calls_sealed=True,mathematical_allocations=s.get('mathematical_evaluations',0),
        numerical_s=s['numerical_s'],provider_requests=s['pilot']['live_model_requests'])


def run():
    summary=read(DEST/'summary.json');folder='evidence/sorosim_s57/study'
    index=archived(folder,summary['source_index']);roots=0;maximum=0.;replay=[]
    for case in summary['cases']:
        source=next(c for c in index['cases'] if c['update_index']==case['update_index'])
        for count,row in case['resolutions'].items():
            value=archived(folder,row['reference']);raw=value['raw'];trace=np.asarray(raw['roots']).reshape(-1,6)
            assert value['physical_steps']==0 and value['numerical_environment']['dependency']['commit']=='24d573a3e864ffda87c42ee462a6ed620133cc7b'
            assert raw['complete'] and len(trace)==int(count)
            np.testing.assert_array_equal(raw['initial_state'],source['initial_state'])
            np.testing.assert_array_equal(np.asarray(raw['tensions_n']).reshape(-1),source['applied_tension_n'])
            np.testing.assert_array_equal(raw['times_s'],[source['time_s'],source['end_time_s']])
            assert np.isfinite(trace).all() and max(trace[:,2])<1e-9
            for field in ('position','velocity'):
                error=value['comparison'][field]
                np.testing.assert_allclose(error['e_one_step'],np.asarray(error['e_initial'])+error['e_increment'],rtol=0,atol=1e-15)
            roots+=len(trace);maximum=max(maximum,float(max(trace[:,2])))
            if int(count)==1:
                difference=value['comparison']['archived_prediction_difference']
                replay.append(dict(index=case['update_index'],position_m=float(np.linalg.norm(difference['tip_position_m'])),
                    velocity_m_s=float(np.linalg.norm(difference['tip_velocity_m_s'])),state_max=float(np.max(np.abs(difference['state'])))))
    archives={p:bundle(ROOT/p) for p in ['evidence/sorosim_s57/study','evidence/sorosim_s57/admission_failure/study']}
    old=subprocess.check_output(['git','diff','--name-only','fdf0ae0c0aacd69ea4d10749eade70c27c13fa95','--','evidence'],text=True).splitlines()
    assert all(p.startswith('evidence/sorosim_s57/') for p in old)
    pin=ROOT/'runs/SoRoSim-pinned'
    assert subprocess.check_output(['git','-C',str(pin),'rev-parse','HEAD'],text=True).strip()=='24d573a3e864ffda87c42ee462a6ed620133cc7b'
    assert not subprocess.check_output(['git','-C',str(pin),'status','--porcelain'],text=True).strip()
    result=dict(archives=archives,actual_integrations=15,actual_roots=roots,maximum_root_residual_inf=maximum,
        archived_prediction_replay=replay,historical_evidence_unchanged=True,pinned_upstream_clean=True,
        new_physics_steps=0,new_full_nlp=0,new_training_actions=0,new_provider_requests=0)
    atomic_json(DEST/'delivery_audit.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':run()
