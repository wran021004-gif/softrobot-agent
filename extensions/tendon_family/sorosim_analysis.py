"""SoRoSim binding to the existing candidate and EndpointLinearizedModel contracts."""
from contextlib import nullcontext
import numpy as np
from schemas.platform import SignalSpec, Binding, Payload
from schemas.platform_analysis import AnalysisResult, EndpointLinearizedModel, EndpointOutputLinearization
from tools.platform_store import plain
from tools.state_io import digest
from .sorosim_control import checked_control
from .sorosim_spec import SorosimModel
from .sorosim_session import SorosimSession
from .gvs_profile import candidate_numerical
from .math_analysis import _configuration_boundary, _validate_task_protocol
from extensions.math_analysis.kernels import LIMITATIONS


def prepare(inp,p):
    _validate_task_protocol(inp,p)
    control=checked_control(inp);numerical=candidate_numerical(inp,control)
    spec=SorosimModel(dict(basis=control.recipe.basis,gauss_per_interval=control.solver.gauss_per_interval)).convert(
        inp.robot.structure.data,inp.policy.discretization.data,inp.task.environment.data,solver=control.solver)
    qs=[1/p.baseline_lengths_m[name.split('.')[0]] for name in spec['coordinate_order']]
    return spec,numerical,qs+[q/p.duration_s for q in qs]


def linear_model(inp,binding,p,point,raw,spec,scales):
    """Only conversion; residual differentiation and conditioning stay in MATLAB."""
    state=[SignalSpec(name=name+suffix,entity=name.split('.')[0],dimension=1,units=unit,
        frame='segment_local',phase='continuous_state') for suffix,unit in [('', 'rad/m'),('.rate','rad/(m*s)')]
        for name in spec['coordinate_order']]
    inputs=[SignalSpec(name='tendon_tension',entity=name,dimension=1,units='N',frame='tendon_path',
        phase='continuous_input') for name in spec['tendon_order']]
    position=EndpointOutputLinearization(name='tip_position',units='m',value0=raw['position'],C=raw['C'],D=raw['D'],scales=[p.output_scale_m]*3)
    velocity=EndpointOutputLinearization(name='tip_velocity',units='m/s',value0=raw['velocity'],C=raw['Cv'],D=raw['Dv'],scales=[p.output_scale_m/p.duration_s]*3)
    bound={**binding,'model_identity':spec['identity'],'model_provider':'model.sorosim_gvs@1.0.0',
        'basis':spec['resolved_basis'],'coordinate_order':spec['coordinate_order'],'tendon_order':spec['tendon_order'],
        'tension_limits_n':[r['force_limit_n'] for r in spec['routes']],
        'analysis_protocol_identity':digest(plain(p)),'mount':inp.task.environment.data['mount'],
        'task_duration_s':inp.task.timing.duration_s,'control_period_s':inp.task.timing.control_period_s,
        'physics_timestep_s':inp.task.timing.timestep_s,'target_m':inp.task.goal.data['target_m'],
        'output_expression':'world pose/J(q) and world J(q)*qdot; MATLAB-local residual derivatives',
        'derivative_method':raw['raw']['derivative_method']}
    return EndpointLinearizedModel(state_definition=state,input_definition=inputs,
        output_definition=[SignalSpec(name='tip_position',entity='tip',dimension=3,units='m',frame='world',phase='instantaneous')],
        x0=raw['x'],u0=raw['u'],y0=raw['position'],A=raw['A'],B=raw['B'],C=raw['C'],D=raw['D'],drift=raw['drift'],
        time_domain='continuous',binding=bound,operating_point={**point,'equilibrium':raw['equilibrium'],
            'linearization_scope':raw['linearization_scope']},state_scales=scales,input_scales=[p.input_scale_n]*len(inputs),
        output_scales=[p.output_scale_m]*3,normalization_derivation='Curvature 1/baseline segment length; rate divided by protocol duration; input/output scales from frozen protocol.',
        protocol_identity=digest(plain(p)),evidence=[binding['configuration']],endpoint_outputs=[position,velocity])


def calculate_candidate_configuration(inp,binding,p,protocol_ref,*,registry=None,operating_points=None,
                                      exact_point=None,session=None,checkpoint=None,design_context=None):
    from .model_applicability import assess_model_uses
    spec,numerical,scales=prepare(inp,p)
    boundary=_configuration_boundary(inp,binding,'model.sorosim_gvs')
    names=operating_points or ['standardized_initial_pretension','controller_start_input','target_equilibrium','halfway_waypoint']
    records=[];initial=numerical['measured_initial_state']
    pretension=[t['pretension_n'] for t in inp.robot.structure.data['tendons']]
    with (SorosimSession() if session is None else nullcontext(session)) as engine:
        if engine.model_identity is None:engine.construct(spec)
        if engine.model_identity!=spec['identity']:raise ValueError('ANALYSIS_CANDIDATE_SESSION_MISMATCH')
        for name in names:
            point=dict(name=name,phase='configuration_'+name,remaining_task_s=p.duration_s,actual_time_s=None,
                construction=dict(method='existing candidate initializer/control preparation',provenance=numerical['provenance']))
            x=initial;u=numerical['nominal']['u0'] if name=='controller_start_input' else pretension
            if name=='saved_state':
                if exact_point is None:
                    records.append(dict(name=name,available=False,reason='SAVED_STATE_EVIDENCE_UNAVAILABLE'));continue
                point={k:v for k,v in exact_point.items() if k not in ('x','u')};x=exact_point['x'];u=exact_point['u']
            operation=name if name in ('target_equilibrium','halfway_waypoint') else 'linearize'
            if name=='fixed_input_equilibrium':operation='design_sensitivity' if design_context else 'static_input'
            target=np.array(inp.task.goal.data['target_m'])
            if name=='halfway_waypoint':
                # Existing kinematics operation; the task and initializer still own the target.
                initial_routing=engine.evaluate('routing',dict(q=x[:len(x)//2],u=u))
                if checkpoint:checkpoint('halfway_initial_routing',initial_routing)
                start=np.array(spec['mount_rotation'])@np.array(initial_routing['tip_pose'])[:3,3]+spec['mount_position']
                target=(start+target)/2
            payload=dict(operation=operation,x=x,u=u,protocol=plain(p),state_scales=scales,target=target.tolist(),
                position_tolerance_m=inp.task.evaluator.parameters.data['tolerance_m'])
            if design_context:
                payload.update(design_context)
            raw=engine.evaluate('analysis',payload)
            if checkpoint:checkpoint(name,dict(request=payload,result=raw))
            construction={**point.get('construction',{}),**raw['construction']}
            diagnostic=dict(stage='S4-A',operation=operation,candidate=binding.get('candidate'),
                model_identity=spec['identity'],operating_point=dict(name=name,x=raw['x'],u=raw['u']),
                numerical_method='SoRoSim residual derivatives / MATLAB local optimization',status=raw['status'],
                failure_code=raw['failure_code'],first_failed_check=raw['failure_code'] or None,
                dimensions=dict(state=len(x),input=len(u)),units=spec['units'],
                numerical_work=raw['construction'],total_s=raw['total_s'],evidence_pointer='/raw_facts',
                unsupported_conclusions=['physical task acceptance','global nonlinear infeasibility'])
            if raw['status']!='computed':
                records.append(dict(name=name,available=False,reason=raw['failure_code'],construction=construction,raw_facts=raw,diagnostic=diagnostic));continue
            point.update(construction=construction)
            model=linear_model(inp,binding,p,point,raw,spec,scales)
            records.append(dict(point=model.operating_point,model=plain(model),construction=construction,
                derivative_check=raw['derivative_check'],raw_facts=raw,diagnostic=diagnostic,research_interpretations=[]))
        environment=dict(environment=engine.environment,dependency=engine.dependency,timings=engine.timings)
    model_binding=Binding(extension_id='model.sorosim_gvs',version='1.0.0',parameters=Payload(
        contract='family.sorosim_model',data=dict(basis=inp.policy.controller.parameters.data['recipe']['basis'])))
    applicability=assess_model_uses(inp.robot,inp.task,model_binding,['reachability','static_equilibrium','linearization','local_model_control'],registry=registry)
    records.insert(0,dict(configuration_only_input=boundary,configuration_only_identity=digest(boundary),
        applicability=plain(applicability),operating_point_rule=p.candidate_rule,requested_operating_points=len(names),
        analysis_binding=boundary['analysis_binding'],numerical_environment=environment))
    return AnalysisResult(kind='candidate_linearization',protocol=protocol_ref,bindings=[binding],records=records,
        evidence=[binding['configuration']],limitations=LIMITATIONS+['Conservative static tangent classification does not prove dynamic stability.'])


def design_context(base,minus,plus,request,p):
    """Require exact authorized candidate perturbations, then rebuild all physics."""
    from schemas.platform import SessionInput
    from tools.research.design import parameter_value,set_parameter
    from copy import deepcopy
    variable=request.variable
    if not (variable.startswith('segments.') and variable.rsplit('.',1)[-1] in ('length_m','young_pa')):
        raise ValueError('UNSUPPORTED_NONSMOOTH_OR_TOPOLOGY_DESIGN_DERIVATIVE')
    value=parameter_value(base['parameters'],variable)
    specs=[]
    for sign,candidate in [(-1,minus),(1,plus)]:
        expected=deepcopy(base['parameters']);set_parameter(expected,variable,value+sign*request.step)
        if candidate['parameters']!=expected:raise ValueError('DESIGN_PARTIAL_REQUIRES_EXACT_SINGLE_VARIABLE_PAIR')
        cfg=candidate['configuration'];original=base['configuration']
        if cfg['task']!=original['task'] or cfg['policy']['controller']!=original['policy']['controller']:
            raise ValueError('DESIGN_PARTIAL_TASK_OR_CONTROL_CHANGED')
        specs.append(prepare(SessionInput.model_validate(cfg),p)[0])
    return dict(minus_specification=specs[0],plus_specification=specs[1],design_step=request.step,
        design_variable=dict(version=request.version,path=variable,baseline=value,
            minus_candidate=plain(request.minus_candidate),plus_candidate=plain(request.plus_candidate),
            authorization='existing candidate verification and frozen family domains'))
