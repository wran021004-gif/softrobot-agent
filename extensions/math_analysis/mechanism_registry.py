"""Registered observations of NativeModel.mechanics; no engine or expression evaluator.

Tendon Jacobians always describe geometry. Active ideal-tension channels are
forces, never fixed-payout constraints. Passive observations require the actual
fixed-payout assembly, qualified equilibrium and unilateral active set.
"""
from copy import deepcopy
import numpy as np


def _primitive(field, unit, shape, frame, dependencies, meaning):
    return dict(field=field,unit=unit,shape=shape,frame=frame,
        parameter_dependencies=dependencies.split(),meaning=meaning,
        source='extensions.tendon_family.mujoco_analysis.NativeModel.mechanics',
        state_requirements='Finite contact-free unconstrained named hinges; exact declared qpos/qvel and legal absolute tensions.',
        model='MuJoCo native ideal active tension',validity='instantaneous local numerical observation')


PRIMITIVES = {
    'tip_jacobian': _primitive('tip_jacobian_m_rad','m/rad',['3','nv'],'world / named hinges',
        'geometry routing','Tip velocity = J qvel; geometric map, not task feasibility.'),
    'tendon_jacobian': _primitive('tendon_jacobian_m_rad','m/rad',['ntendon','nv'],'ordered tendon lengths / named hinges',
        'geometry routing','Length rates = J_length qvel. Active channels do not constrain length rates to zero.'),
    'input_force_map': _primitive('input_force_map_nm_n','N*m/N',['nv','nu'],'named hinges / ordered absolute tensions',
        'geometry routing','Active generalized force = map times nonnegative absolute tension; native sign already resolved.'),
    'mass_matrix': _primitive('mass_matrix_kg_m2','kg*m^2',['nv','nv'],'named hinges',
        'geometry density','Native articulated inertia; independent of ideal tendon force and stiffness at fixed pose.'),
    'tip_acceleration_input_map': _primitive('tip_acceleration_input_map_m_s2_n','m/s^2/N',['3','nu'],'world / ordered absolute tensions',
        'geometry routing density','Local derivative of tip acceleration with respect to active absolute tensions.'),
    'drive_singular_values': _primitive('function_metrics/drive_singular_values_m_s2_n','m/s^2/N',['min(3,nu)'],'world / ordered absolute tensions',
        'geometry routing density','Singular values of signed local input increments; no bounded nonnegative task witness.'),
    'drive_directions': _primitive(None,'1',['3','min(3,nu)'],'world',
        'geometry routing density','Left singular vectors; sign and repeated-singular-value basis are ambiguous.'),
    'instantaneous_braking': _primitive('function_metrics/instantaneous_speed_derivative_range_m_s2','m/s^2',['2'],'along current world velocity',
        'geometry routing density stiffness damping input_bounds','Minimum/maximum instantaneous speed rate over actual tension box; requires nonzero velocity.'),
    'tendon_row_projection': _primitive(None,'1',['3'],'named hinge row space',
        'geometry routing','Relative residual of each tip Jacobian row projected onto tendon geometric row space; not a passive constraint nullspace.'),
    'mass_balance_residual': _primitive('mass_balance_residual_inf_nm','N*m',[],'named hinges',
        'geometry routing density stiffness damping','Native force balance residual; numerical consistency only.'),
    'directional_drive': _primitive(None,'m/s^2/N',['nu'],'specified unit world direction / ordered tensions',
        'geometry routing density','Signed directional acceleration coefficients; not independent signed physical inputs.'),
    'directional_acceleration_bounds': _primitive(None,'m/s^2',['2'],'specified unit world direction',
        'geometry routing density stiffness damping input_bounds','Exact local affine minimum/maximum over the legal absolute-tension box, including current drift; no finite-horizon claim.'),
    'input_force_directions': _primitive(None,'1',['nv','nu'],'normalized named hinge force columns',
        'geometry routing','Active tendon generalized-force directions; zero channels are undefined, never fixed-length constraints.'),
    'directional_tendon_row_residual': _primitive(None,'1',[],'named hinge geometric row space',
        'geometry routing','Relative residual of the selected tip-motion row in tendon geometric row space; no passive active-set inference.'),
    'motion_decoupling': _primitive(None,'1',[],'specified world direction / named hinges',
        'geometry','Kinematic fraction of selected tip motion after projecting out orthogonal tip rows; no bounded-tension or dynamic feasibility.'),
    'total_mass': _primitive(None,'kg',[],'all native bodies',
        'geometry density','Sum of native body masses, including unchanged rigid assembly parts; no task-capability interpretation.'),
    'body_inertia_trace': _primitive(None,'kg*m^2',[],'sum of body principal inertia traces',
        'geometry density','Sum of body-local principal inertia traces, not articulated inertia about one world origin.'),
    'joint_stiffness': _primitive('components/joint_stiffness_nm_rad','N*m/rad',['nv'],'named hinges',
        'geometry stiffness','Compiled native hinge stiffness; not static compliance or task performance.'),
    'joint_damping': _primitive('components/damping_nm_s_rad','N*m*s/rad',['nv'],'named hinges',
        'geometry damping','Compiled native hinge damping; not a closed-loop damping or stability certificate.'),
}


LEGACY_ACTIVE_MECHANISMS=tuple(PRIMITIVES)
CONSTRAINED = {
    'constraint_length_jacobian':('m/rad',['ntendon','nv'],'Actual length-rate Jacobian; geometry alone does not identify active unilateral constraints.','ordered tendon lengths / named hinges'),
    'constraint_active_set':('1',['ntendon'],'Length-bound activity at the declared tolerance, including zero-multiplier boundaries.','ordered tendons'),
    'constraint_multiplier':('N',['ntendon'],'Nonnegative NNLS tension fit; physical eligibility also requires all equilibrium qualification checks.','ordered tendons'),
    'slack_margin':('m',['ntendon'],'Payout minus actual length; negative values expose a constraint violation.','ordered tendons'),
    'constrained_motion_subspace':('1',['nv','free'],'Orthonormal basis of the positive-multiplier tangent nullspace; basis is not unique and boundary inequalities are separate.','named hinges / tangent coordinates'),
    'tangent_stiffness':('N*m/rad',['free','free'],'Z.T H_Lagrangian Z, including loaded geometric stiffness; not compiled joint stiffness.','tangent coordinates'),
    'tangent_compliance':('m/N',['3','3'],'J_point Z (Z.T H_Lagrangian Z)^-1 Z.T J_point.T at the qualified smooth loaded equilibrium.','world point displacement / world point force'),
    're_equilibrated_position_response':('m',['3'],'Position under selected load minus the separately re-equilibrated unloaded position of the same assembly and station.','world'),
    'constraint_tip_row_residual':('1',['2'],'Legacy X/Y tip-row coverage by positive constraints only.','world X/Y / named hinges'),
    'directional_material_response':('m/N',['2','3'],'Signed local force-increment QP responses, preserving unilateral boundary inequalities.','world'),
    'constraint_output_row_residual':('1',['projection'],'Declared output row coverage by positive constraints only; not loaded compliance or boundary-cone feasibility.','declared world output rows / named hinges'),
    'constraint_payout':('m',['ntendon'],'Frozen assembly payout, unchanged across all load cases.','ordered tendons'),
    'constraint_length_residual':('m',['ntendon'],'g=actual length-payout <= 0; positive entries are violations.','ordered tendons'),
    'constraint_tension_margin':('N',['ntendon'],'Declared tendon capacity minus fitted multiplier; this diagnostic is not a task acceptance certificate.','ordered tendons'),
    'constraint_kkt_residual':('N*m',[],'Stationarity infinity residual only; primal, complementarity and capacity checks remain separately reported.','named hinge stationarity'),
    'constraint_boundary_set':('1',['ntendon'],'Active length rows without positive multipliers; impose one-sided local inequalities.','ordered tendons'),
    'constraint_slack_set':('1',['ntendon'],'Inactive length rows; they impose no local motion equality.','ordered tendons'),
    'constraint_feasible_equalities':('m/rad',['positive','nv'],'J_positive dq=0 at the qualified equilibrium.','ordered positive constraints / named hinges'),
    'constraint_feasible_inequalities':('m/rad',['boundary','nv'],'J_boundary dq<=0 at the qualified equilibrium; never replace by a bilateral nullspace.','ordered boundary constraints / named hinges')}
COMMON_GEOMETRY=('tip_jacobian','material_point_jacobian','tendon_jacobian','joint_stiffness','joint_damping','all_tendon_output_row_residual')
for name,(unit,shape,meaning,frame) in CONSTRAINED.items():
    PRIMITIVES[name]=dict(field=name,unit=unit,shape=shape,frame=frame,
        parameter_dependencies=['geometry','routing','stiffness','payout','external_load'],
        source='extensions.tendon_family.passive_equilibrium.mechanics',model='native hard unilateral equilibrium',
        validity='Actual load and material-point binding; smooth tangent quantities require qualified equilibrium, LICQ and strict complementarity.',
        meaning=meaning)
PRIMITIVES['directional_material_response'].update(
    validity='Qualified equilibrium; positive rows are equalities and zero-multiplier active rows are inequalities. Two local +/-0.001 N QPs; not an ordinary gradient at a switching boundary.',
    meaning='Two signed material-point response vectors per newton along the declared world force direction; finite-load nonlinear response remains unmeasured.')

PRIMITIVES['material_point_jacobian']=_primitive('material_point_jacobian_m_rad','m/rad',['3','nv'],'world / named hinges',
    'geometry','Velocity of the declared material station = J_point qvel; body attachment is resolved from the actual mesh.')
PRIMITIVES['all_tendon_output_row_residual']=_primitive(None,'1',['projection'],'declared world output rows / named hinges',
    'geometry routing','Geometric coverage by ALL tendon routes, including slack routes; never an effective unilateral constraint space.')
for name in ('constraint_tip_row_residual','constraint_output_row_residual'):
    PRIMITIVES[name].update(field=None,source='extensions.tendon_family.passive_inverse.row_match',
        meaning=('Legacy world-X/Y tip row coverage by positive-multiplier constraints; not general 3D decoupling.' if name=='constraint_tip_row_residual' else
            'Coverage of explicitly projected tip rows by actual positive-multiplier constraints. Boundary inequalities remain in the feasible cone; loaded compliance is separate.'))
for name,field in dict(constraint_payout='components/constraint_payout_m',constraint_length_residual='equilibrium/equilibrium/length_residual_m',
        constraint_tension_margin='constraint_tension_margin_n',constraint_kkt_residual='constraint_state/stationarity_inf_nm',
        constraint_boundary_set='constraint_boundary_set',constraint_slack_set='constraint_slack_set',
        constraint_feasible_equalities='feasible_cone/equalities',constraint_feasible_inequalities='feasible_cone/inequalities').items():
    PRIMITIVES[name]['field']=field

ALIASES={'material_point_force_response':'tangent_compliance'}
PRIMITIVES['material_point_force_response']={**deepcopy(PRIMITIVES['tangent_compliance']),
    'alias_of':'tangent_compliance','meaning':'Historical name for the same J_point C J_point.T matrix; no independent experiment.'}
CONSTRAINED['material_point_force_response']=CONSTRAINED['tangent_compliance']
for name,meta in PRIMITIVES.items():
    meta.update(physical_modes=['passive_unilateral_equilibrium'] if name in CONSTRAINED else
        ['active_ideal_tension','passive_unilateral_equilibrium'] if name in COMMON_GEOMETRY else ['active_ideal_tension'],
        operations=['inspect','compare'] if name in ('drive_directions','constraint_active_set','constraint_boundary_set','constraint_slack_set',
            'constrained_motion_subspace','directional_material_response') else ['inspect','differentiate','optimize','compare'],
        main_visible=name not in (*ALIASES,'constraint_tip_row_residual'))
    meta['world_projection']=name in ('tip_jacobian','material_point_jacobian','tip_acceleration_input_map',
        'tangent_compliance','material_point_force_response','re_equilibrated_position_response')
    meta['state_requirements']=meta.get('state_requirements','Frozen fixed-payout assembly and load; qualified equilibrium for constrained response, LICQ and strict complementarity for smooth tangent matrices.')
    meta['requires_qualified_equilibrium']=name in ('constraint_feasible_equalities','constraint_feasible_inequalities')
    if len(meta['operations'])==2:meta['unavailable_operation_reason']='Discrete active-set, basis/sign ambiguity or one-sided cone response does not define an ordinary structural gradient.'


PRIMITIVES['finite_time_task_violation']=dict(field='signed_task_gap',unit='1',shape=[],frame='all frozen load cases and windows',
    physical_modes=['passive_unilateral_equilibrium'],operations=['inspect','differentiate','optimize','compare'],
    main_visible=False,world_projection=False,parameter_dependencies=['geometry','routing','stiffness','payout','damping'],
    requires_qualified_equilibrium=False,state_requirements='Frozen dynamic initial state, loading protocol and complete sampling grid.',
    source='extensions.reference.passive_response.task_metrics',model='MuJoCo fixed payout soft limits',
    validity='Every frozen constraint must have valid measurements and a legal normalization scale for a scalar objective.',
    meaning='Maximum normalized signed violation over every required load and constraint; independent acceptance remains unmeasured.')

for meta in PRIMITIVES.values():
    if 'differentiate' in meta['operations']:meta['operations'].append('interact')


def mechanism_ids(mode, operation=None):
    return [k for k,v in PRIMITIVES.items() if v['main_visible'] and mode in v['physical_modes'] and
        (operation is None or operation in v['operations'])]


def output_rows(target):
    """Explicit world direction or orthonormal output subspace, never inferred."""
    return np.asarray(target.projection_world if target.projection_world is not None else [target.direction_world])


def validate_projection(rows):
    matrix=np.asarray(rows,dtype=float)
    if matrix.ndim!=2 or matrix.shape[1]!=3 or not 1<=len(matrix)<=3 or not np.allclose(matrix@matrix.T,np.eye(len(matrix)),atol=1e-8,rtol=0):
        raise ValueError('ORTHONORMAL_WORLD_PROJECTION_ROWS_REQUIRED')


def catalog():
    return dict(primitives=deepcopy(PRIMITIVES),compositions=['identity','norm','minimum','maximum','directional_norm','generalized_projection','direction_cosine'],
        unavailable=dict(hybrid_or_contact='Active/passive mixtures and contact sensitivities are not implemented.',
            dynamic_modes='No registered native eigenmode/frequency-response backend; PHS modal_target/matching remain specialized prototypes.',
            energy_dissipation='Compiled stiffness/damping are exposed; no integrated energy/dissipation mechanism backend.'),
        legacy_sources=dict(endpoint='bounded affine task kernel; no local mechanism substitution',
            braking='bounded affine task kernel',native_dynamics_v1='NativeModel.mechanics',
            fixed_input_structure_v1='same mechanics plus existing short fixed-input rollouts'))


def derived(mechanics, target):
    """Small compositions of existing native exports, never a second physics kernel."""
    name=target.quantity
    if name in ('constraint_tip_row_residual','constraint_output_row_residual','all_tendon_output_row_residual'):
        from extensions.tendon_family.passive_inverse import row_match
        J=np.asarray(mechanics['tendon_jacobian_m_rad'])
        if name!='all_tendon_output_row_residual':
            if not mechanics['constraint_state']['qualified']:return None
            J=J[np.asarray(mechanics['equilibrium']['equilibrium']['positive'],dtype=bool)]
        projection=np.eye(3)[:2] if name=='constraint_tip_row_residual' else output_rows(target)
        rows=projection@np.asarray(mechanics['tip_jacobian_m_rad'])
        if np.any(np.linalg.norm(rows,axis=1)<=1e-14):return None
        return row_match(J,rows)['row_residuals']
    if name=='drive_directions':return np.linalg.svd(mechanics['tip_acceleration_input_map_m_s2_n'],full_matrices=False)[0]
    if name in ('total_mass','body_inertia_trace'):
        return np.sum(mechanics['components']['body_mass_kg' if name=='total_mass' else 'body_inertia_kg_m2'])
    if name=='input_force_directions':
        matrix=np.asarray(mechanics['input_force_map_nm_n']);norms=np.linalg.norm(matrix,axis=0)
        return matrix/norms if np.all(norms>1e-14) else None
    if name in ('directional_drive','directional_acceleration_bounds'):
        direction=np.asarray(target.direction_world);coefficients=direction@np.asarray(mechanics['tip_acceleration_input_map_m_s2_n'])
        if name=='directional_drive':return coefficients
        bounds=np.asarray(mechanics['input_bounds_n']);u=np.asarray(mechanics['actual_tensions_n'])
        changes=coefficients[:,None]*(bounds-u[:,None]);current=direction@np.asarray(mechanics['tip_acceleration_m_s2'])
        return current+np.array([np.min(changes,axis=1).sum(),np.max(changes,axis=1).sum()])
    tip=np.asarray(mechanics['tip_jacobian_m_rad']);length=np.asarray(mechanics['tendon_jacobian_m_rad'])
    if name=='tendon_row_projection':
        rows=tip;norms=np.linalg.norm(rows,axis=1)
        return np.linalg.norm(rows-rows@np.linalg.pinv(length)@length,axis=1)/norms if np.all(norms>1e-14) else None
    row=np.asarray(target.direction_world)@tip;norm=float(np.linalg.norm(row))
    if norm<=1e-14:return None
    if name=='directional_tendon_row_residual':return np.linalg.norm(row-row@np.linalg.pinv(length)@length)/norm
    orthogonal=(np.eye(3)-np.outer(target.direction_world,target.direction_world))@tip
    return np.linalg.norm(row-row@np.linalg.pinv(orthogonal)@orthogonal)/norm


def observe(mechanics, target):
    """Use only registered primitive/reduction pairs; preserve units and raw source."""
    from tools.research.contracts import PhysicalMechanismTarget
    target=PhysicalMechanismTarget.model_validate(target.model_dump() if hasattr(target,'model_dump') else target)
    meta=deepcopy(PRIMITIVES[target.quantity]);value=mechanics
    passive=mechanics.get('physical_problem')=='passive_unilateral_equilibrium'
    mode='passive_unilateral_equilibrium' if passive else 'active_ideal_tension'
    if mode not in meta['physical_modes']:
        return dict(status='not_applicable',reason='MECHANISM_PHYSICAL_MODE_MISMATCH',value=None,metadata=meta)
    if meta['requires_qualified_equilibrium'] and not mechanics['constraint_state']['qualified']:
        return dict(status='not_applicable',reason='QUALIFIED_EQUILIBRIUM_REQUIRED',value=None,metadata=meta)
    if meta['field']:
        for key in meta['field'].split('/'):value=value[key]
    else:value=derived(mechanics,target)
    if value is None:
        return dict(status='not_applicable',reason='QUALIFIED_REGULAR_EQUILIBRIUM_REQUIRED' if passive else 'NONZERO_VELOCITY_REQUIRED' if target.quantity=='instantaneous_braking' else 'NONZERO_GEOMETRIC_ROW_OR_FORCE_CHANNEL_REQUIRED',
            value=None,metadata=meta,target=target.model_dump())
    raw=np.asarray(value,dtype=float)
    nv=len(mechanics['coordinates']['dof_order']);nu=len(mechanics['coordinates']['tendon_order'])
    counts=mechanics.get('constraint_state',{})
    free=nv-mechanics.get('equilibrium',{}).get('equilibrium',{}).get('positive_rank',counts.get('positive_count',0))
    dimensions={'3':3,'nv':nv,'nu':nu,'ntendon':nu,'min(3,nu)':min(3,nu),'2':2,'free':free,
        'positive':counts.get('positive_count',0),'boundary':counts.get('boundary_count',0),
        'projection':len(output_rows(target)) if target.quantity in ('constraint_output_row_residual','all_tendon_output_row_residual') else 0}
    expected=tuple(dimensions[s] for s in meta['shape'])
    if passive and not raw.size and 0 in expected:raw=raw.reshape(expected)
    if raw.shape!=expected or not np.isfinite(raw).all():raise ValueError('MECHANISM_DIMENSION_OR_FINITE_VALUE_MISMATCH')
    source_shape=list(raw.shape)
    if not raw.size and target.reduction in ('minimum','maximum'):
        return dict(status='not_applicable',reason='EMPTY_TANGENT_SPACE_HAS_NO_EXTREMUM',value=None,metadata=meta,target=target.model_dump())
    if target.tendon_channel is not None:
        if target.tendon_channel>=nu:raise ValueError('TENDON_CHANNEL_OUTSIDE_CURRENT_MODEL')
        raw=raw[:,target.tendon_channel] if raw.ndim==2 else raw[target.tendon_channel]
    if target.reduction=='norm':value=float(np.linalg.norm(raw))
    elif target.reduction=='minimum':value=float(np.min(raw))
    elif target.reduction=='maximum':value=float(np.max(raw))
    elif target.reduction=='directional_norm':value=float(np.linalg.norm(np.asarray(target.direction_world)@raw))
    elif target.reduction=='directional_component':value=float(np.asarray(target.direction_world)@raw)
    elif target.reduction in ('generalized_projection','direction_cosine'):
        if len(target.direction_generalized)!=nv:raise ValueError('GENERALIZED_DIRECTION_MUST_MATCH_NAMED_HINGES')
        value=float(np.asarray(target.direction_generalized)@raw)
        if target.reduction=='direction_cosine':
            norm=float(np.linalg.norm(raw))
            if norm<=1e-14:return dict(status='not_applicable',reason='ZERO_FORCE_CHANNEL_HAS_NO_DIRECTION',value=None,metadata=meta,target=target.model_dump())
            value/=norm;meta['unit']='1'
    else:value=raw.tolist()
    meta.update(actual_shape=source_shape,result_shape=list(np.asarray(value).shape),
        dof_order=mechanics['coordinates']['dof_order'],tendon_order=mechanics['coordinates']['tendon_order'],
        state=dict(time_s=mechanics['time_s'],qpos_rad=mechanics['qpos_rad'],qvel_rad_s=mechanics['qvel_rad_s']),
        physical_inputs=dict(tensions_n=mechanics['actual_tensions_n'],bounds_n=mechanics['input_bounds_n']))
    if passive:meta.update(model='native unilateral fixed-payout assembly',
        state_requirements='Finite named-hinge geometry; equilibrium qualification governs constrained tangent and re-equilibrated response.',
        constraint_state=mechanics['constraint_state'],point_binding=mechanics['point_binding'])
    if passive and meta['source'].endswith('NativeModel.mechanics'):meta['source']='extensions.tendon_family.passive_equilibrium.mechanics'
    if not passive and mechanics.get('point_binding'):meta['point_binding']=mechanics['point_binding']
    return dict(status='computed',value=value,unit=meta['unit'],target=target.model_dump(),metadata=meta,
        source_pointer='/mechanics/'+meta['field'] if meta['field'] else '/mechanics')
