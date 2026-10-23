"""S132 synthetic geometric paths only; no Provider, physics or controller run."""
from copy import deepcopy
import json
import math
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock,patch
import numpy as np
from schemas.platform import BackendResult, SessionInput
from tools.platform_registry import registry
from tools.platform_tasks import check_definition
from tools.platform_store import plain
from tools.state_io import digest
from tools.research.config import ROOT,resolve
from tools.research_tasks import task_adapter,assemble_acceptance
from tools.research.task_constraints import describe_analysis_requirements,analysis_capabilities,check_analysis_applicability
from tools.research.contracts import AnalysisRequest
from tools.research import analysis
from tools.research.optimal_capability import CONIC,SENSITIVITY,method_admission
from tools.task_intake import parse_response,compile_draft
from extensions.reference.implementation import polyline_samples


TASK=json.loads((ROOT/'tasks/tracking_linear_development.json').read_text(encoding='utf-8'))['task']
SOURCE=dict(artifact_id='a'*64,media_type='application/json')


def fixture(positions=None,times=None,status='completed',task=None):
    task=task or TASK
    positions=task['goal']['data']['vertices_m'] if positions is None else positions
    return BackendResult(solver_status=status,backend_id='synthetic.path_fixture',model_id='synthetic.polyline',
        signals=[dict(spec=task['observations'][0],times_s=times or np.linspace(.02,.4,len(positions)).tolist(),values=positions)],
        data=dict(contract='platform.empty',data={}),limitations=['Synthetic saved polyline; no robot execution'],
        initial_state=dict(contract='platform.empty',data={}),seed=17)


def evaluate(result=None,task=None):
    task=check_definition(task or TASK)
    return registry().get('evaluate.tracking',kind='evaluator').resolve()(task,result or fixture(),SOURCE,registry(),digest(plain(task)))


class TrackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec=resolve(ROOT/'configs/research/study.json')

    def configuration(self):
        cfg=deepcopy(self.spec['configuration']);cfg['task']=deepcopy(TASK)
        return cfg

    def test_registry_and_reference_have_no_time_or_reach_target(self):
        self.assertEqual(check_definition(TASK).family,'task.tracking')
        self.assertEqual(registry().get('task.tracking').version,'1.0.0')
        self.assertEqual(TASK['status'],'draft')
        self.assertEqual(TASK['goal']['data']['time_requirement'],'none')
        for key in ('target_m','times_s','positions_m'):self.assertNotIn(key,TASK['goal']['data'])
        adapter=task_adapter(self.configuration())
        self.assertIsNone(adapter.describe()['scoring_interval_s'])
        self.assertIsNone(adapter.operating_point()['reference_velocity_m_s'])
        with self.assertRaisesRegex(ValueError,'NO_TIME_REFERENCE'):adapter.reference_at([.1,.2])

    def test_exact_geometry_is_invariant_to_speed_duration_and_pauses(self):
        vertices=TASK['goal']['data']['vertices_m']
        paths=[vertices,[vertices[0]]*4+vertices[1:],[vertices[0],vertices[1],vertices[1],vertices[2]]]
        # Keep corners when adding intermediate measurements: this is the same geometry.
        paths.append([vertices[0],np.mean(vertices[:2],axis=0).tolist(),vertices[1],np.mean(vertices[1:],axis=0).tolist(),vertices[2]])
        for values in paths:
            for end in (.1,4.,100.):
                out=evaluate(fixture(values,np.linspace(.001,end,len(values)).tolist()))
                self.assertTrue(out.task_success,out)
                self.assertLess(max(m.value for m in out.metrics),1e-14)
                self.assertEqual(out.source.model_dump(),SOURCE)
                self.assertEqual(out.evaluator_version,'1.0.0')
                self.assertEqual(out.comparison_identity,digest(plain(check_definition(TASK))))

    def test_known_spatial_offset_and_rms_without_time_weights(self):
        vertices=np.asarray(TASK['goal']['data']['vertices_m']);normal=np.array([1.,0.,-1.])/math.sqrt(2)
        out=evaluate(fixture((vertices+.002*normal).tolist()))
        metrics={m.name:m.value for m in out.metrics}
        self.assertTrue(out.task_success)
        self.assertAlmostEqual(metrics['max_position_error'],.002,places=14)
        self.assertAlmostEqual(metrics['rms_position_error'],.002,places=14)
        local=vertices.copy();local[1]+=.002*normal
        varied=evaluate(fixture(local.tolist()))
        second={m.name:m.value for m in varied.metrics}
        self.assertTrue(varied.task_success)
        self.assertAlmostEqual(second['max_position_error'],metrics['max_position_error'],places=14)
        self.assertLess(second['rms_position_error'],metrics['rms_position_error'])

    def test_excursion_shortcut_stationary_reverse_and_backtracking_fail_geometry(self):
        v=np.asarray(TASK['goal']['data']['vertices_m']);bad=v.copy();bad[1]+=.006*np.array([1.,0.,-1.])/math.sqrt(2)
        for values,failed in ((bad.tolist(),'tracking_max_error'),(v[[0,2]].tolist(),'path_coverage'),
                ([v[0].tolist()]*3,'path_end'),(v[::-1].tolist(),'path_start'),
                (v[[0,1,0,1,2]].tolist(),'path_progress_regression')):
            out=evaluate(fixture(values))
            self.assertEqual(out.validity,'valid');self.assertFalse(out.task_success)
            self.assertFalse(next(c.satisfied for c in out.constraints if c.name==failed),out)

    def test_missing_incomplete_and_invalid_evidence_are_not_task_failures(self):
        cases=[(fixture(status='failed'),'incomplete'),(fixture([TASK['goal']['data']['vertices_m'][0]]),'incomplete')]
        empty=fixture().model_copy(update=dict(signals=[]));cases.append((empty,'incomplete'))
        for field,value in (('units','mm'),('frame','robot_base'),('phase','sampled_state')):
            raw=plain(fixture());raw['signals'][0]['spec'][field]=value
            cases.append((BackendResult.model_validate(raw),'invalid'))
        for result,validity in cases:
            out=evaluate(result);self.assertEqual(out.validity,validity);self.assertIsNone(out.task_success);self.assertEqual(out.metrics,[])
        raw=plain(fixture());raw['signals'][0]['times_s']=[.1,.1,.2]
        with self.assertRaisesRegex(ValueError,'TIME_NOT_INCREASING'):BackendResult.model_validate(raw)

    def test_bad_reference_units_frames_nodes_or_timed_goal_are_rejected(self):
        for field,value in (('units','mm'),('frame','base'),('vertices_m',[[0,0,0],[0,0,0]]),
                ('vertices_m',[[0,0,0],[1,0,0],[.5,0,0]]),('times_s',[0,.2,.4])):
            task=deepcopy(TASK);task['goal']['data'][field]=value
            with self.assertRaises(ValueError):check_definition(task)
        task=deepcopy(TASK);task['goal']['data'].pop('time_requirement')
        with self.assertRaises(ValueError):check_definition(task)

    def test_math_retains_free_geometry_and_bounds_without_scheduling_reference(self):
        cfg=self.configuration();req=describe_analysis_requirements(cfg,dict(candidate=SOURCE))
        c=req.constraints[0]
        self.assertEqual(c.kind,'path_bound')
        self.assertEqual(c.path_vertices_m,cfg['task']['goal']['data']['vertices_m'])
        self.assertEqual(c.reference,[])
        self.assertEqual(req.physical_inputs['upper'],[t['force_limit_n'] for t in cfg['robot']['structure']['data']['tendons']])
        rows=analysis_capabilities(cfg,req,self.spec['analysis_protocol'],mathematical_methods={CONIC:True,SENSITIVITY:True})
        self.assertTrue(all(r['status']=='not_applicable' for r in rows))
        self.assertTrue(all(not r.get('full_task_supported',False) for r in rows))
        for row in rows:
            for coverage in row.get('coverage', []):
                self.assertEqual(coverage['expressible'], coverage['constraint_id']=='geometric_path')

    def test_pure_math_kernels_do_not_silently_replace_geometry_with_reach(self):
        from tests.research.test_trajectory_feasibility import fixture as affine_fixture
        from extensions.math_analysis.trajectory import trajectory_feasibility
        from extensions.math_analysis.task_capability import task_capability
        from extensions.math_analysis.conic_capability import conic_capability
        model,_,protocol=affine_fixture()
        req=describe_analysis_requirements(self.configuration(),{})
        # A compatible synthetic 3D output still cannot make free progress a fixed norm bound.
        model.endpoint_outputs=[NS(name='tip_position',units='m',frame='world',value0=[0.,0.,0.],C=[[1.],[0.],[0.]],D=[[0.],[0.],[0.]])]
        protocol.period_s=.02
        for kernel in (trajectory_feasibility,task_capability,conic_capability):
            out=kernel(model,req,protocol)
            self.assertEqual(out['status'],'not_applicable',out)
            self.assertFalse(out.get('full_requested_coverage',False))
            self.assertFalse(any(c['analyzed_indices'] for c in out['coverage']))

    def test_robot_analysis_and_composite_acceptance_remain_explicitly_unsupported(self):
        cfg=self.configuration();q=AnalysisRequest(candidate=SOURCE,operation='trajectory_feasibility',protocol=self.spec['analysis_protocol'])
        with patch('extensions.tendon_family.math_analysis.calculate_candidate_configuration',side_effect=AssertionError('NO_ROBOT_WORKER')):
            out=analysis.calculate(cfg,dict(configuration=SOURCE),q)
        self.assertEqual(out['status'],'not_applicable')
        self.assertEqual(out['task_acceptance'],'unmeasured')
        fit=method_admission(dict(canonical_task=TASK,mathematical_methods={CONIC:True},budgets=dict(mathematical_evaluations=8)),q)
        self.assertIn('TRACKING_ROBOT_MODEL_CONSTRUCTION_UNSUPPORTED',fit['reasons'])
        self.assertEqual(task_adapter(cfg).check_compatibility()['technical_compatibility']['status'],'unsupported')
        from tools.research.physical_replay import model_context
        with patch('extensions.tendon_family.backends.physics_for',side_effect=AssertionError('NO_PHYSICS')):
            with self.assertRaisesRegex(ValueError,'GEOMETRIC_TRACKING_PHYSICAL_REPLAY_UNSUPPORTED'):model_context(cfg)
        with self.assertRaisesRegex(ValueError,'TRACKING_COMPOSITE_ACCEPTANCE_UNSUPPORTED'):assemble_acceptance(cfg,None,None)

    def test_intake_reports_registry_without_auto_compilation_or_authority(self):
        from tests.research.test_task_intake import CASES
        text,response=CASES['tracking'];parsed=parse_response(text,json.dumps(response))
        compiled=compile_draft(parsed.draft)
        self.assertFalse(compiled.executable);self.assertIsNone(compiled.configuration_preview)
        self.assertIn('task.tracking',compiled.capabilities['registered_tasks'])
        self.assertEqual(compiled.capabilities['evaluation']['status'],'unsupported')
        self.assertEqual(compiled.capabilities['evaluation']['registered_definition']['evaluator'],'evaluate.tracking')

    def test_optional_timed_evaluator_grid_and_adapter_references(self):
        from extensions.reference.contracts import TrackingGoal
        task=json.loads((ROOT/'tasks/tracking_timed_development.json').read_text(encoding='utf-8'))['task']
        goal=TrackingGoal.model_validate(task['goal']['data']);times=np.arange(1,21)*.02
        values=[goal.at_time(float(t))[0] for t in times]
        out=evaluate(fixture(values,times.tolist(),task=task),task=task)
        self.assertTrue(out.task_success)
        lagged=[goal.at_time(max(0.,float(t)-.2))[0] for t in times]
        self.assertFalse(evaluate(fixture(lagged,times.tolist(),task=task),task=task).task_success)
        self.assertEqual(evaluate(fixture(values[:-1],times[:-1].tolist(),task=task),task=task).validity,'incomplete')
        self.assertEqual(evaluate(fixture(values,(times*2).tolist(),task=task),task=task).validity,'invalid')
        cfg=self.configuration();cfg['task']=task
        adapter=task_adapter(cfg);positions,_=adapter.reference_at(times)
        np.testing.assert_allclose(positions,values,rtol=0,atol=1e-15)
        req=adapter.analysis_requirements({});c=req.constraints[0]
        self.assertEqual(c.kind,'norm_bound');self.assertEqual(c.indices,list(range(1,21)))
        np.testing.assert_allclose(c.reference,values)
        self.assertIsNotNone(adapter.describe()['scoring_interval_s'])
        bad=deepcopy(task);bad['timing']['duration_s']=.41;bad['goal']['data']['times_s'][-1]=.41
        with self.assertRaisesRegex(ValueError,'HORIZON_MISMATCH'):check_definition(bad)

    def test_saved_exact_model_has_conditional_conic_support_without_robot_build(self):
        from tests.research.test_task_analysis_contract import TaskAnalysisTests
        fixture=TaskAnalysisTests();fixture.setUpClass();fixture.setUp()
        model=fixture.fixture_model();cfg=fixture.cfg;cfg['task']=deepcopy(TASK)
        req=task_adapter(cfg).analysis_requirements({})
        model=model.model_copy(update=dict(binding={**model.binding,'task_identity':digest(TASK)},
            operating_point={**model.operating_point,'remaining_task_s':.4}))
        protocol=deepcopy(self.spec['analysis_protocol']);protocol.update(duration_s=.4,period_s=.02)
        rows=analysis_capabilities(cfg,req,protocol,model=model,mathematical_methods={CONIC:True,SENSITIVITY:True})
        conic=next(r for r in rows if r.get('method_version')=='sampled-affine-conic-path-progress-v1')
        self.assertEqual(conic['status'],'conditional');self.assertEqual(conic['kernel_subproblems_per_model'],19)
        self.assertFalse(conic['full_task_supported'])
        self.assertEqual(conic['coverage'][0]['status'],'applicable')
        wrong=model.model_copy(update=dict(binding={**model.binding,'task_identity':'wrong'}))
        rows=analysis_capabilities(cfg,req,protocol,model=wrong,mathematical_methods={CONIC:True})
        self.assertTrue(all(r['status']=='not_applicable' for r in rows))
        partial=model.model_copy(update=dict(operating_point={**model.operating_point,'actual_time_s':.1,'remaining_task_s':.3}))
        rows=analysis_capabilities(cfg,req,protocol,model=partial,mathematical_methods={CONIC:True})
        self.assertTrue(all(r['status']=='not_applicable' for r in rows))


if __name__=='__main__':unittest.main()
