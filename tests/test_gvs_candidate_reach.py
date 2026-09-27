"""Length candidates must own preparation while task/recipe remain frozen."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from schemas.platform import SessionInput,EvidenceRef
from tools.state_io import digest
from tools.platform_store import plain
from tools.platform_registry import registry
from tools.platform_tools import _candidate
from extensions.tendon_family.backends import physics_for
from extensions.tendon_family.gvs_basis import resolve_basis
from extensions.tendon_family.gvs_profile import checked_reach,reach_numerical,prepare_execution
from extensions.tendon_family.gvs_nmpc import ReachNMPCController,resolve_gvs_nmpc_control,workspace_key
from examples.gvs_design_input import experiment_input
from examples.gvs_nmpc_route_experiment import route_input


class CandidateReachTests(unittest.TestCase):
    def test_candidate_preparation_owns_physics_and_guesses(self):
        baseline=SessionInput.model_validate(experiment_input())
        inp=_candidate(baseline,{'components/near/length_m':.162},registry())
        self.assertEqual(inp.task,baseline.task)
        self.assertEqual(inp.policy.controller,baseline.policy.controller)
        physics=physics_for(inp);control=checked_reach(inp)
        numerical=reach_numerical(inp)
        self.assertNotEqual(physics['identity'],physics_for(baseline)['identity'])
        self.assertEqual(numerical['coordinate_order'],list(resolve_basis(inp.robot.structure.data,control.recipe.basis).coordinate_order))
        self.assertEqual(numerical['tendon_order'],[t['entity'] for t in physics['tendons']])
        self.assertEqual(numerical['force_limits_n'],[t['force_limit_n'] for t in physics['tendons']])
        self.assertEqual(numerical['nominal']['q0'],[0.]*len(numerical['coordinate_order']))
        self.assertFalse(numerical['provenance']['historical_states_reused'])
        self.assertFalse(numerical['provenance']['nominal_is_current_target_solution'])
        self.assertNotEqual(workspace_key(inp.task,inp.robot,control.recipe),workspace_key(baseline.task,baseline.robot,control.recipe))
        controller=ReachNMPCController(inp.policy.controller.parameters.data,.01)
        prepare_execution(SimpleNamespace(save_artifact=lambda v,k:EvidenceRef(artifact_id=digest(v))),controller,inp)
        plan=resolve_gvs_nmpc_control(inp,physics)
        self.assertEqual(plan['numerical_reference']['artifact_id'],digest(controller.profile['numerical']))
        self.assertEqual(controller.preparation['physics_identity'],physics['identity'])
        self.assertEqual(plan['robot'],plain(inp.robot))
        cold=inp.model_copy(deep=True);cold.policy.controller.parameters.data['numerical_source']='initial_state_pretension'
        self.assertEqual(reach_numerical(cold)['nominal']['u0'],[t['pretension_n'] for t in physics['tendons']])

    def test_public_build_solve_free_second_input_and_budget(self):
        from extensions.tendon_family.route import create,view
        from tools.platform_host import Host
        frozen=experiment_input(target_m=(.29,.05,.19))
        value=route_input('design-check',True,task_input=frozen)
        self.assertEqual(value['policy']['route'],frozen['policy']['route'])
        self.assertEqual(value['policy']['budget'],frozen['policy']['budget'])
        root=Path('runs/gvs_candidate_checks')/uuid4().hex;host=Host(root,value['run_id'])
        host.store.create(dict(project_id=uuid4().hex,grant_id=uuid4().hex,
            authorization_source='Solve-free candidate plumbing check',budget=value['policy']['budget']))
        with patch('extensions.tendon_family.gvs_lqr._candidate_operating_point',side_effect=AssertionError('hidden solve')),patch('extensions.tendon_family.gvs_nmpc.TrajectoryWorkspace',side_effect=AssertionError('hidden graph')):
            create(root,value)
            receipt=host.invoke(dict(request_id='build',tool_id='route.advance',reason='Fixture',arguments=dict(
                node_id='build',action='build',combination='candidate_gvs_nmpc',reason='Fixture',next_step='Inspect',
                changes={'components/far/length_m':.118})))
        self.assertEqual(receipt['execution_status'],'completed',receipt)
        result=host.store.artifact(host.store.artifact(receipt['output'])['detail']['result'])
        candidate=SessionInput.model_validate(host.store.artifact(result['configuration']))
        self.assertEqual(plain(candidate.task),value['task'])
        self.assertEqual(plain(candidate.policy.controller),value['policy']['controller'])
        self.assertEqual(reach_numerical(candidate)['provenance']['physics_identity'],physics_for(candidate)['identity'])
        self.assertEqual(view(host)['counts']['solves'],0)


if __name__=='__main__':unittest.main()
