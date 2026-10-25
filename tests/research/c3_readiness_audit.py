"""Read-only C3 wire/cost audit; never creates a Study or sends a request."""
from copy import deepcopy
import json
from pathlib import Path
import tarfile
import httpx
from tests.research.test_c1_method_context import C1Archive
from tools.platform_store import plain
from tools.research.agent import DeepSeekModel
from tools.research.research_context import compact_scientific_delivery
from tools.research.session_handoff import initial_messages


class C3Archive(C1Archive):
    def __init__(self):
        path=Path(__file__).resolve().parents[2]/'evidence/c3_blank_autonomous_softarm/immutable_artifacts.tar.gz'
        self.archive=tarfile.open(path)
        self.snapshot=json.load(self.archive.extractfile(next(m for m in self.archive.getmembers() if m.name.startswith('snapshot/'))))


def serialized(value):
    return httpx.Request('POST','https://offline.invalid',json=value).content


def context_audit():
    archive=C3Archive();requests=archive.requests();rows=[]
    from tools.research.provider_context import official_tokenizer
    try:tokenizer=official_tokenizer()
    except ImportError:tokenizer=None
    for index in (0,12,24):
        event,meta,wire,packet,events=requests[index]
        after=deepcopy(wire);packet=deepcopy(packet)
        packet['research']=compact_scientific_delivery(packet['research'],decision_only=True)
        after['messages'][-1]['content']='CURRENT_RESEARCH_PACKET\n'+json.dumps(packet,separators=(',',':'))
        short=deepcopy(after)
        short['messages']=[wire['messages'][0],*DeepSeekModel.format_request_messages(initial_messages(packet['study_id'])),after['messages'][-1]]
        variants={'original':wire,'same_session':after,'verified_handoff_projection':short}
        # Count actual repeated numerical payloads, not evidence references.
        probes=('0.19304308687570046','61.52347153119494')
        rows.append(dict(boundary=index+1,request_reference=meta['request'],
            sizes={k:dict(bytes=len(serialized(v)),offline_tokens=len(tokenizer.encode(serialized(v).decode(),add_special_tokens=False).ids) if tokenizer else None)
                for k,v in variants.items()},
            contributions=dict(system_bytes=sum(len(serialized(m)) for m in wire['messages'] if m['role']=='system'),
                historical_assistant_bytes=sum(len(serialized(m)) for m in wire['messages'] if m['role']=='assistant'),
                tool_feedback_bytes=sum(len(serialized(m)) for m in wire['messages'] if m['role']=='tool'),
                packet_bytes=len(serialized(json.loads(wire['messages'][-1]['content'].split('\n',1)[1]))),
                schema_bytes=len(serialized(wire.get('tools',[])))),
            payload_occurrences={k:{p:serialized(v).decode().count(p) for p in probes} for k,v in variants.items()},
            history_preserved=wire['messages'][:-1]==after['messages'][:-1],
            stop_and_select_rules_preserved=packet['guidance']==json.loads(wire['messages'][-1]['content'].split('\n',1)[1])['guidance'],
            budget_preserved=packet['research']['budget']==json.loads(wire['messages'][-1]['content'].split('\n',1)[1])['research']['budget'],
            handoff_status='Offline complete-wire projection only; actual rotation requires existing live admission and settled boundary verification'))
        for report in packet['research'].get('latest_reports',[]):
            archive.artifact(report['report_reference'])
            for ref in report['result_references']:archive.artifact(ref)
    archive.archive.close()
    return dict(boundaries=rows,provider_requests=0,scientific_workers=0,
        token_scope='Pinned local tokenizer over serialized JSON; not Provider prompt usage',
        contributions_scope='Serialized components include their own framing, not an additive partition')


if __name__=='__main__':
    print(json.dumps(context_audit(),indent=2))
