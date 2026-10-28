import assert from 'node:assert/strict';
import test from 'node:test';
import { convertRequest } from '../src/request.mjs';

test('moves leading system guidance to instructions and preserves ordered text history', () => {
  assert.deepEqual(convertRequest({ model: 'account-model', messages: [
    { role: 'system', content: '简明回答' }, { role: 'system', content: '用中文' },
    { role: 'developer', content: 'Research assistant' }, { role: 'user', content: '一' },
    { role: 'assistant', content: '二' }, { role: 'user', content: '三' },
  ], stream: false }), { model: 'account-model', instructions: '简明回答\n\n用中文', input: [
    { role: 'developer', content: 'Research assistant' }, { role: 'user', content: '一' },
    { role: 'assistant', content: '二' }, { role: 'user', content: '三' },
  ] });
});

for (const field of ['temperature', 'top_p', 'max_output_tokens', 'max_tokens', 'conversation',
  'previous_response_id', 'store', 'n', 'metadata', 'response_format']) {
  test(`rejects unsupported ${field}`, () => assert.throws(() => convertRequest({
    model: 'm', messages: [{ role: 'user', content: 'hi' }], [field]: 1,
  }), { code: 'unsupported_parameter' }));
}

for (const body of [null, [], {}, { model: 'm', messages: [] },
  { model: 'm', messages: [{ role: 'tool', content: 'hi' }] },
    { model: 'm', messages: [{ role: 'user', content: 'hi', name: 'x' }] },
  { model: 'm', messages: [{ role: 'system', content: 'only system' }] },
  { model: 'm', messages: [{ role: 'user', content: 'hi' }, { role: 'system', content: 'late' }] },
  { model: 'm', messages: [{ role: 'user', content: 'hi' }], stream: true }]) {
  test(`rejects invalid request ${JSON.stringify(body)}`, () => assert.throws(() => convertRequest(body)));
}
