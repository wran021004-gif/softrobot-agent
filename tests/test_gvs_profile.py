"""Bounded checks of import/scope and truthful saved-result interpretation."""
import copy
import gzip
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
from schemas.platform import SessionInput
from extensions.tendon_family.gvs_profile import profile_input, checked_profile, execution_scope
from extensions.tendon_family.gvs_reporting import summarize, reconstruct_motion
from tools.platform_skills import scope_match
from tools.spec_tools import ROOT


class ProfileTests(unittest.TestCase):
    def test_public_fresh_process_preparation_and_retrieval(self):
        folder=ROOT/'runs/profile_focused_checks'/uuid4().hex
        result=subprocess.run([sys.executable,str(ROOT/'examples/gvs_nmpc_profile.py'),'prepare','--output',str(folder)],
            capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        from tools.platform_host import Host
        from tools.platform_skills import applicable
        state=json.loads((folder/'workflow.json').read_text(encoding='utf8'))
        host=Host(folder,state['run_id'])
        self.assertEqual(host.store.remaining(host.run_id)['used']['backend_solves'],0)
        fresh=Host(folder,'fresh-reader');fresh.create(profile_input('fresh-reader'))
        records=applicable(fresh,None)
        self.assertEqual(records[0]['scope_assessment']['match'],'matching')
        self.assertEqual(records[0]['status'],'candidate')
        self.assertIsNone(records[0]['human_approval'])
        numerical=checked_profile(SessionInput.model_validate(profile_input('x')))['numerical_reference']
        self.assertIn('warm_guess',host.store.artifact(numerical))
        from tools.platform_tools import simulation_preflight
        from schemas.platform_operations import Simulate
        from tools.platform_registry import registry
        simulation_preflight(SessionInput.model_validate(profile_input('x')),Simulate(),registry())

    def test_scope_and_artifact_rejection(self):
        inp=SessionInput.model_validate(profile_input('x'));profile=checked_profile(inp)
        changed=inp.model_copy(deep=True);changed.task.goal.data['target_m'][0]+=.001
        with self.assertRaisesRegex(ValueError,'SCOPE_MISMATCH'):checked_profile(changed)
        self.assertEqual(scope_match(execution_scope(inp),changed),'unvalidated_starting_point')
        changed=changed.model_copy(update={'policy':changed.policy.model_copy(update={
            'backend':changed.policy.backend.model_copy(update={'extension_id':'backend.matlab_spatial'})})})
        self.assertEqual(scope_match(execution_scope(inp),changed),'incompatible')
        bad=copy.deepcopy(profile);bad['numerical']['tendon_order'].reverse()
        with patch('extensions.tendon_family.gvs_profile.load_profile',return_value=bad):
            with self.assertRaisesRegex(ValueError,'NUMERICAL_IDENTITY'):checked_profile(inp)

    def test_saved_reach_settling_and_incomplete_reporting(self):
        folder=ROOT/'runs/stage315_complete_control_20260927'
        summary=json.loads((folder/'public_summary.json').read_text(encoding='utf8'))
        backend=ROOT/summary['backend_folder']
        files={p.name:p.read_bytes() for p in backend.iterdir() if p.is_file()}
        rows=json.loads(gzip.decompress(files['trajectory.json.gz']))
        obs=json.loads(files['controller_observations.json'])
        inp=SessionInput.model_validate(profile_input('x'))
        motion,physics=reconstruct_motion(files,rows,inp.task.goal.data['target_m'])
        result=json.loads((folder/'public_result.json').read_text(encoding='utf8'))
        evaluation=json.loads((folder/'saved_evaluation.json').read_text(encoding='utf8'))
        limits=[t['force_limit_n'] for t in physics['tendons']]
        s=summarize(inp.task,result,evaluation,rows,obs,motion,limits)
        self.assertTrue(s['official_task_success']);self.assertFalse(s['sampled_settling']['passed'])
        self.assertEqual(s['accepted_plans'],35);self.assertEqual(s['deadline_misses'],35)
        partial=summarize(inp.task,result,None,rows[:10],obs[:10],motion[:10],limits)
        self.assertFalse(partial['complete']);self.assertIsNone(partial['sampled_settling']['passed'])
        self.assertIsNone(partial['terminal_error_m']);self.assertIsNone(partial['official_task_success'])


if __name__=='__main__':unittest.main()
