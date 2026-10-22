"""Synthetic model responses only: parser boundaries, not LLM quality or evidence."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from schemas.platform import SessionInput
from schemas.task_intake import TaskIntakeDraft
from tools.state_io import read, digest
from tools.task_intake import (SETTLING, acceptance_view, main, parse_response,
                               request_draft, request_messages)

ROOT = Path(__file__).resolve().parents[2]


def requirement(id, quote=None, *, kind='behavior', source='user_explicit', pointer=None, question=None):
    return dict(id=id, kind=kind, source=source, quote=quote, config_pointer=pointer, question=question)


def fixture(intent, clauses, object_quote, missing, relations=()):
    text = '；'.join(clauses)
    rows = [requirement('r' + str(i), q, kind=k) for i, (q, k) in enumerate(clauses.items())]
    rows += [requirement('m' + str(i), source='undefined', kind='acceptance', question=q)
             for i, q in enumerate(missing)]
    proposal = dict(goal_quote=next(iter(clauses)), object_quote=object_quote, intent=intent,
        requirements=rows, temporal_relations=list(relations), explanation='离线合成解释：保留原任务，缺失条件待确认。')
    return text, proposal


CASES = {
    'reach': fixture('reach', {'让末端到达目标 (0.29, 0.035, 0.19) m': 'behavior',
        '终点误差不超过 0.01 m': 'acceptance'}, '末端', ['坐标系、任务时长和评价器是什么？']),
    'hold': fixture('reach_and_hold', {'让末端到达目标': 'behavior', '然后保持 2 s': 'behavior',
        '全程不能超过 5 N': 'constraint'}, '末端', ['目标、位置和速度容差、力的对象和信号如何定义？'],
        [dict(first='r0', relation='then', second='r1', quote='然后保持 2 s')]),
    'tracking': fixture('tracking', {'末端跟踪圆形轨迹，半径 0.1 m，周期 3 s': 'behavior',
        '连续跟踪 4 圈': 'constraint'}, '末端', ['圆心、平面、相位、坐标系和误差判据是什么？',
        '轨迹信号和评价器如何定义？']),
    'obstacle': fixture('obstacle_reach', {'末端到达 (0.3, 0, 0.2) m': 'behavior',
        '途中避开球形障碍物': 'environment', '与障碍物间距至少 0.02 m': 'constraint'}, '末端',
        ['障碍物的位置、尺寸、距离信号、碰撞规则和评价器是什么？']),
    'catch': fixture('catch_and_hold', {'软臂捕获质量 0.05 kg 的下落小球': 'behavior',
        '捕获后保持 2 s': 'behavior', '不能让球反弹或掉落': 'constraint'}, '下落小球',
        ['小球初始状态、接触和捕获定义、保持判据及观测信号是什么？'],
        [dict(first='r0', relation='then', second='r1', quote='捕获后保持 2 s')]),
    'disturbance': fixture('disturbance_stabilization', {'平台在 1 s 后开始扰动': 'environment',
        '扰动期间末端保持世界坐标位置': 'behavior', '持续 3 s，偏差不超过 0.005 m': 'acceptance'}, '末端',
        ['平台扰动波形、幅值、方向、初始目标和信号及评价器如何定义？'],
        [dict(first='r1', relation='during', second='r0', quote='扰动期间末端保持世界坐标位置')]),
}


class IntakeTests(unittest.TestCase):
    def parse(self, name='hold', proposal=None, **kwargs):
        text, original = CASES[name]
        return parse_response(text, json.dumps(proposal or original, ensure_ascii=False), **kwargs)

    def test_five_task_classes_and_plain_reach(self):
        for name, (text, proposal) in CASES.items():
            with self.subTest(name=name):
                result = self.parse(name)
                self.assertEqual(result.status, 'draft', result.error)
                draft = result.draft
                self.assertEqual(draft.user_text, text)
                self.assertEqual(draft.intent, proposal['intent'])
                self.assertEqual(draft.task_object, proposal['object_quote'])
                self.assertFalse(draft.executable)
                self.assertEqual(draft.status, 'needs_confirmation')
                self.assertEqual(draft.execution_support, 'not_assessed')
                self.assertEqual(draft.registered_task_families, ['task.reach'])
                self.assertTrue(draft.missing_definitions)
                self.assertEqual([r.value for r in draft.requirements if r.source == 'user_explicit'],
                                 [r['quote'] for r in proposal['requirements'] if r['source'] == 'user_explicit'])
                self.assertTrue(all(r.value is None for r in draft.requirements if r.source == 'undefined'))
                self.assertEqual([r.model_dump(exclude={'source'}) for r in draft.temporal_relations],
                                 proposal['temporal_relations'])
                TaskIntakeDraft.model_validate_json(draft.model_dump_json(), strict=True)

    def test_no_automatic_reach_substitution_or_environment_adoption(self):
        view = acceptance_view(read(ROOT/'tasks/reach_hold.json'))
        for name in ('tracking', 'obstacle', 'catch', 'disturbance'):
            draft = self.parse(name, context=view).draft
            self.assertEqual(draft.intent, CASES[name][1]['intent'])
            self.assertFalse(any(r.source == 'verified_configuration' for r in draft.requirements))
            self.assertFalse(draft.executable)

    def test_invalid_empty_truncated_strict_and_duplicate_json(self):
        for content in ('', ' ', 'null', '{}', '[]', '{', '{"intent":',
                        '```json\n{}\n```', '{"a":1,"a":2}'):
            with self.subTest(content=content):
                result = parse_response(CASES['hold'][0], content)
                self.assertEqual(result.status, 'parse_failed')
                self.assertIsNone(result.draft)
        for reason in ('length', 'content_filter', 'tool_calls', None):
            result = self.parse(finish_reason=reason)
            self.assertIsNone(result.draft)
            self.assertIn('INCOMPLETE', result.error)
        for field, value in (('intent', 1), ('object_quote', 10), ('requirements', 'bad'),
                             ('executable', True), ('temporal_relations', None)):
            proposal = deepcopy(CASES['hold'][1]); proposal[field] = value
            self.assertEqual(self.parse(proposal=proposal).status, 'parse_failed')

    def test_source_forgery_and_omissions_fail_closed(self):
        original = CASES['hold'][1]
        mutations = []
        p = deepcopy(original); p['requirements'][0]['quote'] = '容差 0.001 m'; mutations.append(p)
        p = deepcopy(original); p['requirements'].pop(2); mutations.append(p)
        p = deepcopy(original); p['requirements'][0]['value'] = 0.01; mutations.append(p)
        p = deepcopy(original); p['requirements'][0]['source'] = 'human_approved'; mutations.append(p)
        p = deepcopy(original); p['requirements'][0]['config_pointer'] = '/task'; mutations.append(p)
        p = deepcopy(original); p['requirements'][1]['id'] = 'r0'; mutations.append(p)
        p = deepcopy(original); p['temporal_relations'][0]['second'] = 'missing'; mutations.append(p)
        p = deepcopy(original); p['temporal_relations'][0]['quote'] = '保持之前到达'; mutations.append(p)
        p = deepcopy(original); p['requirements'].append(requirement('x', source='llm_candidate',
            question='是否保持 10 s？')); mutations.append(p)
        p = deepcopy(original); p['requirements'].append(requirement('x', source='verified_configuration',
            pointer='/task/evaluator/parameters/data/tolerance_m')); mutations.append(p)
        for proposal in mutations:
            with self.subTest(proposal=proposal):
                result = self.parse(proposal=proposal)
                self.assertEqual(result.status, 'parse_failed')
                self.assertIsNone(result.draft)

    def test_four_sources_and_deterministic_values(self):
        source = read(ROOT/'tasks/reach_hold.json')
        view = acceptance_view(source)
        p = deepcopy(CASES['hold'][1])
        pointer = '/task/evaluator/parameters/data/tolerance_m'
        p['requirements'] += [requirement('cfg', source='verified_configuration', pointer=pointer),
                             requirement('candidate', source='llm_candidate', question='是否需要区分到达与保持阶段？')]
        draft = self.parse(proposal=p, context=view).draft
        self.assertEqual({r.source for r in draft.requirements},
                         {'user_explicit', 'verified_configuration', 'llm_candidate', 'undefined'})
        self.assertEqual(draft.requirements[-2].value, 0.01)
        self.assertEqual(draft.requirements[-2].source_identity, digest(source))
        self.assertIsNone(draft.requirements[-1].value)
        # The model cannot supply or override a numerical value at all.
        p['requirements'][-2]['value'] = 0.5
        self.assertEqual(self.parse(proposal=p, context=view).status, 'parse_failed')
        del p['requirements'][-2]['value']
        p['requirements'][-2]['config_pointer'] = '/policy/model'
        self.assertEqual(self.parse(proposal=p, context=view).status, 'parse_failed')

    def test_reach_free_source_bundle_and_task_only(self):
        source = read(ROOT/'tasks/reach_hold.json'); before = deepcopy(source)
        view = acceptance_view(source, source_label='tasks/reach_hold.json')
        self.assertEqual(source, before)
        facts = view.facts
        self.assertEqual(facts['/task/environment/data/environment/environment_id'], 'reach_free')
        self.assertEqual(facts['/task/evaluator/parameters/data/tolerance_m'], 0.01)
        self.assertEqual([facts['/settling/'+key] for key in
                          ('window_s', 'position_limit_m', 'speed_limit_m_s')], [0.05, 0.01, 0.02])
        self.assertAlmostEqual(view.holding_interval_s[0], 0.30)
        self.assertEqual(view.holding_interval_s[1], 0.35)
        task_only = acceptance_view(source['task'])
        self.assertIsNone(task_only.holding_interval_s)
        self.assertFalse(any('settling' in p for p in task_only.facts))
        self.assertTrue(any('undefined' in t for t in task_only.limitations))
        for settling in ({}, {'window_s': 0.05}, {**source['settling'], 'window_s': 0.5},
                         {**source['settling'], 'window_s': 0.055}, {**source['settling'], 'speed_limit_m_s': '0.02'}):
            bad = deepcopy(source); bad['settling'] = settling
            with self.assertRaises(ValueError): acceptance_view(bad)

    def test_frozen_snapshot_matches_existing_adapter_and_analysis(self):
        # Existing resolver only constructs this test fixture; intake never uses it.
        from tools.research.config import resolve
        from tools.research_tasks import task_adapter
        from tools.research.task_constraints import describe_analysis_requirements
        cfg = resolve(ROOT/'configs/research/study.json')['configuration']
        before = deepcopy(cfg)
        adapter = task_adapter(cfg)
        requirements = describe_analysis_requirements(cfg, {})
        with patch('tools.research.config.resolve', side_effect=AssertionError('mutable study read')):
            view = acceptance_view(SessionInput.model_validate(cfg))
        self.assertEqual(cfg, before)
        self.assertEqual(view.adapter_limits, adapter.ranking_limits())
        self.assertEqual(view.holding_interval_s, [adapter.holding_start_s(), 0.35])
        self.assertEqual(view.facts[SETTLING+'window_s'], 0.05)
        self.assertEqual([c.radius for c in requirements.constraints], [0.01, 0.01, 0.02])
        self.assertEqual(requirements.constraints[1].indices, list(range(30, 36)))
        self.assertEqual(describe_analysis_requirements(cfg, {}).model_dump(), requirements.model_dump())
        self.assertFalse(any('/model' in p or '/budget' in p for p in view.facts))
        cfg['policy']['controller']['parameters']['data']['settling']['position_limit_m'] = 0.007
        changed = acceptance_view(cfg)
        self.assertEqual(changed.adapter_limits['holding_max_error_m'], 0.007)
        self.assertEqual(changed.adapter_limits['terminal_error_m'], 0.01)
        self.assertNotEqual(changed.source_identity, view.source_identity)

    def test_provider_default_off_and_single_mocked_json_request(self):
        import openai
        with patch.object(openai, 'OpenAI', side_effect=AssertionError('provider must stay off')):
            self.assertEqual(request_draft('任务').error, 'PROVIDER_DISABLED_USE_OFFLINE_FIXTURE')
        text, proposal = CASES['catch']
        message = SimpleNamespace(content=json.dumps(proposal), tool_calls=None, refusal=None)
        response = SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason='stop')])
        client = Mock(); client.chat.completions.create.return_value = response
        with patch.object(openai, 'OpenAI') as factory:
            factory.return_value.__enter__.return_value = client
            result = request_draft(text, enable_provider=True, model='offline-mock')
            self.assertEqual(result.status, 'draft', result.error)
            client.chat.completions.create.assert_called_once()
            self.assertEqual(factory.call_args.kwargs['max_retries'], 0)
            kwargs = client.chat.completions.create.call_args.kwargs
            self.assertEqual(kwargs['response_format'], {'type': 'json_object'})
            self.assertNotIn('tools', kwargs)
            self.assertEqual(len(kwargs['messages']), 2)
            response.choices[0].finish_reason = 'length'
            self.assertEqual(request_draft(text, enable_provider=True, model='offline-mock').status, 'parse_failed')
        self.assertIn('Never downgrade', request_messages(text)[0]['content'])

    def test_provider_mocked_failure_paths_never_retry(self):
        import openai
        text, proposal = CASES['reach']
        client = Mock()
        with patch.object(openai, 'OpenAI') as factory:
            factory.return_value.__enter__.return_value = client
            for content, reason, refusal, calls in (('', 'stop', None, None),
                    (json.dumps(proposal), 'stop', 'refused', None),
                    ('{}', 'stop', None, ['unexpected']), ('{', 'stop', None, None)):
                client.reset_mock()
                message = SimpleNamespace(content=content, refusal=refusal, tool_calls=calls)
                client.chat.completions.create.return_value = SimpleNamespace(
                    choices=[SimpleNamespace(message=message, finish_reason=reason)])
                result = request_draft(text, enable_provider=True, model='offline-mock')
                self.assertEqual(result.status, 'parse_failed')
                self.assertIsNone(result.draft)
                client.chat.completions.create.assert_called_once()
            client.reset_mock()
            client.chat.completions.create.side_effect = openai.OpenAIError('synthetic secret must not leak')
            result = request_draft(text, enable_provider=True, model='offline-mock')
            self.assertEqual(result.error, 'PROVIDER_ERROR: OpenAIError')
            client.chat.completions.create.assert_called_once()

    def test_cli_utf8_direct_input_and_failure_exit(self):
        # Normal workspace ACL, no Windows TemporaryDirectory 0700 permissions.
        folder = ROOT/'runs'/('intake-fixture-' + uuid4().hex); folder.mkdir(parents=True)
        files = [folder/'task.txt', folder/'response.json']
        try:
            text, proposal = CASES['catch']
            files[0].write_text(text, encoding='utf-8')
            files[1].write_text(json.dumps(proposal, ensure_ascii=False), encoding='utf-8')
            process = subprocess.run([sys.executable, '-m', 'tools.task_intake', '--file', str(files[0]),
                '--response-file', str(files[1]), '--context', 'tasks/reach_hold.json'],
                cwd=ROOT, capture_output=True, encoding='utf-8', env={**__import__('os').environ, 'PYTHONIOENCODING': 'utf-8'})
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(json.loads(process.stdout)['draft']['intent'], 'catch_and_hold')
            for input_args in (['--text', text], ['--file', str(files[0])]):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = main(input_args + ['--response-file', str(files[1])])
                self.assertEqual(code, 0)
                self.assertEqual(json.loads(output.getvalue())['draft']['intent'], 'catch_and_hold')
            for args in (['--text', text], ['--text', text, '--response-file', str(files[1]), '--finish-reason', 'length']):
                output = io.StringIO()
                with redirect_stdout(output): code = main(args)
                self.assertEqual(code, 2)
                self.assertIsNone(json.loads(output.getvalue())['draft'])
        finally:
            for path in files: path.unlink(missing_ok=True)
            folder.rmdir()


if __name__ == '__main__':
    unittest.main()
