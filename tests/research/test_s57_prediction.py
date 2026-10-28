"""Saved evidence and fabricated worker-boundary fixtures; no engines or physics."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import gc
import shutil
import subprocess
from uuid import uuid4
import unittest
from unittest.mock import patch

import numpy as np

from tools.research import nmpc_prediction_diagnostic as diagnostic
from tools.research import mechanics
from tools.research.contracts import NMPCPredictionDiagnostic
from tools.research.state import state, update, core_hashes
from tools.state_io import read, atomic_json
from tools.research import core
from tools.platform_store import ProjectConfig

ROOT=Path(__file__).resolve().parents[2]
FOLDER='evidence/sorosim_s56/physics/study'
REF=read(ROOT/'evidence/sorosim_s56/physics/summary.json')['nmpc']


class ArchivedPredictionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.index=diagnostic.archive_index(FOLDER,REF)

    def test_archive_only_alignment_and_applied_action(self):
        with patch.dict('sys.modules',{'mujoco':None,'matlab.engine':None}):
            index=diagnostic.archive_index(FOLDER,REF)
        self.assertEqual(index['new_physical_steps'],0)
        self.assertEqual(index['tendon_order'],['tendon_0','tendon_1','tendon_2','tendon_3'])
        for c in index['cases']:
            self.assertAlmostEqual(c['before']['time_s'],c['update_index']*.01)
            self.assertAlmostEqual(c['after']['time_s'],(c['update_index']+1)*.01)
            self.assertTrue(c['accepted_action_equals_applied'])
            self.assertEqual(c['initial_state'],c['projection_reconstruction']['q_gvs']+c['projection_reconstruction']['qdot_gvs'])
            self.assertEqual(len(c['initial_state']),24)

    def altered(self, filename, change):
        original=diagnostic.archived
        def load(folder,ref,raw=False):
            value=original(folder,ref,raw)
            if ref==self.index['source_files'][filename]:
                value=deepcopy(value);change(value)
            return value
        return patch.object(diagnostic,'archived',side_effect=load)

    def test_missing_target_time_and_action_cannot_be_manufactured(self):
        for filename,change in [('controller_observations.json',lambda v:v[19].update(time_s=.18)),
                ('controller_observations.json',lambda v:v[19].update(actual_tension_n=[0.]*4)),
                ('control_spec.json',lambda v:v['specification']['tendon_order'].reverse()),
                ('controller_observations.json',lambda v:v.pop())]:
            with self.subTest(filename=filename),self.altered(filename,change),self.assertRaises(ValueError):
                diagnostic.archive_index(FOLDER,REF)

    def test_fallback_and_missing_prediction_remain_missing(self):
        for change in (lambda v:v[19].update(plan_accepted=False,failure_response_used=True),
                       lambda v:v[19].pop('one_step_prediction')):
            with self.altered('controller_observations.json',change):
                case=diagnostic.archive_index(FOLDER,REF)['cases'][1]
            self.assertIsNone(case['accepted_prediction']);self.assertFalse(case['accepted_action_equals_applied'])

    def test_explicit_typed_resolution_and_index(self):
        query=dict(candidate=REF,source=REF,update_index=19,substeps=32)
        self.assertEqual(NMPCPredictionDiagnostic(**query).substeps,32)
        for bad in (dict(substeps=2),dict(substeps=64),dict(update_index=34)):
            with self.assertRaises(ValueError):NMPCPredictionDiagnostic(**dict(query,**bad))

    def test_signed_vectors_and_incomplete_math(self):
        c=self.index['cases'][1];p=c['accepted_prediction']
        raw=dict(complete=True,substeps=1,tip_positions_m=[c['before']['tip_position_m'],p['tip_position_m']],
            tip_velocities_m_s=[c['before']['tip_velocity_m_s'],p['tip_velocity_m_s']],states=[c['initial_state'],p['state']])
        result=diagnostic.compare_outputs(raw,c)
        for field in ('position','velocity'):
            v=result[field];np.testing.assert_allclose(v['e_one_step'],np.asarray(v['e_initial'])+v['e_increment'],atol=1e-15)
        self.assertTrue(result['same_original_experiment'])
        self.assertEqual(result['archived_prediction_difference']['state'],[0.]*24)
        raw['complete']=False
        self.assertNotIn('e_one_step',diagnostic.compare_outputs(raw,c)['position'])

    def test_candidate_task_source_binding(self):
        host=SimpleNamespace(store=SimpleNamespace(artifact=lambda r:self.index))
        query=NMPCPredictionDiagnostic(candidate=REF,source=REF,update_index=19,substeps=1)
        with patch.object(diagnostic,'state',return_value=dict(scoped_context=[REF])):
            with self.assertRaisesRegex(ValueError,'CANDIDATE_TASK_MODEL'):
                diagnostic.admitted_case(host,query,dict(robot={},task={},seed=0,policy={k:{} for k in self.index['scientific_configuration']['policy']}))

    def test_scientific_identity_excludes_archive_labels_and_feedback_is_versioned(self):
        from tools.research.diagnostic_relations import scoped_feedback
        relabeled=dict(self.index,source_study='different label')
        self.assertEqual(diagnostic.interval_identity(self.index,self.index['cases'][0]),
            diagnostic.interval_identity(relabeled,self.index['cases'][0]))
        packet=dict(schema='sorosim_s57_prediction_feedback_v1')
        host=SimpleNamespace(store=SimpleNamespace(artifact=lambda ref:packet))
        self.assertEqual(scoped_feedback(host,[REF])[0]['evidence'],packet)

    def test_json_roundtrip_spec_admits_exact_one_interval_gateway_request(self):
        from extensions.tendon_family.sorosim_codesign import predict_archived_interval
        candidate=diagnostic.archived(FOLDER,self.index['candidate'])
        c=self.index['cases'][1];p=c['accepted_prediction']
        # Fabricated gateway outcome: tests payload construction, never numerical evidence.
        raw=dict(status='fixture',complete=True,substeps=1,roots=[1,1,0,1,0,0],
            states=[c['initial_state'],p['state']],tip_positions_m=[c['before']['tip_position_m'],p['tip_position_m']],
            tip_velocities_m_s=[c['before']['tip_velocity_m_s'],p['tip_velocity_m_s']])
        with patch('extensions.tendon_family.sorosim_codesign.SorosimSession') as session:
            engine=session.return_value.__enter__.return_value
            engine.environment={};engine.dependency={};engine.timings={};engine.evaluate.return_value=raw
            out=predict_archived_interval(candidate['configuration'],self.index,c,1)
            request=engine.evaluate.call_args.args[1]
            self.assertEqual(request['x'],c['initial_state'])
            self.assertEqual(request['tensions_n'],[c['applied_tension_n']])
            self.assertEqual(request['times_s'],[.19,.2])
            self.assertEqual(out['root_count'],1)

    def test_count_receipt_failure_deduplication_and_recovery(self):
        directory=ROOT/'runs'/('s57-fixture-'+uuid4().hex)
        directory.mkdir()
        def cleanup():
            gc.collect()
            if directory.resolve().parent!=(ROOT/'runs').resolve():raise ValueError('WORKSPACE_FIXTURE_REQUIRED')
            shutil.rmtree(directory)
        self.addCleanup(cleanup)
        # Fabricated worker failure tests ledger/receipt ownership only.
        with patch.object(core,'ProjectConfig',side_effect=lambda **kw:ProjectConfig(**dict(kw,project_id=Path(directory).name,grant_id=Path(directory).name))):
            host=core.prepare(ROOT/'configs/research/study_sorosim_s57_prediction.json',directory)
        update(host,freeze='offline_fixture',core_hashes=core_hashes())
        case=self.index['cases'][1];query=NMPCPredictionDiagnostic(candidate=REF,source=REF,update_index=19,substeps=1)
        def worker(args,log,timeout):
            folder=Path(args[-1]).parent
            atomic_json(folder/'result.json',dict(status='engineering_error',reason='fabricated fixture'))
            return SimpleNamespace(returncode=0)
        with patch.object(mechanics,'guard'),patch.object(mechanics,'verify_candidate',return_value=dict(configuration={})),\
             patch.object(diagnostic,'admitted_case',return_value=(self.index,case)),\
             patch('tools.service_execution._run_contained',side_effect=worker),patch('tools.research.rl.compatible_references'):
            result=mechanics.dispatch(host,'nmpc_prediction_diagnostic',query,'fixture')
            self.assertEqual(state(host)['mathematical_evaluations'],1)
            self.assertEqual(host.store.remaining()['used']['backend_solves'],0)
            self.assertIsNone(state(host)['pending'])
            with self.assertRaisesRegex(ValueError,'ALREADY_EXECUTED'):
                mechanics.dispatch(host,'nmpc_prediction_diagnostic',query,'different-id')
            self.assertEqual(state(host)['mathematical_evaluations'],1)
            self.assertEqual(host.store.artifact(result['reference'])['substeps'],1)
            uncertain=subprocess.TimeoutExpired('fabricated worker',1)
            uncertain.termination_confirmed=False
            query=query.model_copy(update=dict(substeps=4))
            with patch('tools.service_execution._run_contained',side_effect=uncertain),self.assertRaisesRegex(ValueError,'UNKNOWN_MATHEMATICAL_OUTCOME'):
                mechanics.dispatch(host,'nmpc_prediction_diagnostic',query,'uncertain-fixture')
            self.assertEqual(state(host)['mathematical_evaluations'],2)
            pending=state(host)['pending'];self.assertIsNotNone(pending)
            folder=Path(pending['folder'])
            atomic_json(folder/'boundary.json',dict(termination_confirmed=True,returncode=1,elapsed_s=.1))
            recovered=mechanics.recover(host)
            self.assertEqual(recovered['status'],'incomplete')
            self.assertEqual(state(host)['mathematical_evaluations'],2)
            self.assertIsNone(state(host)['pending'])


if __name__=='__main__':unittest.main()
