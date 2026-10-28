import { randomBytes, randomUUID } from 'node:crypto';
import { lstat, open, readFile, rename, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { GatewayError as ChatGPTError } from './errors.mjs';

// Caller holds the application lifetime lock, including while creating the key.
export async function loadLocalKey(directory, encryption, { readOnly = false } = {}) {
  if (!await encryption.isAvailable()) throw new ChatGPTError('protected_storage_unavailable', 'OS protected storage is required.');
  const filename = join(directory, 'local-api-key.json');
  try {
    const info = await lstat(filename);
    if (!info.isFile() || info.isSymbolicLink() || info.size > 16384) throw new Error('Invalid file');
    const record = JSON.parse(await readFile(filename, 'utf8'));
    if (record.version !== 1 || record.provider !== encryption.id || typeof record.ciphertext !== 'string') throw new Error('Invalid envelope');
    const key = await encryption.decrypt(Buffer.from(record.ciphertext, 'base64'));
    if (!/^[A-Za-z0-9_-]{43}$/.test(key)) throw new Error('Invalid secret');
    return key;
  } catch (error) {
    if (error.code !== 'ENOENT') throw new ChatGPTError('local_key_unreadable', 'The protected local API secret could not be read. Existing data was preserved.');
  }
  if (readOnly) throw new ChatGPTError('local_key_missing', 'Run npm run status or npm run login once to initialize protected local storage.');
  const key = randomBytes(32).toString('base64url');
  const record = { version: 1, provider: encryption.id, ciphertext: Buffer.from(await encryption.encrypt(key)).toString('base64') };
  const temporary = join(directory, `.local-key-${randomUUID()}.tmp`);
  try {
    const file = await open(temporary, 'wx', 0o600);
    try { await file.writeFile(JSON.stringify(record)); await file.sync(); } finally { await file.close(); }
    await rename(temporary, filename);
  } finally { await rm(temporary, { force: true }); }
  return key;
}
