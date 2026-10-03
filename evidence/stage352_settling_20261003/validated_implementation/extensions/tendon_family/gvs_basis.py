"""Trusted, serializable bending bases shared by all GVS consumers."""

import numpy as np

from .contracts import (Design, GVSBasisSpecification, GVSSegmentBasis,
                        ResolvedGVSBasis, Reserved, Segment)
from .gvs_structure import structural_locations


def resolve_basis(design, specification=None):
    design = Design.model_validate(design)
    specification = GVSBasisSpecification.model_validate(specification or {})
    order = []
    segments = []
    components = {component.id: component for component in design.components}
    chain = []
    current = design.tip.part
    visited = set()
    while current != 'fixed_base':
        if current in visited:
            raise ValueError('GVS component graph contains a cycle')
        visited.add(current)
        component = components.get(current)
        if component is None:
            raise ValueError('GVS tip chain references unknown component: ' + current)
        if isinstance(component, Reserved):
            raise ValueError('GVS does not implement reserved topology: ' + component.kind)
        chain.append(component)
        current = component.connection.part
    if visited != set(components):
        raise ValueError('GVS requires one serial component chain')
    locations = structural_locations(design)
    for component in reversed(chain):
        if not isinstance(component, Segment):
            continue
        knots = ((0.0, 1.0) if specification.strategy == 'first_order'
                 else tuple(location.s for location in locations[component.id]))
        start = len(order)
        for axis in ('y', 'z'):
            for index in range(len(knots)):
                suffix = str(index) if specification.strategy == 'first_order' else 'node_' + str(index)
                order.append(f'{component.id}.kappa_{axis}_{suffix}')
        segments.append(GVSSegmentBasis(segment=component.id, start=start, length_m=component.length_m,
                                        knots=knots, locations=locations[component.id]))
    return ResolvedGVSBasis(specification=specification, coordinate_order=order,
                            segments=segments, dimension=len(order))


def segment_slice(segment):
    return slice(segment.start, segment.start + 2 * len(segment.knots))


def basis_matrix(resolved, segment, normalized_s):
    """Map local coefficients to [kappa_y, kappa_z] at normalized arc s."""
    u = float(normalized_s)
    if not 0.0 <= u <= 1.0:
        raise ValueError('GVS segment coordinate must be within [0, 1]')
    if resolved.specification.strategy == 'first_order':
        values = np.array([1.0, 2.0 * u - 1.0])
    else:
        knots = segment.knots
        values = np.zeros(len(knots))
        index = min(int(np.searchsorted(knots, u, side='right')) - 1, len(knots) - 2)
        index = max(index, 0)
        t = (u - knots[index]) / (knots[index + 1] - knots[index])
        values[index] = 1.0 - t
        values[index + 1] = t
    zeros = np.zeros_like(values)
    return np.array([np.r_[values, zeros], np.r_[zeros, values]])


def segment_basis(resolved, name):
    return next(segment for segment in resolved.segments if segment.segment == name)


def integration_intervals(segment, normalized_end, steps):
    """Midpoint samples partitioned at each represented structural knot."""
    boundaries = [0.0, *(knot for knot in segment.knots[1:-1]
                          if knot < normalized_end), normalized_end]
    for left, right in zip(boundaries, boundaries[1:]):
        count = max(1, int(np.ceil(steps * (right - left))))
        width = (right - left) / count
        for index in range(count):
            yield left + (index + .5) * width, width


def basis_quadrature(segment, count):
    """Gauss nodes and normalized weights on each knot interval."""
    nodes, weights = np.polynomial.legendre.leggauss(count)
    for left, right in zip(segment.knots, segment.knots[1:]):
        scale = (right - left) / 2
        for node, weight in zip(nodes, weights):
            yield left + (node + 1) * scale, weight * scale
