"""S5.8 admission/selection regressions; fabricated passes are fixtures only."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from tests.research import test_agent_feedback as fixtures
from tools.research import core, feedback
from tools.research.config import resolve
from tools.research.state import ROOT, state, update, save
from tools.state_io import read, atomic_json


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

    def test_inactive_gain_is_repeat_but_effective_weight_change_is_new(self):
        request=dict(version='serial_family_generation_v2',family_space_identity=self.spec['family_space_identity'],segment_count=2,tendon_count=4)
        original=self.generate(request)
        changed=deepcopy(request);changed['tendon_parameters']={'length_servo_gain_n_m':1500.}
        gain=self.generate(changed)
        identify=lambda ref:feedback.experiment_identity(self.host.store.artifact(ref),'nmpc',environment=self.spec['numerical_environment'])
        first=identify(original)
        self.assertEqual(feedback.compare_experiments(first,identify(gain))['relation'],'equivalent_repeat')
        changed=deepcopy(request);changed['control_weights']={'holding_tip_speed_weight':.2}
        weighted=identify(self.generate(changed))
        self.assertEqual(feedback.compare_experiments(first,weighted)['relation'],'same_robot_different_control')
        old=deepcopy(first);old.pop('identity_version')
        self.assertEqual(feedback.compare_experiments(first,old)['relation'],'unresolved_comparison')
        self.assertEqual(self.host.store.remaining()['used']['backend_solves'],0)

    def test_stop_error_names_exact_missing_evidence_without_supplying_it(self):
        candidate=self.generate();ref=self.result(candidate)
        with patch.object(core,'guard'),self.assertRaisesRegex(ValueError,ref['artifact_id']):
            core.dispatch(self.host,self.plan('stop',next_step='stop'),'s58-missing-citation-fixture')
        self.assertNotEqual(state(self.host)['research_status'],'stopped')

    def test_sealed_driver_export_recovers_without_rewriting_archive(self):
        from tests.research import sorosim_s58_agent_pilot as pilot
        destination=self.folder/'sealed_export_fixture';(destination/'study').mkdir(parents=True)
        atomic_json(destination/'summary.json',{'research_status':'stopped','fixture':True})
        atomic_json(destination/'study/archive_manifest.json',{'fixture':True})
        before=(destination/'study/archive_manifest.json').read_bytes()
        with patch.object(pilot,'DEST',destination),patch.object(pilot,'save',side_effect=AssertionError('No mutation')):
            pilot.export(self.host)
        self.assertEqual((destination/'study/archive_manifest.json').read_bytes(),before)

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
