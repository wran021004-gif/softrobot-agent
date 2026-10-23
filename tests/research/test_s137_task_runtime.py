"""S137: synthetic saved signals and frozen snapshots, no engines/providers."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from schemas.platform import SessionInput
from tools.research.config import (ROOT, resolve, effective_input,
                                   configuration_ownership, same_robot_structure)
from tools.research_tasks import task_adapter, assemble_acceptance
from tests.research.test_tracking import TASK, evaluate, fixture


class TaskRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = resolve(ROOT/'configs/research/study.json')
        cls.timed = json.loads((ROOT/'tasks/tracking_timed_development.json').read_text(encoding='utf-8'))['task']

    def configuration(self, task=None):
        cfg = deepcopy(self.spec['configuration'])
        if task is not None:
            cfg['task'] = deepcopy(task)
        return cfg

    def test_all_saved_envelopes_use_the_effective_snapshot_without_reload(self):
        cfg = self.configuration()
        expected = task_adapter(cfg).analysis_requirements({})
        values = [cfg, SessionInput.model_validate(cfg), self.spec, dict(input=cfg),
                  dict(effective=cfg), dict(effective=dict(configuration=cfg))]
        with patch('tools.research.config.read', side_effect=AssertionError('must not reload sources')):
            for value in values:
                with self.subTest(envelope=type(value).__name__):
                    self.assertEqual(effective_input(value), cfg)
                    self.assertEqual(task_adapter(value).analysis_requirements({}), expected)

    def test_reach_terminal_hold_and_physical_requirements_remain_distinct(self):
        adapter = task_adapter(self.spec)
        rows = adapter.condition_view()['conditions']
        self.assertEqual([r['condition_id'] for r in rows],
                         ['terminal_error_m', 'holding_max_error_m', 'holding_max_speed_m_s'])
        self.assertEqual([r['limit'] for r in rows], [.01, .01, .02])
        self.assertEqual(rows[0]['sampling']['time_s'], .35)
        self.assertAlmostEqual(rows[1]['sampling']['window_s'][0], .3)
        self.assertEqual(rows[2]['signal']['units'], 'm/s')
        self.assertEqual(rows[2]['signal']['frame'], 'world')
        self.assertIn('absolute world', rows[2]['meaning'])
        req = adapter.analysis_requirements({})
        self.assertEqual([r.radius for r in req.constraints], [r['limit'] for r in rows])
        self.assertEqual(req.constraints[1].indices, list(range(30, 36)))
        execution = adapter.execution_requirements()
        self.assertEqual(execution['protocol_id'], 'offline_reach_hold_v1')
        self.assertIn('holding_coverage', execution['protocol_components'])
        self.assertIn('force_bounds', execution['protocol_components'])
        self.assertEqual(execution['physical_inputs'], req.physical_inputs)
        self.assertEqual(execution['selected_bindings']['controller'],
                         dict(extension_id='controller.gvs_nmpc', version='11.0.0'))
        self.assertEqual(adapter.control_reference()['kind'], 'constant')

    def test_untimed_conditions_match_the_independent_evaluator_without_deadline(self):
        cfg = self.configuration(TASK)
        adapter = task_adapter(cfg)
        view = adapter.condition_view()
        ev = evaluate()
        self.assertEqual({r['condition_id']: r['limit'] for r in view['conditions']},
                         {r.name: r.limit for r in ev.constraints})
        self.assertEqual(len(view['conditions']), 5)
        self.assertTrue(all(r['expressibility'] == 'proxy_only' for r in view['conditions']))
        self.assertTrue(all('no speed bound or arrival deadline' in r['sampling']['time_semantics']
                            for r in view['conditions']))
        self.assertEqual(adapter.control_reference()['kind'], 'free_progress')
        self.assertEqual(adapter.execution_requirements()['protocol_id'], 'development_tracking_v1')
        self.assertEqual(adapter.execution_requirements()['signals'], TASK['observations'])
        self.assertEqual({c.constraint_id for c in adapter.analysis_requirements({}).constraints if c.kind == 'unsupported'},
                         {r['condition_id'] for r in view['conditions']})
        self.assertTrue(evaluate(fixture(times=[.1, 2., 100.])).task_success)

    def test_timed_position_conditions_follow_only_the_scored_window(self):
        task = deepcopy(self.timed)
        task['sampling']['window_s'] = [.04, .2]
        adapter = task_adapter(self.configuration(task))
        rows = adapter.condition_view()['conditions']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['condition_id'], 'tracking_max_error')
        self.assertEqual(rows[0]['sampling']['window_s'], [.04, .2])
        self.assertEqual(rows[0]['expressibility'], 'sampled_norm_bound')
        req = adapter.analysis_requirements({})
        self.assertEqual(req.constraints[0].indices, list(range(2, 11)))
        positions, velocities = adapter.reference_at([.04, .2])
        self.assertEqual(positions[0].tolist(), req.constraints[0].reference[0])
        self.assertEqual(positions[1].tolist(), req.constraints[0].reference[-1])
        self.assertEqual(velocities.shape, (2, 3))
        self.assertEqual(adapter.control_reference()['kind'], 'timed')
        self.assertIsNone(adapter.execution_requirements()['protocol_id'])
        self.assertTrue(adapter.execution_requirements()['missing'])

    def test_task_only_references_do_not_invent_frozen_hold_or_execution_data(self):
        for task, kind in ((self.spec['configuration']['task'], 'constant'), (TASK, 'free_progress'), (self.timed, 'timed')):
            for envelope in (dict(task=task), task):
                adapter = task_adapter(envelope)
                self.assertEqual(adapter.control_reference()['kind'], kind)
                self.assertFalse(adapter.execution_requirements()['configuration_available'])
                self.assertIsNone(adapter.execution_requirements()['protocol_id'])
                self.assertEqual(adapter.execution_requirements()['selected_bindings'], {})
                with self.assertRaisesRegex(ValueError, 'EFFECTIVE_CONFIGURATION_REQUIRED'):
                    adapter.analysis_requirements({})
        reach = task_adapter(dict(task=self.spec['configuration']['task'])).condition_view()
        self.assertEqual(len(reach['conditions']), 1)
        self.assertTrue(reach['missing'])

    def test_control_weights_do_not_change_hard_limits_or_acceptance(self):
        for task in (None, TASK, self.timed):
            before = self.configuration(task)
            after = deepcopy(before)
            after['policy']['controller']['parameters']['data']['recipe'].update(
                tracking_weight=7., terminal_weight=11., holding_tip_speed_weight=0., horizon=7)
            self.assertEqual(task_adapter(before).condition_view(), task_adapter(after).condition_view())
            self.assertEqual(task_adapter(before).analysis_requirements({}).constraints,
                             task_adapter(after).analysis_requirements({}).constraints)
        cfg = self.configuration(TASK)
        cfg['task']['status'] = 'development_valid'
        cfg['policy']['controller']['version'] = '12.0.0'
        changed = deepcopy(cfg)
        changed['policy']['controller']['parameters']['data']['recipe']['tracking_weight'] = 100.
        profile = dict(complete=True, solver_error_count=0, force_bound_violation_n=0,
                       tracking_sampling_complete=True)
        result = evaluate(task=cfg['task'])
        self.assertEqual(assemble_acceptance(cfg, result, profile), assemble_acceptance(changed, result, profile))
        from tools.research.config import rl_configuration
        reward = rl_configuration(self.spec['control']['rl_defaults'], reward=dict(position=9., holding_speed=0.))
        self.assertEqual(reward['reward']['position'], 9.)
        self.assertEqual(task_adapter(cfg).condition_view(), task_adapter(changed).condition_view())

    def test_structure_comparison_and_configuration_ownership(self):
        reach = self.configuration()
        tracking = self.configuration(TASK)
        tracking['policy']['controller']['parameters']['data']['recipe']['tracking_weight'] = 13.
        self.assertTrue(same_robot_structure(reach, tracking))
        changed = deepcopy(tracking)
        changed['robot']['structure']['data']['tendons'][0]['force_limit_n'] += 1.
        self.assertFalse(same_robot_structure(reach, changed))
        changed = deepcopy(tracking)
        segment = next(c for c in changed['robot']['structure']['data']['components'] if c['kind'] == 'flexible_segment')
        segment['length_m'] += .001
        self.assertFalse(same_robot_structure(reach, changed))
        owners = configuration_ownership(self.spec)
        self.assertEqual(owners['budget']['study'], self.spec['budgets'])
        self.assertTrue(all(k.startswith('segments.') for k in owners['structure']['grant']))
        self.assertEqual(owners['control']['grant']['holding_tip_speed_weight'],
                         self.spec['allowed_parameters']['holding_tip_speed_weight'])
        self.assertEqual({**owners['structure']['grant'], **owners['control']['grant']}, self.spec['allowed_parameters'])
        self.assertEqual(owners['algorithm_authorization']['capabilities'], self.spec['capabilities'])
        self.assertIn('/policy/controller/parameters/data/settling', owners['frozen_acceptance']['paths'])

    def test_condition_bindings_select_real_results_and_math_coverage(self):
        from tools.platform_registry import registry
        from tools.platform_tasks import check_definition
        from tests.research.test_tracking import SOURCE
        cfg = self.configuration()
        task = check_definition(cfg['task'])
        target = task.goal.data['target_m']
        times = [i*.01 for i in range(1, 36)]
        reach = registry().get('evaluate.reach', kind='evaluator').resolve()(
            task, fixture([target]*35, times=times, task=cfg['task']), SOURCE, registry(), 'synthetic')
        timed_task = check_definition(self.timed)
        times = [i*.02 for i in range(1, 21)]
        positions = [registry().parse(timed_task.goal).at_time(t)[0] for t in times]
        timed = evaluate(fixture(positions, times=times, task=self.timed), task=self.timed)
        for configuration, result in ((cfg, reach), (self.configuration(TASK), evaluate()),
                                      (self.configuration(self.timed), timed)):
            adapter = task_adapter(configuration)
            requirements = {c.constraint_id: c for c in adapter.analysis_requirements({}).constraints}
            for row in adapter.condition_view()['conditions']:
                binding, math = row['evaluation_binding'], row['mathematical_binding']
                constraint = requirements[math['constraint_id']]
                if binding['source'] == 'EvaluationResult':
                    observed = next(c for c in result.constraints if c.name == binding['constraint'])
                    self.assertEqual(observed.limit, row['limit'])
                    if binding['metric'] is not None:
                        self.assertEqual(observed.observed, next(m.value for m in result.metrics if m.name == binding['metric']))
                    else:
                        self.assertEqual(row['condition_id'], 'path_start')
                        self.assertIsNone(row['metric'])
                        self.assertNotIn('path_start', {m.name for m in result.metrics})
                if math['coverage'] == 'unsupported':
                    self.assertEqual(constraint.kind, 'unsupported')
                    self.assertEqual(requirements[math['proxy_constraint_id']].kind, 'path_bound')
                else:
                    self.assertEqual(math['coverage'], 'exact_sampled_expression')
                    self.assertEqual(constraint.kind, 'norm_bound')
            if configuration['task'] == self.timed:
                self.assertEqual(row['condition_id'], 'tracking_max_error')
                self.assertEqual(math['constraint_id'], 'timed_tracking')
        # Existing saved F3 acceptance/Profile, read only; no recomputed physics.
        folder = ROOT/'evidence/f3_formal/closeout_20261023'
        audit = json.loads((folder/'audit.json').read_text(encoding='utf-8'))
        artifacts = json.loads((folder/'artifacts.json').read_text(encoding='utf-8'))
        selected = artifacts[audit['references']['selected']['artifact_id']]
        for row in task_adapter(cfg).condition_view()['conditions'][1:]:
            binding = row['evaluation_binding']
            self.assertEqual(binding['source'], 'research.task_acceptance')
            value = selected['profile']
            for part in binding['profile_pointer'].strip('/').split('/'):
                value = value[part]
            self.assertEqual(value, selected['acceptance']['metrics'][binding['metric']])
            self.assertEqual(value, selected['acceptance']['components'][binding['component']]['value'])
            self.assertNotIn(row['metric'], {m.name for m in reach.metrics})

    def test_known_protocol_never_claims_execution_admission(self):
        for task in (None, TASK, self.timed):
            cfg = self.configuration(task)
            cfg['task']['status'] = 'draft'
            adapter = task_adapter(cfg)
            view = adapter.execution_requirements()
            self.assertFalse(view['task_reviewed'])
            self.assertTrue(view['configuration_available'])
            self.assertEqual(view['configuration_check'], 'not_checked')
            self.assertEqual(view['capability_check'], 'not_checked')
            self.assertEqual(view['execution_admission'], 'not_assessed')
            self.assertTrue(any('drafts cannot execute' in r for r in view['known_blockers']))
            self.assertEqual(view['protocol_id'], view['protocol_template_id'])
            self.assertEqual(adapter.check_compatibility()['technical_compatibility']['status'], 'unsupported')
            if task == self.timed:
                self.assertIsNone(view['protocol_template_id'])
            cfg['task']['status'] = 'development_valid'
            reviewed = task_adapter(cfg).execution_requirements()
            self.assertTrue(reviewed['task_reviewed'])
            self.assertEqual(reviewed['execution_admission'], 'not_assessed')
        task_only = task_adapter(dict(task=TASK)).execution_requirements()
        self.assertEqual(task_only['protocol_template_id'], 'development_tracking_v1')
        self.assertIsNone(task_only['protocol_id'])
        self.assertTrue(task_only['known_blockers'])

    def test_family_domains_generator_and_study_grants_remain_separate(self):
        from extensions.tendon_family.family_space import decision_summary
        for filename in ('study_family_space_dev.json', 'study_mixed_family_search_dev.json', 'topology.json'):
            spec = resolve(ROOT/'configs/research'/filename)
            before = deepcopy(spec)
            with patch('tools.research.config.read', side_effect=AssertionError('must not reload sources')):
                owners = configuration_ownership(spec)
            structure = owners['structure']
            self.assertEqual(spec, before)
            self.assertEqual(structure['topology_authorization'], spec.get('topology_authorization'))
            self.assertEqual(structure['family_search'], spec.get('family_search'))
            self.assertEqual(owners['algorithm_authorization']['actions'], spec['allowed_plan_actions'])
            self.assertEqual(owners['budget']['study']['physical_launches'], 0)
            if 'family_space' in spec:
                space = spec['family_space']
                summary = decision_summary(space, None, [])
                self.assertEqual(structure['design_space']['segment_domain'], summary['segment_domain'])
                self.assertEqual(structure['generator_capability'], summary['executable_domain'])
                self.assertEqual(owners['control']['family_domains'], summary['control_domains'])
                self.assertNotIn('control_domains', structure['design_space'])
                self.assertEqual(structure['grant'], {})
                self.assertTrue(structure['declared_only']['tendon_counts'])
                if filename == 'study_family_space_dev.json':
                    self.assertIn(1, structure['declared_only']['segment_counts'])
                    self.assertIsNone(structure['family_search'])
                else:
                    self.assertEqual(structure['family_search']['segment_counts'], [1, 2, 3])
                    self.assertNotIn('control', structure['family_search']['variable_groups'])
            else:
                self.assertIsNone(structure['design_space'])
                self.assertTrue(structure['grant'])
                self.assertEqual(structure['topology_authorization']['tendon_count_bounds'], [5, 7])
                self.assertIn('patch', ' '.join(structure['generator_capability']['parameters']))
        unknown = configuration_ownership(self.configuration())
        self.assertIsNone(unknown['structure']['grant'])
        self.assertIsNone(unknown['structure']['topology_authorization'])


if __name__ == '__main__':
    unittest.main()
