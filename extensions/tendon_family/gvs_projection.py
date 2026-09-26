"""Project serial bending cells through the resolved GVS representation."""

import numpy as np

from .compiler import rx
from .contracts import Design, ResolvedGVSBasis
from .gvs_basis import basis_matrix, resolve_basis, segment_slice


PROJECTOR_ID = 'backend_discrete_to_gvs_integrated_v2'
LEGACY_PROJECTOR_ID = 'backend_discrete_to_gvs_resolved_v1'


def cell_average_basis(resolved, local, left, right):
    """Exact average of the linear basis, split at structural knots."""
    left, right = max(0., left), min(1., right)
    edges = [left, *(k for k in local.knots if left < k < right), right]
    return sum((b-a) * basis_matrix(resolved, local, (a+b)/2)
               for a, b in zip(edges, edges[1:])) / (right-left)


def _resolved(design, basis=None):
    if isinstance(design, ResolvedGVSBasis):
        return design
    return resolve_basis(Design.model_validate(design), basis)


def _segments(physics, resolved, convention=PROJECTOR_ID):
    if convention not in (PROJECTOR_ID,LEGACY_PROJECTOR_ID):
        raise ValueError('UNKNOWN_GVS_MAPPING_CONVENTION: '+convention)
    result = []
    for local in resolved.segments:
        bodies = physics['entity_map'][local.segment]['bodies']
        parts = [physics['parts'][index] for index in bodies]
        length = local.length_m
        center = 0.0
        samples = []
        for part in parts:
            ds = part['length_m']
            center += ds / 2
            dofs = part['dofs']
            if len(dofs) != 2:
                raise ValueError('GVS_PROJECTOR_REQUIRES_BIAXIAL_CELL: ' + part['entity'])
            samples.append(dict(dofs=dofs, cell_length_m=ds,
                                normalized_center=center / length,
                                normalized_interval=((center-ds/2)/length, (center+ds/2)/length),
                                principal_to_segment=rx(part['section_axis_rad'])[1:, 1:]))
            center += ds / 2
        matrix = np.vstack([(basis_matrix(resolved,local,sample['normalized_center'])
                             if convention==LEGACY_PROJECTOR_ID else
                             cell_average_basis(resolved, local, *sample['normalized_interval']))
                            for sample in samples])
        if np.linalg.matrix_rank(matrix) < matrix.shape[1]:
            raise ValueError('GVS_PROJECTOR_BASIS_RANK_DEFICIENT: ' + local.segment)
        result.append((local, samples, matrix))
    return result


def description(physics, design, basis=None, *, convention=PROJECTOR_ID):
    resolved = _resolved(design, basis)
    segments = [dict(segment=local.segment, sample_count=len(samples),
                     condition_number=float(np.linalg.cond(matrix)))
                for local, samples, matrix in _segments(physics, resolved, convention)]
    return dict(id=convention, version='1.0.0' if convention==LEGACY_PROJECTOR_ID else '2.0.0',
                coordinate_order=resolved.coordinate_order,
                resolved_basis=resolved.model_dump(mode='json'), segments=segments,
                reconstruction=('historical whole-cell midpoint curvature; least squares at cell centers'
                    if convention==LEGACY_PROJECTOR_ID else
                    'segment mean curvature from principal joint angle / actual cell length; least squares on exactly integrated basis split at knots'))


def project(physics, design, qpos, qvel, basis=None, *, convention=PROJECTOR_ID):
    resolved = _resolved(design, basis)
    qpos = np.asarray(qpos, dtype=float)
    qvel = np.asarray(qvel, dtype=float)
    if qpos.shape != (len(physics['dofs']),) or qvel.shape != qpos.shape or not np.all(np.isfinite(np.r_[qpos, qvel])):
        raise ValueError('GVS_PROJECTOR_BACKEND_STATE_MISMATCH')
    q_gvs = np.zeros(resolved.dimension)
    qdot_gvs = np.zeros(resolved.dimension)
    residuals = []
    rate_residuals = []
    for local, samples, matrix in _segments(physics, resolved, convention):
        curvature = []
        rates = []
        for sample in samples:
            indices = sample['dofs']
            rotation = sample['principal_to_segment']
            ds = sample['cell_length_m']
            curvature.extend(rotation @ qpos[indices] / ds)
            rates.extend(rotation @ qvel[indices] / ds)
        curvature = np.asarray(curvature)
        rates = np.asarray(rates)
        sl = segment_slice(local)
        q_gvs[sl] = np.linalg.lstsq(matrix, curvature, rcond=None)[0]
        qdot_gvs[sl] = np.linalg.lstsq(matrix, rates, rcond=None)[0]
        residuals.extend(curvature - matrix @ q_gvs[sl])
        rate_residuals.extend(rates - matrix @ qdot_gvs[sl])
    diagnostics = description(physics, resolved, convention=convention)
    diagnostics.update(q_gvs=q_gvs.tolist(), qdot_gvs=qdot_gvs.tolist(),
                       projection_residual_max_rad_m=float(np.max(np.abs(residuals), initial=0.0)),
                       rate_projection_residual_max_rad_m_s=float(np.max(np.abs(rate_residuals), initial=0.0)))
    return diagnostics


def discretize(physics, design, q_gvs, qdot_gvs, basis=None, *, convention=PROJECTOR_ID):
    """Construct the serial-cell state represented by GVS coefficients."""
    resolved = _resolved(design, basis)
    q_gvs = np.asarray(q_gvs, dtype=float)
    qdot_gvs = np.asarray(qdot_gvs, dtype=float)
    if q_gvs.shape != (resolved.dimension,) or qdot_gvs.shape != q_gvs.shape:
        raise ValueError('GVS_DISCRETIZATION_STATE_DIMENSION_MISMATCH')
    mapping = discretization_jacobian(physics, resolved, convention=convention)
    return mapping @ q_gvs, mapping @ qdot_gvs


def discretization_jacobian(physics, design, basis=None, *, convention=PROJECTOR_ID):
    """Exact linear cell-angle Jacobian used by discretization and virtual work."""
    resolved = _resolved(design, basis)
    mapping = np.zeros((len(physics['dofs']), resolved.dimension))
    for local, samples, _ in _segments(physics, resolved, convention):
        for sample in samples:
            matrix = (basis_matrix(resolved,local,sample['normalized_center']) if convention==LEGACY_PROJECTOR_ID
                      else cell_average_basis(resolved, local, *sample['normalized_interval']))
            mapping[sample['dofs'], segment_slice(local)] = (
                sample['cell_length_m'] * sample['principal_to_segment'].T @ matrix
            )
    return mapping
