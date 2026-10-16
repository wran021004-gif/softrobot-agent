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
    else:
        trajectory=request['trajectory'];arguments=trajectory['objective_definition'];substeps=trajectory['substeps']
        for key,value in [('model_identity',spec['identity']),('design_identity',spec['design_identity']),
            ('task_identity',digest(plain(inp.task))),('coordinate_order',spec['coordinate_order']),('tendon_order',spec['tendon_order'])]:
            if trajectory[key]!=value:raise ValueError('CODESIGN_REPLAY_IDENTITY_MISMATCH: '+key)
        tensions=np.array(trajectory['tensions_n'])
    recipe=plain(control.recipe);recipe['substeps']=substeps
    nmpc=dict(recipe=recipe,elapsed_s=0.,measured_state=numerical['measured_initial_state'],
        previous_input=numerical['nominal']['u0'],warm=None,period_s=timing.control_period_s,duration_s=timing.duration_s,
        target=inp.task.goal.data['target_m'],position_tolerance_m=inp.task.evaluator.parameters.data['tolerance_m'],
        settling=plain(control.settling),initial_tensions=tensions.tolist())
    payload=dict(operation=request['operation'],control=nmpc,requirements=requirements,arguments=arguments)
    if request.get('check_only'):payload['check_only']=True
    if request.get('checkpoint_path'):payload['checkpoint_path']=request['checkpoint_path']
    if request['operation']=='replay':payload['trajectory']=trajectory
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
        verified=request['operation']=='replay' and out['passed']
        claim=ScopedMathematicalClaim(conclusion='feasible_witness' if verified else 'inconclusive',binding=binding,
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
        return dict(status='computed',mathematical_facts=out,trajectory=out.get('trajectory'),
            replay=out if request['operation']=='replay' else None,task_requirements=requirements,
            objective_definition=arguments,verified_conclusions=[plain(claim)],research_interpretations=[],
            numerical_environment=dict(environment=session.environment,timings=session.timings),
            physical_validation='not_run',task_acceptance='unmeasured')
