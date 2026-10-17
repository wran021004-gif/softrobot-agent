"""Independent open-loop transfer and one controlled earlier-braking NMPC trial."""
import json
from pathlib import Path
import tarfile

import numpy as np
from tests.research.sorosim_s56_refinement import initialize,finish,plan
from tests.research.sorosim_s5t_pilot import sealed
from tools.research import core
from tools.research.feedback import experiment_preflight
from tools.research.state import state,save
from tools.state_io import atomic_json,read

ROOT=Path(__file__).resolve().parents[2]


def run():
    host,candidate,old_source=initialize('s56_physics')
    codesign=read(ROOT/'evidence/sorosim_s56/codesign/summary.json')
    summary=dict(stage='S5.6-C',source_freeze=state(host)['freeze'],candidate=candidate,
        codesign_summary='evidence/sorosim_s56/codesign/summary.json',open_loop=None,nmpc=None)
    if codesign.get('physical_source'):
        with tarfile.open(ROOT/'evidence/sorosim_s56/codesign/study/immutable_artifacts.tar.gz') as archive:
            source=sealed(archive,codesign['physical_source'])
        old=host.store.artifact(old_source)
        change=float(np.linalg.norm(np.asarray(source['trajectory']['tensions_n'])-old['trajectory']['tensions_n']))
        reference=save(host,source,'new_independent_mathematical_source')
        preflight=experiment_preflight(host,candidate,'fixed_tension',source_ref=reference)
        summary.update(control_change_norm_n=change,open_loop_preflight=preflight)
        if change>1e-6 and preflight['admitted']:
            result=core.dispatch(host,plan('physical_replay',physical_replay=dict(candidate=candidate,source=reference)),
                's56-open-loop')['result']
            summary['open_loop']=result['reference']
            summary['open_loop_facts']={k:result.get(k) for k in ('status','acceptance','comparison','profile','charged_numerical_s')}
        else:summary['open_loop_blocker']='equivalent commands or unresolved scientific novelty'
    else:summary['open_loop_blocker']='No complete independently integrated new control sequence from P2'
    atomic_json(host.store.root/'partial_summary.json',summary)
    # Change exactly one controller factor. Predictor fidelity remains explicitly limited.
    preflight=experiment_preflight(host,candidate,'nmpc')
    summary['nmpc_preflight']=preflight
    if preflight['admitted']:
        result=core.dispatch(host,plan('execute',candidate=candidate),'s56-earlier-braking')['result']
        summary.update(nmpc=result['reference'],nmpc_facts={k:result.get(k) for k in
            ('status','acceptance','controller_facts','execution','profile')})
    else:summary['nmpc_blocker']='scientific equivalence preflight withheld the controller'
    summary.update(numerical_s=state(host)['numerical_s'],nmpc_launches=state(host).get('nmpc_launches',0),
        physical_launches=host.store.remaining()['used']['backend_solves'],provider_requests=0,ppo_actions=0,
        intervention='holding_brake_lead_s 0 to .02; all other controller factors fixed',
        scope='offline computation; one-substep predictor is numerically limited; no real-time or robustness claim')
    finish(host,summary,'evidence/sorosim_s56/physics')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('open_loop_facts','nmpc_facts')}),flush=True)


if __name__=='__main__':run()
