"""Candidate-local full-task MATLAB optimization for the existing mechanics worker."""
import numpy as np
from schemas.platform import SessionInput
from schemas.platform_analysis import ScopedMathematicalClaim
from tools.platform_store import plain
from tools.state_io import digest
from tools.research.task_constraints import describe_analysis_requirements
from .sorosim_control import checked_control
from .sorosim_spec import SorosimModel
from .sorosim_session import SorosimSession
from .gvs_profile import candidate_numerical


def compare_refinements(coarse, fine):
    """Observed aligned vector differences; these are not continuous-time bounds."""
    times=np.asarray(coarse['times_s'])
    if (not coarse['complete'] or not fine['complete'] or
            not np.array_equal(times,np.asarray(fine['times_s']))):
        raise ValueError('COMPLETE_IDENTICAL_OUTPUT_GRIDS_REQUIRED')
    dp=np.asarray(fine['tip_positions_m'])-coarse['tip_positions_m']
    dv=np.asarray(fine['tip_velocities_m_s'])-coarse['tip_velocities_m_s']
    pn=np.linalg.norm(dp,axis=1);vn=np.linalg.norm(dv,axis=1)
    windows=[]
    for lo,hi in ((0.,.01),(.14,.16),(.25,.29),(.29,.30),(.30,.35)):
        mask=(times>=lo-1e-12)&(times<=hi+1e-12)
        windows.append(dict(interval_s=[lo,hi],maximum_position_m=float(max(pn[mask])),
            maximum_velocity_m_s=float(max(vn[mask]))))
    return dict(times_s=times.tolist(),position_difference_m=dp.tolist(),
        velocity_difference_m_s=dv.tolist(),position_norm_m=pn.tolist(),velocity_norm_m_s=vn.tolist(),
        maximum_position_m=float(max(pn)),maximum_velocity_m_s=float(max(vn)),
        position_tolerance_fraction=float(max(pn)/.01),speed_tolerance_fraction=float(max(vn)/.02),
        largest_position_time_s=float(times[np.argmax(pn)]),
        largest_velocity_time_s=float(times[np.argmax(vn)]),windows=windows,
        interpretation='observed numerical differences, no rigorous error bound')


def refine_fixed_sequence(configuration, candidate_ref, source, substeps):
    """Reintegrate one archived physical input grid with production implicit roots."""
    inp=SessionInput.model_validate(configuration);control=checked_control(inp)
    numerical=candidate_numerical(inp,control);timing=inp.task.timing
    spec=SorosimModel(dict(basis=control.recipe.basis,
        gauss_per_interval=control.solver.gauss_per_interval)).convert(
        inp.robot.structure.data,inp.policy.discretization.data,inp.task.environment.data,solver=control.solver)
    trajectory=source['trajectory'];source_times=trajectory['times_s'];u=trajectory['tensions_n']
    N=round(timing.duration_s/timing.control_period_s)
    times=[i*timing.control_period_s for i in range(N+1)]
    for key,expected in (('model_identity',spec['identity']),('design_identity',spec['design_identity']),
                         ('task_identity',digest(plain(inp.task))),('tendon_order',spec['tendon_order']),
                         ('coordinate_order',spec['coordinate_order'])):
        if trajectory[key]!=expected:
            raise ValueError('REFINEMENT_SOURCE_IDENTITY_MISMATCH: '+key)
    if (substeps not in (2,4,8,16,32,64) or len(u)!=N or
            len(source_times)!=len(trajectory['states']) or
            any(not any(abs(t-s)<1e-12 for s in source_times) for t in times) or
            any(b<=a for a,b in zip(source_times,source_times[1:])) or
            abs(source_times[0])>1e-12 or abs(source_times[-1]-timing.duration_s)>1e-12 or
            not np.allclose(trajectory['states'][0],numerical['measured_initial_state'],atol=1e-12,rtol=0)):
        raise ValueError('REFINEMENT_GRID_OR_INITIAL_STATE_MISMATCH')
    tensions=np.asarray(u,dtype=float)
    configured_limits={t['id']:t['force_limit_n'] for t in
        configuration['robot']['structure']['data']['tendons']}
    limits=np.asarray([configured_limits[name] for name in spec['tendon_order']])
    if (tensions.shape!=(N,len(spec['routes'])) or not np.isfinite(tensions).all() or
            np.any(tensions<0) or np.any(tensions>limits)):
        raise ValueError('REFINEMENT_TENSION_OR_FORCE_LIMIT_MISMATCH')
    request=dict(kind='fixed_sequence',x=trajectory['states'][0],u=u[0],
        a=[0.]*len(spec['coordinate_order']),tensions_n=u,times_s=times,
        period_s=timing.control_period_s,substeps=substeps)
    with SorosimSession() as session:
        session.construct(spec)
        out=session.evaluate('diagnose',request)
        environment=dict(environment=session.environment,dependency=session.dependency,
            timings=session.timings)
    result=dict(status=out['status'],complete=out['complete'],candidate=candidate_ref,
        model_identity=spec['identity'],source_identity=digest(trajectory),
        tension_sequence_sha256=digest(dict(tensions_n=u,times_s=times,tendon_order=spec['tendon_order'])),
        state_trajectory_sha256=digest(out['states']),substeps=substeps,
        initial_state=out['initial_state'],raw=out,numerical_environment=environment,
        task_acceptance='unmeasured')
    if not out['complete']:
        result.update(original_task_satisfied=False,reason='INCOMPLETE_INTEGRATION')
        return result
    binding=dict(candidate=candidate_ref,configuration_identity=digest(plain(inp)),
        design_identity=spec['design_identity'],physics_identity=spec['physics_identity'])
    requirements=plain(describe_analysis_requirements(inp,binding))
    positions=np.asarray(out['tip_positions_m']);velocities=np.asarray(out['tip_velocities_m_s'])
    violations=[]
    for constraint in requirements['constraints']:
        values=velocities if constraint['signal']['name']=='tip_velocity' else positions
        for index,reference in zip(constraint['indices'],constraint['reference']):
            norm=float(np.linalg.norm(values[index]-reference))
            if norm>constraint['radius']:
                violations.append(dict(constraint_id=constraint['constraint_id'],sample_index=index,
                    time_s=times[index],value=norm,limit=constraint['radius'],excess=norm-constraint['radius']))
    start=timing.duration_s-control.settling.window_s
    hold=[i for i,t in enumerate(times) if t>=start-1e-12]
    target=np.asarray(inp.task.goal.data['target_m'])
    errors=np.linalg.norm(positions-target,axis=1)
    result.update(terminal_position_error_m=float(errors[-1]),
        holding_max_position_error_m=float(max(errors[hold])),
        holding_max_speed_m_s=float(max(np.linalg.norm(velocities[hold],axis=1))),
        time_localized_task_violations=violations,original_task_satisfied=not violations,
        root_count=N*substeps)
    return result


def calculate(request,checkpoint=None):
    inp=SessionInput.model_validate(request['configuration']);control=checked_control(inp)
    numerical=candidate_numerical(inp,control);timing=inp.task.timing
    spec=SorosimModel(dict(basis=control.recipe.basis,gauss_per_interval=control.solver.gauss_per_interval)).convert(
        inp.robot.structure.data,inp.policy.discretization.data,inp.task.environment.data,solver=control.solver)
    binding=dict(candidate=request['design_candidate'],configuration_identity=digest(plain(inp)),
        design_identity=spec['design_identity'],physics_identity=spec['physics_identity'])
    requirements=plain(describe_analysis_requirements(inp,binding));steps=round(timing.duration_s/timing.control_period_s)
    if any(c['kind']!='norm_bound' or c['signal']['name'] not in ('tip_position','tip_velocity') for c in requirements['constraints']):
        raise ValueError('UNSUPPORTED_CODESIGN_TASK_REQUIREMENTS')
    if request['operation']=='solve':
        arguments={k:v for k,v in request['arguments'].items() if k!='candidate'};substeps=arguments['substeps']
        tensions=np.full((steps,len(spec['routes'])),.2)
        if arguments['initialization']=='ramp_0_2_to_0_4':tensions[:]=np.linspace(.2,.4,steps)[:,None]
        if arguments['initialization']=='saved_candidate_controls':
            warm=request['warm_trajectory']
            for key,value in [('model_identity',spec['identity']),('design_identity',spec['design_identity']),
                    ('task_identity',digest(plain(inp.task))),('coordinate_order',spec['coordinate_order']),
                    ('tendon_order',spec['tendon_order'])]:
                if warm[key]!=value:raise ValueError('CODESIGN_WARM_IDENTITY_MISMATCH: '+key)
            tensions=np.asarray(warm['tensions_n'],dtype=float)
            limits=np.asarray(requirements['physical_inputs']['upper'])
            if (tensions.shape!=(steps,len(spec['routes'])) or not np.isfinite(tensions).all() or
                    np.any(tensions<0) or np.any(tensions>limits) or
                    any(not any(abs(t-s)<1e-12 for s in warm['times_s']) for t in requirements['time_grid_s']) or
                    not np.allclose(warm['states'][0],numerical['measured_initial_state'],atol=1e-12,rtol=0)):
                raise ValueError('CODESIGN_WARM_CONTROL_GRID_OR_INITIAL_MISMATCH')
        if arguments['initialization']=='saved_candidate_trajectory':
            warm=request['warm_trajectory']
            for key,value in [('model_identity',spec['identity']),('design_identity',spec['design_identity']),
                ('task_identity',digest(plain(inp.task))),('coordinate_order',spec['coordinate_order']),
                ('tendon_order',spec['tendon_order']),('substeps',substeps)]:
                if warm[key]!=value:raise ValueError('CODESIGN_WARM_IDENTITY_MISMATCH: '+key)
            if (len(warm['times_s'])!=steps*substeps+1 or
                    any(abs(t-i*timing.control_period_s/substeps)>1e-12 for i,t in enumerate(warm['times_s']))):
                raise ValueError('CODESIGN_WARM_TIME_GRID_MISMATCH')
            states=np.asarray(warm['states'],dtype=float)
            tensions=np.asarray(warm['tensions_n'],dtype=float)
            limits=np.asarray(requirements['physical_inputs']['upper'])
            if (states.shape!=(steps*substeps+1,len(numerical['measured_initial_state'])) or
                    not np.isfinite(states).all() or not np.allclose(states[0],numerical['measured_initial_state'],atol=1e-12,rtol=0)):
                raise ValueError('CODESIGN_WARM_FULL_STATE_OR_INITIAL_MISMATCH')
            if (tensions.shape!=(steps,len(spec['routes'])) or not np.isfinite(tensions).all() or
                    np.any(tensions<0) or np.any(tensions>limits)):
                raise ValueError('CODESIGN_WARM_TENSION_OUT_OF_BOUNDS')
            slacks=warm.get('slacks',{})
            if (not all(k in slacks and np.isfinite(slacks[k]) for k in ('position','speed')) or
                    slacks['speed']!=0):
                raise ValueError('CODESIGN_WARM_EPIGRAPH_MISSING')
    else:
        trajectory=request['trajectory'];arguments=trajectory['objective_definition'];substeps=trajectory['substeps']
        shared=[('task_identity',digest(plain(inp.task))),('tendon_order',spec['tendon_order'])]
        if request['operation']=='replay':
            shared += [('model_identity',spec['identity']),('design_identity',spec['design_identity']),
                ('coordinate_order',spec['coordinate_order'])]
        elif request['operation']=='cross_replay':
            if trajectory['design_identity']==spec['design_identity']:
                raise ValueError('CROSS_REPLAY_REQUIRES_DISTINCT_DESIGNS')
            if len(trajectory['tensions_n'])!=steps or any(len(u)!=len(spec['routes']) for u in trajectory['tensions_n']):
                raise ValueError('CROSS_REPLAY_INCOMPLETE_TENSION_SEQUENCE')
            if len(trajectory['times_s'])!=steps+1 or not np.allclose(trajectory['times_s'],requirements['time_grid_s'],rtol=0,atol=1e-12):
                raise ValueError('CROSS_REPLAY_TIME_GRID_MISMATCH')
        else:
            raise ValueError('UNSUPPORTED_CODESIGN_OPERATION')
        for key,value in shared:
            if trajectory[key]!=value:raise ValueError('CODESIGN_REPLAY_IDENTITY_MISMATCH: '+key)
        tensions=np.array(trajectory['tensions_n'])
        if request['operation']=='cross_replay':
            limits=np.asarray(requirements['physical_inputs']['upper'])
            if not np.isfinite(tensions).all() or np.any(tensions<0) or np.any(tensions>limits):
                raise ValueError('CROSS_REPLAY_TENSION_OUT_OF_BOUNDS')
    recipe=plain(control.recipe);recipe['substeps']=substeps
    recipe['max_iterations']=arguments.get('max_iterations',recipe['max_iterations'])
    nmpc=dict(recipe=recipe,elapsed_s=0.,measured_state=numerical['measured_initial_state'],
        previous_input=numerical['nominal']['u0'],warm=None,period_s=timing.control_period_s,duration_s=timing.duration_s,
        target=inp.task.goal.data['target_m'],position_tolerance_m=inp.task.evaluator.parameters.data['tolerance_m'],
        settling=plain(control.settling),initial_tensions=tensions.tolist())
    payload=dict(operation=request['operation'],control=nmpc,requirements=requirements,arguments=arguments)
    if request.get('warm_trajectory') is not None and arguments.get('initialization')!='saved_candidate_controls':
        payload['warm_trajectory']=request['warm_trajectory']
    if request.get('check_only'):payload['check_only']=True
    if request.get('checkpoint_path'):payload['checkpoint_path']=request['checkpoint_path']
    if request['operation'] in ('replay','cross_replay'):payload['trajectory']=trajectory
    with SorosimSession() as session:
        session.construct(spec)
        if checkpoint:checkpoint('environment',dict(environment=session.environment,dependency=session.dependency,specification=spec))
        out=session.evaluate('codesign',payload)
        if checkpoint:checkpoint('matlab_result',out)
        if request.get('check_only'):return out
        if request['operation']=='solve':
            out['trajectory'].update(model_identity=spec['identity'],design_identity=spec['design_identity'],
                task_identity=digest(plain(inp.task)),coordinate_order=spec['coordinate_order'],tendon_order=spec['tendon_order'],
                objective_definition=arguments,substeps=substeps,design_candidate=request['design_candidate'])
        elif request['operation']=='cross_replay':
            out['trajectory'].update(model_identity=spec['identity'],design_identity=spec['design_identity'],
                task_identity=digest(plain(inp.task)),coordinate_order=spec['coordinate_order'],tendon_order=spec['tendon_order'],
                objective_definition=arguments,substeps=substeps,design_candidate=request['design_candidate'])
        verified=request['operation'] in ('replay','cross_replay') and out['passed']
        failed=('REPLAY_MISMATCH' if not out['passed'] else None) if request['operation'] in ('replay','cross_replay') else (
            'RETURNED_TRAJECTORY_INFEASIBLE' if not out['relaxed_feasible'] else
            'OPTIMIZER_NOT_CONVERGED' if not out['converged'] else None)
        diagnostic=dict(stage='S4.5' if request['operation']=='cross_replay' else 'S4-B',operation=request['operation'],candidate=request['design_candidate'],
            model_identity=spec['identity'],operating_point=dict(x=numerical['measured_initial_state'],
                u=numerical['nominal']['u0'],time_s=0.),numerical_method='full-task SQP / implicit Euler',
            status=out['status'],failure_code=failed,first_failed_check=failed,
            dimensions=dict(state=len(numerical['measured_initial_state']),inputs=len(spec['routes']),intervals=steps),
            units=spec['units'],numerical_work={k:out[k] for k in ('iterations','function_evaluations') if k in out},
            timing={k:v for k,v in out.items() if k.endswith('_s')},evidence_pointer='/mathematical_facts',
            raw_error=out.get('message'),supported_conclusions='Relaxed feasibility requires separate replay; optimizer convergence reported separately.',
            unsupported_conclusions=['physical task acceptance','global optimality'])
        claim=ScopedMathematicalClaim(conclusion='feasible_witness' if verified and (request['operation']=='replay' or out['task']['original_sampled_requirements_satisfied']) else 'inconclusive',binding=binding,
            requirement_identity=digest(requirements),model_identity=spec['identity'],
            model_declaration=dict(provider='model.sorosim_gvs@1.0.0',protocol='sorosim_full_task_gap_v1'),
            protocol_identity=digest(arguments),operating_point=dict(x=numerical['measured_initial_state'],time_s=0.),
            horizon=dict(duration_s=timing.duration_s,control_intervals=steps,substeps=substeps),
            physical_inputs=requirements['physical_inputs'],constraint_coverage=requirements['constraints'],
            numerical_result_pointer='/mathematical_facts',computation_status=out['status'],
            verification_status='independent_implicit_replay_passed' if verified else 'requires_independent_replay',
            supported_interpretation='Full-task relaxed rod-model trajectory verified with explicitly reported task slacks.' if verified else
                'Returned mathematical optimization; solver status alone is not feasibility evidence.',
            unsupported_conclusions=['physical task success','original unrelaxed constraints when slacks are nonzero','global optimality','dynamic model equivalence to MuJoCo'])
        return dict(status='computed',mathematical_facts=out,diagnostic=diagnostic,trajectory=out.get('trajectory'),
            replay=out if request['operation'] in ('replay','cross_replay') else None,task_requirements=requirements,
            objective_definition=arguments,verified_conclusions=[plain(claim)],research_interpretations=[],
            numerical_environment=dict(environment=session.environment,timings=session.timings),
            physical_validation='not_run',task_acceptance='unmeasured')
