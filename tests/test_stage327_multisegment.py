"""Solve-free checks for the frozen two-segment reference and public evaluator."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
import numpy as np
from examples.gvs_tracking import multisegment_input
from extensions.tendon_family.tracking import reference_at, evaluate_tracking, checked_tracking
from extensions.tendon_family.gvs_trajectory import TrajectoryWorkspace
from schemas.platform import SessionInput, EvidenceRef, Signal, SignalSpec, BackendResult, Payload
from tools.platform_registry import registry


class MultisegmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline=json.loads(Path('runs/stage326_gvs_kernel_efficiency_20260928/confirmation_input.json').read_text())
        cls.value=multisegment_input(cls.baseline)
        cls.inp=SessionInput.model_validate(cls.value)

    def test_endpoints_derivatives_and_clamps(self):
        r=self.inp.task.goal.data
        p,v=reference_at(r,[-1,0,.4,.7,1])
        np.testing.assert_allclose(p,[r['start_m'],*[k['position_m'] for k in r['knots']],r['end_m']])
        np.testing.assert_allclose(v,0,atol=1e-14)
        eps=1e-6
        for t in (.2,.55):
            a,_=reference_at(r,t-eps);b,_=reference_at(r,t+eps)
            _,velocity=reference_at(r,t)
            np.testing.assert_allclose((b-a)/(2*eps),velocity,atol=1e-9)
        p,v=reference_at(r,[.4-eps,.4,.4+eps])
        np.testing.assert_allclose(p,np.tile(r['knots'][1]['position_m'],(3,1)),atol=1e-12)
        np.testing.assert_allclose(v,0,atol=1e-10)
        np.testing.assert_allclose(np.diff(v,axis=0)/eps,0,atol=1e-4)
        self.assertEqual(self.value['robot'],self.baseline['robot'])
        self.assertEqual(self.value['policy'],self.baseline['policy'])
        checked_tracking(self.inp)

    def test_legacy_reference_compatibility(self):
        r=deepcopy(self.baseline['task']['goal']['data'])
        p,v=reference_at(r,.2)
        np.testing.assert_allclose(p,(np.array(r['start_m'])+r['end_m'])/2)
        np.testing.assert_allclose(v,1.875*(np.array(r['end_m'])-r['start_m'])/.4)
        r.update(interpolation='constant',end_m=r['start_m'])
        p,v=reference_at(r,[-1,.2,1])
        np.testing.assert_allclose(p,np.tile(r['start_m'],(3,1)))
        np.testing.assert_allclose(v,0)
        self.assertEqual(type(registry().parse(self.inp.task.goal)).__name__,'CartesianReferenceV2')

    def test_absolute_prediction_schedule_preserves_workspace(self):
        # Exercise the real bound-update method, without constructing or solving a graph.
        problem=SimpleNamespace(variables={f'reference/{quantity}/{k}/{j}':{} for quantity in ('position','velocity') for k in range(1,11) for j in range(3)},initial_guess={})
        solver=object();warm=object()
        ws=SimpleNamespace(tracking=True,reference=self.inp.task.goal.data,parameters=SimpleNamespace(horizon=10,substeps=1),period=.01,problem=problem,solver=solver,warm=warm)
        for elapsed in (.35,.4,.65,.7):
            schedule=TrajectoryWorkspace._set_prediction_time(ws,elapsed)
            times=elapsed+np.arange(11)*.01
            p,v=reference_at(ws.reference,times)
            np.testing.assert_allclose(schedule['node_times_s'],times)
            for k in range(1,11):
                for j in range(3):
                    self.assertAlmostEqual(problem.variables[f'reference/position/{k}/{j}']['bounds'][0],p[k,j])
                    self.assertAlmostEqual(problem.variables[f'reference/velocity/{k}/{j}']['bounds'][0],v[k,j])
            self.assertIs(ws.problem,problem);self.assertIs(ws.solver,solver);self.assertIs(ws.warm,warm)
        np.testing.assert_allclose(ws.reference_velocities,0)

    def test_all_70_samples_and_unique_knot_rms(self):
        task=self.inp.task;times=np.arange(1,71)*.01
        positions,_=reference_at(task.goal.data,times)
        result=BackendResult(solver_status='completed',backend_id='backend.family_mujoco',model_id='synthetic',
            signals=[Signal(spec=task.observations[0],times_s=times.tolist(),values=positions.tolist())],
            data=Payload(contract='platform.empty',data={}),limitations=[],initial_state=Payload(contract='platform.empty',data={}),seed=0)
        result.signals.extend(Signal(spec=SignalSpec(name='tendon_tension',entity=e,dimension=1,units='N',frame='path',phase='pre_step_solver'),
            times_s=(times-.01).tolist(),values=[[0.]]*70) for e in task.evaluator.parameters.data['tension_limits_n'])
        def evaluate(r):return evaluate_tracking(task,r,EvidenceRef(artifact_id='0'*64),registry(),'synthetic')
        self.assertTrue(evaluate(result).task_success)
        for index in (0,39):
            failed=deepcopy(result);failed.signals[0].values[index][1]+=.011
            out=evaluate(failed)
            self.assertFalse(out.task_success);self.assertEqual(out.metrics[-1].value,0)
            self.assertAlmostEqual(out.metrics[1].value,.011/np.sqrt(70))
        missing=deepcopy(result);missing.signals[0].times_s.pop(39);missing.signals[0].values.pop(39)
        self.assertEqual(evaluate(missing).validity,'incomplete')


if __name__=='__main__':unittest.main()
