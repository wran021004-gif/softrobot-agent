"""Model contracts and real mock wires; fixtures are not research progress."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
import mujoco
import numpy as np
from tools.research import experience
from tools.research.state import state,update,save
from tools.research.design import generate_candidate
from tools.research.optimal_capability import family_analysis_parameters
from tools.research.scientific_intent import parameter_catalog
from extensions.tendon_family.mujoco_analysis import NativeModel
from extensions.tendon_family.mjcf import parameter_effect_semantics
from tests.research.test_research_authorization_preflight import fixture,approve
from tests.research.test_recent_round_tools import run_fixture
from tools.research.contracts import REGISTERED_MATHEMATICS_SCOPE


class KnowledgePhysicsTests(unittest.TestCase):
    def generate(self,h,**changes):
        q=dict(version='serial_family_generation_v2',family_space_identity=state(h)['spec']['family_space_identity'],segment_count=3,tendon_count=4,**changes)
        return generate_candidate(h,q,dict(origin='fabricated offline regression fixture'))['candidate']

    def test_actual_native_fixed_absolute_input_overrides_pretension_and_diameter_is_not_elasticity(self):
        with fixture() as h,patch('mujoco.mj_step',side_effect=AssertionError('NO_ROLLOUT')):
            base=self.generate(h);cfg=h.store.artifact(base)['configuration'];native=NativeModel(cfg)
            d=mujoco.MjData(native.model);u=[.5]*len(native.aids);native.apply(d,u)
            for key,value in [('pretension_n',.7),('diameter_m',.0005)]:
                ref=self.generate(h,tendon_parameters={key:value});other=NativeModel(h.store.artifact(ref)['configuration'])
                data=mujoco.MjData(other.model);other.apply(data,u)
                np.testing.assert_allclose(data.qacc,d.qacc,atol=1e-12,rtol=0)
                for field in ('body_mass','body_inertia','jnt_stiffness','actuator_gainprm','actuator_biasprm'):
                    np.testing.assert_array_equal(getattr(other.model,field),getattr(native.model,field))
                self.assertEqual(other.cost['physics_steps'],0)
            rows={r['parameter_id']:r for r in family_analysis_parameters(state(h)['spec'],h.store.artifact(base))}
            from tools.research.config import ROOT
            historical=json.loads((ROOT/'tests/research/fixtures/m1_parameter_errors.json').read_text(encoding='utf8'))
            self.assertEqual({r['parameter'] for r in historical['errors']},{'tendon_parameters.pretension_n','tendon_parameters.diameter_m'})
            for key in ('pretension_n','diameter_m'):
                row=rows['tendon_parameters.'+key]
                self.assertFalse(row['continuous_perturbation']);self.assertFalse(row['execution_semantics']['method_identifiable'])
            self.assertFalse(rows['tendon_parameters.pretension_n']['execution_semantics']['fixed_absolute_input_effect'])
            self.assertIn('tendon_elastic_stiffness',rows['tendon_parameters.diameter_m']['execution_semantics']['excluded_effects'])
            catalog={r['parameter_id']:r for r in parameter_catalog(state(h)['spec'],h.store.artifact(base))}
            self.assertFalse(catalog['tendon_parameters.pretension_n']['selectable'])
            self.assertFalse(catalog['tendon_parameters.diameter_m']['selectable'])
            self.assertEqual(state(h)['mathematical_evaluations'],0)

    def test_other_actuator_models_are_not_globally_prohibited(self):
        ideal=parameter_effect_semantics('tendon_parameters.length_servo_gain_n_m','ideal_tension')
        realistic=parameter_effect_semantics('tendon_parameters.length_servo_gain_n_m','actuator_realistic')
        self.assertEqual(ideal['effect_channels'],[]);self.assertEqual(realistic['effect_channels'],['drive'])
        self.assertNotIn('fixed_absolute_input_effect',parameter_effect_semantics('tendon_parameters.pretension_n','actuator_realistic'))

    def test_new_logical_filters_and_original_manifest_are_independent(self):
        with fixture() as h:
            old=deepcopy(state(h)['spec']);self.assertFalse(experience.retrieve(h,dict(knowledge_type='experience'))['results'])
            spec=deepcopy(old);spec['knowledge']=dict(mode='enabled',allowed_kinds=['procedure','case'],include_entry_ids=['skill-parameter-model','experience-premature-stop'])
            spec['knowledge_manifest']=experience.freeze_knowledge(spec['knowledge']);update(h,spec=spec)
            for kind in ('skill','experience'):
                result=experience.retrieve(h,dict(knowledge_type=kind));self.assertEqual(len(result['results']),1)
                row=result['results'][0];self.assertEqual(row['knowledge_type'],kind)
                actual=experience.retrieve(h,row['read_query']);self.assertIn('content_sha256',actual['results'][0])
                self.assertFalse(actual['scientific_evidence'])
            update(h,spec=old)
            self.assertFalse(experience.retrieve(h,dict(operation='search',entry_id='experience-premature-stop'))['results'])
            with self.assertRaisesRegex(ValueError,'EXACT_EXPERIENCE_READ'):
                experience.retrieve(h,dict(operation='read',entry_id='experience-premature-stop',revision='1'))

    def test_timed_hint_actual_read_and_adoption_have_separate_receipts(self):
        with fixture() as h:
            approve(h,[REGISTERED_MATHEMATICS_SCOPE]);hint=experience.retrieval_hint(h)
            self.assertEqual(hint['decision_notice']['phase'],'first_scientific_plan');self.assertLessEqual(len(hint['hints']),2)
            self.assertIsNone(experience.read_progress(h));self.assertEqual(experience.hint_progress(h),[])
            query=hint['hints'][0]['read_query']
            with patch('tools.research.agent.credential',return_value='offline'):
                sent=run_fixture(h,[('experience_retrieve',query),None],limit=2)
            initial=json.loads(sent[0]['messages'][-1]['content'].split('\n',1)[1])['research']['knowledge']['access']
            self.assertTrue(initial['decision_notice']);self.assertTrue(experience.hint_progress(h))
            self.assertEqual(experience.retrieval_hint(h)['hints'],[])
            progress=experience.read_progress(h);self.assertTrue(progress['reads'][0]['body_delivered'])
            binding=experience.disposition_bindings(h,{query['entry_id']+'@'+query['revision']:'adopted'})[0]
            self.assertEqual(binding['disposition'],'adopted')
            with self.assertRaisesRegex(ValueError,'EXACT_ACTUAL_READ'):
                experience.disposition_bindings(h,{'unread@1':'adopted'})
            self.assertFalse(state(h)['plans']);self.assertEqual(state(h)['mathematical_evaluations'],0)

    def test_repeated_failed_search_and_stop_each_have_one_notice(self):
        with fixture() as h:
            candidate=self.generate(h)
            plan=save(h,dict(original_plan=dict(action='diagnose')),'original_research_plan')
            refs=[save(h,dict(candidate=candidate,native_dynamics=dict(optimization=dict(best=dict(task_gap=dict(accepted=False)),stop_reason='iteration_limit')))) for _ in range(2)]
            update(h,plans=[plan],analysis_results=refs)
            hint=experience.retrieval_hint(h);self.assertEqual(hint['decision_notice']['phase'],'finite_search_structural_review')
            route=save(h,dict(tool='research_plan',action='stop'),'research_tool_route')
            update(h,pilot={**state(h)['pilot'],'tool_route':route})
            self.assertEqual(experience.retrieval_hint(h)['decision_notice']['phase'],'voluntary_stop')

    def test_new_cards_are_compact_and_disclose_no_winning_arrays(self):
        from tools.research.config import ROOT
        for row in experience._index_rows():
            if row.get('introduced_in')!='knowledge_organization_v1':continue
            body=json.loads((ROOT/row['path']).read_text(encoding='utf8'))
            self.assertLess(len(json.dumps(body)),6500)
            if row['kind']=='case':
                self.assertTrue(3<=len(body['decision_trace'])<=7)
                self.assertNotIn('parameters',body);self.assertNotIn('trajectory',body)
                self.assertNotIn('decision_owner',body)
            else:
                for key in ('skill_id','principle','assumptions','applicability','diagnostic_questions','possible_actions','expected_observations','cannot_conclude','evidence_sources','validation_status'):self.assertIn(key,body)

    def test_compact_skill_is_delivered_without_read_and_citation_remains_distinct(self):
        with fixture() as h:
            from tests.research.test_cross_task_integration import plan
            spec=deepcopy(state(h)['spec']);spec['knowledge']=dict(mode='enabled',delivery='compact_skill_v1',
                allowed_kinds=['procedure','case'],include_entry_ids=['skill-parameter-model','experience-premature-stop'])
            spec['knowledge_manifest']=experience.freeze_knowledge(spec['knowledge']);update(h,spec=spec)
            approve(h,[REGISTERED_MATHEMATICS_SCOPE]);hint=experience.retrieval_hint(h)
            self.assertNotIn('decision_notice',hint);self.assertNotIn('hints',hint)
            self.assertEqual(set(hint['skill']),{'key','principle','when'})
            self.assertLess(len(json.dumps(hint)),850)
            key=hint['skill']['key'];self.assertEqual(key,'summary:skill-parameter-model@1')
            with self.assertRaisesRegex(ValueError,'EXACT_ACTUAL_READ'):experience.disposition_bindings(h,{key:'adopted'})
            candidate=self.generate(h)
            value=plan('diagnose',candidate);value['experience_disposition']={key:'adopted'}
            with patch('tools.research.agent.credential',return_value='offline'):
                sent=run_fixture(h,[('research_route',dict(tool='research_plan',action='diagnose')),('research_plan',value),None],limit=3)
            self.assertEqual(len(experience.hint_progress(h)),1);self.assertIsNone(experience.read_progress(h))
            self.assertTrue(state(h)['plans'],[h.store.artifact(e['outputs'][0]) for e in h.store.events(h.run_id)
                if e['kind']=='model_original_tool_feedback'])
            original=h.store.artifact(state(h)['plans'][0])
            self.assertEqual(original['experience_read_bindings'],[])
            self.assertFalse(original['skill_summary_citations'][0]['full_read'])
            self.assertIsNone(experience.retrieval_hint(h));self.assertFalse(state(h)['retrievals'])
            full=experience.retrieve(h,dict(operation='read',entry_id='skill-parameter-model',revision='1'))
            self.assertIn('content',full['results'][0]);self.assertEqual(len(state(h)['retrievals']),1)


if __name__=='__main__':unittest.main()
