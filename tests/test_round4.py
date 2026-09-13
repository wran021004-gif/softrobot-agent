"""Focused offline risks. These tests never execute MATLAB or mj_step."""
import json
from pathlib import Path
import tempfile
from contextlib import contextmanager
import uuid
import unittest
from unittest.mock import patch
import numpy as np
from tools.spec_tools import ROOT
from tools.closeout_state import atomic_json,read


@contextmanager
def scratch():
    # Keep test evidence. tempfile's private Windows ACL conflicts with the managed token.
    path=ROOT/'runs/round4_test_evidence'/uuid.uuid4().hex
    path.mkdir(parents=True)
    yield path


class Round4Tests(unittest.TestCase):
    def test_saved_backend_times_align_despite_float_roundoff(self):
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from tools.observation_viewer import ObservationViewer
        folder=ROOT/'runs/round4/validation/oscillator'
        v=ObservationViewer([folder/'mujoco_observation.json',folder/'matlab_observation.json'])
        try:
            self.assertEqual(len(v.times),1001)
            v.seek(.2)
            self.assertEqual(v.label.get_text().count('state t=0.2000'),2)
            self.assertAlmostEqual(v.slider.val,.2)
        finally:plt.close(v.figure)

    def test_explicit_interrupted_retry_consumes_new_attempt(self):
        from tools.round4_budget import Budget
        with scratch() as tmp:
            b=Budget(tmp);b.reserve('length_mujoco','candidate_C1',{},stage='coarse')
            resumed=Budget(tmp,retry_interrupted=True)
            value=resumed.call('length_mujoco','candidate_C1',{},Path(tmp)/'retry.json',lambda:dict(status='pass'),stage='coarse')
            rows=read(b.path)['attempts']
            self.assertEqual(len(rows),2);self.assertEqual(rows[0]['status'],'interrupted')
            self.assertEqual(rows[1]['retry_of'],0);self.assertEqual(value['status'],'pass')

    def test_authority_fixed_parameters_and_envelope(self):
        from tools.experiment_policy_tools import validate_experiment_policy
        from tools.round4_authority import POLICY,validate_round4_authority
        exp=validate_experiment_policy(ROOT/POLICY)
        exp.validate_candidate({**exp.baseline.model_dump(),'total_length_m':.8})
        for change in ({'total_length_m':.81},{'tendon_count':4},{'tendon_routing_radius_m':.015}):
            with self.assertRaises(ValueError):exp.validate_candidate({**exp.baseline.model_dump(),**change})
        p=exp.policy.model_copy(update={'seed':18})
        with self.assertRaises(ValueError):validate_round4_authority(p,exp.path,exp.envelope)

    def test_budget_recovery_integrity_and_reservation(self):
        from tools.round4_budget import Budget
        with scratch() as tmp:
            b=Budget(tmp);p=Path(tmp)/'result.json';calls=[]
            first=b.call('mechanics','one',{},p,lambda:calls.append(1) or {'status':'pass'})
            self.assertEqual(first,b.call('mechanics','one',{},p,lambda: self.fail('repeated solve')))
            self.assertEqual(calls,[1]);atomic_json(p,{'corrupt':True})
            with self.assertRaises(ValueError):b.call('mechanics','one',{},p,lambda:None)
            b.reserve('mechanics','crashed',{})
            with self.assertRaises(ValueError):b.reserve('mechanics','crashed',{})
            for i in range(22):b.reserve('mechanics',str(i),{})
            with self.assertRaises(ValueError):b.reserve('mechanics','over',{})

    def test_task_partitions_and_window_evaluation(self):
        from tools.task_family_tools import generate_task_instance,evaluate_task_instance
        instance=generate_task_instance('tip_stability_external_force')
        self.assertEqual(instance,generate_task_instance('tip_stability_external_force'))
        with self.assertRaises(ValueError):generate_task_instance('reach_free',17,'evaluation')
        generate_task_instance('reach_free',10017,'evaluation')
        rows=[dict(time_s=(i+1)*.002,tip_m=list(instance.target_m)) for i in range(1000)]
        result=dict(status='fail',failure_code='TASK_FAILED',metrics={'task_success':False,
            'target_position_m':list(instance.target_m),'position_error_max_m':instance.tolerance_m},
            artifacts={'disturbances':[instance.disturbance]})
        rows[9]['tip_m'][0]+=.1  # Outside stability evaluation interval.
        self.assertTrue(evaluate_task_instance(instance,result,rows)['task_success'])
        rows[500]['tip_m'][0]+=.02
        value=evaluate_task_instance(instance,result,rows)
        self.assertEqual(value['status'],'EVALUATED');self.assertFalse(value['task_success'])
        self.assertEqual(evaluate_task_instance(instance,result,rows[:-1])['status'],'EVIDENCE_INCOMPLETE')
        self.assertEqual(evaluate_task_instance(instance,result,rows[10:])['status'],'EVIDENCE_INCOMPLETE')

    def test_changed_cached_context_and_task_evidence_are_rejected(self):
        from tools.round4_budget import Budget
        from tools.task_family_tools import generate_task_instance,evaluate_task_instance
        with scratch() as tmp:
            b=Budget(tmp);b.call('mechanics','same',{'input':1},Path(tmp)/'a.json',lambda:{'status':'pass'})
            with self.assertRaises(ValueError):b.call('mechanics','same',{'input':2},Path(tmp)/'a.json',lambda:self.fail('unexpected call'))
        i=generate_task_instance('reach_free')
        self.assertEqual(evaluate_task_instance(i,dict(metrics={'task_success':True}),[])['status'],'EVIDENCE_MISMATCH')
        with self.assertRaises(ValueError):type(i).model_validate({**i.model_dump(),'package':'../elsewhere'})

    def test_diagnostic_condition_not_applicable_and_saved_guard(self):
        from tools.round4_validation import solve_diagnostic
        source=read(ROOT/'runs/round4/validation/historical_recheck.json')
        p={**source['input'],'tip_force_n':[0,1,0]}
        result=solve_diagnostic(None,p,None,'invalid_condition')
        self.assertFalse(result['backend_started']);self.assertEqual(result['result']['failure_kind'],'CONDITION_NOT_APPLICABLE')
        d=source['result']['diagnostics']
        self.assertEqual(d['trigger']['state_kind'],'solver_internal_trial')
        self.assertGreater(d['trigger']['actual_value'],d['trigger']['threshold'])
        self.assertLess(d['last_valid_time_s'],d['trigger']['time_s'])

    def test_replay_never_steps_or_changes_raw_and_preserves_stage(self):
        from tools.observation_tools import load_observation
        from tools.artifact_tools import file_hash
        source=ROOT/'runs/20260912T082519_263560Z_eb328077'
        before=file_hash(source/'trajectory.json.gz')
        with patch('mujoco.mj_step',side_effect=AssertionError('step forbidden')),patch('mujoco.mj_forward',side_effect=AssertionError('forward forbidden')):
            r=load_observation(source)
        s=r['samples'][0]
        self.assertLess(s['input_time_s'],s['time_s'])
        np.testing.assert_allclose(s['centerline_m'][-1],s['tip_m'],atol=1e-12)
        self.assertEqual(before,file_hash(source/'trajectory.json.gz'))
        self.assertNotIn('contact_positions',s)

    def test_failed_analysis_and_incompatible_comparison(self):
        from tools.observation_tools import load_observation,comparison_eligibility
        with scratch() as tmp:
            p=Path(tmp)/'failed.json'
            atomic_json(p,dict(input=dict(length_m=.4,n=8,operation='dynamic'),result=dict(status='fail',reason='domain exceeded')))
            r=load_observation(p);self.assertEqual(r['samples'],[])
            self.assertFalse(comparison_eligibility(r,r)['eligible'])

    def test_catalog_entries_and_missing_status(self):
        from capabilities.registry import query_tools
        import importlib
        rows=query_tools();self.assertEqual(len({r['category'] for r in rows}),6)
        self.assertTrue(query_tools(implementation_status='PLANNED'))
        for row in rows:
            for key in ('purpose','inputs','outputs','units','coordinate_frame','time_semantics','assumptions','limitations','dependencies','states','cost','input_example','evidence_refs'):
                self.assertIn(key,row,row['name'])
            if row['implementation_status']=='IMPLEMENTED':
                entry=row['implementation'];obj=importlib.import_module(entry['module'])
                for part in entry['callable'].split('.'):obj=getattr(obj,part)
                self.assertTrue(callable(obj))

    def test_coarse_coverage_and_reserved_refinement(self):
        from tools.round4_campaign import make_plan
        p=make_plan();self.assertEqual(p['lengths'][0],.05);self.assertEqual(p['lengths'][-1],.8)
        self.assertIn(.298,p['lengths']);self.assertIn(.4,p['lengths'])
        accepted=[l for l in p['lengths'] if l>=np.linalg.norm([.25,0,.15])-.01]
        self.assertLessEqual(len(accepted),10)


if __name__=='__main__':unittest.main()
