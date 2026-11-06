"""Representative real topology/kinematics checks; no Provider or dynamic rollout."""
from contextlib import contextmanager
from copy import deepcopy
import os
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

import mujoco
import numpy as np

from schemas.platform import SessionInput
from tools.research import core
from tools.research.config import ROOT,resolve
from tools.research.state import state,update
from tools.research.design import generate_candidate
from tools.research.agent import plan_schema
from tools.state_io import read,digest,atomic_json
from tools.platform_store import plain
from extensions.tendon_family.family_space import parse_space,parse_build,resolved_request,parameter_capabilities,decision_summary
from extensions.tendon_family.generated_serial import generate_family
from extensions.tendon_family.backends import physics_for
from extensions.tendon_family.scene import assemble_physical
from extensions.tendon_family.passive import PassiveModel
from extensions.tendon_family.passive_equilibrium import StaticProblem,solve
from extensions.tendon_family.passive_execution import constraint_mechanism,observation_specs,source_binding
from extensions.reference.passive_response import task_definition
from tools.platform_registry import registry
from tests.research.test_cross_task_integration import fixture_directory

SPEC=ROOT/'configs/research/study_phs2d_topology_successor_20261106.json'


@contextmanager
def topology_fixture():
    spec=resolve(SPEC);spec['study_id']='topology-engineering-'+uuid4().hex[:8]
    spec['configuration']['run_id']=spec['study_id']
    spec['resolved_identity']=digest({k:v for k,v in spec.items() if k!='resolved_identity'})
    with fixture_directory() as folder,patch('tools.research.config.resolve',return_value=spec):
        h=core.prepare(directory=folder)
        from tools.research.research_context import import_history
        import_history(h)
        yield h


class TopologySupportTests(unittest.TestCase):
    def test_representative_real_generation_native_geometry_and_static_dimensions(self):
        records=[];started=time.perf_counter()
        with topology_fixture() as h:
            spec=state(h)['spec'];ledger=h.store.remaining()['used']
            for n,t in ((1,1),(1,12),(9,1),(9,12),(9,4),(5,6)):
                tick=time.perf_counter()
                q=dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],
                    segment_count=n,tendon_count=t,payout_lengths_m={f'tendon_{i}':.405+.0001*i for i in range(t)})
                result=generate_candidate(h,q,dict(origin='Independent topology engineering check; no formal evaluation'))
                self.assertEqual(result['status'],'generated',result)
                candidate=h.store.artifact(result['candidate']);inp=SessionInput.model_validate(candidate['configuration'])
                design=inp.robot.structure.data;parts={p['id']:p for p in design['components']}
                self.assertEqual(len(parts),3*n-1);self.assertEqual(parts['payload']['connection']['part'],f'segment_{n-1}')
                for i in range(1,n):
                    self.assertEqual(parts[f'guide_{i}']['connection']['part'],f'segment_{i-1}')
                    self.assertEqual(parts[f'connector_{i}']['connection']['part'],f'guide_{i}')
                    self.assertEqual(parts[f'segment_{i}']['connection']['part'],f'connector_{i}')
                    self.assertEqual(set(parts[f'guide_{i}']['guide_holes']),{f'tendon_{j}_hole' for j in range(t)})
                self.assertEqual(len(design['tendons']),t);self.assertEqual(design['actuators'],[])
                resolved=resolved_request(spec['family_space'],q)
                self.assertEqual(resolved['payout_lengths_m'],q['payout_lengths_m'])
                rows=parameter_capabilities(spec['family_space'],q)
                self.assertEqual({r['parameter_id'] for r in rows if r['parameter_id'].startswith('payout_lengths_m.')},
                    {f'payout_lengths_m.tendon_{i}' for i in range(t)})
                physics=physics_for(inp);goal,bounds,problem=task_definition(inp.task,registry())
                scene=assemble_physical(inp,physics);scene['control']=dict(tension_execution_mode='passive_fixed_payout_v1',
                    solreflimit=goal.solreflimit,solimplimit=goal.solimplimit)
                native=PassiveModel(physics,plain(problem),scene=scene)
                native.protocol['static_solver'].update(goal.unloaded_static_solver)
                m=native.model;d=mujoco.MjData(m);mujoco.mj_fwdPosition(m,d)
                self.assertEqual(m.ntendon,t);self.assertEqual(m.nu,0);self.assertEqual(m.nv,16*n)
                np.testing.assert_allclose(native.payout,[q['payout_lengths_m'][f'tendon_{i}'] for i in range(t)])
                J=native.tendon_jac(d);self.assertEqual(J.shape,(t,m.nv))
                mechanism=constraint_mechanism(native,d,goal)
                for name in ('actual_tension_n','constraint_states','constraint_residuals_m','constraint_active','constraint_classification'):
                    self.assertEqual(len(mechanism[name]),t,name)
                observations=observation_specs(inp)
                tendon_signals=[s for s in observations if s.name=='tendon_tension']
                self.assertEqual(len(tendon_signals),10*t)
                self.assertEqual(source_binding(candidate['configuration'])['design_identity'],physics['design_identity'])
                static=StaticProblem(native);initial=dict(status='not_checked')
                try:
                    self.assertEqual(static.constraint(np.zeros(m.nv)).shape,(t,))
                    self.assertEqual(static.jacobian(np.zeros(m.nv)).shape,(t,m.nv))
                    initial=dict(status='forward_completed',native_contacts=int(static.d.ncon))
                    if n==1:
                        qualification=static.qualify(np.zeros(m.nv))
                        self.assertEqual(np.asarray(qualification['Jlength']).shape,(t,m.nv))
                        self.assertEqual(len(qualification['tensions_n']),t)
                        initial['zero_pose_qualification']={k:qualification[k] for k in
                            ('status','kkt_pass','capacity','second_order_sufficient','native_contacts')}
                except Exception as exc:
                    initial=dict(status='initial_forward_failed',error=type(exc).__name__,reason=str(exc),
                        numerical_failure=getattr(exc,'mujoco_diagnostic',None))
                if (n,t)==(1,1):
                    try:
                        load=native.load(problem.baseline_load)
                        checked=solve(native,load.material_s,load.force_world_n,multistart=goal.unloaded_multistart)
                        initial['unloaded_static_check']=checked
                    except Exception as exc:
                        initial['unloaded_static_check']=dict(status='failed',error=type(exc).__name__,reason=str(exc),
                            progress=getattr(exc,'equilibrium_progress',None))
                records.append(dict(segments=n,tendons=t,request=q,candidate_identity=candidate['identity'],
                    physics_identity=physics['identity'],generation='supported',native_compile='passed',
                    native_nv=m.nv,ntendon=m.ntendon,payout_shape=list(native.payout.shape),jacobian_shape=list(J.shape),
                    initial_geometry=dict(position_stage='completed',native_contacts=int(d.ncon),
                        route_and_hole_clearance='passed_by_generator',scope='Contact facts at frozen zero pose; not qualification'),
                    static=initial,dynamic_interface='actual-tendon arrays and ten-case observation bindings checked',
                    dynamic_rollout_executed=False,task_acceptance='unmeasured',elapsed_s=time.perf_counter()-tick))
            self.assertEqual(h.store.remaining()['used'],ledger)
            self.assertEqual(state(h)['mathematical_evaluations'],0)
            self.assertEqual(state(h)['physical_replays'],[])
            if os.environ.get('PHS_TOPOLOGY_EVIDENCE'):
                atomic_json(ROOT/os.environ['PHS_TOPOLOGY_EVIDENCE'],dict(
                    scope='Independent local engineering checks; excluded from formal Study science ledger',
                    family_space_identity=spec['family_space_identity'],cases=records,elapsed_s=time.perf_counter()-started,
                    provider_requests=0,full_ten_condition_executions=0))

    def test_historical_space_serialization_and_nine_by_four_design_unchanged(self):
        old=read(ROOT/'configs/research/family_space_phs2d_route_research_v2.json')
        new=read(ROOT/'configs/research/family_space_phs2d_topology_research_v3.json')
        self.assertEqual(plain(parse_space(old)),old)
        def build(space):
            return parse_build(dict(space=space,request=dict(version='serial_family_generation_v2',
                family_space_identity=digest(space),segment_count=9,tendon_count=4)))
        self.assertEqual(generate_family(build(old)),generate_family(build(new)))
        for values in (dict(tendon_count=0),dict(tendon_count=13),dict(segment_count=10)):
            req=dict(version='serial_family_generation_v2',family_space_identity=digest(new),segment_count=1,tendon_count=1)
            req.update(values)
            with self.assertRaises(ValueError):generate_family(parse_build(dict(space=new,request=req)))

    def test_common_domain_unknown_tendons_and_main_schema(self):
        spec=resolve(SPEC);space=spec['family_space'];q=dict(version='serial_family_generation_v2',
            family_space_identity=spec['family_space_identity'],segment_count=5,tendon_count=6)
        resolved=resolved_request(space,q)
        self.assertEqual(set(resolved['payout_lengths_m']),{f'tendon_{i}' for i in range(6)})
        for invalid in ({'tendon_6':.4},{'tendon_0':.1}):
            with self.assertRaises(ValueError):resolved_request(space,{**q,'payout_lengths_m':invalid})
        summary=decision_summary(space,None,[])
        self.assertEqual(summary['executable_domain']['payout_bound_tendon_counts'],list(range(1,13)))
        self.assertEqual(summary['passive_payout_domain_m'],dict(minimum=.3,maximum=.5,default=.406))
        for focused in (False,True):
            schema=plan_schema(['generate'],decision_required=True,study=spec,focused=focused)
            props=schema['$defs']['GenerationRequestV2']['properties']
            self.assertEqual(props['segment_count']['enum'],list(range(1,10)))
            self.assertEqual(props['tendon_count']['minimum'],1);self.assertEqual(props['tendon_count']['maximum'],12)
            self.assertEqual(props['payout_lengths_m']['additionalProperties']['minimum'],.3)


if __name__=='__main__':unittest.main()
