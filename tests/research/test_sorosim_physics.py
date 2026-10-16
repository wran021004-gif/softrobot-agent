"""Matched physical checks; evidence is produced only by a real Engine run."""
import importlib.util
import json
import os
from pathlib import Path
import time
import unittest
import numpy as np

from test_sorosim_contract import ROOT, final_candidate
from tools.state_io import read, atomic_json, digest
from extensions.tendon_family.sorosim_spec import specification
from extensions.tendon_family.sorosim_session import SorosimSession
from extensions.tendon_family.contracts import GVSModelParameters
from extensions.tendon_family.gvs import forward_kinematics, tendon_kinematics

# Declared before numerical execution. SI units, absolute AND relative checks.
LIMITS = dict(length_m=2e-6,pose_m=2e-6,force_map_m2=2e-6,relative=2e-3,
    fd_routing_m2=2e-8,fd_tip_m2=2e-8,fd_force_nm3=2e-8)


def error(a,b):
    a,b=np.asarray(a),np.asarray(b)
    absolute=float(np.max(np.abs(a-b)))
    return dict(absolute=absolute,relative=absolute/max(float(np.max(np.abs(b))),1e-15))


def matched(session,inp,q,u):
    p=GVSModelParameters(basis=inp.policy.controller.parameters.data['recipe']['basis'],
        integration_steps_per_segment=192,quadrature_points_per_segment=5)
    raw=session.evaluate('routing',dict(q=list(q),u=list(u)))
    expected=forward_kinematics(inp.robot.structure.data,q,integration_steps_per_segment=192,basis=p.basis)
    order,length,jac=tendon_kinematics(inp.robot.structure.data,q,p)
    return dict(q=list(q),u=list(u),raw=raw,reference=dict(lengths=length.tolist(),length_jacobian=jac.tolist(),
        tip_pose=expected['tip_transform'].tolist()),
        errors=dict(length=error(raw['lengths'],length),force_map=error(raw['force_map'],-jac.T),
            pose=error(np.asarray(raw['tip_pose'])[:3,3],expected['tip_position_m'])),
        independent=session.evaluate('checks',dict(q=list(q),u=list(u))))


def frozen_checks(session,inp):
    """Only two fixed V1/V2 probes, not the 248-solve historical campaign."""
    ref=ROOT/'validation/sorosim'
    module_spec=importlib.util.spec_from_file_location('frozen_sorosim_gvs',ref/'run_gvs.py')
    module=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(module)
    cfg=read(ref/'cases.json');rows=[]
    session.engine.addpath(str(ref),nargout=0)
    # Test-only workspace, isolated from gateway's session-local production model.
    for case in cfg['cases']:
        d=module.make_design(cfg,case)
        spec=specification(d,dict(cells={c.id:12 for c in d.components}),inp.task.environment.data,
            basis=dict(strategy='first_order'),solver=dict(gauss_per_interval=20))
        session.call('clear');session.model_identity=None;session.construct(spec)
        q=case['probes_rad_m'][-1];u=cfg['probe_tensions_n']
        raw=session.evaluate('routing',dict(q=q,u=u))
        session.engine.workspace['frozen_cfg_json']=json.dumps(cfg)
        session.engine.workspace['frozen_case_json']=json.dumps(case)
        session.engine.eval("fc=jsondecode(frozen_cfg_json); fm=jsondecode(frozen_case_json); [fs,ft]=sv_model(fc,fm,20);",nargout=0)
        session.engine.workspace['frozen_q_json']=json.dumps(q)
        session.engine.eval("fq=jsondecode(frozen_q_json); fv=sv_terms(fs,ft,fc,fq,fc.probe_tensions_n,true);",nargout=0)
        expected=json.loads(session.engine.eval('jsonencode(fv)',nargout=1))
        rows.append(dict(case=case['id'],q=q,u=u,production=raw,
            errors=dict(length=error(raw['lengths'],expected['tendon_lengths']),
                force_map=error(raw['force_map'],expected['tendon_force_map']),
                pose=error(raw['tip_pose'],expected['pose']),
                tangent=error(raw['force_state_derivative'],np.asarray(expected['A0'])-np.asarray(expected['Rq'])))))
    session.engine.eval('clear fc fm fs ft fq fv frozen_cfg_json frozen_case_json frozen_q_json',nargout=0)
    return rows


def run_s1(destination):
    destination=Path(destination)
    if destination.exists(): raise ValueError('PRESERVE_EXISTING_EVIDENCE')
    inp,source=final_candidate();u=[.3,.1,.2,.1];rows=[]
    spec=specification(inp.robot.structure.data,inp.policy.discretization.data,inp.task.environment.data,
        basis=inp.policy.controller.parameters.data['recipe']['basis'])
    with SorosimSession() as session:
        frozen=frozen_checks(session,inp)
        session.call('clear');session.model_identity=None
        construction=session.construct(spec)
        for q in [np.zeros(12),np.array([1.2,.8,-.7,.4,-.5,.3,-.9,.6,1.1,-.5,.2,-.3])]:
            rows.append(matched(session,inp,q,u))
    atomic_json(destination,dict(stage='S1',source=source,specification=spec,construction=construction,
        reference_resolution=dict(gvs_midpoint_steps=192,gauss_per_structural_interval=5),
        limits=LIMITS,frozen=frozen,probes=rows,timings=session.timings,
        scope='Matched bending geometry/routing only; no task success or S2 dynamic claim'))
    return read(destination)


def verify_s1(evidence):
    assert evidence['limits']==LIMITS
    assert evidence['construction']['coordinates']==12
    assert evidence['construction']['coordinate_rank']==12
    for row in evidence['probes']:
        for key,unit in [('length','length_m'),('pose','pose_m'),('force_map','force_map_m2')]:
            assert row['errors'][key]['absolute']<=LIMITS[unit],(key,row['errors'][key])
            assert row['errors'][key]['relative']<=LIMITS['relative'],(key,row['errors'][key])
        for key,bound in [('routing_jacobian_error','fd_routing_m2'),('tip_jacobian_error','fd_tip_m2'),
                          ('force_state_derivative_error','fd_force_nm3')]:
            assert row['independent'][key]<=LIMITS[bound],(key,row['independent'])
    for row in evidence['frozen']:
        assert max(v['absolute'] for v in row['errors'].values())<=1e-10,row['errors']


class PhysicsTests(unittest.TestCase):
    def test_s1_evidence(self):
        path=ROOT/'evidence/sorosim_control/s1.json'
        if not path.exists(): self.skipTest('Real S1 evidence not yet recorded')
        verify_s1(read(path))

    def test_compiled_physical_quantities_and_rank(self):
        inp,_=final_candidate();s=specification(inp.robot.structure.data,inp.policy.discretization.data,inp.task.environment.data)
        physical={c['id']:c for c in inp.robot.structure.data['components']}
        for link in s['links']:
            p=physical[link['id']]
            if link['kind']=='flexible_segment':
                self.assertEqual(link['canonical_sections'],p['sections'])
                self.assertEqual(link['canonical_physics'],p['physics'])
                self.assertAlmostEqual(sum(link['weights']),p['length_m'])
            else:
                np.testing.assert_array_equal(link['inertia'],p['inertia_com_local_kg_m2'])
                self.assertEqual(link['mass_kg'],p['mass_kg'])
        changed=json.loads(json.dumps(inp.robot.structure.data))
        changed['components'][-1]['com_local_m'][0]+=.001
        self.assertNotEqual(s['identity'],specification(changed,inp.policy.discretization.data,inp.task.environment.data)['identity'])


if __name__=='__main__':
    path=os.environ.get('SOROSIM_S1_EVIDENCE')
    if path: verify_s1(run_s1(path))
    unittest.main()
