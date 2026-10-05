"""Focused fixed-target semantics and scoped runtime isolation, no replay."""
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
from extensions.tendon_family import milestone5_fixed_transition as fixed
from extensions.tendon_family import gvs_trajectory as trajectory


class SuccessorChecks(unittest.TestCase):
    def test_independent_solve_preserves_fixed_recurrence_and_initial_state(self):
        model=SimpleNamespace(full_n=1,damping=np.array([[3.]]),data=SimpleNamespace(time=0.),
            model=SimpleNamespace(opt=SimpleNamespace(timestep=.0005)),motion=lambda x:{})
        state=np.array([.2,.4]);h=.0005;steps=20;a=5/(2+3*h)
        with patch.object(fixed,'forward_terms',return_value=dict(mass=np.array([[2.]]),force=np.array([5.]))):
            result=fixed.predict(model,state,[1.],deadline=float('inf'))
        np.testing.assert_array_equal(state,[.2,.4])
        np.testing.assert_allclose(result['state'],[.2+steps*h*.4+h*h*a*steps*(steps+1)/2,.4+steps*h*a],atol=1e-14)
        self.assertEqual(result['step_count'],20);self.assertEqual(result['backend_steps'],0)
        self.assertLessEqual(max(r['backward_error'] for r in result['rows']),1e-12)
        model.model.opt.timestep=.00025
        with self.assertRaisesRegex(ValueError,'FIXED_BACKEND_STEP'):fixed.predict(model,state,[1.],deadline=float('inf'))

    def test_non_spd_cannot_pass_independent_cholesky_audit(self):
        model=SimpleNamespace(full_n=1,damping=np.zeros((1,1)),model=SimpleNamespace(opt=SimpleNamespace(timestep=.0005)))
        with patch.object(fixed,'forward_terms',return_value=dict(mass=np.array([[-1.]]),force=np.array([1.]))):
            with self.assertRaises(np.linalg.LinAlgError):fixed.predict(model,[0.,0.],[1.],deadline=float('inf'))

    def test_experimental_provider_is_nested_and_exception_safe(self):
        original=object();first=object();second=object()
        with patch.object(trajectory,'functions_for',return_value=original):
            self.assertIs(trajectory.trajectory_functions(None),original)
            with trajectory.use_trajectory_functions(lambda f:first):
                self.assertIs(trajectory.trajectory_functions(None),first)
                with self.assertRaisesRegex(RuntimeError,'test'):
                    with trajectory.use_trajectory_functions(lambda f:second):
                        self.assertIs(trajectory.trajectory_functions(None),second)
                        raise RuntimeError('test')
                self.assertIs(trajectory.trajectory_functions(None),first)
            self.assertIs(trajectory.trajectory_functions(None),original)

    def test_each_feedback_command_is_sealed_before_own_advance(self):
        from contextlib import ExitStack
        from extensions.tendon_family.milestone5_feedback_runtime import history
        events=[]
        inp=SimpleNamespace(robot=SimpleNamespace(structure=SimpleNamespace(data={})),
            policy=SimpleNamespace(controller=SimpleNamespace(parameters=SimpleNamespace(data={'recipe':{'basis':{}}}))),
            task=SimpleNamespace(timing=SimpleNamespace(control_period_s=.01,duration_s=.03),goal=SimpleNamespace(data={'target_m':[0.,0.,0.]})))
        class Controller:
            def __init__(self):
                self.seed={'states':[[0.,0.]],'tensions':[[0.]]};self.workspace=SimpleNamespace(last=self.seed)
                self.observations=[];self.stop_requested=False;self.last={'plan_accepted':True}
            def configure(self,*args):pass
            def command(self,t,geometry,q,v):
                u=q[0]+1.;self.workspace.last={'states':[list(q)+list(v)],'tensions':[[u]]}
                self.seed=None;self.observations.append({'time_s':t});return [u]
        def advance(x,u,**kwargs):
            self.assertEqual(events[-1]['phase'],'sealed_before_emulated_advance')
            self.assertEqual(events[-1]['input_n'],u)
            state=np.asarray(x)+1.
            return dict(state=state.tolist(),position_m=[state[0],0.,0.],velocity_m_s=[state[1],0.,0.],
                speed_m_s=state[1],max_scaled_residual=0.,backend_equivalent_integration_steps=20,cost_s=0.)
        model=SimpleNamespace(full_n=1,motion=lambda x:{'position_m':[x[0],0.,0.]},propagate=advance)
        patches={
            'schemas.platform.SessionInput.model_validate':lambda cfg:inp,
            'extensions.tendon_family.gvs_profile.prepare_execution':lambda *args:None,
            'extensions.tendon_family.gvs_nmpc.DeadlineReachNMPCController':lambda *args:Controller(),
            'extensions.tendon_family.gvs_nmpc.resolve_gvs_nmpc_control':lambda *args:{},
            'extensions.tendon_family.gvs_basis.resolve_basis':lambda *args:None,
            'extensions.tendon_family.gvs_projection.project':lambda physics,basis,q,v:dict(q_gvs=list(q),qdot_gvs=list(v)),
            'extensions.tendon_family.diagnostic_math.charge_units':lambda *args:None}
        with ExitStack() as stack:
            for target,replacement in patches.items():stack.enter_context(patch(target,replacement))
            result=history({},[0.,0.],model,{},None,provider=lambda f:f,count=3,deadline=float('inf'),save_update=events.append)
        self.assertTrue(result['complete']);self.assertEqual(result['backend_steps'],0)
        self.assertEqual([r['input_n'] for r in result['rows']],[[1.],[2.],[3.]])
        self.assertEqual([e['phase'] for e in events],['sealed_before_emulated_advance','emulated_endpoint']*3)
        for previous,current in zip(result['rows'],result['rows'][1:]):
            self.assertEqual(current['initial_full_state'],previous['state'])
            self.assertEqual(current['warm_before_command'],previous['selected_plan'])


if __name__=='__main__':unittest.main()
