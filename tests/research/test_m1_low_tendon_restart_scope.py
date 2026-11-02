"""Fresh task/resource scope fixtures; no Provider or scientific Worker."""
import unittest
from unittest.mock import patch
from tools.research import config
from tools.research.conditions import configuration_for_condition
from tools.research.state import state,require_research_authorization
from tools.research.structure_intent import compile_search
from tools.research_tasks import task_adapter
from tools.research.control_correction import task_measure
from tests.research import test_m1_native_search_scope as fixtures

SPEC=config.ROOT/'configs/research/study_m1_low_tendon_speed004_v1.json'


class LowTendonRestartScopeTests(unittest.TestCase):
    def test_new_speed_threshold_reaches_every_condition_without_changing_geometry_or_positions(self):
        old=config.resolve(fixtures.SPEC);new=config.resolve(SPEC)
        self.assertNotEqual(old['resolved_identity'],new['resolved_identity'])
        self.assertNotEqual(old['canonical_task_identity'],new['canonical_task_identity'])
        self.assertEqual(old['family_space_identity'],new['family_space_identity'])
        for key in ('backend','dynamics_model','discretization'):
            self.assertEqual(old['configuration']['policy'][key],new['configuration']['policy'][key])
        for a,b in zip(old['task_conditions'],new['task_conditions']):
            self.assertEqual(a['task']['goal'],b['task']['goal'])
            self.assertEqual(a['task']['timing'],b['task']['timing'])
            self.assertEqual(a['task']['environment'],b['task']['environment'])
            cfg=configuration_for_condition(new['configuration'],b)
            options=task_adapter(cfg).control_search_options()
            self.assertEqual(options['speed_limit'],.04)
            self.assertEqual(options['position_limit'],.01)
            self.assertEqual(options['terminal_position_limit'],.01)
            self.assertAlmostEqual(options['holding_start'],.54)
            # Synthetic threshold fixture, not a task observation or acceptance.
            outputs=dict(times_s=[.54,.60],tip_positions_m=[options['target']]*2,tip_velocities_m_s=[[.035,0,0]]*2)
            self.assertLessEqual(task_measure(outputs,**options)['signed_maximum_excess'],0)
            options['speed_limit']=.03
            self.assertGreater(task_measure(outputs,**options)['signed_maximum_excess'],0)

    def test_fresh_pool_and_exact_authorization_gate(self):
        with patch.object(fixtures,'SPEC',SPEC),fixtures.scoped_fixture() as h:
            s=state(h)
            for key in ('candidates','analysis_results','search_results','physical_replays','scoped_context'):
                self.assertFalse(s.get(key))
            self.assertFalse(s['spec']['research_decisions']['background'])
            self.assertEqual(h.store.remaining()['used']['model_calls'],0)
            self.assertEqual(h.store.remaining()['remaining']['model_calls'],87)
            self.assertIsNone(s['spec']['budgets']['mathematical_evaluations'])
            with self.assertRaisesRegex(ValueError,'INDEPENDENT_FORMAL_STUDY_APPROVAL'):require_research_authorization(h)

    def test_all_registered_mathematics_and_native_effort_are_selectable(self):
        with patch.object(fixtures,'SPEC',SPEC),fixtures.scoped_fixture() as h:
            spec=state(h)['spec']
            self.assertEqual(len(spec['mathematical_methods']),5)
            self.assertTrue({'control_search','execute','search','generate','physical_replay'}<=set(spec['allowed_plan_actions']))
            self.assertEqual(spec['family_search']['segment_counts'],list(range(1,10)))
            self.assertEqual(spec['family_search']['tendon_counts'],list(range(1,8)))
            value=fixtures.proposal(['tendon_count','lengths'],segment_counts=[2],tendon_counts=[1,2,3],initial_tendon_count=1,
                control_search_effort=dict(method='pattern',evaluation_requests=8000,iterations=1000,knot_count=64))
            with patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_WORKER')):
                compiled=compile_search(h,value,'low-tendon-resource-fixture')
            self.assertEqual(compiled['search']['tendon_counts'],[1,2,3])
            self.assertEqual(len(compiled['search']['control_settings']['knots_s']),64)
            self.assertEqual(compiled['search']['control_settings']['iterations'],1000)


if __name__=='__main__':unittest.main()
