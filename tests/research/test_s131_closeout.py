"""Saved F3 observations and projection regressions; no scientific execution."""
from copy import deepcopy
import json
import math
from pathlib import Path
import unittest
from tools.state_io import digest
from tools.research.research_context import current_evidence_corrections

ROOT=Path(__file__).resolve().parents[2]
FOLDER=ROOT/'evidence/f3_formal/closeout_20261023'


class CloseoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit=json.loads((FOLDER/'audit.json').read_text(encoding='utf-8'))
        cls.artifacts=json.loads((FOLDER/'artifacts.json').read_text(encoding='utf-8'))

    def artifact(self,key):
        return self.artifacts[self.audit['references'][key]['artifact_id']]

    def test_exported_identity_schedule_and_saved_acceptance(self):
        for key,value in self.artifacts.items():self.assertEqual(digest(value),key)
        source=self.artifact('source')['trajectory'];raw=self.artifact('raw')
        self.assertEqual(len(source['tensions_n']),35)
        self.assertEqual([r['actual_tension_n'] for r in raw['samples'][1:]],source['tensions_n'])
        candidate=self.artifact('candidate');task=candidate['configuration']['task']
        target=task['goal']['data']['target_m']
        errors=[math.dist(r['tip_m'],target) for r in raw['samples']]
        self.assertAlmostEqual(errors[-1],self.audit['metrics']['terminal_error_m'],places=14)
        hold=[r for r in raw['samples'] if r['time_s']>=.3-1e-12]
        self.assertEqual(len(hold),6)
        self.assertEqual(max(r['position_error_m'] for r in hold),self.audit['metrics']['holding_max_error_m'])
        self.assertTrue(self.artifact('selected')['acceptance']['accepted'])
        self.assertNotEqual(source['tensions_n'][0],source['tensions_n'][1])
        self.assertEqual(source['tensions_n'][30:],[source['tensions_n'][30]]*5)

    def test_current_corrections_preserve_predicates_and_replace_inferences(self):
        old=self.artifact('correction');before=deepcopy(old)
        ref=self.audit['references']['correction'];new=current_evidence_corrections(old,ref)
        self.assertEqual(old,before)
        self.assertEqual(new['full_history_query'],dict(reference=ref,pointer='',view='full'))
        original=new['mathematics'][0]['summary']
        self.assertIs(original['original_feasible'],False)
        self.assertIn('not a proof of infeasibility',new['mathematics'][0]['current_conclusion'])
        residuals=original['original_predicate_diagnostics']['recomputed']['maxima_by_constraint']
        self.assertTrue(any(0<r['positive_violation']<2e-14 and r['unit']=='m/s' for r in residuals))
        for row in new['historical_control_updates']:
            self.assertFalse(row['prediction_aggregate_available'])
            self.assertFalse(row['terminal_update']['failure_response_used'])
            self.assertTrue(row['terminal_update']['prediction_shape_invalid'])
            self.assertIn('distinct from fallback',row['current_conclusion'])
        self.assertEqual(new['reporter_saved_output_revalidation'],old['reporter_saved_output_revalidation'])
        self.assertLess(len(json.dumps(new)),len(json.dumps(old)))
        self.assertEqual(self.audit['sqlite_sha256_before'],self.audit['sqlite_sha256_after'])


if __name__=='__main__':unittest.main()
