"""Isolated numerical admission checks; no provider and no physical launches."""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata as metadata
import inspect
import time
import json
import typing
import jax
jax.config.update('jax_enable_x64', True)
import jax.numpy as jnp
import numpy as np
import casadi as ca
import cyipopt  # Verify the native binary loads; this does not launch a solve.
from schemas.soromox_pilot import WorkerInput, WorkerOutput
from extensions.tendon_family.soromox_mapping import RoutingMap
from extensions.tendon_family.gvs import _topology
from extensions.tendon_family.gvs_basis import resolve_basis, basis_matrix
from extensions.tendon_family.gvs_casadi import _SymbolicKinematics
from extensions.tendon_family.pcc import rigid_transform
from extensions.tendon_family.sections import properties, at
from soromox.systems import GVS, GVSSegment, JointSpec, LinkSpec, StrainBasisSpec
from soromox.systems.gvs.specs import BasisType


def timed(fn):
    started = time.perf_counter()
    value = fn()
    jax.block_until_ready(value)
    return value, time.perf_counter()-started


def reference(design, basis):
    topology = _topology(design)
    q = ca.MX.sym('q', basis.dimension)
    state = _SymbolicKinematics(topology, q, 24, basis)
    tip = state.attachment_pose(topology[0].tip)[:3, 3]
    lengths = []
    for tendon in topology[0].tendons:
        points = []
        for point in tendon.points:
            a = point.attachment
            offset = topology[1][a.part].guide_holes[point.hole] if point.hole else None
            points.append(state.attachment_pose(a, offset)[:3, 3])
        lengths.append(sum(ca.norm_2(b-a) for a, b in zip(points, points[1:])))
    values = ca.vertcat(tip, *lengths)
    return ca.Function('pilot_mapping', [q], [values, ca.jacobian(values, q)])


def checks(request):
    started = time.perf_counter()
    costs = {}
    cfg = request.configuration
    design = cfg['robot']['structure']['data']
    basis_spec = cfg['policy']['controller']['parameters']['data']['recipe']['basis']
    basis = resolve_basis(design, basis_spec)
    routing = RoutingMap(design, basis_spec)
    n = basis.dimension
    states = [np.zeros(n), np.linspace(-2., 3., n), np.array([0., 2., 0.]* (n//3))]
    # Freeze thresholds before evaluating any result.
    tolerances = dict(mapping_abs=1e-9, state_jacobian_abs=1e-8,
                      design_derivative_relative=1e-5, design_derivative_abs=1e-8,
                      curvature_basis_abs=1e-10, native_length_derivative_abs=1e-7,
                      central_steps_m=[1e-4, 1e-5, 1e-6])
    fn = jax.jit(routing.quantities)
    jac = jax.jit(jax.jacfwd(routing.quantities, argnums=0))
    dp = jax.jit(jax.jacfwd(routing.quantities, argnums=1))
    _, costs['mapping_cold_compile_and_evaluate'] = timed(lambda: (fn(states[0], .16), jac(states[0], .16), dp(states[0], .16)))
    t = time.perf_counter(); ca_fn = reference(design, basis); costs['casadi_construction'] = time.perf_counter()-t
    records = []
    passed = True
    for q in states:
        actual, warmed = timed(lambda: fn(q, .16))
        t = time.perf_counter(); expected, j_expected = ca_fn(q); ca_elapsed = time.perf_counter()-t
        j_actual = np.asarray(jac(q, .16)); derivative = np.asarray(dp(q, .16))
        value_error = float(np.max(np.abs(np.asarray(actual)-np.asarray(expected).ravel())))
        jac_error = float(np.max(np.abs(j_actual-np.asarray(j_expected))))
        steps = []
        for h in tolerances['central_steps_m']:
            finite = np.asarray((fn(q, .16+h)-fn(q, .16-h))/(2*h))
            error = float(np.max(np.abs(finite-derivative)))
            scale = float(np.max(np.abs(derivative)))
            ok = error <= tolerances['design_derivative_abs']+tolerances['design_derivative_relative']*scale
            steps.append(dict(step_m=h, max_abs_error=error, passed=ok)); passed &= ok
        passed &= value_error <= tolerances['mapping_abs'] and jac_error <= tolerances['state_jacobian_abs']
        u = np.linspace(.2, .4, len(design['tendons']))
        force = -j_actual[3:].T @ u
        direction = np.linspace(-.4, .6, n)
        h = 1e-5
        length_work = float(u @ ((np.asarray(fn(q+h*direction, .16))[3:]-np.asarray(fn(q-h*direction, .16))[3:])/(2*h)))
        work_error = abs(float(force @ direction)+length_work)
        passed &= work_error <= tolerances['state_jacobian_abs']
        records.append(dict(q_rad_m=q.tolist(), mapping_abs_error=value_error, state_jacobian_abs_error=jac_error,
            partial_length_derivative=derivative.tolist(), central_difference=steps, virtual_work_sign_error=work_error,
            warmed_jax_s=warmed, casadi_evaluation_s=ca_elapsed, tip_robot_base_m=np.asarray(actual)[:3].tolist(),
            tendon_lengths_m=np.asarray(actual)[3:].tolist()))

    # Probe the actual supported factory; this object is NOT the current robot.
    segment = next(c for c in design['components'] if c['kind']=='flexible_segment')
    probe_link = LinkSpec.elliptical(length=.16, semi_major=.0095, semi_minor=.0076,
        density=1100., young_modulus=7.2e6, poisson_ratio=.45,
        material_damping_coefficient=1., reference_strain=[0, 0, 0, 1, 0, 0])
    rejection = None
    try:
        GVS.from_segments([GVSSegment(probe_link, JointSpec.fixed(),
            StrainBasisSpec(type='structural_linear', strain_selector=('kappa_y', 'kappa_z'), basis_order=2), 5)])
    except (ValueError, KeyError) as exc:
        rejection = dict(type=type(exc).__name__, message=str(exc))
    t = time.perf_counter()
    probe = GVS.from_segments([GVSSegment(probe_link, JointSpec.fixed(),
        StrainBasisSpec(type='legendre', strain_selector=('kappa_y', 'kappa_z'), basis_order=2), 5)],
        gravity=jnp.array([0., 0., -9.81]), backend='jax')
    costs['native_probe_construction'] = time.perf_counter()-t
    # Public geometry update retains matrix semantics: do not call stiffness
    # a material-refresh check. Only native kinematics are tested here.
    def native_tip(length):
        updated = probe.update_link_params(length=jnp.reshape(length, (1,)))
        return updated.forward_kinematics(jnp.zeros(updated.num_coordinates), length)[:3, 3]
    native_fn = jax.jit(native_tip); native_dp = jax.jit(jax.jacfwd(native_tip))
    values, costs['native_probe_cold_compile_and_evaluate'] = timed(lambda: (native_fn(.16), native_dp(.16)))
    native_fd = np.asarray((native_fn(.16001)-native_fn(.15999))/.00002)
    native_error = float(np.max(np.abs(np.asarray(values[1])-native_fd)))
    passed &= native_error <= tolerances['native_length_derivative_abs']

    # A polynomial interpolating nodal values cannot preserve the hat strain
    # between knots. This is a diagnostic of the tempting equal-DOF mapping.
    samples = np.array([0., .25, .5, .75, 1.])
    local = basis.segments[0]
    hat = np.array([basis_matrix(basis, local, float(s))[0, :len(local.knots)] for s in samples])
    vandermonde = np.polynomial.legendre.legvander(np.array(local.knots)*2-1, len(local.knots)-1)
    nodal_to_poly = np.linalg.inv(vandermonde)
    polynomial = np.polynomial.legendre.legvander(samples*2-1, len(local.knots)-1) @ nodal_to_poly
    basis_error = float(np.max(np.abs(hat-polynomial)))
    sections = []
    for s in _topology(design)[3]:
        for u in (0., .5, 1.):
            prop = properties(at(s, u))
            sections.append(dict(segment=s.id, normalized_s=u, area_m2=prop['area_m2'],
                angle_rad=at(s, u).angle_rad, bending_area_m4=prop['bending_area_m4'],
                off_diagonal_m4=prop['bending_area_m4'][0][1]))
    import soromox.systems.gvs.specs as specs
    import soromox.systems.gvs.structures as structures
    import soromox.systems.components.cross_sections as cross_sections
    sources = {}
    for module in (specs, structures, cross_sections):
        path = Path(inspect.getfile(module)); body = path.read_bytes()
        sources[module.__name__] = dict(sha256=hashlib.sha256(body).hexdigest(), filename=path.name)
    reasons = [
        'Native GVS factory rejects structural_linear. Its six supported basis families lack the required nodal hat basis.',
        'An equal-coordinate quadratic Legendre interpolation changes the strain field between structural knots; it is not a coordinate transform.',
        'Native cross-section properties expose principal moments, whereas the source has rotated bending/inertial tensors and a distal rotation varying with arc position.',
        'The minimal factory mapping also lacks the separately owned guide, connector and payload inertia/offset representation. They have not been homogenized or dropped.',
        'Subdivision plus tied coordinates, tensor rotation and discrete rigid inertia would require a larger mechanics adapter and new validation; this bounded pilot stops at admission.'
    ]
    if not passed or rejection is None or basis_error <= tolerances['curvature_basis_abs']:
        reasons.insert(0, 'Admission diagnostic failed; inspect all retained numerical records.')
    costs['worker_total'] = time.perf_counter()-started
    return WorkerOutput(gate='model_incompatible' if passed and rejection and basis_error>tolerances['curvature_basis_abs'] else 'check_failed',
        reasons=reasons, checks=dict(tolerances=tolerances, exact_mapping_passed=bool(passed), representative_states=records,
            resolved_model=dict(dimensions=request.dimensions['dimensions'], coordinate_order=request.dimensions['coordinate_order'],
                tendon_input_order=request.dimensions['tendon_input_order'], actuator_command_order=request.dimensions['actuator_command_order'],
                backend_position_order=request.dimensions['backend_position_order'],
                physical_initialization=request.dimensions['physical_initialization'],
                basis=basis.model_dump(mode='json'), gravity_m_s2=[0.,0.,-9.81],
                mount_position_m=[0.,0.,.15], input_abstraction='independent ideal tension 0..8 N',
                assumptions=['bending only','straight frictionless discrete tendon spans','no motor dynamics','no contact']),
            native_factory_rejection=rejection, supported_basis=list(typing.get_args(BasisType)),
            basis_mismatch=dict(normalized_s=samples.tolist(), required_hat=hat.tolist(), interpolated_legendre=polynomial.tolist(),
                max_abs_basis_error=basis_error, variable=local.segment+'.kappa_y_node_1', time_s=None),
            section_tensors=sections, native_probe=dict(label='single unrotated link; not candidate mechanics',
                tip_m=np.asarray(values[0]).tolist(), partial_length_derivative=np.asarray(values[1]).tolist(), fd_abs_error=native_error),
            physical_initial_mapping=request.dimensions['numerical_initialization'],
            objective_gradient='not_run: no admitted NLP', constraint_jacobian='not_run: no admitted dynamics transcription',
            mechanics_design_derivatives='not_established', independent_replay='not_run: no admitted candidate'),
        costs_s=costs, versions={n: metadata.version(n) for n in ['soromox','jax','jaxlib','cyipopt','numpy','scipy','equinox','diffrax','casadi','pydantic']},
        sources=sources)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('request'); parser.add_argument('output'); args = parser.parse_args()
    request = WorkerInput.model_validate_json(Path(args.request).read_text(encoding='utf8'))
    output = checks(request)
    Path(args.output).write_text(output.model_dump_json(indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
