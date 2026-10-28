import assert from 'node:assert/strict';
import test from 'node:test';
import {convertRequest} from '../src/request.mjs';
import {streamResponse,completedResponse} from '../src/inference.mjs';

const call={type:'function_call',call_id:'call-1',name:'research_plan',namespace:'research',arguments:'{"action":"generate"}',status:'completed'};
const tools=[{type:'function',function:{name:'research_plan',description:'Submit a Plan.',parameters:{type:'object',properties:{action:{type:'string'}}}}}];
test('catalog model identifiers preserve punctuation without slug guessing',()=>{
  assert.equal(convertRequest({model:'synthetic-model.1',messages:[{role:'user',content:'Hi.'}]}).model,'synthetic-model.1');
});

test('namespace tools, structured text, call IDs and results remain exact',()=>{
  const body=convertRequest({model:'account-model',reasoning_effort:'medium',tools,messages:[
    {role:'system',content:'English research instructions.'},
    {role:'user',content:[{type:'text',text:'Choose an action.'}]},
    {role:'assistant',content:null,tool_calls:[{id:'call-1',type:'function',function:{name:call.name,arguments:call.arguments}}]},
    {role:'tool',tool_call_id:'call-1',content:'{"status":"generated"}'},
  ]});
  assert.equal(body.tools[0].type,'namespace');assert.equal(body.tools[0].tools[0].name,'research_plan');
  assert.deepEqual(body.reasoning,{effort:'medium'});
  assert.equal(body.input[1].call_id,'call-1');assert.equal(body.input[2].call_id,'call-1');
  assert.equal(body.input[2].type,'function_call_output');assert.equal(body.input[2].output,'{"status":"generated"}');
});
test('completed output preserves encrypted reasoning and unknown usage',()=>{
  const original=[{type:'reasoning',id:'r',summary:[],encrypted_content:'opaque-fixture'},call];
  const result=completedResponse({status:'completed',output:original});
  assert.equal(result.usage,undefined);assert.equal(result.tool_calls[0].id,'call-1');
  const converted=convertRequest({model:'account-model',messages:[{role:'user',content:'Act.'},
    {role:'assistant',content:null,tool_calls:result.tool_calls,provider_output:result.provider_output},
    {role:'tool',tool_call_id:'call-1',content:'done'}]});
  assert.deepEqual(converted.input[1],original[0]);assert.deepEqual(converted.input[2],call);
  result.tool_calls[0].function.arguments='{}';
  assert.throws(()=>convertRequest({model:'account-model',messages:[{role:'user',content:'Act.'},
    {role:'assistant',content:null,tool_calls:result.tool_calls,provider_output:original}]}));
});
test('original usage is mapped without estimated counts',()=>{
  const r=completedResponse({status:'completed',output:[],usage:{input_tokens:8,output_tokens:3,total_tokens:11,output_tokens_details:{reasoning_tokens:2}}});
  assert.equal(r.usage.prompt_tokens,8);assert.equal(r.usage.completion_tokens_details.reasoning_tokens,2);
  assert.throws(()=>completedResponse({status:'incomplete',output:[call]}),{code:'response_incomplete'});
});
test('Responses completion, interruption and upstream errors are distinct',async()=>{
  const run=events=>streamResponse('synthetic-token',{model:'account-model',input:[{role:'user',content:'Hi.'}],reasoning:{effort:'none'}},new AbortController().signal,config=>{
    assert.equal(config.maxRetries,0);assert.equal(config.fetchOptions.redirect,'error');
    return {responses:{create:async(body)=>{
      assert.equal(body.store,false);assert.equal(body.stream,true);assert.equal(body.reasoning.effort,'none');
      return (async function*(){yield* events;})();
    }}};
  });
  assert.equal((await run([{type:'response.completed',response:{status:'completed',output:[call]}}])).tool_calls.length,1);
  await assert.rejects(run([{type:'response.output_text.delta',delta:'partial'}]),{code:'stream_interrupted'});
  await assert.rejects(run([{type:'response.incomplete'}]),{code:'response_incomplete'});
  await assert.rejects(run([{type:'response.failed',response:{error:{code:'subscription_sharing_usage_limit_exceeded'}}}]),{code:'subscription_sharing_usage_limit_exceeded'});
});
