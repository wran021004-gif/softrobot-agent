"""Project compiled serial-cell bending state into the frozen first-order GVS basis."""
import numpy as np

from .compiler import rx
from .contracts import Design
from .gvs import coordinate_order


PROJECTOR_ID='backend_discrete_to_gvs_first_order_v1'


def _segments(physics, design):
    coordinates=(list(design) if isinstance(design,(list,tuple)) and all(isinstance(item,str) for item in design)
        else coordinate_order(Design.model_validate(design)))
    names=[]
    for coordinate in coordinates:
        name=coordinate.split('.',1)[0]
        if name not in names: names.append(name)
    result=[]
    for name in names:
        bodies=physics['entity_map'][name]['bodies']
        parts=[physics['parts'][index] for index in bodies]
        if len(parts)<2: raise ValueError('GVS_PROJECTOR_REQUIRES_TWO_CELLS_PER_SEGMENT: '+name)
        length=sum(part['length_m'] for part in parts)
        center=0.; samples=[]
        for part in parts:
            ds=part['length_m']; center+=ds/2
            dofs=part['dofs']
            if len(dofs)!=2: raise ValueError('GVS_PROJECTOR_REQUIRES_BIAXIAL_CELL: '+part['entity'])
            samples.append(dict(dofs=dofs,cell_length_m=ds,normalized_center=center/length,
                principal_to_segment=rx(part['section_axis_rad'])[1:,1:]))
            center+=ds/2
        basis=np.array([[1.,2*sample['normalized_center']-1.] for sample in samples])
        if np.linalg.matrix_rank(basis)<2: raise ValueError('GVS_PROJECTOR_BASIS_RANK_DEFICIENT: '+name)
        result.append((name,samples,basis))
    return result


def description(physics,design):
    coordinates=(list(design) if isinstance(design,(list,tuple)) and all(isinstance(item,str) for item in design)
        else coordinate_order(Design.model_validate(design)))
    segments=[]
    for name,samples,basis in _segments(physics,design):
        segments.append(dict(segment=name,sample_count=len(samples),condition_number=float(np.linalg.cond(basis))))
    return dict(id=PROJECTOR_ID,version='1.0.0',coordinate_order=coordinates,segments=segments,
        reconstruction='segment_curvature = principal_axis_rotation @ joint_angle / cell_length; deterministic least squares on [1, 2*s/L-1]')


def project(physics,design,qpos,qvel):
    qpos=np.asarray(qpos,dtype=float);qvel=np.asarray(qvel,dtype=float)
    if qpos.shape!=(len(physics['dofs']),) or qvel.shape!=qpos.shape or not np.all(np.isfinite(np.r_[qpos,qvel])):
        raise ValueError('GVS_PROJECTOR_BACKEND_STATE_MISMATCH')
    q_gvs=[];qd_gvs=[];residuals=[];rate_residuals=[]
    diagnostics=description(physics,design)
    for _,samples,basis in _segments(physics,design):
        curvature=[];rates=[]
        for sample in samples:
            indices=sample['dofs']; rotation=sample['principal_to_segment']; ds=sample['cell_length_m']
            curvature.append(rotation@qpos[indices]/ds)
            rates.append(rotation@qvel[indices]/ds)
        curvature=np.asarray(curvature);rates=np.asarray(rates)
        cy=np.linalg.lstsq(basis,curvature[:,0],rcond=None)[0]
        cz=np.linalg.lstsq(basis,curvature[:,1],rcond=None)[0]
        vy=np.linalg.lstsq(basis,rates[:,0],rcond=None)[0]
        vz=np.linalg.lstsq(basis,rates[:,1],rcond=None)[0]
        q_gvs.extend([cy[0],cy[1],cz[0],cz[1]])
        qd_gvs.extend([vy[0],vy[1],vz[0],vz[1]])
        residuals.extend((curvature-np.c_[basis@cy,basis@cz]).ravel())
        rate_residuals.extend((rates-np.c_[basis@vy,basis@vz]).ravel())
    diagnostics.update(q_gvs=np.asarray(q_gvs).tolist(),qdot_gvs=np.asarray(qd_gvs).tolist(),
        projection_residual_max_rad_m=float(np.max(np.abs(residuals),initial=0.)),
        rate_projection_residual_max_rad_m_s=float(np.max(np.abs(rate_residuals),initial=0.)))
    return diagnostics


def discretize(physics,design,q_gvs,qdot_gvs):
    """Construct the backend cell state represented by a GVS state (for validation/initialization)."""
    coordinates=coordinate_order(Design.model_validate(design));n=len(coordinates)
    q_gvs=np.asarray(q_gvs,dtype=float);qdot_gvs=np.asarray(qdot_gvs,dtype=float)
    if q_gvs.shape!=(n,) or qdot_gvs.shape!=(n,): raise ValueError('GVS_DISCRETIZATION_STATE_DIMENSION_MISMATCH')
    mapping=discretization_jacobian(physics,design)
    return mapping@q_gvs,mapping@qdot_gvs


def discretization_jacobian(physics,design):
    """Exact linear cell-angle Jacobian used by discretize and virtual work."""
    mapping=np.zeros((len(physics['dofs']),len(coordinate_order(Design.model_validate(design)))))
    for index,(_,samples,_) in enumerate(_segments(physics,design)):
        for sample in samples:
            phi=2*sample['normalized_center']-1.;ds=sample['cell_length_m']
            basis=np.array([[1.,phi,0.,0.],[0.,0.,1.,phi]])
            mapping[sample['dofs'],4*index:4*index+4]=ds*sample['principal_to_segment'].T@basis
    return mapping
