"""Focused reference, interval scoring, graph timing and owned analysis checks."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
import numpy as np
from examples.gvs_tracking import tracking_input, live_input
from extensions.tendon_family.tracking import reference_at, evaluate_tracking, CartesianReference
from schemas.platform import SessionInput, EvidenceRef, Signal, SignalSpec, BackendResult, Payload
from tools.platform_registry import registry


class TrackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value=tracking_input()
        cls.inp=SessionInput.model_validate(cls.value)

    def test_reference_endpoints_and_derivative(self):
        r=self.inp.task.goal.data
        p,v=reference_at(r,[-1,0,.2,.4,1])
        np.testing.assert_allclose(p[0],r['start_m'])
        np.testing.assert_allclose(p[-1],r['end_m'])
        np.testing.assert_allclose(v[[0,1,3,4]],0,atol=1e-14)
        eps=1e-6
        a,_=reference_at(r,.2-eps);b,_=reference_at(r,.2+eps)
        np.testing.assert_allclose((b-a)/(2*eps),v[2],atol=1e-9)
        for t in (0,.4):
            _,a=reference_at(r,t-eps);_,b=reference_at(r,t+eps)
            np.testing.assert_allclose((b-a)/(2*eps),0,atol=1e-4)
        with self.assertRaises(ValueError):CartesianReference.model_validate({**r,'interpolation':'constant'})

    def test_interval_evaluation_rejects_terminal_only_and_missing(self):
        task=self.inp.task;times=np.arange(1,41)*.01
        positions,_=reference_at(task.goal.data,times)
        spec=next(s for s in task.observations if s.name=='tip_position')
        result=BackendResult(solver_status='completed',backend_id='backend.family_mujoco',model_id='test',
            signals=[Signal(spec=spec,times_s=times.tolist(),values=positions.tolist())],data=Payload(contract='platform.empty',data={}),
            limitations=[],initial_state=Payload(contract='platform.empty',data={}),seed=0)
        result.signals.extend(Signal(spec=SignalSpec(name='tendon_tension',entity=entity,dimension=1,units='N',frame='path',phase='pre_step_solver'),
            times_s=(times-.01).tolist(),values=[[0.]]*40) for entity in task.evaluator.parameters.data['tension_limits_n'])
        def evaluate(r):return evaluate_tracking(task,r,EvidenceRef(artifact_id='0'*64),registry(),'test')
        self.assertTrue(evaluate(result).task_success)
        failed=deepcopy(result);failed.signals[0].values[10][1]+=.011
        out=evaluate(failed);self.assertFalse(out.task_success)
        self.assertEqual(out.metrics[-1].value,0)
        self.assertAlmostEqual(out.metrics[1].value,.011/np.sqrt(40))
        missing=deepcopy(result);missing.signals[0].times_s.pop(10);missing.signals[0].values.pop(10)
        self.assertEqual(evaluate(missing).validity,'incomplete')
        incomplete=result.model_copy(update={'solver_status':'failed'})
        self.assertIsNone(evaluate(incomplete).task_success)
        force_failure=deepcopy(result);force_failure.signals[1].values[0]=[9.]
        self.assertFalse(evaluate(force_failure).task_success)

    def test_same_graph_path_constant_and_absolute_moving_reference(self):
        from extensions.tendon_family.gvs_profile import candidate_numerical, load_profile
        from extensions.tendon_family.tracking import checked_tracking
        from extensions.tendon_family.gvs_trajectory import TrajectoryWorkspace
        for constant in (False,True):
            value=deepcopy(self.value)
            if constant:
                ref=value['task']['goal']['data'];ref.update(interpolation='constant',end_m=ref['start_m'])
            inp=SessionInput.model_validate(value);control=checked_tracking(inp)
            numerical=candidate_numerical(inp,control,load_profile())
            ws=TrajectoryWorkspace(inp.task,inp.robot,control.recipe,numerical['measured_initial_state'],numerical['nominal']['u0'])
            identity=ws.problem.objective_function.data['expression_digest']
            ws._set_prediction_time(.35)
            p,v=reference_at(inp.task.goal.data,.36)
            for j in range(3):
                self.assertAlmostEqual(ws.problem.variables[f'reference/position/1/{j}']['bounds'][0],p[j])
                self.assertAlmostEqual(ws.problem.variables[f'reference/velocity/1/{j}']['bounds'][0],v[j])
            ws._set_prediction_time(.4)
            np.testing.assert_allclose(ws.reference_velocities,0,atol=1e-14)
            self.assertEqual(identity,ws.problem.objective_function.data['expression_digest'])
            self.assertIsNone(ws.holding_start)

    def test_candidate_analysis_matches_direct_changed_configuration(self):
        from extensions.tendon_family.candidate_analysis import evaluate_candidate, CandidateDynamicsRequest
        from extensions.tendon_family.gvs import gvs_evaluate_tool_v2
        from extensions.tendon_family.contracts import GVSDynamicsRequestV3
        from extensions.tendon_family.candidate import apply
        from extensions.tendon_family.gvs_basis import resolve_basis
        parent=SessionInput.model_validate(live_input(self.value))
        changed=apply(deepcopy(parent),registry().parse(parent.policy.candidate_builder.parameters),{'components/near/length_m':.162})
        # An owned immutable build artifact, with an unrelated selected incumbent.
        artifacts={'node':dict(candidate_id='changed',configuration='config'),'config':changed.model_dump(mode='json')}
        state={'route':{'nodes':[dict(node_id='built',action='build',status='completed',result='node')],'current':'different'}}
        ctx=SimpleNamespace(input=parent,reg=registry(),run_id='owner',artifact=lambda ref:artifacts[ref],
            store=SimpleNamespace(session=lambda _:dict(state=state)))
        n=len(resolve_basis(changed.robot.structure.data,changed.policy.controller.parameters.data['recipe']['basis']).coordinate_order)
        args=CandidateDynamicsRequest(source_node='built',state=dict(q=[0.]*n,qdot=[0.]*n),
            input=dict(tendon_tensions_n={t['id']:0. for t in changed.robot.structure.data['tendons']}),samples_per_segment=2)
        result=evaluate_candidate(ctx,args)
        direct=gvs_evaluate_tool_v2(SimpleNamespace(input=changed,reg=ctx.reg),GVSDynamicsRequestV3(
            **args.model_dump(exclude={'source_node'}),basis=changed.policy.controller.parameters.data['recipe']['basis']))
        self.assertEqual(result.calculation,direct.model_dump(mode='json'))
        self.assertNotIn('execution_id',result.binding)
        self.assertEqual(result.binding['candidate_id'],'changed')
        self.assertAlmostEqual(result.calculation['tip']['position_m'][0],.310)
        with self.assertRaisesRegex(ValueError,'OWNED_COMPLETED_BUILD'):
            evaluate_candidate(ctx,args.model_copy(update={'source_node':'unowned'}))


if __name__=='__main__':unittest.main()
