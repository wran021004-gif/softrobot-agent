import assert from 'node:assert/strict';
import test from 'node:test';
import { request as httpRequest } from 'node:http';
import { ChatGPTError } from '@siwc/local';
import { createGateway } from '../src/server.mjs';
import { streamResponse } from '../src/inference.mjs';

const key = 'test-local-access-secret-1234567890';
const chat = { model: 'actual-model', messages: [{ role: 'user', content: '请只回答 OK' }], stream: false };

test('HTTP to Responses tool call, original reasoning and result continuation',async t=>{
  const upstream=[];
  const f=await fixture(t,{streamResponse:options=>streamResponse('synthetic-token',options,options.signal,()=>({responses:{create:async body=>{
    upstream.push(body);
    const output=upstream.length===1 ? [{type:'reasoning',summary:[],encrypted_content:'opaque-fixture'},
      {type:'function_call',namespace:'research',name:'read',call_id:'exact-call',arguments:'{}',status:'completed'}]
      : [{type:'message',role:'assistant',content:[{type:'output_text',text:'Feedback consumed.'}]}];
    return (async function*(){
      if(upstream.length===1)for(const [output_index,item] of output.entries())yield {type:'response.output_item.done',output_index,item};
      yield {type:'response.completed',response:{status:'completed',output:upstream.length===1 ? [] : output}};
    })();
  }}}))});
  const request={model:'actual-model',reasoning_effort:'medium',tools:[{type:'function',function:{name:'read',parameters:{type:'object',properties:{}}}}],
    messages:[{role:'user',content:'Read the evidence.'}]};
  const first=await (await f.post(request)).json();
  assert.equal(first.choices[0].finish_reason,'tool_calls');assert.equal(first.choices[0].message.tool_calls[0].id,'exact-call');
  assert.equal(first.gateway_completion.output_source,'completed_item_events');
  const second=await (await f.post({...request,messages:[...request.messages,first.choices[0].message,
    {role:'tool',tool_call_id:'exact-call',content:'Exact evidence fixture.'}]})).json();
  assert.equal(second.choices[0].message.content,'Feedback consumed.');
  assert.equal(upstream[1].input[1].encrypted_content,'opaque-fixture');
  assert.equal(upstream[1].input.at(-1).call_id,'exact-call');assert.equal(second.usage,undefined);
});
async function fixture(t, overrides = {}) {
  let calls = 0;
  const client = {
    getSession: async () => ({ status: 'connected', sharing: true }),
    listModels: async () => [{ slug: 'actual-model', displayName: 'Actual' }],
    streamResponse: async (options) => { calls++; assert.deepEqual(options.input, [{ role: 'user', content: '请只回答 OK' }]); return { text: 'OK' }; },
    ...overrides,
  };
  const server = createGateway({ client, apiKey: key });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => { server.closeAllConnections(); return new Promise(resolve => server.close(resolve)); });
  const base = `http://127.0.0.1:${server.address().port}`;
  const request = (path, init = {}) => fetch(base + path, {
    ...init, headers: { authorization: `Bearer ${key}`, 'content-type': 'application/json', ...init.headers },
  });
  const post = (body = chat, headers) => request('/v1/chat/completions', { method: 'POST', body: JSON.stringify(body), headers });
  const hostileHost = () => new Promise((resolve, reject) => {
    const req = httpRequest(`${base}/health`, { headers: { host: 'evil.invalid', authorization: `Bearer ${key}` } }, res => {
      res.resume(); res.on('end', () => resolve(res.statusCode));
    });
    req.on('error', reject); req.end();
  });
  return { request, post, hostileHost, calls: () => calls };
}

test('authenticated HTTP health, catalog and nonstream completion', async t => {
  const f = await fixture(t);
  const health = await (await f.request('/health')).json();
  assert.deepEqual(health, { status: 'ok', account_status: 'connected', plan_usage: true });
  assert.equal((await (await f.request('/v1/models')).json()).data[0].id, 'actual-model');
  const res = await f.post();
  assert.equal(res.status, 200);
  assert.equal(res.headers.get('access-control-allow-origin'), null);
  assert.equal((await res.json()).choices[0].message.content, 'OK');
  assert.equal(f.calls(), 1);
});

test('catalog upstream admission error preserves safe diagnostics and never starts inference', async t => {
  const f=await fixture(t,{listModels:async()=>{throw new ChatGPTError('subscription_sharing_route_not_supported',
    'Sanitized SDK diagnostic',false,403,{requestId:'req_p5_fixture',param:'model',responseShape:'{error:{code:string}}'});}});
  const response=await f.request('/v1/models');const body=await response.json();
  assert.equal(response.status,403);assert.equal(body.error.upstream_status,403);
  assert.equal(body.error.code,'subscription_sharing_route_not_supported');
  assert.equal(body.error.requestId,'req_p5_fixture');assert.equal(body.error.param,'model');
  assert.equal(f.calls(),0);
});

test('rejects absent auth, foreign Origin, hostile Host and unsupported request without inference', async t => {
  const f = await fixture(t);
  assert.equal((await f.request('/health', { headers: { authorization: '' } })).status, 401);
  assert.equal((await f.post(chat, { origin: 'https://evil.invalid' })).status, 403);
  assert.equal(await f.hostileHost(), 403);
  const unsupported = await f.post({ ...chat, temperature: 0 });
  assert.equal(unsupported.status, 400);
  assert.equal((await unsupported.json()).error.upstream_status, undefined);
  assert.equal((await f.post({ ...chat, model: 'invented-model' })).status, 400);
  assert.equal((await f.request('/v1/chat/completions', { method: 'POST', body: '{' })).status, 400);
  assert.equal((await f.post(chat, { 'content-type': 'text/plain' })).status, 415);
  assert.equal((await f.post({ ...chat, messages: [{ role: 'user', content: 'x'.repeat(1024 * 1024) }] })).status, 413);
  assert.equal(f.calls(), 0);
});

for (const session of [{ status: 'connected', sharing: false }, { status: 'reauth_required', sharing: false }]) {
  test(`requires authorized plan usage for ${session.status}/${session.sharing}`, async t => {
    const f = await fixture(t, { getSession: async () => session });
    assert.equal((await f.post()).status, session.status === 'connected' ? 403 : 401);
    assert.equal(f.calls(), 0);
  });
}

for (const [code, upstream, expected] of [
  ['subscription_sharing_usage_limit_exceeded', 200, 429],
  ['subscription_sharing_usage_unavailable', 200, 503], ['subscription_sharing_user_not_eligible', 403, 403],
  ['subscription_sharing_invalid_user', 200, 401], ['chatpass_v2_scope_not_authorized', 200, 403],
  ['api_error', 401, 401], ['api_error', 503, 503], ['stream_interrupted', undefined, 502],
  ['response_incomplete', undefined, 502], ['invalid_grant', 400, 400],
]) {
  test(`maps ${code}/${upstream} without reporting a partial success`, async t => {
    const f = await fixture(t, { streamResponse: async () => { throw new ChatGPTError(code, 'Sanitized SDK diagnostic', false, upstream); } });
    const res = await f.post(); const body = await res.json();
    assert.equal(res.status, expected); assert.equal(body.error.code, code);
    assert.equal(body.error.upstream_status, upstream); assert.equal(body.choices, undefined);
  });
}

test('unknown exception cannot leak secrets and empty completed text is rejected', async t => {
  const f = await fixture(t, { streamResponse: async () => { throw new Error('access-token-sensitive'); } });
  const res = await f.post(); assert.equal(res.status, 500);
  assert.equal((await res.text()).includes('access-token-sensitive'), false);
  const empty = await fixture(t, { streamResponse: async () => ({ text: '' }) });
  assert.equal((await empty.post()).status, 502);
});
