"""A+ focused synthetic checks. NativeModel is fabricated; no engine or Provider."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
from tools.platform_store import plain
from tools.state_io import atomic_json,read,digest
from tools.research import core,analysis,reporter
from tools.research.config import ROOT
from tools.research.state import state,update
from tools.research.contracts import AnalysisRequest,MechanismStudy
from tools.research.design import family_configuration,set_parameter
from tools.research.scientific_intent import compile_question
from tools.research.structure_research import parameters,prepare_context,calculate,summary
from tools.research.research_context import agent_decision_brief
from extensions.math_analysis.differentiation_router import differentiate,coordinate
from extensions.math_analysis.mechanism_registry import observe
from extensions.tendon_family.family_space import resolved_request,parse_space
from tests.research.test_p63b3_action_interface import provision,feedback
from tests.research.test_p63a_math_interface import generate,diagnose
from tests.research.test_p63c2_scientific_intent import mechanism_question
from tests.research.test_information_flow import generation,packet
from tests.research.test_recent_round_tools import run_fixture


class SyntheticNative:
    def __init__(self,cfg):
        parts=[p for p in cfg['robot']['structure']['data']['components'] if p['kind']=='flexible_segment']
        self.signal=sum((i+1)*p['length_m'] for i,p in enumerate(parts))
        self.physics=dict(identity='SYNTHETIC-NO-ENGINE-'+str(self.signal));self.order=['q'];self.tendons=['t']
        self.scene=dict(qpos_rad=[0.],qvel_rad_s=[0.])
        self.cost=dict(model_builds=1,mechanics_evaluations=0,physics_steps=0,rollouts=0)
    def restore(self,point,**kw):return dict(point)
    def reconstruct(self,point):return point,self.restore(point)
    def checkpoint(self,data):return dict(fixture='Synthetic state; no engine',qvel=data.get('qvel_rad_s'))
    def mechanics(self,data,u):
        self.cost['mechanics_evaluations']+=1
        return dict(time_s=0.,qpos_rad=[0.],qvel_rad_s=data.get('qvel_rad_s',[0.]),
            coordinates=dict(dof_order=['q'],tendon_order=['t']),actual_tensions_n=[1.],input_bounds_n=[[0.,8.]],
            tip_acceleration_input_map_m_s2_n=[[self.signal],[0.],[0.]],mass_matrix_kg_m2=[[self.signal]])


def prepare(*,physical=False):
    h=provision();spec=deepcopy(state(h)['spec'])
    spec['research_decisions']['analysis_interface']='scientific_question_v2'
    spec['mathematical_methods']['mechanism_structure_v1']='OFFLINE A+ synthetic fixture only'
    spec['budgets']['mathematical_evaluations']=32
    if physical:
        spec['family_space']=plain(parse_space(read(ROOT/'configs/research/family_space_s7.json')))
        spec['family_space_identity']=digest(spec['family_space'])
    update(h,spec=spec);c=generate(h)
    spec=deepcopy(state(h)['spec'])
    spec['family_sensitivity_variables']['variables']=[r['parameter_id'] for r in parameters(spec,h.store.artifact(c)) if '*' not in r['parameter_id']]
    update(h,spec=spec);diagnose(h,c,'scientific_question')
    return h,c


def execute_synthetic(h,c,q):
    compiled=compile_question(h,q,tool_use_id='aplus-synthetic-compile')
    assert compiled['status']=='ready',compiled
    def worker(command,log,timeout,**kw):
        req=read(Path(command[-1]));query=AnalysisRequest.model_validate(req['query'])
        context=prepare_context(state(h)['spec'],h.store.artifact(c),query.mechanism_study,[])
        with patch('extensions.tendon_family.mujoco_analysis.NativeModel',SyntheticNative):
            value=calculate(h.store.artifact(c)['configuration'],req['binding'],query,
                dict(actual_time_s=0.,u=[1.],qpos_rad=[0.],qvel_rad_s=[0.]),context)
        from schemas.platform_analysis import TaskAnalysisRequirement
        value=analysis.scoped_result(value,TaskAnalysisRequirement.model_validate(req['task_analysis']),req['analysis_applicability'],query)
        atomic_json(Path(command[-1]).with_name('result.json'),value)
        return SimpleNamespace(returncode=0)
    with patch('tools.service_execution._run_contained',side_effect=worker):
        return analysis.dispatch(h,compiled['request'],'aplus-synthetic-'+str(len(state(h)['analysis_results'])),guard=lambda *a:None,origin='engineering_preflight')


class AplusTests(unittest.TestCase):
    def test_actual_domains_compile_material_section_and_routing_and_exclusions(self):
        h,c=prepare(physical=True);spec=state(h)['spec'];candidate=h.store.artifact(c)
        rows={r['parameter_id']:r for r in parameters(spec,candidate)}
        paths=['segments.0.length_m','segments.0.young_pa','segments.0.physical_parameters.density_kg_m3',
            'segments.0.physical_parameters.viscosity_y_nm2_s','segments.1.sections.0.parameters.width_y_m','spans.0.radius_m',
            'spans.0.phase_rad','spans.0.guide_s.0','spans.0.anchor_s']
        for path in paths:
            with self.subTest(path=path):
                self.assertIn(path,list(rows));row=rows[path];self.assertTrue(row['mechanism_differentiation']['supported'],row)
                request=resolved_request(spec['family_space'],candidate['parameters'])
                new=row['current_value']+.005*(row['maximum']-row['minimum'])
                if new>row['maximum']:new=row['current_value']-.005*(row['maximum']-row['minimum'])
                set_parameter(request,path,new)
                cfg,build,_=family_configuration(candidate['configuration'],spec['family_space'],request,h.run_id)
                self.assertNotEqual(cfg['robot']['structure']['data'],candidate['configuration']['robot']['structure']['data'])
                q=mechanism_question();q['parameter_paths']=[path]
                self.assertEqual(compile_question(h,q,tool_use_id='domain-'+path)['status'],'ready')
        excluded=[r for r in rows.values() if r['category'] in ('controller','discretization') or r.get('input_set_changes')]
        self.assertTrue(excluded)
        for row in excluded:self.assertFalse(row['mechanism_differentiation']['supported'])
        # Undeclared material is unavailable, never synthesized by its name.
        legacy,base=prepare();known={r['parameter_id'] for r in parameters(state(legacy)['spec'],legacy.store.artifact(base))}
        self.assertNotIn('segments.0.physical_parameters.density_kg_m3',known)
        q=mechanism_question();q['parameter_paths']=['segments.0.physical_parameters.density_kg_m3']
        self.assertEqual(compile_question(legacy,q,tool_use_id='absent')['status'],'unsupported')

    def test_one_sided_boundaries_log_scaling_and_nonsmooth_unresolved(self):
        for x in (1.,10.):
            row=dict(current_value=x,minimum=1.,maximum=10.,unit='m',continuous_perturbation=True)
            seen=[]
            def probe(v):
                seen.append(v);return dict(record_index=len(seen)-1,observation=dict(value=v*v,unit='1'))
            baseline=probe(x);result=differentiate(row,baseline,probe,goal='increase')
            np.testing.assert_allclose(result['derivatives'],[2*x]*2,rtol=1e-11)
            self.assertEqual(len(seen),4);self.assertTrue(all(1<=v<=10 for v in seen))
            if x==10:self.assertIsNone(result['suggested_delta'])
        row=dict(current_value=1e6,minimum=1e3,maximum=1e9,unit='Pa',continuous_perturbation=True)
        self.assertEqual(coordinate(row)['kind'],'normalized_log_domain')
        def log(v):return dict(record_index=1,observation=dict(value=float(np.log(v)),unit='1'))
        r=differentiate(row,log(1e6),log,goal='increase')
        np.testing.assert_allclose(r['derivatives'],[1e-6]*2,rtol=1e-10)
        row.update(current_value=1e6,minimum=0.,maximum=2e6)
        def cusp(v):return dict(record_index=1,observation=dict(value=abs(v-1e6),unit='1'))
        self.assertEqual(differentiate(row,cusp(1e6),cusp,goal='increase')['direction_status'],'unresolved')

    def test_directional_bounds_force_direction_and_geometric_compositions(self):
        m=dict(time_s=0.,qpos_rad=[0.]*3,qvel_rad_s=[0.]*3,
            coordinates=dict(dof_order=['a','b','c'],tendon_order=['t0','t1']),
            input_bounds_n=[[0.,8.],[1.,5.]],actual_tensions_n=[2.,3.],
            tip_acceleration_input_map_m_s2_n=[[2.,-1.],[0.,0.],[0.,0.]],tip_acceleration_m_s2=[7.,0.,0.],
            input_force_map_nm_n=[[1.,0.],[0.,2.],[0.,0.]],tip_jacobian_m_rad=np.eye(3).tolist(),
            tendon_jacobian_m_rad=[[1.,0.,0.],[0.,1.,0.]],
            components=dict(body_mass_kg=[1.,2.],body_inertia_kg_m2=[[1.,2.,3.]],joint_stiffness_nm_rad=[1.,2.,3.],damping_nm_s_rad=[0.,1.,2.]))
        self.assertEqual(observe(m,dict(quantity='directional_acceleration_bounds',direction_world=[1.,0.,0.]))['value'],[1.,21.])
        self.assertEqual(observe(m,dict(quantity='directional_drive',direction_world=[1.,0.,0.],tendon_channel=1))['value'],-1.)
        self.assertEqual(observe(m,dict(quantity='input_force_map',tendon_channel=1,reduction='direction_cosine',direction_generalized=[0.,1.,0.]))['value'],1.)
        for quantity,expected in [('directional_tendon_row_residual',1.),('motion_decoupling',1.)]:
            self.assertEqual(observe(m,dict(quantity=quantity,direction_world=[0.,0.,1.]))['value'],expected)
        self.assertEqual(observe(m,dict(quantity='total_mass'))['value'],3.)
        self.assertEqual(observe(m,dict(quantity='body_inertia_trace'))['value'],6.)

    def test_two_parameter_shared_baseline_joint_check_and_bounded_powell(self):
        for operation,cap in [('differentiate',10),('optimize',13)]:
            h,c=prepare();q=mechanism_question(operation);q.update(parameter_paths=['segments.0.length_m','segments.1.length_m'],requested_budget=cap)
            before=deepcopy(state(h)['candidates']);out=execute_synthetic(h,c,q);raw=h.store.artifact(out['reference'])['structure_research']
            self.assertEqual(state(h)['candidates'],before);self.assertTrue(raw['joint_direction_check']['passed'])
            self.assertTrue(raw['selected_joint_direction_check']['passed'])
            self.assertEqual(len(raw['parameter_sensitivities']),2);self.assertLessEqual(raw['cost']['model_builds'],cap)
            self.assertEqual(raw['cost']['physics_steps'],0);self.assertTrue(raw['structure_direction'])
            if operation=='optimize':
                self.assertIn('Powell',raw['local_search']['method'])
                for change in raw['structure_direction']['parameter_changes']:
                    self.assertLessEqual(abs(change['delta'])/(change['bounds'][1]-change['bounds'][0]),.02+1e-12)

    def test_v2_uses_existing_m1_and_exact_saved_state_semantics(self):
        h,c=prepare();other=generate(h,(.165,.11));diagnose(h,c,'scientific_question')
        q=mechanism_question();q.update(effect_semantics='fixed_input_response',target='tip_velocity',response_horizon_s=.01,
            comparison_candidates=[other],requested_budget=2)
        r=compile_question(h,q,tool_use_id='m1');self.assertEqual(r['status'],'ready',r)
        self.assertEqual(r['request']['operation'],'fixed_input_structure_v1');AnalysisRequest.model_validate(r['request'])
        q.update(operation='inspect',comparison_candidates=[],parameter_paths=[],requested_budget=1)
        r=compile_question(h,q,tool_use_id='m1-input');self.assertEqual(r['request']['operation'],'short_input_response_v1')
        q=mechanism_question();q['operating_point']='saved_native_state'
        self.assertEqual(compile_question(h,q,tool_use_id='no-source')['status'],'needs_prerequisite')
        # Same source must be explicit in the original request; no early reconstruction.
        from tools.research.state import save
        source=save(h,dict(candidate=c,phase='interval_start_native',input_units='N'),'synthetic-native-source')
        q['saved_state']=source
        r=compile_question(h,q,tool_use_id='saved-source');self.assertEqual(r['status'],'ready',r)
        parsed=AnalysisRequest.model_validate(r['request']);self.assertEqual(plain(parsed.saved_state),source)
        self.assertEqual(parsed.mechanism_study.point_semantics,'saved_native_state')

    def test_main_reads_may_reject_or_adopt_only_original_generate_creates_candidate(self):
        h,c=prepare();before=deepcopy(state(h)['candidates']);out=execute_synthetic(h,c,mechanism_question())
        ref=out['reference'];raw=deepcopy(h.store.artifact(ref));direction=raw['structure_research']['structure_direction']
        self.assertEqual(state(h)['candidates'],before)
        self.assertFalse(direction['formal_candidate_created']);self.assertTrue(direction['generation_handoff']['agent_decision_required'])
        report=reporter.assemble(h,[ref]);self.assertEqual(report.results[0].mathematics.claim.conclusion,'diagnostic')
        from tools.research.evidence_views import result_card
        compact=summary(raw,ref);handoff=compact['generation_handoff'];self.assertIn('reject',handoff['alternatives'])
        # Main rejection is simply no generation submission; reading never registers a proposal.
        core.read_tool_evidence(h,dict(reference=ref,view='working_set',pointer='/mathematical_decision_view'),record_read=True)
        self.assertEqual(state(h)['candidates'],before)
        # Adoption reads the exact validated generation request, then submits the existing Plan.
        request=core.read_evidence(h,handoff['generation_query'],record_read=False)
        plan=generation(h);plan.update(generation=request,supporting_evidence=[ref],hypothesis='Synthetic local mechanism direction, not measured task improvement.')
        wires=run_fixture(h,[('evidence_read',handoff['generation_query']),
            ('research_route',handoff['if_action_not_loaded']['input']),('research_plan',plan),None])
        receipt=feedback(h,'offline-use-2')['new_facts']['value'];self.assertEqual(receipt['status'],'generated',receipt)
        new=receipt['candidate'];self.assertEqual(len(state(h)['candidates']),len(before)+1)
        actual=resolved_request(state(h)['spec']['family_space'],h.store.artifact(new)['parameters'])
        expected=resolved_request(state(h)['spec']['family_space'],h.store.artifact(c)['parameters'])
        for change in direction['parameter_changes']:set_parameter(expected,change['parameter_path'],change['suggested_value'])
        self.assertEqual(actual,expected);self.assertEqual(h.store.artifact(ref),raw)
        brief=agent_decision_brief(h);self.assertTrue(brief['mechanism_research']['formal_candidate_created'])
        self.assertTrue(brief['mathematical_research']);self.assertTrue(packet(wires[-1])['mechanism_research'])
        atomic_json(ROOT/'runs/structure_mechanism_aplus_synthetic_handoff.json',dict(scope='SYNTHETIC ONLY; no real engine or Provider',
            source=ref,source_candidate=c,structure_direction=direction,main_generation_plan=plan,generated_candidate=new,
            rejection_candidate_count=len(before),adoption_candidate_count=len(state(h)['candidates']),reporter_claim='diagnostic',
            immutable_result_preserved=h.store.artifact(ref)==raw,mathematical_research=brief['mathematical_research'],mechanism_research=brief['mechanism_research']))


if __name__=='__main__':unittest.main()
