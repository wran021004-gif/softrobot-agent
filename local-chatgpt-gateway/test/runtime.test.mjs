import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { acquireRuntimeLock } from '../src/runtime.mjs';
import { ConnectionStore } from '../.devkit/packages/local/dist/storage.js';

test('lifetime lock coexists with SDK lock and prevents a second runtime', async t => {
  const directory = await mkdtemp(join(tmpdir(), 'gateway-lock-'));
  t.after(() => rm(directory, { recursive: true, force: true }));
  const store = new ConnectionStore(directory, { id: 'test-only', isAvailable: () => true, encrypt() {}, decrypt() {} });
  const release = await acquireRuntimeLock(directory, () => assert.fail('Lock compromised'));
  try {
    await assert.rejects(acquireRuntimeLock(directory, () => {}), { code: 'ELOCKED' });
    assert.equal(await store.withLock(() => store.read()), undefined);
    await assert.rejects(acquireRuntimeLock(directory, () => {}), { code: 'ELOCKED' });
  } finally { await release(); }
  await (await acquireRuntimeLock(directory, () => {}))();
});
