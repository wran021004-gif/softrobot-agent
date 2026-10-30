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
}


def catalog():
    return dict(primitives=deepcopy(PRIMITIVES),compositions=['identity','norm','minimum','maximum','directional_norm'],
        unavailable=dict(passive_constraint_nullspace='Requires actual passive fixed payout, verified taut active set and qualified equilibrium; active tension channels are not constraints.'),
        legacy_sources=dict(endpoint='bounded affine task kernel; no local mechanism substitution',
            braking='bounded affine task kernel',native_dynamics_v1='NativeModel.mechanics',
            fixed_input_structure_v1='same mechanics plus existing short fixed-input rollouts'))


def observe(mechanics, target):
    """Use only registered primitive/reduction pairs; preserve units and raw source."""
    from tools.research.contracts import MechanismTarget
    target=MechanismTarget.model_validate(target)
    meta=deepcopy(PRIMITIVES[target.quantity]);value=mechanics
    if meta['field']:
        for key in meta['field'].split('/'):value=value[key]
    elif target.quantity=='drive_directions':
        value=np.linalg.svd(mechanics['tip_acceleration_input_map_m_s2_n'],full_matrices=False)[0]
    else:
        length=np.asarray(mechanics['tendon_jacobian_m_rad']);tip=np.asarray(mechanics['tip_jacobian_m_rad'])
        residual=tip-tip@np.linalg.pinv(length)@length
        norms=np.linalg.norm(tip,axis=1)
        # A zero row carries no directional information; do not claim matching.
        if np.any(norms<=1e-14):value=None
        else:value=np.linalg.norm(residual,axis=1)/norms
    if value is None:
        return dict(status='not_applicable',reason='NONZERO_VELOCITY_REQUIRED' if target.quantity=='instantaneous_braking' else 'NONZERO_TIP_ROWS_REQUIRED',
            value=None,metadata=meta,target=target.model_dump())
    raw=np.asarray(value,dtype=float)
    nv=len(mechanics['coordinates']['dof_order']);nu=len(mechanics['coordinates']['tendon_order'])
    expected=tuple({'3':3,'nv':nv,'nu':nu,'min(3,nu)':min(3,nu),'2':2}[s] for s in meta['shape'])
    if raw.shape!=expected or not np.isfinite(raw).all():raise ValueError('MECHANISM_DIMENSION_OR_FINITE_VALUE_MISMATCH')
    if target.reduction=='norm':value=float(np.linalg.norm(raw))
    elif target.reduction=='minimum':value=float(np.min(raw))
    elif target.reduction=='maximum':value=float(np.max(raw))
    elif target.reduction=='directional_norm':value=float(np.linalg.norm(np.asarray(target.direction_world)@raw))
    else:value=raw.tolist()
    meta.update(actual_shape=list(raw.shape),result_shape=list(np.asarray(value).shape),
        dof_order=mechanics['coordinates']['dof_order'],tendon_order=mechanics['coordinates']['tendon_order'],
        state=dict(time_s=mechanics['time_s'],qpos_rad=mechanics['qpos_rad'],qvel_rad_s=mechanics['qvel_rad_s']),
        physical_inputs=dict(tensions_n=mechanics['actual_tensions_n'],bounds_n=mechanics['input_bounds_n']))
    return dict(status='computed',value=value,unit=meta['unit'],target=target.model_dump(),metadata=meta,
        source_pointer='/mechanics/'+meta['field'] if meta['field'] else '/mechanics')
