"""Offline fixtures and a bounded real-GVS engineering pair; no physical acceptance."""
from copy import deepcopy
import json
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import numpy as np

from extensions.math_analysis.task_capability import task_capability
from tests.research.test_trajectory_feasibility import fixture
from tests.research import test_task_analysis_contract as task_fixtures
from tools.platform_store import plain
from tools.research import analysis
from tools.research.contracts import AnalysisRequest
from tools.research.evidence_views import result_card
from tools.research.state import state, update


def terminal_fixture(target=.5, radius=.1):
    model, req, p = fixture(nominal=0., duration=1.)
    c = req.constraints[0].model_copy(update=dict(indices=[1], reference=[[target]], radius=radius))
    return model, req.model_copy(update=dict(constraints=[c])), p


class SignedTests(unittest.TestCase):
    def test_signed_norm_satisfied_boundary_and_violation(self):
        m, r, p = terminal_fixture(target=0., radius=.25)
        for u, expected in ((0., -1.), (.25, 0.), (.5, 1.)):
            out = task_capability(m, r, p, applied_input_n=[[u]])
            self.assertAlmostEqual(out['best_found_violation'], expected)
            self.assertTrue(out['replay']['numerically_valid'])
            self.assertEqual(out['status'], 'feasible_witness' if expected <= 0 else 'inconclusive')
            self.assertEqual(out['quantities']['optimal_task_violation']['status'], 'unavailable')

    def test_asymmetric_interval_units_reference_and_normalization(self):
        m, r, p = terminal_fixture(target=.2)
        c = r.constraints[0].model_copy(update=dict(kind='component_interval', radius=None, lower=[-.1], upper=[.3]))
        r = r.model_copy(update=dict(constraints=[c]))
        for u, expected in ((.2, -1/3), (.5, 0.), (.8, 1.)):
            out = task_capability(m, r, p, applied_input_n=[[u]])
            self.assertAlmostEqual(out['best_found_violation'], expected)
            record = out['replay']['records'][0]
            self.assertEqual((record['units'], record['lower'], record['upper']), ('m', [-.1], [.3]))
            self.assertEqual(record['normalization_scale'], .3)

    def test_minimax_optimizes_margin_instead_of_energy(self):
        from extensions.math_analysis.trajectory import trajectory_feasibility
        m, r, p = terminal_fixture()
        old = trajectory_feasibility(m, r, p)
        out = task_capability(m, r, p)
        self.assertGreater(old['applied_input_n'][0][0], .399)
        self.assertLess(old['applied_input_n'][0][0], .401)
        self.assertAlmostEqual(out['applied_input_n'][0][0], .5, places=6)
        self.assertLess(out['best_found_violation'], -.99999)
        self.assertEqual(len(out['starts']), 3)
        self.assertTrue(all(s['finite_return'] for s in out['starts']))
        self.assertEqual(out['quantities']['lower_bound'], dict(value=-1., status='verified'))
        self.assertEqual(out['quantities']['upper_bound']['status'], 'unavailable')

    def test_tradeoff_bottleneck_and_positive_value_not_infeasibility_proof(self):
        m, r, p = terminal_fixture(target=.2)
        c = r.constraints[0].model_copy(update=dict(constraint_id='second', reference=[[.8]]))
        out = task_capability(m, r.model_copy(update=dict(constraints=r.constraints+[c])), p)
        self.assertAlmostEqual(out['best_found_violation'], 2., places=6)
        self.assertEqual(out['status'], 'inconclusive')
        self.assertIsNone(out['certificate'])
        self.assertEqual(len(out['co_bottleneck_records']), 2)
        self.assertEqual(out['research_diagnostics']['bottleneck']['sample_index'], 1)

    def test_failed_nonfinite_and_disagreeing_starts_keep_checked_best(self):
        m, r, p = terminal_fixture()
        for mode in ('nonfinite', 'failed', 'different'):
            returns = iter((.1, .4, .9))
            def solve(fun, x, **kw):
                u = next(returns)
                value = np.array([u, abs(u-.5)/.1-1]) if mode == 'different' else (
                    np.full(2, np.nan) if mode == 'nonfinite' else x)
                return NS(x=value, success=mode == 'nonfinite', status=9, message='fixture', nit=1)
            with patch('extensions.math_analysis.task_capability.minimize', side_effect=solve):
                out = task_capability(m, r, p)
            self.assertTrue(out['replay']['numerically_valid'])
            self.assertIn(out['status'], ('inconclusive', 'feasible_witness'))
            self.assertIsNone(out['certificate'])
            if mode == 'different':
                self.assertGreater(out['start_value_spread'], 1.)
                self.assertAlmostEqual(out['applied_input_n'][0][0], .4)

    def test_illegal_controls_replay_mismatch_and_nonfinite_model(self):
        m, r, p = terminal_fixture()
        for u in (-.01, 1.01, float('nan')):
            out = task_capability(m, r, p, applied_input_n=[[u]])
            self.assertNotIn('best_found_violation', out)
            self.assertEqual(out['status'], 'inconclusive')
        from extensions.math_analysis.trajectory import verify_witness
        def corrupt(*args):
            result = verify_witness(*args); result['max_prediction_replay_error'] = 1.
            return result
        with patch('extensions.math_analysis.task_capability.verify_witness', side_effect=corrupt):
            out = task_capability(m, r, p)
        self.assertFalse(out['replay']['numerically_valid'])
        self.assertEqual(out['quantities'], {})
        m.B = [[float('nan')]]
        self.assertEqual(task_capability(m, r, p)['status'], 'not_applicable')

    def test_partial_remaining_time_zero_horizon_feedthrough_and_channels(self):
        for nu in (1, 5, 7):
            m, r, p = fixture(nu=nu, start=2., feedthrough=.1)
            out = task_capability(m, r, p)
            self.assertEqual(out['coverage'][0]['unchecked_indices'], [0, 1])
            self.assertFalse(out['all_requested_checked'])
            self.assertLess(out['replay']['max_prediction_replay_error'], 1e-10)
            self.assertEqual(out['replay']['records'][0]['absolute_time_s'], 2.)
        m.operating_point.update(actual_time_s=3., remaining_task_s=0.)
        out = task_capability(m, r, p)
        self.assertEqual(out['applied_input_n'], [])
        self.assertEqual(out['starts'][0]['iterations'], 0)

    def test_zero_normalization_unsupported_signal_and_bad_time(self):
        m, r, p = terminal_fixture(radius=0.)
        self.assertEqual(task_capability(m, r, p)['status'], 'not_applicable')
        m, r, p = terminal_fixture()
        c = r.constraints[0].model_copy(update=dict(signal=r.constraints[0].signal.model_copy(update=dict(units='mm'))))
        out = task_capability(m, r.model_copy(update=dict(constraints=[c])), p)
        self.assertEqual(out['status'], 'not_applicable')
        self.assertEqual(out['coverage'][0]['unchecked_indices'], [1])
        p.period_s = .3
        self.assertEqual(task_capability(m, r, p)['status'], 'not_applicable')

    def test_scientific_controlled_gain_example(self):
        m, r, p = terminal_fixture(target=.8)
        m.B = [[.5]]
        base = task_capability(m, r, p)
        changed = deepcopy(m); changed.B = [[1.]]
        fixed = task_capability(changed, r, p, applied_input_n=base['applied_input_n'])
        optimized = task_capability(changed, r, p)
        # A synthetic authority increase can worsen a fixed command yet help after reoptimization.
        self.assertAlmostEqual(base['best_found_violation'], 2.)
        self.assertAlmostEqual(fixed['best_found_violation'], 1.)
        self.assertAlmostEqual(optimized['best_found_violation'], -1., places=6)
        self.assertEqual(fixed['control_reoptimization'], 'fixed_control')
        self.assertEqual(optimized['control_reoptimization'], 'required')


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        task_fixtures.TaskAnalysisTests.setUpClass()

    def setUp(self):
        self.f = task_fixtures.TaskAnalysisTests(); self.f.setUp()
        self.q = self.f.q.model_copy(update=dict(operation='task_capability'))

    def test_f0_card_exact_raw_pointers_and_unchanged_contract(self):
        from tests.research.test_research_reporting import offline_host, ref
        from tools.research.core import read_evidence
        value = json.loads(json.dumps(self.f.compute_fixture(self.q)))
        candidate = plain(self.q.candidate)
        value.update(candidate=candidate)
        reference = ref(value)
        host, current = offline_host({reference['artifact_id']:value, candidate['artifact_id']:dict(configuration=self.f.cfg)},
            analysis_results=[reference])
        before = deepcopy(current)
        card = result_card(host, reference)
        self.assertEqual(card.mathematics.claim.conclusion, 'feasible_witness')
        self.assertEqual(card.deterministic_summary['coverage'], 'full')
        for quantity in card.mathematics.quantities:
            if quantity.source:
                raw = read_evidence(host, plain(quantity.source), record_read=False)
                self.assertEqual(raw, quantity.value)
        self.assertEqual(current, before)
        self.assertFalse(card.authoritative_scientific_evidence)
        self.assertFalse(card.deterministic_summary['task_capability']['verification_scope']['optimality'])
        json.dumps(plain(card), allow_nan=False)

    def test_partial_and_unsupported_do_not_become_complete_success(self):
        m = self.f.fixture_model().model_copy(update=dict(operating_point=dict(actual_time_s=.31, remaining_task_s=.04)))
        q = self.q.model_copy(update=dict(operating_point='saved_state', saved_state=self.q.candidate))
        envelope = dict(records=[{}, dict(model=plain(m), point=m.operating_point, construction={})])
        with patch('extensions.tendon_family.math_analysis.calculate_candidate_configuration', return_value=envelope):
            out = analysis.calculate(self.f.cfg, self.f.binding, q, dict(actual_time_s=.31, u=m.u0))
        self.assertFalse(out['analysis_applicability']['full_task_supported'])
        self.assertIn('incomplete', out['scoped_claim']['supported_interpretation'])
        cfg = deepcopy(self.f.cfg)
        cfg['task']['environment']['data']['external_forces'] = [dict(entity='tip', force_n=[1.,0.,0.], start_s=0., end_s=.35)]
        with patch('extensions.tendon_family.math_analysis.calculate_candidate_configuration') as build:
            out = analysis.calculate(cfg, self.f.binding, self.q)
        build.assert_not_called()
        self.assertEqual(out['scoped_claim']['conclusion'], 'not_applicable')

    def test_comparison_rejects_task_solver_source_and_control_confounds(self):
        from tools.research.capability import CapabilityComparison, comparison_context
        raw = json.loads(json.dumps(self.f.compute_fixture(self.q)))
        raw.update(candidate=plain(self.q.candidate), implementation='fixture', requested_operation=plain(self.q))
        reference = dict(artifact_id='b'*64, media_type='application/json')
        base = dict(configuration=self.f.cfg, parameters=dict(segments=dict(near=dict(length_m=.16)), weight=1.),
            source_identity='source', profile_identity='profile')
        other = deepcopy(base); other['parameters']['segments']['near']['length_m'] = .161
        q = self.q.model_copy(update=dict(capability_comparison=CapabilityComparison(
            baseline_result=reference, variable='segments.near.length_m', normalization_scale=.16)))
        current = dict(analysis_results=[reference], freeze='fixture')
        with patch('tools.research.core.read_evidence', return_value=raw), \
                patch('tools.research.design.verify_candidate', return_value=base), \
                patch('tools.research.state.state', return_value=current):
            self.assertAlmostEqual(comparison_context(None, other, q)['step'], .001)
            for change in ('control', 'task', 'source', 'profile', 'parameter', 'solver', 'unregistered'):
                changed, request = deepcopy(other), q
                if change == 'control': changed['configuration']['policy']['controller']['version'] = 'different'
                elif change == 'task': changed['configuration']['task']['task_version'] = 'different'
                elif change in ('source', 'profile'): changed[change+'_identity'] = 'different'
                elif change == 'parameter': changed['parameters']['weight'] = 2.
                elif change == 'solver': request = q.model_copy(update=dict(protocol=q.protocol.model_copy(update=dict(endpoint_max_iterations=1))))
                else: current['analysis_results'] = []
                with self.subTest(change=change), self.assertRaises(ValueError):
                    comparison_context(None, changed, request)

    def test_failed_replay_does_not_project_verified_samples(self):
        from extensions.math_analysis.trajectory import verify_witness
        def corrupt(*args):
            result = verify_witness(*args); result['max_prediction_replay_error'] = 1.
            return result
        with patch('extensions.math_analysis.task_capability.verify_witness', side_effect=corrupt):
            out = self.f.compute_fixture(self.q)
        self.assertEqual(analysis.decision_result(out, plain(self.q.candidate))['margins'], [])
        self.assertEqual(out['scoped_claim']['conclusion'], 'inconclusive')
        self.assertTrue(all(not c['satisfied_indices'] for c in out['scoped_claim']['constraint_coverage']))

    def test_real_gvs_pair_dispatch_store_budget_and_reuse(self):
        from tests.research.test_mainline import MainlineTests
        from tools.research.design import construct
        from tools.research.capability import comparison_context
        case = MainlineTests(); case.setUp(); self.addCleanup(case.tearDown)
        update(case.host, freeze='F1-B-offline-engineering-fixture', mathematical_evaluations=0,
            profile={**state(case.host)['profile'], 'version':1})
        # Generated baseline and perturbation use the existing configuration builder.
        params = deepcopy(case.spec['reference_parameters'])
        baseline_candidate = construct(case.host, params, dict(label='F1-B offline baseline'))
        q = AnalysisRequest(candidate=baseline_candidate, operation='task_capability',
            operating_point='controller_start_input', protocol=case.spec['analysis_protocol'])
        first = analysis.dispatch(case.host, q, 'f1b-base', guard=lambda *a: None)
        self.assertEqual(first['status'], 'computed')
        params['segments']['near']['length_m'] += .001
        changed = construct(case.host, params, dict(label='F1-B offline +1mm near length'))
        compare = AnalysisRequest.model_validate(dict(**{**plain(q), 'candidate': changed}, capability_comparison=
            __import__('tools.research.capability', fromlist=['CapabilityComparison']).CapabilityComparison(
                baseline_result=first['reference'], variable='segments.near.length_m', normalization_scale=.16)))
        original_spec = state(case.host)['spec']
        limited = deepcopy(original_spec); limited['budgets']['mathematical_evaluations'] = 2
        update(case.host, spec=limited)
        with patch('tools.service_execution._run_contained') as worker, self.assertRaisesRegex(ValueError, 'BUDGET_CANNOT_FIT'):
            analysis.dispatch(case.host, compare, 'f1b-no-budget', guard=lambda *a: None)
        worker.assert_not_called()
        self.assertEqual(state(case.host)['mathematical_evaluations'], 1)
        update(case.host, spec=original_spec)
        second = analysis.dispatch(case.host, compare, 'f1b-plus', guard=lambda *a: None)
        raw = case.host.store.artifact(second['reference'])
        self.assertEqual(raw['status'], 'computed', raw.get('reason'))
        result = raw['trajectory']['structural_comparison']
        self.assertEqual(result['status'], 'computed_estimate')
        self.assertAlmostEqual(result['step'], .001)
        self.assertEqual(result['baseline_result'], first['reference'])
        self.assertEqual(raw['charged_analysis_evaluations'], 2)
        self.assertEqual(state(case.host)['mathematical_evaluations'], 3)
        before = state(case.host)['numerical_s']
        reused = analysis.dispatch(case.host, compare, 'f1b-plus', guard=lambda *a: None)
        self.assertEqual(reused['operation_reuse']['additional_analysis_evaluations'], 0)
        self.assertEqual(state(case.host)['numerical_s'], before)
        card = result_card(case.host, second['reference'])
        self.assertEqual(len(card.mathematics.quantities), 10)
        for bad in ('holding_tip_speed_weight', 'segments.near.tendon_count'):
            badq = compare.model_copy(update=dict(capability_comparison=compare.capability_comparison.model_copy(update=dict(variable=bad))))
            with self.assertRaises(ValueError):
                comparison_context(case.host, case.host.store.artifact(changed), badq)
        report = dict(label='Bounded offline engineering fixture, not formal Study or physical acceptance',
            baseline=case.host.store.artifact(first['reference']), changed=raw,
            baseline_result=first['reference'], changed_result=second['reference'], card=plain(card))
        from tools.research.state import science_hashes, core_hashes
        import platform, scipy
        report.update(source_hashes=dict(science=science_hashes(), core=core_hashes()),
            environment=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
                blas_threads=1),
            source_store=dict(root=str(case.host.store.root), run_id=case.host.run_id,
                lifecycle='Temporary engineering Store; exact exported artifacts remain below'),
            supporting_artifacts={})
        for reference in (baseline_candidate, changed):
            artifact = case.host.store.artifact(reference)
            report['supporting_artifacts'][reference['artifact_id']] = artifact
            config_ref = artifact['configuration_reference']
            report['supporting_artifacts'][config_ref['artifact_id']] = case.host.store.artifact(config_ref)
        for stored_result in (report['baseline'], raw):
            log = stored_result['worker_log']
            report['supporting_artifacts'][log['artifact_id']] = case.host.store.artifact(log)
        # Optional exact raw export is confined to an explicitly supplied evidence folder.
        import os
        if os.environ.get('F1B_EVIDENCE_DIR'):
            from pathlib import Path
            from tools.state_io import atomic_json
            folder = Path(os.environ['F1B_EVIDENCE_DIR']); folder.mkdir(parents=True, exist_ok=True)
            atomic_json(folder/'gvs_pair.json', report)
        print('F1B_GVS_PAIR', json.dumps(dict(base=report['baseline']['trajectory']['best_found_violation'],
            changed=raw['trajectory']['best_found_violation'], comparison=result['quantities'],
            seconds=[first['charged_numerical_s'], second['charged_numerical_s']],
            solver_success=[s['success'] for s in raw['trajectory']['starts']])))


if __name__ == '__main__':
    unittest.main()
