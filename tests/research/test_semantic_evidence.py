"""Offline scientific discovery and actual SDK wire; no numerical execution."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator
from tools.research import agent,core
from tools.research.contracts import EvidenceIntentQuery, EvidenceReadQuery
from tools.research.state import state,update
from tools.research.object_choices import main_projection
from tests.research.test_p63c2_scientific_intent import question_host
from tests.research.test_p63a_math_interface import generate
from tests.research.test_recent_round_tools import run_fixture
from tests.research.test_information_flow import packet


def all_pages(h,q):
    pages=[]
    while q:
        page=core.read_tool_evidence(h,q);pages.append(page)
        q=page.get('next_query')
        if len(pages)>100:raise AssertionError('Pagination made no progress')
    return pages


class SemanticEvidenceTests(unittest.TestCase):
    def setUp(self):
        for name in ('tools.service_execution._run_contained','mujoco.mj_step',
                'extensions.tendon_family.mujoco_analysis.NativeModel'):
            p=patch(name,side_effect=AssertionError('NO_WORKER_OR_PHYSICS_ALLOWED'));p.start();self.addCleanup(p.stop)

    def host(self):
        h=question_host();c=generate(h);return h,c

    def test_active_structure_parameters_methods_and_raw_compatibility(self):
        h,c=self.host();before=deepcopy(state(h));used=h.store.remaining()
        for topic in ('structure','structure_parameters','task','mechanism_capabilities','mathematical_methods','mathematical_results'):
            pages=all_pages(h,dict(subject='current_candidate',topic=topic))
            self.assertTrue(all(not p['formal_read_credit'] for p in pages))
            self.assertTrue(all(p['subject']==c for p in pages))
            for page in pages:
                for source in page['sources']:core.read_evidence(h,source,record_read=False)
        rows=[r for p in all_pages(h,dict(subject=c,topic='structure_parameters')) for r in p['facts']]
        group=rows[0]['parameter_group']
        chosen=core.read_tool_evidence(h,dict(subject=c,topic='structure_parameters',group=group))
        self.assertTrue(all(r['parameter_group']==group for r in chosen['facts']))
        exact=core.read_tool_evidence(h,dict(reference=c,view='fields',pointer='/parameters',fields=['segment_count']),record_read=False)
        self.assertEqual(exact['segment_count'],2)
        self.assertEqual(state(h),before);self.assertEqual(h.store.remaining(),used)

    def test_unknown_ambiguous_foreign_and_mixed_queries(self):
        h,c=self.host()
        with self.assertRaises(ValueError):core.read_tool_evidence(h,dict(subject=c,topic='invented'))
        groups=core.read_tool_evidence(h,dict(subject=c,topic='structure_parameters',group='material'))
        self.assertEqual(groups['status'],'selection_required')
        self.assertTrue(groups['choices'])
        with self.assertRaisesRegex(ValueError,'NOT_REGISTERED_IN_STUDY'):
            core.read_tool_evidence(h,dict(subject=dict(artifact_id='f'*64),topic='structure'))
        with self.assertRaises(ValueError):EvidenceReadQuery.model_validate(dict(subject=c,topic='structure',pointer='/parameters'))
        for q in (dict(subject=c,topic='structure'),dict(reference=c,view='full')):
            EvidenceReadQuery.model_validate(q);Draft202012Validator(agent.evidence_query_schema(state(h)['spec'])).validate(q)

    def test_page_handle_pins_subject_scope_content_and_projection(self):
        h,c=self.host();q=dict(subject=c,topic='structure_parameters')
        first=core.read_tool_evidence(h,q);nxt=first['next_query']
        self.assertEqual(main_projection(h,nxt)['continuation'],nxt['continuation'])
        self.assertEqual(core.read_tool_evidence(h,nxt)['status'],'available')
        bad=deepcopy(nxt);bad['topic']='mathematical_methods'
        with self.assertRaisesRegex(ValueError,'SCOPE_MISMATCH'):core.read_tool_evidence(h,bad)
        bad=deepcopy(nxt);bad['continuation']['content_identity']='stale'
        with self.assertRaisesRegex(ValueError,'STALE_EVIDENCE'):core.read_tool_evidence(h,bad)
        bad=deepcopy(nxt);bad['continuation']['study_id']='other'
        with self.assertRaisesRegex(ValueError,'SCOPE_MISMATCH'):core.read_tool_evidence(h,bad)

    def test_actual_main_schema_feedback_and_sdk_resume(self):
        h,c=self.host()
        q=dict(subject=c,topic='structure_parameters')
        nxt=core.read_tool_evidence(h,q)['next_query']
        wires=run_fixture(h,[('evidence_read',q),('evidence_read',nxt),('evidence_read',dict(subject=c,topic='mathematical_methods')),None])
        schema=next(t['function']['parameters'] for t in wires[0]['tools'] if t['function']['name']=='evidence_read')
        self.assertIn('EvidenceIntentQuery',schema['$defs'])
        for wire in wires:
            self.assertIn('scientific_queries',packet(wire)['evidence_access'])
        self.assertIn('evidence_continuation_v1',json.dumps(wires[1]))
        self.assertIn('semantic_evidence_v1',json.dumps(wires[1]))
        self.assertNotIn('SCOPE_MISMATCH',json.dumps(wires))
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)

    def test_passive_v2_registered_mechanisms_and_v4_preparation(self):
        from tests.research.test_passive_program_v2 import prepared_host_v2
        from tools.research.scientific_intent import question_schema
        h,c=prepared_host_v2(mathematical_budget=5)
        structure=all_pages(h,dict(subject=c,topic='structure'))
        facts={k:v for p in structure for k,v in p['facts'].items()}
        self.assertEqual(len(facts['fixed_payout_lengths_m']),1)
        mechanisms=all_pages(h,dict(subject=c,topic='mechanism_capabilities'))
        facts={k:v for p in mechanisms for k,v in p['facts'].items()}
        self.assertIn('finite_time_response',facts)
        self.assertEqual(facts['finite_time_response']['effect_semantics'],'finite_time_task_response')
        primitives=all_pages(h,dict(subject=c,topic='mechanism_capabilities',group='primitives'))
        self.assertIn('constraint_length_residual',{k for p in primitives for k in p['facts']})
        params=[r for p in all_pages(h,dict(subject=c,topic='structure_parameters')) for r in p['facts']]
        self.assertTrue(any(r['selectable'] for r in params))
        self.assertEqual(state(h)['spec']['research_decisions']['analysis_interface'],'scientific_question_v4')
        self.assertIn('structure',question_schema(state(h)['spec'],host=h)['properties'])
        used=h.store.remaining()['used'];self.assertEqual(used['backend_solves'],0)
        self.assertEqual(state(h)['mathematical_evaluations'],0)


if __name__=='__main__':unittest.main()
