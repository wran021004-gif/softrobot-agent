"""Registered observations of NativeModel.mechanics; no engine or expression evaluator.

Tendon Jacobians always describe geometry. Active ideal-tension channels are
forces, never fixed-payout constraints. Passive active-set nullspaces require a
separate qualified passive model and are deliberately unavailable here.
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
    'tendon_jacobian': _primitive('tendon_jacobian_m_rad','m/rad',['nu','nv'],'ordered tendon lengths / named hinges',
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


def catalog():
    return dict(primitives=deepcopy(PRIMITIVES),compositions=['identity','norm','minimum','maximum','directional_norm','generalized_projection','direction_cosine'],
        unavailable=dict(passive_constraint_nullspace='Requires actual passive fixed payout, verified taut active set and qualified equilibrium; active tension channels are not constraints.'),
        legacy_sources=dict(endpoint='bounded affine task kernel; no local mechanism substitution',
            braking='bounded affine task kernel',native_dynamics_v1='NativeModel.mechanics',
            fixed_input_structure_v1='same mechanics plus existing short fixed-input rollouts'))


def derived(mechanics, target):
    """Small compositions of existing native exports, never a second physics kernel."""
    name=target.quantity
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
    from tools.research.contracts import MechanismTarget
    target=MechanismTarget.model_validate(target)
    meta=deepcopy(PRIMITIVES[target.quantity]);value=mechanics
    if meta['field']:
        for key in meta['field'].split('/'):value=value[key]
    else:value=derived(mechanics,target)
    if value is None:
        return dict(status='not_applicable',reason='NONZERO_VELOCITY_REQUIRED' if target.quantity=='instantaneous_braking' else 'NONZERO_GEOMETRIC_ROW_OR_FORCE_CHANNEL_REQUIRED',
            value=None,metadata=meta,target=target.model_dump())
    raw=np.asarray(value,dtype=float)
    nv=len(mechanics['coordinates']['dof_order']);nu=len(mechanics['coordinates']['tendon_order'])
    expected=tuple({'3':3,'nv':nv,'nu':nu,'min(3,nu)':min(3,nu),'2':2}[s] for s in meta['shape'])
    if raw.shape!=expected or not np.isfinite(raw).all():raise ValueError('MECHANISM_DIMENSION_OR_FINITE_VALUE_MISMATCH')
    source_shape=list(raw.shape)
    if target.tendon_channel is not None:
        if target.tendon_channel>=nu:raise ValueError('TENDON_CHANNEL_OUTSIDE_CURRENT_MODEL')
        raw=raw[:,target.tendon_channel] if raw.ndim==2 else raw[target.tendon_channel]
    if target.reduction=='norm':value=float(np.linalg.norm(raw))
    elif target.reduction=='minimum':value=float(np.min(raw))
    elif target.reduction=='maximum':value=float(np.max(raw))
    elif target.reduction=='directional_norm':value=float(np.linalg.norm(np.asarray(target.direction_world)@raw))
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
    return dict(status='computed',value=value,unit=meta['unit'],target=target.model_dump(),metadata=meta,
        source_pointer='/mechanics/'+meta['field'] if meta['field'] else '/mechanics')
