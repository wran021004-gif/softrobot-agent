"""One sealed S5-A fixed-tension MuJoCo rollout through the research ledger."""
import hashlib
import json
from pathlib import Path
import tarfile

from schemas.platform import SessionInput
from tools.platform_store import plain
from tools.research import core
from tools.research.design import verify_candidate, numerical_binding
from tools.research.state import state, save
from tools.state_io import atomic_json, digest, read

ROOT=Path(__file__).resolve().parents[2]
S45=ROOT/'evidence/sorosim_s45'
STUDY=ROOT/'configs/research/study_sorosim_s5_open_loop.json'


def plan(action,**data):
    return dict(action=action,
        hypothesis='A mathematical Design B tension witness may or may not transfer to MuJoCo.',
        expected_observation='Complete physical trajectory, actual tensions and frozen-task acceptance.',
        weakening_observation='Model mismatch, incomplete rollout, physical task failure or invalid force delivery.',
        fixed_conditions='Exact Design B geometry, 35 tension commands, tendon order and original task.',
        stopping_condition='One open-loop physical launch and independent task evaluation.',
        interpretation='One physical rollout tests transfer; it is not NMPC, RL or robust acceptance.',**data)


def sealed(archive,reference):
    body=archive.extractfile('artifacts/'+reference['artifact_id']+'.json').read()
    if hashlib.sha256(body).hexdigest()!=reference['artifact_id']:
        raise ValueError('SEALED_S45_ARTIFACT_HASH_MISMATCH')
    return json.loads(body)


def run(directory):
    from extensions.tendon_family.sorosim_control import checked_control
    from extensions.tendon_family.sorosim_spec import SorosimModel
    from extensions.tendon_family.sorosim_session import SorosimSession

    host=core.prepare(STUDY,directory)
    if 'freeze' not in state(host):core.bind(host)
    old=read(ROOT/'evidence/sorosim_s4b/recovered_pilot/summary.json')['rows'][1]
    with tarfile.open(ROOT/'evidence/sorosim_s4b/recovered_pilot/immutable_artifacts.tar.gz') as archive:
        candidate_source=sealed(archive,old['candidate'])
    generated=core.dispatch(host,plan('generate',generation=candidate_source['parameters']),'s5a-generate-B')['result']
    candidate_ref=generated['candidate']
    candidate=verify_candidate(host,candidate_ref)
    physical=numerical_binding(candidate['configuration'],state(host)['spec'])['physical_design_identity']
    if physical!=old['physical_design_identity']:
        raise ValueError('S5A_GENERATED_CANDIDATE_DIFFERS_FROM_MATHEMATICAL_DESIGN')
    index=read(S45/'interior_summary.json')
    audit=read(S45/'posthoc_verification.json')
    source_archive=S45/'final_study/immutable_artifacts.tar.gz'
    if (hashlib.sha256(source_archive.read_bytes()).hexdigest()!=audit['source_archive_sha256'] or
            not audit['checks']['repaired_verification_passed']):
        raise ValueError('S5A_MATHEMATICAL_SOURCE_NOT_VERIFIED')
    with tarfile.open(source_archive) as archive:
        solve=sealed(archive,index['solve']['reference'])
    trajectory=solve['trajectory']
    cfg=candidate['configuration'];inp=SessionInput.model_validate(cfg)
    control=checked_control(inp)
    spec=SorosimModel(dict(basis=control.recipe.basis,
        gauss_per_interval=control.solver.gauss_per_interval)).convert(
        inp.robot.structure.data,inp.policy.discretization.data,inp.task.environment.data,solver=control.solver)
    if spec['identity']!=trajectory['model_identity'] or digest(plain(inp.task))!=trajectory['task_identity']:
        raise ValueError('S5A_MATHEMATICAL_MODEL_OR_TASK_MISMATCH')
    with SorosimSession() as session:
        session.construct(spec)
        outputs=session.evaluate('trajectory_outputs',dict(states=trajectory['states'],
            tensions_n=trajectory['tensions_n'],times_s=trajectory['times_s']))
        environment=dict(dependency=session.dependency,environment=session.environment,timings=session.timings)
    math_ref=save(host,dict(outputs=outputs,environment=environment,source=index['solve']['reference']),
        'mathematical_saved_state_outputs')
    source=save(host,dict(source_kind='verified_mathematical_trajectory',
        source_archive=str(source_archive.relative_to(ROOT)),source_archive_sha256=audit['source_archive_sha256'],
        source_solve=index['solve']['reference'],source_replay=index['independent_replay']['reference'],
        posthoc_verification=audit,trajectory=trajectory,mathematical_outputs=outputs,
        output_reference=math_ref),'s5a_exact_mathematical_source')
    result=core.dispatch(host,plan('physical_replay',physical_replay=dict(candidate=candidate_ref,source=source),
        supporting_evidence=[source,math_ref]),'s5a-open-loop-B')['result']
    summary=dict(stage='S5-A',source=source,candidate=candidate_ref,result=result['reference'],
        acceptance=result['acceptance'],comparison=result['comparison'],
        physical_launches=state(host).get('physical_replay_launches',0),
        numerical_s=state(host)['numerical_s'],provider_requests=0,rl_actions=0,nmpc_updates=0)
    summary_ref=save(host,summary,'s5a_summary')
    core.dispatch(host,plan('stop',supporting_evidence=[result['reference'],summary_ref]),'s5a-stop')
    export=core.export(host,ROOT/'evidence/sorosim_s5a/study')
    atomic_json(ROOT/'evidence/sorosim_s5a/summary.json',dict(stage='S5-A',source=source,
        candidate=candidate_ref,result=result['reference'],acceptance=result['acceptance'],
        comparison={k:v for k,v in result['comparison'].items() if k!='samples'},
        physical_launches=summary['physical_launches'],numerical_s=summary['numerical_s'],
        stage_summary_reference=summary_ref))
    return export


if __name__=='__main__':
    import sys
    print(run(Path(sys.argv[1])))
