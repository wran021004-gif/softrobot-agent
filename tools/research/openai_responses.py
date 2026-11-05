"""Stateless Responses wire conversion for the existing SDK/Store boundary.

The SDK still owns messages and tool execution. Original upstream requests and
responses are archived separately; the Chat view is a deterministic projection.
"""
from copy import deepcopy
import json


def request_wire(host, wire):
    """Preserve text/function history and original encrypted reasoning items."""
    originals={}
    for event in host.store.events(host.run_id):
        if event['kind']!='r3_response' or event['status']!='metadata_saved':continue
        reception=host.store.artifact(event['outputs'][0])
        if reception.get('protocol')!='openai_responses_v1' or reception['http_status']!=200:continue
        body=json.loads(host.store.artifact(reception['body'],raw=True))
        for choice in body.get('choices',[]):
            message=choice['message'];calls=message.get('tool_calls',[])
            if calls:originals[tuple(c['id'] for c in calls)]=(message,reception)
    items=[]
    def content(value,kind):
        if isinstance(value,str):return [dict(type=kind,text=value)] if value else []
        result=[]
        for block in value or []:
            if block.get('type')!='text':raise ValueError('RESPONSES_TEXT_ONLY_RESEARCH_PROFILE_REQUIRED')
            result.append(dict(type=kind,text=block['text']))
        return result
    for message in wire['messages']:
        calls=message.get('tool_calls',[]);key=tuple(c['id'] for c in calls)
        if key in originals:
            original,reception=originals[key]
            semantic=lambda cs:[(c['id'],c['function']['name'],json.loads(c['function']['arguments'])) for c in cs]
            if (semantic(calls)!=semantic(original['tool_calls']) or
                    content(message.get('content'),'output_text')!=content(original.get('content'),'output_text')):
                raise ValueError('RESPONSES_ORIGINAL_TOOL_MESSAGE_MISMATCH')
            upstream=json.loads(host.store.artifact(reception['upstream_body'],raw=True))
            items.extend(deepcopy(upstream['output']));continue
        role=message['role']
        if role=='tool':
            output=message.get('content')
            items.append(dict(type='function_call_output',call_id=message['tool_call_id'],
                output=output if isinstance(output,str) else content(output,'input_text')))
            continue
        blocks=content(message.get('content'),'output_text' if role=='assistant' else 'input_text')
        if blocks:items.append(dict(role=role,content=blocks))
        for call in calls:
            if call['type']!='function':raise ValueError('RESPONSES_FUNCTION_TOOLS_REQUIRED')
            items.append(dict(type='function_call',call_id=call['id'],**deepcopy(call['function'])))
    result=dict(model=wire['model'],input=items,stream=False,store=False,
        reasoning=dict(effort=wire['reasoning_effort']),include=['reasoning.encrypted_content'])
    if wire.get('tools'):
        # Responses defaults to strict schemas; retain the SDK's existing contract.
        result['tools']=[dict(type='function',strict=False,**deepcopy(t['function'])) for t in wire['tools']]
    if 'tool_choice' in wire:result['tool_choice']=wire['tool_choice']
    if 'max_completion_tokens' in wire:result['max_output_tokens']=wire['max_completion_tokens']
    return result


def chat_view(body):
    """Expose only actual upstream text/tool fields; incomplete stays incomplete."""
    value=json.loads(body);calls=[];texts=[]
    for item in value.get('output',[]):
        if item['type']=='function_call':
            calls.append(dict(id=item['call_id'],type='function',function=dict(name=item['name'],arguments=item['arguments'])))
        elif item['type']=='message':
            for block in item.get('content',[]):
                if block['type']=='output_text':texts.append(block['text'])
                elif block['type']=='refusal':texts.append(block['refusal'])
    message=dict(role='assistant',content=''.join(texts) or None)
    if calls:message['tool_calls']=calls
    reason=('tool_calls' if calls else 'stop') if value.get('status')=='completed' else 'length'
    result=dict(id=value.get('id'),object='chat.completion',model=value.get('model'),
        choices=[dict(index=0,message=message,finish_reason=reason)])
    usage=value.get('usage')
    if usage:
        result['usage']=dict(prompt_tokens=usage.get('input_tokens'),completion_tokens=usage.get('output_tokens'),total_tokens=usage.get('total_tokens'))
        for source,target in (('input_tokens_details','prompt_tokens_details'),('output_tokens_details','completion_tokens_details')):
            if usage.get(source) is not None:result['usage'][target]=usage[source]
    return json.dumps(result,separators=(',',':')).encode('utf-8')
