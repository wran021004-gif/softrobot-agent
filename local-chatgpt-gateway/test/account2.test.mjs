import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import test from 'node:test';

const exec = promisify(execFile);
const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));
const launcher = fileURLToPath(new URL('../scripts/account2.mjs', import.meta.url));

test('account2 isolates state and key despite inherited old settings; preserves credential files',
  { skip: process.platform !== 'win32', timeout: 60_000 }, async t => {
    const root = await mkdtemp(join(tmpdir(), 'gateway-account2-'));
    t.after(() => rm(root, { recursive: true, force: true }));
    const oldDirectory = join(root, 'old-state');
    const env = { ...process.env, USERPROFILE: root, LOCALAPPDATA: root,
      SIWC_STATE_DIR: oldDirectory, SIWC_PORT: '8787' };
    const run = (path, args) => exec(process.execPath, [path, ...args], { env, windowsHide: true, timeout: 20_000 });
    await run(cli, ['status']);
    const oldEnvelope = await readFile(join(oldDirectory, 'local-api-key.json'));
    const oldKey = (await run(cli, ['key'])).stdout;
    const credentials = join(root, '.softrobot-agent');
    await mkdir(credentials);
    const originalFile = join(credentials, 'chatgpt-api.json');
    const original = JSON.stringify({ base_url: 'http://127.0.0.1:8787', api_key: oldKey });
    await writeFile(originalFile, original);

    await run(launcher, ['setup']);
    const secondFile = join(credentials, 'chatgpt-api-account2.json');
    const secondText = await readFile(secondFile, 'utf8');
    const second = JSON.parse(secondText);
    assert.equal(second.base_url, 'http://127.0.0.1:8788');
    assert.match(second.api_key, /^[A-Za-z0-9_-]{43}$/);
    assert.notEqual(second.api_key, oldKey);
    const newEnv = { ...env, SIWC_STATE_DIR: join(root, 'LocalResearchChatGPTGateway-Account2') };
    const newKey = (await exec(process.execPath, [cli, 'key'], { env: newEnv, windowsHide: true })).stdout;
    assert.equal(second.api_key, newKey);
    assert.equal(await readFile(originalFile, 'utf8'), original);
    assert.deepEqual(await readFile(join(oldDirectory, 'local-api-key.json')), oldEnvelope);
    await run(launcher, ['setup']);
    assert.equal(await readFile(secondFile, 'utf8'), secondText);

    await writeFile(secondFile, '{"keep":"user-owned"}');
    const failed = await run(launcher, ['setup']).catch(error => error);
    assert.equal(failed.code, 1);
    assert.equal(await readFile(secondFile, 'utf8'), '{"keep":"user-owned"}');
    assert.equal(await readFile(originalFile, 'utf8'), original);
    assert.deepEqual(await readFile(join(oldDirectory, 'local-api-key.json')), oldEnvelope);
  });
