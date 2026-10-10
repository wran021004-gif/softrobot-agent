"""Exact source-geometry diagnostic map, not a replacement dynamics backend.

Runtime lengths enter all poses and tendon lengths. Topology, normalized
integration locations and routing are static. No candidate scalar is extracted
while tracing. Mechanics admission is checked separately against native GVS.
"""
import jax
jax.config.update('jax_enable_x64', True)
import jax.numpy as jnp
import numpy as np
from .contracts import Design
from .gvs import _topology
from .gvs_basis import resolve_basis, integration_intervals, basis_matrix, segment_slice
from .pcc import rigid_transform


def cell_pose(length, ky, kz):
    k2 = ky*ky + kz*kz
    k = jnp.sqrt(k2 + 1e-30)
    theta = k*length
    low = theta*theta < 1e-4
    a0 = length-k2*length**3/6+k2**2*length**5/120-k2**3*length**7/5040
    b0 = length**2/2-k2*length**4/24+k2**2*length**6/720-k2**3*length**8/40320
    c0 = length**3/6-k2*length**5/120+k2**2*length**7/5040-k2**3*length**9/362880
    a = jnp.where(low, a0, jnp.sin(theta)/k)
    b = jnp.where(low, b0, (1-jnp.cos(theta))/(k*k))
    c = jnp.where(low, c0, (theta-jnp.sin(theta))/(k**3))
    w = jnp.array([[0., -kz, ky], [kz, 0., 0.], [-ky, 0., 0.]])
    rotation = jnp.eye(3)+a*w+b*(w@w)
    position = (length*jnp.eye(3)+b*w+c*(w@w))[:, 0]
    return jnp.eye(4).at[:3, :3].set(rotation).at[:3, 3].set(position)


class RoutingMap:
    def __init__(self, design, basis, integration_steps=24):
        self.design, self.parts, self.chain, self.segments = _topology(Design.model_validate(design))
        self.basis = resolve_basis(self.design, basis)
        self.steps = integration_steps
        self.length_indices = {s.id: i for i, s in enumerate(self.segments)}
        self.locals = {s.segment: s for s in self.basis.segments}

    def quantities(self, q, proximal_length):
        lengths = jnp.stack([proximal_length, .27-proximal_length])
        bases, poses = {}, {}

        def base(part):
            if part not in bases:
                a = self.parts[part].connection
                bases[part] = pose(a.part, a.s) @ jnp.asarray(rigid_transform(a.position_m, a.quaternion_wxyz))
            return bases[part]

        def pose(part, s):
            key = (part, s)
            if key not in poses:
                if part == 'fixed_base':
                    result = jnp.eye(4)
                elif part not in self.locals:
                    result = base(part)
                else:
                    local = self.locals[part]
                    result = base(part)
                    if s > 0:
                        # Static NumPy operations only encode the declared basis.
                        samples = list(integration_intervals(local, s, self.steps))
                        matrices = jnp.asarray(np.stack([basis_matrix(self.basis, local, u) for u, _ in samples]))
                        curves = matrices @ q[segment_slice(local)]
                        widths = jnp.asarray([w for _, w in samples]) * lengths[self.length_indices[part]]
                        def step(transform, values):
                            width, curve = values
                            return transform @ cell_pose(width, curve[0], curve[1]), None
                        result, _ = jax.lax.scan(step, result, (widths, curves))
                poses[key] = result
            return poses[key]

        tip = self.design.tip
        tip_pose = pose(tip.part, tip.s) @ jnp.asarray(rigid_transform(tip.position_m, tip.quaternion_wxyz))
        tendon_lengths = []
        for tendon in self.design.tendons:
            positions = []
            for point in tendon.points:
                a = point.attachment
                offset = self.parts[a.part].guide_holes[point.hole] if point.hole else a.position_m
                positions.append((pose(a.part, a.s) @ jnp.asarray(rigid_transform(offset, a.quaternion_wxyz)))[:3, 3])
            positions = jnp.stack(positions)
            tendon_lengths.append(jnp.sum(jnp.linalg.norm(positions[1:]-positions[:-1], axis=1)))
        return jnp.concatenate([tip_pose[:3, 3], jnp.stack(tendon_lengths)])

    def tendon_force(self, q, proximal_length, tensions):
        return -jax.jacfwd(self.quantities, argnums=0)(q, proximal_length)[3:].T @ tensions
