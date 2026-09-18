"""Real DeepSeek response replay; no network, backend execution or integration."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4

from examples.platform_route import main, prepare
from extensions.tendon_family.route import create, view
from schemas.platform import ModelResponse
from tools.platform_host import Host
from tools.platform_models import DeepSeekAdapter, provider_name
from tools.platform_store import Store, encode
from tools.state_io import read


FIXTURE = read(Path(__file__).parent / 'fixtures/deepseek_route_two_calls.json')


def reply(count):
    response = deepcopy(FIXTURE['response'])
    message = response['raw']['choices'][0]['message']
    message['tool_calls'] = message['tool_calls'][:count]
    if count == 0:
        response['raw']['choices'][0]['finish_reason'] = 'stop'
    return ModelResponse.model_validate(response)


class Replay(DeepSeekAdapter):
    def __init__(self, host, responses):
        self.host, self.responses, self.payloads, self.turns = host, list(responses), [], []

    def respond(self, payload, turn):
        # A repair is still a live route when actually submitted to the adapter.
        assert self.host.store.session(self.host.run_id)['state']['route']['final'] is None
        self.payloads.append(deepcopy(payload))
        self.turns.append(turn)
        return self.responses.pop(0)


class Crash(BaseException):
    pass


class RouteModelProtocol(unittest.TestCase):
    def setup_route(self, *, turns=2, calls=10, project_calls=10):
        root = Path('runs/route_protocol_checks') / uuid4().hex
        prepare(root)
        host = Host(root, 'family-route')
        project = read(root / 'inputs/project.json')
        project['budget']['model_calls'] = project_calls
        host.store.create(project)
        inp = read(root / 'inputs/route.json')
        inp['policy']['model']['max_turns'] = turns
        inp['policy']['budget']['model_calls'] = calls
        create(root, inp)
        return root, host

    def test_count_correction_success_and_actual_payload(self):
        raw = FIXTURE['response']['raw']
        self.assertEqual(hashlib.sha256(encode(FIXTURE['response']).encode('utf8')).hexdigest(),
                         FIXTURE['source_response']['artifact_id'])
        self.assertEqual(raw['choices'][0]['finish_reason'], 'tool_calls')
        self.assertEqual([c['function']['name'] for c in raw['choices'][0]['message']['tool_calls']],
                         [provider_name('route.inspect'), provider_name('evidence.read')])
        for count in (0, 2):
            with self.subTest(count=count):
                _, host = self.setup_route()
                adapter = Replay(host, [reply(count), reply(1)])
                session = host.run(adapter)
                self.assertEqual(adapter.turns, [0, 1])
                self.assertEqual(session['status'], 'stopped')
                self.assertEqual(session['state']['stop_reason'], 'MODEL_TURN_LIMIT')
                self.assertNotIn('protocol_correction', session['state'])
                payload = adapter.payloads[1]
                self.assertIn('Call exactly one tool', payload['messages'][0]['content'])
                self.assertIn('action="finish"', payload['messages'][0]['content'])
                correction = json.loads(payload['messages'][-1]['content'])['protocol_correction']
                self.assertEqual(correction['tool_call_count'], count)
                self.assertIn(f'contained {count} tool calls', correction['requirement'])
                self.assertEqual(host.store.artifact(correction['response']), reply(count).model_dump(mode='json'))
                self.assertEqual(payload['thinking'], {'type': 'enabled'})
                self.assertEqual(set(payload), {'model', 'messages', 'tools', 'max_tokens', 'stream', 'thinking'})
                delivered = [e for e in host.store.events(host.run_id) if e['kind'] == 'context_delivery']
                self.assertEqual([e['request_id'] for e in delivered], ['model-0', 'model-1'])
                self.assertEqual(host.store.artifact(delivered[1]['inputs'][0]), payload)
                self.assertIsNone(host.store.lookup(host.run_id, 'model-0-tool'))
                self.assertEqual(host.store.lookup(host.run_id, 'model-1-tool')['status'], 'completed')
                used = host.store.remaining()['used']
                self.assertEqual((used['model_calls'], used['tool_calls'], used['backend_solves']), (2, 1, 0))

    def test_second_failure_seals_and_resume_returns_nonzero(self):
        for response in (reply(0), reply(2), ModelResponse(raw={'invalid': 'response'})):
            with self.subTest(response=response.raw):
                root, host = self.setup_route(turns=4)
                adapter = Replay(host, [reply(2), response])
                session = host.run(adapter)
                self.assertEqual(session['status'], 'failed')
                self.assertIn('MODEL_PROTOCOL_CORRECTION_FAILED', session['state']['stop_reason'])
                self.assertEqual(view(host)['route']['final']['stop_reason'], session['state']['stop_reason'])
                self.assertEqual(host.store.remaining()['used']['model_calls'], 2)
                self.assertEqual(host.store.remaining()['used']['tool_calls'], 0)
                before = host.store.events(host.run_id)
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(['resume', str(root)]), 1)
                self.assertEqual(host.store.events(host.run_id), before)

    def test_correction_respects_turn_session_and_project_budgets(self):
        for limits in (dict(turns=1), dict(calls=1), dict(project_calls=1)):
            with self.subTest(limits=limits):
                _, host = self.setup_route(**limits)
                adapter = Replay(host, [reply(2)])
                session = host.run(adapter)
                self.assertEqual(adapter.turns, [0])
                self.assertEqual(session['status'], 'failed')
                self.assertIn('MODEL_PROTOCOL_CORRECTION_BUDGET_EXHAUSTED', session['state']['stop_reason'])
                self.assertIsNotNone(session['state']['route']['final'])
                self.assertEqual(host.store.remaining()['used']['model_calls'], 1)

    def test_recovery_after_receipt_and_correction_state_commits(self):
        import tools.platform_models as models
        for checkpoint in ('invalid_receipt', 'correction_state', 'corrected_receipt', 'tool_receipt'):
            with self.subTest(checkpoint=checkpoint):
                root, host = self.setup_route()
                adapter = Replay(host, [reply(2), reply(1)])
                original_complete, original_failure, original_invoke = Store.complete, models._model_failure, Host.invoke

                def complete(store, row, receipt, *args, **kwargs):
                    result = original_complete(store, row, receipt, *args, **kwargs)
                    target = 'model-0' if checkpoint == 'invalid_receipt' else 'model-1'
                    if row['request_id'] == target:
                        raise Crash()
                    return result

                def failure(h, receipt):
                    result = original_failure(h, receipt)
                    raise Crash()

                def invoke(h, request, **kwargs):
                    result = original_invoke(h, request, **kwargs)
                    raise Crash()

                if checkpoint == 'correction_state':
                    hook = patch.object(models, '_model_failure', failure)
                elif checkpoint == 'tool_receipt':
                    hook = patch.object(Host, 'invoke', invoke)
                else:
                    hook = patch.object(Store, 'complete', complete)
                with hook, self.assertRaises(Crash):
                    host.run(adapter)
                self.assertIsNone(view(host)['route']['final'])
                Host(root, host.run_id).run(adapter)
                self.assertEqual(adapter.turns, [0, 1])
                self.assertEqual(host.store.remaining()['used']['model_calls'], 2)
                self.assertEqual(host.store.remaining()['used']['tool_calls'], 1)
                self.assertEqual(len([e for e in host.store.events(host.run_id)
                                     if e['kind'] == 'model_protocol_correction']), 1)

    def test_unknown_correction_request_is_not_resent(self):
        root, host = self.setup_route()
        adapter = Replay(host, [reply(2), reply(1)])
        original = adapter.respond

        def interrupt(payload, turn):
            if turn == 1:
                raise Crash()
            return original(payload, turn)

        with patch.object(adapter, 'respond', interrupt), self.assertRaises(Crash):
            host.run(adapter)
        Host(root, host.run_id).run(adapter)
        session = host.store.session(host.run_id)
        self.assertEqual(adapter.turns, [0])
        self.assertEqual(session['status'], 'needs_input')
        self.assertIn('MODEL_REQUEST_UNKNOWN', session['state']['stop_reason'])
        self.assertIsNone(view(host)['route']['final'])
        self.assertEqual(host.store.remaining()['used']['model_calls'], 2)

    def test_cli_start_failure_and_task_tolerance_are_separate(self):
        root = Path('runs/route_protocol_checks') / uuid4().hex
        prepare(root)
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'offline-test-only'}), \
                patch.object(DeepSeekAdapter, 'respond', side_effect=[reply(2), reply(0)]), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(main(['start', str(root)]), 1)
        # A sealed, normally stopped delivery may report an unmet robot tolerance.
        host = Host(root, 'family-route')
        with host.store.transaction() as db:
            state = host.store.session(host.run_id, db)['state']
            state['route']['final']['task_success'] = False
            state['route']['final']['delivery_status'] = 'evaluated'
            state['route']['final']['stop_reason'] = state['stop_reason'] = 'offline delivery'
            host.store.update_state(db, host.run_id, state, 'stopped')
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(['resume', str(root)]), 0)
        self.assertFalse(view(host)['route']['final']['task_success'])


if __name__ == '__main__':
    unittest.main()
