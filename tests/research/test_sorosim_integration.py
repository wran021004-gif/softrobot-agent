"""Bounded real MuJoCo worker through the existing backend and task evaluator."""
from pathlib import Path
import os
import sys
import time
import unittest
import numpy as np

from test_sorosim_contract import ROOT,final_candidate
from test_sorosim_nmpc import prepare_controller
from tools.state_io import read,atomic_json,digest
from tools.platform_store import plain
from tools.platform_registry import registry


def worker(destination,limit):
    from tools.service_execution import contain_worker_children
    job=contain_worker_children()  # Must precede Engine/native startup.
    inp,source=final_candidate();reg=registry();started=time.perf_counter()
    folder=destination.parent/'closed_loop_raw'
    if folder.exists():raise ValueError('PRESERVE_EXISTING_EXECUTION')
    folder.mkdir(parents=True)
    controller=prepare_controller(inp,folder)
    backend=reg.get(inp.policy.backend.extension_id,inp.policy.backend.version,'backend').resolve()()
    backend.engineering_control_update_limit=limit
    try:
        backend.compile(inp,reg)
        initializer,parameters=reg.bind(inp.task.initializer,'initializer')
        initial=initializer.resolve()(parameters,inp.seed)
        backend.initialize(initial,controller)
        result=backend.run(folder,None)
        observations=controller.observations
    finally:
        shutdown=time.perf_counter();backend.close();shutdown_s=time.perf_counter()-shutdown
    # Invoke the original frozen evaluator with the original 0.35 s task.
    evaluator,parameters=reg.bind(inp.task.evaluator,'evaluator')
    with controller.validation_store.transaction() as db:
        result_reference=controller.validation_store.put(db,result)
    task_evaluation=evaluator.resolve()(inp.task,result,
        result_reference,reg,digest(inp.task.model_dump(mode='json')))
    from extensions.tendon_family.gvs_reporting import aligned_predictions
    import gzip,json
    with gzip.open(folder/'trajectory.json.gz','rt',encoding='utf8') as f:rows=json.load(f)
    from extensions.tendon_family.gvs_reporting import reconstruct_motion
    files={p.name:p.read_bytes() for p in folder.iterdir() if p.is_file()}
    motion,_=reconstruct_motion(files,rows,inp.task.goal.data['target_m'])
    comparisons,missing=aligned_predictions(rows,observations,motion)
    from extensions.tendon_family.gvs_reporting import summarize
    from tools.research_tasks import assemble_acceptance
    evaluation=task_evaluation.model_dump(mode='json')
    profile=summarize(inp.task,result.model_dump(mode='json'),evaluation,rows,observations,motion,
        controller.limits,controller.plan['settling'])
    acceptance=assemble_acceptance(inp,evaluation,profile,motion=motion)
    with controller.validation_store.transaction() as db:
        evidence_references=dict(result=plain(controller.validation_store.put(db,result)),
            evaluation=plain(controller.validation_store.put(db,task_evaluation)),
            profile=plain(controller.validation_store.put(db,profile)),
            acceptance=plain(controller.validation_store.put(db,acceptance)))
    value=dict(stage='S3_short_closed_loop',source=source,updates=len(observations),limit=limit,
        observations=observations,rows=rows,result=result.model_dump(mode='json'),
        independent_task_evaluation=task_evaluation.model_dump(mode='json') if hasattr(task_evaluation,'model_dump') else task_evaluation,
        profile=profile,acceptance=acceptance,evidence_references=evidence_references,
        task_identity=digest(inp.task.model_dump(mode='json')),original_duration_s=inp.task.timing.duration_s,
        matlab_environment=controller.session.environment,timings=controller.session.timings,
        worker_shutdown_s=shutdown_s,worker_total_s=time.perf_counter()-started,
        predictions= (comparisons,missing),
        scope='At most five updates; deliberately incomplete original task; no task success claim')
    atomic_json(destination,value)


def launch(destination,limit=3):
    from tools.service_execution import _run_contained
    destination=Path(destination).resolve()
    if destination.exists():raise ValueError('PRESERVE_EXISTING_EVIDENCE')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.with_suffix('.log').open('w',encoding='utf8') as log:
        done=_run_contained([sys.executable,'-X','faulthandler','-m','test_sorosim_integration','worker',str(destination),str(limit)],log,None)
    atomic_json(destination.with_suffix('.boundary.json'),dict(returncode=done.returncode,
        termination_confirmed=True,engineering_update_limit=limit))
    if done.returncode:raise RuntimeError(f'Contained worker failed: {done.returncode}; inspect {destination.with_suffix(".log").name}')
    return read(destination)


def verify(e):
    assert 2<=e['updates']<=5
    assert e['original_duration_s']==.35
    calls=e['timings']['calls']
    assert sum(c['operation']=='environment' for c in calls)==1
    assert sum(c['operation']=='construct' for c in calls)==1
    assert sum(c['operation']=='nmpc' for c in calls)==e['updates']
    observations=e['observations']
    assert any(o['plan_accepted'] for o in observations)
    for o in observations:
        facts=o['mathematical_facts']
        assert facts is not None
        np.testing.assert_allclose(facts['initial_state'],o['measured_initial_state'],atol=1e-12)
        if o['plan_accepted']:assert facts['constraint_violation']<=1e-5
        assert all(0<=t<=8 for t in o['actual_tension_n'])
    assert np.linalg.norm(np.array(observations[1]['measured_initial_state'])-observations[0]['measured_initial_state'])>1e-8
    assert e['result']['data']['data']['reason']=='ENGINEERING_CONTROL_UPDATE_LIMIT'
    assert e['result']['solver_status']!='completed'
    # Incomplete task evidence must never be promoted to accepted task success.
    assert e['independent_task_evaluation']['task_success'] is None
    assert e['acceptance']['accepted'] is not True


class IntegrationTests(unittest.TestCase):
    def test_registered_real_candidate_path(self):
        from tools.platform_validation import validate_arguments
        from extensions.tendon_family.scene import assemble
        from extensions.tendon_family.backends import physics_for,MujocoBackend
        inp,_=final_candidate();r=registry();definition,parameters=r.bind(inp.policy.controller,'controller')
        definition.hook('route_applicability')(inp)
        backend,parameters=r.bind(inp.policy.backend,'backend')
        MujocoBackend.check(inp,parameters,None)
        scene=assemble(inp,physics_for(inp))
        self.assertEqual(scene['control']['mode'],'sorosim_nmpc')
        self.assertEqual(scene['duration_s'],.35)
        self.assertEqual(scene['control']['effective_parameters']['horizon'],10)

    def test_real_short_loop(self):
        p=ROOT/'evidence/sorosim_control/s3_closed_loop.json'
        if not p.exists():self.skipTest('Real short loop not yet recorded')
        verify(read(p))


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='worker':
        worker(Path(sys.argv[2]),int(sys.argv[3]))
    else:
        p=os.environ.get('SOROSIM_S3_CLOSED_LOOP')
        if p:verify(launch(p))
        unittest.main()
