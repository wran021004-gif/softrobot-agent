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
            dict(name='lateral',material_s=.5,force_world_n=[0.,.01,0.])],monitor_s=[.5],baseline_load='unloaded')
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
