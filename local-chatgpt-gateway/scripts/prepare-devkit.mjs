// Prepare an independently obtained pinned official DevKit checkout.
import {cp,readFile,writeFile,access} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {createHash} from 'node:crypto';
const source=resolve(process.argv[2] ?? '');
const target=new URL('../.devkit/',import.meta.url);
const expected={"packages/local/src/index.ts": "c232e8cbb8761b151e073d4f57f8373b321b1397afd4a58f454e23268c9b5bd4", "packages/local/src/types.ts": "158b1af7ee4bf9adf4ed8564c17d7b17201c56d334a684da1d8a0fb344ce2b7d"};
for (const [file,hash] of Object.entries(expected)) {
  const bytes=await readFile(join(source,file));
  if (createHash('sha256').update(bytes).digest('hex')!==hash) throw Error('Pinned DevKit source mismatch: '+file);
}
try {await access(target);throw Error('Existing .devkit preserved. Choose a fresh checkout/worktree.');}
catch(e) {if(e.code!=='ENOENT') throw e;}
for (const file of ['packages/local','scripts/copy-package-notices.mjs','tsconfig.base.json','LICENSE','THIRD_PARTY_NOTICES.md','docs/dependency-inventory.json']) {
  await cp(join(source,file),new URL(file,target),{recursive:true,filter:p=>!/[\\/](node_modules|dist)([\\/]|$)/.test(p)});
}
const index=new URL('packages/local/src/index.ts',target);
await writeFile(index,(await readFile(index,'utf8')).replace('=> streamResponse(accessToken, options, signal)','=> (config.inference ?? streamResponse)(accessToken, options, signal)'));
const types=new URL('packages/local/src/types.ts',target);
await writeFile(types,(await readFile(types,'utf8')).replace('export interface ChatGPTConfig {','export interface ChatGPTConfig {\n  inference?: (accessToken: string, options: StreamResponseOptions, signal: AbortSignal) => Promise<{text: string}>;'));
