import assert from 'node:assert/strict';
import { createHash, createCipheriv, createDecipheriv, randomBytes } from 'node:crypto';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { get } from 'node:http';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { exportJWK, generateKeyPair, SignJWT } from 'jose';
import { createChatGPT } from '@siwc/local';
import { ConnectionStore } from '../.devkit/packages/local/dist/storage.js';
import { createGateway } from '../src/server.mjs';

const issuer = 'https://auth.openai.com';
const clientId = 'oaiapp_mock_registration';
const { publicKey, privateKey } = await generateKeyPair('RS256');
const jwks = { keys: [{ ...await exportJWK(publicKey), kid: 'flow-test', alg: 'RS256', use: 'sig' }] };
const direct = 'openid profile email offline_access resource.invoke chatgpt.tokens.use.direct';
const localFetch = globalThis.fetch;

// In-memory random key for mocked OAuth tests only. Production uses Windows DPAPI.
function encryption() {
  const key = randomBytes(32);
  return { id: 'ephemeral-test-only', isAvailable: () => true,
    encrypt(text) { const iv = randomBytes(12); const c = createCipheriv('aes-256-gcm', key, iv); const data = Buffer.concat([c.update(text), c.final()]); return Buffer.concat([iv, c.getAuthTag(), data]); },
    decrypt(data) { const b = Buffer.from(data); const d = createDecipheriv('aes-256-gcm', key, b.subarray(0, 12)); d.setAuthTag(b.subarray(12, 28)); return Buffer.concat([d.update(b.subarray(28)), d.final()]).toString(); },
  };
}
const callback = url => new Promise((resolve, reject) => {
  const req = get(url, res => { res.resume(); res.once('end', () => resolve(res.statusCode)); }); req.once('error', reject);
});

async function fixture(t, { scope = direct, badNonce = false, invalidRefresh = false } = {}) {
  const directory = await mkdtemp(join(tmpdir(), 'gateway-oauth-mock-'));
  t.after(() => rm(directory, { recursive: true, force: true }));
  const provider = encryption();
  const store = new ConnectionStore(directory, provider);
  let authorization; let signIns = 0; let refreshes = 0; let inferences = 0; let revocations = 0;
  const hosts = [];
  t.mock.method(globalThis, 'fetch', async (url, init = {}) => {
    const address = String(url);
    if (address === `${issuer}/.well-known/openid-configuration`) return Response.json({ issuer, authorization_endpoint: `${issuer}/authorize`, token_endpoint: `${issuer}/api/accounts/oauth/token`, jwks_uri: `${issuer}/jwks`, revocation_endpoint: `${issuer}/revoke` });
    if (address === `${issuer}/jwks`) return Response.json(jwks);
    if (address === `${issuer}/api/accounts/oauth/token`) {
      assert.equal(init.body.get('client_id'), clientId);
      assert.equal(init.body.get('resource'), 'https://api.openai.com/v1');
      const refresh = init.body.get('grant_type') === 'refresh_token';
      if (refresh) {
        refreshes++;
        assert.equal(init.body.has('scope'), false);
        assert.equal(init.body.get('refresh_token'), 'synthetic-refresh');
        if (invalidRefresh) return Response.json({ error: 'invalid_grant' }, { status: 400 });
      } else {
        assert.equal(init.body.get('redirect_uri'), authorization.searchParams.get('redirect_uri'));
        assert.equal(createHash('sha256').update(init.body.get('code_verifier')).digest('base64url'), authorization.searchParams.get('code_challenge'));
      }
      const jwt = await new SignJWT({ nonce: badNonce ? 'wrong' : authorization.searchParams.get('nonce'), email: 'mock@example.invalid' })
        .setProtectedHeader({ alg: 'RS256', kid: 'flow-test' }).setIssuer(issuer).setAudience(clientId)
        .setSubject('mock-verified-subject').setIssuedAt().setExpirationTime('1h').sign(privateKey);
      return Response.json({ access_token: refresh ? 'synthetic-rotated-access' : 'synthetic-access',
        refresh_token: refresh ? 'synthetic-rotated-refresh' : 'synthetic-refresh', token_type: 'Bearer', expires_in: 3600, scope, id_token: jwt });
    }
    if (address === 'https://api.openai.com/v1/models') return Response.json({ models: [{ slug: 'mock-visible', display_name: 'Mock Model', visibility: 'list' }, { slug: 'hidden', visibility: 'hidden' }] });
    if (address === 'https://api.openai.com/v1/responses') {
      inferences++;
      assert.equal(new Headers(init.headers).get('authorization'), 'Bearer synthetic-access');
      assert.deepEqual(JSON.parse(init.body), { model: 'mock-visible', instructions: 'Use Chinese', input: [
        { role: 'user', content: 'hello' }, { role: 'assistant', content: 'hi' }, { role: 'user', content: '请只回答 OK' },
      ], store: false, stream: true });
      return new Response('data: {"type":"response.output_text.delta","delta":"OK"}\n\ndata: {"type":"response.completed","response":{"status":"completed"}}\n\n', { headers: { 'content-type': 'text/event-stream' } });
    }
    if (address === `${issuer}/revoke`) { revocations++; return new Response(null, { status: 200 }); }
    assert.fail('Unexpected network request in mocked OAuth test');
  });
  const client = createChatGPT({ appName: 'Gateway OAuth Test', appId: 'gateway-test', redirectPort: 0,
    storageDir: directory, credentialEncryption: provider, sendHostId: true,
    async openBrowser(url) {
      authorization = new URL(url); signIns++;
      hosts.push(authorization.searchParams.get('ext_agent_host_id'));
      assert.equal(authorization.searchParams.get('client_id'), signIns === 1 ? 'dynamic_agent_client' : clientId);
      assert.equal(authorization.searchParams.has('agent_name_hint'), signIns === 1);
      assert.equal(authorization.searchParams.get('code_challenge_method'), 'S256');
      assert.equal(authorization.searchParams.get('scope'), direct);
      const cb = new URL(authorization.searchParams.get('redirect_uri'));
      assert.equal(cb.hostname, '127.0.0.1'); assert.equal(cb.pathname, '/auth/callback');
      cb.searchParams.set('code', 'mock-code'); cb.searchParams.set('client_id', clientId);
      cb.searchParams.set('state', 'unrelated-state'); assert.equal(await callback(cb), 400);
      cb.searchParams.set('state', authorization.searchParams.get('state')); assert.equal(await callback(cb), 200);
    },
  });
  return { client, store, directory, hosts, counts: () => ({ refreshes, inferences, revocations }) };
}

test('dynamic OAuth → identity/scope checks → account catalog → mocked Responses completion → local HTTP', async t => {
  const f = await fixture(t);
  const session = await f.client.signIn(); assert.equal(session.sharing, true);
  const server = createGateway({ client: f.client, apiKey: 'mock-independent-local-secret-1234567890' });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => { server.closeAllConnections(); return new Promise(resolve => server.close(resolve)); });
  const response = await localFetch(`http://127.0.0.1:${server.address().port}/v1/chat/completions`, {
    method: 'POST', headers: { authorization: 'Bearer mock-independent-local-secret-1234567890', 'content-type': 'application/json' },
    body: JSON.stringify({ model: 'mock-visible', messages: [ { role: 'system', content: 'Use Chinese' },
      { role: 'user', content: 'hello' }, { role: 'assistant', content: 'hi' }, { role: 'user', content: '请只回答 OK' } ], stream: false }),
  });
  assert.equal(response.status, 200); assert.equal((await response.json()).choices[0].message.content, 'OK');
  assert.equal(f.counts().inferences, 1);
  const raw = await readFile(join(f.directory, 'chatgpt-auth.json'), 'utf8');
  for (const secret of ['synthetic-access', 'synthetic-refresh', 'mock@example.invalid', clientId]) assert.equal(raw.includes(secret), false);
  await f.client.disconnect(); assert.equal(f.counts().revocations, 1);
  await f.client.signIn();
  assert.match(f.hosts[0], /^urn:uuid:/); assert.equal(f.hosts[1], f.hosts[0]);
});

test('identity-only consent is saved but cannot list models or infer', async t => {
  const f = await fixture(t, { scope: 'openid profile email offline_access' });
  const session = await f.client.signIn();
  assert.equal(session.status, 'connected'); assert.equal(session.sharing, false);
  await assert.rejects(f.client.listModels(), { code: 'sharing_not_enabled' });
  assert.equal(f.counts().inferences, 0);
});

test('initial login rejects a signed ID token with wrong nonce', async t => {
  const f = await fixture(t, { badNonce: true });
  await assert.rejects(f.client.signIn(), { code: 'invalid_id_token' });
  assert.equal((await f.client.getSession()).status, 'disconnected');
});

for (const invalidRefresh of [false, true]) {
  test(`refresh serialization and invalidation: invalid_grant=${invalidRefresh}`, async t => {
    const f = await fixture(t, { invalidRefresh }); await f.client.signIn();
    await f.store.withLock(async () => {
      const state = await f.store.read(); state.profiles[0].credentials.expiresAt = Date.now() - 1000; await f.store.write(state);
    });
    if (invalidRefresh) {
      await assert.rejects(f.client.listModels(), { code: 'invalid_grant' });
      assert.equal((await f.client.getSession()).status, 'reauth_required');
    } else {
      await Promise.all([f.client.listModels(), f.client.listModels()]);
      const state = await f.store.withLock(() => f.store.read());
      assert.equal(state.profiles[0].credentials.refreshToken, 'synthetic-rotated-refresh');
    }
    assert.equal(f.counts().refreshes, 1); assert.equal(f.counts().inferences, 0);
  });
}
