"""Exact recorded NMPC command handoff; no rollout, optimizer or PPO training."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from tools.research import rl
from tools.research.contracts import RLRequest
from tools.research.state import state, save, update
from tools.state_io import digest
from tests.research.test_s127_math_admission import candidate_fixture


class RLHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.h,cls.candidate=candidate_fixture()

    def setUp(self):
        h=self.h;self.cfg=h.store.artifact(self.candidate)['configuration']
        self.order=[t['id'] for t in self.cfg['robot']['structure']['data']['tendons']]
        self.period=self.cfg['task']['timing']['control_period_s'];self.steps=round(self.cfg['task']['timing']['duration_s']/self.period)
        self.observations=[dict(time_s=i*self.period,phase='current_state_before_integration',actual_tension_n=[.2]*len(self.order),predicted_tension_n=[999.]*len(self.order)) for i in range(self.steps)]
        metadata=save(h,dict(solver_status='completed'))
        self.source=dict(metadata=metadata,configuration=deepcopy(self.cfg),owner=h.run_id,
            files={'controller_observations.json':metadata})
        self.result=save(h,dict(status='evaluated',candidate=self.candidate,execution_id='synthetic-recorded-fixture',owning_study=h.run_id,
            acceptance=dict(accepted=False),execution=dict(receipts=dict(simulation=dict(execution_id='synthetic-recorded-fixture',output=metadata)))))
        update(h,results=[self.result],mechanics_results=[],compatible_residual_references=[])

    def references(self):
        from extensions.tendon_family.control_evidence import ControlEvidence
        with patch.object(ControlEvidence,'resolve',return_value=self.source),patch.object(ControlEvidence,'read_file',return_value=self.observations):
            return rl.compatible_references(self.h)

    def test_failed_complete_nmpc_uses_measured_inputs_and_no_repeat_execution(self):
        before=self.h.store.remaining();refs=self.references();self.assertTrue(refs[0]['available'])
        self.assertEqual(refs[0]['command_origin'],'measured_applied_interval_inputs')
        import numpy as np
        with np.load(refs[0]['reference']['path']) as data:self.assertTrue(np.all(data['saved_tensions_n']==.2))
        self.assertEqual(rl.compatible_references(self.h,publish=False),refs)
        self.assertEqual(self.references(),refs);self.assertEqual(self.h.store.remaining(),before)
        request=RLRequest(operation='start',candidate=self.candidate,mode='residual',reference=refs[0]['reference'],rationale='Fixture typed admission only')
        self.assertEqual(request.mode,'residual')

    def test_bad_grid_bounds_missing_actual_and_candidate_are_rejected(self):
        original=deepcopy(self.observations)
        cases=[original[:-1],list(reversed(original)),[dict(r,time_s=0.) for r in original],
            [dict(r,time_s=float('nan')) for r in original],[dict(r,phase='post_step') for r in original],
            [dict(r,actual_tension_n=[float('nan')]*len(self.order)) for r in original],
            [dict(r,actual_tension_n=[999.]*len(self.order)) for r in original],
            [{k:v for k,v in r.items() if k!='actual_tension_n'} for r in original]]
        for observations in cases:
            with self.subTest(case=str(observations[:1])):
                self.observations=observations;self.assertFalse(any(r['available'] for r in self.references()))
        self.observations=original;self.source['configuration']['task']['timing']['duration_s']+=.01
        self.assertFalse(any(r['available'] for r in self.references()))

    def test_new_result_refresh_and_direct_entry_without_any_reference(self):
        self.assertFalse(rl.compatible_references(self.h,publish=False))
        request=RLRequest(operation='start',candidate=self.candidate,mode='direct',rationale='Direct does not require NMPC')
        self.assertIsNone(request.reference)
        with self.assertRaisesRegex(ValueError,'RESIDUAL_REQUIRES_REFERENCE'):
            RLRequest(operation='start',candidate=self.candidate,mode='residual',rationale='Missing reference')
        self.assertTrue(self.references()[0]['available'])


if __name__=='__main__':unittest.main()
