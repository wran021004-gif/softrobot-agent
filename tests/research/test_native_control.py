"""Changed native control boundaries; fixtures are not scientific evidence."""
from copy import deepcopy
import unittest
from tools.platform_store import plain
from tools.research.contracts import AnalysisRequest
from tools.research.native_analysis import applicability, assessment
from tools.research.local_control_search import search
from tests.research.test_mujoco_analysis import NativeAnalysisTests
from tests.research.test_local_control_search import LocalSearchTests, start
from schemas.platform import SessionInput


class NativeControlTests(unittest.TestCase):
    def test_schema_requires_source_and_explicit_v2_window(self):
        NativeAnalysisTests.setUpClass();f=NativeAnalysisTests();f.setUp()
        q=plain(f.q);q['operation']='mujoco_direct_control_v1'
        with self.assertRaises(ValueError):AnalysisRequest.model_validate(q)
        q['control_optimization']=dict(source=f.t.ref,settings=dict(version='local_control_search_v2',
            knots_s=[.30,.34],correction_window_s=[.30,.35]))
        query=AnalysisRequest.model_validate(q)
        inp=SessionInput.model_validate(f.t.cfg)
        fit=applicability(f.t.req,query,assessment(inp,f.t.req),dict(actual_time_s=.30,integration_state=[1]))
        self.assertFalse(fit['full_task_supported'])
        q['control_optimization']['settings']['correction_window_s']=[.31,.35]
        q['control_optimization']['settings']['knots_s']=[.31,.34]
        query=AnalysisRequest.model_validate(q)
        fit=applicability(f.t.req,query,assessment(inp,f.t.req),dict(actual_time_s=.31,integration_state=[1]))
        self.assertTrue(any('All task' in r for r in fit['reasons']))

    def test_native_stop_does_not_claim_physical_acceptance(self):
        f=LocalSearchTests();f.setUp();callback=f.evaluator()
        def evaluate(*args):
            row=callback(*args);row['task_gap']['accepted']=False
            return row
        result=search([start()],evaluate,dict(evaluation_requests=15),evaluation_kind='native_short_rollout',
            stop_when=lambda row:row['task_gap']['normalized_gap']==0)
        self.assertEqual(result['stop_reason'],'local_target_reached')
        self.assertFalse(result['best']['task_gap']['accepted'])
        self.assertEqual(result['cost_feedback']['new_physical_evaluations'],0)
        self.assertTrue(result['best']['local_solver']['success'])


if __name__=='__main__':unittest.main()
