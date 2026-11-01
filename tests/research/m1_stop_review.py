"""Read-only reconstruction of the real pre-STOP request, not Study recovery."""
from copy import deepcopy
import json
from tools.platform_host import Host
from tools.research.config import ROOT

RUN='m1-elevated-auth-checked-20261101-b824e6d1'


class HistoricalReads:
    """Restrict reads to the recorded decision boundary; forbid Store mutations."""
    def __init__(self,store,snapshot,events,ledger):
        self.store=store;self.snapshot=snapshot;self.history=events;self.ledger=ledger

    def session(self,run_id,db=None):
        result=self.store.session(run_id,db);result['state']=deepcopy(self.snapshot);return result

    def events(self,run_id,db=None):return deepcopy(self.history)

    def remaining(self,db=None):return deepcopy(self.ledger)

    def __getattr__(self,name):
        if name in ('transaction','put','event','update_state','create','reserve','complete'):
            raise AssertionError('Historical Study is read only: '+name)
        return getattr(self.store,name)


def historical_decision(number=70):
    h=Host(ROOT/'runs/research'/RUN,RUN,actor='unified-research')
    store=h.store;events=store.events(RUN)
    requests=list({e['request_id']:e for e in events if e['kind']=='r3_request'}.values())
    event=requests[number-1]
    before=[e for e in events if e['sequence']<event['sequence']]
    meta=store.artifact(event['outputs'][0]);wire=store.artifact(meta['request'])
    packet=json.loads(wire['messages'][-1]['content'].split('\n',1)[1])['research']
    s=deepcopy(store.session(RUN)['state']);s.update(research_status='ready',count_closeout=False)
    s.pop('final_disposition');s.pop('closed_unix',None)
    known={r['artifact_id'] for e in before for r in e['outputs']}
    s['plans']=[r for r in s['plans'] if r['artifact_id'] in known]
    route=next(e['outputs'][0] for e in reversed(before) if e['kind']=='research_tool_route')
    s['pilot'].update(tool_route=route,unconsumed_response=None)
    ledger=deepcopy(store.remaining());budget=packet['budget']
    for key,field,total in [('model_calls','model_calls',160),('tool_calls','public_operations',640)]:
        ledger['used'][key]=total-budget[field];ledger['remaining'][key]=budget[field]
    ledger['occupied']={}
    h.store=HistoricalReads(store,s,before,ledger)
    return h,wire,dict(request_id=event['request_id'],reference=event['outputs'][0],wire_reference=meta['request'],
        reconstruction='All 14 mathematical results existed at the requested pre-STOP boundary. Later events are excluded; original wire supplies remaining counts. Original Store is never changed.')
