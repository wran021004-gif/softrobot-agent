"""M3-C3 interface fixtures. Scores/crashes below are synthetic, never science."""
from copy import deepcopy
import gc
import json
import shutil
import unittest
from unittest.mock import patch
from uuid import uuid4

from schemas.platform import ProjectConfig
from tools.research import core, design, analysis, search
from tools.research.config import ROOT, resolve
from tools.research.contracts import FamilyMixedSearch, Plan, AnalysisRequest
from tools.research.state import state, update, save
from tools.platform_store import plain
from tools.state_io import digest


def request(spec, **changes):
    return dict(version='family_mixed_search_v1',family_space_identity=spec['family_space_identity'],
        variable_groups=['segment_count','tendon_count','spans','lengths','routing'],
        segment_counts=[1,2,3],tendon_counts=[3,4],span_strategies=['whole_chain','distributed_consecutive'],
        screening_fidelity='coarse',objective='target_equilibrium_residual',operating_point='target_equilibrium',
        max_proposals=12,max_evaluations=8,**changes)


def plan(q):
    return dict(action='search',search=q,hypothesis='Synthetic fixture of feedback selection',
        expected_observation='Bounded proposals',weakening_observation='Unavailable score',
        fixed_conditions='Frozen family, task, fidelity',stopping_condition='Finite counts',
        interpretation='Interface test; fabricated scores are not scientific evidence')


class MixedSearchTests(unittest.TestCase):
    def setUp(self):
        self.folder=ROOT/'runs'/('mixed-fixture-'+uuid4().hex)
        fixture=lambda **v:ProjectConfig(**{**v,'project_id':self.folder.name,'grant_id':self.folder.name})
        with patch.object(core,'ProjectConfig',side_effect=fixture):
            self.host=core.prepare(ROOT/'configs/research/study_mixed_family_search_dev.json',self.folder)
        self.spec=state(self.host)['spec']
        self.addCleanup(self.cleanup)

    def cleanup(self):
        gc.collect()
        if self.folder.resolve().parent!=(ROOT/'runs').resolve():raise ValueError('WORKSPACE_FIXTURE_REQUIRED')
        if self.folder.exists():shutil.rmtree(self.folder)

    def generate(self, **changes):
        return design.generate_candidate(self.host,dict(version='serial_family_generation_v2',
            family_space_identity=self.spec['family_space_identity'],segment_count=2,tendon_count=3),
            dict(origin='synthetic_test'),**changes)

    def scored(self, host, query, key, **kwargs):
        c=design.verify_candidate(host,query['candidate'])
        p=c['parameters']
        # Explicit synthetic preference for two segments, extra tendon and shorter root.
        score=abs(p['segment_count']-2)+1/p['tendon_count']+c['resolved_parameters']['segments'][0]['length_m']
        value=dict(status='computed',proxy_values={'target_equilibrium_residual':score},
            operation_key=key+'-analysis',
            candidate=query['candidate'],requested_operation=plain(AnalysisRequest.model_validate(query)),
            charged_numerical_s=0.,charged_analysis_evaluations=1,fixture=True)
        ref=save(host,value,'synthetic_analysis_fixture')
        s=state(host)
        update(host,analysis_results=[*s['analysis_results'],ref],mathematical_evaluations=s['mathematical_evaluations']+1)
        return dict(reference=ref)

    def run_scored(self, q=None, key='fixture-search'):
        with patch.object(core,'guard'),patch.object(analysis,'dispatch',side_effect=self.scored):
            return core.dispatch(self.host,plan(q or request(self.spec)),key)

    def test_fidelity_physical_binding_and_immutable_study(self):
        a=self.generate(screening_fidelity='coarse');b=self.generate(screening_fidelity='standard')
        self.assertEqual(a['status'],'generated');self.assertEqual(b['status'],'generated')
        ca=design.verify_candidate(self.host,a['candidate']);cb=design.verify_candidate(self.host,b['candidate'])
        self.assertEqual(ca['physical_design_identity'],cb['physical_design_identity'])
        self.assertNotEqual(ca['identity'],cb['identity'])
        self.assertNotEqual(ca['numerical_model_identity'],cb['numerical_model_identity'])
        self.assertFalse(design.final_fidelity_matches(self.spec,ca))
        self.assertTrue(design.final_fidelity_matches(self.spec,cb))
        self.assertEqual(self.generate(screening_fidelity='unauthorized')['status'],'invalid')
        with self.assertRaisesRegex(ValueError,'CANNOT_CHANGE_FROZEN'):
            with patch.object(core.subprocess,'check_output',return_value=''):
                core.bind(self.host,specification={**self.spec,'final_evaluation_identity':'changed'})
        self.assertFalse(state(self.host).get('success_gate'))

    def test_search_contract_and_legacy_identities(self):
        q=FamilyMixedSearch.model_validate(request(self.spec))
        self.assertIsInstance(Plan.model_validate(plan(plain(q))).search,FamilyMixedSearch)
        self.assertEqual(self.spec['family_space']['segment_count_bounds'],[1,9])
        self.assertIsNone(state(self.host)['reference_candidate'])
        for bounds in ({'cells':(1,4)},{'length_m':(.01,.4)}):
            with self.assertRaises(ValueError):search.search_problem(self.host,q.model_copy(update=dict(bounds=bounds)),1)
        with self.assertRaises(ValueError):FamilyMixedSearch.model_validate({**request(self.spec),'variable_groups':['control']})
        with self.assertRaises(ValueError):search.search_problem(self.host,q.model_copy(update=dict(segment_counts=[4])),1)
        search.search_problem(self.host,q.model_copy(update=dict(variable_groups=[*q.variable_groups,'sections'],
            bounds={'section.rectangle.width_y_m':(.007,.016)})),1)
        old=resolve(ROOT/'configs/research/study.json')
        self.assertEqual(digest(old['configuration']),'31af3e097ad29fef1ffd74c5178a6267fc5ffe35889c63e98f531dd42c0df69e')
        self.assertEqual(search.coordinate_proposal(dict(best=[.5],iteration=1,step=.25))['x'],[.25])

    def test_feedback_lineage_conditional_coordinates_and_reuse(self):
        out=self.run_scored();rows=out['result']['result']['evaluated']
        self.assertGreater(len({r['parameters']['segment_count'] for r in rows}),1)
        self.assertGreater(len({r['parameters']['tendon_count'] for r in rows}),1)
        self.assertGreater(len({r['parameters']['segments']['0']['length_m'] for r in rows}),1)
        self.assertGreater(len({digest(r['parameters']['spans']) for r in rows}),2)
        self.assertIsNone(rows[0]['lineage']['previous_candidate_ref'])
        self.assertEqual(rows[0]['lineage']['evidence_used'],[])
        # Two-segment proposal beats the initial one; next tendon move uses that score.
        self.assertEqual(rows[2]['lineage']['previous_candidate_ref'],rows[1]['evidence']['candidate'])
        self.assertEqual(rows[2]['lineage']['evidence_used'],[rows[1]['evidence']['analysis']])
        for row in rows:
            self.assertEqual(len(row['point']['segments']),row['parameters']['segment_count'])
            self.assertEqual(row['lineage']['origin'],'optimizer_internal')
            self.assertEqual(self.host.store.artifact(row['evidence']['analysis'])['candidate'],row['evidence']['candidate'])
        used=state(self.host)['mathematical_evaluations']
        self.run_scored(key='same-query-new-plan')
        self.assertEqual(state(self.host)['mathematical_evaluations'],used)
        self.assertIsNone(state(self.host)['pending'])

    def test_proposal_changes_when_feedback_changes(self):
        from tools.research.mixed_moves import initial,next_move
        q=FamilyMixedSearch.model_validate(request(self.spec));space=self.spec['family_space']
        first=initial(space,q);neighbor,_,_=next_move(space,q,first,0,.25)
        after_good,_,_=next_move(space,q,neighbor,1,.25)
        after_bad,_,_=next_move(space,q,first,1,.25)
        self.assertEqual(after_good['segment_count'],2)
        self.assertEqual(after_bad['segment_count'],1)
        self.assertNotEqual(after_good,after_bad)

    def test_pending_checkpoint_recovery_reuses_sealed_analysis(self):
        q=request(self.spec);q.update(max_evaluations=2)
        original=self.scored;calls=[]
        def interrupted(*args,**kwargs):
            result=original(*args,**kwargs);calls.append(result)
            raise RuntimeError('fixture interruption after immutable score')
        with patch.object(analysis,'dispatch',side_effect=interrupted):
            with self.assertRaises(RuntimeError):
                search.run_search(self.host,q,'pending',guard=lambda *a:None,execute=None,capacity=None)
        self.assertIsNotNone(state(self.host)['searches']['pending']['pending'])
        with patch.object(analysis,'dispatch',side_effect=original):
            output=search.run_search(self.host,q,'recovery',guard=lambda *a:None,execute=None,capacity=None)
        self.assertEqual(output['result']['evaluated'][0]['evidence']['analysis'],calls[0]['reference'])
        self.assertEqual(output['result']['evaluated'][0]['actual_mathematical_evaluations'],1)
        self.assertEqual(output['result']['evaluated'][0]['lineage']['cost']['additional_evaluations'],0)
        self.assertEqual(state(self.host)['mathematical_evaluations'],2)
        self.assertEqual(output['result']['resource_use']['actual_mathematical_evaluations'],2)

    def test_screening_synthetic_pass_cannot_close_or_select(self):
        from tools.research.budget import observe_pass
        from tools.research.feedback import result_view,eligibility
        generated=self.generate(screening_fidelity='coarse');ref=generated['candidate']
        c=design.verify_candidate(self.host,ref)
        result=dict(candidate=ref,status='evaluated',owning_study=self.host.run_id,fresh_execution=True,
            acceptance=dict(accepted=True,metrics=dict(terminal_error_m=0.,holding_max_error_m=0.,holding_max_speed_m_s=0.)),
            scientific_configuration=c['scientific_configuration'],profile_identity=c['profile_identity'],fixture=True)
        r=save(self.host,result,'synthetic_backend_fixture');update(self.host,results=[r],evaluation_reads=[r])
        observe_pass(self.host,r)
        self.assertFalse(state(self.host).get('success_gate'))
        self.assertEqual(result_view(self.host,r)['task_performance'],'provisional')
        self.assertFalse(eligibility(self.host,r)['eligible'])
        from tools.research.execution import execute
        with patch('tools.research.execution.guard'),patch('tools.research.execution.capacity',return_value=dict(admitted=1)):
            blocked=execute(self.host,ref,'screening-launch')
        self.assertEqual(blocked['status'],'final_fidelity_required')
        self.assertIsNone(blocked['task_success'])
        self.assertEqual(state(self.host).get('nmpc_launches',0),0)
        final=self.generate(screening_fidelity='standard')['candidate']
        cc=design.verify_candidate(self.host,final)
        passing=save(self.host,{**result,'candidate':final,'scientific_configuration':cc['scientific_configuration']},'synthetic_final_fixture')
        update(self.host,results=[r,passing])
        observe_pass(self.host,passing)
        self.assertEqual(state(self.host)['success_gate']['candidate'],final)
        with self.assertRaisesRegex(ValueError,'IMMEDIATE_CLOSEOUT'):
            core.guard(self.host,True)

    def test_runtime_native_failure_containment_exact_cache_and_no_substitution(self):
        from tools.research.runtime_capability import capability
        from tools.service_execution import _run_contained
        a=self.generate(screening_fidelity='standard')['candidate']
        with patch('tools.service_execution._run_contained',return_value=__import__('subprocess').CompletedProcess([],3221225725)) as native:
            result=capability(self.host,a);again=capability(self.host,a)
            self.assertEqual(native.call_count,1)
        self.assertEqual(result['status'],'runtime_unavailable')
        self.assertEqual(again['reference'],result['reference'])
        self.assertIsNone(result['task_success'])
        self.assertFalse(result['physical_infeasibility_proven'])
        self.assertEqual(set(result['binding']['effective_discretization']['data']['cells'].values()),{12})
        other=design.generate_candidate(self.host,dict(version='serial_family_generation_v2',
            family_space_identity=self.spec['family_space_identity'],segment_count=1,tendon_count=3),{},screening_fidelity='standard')['candidate']
        with patch('tools.service_execution._run_contained',return_value=__import__('subprocess').CompletedProcess([],0)) as native:
            self.assertEqual(capability(self.host,other)['status'],'runtime_available')
            self.assertEqual(native.call_count,1)

    def test_invalid_attempts_and_failed_math_keep_cost_and_bounds(self):
        before=state(self.host).get('construction_numerical_s',0.)
        invalid=design.generate_candidate(self.host,dict(version='serial_family_generation_v2',
            family_space_identity=self.spec['family_space_identity'],segment_count=1,tendon_count=3,
            segments={'0':dict(length_m=2.)}),dict(origin='invalid_test'))
        self.assertEqual(invalid['status'],'invalid')
        self.assertGreater(state(self.host)['construction_numerical_s'],before)
        self.assertEqual(state(self.host)['mathematical_evaluations'],0)
        q=request(self.spec);q.update(max_proposals=3,max_evaluations=2)
        original=self.scored
        def failed(*args,**kwargs):
            out=original(*args,**kwargs);value=self.host.store.artifact(out['reference'])
            value.update(status='incomplete',proxy_values={})
            ref=save(self.host,value,'synthetic_failed_math');s=state(self.host)
            update(self.host,analysis_results=[*s['analysis_results'][:-1],ref])
            return dict(reference=ref)
        with patch.object(analysis,'dispatch',side_effect=failed):
            out=search.run_search(self.host,q,'failed',guard=lambda *a:None,execute=None,capacity=None)
        self.assertEqual(out['result']['status'],'no_supported_result')
        self.assertEqual(state(self.host)['mathematical_evaluations'],2)
        self.assertGreater(state(self.host)['construction_numerical_s'],0.)
        self.assertFalse(state(self.host).get('success_gate'))

    def test_recorded_exact_six_segment_failure_never_reprobes(self):
        from tools.research.runtime_capability import capability
        ref=design.generate_candidate(self.host,dict(version='serial_family_generation_v2',
            family_space_identity=self.spec['family_space_identity'],segment_count=6,tendon_count=3),
            dict(origin='recorded_failure_binding_test'),screening_fidelity='standard')['candidate']
        with patch('tools.service_execution._run_contained',side_effect=AssertionError('Do not repeat recorded native failure')):
            support=capability(self.host,ref)
        self.assertEqual(support['status'],'runtime_unavailable')
        self.assertEqual(support['native_status_hex'],'0xC00000FD')
        self.assertTrue(support['boundary']['reused_recorded_failure'])
        self.assertEqual(state(self.host).get('runtime_probe_launches',0),0)

    def test_invalid_search_proposal_retains_cost_and_spends_no_math(self):
        generate=design.generate_candidate;attempts=[]
        def invalid_first(host,request,provenance,**kwargs):
            raw=deepcopy(request)
            if not attempts:raw['segments']['0']['length_m']=2.
            attempts.append(raw)
            return generate(host,raw,provenance,**kwargs)
        q=request(self.spec);q.update(max_proposals=2,max_evaluations=1)
        with patch.object(design,'generate_candidate',side_effect=invalid_first):
            output=self.run_scored(q)['result']['result']
        first=output['evaluated'][0]
        self.assertEqual(first['computation_status'],'invalid')
        self.assertEqual(first['actual_mathematical_evaluations'],0)
        self.assertIsNone(first['lineage']['new_candidate_ref'])
        self.assertGreater(first['lineage']['cost']['construction_numerical_s'],0.)
        self.assertEqual(state(self.host)['mathematical_evaluations'],1)

    def test_revised_search_can_cite_owned_previous_evidence(self):
        ref=self.generate(screening_fidelity='coarse')['candidate']
        query=dict(candidate=ref,operation='equilibrium',operating_point='target_equilibrium',
            protocol=self.spec['analysis_protocol'],scoring_window_s=self.spec['scoring_window_s'])
        evidence=self.scored(self.host,query,'context')['reference']
        q=request(self.spec);q.update(previous_candidate_ref=ref,evidence_used=[evidence],max_proposals=1,max_evaluations=1)
        row=self.run_scored(q)['result']['result']['evaluated'][0]
        self.assertEqual(row['lineage']['previous_candidate_ref'],ref)
        self.assertEqual(row['lineage']['evidence_used'],[evidence])
        unrelated=save(self.host,dict(fixture=True),'unowned_context_fixture')
        q['evidence_used']=[unrelated]
        with self.assertRaisesRegex(ValueError,'OWNED_SEARCH_EVIDENCE'):
            search.search_problem(self.host,q,1)

    def test_individual_routes_and_section_moves_stay_conditional(self):
        from tools.research.mixed_moves import initial,next_move,generation
        q=request(self.spec);q.update(variable_groups=['segment_count','sections','routing'],
            tendon_counts=[3],span_strategies=['whole_chain'],section_types=['circle','tube'])
        q=FamilyMixedSearch.model_validate(q);p=initial(self.spec['family_space'],q);paths=[]
        for cursor in range(32):
            move,path,_=next_move(self.spec['family_space'],q,p,cursor,.25)
            paths+=path
            self.assertEqual(len(move['angular_offsets_rad']),move['tendon_count'])
            self.assertEqual(len(move['radii_m']),move['tendon_count'])
            self.assertEqual(len(move['segments']),move['segment_count'])
            if path==['radii_m.0']:
                generated=generation(self.spec['family_space'],q,move)
                self.assertNotEqual(generated['spans'][0]['radius_m'],generated['spans'][1]['radius_m'])
        self.assertIn('segments.0.section_kind',paths)
        self.assertIn('angular_offsets_rad.0',paths)
        self.assertIn('radii_m.0',paths)

