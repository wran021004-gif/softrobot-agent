"""One S5-B SoRoSim feedback rollout through the existing research execution owner."""
import hashlib
import json
from pathlib import Path
import tarfile

from tools.research import core
from tools.research.design import numerical_binding, verify_candidate
from tools.research.state import state, save
from tools.state_io import atomic_json, read

ROOT=Path(__file__).resolve().parents[2]
STUDY=ROOT/'configs/research/study_sorosim_s5_nmpc.json'


def plan(action,**data):
    return dict(action=action,
        hypothesis='Feedback may reduce the Design B open-loop physical task error.',
        expected_observation='Actual MuJoCo trajectory and original-task acceptance after 35 SoRoSim updates.',
        weakening_observation='Incomplete updates, unusable solves, large innovations or physical task failure.',
        fixed_conditions='Same Design B geometry, frozen task, timestep, SoRoSim controller and MuJoCo backend.',
        stopping_condition='One complete budgeted NMPC launch, or its observed incomplete outcome.',
        interpretation='One offline feedback rollout; not proof of real-time control or robust success.',**data)


def run(directory):
    host=core.prepare(STUDY,directory)
    if 'freeze' not in state(host):core.bind(host)
    old=read(ROOT/'evidence/sorosim_s4b/recovered_pilot/summary.json')['rows'][1]
    with tarfile.open(ROOT/'evidence/sorosim_s4b/recovered_pilot/immutable_artifacts.tar.gz') as archive:
        body=archive.extractfile('artifacts/'+old['candidate']['artifact_id']+'.json').read()
    if hashlib.sha256(body).hexdigest()!=old['candidate']['artifact_id']:
        raise ValueError('SEALED_DESIGN_B_HASH_MISMATCH')
    parameters=json.loads(body)['parameters']
    generated=core.dispatch(host,plan('generate',generation=parameters),'s5b-generate-B')['result']
    candidate=generated['candidate']
    actual=verify_candidate(host,candidate)
    if numerical_binding(actual['configuration'],state(host)['spec'])['physical_design_identity']!=old['physical_design_identity']:
        raise ValueError('S5B_DESIGN_B_MISMATCH')
    result=core.dispatch(host,plan('execute',candidate=candidate),'s5b-feedback-B')['result']
    ref=result['reference']
    compact=dict(stage='S5-B',candidate=candidate,result=ref,status=result['status'],
        acceptance=result.get('acceptance'),controller_facts=result.get('controller_facts'),
        numerical_s=state(host)['numerical_s'],nmpc_launches=state(host).get('nmpc_launches',0),
        provider_requests=0,rl_actions=0,source_open_loop=read(ROOT/'evidence/sorosim_s5a/summary.json')['result'])
    summary=save(host,compact,'s5b_summary')
    core.dispatch(host,plan('stop',supporting_evidence=[ref,summary]),'s5b-stop')
    exported=core.export(host,ROOT/'evidence/sorosim_s5b/study')
    atomic_json(ROOT/'evidence/sorosim_s5b/summary.json',dict(compact,stage_summary_reference=summary))
    return exported


if __name__=='__main__':
    import sys
    print(run(Path(sys.argv[1])))
