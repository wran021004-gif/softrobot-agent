"""Fixed-topology, source-relative transverse routing, owned by physical location."""
from copy import deepcopy
import math
import numpy as np


def locations(design):
    components = {c['id']: c for c in design['components']}
    roots = [c['id'] for c in components.values()
             if c['kind'] == 'flexible_segment' and c['connection']['part'] == 'fixed_base']
    if len(roots) != 1:
        raise ValueError('ROUTING_REQUIRES_ONE_SERIAL_ROOT_SEGMENT')

    def owner(part, seen=()):
        if part == 'fixed_base': return roots[0]
        if part in seen: raise ValueError('ROUTING_CONNECTION_CYCLE')
        c = components[part]
        return part if c['kind'] == 'flexible_segment' else owner(c['connection']['part'], (*seen, part))

    result = []
    # Each named hole is one physical location, even if several routes share it.
    for c in components.values():
        for hole, point in c.get('guide_holes', {}).items():
            result.append(dict(path=f"components/{c['id']}/guide_holes/{hole}",
                owner=owner(c['id']), point=point, rigid=c['id']))
    for t in design['tendons']:
        for i, p in enumerate(t['points']):
            if p.get('hole'): continue
            a = p['attachment']; part = a['part']
            result.append(dict(path=f"tendons/{t['id']}/points/{i}/attachment/position_m",
                owner=owner(part), point=a['position_m'],
                rigid=part if part != 'fixed_base' and components[part]['kind'] != 'flexible_segment' else None))
    return result


def envelope(design, component):
    """Necessary open bounds from real rigid envelopes and hole separation.

    No artificial backbone containment: this model permits exterior routing.
    Compiler span/topology checks remain coupled constraints on the whole edit.
    """
    parts = {c['id']: c for c in design['components']}; lo, hi = 0., math.inf
    for row in locations(design):
        if row['owner'] != component or not row['rigid']: continue
        c = parts[row['rigid']]; radius = c.get('hole_radius_m', 0.) if '/guide_holes/' in row['path'] else 0.
        for x, h in zip(row['point'][1:], c['envelope_halfsize_m'][1:]):
            if x: hi = min(hi, (h-radius)/abs(x))
        if c.get('guide_holes'):
            points = list(c['guide_holes'].values())
            for i, a in enumerate(points):
                for b in points[i+1:]:
                    distance = np.linalg.norm(np.array(a[1:])-b[1:])
                    if not distance: raise ValueError('COINCIDENT_SOURCE_GUIDE_HOLES')
                    lo = max(lo, 2*c['hole_radius_m']/distance)
    return dict(exclusive_minimum=float(lo), exclusive_maximum=float(hi) if math.isfinite(hi) else None,
        reason='Positive scale; rigid envelope clearance and strict hole separation; full compiler checks still required')


def transform(data, source, scales):
    from .candidate import locate
    for component, scale in scales.items():
        bounds = envelope(source, component)
        if not math.isfinite(scale) or scale <= bounds['exclusive_minimum'] or (
                bounds['exclusive_maximum'] is not None and scale >= bounds['exclusive_maximum']):
            raise ValueError('ROUTING_GEOMETRY_BOUND: '+component)
    for row in locations(source):
        if row['owner'] not in scales: continue
        obj, key = locate(data, row['path'])
        value = row['point']; scale = scales[row['owner']]
        obj[int(key) if isinstance(obj, list) else key] = [value[0], value[1]*scale, value[2]*scale]


def normalize(candidate, historical):
    """Verify actual uniform offsets, never trust metadata as compatibility proof."""
    from .candidate import read_parameter, locate
    ratios = {}
    for row in locations(historical):
        a = row['point']; b = read_parameter(candidate, row['path'])
        if a[0] != b[0]: raise ValueError('ROUTING_LONGITUDINAL_OFFSET_CHANGED')
        for old, new in zip(a[1:], b[1:]):
            if old: ratios.setdefault(row['owner'], []).append(new/old)
            elif new: raise ValueError('ROUTING_ANGULAR_LAYOUT_CHANGED')
    scales = {}
    for component, values in ratios.items():
        if not np.allclose(values, values[0], rtol=1e-10, atol=1e-12):
            raise ValueError('ROUTING_UNIFORM_SEGMENT_SCALE_REQUIRED')
        scales[component] = values[0]
    # Validate the scale and geometry, then restore only routing for comparison.
    probe = deepcopy(historical); transform(probe, historical, scales)
    for row in locations(historical):
        obj, key = locate(candidate, row['path'])
        obj[int(key) if isinstance(obj, list) else key] = deepcopy(row['point'])
    return scales


def expand_routing(data, space, changes):
    from .design_decisions import expand_segment
    subset = space.model_copy(update={'semantic_decisions': {
        p: d for p, d in space.semantic_decisions.items() if d.operation != 'routing_radius_scale'}})
    previous = deepcopy(data.get('metadata', {}).get('design_decisions', {}).get('selections', {}))
    expand_segment(data, subset, changes)
    scales, selected = {}, {}
    for path, decision in space.semantic_decisions.items():
        if decision.operation != 'routing_radius_scale': continue
        value = changes.get(path, previous.get(path, decision.baseline_value))
        for component in decision.components:
            if component in scales: raise ValueError('OVERLAPPING_ROUTING_OWNER')
            scales[component] = value
        selected[path] = value
    if selected:
        transform(data, space.semantic_source.model_dump(mode='json'), scales)
        data.setdefault('metadata', {}).setdefault('design_decisions', {}).setdefault('selections', {}).update(selected)
