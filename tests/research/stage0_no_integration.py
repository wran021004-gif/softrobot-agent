"""Bounded Stage 0 unittest runner: compilation and synthetic fixtures only."""
from contextlib import ExitStack
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'


MODULES = [
    'tests.research.test_family_space',
    'tests.research.test_mixed_search',
    'tests.research.test_bf7_native_search',
    'tests.research.test_cross_task_integration',
    'tests.research.test_bf4_tracking',
    'tests.research.test_bf5_tool_axis',
    'tests.research.test_bf6_oriented_tracking',
    'tests.research.test_stage0_base_routing',
    'tests.research.test_research_knowledge.KnowledgeTests.test_ppo_rejects_all_three_bf_tasks_before_scene_or_xml',
    'tests.research.test_research_knowledge.KnowledgeTests.test_native_t1_t2_catalog_does_not_inherit_direct_control_task_support',
]
MODULES += ['tests.research.test_native_external_force.ExternalForceTests.' + name for name in (
    'test_tick_boundaries_sum_and_clear_world_com_couple',
    'test_assessment_accepts_only_existing_force_contract_and_grid',
    'test_restore_uses_frozen_force_and_rejects_extra_generalized_force',
    'test_mechanics_includes_com_generalized_force_without_tip_couple',
    'test_task_only_pair_composes_with_original_limits_and_same_robot',
    'test_original_acceptance_keeps_incomplete_separate_from_task_failure',
    'test_six_channel_force_binding_uses_candidate_owned_limits',
)]


def main():
    attempted = []

    def forbidden(name):
        def fail(*args, **kwargs):
            attempted.append(name)
            raise AssertionError('STAGE0_FORBIDS_EXECUTION: ' + name)
        return fail

    original_popen = subprocess.Popen

    def read_only_git(command, *args, **kwargs):
        if (isinstance(command, (list, tuple)) and command and command[0] == 'git'
                and command[1] in ('rev-parse', 'status', 'diff', 'log')):
            return original_popen(command, *args, **kwargs)
        if isinstance(command, str) and command in ('ver', 'command /c ver', 'cmd /c ver'):
            return original_popen(command, *args, **kwargs)
        return forbidden('subprocess.Popen')(command, *args, **kwargs)

    with ExitStack() as stack:
        for name in (
            'mujoco.mj_step', 'mujoco.mj_step1', 'mujoco.mj_step2', 'mujoco.mj_rollout',
            'extensions.tendon_family.mujoco_analysis.NativeModel.rollout',
            'extensions.tendon_family.mujoco_analysis.NativeModel.rollout_sequence',
            'extensions.tendon_family.mujoco_analysis.NativeModel.reconstruct',
            'tools.research.native_control.calculate',
            'tools.service_execution._run_contained',
            'scipy.integrate.solve_ivp', 'httpx.Client.send', 'httpx.AsyncClient.send',
        ):
            # Some MuJoCo distributions expose only the Python rollout module.
            if name == 'mujoco.mj_rollout':
                import mujoco
                if not hasattr(mujoco, 'mj_rollout'):
                    continue
            stack.enter_context(patch(name, side_effect=forbidden(name)))
        stack.enter_context(patch('subprocess.Popen', side_effect=read_only_git))
        names = sys.argv[1:] or MODULES
        suite = unittest.defaultTestLoader.loadTestsFromNames(names)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    print('Stage 0 forbidden execution attempts:', attempted)
    return 0 if result.wasSuccessful() and not attempted else 1


if __name__ == '__main__':
    sys.exit(main())
