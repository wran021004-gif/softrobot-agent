"""Read-only historical and synthetic decision checks; no Provider or Worker."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
from tools.research.evidence_views import native_search_summary
from tools.research.research_context import research_opportunity_review
from tools.research.core import read_tool_evidence
from tools.research.agent import plan_schema
from tools.research.state import state,update
from tests.research.m1_stop_review import historical_decision
from tests.research.test_research_authorization_preflight import fixture


class ResearchOpportunityTests(unittest.TestCase):
    def test_real_pre_stop_coverage_delivery_and_ledger_are_preserved(self):
        h,wire,source=historical_decision();before=deepcopy(h.store.store.session(h.run_id)['state'])
        ledger=h.store.store.remaining()
        with patch('httpx.Client.send',side_effect=AssertionError('NO_PROVIDER')),patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_WORKER')):
            view=read_tool_evidence(h,dict(reference=state(h)['family_space_reference'],view='working_set',pointer='/research_opportunities'),record_read=False)
        self.assertEqual(view['version'],'research_opportunity_review_v1')
        self.assertFalse(view['full_independent_acceptance']);self.assertEqual(view['coverage']['physical_structures'],2)
        self.assertEqual(len(view['conditions']),6)
        self.assertFalse(view['comparison']['cross_structure_common_task'])
        by={(tuple(r['topology']),r['condition']):r for r in view['conditions']}
        self.assertEqual(by[(3,4),'positive_high']['control_studies'],5)
        self.assertEqual(by[(3,6),'negative_low']['control_studies'],3)
        self.assertEqual(by[(3,6),'central_high']['control_studies'],0)
        self.assertEqual(view['remaining']['mathematics'],78)
        self.assertNotIn('search',view['allowed_plan_actions'])
        self.assertEqual(view['finite_control_searches']['stop_reasons'],dict(iteration_limit=4,evaluation_request_budget=4))
        self.assertLessEqual(len(json.dumps(view,separators=(',',':')).encode()),4096)
        self.assertEqual(h.store.store.session(h.run_id)['state'],before)
        self.assertEqual(h.store.store.remaining(),ledger)

    def test_recorded_effort_is_not_convergence_or_global_infeasibility(self):
        opt=dict(stop_reason='evaluation_request_budget',iterations_started=4,search_dimension=24,
            cost_feedback=dict(evaluation_callbacks=80,request_budget=80),
            candidates=[dict(label='baseline',measure=dict(normalized_gap=35.6))],
            best=dict(measure=dict(normalized_gap=31.65),task_gap=dict(accepted=False)))
        value=dict(native_dynamics=dict(optimization=opt))
        row=native_search_summary(value,dict(artifact_id='fixture'))
        self.assertEqual(row['callbacks'],80);self.assertEqual(row['baseline']['normalized_gap'],35.6)
        self.assertFalse(row['model_predicates_passed']);self.assertNotIn('converged',row)
        self.assertIsNone(native_search_summary({},dict(artifact_id='fixture')))

    def test_empty_study_keeps_stop_and_no_forced_research_direction(self):
        with fixture() as h:
            view=research_opportunity_review(h)
            self.assertFalse(view['full_independent_acceptance']);self.assertEqual(view['conditions'],[])
            self.assertIn('stop',view['allowed_plan_actions'])
            schema=plan_schema(['stop'],decision_required=True,focused=True,study=state(h)['spec'])
            self.assertEqual(schema['properties']['action']['enum'],['stop'])
            self.assertIn('considered legal alternatives',schema['properties']['interpretation']['description'])
            self.assertNotIn('next_structure',schema['properties'])

    def test_existing_native_search_handles_open_topology_and_all_conditions_offline(self):
        from tools.research import search,analysis
        from tools.research.structure_intent import compile_search
        from tools.research.config import ROOT
        from tests.research.test_bf7_native_search import NativeMixedSearchTests
        from tests.research.test_cross_task_integration import plan
        with fixture() as h:
            spec=deepcopy(state(h)['spec'])
            grant=json.loads((ROOT/'configs/research/study_family_mujoco_search.json').read_text())['family_search']
            grant.update(segment_counts=list(range(1,10)),tendon_counts=list(range(1,8)))
            spec.update(family_search=grant)
            from tools.state_io import digest
            cfg=spec['configuration'];backend=cfg['policy']['backend']
            fidelity=dict(cells_per_segment=12,backend=backend['extension_id']+'@'+backend['version'])
            policy=dict(version='numerical_fidelity_v1',screening=dict(standard=fidelity),final_evaluation=fidelity,
                require_exact_fidelity=True,alternative_runtimes=[],runtime_preflight_limit=0)
            spec.update(fidelity_policy=policy,final_evaluation_identity=digest(dict(policy=policy,backend=backend,
                task=spec['canonical_task'],controller=cfg['policy']['controller'],model=cfg['policy']['dynamics_model'])))
            spec['research_decisions']['structure_search_interface']='scientific_structure_search_v1'
            spec['capabilities']+=['search'];spec['allowed_plan_actions']+=['search']
            update(h,spec=spec)
            value=plan('search',search=dict(version='scientific_structure_search_v1',research_goal='structure_control_codesign',
                design_variable_groups=['segment_count','tendon_count'],evaluation_model='native_mujoco',control_treatment='reoptimized',
                initial_tension_n=.2,structure_search_effort=dict(max_proposals=3,max_evaluations=9),
                control_search_effort=dict(method='pattern',iterations=1,knot_count=2,evaluation_requests=2)))
            value=compile_search(h,value,'offline-open-search')
            scorer=NativeMixedSearchTests().scored
            with patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_WORKER')),patch.object(analysis,'dispatch',side_effect=scorer):
                out=search.run_search(h,value['search'],'offline-open-search',guard=lambda *a:None,execute=None,capacity=None)
            self.assertEqual(state(h)['mathematical_evaluations'],9)
            self.assertEqual(len(state(h)['control_initializations']),9)
            self.assertEqual(state(h)['physical_replays'],[])
            topologies={(h.store.artifact(r)['parameters']['segment_count'],h.store.artifact(r)['parameters']['tendon_count']) for r in state(h)['candidates'].values()}
            self.assertGreater(len({n for n,t in topologies}),1);self.assertGreater(len({t for n,t in topologies}),1)
