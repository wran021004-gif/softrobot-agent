"""Analytic fixtures verify definitions, not implementation line structure."""
import unittest
import numpy as np
from scipy.linalg import expm
from schemas.platform_analysis import AnalysisProtocol
from extensions.math_analysis.kernels import finite_gramian,held_gramian,zoh,correction


class MathAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.p=AnalysisProtocol(baseline_lengths_m={'near':.16,'far':.12},frequency_rad_s=[.1,1.,10.])

    def test_finite_gramian_integrator_unstable_and_stiff(self):
        for a in (0.,2.,-10000.):
            T=.35; A=np.array([[a]]);B=np.array([[2.]])
            expected=4*T if a==0 else 4*np.expm1(2*a*T)/(2*a)
            np.testing.assert_allclose(finite_gramian(A,B,T),[[expected]],rtol=1e-11,atol=1e-12)
        # Double integrator has no infinite-horizon Gramian.
        T=.1; A=np.array([[0.,1.],[0.,0.]]);B=np.array([[0.],[1.]])
        np.testing.assert_allclose(finite_gramian(A,B,T),[[T**3/3,T*T/2],[T*T/2,T]],atol=1e-14)

    def test_zoh_held_energy_and_normalization(self):
        A=np.array([[0.]]); B=np.array([[2.]])
        Ad,Bd,g=zoh(A,B,np.array([3.]),.01)
        np.testing.assert_allclose([Ad.item(),Bd.item(),g.item()],[1.,.02,.03])
        np.testing.assert_allclose(held_gramian(Ad,Bd,.01,35),[[1.4]])
        A=np.array([[-2.,3.],[0.,-1.]]);B=np.array([[1.],[2.]])
        S=np.diag([.1,10.]); Si=np.linalg.inv(S)
        np.testing.assert_allclose(finite_gramian(Si@A@S,Si@B,.1),Si@finite_gramian(A,B,.1)@Si.T,atol=1e-12)
        np.testing.assert_allclose(expm(Si@A@S*.1),Si@expm(A*.1)@S,atol=1e-12)

    def test_unreachable_target_not_silently_finite_energy(self):
        G=np.diag([2.,0.]);r=correction(G,np.array([1.,1.]),self.p)
        self.assertFalse(r['reachable']);self.assertIsNone(r['energy'])
        np.testing.assert_allclose(r['unreachable_output_normalized'],[0.,1.])
        self.assertAlmostEqual(correction(G,np.array([1.,0.]),self.p)['energy'],.5)

    def test_host_evidence_serialization_and_zero_execution_usage(self):
        from pathlib import Path
        from uuid import uuid4
        from examples.platform_fixtures import reference_input,project
        from tools.platform_host import Host
        from tools.platform_store import Store,plain
        from tools.state_io import digest
        from schemas.platform import SignalSpec
        from schemas.platform_analysis import OutputLinearizedModel
        root=Path('runs/math_analysis_tests')/uuid4().hex
        store=Store(root); config=project()
        budget=dict(tool_calls=3,model_calls=0,backend_solves=0,worker_calls=0,wall_s=60.)
        config['budget']=budget;store.create(config)
        inp=reference_input('fixture');inp['policy'].update(budget=budget,timeout_s=20.,
            tool_bindings={'analysis.control_metrics':'1.0.0','evidence.read':'1.0.0'},allowed_tools=[])
        host=Host(root,'fixture');host.create(inp)
        s=SignalSpec(name='position',entity='fixture',dimension=1,units='m',frame='world',phase='continuous')
        with store.transaction() as db:
            source=store.put(db,dict(kind='analytic fixture, no robot execution'))
            pref=store.put(db,self.p)
            model=OutputLinearizedModel(state_definition=[s],input_definition=[s],output_definition=[s],
                x0=[0.],u0=[0.],y0=[0.],A=[[-1.]],B=[[1.]],C=[[1.]],D=[[0.]],drift=[0.],time_domain='continuous',
                binding=dict(tension_limits_n=[8.],target_m=[1.],source='analytic fixture'),operating_point={},
                state_scales=[1.],input_scales=[1.],output_scales=[1.],normalization_derivation='identity fixture',
                protocol_identity=digest(plain(self.p)),evidence=[source])
            mref=store.put(db,model)
        receipt=host.invoke(dict(request_id='metrics',tool_id='analysis.control_metrics',tool_version='1.0.0',
            arguments=dict(models=[plain(mref)],protocol=plain(pref),implementation='scipy'),reason='Analytic public interface verification'))
        self.assertEqual(receipt['execution_status'],'completed',receipt)
        result=store.artifact(receipt['output'])
        self.assertEqual(result['evidence'],[plain(mref)])
        self.assertEqual(result['records'][0]['model_reference'],plain(mref))
        for key in ('model_calls','backend_solves','worker_calls'): self.assertEqual(receipt['charged'][key],0)
        np.testing.assert_allclose(result['records'][0]['raw']['A_d'],[[np.exp(-.01)]])

    def test_saved_phase_pairs_previous_and_next_applied_input(self):
        from extensions.tendon_family.math_analysis import saved_points
        p=self.p.model_copy(update={'samples_s':[.1,.2]})
        case={'saved':{'controller_observations.json':[dict(time_s=.1,phase='current_state_before_integration',
            gvs_q=[2.],gvs_qdot=[3.],measured_initial_state=[2.,3.],actual_tension_n=[4.])],
            'actual_commands.json':[dict(time_s=.09,desired_tension_n=[1.]),dict(time_s=.1,desired_tension_n=[4.])]}}
        points=saved_points(case,p)
        self.assertEqual(points[0]['preceding_input_n'],[1.]);self.assertEqual(points[0]['u'],[4.])
        self.assertFalse(points[1]['available'])


if __name__=='__main__': unittest.main()
