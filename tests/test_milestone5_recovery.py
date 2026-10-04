"""Focused saved-receipt, accepted-decision and alignment/accounting checks."""
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace
import json
import subprocess
import unittest
import numpy as np
from examples import milestone5_preparation as prep
from examples import milestone5_recovery as recovery
from tools.state_io import read
from extensions.tendon_family.milestone5_recovery import vector_accounting


class DecisionStore:
    def __init__(self,decisions):
        self.values=decisions
        self.receipts=[dict(execution_status='completed',tool_id=prep.RESEARCH.extension_id,output=dict(artifact_id='receipt-'+k,media_type='application/json')) for k in decisions]
    @contextmanager
    def connect(self,*args):
        yield SimpleNamespace(execute=lambda *args:[(json.dumps(r),) for r in self.receipts])
    def artifact(self,ref):
        key=ref['artifact_id']
        if key.startswith('receipt-'):return dict(reference=dict(artifact_id=key[8:],media_type='application/json'))
        return deepcopy(self.values[key])


class RecoveryTests(unittest.TestCase):
    def test_completed_receipts_bind_and_need_no_new_reservation(self):
        registration=read(prep.RUN/'registration.json');accounting=read(prep.RUN/'accounting.json');before=prep.Store(prep.RUN).remaining()
        completed=[]
        for name,weight in [('history075',.075),('history15',.15)]:
            cfg=deepcopy(registration['development_configuration']);cfg['policy']['controller']['parameters']['data']['recipe']['holding_tip_speed_weight']=weight
            p=dict(operation='history',configuration=cfg,initial_state=registration['development_initial_state'],allowance_s=1200.)
            self.assertTrue(prep.completed_calculation(name,p)['result']['complete']);completed.append(name)
            bad=deepcopy(p);bad['initial_state'][0]+=.001
            with self.assertRaisesRegex(ValueError,'PROTOCOL_MISMATCH'):prep.completed_calculation(name,bad)
        admission=prep.recovery_admission(registration,completed,before['remaining'],accounting['numerical_work'])
        self.assertTrue(admission['passed']);self.assertEqual(admission['required_solves'],0);self.assertEqual(admission['required_wall_s'],660.)
        missing=prep.recovery_admission(registration,[],before['remaining'],accounting['numerical_work'])
        self.assertFalse(missing['passed']);self.assertEqual(missing['required_wall_s'],3060.)
        self.assertEqual(before,prep.Store(prep.RUN).remaining())

    def test_common_finalization_requires_actual_accepted_decisions(self):
        registration=read(prep.RUN/'registration.json');reference=read(prep.RUN/'reference.json');selection=dict(holding_weights=[.075,.15],rationale='Historical supported provisional pair, deferred screening')
        p=prep.protocol(registration,selection,reference)
        self.assertIn('implementation_identity',p);self.assertFalse(p['research_pair_selected']);self.assertFalse(p['research_interpretation_complete'])
        decisions={phase:dict(phase=phase,**selection) for phase in ('selection','interpretation')};store=DecisionStore(decisions)
        refs={k:dict(artifact_id=k,media_type='application/json') for k in decisions}
        complete=prep.protocol(registration,selection,reference,research_store=store,decision_refs=refs,supersedes='old blocked protocol')
        self.assertTrue(complete['research_pair_selected']);self.assertTrue(complete['research_interpretation_complete']);self.assertEqual(complete['supersedes'],'old blocked protocol')
        self.assertFalse(complete['ready_for_bounded_prospective_experiment'])
        store.receipts=[]
        with self.assertRaisesRegex(ValueError,'ACCEPTED_RESEARCH_RECEIPT_REQUIRED'):prep.protocol(registration,selection,reference,research_store=store,decision_refs=refs)
        from examples.milestone5_future_validation import readiness
        p.pop('research_pair_selected');self.assertFalse(readiness(p)['passed'])

    def test_saved_alignment_and_substitution_arithmetic(self):
        alignment=read(recovery.RUN/'align.json')['result'];comparison=read(recovery.RUN/'compare.json')['result']
        for case,comp in zip(alignment['cases'],comparison['cases']):
            self.assertEqual(len(case['rows']),35)
            for i,row in enumerate(case['rows']):
                self.assertAlmostEqual(row['start_s'],i*.01);self.assertAlmostEqual(row['end_s'],(i+1)*.01)
                self.assertEqual(row['observation_s'],row['command_application_s']);self.assertEqual(row['actual_one_step']['applied_tension_n'],row['actual_input_n'])
                self.assertAlmostEqual(np.linalg.norm(np.asarray(row['preview_endpoint']['velocity_m_s'])-row['observed_endpoint']['velocity_m_s']),row['preview_vector_error_m_s'])
                self.assertEqual(row['holding'],i>=29)
            outputs=comp['outputs'];self.assertLess(comp['coarse_reproduction']['state_max'],1e-7);self.assertTrue(outputs['D']['reused']);self.assertEqual(outputs['D']['new_charge'],0)
            recalculated=vector_accounting(*(outputs[k]['endpoint'] for k in 'ABCD'),comp['observed'])
            self.assertEqual(recalculated,comp['ordered_accounting'])
            for value in recalculated.values():self.assertLess(value['identity_residual'],1e-12)

    def test_production_defaults_and_public_reservations_unchanged(self):
        for name in ('extensions/tendon_family/gvs_nmpc.py','extensions/tendon_family/gvs_trajectory.py','extensions/tendon_family/diagnostic_math.py','extensions/tendon_family/gvs_projection.py','tools/batch_budget.py'):
            saved=subprocess.check_output(['git','show','HEAD:'+name],cwd=prep.ROOT)
            self.assertEqual(saved.replace(b'\r\n',b'\n'),(prep.ROOT/name).read_bytes().replace(b'\r\n',b'\n'))
        self.assertEqual(prep.reservations()['complete_requirement']['wall_s'],5830.)


if __name__=='__main__':unittest.main()
