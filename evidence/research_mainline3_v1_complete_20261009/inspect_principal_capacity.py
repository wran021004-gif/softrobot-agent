from pathlib import Path
from tools.state_io import read,atomic_json
from tools.platform_store import Store,encode
from tools.platform_host import Host
from tools.research_investigations import InvestigationDispatcher
from tools.context_assembly import measure_input
import json
out=Path('evidence/research_mainline3_v1_complete_20261009');m=read(out/'validation_manifest.json');s=Store(Path(m['phases']['coordinated']['output']));h=Host(s.root,'mainline3-coordinated');d=InvestigationDispatcher(h);n=s.session(h.run_id)['state']['investigations']['principal-coordinated-v2'];print(dict(usage=n['usage'],purpose=n['requests_by_purpose'],next_purpose=n.get('next_request_purpose'),deadline=n['started_unix']+n['order']['timeout_s']))
print(s.artifact(n['failure_record']))
events=s.events(h.run_id);send=[e for e in events if e['kind']=='investigation_provider_attempt' and e['request_id'].startswith('investigation-principal')][-1];wire=s.artifact(send['outputs'][0])['payload'];raw=s.artifact(n['provider_response_refs'][-1]);feedback=s.artifact([e for e in events if e['kind']=='investigation_protocol_correction' and e['request_id']=='investigation-principal-coordinated-v2'][-1]['outputs'][0]);message=raw['choices'][0]['message']
d._append_correction(wire,d._assistant_history(message),message['tool_calls'][0]['id'],feedback)
print(dict(measurement=measure_input(wire,s.session(h.run_id)['snapshot']['input']['policy']['model'],'research_decision'),feedback=feedback,message_bytes=len(encode(message).encode())))
packet=json.loads(wire['messages'][1]['content']);print({k:len(encode(v).encode()) for k,v in packet.items()})
atomic_json(out/'principal_capacity_failed_wire.json',wire)
