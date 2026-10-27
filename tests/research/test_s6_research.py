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
from tools.research.control_correction import corrected_tensions, correction_basis, constraint_vectors
from tools.research.local_control_search import search
from tools.research.evidence_policy import admit_decision, comparable_task
from tools.research.research_context import import_history, context
from tools.research.state import state
from tools.research.physical_replay import initialize_schedule
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
    def test_not_applicable_feedback_exposes_actual_refusal_without_science(self):
        from tools.research.research_context import tool_feedback
        value=dict(status='not_applicable',analysis_applicability=dict(reasons=['Fixture window does not start at selected state']),
            task_acceptance='unmeasured',additional_analysis_evaluations=0)
        with patch('tools.research.research_context.save',return_value=dict(artifact_id='a'*64)),patch(
                'tools.research.evidence_policy.registered_references',return_value=[]):
            result=tool_feedback(SimpleNamespace(),value)
        self.assertEqual(result['execution_feedback']['reasons'],value['analysis_applicability']['reasons'])
        self.assertFalse(result['execution_feedback']['scientific_execution_started'])
        self.assertEqual(result['execution_feedback']['additional_analysis_evaluations'],0)

    def test_old_serialization_does_not_add_new_semantics(self):
        p=plan();self.assertNotIn('decision',p.model_dump(mode='json'));self.assertNotIn('control_search',p.model_dump(mode='json'))
        legacy=LocalControlSearchSettings().model_dump(mode='json')
        self.assertFalse({'version','correction_window_s','safety_margin_fraction'} & legacy.keys())
        self.assertEqual(LocalControlSearchSettings(version='local_control_search_v2',safety_margin_fraction=.05).model_dump(mode='json')['safety_margin_fraction'],.05)

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
        for options in [dict(knots_s=[.1,.2]),dict(version='local_control_search_v2',knots_s=[-.1,.2]),dict(version='local_control_search_v2',knots_s=[.1,.2],correction_window_s=[.11,.2])]:
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

    def test_distinct_terminal_and_holding_limits(self):
        outputs=dict(times_s=[0.,.1],tip_positions_m=[[.01,0,0],[.01,0,0]],tip_velocities_m_s=[[0,0,0]]*2)
        vectors=constraint_vectors(outputs,[0,0,0],.1,.02,.02,terminal_position_limit=.005)
        np.testing.assert_array_equal(vectors[:,0],[2.,.5,0.])

    def test_margin_is_versioned_and_method_specific(self):
        for options in [dict(safety_margin_fraction=.05),dict(version='local_control_search_v2',method='pattern',safety_margin_fraction=.05)]:
            with self.assertRaises(ValueError):LocalControlSearchSettings(**options)

    def test_model_margin_survives_small_curvature_without_relaxing_acceptance(self):
        s=start();s['limits']=[8.];tr=s['schedule']['trajectory']
        tr.update(tensions_n=[[4.],[4.]],times_s=[0.,.1,.2],tendon_order=['a'])
        s['task_options'].update(holding_start=.1)
        def evaluate(s,source,metadata):
            delta=source['trajectory']['tensions_n'][-1][0]-4.;speed=.021+.1*delta+.05*delta**2
            gap=max(0.,speed/.02-1)
            return dict(reference='synthetic-curved-fixture',task_gap=dict(valid_complete=True,accepted=speed<=.02,
                normalized_gap=gap,components={'speed':gap}),outputs=dict(times_s=[0.,.1,.2],
                tip_positions_m=[[0,0,0]]*3,tip_velocities_m_s=[[speed,0,0]]*3))
        settings=dict(version='local_control_search_v2',knots_s=[0.,.1],evaluation_requests=4)
        boundary=search([s],evaluate,settings);margin=search([s],evaluate,dict(settings,safety_margin_fraction=.05))
        self.assertFalse(boundary['best']['task_gap']['accepted'])
        self.assertTrue(margin['best']['task_gap']['accepted'])
        self.assertEqual(margin['stop_reason'],'first_original_task_pass')
        self.assertEqual(s['task_options']['speed_limit'],.02)

    def test_new_structure_initialization_is_explicit_and_unmeasured(self):
        source=start()['schedule'];before=deepcopy(source)
        model=(SimpleNamespace(task={'id':'new-task'}),dict(tendons=[dict(entity=k) for k in ['a','b','c','d']]),{},dict(identity='new-model',design_identity='new-design'))
        with patch('tools.research.physical_replay.model_context',return_value=model),patch('tools.research.physical_replay.binding') as binding:
            result=initialize_schedule({},source,dict(artifact_id='a'*64))
        self.assertEqual(source,before);self.assertEqual(result['task_acceptance'],'unmeasured')
        self.assertFalse(result['provenance']['inherited_acceptance'])
        self.assertEqual(result['trajectory']['model_identity'],'new-model');binding.assert_called_once()
        model[1]['tendons'].pop()
        with patch('tools.research.physical_replay.model_context',return_value=model):
            with self.assertRaisesRegex(ValueError,'UNSUPPORTED_CROSS_TOPOLOGY'):initialize_schedule({},source,{})

    def test_public_search_rejects_unsupported_task_without_fallback(self):
        from tools.research.local_control_search import dispatch
        ref=dict(artifact_id='a'*64)
        p=plan('control_search',control_search=dict(candidate=ref,source=ref,settings=dict(version='local_control_search_v2')))
        cfg=dict(task=dict(family='task.tracking'))
        with patch('tools.research.state.guard'),patch('tools.research.state.state',return_value=dict(spec=dict(capabilities=['control_search'],budgets={'physical_launches':48}))),patch(
                'tools.research.design.verify_candidate',return_value={'configuration':cfg}),patch('tools.research_tasks.task_adapter'),patch(
                'tools.research.physical_replay.model_context') as backend:
            with self.assertRaisesRegex(ValueError,'UNSUPPORTED_CONTROL_SEARCH_TASK'):dispatch(SimpleNamespace(),p,'fixture')
        backend.assert_not_called()


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

    def test_forged_reference_rejected_and_unsupported_experiment_claim_annotated(self):
        with self.assertRaisesRegex(ValueError,'UNREGISTERED'):admit_decision(self.host,plan(decision=decision(),supporting_evidence=[self.ref]))
        proposal=plan(decision=decision(inference='structural_infeasibility'))
        result=admit_decision(self.host,proposal)
        self.assertEqual(result['inference_status'],'unsupported_inference')
        self.assertEqual(result['execution_basis'],'empirical_experiment')
        self.assertEqual(proposal.decision.claimed_inference,'structural_infeasibility')
        self.assertFalse(result['prospective_guarantee'])
        with self.assertRaisesRegex(ValueError,'INFERENCE_NOT_SUPPORTED'):
            admit_decision(self.host,plan('stop',decision=decision('STOP',inference='structural_infeasibility')))
        self.host.store.reserve.assert_not_called()

    def test_legal_exploration_needs_no_certificate(self):
        self.assertFalse(admit_decision(self.host,plan(decision=decision()))['prospective_guarantee'])

    def test_wrong_intent_rejected(self):
        with self.assertRaisesRegex(ValueError,'INTENT_ACTION'):admit_decision(self.host,plan(decision=decision('CONTROL_SEARCH')))
        self.s['success_gate']={'observed_task_pass':True}
        with self.assertRaisesRegex(ValueError,'EXACT_SELECTION_BEFORE_STOP'):admit_decision(self.host,plan('stop',decision=decision('STOP')))
        from tools.research.budget import closeout_operations
        self.assertEqual(closeout_operations(self.host)['research_plan'],['select'])

    def test_zero_rule_cannot_hide_nonzero_initial_state(self):
        spec=dict(start_mode='family_space',candidate_initialization='all_candidate_dofs_zero_v1')
        task=dict(initializer=dict(parameters=dict(data=dict(unspecified='zero',qpos_rad={'j':0.},qvel_rad_s={'j':0.}))))
        self.assertEqual(comparable_task(spec,task)['initializer']['parameters']['data'],dict(rule=spec['candidate_initialization']))
        task['initializer']['parameters']['data']['qvel_rad_s']['j']=.1
        with self.assertRaisesRegex(ValueError,'INITIAL_STATE_MISMATCH'):comparable_task(spec,task)

    def test_cross_task_evidence_rejected(self):
        self.s['results']=[self.ref]
        self.host.store.artifact.side_effect=lambda r:dict(candidate=self.ref) if r==self.ref else {}
        with patch('tools.research.evidence_policy.summarize_evidence',return_value={}),patch.object(self.host.store,'artifact',side_effect=[dict(candidate=self.ref),dict(configuration=dict(task={'id':'other'}))]):
            with self.assertRaisesRegex(ValueError,'TASK_IDENTITY'):admit_decision(self.host,plan(decision=decision(),supporting_evidence=[self.ref]))
        self.s['spec']['research_decisions']['background']=[dict(reference=self.ref)]
        with patch('tools.research.evidence_policy.summarize_evidence',return_value={'evidence_reference':self.ref}),patch.object(
                self.host.store,'artifact',side_effect=[dict(candidate=self.ref),dict(configuration=dict(task={'id':'other'}))]):
            result=admit_decision(self.host,plan(decision=decision(inference='local_diagnostic'),supporting_evidence=[self.ref]))
        self.assertEqual(result['inference_status'],'unsupported_inference')
        self.assertIn('EVIDENCE_TASK_IDENTITY_MISMATCH',result['claim_scope_issues'])

    def test_claim_transfer_is_soft_for_experiment_and_hard_for_formal_conclusion(self):
        self.s['results']=[self.ref]
        target=dict(robot={'id':'r'},task={'id':'t'},policy={k:{} for k in ('backend','discretization','dynamics_model')})
        for mismatch in ('design','model'):
            source=deepcopy(target)
            if mismatch=='design':source['robot']['id']='different'
            else:source['policy']['backend']={'different':True}
            with patch('tools.research.design.verify_candidate',return_value={'configuration':target}),patch(
                    'tools.research.evidence_policy.summarize_evidence',return_value={'evidence_reference':self.ref}),patch.object(self.host.store,'artifact',
                    side_effect=[dict(candidate=self.ref),dict(configuration=source)]):
                result=admit_decision(self.host,plan(decision=decision(inference='local_diagnostic',selected_candidate=self.ref),supporting_evidence=[self.ref]))
                self.assertEqual(result['inference_status'],'unsupported_inference')
                self.assertIn('EVIDENCE_DESIGN_IDENTITY_MISMATCH' if mismatch=='design' else 'EVIDENCE_MODEL_SCOPE_MISMATCH',result['claim_scope_issues'])
            with patch('tools.research.design.verify_candidate',return_value={'configuration':target}),patch(
                    'tools.research.evidence_policy.summarize_evidence',return_value={'evidence_reference':self.ref}),patch.object(self.host.store,'artifact',
                    side_effect=[dict(candidate=self.ref),dict(configuration=source)]):
                with self.assertRaisesRegex(ValueError,'DESIGN_IDENTITY' if mismatch=='design' else 'MODEL_SCOPE'):
                    admit_decision(self.host,plan('stop',decision=decision('STOP',inference='local_diagnostic',selected_candidate=self.ref),supporting_evidence=[self.ref]))


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
            self.assertEqual(current['method_remaining']['mathematical_evaluations'],8)
            self.assertEqual(current['rl_accounting']['admitted'],0)
            self.assertAlmostEqual(best['task_gap']['normalized_gap'],.054502039,places=8)
            self.assertEqual([round(v['time_s'],2) for v in best['violations']['samples']],[.3,.33])
            self.assertEqual(before,host.store.remaining());self.assertEqual(before['used']['backend_solves'],0)
            source=host.store.artifact(current['history'][0]['source'])
            self.assertEqual(np.asarray(source['trajectory']['tensions_n']).shape,(35,4))
            self.assertEqual(source,read(ROOT/'evidence/control_search_p1/best_control.json')['schedule'])
            citation=plan(decision=decision(),supporting_evidence=[current['history'][0]['source'],best['raw_reference']])
            self.assertEqual(len(admit_decision(host,citation)['resolved_evidence']),2)
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
            from tools.research.state import update
            update(host,research_status='stopped')
            self.assertEqual(context(host)['actions'],[])


if __name__=='__main__':unittest.main()
