"""Targeted archived continuity/diagnostic checks; no live sends or physics."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from tests.research.c3_readiness_audit import C3Archive, serialized
from tools.research.session_handoff import feedback_delivery, pending_feedback_delivery
from tools.research.research_context import read_coverage

ROOT=Path(__file__).resolve().parents[2]


def archive(arm):
    name='heuristic' if arm=='a' else 'math_search'
    a=C3Archive(ROOT/f'evidence/c3_{name}_ab_100ms_20261025/immutable_artifacts.tar.gz')
    bodies={m.name:a.archive.extractfile(m).read() for m in a.archive.getmembers() if m.name.startswith('artifacts/')}
    decoded={}
    def artifact(ref,raw=False):
        from tools.platform_store import plain
        ref=plain(ref)
        key='artifacts/'+ref['artifact_id']+('.json' if ref.get('media_type','application/json')=='application/json' else '.bin')
        if raw:return bodies[key]
        if key not in decoded:decoded[key]=json.loads(bodies[key])
        return deepcopy(decoded[key])
    a.artifact=artifact
    return a


def boundary_projection(a,index):
    event,meta,wire,packet,events=a.requests()[index-1]
    committed=next(e for e in reversed(events) if e['kind']=='session_handoff' and e['status']=='committed')
    boundary=next(e for e in reversed(events[:events.index(committed)]) if e['kind']=='request_feedback_boundary')
    h,s=a.host(events);ids=a.artifact(boundary['outputs'][0])['tool_ids']
    preparation=a.artifact(committed['outputs'][0])
    s.clear();s.update(a.artifact(preparation['source_state']))
    s['pilot'].update(framework_session_id=preparation['next_session'],handoff=committed['outputs'][0])
    h.store.remaining.return_value=preparation['budget']
    delivery=feedback_delivery(h,ids)
    after=deepcopy(wire);after_packet=deepcopy(packet)
    from tools.research.research_context import agent_decision_brief
    after_packet['research']=agent_decision_brief(h)
    after_packet['research']['pending_feedback_delivery']=delivery
    after['messages'][-1]['content']='CURRENT_RESEARCH_PACKET\n'+json.dumps(after_packet,separators=(',',':'))
    return h,s,after,delivery,dict(boundary=index,original_wire=meta['request'],
        original_bytes=len(serialized(wire)),projected_bytes=len(serialized(after)),tool_ids=ids,
        missing_in_original=not any(m.get('role')=='tool' and m.get('tool_call_id') in ids for m in wire['messages']))


class C3ContinuityTests(unittest.TestCase):
    def test_a19_to20_and_b_archived_boundary(self):
        for arm,index in [('a',20),('b',42)]:
            a=archive(arm)
            try:
                h,s,wire,delivery,facts=boundary_projection(a,index)
                self.assertTrue(facts['missing_in_original'])
                self.assertTrue(delivery['items'])
                for row in delivery['items']:
                    original=h.store.artifact(row['feedback_reference'])
                    self.assertEqual(row['query'],original['tool_use']['input'])
                    if row['delivery']=='exact_feedback':self.assertEqual(row['result'],original['result'])
                if arm=='a':self.assertIn('/control_result_links',json.dumps(delivery))
                self.assertLess(facts['projected_bytes']-facts['original_bytes'],24000)
                self.assertFalse(any(m.get('tool_calls') for m in wire['messages']))
            finally:a.archive.close()

    def test_dynamic_content_and_summary_credit(self):
        a=archive('a')
        try:
            h,s,wire,delivery,_=boundary_projection(a,20)
            events=h.store.events.return_value
            # Synthetic send/response envelope around REAL archived feedback; never science.
            refs={}
            old=h.store.artifact.side_effect
            def artifact(ref,raw=False):return refs[ref['artifact_id']] if ref['artifact_id'] in refs else old(ref,raw=raw)
            h.store.artifact.side_effect=artifact
            def ref(key,value):
                refs[key]=value
                return dict(artifact_id=key,media_type='application/json')
            prep=ref('fixture-preparation',dict(pending_feedback_delivery=delivery));s['pilot']['handoff']=prep
            self.assertEqual(pending_feedback_delivery(h),delivery)
            req=ref('fixture-meta',dict(request=ref('fixture-wire',wire)))
            events.append(dict(kind='r3_request',request_id='fixture-send',outputs=[req]))
            self.assertEqual(pending_feedback_delivery(h),delivery)  # sent/unknown is not acknowledged
            events.append(dict(kind='r3_response',request_id='fixture-send',outputs=[ref('fixture-response',dict(http_status=200))]))
            self.assertIsNone(pending_feedback_delivery(h))
            rows=read_coverage(h);ids={r['tool_id'] for r in delivery['items'] if r['delivery']=='exact_feedback'}
            self.assertTrue(any(r['delivery_status']=='summary_only' for r in rows))
            self.assertFalse(any(r['complete_data'] for r in rows if r['query']['view']=='working_set'))
            dynamic=[r for r in rows if r['query']['view']=='working_set']
            for i,row in enumerate(dynamic):
                if row['classification']=='exact_repeat':
                    self.assertTrue(any(p['query']==row['query'] and p['successfully_provided'] and
                        p['delivery_identity']==row['delivery_identity'] for p in dynamic[:i]))
        finally:a.archive.close()

    def test_real_disposition_error_corrects_experience_field(self):
        from tools.research.agent import error_feedback
        a=archive('a')
        try:
            h,s=a.host()
            error=next(a.artifact(e['outputs'][0]) for e in a.snapshot['events'] if e['kind']=='tool_request_error'
                and 'DISPOSITION_REQUIRES_EXACT_ACTUAL_READ' in a.artifact(e['outputs'][0]).get('message',''))
            with patch('tools.research.agent.record',return_value={'artifact_id':'fixture-error'}):
                result=error_feedback(h,error['tool_use'],ValueError(error['message']),s)
            self.assertEqual(result['field'],'experience_disposition')
            self.assertIn('remove',result['expected'])
            self.assertNotIn('then SELECT',result['expected'])
        finally:a.archive.close()

    def test_b_diagnostic_alignment_bottleneck_and_numerical_tie(self):
        from tools.research.evidence_views import diagnostic_relations
        from tools.research.core import read_evidence
        a=archive('b')
        try:
            h,s=a.host();ref=s['results'][-1]
            d=read_evidence(h,dict(reference=ref,view='working_set',pointer='/diagnostic_relations'),record_read=False)
            relation=d['relations'][0]
            self.assertEqual(relation['status'],'partial_comparison')
            self.assertEqual(relation['missing_conditions'],['saved_prediction_samples','recorded_aligned_difference'])
            self.assertIsNone(relation['sample_differences'])
            self.assertEqual(d['task_diagnosis']['violated_constraints']['holding_speed']['limit'],.02)
            self.assertAlmostEqual(d['task_diagnosis']['violated_constraints']['holding_speed']['value'],.18173358255275762)
            self.assertEqual(d['task_diagnosis']['critical_samples'][0]['time_s'],.31)
            resolution=d['search_comparisons'][0]['resolution']
            self.assertEqual(resolution['status'],'indistinguishable_at_recorded_numerical_precision')
            self.assertLess(abs(resolution['score_delta']),min(b-a for a,b in resolution['recorded_support_intervals']))
            self.assertTrue(any(r['kind']=='same_candidate_different_controllers' for r in d['relations']))
            # Explicit alignment fixture, using recorded physical samples as FABRICATED
            # predictions. This exercises admission only, never scientific agreement.
            physical=a.artifact(s['physical_replays'][0]);source_ref=physical['source_reference']
            source=a.artifact(source_ref);raw=a.artifact(physical['raw_reference'])
            source['mathematical_outputs']=dict(times_s=source['trajectory']['times_s'],
                tip_positions_m=[v['tip_m'] for v in raw['samples']],tip_velocities_m_s=[v['tip_velocity_m_s'] for v in raw['samples']])
            physical['comparison'].update(aligned=True,samples=[dict(fixture_only=True)])
            original=h.store.artifact.side_effect
            h.store.artifact.side_effect=lambda r,raw=False:deepcopy(source) if r==source_ref else deepcopy(physical) if r==s['physical_replays'][0] else original(r,raw=raw)
            self.assertEqual(diagnostic_relations(h,ref)['relations'][0]['status'],'comparable')
        finally:a.archive.close()


if __name__=='__main__':unittest.main()
