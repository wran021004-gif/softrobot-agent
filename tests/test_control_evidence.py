"""Small deterministic checks: saved evidence, missing history and phase/input alignment."""
import unittest
from pathlib import Path
from copy import deepcopy
from tools.platform_store import Store
from extensions.tendon_family.control_evidence import (
    ControlEvidence,EvidenceQuery,ExecutionComparison,aligned_interval_predictions)

ROOT=Path(__file__).resolve().parents[1]
EXECUTION='f9b8c232a576465ab5ef1ca92658faad'


class EvidenceTests(unittest.TestCase):
    def test_deadline_horizon_and_exact_shifted_warm_prefix(self):
        from extensions.tendon_family.gvs_nmpc import deadline_horizon,DeadlineReachNMPCController,GVSNMPCController
        from types import SimpleNamespace
        from unittest.mock import patch
        self.assertEqual(deadline_horizon(.35,.25,.01,10),10)
        self.assertEqual(deadline_horizon(.35,.26,.01,10),9)
        self.assertEqual(deadline_horizon(.35,.34,.01,10),1)
        with self.assertRaises(ValueError):deadline_horizon(.35,.345,.01,10)
        from extensions.tendon_family.contracts import GVSTrajectoryParameters
        c=DeadlineReachNMPCController.__new__(DeadlineReachNMPCController)
        c.parameters=GVSTrajectoryParameters(horizon=10);c.period_s=.01;c.seed=None
        c.plan={'task':{},'robot':{}}
        old=SimpleNamespace(duration=.35,parameters=c.parameters,nominal_x=[0,0],nominal_u=[1],
            last=dict(states=[[i] for i in range(11)],tensions=[[i] for i in range(10)]))
        c.workspace=old;c.last={};c.observations=[{}]
        def command(controller,*args):
            self.assertEqual(controller.seed,dict(states=[[1],[2]],tensions=[[1]]))
            return [1]
        with patch('extensions.tendon_family.gvs_nmpc.TaskDefinition.model_validate',return_value=None), \
             patch('extensions.tendon_family.gvs_nmpc.RobotDescription.model_validate',return_value=None), \
             patch('extensions.tendon_family.gvs_nmpc.TrajectoryWorkspace',return_value=SimpleNamespace()), \
             patch.object(GVSNMPCController,'command',command):
            self.assertEqual(c.command(.34,{},[],[]),[1])
        self.assertEqual(c.last['effective_horizon'],1)

    def test_saved_execution_missing_plans_are_not_regenerated(self):
        store=Store(ROOT/'runs/stage340_bounded_autonomous_20261001')
        if not store.db.exists():self.skipTest('local-only sealed historical ledger absent')
        result=ControlEvidence(store).query(EvidenceQuery(execution_id=EXECUTION,operation='prediction',update_ids=[0,4,34]))
        self.assertEqual(result.observations['initialization_selected'],9)
        self.assertEqual(len(result.observations['aligned_intervals']),3)
        self.assertEqual(len(result.capabilities['missing']),3)
        self.assertNotIn('plans',result.observations['updates'][0])
        comparison=ControlEvidence(store).compare(ExecutionComparison(baseline_execution_id=EXECUTION,
            variant_execution_id=EXECUTION,changed_factor='recording'))
        self.assertTrue(comparison['comparable'])
        self.assertEqual(comparison['baseline'],comparison['variant'])
        with self.assertRaisesRegex(ValueError,'MANIFEST_OWNERSHIP'):
            ControlEvidence(store).query(EvidenceQuery(execution_id=EXECUTION,
                export_manifest=dict(artifact_id='0'*64,media_type='application/json')))

    def test_recorded_baseline_variant_conditions(self):
        baseline=Store(ROOT/'runs/stage340_bounded_autonomous_20261001')
        variant=Store(ROOT/'runs/stage341_control_evidence_20261001/validation')
        if not baseline.db.exists() or not variant.db.exists():self.skipTest('local-only sealed comparison ledgers absent')
        request=ExecutionComparison(baseline_execution_id=EXECUTION,
            variant_execution_id='83796acafa72407492689c1275f9f460',changed_factor='controller')
        reader=ControlEvidence(baseline);result=reader.compare(request,ControlEvidence(variant))
        self.assertTrue(result['comparable']);self.assertEqual(result['material_mismatches'],['controller'])
        self.assertLess(result['variant']['terminal_error_m'],result['baseline']['terminal_error_m'])
        wrong=reader.compare(request.model_copy(update={'changed_factor':'recording'}),ControlEvidence(variant))
        self.assertFalse(wrong['comparable'])

    def test_alignment_requires_next_timestamp_and_actual_command(self):
        update=dict(time_s=.1,phase='current_state_before_integration',tip_position_m=[0,0,0],actual_tension_n=[1.],
            one_step_prediction=dict(time_s=.11,frame='world',applied_tension_n=[1.],tip_position_m=[.01,0,0]))
        rows=[dict(time_s=.11,tip_m=[.012,0,0])];commands=[dict(time_s=.1,desired_tension_n=[1.])]
        good,missing=aligned_interval_predictions(rows,[update],commands,.01,[.02,0,0],[0])
        self.assertFalse(missing);self.assertAlmostEqual(good[0]['tip_difference_m'],.002)
        self.assertLess(good[0]['actual_error_change_m'],0)
        for change in ('time','input','phase'):
            bad=deepcopy(update)
            if change=='time':bad['one_step_prediction']['time_s']=.2
            elif change=='input':bad['actual_tension_n']=[2.]
            else:bad['phase']='post_step'
            good,missing=aligned_interval_predictions(rows,[bad],commands,.01,[.02,0,0],[0])
            self.assertFalse(good);self.assertTrue(missing)


if __name__=='__main__':unittest.main()
