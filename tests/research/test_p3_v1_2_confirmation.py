"""Synthetic v1.2 confirmation scope fixtures; no physical or Provider execution."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from schemas.platform import TaskDefinition
from tools.platform_store import plain
from tools.state_io import digest
from extensions.reference.contracts import PassiveResponseEvaluationV2
from extensions.reference.passive_evaluation_v2 import confirmation,stiffness
from extensions.tendon_family.passive_execution import paired_raw,baseline_arm,execute_confirmation
from tests.research.test_p3_study_readiness import small_task,fixture


class TwoCellReplayPolicy(unittest.TestCase):
    def test_fresh_executor_and_frozen_replay_only_policy(self):
        value=plain(small_task())
        value['evaluator']['parameters']['data']['numerical_confirmation']['variants']=[]
        task=TaskDefinition.model_validate(value)
        source=paired_raw(fixture(task),fixture(task,True),Path('synthetic-source'),['tendon_0','tendon_1'],0.)
        def replay(inp,raw,folder):
            return dict(status='verified',integrations=0,raw_identity=digest(raw),traces=raw['trace_files'],
                rows_checked=raw['physics_steps'],route_checked_poses=raw['physics_steps'],maximum_position_difference_m=0.,cost={})
        independent=deepcopy(source)
        with patch('extensions.tendon_family.passive_execution.atomic_json'),patch('mujoco.mj_step',side_effect=AssertionError('PHYSICS_FORBIDDEN')),\
                patch('extensions.tendon_family.passive_execution.execute_pair',return_value=SimpleNamespace(data=SimpleNamespace(data=independent))) as fresh,\
                patch('extensions.tendon_family.passive_execution.execute',side_effect=AssertionError('OPTIONAL_VARIANTS_NOT_REQUIRED')),\
                patch('extensions.tendon_family.passive_execution.replay_saved_traces',side_effect=replay),\
                patch('extensions.tendon_family.passive_execution.backend_result',side_effect=lambda inp,raw:raw):
            raw=execute_confirmation(SimpleNamespace(task=task),'synthetic-independent',source,dict(artifact_id='a'*64),'source-execution')
        self.assertEqual(fresh.call_count,1)
        self.assertEqual(raw['numerical_confirmation']['executions'],{})
        self.assertEqual(set(raw['numerical_confirmation']['saved_state_replay']),{'baseline','ablation'})
        self.assertEqual(confirmation(task,raw),('valid',None))
        raw['numerical_confirmation']['source_execution_id']=raw['numerical_confirmation']['independent_execution_id']
        self.assertEqual(confirmation(task,raw)[0],'invalid')

    def test_legacy_defaults_and_missing_replay_are_preserved(self):
        task=small_task();ev=PassiveResponseEvaluationV2.model_validate(task.evaluator.parameters.data)
        self.assertEqual(ev.numerical_confirmation.variants,('half_timestep','initial_perturbation'))
        self.assertNotIn('variants',plain(ev.numerical_confirmation))
        value=plain(task);value['evaluator']['parameters']['data']['numerical_confirmation']['variants']=[]
        task=TaskDefinition.model_validate(value)
        pair=paired_raw(fixture(task),fixture(task,True),Path('synthetic'),['tendon_0','tendon_1'],0.)
        self.assertEqual(confirmation(task,pair),('incomplete','INDEPENDENT_NUMERICAL_CONFIRMATION_REQUIRED'))


if __name__=='__main__':unittest.main()
