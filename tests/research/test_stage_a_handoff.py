"""Stage A contracts and real SDK/Mock HTTP discovery; no numerical execution."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
from jsonschema import Draft202012Validator
from tools.research import core
from tools.research.state import state
from tools.research.scientific_intent import question_schema,compile_question
from tools.research.task_constraints import mathematical_method_view,mathematical_opportunity_summary
from tools.research_tasks import task_adapter
from extensions.tendon_family.family_space import decision_summary,parameter_capabilities
from tests.research.test_passive_program_v2 import prepared_host_v2
from tests.research.test_p63g3_action_handoff import diagnosis
from tests.research.test_recent_round_tools import run_fixture
from tests.research.test_information_flow import packet,generation


def dynamic_question(operation='inspect',budget=1):
    return dict(version='scientific_question_v4',domain='structure',structure=dict(operation=operation,
        effect_semantics='finite_time_task_response',target='finite_time_task_violation',
        load_condition='all_frozen_conditions',requested_budget=budget,
        **(dict(parameter_paths=['segments.0.young_pa']) if operation=='differentiate' else {})))


class StageAHandoffTests(unittest.TestCase):
    def setUp(self):
        self.h,self.c=prepared_host_v2(mathematical_budget=5)
        with patch.object(core,'guard'):core.dispatch(self.h,diagnosis(self.c,'mechanism_research'),'stage-a-diagnose')
        for name in ('tools.service_execution._run_contained','mujoco.mj_step'):
            stop=patch(name,side_effect=AssertionError('NO_WORKER_OR_INTEGRATION_IN_CONTRACT_TEST'))
            stop.start();self.addCleanup(stop.stop)

    def test_dynamic_facts_do_not_enter_affine_constraints(self):
        candidate=self.h.store.artifact(self.c);adapter=task_adapter(candidate['configuration'])
        self.assertEqual(adapter.analysis_requirements({}).constraints,[])
        view=mathematical_method_view(self.h,self.c)
        rows=adapter.dynamic_constraint_view()
        self.assertTrue(any(r['constraint_id']=='qualification:lateral:unloaded' for r in rows))
        focus=mathematical_opportunity_summary(view,observations=[dict(constraint_id='evaluator:response_maximum',passed=False)])
        self.assertEqual(focus['current_focus'][0]['constraint_id'],'evaluator:response_maximum')
        self.assertIn('mechanism_structure_v1',[m['method'] for m in focus['methods']])
        self.assertFalse(view['methods']['mechanism_structure_v1']['full_task_supported'])

    def test_passive_parameter_effects_and_exact_topology(self):
        spec=state(self.h)['spec'];candidate=self.h.store.artifact(self.c)
        view=decision_summary(spec['family_space'],{},[])
        self.assertEqual(view['execution_effects']['mode'],'passive_fixed_payout_v1')
        self.assertEqual(view['executable_domain']['payout_bound_tendon_counts'],[1])
        rows={r['parameter_id']:r for r in parameter_capabilities(spec['family_space'],candidate['parameters'])}
        for key in ('pretension_n','length_servo_gain_n_m'):
            self.assertFalse(rows['tendon_parameters.'+key]['effective_in_current_execution'])
        self.assertEqual(rows['segments.0.young_pa']['supported_methods'],['generate','mechanism_structure_v1'])

    def test_schema_compiler_and_cost_use_identical_frozen_program(self):
        schema=question_schema(state(self.h)['spec'],self.h.store.artifact(self.c),'mechanism_research')
        Draft202012Validator.check_schema(schema)
        q=dynamic_question('differentiate',5);Draft202012Validator(schema).validate(q)
        result=compile_question(self.h,q,tool_use_id='stage-a-cost')
        self.assertEqual(result['status'],'ready',result)
        self.assertEqual(result['dynamic_cost_bound'],dict(model_builds=5,episodes=5,physics_steps=2500))
        study=result['request']['mechanism_study']
        self.assertEqual(study['target']['quantity'],'finite_time_task_violation')
        self.assertEqual(study['point_semantics'],'frozen_task_initial_state')
        self.assertFalse(state(self.h)['analysis_results'])

    def test_rejects_wrong_path_mode_load_target_and_budget_without_worker(self):
        before=self.h.store.remaining()
        for changes in [dict(parameter_paths=['segments.99.young_pa']),dict(physical_problem='active_ideal_tension'),
                dict(load_condition='unloaded'),dict(target='response_maximum'),dict(requested_budget=1)]:
            q=dynamic_question('differentiate',5);q['structure'].update(changes)
            result=compile_question(self.h,q,tool_use_id='stage-a-negative')
            self.assertNotEqual(result['status'],'ready',result)
            self.assertFalse(result['scientific_execution_started'])
        self.assertEqual(self.h.store.remaining(),before)

    def test_optional_pair_is_explicit_and_doubles_episode_cost(self):
        q=dynamic_question();q['structure']['passive_ablation']=['tendon_0']
        schema=question_schema(state(self.h)['spec'],self.h.store.artifact(self.c),'mechanism_research')
        Draft202012Validator(schema).validate(q)
        result=compile_question(self.h,q,tool_use_id='stage-a-pair')
        self.assertEqual(result['status'],'ready',result)
        self.assertEqual(result['dynamic_cost_bound'],dict(model_builds=2,episodes=2,physics_steps=1000))
        q['structure']['passive_ablation']=['unowned_limit']
        self.assertNotEqual(compile_question(self.h,q,tool_use_id='stage-a-bad-pair')['status'],'ready')

    def test_foreign_comparison_source_is_rejected_before_reservation(self):
        before=self.h.store.remaining()
        q=dynamic_question('compare',2)
        q['structure']['comparison_candidates']=[dict(artifact_id='f'*64)]
        result=compile_question(self.h,q,tool_use_id='stage-a-foreign-candidate')
        self.assertNotEqual(result['status'],'ready',result)
        self.assertFalse(result['scientific_execution_started'])
        self.assertEqual(self.h.store.remaining(),before)

    def test_sdk_wire_retains_passive_discovery_and_dynamic_schema(self):
        wires=run_fixture(self.h,[('research_route',dict(tool='research_plan',action='diagnose')),
            ('research_plan',diagnosis(self.c,'mechanism_research')),None])
        final=packet(wires[-1]);self.assertTrue(final['mechanism_research']['finite_time_response'])
        schema=next(t['function']['parameters'] for t in wires[-1]['tools'] if t['function']['name']=='research_analysis')
        self.assertIn('finite_time_task_response',json.dumps(schema))
        self.assertNotIn('state_vector',json.dumps(final['mechanism_research']))

    def test_sdk_passive_parent_edit_preserves_all_other_physical_parameters(self):
        from extensions.tendon_family.family_space import resolved_request
        from tools.research.design import set_parameter
        plan=generation(self.h)
        plan.update(generation=dict(changes={'segments.0.young_pa':7330000.}))
        plan['decision']['selected_candidate']=self.c
        wires=run_fixture(self.h,[('research_route',dict(tool='research_plan',action='generate')),('research_plan',plan),None])
        new=next(r for r in state(self.h)['candidates'].values() if r!=self.c)
        space=state(self.h)['spec']['family_space']
        expected=resolved_request(space,self.h.store.artifact(self.c)['parameters'])
        set_parameter(expected,'segments.0.young_pa',7330000.)
        self.assertEqual(resolved_request(space,self.h.store.artifact(new)['parameters']),expected)
        self.assertTrue(packet(wires[-1]))


if __name__=='__main__':unittest.main()
