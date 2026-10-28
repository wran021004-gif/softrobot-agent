import { once } from 'node:events';
import { resolve, join } from 'node:path';
import { homedir } from 'node:os';
import { createChatGPT } from '@siwc/local';
import { createDPAPIEncryption, secureDirectory } from './security.mjs';
import { loadLocalKey } from './state.mjs';
import { createGateway, requirePlan } from './server.mjs';
import { publicError, GatewayError as ChatGPTError } from './errors.mjs';
import { streamResponse } from './inference.mjs';
import { acquireRuntimeLock } from './runtime.mjs';

const directory = process.env.SIWC_STATE_DIR ? resolve(process.env.SIWC_STATE_DIR)
  : join(process.env.LOCALAPPDATA ?? join(homedir(), 'AppData', 'Local'), 'LocalResearchChatGPTGateway');
const [command = 'status', ...args] = process.argv.slice(2);
const value = flag => { const i = args.indexOf(flag); return i >= 0 ? args[i + 1] : undefined; };

async function main() {
  const allowed = {
    login: ['--new', '--consent', '--profile', '--label'], logout: [], status: [], profiles: [],
    select: [], key: [], serve: [], smoke: ['--model'],
  };
  if (!Object.hasOwn(allowed, command)) throw new ChatGPTError('invalid_command', 'Use login, logout, status, profiles, select, key, serve or smoke.');
  for (let i = 0; i < args.length; i++) {
    if (command === 'select' && i === 0 && args.length === 1) continue;
    if (!allowed[command].includes(args[i])) throw new ChatGPTError('invalid_command', 'Unknown command option.');
    if (['--profile', '--label', '--model'].includes(args[i]) && (!args[++i] || args[i].startsWith('--'))) {
      throw new ChatGPTError('invalid_command', 'Missing option value.');
    }
  }
  if (command === 'smoke' && !value('--model')) {
    throw new ChatGPTError('model_required', 'Use smoke --model with an explicit active-account catalog model. No inference sent.');
  }
  await secureDirectory(directory);
  const encryption = createDPAPIEncryption();
  if (!await encryption.isAvailable()) throw new ChatGPTError('protected_storage_unavailable', 'Windows DPAPI is required. This version has no Linux storage adapter.');
  if (command === 'key') {
    // Reading an existing local key neither changes OAuth state nor races token refresh.
    process.stdout.write(await loadLocalKey(directory, encryption, { readOnly: true }));
    return;
  }
  // A single runtime owns this installation. Login/profile changes require stopping the server.
  let release;
  try {
    release = await acquireRuntimeLock(directory, () => { console.error('Gateway runtime lock was lost. Stop and restart this installation.'); process.exit(1); });
  } catch {
    throw new ChatGPTError('runtime_busy', 'Another gateway command owns this installation. Stop the running server before login, logout or selecting a profile.');
  }
  try {
    const client = createChatGPT({
      appName: 'Local Research ChatGPT Gateway', appId: 'local-research-chatgpt-gateway',
      inference: streamResponse, redirectPort: 0, storageDir: directory, credentialEncryption: encryption, sendHostId: true,
    });
    const apiKey = await loadLocalKey(directory, encryption);
    if (command === 'login') {
      console.log('Continue with ChatGPT：请在系统浏览器选择账号和工作区，批准 ChatGPT plan usage。等待最长 10 分钟。');
      const cancel = () => client.cancelSignIn();
      process.once('SIGINT', cancel);
      try {
        const session = await client.signIn({ newProfile: args.includes('--new'), reconsent: args.includes('--consent'), profileId: value('--profile'), label: value('--label') });
        console.log(JSON.stringify(session, null, 2));
        console.log(session.sharing ? '身份与计划使用权限已验证；尚未执行真实推理。' : '身份已验证，但未获得 ChatGPT plan usage；不能推理。请运行 npm run login -- --consent。');
      } finally { process.removeListener('SIGINT', cancel); }
    } else if (command === 'logout') {
      await client.disconnect(); console.log('已退出；保留账号注册映射和本机 host ID，便于重新连接。');
    } else if (command === 'profiles') {
      console.log(JSON.stringify(await client.listProfiles(), null, 2));
    } else if (command === 'select') {
      if (args.length !== 1) throw new ChatGPTError('invalid_command', 'Use npm run select -- PROFILE_ID.');
      console.log(JSON.stringify(await client.selectProfile(args[0]), null, 2));
    } else if (command === 'status') {
      console.log(JSON.stringify(await client.getSession(), null, 2));
    } else if (command === 'smoke') {
      // Start a temporary authenticated local server and send exactly ONE inference HTTP request.
      // No retries, no fallback billing, and no inference on login/catalog-only failures.
      await requirePlan(client);
      const server = createGateway({ client, apiKey });
      server.listen(0, '127.0.0.1'); await once(server, 'listening');
      try {
        const base = `http://127.0.0.1:${server.address().port}`;
        const headers = { authorization: `Bearer ${apiKey}`, 'content-type': 'application/json' };
        const catalog = await fetch(`${base}/v1/models`, { headers });
        if (!catalog.ok) throw new ChatGPTError('smoke_catalog_failed', 'Model discovery failed. No inference sent.', false, catalog.status);
        const models = (await catalog.json()).data;
        const model = value('--model');
        if (!model || !models.some(item => item.id === model)) throw new ChatGPTError('model_not_found', 'Select a model returned by the active account. No inference sent.');
        console.log(`身份和 plan usage 已验证；模型发现成功；选择 ${model}。将只发送一次“请只回答 OK”。`);
        const response = await fetch(`${base}/v1/chat/completions`, {
          method: 'POST', headers, signal: AbortSignal.timeout(195_000),
          body: JSON.stringify({ model, reasoning_effort: 'none', messages: [{ role: 'user', content: 'Reply only OK.' }], stream: false }),
        });
        const body = await response.json();
        if (!response.ok) {
          console.error(JSON.stringify(body)); process.exitCode = 1; return;
        }
        const answer = body.choices?.[0]?.message?.content;
        if (!answer?.trim()) throw new ChatGPTError('smoke_empty', 'Local HTTP returned no answer.');
        console.log(JSON.stringify({ verified: true, model, upstream_completed: true, local_http_status: response.status, answer }, null, 2));
      } finally { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); }
    } else if (command === 'serve') {
      const port = Number(process.env.SIWC_PORT ?? 8787);
      if (!Number.isInteger(port) || port < 1 || port > 65535) throw new ChatGPTError('invalid_port', 'SIWC_PORT must be between 1 and 65535.');
      const server = createGateway({ client, apiKey });
      server.listen(port, '127.0.0.1'); await once(server, 'listening');
      console.log(`Local ChatGPT Gateway: http://127.0.0.1:${port} (Bearer 认证；Ctrl+C 停止)`);
      await new Promise(resolve => {
        const stop = () => { server.closeAllConnections(); server.close(resolve); };
        process.once('SIGINT', stop); process.once('SIGTERM', stop);
      });
    }
  } finally { await release(); }
}

main().catch(error => {
  console.error(JSON.stringify(publicError(error).body));
  process.exitCode = 1;
});
