"""Two bounded PPO routes and independent task evaluations on exact Design B."""
import hashlib
import json
from pathlib import Path
import tarfile
import time

from tools.research import core, rl
from tools.research.design import numerical_binding,verify_candidate
from tools.research.state import state,save
from tools.state_io import atomic_json,read

ROOT=Path(__file__).resolve().parents[2]
STUDY=ROOT/'configs/research/study_sorosim_s5_rl.json'


def sealed(archive,reference):
    body=archive.extractfile('artifacts/'+reference['artifact_id']+'.json').read()
    if hashlib.sha256(body).hexdigest()!=reference['artifact_id']:
        raise ValueError('SEALED_SOURCE_HASH_MISMATCH')
    return json.loads(body)


def plan(action,**data):
    return dict(action=action,
        hypothesis='Candidate-bound direct or residual PPO may reduce Design B physical task error.',
        expected_observation='Published checkpoint, actual training actions and independent original-task evaluation.',
        weakening_observation='No valid checkpoint, incomplete episode, task failure or ineffective residual change.',
        fixed_conditions='Exact Design B geometry, four SI tendon channels, frozen task and MuJoCo backend.',
        stopping_condition='At most one 32768-action stage and one independent evaluation per route.',
        interpretation='Training reward and checkpoint publication alone do not establish task acceptance.',**data)


def route(host,candidate,mode,reference=None):
    request=dict(operation='start',candidate=candidate,mode=mode,allocation=dict(actions=32768),
        rationale='Bounded '+mode+' PPO pilot on exact Design B; assess only by independent task evaluation')
    if reference is not None:request['reference']=reference
    started=rl.dispatch(host,request,'s5rl-'+mode+'-start')
    run_id=started['run_id']
    while rl.reconcile(host,run_id,lightweight=True)['worker_alive']:
        time.sleep(5)
    terminal=rl.dispatch(host,dict(operation='status',run_id=run_id,
        rationale='Record terminal actual actions, PPO updates and checkpoint'), 's5rl-'+mode+'-terminal')
    summary_ref=terminal['training_summary_reference']
    summary=core.read_evidence(host,dict(reference=summary_ref))
    result=dict(mode=mode,run_id=run_id,training_summary=summary_ref,
        actual_actions=summary['consumed']['attempted_actions'],status=summary['status'])
    checkpoint=(summary.get('checkpoint') or {}).get('generation')
    if checkpoint and summary['checkpoint'].get('policy_present'):
        evaluation=rl.dispatch(host,dict(operation='evaluate',run_id=run_id,checkpoint=checkpoint,
            rationale='Independent original-task episode of exact published '+mode+' policy'),
            's5rl-'+mode+'-evaluate')
        result['evaluation']=evaluation['reference']
        result['evaluation_facts']=core.read_evidence(host,dict(reference=evaluation['reference']))
    else:
        result['evaluation']='unavailable_no_published_checkpoint'
    return result


def run(directory):
    host=core.prepare(STUDY,directory)
    if 'freeze' not in state(host):core.bind(host)
    old=read(ROOT/'evidence/sorosim_s4b/recovered_pilot/summary.json')['rows'][1]
    with tarfile.open(ROOT/'evidence/sorosim_s4b/recovered_pilot/immutable_artifacts.tar.gz') as archive:
        params=sealed(archive,old['candidate'])['parameters']
    candidate=core.dispatch(host,plan('generate',generation=params),'s5rl-generate-B')['result']['candidate']
    current=verify_candidate(host,candidate)
    if numerical_binding(current['configuration'],state(host)['spec'])['physical_design_identity']!=old['physical_design_identity']:
        raise ValueError('S5RL_DESIGN_B_MISMATCH')
    s5a=read(ROOT/'evidence/sorosim_s5a/summary.json')
    archive_path=ROOT/'evidence/sorosim_s5a/study/immutable_artifacts.tar.gz'
    with tarfile.open(archive_path) as archive:
        source=sealed(archive,s5a['source'])
    if hashlib.sha256(archive_path.read_bytes()).hexdigest()!=read(ROOT/'evidence/sorosim_s5a/comparison_detail.json')['source_archive_sha256']:
        raise ValueError('S5A_ARCHIVE_CHANGED')
    source_ref=save(host,source,'imported_sealed_s45_mathematical_source')
    relation=rl.import_mathematical_reference(host,candidate,source_ref)
    compatible=rl.compatible_references(host)
    matching=[v for v in compatible if v.get('available') and v['source']==source_ref and v['candidate']==candidate]
    if len(matching)!=1:raise ValueError('EXACT_RESIDUAL_REFERENCE_NOT_ADMITTED')
    direct=route(host,candidate,'direct')
    results=[direct]
    if not state(host).get('success_gate'):
        results.append(route(host,candidate,'residual',matching[0]['reference']))
    citations=[r for row in results for r in (row['training_summary'],row['evaluation']) if isinstance(r,dict)]
    summary=dict(stage='S5-RL',candidate=candidate,source=source_ref,reference_relation=relation,
        reference=matching[0],routes=results,allocation_actions_per_route=32768,
        provider_requests=0,physical_launches=host.store.remaining()['used']['backend_solves'],
        ledger=host.store.remaining(),stage_usage=rl.allocation_feedback(host))
    summary_ref=save(host,summary,'s5rl_stage_summary')
    core.dispatch(host,plan('stop',next_step='stop',supporting_evidence=[*citations,summary_ref]),'s5rl-stop')
    exported=core.export(host,ROOT/'evidence/sorosim_s5rl/study')
    atomic_json(ROOT/'evidence/sorosim_s5rl/summary.json',dict(summary,stage_summary_reference=summary_ref))
    return exported


if __name__=='__main__':
    import sys
    print(run(Path(sys.argv[1])))
