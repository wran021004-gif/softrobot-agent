import assert from 'node:assert/strict';
import { execFile, spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdtemp, rm } from 'node:fs/promises';
import { createServer } from 'node:net';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import test from 'node:test';

const exec = promisify(execFile);
const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));

test('smoke requires an explicit model before touching account state', async () => {
  const result = await exec(process.execPath, [cli, 'smoke'], { windowsHide: true }).catch(error => error);
  assert.equal(result.code, 1);
  assert.equal(JSON.parse(result.stderr).error.code, 'model_required');
});

test('real Windows CLI initializes, serves authenticated health, reads key concurrently and blocks unsigned inference', { skip: process.platform !== 'win32', timeout: 40_000 }, async t => {
  const directory = await mkdtemp(join(tmpdir(), 'gateway-cli-test-'));
  t.after(() => rm(directory, { recursive: true, force: true }));
  const portProbe = createServer();
  portProbe.listen(0, '127.0.0.1'); await once(portProbe, 'listening');
  const port = portProbe.address().port; await new Promise(resolve => portProbe.close(resolve));
  const env = { ...process.env, SIWC_STATE_DIR: directory, SIWC_PORT: String(port) };
  const run = command => exec(process.execPath, [cli, command], { env, windowsHide: true, timeout: 15_000 });
  assert.equal(JSON.parse((await run('status')).stdout).status, 'disconnected');
  const server = spawn(process.execPath, [cli, 'serve'], { env, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  t.after(async () => { if (server.exitCode === null) { server.kill(); await once(server, 'close'); } });
  await new Promise((resolve, reject) => {
    let output = '';
    const timer = setTimeout(() => reject(new Error('Gateway did not start')), 15_000);
    server.once('error', error => { clearTimeout(timer); reject(error); });
    server.once('exit', () => { clearTimeout(timer); reject(new Error('Gateway exited before ready')); });
    server.stdout.on('data', chunk => { output += chunk.toString(); if (output.includes('Local ChatGPT Gateway:')) { clearTimeout(timer); resolve(); } });
    server.stderr.resume();
  });
  const key = (await run('key')).stdout;
  assert.match(key, /^[A-Za-z0-9_-]{43}$/);
  const headers = { authorization: `Bearer ${key}` };
  const health = await fetch(`http://127.0.0.1:${port}/health`, { headers });
  assert.equal(health.status, 200);
  assert.deepEqual(await health.json(), { status: 'ok', account_status: 'disconnected', plan_usage: false });
  const models = await fetch(`http://127.0.0.1:${port}/v1/models`, { headers });
  assert.equal(models.status, 401);
  const blocked = await run('status').catch(error => error);
  assert.equal(JSON.parse(blocked.stderr).error.code, 'runtime_busy');
});
