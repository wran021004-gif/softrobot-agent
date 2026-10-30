"""B0/B directed offline fixtures; no real engine or Provider."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from tools.platform_store import plain
from tools.research import core
from tools.research.state import state,update
from tools.research.research_context import agent_decision_brief
from tools.research.design import set_parameter
from extensions.tendon_family.family_space import resolved_request
from tests.research.test_structure_mechanism_aplus import prepare,execute_synthetic
from tests.research.test_p63a_math_interface import generate,diagnose
from tests.research.test_p63c2_scientific_intent import mechanism_question
from tests.research.test_information_flow import generation


class DirectionProjectionTests(unittest.TestCase):
    def test_two_candidates_alternate_without_cross_candidate_direction(self):
        h,a=prepare();b=generate(h,(.17,.11));diagnose(h,a,'scientific_question')
        ar=execute_synthetic(h,a,mechanism_question())['reference']
        diagnose(h,b,'scientific_question');br=execute_synthetic(h,b,mechanism_question())['reference']
        for candidate,expected,other in [(b,br,ar),(a,ar,br),(b,br,ar)]:
            diagnose(h,candidate,'scientific_question');view=agent_decision_brief(h)['mechanism_research']
            self.assertEqual(view['candidate'],candidate);self.assertEqual(view['direction_candidate'],candidate)
            self.assertEqual(view['direction_query']['reference'],expected)
            self.assertTrue(any(r['query']['reference']==other and r['relation']=='other_candidate_history' for r in view['historical_directions']))
        c=generate(h,(.18,.11));diagnose(h,c,'scientific_question');view=agent_decision_brief(h)['mechanism_research']
        self.assertFalse(view['direction_proposed']);self.assertIsNone(view['direction_query'])

    def test_citation_and_generated_candidate_do_not_prove_suggestion_adopted(self):
        h,c=prepare();ref=execute_synthetic(h,c,mechanism_question())['reference']
        request=resolved_request(state(h)['spec']['family_space'],h.store.artifact(c)['parameters'])
        set_parameter(request,'segments.1.length_m',.111)
        plan=generation(h);plan.update(generation=request,supporting_evidence=[ref])
        with patch.object(core,'guard'):out=core.dispatch(h,plan,'b0-cite-but-other-edit')
        changed=out['result']['candidate'];diagnose(h,changed,'scientific_question')
        view=agent_decision_brief(h)['mechanism_research']
        self.assertFalse(view['direction_proposed']);self.assertIsNone(view['direction_candidate'])
        self.assertTrue(view['generation_plan_cited_evidence']);self.assertTrue(view['formal_candidate_created'])
        self.assertFalse(view['suggestion_adopted'])
        self.assertEqual(view['generation_relations'][0]['relation'],'historical_parent_direction')
        diagnose(h,c,'scientific_question');view=agent_decision_brief(h)['mechanism_research']
        self.assertTrue(view['direction_proposed']);self.assertFalse(view['suggestion_adopted'])

    def test_original_budget_closeout_and_authorization_own_l0_admission(self):
        h,c=prepare();original=deepcopy(state(h))
        ready=agent_decision_brief(h)['mechanism_research'];self.assertTrue(ready['operation_admission']['differentiate']['can_prepare'])
        for change in ('budget','closeout','grant'):
            update(h,**deepcopy(original))
            if change=='budget':update(h,mathematical_evaluations=32)
            elif change=='closeout':update(h,count_closeout=True)
            else:
                spec=deepcopy(state(h)['spec']);spec['mathematical_methods'].pop('mechanism_structure_v1');update(h,spec=spec)
            brief=agent_decision_brief(h);view=brief['mechanism_research']
            self.assertTrue(brief['mathematical_research'])
            self.assertTrue(all(not r['can_prepare'] for r in view['operation_admission'].values()),view)


if __name__=='__main__':unittest.main()
