import { createServer } from 'node:http';
import { createHash, randomUUID, timingSafeEqual } from 'node:crypto';
import { ChatGPTError } from '@siwc/local';
import { convertRequest } from './request.mjs';
import { publicError, GatewayError } from './errors.mjs';

const fail = (status, code, message) => { throw new GatewayError(code, message, false, status); };
const digest = value => createHash('sha256').update(value).digest();

export async function requirePlan(client) {
  const session = await client.getSession();
  if (session.error && session.status !== 'connected') {
    const e = session.error;
    throw new ChatGPTError(e.code, e.message, e.retryable, e.status);
  }
  if (session.status !== 'connected') fail(401, 'sign_in_required', 'Run npm run login in a separate terminal after stopping the gateway.');
  if (!session.sharing) fail(403, 'sharing_not_enabled', 'Signed in without ChatGPT plan usage. Stop the gateway and run npm run login -- --consent.');
}

async function readJSON(request) {
  if (request.headers['content-type']?.split(';', 1)[0].trim().toLowerCase() !== 'application/json') {
    fail(415, 'invalid_content_type', 'Use Content-Type: application/json.');
  }
  const chunks = [];
  let bytes = 0;
  for await (const chunk of request.iterator({ destroyOnReturn: false })) {
    bytes += chunk.length;
    if (bytes > 1024 * 1024) fail(413, 'request_too_large', 'Request body exceeds 1 MiB.');
    chunks.push(chunk);
  }
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); }
  catch { fail(400, 'invalid_json', 'Request body must be valid JSON.'); }
}

export function createGateway({ client, apiKey }) {
  if (typeof apiKey !== 'string' || apiKey.length < 32) throw new Error('A strong local API secret is required.');
  const expected = digest(`Bearer ${apiKey}`);
  let active = 0;
  const server = createServer(async (request, response) => {
    const send = (status, body) => {
      if (response.destroyed) return;
      response.writeHead(status, {
        'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store',
        'X-Content-Type-Options': 'nosniff', 'Content-Security-Policy': "default-src 'none'; frame-ancestors 'none'",
      });
      response.end(JSON.stringify(body));
    };
    let admitted = false;
    const controller = new AbortController();
    const cancel = () => { if (!response.writableEnded) controller.abort(); };
    response.once('close', cancel);
    const signal = AbortSignal.any([controller.signal, AbortSignal.timeout(190_000)]);
    try {
      const host = `127.0.0.1:${server.address().port}`;
      if (request.headers.host !== host || request.headers.origin !== undefined ||
          ['cross-site', 'same-site'].includes(request.headers['sec-fetch-site'])) {
        fail(403, 'local_requests_only', 'Use a local HTTP client with the gateway secret. Browser origins are not accepted.');
      }
      if (!timingSafeEqual(expected, digest(request.headers.authorization ?? ''))) fail(401, 'invalid_local_key', 'A valid local Bearer secret is required.');
      if (active >= 4) fail(429, 'local_busy', 'The local gateway is busy. Retry later.');
      active++; admitted = true;
      const path = request.url;
      if (request.method === 'GET' && path === '/health') {
        const state = await client.getSession();
        send(200, { status: 'ok', account_status: state.status, plan_usage: state.sharing });
      } else if (request.method === 'GET' && path === '/v1/models') {
        await requirePlan(client);
        const models = await client.listModels({ signal });
        send(200, { object: 'list', data: models.map(model => ({ id: model.slug, object: 'model', owned_by: 'openai', display_name: model.displayName })) });
      } else if (request.method === 'POST' && path === '/v1/chat/completions') {
        const options = convertRequest(await readJSON(request));
        await requirePlan(client);
        const models = await client.listModels({ signal });
        if (!models.some(model => model.slug === options.model)) fail(400, 'model_not_found', 'Choose a model returned by GET /v1/models for the active ChatGPT account.');
        // DevKit resolves only after response.completed, never after just a text delta.
        const result = await client.streamResponse({ ...options, signal });
        if (!result.text?.trim() && !result.tool_calls?.length) fail(502, 'empty_response', 'The completed response contained no text.');
        send(200, {
          id: `chatcmpl-local-${randomUUID()}`, object: 'chat.completion', created: Math.floor(Date.now() / 1000),
          ...(result.usage ? {usage:result.usage} : {}), model: options.model, choices: [{ index: 0, message: { role: 'assistant', content: result.text || null, ...(result.tool_calls?.length ? {tool_calls:result.tool_calls} : {}), ...(result.provider_output ? {provider_output:result.provider_output} : {}) }, finish_reason: result.tool_calls?.length ? 'tool_calls' : 'stop' }],
        });
      } else fail(404, 'not_found', 'Unknown route or HTTP method.');
    } catch (error) {
      const result = publicError(error);
      send(result.status, result.body);
      // Drain rejected request bodies without retaining them or logging contents.
      request.resume();
    } finally {
      if (admitted) active--;
      response.removeListener('close', cancel);
    }
  });
  server.requestTimeout = 30_000;
  server.headersTimeout = 10_000;
  server.keepAliveTimeout = 5_000;
  server.maxHeadersCount = 50;
  return server;
}
