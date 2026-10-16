"""Contract tests plus opt-in real dependency evidence; no provider requests."""
from copy import deepcopy
import json
import os
from pathlib import Path
import unittest

from schemas.platform import SessionInput
from tools.state_io import read, digest, atomic_json
from tools.research.config import resolve
from tools.platform_registry import registry

ROOT = Path(__file__).resolve().parents[2]


def final_candidate(*, sorosim=True):
    """Regenerate the saved M3-C3 design using the existing family generator."""
    from tools.research.numerics import archived
    from extensions.tendon_family.family_space import parse_build
    from extensions.tendon_family.generated_serial import generate_family
    evidence = read(ROOT/'evidence/m3c3_mixed_family_search/search_verification.json')
    ref = evidence['best']['evidence']['candidate']
    old = archived('evidence/m3c3_mixed_family_search/search', ref)
    study = resolve(ROOT/'configs/research/study_m3d_agent_feedback.json')
    request = deepcopy(old['parameters'])
    for segment in request['segments'].values():
        segment['cells'] = study['fidelity_policy']['final_evaluation']['cells_per_segment']
    design, mesh, physics = generate_family(parse_build(dict(space=study['family_space'], request=request)))
    assert digest(design) == digest(old['configuration']['robot']['structure']['data'])
    cfg = deepcopy(old['configuration'])
    cfg['robot']['structure']['data'] = design
    cfg['policy']['discretization']['data'] = mesh
    cfg['policy']['candidate_builder']['parameters']['data']['request'] = request
    cfg['task']['initializer']['parameters']['data'] = dict(unspecified='zero',
        qpos_rad={j:0. for j in physics['dofs']}, qvel_rad_s={j:0. for j in physics['dofs']})
    if sorosim:
        cfg['policy']['controller'].update(extension_id='controller.sorosim_matlab_nmpc',version='1.0.0')
        cfg['policy']['controller']['parameters']['contract'] = 'family.sorosim_reach_control'
    return SessionInput.model_validate(cfg), dict(candidate=ref, physical_design_identity=old['physical_design_identity'],
        reference_commit='e1ae76331d37ca1258803def6f07219f00aa5352', base_commit='5dd325eb2c179c01d13aba50074b15db64a0cfdb')


class ContractTests(unittest.TestCase):
    def test_registration_and_frozen_defaults(self):
        reg = registry()
        self.assertEqual(reg.get('controller.gvs_nmpc','11.0.0','controller').binding,
            'extensions.tendon_family.gvs_nmpc:DeadlineReachNMPCController')
        new = reg.get('controller.sorosim_matlab_nmpc','1.0.0','controller')
        self.assertNotIn('extensions/tendon_family/gvs_casadi.py',new.sources)
        self.assertNotIn('extensions/optimization/ipopt.py',new.sources)
        self.assertIn('controller.sorosim_matlab_nmpc',reg.get('backend.family_mujoco','1.1.0','backend').capabilities['controllers'])
        cfg = resolve(ROOT/'configs/research/study_m3d_agent_feedback.json')
        self.assertEqual(cfg['configuration']['policy']['controller']['extension_id'],'controller.gvs_nmpc')

    def test_backend_specific_source_freeze(self):
        import subprocess
        path=ROOT/'evidence/sorosim_control/source_freeze.json'
        if not path.exists():self.skipTest('Delivery source identity not recorded')
        frozen=read(path);identity=frozen.pop('identity')
        self.assertEqual(digest(frozen),identity)
        for source,blob in frozen['git_blobs'].items():
            # Historical S3 evidence stays bound to its completion tree. S3.5
            # instrumentation has a separate current-source freeze and test.
            actual=subprocess.check_output(['git','rev-parse',
                'cdb2f8d196af7f7d04c14efda3b960b88c20a782:'+source],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
            self.assertEqual(actual,blob,source)
        self.assertEqual(frozen['external_dependency_identity'],digest(read(ROOT/'evidence/sorosim_control/s0.json')['dependency']))

    def test_sparse_configuration_preserves_science(self):
        source = ROOT/'configs/research/study_m3d_agent_feedback.json'
        original = resolve(source)
        selected = resolve(source,backend_profile='sorosim_matlab_v1')
        a = original['configuration']; b = selected['configuration']
        self.assertEqual(a['task'],b['task'])
        self.assertEqual(a['robot'],b['robot'])
        self.assertEqual(a['policy']['controller']['parameters']['data']['recipe'],b['policy']['controller']['parameters']['data']['recipe'])
        self.assertIn('solver',b['policy']['controller']['parameters']['data'])
        self.assertEqual(a['policy']['dynamics_model'],b['policy']['dynamics_model'])
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_MATHEMATICAL_BACKEND_PROFILE'):
            resolve(source,backend_profile='unknown')

    def test_s4_is_explicitly_unsupported(self):
        from extensions.tendon_family.model_applicability import assess_model_uses
        from schemas.platform import Binding,Payload
        inp,_=final_candidate()
        model=Binding(extension_id='model.sorosim_gvs',version='1.0.0',parameters=Payload(
            contract='family.sorosim_model',data=dict(basis=inp.policy.controller.parameters.data['recipe']['basis'])))
        verdict=assess_model_uses(inp.robot,inp.task,model,['static_equilibrium','linearization'])
        self.assertTrue(all(v.status=='REJECT' for v in verdict.uses.values()))

    def test_session_cleanup_is_idempotent_software_fixture(self):
        from extensions.tendon_family.sorosim_session import SorosimSession
        from types import SimpleNamespace
        closed=[];s=SorosimSession(root='unused_software_fixture')
        s.engine=SimpleNamespace(quit=lambda:closed.append(True));s.model_identity='software_fixture'
        s.close();s.close()
        self.assertEqual(closed,[True]);self.assertIsNone(s.model_identity)
        with self.assertRaisesRegex(RuntimeError,'MATLAB_SESSION_CLOSED'):s.call('environment')

    def test_actual_candidate_and_unsupported_method(self):
        from extensions.tendon_family.sorosim_control import checked_control
        from extensions.tendon_family.gvs_profile import candidate_numerical
        inp,_ = final_candidate()
        control = checked_control(inp)
        data = candidate_numerical(inp,control)
        self.assertEqual((len(data['coordinate_order']),len(data['tendon_order'])),(12,4))
        reg = registry()
        reg.bind(inp.policy.controller,'controller')
        support = reg.get('candidate.family','6.0.0','candidate_builder').capabilities['parameter_support']
        self.assertIn('controller.sorosim_matlab_nmpc@1.0.0',support['controller'])
        inp.policy.controller.parameters.data['recipe']['integration_method']='implicit_midpoint'
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_INTEGRATION'):
            checked_control(inp)


def environment_evidence(destination):
    import platform
    import numpy, scipy, mujoco
    from extensions.tendon_family.sorosim_session import SorosimSession
    destination = Path(destination)
    if destination.exists():
        raise ValueError('PRESERVE_EXISTING_EVIDENCE')
    with SorosimSession() as session:
        environment = session.environment
        dependency = session.dependency
    atomic_json(destination,dict(stage='S0',environment=environment,dependency=dependency,
        timings=session.timings,python=platform.python_version(),numpy=numpy.__version__,scipy=scipy.__version__,
        mujoco=mujoco.__version__,scope='Real Engine + pinned upstream MEX + fmincon SQP smoke; no robot mechanics or NMPC claim'))


if __name__ == '__main__':
    if os.environ.get('SOROSIM_S0_EVIDENCE'):
        environment_evidence(os.environ['SOROSIM_S0_EVIDENCE'])
    unittest.main()
