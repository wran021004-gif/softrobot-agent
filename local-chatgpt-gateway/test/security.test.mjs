import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { createDPAPIEncryption, secureDirectory } from '../src/security.mjs';
import { loadLocalKey } from '../src/state.mjs';

test('real Windows DPAPI round trip, tamper rejection and no plaintext at rest', { skip: process.platform !== 'win32' }, async t => {
  const directory = await mkdtemp(join(tmpdir(), 'gateway-dpapi-'));
  t.after(() => rm(directory, { recursive: true, force: true }));
  await secureDirectory(directory);
  const provider = createDPAPIEncryption();
  assert.equal(await provider.isAvailable(), true);
  const plain = 'synthetic-access-refresh-and-id-token';
  const encrypted = await provider.encrypt(plain);
  assert.equal(Buffer.from(encrypted).includes(Buffer.from(plain)), false);
  assert.equal(await provider.decrypt(encrypted), plain);
  const tampered = Buffer.from(encrypted); tampered[tampered.length - 1] ^= 1;
  await assert.rejects(provider.decrypt(tampered));
  const key = await loadLocalKey(directory, provider);
  assert.equal(await loadLocalKey(directory, provider), key);
  const filename = join(directory, 'local-api-key.json');
  assert.equal((await readFile(filename, 'utf8')).includes(key), false);
  await writeFile(filename, 'corrupted encrypted file');
  await assert.rejects(loadLocalKey(directory, provider));
  assert.equal(await readFile(filename, 'utf8'), 'corrupted encrypted file');
});

test('unavailable encryption refuses to create a local secret', async t => {
  const directory = await mkdtemp(join(tmpdir(), 'gateway-fail-closed-'));
  t.after(() => rm(directory, { recursive: true, force: true }));
  await assert.rejects(loadLocalKey(directory, { id: 'unavailable', isAvailable: () => false }));
});
