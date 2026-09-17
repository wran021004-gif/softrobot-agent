"""Bounded domain checks using existing archived trajectories; zero new solves."""
import gzip
import json
import unittest
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
from examples.platform_domain_example import session_input, CHANGES
from examples.platform_fixtures import reference_input, project
from extensions.robot_domain.contracts import RodDesign
from extensions.robot_domain.signals import from_rows, select
from schemas.platform import BackendResult, Payload, ExportBundle, SessionInput
from schemas.robot_ir import RobotIR
from tools.platform_registry import registry
from tools.platform_tools import _candidate
from tools.platform_host import Host
from tools.platform_store import Store, plain, zero
from tools.design_compiler import build_robot_ir
from tools.spec_tools import ROOT


class DomainTests(unittest.TestCase):
    def test_design_rebuild_and_frozen_scope(self):
        reg = registry()
        inp = SessionInput.model_validate(session_input('mujoco'))
        original = inp.model_dump(mode='json')
        result = _candidate(inp, CHANGES, reg)
        baseline = build_robot_ir(RodDesign.model_validate(inp.robot.structure.data))
        ir = build_robot_ir(RodDesign.model_validate(result.robot.structure.data))
        self.assertEqual(inp.model_dump(mode='json'), original)
        self.assertEqual(result.task, inp.task)
        self.assertEqual(ir.section.segment_length_m, .32 / 8)
        self.assertEqual(ir.resolved_rod.mass_kg[0], 1.1 * .32 / 8)
        self.assertAlmostEqual(ir.resolved_rod.inertia_diagonal_kg_m2[0][1],
            (1.1 * .32 / 8) * (3 * .019**2 + (.32 / 8)**2) / 12)
        self.assertEqual(ir.resolved_rod.stiffness_nm_rad[0], .0042 / (.32 / 8))
        self.assertEqual(ir.resolved_rod.damping_nm_s_rad[0], .004 / (.32 / 8))
        self.assertEqual(ir.resolved_rod.natural_y_rad[0], -.05 / 8)
        self.assertNotEqual(ir.tendon_routes, baseline.tendon_routes)
        self.assertEqual(result.policy.controller.parameters.data['bend_z_rad'], .9)
        with self.assertRaisesRegex(ValueError, 'Routing'):
            _candidate(inp, {'design.body_radius_m': .018, 'design.tendon_routing_radius_m': .02}, reg)
        with self.assertRaisesRegex(ValueError, 'NOT_AUTHORIZED'):
            _candidate(inp, {'design.segments': 10.}, reg)

    def archive(self):
        # Prior real short-run exports; read only, never replay the experiment.
        path = next(iter(sorted((ROOT / 'runs/platform_acceptance').glob('*/numerical/sessions/reach-a/executions/*/backend/trajectory.json.gz'))), None)
        if path is None:
            self.skipTest('Existing short MuJoCo archive unavailable; run the public example for live evidence')
        return path.parent

    def test_saved_signal_entities_times_and_missing(self):
        folder = self.archive()
        rows = json.loads(gzip.decompress((folder / 'trajectory.json.gz').read_bytes()))
        ir = RobotIR.model_validate_json((folder / 'robot_ir.json').read_text(encoding='utf8'))
        signals = from_rows(rows, 'mujoco', ir)
        force = select(signals, 'actuator_force', 'tendon_0')
        tension = select(signals, 'tendon_tension', 'tendon_0')
        joint = select(signals, 'joint_position', 'joint_0_y')
        self.assertEqual(force.times_s, [r['solver_time_s'] for r in rows])
        self.assertEqual(joint.times_s, [r['time_s'] for r in rows])
        self.assertEqual(force.spec.phase, 'pre_step_solver')
        self.assertEqual(joint.spec.phase, 'post_step')
        self.assertEqual(tension.values, [[-r['solver_actuator_force_n'][0]] for r in rows])
        self.assertEqual(len([s for s in signals if s.spec.name == 'joint_position']), ir.segments * 2)
        self.assertIsNone(select(signals, 'contact_normal_approx'))
        with self.assertRaisesRegex(ValueError, 'SELECTION_REQUIRED'):
            select(signals, 'actuator_force')
        # Minimal saved MATLAB-shaped sample tests its distinct phase, not a solve.
        sample = dict(time_s=0., solver_time_s=0., qpos_rad=[.1] * ir.segments,
                      solver_actuator_force_n=[-2.] * ir.tendon_count)
        matlab = from_rows([sample], 'matlab', ir)
        self.assertEqual(select(matlab, 'joint_position', 'joint_7_y').spec.phase, 'sampled_state')
        self.assertEqual(select(matlab, 'actuator_force', 'tendon_3').values, [[-2.]])
        self.assertIsNone(select(matlab, 'tendon_length'))

    def test_archive_bridge_aliases_and_legacy_entry(self):
        folder = self.archive()
        root = ROOT / 'runs/platform_domain_checks' / uuid4().hex
        store = Store(root)
        store.create(project())
        inp = reference_input('archive-check')
        inp['policy']['allowed_tools'] = []
        inp['policy']['tool_bindings'] = {'diagnostics.saved_trajectory': '2.0.0',
            'diagnostics.signal_rule': '2.0.0', 'visualization.saved_replay': '1.0.0'}
        host = Host(root, inp['run_id'])
        host.create(inp)
        old = json.loads((folder / 'result.json').read_text(encoding='utf8'))
        result = BackendResult(solver_status='completed', backend_id='backend.mujoco', model_id=old['model_id'],
            signals=[], data=Payload(contract='legacy.backend_data', data=dict(backend='mujoco', original=old, exported_files=[])),
            initial_state=Payload(contract='legacy.initial_state', data={}), seed=17, limitations=['archived test import; no new simulation'])
        with store.transaction() as db:
            ref = store.put(db, result)
            files = [dict(filename=p.name, reference=store.put(db, p.read_bytes(), 'application/octet-stream'))
                for p in folder.iterdir() if p.is_file()]
            bundle = store.put(db, ExportBundle(result=ref, files=files, source='backend.mujoco'))
            state = store.session(host.run_id, db)['state']
            candidate = store.put(db, dict(role='archived test fixture, not a newly executed candidate'))
            metadata = dict(artifact_id=ref.artifact_id, candidate='archive', candidate_input=plain(candidate), original_execution_id='archive-origin')
            state['result_executions'] = {'archive-origin': metadata, 'archive-alias': dict(metadata)}
            store.update_state(db, host.run_id, state)
            store.event(db, host.run_id, 'simulation', 'completed', execution='archive-origin', outputs=[bundle])
        def call(tool, execution=None):
            args = dict(result=plain(ref))
            if execution:
                args['execution_id'] = execution
            return host.invoke(dict(request_id=uuid4().hex, tool_id=tool,
                tool_version=inp['policy']['tool_bindings'][tool], arguments=args, reason='Archived bridge check; zero dynamics'))
        with patch('tools.reach_dynamics.DynamicsBackends.simulate', side_effect=AssertionError('No solve')):
            ambiguous = call('diagnostics.saved_trajectory')
            self.assertIn('SELECTION_REQUIRED', ambiguous['error'])
            for tool in inp['policy']['tool_bindings']:
                receipt = call(tool, 'archive-alias')
                self.assertEqual(receipt['execution_status'], 'completed', receipt)
                product = store.artifact(receipt['output'])
                self.assertEqual(product['original_execution_id'], 'archive-origin')
                self.assertEqual(product['source_execution_id'], 'archive-alias')
                self.assertEqual(product['candidate_id'], 'archive')
                self.assertEqual(store.artifact(product['files']['trajectory.json.gz'], raw=True), (folder / 'trajectory.json.gz').read_bytes())
            from tools.public_services import saved_diagnosis
            from tools.artifact_tools import file_hash
            from schemas.public_tools import SavedDiagnosis
            legacy_registry = {p.name: dict(sha256=file_hash(p)) for p in folder.iterdir() if p.is_file()}
            report = saved_diagnosis(folder, legacy_registry, plain(SavedDiagnosis(result_ref='result.json', backend='mujoco')))
            self.assertEqual(report['backend_solves'], 0)
        self.assertEqual(store.remaining()['used']['backend_solves'], 0)


if __name__ == '__main__':
    unittest.main()
