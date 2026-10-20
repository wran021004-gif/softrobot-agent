"""Sealed decision-time snapshots; no solver, workflow dispatch, or archive writes."""
from copy import deepcopy
import json
from unittest.mock import Mock
from tools.research.config import ROOT
from tools.research.state import state
from tools.state_io import atomic_json, digest
from tests.research.s8_audit import archive_host

CASES = (('historical_start',34),('fresh_failure',319),('last_exploration_request',450))
OUT = ROOT/'evidence/s12_decision_probe'


def snapshot(sequence):
    h,values=archive_host('evidence/s11_mirror/study')
    events=[e for e in h.store.events(h.run_id) if e['sequence']<=sequence]
    event=next(e for e in events if e['sequence']==sequence)
    packet=deepcopy(h.store.artifact(event['outputs'][0]))
    # Only objects reachable from already published event inputs/outputs exist here.
    available={}
    def include(value):
        if isinstance(value,dict):
            identity=value.get('artifact_id')
            if isinstance(identity,str) and identity in values and identity not in available:
                available[identity]=values[identity];include(values[identity])
            else:
                for x in value.values():include(x)
        elif isinstance(value,list):
            for x in value:include(x)
    for e in events:include(e.get('inputs',[]));include(e.get('outputs',[]))
    s=deepcopy(state(h));research=packet['research']
    for key in ('results','physical_replays','mechanics_results','analysis_results','control_search_results',
                'matched_state_results','rl_evaluations','plans','research_mathematics','reads','evaluation_reads'):
        s[key]=[r for r in s.get(key,[]) if r['artifact_id'] in available]
    s['candidates']={k:r for k,r in s['candidates'].items() if r['artifact_id'] in available}
    s['control_initializations']=[r for r in s['control_initializations'] if r['source']['artifact_id'] in available]
    s.update(research_status='ready',pending=None,selected=None,final_disposition=None)
    s.pop('success_gate',None)
    for key,value in research['method_used'].items():s[key]=value
    s['physical_replay_launches']=len(s['physical_replays'])
    ledger=deepcopy(h.store.remaining());ledger['remaining']['model_calls']=research['budget']['provider_budget']['remaining_total']
    ledger['remaining']['backend_solves']=research['budget']['science_budget']['remaining_physical']
    ledger['remaining']['tool_calls']=s['spec']['budgets']['public_operations']-sum(e['kind']=='model_original_tool_request' for e in events)
    h.store.session.return_value={'state':s};h.store.events.return_value=events;h.store.remaining.return_value=ledger
    h.store.artifact.side_effect=lambda r,raw=False:available[dict(r)['artifact_id']]
    # Any persistence/dispatch accidentally introduced into this probe fails closed.
    h.store.transaction.side_effect=AssertionError('READ_ONLY_PROBE_NO_WRITES')
    h.store.reserve.side_effect=AssertionError('READ_ONLY_PROBE_NO_RESERVATION')
    return h,packet,available,event


def offline():
    rows=[]
    for name,sequence in CASES:
        h,p,values,event=snapshot(sequence)
        from tools.research.agent import plan_schema
        rows.append(dict(name=name,source='evidence/s11_mirror/study',cutoff_sequence=sequence,
            packet=event['outputs'][0],packet_identity=digest(p),accessible_artifacts=len(values),
            remaining=h.store.remaining()['remaining'],original_actions=p['research']['actions'],
            next_request_will_protect=p['research']['budget']['closeout']['next_request_will_protect'],
            contract_identity=digest(plan_schema(state(h)['spec']['allowed_plan_actions']))))
    result=dict(version='s12_decision_probe_v1',states=rows,provider_request_ceiling=6,
        sampling='Three identical states x old/new, one response each; no invented tool success or follow-up',
        new_provider_requests=0,new_scientific_executions=0,
        boundary='In-memory hash-verified archive subset; no dispatch, reserve, transaction or scientific callback',
        live_status='not_tested',limitation='Offline archive replay is not a newly sampled model decision')
    OUT.mkdir(parents=True,exist_ok=True);atomic_json(OUT/'frozen_cases.json',result)
    return result


if __name__=='__main__':print(json.dumps(offline()))
