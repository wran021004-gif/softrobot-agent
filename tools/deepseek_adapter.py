"""Single-model official Chat Completions tool loop; credentials never enter artifacts."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler
from schemas.workbench import Decision
from tools.state_io import atomic_json, read
from tools.workbench_catalog import TOOLS, DESIGN_TOOLS
from tools.design_session import compact_result


def redact(value, key):
    if isinstance(value, str):
        return value.replace(key, '[REDACTED]') if key else value
    if isinstance(value, list):
        return [redact(v, key) for v in value]
    if isinstance(value, dict):
        return {k: redact(v, key) for k, v in value.items()}
    return value


def native_tools():
    tools = []
    for name in [*DESIGN_TOOLS, 'read_evidence', 'stop_design', 'capability_missing']:
        info = TOOLS.get(name)
        schema = info['schema'].model_json_schema() if info else {'type': 'object', 'properties': {}, 'required': []}
        schema['properties'].update(reason={'type': 'string', 'description': '简要依据；引用真实观测，不输出长推理'},
                                    evidence={'type': 'array', 'items': {'type': 'string'}, 'minItems': 1})
        schema['required'] = schema.get('required', []) + ['reason', 'evidence']
        schema['additionalProperties'] = False
        description = (info['purpose'] + '；成本：' + json.dumps(info['cost']) + '；前置检查：' + str(info['requires'])) if info else '引用证据结束本次设计，说明停止或能力不足的原因'
        tools.append(dict(type='function', function=dict(name=name, description=description, parameters=schema)))
    return tools


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('DEEPSEEK_REDIRECT_REFUSED')


def request_completion(config, payload, key):
    url = config['base_url'].rstrip('/') + '/chat/completions'
    request = Request(url, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                      headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    try:
        with build_opener(NoRedirect).open(request, timeout=config['timeout_s']) as response:
            return json.loads(response.read().decode('utf-8'))
    except HTTPError as exc:
        # Do not persist server bodies, request headers or credential-bearing objects.
        raise RuntimeError(f'DEEPSEEK_HTTP_{exc.code}') from None
    except URLError:
        raise RuntimeError('DEEPSEEK_NETWORK_ERROR') from None


def encoded_size(value):
    return len(json.dumps(value, ensure_ascii=False).encode('utf-8'))


def input_metrics(payload):
    parts = dict(system=0, context=0, assistant=0, tool_feedback=0, reasoning=0,
                 tools=encoded_size(payload['tools']))
    for message in payload['messages']:
        key = {'system': 'system', 'user': 'context', 'assistant': 'assistant', 'tool': 'tool_feedback'}[message['role']]
        parts[key] += encoded_size(message)
        if 'reasoning_content' in message:
            parts['reasoning'] += encoded_size(message['reasoning_content'])
    context_parts = {}
    for message in payload['messages']:
        if message['role'] == 'user' and message['content'].startswith('最新权威上下文与状态：\n'):
            context_parts = {k: encoded_size(v) for k, v in json.loads(message['content'].split('\n', 1)[1]).items()}
    return dict(total_bytes=encoded_size(payload), components=parts, context_sections=context_parts,
                note='UTF-8 请求 JSON；reasoning 是 assistant 的子项，不能再次相加')


def payload_for(book, *, fresh=False):
    config = book.state['request']['design_session']
    state = book.state
    start = state.get('context_start', 0)
    active = [r for r in state['model_calls'][start:] if r.get('status') == 'completed']
    if fresh or len(active) >= config.get('context_turns', 2):
        # Start a NEW conversation from saved facts, never trim reasoning inside
        # a replayed assistant/tool exchange. Completed records remain immutable.
        start = len(state['model_calls'])
        active = []
    state['context_start'] = start
    messages = [{'role': 'system', 'content': (book.root / 'inputs/system_prompt.md').read_text(encoding='utf-8')},
                {'role': 'user', 'content': '继续有限设计任务；本会话片段以最新保存状态为事实依据。'}]
    for row in active:
        messages.append(row['message'])
        feedback = json.dumps(row['feedback'], ensure_ascii=False)
        calls = row['message'].get('tool_calls', [])
        if calls:
            messages.extend({'role': 'tool', 'tool_call_id': c['id'], 'content': feedback} for c in calls)
        else:
            messages.append({'role': 'user', 'content': feedback})
    context = book.context()
    if not active:
        last = next((r for r in reversed(state['model_calls']) if r.get('status') == 'completed'), None)
        if last:
            context['latest_feedback'] = compact_feedback(last['feedback'])
    messages.append({'role': 'user', 'content': '最新权威上下文与状态：\n' + json.dumps(context, ensure_ascii=False)})
    payload = dict(model=config['model'], messages=messages, tools=native_tools(), tool_choice='required',
                   thinking={'type': config['thinking']}, max_tokens=config['max_tokens'], stream=False)
    if config['thinking'] == 'disabled':
        payload['temperature'] = config['temperature']
    return payload


def compact_feedback(feedback):
    decision = feedback['decision']
    return dict(decision={k: decision[k] for k in ('sequence', 'status', 'failure_code') if k in decision},
                result=compact_result(feedback['result']) if feedback.get('result') else None,
                result_ref=feedback.get('result_ref'), cite_as=feedback.get('cite_as'))


def parse_decision(row):
    calls = row['message'].get('tool_calls', [])
    try:
        if row.get('finish_reason') == 'length':
            raise ValueError('MODEL_OUTPUT_TRUNCATED')
        if len(calls) != 1:
            raise ValueError('ONE_TOOL_PER_DECISION_REQUIRED')
        call = calls[0]['function']
        args = json.loads(call['arguments'])
        reason, evidence = args.pop('reason'), args.pop('evidence')
        if call['name'] in ('stop_design', 'capability_missing'):
            return Decision(action='stop' if call['name'] == 'stop_design' else 'capability_missing',
                            arguments=args, reason=reason, evidence=evidence)
        return Decision(action='continue', tool=call['name'], arguments=args, reason=reason, evidence=evidence)
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        return dict(action='continue', tool='INVALID_MODEL_OUTPUT', arguments={}, evidence=['request'], reason=str(exc))


def apply_response(book, row):
    # The proposed sequence is persisted before dispatch. A crash after submit
    # can therefore attach feedback without executing the same decision twice.
    sequence = row['decision_sequence']
    if len(book.state['decisions']) == sequence:
        book.submit(parse_decision(row))
    decision = book.state['decisions'][sequence]
    attempt = next((a for a in book.state['attempts'] if a['decision'] == sequence), None)
    ref = attempt.get('result_ref') if attempt else decision.get('result_ref')
    result = read(book.root / ref) if ref else None
    feedback = dict(decision=decision, result=result, result_ref=ref,
                    cite_as=book.state['evidence'].get(ref, {}).get('evaluation_id') or ref)
    row.update(status='completed', feedback=compact_feedback(feedback))
    atomic_json(book.root / row['folder'] / 'feedback.json', row['feedback'])
    book.register(book.root / row['folder'] / 'feedback.json')
    book.save()


def stop(book, reason):
    book.state.update(status='STOPPED', stop_reason=reason)
    book.save()
    return book.state


def run_model(book, *, steps=None, transport=None):
    state = book.state
    config = state['request']['design_session']
    send = transport or request_completion
    count = 0
    for row in state['model_calls']:
        if row['status'] == 'reserved':
            path = book.root / row['folder'] / 'response.json'
            if path.exists():
                absorb_response(book, row, read(path))
            else:
                row.update(status='failed', error='MODEL_CALL_INTERRUPTED; reservation remains charged')
                book.save()
    while state['status'] not in ('STOPPED', 'CAPABILITY_MISSING'):
        if steps is not None and count >= steps:
            state['status'] = 'PAUSED'
            book.save()
            break
        pending = next((m for m in state['model_calls'] if m['status'] == 'responded'), None)
        if pending:
            apply_response(book, pending)
            count += 1
            continue
        failures = sum(m['status'] == 'failed' for m in state['model_calls'])
        if failures > config['model_failure_retries']:
            return stop(book, 'MODEL_FAILURE_RETRY_EXHAUSTED')
        if book.remaining()['model_calls'] <= 0 or book.remaining()['decisions'] <= 0:
            return stop(book, 'MODEL_OR_DECISION_BUDGET_EXHAUSTED')
        payload = payload_for(book)
        if encoded_size(payload) > config['max_input_bytes']:
            payload = payload_for(book, fresh=True)
        state['last_input_metrics'] = input_metrics(payload)
        if encoded_size(payload) > config['max_input_bytes']:
            atomic_json(book.root / 'blocked_request.json', payload)
            book.register(book.root / 'blocked_request.json')
            return stop(book, 'MODEL_INPUT_BUDGET_EXHAUSTED; evidence remains saved')
        key = os.environ.get('DEEPSEEK_API_KEY', '')
        if not key:
            state.update(status='WAITING_FOR_KEY', stop_reason='填写 DEEPSEEK_API_KEY 后 resume；未发送模型请求、未消耗模型预算')
            book.save()
            break
        folder = book.root / 'model_calls' / f'{len(state["model_calls"]):03d}'
        folder.mkdir(parents=True)
        atomic_json(folder / 'request.json', redact(payload, key))
        book.register(folder / 'request.json')
        row = dict(index=len(state['model_calls']), status='reserved', folder=folder.relative_to(book.root).as_posix(),
                   decision_sequence=len(state['decisions']), model=config['model'],
                   context_start=state['context_start'], input_metrics=state['last_input_metrics'],
                   transport='injected_test' if transport else 'official_deepseek')
        state['model_calls'].append(row)
        state.update(status='MODEL_CALL', stop_reason=None)
        book.save()  # Persist charge before any HTTP I/O; no SDK hidden retries.
        try:
            response = redact(send(config, payload, key), key)
            choice = response['choices'][0]
            message = choice['message']
            saved = dict(message={k: message[k] for k in ('role', 'content', 'reasoning_content', 'tool_calls') if k in message},
                         finish_reason=choice.get('finish_reason'), usage=response.get('usage', {}),
                         response_model=response.get('model'))
            atomic_json(folder / 'response.json', saved)
            book.register(folder / 'response.json')
            absorb_response(book, row, saved)
        except KeyboardInterrupt:
            row.update(status='failed', error='MODEL_CALL_INTERRUPTED')
            state['status'] = 'WAITING_MODEL_RETRY'
            book.save()
            raise
        except Exception as exc:
            row.update(status='failed', error=redact(str(exc), key))
            state.update(status='WAITING_MODEL_RETRY', stop_reason=row['error'])
            if failures >= config['model_failure_retries']:
                state.update(status='STOPPED', stop_reason='MODEL_FAILURE_RETRY_EXHAUSTED: ' + row['error'])
            book.save()
            break  # Resume explicitly uses the remaining retry, never a hidden loop.
    return state


def absorb_response(book, row, saved):
    book.register(book.root / row['folder'] / 'response.json')
    row.update(status='responded', **saved)
    book.save()
