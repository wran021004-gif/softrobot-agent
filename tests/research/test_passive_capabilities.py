"""Integration fixtures are offline; no autonomous or physical success is claimed."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
from tools.research import experience
from tools.research.config import ROOT, resolve, role_provider
from tools.research.state import state, update
from tools.research.contracts import REGISTERED_MATHEMATICS_SCOPE
from tools.research.evidence_policy import registered_references
from tests.research.test_phs2d_knowledge_start import fixture
from tests.research.test_recent_round_tools import run_fixture
from tests.research.test_research_authorization_preflight import approve

SPEC=ROOT/'configs/research/study_passive_research_capabilities_v1.json'


class PassiveKnowledgeTests(unittest.TestCase):
    def test_sdk_catalogue_exact_read_and_progress_without_answers(self):
        new=resolve(SPEC)
        with fixture() as h:
            spec=deepcopy(state(h)['spec'])
            for key in ('knowledge','knowledge_manifest'):
                spec[key]=new[key]
            spec['research_decisions']['role_policy']=new['research_decisions']['role_policy']
            update(h,spec=spec)
            approve(h,[REGISTERED_MATHEMATICS_SCOPE])
            query=dict(operation='read',entry_id='passive-structure-mechanics',revision='1')
            with patch('tools.research.agent.credential',return_value='offline-fixture'):
                wires=run_fixture(h,[('experience_retrieve',query),None],limit=2)
            packets=[next(json.loads(m['content'].split('\n',1)[1])['research']
                for m in wire['messages'] if isinstance(m.get('content'),str)
                and m['content'].startswith('CURRENT_RESEARCH_PACKET\n')) for wire in wires]
            catalogue=packets[0]['knowledge']['catalogue']
            self.assertEqual(sum(r['entry_id'].startswith('skill-') for r in catalogue),6)
            self.assertIn(('passive-force-response-research','2'),[(r['entry_id'],r['revision']) for r in catalogue])
            self.assertIn('expert_process',packets[0]['knowledge']['access'])
            self.assertNotIn('expert_process',packets[1]['knowledge']['access'] or {})
            self.assertNotIn('Chord',json.dumps(packets[0]['knowledge']))
            self.assertTrue(experience.read_progress(h)['reads'][0]['body_delivered'])
            self.assertEqual(packets[0]['knowledge']['reporter_role']['reasoning'],'medium')
            body=experience.retrieve(h,query)['results'][0]['content']
            self.assertGreaterEqual(len(body['topics']),10)
            self.assertTrue(all(r['evidence_grade'] and r['source'] for r in body['topics']))
            for entry in ('phs2d-passive-research','p3-passive-progressive-stiffness'):
                self.assertFalse(experience.retrieve(h,dict(entry_id=entry))['results'])
            self.assertEqual(registered_references(h),[])
            self.assertEqual(state(h)['mathematical_evaluations'],0)
        old=resolve(ROOT/'configs/research/study_phs2d_topology_successor_20261106.json')
        self.assertEqual(role_provider(old,old['runtime']['provider'],'reporter')['reasoning'],'none')
        self.assertEqual(role_provider(new,new['runtime']['provider'],'main')['reasoning'],'medium')


if __name__=='__main__':unittest.main()
