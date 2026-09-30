"""Focused deterministic task-time analysis boundary checks."""
import importlib.metadata
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4

import numpy as np

from examples.offline_math_analysis import verification_acceptance
from examples.platform_fixtures import project, reference_input
from extensions.math_analysis.kernels import bounded_endpoint, raw_scipy
from schemas.platform import SignalSpec
from schemas.platform_analysis import (EndpointLinearizedModel, EndpointOutputLinearization,
    EndpointTarget, TaskAnalysisProtocol)
from tools.platform_host import Host
from tools.platform_store import Store, plain
from tools.state_io import digest


def protocol(**updates):
    value=TaskAnalysisProtocol(baseline_lengths_m={'near':.16,'far':.12},
        frequency_rad_s=[.1,1.,10.])
    return value.model_copy(update=updates)


def model_for(p, *, time_domain='continuous'):
    state=SignalSpec(name='state',entity='fixture',dimension=2,units='m',frame='world',phase='continuous')
    inp=SignalSpec(name='tension',entity='t0',dimension=1,units='N',frame='robot_base',phase='held')
    out=SignalSpec(name='tip_position',entity='tip',dimension=3,units='m',frame='world',phase='instantaneous')
    C=[[1.,0.],[0.,0.],[0.,0.]]; D=[[0.],[0.],[0.]]
    position=EndpointOutputLinearization(name='tip_position',units='m',value0=[0.,0.,0.],C=C,D=D,scales=[1.]*3)
    velocity=EndpointOutputLinearization(name='tip_velocity',units='m/s',value0=[0.,0.,0.],
        C=[[0.,1.],[0.,0.],[0.,0.]],D=D,scales=[1.]*3)
    return EndpointLinearizedModel(state_definition=[state],input_definition=[inp],output_definition=[out],
        x0=[0.,0.],u0=[.5],y0=[0.,0.,0.],A=[[0.,1.],[0.,0.]],B=[[0.],[1.]],C=C,D=D,
        drift=[0.,0.],time_domain=time_domain,timestep=.01 if time_domain=='discrete' else None,
        binding=dict(tension_limits_n=[1.],target_m=[.00008,0.,0.],source='analytic fixture'),
        operating_point=dict(remaining_task_s=.02),state_scales=[1.,1.],input_scales=[1.],output_scales=[1.]*3,
        normalization_derivation='identity analytic fixture',protocol_identity=digest(plain(p)),evidence=[],
        endpoint_outputs=[position,velocity])


class TaskAnalysisTests(unittest.TestCase):
    def test_alignment_reports_effective_duration_and_rejects_rounding(self):
        p=protocol(); m=model_for(p)
        raw=raw_scipy(np.asarray(m.A),np.asarray(m.B),np.asarray(m.C),np.asarray(m.D),np.asarray(m.drift),p)
        self.assertEqual(raw['held_sampling'][0]['effective_horizon_s'],.05)
        self.assertEqual(raw['held_sampling'][0]['step_count'],5)
        bad=protocol(windows_s=[.015])
        with self.assertRaisesRegex(ValueError,'SAMPLED_HORIZON_NOT_ALIGNED'):
            raw_scipy(np.asarray(m.A),np.asarray(m.B),np.asarray(m.C),np.asarray(m.D),np.asarray(m.drift),bad)
        with self.assertRaisesRegex(ValueError,'FREQUENCY_GRID'):
            TaskAnalysisProtocol(baseline_lengths_m={'near':.16,'far':.12},frequency_rad_s=[1.,.1])

    def test_bounded_position_and_braking_known_feasible_and_independently_checked(self):
        p=protocol(); m=model_for(p)
        target=EndpointTarget(position_m=(.00008,0.,0.),position_tolerance_m=1e-6,position_scale_m=.01,
            tip_speed_limit_m_s=.02,tip_velocity_scale_m_s=.02)
        position=bounded_endpoint(m,p,target,braking=False)
        braking=bounded_endpoint(m,p,target,braking=True,
            warm_start=np.asarray(position['delta_input_n']).reshape(-1))
        self.assertEqual(position['status'],'feasible_in_local_model',position)
        self.assertEqual(braking['status'],'feasible_in_local_model',braking)
        self.assertTrue(all(position['checks'].values()))
        self.assertTrue(all(braking['checks'].values()))
        applied=np.asarray(braking['applied_input_n'])
        self.assertTrue(np.all((applied>=0)&(applied<=1)))

    def test_scipy_host_call_does_not_require_matlab_and_discrete_is_rejected(self):
        root=Path('runs/task_analysis_tests')/uuid4().hex; store=Store(root)
        budget=dict(tool_calls=5,model_calls=0,backend_solves=0,worker_calls=0,wall_s=60.)
        cfg=project(); cfg['budget']=budget; store.create(cfg)
        inp=reference_input('fixture-task-v2'); inp['policy'].update(budget=budget,timeout_s=20.,
            tool_bindings={'analysis.control_metrics':'2.0.0'},allowed_tools=[])
        host=Host(root,'fixture-task-v2'); host.create(inp); p=protocol()
        with store.transaction() as db:
            pref=store.put(db,p); mref=store.put(db,model_for(p))
            discrete=store.put(db,model_for(p,time_domain='discrete'))
        real_version=importlib.metadata.version
        def without_matlab(name):
            if name=='matlabengine': raise importlib.metadata.PackageNotFoundError(name)
            return real_version(name)
        request=lambda rid,ref: dict(request_id=rid,tool_id='analysis.control_metrics',tool_version='2.0.0',
            arguments=dict(models=[plain(ref)],protocol=plain(pref),implementation='scipy'),reason='Focused interface check')
        with patch('importlib.metadata.version',side_effect=without_matlab):
            receipt=host.invoke(request('scipy-without-matlab',mref))
        self.assertEqual(receipt['execution_status'],'completed',receipt)
        rejected=host.invoke(request('reject-discrete',discrete))
        self.assertEqual(rejected['execution_status'],'failed',rejected)
        self.assertIn('CONTINUOUS_INPUT_MODEL_REQUIRED',rejected['error'])
        for key in ('model_calls','backend_solves','worker_calls'):
            self.assertEqual(receipt['charged'][key],0)

    def test_full_acceptance_requires_matlab(self):
        base={key:True for key in ('protocol_binding_passed','derivative_checks_passed','repeat_checks_passed',
            'serialized_outputs_verified','prohibited_usage_zero','caller_contract_identical')}
        self.assertFalse(verification_acceptance(dict(base,matlab_checks_passed=False))['full_cross_implementation_accepted'])
        self.assertTrue(verification_acceptance(dict(base,matlab_checks_passed=True))['full_cross_implementation_accepted'])

    def test_velocity_derivative_keeps_moving_configuration_term_and_boundary_is_configuration_only(self):
        from schemas.platform import SessionInput
        from extensions.tendon_family.gvs_profile import reach_input
        from extensions.tendon_family.math_analysis import make_graph_from_input, _configuration_boundary
        inp=SessionInput.model_validate(reach_input('velocity-derivative'))
        n=12; q=np.linspace(-.4,.5,n); qdot=np.linspace(-2.,3.,n); x=np.r_[q,qdot]
        u=np.asarray([row['pretension_n'] for row in inp.robot.structure.data['tendons']])
        graph=make_graph_from_input(inp,dict(x=x.tolist(),u=u.tolist())); output=graph[3]
        direction=np.cos(np.arange(2*n)+1); eps=1e-6
        plus=np.asarray(output(x+eps*direction,u)[3]).reshape(-1)
        minus=np.asarray(output(x-eps*direction,u)[3]).reshape(-1)
        finite=(plus-minus)/(2*eps)
        analytic=np.asarray(output(x,u)[4])@direction
        np.testing.assert_allclose(finite,analytic,rtol=3e-4,atol=3e-6)
        boundary=_configuration_boundary(inp,dict(candidate_id='screen-01',source_node='build-01',
            basis={'strategy':'structural_linear'}))
        self.assertFalse(set(boundary)&{'trajectory','evaluation','terminal_error','actual_tension_n','optimizer_history'})
        self.assertFalse(boundary['execution_data_used'])


if __name__=='__main__': unittest.main()
