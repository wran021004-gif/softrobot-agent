import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import test from 'node:test';
import { diagnoseStoredState } from '../scripts/diagnose-state.mjs';

test('offline diagnostics never expose account, registration or token values', () => {
  const encoded = value => `fixture.${Buffer.from(JSON.stringify(value)).toString('base64url')}.fixture`;
  const state={activeProfileId:'private-profile',profiles:[{id:'private-profile',status:'connected',
    clientId:'private-client',subject:'private-subject',identity:{email:'private@example.invalid'},
    profileIdToken:encoded({sub:'private-subject',aud:'private-client',iss:'https://auth.openai.com'}),
    credentials:{accessToken:encoded({client_id:'private-client'}),expiresAt:Date.now()+10000},
    scopes:['chatgpt.tokens.use.direct']}]};
  const result=diagnoseStoredState(state,{id:'urn:uuid:00000000-0000-4000-8000-000000000000'});
  assert.equal(result.id_token_subject_matches_profile,true);
  assert.equal(result.access_client_matches_registration,true);
  assert.equal(result.network_requests,0);
  assert.equal(result.signature_reverified,false);
  assert.equal(JSON.stringify(result).includes('private-'),false);
  assert.equal(JSON.stringify(result).includes('private@'),false);
});

test('Node native proxy routes through CONNECT and keeps loopback direct without external requests', {timeout:15000}, async t => {
  const direct=createServer((req,res)=>res.end('direct'));
  let tunnels=0;
  const proxy=createServer();
  proxy.on('connect',(req,socket)=>{
    tunnels++;assert.equal(req.url,'p5-offline.invalid:80');
    socket.write('HTTP/1.1 200 Connection Established\r\n\r\n');
    socket.once('data',()=>socket.end('HTTP/1.1 200 OK\r\nContent-Length: 7\r\nConnection: close\r\n\r\nproxied'));
  });
  await Promise.all([new Promise(r=>direct.listen(0,'127.0.0.1',r)),new Promise(r=>proxy.listen(0,'127.0.0.1',r))]);
  t.after(()=>{direct.closeAllConnections();proxy.closeAllConnections();direct.close();proxy.close();});
  const url=`http://127.0.0.1:${proxy.address().port}`;
  const code=`const a=await fetch('http://p5-offline.invalid/'); const b=await fetch('http://127.0.0.1:${direct.address().port}/'); process.stdout.write((await a.text())+','+(await b.text()));`;
  const {stdout}=await promisify(execFile)(process.execPath,['--use-env-proxy','--input-type=module','-e',code],{
    env:{...process.env,HTTP_PROXY:url,HTTPS_PROXY:url,NO_PROXY:'localhost,127.0.0.1,::1'},windowsHide:true,timeout:10000});
  assert.equal(stdout,'proxied,direct');assert.equal(tunnels,1);
});
