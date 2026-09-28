"""Bounded, solve-free checks for expansion, attribution and saved alignment."""
from copy import deepcopy
from types import SimpleNamespace
import unittest
import numpy as np
from examples.gvs_design_input import multiphysics_input
from schemas.platform import SessionInput
from extensions.tendon_family.candidate import apply, candidate_facts, check_design_statement
from extensions.tendon_family.contracts import Space
from extensions.tendon_family.compiler import resolve
from extensions.tendon_family.gvs_profile import checked_reach, reach_numerical


class MultiphysicsTests(unittest.TestCase):
    def setUp(self):
        self.inp=SessionInput.model_validate(multiphysics_input())
        self.space=Space.model_validate(self.inp.policy.candidate_builder.parameters.data)
        self.changes={'components/near/length_m':.162,'design/section_scale':1.02,'design/material_scenario':'compliant'}

    def candidate(self): return apply(deepcopy(self.inp),self.space,self.changes)

    def test_expansion_formulas_no_compounding_scope(self):
        x=self.candidate(); checked_reach(x)
        again=apply(deepcopy(x),self.space,{'design/section_scale':1.02})
        self.assertEqual(x.robot,again.robot)
        reset=apply(deepcopy(x),self.space,{'design/section_scale':1.,'design/material_scenario':'baseline'})
        self.assertEqual(reset.robot.structure.data['components'][0]['sections'],self.inp.robot.structure.data['components'][0]['sections'])
        a=resolve(self.inp.robot.structure.data,self.inp.policy.discretization.data)
        b=resolve(x.robot.structure.data,x.policy.discretization.data)
        for old,new in zip(a['parts'],b['parts']):
            if old['section'] is None:
                for key in ('mass_kg','inertia_com_local_kg_m2','envelope_halfsize_m'):
                    self.assertEqual(old[key],new[key])
                continue
            ratio=new['length_m']/old['length_m']
            self.assertAlmostEqual(new['mass_kg']/old['mass_kg'],1.02**2*ratio)
            np.testing.assert_allclose(np.array(new['stiffness_nm_rad'])/old['stiffness_nm_rad'],.9*1.02**4/ratio)
            np.testing.assert_allclose(np.array(new['damping_nm_s_rad'])/old['damping_nm_s_rad'],1/ratio)
            self.assertAlmostEqual(new['inertia_com_local_kg_m2'][0][0]/old['inertia_com_local_kg_m2'][0][0],1.02**4*ratio)
        for scale in (.95,1.05):
            checked_reach(apply(deepcopy(self.inp),self.space,{'design/section_scale':scale}))
        historical=x.model_dump(mode='json'); historical['policy']['controller']['version']='4.0.0'
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED'): checked_reach(historical)
        x.robot.structure.data['tendons'][0]['force_limit_n']=9.
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED'): checked_reach(x)
        with self.assertRaisesRegex(ValueError,'NOT_AUTHORIZED'):
            apply(deepcopy(self.inp),self.space,{'components/near/physics/young_pa':1e6})

    def test_preparation_and_delivery(self):
        x=self.candidate(); n=reach_numerical(x)
        self.assertFalse(n['provenance']['historical_states_reused'])
        self.assertEqual(n['force_limits_n'],[8.]*6)
        self.assertEqual(n['provenance']['physics_identity'],resolve(x.robot.structure.data,x.policy.discretization.data)['identity'])
        facts=candidate_facts(self.inp,x.model_dump(mode='json'),{},'selected','owner','exec')
        self.assertTrue(facts['multi_category_coverage'])
        self.assertTrue(check_design_statement(facts,deepcopy(facts))['accepted'])
        bad=deepcopy(facts);bad['parameters'][-1]['effective_value']='stiff'
        self.assertFalse(check_design_statement(facts,bad)['accepted'])
        bad=deepcopy(facts);bad['physical_changes'][0]['effective_value']=.16
        self.assertFalse(check_design_statement(facts,bad)['accepted'])

    def test_owned_analysis(self):
        from extensions.tendon_family.candidate_analysis import evaluate_candidate, CandidateDynamicsRequest
        from extensions.tendon_family.gvs_basis import resolve_basis
        from tools.platform_registry import registry
        x=self.candidate(); n=len(resolve_basis(x.robot.structure.data,x.policy.controller.parameters.data['recipe']['basis']).coordinate_order)
        artifacts={'build':dict(candidate_id='candidate',configuration='config'),'config':x.model_dump(mode='json')}
        ctx=SimpleNamespace(input=self.inp,reg=registry(),run_id='owner',artifact=lambda r:artifacts[r],
            store=SimpleNamespace(session=lambda _:dict(state={'route':{'nodes':[dict(node_id='build',action='build',status='completed',result='build')]}})))
        args=CandidateDynamicsRequest(source_node='build',state=dict(q=[0.]*n,qdot=[0.]*n),
            input=dict(tendon_tensions_n={t['id']:0. for t in x.robot.structure.data['tendons']}))
        result=evaluate_candidate(ctx,args)
        self.assertEqual(result.binding['candidate_id'],'candidate')
        self.assertAlmostEqual(result.physical_summary['sections'][0]['material']['young_pa'],7.2e6)
        self.assertAlmostEqual(result.calculation['tip']['position_m'][0],.310)
        with self.assertRaisesRegex(ValueError,'OWNED_COMPLETED'): evaluate_candidate(ctx,args.model_copy(update={'source_node':'other'}))

    def test_saved_one_step_alignment(self):
        from extensions.tendon_family.gvs_reporting import aligned_predictions
        obs=[dict(time_s=0.,actual_tension_n=[2.],one_step_prediction=dict(time_s=.01,frame='world',
            applied_tension_n=[2.],tip_position_m=[0.,0.,0.]))]
        rows=[dict(time_s=.01,tip_m=[.001,0.,0.])]
        matched,missing=aligned_predictions(rows,obs)
        self.assertEqual(len(matched),1);self.assertFalse(missing)
        self.assertAlmostEqual(matched[0]['tip_difference_m'],.001)
        self.assertEqual(aligned_predictions([],obs)[1][0]['reason'],'next execution timestamp missing or ambiguous')
        obs.append(dict(time_s=.005))
        self.assertFalse(aligned_predictions(rows,obs)[0])


if __name__=='__main__': unittest.main()
