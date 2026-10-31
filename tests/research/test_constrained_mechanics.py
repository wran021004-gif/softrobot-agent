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
            (ROOT/'docs/research/r3_b_stage2_real_equilibrium.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')


if __name__=='__main__':unittest.main()
