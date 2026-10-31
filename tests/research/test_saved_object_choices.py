"""Synthetic selector contracts; no live Provider or scientific execution."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from jsonschema import Draft202012Validator,ValidationError
from tools.research.agent import plan_schema
from tools.research.contracts import Plan
from tools.research.provider import provider_schema
from tools.research.object_choices import (saved_choice,choice_schema,reference_schema,
    expand_choice,expand_references,bind_plan_selection,reference_choices)


def ref(name):return dict(artifact_id=name*64,media_type='application/json')


def rationale(action):
    return dict(action=action,hypothesis='Synthetic selector fixture.',expected_observation='Recorded prediction.',
        weakening_observation='Prediction fails.',fixed_conditions='Frozen fixture.',stopping_condition='Finite fixture.',
        interpretation='Interface test only.',decision=dict(hypothesis_id='fixture',research_intent='PHYSICAL_VALIDATION',
            selected_method='fixture',requested_budget=1))


class SavedChoiceTests(unittest.TestCase):
    def setUp(self):
        self.c,self.u,self.m=ref('c'),ref('a'),ref('b')
        self.s=dict(profile=dict(identity='current'),analysis_results=[self.m])
        self.records={self.c['artifact_id']:dict(profile_identity='current'),
            self.u['artifact_id']:dict(provenance=dict(candidate=self.c)),
            self.m['artifact_id']:dict(candidate=self.c,status='computed',control_schedule_reference=self.u,
                native_dynamics=dict(optimization=dict(best=dict(measure=dict(signed_maximum_excess=-.1),task_gap=dict(valid_complete=True)))))}
        self.h=type('Host',(),{})();self.h.store=type('Store',(),{})()
        self.h.store.artifact=lambda reference,**kwargs:deepcopy(self.records[reference['artifact_id']])
        p=patch('tools.research.object_choices.state',return_value=self.s);p.start();self.addCleanup(p.stop)

    def test_replay_choice_cannot_mix_hashes_or_other_evidence(self):
        options=[saved_choice(self.h,'result_1')]
        schema=choice_schema(plan_schema(['physical_replay'],decision_required=True,focused=True),options)
        Draft202012Validator.check_schema(schema)
        value=rationale('physical_replay');value['decision']={'hypothesis_id':'fixture'}
        value['physical_replay']=dict(result_choice='result_1')
        Draft202012Validator(schema).validate(value)
        expanded,_=expand_choice(self.h,value);Plan.model_validate(expanded)
        self.assertEqual(expanded['physical_replay'],dict(candidate=self.c,source=self.u))
        self.assertEqual(expanded['supporting_evidence'],[self.m])
        self.assertEqual(expanded['decision']['selected_candidate'],self.c)
        for extra in (dict(selected_candidate=self.c),dict(supporting_evidence=[ref('d')])):
            with self.assertRaises(ValidationError):Draft202012Validator(schema).validate({**value,**extra})
        wrong=deepcopy(value);wrong['physical_replay']['candidate']=ref('d')
        with self.assertRaises(ValidationError):Draft202012Validator(schema).validate(wrong)

    def test_unknown_incomplete_old_profile_and_mismatched_control_rejected(self):
        for name in ('result_0','result_2','result_01','anything'):
            with self.subTest(name=name),self.assertRaises(ValueError):saved_choice(self.h,name)
        record=self.records[self.m['artifact_id']]
        record['status']='execution_incomplete'
        with self.assertRaisesRegex(ValueError,'COMPLETE'):saved_choice(self.h,'result_1')
        record['status']='computed';self.records[self.c['artifact_id']]['profile_identity']='old'
        with self.assertRaisesRegex(ValueError,'CURRENT_PROFILE'):saved_choice(self.h,'result_1')
        self.records[self.c['artifact_id']]['profile_identity']='current'
        self.records[self.u['artifact_id']]['provenance']['candidate']=ref('d')
        with self.assertRaisesRegex(ValueError,'MISMATCH'):saved_choice(self.h,'result_1')

    def test_mathematical_failure_is_labelled_and_does_not_become_a_pass(self):
        self.records[self.m['artifact_id']]['native_dynamics']['optimization']['best']['measure']['signed_maximum_excess']=1.3
        option=saved_choice(self.h,'result_1')
        self.assertEqual(option['mathematical_status'],'not_satisfied')
        self.assertFalse(option['formal_acceptance_read_credit'])
        self.assertEqual(option['independent_task_acceptance'],'unmeasured_for_this_choice')

    def test_select_binds_candidate_and_support_to_one_evaluation(self):
        evaluation=ref('e');self.records[evaluation['artifact_id']]=dict(candidate=self.c)
        schema=reference_schema(plan_schema(['select'],decision_required=True,focused=True),{'evaluation_7':evaluation},'select')
        value=rationale('select');value['decision']['research_intent']='SELECT';value['selected_execution']='evaluation_7'
        # Scientific text equal to a selector remains ordinary text.
        value['hypothesis']='evaluation_7'
        Draft202012Validator(schema).validate(value)
        expanded=bind_plan_selection(self.h,expand_references(value,schema));Plan.model_validate(expanded)
        self.assertEqual(expanded['selected_execution'],evaluation)
        self.assertEqual(expanded['supporting_evidence'],[evaluation])
        self.assertEqual(expanded['decision']['selected_candidate'],self.c)
        self.assertEqual(expanded['hypothesis'],'evaluation_7')
        self.assertNotIn('x-research-reference-choices',provider_schema(schema))

    def test_execute_needs_one_candidate_choice_and_does_not_change_parameters(self):
        schema=reference_schema(plan_schema(['execute'],decision_required=True,focused=True),{'candidate_9':self.c},'execute')
        value=rationale('execute');value['decision']['research_intent']='NMPC_EXECUTION';value['candidate']='candidate_9'
        Draft202012Validator(schema).validate(value)
        expanded=bind_plan_selection(self.h,expand_references(value,schema));Plan.model_validate(expanded)
        self.assertEqual(expanded['candidate'],expanded['decision']['selected_candidate'])

    def test_joint_select_rejects_different_candidates(self):
        first,second=ref('e'),ref('f')
        self.records[first['artifact_id']]=dict(candidate=self.c);self.records[second['artifact_id']]=dict(candidate=ref('d'))
        value=rationale('select');value['selected_execution']=[first,second]
        with self.assertRaisesRegex(ValueError,'IDENTICAL_CANDIDATE'):bind_plan_selection(self.h,value)


class SelectAdmissionTests(unittest.TestCase):
    def test_short_choice_keeps_public_read_gate_and_auto_closure(self):
        from tests.research.test_p63g_bounded_evidence import bounded_host,BoundedEvidenceTests
        from tests.research.test_recent_round_tools import run_fixture
        from tests.research.test_p63r3_closure import selection
        from tools.research.state import state
        from tools.research.feedback import eligibility
        h=bounded_host();candidate,evaluation=BoundedEvidenceTests().physical(h)
        choice=next(k for k,v in reference_choices(h).items() if v==evaluation)
        value=selection(candidate,evaluation);value['selected_execution']=choice
        value.pop('supporting_evidence');value['decision'].pop('selected_candidate')
        self.assertFalse(eligibility(h,evaluation,selection=True)['eligible'])
        with patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_REAL_WORKER')):
            wires=run_fixture(h,[('evidence_read',dict(reference=evaluation,view='acceptance_certificate')),
                ('research_route',dict(tool='research_plan',action='select')),('research_plan',value)])
        self.assertEqual(state(h)['selected'],evaluation)
        self.assertEqual(state(h)['research_status'],'stopped')
        self.assertTrue(all('x-research-reference-choices' not in str(w['tools']) for w in wires))


if __name__=='__main__':unittest.main()
