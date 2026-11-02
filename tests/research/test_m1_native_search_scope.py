"""Expanded scope: synthetic callbacks, original admissions, zero real Worker."""
from contextlib import contextmanager
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
from uuid import uuid4
from tools.research import core,search,analysis
from tools.research.config import ROOT,resolve
from tools.research.state import state,update,save,require_research_authorization
from tools.research.contracts import FamilyMixedSearch,REGISTERED_MATHEMATICS_SCOPE
from tools.research.structure_intent import compile_search,StructureChoiceError
from tools.research.mixed_moves import initial,candidate_seed,generation
from tools.research.design import generate_candidate
from tools.platform_store import plain
from tools.state_io import digest
from tests.research.test_cross_task_integration import fixture_directory,plan
from tests.research.test_research_authorization_preflight import approve
from tests.research import test_bf7_native_search as native_fixture
from tests.research.test_recent_round_tools import run_fixture

SPEC=ROOT/'configs/research/study_m1_elevated_native_search_v1.json'


@contextmanager
def scoped_fixture():
    spec=resolve(SPEC);spec=deepcopy(spec);spec['study_id']='search-scope-fixture-'+uuid4().hex[:8]
    spec['configuration']['run_id']=spec['study_id'];spec.pop('resolved_identity');spec['resolved_identity']=digest(spec)
    with fixture_directory() as folder,patch('tools.research.config.resolve',return_value=spec):
        h=core.prepare(directory=folder);update(h,freeze='synthetic-offline-scope',pilot={**state(h)['pilot'],'session_handoff_live_admitted':True,'session_handoff_boundary':'request_feedback'})
        # Production bind imports the frozen archive before Main sees its references.
        from tools.research.research_context import import_history
        import_history(h)
        yield h


def proposal(groups=None,**changes):
    q=dict(version='scientific_structure_search_v1',research_goal='structure_control_codesign',
        design_variable_groups=groups or ['lengths'],evaluation_model='native_mujoco',control_treatment='reoptimized',
        segment_counts=[3],tendon_counts=[4],structure_search_effort=dict(max_proposals=2,max_evaluations=6),
        initial_tension_n=.2,control_search_effort=dict(method='pattern',iterations=1,knot_count=2,evaluation_requests=2))
    q.update(changes);return plan('search',search=q)


class M1NativeSearchScopeTests(unittest.TestCase):
    def test_scope_grants_only_remainder_and_requires_original_exact_authorization(self):
        spec=resolve(SPEC)
        self.assertEqual(spec['family_search']['evaluation_modes'],['mujoco_control'])
        self.assertEqual(spec['family_search']['segment_counts'],list(range(1,10)))
        self.assertEqual(spec['family_search']['tendon_counts'],list(range(1,8)))
        self.assertEqual([spec['budgets'][k] for k in ('provider_requests','public_operations','mathematical_evaluations','physical_launches')],[87,569,78,18])
        self.assertEqual(spec['fidelity_policy']['screening']['standard'],spec['fidelity_policy']['final_evaluation'])
        self.assertEqual(spec['fidelity_policy']['final_evaluation']['cells_per_segment'],12)
        with scoped_fixture() as h:
            with self.assertRaisesRegex(ValueError,'INDEPENDENT_FORMAL_STUDY_APPROVAL'):require_research_authorization(h)
            self.assertEqual(h.store.remaining()['used']['model_calls'],0)

    def test_schema_and_guidance_expose_only_frozen_span_strategies(self):
        from tools.research.agent import plan_schema
        from extensions.tendon_family.family_space import span_strategies
        spec=resolve(SPEC);allowed=span_strategies(spec['family_space'])
        schema=plan_schema(['search'],decision_required=True,family_version='serial_family_space_v2',study=spec)
        variants=schema['$defs']['ScientificStructureSearch']['properties']['span_strategies']['anyOf']
        self.assertEqual(next(b['items']['enum'] for b in variants if b.get('type')=='array'),allowed)
        self.assertEqual(search.request_guidance(spec)['search']['applicable_span_strategies'],allowed)
        with scoped_fixture() as h:
            with self.assertRaises(StructureChoiceError) as caught:
                compile_search(h,proposal(span_strategies=['whole_chain','distal']),'forbidden-span')
            self.assertEqual(caught.exception.issues[0]['choices'],allowed)

    def test_no_historical_raw_context_or_acceptance_is_imported(self):
        from tools.research.research_context import import_history
        from tools.research.design import verify_candidate
        with scoped_fixture() as h:
            before=h.store.remaining();import_history(h);s=state(h)
            self.assertEqual(s['spec']['research_decisions']['background'],[])
            self.assertEqual(s['scoped_context'],[])
            self.assertFalse(s['candidates']);self.assertFalse(s['analysis_results']);self.assertFalse(s['physical_replays'])
            self.assertEqual(s['mathematical_evaluations'],0);self.assertEqual(h.store.remaining(),before)
            self.assertIsNone(s['reference_candidate'])

    def test_fixed_topology_continuous_block_changes_structure_and_evaluates_all_conditions(self):
        with scoped_fixture() as h,patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_WORKER')):
            p=compile_search(h,proposal(bounds={'length_m':[.11,.18]}),'fixed-block')
            with patch.object(analysis,'dispatch',side_effect=native_fixture.NativeMixedSearchTests().scored):
                out=search.run_search(h,p['search'],'fixed-block',guard=lambda *a:None,execute=None,capacity=None)
            rows=out['result']['evaluated'];self.assertEqual(len(rows),2)
            self.assertNotEqual(rows[0]['parameters']['segments']['0']['length_m'],rows[1]['parameters']['segments']['0']['length_m'])
            self.assertEqual(state(h)['mathematical_evaluations'],6);self.assertEqual(len(state(h)['control_initializations']),6)
            sources=[]
            for row in rows:
                self.assertEqual(len(row['evidence']['conditions']),3);self.assertEqual(row['task_acceptance'],'unmeasured')
                sources += [v['control_source'] for v in row['evidence']['conditions'].values()]
            self.assertEqual(len({r['artifact_id'] for r in sources}),6)
            self.assertIn('comparison_scope',out['result']);self.assertFalse(state(h).get('success_gate'));self.assertFalse(state(h)['physical_replays'])
            with patch.object(analysis,'dispatch',side_effect=AssertionError('NO_RECOMPUTE')):
                again=search.run_search(h,p['search'],'same-query-new-id',guard=lambda *a:None,execute=None,capacity=None)
            self.assertTrue(again['reused']);self.assertEqual(state(h)['mathematical_evaluations'],6)

    def test_main_selects_mixed_start_independently_of_list_order(self):
        with scoped_fixture() as h:
            value=proposal(['segment_count','tendon_count'],segment_counts=[1,3,9],tendon_counts=[1,4,7],
                structure_search_effort=dict(max_proposals=3,max_evaluations=9))
            with self.assertRaises(StructureChoiceError):compile_search(h,value,'missing-start')
            value['search'].update(initial_segment_count=3,initial_tendon_count=4)
            p=compile_search(h,value,'mixed-start');q=FamilyMixedSearch.model_validate(p['search'])
            point=initial(state(h)['spec']['family_space'],q)
            reverse=q.model_copy(update=dict(segment_counts=list(reversed(q.segment_counts)),tendon_counts=list(reversed(q.tendon_counts))))
            self.assertEqual(initial(state(h)['spec']['family_space'],reverse),point)
            self.assertEqual((point['segment_count'],point['tendon_count']),(3,4))
            with patch.object(analysis,'dispatch',side_effect=native_fixture.NativeMixedSearchTests().scored):
                out=search.run_search(h,p['search'],'mixed-start',guard=lambda *a:None,execute=None,capacity=None)
            points=[(r['parameters']['segment_count'],r['parameters']['tendon_count']) for r in out['result']['evaluated']]
            self.assertEqual(points[0],(3,4));self.assertGreater(len({n for n,t in points}),1);self.assertGreater(len({t for n,t in points}),1)

    def test_candidate_seed_preserves_representable_routing_instead_of_resetting_it(self):
        with scoped_fixture() as h:
            p=compile_search(h,proposal(),'seed-source');q=FamilyMixedSearch.model_validate(p['search']);space=state(h)['spec']['family_space']
            point=initial(space,q);point['routing']['phase_rad']=.3;point['radii_m']=[.022]*4
            ref=generate_candidate(h,generation(space,q,point),dict(origin='synthetic seed fixture'))['candidate'];c=h.store.artifact(ref)
            seed=candidate_seed(space,q,c);reconstructed=generation(space,q,initial(space,q,seed))
            new=generate_candidate(h,reconstructed,dict(origin='synthetic seed verification'))['candidate']
            self.assertEqual(h.store.artifact(new)['configuration']['robot'],c['configuration']['robot'])
            self.assertEqual(state(h)['mathematical_evaluations'],0)

    def test_insufficient_three_condition_budget_rejected_before_generation(self):
        with scoped_fixture() as h,patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_WORKER')):
            update(h,mathematical_evaluations=76)
            with self.assertRaisesRegex(ValueError,'ALL_CONDITIONS'):
                compile_search(h,proposal(),'cannot-fit-three')
            self.assertFalse(state(h)['candidates']);self.assertFalse(state(h).get('control_initializations'))

    def test_unknown_worker_outcome_blocks_a_new_search_without_relaunch(self):
        from tools.research.state import guard
        with scoped_fixture() as h,patch.object(analysis,'dispatch',side_effect=AssertionError('NO_RELAUNCH')):
            approve(h,[REGISTERED_MATHEMATICS_SCOPE]);p=compile_search(h,proposal(),'unknown-block')
            update(h,pending=dict(request_id='synthetic-unknown-worker'))
            with self.assertRaisesRegex(ValueError,'PENDING_EXECUTION_RECOVER'):
                search.run_search(h,p['search'],'new-id',guard=guard,execute=None,capacity=None)
            self.assertEqual(state(h)['mathematical_evaluations'],0)

    def test_actual_mock_provider_schema_delivers_search_results_to_main(self):
        def scored(host,query,key,**kwargs):
            out=native_fixture.NativeMixedSearchTests().scored(host,query,key,**kwargs)
            value=host.store.artifact(out['reference']);t=value['nonlinear_capability']
            t.update(method='mujoco-nonlinear-task-capability-v1',status='computed',best_found_J=t['J'],search_quality=dict(fixture=True,convergence='unresolved'),
                improvement=t['initial_J']-t['J'],physics_steps=0,response_steps_completed=0)
            value['native_dynamics']['optimization']=dict(best=dict(measure=dict(signed_maximum_excess=t['J']),task_gap=dict(accepted=False,valid_complete=True)))
            ref=save(host,value,'synthetic_complete_delivery_fixture')
            update(host,analysis_results=[ref if r==out['reference'] else r for r in state(host)['analysis_results']])
            return dict(reference=ref)
        with scoped_fixture() as h:
            approve(h,[REGISTERED_MATHEMATICS_SCOPE]);value=proposal()
            with patch('tools.research.agent.credential',return_value='offline'),patch.object(core,'guard'),patch('tools.research.state.guard'), \
                    patch.object(analysis,'dispatch',side_effect=scored), \
                    patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_WORKER')):
                sent=run_fixture(h,[('research_route',dict(tool='research_plan',action='search')),('research_plan',value),None],limit=3)
            schema=next(t['function']['parameters'] for t in sent[1]['tools'] if t['function']['name']=='research_plan')
            self.assertIn('ScientificStructureSearch',schema.get('$defs',{}))
            self.assertEqual(len(state(h)['search_results']),1)
            packet=json.loads(sent[-1]['messages'][-1]['content'].split('\n',1)[1])['research']
            self.assertIn('search',json.dumps(packet));self.assertEqual(state(h)['mathematical_evaluations'],6)


if __name__=='__main__':unittest.main()
