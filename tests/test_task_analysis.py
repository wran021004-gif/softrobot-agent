"""Focused deterministic task-time analysis boundary checks."""
import importlib.metadata
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4

import numpy as np

from examples.offline_math_analysis import verification_acceptance
from examples.platform_fixtures import project, reference_input
from extensions.math_analysis.kernels import _minimum_residual_certificate, bounded_endpoint, raw_scipy
from schemas.platform import SignalSpec
from schemas.platform_analysis import (EndpointLinearizedModel, EndpointOutputLinearization,
    EndpointTarget, MathOptimizeRequest, TaskAnalysisProtocol)
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
    def test_scaled_residual_solver_result_is_not_an_infeasibility_certificate(self):
        result=_minimum_residual_certificate(np.asarray([[5e-8,5e-8]]),np.asarray([0.]),np.asarray([7.5e-8]),
            np.asarray([0.,0.]),np.asarray([.1,2.]),2e-8,1e-8)
        self.assertFalse(result['certified_infeasible'],result)
        self.assertLessEqual(result['separating_direction']['lower_bound'],2e-8+result['separating_direction']['numerical_allowance'])
        np.testing.assert_allclose(np.asarray([[5e-8,5e-8]])@np.asarray([0.,1.5]),[7.5e-8],atol=1e-20)

    def test_separating_direction_certificate_is_independently_checkable(self):
        result=_minimum_residual_certificate(np.zeros((1,1)),np.asarray([0.]),np.asarray([1.]),
            np.asarray([0.]),np.asarray([1.]),.1,1e-8)
        self.assertTrue(result['certified_infeasible'],result)
        certificate=result['separating_direction']
        self.assertGreater(certificate['lower_bound']-.1-certificate['numerical_allowance'],0.)
        self.assertAlmostEqual(certificate['unit_norm'],1.)
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

    def test_candidate_protocol_uses_effective_task_timing_and_optimizer_seals_space(self):
        from schemas.platform import SessionInput
        from extensions.tendon_family.gvs_profile import reach_input
        from extensions.tendon_family.math_analysis import _validate_task_protocol
        inp=SessionInput.model_validate(reach_input('protocol-binding'))
        _validate_task_protocol(inp,protocol())
        with self.assertRaisesRegex(ValueError,'TASK_DURATION_MISMATCH'):
            _validate_task_protocol(inp,protocol(duration_s=.34))
        refs=dict(artifact_id='0'*64,media_type='application/json')
        variables={'components/near/length_m':(.15,.17),'components/far/length_m':(.11,.13),
            'design/section_scale':(.95,1.05)}
        request=MathOptimizeRequest(source_node='build',protocol=refs,target=refs,variables=variables,
            material_scenarios=['compliant','stiff'],max_evaluations=24)
        self.assertEqual(request.max_evaluations,24)
        with self.assertRaisesRegex(ValueError,'NEAR_FAR_AND_SECTION_SCALE'):
            MathOptimizeRequest(source_node='build',protocol=refs,target=refs,
                variables={k:v for k,v in variables.items() if 'far' not in k},material_scenarios=['compliant','stiff'])

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
            tool_bindings={'analysis.control_metrics':'2.0.0','analysis.bounded_endpoint':'1.0.0'},allowed_tools=[])
        host=Host(root,'fixture-task-v2'); host.create(inp); p=protocol()
        with store.transaction() as db:
            pref=store.put(db,p); mref=store.put(db,model_for(p))
            discrete=store.put(db,model_for(p,time_domain='discrete'))
            envelope=store.put(db,dict(kind='candidate_linearization',protocol=plain(pref),bindings=[],
                records=[dict(model=plain(mref))],evidence=[]))
            target=store.put(db,EndpointTarget(position_m=(.00008,0.,0.),position_tolerance_m=1e-6,
                position_scale_m=.01,tip_speed_limit_m_s=.02,tip_velocity_scale_m_s=.02))
        real_version=importlib.metadata.version
        def without_matlab(name):
            if name=='matlabengine': raise importlib.metadata.PackageNotFoundError(name)
            return real_version(name)
        request=lambda rid,ref: dict(request_id=rid,tool_id='analysis.control_metrics',tool_version='2.0.0',
            arguments=dict(models=[plain(ref)],protocol=plain(pref),implementation='scipy'),reason='Focused interface check')
        with patch('importlib.metadata.version',side_effect=without_matlab):
            receipt=host.invoke(request('scipy-without-matlab',mref))
        self.assertEqual(receipt['execution_status'],'completed',receipt)
        expanded=host.invoke(request('scipy-envelope',envelope))
        self.assertEqual(expanded['execution_status'],'completed',expanded)
        self.assertEqual(store.artifact(expanded['output'])['records'][0]['model_reference'],plain(mref))
        endpoint=host.invoke(dict(request_id='endpoint-envelope',tool_id='analysis.bounded_endpoint',tool_version='1.0.0',
            arguments=dict(models=[plain(envelope)],protocol=plain(pref),target=plain(target)),reason='Public envelope expansion regression'))
        self.assertEqual(endpoint['execution_status'],'completed',endpoint)
        self.assertEqual(store.artifact(endpoint['output'])['records'][0]['model_reference'],plain(mref))
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

    def test_route_records_exact_shared_analysis_and_optimizer_linkage(self):
        from extensions.tendon_family.route import create as create_route
        root=Path('runs/task_analysis_tests')/uuid4().hex;store=Store(root)
        budget=dict(tool_calls=8,model_calls=0,backend_solves=0,worker_calls=0,wall_s=120.)
        store.create(dict(project_id='route-analysis-link',grant_id=uuid4().hex,
            authorization_source='Focused synthetic linkage test; no numerical or backend execution.',budget=budget))
        p=protocol();target=EndpointTarget(position_m=(.29,.035,.19),position_tolerance_m=.01,
            position_scale_m=.01,tip_speed_limit_m_s=.02,tip_velocity_scale_m_s=.02)
        with store.transaction() as db: pref=plain(store.put(db,p));tref=plain(store.put(db,target))
        frozen=json.loads(Path('runs/stage333_bounded_recovery_independent_lengths_20260929_114923/resolved_frozen_input.json').read_text(encoding='utf8'))
        frozen['run_id']='route-analysis-link';frozen['policy'].update(budget=budget,timeout_s=30.,model={},allowed_tools=[],
            tool_bindings={'route.advance':'1.0.0','route.record_analysis':'1.0.0'})
        frozen['policy']['route']['data'].update(historical_case=None,analysis_protocol=pref,
            endpoint_target=tref,analysis_required_before_run=True)
        create_route(root,frozen);host=Host(root,frozen['run_id'])
        built=host.invoke(dict(request_id='build',tool_id='route.advance',tool_version='1.0.0',reason='Synthetic owned build',
            arguments=dict(node_id='build',action='build',combination='candidate_gvs_nmpc',candidate_id='linked',
                reason='Synthetic owned build',next_step='Attach synthetic evidence')))
        self.assertEqual(built['execution_status'],'completed',built)
        build_node=store.session(host.run_id)['state']['route']['nodes'][0];build_out=store.artifact(build_node['result'])
        binding=dict(configuration=build_out['configuration'],candidate_id='linked')
        with store.transaction() as db:
            lref=plain(store.put(db,dict(kind='candidate_linearization',protocol=pref,bindings=[binding],records=[],evidence=[])))
            mref=plain(store.put(db,dict(kind='control_metrics',protocol=pref,bindings=[binding],records=[],evidence=[])))
            eref=plain(store.put(db,dict(kind='bounded_endpoint',protocol=pref,bindings=[binding],records=[],evidence=[tref])))
            sref=plain(store.put(db,dict(kind='design_screen',protocol=pref,bindings=[binding],
                records=[dict(priority_reasoning=dict(priority='conditional_support'))],evidence=[lref,mref,eref])))
        receipt=host.invoke(dict(request_id='record',tool_id='route.record_analysis',tool_version='1.0.0',
            reason='Synthetic exact linkage',arguments=dict(node_id='analysis',source_node='build',evidence=[build_node['result']],
                linearization=lref,metrics=mref,endpoint=eref,screen=sref,
                validation_disposition='recommended',reason='Local evidence remains advisory.',next_step='Backend validation.')))
        self.assertEqual(receipt['execution_status'],'completed',receipt)
        summary=store.artifact(receipt['output'])['detail']['summary']
        self.assertEqual(summary['analysis_report'],sref);self.assertIsNone(summary['math_optimization'])
        self.assertEqual(store.remaining(host.run_id)['used']['backend_solves'],0)

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
