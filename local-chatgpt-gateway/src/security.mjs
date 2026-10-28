import { spawn } from 'node:child_process';
import { mkdir, lstat } from 'node:fs/promises';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { GatewayError as ChatGPTError } from './errors.mjs';

const script = fileURLToPath(new URL('../scripts/dpapi.ps1', import.meta.url));
const unavailable = () => new ChatGPTError('protected_storage_unavailable', 'Windows DPAPI protected storage is unavailable. No plaintext fallback is allowed.');

function invoke(action, input) {
  if (process.platform !== 'win32') return Promise.reject(unavailable());
  return new Promise((resolve, reject) => {
    const executable = join(process.env.SystemRoot ?? 'C:\\Windows', 'System32/WindowsPowerShell/v1.0/powershell.exe');
    const child = spawn(executable, ['-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', script, '-Action', action], {
      windowsHide: true, shell: false, stdio: ['pipe', 'pipe', 'pipe'],
    });
    const chunks = []; let bytes = 0; let settled = false;
    const finish = (error, value) => {
      if (settled) return;
      settled = true; clearTimeout(timer);
      if (error) reject(unavailable()); else resolve(value);
    };
    const timer = setTimeout(() => { child.kill(); finish(true); }, 15_000);
    child.on('error', () => finish(true));
    child.stdin.on('error', () => finish(true));
    child.stderr.resume();
    child.stdout.on('data', chunk => {
      bytes += chunk.length;
      if (bytes > 4 * 1024 * 1024) { child.kill(); finish(true); } else chunks.push(chunk);
    });
    child.on('close', code => finish(code !== 0, Buffer.concat(chunks).toString('ascii').trim()));
    child.stdin.end(input);
  });
}

export function createDPAPIEncryption() {
  let availability;
  const provider = {
    id: 'windows-dpapi-current-user-v1',
    async isAvailable() {
      availability ??= (async () => {
        try { const encrypted = await provider.encrypt('gateway-storage-check'); return await provider.decrypt(encrypted) === 'gateway-storage-check'; }
        catch { return false; }
      })();
      const available = await availability;
      if (!available) availability = undefined;
      return available;
    },
    async encrypt(plaintext) {
      return Buffer.from(await invoke('encrypt', Buffer.from(plaintext, 'utf8').toString('base64')), 'base64');
    },
    async decrypt(ciphertext) {
      return Buffer.from(await invoke('decrypt', Buffer.from(ciphertext).toString('base64')), 'base64').toString('utf8');
    },
  };
  return provider;
}

export async function secureDirectory(directory) {
  await mkdir(directory, { recursive: true, mode: 0o700 });
  const info = await lstat(directory);
  if (!info.isDirectory() || info.isSymbolicLink()) throw unavailable();
  await invoke('prepare', directory);
}
