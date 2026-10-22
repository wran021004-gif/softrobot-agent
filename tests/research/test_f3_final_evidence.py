"""Read-only verification of saved real evidence and the unapproved F3 draft."""
import hashlib
from types import SimpleNamespace
import unittest
from tools.state_io import read
from tools.platform_store import encode
from tools.research.config import ROOT,resolve
from tools.research.state import require_authorization


class FinalEvidenceTests(unittest.TestCase):
    def test_all_exported_artifacts_keep_exact_store_identities(self):
        artifacts=read(ROOT/'evidence/f3_prestudy/artifacts.json')
        for identity,value in artifacts.items():
            self.assertEqual(hashlib.sha256(encode(value).encode('utf-8')).hexdigest(),identity)
        audit=read(ROOT/'evidence/f3_prestudy/real_socp_audit.json')
        result=artifacts[audit['result_reference']['artifact_id']]
        self.assertEqual(result,read(ROOT/'evidence/f3_prestudy/real_socp_result.json'))
        self.assertEqual(audit['charged_evaluations'],2)
        self.assertEqual(audit['reserved_evaluations'],2)
        self.assertEqual(audit['attempt_boundaries'],dict(model_build=1,capability=1,dual_face=0))
        self.assertTrue(audit['replay']['numerically_valid'])
        self.assertLess(audit['gap'],1e-8)
        self.assertEqual(audit['worker_runtime']['threads'],
            dict(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1'))
        self.assertEqual(audit['task_acceptance'],'unmeasured')
        self.assertEqual(audit['ledger']['used']['model_calls'],0)
        self.assertEqual(audit['ledger']['used']['backend_solves'],0)
        delivery=read(ROOT/'evidence/f3_prestudy/deterministic_delivery.json')
        self.assertEqual(delivery['operation_reuse']['additional_analysis_evaluations'],0)
        handoff=read(ROOT/'evidence/f3_prestudy/control_handoff.json')
        self.assertFalse(handoff['physical_execution'])
        source=artifacts[handoff['result']['result']['source']['artifact_id']]
        self.assertEqual(source,handoff['source'])
        self.assertEqual(source['task_acceptance'],'unmeasured')
        self.assertFalse(source['inherited_acceptance'])

    def test_pending_draft_preserves_original_science_and_cannot_execute(self):
        spec=resolve(ROOT/'configs/research/study_f3_pending.json')
        original=resolve(ROOT/'configs/research/study_s125_cold.json')
        for key in ('canonical_task','canonical_task_identity','family_space','family_space_identity'):
            self.assertEqual(spec[key],original[key])
        self.assertEqual(len(spec['family_sensitivity_variables']['variables']),18)
        self.assertFalse((ROOT/'runs/research'/spec['study_id']).exists())
        host=SimpleNamespace(run_id=spec['study_id'],store=SimpleNamespace(
            session=lambda _:dict(state=dict(spec=spec)),events=lambda _:[]))
        with self.assertRaisesRegex(ValueError,'INDEPENDENT_FORMAL_STUDY_APPROVAL_REQUIRED'):
            require_authorization(host)

    def test_final_binding_is_resolved_without_study_creation(self):
        from tests.research.f3_draft_binding import bind
        output=ROOT/'runs/f3-binding-offline-check.json'
        bound=bind(output,require_clean=False)
        spec=resolve(bound['configuration'])
        self.assertEqual(spec['base_commit'],bound['commit'])
        self.assertEqual(spec['resolved_identity'],bound['resolved_identity'])
        self.assertFalse(bound['study_created'])


if __name__=='__main__':unittest.main()
