"""Focused prior-baseline identity and import seam checks; no simulation."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from examples.stage352_settling_campaign import verify_baseline,CONFIG
from tools.state_io import read
from tools.improvement_workflow import MODE_LIMITS


class BaselineReuseTests(unittest.TestCase):
    def test_saved_identity_scope_and_rejected_substitution(self):
        config=read(CONFIG)
        with patch('tools.diagnostic_improvement.complete_execution',side_effect=AssertionError('No baseline simulation')):
            verified=verify_baseline(config)
        self.assertEqual(verified['source']['execution_id'],config['execution_id'])
        self.assertEqual(verified['source']['owner'],'gvs-stage351-baseline-executor')
        self.assertEqual(verified['historical_usage']['backend_solves'],1)
        self.assertTrue(all(k==v for k,v in verified['artifact_hashes'].items()))
        self.assertEqual(verified['recipe']['terminal_tip_speed_weight'],0.)
        self.assertEqual(verified['recipe']['holding_tip_speed_weight'],0.)
        wrong=deepcopy(config);wrong['configuration_artifact']='0'*64
        with self.assertRaisesRegex(ValueError,'PRIOR_BASELINE_REFERENCE_MISMATCH'):verify_baseline(wrong)
        self.assertEqual(MODE_LIMITS,dict(model_calls=24,tool_calls=60,wall_s=3600.,backend_solves=1,worker_calls=0))
