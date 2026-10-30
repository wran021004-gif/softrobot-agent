// Own Responses conversion; OAuth renewal, permission checks and storage stay
// in the pinned DevKit. This function runs only inside its authenticated path.
import OpenAI from 'openai';
import { apiError, ChatGPTError } from '../.devkit/packages/local/dist/errors.js';

export function completedResponse(response) {
  if (response.status !== 'completed') throw new ChatGPTError('response_incomplete','Response did not complete.',true);
  const output=response.output ?? [];
  if (output.some(i => !['message','function_call','reasoning'].includes(i.type))) {
    throw new ChatGPTError('subscription_sharing_unsupported_capability','Unsupported output item; no tool was executed.',false);
  }
  if (output.some(i => i.status && i.status !== 'completed')) {
    throw new ChatGPTError('invalid_stream','Incomplete output item.',true);
  }
  const tool_calls=output.filter(i => i.type === 'function_call').map(i => {
    if ((i.namespace && i.namespace !== 'research') || !i.call_id || !i.name || typeof i.arguments !== 'string') {
      throw new ChatGPTError('invalid_stream','Incomplete function call.',true);
    }
    return {id:i.call_id,type:'function',function:{name:i.name,arguments:i.arguments}};
  });
  const text=output.filter(i => i.type === 'message').flatMap(i => i.content ?? []).filter(c => c.type === 'output_text').map(c => c.text).join('');
  const u=response.usage;
  return {text,tool_calls,provider_output:output,
    ...(u ? {usage:{prompt_tokens:u.input_tokens,completion_tokens:u.output_tokens,total_tokens:u.total_tokens,
      ...(u.output_tokens_details ? {completion_tokens_details:u.output_tokens_details} : {}),
      ...(u.input_tokens_details ? {prompt_tokens_details:u.input_tokens_details} : {})}} : {})};
}

export async function streamResponse(accessToken, options, signal, createClient = config => new OpenAI(config)) {
  const client=createClient({apiKey:accessToken,baseURL:'https://api.openai.com/v1',organization:null,project:null,
    logLevel:'warn',maxRetries:0,fetchOptions:{redirect:'error'},
    defaultHeaders:{authorization:`Bearer ${accessToken}`,'openai-organization':null,'openai-project':null}});
  const requestSignal=AbortSignal.any([signal,AbortSignal.timeout(180_000)]);
  try {
    const {signal:ignored,onDelta,...body}=options;
    const stream=await client.responses.create({...body,store:false,stream:true,
      include:['reasoning.encrypted_content']},{signal:requestSignal,headers:{accept:'text/event-stream'}});
    const completedItems=new Map();
    for await (const event of stream) {
      requestSignal.throwIfAborted();
      if (event.type === 'response.output_item.done') completedItems.set(event.output_index,event.item);
      if (event.type === 'response.completed') {
        // Some streams omit the output list on the terminal event. Only exact
        // completed items may fill it, and only after the response itself completes.
        const output=event.response.output?.length ? event.response.output
          : [...completedItems].sort(([a],[b])=>a-b).map(([,item])=>item);
        return {...completedResponse({...event.response,output}),gateway_completion:{
          output_source:event.response.output?.length ? 'terminal_output' : 'completed_item_events',
          terminal_output_items:event.response.output?.length ?? 0,completed_item_events:completedItems.size}};
      }
      if (event.type === 'response.incomplete') throw new ChatGPTError('response_incomplete','Response stopped before completion.',true);
      if (event.type === 'response.failed' || event.type === 'error') throw apiError(event.response ?? event,200);
    }
    throw new ChatGPTError('stream_interrupted','Stream ended without response.completed.',true);
  } catch (error) {
    if (error instanceof ChatGPTError) throw error;
    if (signal.aborted) throw new ChatGPTError('cancelled','Request cancelled.',false);
    if (error instanceof OpenAI.APIError) throw apiError(error.error,error.status,error.requestID);
    throw new ChatGPTError('network_error','Responses transport failed; outcome may be unknown.',true);
  }
}
