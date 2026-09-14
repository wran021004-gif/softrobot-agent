"""Focused framework regressions; test types are explicit in names/docstrings."""
import gzip
import json
import unittest
from unittest.mock import patch, Mock
from uuid import uuid4
from tools.spec_tools import ROOT
from tools.state_io import atomic_json, read
from tools.artifact_tools import file_hash
from tools.public_services import ServiceSession
from tools.public_feedback import normalize

CALLER = dict(actor_id='framework-fixture', origin='agent', transport='offline_native_fixture')


def session(permissions=('analysis','read_evidence'), budget=20):
    s = ServiceSession(ROOT/'runs/framework_tests'/uuid4().hex)
    s.create(dict(profile_id='framework-test', permissions=list(permissions), tool_calls=budget))
    return s


def call(s, name, args):
    return s.invoke(dict(tool_id=name, arguments=args, reason='Framework acceptance', evidence=[]), caller=CALLER)


def saved(s, contacts=1, duration=4.):
    folder=s.root/'saved';folder.mkdir()
    rows=[dict(time_s=3+i*.01,solver_time_s=2.99+i*.01,qpos_rad=[0],qvel_rad_s=[0],
        solver_tendon_length_m=[1],solver_actuator_force_n=[0],command_m=[1],solver_contact_count=contacts)
        for i in range(11)]
    with gzip.open(folder/'trajectory.json.gz','wt',encoding='utf8') as f: json.dump(rows,f)
    p=dict(model_id='matlab_tdcr_planar_dynamic_v1',mass=[.1],fmax=20,kp=1000,length=1,offsets=[[0,.01]],natural=[0],stiffness=[.1],damping=[.1])
    if duration is not None:p['duration']=duration
    atomic_json(folder/'shared_input.json',p)
    atomic_json(folder/'result.json',dict(backend='matlab',complete=False))
    state=s.load()
    for path in folder.iterdir():state['evidence'][path.relative_to(s.root).as_posix()]=dict(sha256=file_hash(path))
    atomic_json(s.root/'state.json',state)
    return 'saved/result.json'


class SemanticRegressions(unittest.TestCase):
    def test_injected_incomplete_cannot_fail_task_or_model(self):
        for solver in ('failed','incomplete','not_run','unknown'):
            for success in (False,True):
                result=normalize('dynamics.simulate_candidate',dict(status='completed',data=dict(
                    complete=False,computation_status=solver,execution_completed=True,
                    canonical_task_success=success,model_task_success=success)),call_id='fixture',caller=CALLER)
                self.assertEqual(result['task_status'],'NOT_ASSESSED')
                self.assertEqual(result['analysis_status'],'NOT_ASSESSED')
                self.assertNotEqual(result['solver_status'],'COMPLETED')

    def test_injected_contact_only_and_no_event(self):
        for contacts in (0,1):
            s=session();ref=saved(s,contacts)
            result=call(s,'diagnostics.saved_trajectory',dict(result_ref=ref,backend='matlab',entity='contact'))
            self.assertEqual(result['execution_status'],'completed',result)
            data=read(s.root/result['details_ref'])
            self.assertEqual(len(data['events']),contacts)
            self.assertEqual(data['queries'],[])
            self.assertAlmostEqual(data['numerical']['remaining_duration_s'],.9)

    def test_injected_missing_duration_is_unknown(self):
        s=session();ref=saved(s,duration=None)
        r=call(s,'diagnostics.saved_trajectory',dict(result_ref=ref,backend='matlab',entity='tendon_0'))
        self.assertIsNone(read(s.root/r['details_ref'])['numerical']['remaining_duration_s'])


class ExtensionTests(unittest.TestCase):
    def test_catalog_bindings_and_unimplemented_declarations(self):
        from tools.tool_registry import service_tools,ServiceTool
        from tools.public_catalog import entries,native_tools
        from tools.dynamic_actions import BINDINGS
        from schemas.dynamic_workbench import TOOLS
        from schemas.public_tools import PCCJacobian
        self.assertEqual(set(BINDINGS),set(TOOLS))
        for tool in service_tools().values():self.assertTrue(callable(tool.resolve()))
        definitions=service_tools()
        definitions['analysis.future']=ServiceTool('analysis.future',PCCJacobian,'analysis','Planned declaration',None)
        with patch('tools.tool_registry.service_tools',return_value=definitions):
            self.assertFalse(entries()['analysis.future']['implemented'])
            self.assertNotIn('analysis__future',[t['function']['name'] for t in native_tools('services')])
            rejected=call(session(),'analysis.future',dict(length_m=1.,bend_rad=[0.,0.]))
            self.assertEqual(rejected['execution_status'],'rejected')

    def test_native_math_extension_discovery_call_cache_read(self):
        from tools.public_catalog import native_tools
        s=session()
        tool=next(t['function'] for t in native_tools('services') if t['function']['name']=='analysis__pcc_condition')
        args=dict(length_m=1.,bend_rad=[0.,0.],reason='Geometric conditioning',evidence=[])
        output=s.apply_tool_call(dict(name=tool['name'],arguments=json.dumps(args)),caller=CALLER)
        self.assertEqual(output['execution_status'],'completed',output)
        data=read(s.root/output['details_ref'])
        self.assertEqual(data['singular_values_m_per_rad'],[.5,.5])
        self.assertEqual(data['condition_number'],1.)
        self.assertEqual(output['task_status'],'NOT_ASSESSED')
        with patch('tools.service_execution.execute',side_effect=AssertionError('Cached result must not execute')):
            again=call(s,'analysis.pcc_condition',dict(length_m=1.,bend_rad=[0.,0.]))
        self.assertTrue(again['cost']['cache_hit'])
        page=call(s,'evidence.read_json',dict(evidence_ref=output['details_ref'],pointer='/rank'))
        self.assertEqual(read(s.root/page['details_ref'])['content'],2)
        self.assertEqual(s.load()['used']['tool_calls'],3)
        denied=call(session(permissions=('read_evidence',)),'analysis.pcc_condition',dict(length_m=1.,bend_rad=[0.,0.]))
        self.assertEqual(denied['error']['category'],'permission')

    def test_injected_worker_timeout_keeps_charge(self):
        import subprocess
        s=session()
        with patch('tools.service_execution.subprocess.run',side_effect=subprocess.TimeoutExpired('worker',.01)):
            out=call(s,'analysis.pcc_condition',dict(length_m=1.,bend_rad=[0.,0.]))
        self.assertEqual(out['error']['code'],'TIMEOUT')
        self.assertEqual(s.load()['used']['tool_calls'],1)

    def test_model_capabilities_units_and_missing_quantity(self):
        from tools.model_provider import PCCModel
        model=PCCModel(.3,[0,0])
        for query,error in ((dict(quantity='mass_matrix',units='kg'),'MODEL_QUANTITY_UNAVAILABLE'),
                            (dict(quantity='tip',units='mm'),'UNIT_MISMATCH')):
            with self.assertRaisesRegex(ValueError,error):model.get(query)

    def test_independent_rule_requires_only_count_and_tracks_missing_failure(self):
        for count,expected in ((1,'EVENTS_FOUND'),(0,'NO_EVENT'),(None,'MISSING_DATA'),(-1,'EXECUTION_FAILED')):
            s=session();ref=saved(s)
            path=s.root/'saved/trajectory.json.gz'
            # Only one declared signal, no tendon/joint data needed by this rule.
            rows=[dict(solver_time_s=.1,**({'solver_contact_count':count} if count is not None else {}))]
            with gzip.open(path,'wt',encoding='utf8') as f:json.dump(rows,f)
            state=s.load();state['evidence']['saved/trajectory.json.gz']['sha256']=file_hash(path);atomic_json(s.root/'state.json',state)
            out=call(s,'diagnostics.signal_rule',dict(result_ref=ref,backend='matlab'))
            data=read(s.root/out['details_ref']);self.assertEqual(data['status'],expected)
            self.assertEqual(out['execution_status'],'failed' if expected=='EXECUTION_FAILED' else 'completed')
            if count==1:
                self.assertEqual(data['events'][0]['sample_index'],0)
                self.assertEqual(data['source_hashes']['saved/trajectory.json.gz'],file_hash(path))
                self.assertEqual(data['events'][0]['causal_hypotheses'],[])
            not_applicable=call(s,'diagnostics.signal_rule',dict(result_ref=ref,backend='matlab',entity='tip'))
            self.assertEqual(not_applicable['analysis_status'],'NOT_APPLICABLE')


def evaluation_config(mode='C1'):
    from tools.task_context import development_context
    from schemas.exploration import ExplorationControl
    from schemas.design_spec import DesignSpec
    return dict(authorization='User framework small development acceptance',permissions=['simulate'],backends=['mujoco'],
        controller_modes=['C1','C2'],task_context=development_context(ROOT/'configs/framework/reach_dev.yaml'),
        design=DesignSpec(robot_family='tendon_driven_continuum',sections=1,segments=8,total_length_m=.3,
            body_radius_m=.02,tendon_count=4,tendon_routing_radius_m=.018),
        control=ExplorationControl(mode=mode),bounds={'control.bend_z_rad':[-1.5,1.5]},
        max_evaluations=2,max_calls=8,wall_s=20.,per_evaluation_timeout_s=5.)


class BoundaryTests(unittest.TestCase):
    def test_injected_legacy_campaign_evaluator_and_proposal_adapters(self):
        from tools.optimization_interfaces import CampaignEvaluator,MatlabCoordinateProposal,coordinate_proposal
        book=Mock();book.ledger={'used':{'matlab_dynamic':0}}
        def solve(cid,backend,purpose):
            self.assertEqual((cid,backend,purpose),('specimen','matlab','search:adapter'))
            book.ledger['used']['matlab_dynamic']+=1
            return dict(complete=False,computation_status='failed',position_error_m=0.,canonical_task_success=False)
        book.simulate.side_effect=solve
        result=CampaignEvaluator(book,'matlab').evaluate({'candidate_id':'specimen'},'search:adapter')
        self.assertEqual(result.status,'INCOMPLETE');self.assertIsNone(result.score)
        self.assertEqual(result.actual_evaluations,1)
        state=dict(best=[.5,.25],iteration=1,step=.1)
        expected=dict(x=[.4,.25],axis=1,direction=-1,algorithm='bounded_coordinate_pattern_local_v1')
        self.assertEqual(coordinate_proposal(state),expected)
        receipt={};book.reserve.return_value=(receipt,True)
        book.backends.engine.return_value.tdcr_search_step.return_value=json.dumps(expected)
        self.assertEqual(MatlabCoordinateProposal(book).propose(state,'adapter'),expected)
        book.finish.assert_called_once_with(receipt,proposal=expected)
        book.reserve.return_value=({'proposal':expected},False)
        self.assertEqual(MatlabCoordinateProposal(book).propose(state,'adapter'),expected)
        self.assertEqual(book.backends.engine.return_value.tdcr_search_step.call_count,1)

    def test_controller_lifecycle_reset_observations_compatibility(self):
        from controllers.registry import ControllerRuntime
        from tools.reach_dynamics import make_controller
        from tools.design_compiler import build_robot_ir
        cfg=evaluation_config('C2');context=cfg['task_context'];ir=build_robot_ir(cfg['design'])
        c=make_controller(ir,context.task,cfg['control'])
        with self.assertRaisesRegex(ValueError,'CONTROLLER_BACKEND_UNSUPPORTED'):ControllerRuntime(c,'matlab',.002)
        run=ControllerRuntime(c,'mujoco',.002)
        with self.assertRaisesRegex(ValueError,'NOT_RUNNING'):run.command(0,{})
        run.start()
        with self.assertRaisesRegex(ValueError,'OBSERVATION_MISSING'):run.command(0,{})
        first=run.command(0,dict(step=0,tip_position_m=[.3,0,0]))
        with self.assertRaisesRegex(ValueError,'TIME_MISMATCH'):run.command(.1,dict(step=1,tip_position_m=[.3,0,0]))
        run.finish();run.start()
        self.assertEqual(first,run.command(0,dict(step=0,tip_position_m=[.3,0,0])))
        self.assertEqual(len(c.updates),1)
        previous=c.initial_target.tendon_target_lengths_m
        self.assertLessEqual(max(abs(a-b) for a,b in zip(first.tendon_target_lengths_m,previous)),c.parameters.max_command_update_m+1e-12)

    def test_injected_evaluation_search_budget_recovery_and_frozen_task(self):
        from tools.evaluation_runtime import EvaluationSession
        from tools.optimization_interfaces import ParameterSpace
        from tools.search_runtime import search
        backend=Mock()
        backend.simulate.return_value=dict(complete=True,computation_status='completed',position_error_m=.02,canonical_task_success=False)
        root=ROOT/'runs/framework_tests'/uuid4().hex
        runtime=EvaluationSession(root,backend);cfg=evaluation_config();runtime.create(cfg)
        space=ParameterSpace(['control.bend_z_rad'],cfg['bounds'])
        result=search(root/'search.json',space,{'control.bend_z_rad':cfg['control'].bend_z_rad},runtime,max_trials=2)
        self.assertEqual(result['actual_evaluations'],2)
        self.assertEqual(backend.simulate.call_count,2)
        again=search(root/'search.json',space,{'control.bend_z_rad':cfg['control'].bend_z_rad},runtime,max_trials=2)
        self.assertEqual(result,again)
        with self.assertRaisesRegex(ValueError,'BUDGET_EXHAUSTED'):runtime.evaluate({'control.bend_z_rad':0})
        with self.assertRaisesRegex(ValueError,'PARAMETER_NOT_AUTHORIZED'):runtime.evaluate({'task.target_m':0})
        state,_=runtime.load();row=next(iter(state['trials'].values()));row['status']='reserved';row.pop('outcome')
        atomic_json(root/'state.json',state)
        backend.simulate.side_effect=AssertionError('No replay')
        recovered=runtime.evaluate(result['trials'][0]['parameters'])
        self.assertEqual(recovered.actual_evaluations,0)
        self.assertEqual(runtime.load()[0]['used']['evaluations'],2)
        other=EvaluationSession(ROOT/'runs/framework_tests'/uuid4().hex,Mock());other.create(cfg)
        with self.assertRaisesRegex(ValueError,'SEARCH_IDENTITY_CHANGED'):
            search(root/'search.json',space,{'control.bend_z_rad':cfg['control'].bend_z_rad},other,max_trials=2)

    def test_injected_interruption_without_seal_retains_cost(self):
        from tools.evaluation_runtime import EvaluationSession
        backend=Mock();backend.simulate.side_effect=KeyboardInterrupt('injected process interruption')
        runtime=EvaluationSession(ROOT/'runs/framework_tests'/uuid4().hex,backend);runtime.create(evaluation_config())
        with self.assertRaises(KeyboardInterrupt):runtime.evaluate({})
        outcome=runtime.evaluate({})
        self.assertEqual(outcome.status,'INCOMPLETE');self.assertIsNone(outcome.score)
        self.assertEqual(backend.simulate.call_count,1)
        self.assertEqual(runtime.load()[0]['used']['evaluations'],1)
        self.assertEqual(runtime.load()[0]['used']['wall_s'],5.)

    def test_invalid_and_partial_scores_do_not_rank(self):
        from tools.optimization_interfaces import evaluation_from_result
        for complete,score in ((False,0),(True,float('nan')),(True,-.1),(True,None)):
            result=evaluation_from_result(dict(complete=complete,computation_status='completed',position_error_m=score,canonical_task_success=True))
            self.assertNotEqual(result.status,'VALID');self.assertIsNone(result.score);self.assertIsNone(result.task_success)


if __name__=='__main__':unittest.main()
