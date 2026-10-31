"""Small real MuJoCo constrained mechanics checks; no Provider or campaign."""
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
import json
import unittest
import numpy as np
import mujoco
from tools.platform_store import plain
from tools.state_io import digest
from extensions.tendon_family.family_space import parse_space,resolved_request
from extensions.tendon_family.generated_serial import generate_family
from extensions.tendon_family.passive import PassiveModel,material_point
from extensions.tendon_family.passive_equilibrium import solve,StaticProblem

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'runs/stage2_validation'
OUT.mkdir(parents=True,exist_ok=True)


def physical_fixture():
    space=plain(parse_space(json.loads((ROOT/'configs/research/family_space_s7.json').read_text())))
    request=dict(version='serial_family_generation_v2',family_space_identity=digest(space),
        segment_count=1,tendon_count=1,segments={'0':dict(cells=2)})
    _,_,active=generate_family(dict(space=space,request=request))
    length=active['reference_lengths_m'][0]-.0002
    space['passive_payout_domains_m']={'tendon_0':dict(minimum=length-.001,maximum=length+.01,default=length)}
    space=plain(parse_space(space));request['family_space_identity']=digest(space)
    request=resolved_request(space,request)
    design,mesh,physics=generate_family(dict(space=space,request=request))
    problem=dict(mode='passive_unilateral_equilibrium',mount_position=[0.,0.,1.],mount_rotation=np.eye(3).tolist(),
        gravity=[0.,0.,0.],loads=[dict(name='unloaded',material_s=.5,force_world_n=[0.,0.,0.]),
            dict(name='lateral',material_s=.5,force_world_n=[0.,.01,0.])],monitor_s=[.5],baseline_load='unloaded',
        observations=[dict(name='middle_response',quantity='material_displacement',load_condition='lateral',material_s=.5,maximum=.001),
            dict(name='tip_motion',quantity='tip_displacement',load_condition='lateral',material_s=.5,maximum=.001),
            dict(name='decoupling_ratio',quantity='displacement_ratio',load_condition='lateral',material_s=.5,maximum=2.)])
    return space,request,design,mesh,physics,problem


def prepared_host():
    """Fresh frozen engineering Study, with original ledger and explicit grant."""
    from tools.research import core
    from tools.research.config import _reference
    from tools.research.state import state,save,update
    space,request,_,_,_,problem=physical_fixture()
    name='stage2-constrained-'+uuid4().hex[:8];folder=ROOT/'runs'/name;folder.mkdir(parents=True)
    task=_reference(ROOT/'tasks/bf7_shared_reach_v1_central_high.json','task',dict(references={}))
    task['task'].update(physical_problem=problem,actuator_channels=[],task_id=name)
    (folder/'task.json').write_text(json.dumps(task),encoding='utf-8')
    (folder/'space.json').write_text(json.dumps(space),encoding='utf-8')
    cfg=json.loads((ROOT/'configs/research/study_s125_cold.json').read_text())
    cfg.update(study_id=name,task=str(folder/'task.json'),family_space=str(folder/'space.json'),control='control.json',
        execution_instructions='Research the frozen passive assembly through mechanism_research. Choose load conditions, constrained observables, legal physical parameters and finite mathematical effort. Compare constrained motion and load compliance. Decide whether evidence supports a structural proposal; only you choose whether to generate it. Passive independent dynamic acceptance is not registered; do not claim SELECT eligibility. Use English.',
        mathematical_methods=dict(mechanism_structure_v1='Stage II authorized bounded real constrained mathematics'),
        family_sensitivity_variables=dict(version='family_sensitivity_v2',variables=['segments.*.young_pa','payout_lengths_m.*']))
    cfg['budgets']['mathematical_evaluations']=12
    cfg['research_decisions'].update(analysis_interface='scientific_question_v4',architecture='english_decision_v1',
        tool_schema_policy=dict(version='research_information_flow_v1'),conversation_policy=dict(version='recent_round_trace_v1',trace_limit=8),
        role_policy=dict(version='research_roles_v2',main=dict(thinking='disabled',reasoning_effort='none'),reporter=dict(thinking='enabled',reasoning_effort='low')),
        language_policy=dict(version='english_sources_v1',authored_language='en'))
    cfgpath=ROOT/'configs/research'/('._'+name+'.json');cfgpath.write_text(json.dumps(cfg),encoding='utf-8')
    try:h=core.prepare(cfgpath,folder)
    finally:cfgpath.unlink()
    core.bind(h)
    pilot=state(h)['pilot'];pilot.update(session_handoff_live_admitted=True,session_handoff_boundary='request_feedback');update(h,pilot=pilot)
    scope=dict(study_id=h.run_id,resolved_identity=state(h)['spec']['resolved_identity'],execution_scopes=['registered mathematics'])
    save(h,dict(user_approval='Stage II user authorization: bounded real numerics, no autonomous Study.',scope=scope,scope_identity=digest(scope)),'formal_study_authorization')
    request['family_space_identity']=state(h)['spec']['family_space_identity']
    from tools.research.design import generate_candidate
    generated=generate_candidate(h,request,dict(origin='stage2_real_engineering'))
    assert generated['status']=='generated',generated
    return h,generated['candidate']


def passive_question(operation='inspect',quantity='tangent_compliance',budget=1):
    return dict(version='scientific_question_v4',domain='structure',structure=dict(operation=operation,
        physical_problem='passive_unilateral_equilibrium',effect_semantics='re_equilibrated_passive_response' if quantity=='re_equilibrated_position_response' else 'mechanism_effect',
        operating_point='re_equilibrated',control_treatment='no_active_control',load_condition='lateral',
        target=dict(quantity=quantity,reduction='norm',goal='increase',material_s=.5),
        parameter_paths=['segments.0.young_pa'] if operation in ('differentiate','optimize') else [],requested_budget=budget))


class ConstrainedMechanicsTests(unittest.TestCase):
    def test_real_active_two_scale_native_path(self):
        from tests.research.test_r3_b_stage1 import integrated_host,structure_question
        from tools.research.scientific_intent import compile_question
        from tools.research import analysis
        from tools.research.state import state
        h,c=integrated_host();q=structure_question()
        request=compile_question(h,q,tool_use_id='real-active-difference')
        self.assertEqual(request['status'],'ready',request)
        result=analysis.dispatch(h,request['request'],'real-active-two-scale',guard=lambda *a:None,origin='engineering_preflight')
        self.assertEqual(result['status'],'computed',result)
        self.assertEqual(result['structure_research']['cost']['model_builds'],5)
        self.assertEqual(result['structure_research']['cost']['physics_steps'],0)
        from extensions.tendon_family.mjcf import compile_xml
        from extensions.tendon_family.backends import physics_for
        from extensions.tendon_family.scene import assemble_physical
        from schemas.platform import SessionInput
        from io import BytesIO
        inp=SessionInput.model_validate(h.store.artifact(c)['configuration']);physics=physics_for(inp)
        scene=assemble_physical(inp,physics);scene['control']=dict(tension_execution_mode='actuator_realistic')
        xml=BytesIO();compile_xml(physics,scene,None,xml);realistic=mujoco.MjModel.from_xml_string(xml.getvalue().decode())
        self.assertEqual(realistic.nu,len(physics['tendons']))
        result['realistic_compilation_check']=dict(model_builds=1,nu=realistic.nu,physics_steps=0)
        (OUT/'active_two_scale.json').write_text(json.dumps(dict(scope='Real native worker, no synthetic numerical matrices',result=result),indent=2),encoding='utf-8')

    def test_real_shared_worker_v4_feedback_and_generation(self):
        from unittest.mock import patch
        from tests.research.test_recent_round_tools import run_fixture
        from tests.research.test_p63g3_action_handoff import diagnosis
        from tests.research.test_information_flow import packet,generation
        from tools.research.state import state
        from tools.research.research_context import agent_decision_brief
        h,c=prepared_host();spec=deepcopy(state(h)['spec'])
        diagnose=diagnosis(c,'mechanism_research')
        diagnose.update(hypothesis='A fixed-payout active set may limit tip motion while retaining material-point compliance.',
            expected_observation='Qualified equilibria and measured constrained compliance under the frozen lateral load.',
            weakening_observation='Unqualified equilibrium or no useful decoupling.',fixed_conditions='Same assembly, payout and frozen load bindings.',
            interpretation='Local numerical mechanism evidence; independent dynamic acceptance remains unmeasured.')
        with patch('tools.research.reporter._wire',side_effect=ValueError('OFFLINE_REPORTER_UNAVAILABLE')),\
                patch('tools.research.reporter.interpretation_priority',return_value='stage2_new_mechanism_result'):
            wires=run_fixture(h,[('research_route',dict(tool='research_plan',action='diagnose')),
                ('research_plan',diagnose),
                ('research_analysis',passive_question(quantity='constraint_tip_row_residual')),
                ('research_analysis',passive_question()),
                ('research_analysis',passive_question('differentiate','re_equilibrated_position_response',5)),None])
        s=state(h);self.assertEqual(s['spec'],spec);self.assertEqual(s['mathematical_evaluations'],7)
        self.assertEqual(len(s['analysis_results']),3)
        raw=h.store.artifact(s['analysis_results'][-1]);self.assertEqual(raw['status'],'computed',raw)
        sensitivity=raw['structure_research']['parameter_sensitivities'][0]
        self.assertTrue(sensitivity['consistency']['passed'],sensitivity)
        self.assertTrue(sensitivity['implicit_sensitivity']['baseline_included'])
        self.assertEqual(sensitivity['implicit_sensitivity']['status'],'regular_implicit_gradient',sensitivity)
        self.assertEqual(raw['structure_research']['cost']['physics_steps'],0)
        self.assertEqual(raw['structure_research']['cost']['equilibrium_solves'],10)
        l0=packet(wires[-1]);latest=l0['mathematical_research']['latest_result']
        self.assertEqual(latest['status'],'computed');self.assertEqual(latest['effect_semantics'],'re_equilibrated_passive_response')
        self.assertEqual(latest['structure_research']['registered_acceptance'],'not_registered')
        self.assertEqual(len(latest['structure_research']['task_observations']),3)
        self.assertEqual(l0['reporter_findings'][-1]['status'],'unavailable')
        from tools.research.scientific_intent import compile_question
        before=s['mathematical_evaluations']
        for change in (dict(control_treatment='fixed_absolute_tensions'),dict(load_condition='unfrozen'),dict(effect_semantics='closed_loop_performance')):
            q=passive_question();q['structure'].update(change)
            self.assertEqual(compile_question(h,q,tool_use_id='unsupported-passive')['status'],'unsupported')
        self.assertEqual(state(h)['mathematical_evaluations'],before)
        direction=raw['structure_research']['structure_direction'];self.assertTrue(direction['proposal_only'])
        p=generation(h);p['generation']=direction['generation_handoff']['generation'];p['supporting_evidence']=[s['analysis_results'][-1]]
        p.update(hypothesis='A small reduction of the registered modulus may increase the frozen material-point displacement.',
            expected_observation='Legal rebuilt structure matching the numerical proposal.',weakening_observation='Invalid structure or failed later independent validation.',
            fixed_conditions='All other frozen physical and assembly parameters.',interpretation='Adopt this local proposal for generation; task acceptance remains unmeasured.')
        p['decision']['selected_candidate']=c
        with patch('tools.research.reporter._wire',side_effect=ValueError('OFFLINE_REPORTER_UNAVAILABLE')):
            generated=run_fixture(h,[('research_route',dict(tool='research_plan',action='generate')),('research_plan',p),None],id_offset=len(wires))
        self.assertEqual(len(state(h)['candidates']),2)
        attribution=agent_decision_brief(h)['mechanism_research']
        self.assertTrue(attribution['suggestion_adopted']);self.assertTrue(attribution['formal_candidate_created'])
        from extensions.reference.implementation import evaluate_reach
        from schemas.platform import TaskDefinition
        with self.assertRaisesRegex(ValueError,'NOT_REGISTERED'):
            evaluate_reach(TaskDefinition.model_validate(h.store.artifact(c)['configuration']['task']),None,None,None,None)
        self.assertIsNone(state(h)['selected']);self.assertFalse(state(h)['physical_replays'])
        import re
        for wire in wires+generated:
            text=json.dumps(wire)
            self.assertIsNone(re.search(r'(?<![0-9a-f])[0-9a-f]{40,64}(?![0-9a-f])',text,re.I))
            self.assertNotIn('x-research-',text)
            tail=packet(wire)
            self.assertNotIn('Jlength',json.dumps(tail));self.assertNotIn('KKT_condition',json.dumps(tail))
        (OUT/'passive_wire.json').write_text(json.dumps(dict(scope='Actual SDK/Mock HTTP; numerical workers use real MuJoCo. Zero real Provider requests.',
            question=passive_question('differentiate','re_equilibrated_position_response',5),wire=wires[-1],generation_wire=generated[-1]),indent=2),encoding='utf-8')
        (OUT/'passive_sensitivity.json').write_text(json.dumps(dict(scope='Real compiled models and constrained equilibrium/KKT computations; not independent dynamic acceptance',
            result=raw,study_cost=state(h)['analysis_costs']),indent=2),encoding='utf-8')

    def test_domains_boundary_cone_and_unqualified_equilibrium(self):
        from extensions.tendon_family.contracts import Design,ConstrainedPhysicalProblem
        from extensions.tendon_family.passive_equilibrium import tangent,mechanics
        from extensions.math_analysis.mechanism_registry import observe
        from tools.research.contracts import PhysicalMechanismTarget,MechanismQuestionV2
        from pydantic import ValidationError
        space,request,design,mesh,physics,problem=physical_fixture()
        invalid=deepcopy(design);invalid['fixed_payout_lengths_m']['tendon_0']=-1
        with self.assertRaises(ValidationError):Design.model_validate(invalid)
        old=deepcopy(request);oldspace=deepcopy(space);oldspace.pop('passive_payout_domains_m');old['family_space_identity']=digest(oldspace)
        with self.assertRaisesRegex(ValueError,'PAYOUT_REQUIRES'):generate_family(dict(space=oldspace,request=old))
        contact={**problem,'contact_mode':'frictional'}
        with self.assertRaises(ValidationError):ConstrainedPhysicalProblem.model_validate(contact)
        from schemas.platform import TaskDefinition
        from tools.research.config import _reference
        task=_reference(ROOT/'tasks/bf7_shared_reach_v1_central_high.json','task',dict(references={}))['task']
        task['actuator_channels']=[]
        with self.assertRaises(ValidationError):TaskDefinition.model_validate(task)
        self.assertIsNotNone(TaskDefinition.model_validate({**task,'physical_problem':problem}))
        with self.assertRaises(ValidationError):MechanismQuestionV2.model_validate(passive_question()['structure'])
        from extensions.tendon_family.compiler import resolve
        boundary_design=deepcopy(design);boundary_design['fixed_payout_lengths_m']['tendon_0']=physics['reference_lengths_m'][0]
        boundary=resolve(boundary_design,mesh)
        folder=OUT/('boundary-'+uuid4().hex[:8]);folder.mkdir()
        native=PassiveModel(boundary,problem,folder/'model.xml')
        record=mechanics(native,'unloaded',.5)
        self.assertTrue(record['constraint_state']['qualified']);self.assertEqual(record['constraint_state']['boundary_count'],1)
        self.assertIsNone(record['constrained_motion_subspace'])
        response=tangent(native,record['equilibrium']['equilibrium'],.5,[0.,0.,0.],[.5],increment=.001,direction_world=(0.,1.,0.))
        self.assertEqual(response['status'],'nonsmooth_or_degenerate');self.assertEqual(response['numerical_cost']['QP_calls'],2)
        target=PhysicalMechanismTarget(quantity='tangent_compliance',reduction='norm')
        self.assertEqual(observe(record,target)['status'],'not_applicable')
        from extensions.tendon_family.passive_inverse import design_sensitivity
        models=[]
        for offset in (-1e-5,1e-5):
            perturbed=deepcopy(boundary_design);perturbed['fixed_payout_lengths_m']['tendon_0']+=offset
            models.append(PassiveModel(resolve(perturbed,mesh),problem))
        switch=design_sensitivity(native,record['equilibrium']['equilibrium'],*models,'normalized_payout',.01,.5,[0.,0.,0.])
        self.assertEqual(switch['status'],'directional_comparison');self.assertFalse(switch['resolved_comparison']['same_active_set'])
        shorter=deepcopy(request);shorter['segments']['0']['cells']=1
        _,_,other_physics=generate_family(dict(space=space,request=shorter));other=PassiveModel(other_physics,problem)
        different=design_sensitivity(native,record['equilibrium']['equilibrium'],other,models[1],'topology',.01,.5,0.)
        self.assertEqual(different['reason'],'discrete_topology_change')
        weak_design=deepcopy(design);weak_design['tendons'][0].update(force_limit_n=1e-6,pretension_n=0.)
        capacity_model=PassiveModel(resolve(weak_design,mesh),problem)
        candidate=solve(capacity_model,.5,0.)
        rejected=candidate['equilibrium'];self.assertEqual(rejected['status'],'unqualified');self.assertFalse(rejected['capacity'])
        with self.assertRaisesRegex(ValueError,'QUALIFIED'):tangent(native,rejected,.5,0.,[.5])
        (OUT/'boundary_cone.json').write_text(json.dumps(dict(scope='Real MuJoCo boundary equilibrium, directional QPs, active-set switch and capacity qualification failure',
            mechanics=record,tangent=response,active_set_switch=switch,incomparable=different,capacity_failure=candidate,
            model_builds=5,physics_steps=0),indent=2),encoding='utf-8')

    def test_real_passive_compilation_and_equilibrium(self):
        space,request,design,mesh,physics,problem=physical_fixture()
        folder=ROOT/'runs'/('stage2-numerics-'+uuid4().hex[:8]);folder.mkdir(parents=True)
        with self.subTest(scope='real MuJoCo'):
            native=PassiveModel(physics,problem,folder/'model.xml')
            self.assertEqual(native.model.nu,0)
            self.assertTrue(np.all(native.model.tendon_limited))
            self.assertAlmostEqual(native.model.tendon_range[0,1],request['payout_lengths_m']['tendon_0'])
            baseline=solve(native,.5,[0.,0.,0.]);loaded=solve(native,.5,[0.,.01,0.],baseline['equilibrium']['qpos'])
            self.assertEqual(baseline['status'],'qualified_local_minimum',baseline)
            self.assertEqual(loaded['status'],'qualified_local_minimum',loaded)
            p=StaticProblem(native);q=np.array(loaded['equilibrium']['qpos']);v=np.arange(len(q))+1.;h=1e-6
            numerical=(p.constraint(q+h*v)-p.constraint(q-h*v))/(2*h)
            self.assertLess(np.max(abs(numerical-p.jacobian(q)@v)),1e-8)
            data=p.at(q);native.apply_force(data,.5,[0.,.01,0.]);mujoco.mj_forward(native.model,data)
            self.assertTrue(np.isfinite(data.qfrc_constraint).all())
            self.assertTrue(loaded['equilibrium']['positive'][0])
            evidence=dict(scope='Real MuJoCo static hard-constraint equilibrium; no integration or formal acceptance',
                design=design,mesh=mesh,physical_problem=problem,baseline=baseline,loaded=loaded,
                native_limit_reaction_nm=data.qfrc_constraint.tolist(),native_soft_length_residual_m=(data.ten_length-native.payout).tolist(),
                native_version=mujoco.__version__,model_builds=1,physics_steps=0,registered_acceptance='not_registered')
            (OUT/'real_equilibrium.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')


if __name__=='__main__':unittest.main()
