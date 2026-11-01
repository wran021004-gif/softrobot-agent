"""Bounded bridge contracts; synthetic values are interface fixtures only."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from tools.research_tasks import constraint_observation,constraint_gap


class C0BridgeTests(unittest.TestCase):
    def test_signed_bounds_zero_scale_and_invalid_coverage(self):
        def row(key,value,bound,kind='upper'):
            return constraint_observation(dict(constraint_id=key,bound=bound,bound_type=kind,unit='m'),
                dict(value=value,passed=(value<=bound if kind=='upper' else value>=bound)))
        upper=row('upper',3.,2.);lower=row('lower',1.,2.,'lower')
        gap=constraint_gap([upper,lower],valid_complete=True)
        self.assertEqual(gap['signed_task_gap'],.5)
        self.assertEqual(lower['signed_violation'],1.)
        self.assertEqual(len(gap['dominant_constraints']),2)
        self.assertIsNone(constraint_gap([upper,row('zero',0.,0.)],valid_complete=True)['normalized_gap'])
        self.assertIsNone(constraint_gap([upper],valid_complete=False)['normalized_gap'])
        passing=constraint_gap([row('upper',1.,2.)],valid_complete=True)
        self.assertEqual(passing['signed_task_gap'],-.5)
        self.assertEqual(passing['normalized_gap'],0.)

    def test_freeze_detects_passive_solver_without_modifying_evidence(self):
        import tools.research.state as st
        original=st.ROOT
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in st.SCIENCE_FILES:
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes((original/name).read_bytes())
            with patch.object(st,'ROOT',root):
                frozen=st.science_hashes()
                for name in ('passive_equilibrium','passive_inverse'):
                    target=root/('extensions/tendon_family/'+name+'.py');body=target.read_bytes()
                    target.write_bytes(body+b'\n# isolated perturbation\n')
                    self.assertNotEqual(frozen,st.science_hashes())
                    target.write_bytes(body)
                self.assertEqual(frozen,st.science_hashes())

    def test_request_snapshot_is_detached_and_not_persistent(self):
        from tools.platform_store import Store
        with TemporaryDirectory() as tmp:
            s=Store(tmp);calls=[]
            def build():calls.append(1);return dict(value=[])
            with s.read_snapshot():
                s.snapshot_value('a',build)['value'].append(1)
                self.assertEqual(s.snapshot_value('a',build),dict(value=[]))
            s.snapshot_value('a',build)
            self.assertEqual(len(calls),2)
            self.assertFalse(s.db.exists())

    def test_v4_menu_and_old_compiler_alias(self):
        from tools.research.scientific_intent import scientific_actions,action_entry
        spec=dict(research_decisions=dict(analysis_interface='scientific_question_v4'),capabilities=['analysis'])
        goals=[r['scientific_goal'] for r in scientific_actions(spec)]
        self.assertEqual(set(goals),{'mechanism_research','control_feasibility','structure_control_codesign'})
        self.assertIsNotNone(action_entry(spec,'single_parameter_effect'))
        spec['research_decisions']['analysis_interface']='scientific_question_v3'
        self.assertIn('single_parameter_effect',[r['scientific_goal'] for r in scientific_actions(spec)])
