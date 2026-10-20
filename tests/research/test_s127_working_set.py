"""Offline Store projections; fixtures never establish new scientific outcomes."""
from copy import deepcopy
import json
import unittest
from tools.platform_host import Host
from tools.platform_store import plain
from tools.research.config import ROOT
from tools.research.state import state, save, update
from tools.research.agent import record
from tools.research.core import read_evidence
from tools.research.research_context import context, decision_brief, physical_diagnostic, read_coverage
from tests.research.test_s125_contract import cold_host


def historical_host():
    return Host(ROOT/'runs/research/s126-cold-live-20261020','s126-cold-live-20261020',actor='unified-research')


def saved_pointer(h,query):
    value=h.store.artifact(query['reference'])
    if isinstance(value,bytes):value=json.loads(value)
    for key in query['pointer'][1:].split('/') if query['pointer'] else []:
        key=key.replace('~1','/').replace('~0','~');value=value[int(key)] if isinstance(value,list) else value[key]
    return value


class WorkingSetTests(unittest.TestCase):
    def test_real_replay_and_nmpc_measurements_are_read_only_and_exact(self):
        h=historical_host();before=deepcopy(state(h));ledger=h.store.remaining();events=h.store.events(h.run_id)
        for ref in [*before['physical_replays'],*before['results']]:
            value=h.store.artifact(ref);d=physical_diagnostic(h,ref)
            self.assertEqual(d['original_acceptance'],value['acceptance'])
            self.assertFalse(d['task_passed'])
            if value['status']=='evaluated':
                self.assertTrue(d['valid_complete']);self.assertTrue(d['critical_samples'])
                for sample in d['critical_samples']:
                    raw=saved_pointer(h,dict(reference=sample['raw_reference'],pointer=sample['read_pointer']))
                    self.assertEqual(sample['time_s'],raw['time_s'])
                    for v in sample['constraints']:
                        measured=saved_pointer(h,dict(reference=v['raw_reference'],pointer=v['raw_pointer']))
                        self.assertEqual(measured,v['value'])
                    if sample['input_query']:
                        self.assertEqual(saved_pointer(h,sample['input_query']),sample['observed']['actual_tension_n'])
                self.assertEqual(len(d['input_bounds_summary']['limits_n']),len(d['input_bounds_summary']['measured_max_n']))
            else:self.assertFalse(d['valid_complete'])
        self.assertEqual(state(h),before)
        self.assertEqual(h.store.remaining(),ledger);self.assertEqual(h.store.events(h.run_id),events)

    def test_projection_keeps_stop_index_and_does_not_promote_hypotheses(self):
        h=historical_host();before=state(h);c=context(h);ws=c['evidence_working_set']
        self.assertEqual(ws,decision_brief(c)['evidence_working_set'])
        self.assertEqual(ws['all_fresh_results'],c['all_fresh_results']);self.assertEqual(len(ws['all_fresh_results']),9)
        self.assertLessEqual(len(ws['candidate_index']),3);self.assertLessEqual(len(ws['read_coverage']),12)
        self.assertTrue(ws['control_result_links']);self.assertTrue(ws['control_comparisons'])
        for r in ws['candidate_index']:
            self.assertTrue(r['compiled']);self.assertFalse(r['accepted'])
        for r in ws['control_comparisons']:self.assertNotEqual(r['baseline'],r['variant'])
        self.assertNotIn('verified_physical_cause',json.dumps(ws))
        self.assertEqual(state(h),before)

    def test_coverage_requires_delivered_content_and_distinguishes_summary(self):
        h=cold_host();ref=save(h,{'a/b':{'x':[1,2,3]},'z':[4,5,6]})
        def deliver(query,view=None,status='success',payload=None,wire_payload=None,confirmed=True):
            use=dict(name='evidence_read',toolUseId='fixture-'+str(len(h.store.events(h.run_id))),input=dict(reference=ref,**query))
            body=read_evidence(h,dict(reference=ref,view=view or query.get('view','summary'),**{k:v for k,v in query.items() if k!='view'}))
            record(h,'model_original_tool_feedback',dict(tool_use=use,result=dict(toolUseId=use['toolUseId'],status=status,
                content=[dict(text=json.dumps(body if payload is None else payload))])))
            wire=save(h,dict(messages=[dict(role='tool',tool_call_id=use['toolUseId'],content=json.dumps(
                (body if payload is None else payload) if wire_payload is None else wire_payload))]))
            metadata=save(h,dict(request=wire,synthetic_fixture=True));response=save(h,dict(http_status=200,synthetic_fixture=True))
            with h.store.transaction() as db:
                h.store.event(db,h.run_id,'r3_request','sent',request=use['toolUseId'],outputs=[metadata])
                if confirmed:h.store.event(db,h.run_id,'r3_response','received',request=use['toolUseId'],outputs=[response])
        deliver({'view':'summary'});deliver({'pointer':'/a~1b','view':'full'})
        deliver({'pointer':'/a~1b/x','view':'full'});deliver({'pointer':'/a~1b/x','view':'full'})
        deliver({'pointer':'/z','view':'range','start':0,'count':3})
        deliver({'pointer':'/z','view':'range','start':1,'count':1})
        deliver({'view':'full'},payload={'offloaded':'unread'});deliver({'view':'full'},status='error')
        rows=read_coverage(h)
        self.assertEqual(len(rows),7)
        self.assertEqual([r['classification'] for r in rows[:6]],['new_query','new_query','covered_subnode','exact_repeat','new_query','covered_subnode'])
        self.assertFalse(rows[0]['complete_data']);self.assertFalse(rows[-1]['complete_data'])
        self.assertTrue(rows[1]['complete_data'])
        deliver({'pointer':'/z/2','view':'full'})
        deliver({'view':'fields','fields':['a/b','z']})
        deliver({'view':'fields','fields':['z']})
        deliver({'pointer':'/a~1b','view':'fields','fields':['x']},wire_payload={'offloaded':'raw feedback was not model delivery'})
        rows=read_coverage(h)
        self.assertEqual(rows[-4]['classification'],'covered_subnode')
        self.assertEqual(rows[-2]['classification'],'covered_subnode')
        self.assertFalse(rows[-1]['successfully_provided']);self.assertFalse(rows[-1]['complete_data'])
        deliver({'pointer':'/z','view':'full'},confirmed=False)
        self.assertFalse(read_coverage(h)[-1]['successfully_provided'])


if __name__=='__main__':unittest.main()
