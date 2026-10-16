"""Focused saved analysis checks and opt-in real bounded MATLAB investigations."""
from copy import deepcopy
from pathlib import Path
import unittest
import numpy as np
from schemas.platform_analysis import TaskAnalysisProtocol, EndpointLinearizedModel
from tools.platform_store import plain
from tools.state_io import read,digest
from tools.research.config import resolve
from tools.research.design import source_lengths
from test_sorosim_contract import final_candidate,ROOT
from sorosim_s35_probe import save

BATCH=ROOT/'evidence/sorosim_s4a/attempt01'


class AnalysisTests(unittest.TestCase):
    def test_real_operating_points_and_derivatives(self):
        for name in ('standardized_initial_pretension','controller_start_input','target_equilibrium','halfway_waypoint'):
            row=read(BATCH/(name+'.json'))['records'][1]
            model=EndpointLinearizedModel.model_validate(row['model']);raw=row['raw_facts']
            self.assertEqual(np.shape(model.A),(24,24));self.assertEqual(np.shape(model.B),(24,4))
            self.assertTrue(raw['derivative_check']['passed'])
            self.assertEqual(raw['equilibrium'],name=='target_equilibrium')
            M=np.array(raw['raw']['mass_matrix']);A=np.array(model.A);B=np.array(model.B)
            np.testing.assert_allclose(M@A[12:,:12],-np.array(raw['raw']['Rq']),atol=1e-13,rtol=1e-9)
            np.testing.assert_allclose(M@B[12:],-np.array(raw['raw']['Ru']),atol=1e-13,rtol=1e-9)
        construction=read(BATCH/'target_equilibrium_raw.json')['result']['construction']
        self.assertLess(construction['static_residual_inf'],1e-10)
        self.assertLess(construction['position_residual_m'],1e-8)

    def test_real_loaded_input_and_full_rebuild_design_sensitivity(self):
        raw=read(BATCH/'static_input.json');self.assertTrue(raw['input_sensitivity']['verification']['passed'])
        self.assertGreater(np.linalg.norm(raw['raw']['tendon_force_q']),0)
        self.assertTrue(all(s['success'] for s in raw['input_sensitivity']['perturbed_equilibria']))
        s=read(BATCH/'design_sensitivity.json')['sensitivity']
        self.assertTrue(s['verification']['passed']);self.assertNotEqual(s['plus_identity'],s['minus_identity'])
        self.assertGreater(np.linalg.norm(s['p_d']),0)
        self.assertTrue(all(p['success'] for p in s['perturbed_equilibria']))
        self.assertLess(s['verification']['relative_norm'],1e-5)

    def test_real_shared_feasibility_has_distinct_scopes(self):
        self.assertEqual(read(BATCH/'target_equilibrium_endpoint.json')['status'],'feasible_in_local_model')
        exclusion=read(BATCH/'standardized_initial_pretension_trajectory.json')
        self.assertEqual(exclusion['status'],'model_infeasibility_certificate')
        self.assertTrue(exclusion['certificate']['verified'])
        saved=read(BATCH/'saved_state_trajectory.json')
        self.assertEqual(saved['scoped_claim']['conclusion'],'inconclusive')
        self.assertEqual(saved['task_acceptance'],'unmeasured')

    def test_existing_entrypoint_without_casadi_and_failed_point(self):
        import sys
        from unittest.mock import patch
        from tools.research.analysis import calculate,decision_result
        inp,_,p,binding=inputs();query=dict(candidate=binding['candidate'],operation='controllability',
            operating_point='standardized_initial_pretension',protocol=plain(p),scoring_window_s=.05)
        # Reuse real persisted SoRoSim model; this test performs only shared linear algebra.
        envelope=read(BATCH/'standardized_initial_pretension.json')
        with patch.dict(sys.modules,{'casadi':None}),patch('extensions.tendon_family.sorosim_analysis.calculate_candidate_configuration',return_value=envelope):
            out=calculate(plain(inp),binding,query)
        self.assertEqual(out['scoped_claim']['conclusion'],'diagnostic');self.assertIn('metrics',out)
        self.assertEqual(decision_result(out,binding['configuration'])['conclusion'],'diagnostic')
        failed=dict(records=[{},dict(name='standardized_initial_pretension',available=False,reason='INJECTED_SOLVER_FAILURE')])
        with patch('extensions.tendon_family.sorosim_analysis.calculate_candidate_configuration',return_value=failed):
            out=calculate(plain(inp),binding,query)
        self.assertEqual(out['scoped_claim']['conclusion'],'inconclusive')

    def test_nonsmooth_design_derivative_rejected(self):
        from extensions.tendon_family.sorosim_analysis import design_context
        from tools.research.contracts import StaticDesignSensitivity
        pair=read(BATCH/'design_pair.json');request=StaticDesignSensitivity.model_validate(pair['request'])
        _,_,p,_=inputs()
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_NONSMOOTH'):
            design_context(pair['base'],*pair['variants'],request.model_copy(update=dict(variable='segment_count')),p)


def inputs():
    inp,source=final_candidate();cfg=plain(inp)
    study=resolve(ROOT/'configs/research/study_m3d_agent_feedback.json',backend_profile='sorosim_matlab_v1')
    p=TaskAnalysisProtocol(**{**study['analysis_protocol'],'baseline_lengths_m':source_lengths(cfg),
        'duration_s':inp.task.timing.duration_s,'period_s':inp.task.timing.control_period_s})
    binding=dict(candidate_id=source['candidate']['artifact_id'],candidate=source['candidate'],
        configuration=dict(artifact_id=digest(cfg)),basis=cfg['policy']['controller']['parameters']['data']['recipe']['basis'],
        effective_configuration_identity=digest(cfg),task_identity=digest(cfg['task']))
    binding.update(tendon_order=[t['id'] for t in cfg['robot']['structure']['data']['tendons']],
        tension_limits_n=[t['force_limit_n'] for t in cfg['robot']['structure']['data']['tendons']])
    return inp,study,p,binding


def run(folder):
    from extensions.tendon_family.sorosim_analysis import prepare,calculate_candidate_configuration
    from extensions.tendon_family.sorosim_session import SorosimSession
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    inp,study,p,binding=inputs();spec,numerical,scales=prepare(inp,p)
    save(folder,'configuration',plain(inp));save(folder,'protocol',plain(p));save(folder,'binding',binding)
    save(folder,'budget',dict(scope='user authorized S4-A engineering diagnostics',maximum_candidate_evaluations=12,
        planned_operations=['initial','controller_start','target','halfway','fixed_input_equilibrium'],provider_requests=0,physical_steps=0))
    session=SorosimSession()
    try:
        with session:
            session.construct(spec)
            save(folder,'environment',dict(environment=session.environment,dependency=session.dependency,specification=spec))
            for name in ('standardized_initial_pretension','controller_start_input','target_equilibrium','halfway_waypoint'):
                value=calculate_candidate_configuration(inp,binding,p,binding['configuration'],operating_points=[name],
                    session=session,checkpoint=lambda name,v:save(folder,name+'_raw',v))
                save(folder,name,plain(value));print(name,plain(value)['records'][-1].get('reason','computed'),flush=True)
            raw=session.evaluate('analysis',dict(operation='static_input',x=numerical['measured_initial_state'],
                u=numerical['nominal']['u0'],protocol=plain(p),state_scales=scales))
            save(folder,'static_input',raw);print('static_input',raw['status'],flush=True)
    except BaseException as exc:
        save(folder,'failure',dict(type=type(exc).__name__,error=str(exc)));raise
    finally:save(folder,'timings',session.timings)


def extend(folder):
    """Two further investigations: saved state and rebuilt length sensitivity."""
    from extensions.tendon_family.family_space import parse_build
    from extensions.tendon_family.generated_serial import generate_family
    from extensions.tendon_family.sorosim_analysis import design_context
    from tools.research.contracts import StaticDesignSensitivity
    from tools.research.analysis import calculate
    from sorosim_s35_probe import RAW
    folder=Path(folder);inp,study,p,binding=inputs();cfg=plain(inp)
    parameters=deepcopy(inp.policy.candidate_builder.parameters.data['request'])
    base=dict(configuration=cfg,parameters=parameters);variants=[];step=parameters['segments']['0']['length_m']*1e-4
    for sign in (-1,1):
        request=deepcopy(parameters);request['segments']['0']['length_m']+=sign*step
        design,mesh,physics=generate_family(parse_build(dict(space=study['family_space'],request=request)))
        new=deepcopy(cfg);new['robot']['structure']['data']=design;new['policy']['discretization']['data']=mesh
        new['policy']['candidate_builder']['parameters']['data']['request']=request
        variants.append(dict(configuration=new,parameters=request,physical_design_identity=physics['design_identity']))
    refs=[dict(artifact_id=digest(v)) for v in variants]
    sensitivity=StaticDesignSensitivity(variable='segments.0.length_m',step=step,minus_candidate=refs[0],plus_candidate=refs[1])
    context=design_context(base,*variants,sensitivity,p)
    save(folder,'design_pair',dict(base=base,variants=variants,request=plain(sensitivity),
        source='Existing family generator and frozen study domains; engineering diagnostic, not charged as live study candidates.'))
    query=dict(candidate=binding['candidate'],operation='design_sensitivity',operating_point='fixed_input_equilibrium',
        protocol=plain(p),design_sensitivity=plain(sensitivity))
    result=calculate(cfg,binding,query,design_context=context,checkpoint=lambda name,v:save(folder,'design_'+name+'_raw',v))
    save(folder,'design_sensitivity',result);print('design_sensitivity',result['status'],flush=True)
    saved=read(ROOT/'evidence/sorosim_s35/attempt02/physical.json')['probes'][2]
    exact=dict(name='saved_state',available=True,x=saved['x'],u=saved['u'],actual_time_s=.02,
        remaining_task_s=inp.task.timing.duration_s-.02,construction=dict(method='archived exact represented state',source=str(RAW.relative_to(ROOT))))
    query=dict(candidate=binding['candidate'],operation='trajectory_feasibility',operating_point='saved_state',
        saved_state=dict(artifact_id=digest(saved)),protocol=plain(p))
    result=calculate(cfg,binding,query,exact,checkpoint=lambda name,v:save(folder,name+'_raw',v))
    save(folder,'saved_state_trajectory',result);print('saved_state_trajectory',result['status'],result.get('trajectory',{}).get('status'),flush=True)


def shared_checks(folder):
    """Real shared kernels on saved SoRoSim arrays; no MATLAB or nonlinear solves."""
    from extensions.math_analysis.tools import calculate_control_metrics
    from extensions.math_analysis.kernels import bounded_endpoint
    from extensions.math_analysis.trajectory import trajectory_feasibility
    from schemas.platform_analysis import EndpointTarget
    from tools.research.task_constraints import describe_analysis_requirements
    folder=Path(folder);inp,study,p,binding=inputs()
    req=describe_analysis_requirements(inp,binding)
    target=EndpointTarget(position_m=inp.task.goal.data['target_m'],position_tolerance_m=inp.task.evaluator.parameters.data['tolerance_m'],
        position_scale_m=p.output_scale_m,tip_speed_limit_m_s=inp.policy.controller.parameters.data['settling']['speed_limit_m_s'])
    for name in ('standardized_initial_pretension','target_equilibrium'):
        model=EndpointLinearizedModel.model_validate(read(folder/(name+'.json'))['records'][1]['model'])
        metrics=calculate_control_metrics(model,p);save(folder,name+'_metrics',metrics)
        endpoint=bounded_endpoint(model,p,target,braking=True);save(folder,name+'_endpoint',endpoint)
        if name=='standardized_initial_pretension':
            model=model.model_copy(update=dict(operating_point={**model.operating_point,'actual_time_s':0.}))
            result=trajectory_feasibility(model,req,p);save(folder,name+'_trajectory',result)
        print(name,'metrics and bounded feasibility persisted',flush=True)


def resume_saved(folder):
    """Rebind a successfully persisted MATLAB result; never repeat its solve."""
    from unittest.mock import patch
    from tools.research.analysis import calculate
    from extensions.tendon_family.sorosim_analysis import prepare,linear_model
    folder=Path(folder);inp,study,p,binding=inputs();spec,_,scales=prepare(inp,p)
    raw=read(folder/'saved_state_raw.json')['result']
    point=dict(name='saved_state',available=True,actual_time_s=.02,remaining_task_s=p.duration_s-.02,
        construction=raw['construction'])
    model=linear_model(inp,binding,p,point,raw,spec,scales)
    envelope=dict(records=[{},dict(model=plain(model),point=point,construction=raw['construction'],raw_facts=raw)])
    query=dict(candidate=binding['candidate'],operation='trajectory_feasibility',operating_point='saved_state',
        saved_state=dict(artifact_id=digest(raw)),protocol=plain(p))
    with patch('extensions.tendon_family.sorosim_analysis.calculate_candidate_configuration',return_value=envelope):
        result=calculate(plain(inp),binding,query,dict(point,x=raw['x'],u=raw['u']))
    result['recovery']=dict(source='saved_state_raw.json',additional_matlab_operations=0,
        reason='Engineering test binding lacked tension_limits_n at final packaging; pure shared kernels rerun on preserved real arrays.')
    save(folder,'saved_state_trajectory',result)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path);parser.add_argument('--extend',type=Path)
    parser.add_argument('--shared',type=Path);parser.add_argument('--resume',type=Path);args=parser.parse_args()
    if args.run:run(args.run)
    elif args.extend:extend(args.extend)
    elif args.shared:shared_checks(args.shared)
    elif args.resume:resume_saved(args.resume)
    else:unittest.main(argv=['test_sorosim_analysis'])
