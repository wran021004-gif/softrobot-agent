"""Resolve compiler-owned mechanics once, without importing any engine."""
from tools.design_compiler import ensure_robot_ir
from tools.state_io import digest
from .contracts import Part, Tendon, ResolvedPhysics


def resolve_physics(design):
    ir = ensure_robot_ir(design)
    if ir.resolved_rod is None or ir.segments != 8 or ir.tendon_count != 4:
        raise ValueError('RESOLVED_PHYSICS_REQUIRES_SINGLE_SECTION_EIGHT_LINK_FOUR_TENDON_V2')
    rod, ds = ir.resolved_rod, ir.section.segment_length_m
    parts = []
    for i in range(ir.segments):
        diagonal = rod.inertia_diagonal_kg_m2[i]
        parts.append(Part(entity=f'segment_{i}', parent=f'segment_{i-1}' if i else 'fixed_base',
            origin_parent_m=(ds if i else 0., 0., 0.), length_m=ds, radius_m=ir.body_radius_m,
            mass_kg=rod.mass_kg[i], com_local_m=(ds/2, 0., 0.),
            inertia_com_local_kg_m2=tuple(tuple(diagonal[a] if a == b else 0. for b in range(3)) for a in range(3)),
            stiffness_nm_rad=(rod.stiffness_nm_rad[i],)*2,
            damping_nm_s_rad=(rod.damping_nm_s_rad[i],)*2, natural_rad=(rod.natural_y_rad[i], 0.)))
    tendons = tuple(Tendon(entity=f'tendon_{r.index}', actuator=f'tendon_{r.index}_actuator',
        offset_yz_m=r.offset_yz_m, kp_n_m=ir.mechanics.tendon_servo_kp_n_per_m,
        force_limit_n=ir.mechanics.tendon_force_limit_n,
        route_entities=('fixed_base', *(p.entity for p in parts))) for r in ir.tendon_routes)
    body = dict(source_ir_identity=digest(ir.model_dump(mode='json')), source_contracts=ir.physics_contracts,
        parts=tuple(parts), tendons=tendons, derivation=rod.derivation)
    provisional = ResolvedPhysics(identity='', **body)
    return provisional.model_copy(update={'identity': digest(provisional.model_dump(mode='json', exclude={'identity'}))})
