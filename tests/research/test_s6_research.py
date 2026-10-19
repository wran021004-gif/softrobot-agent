"""Offline contract fixtures and hash-verified archive reads; no provider or rollout."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4
from schemas.platform import ProjectConfig
import numpy as np
from tools.research import core
from tools.research.contracts import Plan, LocalControlSearchSettings
from tools.research.control_correction import corrected_tensions, correction_basis
from tools.research.local_control_search import search
from tools.research.evidence_policy import admit_decision
from tools.research.research_context import import_history, context
from tools.research.state import state
from tools.state_io import read
from tests.research.test_local_control_search import start

ROOT=Path(__file__).resolve().parents[2]


def plan(action='diagnose',**changes):
    return Plan.model_validate(dict(action=action,hypothesis='Fixture hypothesis',expected_observation='Measured improvement',
        weakening_observation='No improvement',fixed_conditions='Frozen task',stopping_condition='Finite allocation',
        interpretation='No global inference',**changes))


def decision(intent='DIAGNOSE',inference='empirical_search',**changes):
    return dict(hypothesis_id='FIXTURE',research_intent=intent,claimed_inference=inference,
        selected_method='fixture',**changes)


class ContractTests(unittest.TestCase):
    def test_old_serialization_does_not_add_new_semantics(self):
        p=plan();self.assertNotIn('decision',p.model_dump(mode='json'));self.assertNotIn('control_search',p.model_dump(mode='json'))

    def test_new_action_does_not_replace_old_search(self):
        ref=dict(artifact_id='a'*64)
        p=plan('control_search',control_search=dict(candidate=ref,source=ref,settings={}))
        self.assertEqual(p.action,'control_search')
        with self.assertRaises(ValueError):plan('search',control_search=p.control_search)

    def test_window_is_exact_and_basis_agrees(self):
        times=np.arange(20)*.01;ref=np.ones((20,3));x=np.arange(6).reshape(2,3)*.1
        result=corrected_tensions(ref,times,[.1,.15],x,[8]*3,(.1,.15))
        mask=(times<.1)|(times>.15)
        np.testing.assert_array_equal(result[mask],ref[mask])
        basis=correction_basis(times,[.1,.15],3,(.1,.15))
        np.testing.assert_allclose(result-ref,(basis@x.ravel()).reshape(20,3))

    def test_window_and_horizon_validation(self):
        for options in [dict(knots_s=[.1,.2]),dict(version='local_control_search_v2',knots_s=[.1,.2],correction_window_s=[.11,.2])]:
            with self.assertRaises(ValueError):LocalControlSearchSettings(**options)
        with self.assertRaises(ValueError):search([start()],Mock(),dict(version='local_control_search_v2',knots_s=[0,1]))

    def test_other_channel_counts_and_intervals(self):
        for channels,intervals in [(1,12),(3,20),(6,7)]:
            s=start();tr=s['schedule']['trajectory'];tr.update(times_s=[k*.01 for k in range(intervals+1)],
                tensions_n=[[4.]*channels for _ in range(intervals)],tendon_order=[str(i) for i in range(channels)])
            s['limits']=[8]*channels
            def evaluate(s,source,metadata):
                self.assertEqual(np.asarray(source['trajectory']['tensions_n']).shape,(intervals,channels))
                return dict(reference='fixture',task_gap=dict(valid_complete=True,normalized_gap=1.,accepted=False,components={'fixture':1.}),outputs=None)
            result=search([s],evaluate,dict(version='local_control_search_v2',method='pattern',knots_s=[0,.05],evaluation_requests=2))
            self.assertEqual(len(result['candidates']),2)


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.ref=dict(artifact_id='a'*64,media_type='application/json')
        self.s=dict(spec=dict(research_decisions={'version':'research_decision_v1'}),results=[],base_configuration={'task':{'id':'t'}})
        self.host=SimpleNamespace(store=Mock())
        self.patcher=patch('tools.research.state.state',return_value=self.s);self.patcher.start();self.addCleanup(self.patcher.stop)

    def test_old_study_keeps_plan_contract(self):
        self.s['spec']={};self.assertIsNone(admit_decision(self.host,plan()))

    def test_new_study_requires_typed_decision(self):
        with self.assertRaisesRegex(ValueError,'DECISION_REQUIRED'):admit_decision(self.host,plan())

    def test_forged_reference_and_global_claim_rejected(self):
        with self.assertRaisesRegex(ValueError,'UNREGISTERED'):admit_decision(self.host,plan(decision=decision(),supporting_evidence=[self.ref]))
        with self.assertRaisesRegex(ValueError,'INFERENCE_NOT_SUPPORTED'):admit_decision(self.host,plan(decision=decision(inference='structural_infeasibility')))
        self.host.store.reserve.assert_not_called()

    def test_legal_exploration_needs_no_certificate(self):
        self.assertFalse(admit_decision(self.host,plan(decision=decision()))['prospective_guarantee'])

    def test_wrong_intent_rejected(self):
        with self.assertRaisesRegex(ValueError,'INTENT_ACTION'):admit_decision(self.host,plan(decision=decision('CONTROL_SEARCH')))

    def test_cross_task_evidence_rejected(self):
        self.s['results']=[self.ref]
        self.host.store.artifact.side_effect=lambda r:dict(candidate=self.ref) if r==self.ref else {}
        with patch('tools.research.evidence_policy.summarize_evidence',return_value={}),patch.object(self.host.store,'artifact',side_effect=[dict(candidate=self.ref),dict(configuration=dict(task={'id':'other'}))]):
            with self.assertRaisesRegex(ValueError,'TASK_IDENTITY'):admit_decision(self.host,plan(decision=decision(),supporting_evidence=[self.ref]))


class HistoryTests(unittest.TestCase):
    def test_p1_bound_start_and_only_actual_violating_samples(self):
        import shutil, gc
        directory=ROOT/'runs'/('s6-fixture-'+uuid4().hex)
        def cleanup():
            gc.collect()
            if directory.exists():shutil.rmtree(directory)
        self.addCleanup(cleanup)
        fixture=lambda **v:ProjectConfig(**{**v,'project_id':directory.name,'grant_id':directory.name})
        with patch.object(core,'ProjectConfig',side_effect=fixture):
            host=core.prepare(ROOT/'configs/research/study_s6_2.json',directory=directory)
            with patch('tools.research.core.dispatch') as dispatch:
                import_history(host);before=host.store.remaining();import_history(host)
                current=context(host)
            dispatch.assert_not_called()
            best=current['best_valid'];self.assertTrue(best['historical_only']);self.assertFalse(best['task_gap']['accepted'])
            self.assertAlmostEqual(best['task_gap']['normalized_gap'],.054502039,places=8)
            self.assertEqual([round(v['time_s'],2) for v in best['violations']['samples']],[.3,.33])
            self.assertEqual(before,host.store.remaining());self.assertEqual(before['used']['backend_solves'],0)
            source=host.store.artifact(current['history'][0]['source'])
            self.assertEqual(np.asarray(source['trajectory']['tensions_n']).shape,(35,4))
            self.assertEqual(source,read(ROOT/'evidence/control_search_p1/best_control.json')['schedule'])
            entry=current['history'][0]
            request=plan('control_search',decision=decision('CONTROL_SEARCH',selected_candidate=entry['candidate'],requested_budget=1),
                supporting_evidence=[entry['reference']],control_search=dict(candidate=entry['candidate'],source=entry['source'],
                    settings=dict(version='local_control_search_v2',knots_s=[.3,.34],correction_window_s=[.3,.35],evaluation_requests=1)))
            with patch('tools.research.core.guard'),patch('tools.research.state.guard'),patch('tools.research.physical_replay.evaluate_schedule') as physical:
                output=core.dispatch(host,request,'fixture-public-search')
                again=core.dispatch(host,request,'fixture-public-search')
            physical.assert_not_called()
            self.assertEqual(output['result']['new_physical_evaluations'],0)
            self.assertEqual(output['result']['best']['reference'],entry['reference'])
            self.assertEqual(output['result'],again['result'])
            self.assertEqual(host.store.remaining()['used']['tool_calls'],1)


if __name__=='__main__':unittest.main()
