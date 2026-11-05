"""Directed successor contracts. SDK replies and failure records are fixtures."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from tools.research import experience
from tools.research.config import ROOT, resolve
from tools.research.contracts import REGISTERED_MATHEMATICS_SCOPE
from tools.research.evidence_policy import registered_references
from tools.research.state import state, update, save
from tests.research.test_phs2d_knowledge_start import fixture
from tests.research.test_recent_round_tools import run_fixture
from tests.research.test_research_authorization_preflight import approve


class PhsSuccessorTests(unittest.TestCase):
    def test_protected_closeout_reads_only_frozen_opportunity_view(self):
        from tools.research.core import read_evidence
        from tools.research.evidence_intent import resolve_evidence_intent
        with fixture() as h:
            anchor=state(h)['family_space_reference'];before=h.store.remaining()['used']
            with patch('tools.research.core.protected',return_value=True):
                review=resolve_evidence_intent(h,dict(subject='current_task',topic='research_opportunities',detail_level='evidence_review'))
                self.assertEqual(review['facts']['version'],'research_opportunity_review_v1')
                detail=read_evidence(h,dict(reference=anchor,view='working_set',pointer='/research_opportunities/decision_rule'),record_read=False)
                self.assertIn('Main chooses',detail)
                with self.assertRaisesRegex(ValueError,'PROTECTED_EVIDENCE_READ_REQUIRES'):
                    resolve_evidence_intent(h,dict(subject='current_task',topic='task'))
                wrong=save(h,dict(scope='Offline non-anchor fixture'))
                with self.assertRaisesRegex(ValueError,'PROTECTED_EVIDENCE_READ_REQUIRES'):
                    read_evidence(h,dict(reference=wrong,view='working_set',pointer='/research_opportunities'),record_read=False)
            self.assertEqual(h.store.remaining()['used'],before)
            self.assertEqual(state(h)['mathematical_evaluations'],0)

    def test_sdk_delivers_process_once_and_reads_case_without_science_credit(self):
        new=resolve(ROOT/'configs/research/study_phs2d_mechanism_successor_20261105.json')
        with fixture() as h:
            spec=deepcopy(state(h)['spec'])
            for key in ('knowledge','knowledge_manifest'):spec[key]=new[key]
            update(h,spec=spec)
            approve(h,[REGISTERED_MATHEMATICS_SCOPE])
            query=dict(operation='read',entry_id='phs2d-research-process',revision='1')
            with patch('tools.research.agent.credential',return_value='offline-fixture'):
                wires=run_fixture(h,[('experience_retrieve',query),None],limit=2)
            first=json.dumps(wires[0]);second=json.dumps(wires[1])
            self.assertIn('Early research could not qualify its unloaded baseline',first)
            self.assertIn('Codex/operator',first)
            packet=next(json.loads(m['content'].split('\n',1)[1]) for m in wires[1]['messages']
                if isinstance(m.get('content'),str) and m['content'].startswith('CURRENT_RESEARCH_PACKET\n'))
            self.assertNotIn('expert_process',packet['research']['knowledge']['access'] or {})
            self.assertIn('The early campaign exhausted its allowance',second)
            progress=experience.hint_progress(h)
            self.assertEqual(sum(r['evidence_role']=='confirmed_expert_process_delivery_only' for r in progress),1)
            self.assertTrue(experience.read_progress(h)['reads'][0]['body_delivered'])
            from tools.research.object_choices import main_projection
            receipt=experience.read_progress(h)['reads'][0]['read_receipt']
            binding=experience.disposition_bindings(h,{main_projection(h,receipt):'context_only'})[0]
            self.assertEqual(binding['read_receipt'],receipt)
            summary=experience.disposition_bindings(h,{'summary:phs2d-research-process@1':'context_only'})[0]
            self.assertFalse(summary['full_read'])
            with self.assertRaisesRegex(ValueError,'DISPOSITION_REQUIRES_EXACT_ACTUAL_READ'):
                experience.disposition_bindings(h,{main_projection(h,state(h)['family_space_reference']):'adopted'})
            body=experience.retrieve(h,query)['results'][0]['content']
            self.assertEqual(len(body['trace']),7)
            for key in ('sources','final_result','parameters','payout_lengths_m','label'):
                self.assertNotIn(key,body)
            self.assertFalse(experience.retrieve(h,dict(entry_id='phs2d-passive-research'))['results'])
            self.assertFalse(new['knowledge']['allow_benchmark_answers'])
            self.assertEqual(registered_references(h),[])
            self.assertEqual(state(h)['mathematical_evaluations'],0)
            self.assertEqual(h.store.remaining()['used']['backend_solves'],0)

    def test_cross_candidate_blocker_and_stop_review_do_not_prescribe_experiment(self):
        from tools.research.research_context import initialization_review
        with fixture() as h:
            candidates=[];analyses=[]
            for i in range(2):
                ref=save(h,dict(physical_design_identity='synthetic-design-'+str(i)))
                candidates.append(ref)
                analyses.append(save(h,dict(candidate=ref,requested_operation=dict(mechanism_study=dict(
                    operation='inspect',target=dict(quantity='constraint_active_set'),effect_semantics='mechanism_effect')),
                    structure_research=dict(qualification_diagnosis=dict(status='numerically_unresolved',qualified=False,
                        failure_layers=['KKT_not_qualified'])))))
            update(h,analysis_results=analyses,plans=[save(h,dict(original_plan=dict(action='diagnose')))])
            review=initialization_review(h)
            self.assertTrue(review['repeated_block'])
            self.assertEqual(review['distinct_failed_designs'],2)
            self.assertTrue(any(not row['requested'] for row in review['research_directions']))
            self.assertEqual(experience.decision_phase(h)['phase'],'initialization_failure_review')
            update(h,pilot={**state(h)['pilot'],'tool_route':save(h,dict(tool='research_plan',action='stop'))})
            self.assertEqual(experience.decision_phase(h)['phase'],'voluntary_stop')
            self.assertEqual(state(h)['research_status'],'ready')
            self.assertEqual(state(h)['mathematical_evaluations'],0)


if __name__=='__main__':unittest.main()
