"""N2 offline contracts and bounded five-case parser audit (never live by default)."""
import argparse
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from schemas.platform import SessionInput
from tools.platform_tasks import compile_input
from tools.research.config import resolve, ROOT
from tools.research.task_constraints import describe_analysis_requirements
from tools.research_tasks import assemble_acceptance
from tools.task_intake import (ADOPT_REFERENCE, acceptance_view, compile_draft,
                              main, parse_response, request_draft)
from tests.research.test_task_intake import CASES, fixture, requirement


COMPLETE_CLAUSES = {
    '让末端到达目标 (0.29, 0.035, 0.19) m': 'behavior',
    '世界坐标系': 'constraint',
    '终点误差不超过 0.01 m': 'acceptance',
    '任务时长 0.35 s': 'acceptance',
    '最终保持窗口 0.05 s': 'acceptance',
    '保持窗口位置误差不超过 0.01 m': 'acceptance',
    '保持窗口速度不超过 0.02 m/s': 'acceptance',
    ADOPT_REFERENCE: 'constraint',
}


def complete_draft(clauses=None, *, intent='reach_and_hold', context=None, extra=()):
    text, response = fixture(intent, COMPLETE_CLAUSES if clauses is None else clauses, '末端', [])
    response['requirements'].extend(extra)
    result = parse_response(text, json.dumps(response, ensure_ascii=False), context=context)
    if result.draft is None:
        raise AssertionError(result.error)
    return result.draft


class CompilationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = resolve(ROOT / 'configs/research/study.json')

    def setUp(self):
        self.cfg = deepcopy(self.spec['configuration'])

    def compile(self, draft=None, **kwargs):
        return compile_draft(draft or complete_draft(), trusted_reference=self.cfg,
                             reference_label='explicit test snapshot', **kwargs)

    def test_complete_reach_preview_preserves_original_configuration_and_protocol(self):
        before = deepcopy(self.cfg)
        with patch('tools.research.config.resolve', side_effect=AssertionError('no mutable source reads')):
            result = self.compile(analysis_protocol=self.spec['analysis_protocol'])
        self.assertEqual(result.diagnostics, [])
        self.assertEqual(result.candidate_task.status, 'draft')
        self.assertEqual(result.capabilities['semantic']['status'], 'complete')
        self.assertEqual(result.capabilities['physical']['status'], 'supported')
        self.assertEqual(result.capabilities['evaluation']['status'], 'registered')
        self.assertEqual(result.capabilities['authorization']['status'], 'not_authorized')
        self.assertEqual(self.cfg, before)
        preview = result.configuration_preview.model_dump(mode='json')
        preview['task']['status'] = before['task']['status']
        preview['task']['source'] = before['task']['source']
        self.assertEqual(preview, SessionInput.model_validate(before).model_dump(mode='json'))
        pending = result.acceptance_spec['pending_evidence']
        self.assertEqual(pending, assemble_acceptance(result.configuration_preview, None, None))
        self.assertEqual(pending['status'], 'missing_evidence')
        self.assertTrue({'task_evaluator', 'evaluation_validity', 'execution_complete', 'solver_errors',
            'force_bounds', 'holding_coverage', 'holding_position', 'holding_speed'} <= pending['components'].keys())
        self.assertEqual(pending['components']['holding_coverage']['limit'], 6)
        self.assertEqual(result.acceptance_spec['limits'], dict(terminal_error_m=.01,
            holding_max_error_m=.01, holding_max_speed_m_s=.02))
        math = result.capabilities['mathematics']
        expected = describe_analysis_requirements(result.configuration_preview, {}).model_dump(mode='json')
        self.assertEqual(math['requirements'], expected)
        self.assertEqual([c['radius'] for c in expected['constraints']], [.01, .01, .02])
        self.assertEqual(expected['constraints'][1]['indices'], list(range(30, 36)))
        self.assertEqual(math['status'], 'assessed')
        endpoint = next(r for r in math['operations'] if r['operation'] == 'endpoint')
        self.assertFalse(endpoint['full_task_supported'])
        self.assertEqual(endpoint['coverage'][1]['status'], 'not_applicable')

    def test_missing_tolerance_and_time_are_explicit(self):
        draft = complete_draft({'让末端到达目标': 'behavior', '世界坐标系': 'constraint'}, intent='reach')
        result = self.compile(draft)
        self.assertIsNone(result.configuration_preview)
        self.assertTrue({'target', 'tolerance', 'duration'} <= set(result.capabilities['semantic']['missing']))

    def reference_question(self):
        text, proposal = fixture('reach_and_hold', COMPLETE_CLAUSES, '末端', [])
        proposal['requirements'].append(requirement('q', kind='undefined', source='undefined',
            question='最终窗口从 0.3 s 开始、积分步长为 0.0005 s 吗？'))
        return text, proposal

    def test_reference_question_numbers_require_reprojected_source(self):
        text, proposal = self.reference_question()
        view = acceptance_view(self.cfg)
        raw = json.dumps(proposal)
        result = parse_response(text, raw, context=view, trusted_reference=self.cfg)
        self.assertEqual(result.status, 'draft', result.error)
        question = result.draft.requirements[-1]
        self.assertIsNone(question.value)
        self.assertEqual(question.source_identity, view.source_identity)
        self.assertEqual(question.numeric_references['0.3'], ['view:/holding_interval_s/0'])
        self.assertIn('facts:/task/timing/timestep_s', question.numeric_references['0.0005'])
        self.assertIn('UNGROUNDED_NUMERIC_CANDIDATE', parse_response(text, raw, context=view).error)
        for change in ({'source_identity': 'f' * 64}, {'task_identity': 'e' * 64},
                       {'holding_interval_s': [.301, .35]},
                       {'facts': {**view.facts, '/task/timing/timestep_s': .002}}):
            forged = view.model_copy(update=change)
            self.assertIn('REFERENCE_CONTEXT_MISMATCH',
                parse_response(text, raw, context=forged, trusted_reference=self.cfg).error)
        bad = deepcopy(proposal)
        bad['requirements'][-1]['question'] = '是否采用 0.301 s？'
        self.assertIn('UNGROUNDED_NUMERIC_CANDIDATE',
            parse_response(text, json.dumps(bad), context=view, trusted_reference=self.cfg).error)
        # Metadata is program-owned; models cannot submit numeric provenance.
        bad['requirements'][-1]['numeric_references'] = {'0.301': ['view:/holding_interval_s/0']}
        self.assertIsNone(parse_response(text, json.dumps(bad), context=view, trusted_reference=self.cfg).draft)

    def test_reference_questions_and_forged_provenance_never_auto_resolve(self):
        text, proposal = self.reference_question()
        proposal['temporal_relations'] = [dict(first='r4', relation='during', second='r3', quote=text)]
        draft = parse_response(text, json.dumps(proposal), trusted_reference=self.cfg).draft
        result = self.compile(draft)
        self.assertIsNone(result.configuration_preview)
        self.assertEqual(result.capabilities['temporal']['mappings'][0]['status'], 'mapped')
        review = result.capabilities['reference_review']
        self.assertEqual(review['source_identity'], acceptance_view(self.cfg).source_identity)
        self.assertEqual(review['known_conditions']['holding_interval_s'], [.3, .35])
        self.assertEqual(review['questions'][0]['question'], proposal['requirements'][-1]['question'])
        self.assertEqual(review['questions'][0]['status'], 'unresolved')
        self.assertEqual(result.requirement_mappings[-1]['status'], 'missing')
        for change in ({'source_identity': 'f' * 64}, {'numeric_references': {}},
                       {'numeric_references': {'0.3': ['view:/holding_interval_s/1']}}, {'value': .3}):
            forged = draft.model_copy(update={'requirements': draft.requirements[:-1] +
                [draft.requirements[-1].model_copy(update=change)]})
            rejected = self.compile(forged)
            self.assertIsNone(rejected.candidate_task)
            self.assertIn('DRAFT_SOURCE_VALUES_OR_IDENTITY_MISMATCH', rejected.diagnostics)
        # Reusing a number for a different unit/quantity is still an unapproved
        # question, never a new threshold, even though its numeric source exists.
        proposal['requirements'][-1]['question'] = '位置容差是否应为 0.3 m？'
        questionable = parse_response(text, json.dumps(proposal), trusted_reference=self.cfg).draft
        self.assertIsNone(questionable.requirements[-1].value)
        self.assertIsNone(self.compile(questionable).candidate_task)

    def test_cli_passes_full_context_source_for_offline_numeric_questions(self):
        text, proposal = self.reference_question()
        folder = ROOT / 'runs' / ('intake-reference-' + uuid4().hex)
        folder.mkdir()
        response, reference = folder / 'response.json', folder / 'reference.json'
        try:
            response.write_text(json.dumps(proposal), encoding='utf-8')
            reference.write_text(json.dumps(self.cfg), encoding='utf-8')
            with patch('openai.OpenAI', side_effect=AssertionError('offline')), redirect_stdout(io.StringIO()) as output:
                code = main(['--text', text, '--response-file', str(response),
                             '--context', str(reference), '--compile-reference', str(reference)])
            data = json.loads(output.getvalue())
            self.assertEqual(code, 2)  # Review required, not a parse failure.
            self.assertEqual(data['intake']['status'], 'draft')
            self.assertIsNone(data['compilation']['configuration_preview'])
            self.assertIn('0.3', data['intake']['draft']['requirements'][-1]['numeric_references'])
        finally:
            response.unlink(missing_ok=True)
            reference.unlink(missing_ok=True)
            folder.rmdir()

    @patch.dict(os.environ, {'TASK_INTAKE_API_KEY': 'synthetic',
                            'TASK_INTAKE_BASE_URL': 'https://intake.invalid'}, clear=True)
    def test_mocked_request_checks_context_before_send_and_propagates_source(self):
        text, proposal = self.reference_question()
        view = acceptance_view(self.cfg)
        with patch('openai.OpenAI', side_effect=AssertionError('must not send forged context')):
            result = request_draft(text, enable_provider=True, model='test', trusted_reference=self.cfg,
                context=view.model_copy(update={'source_identity': 'forged'}))
            self.assertIn('REFERENCE_CONTEXT_MISMATCH', result.error)
        client = Mock()
        client.chat.completions.create.return_value = SimpleNamespace(usage=None, choices=[SimpleNamespace(
            finish_reason='stop', message=SimpleNamespace(content=json.dumps(proposal), tool_calls=None, refusal=None))])
        with patch('openai.OpenAI') as factory:
            factory.return_value.__enter__.return_value = client
            result = request_draft(text, enable_provider=True, model='test',
                                   context=view, trusted_reference=self.cfg)
            self.assertEqual(result.status, 'draft', result.error)
            self.assertEqual(result.draft.requirements[-1].source_identity, view.source_identity)
            client.chat.completions.create.assert_called_once()

    def test_final_window_containment_adds_no_acceptance_or_execution_right(self):
        text, proposal = fixture('reach_and_hold', COMPLETE_CLAUSES, '末端', [])
        proposal['temporal_relations'] = [dict(first='r4', relation='during', second='r3', quote=text)]
        result = self.compile(parse_response(text, json.dumps(proposal)).draft)
        self.assertIsNotNone(result.configuration_preview, result.diagnostics)
        self.assertEqual(result.acceptance_spec, self.compile().acceptance_spec)
        self.assertEqual(result.capabilities['mathematics'], self.compile().capabilities['mathematics'])
        with self.assertRaisesRegex(ValueError, 'DEVELOPMENT_HOST_REQUIRES_DEVELOPMENT_VALID'):
            compile_input(result.configuration_preview.model_dump(mode='json'))
        for first, relation, second in [('r3', 'during', 'r4'), ('r4', 'throughout', 'r3'),
                                        ('r0', 'before', 'r4'), ('r4', 'after', 'r3')]:
            proposal['temporal_relations'] = [dict(first=first, relation=relation, second=second, quote=text)]
            self.assertIsNone(self.compile(parse_response(text, json.dumps(proposal)).draft).candidate_task)

    def test_unsupported_semantics_do_not_require_adopting_reach(self):
        for name in ('catch', 'obstacle', 'tracking'):
            text, proposal = CASES[name]
            if name == 'obstacle':
                text = '设计一条软臂；' + text  # Deliberately omitted by the model.
            draft = parse_response(text, json.dumps(proposal)).draft
            for kwargs in ({}, dict(trusted_reference=self.cfg, reference_label='test')):
                result = compile_draft(draft, **kwargs)
                self.assertEqual(result.semantic_spec.user_text, text)
                self.assertIsNone(result.configuration_preview)
                self.assertEqual(result.capabilities['evaluation']['status'], 'unsupported')
                self.assertFalse(any('REFERENCE_REQUIRED' in d or 'ADOPTION_REQUIRED' in d
                                     for d in result.diagnostics))
                if name == 'obstacle':
                    self.assertIn('设计一条软臂', ''.join(g.text for g in draft.unquoted_spans))
                    self.assertIn('UNMAPPED_USER_CONSTRAINT: 设计一条软臂', result.diagnostics)

    def test_hold_relations_map_only_existing_inclusive_sampled_constraints(self):
        text, proposal = fixture('reach_and_hold', COMPLETE_CLAUSES, '末端', [])
        proposal['temporal_relations'] = [
            dict(first='r5', relation='during', second='r4', quote='；'.join(list(COMPLETE_CLAUSES)[4:6])),
            dict(first='r6', relation='throughout', second='r4', quote='；'.join(list(COMPLETE_CLAUSES)[4:7]))]
        result = self.compile(parse_response(text, json.dumps(proposal)).draft)
        self.assertIsNotNone(result.configuration_preview, result.diagnostics)
        for edge in result.capabilities['temporal']['mappings']:
            self.assertEqual(edge['status'], 'mapped')
            self.assertAlmostEqual(edge['interval_s'][0], .30)
            self.assertEqual(edge['interval_s'][1], .35)
        expected = self.compile()
        self.assertEqual(result.acceptance_spec, expected.acceptance_spec)
        self.assertEqual(result.capabilities['mathematics'], expected.capabilities['mathematics'])
        with self.assertRaisesRegex(ValueError, 'DEVELOPMENT_HOST_REQUIRES_DEVELOPMENT_VALID'):
            compile_input(result.configuration_preview.model_dump(mode='json'))
        for edge in (dict(first='r5', relation='after', second='r4'),
                     dict(first='r4', relation='during', second='r5'),
                     dict(first='r0', relation='before', second='r4'),
                     dict(first='r2', relation='during', second='r4')):
            changed = deepcopy(proposal)
            changed['temporal_relations'].append({**edge, 'quote': text})
            rejected = self.compile(parse_response(text, json.dumps(changed)).draft)
            self.assertIsNone(rejected.candidate_task)
            self.assertIn('TEMPORAL_RELATIONS_REQUIRE_REVIEW', ' '.join(rejected.diagnostics))

    def test_unquoted_conditions_and_forged_coverage_cannot_bypass_full_input(self):
        text, proposal = fixture('reach_and_hold', COMPLETE_CLAUSES, '末端', [])
        # A known but unquoted condition remains mapped by the full-text compiler.
        proposal['requirements'].pop(5)
        draft = parse_response(text, json.dumps(proposal)).draft
        self.assertTrue(draft.unquoted_spans)
        result = self.compile(draft)
        self.assertIsNotNone(result.candidate_task)
        self.assertEqual(result.capabilities['quotation_coverage']['status'], 'needs_review')
        for hidden in ('整个运动过程中软臂任何部位不能碰撞障碍物', '终点误差不超过 0.001 m',
                       '保持窗口开始前必须已到达目标', '接近小球不等于捕获成功',
                       '捕获后必须保持且不能反弹脱离'):
            original = text + '；' + hidden
            draft = parse_response(original, json.dumps(proposal)).draft
            self.assertIsNotNone(draft)
            self.assertIn(hidden, ''.join(g.text for g in draft.unquoted_spans))
            forged = draft.model_copy(update={'unquoted_spans': []})
            result = self.compile(forged)
            self.assertIsNone(result.candidate_task, hidden)
            self.assertIn(hidden, ''.join(g['text'] for g in
                result.capabilities['quotation_coverage']['unquoted_spans']))
            self.assertTrue(any('UNMAPPED_USER_CONSTRAINT' in d or 'REFERENCE_CONFLICT' in d
                                for d in result.diagnostics))

    def test_capture_proximity_claim_never_becomes_acceptance(self):
        text, proposal = CASES['catch']
        proposal = deepcopy(proposal)
        proposal.update(intent='reach', explanation='末端接近小球就算捕获成功。')
        draft = parse_response(text, json.dumps(proposal)).draft
        self.assertIsNotNone(draft)  # Explanation is visible, unverified interpretation.
        result = self.compile(draft)
        self.assertIsNone(result.candidate_task)
        self.assertIsNone(result.acceptance_spec)
        self.assertIn('UNMAPPED_USER_CONSTRAINT', ' '.join(result.diagnostics))
        proposal['requirements'][0]['quote'] = '末端接近小球就算捕获成功'
        self.assertIn('USER_QUOTE_NOT_FOUND', parse_response(text, json.dumps(proposal)).error)

    def test_new_constraints_and_even_wrong_llm_kind_cannot_disappear(self):
        for text in ('全程不能超过 5 N', '途中避开球形障碍物', '必须连续时间满足容差',
                     '除终点外不得进入目标区域', '保持窗口速度不超过 0.01 m/s'):
            clauses = {**COMPLETE_CLAUSES, text: 'observable'}
            result = self.compile(complete_draft(clauses, intent='reach'))
            self.assertIsNone(result.configuration_preview, text)
            self.assertTrue(any(row['quote'] == text and row['status'] == 'unresolved'
                                for row in result.requirement_mappings))
        # Putting all text into one quote does not bypass whole-text compilation.
        clauses = {'；'.join(COMPLETE_CLAUSES) + '；途中避开障碍物': 'behavior'}
        self.assertIsNone(self.compile(complete_draft(clauses, intent='reach')).candidate_task)

    def test_unregistered_tasks_and_implementation_diagnostics(self):
        for case, expected in [('tracking', 'tracking evaluator'), ('obstacle', 'collision/distance signals'),
                               ('catch', 'contact/capture evaluator'), ('disturbance', 'platform/disturbance signals')]:
            text, proposal = CASES[case]
            draft = parse_response(text, json.dumps(proposal)).draft
            result = self.compile(draft)
            self.assertEqual(result.semantic_spec, draft)
            self.assertIsNone(result.candidate_task)
            self.assertEqual(result.capabilities['evaluation']['status'], 'unsupported')
            self.assertEqual(result.capabilities['physical']['status'], 'not_assessed')
            self.assertIn(expected, result.capabilities['evaluation']['reasons'])
            self.assertEqual(result.capabilities['mathematics']['status'], 'not_applicable')

    def test_conflict_never_overwrites_reference(self):
        before = deepcopy(self.cfg)
        clauses = dict(COMPLETE_CLAUSES)
        del clauses['终点误差不超过 0.01 m']
        clauses['终点误差不超过 0.001 m'] = 'acceptance'
        result = self.compile(complete_draft(clauses))
        self.assertIsNone(result.candidate_task)
        self.assertTrue(any('REFERENCE_CONFLICT' in d for d in result.diagnostics))
        self.assertEqual(self.cfg, before)

    def test_all_previews_stay_draft_and_original_gate_rejects_them(self):
        for intent in ('reach', 'reach_and_hold'):
            result = self.compile(complete_draft(intent=intent))
            with self.assertRaisesRegex(ValueError, 'DEVELOPMENT_HOST_REQUIRES_DEVELOPMENT_VALID'):
                compile_input(result.configuration_preview.model_dump(mode='json'))
        self.cfg['task']['status'] = 'draft'
        result = self.compile()
        self.assertIsNone(result.configuration_preview)
        self.assertIn('drafts cannot execute', result.capabilities['physical']['reason'])
        self.assertEqual(self.cfg['task']['status'], 'draft')

    def test_actual_backend_controller_signal_and_timing_checks(self):
        changes = [lambda c: c['policy']['backend'].update(extension_id='backend.missing'),
                   lambda c: c['policy']['controller'].update(extension_id='controller.missing'),
                   lambda c: c['task']['observations'][0].update(units='mm'),
                   lambda c: c['task']['timing'].update(duration_s=.3501)]
        for mutate in changes:
            self.cfg = deepcopy(self.spec['configuration'])
            mutate(self.cfg)
            result = self.compile()
            self.assertIsNone(result.configuration_preview)
            self.assertTrue(result.diagnostics)

    def test_reference_is_explicit_full_snapshot_not_a_view_or_task(self):
        draft = complete_draft()
        for reference in (None, acceptance_view(self.cfg).model_dump(mode='json'), self.cfg['task']):
            result = compile_draft(draft, trusted_reference=reference, reference_label='fixture')
            self.assertIsNone(result.configuration_preview)
        result = compile_draft(draft, trusted_reference=self.cfg)
        self.assertIn('EXPLICIT_REFERENCE_LABEL_REQUIRED', ' '.join(result.diagnostics))
        self.assertEqual(self.compile().capabilities['mathematics']['status'], 'not_assessed')
        result = self.compile(analysis_protocol={})
        self.assertIsNotNone(result.candidate_task)
        self.assertEqual(result.capabilities['mathematics']['status'], 'not_assessed')

    def test_cli_compile_and_five_case_offline_audit(self):
        text, proposal = fixture('reach_and_hold', COMPLETE_CLAUSES, '末端', [])
        folder = ROOT / 'runs' / ('intake-cli-' + uuid4().hex)
        folder.mkdir()
        response, reference = folder / 'response.json', folder / 'reference.json'
        try:
            response.write_text(json.dumps(proposal), encoding='utf-8')
            reference.write_text(json.dumps(self.cfg), encoding='utf-8')
            with redirect_stdout(io.StringIO()) as output:
                code = main(['--text', text, '--response-file', str(response), '--compile-reference', str(reference)])
        finally:
            response.unlink(missing_ok=True)
            reference.unlink(missing_ok=True)
            folder.rmdir()
        self.assertEqual(code, 0, output.getvalue())
        self.assertEqual(json.loads(output.getvalue())['compilation']['candidate_task']['status'], 'draft')
        with (patch('openai.OpenAI', side_effect=AssertionError('offline audit cannot connect')),
                redirect_stdout(io.StringIO()) as output):
            self.assertEqual(validation_main([]), 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report['max_requests'], 0)
        self.assertEqual(len(report['reports']), 5)
        self.assertTrue(all(r['semantic_correct'] is None for r in report['reports']))
        with redirect_stdout(io.StringIO()), patch('sys.stderr', new=io.StringIO()):
            with self.assertRaises(SystemExit):
                validation_main(['--enable-provider', '--case', 'all'])

    def test_config_provenance_forgery_candidates_and_missing_questions(self):
        pointer = '/task/evaluator/parameters/data/tolerance_m'
        draft = complete_draft(context=acceptance_view(self.cfg), extra=[
            requirement('config', source='verified_configuration', pointer=pointer)])
        result = self.compile(draft)
        self.assertIsNotNone(result.candidate_task)
        self.assertEqual(result.requirement_mappings[-1]['status'], 'adopted_reference')
        for change in ({'value': .001}, {'source_identity': 'f' * 64}):
            bad = draft.model_copy(update={'requirements': draft.requirements[:-1] +
                [draft.requirements[-1].model_copy(update=change)]})
            self.assertIsNone(self.compile(bad).candidate_task)
        for source in ('undefined', 'llm_candidate'):
            draft = complete_draft(extra=[requirement('question', source=source, question='是否需要连续时间保证？')])
            self.assertIsNone(self.compile(draft).candidate_task)
        forged = complete_draft().model_copy(update={'user_text': complete_draft().user_text + '；全程避障'})
        self.assertIsNone(self.compile(forged).candidate_task)


class ProviderBoundaryTests(unittest.TestCase):
    def test_observed_quote_and_source_failures_remain_closed_offline(self):
        # Small synthetic reproductions of real failures; no repaired live output
        # is substituted for a provider result or admitted into compilation.
        text, proposal = fixture('reach_and_hold', {
            '末端到达目标': 'behavior', '然后保持 0.20 s': 'acceptance',
            '目标位置尚未指定': 'constraint'}, '末端', [])
        mutations = []
        changed = deepcopy(proposal)
        changed['temporal_relations'] = [dict(first='r0', relation='then', second='r1',
            quote='末端到达目标然后保持 0.20 s')]
        mutations.append((changed, 'USER_QUOTE_NOT_FOUND'))
        changed = deepcopy(proposal)
        changed['requirements'][-1].update(source='undefined', question='目标位置是什么？')
        mutations.append((changed, 'SOURCE_CONTENT_CONFLICT'))
        changed = deepcopy(proposal)
        changed['requirements'].append(requirement('question', source='undefined', question='0.21 s 从何时开始？'))
        mutations.append((changed, 'UNGROUNDED_NUMERIC_CANDIDATE'))
        for response, error in mutations:
            result = parse_response(text, json.dumps(response))
            self.assertIsNone(result.draft)
            self.assertIn(error, result.error)

    def test_observed_benign_encoding_failures_become_review_drafts(self):
        text, proposal = fixture('catch_and_hold', {
            '软臂接住小球': 'behavior', '接住后保持 0.20 s': 'acceptance',
            '捕获定义尚未指定': 'constraint'}, '小球', [])
        del proposal['requirements'][0]['config_pointer']
        proposal['requirements'][-1] = requirement('unknown', source='undefined', question='捕获定义是什么？')
        proposal['requirements'].append(requirement('question', source='undefined', question='0.20 s 从何时开始？'))
        result = parse_response(text, json.dumps(proposal))
        self.assertEqual(result.status, 'draft', result.error)
        self.assertIn('捕获定义尚未指定', ''.join(g.text for g in result.draft.unquoted_spans))
        self.assertIsNone(result.draft.requirements[-1].value)
        self.assertIn('0.20 s 从何时开始？', result.draft.missing_definitions)

    @patch.dict(os.environ, {'TASK_INTAKE_API_KEY': 'synthetic',
                            'TASK_INTAKE_BASE_URL': 'https://api.deepseek.com'}, clear=True)
    def test_deepseek_requires_explicit_disabled_without_connecting(self):
        with patch('openai.OpenAI', side_effect=AssertionError('must not connect')):
            for mode in (None, 'enabled'):
                result = request_draft('任务', enable_provider=True, model='deepseek-flash', thinking=mode)
                self.assertEqual(result.error, 'DEEPSEEK_REQUIRES_EXPLICIT_THINKING_DISABLED')

    @patch.dict(os.environ, {'TASK_INTAKE_API_KEY': 'synthetic', 'TASK_INTAKE_BASE_URL': 'https://intake.invalid/v1'}, clear=True)
    def test_explicit_non_thinking_single_request_and_truncation_stays_closed(self):
        text, proposal = CASES['reach']
        message = SimpleNamespace(content=json.dumps(proposal), tool_calls=None, refusal=None)
        choice = SimpleNamespace(message=message, finish_reason='stop')
        client = Mock()
        client.chat.completions.create.return_value = SimpleNamespace(choices=[choice], usage=None)
        with patch('openai.OpenAI') as factory:
            factory.return_value.__enter__.return_value = client
            for mode in (None, 'disabled', 'enabled'):
                client.reset_mock()
                result = request_draft(text, enable_provider=True, model='test', thinking=mode, max_tokens=8192)
                self.assertEqual(result.status, 'draft')
                self.assertEqual(result.provider_receipt['thinking'], mode or 'provider_default')
                options = client.chat.completions.create.call_args.kwargs
                self.assertEqual(options['max_tokens'], 8192)
                if mode is None:
                    self.assertNotIn('extra_body', options)
                else:
                    self.assertEqual(options['extra_body'], {'thinking': {'type': mode}})
                client.chat.completions.create.assert_called_once()
            choice.finish_reason = 'length'
            for partial in ('', '{"goal_quote":"catch","intent":"catch_and_hold"'):
                message.content = partial
                client.reset_mock()
                result = request_draft(text, enable_provider=True, model='test', thinking='disabled')
                self.assertEqual(result.error, 'INCOMPLETE_MODEL_RESPONSE: length')
                self.assertIsNone(result.draft)
                client.chat.completions.create.assert_called_once()
            client.reset_mock()
            self.assertEqual(request_draft(text, enable_provider=True, model='test', thinking='auto').error,
                             'INVALID_THINKING_MODE')
            client.chat.completions.create.assert_not_called()
        # Both existing CLIs must forward the explicit choice to the same client.
        expected = parse_response(text, json.dumps(proposal))
        with (patch('tools.task_intake.request_draft', return_value=expected) as call,
              redirect_stdout(io.StringIO())):
            self.assertEqual(main(['--text', text, '--enable-provider', '--model', 'test', '--thinking', 'disabled']), 0)
            self.assertEqual(call.call_args.kwargs['thinking'], 'disabled')
        with (patch(__name__ + '.request_draft', return_value=expected) as call,
              redirect_stdout(io.StringIO())):
            self.assertEqual(validation_main(['--case', 'reach', '--enable-provider', '--model', 'test',
                                             '--thinking', 'disabled']), 0)
            call.assert_called_once()
            self.assertEqual(call.call_args.kwargs['thinking'], 'disabled')

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'wrong-service', 'OPENAI_BASE_URL': 'https://wrong.invalid',
                             'DEEPSEEK_API_KEY': 'also-wrong'}, clear=True)
    def test_no_fallback_to_other_provider(self):
        with patch('openai.OpenAI', side_effect=AssertionError('must not connect')):
            result = request_draft('任务', enable_provider=True, model='test')
        self.assertIn('TASK_INTAKE_API_KEY', result.error)

    @patch.dict(os.environ, {'TASK_INTAKE_API_KEY': 'synthetic', 'TASK_INTAKE_BASE_URL': 'https://intake.invalid/v1'}, clear=True)
    def test_one_bounded_request_receipt_and_finish_reason(self):
        text, proposal = CASES['reach']
        response = SimpleNamespace(usage=SimpleNamespace(model_dump=lambda **kw:
            dict(prompt_tokens=12, completion_tokens=7, total_tokens=19)), choices=[SimpleNamespace(
                message=SimpleNamespace(content=json.dumps(proposal), tool_calls=None, refusal=None), finish_reason='stop')])
        client = Mock(); client.chat.completions.create.return_value = response
        with patch('openai.OpenAI') as factory:
            factory.return_value.__enter__.return_value = client
            result = request_draft(text, enable_provider=True, model='synthetic', max_tokens=500, timeout_s=5)
            self.assertEqual(result.provider_receipt['usage']['total_tokens'], 19)
            self.assertIsNone(result.provider_receipt['monetary_cost'])
            self.assertNotIn('synthetic', json.dumps(factory.call_args.kwargs.get('default_headers', {})))
            client.chat.completions.create.assert_called_once()
            self.assertEqual(client.chat.completions.create.call_args.kwargs['max_tokens'], 500)
            self.assertEqual(factory.call_args.kwargs['timeout'], 5)
            for reason in ('length', 'content_filter', 'tool_calls', None):
                response.choices[0].finish_reason = reason
                self.assertEqual(request_draft(text, enable_provider=True, model='synthetic').status, 'parse_failed')
        with patch('openai.OpenAI', side_effect=AssertionError('invalid bounds must not connect')):
            for kwargs in ({'max_tokens': 8193}, {'timeout_s': 61}, {'base_url': 'http://unsafe.invalid'},
                           {'base_url': 'https://user:secret@intake.invalid'}):
                self.assertEqual(request_draft(text, enable_provider=True, model='synthetic', **kwargs).status, 'parse_failed')


def validation_main(argv=None):
    """One live case per invocation after authorization; no automatic retries."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=['all', 'reach', 'tracking', 'obstacle', 'catch', 'disturbance'], default='all')
    parser.add_argument('--enable-provider', action='store_true')
    parser.add_argument('--model')
    parser.add_argument('--base-url')
    parser.add_argument('--max-tokens', type=int, default=2000)
    parser.add_argument('--timeout-s', type=float, default=30)
    parser.add_argument('--thinking', choices=['enabled', 'disabled'])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    if args.enable_provider and args.case == 'all':
        parser.error('Live validation is limited to one explicitly selected case per invocation.')
    reports = []
    names = ['reach', 'tracking', 'obstacle', 'catch', 'disturbance'] if args.case == 'all' else [args.case]
    for name in names:
        text, proposal = CASES[name]
        result = (request_draft(text, enable_provider=True, model=args.model, base_url=args.base_url,
                    max_tokens=args.max_tokens, timeout_s=args.timeout_s, thinking=args.thinking) if args.enable_provider else
                  parse_response(text, json.dumps(proposal, ensure_ascii=False)))
        draft = result.draft
        reports.append(dict(case=name, evidence_kind='real_provider' if args.enable_provider else 'synthetic_fixture',
            task=text, format_pass=result.status == 'draft', failure_reason=result.error,
            expected_intent=proposal['intent'], intent_match=None if draft is None else draft.intent == proposal['intent'],
            semantic_correct=None, semantic_review_status='human_review_required',
            review_checks=['Task class correct, no downgrade', 'Every explicit acceptance condition preserved',
                           'Missing definitions identified', 'No invented thresholds, signals or facts',
                           'Temporal meaning retained; quotation coverage alone is insufficient'],
            result=result.model_dump(mode='json')))
    output = json.dumps(dict(max_requests=1 if args.enable_provider else 0, reports=reports), ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + '\n', encoding='utf-8')
    else:
        print(output)
    return 0 if all(r['format_pass'] and r['intent_match'] for r in reports) else 2


def write_demo(folder):
    """Offline delivery examples; resolver is used only by this fixture driver."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    spec = resolve(ROOT / 'configs/research/study.json')
    reference = spec['configuration']
    text, response = fixture('reach_and_hold', COMPLETE_CLAUSES, '末端', [])
    (folder / 'task.txt').write_text(text, encoding='utf-8')
    (folder / 'response.json').write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding='utf-8')
    (folder / 'reference.json').write_text(json.dumps(reference, indent=2), encoding='utf-8')
    (folder / 'analysis_protocol.json').write_text(json.dumps(spec['analysis_protocol'], indent=2), encoding='utf-8')
    examples = {'complete_reach': complete_draft(),
        'missing_reach': complete_draft({'让末端到达目标': 'behavior'}, intent='reach'),
        'conflicting_reach': complete_draft({**COMPLETE_CLAUSES, '终点误差不超过 0.001 m': 'acceptance'}),
        'extra_constraint': complete_draft({**COMPLETE_CLAUSES, '全程不能超过 5 N': 'constraint'})}
    for name in ('tracking', 'obstacle', 'catch', 'disturbance'):
        task, proposal = CASES[name]
        examples[name] = parse_response(task, json.dumps(proposal)).draft
    for name, draft in examples.items():
        result = compile_draft(draft, trusted_reference=reference, reference_label='configs/research/study.json resolved offline fixture',
                               analysis_protocol=spec['analysis_protocol'])
        (folder / (name + '.json')).write_text(result.model_dump_json(indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(folder=str(folder), examples=list(examples), evidence='offline fixture; no physical or LLM quality evidence')))


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--write-demo':
        write_demo(sys.argv[2])
        raise SystemExit(0)
    if '--validate' in sys.argv:
        raise SystemExit(validation_main([v for v in sys.argv[1:] if v != '--validate']))
    unittest.main()
