"""S5.8 admission/selection regressions; fabricated passes are fixtures only."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from tests.research import test_agent_feedback as fixtures
from tools.research import core, feedback
from tools.research.config import resolve
from tools.research.state import ROOT, state, update, save
from tools.state_io import read


class S58AdmissionTests(unittest.TestCase):
    setUp=fixtures.AgentFeedbackTests.setUp
    cleanup=fixtures.AgentFeedbackTests.cleanup
    plan=fixtures.AgentFeedbackTests.plan
    generate=fixtures.AgentFeedbackTests.generate
    result=fixtures.AgentFeedbackTests.result

    def test_frozen_scope_and_real_nested_history(self):
        spec=resolve(ROOT/'configs/research/study_sorosim_s58_agent.json')
        self.assertEqual(spec['family_space']['executable_segment_counts'],[2])
        self.assertEqual(spec['family_space']['executable_tendon_count_bounds'],[4,4])
        self.assertEqual(spec['confirmation']['fresh_independent_repetitions'],0)
        self.assertEqual(spec['budgets']['provider_requests'],26)
        historical=read(ROOT/'evidence/sorosim_s56/physics/summary.json')
        ref=feedback.import_experiment(self.host,'evidence/sorosim_s56/physics/study',historical['nmpc'],'nmpc')
        imported=self.host.store.artifact(ref)
        self.assertTrue(imported['imported_historical_evidence'])
        self.assertEqual(state(self.host)['results'],[])
        repeated=feedback.experiment_preflight(self.host,historical['candidate'],'nmpc')
        self.assertFalse(repeated['admitted'])
        candidate=deepcopy(self.host.store.artifact(historical['candidate']))
        candidate['configuration']['policy']['controller']['parameters']['data']['recipe']['holding_tip_speed_weight']=.8
        candidate['scientific_configuration']['policy']['controller']['parameters']['data']['recipe']['holding_tip_speed_weight']=.8
        changed=save(self.host,candidate,'changed_control_fixture')
        self.assertTrue(feedback.experiment_preflight(self.host,changed,'nmpc')['admitted'])
        self.assertFalse(feedback.eligibility(self.host,historical['nmpc'])['eligible'])
        self.assertEqual(self.host.store.remaining()['used']['backend_solves'],0)

    def test_gap_never_overrides_invalid_or_failed_acceptance(self):
        candidate=self.generate()
        ref=self.result(candidate,accepted=True)
        value=self.host.store.artifact(ref)
        self.assertEqual(feedback.task_gap(value)['normalized_gap'],0)
        value['acceptance']['components']['solver_errors']['passed']=False
        value['acceptance']['accepted']=False
        gap=feedback.task_gap(value)
        self.assertEqual(gap['normalized_gap'],0)
        self.assertFalse(gap['valid_complete'])
        self.assertFalse(gap['accepted'])

    def test_fresh_fixed_sequence_selection_requires_read_and_pass(self):
        candidate=self.generate()
        original=self.result(candidate,accepted=True)
        value=self.host.store.artifact(original)
        value['source_reference']=save(self.host,dict(trajectory={'tensions_n':[[1.]*4]*35}), 'synthetic_sequence_fixture')
        ref=save(self.host,value,'synthetic_fixed_tension_fixture')
        update(self.host,results=[],physical_replays=[ref])
        with patch('tools.research.physical_replay.binding'):
            self.assertFalse(feedback.eligibility(self.host,ref)['eligible'])
            core.read_evidence(self.host,dict(reference=ref))
            self.assertTrue(feedback.eligibility(self.host,ref)['eligible'])
            with patch.object(core,'guard'):
                selected=core.dispatch(self.host,self.plan('select',selected_execution=ref),'s58-select-fixture')
            self.assertTrue(selected['result']['task_passed'])
            frozen=self.host.store.artifact(state(self.host)['selected_solution'])
            self.assertEqual(frozen['solution_identity']['controller']['sequence']['tensions_n'],[[1.]*4]*35)
        self.assertEqual(self.host.store.remaining()['used']['backend_solves'],0)


if __name__=='__main__':unittest.main()
