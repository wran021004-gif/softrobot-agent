"""Export original provider messages and tool responses from the sealed Store."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.platform_store import Store
from tools.state_io import read,atomic_json

HERE=Path(__file__).resolve().parent/'live'
if __name__=='__main__':
    store=Store(HERE);run=read(HERE/'workflow.json')['run_id'];audit=read(HERE/'behavior_audit.json')
    conversation=[];final=None
    for event in store.events(run):
        if event['kind']=='model_raw_response':
            raw=store.artifact(event['outputs'][0])['raw']
            conversation.append(dict(kind='provider_response',request_id=event['request_id'],reference=event['outputs'][0],raw=raw))
            for choice in raw.get('choices',[]):
                for call in choice.get('message',{}).get('tool_calls',[]):
                    function=call['function']
                    envelope=json.loads(function['arguments'])
                    args=envelope.get('arguments',{})
                    if args.get('action')=='finish':final=args['reason']
        if event['kind']=='context_delivery':
            conversation.append(dict(kind='context_delivered',request_id=event['request_id'],reference=event['inputs'][0]))
    with store.connect(True) as db:
        calls=[dict(r) for r in db.execute('SELECT * FROM calls')]
    for row in calls:
        if row['caller']=='model-transport' or not row['receipt']:continue
        receipt=json.loads(row['receipt'])
        conversation.append(dict(kind='tool_response',owner_run_id=row['run_id'],receipt=receipt,
            content=store.artifact(receipt['output']) if receipt.get('output') else None))
    atomic_json(HERE/'conversation.json',dict(run_id=run,events=conversation,
        context_content='Full submitted contexts are preserved under the referenced content addresses in platform.sqlite; provider responses/tool results below are original values.'))
    if final is not None:
        (HERE/'model_final.txt').write_text(final,encoding='utf8')
    print(json.dumps(dict(provider_requests=audit['real_model_requests'],tool_calls=audit['tool_calls'],
        backend_executions=audit['backend_executions'],provider_finish_present=final is not None,
        current_report_delivered=audit['fresh_report_delivered'])))
