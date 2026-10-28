import { GatewayError } from './errors.mjs';
const object = x => x !== null && typeof x === 'object' && !Array.isArray(x);
const fail = message => { throw new GatewayError('invalid_request', message, false, 400); };
const name = x => typeof x === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(x);
function text(content, nullable = false) {
  if (nullable && content == null) return '';
  if (typeof content === 'string') return content;
  if (Array.isArray(content) && content.every(b => object(b) && b.type === 'text' && typeof b.text === 'string')) return content.map(b => b.text).join('');
  fail('Only text content blocks are supported by this gateway.');
}
export function convertRequest(body) {
  if (!object(body)) fail('Expected a JSON request object.');
  if (Object.keys(body).some(k => !['model','messages','stream','tools','tool_choice','reasoning_effort'].includes(k))) {
    throw new GatewayError('unsupported_parameter','Unsupported request parameter.',false,400);
  }
  if (typeof body.model !== 'string' || !body.model.trim() || body.model.length > 200 || (body.stream !== undefined && body.stream !== false) || !Array.isArray(body.messages) || !body.messages.length || body.messages.length > 2000) fail('Use an explicit catalog model, messages and stream:false.');
  if (body.tool_choice !== undefined && body.tool_choice !== 'auto') fail('Only automatic tool selection is supported.');
  if (body.reasoning_effort !== undefined && !['none','medium'].includes(body.reasoning_effort)) fail('Reasoning must be none or medium.');
  const input=[], system=[], pending=new Set(), returned=new Set();
  for (const m of body.messages) {
    if (!object(m) || Object.keys(m).some(k => !['role','content','tool_calls','tool_call_id','provider_output'].includes(k))) fail('Unsupported message shape.');
    if (m.role === 'system') {
      if (input.length || m.tool_calls || m.provider_output) fail('System instructions must precede conversation.');
      system.push(text(m.content)); continue;
    }
    if (m.role === 'tool') {
      if (!pending.has(m.tool_call_id) || returned.has(m.tool_call_id)) fail('Tool output must match one preceding call ID.');
      input.push({type:'function_call_output',call_id:m.tool_call_id,output:text(m.content)});
      returned.add(m.tool_call_id);continue;
    }
    if (!['user','assistant','developer'].includes(m.role)) fail('Unsupported role.');
    const content=text(m.content,m.role === 'assistant');
    const calls=m.tool_calls ?? [];
    if (!Array.isArray(calls) || (calls.length && m.role !== 'assistant')) fail('Invalid tool calls.');
    const functions=calls.map(c => {
      if (!object(c) || c.type !== 'function' || !name(c.function?.name) || typeof c.id !== 'string' || !c.id || typeof c.function.arguments !== 'string' || pending.has(c.id)) fail('Invalid function call identity.');
      pending.add(c.id);
      return {type:'function_call',call_id:c.id,name:c.function.name,namespace:'research',arguments:c.function.arguments};
    });
    if (m.provider_output !== undefined) {
      // Preserve completed opaque reasoning items from the original response.
      if (m.role !== 'assistant' || !Array.isArray(m.provider_output) || m.provider_output.some(i => !['message','function_call','reasoning'].includes(i.type))) fail('Invalid original Provider output.');
      const original=m.provider_output.filter(i => i.type === 'function_call');
      if (JSON.stringify(original.map(i => [i.call_id,i.name,i.arguments])) !== JSON.stringify(functions.map(i => [i.call_id,i.name,i.arguments]))) fail('Provider output call identity mismatch.');
      input.push(...m.provider_output);
    } else {
      if (content) input.push({role:m.role,content});
      input.push(...functions);
    }
  }
  if ([...pending].some(id => !returned.has(id))) fail('Every prior function call needs its result before the next request.');
  if (!input.some(m => m.role === 'user')) fail('A user message is required.');
  const tools=body.tools ?? [];
  if (!Array.isArray(tools)) fail('Tools must be an array.');
  const functions=tools.map(t => {
    if (t.type !== 'function' || !name(t.function?.name) || !object(t.function.parameters)) fail('Only JSON function tools are supported.');
    return {type:'function',name:t.function.name,description:t.function.description ?? '',parameters:t.function.parameters,strict:false};
  });
  return {model:body.model,input,...(system.length ? {instructions:system.join('\n\n')} : {}),
    ...(functions.length ? {tools:[{type:'namespace',name:'research',description:'Caller-owned research tools.',tools:functions}]} : {}),
    ...(body.reasoning_effort ? {reasoning:{effort:body.reasoning_effort}} : {})};
}
