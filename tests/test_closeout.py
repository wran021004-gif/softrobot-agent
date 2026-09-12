"""Persistence/authority/evidence risks; no new numerical rollouts in these tests."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from tools.artifact_tools import create_run,finalize_run,file_hash
from tools.closeout_state import CampaignState,read,resume_artifacts,verify_run
from tools.closeout_campaign import make_plan
from tools.closeout_authority import POLICY
from tools.experiment_policy_tools import validate_experiment_policy
from tools.harness import _snapshot_sources
from tools.spec_tools import ROOT


class CloseoutTests(unittest.TestCase):
    def test_authority_and_fixed_plan(self):
        exp=validate_experiment_policy(ROOT/POLICY);plan=make_plan()
        self.assertEqual(exp.policy.feedback_parameters.update_every_steps,20)
        self.assertEqual(len(plan['search_candidates']),16)
        self.assertEqual(sum(s['MUJOCO'] for s in plan['stage_budgets'].values()),20)
        changed=exp.policy.model_copy(update={'seed':18})
        with patch('tools.experiment_policy_tools.load_experiment_policy',return_value=changed):
            with self.assertRaises(ValueError): validate_experiment_policy(ROOT/POLICY)

    def test_stage_reservation_incumbent_and_fingerprint(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            run=create_run(tmp);state=CampaignState(run,make_plan());design=state.plan['reference_designs'][0]
            first=state.reserve('A',design,'MUJOCO','C1')
            state.complete(first,dict(status='completed',canonical_error_m=.1))
            worse=state.reserve('A',design,'MUJOCO','C1')
            state.complete(worse,dict(status='completed',canonical_error_m=.2))
            self.assertEqual(state.data['incumbents']['global']['attempt_id'],first['attempt_id'])
            for _ in range(2): state.reserve('A',design,'MUJOCO','C1')
            with self.assertRaises(ValueError):state.reserve('A',design,'MUJOCO','C1')
            self.assertEqual(state.remaining()['C']['MUJOCO'],4)
            self.assertNotEqual(state.key(design,'MUJOCO','C1'),state.key(design,'MUJOCO','C2'))
            old=state.key(design,'M1','C1');state.plan['execution_fingerprint']='changed'
            self.assertNotEqual(old,state.key(design,'M1','C1'))

    def test_cross_process_interruption_and_recovery(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            script="""import sys,os
from tools.artifact_tools import create_run
from tools.closeout_campaign import make_plan
from tools.closeout_state import CampaignState
r=create_run(sys.argv[1]);s=CampaignState(r,make_plan());r.save('frozen_plan.json',s.plan)
s.reserve('A',s.plan['reference_designs'][0],'MUJOCO','C1')
print(r.path,flush=True);os._exit(9)
"""
            child=subprocess.run([sys.executable,'-c',script,tmp],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(child.returncode,9)
            path=Path(child.stdout.strip());run=resume_artifacts(path)
            state=CampaignState(run,read(path/'frozen_plan.json'),resume=True)
            old=state.data['attempts'][0];self.assertEqual(old['status'],'interrupted')
            retry=state.reserve('E',old['design'],'MUJOCO','C1',retry_of=old['attempt_id'])
            self.assertNotEqual(retry['attempt_id'],old['attempt_id'])
            self.assertEqual(state.used('A','MUJOCO'),1);self.assertEqual(state.used('E','MUJOCO'),1)

    def test_resume_routes_interrupted_mujoco_to_reserved_recovery(self):
        from tools.closeout_campaign import execute_attempt
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            run=create_run(tmp);state=CampaignState(run,make_plan());design=state.plan['reference_designs'][0]
            for _ in range(4):state.reserve('A',design,'MUJOCO','C1')
            state.data['attempts'][-1]['status']='interrupted'
            with patch.object(state,'reserve',side_effect=RuntimeError('stop before backend')) as reserve:
                with self.assertRaisesRegex(RuntimeError,'stop before backend'):
                    execute_attempt(state,'A',design,'MUJOCO','C1')
            self.assertEqual(reserve.call_args.args[0],'E')
            self.assertEqual(reserve.call_args.args[-1],'attempt_003')

    def test_offline_corruption_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            run=create_run(tmp);_snapshot_sources(run);run.save('numerical.json',{'tip_m':[.1,0,.1]});finalize_run(run,'PASS')
            verify_run(run.path)
            (run.path/'numerical.json').write_text('{}')
            with self.assertRaises(ValueError):verify_run(run.path)

    def test_visual_failure_is_separate(self):
        from tools.debug_tools import DebugObservability
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            debug=DebugObservability(Path(tmp)/'debug',debug=True)
            debug.attempt('forced_plot_error',lambda:(_ for _ in ()).throw(RuntimeError('fixture')))
            self.assertTrue(debug.errors)

    def test_log_replay_never_sends_actions(self):
        from tools.closeout_validation import ReplayAdapter
        adapter=ReplayAdapter([{'time_s':0}]);self.assertEqual(adapter.observe()['time_s'],0)
        with self.assertRaises(ValueError):adapter.apply([.3])
        adapter.close()
        with self.assertRaises(ValueError):adapter.observe()


if __name__=='__main__':unittest.main()
