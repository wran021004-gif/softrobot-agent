"""Small real position-pipeline regressions; no integration or Provider sends."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
import numpy as np
import mujoco
from extensions.tendon_family.passive import PassiveModel
from extensions.tendon_family.passive_equilibrium import solve, initial_qualification, qualification_diagnosis
from tests.research.test_constrained_mechanics import physical_fixture
from tools.research.config import ROOT


class InitialQualificationTests(unittest.TestCase):
    def native(self):
        *_,physics,problem=physical_fixture()
        physics=deepcopy(physics)
        physics['fixed_payout_lengths_m']={t['entity']:length for t,length in zip(physics['tendons'],physics['reference_lengths_m'])}
        return PassiveModel(physics,problem)

    def test_valid_start_and_later_forward_failure_keep_distinct_facts(self):
        native=self.native()
        check=initial_qualification(native,np.zeros(native.model.nv))
        self.assertEqual(check['status'],'passed')
        self.assertEqual(check['cost']['native_position_calls'],1)
        actual=solve(native)
        self.assertEqual(actual['status'],'qualified_local_minimum')
        self.assertGreater(actual['numerical_cost']['native_forward_calls'],0)
        def fail(model,data):raise RuntimeError('offline later-forward fixture')
        with patch.object(mujoco,'mj_forward',new=fail):
            with self.assertRaises(RuntimeError) as error:solve(native)
        diagnosis=qualification_diagnosis(failure=error.exception)
        self.assertEqual(diagnosis['initial_qualification']['status'],'passed')
        self.assertEqual(diagnosis['status'],'initial_forward_failure')
        # The same facts must survive the existing contained Worker exception
        # serializer even outside qualification-only inspect.
        from tests.research.test_cross_task_integration import fixture_directory
        from pathlib import Path
        from tools.research import execution_worker
        with fixture_directory() as folder:
            path=Path(folder)/'request.json'
            path.write_text(json.dumps(dict(kind='candidate_analysis',implementation='offline-fixture',
                configuration={},binding={},query={})))
            with patch.object(execution_worker,'contain_worker_children',return_value=None),\
                    patch('sys.argv',['worker',str(path)]),\
                    patch('tools.research.analysis.calculate',side_effect=error.exception):execution_worker.main()
            saved=json.loads(path.with_name('result.json').read_bytes())
        self.assertEqual(saved['qualification_diagnosis']['initial_qualification']['status'],'passed')
        self.assertEqual(saved['status'],'execution_incomplete')
        from tools.research.analysis import diagnostic_layers
        self.assertEqual(diagnostic_layers(saved)['geometry']['facts']['initial_qualification']['status'],'passed')

    def test_unknown_position_pipeline_continues_original_forward(self):
        native=self.native()
        def no_position(model,data):raise RuntimeError('offline unavailable position fixture')
        def no_forward(model,data):raise RuntimeError('offline forward reached')
        with patch.object(mujoco,'mj_fwdPosition',new=no_position),patch.object(mujoco,'mj_forward',new=no_forward):
            with self.assertRaisesRegex(RuntimeError,'forward reached') as error:solve(native)
        check=error.exception.equilibrium_progress['initial_qualification']
        self.assertEqual(check['status'],'indeterminate')
        self.assertTrue(check['worker']['full_forward_entered'])

    def test_failed_length_is_formal_result_without_full_forward(self):
        native=self.native();native.payout-=.001
        with patch.object(mujoco,'mj_forward') as full,patch.object(mujoco,'mj_step') as step:
            result=solve(native)
        full.assert_not_called();step.assert_not_called()
        self.assertEqual(result['status'],'preflight_failed')
        self.assertEqual(result['numerical_cost']['hessian_columns'],0)
        self.assertEqual(result['numerical_cost']['equilibrium_solves'],0)
        self.assertFalse(result['initial_qualification']['worker']['numerical_solver_started'])
        self.assertEqual(result['task_acceptance'],'unmeasured')

    def test_archived_c_actual_model_stops_before_native_hessian(self):
        path=ROOT/'runs/research/passive-orchestration-20261107-c/analyses/4dd451420cd1439eb94d96eb11b3f550/request.json'
        if not path.exists():self.skipTest('Private archived C request is intentionally not distributed')
        from schemas.platform import SessionInput
        from extensions.tendon_family.backends import physics_for
        from extensions.tendon_family.scene import assemble_physical
        cfg=json.loads(path.read_bytes())['configuration'];inp=SessionInput.model_validate(cfg)
        physics=physics_for(inp);scene=assemble_physical(inp,physics);goal=cfg['task']['goal']['data']
        scene['control']=dict(tension_execution_mode='passive_fixed_payout_v1',solreflimit=goal['solreflimit'],solimplimit=goal['solimplimit'])
        native=PassiveModel(physics,cfg['task']['physical_problem'],scene=scene)
        native.protocol['static_solver'].update(goal['unloaded_static_solver'])
        with patch.object(mujoco,'mj_forward') as full:
            result=solve(native,multistart=goal['unloaded_multistart'])
        full.assert_not_called();p=result['initial_qualification']
        self.assertEqual(p['status'],'failed');self.assertEqual(p['checks']['contacts']['count'],172)
        self.assertLess(p['checks']['contacts']['minimum_distance_m'],-.56)
        np.testing.assert_allclose([t['signed_residual_m'] for t in p['checks']['tendons']],.808)
        self.assertEqual(result['numerical_cost']['optimizer_iterations'],0)

    def test_existing_math_feedback_projects_preflight_with_source(self):
        from tools.research.analysis import diagnostic_layers
        from tools.research.structure_research import summary
        native=self.native();native.payout-=.001;result=solve(native)
        diagnosis=qualification_diagnosis(result)
        raw=dict(status='computed',structure_research=dict(operation='inspect',target=dict(quantity='constraint_active_set'),
            records=[],baseline=dict(status='computed',value=None),qualification_diagnosis=diagnosis,cost=result['numerical_cost'],unsupported_conclusions=['task success']))
        ref=dict(artifact_id='offline-fixture-only')
        layers=diagnostic_layers(raw)
        self.assertEqual(layers['geometry']['status'],'failed')
        self.assertEqual(layers['numerical_solve']['status'],'not_evaluated')
        projected=summary(raw,ref)['qualification_diagnosis']['initial_qualification']
        self.assertEqual(projected['source']['reference'],ref)
        self.assertNotIn('body_poses',projected['checks']['contacts'])
        self.assertEqual(projected['checks']['tendons'][0]['status'],'failed')


if __name__=='__main__':unittest.main()
