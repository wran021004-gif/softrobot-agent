import unittest
from tools.provenance import parameter_provenance
from tools.design_compiler import build_robot_ir
from tools.spec_tools import load_task_package, load_simulator, load_run_settings
from tests.test_architecture import design


class ProvenanceTests(unittest.TestCase):
    def test_values_are_derived_from_authoritative_inputs(self):
        task, env = load_task_package()
        ir = build_robot_ir(design())
        rows = parameter_provenance(design(), ir, task, env, load_simulator(), load_run_settings())
        for name in ('joint_stiffness_nm_per_rad', 'joint_damping_nm_s_per_rad', 'body_density_kg_m3',
                     'tendon_servo_kp_n_per_m', 'tendon_force_limit_n'):
            self.assertEqual(rows[name]['value'], getattr(ir.mechanics, name))
            self.assertIn('legacy_v1_surrogate', rows[name]['source'])
            self.assertIn('not validated', rows[name]['scientific_status'])
        for name, category in [('target_m', 'TASK'), ('gravity_m_s2', 'ENVIRONMENT'),
                               ('segment_length_m', 'ROBOT_DESIGN'), ('tendon_servo_kp_n_per_m', 'ACTUATOR_MODEL'),
                               ('tendon_target_lengths_m', 'CONTROLLER'), ('timestep_s', 'SIMULATOR_NUMERICAL'),
                               ('steps', 'RUN_SETTING')]:
            self.assertEqual(rows[name]['category'], category)
        self.assertIsNone(rows['tendon_target_lengths_m']['value'])
        self.assertEqual(rows['duration_s']['value'], load_run_settings().steps * load_simulator().timestep_s)
        changed = design(segments=10)
        other = parameter_provenance(changed, build_robot_ir(changed), task, env, load_simulator(), load_run_settings())
        self.assertEqual(other['segment_length_m']['value'], changed.total_length_m / changed.segments)
