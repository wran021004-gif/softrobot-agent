// A separate local account instance; reuse the original CLI, OAuth and DPAPI.
import { spawnSync } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { homedir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const [command = 'status', ...extra] = process.argv.slice(2);
const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));
const directory = join(process.env.LOCALAPPDATA ?? join(homedir(), 'AppData', 'Local'), 'LocalResearchChatGPTGateway-Account2');
const credentialFile = join(homedir(), '.softrobot-agent', 'chatgpt-api-account2.json');
const baseURL = 'http://127.0.0.1:8788';
const env = { ...process.env, SIWC_STATE_DIR: directory, SIWC_PORT: '8788',
  HTTP_PROXY: 'http://127.0.0.1:7890', HTTPS_PROXY: 'http://127.0.0.1:7890', NO_PROXY: 'localhost,127.0.0.1,::1' };

function run(args, capture = false) {
  const result = spawnSync(process.execPath, ['--use-env-proxy', cli, ...args], {
    env, windowsHide: true, stdio: capture ? ['ignore', 'pipe', 'pipe'] : 'inherit', encoding: 'utf8',
  });
  if (result.error) throw new Error('Could not start the account2 Gateway CLI.');
  if (result.status !== 0) {
    if (capture) process.stderr.write(result.stderr ?? '');
    process.exit(result.status ?? 1);
  }
  return result.stdout;
}

async function exportCredentials() {
  const config = { base_url: baseURL, api_key: run(['key'], true) };
  await mkdir(dirname(credentialFile), { recursive: true });
  try {
    await writeFile(credentialFile, JSON.stringify(config, null, 2) + '\n', { flag: 'wx', mode: 0o600 });
  } catch (error) {
    if (error.code !== 'EEXIST') throw new Error('Could not create the separate account2 credential file.');
    let saved;
    try { saved = JSON.parse(await readFile(credentialFile, 'utf8')); }
    catch { throw new Error('Existing account2 credentials were preserved; inspect the file locally.'); }
    if (saved.base_url !== config.base_url || saved.api_key !== config.api_key) {
      throw new Error('Existing account2 credentials differ and were preserved; no overwrite performed.');
    }
  }
  console.log(`Account2 credential file: ${credentialFile}`);
}

async function main() {
  if (extra.length || !['setup', 'login', 'status', 'start'].includes(command)) {
    throw new Error('Use npm run account2 -- setup|login|status|start.');
  }
  if (command === 'setup') { run(['status']); await exportCredentials(); }
  else if (command === 'login') { run(['login', '--label', 'Account2']); await exportCredentials(); }
  else run([command === 'start' ? 'serve' : 'status']);
}

main().catch(error => { console.error(error.message); process.exitCode = 1; });
