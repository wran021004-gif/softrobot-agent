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


def payload_for(book):
    config = book.state['request']['design_session']
    messages = [{'role': 'system', 'content': (book.root / 'inputs/system_prompt.md').read_text(encoding='utf-8')},
                {'role': 'user', 'content': '开始一次有预算限制的机器人设计任务，使用本次真实计算反馈修改设计。'}]
    for row in book.state['model_calls']:
        if row.get('status') != 'completed':
            continue
        messages.append(row['message'])
        feedback = json.dumps(row['feedback'], ensure_ascii=False)
        calls = row['message'].get('tool_calls', [])
        if calls:
            messages.extend({'role': 'tool', 'tool_call_id': c['id'], 'content': feedback} for c in calls)
        else:
            messages.append({'role': 'user', 'content': feedback})
    messages.append({'role': 'user', 'content': '最新权威上下文与状态：\n' + json.dumps(book.context(), ensure_ascii=False)})
    return dict(model=config['model'], messages=messages, tools=native_tools(), tool_choice='required',
                thinking={'type': config['thinking']}, temperature=config['temperature'], max_tokens=config['max_tokens'], stream=False)


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
    row.update(status='completed', feedback=dict(decision=decision, result=compact_result(result) if result else None,
                                                result_ref=ref, remaining=book.remaining()))
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
        key = os.environ.get('DEEPSEEK_API_KEY', '')
        if not key:
            state.update(status='WAITING_FOR_KEY', stop_reason='填写 DEEPSEEK_API_KEY 后 resume；未发送模型请求、未消耗模型预算')
            book.save()
            break
        payload = payload_for(book)
        if len(json.dumps(payload, ensure_ascii=False).encode('utf-8')) > config['max_input_bytes']:
            return stop(book, 'MODEL_INPUT_BUDGET_EXHAUSTED; evidence remains saved')
        folder = book.root / 'model_calls' / f'{len(state["model_calls"]):03d}'
        folder.mkdir(parents=True)
        atomic_json(folder / 'request.json', redact(payload, key))
        book.register(folder / 'request.json')
        row = dict(index=len(state['model_calls']), status='reserved', folder=folder.relative_to(book.root).as_posix(),
                   decision_sequence=len(state['decisions']), model=config['model'],
                   transport='injected_test' if transport else 'official_deepseek')
        state['model_calls'].append(row)
        state.update(status='MODEL_CALL', stop_reason=None)
        book.save()  # Persist charge before any HTTP I/O; no SDK hidden retries.
        try:
            response = redact(send(config, payload, key), key)
            choice = response['choices'][0]
            message = choice['message']
            saved = dict(message={k: message[k] for k in ('role', 'content', 'tool_calls') if k in message},
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
