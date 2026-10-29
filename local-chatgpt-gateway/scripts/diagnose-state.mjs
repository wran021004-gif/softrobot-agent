// Offline and read-only: decode protected state in memory, emit booleans only.
// Never create a client, refresh a token, acquire a mutating SDK store or log IDs.
import { readFile, readdir } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { homedir } from 'node:os';
import { pathToFileURL } from 'node:url';
import { createDPAPIEncryption } from '../src/security.mjs';

const claims = token => {
  try { return JSON.parse(Buffer.from(token.split('.')[1], 'base64url').toString('utf8')); }
  catch { return {}; }
};

export function diagnoseStoredState(saved, host) {
  const profile = saved.profiles?.find(p => p.id === saved.activeProfileId);
  const identity = claims(profile?.profileIdToken ?? '');
  const access = claims(profile?.credentials?.accessToken ?? '');
  const audiences = Array.isArray(identity.aud) ? identity.aud : [identity.aud];
  const tokenClient = access.client_id ?? access.azp;
  return {
    active_profile_found: !!profile, stored_status_connected: profile?.status === 'connected',
    required_scopes: Object.fromEntries(['openid', 'profile', 'email', 'offline_access', 'resource.invoke', 'chatgpt.tokens.use.direct']
      .map(scope => [scope, !!profile?.scopes?.includes(scope)])),
    issued_client_saved: !!profile?.clientId && profile.clientId !== 'dynamic_agent_client',
    id_token_subject_matches_profile: identity.sub ? identity.sub === profile?.subject : null,
    id_token_audience_matches_client: identity.aud ? audiences.includes(profile?.clientId) : null,
    id_token_issuer_expected: identity.iss ? identity.iss === 'https://auth.openai.com' : null,
    access_client_matches_registration: tokenClient ? tokenClient === profile?.clientId : null,
    access_token_present: !!profile?.credentials?.accessToken,
    pending_refresh_present: !!profile?.pendingRefresh,
    access_token_expired_now: profile?.credentials ? profile.credentials.expiresAt <= Date.now() : null,
    host_id_format_valid: /^urn:uuid:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(host?.id ?? ''),
    workspace_binding: 'not_independently_recorded_by_pinned_devkit',
    signature_reverified: false, network_requests: 0,
    limitation: 'Decoded claims are consistency checks, not fresh signature verification or upstream admission. No identity or token value is emitted.',
  };
}

async function main() {
  const directory = process.env.SIWC_STATE_DIR ? resolve(process.env.SIWC_STATE_DIR)
    : join(process.env.LOCALAPPDATA ?? join(homedir(), 'AppData', 'Local'), 'LocalResearchChatGPTGateway');
  const file = join(directory, 'chatgpt-auth.json');
  const before = await readFile(file); const envelope = JSON.parse(before);
  const encryption = createDPAPIEncryption();
  if (envelope.version !== 3 || envelope.provider !== encryption.id) throw Error('unsupported_protected_state');
  const saved = JSON.parse(await encryption.decrypt(Buffer.from(envelope.ciphertext, 'base64')));
  const host = JSON.parse(await readFile(join(directory, 'chatgpt-host.json'), 'utf8'));
  const result = diagnoseStoredState(saved, host);
  if (process.argv.includes('--audit-p4')) {
    const profile=saved.profiles.find(p=>p.id===saved.activeProfileId);
    const values=[profile?.subject,profile?.clientId,profile?.profileIdToken,profile?.credentials?.accessToken,
      profile?.credentials?.refreshToken,profile?.identity?.email,profile?.identity?.name,host.id]
      .filter(v=>typeof v==='string' && v.length>3);
    const folder=new URL('../../evidence/p4_provider_acceptance/',import.meta.url);
    let files=0,matches=0;
    for (const name of await readdir(folder)) {
      const body=await readFile(new URL(name,folder),'utf8');files++;
      if (values.some(value=>body.includes(value))) matches++;
      if (name.startsWith('request_')) {
        const wire=JSON.parse(body);
        if (Object.keys(wire).some(k=>!['model','messages','stream','tools','thinking','reasoning_effort','tool_choice'].includes(k))) {
          throw Error('unexpected_request_field');
        }
      }
    }
    result.p4_published_payload_audit={files_checked:files,files_matching_private_auth_values:matches,
      request_fields_contain_no_headers:true,
      limitation:'Exact saved private-value check plus request-field review; not a universal secret detector. No private value is output.'};
  }
  result.state_file_unchanged = before.equals(await readFile(file));
  process.stdout.write(JSON.stringify(result, null, 2));
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().catch(() => { console.error('Offline protected-state inspection failed; no private diagnostics emitted.'); process.exitCode = 1; });
}
