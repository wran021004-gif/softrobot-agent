"""Typed, source-relative physical decision expansion; no executable mappings."""
from copy import deepcopy
import numpy as np
from tools.state_io import digest

MATERIAL_FACTORS = {'baseline': 1., 'compliant': .9, 'stiff': 1.1}
ASSUMPTIONS = ('Numerical simulation scenarios, not validated commercial materials. '
    'Young modulus alone is multiplied; original density and bending viscosity are retained.')


def expand(data, space, changes):
    from .candidate import check_value
    if not space.semantic_decisions:
        return
    if space.semantic_source is None:
        raise ValueError('SEMANTIC_FROZEN_SOURCE_REQUIRED')
    source = space.semantic_source.model_dump(mode='json')
    before = {c['id']: c for c in source['components']}
    after = {c['id']: c for c in data['components']}
    selections = data.get('metadata', {}).get('design_decisions', {}).get('selections', {})
    selections = {key: changes.get(key, selections.get(key, decision.baseline_value))
        for key, decision in space.semantic_decisions.items()}
    groups = {}
    for key, decision in space.semantic_decisions.items():
        value = selections[key]
        check_value(key, value, space.parameters[key], {})
        for name in decision.components:
            original, target = before[name], after[name]
            if decision.operation == 'section_scale':
                target['sections'] = deepcopy(original['sections'])
                for station in target['sections']:
                    section = station['section']
                    if section['kind'] not in ('ellipse', 'rectangle'):
                        raise ValueError('SEMANTIC_SECTION_KIND_UNSUPPORTED')
                    section['parameters'] = {k: v * value for k, v in section['parameters'].items()}
            else:
                target['physics'] = deepcopy(original['physics'])
                if target['physics']['mode'] != 'material':
                    raise ValueError('MATERIAL_SCENARIO_REQUIRES_MATERIAL_INPUT')
                target['physics']['young_pa'] *= MATERIAL_FACTORS[value]
                groups[name] = deepcopy(target['physics'])
    data.setdefault('metadata', {})['design_decisions'] = dict(selections=selections,
        source_identity=digest(source), material_groups=groups, assumptions=ASSUMPTIONS,
        source='Frozen experiment semantic_source; original per-section material parameters')


def expand_segment(data, space, changes):
    """v2 disjoint groups: update only the quantity owned by each decision.

    Original v1 expansion stays available for frozen historical workflows.
    Scales are absolute against semantic_source, never compounded on a candidate.
    """
    from .candidate import check_value
    if not space.semantic_decisions:
        return
    if space.semantic_source is None:
        raise ValueError('SEMANTIC_FROZEN_SOURCE_REQUIRED')
    source = space.semantic_source.model_dump(mode='json')
    before = {c['id']: c for c in source['components']}
    after = {c['id']: c for c in data['components']}
    previous = data.get('metadata', {}).get('design_decisions', {}).get('selections', {})
    selections, owners, groups = {}, set(), {}
    for path, decision in space.semantic_decisions.items():
        value = changes.get(path, previous.get(path, decision.baseline_value))
        check_value(path, value, space.parameters[path], {})
        selections[path] = value
        for component in decision.components:
            owner = (component, decision.operation)
            if owner in owners:
                raise ValueError('OVERLAPPING_SEMANTIC_DECISION: '+component+'/'+decision.operation)
            owners.add(owner)
            original, target = before[component], after[component]
            if decision.operation == 'section_scale':
                if len(target['sections']) != len(original['sections']):
                    raise ValueError('SEMANTIC_SECTION_STATIONS_CHANGED')
                for old, station in zip(original['sections'], target['sections']):
                    if old['section']['kind'] not in ('ellipse', 'rectangle') or station['section']['kind'] != old['section']['kind']:
                        raise ValueError('SEMANTIC_SECTION_KIND_UNSUPPORTED')
                    station['section']['parameters'] = {k: v*value for k,v in old['section']['parameters'].items()}
            else:
                if target['physics']['mode'] != 'material' or original['physics']['mode'] != 'material':
                    raise ValueError('MATERIAL_SCENARIO_REQUIRES_MATERIAL_INPUT')
                # Preserve density, viscosity, and every unowned physical input.
                target['physics']['young_pa'] = original['physics']['young_pa']*MATERIAL_FACTORS[value]
                groups[component] = deepcopy(target['physics'])
    data.setdefault('metadata', {})['design_decisions'] = dict(selections=selections,
        source_identity=digest(source), material_groups=groups, assumptions=ASSUMPTIONS,
        source='Frozen experiment semantic_source; disjoint per-segment expansion v2')


def physical_effects(baseline, effective):
    """Actual physical rows, independently computed from effective design bytes."""
    original = {c['id']: c for c in baseline['components']}
    rows = []
    def add(path, a, b, unit, category):
        if a != b:
            rows.append(dict(path=path, baseline_value=a, effective_value=b,
                baseline_delta=b-a, unit=unit, category=category))
    for c in effective['components']:
        if c['kind'] != 'flexible_segment': continue
        old = original[c['id']]; prefix = 'components/' + c['id']
        add(prefix+'/length_m', old['length_m'], c['length_m'], 'm', 'length')
        for i, (a, b) in enumerate(zip(old['sections'], c['sections'])):
            for key, value in b['section']['parameters'].items():
                add(f'{prefix}/sections/{i}/section/parameters/{key}',
                    a['section']['parameters'][key], value, 'm', 'section')
        for key, unit in (('young_pa', 'Pa'), ('density_kg_m3', 'kg/m^3')):
            add(prefix+'/physics/'+key, old['physics'][key], c['physics'][key], unit, 'material')
    return rows


def physical_summary(design, discretization):
    from .compiler import resolve
    p = resolve(design, discretization)
    sections = []
    for c in design['components']:
        if c['kind'] != 'flexible_segment': continue
        parts = [r for r in p['parts'] if r['component'] == c['id']]
        sections.append(dict(component=c['id'], length_m=c['length_m'], material=c['physics'],
            mass_kg=sum(r['mass_kg'] for r in parts), cells=len(parts),
            area_range_m2=[min(r['section_properties']['area_m2'] for r in parts), max(r['section_properties']['area_m2'] for r in parts)],
            cell_inertia_diagonal_kg_m2=[np.diag(parts[i]['inertia_com_local_kg_m2']).tolist() for i in (0,-1)],
            cell_stiffness_nm_rad=[parts[i]['stiffness_nm_rad'] for i in (0,-1)],
            cell_damping_nm_s_rad=[parts[i]['damping_nm_s_rad'] for i in (0,-1)]))
    return dict(physics_identity=p['identity'], sections=sections,
        force_limits_n={t['entity']:t['force_limit_n'] for t in p['tendons']},
        assumptions=ASSUMPTIONS, applicability=p['applicability'])


def normalize_supported(candidate, historical):
    """v6 technical scope independent of experiment bounds/material options."""
    from .contracts import Design
    Design.model_validate(candidate)
    old = {c['id']:c for c in historical['components']}
    for c in candidate['components']:
        if c['kind'] != 'flexible_segment': continue
        original = old[c['id']]
        # Same stations, shape, orientation, aspect ratios; positive scale per section.
        ratios = []
        for a,b in zip(original['sections'],c['sections']):
            if set(a['section']['parameters']) != set(b['section']['parameters']):
                raise ValueError('GVS_REACH_SECTION_SHAPE_CHANGED')
            ratios.extend(b['section']['parameters'][k]/v for k,v in a['section']['parameters'].items())
        if not ratios or min(ratios)<=0 or not np.allclose(ratios,ratios[0],rtol=1e-10,atol=0):
            raise ValueError('GVS_REACH_UNIFORM_SECTION_SCALE_REQUIRED')
        for a,b in zip(original['sections'],c['sections']):
            b['section']['parameters'] = deepcopy(a['section']['parameters'])
        if c['physics']['mode'] != 'material': raise ValueError('GVS_REACH_MATERIAL_MODE_REQUIRED')
        c['physics'] = deepcopy(original['physics'])
        c['length_m'] = original['length_m']
    candidate.get('metadata',{}).pop('design_decisions',None)
