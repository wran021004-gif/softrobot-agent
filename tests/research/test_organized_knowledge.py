"""Nine historical cases and scoped delivery; offline Store/SDK fixtures only."""
import asyncio
from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
import httpx

from tools.platform_store import plain
from tools.research import core, experience, reporter
from tools.research.config import ROOT, resolve
from tools.research.contracts import ExperienceQuery, KnowledgePolicy
from tools.research.evidence_policy import registered_references
from tools.research.state import state, update
from tests.research.test_phs2d_knowledge_start import fixture
from tests.research.test_recent_round_tools import run_fixture

SPEC=ROOT/'configs/research/study_passive_knowledge_organized_v2.json'


def enable(h):
    new=resolve(SPEC);spec=deepcopy(state(h)['spec'])
    for key in ('knowledge','knowledge_manifest'):spec[key]=new[key]
    update(h,spec=spec)


@contextmanager
def organized_host():
    with fixture() as h:
        enable(h)
        from tests.research.test_research_authorization_preflight import approve
        from tools.research.contracts import REGISTERED_MATHEMATICS_SCOPE
        approve(h,[REGISTERED_MATHEMATICS_SCOPE])
        yield h


class OrganizedKnowledgeTests(unittest.TestCase):
    def test_nine_cases_categories_cross_references_and_legacy_scope(self):
        new=resolve(SPEC);rows=new['knowledge_manifest']['entries']
        self.assertEqual(Counter(r.get('type') for r in rows),
            Counter({'case':9,'general':9,'diagnostic':11,'validation':3,None:7}))
        identities={r['entry_id']+'@'+r['revision'] for r in rows}
        for row in rows:
            content=json.loads((ROOT/row['path']).read_bytes())['entries'][row['content_key']]
            fields=('id','type','summary','trigger','source_refs','evidence_level','applicability','limitations','related_skills') if row['resource_role']=='knowledge' else ('id','when_to_use','inputs','workflow','outputs','limitations','knowledge_refs')
            self.assertTrue(all(content.get(k) for k in fields),row['entry_id'])
            for key in ('knowledge_refs','related_skills'):
                self.assertFalse(set(content.get(key,[]))-identities,(row['entry_id'],key))
            if row.get('type')=='case':
                self.assertGreaterEqual(len(content['action_trace']),6)
                for step in content['action_trace']:
                    self.assertTrue(all(step.get(k) for k in ('action','observation','decision','decision_basis','hypothesis_update','direction_change','source_ref')))
            if row.get('type')=='diagnostic':
                self.assertGreaterEqual(len(content['hypotheses']),3)
                self.assertTrue(all(content.get(k) for k in ('symptom','discriminating_evidence','diagnostic_action','interpretation')))
        # New entries need explicit organization opt-in, even for new active Studies.
        legacy=experience.freeze_knowledge(KnowledgePolicy())['entries']
        self.assertFalse(any(r.get('introduced_in')=='typed_knowledge_v1' for r in legacy))
        self.assertNotIn('organization',plain(KnowledgePolicy()))
        self.assertNotIn('detail',plain(ExperienceQuery()))
        self.assertNotIn('type',plain(ExperienceQuery()))
        old=resolve(ROOT/'configs/research/study_passive_research_capabilities_v1.json')
        self.assertEqual(len(old['knowledge_manifest']['entries']),9)
        self.assertTrue(all(r['revision']=='1' or r['entry_id']=='passive-force-response-research' and r['revision']=='2'
            for r in old['knowledge_manifest']['entries']))

    def test_sdk_l0_summary_full_trace_and_separate_progress(self):
        with organized_host() as h:
            q=dict(operation='read',entry_id='phs2d-case',revision='2')
            with patch('tools.research.agent.credential',return_value='offline-fixture'):
                wires=run_fixture(h,[('experience_retrieve',dict(**q,detail='summary')),
                    ('experience_retrieve',q),None],limit=3)
            packets=[next(json.loads(m['content'].split('\n',1)[1])['research']
                for m in w['messages'] if isinstance(m.get('content'),str) and
                m['content'].startswith('CURRENT_RESEARCH_PACKET\n')) for w in wires]
            initial=packets[0]['knowledge'];catalogue=initial['catalogue']
            self.assertEqual({r['type'] for r in catalogue['types']},{'case','general','diagnostic','validation'})
            self.assertEqual(Counter(r['role'] for r in catalogue['capabilities']),Counter(skill=6,expert_process=1))
            for body_key in ('action_trace','physical_explanation','diagnostic_action','validation_experience'):
                self.assertNotIn(body_key,json.dumps(initial))
            receipts=[h.store.artifact(ref) for ref in state(h)['retrievals']]
            self.assertNotIn('action_trace',receipts[0]['results'][0]['content'])
            self.assertEqual(len(receipts[1]['results'][0]['content']['action_trace']),12)
            progress=experience.read_progress(h)['reads']
            self.assertTrue(next(r for r in progress if not r.get('detail'))['body_delivered'])
            self.assertFalse(next(r for r in progress if r.get('detail')=='summary')['body_delivered'])
            self.assertEqual(registered_references(h),[])
            self.assertEqual(state(h)['mathematical_evaluations'],0)
            self.assertEqual(h.store.remaining()['used']['backend_solves'],0)

    def test_separate_retrieval_and_no_history_design_evidence_bypass(self):
        from pydantic import ValidationError
        from tools.research.object_choices import reference_choices
        with organized_host() as h:
            for type,count in (('case',9),('general',9),('diagnostic',11),('validation',3)):
                page=experience.retrieve(h,dict(type=type))
                self.assertEqual(len(page['results']),count)
                self.assertTrue(all(row['type']==type for row in page['results']))
                self.assertTrue(all('content' not in row for row in page['results']))
            tracking=experience.retrieve(h,dict(type='case',task='tracking'))['results']
            self.assertEqual([r['entry_id'] for r in tracking],['m4-case'])
            for row in experience.entries(h):
                receipt=experience.retrieve(h,dict(operation='read',entry_id=row['entry_id'],revision=row['revision']))
                text=json.dumps(receipt['results'][0]['content'])
                for secret in ('artifact_id','platform.sqlite','model_xml_sha256','payout_lengths_m','P3_real9_E80_full8','<mujoco','D:\\\\softrobot-agent'):
                    self.assertNotIn(secret,text)
            historical=[r for r in experience._index_rows() if r.get('benchmark_sensitive')]
            self.assertEqual(len(historical),9)
            for original in historical:
                id=original['entry_id']
                self.assertEqual(experience.retrieve(h,dict(entry_id=id))['results'],[])
                with self.assertRaisesRegex(ValueError,'EXACT_EXPERIENCE_READ'):
                    experience.retrieve(h,dict(operation='read',entry_id=id,revision=original['revision']))
            # Stronger than a missing-file check: an artifact in the same Store
            # without current-run ownership must not be readable or advertised.
            with h.store.transaction() as db:
                foreign=plain(h.store.put(db,dict(synthetic_foreign_design='not scientific evidence')))
            with self.assertRaisesRegex(ValueError,'EVIDENCE_OUTSIDE_CURRENT_STUDY'):
                core.read_evidence(h,dict(reference=foreign))
            self.assertNotIn(foreign,reference_choices(h,include_all=True).values())
            with self.assertRaises(ValidationError):
                core.read_evidence(h,dict(reference='memory/cases/phs2d_passive_research_v1/success_trace.json'))
            ref=state(h)['retrievals'][-1]
            self.assertIn('query',core.read_evidence(h,dict(reference=ref),record_read=False))

    def test_reporter_scoped_reads_citations_saved_explanation_and_main_feedback(self):
        from tests.research.test_s129_agent_reporting import AgentReportingTests
        fixture_case=AgentReportingTests()
        fixture_case.setUpClass();fixture_case.setUp();self.addCleanup(fixture_case.doCleanups)
        h=fixture_case.h;enable(h);reference=fixture_case.physical()
        original=h.store.artifact(reference);known=registered_references(h);wires=[]
        result=reporter.investigate(h,dict(question='Explain tendon slack and competing causes.',references=[reference]))
        saved=h.store.artifact(result['report_reference'])
        refs=saved['request']['experience_receipts'];self.assertGreater(len(refs),0);self.assertLessEqual(len(refs),2)
        def respond(request):
            wire=json.loads(request.content);wires.append(wire);payload=json.loads(wire['messages'][-1]['content'])
            rows=[r for rec in payload['procedural_guidance'] for r in rec['results']]
            keys=[r['entry_id']+'@'+r['revision'] for r in rows]
            self.assertIn('diagnostic-slack@1',keys)
            content=dict(interpretations=[dict(kind='hypothesis',text='Offline fixture: slack is a competing explanation, not an observed unique cause.',source_ids=[next(iter(payload['source_catalog']))],knowledge_refs=['diagnostic-slack@1'])])
            self.assertFalse({ref['artifact_id'] for ref in refs}&{v['reference']['artifact_id'] for v in payload['source_catalog'].values()})
            return httpx.Response(200,json=dict(id='offline-knowledge-reporter',choices=[dict(index=0,finish_reason='stop',message=dict(role='assistant',content=json.dumps(content)))],usage=dict(prompt_tokens=10,completion_tokens=5,total_tokens=15)))
        asyncio.run(reporter.complete_reports(h,httpx.MockTransport(respond)))
        ref,final=reporter.entries(h)[-1]
        self.assertEqual(final['interpretation_status'],'available',final.get('error'))
        self.assertEqual(final['report']['results'],saved['report']['results'])
        self.assertEqual(h.store.artifact(reference),original)
        self.assertEqual(registered_references(h),known)
        delivered=reporter.reporter_handoff_summary(h,ref,final)
        self.assertEqual(delivered['interpretations'][0]['knowledge_refs'],['diagnostic-slack@1'])
        actual=core.read_evidence(h,dict(reference=ref,pointer='/report/interpretations'),record_read=False)
        self.assertEqual(actual[0]['kind'],'hypothesis')
        self.assertEqual(h.store.remaining()['used']['model_calls'],1)
        self.assertEqual(state(h).get('evaluation_reads',[]),[])
        self.assertEqual(state(h).get('mathematical_evaluations',0),0)
        # Replay only the validation boundary with a fabricated unread citation;
        # this is not another model request or a replacement scientific result.
        from types import SimpleNamespace
        request_event=next(e for e in reversed(h.store.events(h.run_id)) if e['kind']=='r3_request')
        payload=json.loads(wires[0]['messages'][-1]['content'])
        invalid=httpx.Response(200,json=dict(choices=[dict(finish_reason='stop',message=dict(content=json.dumps(
            dict(interpretations=[dict(kind='hypothesis',text='Offline invalid citation fixture.',
                source_ids=[next(iter(payload['source_catalog']))],knowledge_refs=['not-read@1'])]))))]))
        failed=reporter._finish(h,SimpleNamespace(last_request=request_event['request_id']),wires[0],invalid)
        self.assertEqual(h.store.artifact(failed)['error'],'REPORTER_KNOWLEDGE_NOT_READ')
        self.assertEqual(h.store.artifact(reference),original)
        self.assertEqual(h.store.remaining()['used']['model_calls'],1)
