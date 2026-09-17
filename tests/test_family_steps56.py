"""Targeted public-boundary regressions; no dynamics integration."""
import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from examples.platform_tendon_family import example_design,example_discretization,design_space,session,prepare
from extensions.tendon_family.contracts import DynamicsModel
from extensions.tendon_family.optimization import prepare_optimization,CoordinateSearch,SearchParameters
from extensions.tendon_family.preparation import prepare_candidate
from tools.platform_registry import registry
from tools.platform_tools import _candidate,simulation_preflight
from tools.platform_tasks import compile_input
from tools.state_io import atomic_json
from schemas.platform import SessionInput
from schemas.platform_operations import Simulate


class FamilySteps56(unittest.TestCase):
    def input(self):
        d=example_design(); return session('family_mujoco',d,design_space(d))

    def test_final_template_initial_state_and_backend_settings(self):
        with TemporaryDirectory(dir='runs') as folder:
            root=Path(folder); prepare(root)
            space=json.loads((root/'inputs/space.json').read_text(encoding='utf8'))
            three=deepcopy(space['templates']['tube_distal']); tail=deepcopy(three['components'][3])
            tail.update(id='tail',connection=dict(part='far',s=1.),length_m=.04)
            three['components'].insert(4,tail); three['components'][5]['connection']['part']='tail'
            space['templates']['three']=three
            atomic_json(root/'inputs/space.json',space)
            atomic_json(root/'inputs/discretization.json',dict(cells={'near':3,'far':2,'tail':1}))
            atomic_json(root/'inputs/continuous_request.json',dict(design_file='design.json',space_file='space.json',
                discretization_file='discretization.json',changes={'template':'three'}))
            prepared=prepare_candidate(root,'continuous','family_mujoco')
            joint=next(x for x in prepared['built'].resolved_physics['dofs'] if x.startswith('tail'))
            inp=prepared['effective'].model_dump(mode='json')
            inp['task']['initializer']['parameters']['data']['qpos_rad']={joint:.01}
            compile_input(inp)
            args=Simulate(candidate_id='three',changes={})
            actual=simulation_preflight(SessionInput.model_validate(inp),args,registry())['prepared']
            self.assertEqual(actual.effective.robot.structure.data,prepared['effective'].robot.structure.data)
            inp['task']['initializer']['parameters']['data']['qpos_rad']={'missing':.1}
            with self.assertRaisesRegex(ValueError,'INITIAL_UNKNOWN_JOINT'):compile_input(inp)

    def test_model_identity_and_immutable_physics_declarations(self):
        from extensions.tendon_family.execution import resolve_execution
        from extensions.tendon_family.backends import physics_for
        from extensions.tendon_family.scene import assemble
        inp=SessionInput.model_validate(self.input()); plan=resolve_execution(inp,registry())
        self.assertEqual(assemble(inp,physics_for(inp))['experiment_spec']['dynamics_model_identity'],plan['dynamics_model_identity'])
        explicit=self.input(); explicit['policy']['dynamics_model']['parameters']['data']=DynamicsModel().model_dump(mode='json')
        self.assertEqual(resolve_execution(SessionInput.model_validate(explicit),registry())['dynamics_model_identity'],plan['dynamics_model_identity'])
        with self.assertRaisesRegex(ValueError,'PHYSICS_SWITCH_UNSUPPORTED'):DynamicsModel(included=('hinge_elasticity',))

    def test_real_mjcf_configuration(self):
        from extensions.tendon_family.backends import physics_for
        from extensions.tendon_family.scene import assemble
        from extensions.tendon_family.mjcf import compile_xml
        import mujoco
        value=self.input();value['policy']['backend']['parameters']['data']['friction']=[.8,.1,.01]
        inp=SessionInput.model_validate(value)
        with TemporaryDirectory(dir='runs') as folder:
            path=Path(folder)/'robot.xml'; p=physics_for(inp)
            compile_xml(p,assemble(inp,p),registry().bind(inp.policy.backend,'backend')[1],path)
            model=mujoco.MjModel.from_xml_path(str(path))
            self.assertTrue((model.geom_friction[:,0]==.8).all())

    def test_joint_design_control_and_fixed_task(self):
        value=self.input();space=value['policy']['candidate_builder']['parameters']['data']
        space['control_parameters']={'control/feedback_gain':dict(type='number',bounds=[2.,8.])}
        inp=SessionInput.model_validate(value)
        effective=_candidate(inp,{'components/near/length_m':.18,'control/feedback_gain':7.},registry())
        self.assertEqual(effective.task,inp.task)
        self.assertEqual(effective.robot.structure.data['components'][0]['length_m'],.18)
        self.assertEqual(effective.policy.controller.parameters.data['feedback_gain'],7.)
        with self.assertRaisesRegex(ValueError,'OUT_OF_BOUNDS'):_candidate(inp,{'control/feedback_gain':9.},registry())
        req=dict(session=value,template='tube_distal',variables={'components/near/length_m':[.14,.2],'control/feedback_gain':[2.,8.]})
        _,prepared=prepare_optimization(req)
        self.assertEqual(prepared.robot.structure.data['id'],'tube_distal')
        with self.assertRaisesRegex(ValueError,'CONTINUOUS_PHYSICAL'):
            prepare_optimization({**req,'variables':{'discretization/cells/near':[2,6]}})

    def test_search_restore_and_invalid_feedback(self):
        config=SearchParameters(initial={'x':.5},bounds={'x':(0.,1.)},max_trials=3)
        a=CoordinateSearch(config);self.assertEqual(a.propose(),{'x':.5});a.feedback(None)
        saved=a.save().data;b=CoordinateSearch(config);b.restore(saved)
        self.assertEqual(a.propose(),b.propose());a.feedback(1.);b.feedback(1.)
        self.assertEqual(a.propose(),b.propose());self.assertTrue(a.stopped())
        from tools.platform_search import _outcome
        saved=dict(trials=[dict(candidate_id='invalid',score=None),dict(candidate_id='valid',score=.2,comparison_identity='same')],algorithm={})
        out=_outcome(saved,'rejected','BUDGET_EXHAUSTED')
        self.assertEqual(out['best']['candidate_id'],'valid')
        self.assertEqual(out['stop_reason'],'BUDGET_EXHAUSTED')

    def test_legacy_comparison_without_identity_fields(self):
        from extensions.tendon_family.comparison import comparable
        root=Path('runs/tendon_family_20260917')
        if not (root/'matlab_spatial_record.json').exists():self.skipTest('historical evidence not installed')
        records=[json.loads((root/(backend+'_record.json')).read_text(encoding='utf8')) for backend in ('matlab_spatial','family_mujoco')]
        for r in records:
            if r.get('selection'):
                r['selection'].pop('experiment_identity',None);r['selection'].pop('dynamics_model_identity',None)
        out=comparable(root,records)
        self.assertTrue(out['comparable'],out)
        records[0]['receipts']['simulation']['output']['artifact_id']='0'*64
        self.assertFalse(comparable(root,records)['comparable'])

    def test_saved_diagnosis_names_phases_missing_data_and_evidence(self):
        from types import SimpleNamespace
        from extensions.tendon_family.diagnostics import diagnose
        from extensions.robot_domain.contracts import SavedDiagnosis
        from schemas.platform import BackendResult,Payload,EvidenceRef,Signal,SignalSpec
        from extensions.tendon_family.backends import physics_for
        from extensions.tendon_family.scene import assemble
        inp=SessionInput.model_validate(self.input()); p=physics_for(inp); scene=assemble(inp,p)
        ref=EvidenceRef(artifact_id='a'*64)
        signal=Signal(spec=SignalSpec(name='tendon_tension',entity='far_t0',dimension=1,units='N',frame='path',phase='pre_step_solver'),
            times_s=[0.,.05,.1],values=[[0.],[0.],[0.]])
        result=BackendResult(solver_status='failed',backend_id='backend.family_mujoco',model_id='mujoco_serial_bending_v1',
            signals=[signal],data=Payload(contract='family.backend_data',data={'reason':'fixture failure'}),
            limitations=[],initial_state=Payload(contract='family.initial',data={}),seed=17)
        with TemporaryDirectory(dir='runs') as folder:
            folder=Path(folder);atomic_json(folder/'resolved_physics.json',p);atomic_json(folder/'experiment_scene.json',scene)
            ctx=SimpleNamespace(artifact=lambda _:result.model_dump(mode='json'))
            out=diagnose(ctx,SavedDiagnosis(result=ref),dict(root=folder,metadata={'candidate':'named-fixture'}))
        event=out['events'][0]
        self.assertEqual(event['entity'],'far_t0');self.assertEqual(event['phase'],'pre_step_solver')
        self.assertEqual(event['time_range_s'],[0.,.1]);self.assertEqual(event['evidence']['result']['artifact_id'],ref.artifact_id)
        self.assertEqual(out['numerical']['reason'],'fixture failure')
        self.assertTrue(any(m.get('signal')=='tip_position' for m in out['missing']))
        self.assertEqual(out['backend_solves'],0);self.assertFalse(out['rescoring'])

    def test_family_matlab_video_source_needs_no_xml_and_uses_saved_indices(self):
        import gzip
        from unittest.mock import MagicMock
        from tools.simulation_video import _source,_schedule
        from tools.artifact_tools import file_hash
        from extensions.tendon_family.saved import capture_matlab
        with TemporaryDirectory(dir='runs') as folder:
            root=Path(folder).resolve()
            atomic_json(root/'result.json',dict(backend_id='backend.matlab_spatial',model_id='matlab_serial_bending_v1',data={'contract':'family.backend_data'}))
            atomic_json(root/'resolved_physics.json',{});atomic_json(root/'experiment_scene.json',{})
            rows=[dict(time_s=.01),dict(time_s=.02),dict(time_s=.03)]
            (root/'trajectory.json.gz').write_bytes(gzip.compress(json.dumps(rows).encode()))
            registered={p.name:dict(sha256=file_hash(p)) for p in root.iterdir()}
            source=_source(root,registered,'result.json','matlab')
            self.assertEqual(source[0],root)
            self.assertEqual(_schedule(rows,.01,.03,60)[2],[0,1])
            engine=MagicMock();engine.getframe.return_value={'cdata':[]}
            capture_matlab(engine,root,root,[0,2],25)
            self.assertEqual([c.args[1] for c in engine.tf_view.call_args_list],[1.,3.])
            engine.tf_run.assert_not_called();self.assertEqual(engine.close.call_count,2)


if __name__=='__main__':unittest.main()
