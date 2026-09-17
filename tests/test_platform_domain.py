"""Bounded domain checks using existing archived trajectories; zero new solves."""
import gzip
import json
import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
from examples.platform_domain_example import session_input, CHANGES
from examples.platform_fixtures import reference_input, project
from extensions.robot_domain.contracts import RodDesign
from extensions.robot_domain.signals import from_rows, select
from schemas.platform import BackendResult, Payload, ExportBundle, SessionInput, Signal, SignalSpec
from schemas.robot_ir import RobotIR
from tools.platform_registry import registry
from tools.platform_tools import _candidate
from tools.platform_host import Host
from tools.platform_store import Store, plain, zero
from tools.design_compiler import build_robot_ir
from tools.platform_tasks import compile_input
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
        folder = ROOT / 'tests/fixtures/platform_domain/mujoco'
        for name in ('trajectory.json.gz', 'robot_ir.json', 'shared_input.json', 'result.json'):
            self.assertTrue((folder / name).is_file(), 'Required repository fixture missing: ' + name)
        return folder

    def test_backend_observation_contracts(self):
        for backend in ('matlab', 'mujoco'):
            with self.subTest(backend=backend):
                inp = session_input(backend)
                phase = 'sampled_state' if backend == 'matlab' else 'pre_step_solver'
                spec = dict(name='actuator_force', entity='tendon_0', dimension=1,
                            units='N', frame='actuator', phase=phase)
                inp['task']['observations'].append(spec)
                reg = registry()
                key = ('backend.' + backend, '1.0.0')
                # Only bypass optional runtime installation discovery. Real semantic,
                # robot compilation and backend.check paths remain active; no solves.
                reg.extensions[key] = replace(reg.get(*key), dependencies=())
                ctrl_key = ('controller.legacy_length', '1.0.0')
                ctrl = reg.get(*ctrl_key)
                reg.extensions[ctrl_key] = replace(ctrl, capabilities={**ctrl.capabilities, 'observation_specs': [spec]})
                snapshot = compile_input(inp, reg)
                self.assertEqual(snapshot['input']['task']['observations'][-1]['entity'], 'tendon_0')
                for field, wrong in dict(entity='tendon_4', dimension=2, units='m', frame='world',
                                         phase='post_step').items():
                    bad = {**spec, field: wrong}
                    with self.subTest(field=field):
                        invalid = deepcopy(inp)
                        invalid['task']['observations'][-1] = bad
                        with self.assertRaisesRegex(ValueError, 'BACKEND_SIGNAL_SEMANTICS_MISMATCH'):
                            compile_input(invalid, reg)
                        reg.extensions[ctrl_key] = replace(ctrl, capabilities={**ctrl.capabilities, 'observation_specs': [bad]})
                        with self.assertRaisesRegex(ValueError, 'CONTROL_OBSERVATION_SEMANTICS_UNSUPPORTED'):
                            compile_input(inp, reg)
                        reg.extensions[ctrl_key] = replace(ctrl, capabilities={**ctrl.capabilities, 'observation_specs': [spec]})
                # Joint axes are backend/model-specific, not arbitrary entity strings.
                joint = dict(name='joint_position', entity='joint_7_z', dimension=1,
                             units='rad', frame='joint_local', phase='sampled_state' if backend == 'matlab' else 'post_step')
                inp['task']['observations'].append(joint)
                if backend == 'matlab':
                    with self.assertRaisesRegex(ValueError, 'BACKEND_SIGNAL_SEMANTICS_MISMATCH'):
                        compile_input(inp, reg)
                else:
                    compile_input(inp, reg)

    def test_entity_threshold_public_versions(self):
        root = ROOT / 'runs/platform_domain_checks' / uuid4().hex
        store = Store(root)
        store.create(project())
        hosts = {}
        for version in ('1.0.0', '1.1.0'):
            inp = reference_input('threshold-' + version.replace('.', '-'))
            inp['policy']['allowed_tools'] = []
            inp['policy']['tool_bindings'] = {'diagnostics.sample_exceeds': version}
            host = Host(root, inp['run_id'])
            host.create(inp)
            hosts[version] = host
        # Synthetic values isolate strict scalar comparison/entity/phase selection.
        spec = SignalSpec(name='tendon_tension', entity='tendon_0', dimension=1,
                          units='N', frame='actuator', phase='pre_step_solver')
        signals = [Signal(spec=spec, times_s=[0., .1, .2], values=[[-11.], [5.], [12.]]),
            Signal(spec=spec.model_copy(update={'entity': 'tendon_1'}), times_s=[0., .1, .2], values=[[20.], [0.], [5.]]),
            Signal(spec=spec.model_copy(update={'phase': 'sampled_state'}), times_s=[0.], values=[[50.]])]
        result = BackendResult(solver_status='completed', backend_id='backend.mujoco', model_id='synthetic-interface-only',
            signals=signals, data=Payload(contract='legacy.backend_data', data={}),
            initial_state=Payload(contract='legacy.initial_state', data={}), seed=17, limitations=['Synthetic; no physical validation'])
        with store.transaction() as db:
            ref = store.put(db, result)
            unique = store.put(db, result.model_copy(update={'signals': signals[:1]}))
            empty = store.put(db, result.model_copy(update={'signals': [Signal(spec=spec, times_s=[], values=[])]}))
            vector = store.put(db, result.model_copy(update={'signals': [Signal(
                spec=spec.model_copy(update={'dimension': 2}), times_s=[0.], values=[[12., 20.]])]}))

        def call(version='1.1.0', host_version=None, **changes):
            args = dict(result=plain(ref), signal='tendon_tension', threshold=5., units='N')
            args.update(changes)
            return hosts[host_version or version].invoke(dict(request_id=uuid4().hex,
                tool_id='diagnostics.sample_exceeds', tool_version=version, arguments=args, reason='Offline contract check'))

        def output(receipt):
            self.assertEqual(receipt['execution_status'], 'completed', receipt)
            self.assertEqual(receipt['charged']['backend_solves'], 0)
            return store.artifact(receipt['output'])

        with patch('tools.reach_dynamics.DynamicsBackends.simulate', side_effect=AssertionError('No solve')):
            for entity, index, value in [('tendon_0', 2, 12.), ('tendon_1', 0, 20.)]:
                data = output(call(entity=entity, phase='pre_step_solver'))
                self.assertEqual(data['sample_indices'], [index])
                self.assertEqual(data['observed'], [[value]])
                self.assertEqual((data['signal'], data['entity'], data['phase']), ('tendon_tension', entity, 'pre_step_solver'))
                self.assertEqual(data['source'], plain(ref))
                self.assertEqual(data['rule'], 'sample_exceeds@1.1.0')
            for args in ({}, {'entity': 'tendon_0'}):
                self.assertIn('SIGNAL_SELECTION_REQUIRED', call(**args)['error'])
            self.assertEqual(output(call(entity='tendon_9'))['status'], 'missing_data')
            self.assertEqual(output(call(result=plain(empty)))['status'], 'missing_data')
            self.assertEqual(output(call(result=plain(vector)))['status'], 'not_applicable')
            self.assertEqual(output(call(entity='tendon_1', units='m'))['status'], 'not_applicable')
            self.assertEqual(output(call(entity='tendon_1', threshold=20.))['status'], 'no_event')
            self.assertEqual(output(call('1.0.0', result=plain(unique)))['sample_indices'], [2])
            self.assertIn('diagnostics.sample_exceeds@1.1.0', call('1.0.0')['error'])
            self.assertEqual(call('1.0.0', host_version='1.1.0')['execution_status'], 'rejected')
            self.assertEqual(call(entity='tendon_1', threshold='invalid')['execution_status'], 'rejected')
        self.assertEqual(store.remaining()['used']['backend_solves'], 0)

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
