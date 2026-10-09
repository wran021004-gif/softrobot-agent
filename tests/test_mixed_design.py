"""Focused new-path checks. Substituted evaluations are never physical evidence."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import numpy as np
from schemas.design_optimization import DesignOptimizationProblem,Fixed
from schemas.platform import SessionInput
from tools.platform_store import plain
from tools.design_optimization import Allocation,solve,validate_problem,continuous_space,decode,resolved_input
from tools.research_mixed_design import example,configuration,prepare
from extensions.tendon_family.generated_serial import generate,Recipe,dimensions,check_robot
from extensions.tendon_family.finite_templates import catalog,check_robot as finite_check
from tools.platform_tasks import compile_input


class MixedDesignTests(TestCase):
    def test_fixed_integer_conditional_and_exact_simplex(self):
        p=example();p['variables']['terminal_tip_speed_weight']=dict(kind='continuous',bounds=[.1,.1],initial=.1)
        problem,topology=validate_problem(p)
        self.assertIsInstance(problem.variables['terminal_tip_speed_weight'],Fixed)
        for n in (2,4):
            allocation=Allocation(problem.lengths,n)
            for x in (0.,.5,1.):
                lengths=allocation.decode({k:x for k in allocation.initial});self.assertTrue(allocation.valid(lengths))
                self.assertAlmostEqual(sum(lengths),.27,places=14)
            self.assertEqual(len(allocation.active),n-1)
        p['variables']['segment_count']=dict(kind='fixed',value=2.5)
        with self.assertRaises(ValueError):validate_problem(p)
        p=example();p['fixed_tendon_count']=6;p['fixed_actuator_count']=8
        with self.assertRaises(ValueError):validate_problem(p)
        problem,_=validate_problem(example());s=dict(segment_count=2,proximal_tendons=3,distal_tendons=3,material='baseline')
        _,latent=continuous_space(problem,s);latent['length/2']=.5
        with self.assertRaises(ValueError):decode(problem,s,latent)

    def test_explicit_baselines_and_fixed_length_coordinates(self):
        p=example(False);p['lengths']=dict(total_flexible_length_m=.15,baseline_by_count={'2':[.08,.07]},
            fixed_by_count={'2':{'0':.08}})
        problem,_=validate_problem(p);a=Allocation(problem.lengths,2)
        self.assertEqual(a.active,[]);self.assertTrue(a.valid(a.decode({})))
        p['lengths']['baseline_by_count']['2']=[.08,.08]
        with self.assertRaises(ValueError):validate_problem(p)

    def test_archived_compatibility_and_new_routes(self):
        for key,value in catalog()['templates'].items():
            self.assertEqual(finite_check(value['design'],value['discretization']),key)
        for n,p,d in [(2,3,3),(3,4,4),(4,3,4)]:
            recipe=Recipe(segment_count=n,proximal_tendons=p,distal_tendons=d,lengths_m=[.16]+[.11/(n-1)]*(n-1))
            design,mesh,physics=generate(recipe);self.assertEqual(len(physics['dofs']),48)
            self.assertEqual(len(physics['tendons']),p+d);self.assertTrue(np.allclose(physics['transmission'],np.eye(p+d)))
            self.assertNotIn('finite_template',design['metadata']);check_robot(design,mesh)
            self.assertTrue(all(t['pretension_n']==.2 for t in design['tendons']))
        source=catalog()['templates']['T0']['design'];generated=generate(Recipe())[0]
        self.assertEqual([t['points'][0] for t in source['tendons']],[t['points'][0] for t in generated['tendons']])
        changed=generate(Recipe(section_scale=1.02,routing_scale=1.01))[0]
        self.assertEqual(generate(Recipe(section_scale=1.02,routing_scale=1.01))[0],changed)
        self.assertAlmostEqual(changed['components'][1]['guide_holes']['far_h0'][1]/source['components'][1]['guide_holes']['far_h0'][1],1.01)

    def test_full_dispatch_and_numerical_initialization(self):
        problem,_=validate_problem(example());s=plain(problem.method.initial_structures[-1]);_,latent=continuous_space(problem,s)
        cfg=resolved_input(problem,decode(problem,s,latent),'offline-four',configuration()['policy'])
        compile_input(cfg);inp=SessionInput.model_validate(cfg);dims=dimensions(inp)
        self.assertEqual(dims['dimensions']['tendon_input'],7)
        numerical=dims['numerical_initialization'];self.assertEqual(numerical['nominal']['u0'],[.2]*7)
        self.assertFalse(numerical['provenance']['reused']);self.assertTrue(all(v==0 for v in numerical['measured_initial_state']))
        from extensions.tendon_family.gvs_profile import prepare_execution
        class Context:
            def save_artifact(self,value,kind):return {'artifact_id':'0'*64,'media_type':'application/json'}
        class Controller:pass
        controller=Controller();prepare_execution(Context(),controller,inp)
        self.assertEqual(controller.profile['numerical']['tendon_order'],dims['tendon_input_order'])
        from tools.parameter_catalog import effective_catalog
        self.assertTrue(all(r['technical_support']['supported'] for r in effective_catalog(cfg)['parameters']))

    def test_feedback_changes_proposal_and_fixed_all_evaluation(self):
        def evaluator(problem,values,candidate_id):
            score=.1 if values['segment_count']==3 else .03
            return dict(status='evaluated',acceptance=dict(accepted=False,status='valid_failure',metrics=dict(
                terminal_error_m=score,holding_max_error_m=score,holding_max_speed_m_s=score)),evidence=dict(substituted=True))
        result=plain(solve(example(),evaluator=evaluator))
        self.assertEqual(len(result['evaluated']),4)
        third=result['evaluated'][2];self.assertEqual(third['phase'],'feedback_coordinate')
        self.assertEqual(third['resolved']['segment_count'],4)
        self.assertEqual(third['used_feedback'],result['evaluated'][1]['candidate_id'])
        self.assertNotEqual(third['resolved']['parameters']['lengths_m'],result['evaluated'][1]['resolved']['parameters']['lengths_m'])
        p=example(False);p['lengths']['free']=False;p['variables']['holding_tip_speed_weight']=dict(kind='fixed',value=.05)
        r=plain(solve(p,evaluator=evaluator));self.assertEqual(len(r['evaluated']),1)
        self.assertEqual(r['termination_reason'],'all_design_variables_fixed')

    def test_generated_sealed_simulation_receipt_not_repeated(self):
        from tools.research_execution import invoke
        from tools.platform_host import Host
        from tools.design_optimization import ReceiptEvaluator
        root=Path(__file__).resolve().parents[1]/'runs';root.mkdir(exist_ok=True)
        from uuid import uuid4
        folder=root/('mixed_offline_'+uuid4().hex);folder.mkdir()
        self.enterContext(patch('tools.platform_store.ROOT',folder));h=prepare(folder/'store',offline=True)
        problem,_=validate_problem(example());s=plain(problem.method.initial_structures[-1]);_,latent=continuous_space(problem,s)
        values=decode(problem,s,latent);p=deepcopy(configuration()['policy']);p.update(allowed_tools=[],
            tool_bindings={'simulation.run':'1.0.0'},operation_allowances={'simulation.run':dict(timeout_s=30.,reserve_s=30.)})
        cfg=resolved_input(problem,values,'offline-receipt',p);child=Host(h.store.root,'offline-receipt');child.create(cfg);child.resume()
        # A demonstrated sealed backend failure must also be preserved and
        # charged. Recovery must not turn it into another physical launch.
        def configure(controller,physics,plan):
            controller.physics=physics;controller.plan=plan;controller.observations=[]
        with patch('extensions.tendon_family.gvs_nmpc.DeadlineReachNMPCController.configure',configure),patch('extensions.tendon_family.backends.MujocoBackend.run',side_effect=RuntimeError('substituted backend interruption')) as backend:
            first=invoke(child,'simulation.run',dict(candidate_id='offline-receipt',changes={}),request_id='complete-simulation')
            second=invoke(child,'simulation.run',dict(candidate_id='offline-receipt',changes={}),request_id='complete-simulation')
            self.assertEqual(first,second);self.assertEqual(backend.call_count,1)

    def test_complete_generated_profile_chain_with_static_substitute(self):
        from extensions.tendon_family.geometry import geometry
        from tools.design_optimization import ReceiptEvaluator
        from uuid import uuid4
        root=Path(__file__).resolve().parents[1]/'runs';folder=root/('mixed_offline_'+uuid4().hex);folder.mkdir()
        self.enterContext(patch('tools.platform_store.ROOT',folder));h=prepare(folder/'store',offline=True)
        launches=[]
        def configure(controller,physics,plan):
            controller.physics=physics;controller.plan=plan;controller.observations=[]
        def substitute(backend,timeout_s):
            launches.append(True)
            from extensions.tendon_family.mjcf import compile_xml
            p,s=backend.physics,backend.scene;compile_xml(p,s,backend.config,backend.folder/'robot.xml')
            g=geometry(p,np.zeros(len(p['dofs'])));rows=[];observations=[]
            for i in range(35):
                observations.append(dict(time_s=i*.01,optimization_nonconverged=False,solver_failed=False,
                    solver_error=None,failure_response_used=False,deadline_missed=False,update_wall_s=0.,
                    graph_construction_s=0.,plan_accepted=True,optimization_constraint_violation=0.))
                rows.append(dict(time_s=(i+1)*.01,solver_time_s=i*.01,tip_m=g['tip'].tolist(),qpos_rad=s['qpos_rad'],
                    qvel_rad_s=s['qvel_rad_s'],tendon_length_m=g['lengths'].tolist(),tendon_length_change_m=[0.]*len(p['tendons']),
                    tendon_length_rate_m_s=[0.]*len(p['tendons']),tension_n=[.2]*len(p['tendons']),desired_tension_n=[.2]*len(p['tendons']),
                    solver_qfrc_actuator_nm=[0.]*len(p['dofs']),external_torque_nm=[0.]*len(p['dofs'])))
            backend.timings['solve']=0.;return rows,observations,True,'STATIC_OFFLINE_SUBSTITUTE',0
        p=example();p['budget']['max_evaluations']=1;p['method']['initial_structures']=p['method']['initial_structures'][1:]
        with patch('extensions.tendon_family.gvs_nmpc.DeadlineReachNMPCController.configure',configure),patch(
                'extensions.tendon_family.backends.MujocoBackend.solve',substitute) as backend:
            result=plain(solve(p,h));recovered=plain(solve(p,h))
            self.assertEqual(len(launches),1);self.assertEqual(result['evaluated'],recovered['evaluated'])
            self.assertEqual(result['evaluated'][0]['execution_status'],'valid_failure')
            self.assertEqual(result['evaluated'][0]['resolved']['tendon_count'],7)
