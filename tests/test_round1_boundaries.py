import copy
import unittest
from unittest.mock import patch
from pydantic import ValidationError
from agents.contracts.outputs import EngineerOutput
from agents.contracts.optimization import validate_optimization_variables, validate_optimization_candidate
from agents.contracts.permissions import can_write, HUMAN_OWNED
from capabilities.registry import get_robot_family_grammar, get_tool_manifest
from tests.test_architecture import design
from tools.spec_tools import ROOT


class OptimizationTests(unittest.TestCase):
    def test_deny_defaults_and_protected_variables(self):
        names = ['unknown', 'target_m', 'position_error_max_m', 'metrics.position_error_m',
                 'gravity_m_s2', 'timestep_s', 'steps', 'joint_stiffness_nm_per_rad',
                 *(n for n in design().model_dump() if n not in ('total_length_m','tendon_routing_radius_m','tendon_count'))]
        for name in names:
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_optimization_variables(design().robot_family, (name,))
        self.assertEqual(validate_optimization_variables(design().robot_family, ()), ())
        self.assertEqual(get_tool_manifest('optimization')['tools']['optimize_design']['implementation_status'], 'IMPLEMENTED')

    def test_engineer_output_rejects_unapproved_selection(self):
        with self.assertRaises(ValidationError):
            EngineerOutput(design_hypothesis=design(), rationale='test', requested_model_level='M1',
                           requested_control_level='C1', optimization_variables=('body_radius_m',), decision='execute')

    def test_approved_mechanism_and_candidate_boundary(self):
        # Synthetic Human policy fixture only; these numbers never enter the grammar.
        grammar = copy.deepcopy(get_robot_family_grammar(design().robot_family))
        grammar.pop('exploration_envelope_source', None)  # Isolate the historical grammar fixture.
        policy = grammar['design_fields']['total_length_m']['optimization']
        policy.update(optimizable=True, lower_bound=0.3, upper_bound=0.5,
                      scientific_status='human_approved', provenance='synthetic unit test approval')
        with patch('agents.contracts.optimization.get_robot_family_grammar', return_value=grammar):
            for length in (0.3, 0.4, 0.5):
                validate_optimization_candidate(design(), design(total_length_m=length), ('total_length_m',))
            for candidate in (design(total_length_m=0.6), design(body_radius_m=0.03)):
                with self.assertRaises(ValueError):
                    validate_optimization_candidate(design(), candidate, ('total_length_m',))
            for change in ({'lower_bound': None}, {'upper_bound': float('inf')},
                           {'scientific_status': 'human_approval_required'}, {'constraints': ['imagined_law']},
                           {'category': 'SIMULATOR_NUMERICAL'}):
                old = policy.copy()
                policy.update(change)
                with self.subTest(change=change), self.assertRaises(ValueError):
                    validate_optimization_variables(design().robot_family, ('total_length_m',))
                policy.clear()
                policy.update(old)
        # Authorization is re-read; a prior approved selection is not a capability token.
        with self.assertRaises(ValueError):
            validate_optimization_candidate(design(), design(total_length_m=0.81), ('total_length_m',))


class PermissionTests(unittest.TestCase):
    def test_windows_normalization_and_escapes(self):
        for name in ('tools/new.py', 'TOOLS/New.py', r'tools\new.py', ROOT / 'tools/new.py'):
            self.assertTrue(can_write('coding', name), name)
        for name in ('../tools/x.py', 'tools/../tools/x.py', r'tools\..\tasks\task.yaml',
                     'D:/outside.py', 'C:/tools/x.py', 'C:tools/x.py', r'\\server\tools\x.py',
                     r'\\?\D:\softrobot-agent\tools\x.py', 'tools/x.py:stream',
                     'tools./x.py', 'tools /x.py', 'tools/NUL', 'tools/COM1.txt',
                     'tools_backup/x.py', 'TOOLS/../runs/run.json'):
            with self.subTest(name=name):
                self.assertFalse(can_write('coding', name))

    def test_roles_and_truth(self):
        for role in ('coding', 'engineer', 'diagnosis', 'unknown'):
            for folder in (*HUMAN_OWNED, 'runs'):
                self.assertFalse(can_write(role, folder.upper() + '/truth.yaml'))
        for role in ('engineer', 'diagnosis'):
            self.assertTrue(can_write(role, f'proposals/{role}/idea.md'))
            self.assertFalse(can_write(role, 'tools/change.py'))
            self.assertFalse(can_write(role, 'proposals/coding/idea.md'))
        self.assertFalse(can_write('coding', 'agents/contracts/optimization.py'))


if __name__ == '__main__':
    unittest.main()
