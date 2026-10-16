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
        if arguments['initialization']=='saved_candidate_trajectory':
            warm=request['warm_trajectory']
            for key,value in [('design_identity',spec['design_identity']),('task_identity',digest(plain(inp.task))),
                ('tendon_order',spec['tendon_order'])]:
                if warm[key]!=value:raise ValueError('CODESIGN_WARM_IDENTITY_MISMATCH: '+key)
            if len(warm['tensions_n'])!=steps or any(len(u)!=len(spec['routes']) for u in warm['tensions_n']):
                raise ValueError('CODESIGN_WARM_SEQUENCE_INCOMPLETE')
            tensions=np.array(warm['tensions_n'])
            limits=np.asarray(requirements['physical_inputs']['upper'])
            if not np.isfinite(tensions).all() or np.any(tensions<0) or np.any(tensions>limits):
                raise ValueError('CODESIGN_WARM_TENSION_OUT_OF_BOUNDS')
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
    nmpc=dict(recipe=recipe,elapsed_s=0.,measured_state=numerical['measured_initial_state'],
        previous_input=numerical['nominal']['u0'],warm=None,period_s=timing.control_period_s,duration_s=timing.duration_s,
        target=inp.task.goal.data['target_m'],position_tolerance_m=inp.task.evaluator.parameters.data['tolerance_m'],
        settling=plain(control.settling),initial_tensions=tensions.tolist())
    payload=dict(operation=request['operation'],control=nmpc,requirements=requirements,arguments=arguments)
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
