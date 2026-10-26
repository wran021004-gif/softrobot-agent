"""Small offline contract tests; all numeric rows below are synthetic fixtures."""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

from tools.platform_store import plain
from tools.state_io import digest
from tools.research.contracts import AnalysisRequest,LocalControlSearchSettings
from tools.research.nonlinear_capability import response,saved_context,t1_summary,T1,T1_OPERATION,T2_OPERATION


def context(values=(3.,4.,2.)):
    rows=[]
    for d,j in zip((5.4,4.86,5.94),values):
        t=dict(J=j,initial_J=j+1,callbacks=16,iterations_started=3,response_steps_completed=3,
            local_responses=[dict(diagnostic='resolved_local_response')],stop_reason='iteration_limit',
            input_saturation=dict(lower=True,upper=False),coefficient_boundary=False)
        rows.append(dict(value=d,t1=t,candidate={},reference={}))
    return dict(rows=rows,parameter=dict(units='MPa'))


class NonlinearCapabilityTests(unittest.TestCase):
    def test_original_signed_measure_and_existing_search_cost(self):
        from tools.research.control_correction import task_measure
        settings=LocalControlSearchSettings(version='local_control_search_v2',knots_s=[0,.5],correction_window_s=[0,.5])
        def measure(error):
            return task_measure(dict(times_s=[0,.45,.5],tip_positions_m=[[error,0,0]]*3,
                tip_velocities_m_s=[[0,0,0]]*3),[0,0,0],.45,.01,.02)
        initial,best=measure(.008),measure(.004)
        self.assertEqual(initial['normalized_gap'],best['normalized_gap'])
        raw=dict(optimization=dict(best=dict(measure=best,reference='fixture-2',label='finite_difference',coefficients_n=[0]*8),
            candidates=[dict(measure=initial,label='baseline'),dict(label='finite_difference')],
            stop_reason='iteration_limit',cost_feedback=dict(evaluation_callbacks=2),iterations_started=1,local_responses=[]),
            original_schedule={},optimized_schedule=dict(trajectory=dict(tensions_n=[[1]*4]*50),provenance={'fixture':True}),
            cost=dict(rollouts=2,physics_steps=2000))
        result=t1_summary(dict(native_dynamics=raw,binding=dict(tension_bounds_n=[[0,8]]*4)),settings)
        self.assertAlmostEqual(result['J'],-.6);self.assertAlmostEqual(result['improvement'],.4)
        self.assertEqual((result['callbacks'],result['physics_steps']),(2,2000))
        self.assertEqual(result['task_acceptance'],'unmeasured')

    def test_unresolved_limits_opposition_and_missing_search(self):
        monotone=response(context())
        self.assertTrue(monotone['monotone_observed']);self.assertEqual(monotone['direction_status'],'unresolved')
        self.assertIn('CONTROL_SEARCH_QUALITY_UNRESOLVED_AT_LIMIT_OR_FAILURE',monotone['reasons'])
        self.assertEqual(monotone['cost']['physics_steps'],0)
        opposing=response(context((2.,3.,4.)))
        self.assertTrue(opposing['nonmonotonic']);self.assertEqual(opposing['direction_status'],'unresolved')
        c=context();c['rows'][1]['t1']['callbacks']=1
        self.assertEqual(response(c)['direction_status'],'not_comparable')
        c=context();c['rows'][1]['t1']['callbacks']=8
        self.assertIn('UNEQUAL_ACTUAL_SEARCH_OPPORTUNITIES',response(c)['reasons'])
        c=context();c['rows'][1]['t1'].update(local_responses=[],response_steps_completed=0)
        self.assertEqual(response(c)['direction_status'],'unresolved')
        self.assertEqual(response(c)['cost']['physics_steps'],0)

    def test_saved_t1_single_parameter_task_and_search_binding(self):
        refs=[dict(artifact_id=str(i)*64,media_type='application/json') for i in (1,2,3)]
        candidates={};raws={}
        for i,(ref,d) in enumerate(zip(refs,(5.4,4.86,5.94))):
            cfg=dict(task=dict(fixture=True),seed=0,policy={k:{} for k in ('controller','backend','dynamics_model','discretization')})
            candidate=dict(artifact_id=str(i+4)*64,media_type='application/json')
            c=dict(configuration=cfg,parameters=dict(segments={'1':dict(young_pa=d)}))
            candidates[candidate['artifact_id']]=c
            raws[ref['artifact_id']]=dict(status='computed',implementation='fixture',protocol={},candidate=candidate,
                binding=dict(candidate=candidate,effective_configuration_identity=digest(cfg)),
                nonlinear_capability=dict(method=T1,settings={'fixture':True}),native_dynamics=dict(
                    original_schedule=dict(trajectory=dict(times_s=[0,.5],tendon_order=['a'],tensions_n=[[1]])),
                    optimized_schedule=dict(trajectory={}),cost={},
                    initial_state=dict(actual_time_s=0.,configuration_identity=digest(cfg))))
        h=Mock();h.store.artifact.side_effect=lambda r:raws[r['artifact_id']]
        q=SimpleNamespace(candidate=raws[refs[0]['artifact_id']]['candidate'],protocol={},
            nonlinear_response=SimpleNamespace(t1_results=refs,variable='segments.1.young_pa',unit='Pa'))
        state=dict(freeze='fixture',spec={},analysis_results=refs)
        def family(spec,c,path):return c['parameters'],dict(units='Pa')
        with patch('tools.research.state.state',return_value=state),patch('tools.research.design.verify_candidate',side_effect=lambda h,r:candidates[r['artifact_id']]),patch('tools.research.optimal_capability.family_parameters',side_effect=family),patch('tools.research.physical_replay.binding'):
            self.assertEqual(len(saved_context(h,q)['rows']),3)
            for field in ('settings','task','parameter'):
                original=deepcopy((raws,candidates))
                if field=='settings':raws[refs[1]['artifact_id']]['nonlinear_capability']['settings']={'different':True}
                elif field=='task':candidates[raws[refs[1]['artifact_id']]['candidate']['artifact_id']]['configuration']['task']={'changed':True}
                else:candidates[raws[refs[1]['artifact_id']]['candidate']['artifact_id']]['parameters']['other']=1
                self.assertIn('not_comparable',saved_context(h,q))
                raws.clear();raws.update(original[0]);candidates.clear();candidates.update(original[1])

    def test_authorized_catalog_uses_original_request_and_cost_scope(self):
        from tests.research.test_c1_method_context import C1Archive
        from tools.research.task_constraints import mathematical_method_view
        from tools.research.nonlinear_capability import T2
        archive=C1Archive();self.addCleanup(archive.archive.close)
        host,s=archive.host();ref=s['reference_candidate']
        before=deepcopy(s['spec'])
        self.assertNotIn(T1,mathematical_method_view(host,ref)['methods'])
        s['spec']['mathematical_methods']={T1:'offline fixture',T2:'offline fixture'}
        methods=mathematical_method_view(host,ref)['methods']
        self.assertEqual(methods[T1]['request_template']['operation'],T1_OPERATION)
        self.assertEqual(methods[T2]['request_template']['operation'],T2_OPERATION)
        self.assertEqual(methods[T2]['applicability']['execution_support'],'saved_evidence_only')
        s['spec']=before
        host.store.reserve.assert_not_called()

    def test_schema_and_explicit_method_authorization_without_worker(self):
        from tools.research import analysis
        from tools.research.config import resolve,ROOT
        spec=resolve(ROOT/'configs/research/study_b3_r1_history_assisted.json')
        ref=dict(artifact_id='a'*64,media_type='application/json')
        q=dict(candidate=ref,operation=T2_OPERATION,model_source='mujoco',operating_point='standardized_initial_pretension',
            protocol=spec['analysis_protocol'],nonlinear_response=dict(variable='segments.1.young_pa',unit='Pa',t1_results=[ref]*3))
        self.assertIsNone(AnalysisRequest.model_validate(q).capability_method)
        malformed=deepcopy(q);malformed['nonlinear_response']['t1_results']=[ref]*2
        with self.assertRaises(ValueError):AnalysisRequest.model_validate(malformed)
        spec['mathematical_methods']={};h=Mock();h.store.lookup.return_value=None
        with patch.object(analysis,'state',return_value=dict(spec=spec)):
            out=analysis.dispatch(h,q,'fixture',guard=Mock(),origin='engineering_preflight')
        self.assertEqual(out['status'],'not_applicable');h.store.reserve.assert_not_called()
        legacy=AnalysisRequest(candidate=ref,operation='task_capability',capability_method='sampled-affine-conic-minimax-v1',
            operating_point='controller_start_input',protocol=spec['analysis_protocol'])
        self.assertNotIn('nonlinear_response',plain(legacy))


if __name__=='__main__':unittest.main()
