"""Focused risks: physical mapping, exact freeze, proposals and report ownership."""
from copy import deepcopy
import unittest
from tools.research_spec import load_spec, map_initial_state, ResearchSpecification
from tools.fixed_research import baseline_plan, prepare_candidate, proposed_edits, initial_values, _prefer
from tools.platform_tools import simulation_preflight
from tools.platform_tasks import compile_input
from tools.platform_registry import registry
from schemas.platform import SessionInput
from schemas.platform_operations import Simulate
from extensions.tendon_family.gvs_profile import execution_scope


class FixedResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.spec=load_spec()

    def test_exact_frozen_source_and_stopping_policy(self):
        s=self.spec
        self.assertEqual(s['source']['candidate']['execution_id'],'91c3ba1b01d6499fb26df8f95409401b')
        self.assertEqual(s['starting_configuration']['effective']['policy']['controller'],s['execution_template']['policy']['controller'])
        changed=deepcopy(s);changed['execution_template']['policy']['controller']['parameters']['data']['recipe']['max_cpu_s']=1.
        with self.assertRaisesRegex(ValueError,'STARTING_EXECUTION_BINDING_CHANGED'):
            ResearchSpecification.model_validate(changed)

    def test_named_nonzero_velocity_and_structure_mapping(self):
        s=self.spec;case=s['cases'][1]
        initial=map_initial_state(s['execution_template'],case)
        self.assertAlmostEqual(sum(v for k,v in initial['qpos_rad'].items() if k.startswith('near_') and k.endswith('_z')),.01)
        self.assertAlmostEqual(sum(v for k,v in initial['qvel_rad_s'].items() if k.startswith('near_') and k.endswith('_z')),.02)
        a,_=prepare_candidate(s,candidate_id='mapping-length-change',changes={'components/near/length_m':.17},case_id=case['case_id'],seed=18)
        self.assertEqual(a['task']['initializer']['parameters']['data'],initial)
        self.assertEqual(a['seed'],18)
        self.assertEqual(a['task']['sampling']['seeds'],[18])
        self.assertEqual(a['policy']['controller']['parameters'],s['execution_template']['policy']['controller']['parameters'])

    def test_changed_candidate_has_report_owned_scope(self):
        s=self.spec;smoke=s['integration_validation']
        inp,_=prepare_candidate(s,candidate_id='offline-smoke-preflight',changes=smoke['changes'],case_id=smoke['case_id'],seed=17)
        compile_input(inp)
        prepared=simulation_preflight(SessionInput.model_validate(inp),Simulate(candidate_id=inp['run_id'],changes={}),registry())['prepared']
        self.assertEqual(execution_scope(prepared.effective),execution_scope(inp))
        actual=next(c for c in inp['robot']['structure']['data']['components'] if c['id']=='near')
        self.assertEqual(actual['sections'][0]['section']['parameters']['semi_y_m'],.0096)

    def test_plan_and_discrete_proposals_use_frozen_pool(self):
        s=self.spec;plan=baseline_plan(s)
        self.assertEqual(plan['llm_calls'],0)
        variables=s['fixed_baseline']['structural_variables'];centre=initial_values(s,variables)
        proposals=list(proposed_edits(s,variables,centre))
        for point in proposals:
            self.assertEqual(set(point),set(variables))
            for path,value in point.items():
                bounds=s['parameter_grants'][path]
                if isinstance(bounds[0],str):self.assertIn(value,bounds)
                else:self.assertLessEqual(bounds[0],value);self.assertLessEqual(value,bounds[1])
        self.assertTrue(any(p['design/near_material_scenario']=='stiff' for p in proposals))

    def test_incomplete_adaptation_cannot_block_a_later_valid_candidate(self):
        unknown=dict(acceptance=dict(status='incomplete',accepted=None))
        observed=dict(acceptance=dict(status='valid_failure',accepted=False))
        self.assertTrue(_prefer(observed,unknown))
        self.assertFalse(_prefer(unknown,observed))


if __name__=='__main__':unittest.main()
