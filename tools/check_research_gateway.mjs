// Offline validation of an existing Gateway; no server, credentials or inference.
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { access } from 'node:fs/promises';

const root = resolve(process.argv[2] ?? 'local-chatgpt-gateway');
try {
  await access(join(root, 'src', 'cli.mjs'));
  const { convertRequest } = await import(pathToFileURL(join(root, 'src', 'request.mjs')).href);
  const request = {
    model: 'offline-contract-probe', stream: false, reasoning_effort: 'none',
    messages: [{ role: 'user', content: 'Offline contract fixture. Never send this request.' }],
    tools: [{ type: 'function', function: {
      name: 'offline_contract_probe', description: 'Offline fixture only.',
      parameters: { type: 'object', properties: {}, additionalProperties: false },
    } }],
  };
  const converted = convertRequest(request);
  if (converted.model !== request.model || converted.tools?.length !== 1
      || converted.reasoning?.effort !== 'none') {
    throw new Error('Converted tools/reasoning contract differs from research requirements.');
  }
  console.log(JSON.stringify({ status: 'ready', tools: true, reasoning: 'none', inference_requests: 0 }));
} catch (error) {
  console.error(JSON.stringify({ status: 'not_ready', reason: error.message, inference_requests: 0 }));
  process.exitCode = 1;
}
