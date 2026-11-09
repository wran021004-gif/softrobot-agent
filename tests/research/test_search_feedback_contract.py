"""Actual historical Study grants, schema and admission; no numerical worker."""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from jsonschema import Draft202012Validator

from tools.platform_store import Store,plain
from tools.research.agent import plan_schema
from tools.research.contracts import ScientificStructureSearch,FamilyMixedSearch
from tools.research.search import parse_search,search_problem,search_failure
from tools.research.state import state
from tests.research.test_diagnostic_feedback_repair import ROOT,STORE,REF


@unittest.skipUnless((STORE/'platform.sqlite').exists(),'Private original frozen grants are not installed')
class SearchContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.host=SimpleNamespace(store=Store(STORE),run_id='passive-base-only-full-autonomous-study-20261108-02')
        cls.spec=state(cls.host)['spec']
        cls.candidate=cls.host.store.artifact(REF,paths=('candidate',))['candidate']

    def coordinate(self):
        return dict(version='family_mixed_search_v1',family_space_identity=self.spec['family_space_identity'],
            variable_groups=['lengths'],segment_counts=[4],tendon_counts=[4],span_strategies=['whole_chain'],
            screening_fidelity='diagnostic',objective='equilibrium_qualification',
            operating_point='standardized_initial_pretension',evaluation_mode='passive_equilibrium',
            diagnostic_load_conditions=['unloaded'],bounds={'length_m':[.03,.09]},max_proposals=2,max_evaluations=2)

    def coupled(self):
        return dict(version='family_mixed_search_v2',family_space_identity=self.spec['family_space_identity'],
            previous_candidate_ref=self.candidate,max_evaluations=4,
            analysis=dict(operation='interact',effect_semantics='finite_time_task_response',
                target='finite_time_task_violation',parameter_paths=['segments.0.length_m','segments.1.length_m'],
                parameter_bounds={'segments.0.length_m':[.03,.09],'segments.1.length_m':[.03,.09]},
                operating_point='frozen_task_initial_state',control_treatment='no_active_control',
                physical_problem='passive_unilateral_equilibrium',load_condition='all_frozen_conditions',requested_budget=4))

    def schema(self):
        schema=plan_schema(['search'],decision_required=True,focused=True,study=self.spec)
        return {**schema['properties']['search'],'$defs':schema['$defs']}

    def test_coordinate_typed_schema_and_original_backend_accept(self):
        from tools.research.search import coordinate_proposal
        self.assertEqual(coordinate_proposal(dict(best=[.5],iteration=1,step=.25))['x'],[.25])
        self.assertEqual(coordinate_proposal(dict(best=[.9],iteration=0,step=.25))['x'],[1.])
        q=self.coordinate()
        Draft202012Validator(FamilyMixedSearch.model_json_schema()).validate(q)
        p=search_problem(self.host,q,2)
        self.assertEqual(p['passive_problem']['analyses_per_structure'],1)
        scientific=dict(version='scientific_structure_search_v1',research_goal='passive_structure_research',
            design_variable_groups=['lengths'],evaluation_model='passive_equilibrium',control_treatment='no_active_control',
            structure_search_effort=dict(max_proposals=2,max_evaluations=2),proxy_objective='equilibrium_qualification',
            diagnostic_load_conditions=['unloaded'],segment_counts=[4],tendon_counts=[4],bounds={'length_m':[.03,.09]})
        Draft202012Validator(self.schema()).validate(scientific)
        ScientificStructureSearch.model_validate(scientific)
        for field in ('segment_counts','tendon_counts'):
            missing={k:v for k,v in scientific.items() if k!=field}
            self.assertFalse(Draft202012Validator(self.schema()).is_valid(missing))
        misplaced={**scientific,'max_evaluations':8}
        self.assertFalse(Draft202012Validator(self.schema()).is_valid(misplaced))

    def test_coupled_actual_main_schema_and_complete_backend_admission(self):
        q=self.coupled();Draft202012Validator(self.schema()).validate(q)
        from tools.research.object_choices import main_tool_schema,expand_references
        schema=main_tool_schema(plan_schema(['search'],decision_required=True,focused=True,study=self.spec),
            {'candidate_1':self.candidate})
        # The actual last-mile Main wire uses aliases and binds the frozen
        # FamilySpace identity only after schema validation.
        wire={**q,'previous_candidate_ref':'candidate_1'};wire.pop('family_space_identity')
        Draft202012Validator({**schema['properties']['search'],'$defs':schema['$defs']}).validate(wire)
        expanded=expand_references(dict(search=wire),schema)['search']
        expanded['family_space_identity']=self.spec['family_space_identity']
        self.assertEqual(plain(parse_search(expanded)),plain(parse_search(q)))
        parse_search(q);problem=search_problem(self.host,q,4)
        self.assertEqual(problem['max_evaluations'],4);self.assertEqual(len(problem['points']),4)
        self.assertEqual(problem['analysis_request']['mechanism_study']['operation'],'interact')
        with self.assertRaisesRegex(ValueError,'ALL_FOUR'):search_problem(self.host,q,3)
        for operation,budget in [('optimize',4),('interact',8),('interact',12),('interact',20)]:
            bad=deepcopy(q);bad['analysis'].update(operation=operation,requested_budget=budget)
            self.assertFalse(Draft202012Validator(self.schema()).is_valid(bad))
            with self.assertRaises(ValueError):parse_search(bad)
            repair=search_failure(bad,ValueError('fixture'))
            self.assertEqual(repair['error_code'],'INVALID_SEARCH_REQUEST')
            self.assertTrue(repair['retryable']);self.assertLess(len(str(repair)),1200)
        for budget in (3,8):
            bad={**q,'max_evaluations':budget}
            self.assertFalse(Draft202012Validator(self.schema()).is_valid(bad))

    def test_finite_bounds_domain_and_lossless_seed_reject_before_worker(self):
        q=self.coordinate()
        for bounds,code in [({},'FINITE_SEARCH_BOUNDS_REQUIRED'),({'length_m':[-1,.09]},'SEARCH_BOUND_OUTSIDE_SELECTED_PHYSICAL_DOMAIN')]:
            with self.assertRaisesRegex(ValueError,code):search_problem(self.host,{**q,'bounds':bounds},2)
        # The real historical candidate uses complex station geometry, which
        # must never be silently projected into the coordinate representation.
        bad={**q,'previous_candidate_ref':self.candidate}
        with self.assertRaisesRegex(ValueError,'SEARCH_SEED_NOT_REPRESENTABLE_USE_GENERATE'):search_problem(self.host,bad,2)
        repair=search_failure(bad,ValueError('SEARCH_SEED_NOT_REPRESENTABLE_USE_GENERATE: section rotation'))
        self.assertIn('generate',repair['issues'][0]['expected'])


if __name__=='__main__':unittest.main()
