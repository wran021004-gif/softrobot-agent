"""Focused adapter, choice and saved-state alignment checks. No real solve/step."""
from copy import deepcopy
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import time
import unittest
import numpy as np
from schemas.casadi_feedback import ActivityPlan, ControlChoice, CloseoutPlan
from schemas.platform import EvidenceRef, SessionInput
from tools.platform_store import plain
from tools.state_io import atomic_json
from tools.casadi_closed_loop import resolve_candidate, validate_control


BASE=dict(hypothesis='Structure under feedback may differ from failed saved schedule',
    expected_observation='Measure position and velocity feedback',weakening_observation='Holding still fails',
    fixed_conditions='All frozen physical task conditions retained',revision_or_stop_rule='Stop at ceiling',
    disposition='Bounded research choice',limitations=['Sampled simulation only'])


class WiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tools.research_casadi_feedback import prepare, ACTIVITY
        cls.host=prepare();cls.state=cls.host.store.session(ACTIVITY)['state']
        cls.aid=next(iter(cls.state['candidate_sources']))
        cls.ref=EvidenceRef(artifact_id=cls.aid,media_type='application/json')
        cls.source=cls.state['candidate_sources'][cls.aid]
        cls.policy=cls.host.store.session(ACTIVITY)['snapshot']['input']['policy']

    def test_saved_and_nonzero_design_wiring_and_execution_local_initialization(self):
        from extensions.tendon_family.generated_serial import authorize,GeneratorSpace
        from extensions.tendon_family.gvs_nmpc import ReachNMPCController,resolve_gvs_nmpc_control
        from extensions.tendon_family.gvs_profile import prepare_execution
        from extensions.tendon_family.backends import physics_for
        from extensions.tendon_family.scene import assemble
        from extensions.tendon_family.mjcf import compile_xml
        import mujoco
        candidate=deepcopy(self.host.store.artifact(self.ref));candidate.update(d=.6,lengths_m=[.1633,.1067])
        with self.host.store.transaction() as db:fixture=self.host.store.put(db,candidate)
        configs=[];reports=[]
        for ref in (self.ref,fixture):
            cfg,wiring=resolve_candidate(self.host.store,ref,self.source,ControlChoice(candidate=ref),'wiring-fixture',self.policy)
            inp=SessionInput.model_validate(cfg);configs.append(cfg);reports.append(wiring)
            self.assertEqual(wiring['dimensions']['dimensions'],dict(reduced_coordinate=12,reduced_state=24,
                backend_position=48,backend_velocity=48,tendon_input=6,actuator_command=6))
            self.assertEqual(wiring['prediction_design_identity'],wiring['robot_design_identity'])
            self.assertTrue(wiring['eligibility']['eligible']);self.assertFalse(wiring['offline_schedule_used'])
            guess=wiring['dimensions']['numerical_initialization']
            self.assertEqual(guess['measured_initial_state'],[0.]*24)
            self.assertEqual(guess['nominal']['u0'],[.2]*6)
            self.assertFalse(guess['provenance']['historical_states_reused'])
            self.assertEqual(guess['units'],dict(q='rad/m',qdot='rad/(m*s)',tension='N'))
            space=GeneratorSpace.model_validate(inp.policy.candidate_builder.parameters.data)
            authorize(inp,space,{})
            with self.assertRaisesRegex(ValueError,'ALREADY_RESOLVED'):authorize(inp,space,{'lengths_m':[.16,.11]})
            physics=physics_for(inp);scene=assemble(inp,physics)
            path=self.host.store.root/'checks'/('wiring_'+ref.artifact_id[:10]+'.xml');path.parent.mkdir(exist_ok=True)
            _,backend_params=self.host.reg.bind(inp.policy.backend,'backend')
            compile_xml(physics,scene,backend_params,path)
            model=mujoco.MjModel.from_xml_path(str(path));self.assertEqual((model.nq,model.nv,model.nu),(48,48,6))
            self.assertEqual([model.tendon(i).name for i in range(model.ntendon)],candidate['tendon_order'])
            # No mj_step; instantiate controllers with mocked numerical graph only.
            control=ReachNMPCController(inp.policy.controller.parameters.data,inp.task.timing.control_period_s)
            def save(v,k):
                with self.host.store.transaction() as db:return self.host.store.put(db,v)
            with patch('extensions.tendon_family.gvs_nmpc.TrajectoryWorkspace') as workspace:
                prepare_execution(SimpleNamespace(save_artifact=save),control,inp)
                control.configure(physics,resolve_gvs_nmpc_control(inp,physics))
                self.assertEqual(workspace.call_count,1)
                self.assertEqual(plain(workspace.call_args.args[1]),cfg['robot'])
                self.assertEqual(workspace.call_args.kwargs['settling'],cfg['policy']['controller']['parameters']['data']['settling'])
        for name in ('physics_identity','prediction_model_identity','workspace_identity'):
            self.assertNotEqual(reports[0][name],reports[1][name])
        self.assertNotEqual(reports[0]['projection']['resolved_basis'],reports[1]['projection']['resolved_basis'])
        atomic_json(self.host.store.root/'checks/adapter_wiring.json',dict(reports=reports,fixtures=configs,no_simulation_steps=True,no_nmpc_solves=True))

    def test_small_fixed_and_parameterized_model_consistency(self):
        from extensions.tendon_family.gvs_codesign import expression,parameterized
        from extensions.tendon_family.gvs_casadi import GVSCasadiFunctions
        original=self.host.store.artifact(self.source['configuration'])
        candidate=deepcopy(self.host.store.artifact(self.ref));candidate.update(d=.6,lengths_m=[.1633,.1067])
        with self.host.store.transaction() as db:ref=self.host.store.put(db,candidate)
        cfg,_=resolve_candidate(self.host.store,ref,self.source,ControlChoice(candidate=ref),'consistency-fixture',self.policy)
        fixed=GVSCasadiFunctions(expression(cfg));variable=parameterized(expression(original))
        x=np.r_[np.linspace(-.2,.2,12),np.linspace(-.1,.1,12)];u=np.linspace(.2,.7,6)
        a=fixed.evaluate(x,u);b=variable.evaluate(x,u,.6)
        errors={k:float(np.max(np.abs(a[k]-b[k]))) for k in a}
        for k in a:np.testing.assert_allclose(a[k],b[k],rtol=1e-9,atol=1e-9)
        atomic_json(self.host.store.root/'checks/model_consistency.json',dict(d=.6,state=x.tolist(),tensions_n=u.tolist(),maximum_errors=errors,no_solve=True))

    def test_first_action_control_revision_and_stop_with_failed_replay(self):
        from tools.casadi_feedback_service import plan
        state=deepcopy(self.state);state.update(cutoff_unix=time.time()+10000,plans=[],nlp_solves=0,pilot={'live_model_requests':1},
            research_status='ready',results=[r for r in self.state['results'] if r.get('imported')])
        def artifact(ref):return self.host.store.artifact(ref)
        store=SimpleNamespace(session=lambda *a:dict(state=state),remaining=lambda:dict(remaining=dict(model_calls=16,tool_calls=64,backend_solves=2)),
            transaction=lambda:nullcontext(None),update_state=lambda *a:None,artifact=artifact)
        ctx=SimpleNamespace(store=store,run_id='fixture',input=SessionInput.model_validate(self.host.store.session(self.host.run_id)['snapshot']['input']),
            artifact=artifact,save_artifact=lambda *a:EvidenceRef(artifact_id='a'*64,media_type='application/json'))
        evidence=state['historical']['post_stop_correction']
        for action in ('stop','diagnose','closed_loop'):
            choice=dict(candidate=plain(self.ref)) if action=='closed_loop' else None
            accepted=plan(ctx,ActivityPlan(action=action,supporting_evidence=[evidence],control=choice,**BASE)).detail
            self.assertTrue(accepted['accepted']);self.assertIsNone(accepted['batch'])
            state.update(research_status='ready',plans=[],last_expensive_decision_send=None)
        previous=dict(artifact_id='b'*64,media_type='application/json')
        old=dict(candidate=plain(self.ref),control=plain(ControlChoice(candidate=self.ref)))
        state['results'].append(dict(operation='closed_loop',reference=previous,candidate=plain(self.ref)))
        store.artifact=lambda ref:old if plain(ref)==previous else artifact(ref)
        ctx.artifact=store.artifact
        choice=ControlChoice(candidate=self.ref,holding_tip_speed_weight=.075,preceding_execution=previous)
        _,changes=validate_control(store,state,choice,'control_revision')
        self.assertEqual(changes['exact_weight_changes'],{'holding_tip_speed_weight':{'before':.05,'after':.075}})
        with self.assertRaisesRegex(ValueError,'CHANGED_WEIGHTS'):validate_control(store,state,ControlChoice(candidate=self.ref,preceding_execution=previous),'control_revision')
        self.assertTrue(plan(ctx,ActivityPlan(action='control_revision',supporting_evidence=[previous],control=choice,**BASE)).detail['accepted'])
        with self.assertRaisesRegex(ValueError,'ACTUAL_RETURNED_EVIDENCE'):plan(ctx,ActivityPlan(action='stop',supporting_evidence=[evidence],**BASE))
        self.assertTrue(plan(ctx,ActivityPlan(action='stop',supporting_evidence=[previous],**BASE)).detail['accepted'])


class AlignmentTests(unittest.TestCase):
    def test_failed_stage_returns_partial_state_feedback_without_new_launch(self):
        import gzip,json
        from tools.spec_tools import ROOT
        from tools.casadi_closed_loop import saved_partial_feedback
        from extensions.tendon_family.gvs_profile import profile_input
        folder=ROOT/'runs/stage315_complete_control_20260927'
        summary=json.loads((folder/'public_summary.json').read_text())
        backend=ROOT/summary['backend_folder'];files={p.name:p.read_bytes() for p in backend.iterdir() if p.is_file()}
        rows=json.loads(gzip.decompress(files['trajectory.json.gz']))[:4]
        observations=json.loads(files['controller_observations.json'])[:3]
        observations[-1].pop('actual_tension_n',None)  # attempted stop update was never applied
        result=json.loads((folder/'public_result.json').read_text());result['solver_status']='failed'
        result['data']['data']['reason']='CONTROLLER_STOP_REQUESTED'
        cfg=profile_input('partial-fixture');source=dict(files={k:k for k in files},configuration=cfg,manifest='sealed-fixture')
        store=SimpleNamespace(artifact=lambda ref,raw=False:files[ref] if raw else result)
        receipt=dict(simulation=dict(output='result',execution_id='fixture',execution_status='failed',error='failed stage'))
        with patch('extensions.tendon_family.control_evidence.ControlEvidence') as reader:
            reader.return_value.resolve.return_value=source
            reader.return_value.read_file.side_effect=lambda s,n,d:rows if n=='trajectory.json.gz' else observations
            feedback=saved_partial_feedback(store,receipt)
        self.assertTrue(feedback['available']);self.assertFalse(feedback['profile']['complete'])
        self.assertIsNone(feedback['profile']['sampled_settling']['passed'])
        self.assertEqual(feedback['attempted_control_plans'],3);self.assertEqual(feedback['applied_control_updates'],2)
        self.assertEqual(feedback['termination_reason'],'CONTROLLER_STOP_REQUESTED')
        self.assertEqual(feedback['holding_motion'],[])

    def test_saved_state_jacobian_velocity_without_advancing_simulation(self):
        import json
        import mujoco
        from tools.research_casadi_feedback import RUN
        from extensions.tendon_family.backends import physics_for
        from extensions.tendon_family.gvs_nmpc import resolve_gvs_nmpc_control
        from extensions.tendon_family.gvs_reporting import reconstruct_motion
        fixture=json.loads((RUN/'checks/adapter_wiring.json').read_text())
        inp=SessionInput.model_validate(fixture['fixtures'][1]);physics=physics_for(inp)
        aid=fixture['reports'][1]['candidate']['artifact_id']
        xml=(RUN/'checks'/('wiring_'+aid[:10]+'.xml')).read_bytes()
        model=mujoco.MjModel.from_xml_string(xml.decode());data=mujoco.MjData(model)
        ids=[model.joint(j).id for j in physics['dofs']];vi=model.jnt_dofadr[ids]
        velocity=np.linspace(-.01,.01,48);data.qvel[vi]=velocity;mujoco.mj_forward(model,data)
        J=np.zeros((3,model.nv));Jr=np.zeros_like(J);mujoco.mj_jacSite(model,data,J,Jr,model.site('tip_site').id)
        expected=J@data.qvel
        rows=[dict(time_s=.01,tip_m=data.site_xpos[model.site('tip_site').id].tolist(),qpos_rad=[0.]*48,qvel_rad_s=velocity.tolist())]
        files={'robot.xml':xml,'resolved_physics.json':json.dumps(physics).encode(),
            'control_spec.json':json.dumps(resolve_gvs_nmpc_control(inp,physics)).encode()}
        motion,_=reconstruct_motion(files,rows,inp.task.goal.data['target_m'])
        np.testing.assert_allclose(motion[0]['tip_velocity_m_s'],expected,rtol=0,atol=1e-14)
        self.assertAlmostEqual(motion[0]['tip_speed_m_s'],np.linalg.norm(expected))

    def test_timestamp_input_and_velocity_vector_comparison(self):
        from extensions.tendon_family.gvs_reporting import aligned_predictions
        rows=[dict(time_s=.01,tip_m=[0,0,0])]
        prediction=dict(time_s=.01,frame='world',tip_position_m=[.001,0,0],tip_velocity_m_s=[1,0,0],applied_tension_n=[.2]*6)
        observation=dict(time_s=0.,actual_tension_n=[.2]*6,one_step_prediction=prediction)
        motion=[dict(time_s=.01,tip_velocity_m_s=[0,1,0])]
        aligned,missing=aligned_predictions(rows,[observation],motion)
        self.assertEqual(missing,[]);self.assertAlmostEqual(aligned[0]['velocity_difference_m_s'],2**.5)
        self.assertEqual(aligned[0]['speed_magnitude_difference_m_s'],0.)
        for changed,reason in ((dict(actual_tension_n=[.3]*6),'applied input mismatch'),
            (dict(one_step_prediction=dict(prediction,time_s=.02)),'next execution timestamp missing or ambiguous')):
            aligned,missing=aligned_predictions(rows,[dict(observation,**changed)],motion)
            self.assertEqual(aligned,[]);self.assertEqual(missing[0]['reason'],reason)
        aligned,missing=aligned_predictions(rows,[observation],[])
        self.assertIn('velocity_missing_reason',aligned[0])
        self.assertEqual(missing,[])
        aligned,missing=aligned_predictions(rows,[observation,dict(time_s=.005,one_step_prediction=None)],motion)
        self.assertEqual(aligned,[]);self.assertEqual(missing[0]['reason'],'intervening control update')

    def test_protected_context_and_native_stop(self):
        from tools.research_casadi_feedback import provider_guard,feedback_context_references,protect_context_tool
        from strands.tools.tools import PythonAgentTool
        state=dict(research_status='ready')
        ref=dict(artifact_id='a'*64,media_type='application/json')
        value=dict(tool_use=dict(name='research_plan',input=dict(action='closed_loop'),toolUseId='feedback'),
            result=dict(status='success',content=[dict(text='{"operations":[{"feedback":"new result"}]}')]))
        store=SimpleNamespace(session=lambda *a:dict(state=state),remaining=lambda:dict(remaining=dict(model_calls=4)),
            events=lambda *a:[dict(kind='model_original_tool_feedback',outputs=[ref])],artifact=lambda r:value)
        host=SimpleNamespace(store=store,compatibility=lambda:dict(compatible=True))
        self.assertEqual(feedback_context_references(host),['feedback_0'])
        retrieval=PythonAgentTool('retrieve_context',dict(name='retrieve_context',description='Fixture',
            inputSchema=dict(type='object',properties=dict(reference=dict(type='string')),required=['reference'])),lambda *a:None)
        protect_context_tool(retrieval,['feedback_0'])
        self.assertEqual(retrieval.tool_spec['inputSchema']['json']['properties']['reference']['enum'],['feedback_0'])
        wire=dict(tools=[dict(function=dict(name='research_plan',parameters=CloseoutPlan.model_json_schema()))])
        provider_guard(host,wire)
        state['research_status']='stopped'
        with self.assertRaisesRegex(ValueError,'STOP_NO_MORE_SENDS'):provider_guard(host,wire)


if __name__=='__main__':unittest.main()
