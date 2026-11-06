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

const runEvents=events=>streamResponse('synthetic-token',{model:'account-model',input:[{role:'user',content:'Act.'}]},
  new AbortController().signal,()=>({responses:{create:async()=>
    (async function*(){yield* events;})()}}));

test('completed item events survive an omitted terminal output, preserving exact calls and reasoning',async()=>{
  const reasoning={type:'reasoning',id:'reasoning-fixture',encrypted_content:'opaque-fixture',summary:[]};
  const result=await runEvents([
    {type:'response.output_item.done',output_index:1,item:call},
    {type:'response.output_item.done',output_index:0,item:reasoning},
    {type:'response.completed',response:{status:'completed',output:[],usage:{input_tokens:8,output_tokens:3,total_tokens:11}}},
  ]);
  assert.deepEqual(result.provider_output,[reasoning,call]);
  assert.equal(result.tool_calls[0].id,call.call_id);assert.equal(result.tool_calls[0].function.arguments,call.arguments);
  assert.equal(result.usage.total_tokens,11);
  assert.deepEqual(result.gateway_completion,{output_source:'completed_item_events',terminal_output_items:0,completed_item_events:2});
  const text={type:'message',role:'assistant',status:'completed',content:[{type:'output_text',text:'Exact completed text.'}]};
  assert.equal((await runEvents([{type:'response.output_item.done',output_index:0,item:text},
    {type:'response.completed',response:{status:'completed'}}])).text,'Exact completed text.');
});

test('terminal output remains authoritative and empty/delta-only output is never fabricated',async()=>{
  const final={type:'message',role:'assistant',content:[{type:'output_text',text:'Terminal answer.'}]};
  const result=await runEvents([{type:'response.output_item.done',output_index:0,item:call},
    {type:'response.completed',response:{status:'completed',output:[final]}}]);
  assert.equal(result.text,'Terminal answer.');assert.deepEqual(result.tool_calls,[]);
  assert.equal(result.gateway_completion.output_source,'terminal_output');
  const empty=await runEvents([{type:'response.output_text.delta',delta:'unconfirmed'},
    {type:'response.completed',response:{status:'completed',output:[]}}]);
  assert.equal(empty.text,'');assert.deepEqual(empty.tool_calls,[]);assert.equal(empty.usage,undefined);
});

test('completed items alone cannot turn interruption, incompleteness or failure into success',async()=>{
  const done={type:'response.output_item.done',output_index:0,item:call};
  await assert.rejects(runEvents([done]),{code:'stream_interrupted'});
  await assert.rejects(runEvents([done,{type:'response.incomplete'}]),{code:'response_incomplete'});
  await assert.rejects(runEvents([done,{type:'response.failed',response:{error:{code:'subscription_sharing_usage_limit_exceeded'}}}]),{code:'subscription_sharing_usage_limit_exceeded'});
  await assert.rejects(runEvents([{type:'response.output_item.done',output_index:0,item:{...call,status:'incomplete'}},
    {type:'response.completed',response:{status:'completed',output:[]}}]),{code:'invalid_stream'});
});
