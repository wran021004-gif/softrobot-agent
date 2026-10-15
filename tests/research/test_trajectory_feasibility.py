"""Offline M2 fixtures; fabricated systems are not robot scientific evidence."""
from copy import deepcopy
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import numpy as np
from schemas.platform_analysis import TaskAnalysisRequirement
from extensions.math_analysis.trajectory import trajectory_feasibility, sampled_maps, verify_witness


def fixture(nu=1, nominal=.4, start=0., duration=3., sample=1., feedthrough=0.):
    output = NS(name='test_output', units='m', frame='world', value0=[0.], C=[[1.]], D=[[feedthrough]*nu])
    model = NS(A=[[0.]], B=[[1.]*nu], drift=[0.], u0=[nominal]*nu, time_domain='continuous',
        binding=dict(tension_limits_n=[1.]*nu), endpoint_outputs=[output], input_scales=[1.]*nu,
        operating_point=dict(actual_time_s=start, remaining_task_s=duration-start, previous_applied_input_n=[nominal]*nu))
    p = NS(period_s=1., horizon_alignment_atol_s=1e-12, endpoint_check_atol=1e-8, endpoint_max_iterations=100)
    times = [i*sample for i in range(round(duration/sample)+1)]
    req = TaskAnalysisRequirement(binding=dict(fixture=True),duration_s=duration,sample_period_s=sample,time_grid_s=times,
        physical_inputs=dict(lower=[0.]*nu,upper=[1.]*nu),constraints=[dict(constraint_id='moving',
            signal=dict(name='test_output',entity='fixture',dimension=1,units='m',frame='world',phase='post_step'),
            indices=list(range(len(times))),kind='norm_bound',radius=.02,
            reference=[[.2*t] for t in times],provenance=['/synthetic_fixture'])])
    return model,req,p


class NumericalTests(unittest.TestCase):
    def test_scaled_margin_derivatives_and_zero_norm_convention(self):
        from extensions.math_analysis.trajectory import _margins, _margin_jacobian
        from scipy.optimize._numdiff import approx_derivative
        _,req,p=fixture()
        matrix=np.array([[.3,-.2,.7],[-.1,.5,.2]])
        base=np.array([.4,-.2]); z=np.array([.1,.3,-.2])
        norm=req.constraints[0].model_copy(update=dict(radius=.08))
        interval=norm.model_copy(update=dict(kind='component_interval',radius=None,lower=[-.2,-.5],upper=[.3,.7]))
        for c in (norm,interval):
            scale=max(c.radius if c.kind=='norm_bound' else max(np.max(np.abs(c.lower)),np.max(np.abs(c.upper))),p.endpoint_check_atol)
            fd=approx_derivative(lambda v:_margins(c,base+matrix@v)[0]/scale,z,method='3-point')
            np.testing.assert_allclose(_margin_jacobian(c,base+matrix@z,matrix,p.endpoint_check_atol),np.atleast_2d(fd),rtol=1e-8,atol=1e-8)
        np.testing.assert_array_equal(_margin_jacobian(norm,np.zeros(2),matrix,p.endpoint_check_atol),np.zeros((1,3)))
        # Concavity inequality for the zero supergradient of radius - ||r||.
        self.assertLessEqual(_margins(norm,base)[0][0],_margins(norm,np.zeros(2))[0][0])

    def test_known_shared_witness_moving_reference_and_total_bounds(self):
        model,req,p = fixture()
        out = trajectory_feasibility(model,req,p)
        self.assertEqual(out['status'],'feasible_witness')
        self.assertTrue(out['full_requested_coverage'])
        self.assertLess(out['replay']['max_prediction_replay_error'],1e-12)
        self.assertEqual(len(out['replay']['records']),4)
        self.assertTrue(np.all(np.array(out['applied_input_n']) >= 0))
        self.assertTrue(np.all(np.array(out['applied_input_n']) <= 1))
        np.testing.assert_allclose(np.array(out['applied_input_n'])-out['delta_input_n'],.4)
        self.assertGreaterEqual(out['replay']['minimum_tension_margin_n'],-p.endpoint_check_atol)

    def test_matrix_predictions_equal_recurrence_with_drift_initial_and_feedthrough(self):
        model,req,p = fixture(nu=5, feedthrough=.3)
        model.A=[[-.2]]; model.drift=[.07]
        dynamics,maps = sampled_maps(model,3,1.,initial_delta=[.12])
        from extensions.math_analysis.trajectory import _output_map
        z=np.arange(15).reshape(3,5)/100
        rows=[]
        c=req.constraints[0]; output=model.endpoint_outputs[0]
        for k in range(4):
            base,matrix=_output_map(output,maps[k],k,3,np.array(model.u0),np.array(model.u0))
            np.testing.assert_allclose(matrix[:,k*5:],0.)
            rows.append((c,k,k,np.array(c.reference[k]),output,base,matrix))
        from extensions.math_analysis.trajectory import time_scope
        replay=verify_witness(model,dynamics,[.12],z,rows,time_scope(req,p,0.),1e-8)
        self.assertLess(replay['max_prediction_replay_error'],1e-12)
        self.assertFalse(verify_witness(model,dynamics,[.12],z[:,:4],rows,time_scope(req,p,0.),1e-8)['passed'])
        z[0,0]=np.nan
        self.assertFalse(verify_witness(model,dynamics,[.12],z,rows,time_scope(req,p,0.),1e-8)['passed'])

    def test_norm_exclusion_rechecked_with_positive_margin(self):
        model,req,p=fixture(nominal=0.)
        c=req.constraints[0].model_copy(update=dict(indices=[1],reference=[[2.]]))
        req=req.model_copy(update=dict(constraints=[c]))
        out=trajectory_feasibility(model,req,p)
        self.assertEqual(out['status'],'model_infeasibility_certificate')
        cert=out['certificate']; v=np.array(cert['direction']); H=np.array(cert['matrix'])
        coeff=H.T@v
        bound=float(v@(np.array(cert['base'])-cert['reference'])+sum(np.minimum(coeff*cert['delta_lower'],coeff*cert['delta_upper'])))
        self.assertAlmostEqual(bound,cert['lower_bound']); self.assertGreater(cert['margin'],.9)
        self.assertEqual((cert['constraint_id'],cert['sample_index']),('moving',1))

    def test_joint_conflict_without_individual_certificate_is_inconclusive(self):
        model,req,p=fixture(nominal=0.)
        c=req.constraints[0].model_copy(update=dict(indices=[1],reference=[[.2]],radius=.01))
        d=c.model_copy(update=dict(constraint_id='conflict',reference=[[.8]]))
        req=req.model_copy(update=dict(constraints=[c,d]))
        out=trajectory_feasibility(model,req,p)
        self.assertEqual(out['status'],'inconclusive'); self.assertIsNone(out['certificate'])
        self.assertIsNotNone(out['replay']['worst_violation'])
        with patch('extensions.math_analysis.trajectory.minimize',return_value=NS(x=np.zeros(3),success=False,status=9,message='fixture stop',nit=1)):
            out=trajectory_feasibility(model,req.model_copy(update=dict(constraints=[c])),p)
        self.assertEqual(out['status'],'inconclusive')

    def test_component_intervals_and_box_exclusion(self):
        model,req,p=fixture(nominal=0.)
        c=req.constraints[0].model_copy(update=dict(kind='component_interval',radius=None,lower=[-.02],upper=[.02]))
        req=req.model_copy(update=dict(constraints=[c]))
        self.assertEqual(trajectory_feasibility(model,req,p)['status'],'feasible_witness')
        c=c.model_copy(update=dict(indices=[1],reference=[[3.]]))
        out=trajectory_feasibility(model,req.model_copy(update=dict(constraints=[c])),p)
        self.assertEqual(out['certificate']['kind'],'component_box_range')
        self.assertGreater(out['certificate']['margin'],1.9)

    def test_remaining_time_zero_horizon_aligned_different_grid_and_partial(self):
        model,req,p=fixture(start=2.)
        out=trajectory_feasibility(model,req,p)
        self.assertEqual(out['horizon']['step_count'],1)
        self.assertEqual(out['coverage'][0]['analyzed_indices'],[2,3])
        self.assertEqual(out['coverage'][0]['unchecked_indices'],[0,1])
        self.assertFalse(out['full_requested_coverage'])
        model.operating_point['actual_time_s']=3.
        model.operating_point['remaining_task_s']=0.
        out=trajectory_feasibility(model,req,p)
        self.assertEqual(out['horizon']['step_count'],0)
        self.assertEqual(out['status'],'model_infeasibility_certificate')
        model,req,p=fixture(duration=4.,sample=2.)
        self.assertEqual(trajectory_feasibility(model,req,p)['status'],'feasible_witness')
        p.period_s=.7
        self.assertEqual(trajectory_feasibility(model,req,p)['status'],'not_applicable')

    def test_feedthrough_previous_input_and_preceding_hold(self):
        model,req,p=fixture(nominal=.4,feedthrough=2.)
        model.operating_point['previous_applied_input_n']=[.7]
        req=req.model_copy(update=dict(constraints=[req.constraints[0].model_copy(update=dict(indices=[0],reference=[[.6]]))]))
        out=trajectory_feasibility(model,req,p)
        self.assertEqual(out['status'],'feasible_witness')
        self.assertAlmostEqual(out['replay']['records'][0]['output'][0],.6)
        del model.operating_point['previous_applied_input_n']
        self.assertEqual(trajectory_feasibility(model,req,p)['status'],'not_applicable')

    def test_variable_dimensions_and_unsupported_nonfinite(self):
        for nu in (1,5,7):
            model,req,p=fixture(nu=nu)
            self.assertEqual(trajectory_feasibility(model,req,p)['status'],'feasible_witness')
        model,req,p=fixture()
        model.u0=[float('nan')]
        self.assertEqual(trajectory_feasibility(model,req,p)['status'],'not_applicable')

    def test_nonfinite_solver_and_untrusted_certificate_proposal(self):
        model,req,p=fixture(nominal=0.)
        with patch('extensions.math_analysis.trajectory.minimize',return_value=NS(x=np.full(3,np.nan),success=True,status=0,message='fixture corrupt',nit=1)):
            out=trajectory_feasibility(model,req,p)
        self.assertEqual(out['status'],'inconclusive')
        self.assertNotIn('applied_input_n',out)
        from extensions.math_analysis.trajectory import _certificate
        c=req.constraints[0]
        with patch('extensions.math_analysis.trajectory._minimum_residual_certificate',return_value=dict(
                certified_infeasible=True,separating_direction=dict(direction=[100.],lower_bound=999.,margin_over_limit=999.))):
            cert=_certificate(c,1,np.array([0.]),np.array([[1.]]),np.array([.5]),np.array([0.]),np.array([1.]),1e-8)
        self.assertIsNone(cert)
        model,req,p=fixture()
        req=req.model_copy(update=dict(constraints=[req.constraints[0].model_copy(update=dict(signal=req.constraints[0].signal.model_copy(update=dict(frame='robot_base'))))]))
        self.assertEqual(trajectory_feasibility(model,req,p)['status'],'not_applicable')


class ResearchIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tools.research.config import ROOT
        (ROOT/'runs').mkdir(exist_ok=True)

    def setUp(self):
        from test_mainline import MainlineTests
        from test_task_analysis_contract import TaskAnalysisTests
        from tools.research.state import update
        self.case=MainlineTests(); self.case.setUp(); self.addCleanup(self.case.tearDown)
        TaskAnalysisTests.setUpClass()
        old=TaskAnalysisTests(); old.setUp()
        self.model=old.fixture_model(); self.binding=old.binding; self.requirements=old.req
        from tools.research.contracts import AnalysisRequest
        self.query=AnalysisRequest(candidate=self.case.candidate,operation='trajectory_feasibility',
            operating_point='controller_start_input',protocol=self.case.spec['analysis_protocol'])
        update(self.case.host,freeze='synthetic-M2-test-fixture',mathematical_evaluations=0)

    def compute(self,model=None,req=None,query=None,point=None):
        from tools.research import analysis
        from tools.platform_store import plain
        m=model or self.model
        envelope=dict(records=[{},dict(model=plain(m),point=m.operating_point,construction={})])
        with patch('extensions.tendon_family.math_analysis.calculate_candidate_configuration',return_value=envelope), \
                patch('tools.research.analysis.describe_analysis_requirements',return_value=req or self.requirements):
            return analysis.calculate(self.case.cfg,self.binding,query or self.query,point)

    def test_complete_partial_exclusion_inconclusive_and_provenance(self):
        from tools.platform_store import plain
        from tools.state_io import digest
        complete=self.compute()
        self.assertEqual(complete['scoped_claim']['conclusion'],'feasible_witness')
        self.assertTrue(complete['analysis_applicability']['full_task_supported'])
        for c in complete['scoped_claim']['constraint_coverage']:
            self.assertEqual(c['checked_indices'],c['satisfied_indices'])
            self.assertEqual(c['checked_indices'],c['analyzed_indices'])
        claim=complete['scoped_claim']
        self.assertEqual(claim['model_identity'],digest(complete['model']))
        self.assertEqual(claim['requirement_identity'],digest(plain(self.requirements)))
        self.assertEqual(claim['numerical_result_pointer'],'/trajectory')
        self.assertEqual(complete['trajectory']['solver_scope'],'sampled-affine-trajectory-v1')
        c=self.requirements.constraints[0]
        unsupported=c.model_copy(update=dict(constraint_id='unavailable',signal=c.signal.model_copy(update=dict(name='contact_force'))))
        req=self.requirements.model_copy(update=dict(constraints=[c,unsupported]))
        partial=self.compute(req=req)
        self.assertEqual(partial['scoped_claim']['conclusion'],'feasible_witness')
        self.assertFalse(partial['analysis_applicability']['full_task_supported'])
        self.assertEqual(partial['scoped_claim']['constraint_coverage'][1]['unchecked_indices'],[35])
        m=self.model.model_copy(deep=True)
        for o in m.endpoint_outputs:
            if o.name=='tip_position': o.value0[0]+=100.
        m.y0[0]+=100.
        excluded=self.compute(model=m,req=req)
        self.assertEqual(excluded['scoped_claim']['conclusion'],'model_infeasibility_certificate')
        self.assertEqual(excluded['trajectory']['certificate']['sample_index'],35)
        self.assertGreater(excluded['trajectory']['certificate']['margin'],0.)
        nu=len(m.u0); c=c.model_copy(update=dict(reference=[[v+.02 if i==0 else v for i,v in enumerate(c.reference[0])]]))
        with patch('extensions.math_analysis.trajectory.minimize',return_value=NS(x=np.zeros(35*nu),success=False,status=9,message='fixture iteration limit',nit=1)):
            undecided=self.compute(req=self.requirements.model_copy(update=dict(constraints=[c])))
        self.assertEqual(undecided['scoped_claim']['conclusion'],'inconclusive')
        self.assertTrue(undecided['analysis_applicability']['full_task_supported'])
        unsupported_result=self.compute(req=self.requirements.model_copy(update=dict(constraints=[unsupported])))
        self.assertEqual(unsupported_result['scoped_claim']['conclusion'],'not_applicable')

    def test_saved_remaining_horizon_hypothetical_points_and_invalid_physics(self):
        from tools.research import analysis
        q=self.query.model_copy(update=dict(operating_point='saved_state',saved_state=dict(artifact_id='b'*64)))
        m=self.model.model_copy(update=dict(operating_point=dict(actual_time_s=.30,remaining_task_s=.05)))
        out=self.compute(model=m,query=q,point=dict(actual_time_s=.30,u=m.u0))
        self.assertEqual(out['trajectory']['horizon']['step_count'],5)
        self.assertEqual(out['trajectory']['coverage'][1]['analyzed_indices'],list(range(30,36)))
        self.assertFalse(out['analysis_applicability']['full_task_supported'])
        for name in ('halfway_waypoint','target_equilibrium'):
            with patch('extensions.tendon_family.math_analysis.calculate_candidate_configuration') as build:
                out=analysis.calculate(self.case.cfg,self.binding,self.query.model_copy(update=dict(operating_point=name)))
                build.assert_not_called()
            self.assertEqual(out['scoped_claim']['conclusion'],'not_applicable')
        cfg=deepcopy(self.case.cfg)
        cfg['task']['environment']['data']['external_forces']=[dict(entity='tip',force_n=[1.,0.,0.],start_s=0.,end_s=.35)]
        with patch('extensions.tendon_family.math_analysis.calculate_candidate_configuration') as build:
            out=analysis.calculate(cfg,self.binding,self.query); build.assert_not_called()
        self.assertEqual(out['scoped_claim']['conclusion'],'not_applicable')

    def check_surfaces(self,first,query,key):
        from tools.research import analysis, core
        from tools.research.state import state
        host=self.case.host; raw=host.store.artifact(first['reference'])
        packet=core.packet(host)['analysis_results'][-1]
        for k in ('reference','scoped_claim','analysis_applicability','charged_numerical_s','charged_analysis_evaluations','trajectory_evidence'):
            self.assertEqual(first[k],packet[k],k)
        value=core.read_evidence(host,dict(reference=first['reference'],pointer=first['numerical_evidence']['pointer']))
        self.assertEqual(value,raw['trajectory'] if 'trajectory' in raw else raw['analysis_applicability'])
        self.assertNotIn('applied_input_n',packet)
        self.assertNotIn('matrix',str(packet['trajectory_evidence']))
        cost=state(host)['numerical_s']; count=state(host)['mathematical_evaluations']
        with patch('tools.service_execution._run_contained') as worker:
            reused=analysis.dispatch(host,query,key,guard=lambda *args:None); worker.assert_not_called()
        self.assertEqual(reused['reference'],first['reference'])
        self.assertEqual(reused['scoped_claim'],first['scoped_claim'])
        self.assertEqual(state(host)['numerical_s'],cost)
        self.assertEqual(state(host)['mathematical_evaluations'],count)
        self.assertEqual(reused['operation_reuse']['additional_analysis_evaluations'],0)
        return raw

    def test_store_packet_evidence_read_and_reuse_for_all_conclusions(self):
        from tools.research import analysis
        from tools.state_io import atomic_json,read
        from pathlib import Path
        # Exercise the actual numerical kernels inside a deterministic worker fixture.
        def worker(command,log,timeout):
            request=read(command[-1]); q=request['query']; point=request['exact_point']
            result=self.compute(query=q,point=point)
            atomic_json(Path(command[-1]).parent/'result.json',result)
            return NS(returncode=0)
        for variant in ('complete','partial','exclusion','inconclusive','not_applicable'):
            with self.subTest(variant=variant):
                req=self.requirements
                c=req.constraints[0]
                patches=[]
                if variant=='partial':
                    req=req.model_copy(update=dict(constraints=[c,c.model_copy(update=dict(constraint_id='unavailable',signal=c.signal.model_copy(update=dict(name='unknown'))))]))
                elif variant in ('exclusion','inconclusive'):
                    offset=-100. if variant=='exclusion' else .02
                    c=c.model_copy(update=dict(reference=[[v+offset if i==0 else v for i,v in enumerate(c.reference[0])]]))
                    req=req.model_copy(update=dict(constraints=[c]))
                elif variant=='not_applicable':
                    req=req.model_copy(update=dict(constraints=[c.model_copy(update=dict(signal=c.signal.model_copy(update=dict(name='unknown'))))]))
                # self.compute also freezes the supplied task fixture for the test worker.
                original=self.requirements; self.requirements=req
                try:
                    if variant=='inconclusive':
                        patches=[patch('extensions.math_analysis.trajectory.minimize',return_value=NS(x=np.zeros(210),success=False,status=9,message='fixture stop',nit=1))]
                    for p in patches:p.start()
                    with patch('tools.service_execution._run_contained',side_effect=worker):
                        first=analysis.dispatch(self.case.host,self.query,'m2-'+variant,guard=lambda *args:None)
                    raw=self.check_surfaces(first,self.query,'m2-'+variant)
                    self.assertEqual(first['scoped_claim']['conclusion'],dict(complete='feasible_witness',partial='feasible_witness',
                        exclusion='model_infeasibility_certificate',inconclusive='inconclusive',not_applicable='not_applicable')[variant])
                finally:
                    self.requirements=original
                    for p in patches:p.stop()

    def test_saved_state_five_seven_channels_and_mismatch_rejection(self):
        from tools.research import analysis
        from tools.research.state import save
        from tools.state_io import digest
        from extensions.tendon_family.gvs_basis import resolve_basis
        for nu in (5,7):
            cfg=deepcopy(self.case.cfg); tendons=cfg['robot']['structure']['data']['tendons']
            if nu==5: del tendons[-1]
            else:
                tendons.append({**deepcopy(tendons[-1]),'id':'synthetic_seventh_input'})
            basis=cfg['policy']['controller']['parameters']['data']['recipe']['basis']
            order=list(resolve_basis(cfg['robot']['structure']['data'],basis).coordinate_order)
            point=dict(candidate=self.case.candidate,configuration_identity=digest(cfg),x=[0.]*(2*len(order)),u=[.2]*nu,
                coordinate_order=order,tendon_order=[t['id'] for t in tendons],actual_time_s=.3,
                phase='interval_start_previous_applied_input',input_units='N')
            candidate={**self.case.host.store.artifact(self.case.candidate),'configuration':cfg}
            for invalid in ('valid','dimension','order','phase','ownership'):
                saved=deepcopy(point)
                if invalid=='dimension':saved['u'].append(.2)
                elif invalid=='order':saved['tendon_order'].reverse()
                elif invalid=='phase':saved['phase']='post_step'
                elif invalid=='ownership':saved['configuration_identity']='wrong'
                from tools.platform_store import plain
                from tools.research.contracts import AnalysisRequest
                q=AnalysisRequest.model_validate({**plain(self.query),'operating_point':'saved_state','saved_state':save(self.case.host,saved)})
                with patch('tools.research.analysis.verify_candidate',return_value=candidate), \
                        patch('tools.service_execution._run_contained',return_value=NS(returncode=1)) as worker:
                    if invalid=='valid':
                        analysis.dispatch(self.case.host,q,f'channels-{nu}',guard=lambda *args:None)
                        self.assertEqual(worker.call_count,1)
                    else:
                        with self.assertRaises(ValueError):analysis.dispatch(self.case.host,q,f'bad-{nu}-{invalid}',guard=lambda *args:None)
                        worker.assert_not_called()

    def test_real_candidate_gvs_through_existing_worker_store_and_packet(self):
        from tools.research import analysis
        first=analysis.dispatch(self.case.host,self.query,'m2-real-gvs',guard=lambda *args:None)
        self.assertEqual(first['status'],'computed')
        raw=self.check_surfaces(first,self.query,'m2-real-gvs')
        model=raw['model']
        self.assertEqual(len(model['x0']),2*len(model['binding']['coordinate_order']))
        self.assertEqual(len(model['u0']),len(model['binding']['tendon_order']))
        self.assertEqual(model['binding']['tension_limits_n'],raw['task_analysis']['physical_inputs']['upper'])
        self.assertEqual([(o['name'],o['frame'],o['units']) for o in model['endpoint_outputs']],
            [('tip_position','world','m'),('tip_velocity','world','m/s')])
        self.assertEqual(raw['trajectory']['horizon']['step_count'],35)
        self.assertEqual(raw['task_acceptance'],'unmeasured')
        print('M2_REAL_GVS',dict(conclusion=raw['scoped_claim']['conclusion'],nx=len(model['x0']),nu=len(model['u0']),
            replay_error=raw['trajectory'].get('replay',{}).get('max_prediction_replay_error'),
            certificate=first['trajectory_evidence']['certificate'],charged_numerical_s=first['charged_numerical_s']))
        # Optional non-secret export retains the original result and exact artifact references.
        import os
        if os.environ.get('M2_EVIDENCE_DIR'):
            from pathlib import Path
            from tools.state_io import atomic_json
            from tools.research.state import science_hashes,core_hashes
            folder=Path(os.environ['M2_EVIDENCE_DIR']); folder.mkdir(parents=True,exist_ok=True)
            atomic_json(folder/'real_gvs.json',dict(label='Offline integration fixture, not robot acceptance or a live Agent run',
                response=first,packet_analysis=__import__('tools.research.core',fromlist=['packet']).packet(self.case.host)['analysis_results'][-1],
                original_result=raw,source_hashes=dict(science=science_hashes(),core=core_hashes())))

    def test_source_fingerprints_include_the_new_kernel(self):
        from tools.research.state import science_hashes
        from extensions.tendon_family.manifest import NMPC_SOURCES
        path='extensions/math_analysis/trajectory.py'
        self.assertIn(path,NMPC_SOURCES)
        self.assertIn(path,science_hashes())


def controlled_real_gvs_ab():
    """Explicit opt-in comparison, never run by test discovery; exactly two solves."""
    import os, time, sys, platform
    import scipy
    from pathlib import Path
    from tools.state_io import read, digest, atomic_json
    from tools.platform_store import plain
    from tools.research.config import ROOT, resolve
    from schemas.platform_analysis import EndpointLinearizedModel, TaskAnalysisProtocol
    from schemas.platform import SessionInput
    from extensions.tendon_family.math_analysis import calculate_candidate_configuration
    from extensions.math_analysis import trajectory
    folder=ROOT/'evidence/task_feasibility_20261015'
    destination=folder/'analytic_jacobian_ab.json'
    if destination.exists():
        raise ValueError('CONTROLLED_PAIR_ALREADY_RECORDED; DO_NOT_RELAUNCH')
    original=read(folder/'real_gvs.json')['original_result']
    cfg=resolve(ROOT/'configs/research/study.json')['configuration']
    assert digest(cfg)==original['binding']['effective_configuration_identity']
    p=TaskAnalysisProtocol.model_validate(original['protocol'])
    req=TaskAnalysisRequirement.model_validate(original['task_analysis'])
    assert p.endpoint_max_iterations==100
    threads={k:os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')}
    assert set(threads.values())=={'1'}
    started=time.perf_counter()
    envelope=plain(calculate_candidate_configuration(SessionInput.model_validate(cfg),original['binding'],p,original['binding']['configuration'],
        operating_points=['controller_start_input']))
    construction_s=time.perf_counter()-started
    m=envelope['records'][1]['model']
    m['operating_point']['actual_time_s']=0.
    model=EndpointLinearizedModel.model_validate(m)
    for key in ('A','B','drift','x0','u0','endpoint_outputs'):
        assert plain(model)[key]==original['model'][key], key
    solve=trajectory.minimize
    outcomes={}
    for mode in ('numerical_difference','analytic'):
        counts=dict(jacobian=0)
        def optimizer(*args,**kwargs):
            if mode=='numerical_difference':
                constraint=kwargs['constraints'][0]
                constraint.pop('jac')
                # Observe SciPy's existing differentiation, without supplying a
                # replacement Jacobian or changing its bounds/steps.
                from scipy.optimize import _slsqp_py
                differentiate=_slsqp_py.approx_derivative
                def measured(*a,**kw):
                    counts['jacobian']+=1
                    return differentiate(*a,**kw)
                with patch.object(_slsqp_py,'approx_derivative',side_effect=measured):
                    return solve(*args,**kwargs)
            return solve(*args,**kwargs)
        started=time.perf_counter()
        with patch.object(trajectory,'minimize',side_effect=optimizer):
            result=trajectory.trajectory_feasibility(model,req,p)
        total_s=time.perf_counter()-started
        replay=result.get('replay',{})
        outcomes[mode]=dict(solver=result['solver'],total_kernel_elapsed_s=total_s,
            measured_constraint_jacobian_calls=counts['jacobian'] if mode=='numerical_difference' else result['solver']['constraint_jacobian_evaluations'],
            conclusion=result['status'],certificate=result.get('certificate'),replay=replay,
            applied_input_n=result.get('applied_input_n'),result_identity=digest(result))
        print(mode,dict(solver=result['solver'],conclusion=result['status'],worst=replay.get('worst_violation')),flush=True)
    record=dict(label='One controlled offline real-GVS pair; no task acceptance or NMPC execution',
        original_evidence=dict(path='evidence/task_feasibility_20261015/real_gvs.json',pointer='/original_result',
            artifact_id=digest(original)),configuration_identity=digest(cfg),model_identity=digest(plain(model)),
        original_model_identity=digest(original['model']),requirement_identity=digest(plain(req)),protocol=plain(p),
        dimensions=dict(state=len(model.x0),input=len(model.u0),intervals=35,variables=210,constraint_samples=13),
        construction_and_linearization_elapsed_s=construction_s,shared_model=True,identical_initial_delta_input='all zeros',
        environment=dict(python=sys.version,numpy=np.__version__,scipy=scipy.__version__,platform=platform.platform(),threads=threads),
        methods=outcomes,source_identity=__import__('tools.research.state',fromlist=['science_hashes']).science_hashes())
    atomic_json(destination,record)
    return record


if __name__ == '__main__': unittest.main()
