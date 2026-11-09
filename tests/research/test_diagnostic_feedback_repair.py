"""Read-only historical regression. No Provider, Worker, integration or Replay."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import types
import unittest

from schemas.platform import SessionInput
from tools.platform_store import Store,plain
from tools.state_io import digest
from tools.research.feedback import diagnostic_task_gap,task_gap
from tools.research.evidence_views import task_diagnosis,compact_task_diagnosis
from tools.research_tasks import task_adapter
from extensions.reference.passive_evaluation_v2 import metrics

ROOT=Path(__file__).resolve().parents[2]
STORE=ROOT/'runs/research/passive-base-only-full-autonomous-study-20261108-02'
REF=dict(artifact_id='d671cd6b1f7200b80fa98239c53fb4e4f5425f5cb7a3551fed445d3fdfb50543',media_type='application/json')


@unittest.skipUnless((STORE/'platform.sqlite').exists(),'Private original saved evidence is not installed')
class HistoricalDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store=Store(STORE);cls.result=cls.store.artifact(REF)
        cls.record=cls.result['structure_research']['records'][0]
        cls.adapter=task_adapter(cls.record['configuration'])
        cls.raw=cls.record['mechanics']['dynamic_execution']
        cls.task=SessionInput.model_validate(cls.record['configuration']).task
        cls.diagnostic=diagnostic_task_gap(cls.result,REF)

    def test_result75_complete_and_exact_historical_values(self):
        rows=self.diagnostic['constraints']
        self.assertEqual(self.diagnostic['status'],'complete');self.assertEqual(len(rows),251)
        expected=json.loads((ROOT/'docs/research/passive-study-review-20261109/result75-original-task-diagnostic.json').read_text())
        historical={r['name']:r['value'] for r in expected['diagnostic_measurements']}
        self.assertEqual(len(historical),251)
        for row in rows:
            self.assertAlmostEqual(row['observed_value'],historical[row['constraint_id'].removeprefix('evaluator:')],places=14)
            self.assertTrue(row['source_pointer']);self.assertEqual(row['source_reference'],REF)
            self.assertEqual(row['task_identity'],digest(self.task.model_dump(mode='json')))

    def test_missing_episode_and_window_are_partial_or_unavailable(self):
        raw={**self.raw,'episodes':self.raw['episodes'][1:]}
        d=self.adapter.diagnostic_task_gap(raw)
        self.assertEqual(d['status'],'partial')
        missing=[r for r in d['constraints'] if r['condition_id']==self.raw['episodes'][0]['load_condition']]
        self.assertTrue(all(r['observed_value'] is None and r['missing_reason'] for r in missing))
        self.assertEqual(self.adapter.diagnostic_task_gap({})['status'],'unavailable')
        raw={**self.raw,'episodes':deepcopy(self.raw['episodes'])}
        raw['episodes'][0]['samples']=[];raw['episodes'][0]['qualification_samples']=[]
        self.assertEqual(self.adapter.diagnostic_task_gap(raw)['status'],'partial')

    def test_formal_result_and_ranking_are_unchanged(self):
        before=digest(self.result);formal=plain(metrics(self.task,self.raw))
        self.assertEqual(formal['validity'],'invalid')
        self.assertEqual(formal['reason'],'DYNAMIC_STAGE_NOT_QUALIFIED:loaded')
        self.assertEqual(formal['constraints'],[])
        self.assertFalse(self.diagnostic['comparable']);self.assertIsNone(self.diagnostic['accepted'])
        self.assertIsNone(self.diagnostic['normalized_gap'])
        self.assertEqual(digest(self.result),before)
        self.assertEqual(self.store.artifact(REF),self.result)

    def test_formal_extractor_matches_original_on_saved_valid_result34(self):
        # Frozen original valid-grid nonsuccess used in the earlier manual audit.
        review=json.loads((ROOT/'docs/research/passive-study-review-20261109/result75-original-task-diagnostic.json').read_text())
        text=json.dumps(review)
        import re
        candidates=re.findall(r'[0-9a-f]{64}',text)
        original=types.ModuleType('extensions.reference._original_passive_evaluation')
        original.__package__='extensions.reference'
        source=subprocess.check_output(['git','show','8f5a1e7619134d1218f277629f7dce974cfc3f77:extensions/reference/passive_evaluation_v2.py'],cwd=ROOT).decode()
        exec(compile(source,'original-passive-evaluator','exec'),original.__dict__)
        # Read the exact reference named by the historical cross-check.
        for identity in candidates:
            try:value=self.store.artifact(dict(artifact_id=identity,media_type='application/json'))
            except ValueError:continue
            records=(value.get('structure_research') or {}).get('records',[])
            if not records or identity==REF['artifact_id']:continue
            record=records[0];raw=record.get('mechanics',{}).get('dynamic_execution')
            if raw is None:continue
            task=SessionInput.model_validate(record['configuration']).task
            old=original.metrics(task,raw)
            if old['validity']!='valid':continue
            self.assertEqual(plain(metrics(task,raw)),plain(old));return
        self.fail('Historical valid-grid cross-check result reference missing')

    def test_main_projection_has_numbers_and_no_trajectory(self):
        diagnosis=task_diagnosis(self.result,REF)
        compact=compact_task_diagnosis(diagnosis)
        self.assertEqual(diagnosis['diagnostic_status'],'complete')
        self.assertEqual(len(diagnosis['conditions']),11)  # ten loads plus no-contact
        self.assertTrue(compact['worst_constraints']);self.assertTrue(compact['metrics'])
        wire=json.dumps(compact)
        self.assertNotIn('qualification_samples',wire);self.assertNotIn('qpos_rad',wire)
        self.assertLess(len(wire),8000)


if __name__=='__main__':unittest.main()
