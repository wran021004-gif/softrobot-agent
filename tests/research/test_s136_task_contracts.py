"""S136 contract regressions; synthetic saved data, no physical execution."""
from copy import deepcopy
import json
import unittest

from schemas.platform_analysis import TaskAnalysisRequirement
from tools.platform_tasks import check_definition
from tools.platform_store import plain
from tools.research.config import ROOT, resolve
from tools.research_tasks import task_adapter
from tools.state_io import digest
from tools.task_intake import compile_draft, parse_response
from tests.research.test_tracking import TASK, evaluate, fixture


class TaskContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.configuration = resolve(ROOT/'configs/research/study.json')['configuration']
        cls.timed = json.loads((ROOT/'tasks/tracking_timed_development.json').read_text(encoding='utf-8'))['task']

    def adapter(self, task=TASK):
        cfg = deepcopy(self.configuration)
        cfg['task'] = deepcopy(task)
        return task_adapter(cfg)

    def test_every_geometric_acceptance_condition_survives_translation(self):
        adapter = self.adapter()
        requirement = adapter.analysis_requirements({'candidate_id': 'synthetic'})
        expected = {row.name for row in evaluate().constraints}
        retained = {row.constraint_id: row for row in requirement.constraints if row.kind == 'unsupported'}
        self.assertEqual(set(retained), expected)
        self.assertEqual(requirement.constraints[0].kind, 'path_bound')
        for name, row in retained.items():
            payload = row.unsupported_requirement
            self.assertEqual(payload['condition'], name)
            self.assertEqual(payload['evaluator'], TASK['evaluator'])
            self.assertEqual(payload['goal'], TASK['goal'])
            self.assertEqual(payload['limit'], TASK['evaluator']['parameters']['data']['max_error_m'])
            self.assertEqual(payload['units'], 'm')
            self.assertEqual(row.signal.model_dump(), plain(check_definition(TASK).observations[0]))
            self.assertIn('/task/evaluator/parameters', row.provenance)
        self.assertEqual(requirement.binding['task_identity'], digest(adapter.task))
        self.assertEqual(requirement.binding['effective_configuration_identity'], digest(adapter.configuration))
        self.assertEqual(TaskAnalysisRequirement.model_validate_json(requirement.model_dump_json()), requirement)

    def test_conic_proxy_can_solve_without_claiming_retained_conditions(self):
        from tests.research.test_tracking_math import problem
        from extensions.math_analysis.conic_capability import conic_capability
        model, req, protocol = problem()
        retained = self.adapter().analysis_requirements({}).constraints[1:]
        retained = [row.model_copy(update={'indices': req.constraints[0].indices,
            'reference': [[0.]*3 for _ in req.constraints[0].indices]}) for row in retained]
        req = req.model_copy(update={'constraints': [*req.constraints, *retained]})
        out = conic_capability(model, req, protocol)
        self.assertEqual(out['status'], 'feasible_witness', out)
        self.assertFalse(out['full_requested_coverage'])
        self.assertFalse(out['all_requested_checked'])
        coverage = {row['constraint_id']: row for row in out['coverage']}
        for row in retained:
            self.assertEqual(coverage[row.constraint_id]['analyzed_indices'], [])
            self.assertEqual(coverage[row.constraint_id]['unchecked_indices'], row.indices)

    def test_objectives_are_preferences_and_do_not_change_acceptance_or_math(self):
        changed = deepcopy(TASK)
        changed['objectives'] = [dict(metric='rms_position_error', direction='maximize', units='m', weight=7.)]
        # Incomplete stationary path has zero nearest-path error and still fails completion.
        positions = [TASK['goal']['data']['vertices_m'][0]]*3
        before = evaluate(fixture(positions))
        after = evaluate(fixture(positions, task=changed), task=changed)
        self.assertFalse(after.task_success)
        self.assertEqual(before.constraints, after.constraints)
        self.assertNotIn('rms_position_error', {row.name for row in after.constraints})
        self.assertEqual(self.adapter().analysis_requirements({}).constraints,
                         self.adapter(changed).analysis_requirements({}).constraints)

    def test_timed_metric_must_be_emitted_by_timed_evaluator(self):
        changed = deepcopy(self.timed)
        changed['objectives'] = [dict(metric='path_coverage_error', direction='minimize', units='m')]
        with self.assertRaisesRegex(ValueError, 'TRACKING_METRIC_OR_UNIT_UNAVAILABLE'):
            check_definition(changed)
        changed['goal'] = deepcopy(TASK['goal'])
        self.assertEqual(check_definition(changed).family, 'task.tracking')

    def test_horizon_roles_and_explicit_timed_reference(self):
        untimed = self.adapter().analysis_requirements({})
        self.assertEqual(untimed.horizon_semantics, 'numerical_witness_horizon_inclusive_samples')
        self.assertEqual(untimed.constraints[0].reference, [])
        later = deepcopy(TASK)
        later['timing']['duration_s'] = 4.
        other = self.adapter(later).analysis_requirements({})
        self.assertEqual(other.horizon_semantics, untimed.horizon_semantics)
        self.assertEqual(other.constraints[0].path_vertices_m, untimed.constraints[0].path_vertices_m)
        self.assertTrue(evaluate(fixture(times=[.1, 2., 100.])).task_success)
        timed = self.adapter(self.timed).analysis_requirements({})
        self.assertEqual(timed.horizon_semantics, 'absolute_task_time_inclusive_samples')
        self.assertEqual(timed.constraints[0].indices, list(range(1, 21)))
        self.assertEqual(timed.constraints[0].reference[9], self.timed['goal']['data']['vertices_m'][1])
        self.assertEqual(timed.constraints[0].reference[-1], self.timed['goal']['data']['vertices_m'][-1])

    def test_reach_legacy_holding_owner_and_input_bounds_are_unchanged(self):
        cfg = deepcopy(self.configuration)
        before = task_adapter(cfg).analysis_requirements({})
        changed = deepcopy(cfg)
        changed['policy']['controller']['parameters']['data']['recipe']['horizon'] = 7
        after = task_adapter(changed).analysis_requirements({})
        self.assertEqual(before.constraints, after.constraints)
        self.assertEqual(before.horizon_semantics, 'absolute_task_time_inclusive_samples')
        self.assertEqual([c.radius for c in before.constraints], [.01, .01, .02])
        self.assertEqual([c.indices for c in before.constraints], [[35], list(range(30, 36)), list(range(30, 36))])
        self.assertEqual(before.physical_inputs['tendon_order'], [t['id'] for t in cfg['robot']['structure']['data']['tendons']])
        self.assertEqual(before.physical_inputs['upper'], [t['force_limit_n'] for t in cfg['robot']['structure']['data']['tendons']])
        self.assertEqual(before.constraints[2].signal.units, 'm/s')

    def test_intake_registration_is_not_compilation_or_execution(self):
        from tests.research.test_task_intake import CASES
        text, response = CASES['tracking']
        draft = parse_response(text, json.dumps(response)).draft
        preview = compile_draft(draft)
        self.assertFalse(draft.executable)
        self.assertFalse(preview.executable)
        self.assertIsNone(preview.configuration_preview)
        self.assertIn('explicitly timed', preview.capabilities['evaluation']['registered_definition']['scope'])
        for task in (TASK, self.timed):
            developed = deepcopy(task)
            developed['status'] = 'development_valid'
            self.assertEqual(self.adapter(developed).check_compatibility()['technical_compatibility']['status'], 'unsupported')


if __name__ == '__main__':
    unittest.main()
