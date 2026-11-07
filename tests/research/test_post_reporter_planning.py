"""Small offline interface checks; scripted choices are fixtures, not autonomy."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from jsonschema import Draft202012Validator
from tools.research import agent,core
from tools.research.config import ROOT,resolve
from tools.research.state import state,update
from tools.research.contracts import FamilyMixedSearch
from tools.research.research_context import information_flow_brief
from tools.research.structure_intent import compile_search
from tools.research.budget import provider_allowance
from tests.research.test_passive_capabilities import passive_host
from tests.research.test_recent_round_tools import run_fixture
from tests.research.test_information_flow import packet

PROFILE=ROOT/'configs/research/study_passive_post_reporter_mixed_search_20261107.json'


def search_plan(candidate):
    return dict(action='search',hypothesis='Offline fixture: varying count and length may change a unilateral static mechanism.',
        expected_observation='Distinct discrete and continuous coordinate proposals.',weakening_observation='Initial qualification fails or no informative response.',
        fixed_conditions='Frozen task, unilateral tendon model and no dynamics.',stopping_condition='Three math evaluations; no task acceptance.',
        interpretation='Offline contract fixture; not a Main research decision.',supporting_evidence=[],
        decision=dict(hypothesis_id='offline-mixed',selected_candidate=candidate,claimed_inference='empirical_search',
            selected_variables=['segment_count','lengths'],requested_budget=3),
        search=dict(version='scientific_structure_search_v1',research_goal='passive_structure_research',
            design_variable_groups=['segment_count','lengths'],evaluation_model='passive_equilibrium',control_treatment='no_active_control',
            proxy_objective='equilibrium_qualification',diagnostic_load_conditions=['unloaded'],
            segment_counts=[2,3],tendon_counts=[3],initial_segment_count=2,initial_tendon_count=3,initial_span_strategy='whole_chain',
            bounds={'length_m':[.08,.14]},structure_search_effort=dict(max_proposals=5,max_evaluations=3)))


def representable_candidate(h):
    """Synthetic choice via the existing mixed generator, not a lossy seed fix."""
    from tools.research.mixed_moves import initial,generation
    from tools.research.design import generate_candidate
    spec=state(h)['spec'];space=spec['family_space']
    q=FamilyMixedSearch.model_validate(dict(version='family_mixed_search_v1',family_space_identity=spec['family_space_identity'],
        variable_groups=['segment_count','lengths'],segment_counts=[2,3],tendon_counts=[3],screening_fidelity='diagnostic',
        objective='equilibrium_qualification',operating_point='standardized_initial_pretension',max_proposals=5,max_evaluations=3,
        evaluation_mode='passive_equilibrium',diagnostic_load_conditions=['unloaded'],bounds={'length_m':[.08,.14]}))
    return generate_candidate(h,generation(space,q,initial(space,q)),dict(origin='offline representable coordinate fixture'))['candidate']


class PostReporterPlanningTests(unittest.TestCase):
    def test_passive_search_batch_reaches_main_and_reporter_without_native_j_fields(self):
        from tools.research.mixed_moves import initial,generation,next_move
        from tools.research.design import generate_candidate
        from tools.research.state import save
        from tools.research.feedback import scientific_result_delivery
        from tools.research.evidence_views import result_card
        with passive_host(PROFILE) as h:
            spec=state(h)['spec'];space=spec['family_space'];seed=representable_candidate(h)
            q=FamilyMixedSearch.model_validate(compile_search(h,search_plan(seed),'offline-projection-query')['search'])
            points=[initial(space,q)];paths=[['family_defaults_and_authorized_ranges']]
            for cursor in (0,1):
                point,changed,_=next_move(space,q,points[-1],cursor,q.step);points.append(point);paths.append(changed)
            rows=[];analyses=[]
            for i,point in enumerate(points):
                ref=generate_candidate(h,generation(space,q,point),dict(origin='offline projection fixture'))['candidate']
                a=save(h,dict(fixture='Synthetic numerical fields only; no scientific Worker',index=i,status='computed',candidate=ref))
                analyses.append(a);qualified=i<2
                conditions={'unloaded':dict(analysis=a,status='computed' if qualified else 'unresolved',score=-.5 if qualified else None,
                    facts=dict(constraint_state=dict(qualified=qualified),qualification_diagnosis=dict(status='qualified' if qualified else 'preflight_failed',failure_layers=[] if qualified else ['tendons'])))}
                rows.append(dict(parameters=h.store.artifact(ref)['parameters'],evidence=dict(candidate=ref,conditions=conditions),
                    computation_status='computed' if qualified else 'unresolved',proxy_values={'equilibrium_qualification':-.5} if qualified else {},
                    mathematical_numerical_s=0.,lineage=dict(variables_or_topology_changed=paths[i])))
            checkpoint=save(h,dict(problem=dict(query=q.model_dump(mode='json'))))
            rows.append(dict(parameters=rows[0]['parameters'],evidence={},computation_status='invalid',
                construction=dict(status='invalid',reason='UNKNOWN_PAYOUT_TENDON'),actual_mathematical_evaluations=0))
            result=dict(physical_problem=dict(diagnostic_only=True),status='best_mathematical_candidate',score_semantics='Offline synthetic qualification fixture; no performance claim',
                termination_reason='evaluation_budget_exhausted',resource_use=dict(actual_mathematical_evaluations=3),
                search_state=checkpoint,evaluated=rows,best_passive_candidate=rows[0])
            ref=save(h,dict(result=result));update(h,analysis_results=analyses,search_results=[ref])
            delivered=scientific_result_delivery(h);fixed=delivered['latest_search']['fixed_result']
            self.assertEqual(len(fixed['structures']),4)
            self.assertEqual(fixed['actual_counts']['evaluated_designs'],3)
            self.assertEqual(fixed['actual_counts']['construction_failures'],1)
            self.assertEqual(fixed['structures'][3]['construction']['reason'],'UNKNOWN_PAYOUT_TENDON')
            self.assertEqual(fixed['structures'][2]['conditions']['unloaded']['failure_layers'],['tendons'])
            self.assertIsNone(delivered['latest_evaluation'])  # Child solves owned by this batch.
            card=result_card(h,ref)
            self.assertEqual(card.deterministic_summary['passive_family_search'],fixed)
            self.assertEqual(h.store.remaining()['used']['model_calls'],0)

    def test_passive_count_decrease_preserves_retained_payouts_without_stale_channels(self):
        from extensions.tendon_family.generated_serial import generate_family
        from tools.research.mixed_moves import initial,generation,reshape
        spec=resolve(PROFILE);space=spec['family_space']
        q=FamilyMixedSearch.model_validate(dict(version='family_mixed_search_v1',family_space_identity=spec['family_space_identity'],
            variable_groups=['tendon_count'],segment_counts=[2],tendon_counts=[3,4],screening_fidelity='diagnostic',
            objective='equilibrium_qualification',operating_point='standardized_initial_pretension',max_proposals=3,max_evaluations=3,
            evaluation_mode='passive_equilibrium',diagnostic_load_conditions=['unloaded']))
        point=initial(space,q);point['tendon_count']=4;point=reshape(space,q,point)
        generation(space,q,point)  # Resolves the actual zero-route payouts, no dynamics.
        retained=deepcopy(point['payout_lengths_m']);self.assertEqual(len(retained),4)
        point['tendon_count']=3;point=reshape(space,q,point)
        request=generation(space,q,point);design,_,_=generate_family(dict(space=space,request=request))
        self.assertEqual(request['payout_lengths_m'],{k:v for k,v in retained.items() if k!='tendon_3'})
        self.assertEqual(len(design['fixed_payout_lengths_m']),3)
        # Direct malformed generation input remains an error; no general repair.
        request['payout_lengths_m']['tendon_3']=retained['tendon_3']
        with self.assertRaisesRegex(ValueError,'UNKNOWN_PAYOUT_TENDON'):generate_family(dict(space=space,request=request))

    def test_finite_time_novelty_and_operator_pause_keep_reporter_available_on_resume(self):
        import asyncio
        from tools.research import reporter
        from schemas.research_reporting import ScientificReport
        def card(artifact,dynamic):
            return dict(identity=dict(result=dict(reference=dict(artifact_id=artifact*64,media_type='application/json'),pointer=''),
                operation='mechanism_structure_v1',task_identity='offline',candidate=None),
                evidence_summary=dict(verification_status='computed'),metrics=[],main_violations=[],mathematics=dict(claim={}),
                deterministic_summary=dict(structure_research=dict(effect_semantics='finite_time_task_response' if dynamic else 'mechanism_effect')))
        old=dict(mode='result_summary',results=[card('a',False)])
        new=dict(mode='result_summary',results=[card('b',True)])
        self.assertEqual(reporter.interpretation_priority(new,[old],decision_v3=True),'new_finite_time_structure_result')
        self.assertEqual(reporter.interpretation_priority(new,[new],decision_v3=True),'routine_or_repeated_result')
        with passive_host(PROFILE) as h:
            from tools.research.state import save
            source=save(h,dict(fixture='Offline pause only; no numerical facts'))
            reporter._save(h,ScientificReport(mode='investigation',question='Offline pause fixture; no numerical facts.',
                results=[dict(identity=dict(result=dict(reference=source,pointer='')),
                    evidence_summary=dict(claim_kind='UNVERIFIED_HYPOTHESIS',verification_status='offline_fixture'))]))
            with patch('tools.research.reporter._wire',side_effect=AssertionError('NO_PROVIDER_REQUEST')):
                asyncio.run(reporter.complete_reports(h,None,max_model_calls=0))
            self.assertEqual(reporter.current_reports(h,status_only=True)[0][1]['interpretation_status'],'deferred')
            self.assertEqual(h.store.remaining()['used']['model_calls'],0)

    def test_direct_plan_original_admission_and_optional_route(self):
        with passive_host(PROFILE) as h:
            c=representable_candidate(h)
            # Only the availability boundary is stubbed; the SDK schema,
            # canonical compiler, original admission and Plan persistence run.
            original=__import__('tools.research.reporter',fromlist=['current_reports']).current_reports
            def available(host,*,status_only=False,limit=None):
                return [(c,dict(interpretation_status='available'))] if status_only else original(host,limit=limit)
            with patch('tools.research.reporter.current_reports',side_effect=available),\
                    patch('tools.research.agent.credential',return_value='offline-fixture'),\
                    patch.object(core,'run_search',return_value=dict(status='OFFLINE_EXECUTION_STUB_ONLY')) as execute:
                wires=run_fixture(h,[('research_plan',search_plan(c)),None],limit=2)
            schema=next(t['function']['parameters'] for t in wires[0]['tools'] if t['function']['name']=='research_plan')
            Draft202012Validator.check_schema(schema)
            self.assertEqual(set(schema['properties']['action']['enum']),{'generate','diagnose','search','stop'})
            self.assertIn('research_route',{t['function']['name'] for t in wires[0]['tools']})
            self.assertIn('search',packet(wires[0])['tool_continuation']['direct_plan']['actions'])
            execute.assert_called_once()
            saved=h.store.artifact(state(h)['plans'][-1])
            self.assertEqual(saved['original_plan']['action'],'search')
            self.assertEqual(saved['original_plan']['search']['variable_groups'],['segment_count','lengths'])
            self.assertEqual(state(h)['mathematical_evaluations'],0)
            self.assertFalse(any(e['kind']=='research_tool_route' for e in h.store.events(h.run_id)))
            # Explicit routes remain valid without submitting a scientific Plan.
            pilot=state(h)['pilot'];update(h,pilot={**pilot,'tool_directory':[dict(tool='research_plan',actions=['search'])]})
            result=agent.select_tool_route(h,dict(tool='research_plan',action='search'),'offline-optional-route')
            self.assertFalse(result['scientific_execution_started'])

    def test_post_result_context_has_sources_choices_and_interpretation_indices(self):
        ref=dict(artifact_id='a'*64,media_type='application/json');candidate=dict(artifact_id='b'*64,media_type='application/json')
        report=dict(report_reference=ref,reporter_status='available',result_references=[ref],findings=[],
            interpretations=[dict(kind='supported_explanation',text='Offline fixture: local support only.',sources=[dict(reference=ref,pointer='/fixture')]),
                dict(kind='unresolved_question',text='Offline fixture: finite response unknown.',sources=[dict(reference=ref,pointer='/fixture')])])
        spec=resolve(PROFILE)
        from tools.research.search import request_guidance
        brief=dict(analysis_interface='scientific_question_v4',latest_reports=[report],post_result_source=dict(reference=ref),
            structure_actions=request_guidance(spec))
        delivered=dict(research_state=dict(current_candidate=candidate,task={}),current_control={},budget={},
            mathematical_research=dict(latest_result=dict(reference=ref)),
            tool_continuation=dict(loaded=dict(plan_actions=['generate','diagnose','search','stop'])))
        before=deepcopy((brief,delivered));view=information_flow_brief(brief,delivered)
        decision=view['post_result_decision']
        self.assertFalse(decision['formal_plan']['route_required'])
        self.assertEqual(decision['candidate'],candidate);self.assertEqual(decision['scientific_evidence'],ref)
        self.assertEqual(len(decision['hypothesis_feedback']),2)
        self.assertIn('lengths',decision['passive_search']['structural_groups'])
        self.assertIn('physical.curvature_y_rad_m',decision['passive_search']['bounds_catalogue']['materials'])
        self.assertIn('six entries',decision['passive_search']['evaluation_cost'])
        self.assertFalse(view['reporter_findings'][0]['scientific_citation_eligible'])
        self.assertEqual((brief,delivered),before)

    def test_stage_review_preserves_reporter_plus_four_ordinary_requests(self):
        # Actual SDK review hook over the one Store counter; no new phase ledger.
        with passive_host(PROFILE) as h:
            read=dict(reference=state(h)['family_space_reference'],view='summary',pointer='/version')
            with patch('tools.research.agent.credential',return_value='offline-fixture'):
                wires=run_fixture(h,[('evidence_read',read)]*9,limit=16,pause_exploration_remaining=5)
            self.assertEqual(len(wires),9)
            allowance=provider_allowance(h)
            self.assertEqual(allowance['remaining_total'],7)
            self.assertEqual(allowance['science_capable_main_requests']-1,4)  # one Reporter send
            remaining=h.store.remaining()
            with patch.object(h.store,'remaining',return_value={**remaining,'remaining':{**remaining['remaining'],'model_calls':2}}):
                self.assertTrue(provider_allowance(h)['protected_current_request'])

    def test_existing_mixed_coordinates_compile_discrete_and_continuous(self):
        from extensions.tendon_family.generated_serial import generate_family
        from tools.research.mixed_moves import initial,generation,next_move,candidate_seed
        with passive_host(PROFILE) as h:
            spec=state(h)['spec'];space=spec['family_space']
            c=representable_candidate(h)
            compiled=compile_search(h,search_plan(c),'offline-coordinate-compile')
            q=FamilyMixedSearch.model_validate(compiled['search']);point=initial(space,q)
            seed=candidate_seed(space,q,h.store.artifact(c))
            reconstructed=generation(space,q,initial(space,q,seed))
            original=h.store.artifact(c)['parameters']
            self.assertEqual(reconstructed['segments'],original['segments'])
            changed=deepcopy(h.store.artifact(c));changed['parameters']['segments']['1']['sections'][-1]['angle_rad']+=.01
            with self.assertRaisesRegex(ValueError,'section rotation'):candidate_seed(space,q,changed)
            first,paths,_=next_move(space,q,point,0,q.step)
            self.assertEqual(paths,['segment_count']);self.assertEqual(first['segment_count'],3)
            second,paths,_=next_move(space,q,first,1,q.step)
            self.assertEqual(paths,['segments.0.length_m'])
            self.assertNotEqual(second['segments']['0']['length_m'],first['segments']['0']['length_m'])
            for p in (point,first,second):generate_family(dict(space=space,request=generation(space,q,p)))
            self.assertEqual(state(h)['mathematical_evaluations'],0)


if __name__=='__main__':unittest.main()
