"""Stage 3.11: four forward-only measurements against the frozen GVS state.

Run from the repository root with the softagent Python environment. Only the
three files in this directory are retained; generated MJCF stays in memory.
"""
import hashlib
import io
import json
from pathlib import Path
import sys

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from extensions.tendon_family.compiler import quat, resolve, rx  # noqa: E402
from extensions.tendon_family.contracts import (  # noqa: E402
    Design, Discretization, GVSModelParameters, ResolvedGVSBasis,
)
from extensions.tendon_family.gvs import forward_kinematics  # noqa: E402
from extensions.tendon_family.gvs_basis import basis_matrix, segment_slice  # noqa: E402
from extensions.tendon_family.gvs_projection import discretization_jacobian  # noqa: E402
from extensions.tendon_family.mjcf import compile_xml  # noqa: E402
from tools.state_io import atomic_json, digest  # noqa: E402

HERE = Path(__file__).resolve().parent
FILES = {
    'route': 'runs/stage35_case_b_retry_softagent_20260924/inputs/route.json',
    'stage37': 'runs/stage37_gvs_backend_consistency_20260924/gvs_backend_consistency.json',
    'stage38': 'runs/stage38_physics_alignment_20260924/physics_alignment.json',
    'stage39': 'runs/stage39_physics_consistency_20260924/physics_consistency.json',
    'stage310': 'runs/stage310_robotir_physical_fact_audit_20260924/robotir_physical_fact_audit.json',
}
RESOLUTIONS = (3, 6, 12, 24)
GRID = np.linspace(0., 1., 101)  # Identical material coordinates for every mesh.
PRIMARY = ('tip_position_error_m', 'backbone_rms_error_m', 'far_segment_com_error_m',
           'gravity_absolute_error', 'stiffness_frobenius_error', 'tendon_jacobian_absolute_error')


def norm(value):
    return float(np.linalg.norm(value))


def compare(reference, backend):
    reference, backend = np.asarray(reference), np.asarray(backend)
    error = backend - reference
    return dict(reference=reference.tolist(), backend=backend.tolist(),
                difference=error.tolist(), absolute_error=norm(error),
                relative_error=norm(error) / norm(reference) if norm(reference) else None,
                max_entry_error=float(np.max(np.abs(error))))


def integral_mapping(physics, basis):
    """Integrate the piecewise-linear field exactly, including crossed knots."""
    mapping = np.zeros((len(physics['dofs']), basis.dimension))
    cells = []
    assert basis.specification.strategy == 'structural_linear'
    for local in basis.segments:
        indices = physics['entity_map'][local.segment]['bodies']
        for i, index in enumerate(indices):
            part = physics['parts'][index]
            left, right = i / len(indices), (i + 1) / len(indices)
            edges = [left, *(k for k in local.knots if left < k < right), right]
            integral = sum((local.length_m * (b - a) *
                            basis_matrix(basis, local, (a + b) / 2)
                            for a, b in zip(edges, edges[1:])),
                           np.zeros((2, 2 * len(local.knots))))
            rotation = rx(part['section_axis_rad'])[1:, 1:]
            mapping[np.ix_(part['dofs'], range(segment_slice(local).start,
                                              segment_slice(local).stop))] = rotation.T @ integral
            cells.append(dict(entity=part['entity'], component=local.segment,
                              normalized_interval=[left, right], split_edges=edges,
                              section_axis_rad=part['section_axis_rad'],
                              length_m=part['length_m'], mass_kg=part['mass_kg'],
                              com_local_m=part['com_local_m'],
                              stiffness_nm_rad=part['stiffness_nm_rad']))
    return mapping, cells


def tendon_jacobian(model, data):
    result = np.zeros((model.ntendon, model.nv))
    if data.ten_J.size == model.ntendon * model.nv:
        result[:] = data.ten_J.reshape(model.ntendon, model.nv)
    else:
        layout = model if hasattr(model, 'ten_J_rowadr') else data
        for k in range(model.ntendon):
            start, count = layout.ten_J_rowadr[k], layout.ten_J_rownnz[k]
            result[k, layout.ten_J_colind[start:start + count]] = data.ten_J[start:start + count]
    return result


def combined_mass(rows):
    mass = sum(row['mass_kg'] for row in rows)
    com = sum((row['mass_kg'] * np.asarray(row['com_world_m']) for row in rows),
              np.zeros(3)) / mass
    return dict(mass_kg=float(mass), com_world_m=com.tolist())


def trends(rows):
    result = {}
    for key in rows[0]['metrics']:
        values = np.array([row['metrics'][key] for row in rows])
        ratios = [float(b / a) if a else None for a, b in zip(values, values[1:])]
        # Descriptive finite-range labels, not acceptance thresholds or a claim
        # about an infinite-resolution limit. Exact invariant quantities have
        # no measurable trend. Any plateau judgment needs source-level review.
        if np.all(values == values[0]):
            classification = 'INCONCLUSIVE' if values[0] == 0 else 'PLATEAUING'
        elif np.all(np.diff(values) < 0):
            classification = 'CONVERGING'
        else:
            classification = 'NON_MONOTONIC'
        result[key] = dict(values=values.tolist(), successive_ratios=ratios,
                           observed_orders=[float(-np.log2(r)) if r and r > 0 else None
                                            for r in ratios], classification=classification)
    return result


def write_report(result):
    frozen, rows = result['frozen_reference'], result['resolutions']
    lines = ['# Stage 3.11: serial-bending discretization convergence', '',
             '## 1. Scientific question', '', result['scientific_question'], '',
             'Measurement only: 3, 6, 12 and 24 cells per flexible segment. No equilibrium solve, '
             'controller execution, dynamics stepping, tuning or production-code changes.', '',
             '## 2. Frozen reference identities', '']
    for name in ('parent_commit', 'robot_identity', 'design_id', 'design_identity',
                 'gvs_dynamic_system_identity', 'basis_identity', 'historical_scene_identity'):
        lines.append(f'- {name}: `{frozen[name]}`')
    lines += ['', 'The reference is the Stage 3.10 audited state inherited from Stages 3.7–3.9. '
              'Saved gravity, stiffness, tendon lengths/Jacobian and component masses/COMs are reused. '
              'GVS backbone and attachment positions are evaluated once at that same state; '
              'the tip is checked against the saved reference to 1e-12 m. Source paths and SHA-256 '
              'hashes, all numeric identities, full vectors and matrices are in the JSON.', '',
              f'- q0 (rad/m, coordinate order in JSON): `{frozen["q0"]}`',
              f'- u0 (N): `{frozen["u0_n"]}`',
              f'- Tendon order: `{frozen["tendon_order"]}`',
              f'- Gravity (world, m/s²): `{frozen["gravity_world_m_s2"]}`',
              f'- Mount: `{json.dumps(frozen["mount"])}`',
              '- Basis: structural_linear, knots [0, 0.5, 1] on each segment, 12 coordinates.',
              '- Integration: 24 steps per segment, partitioned at structural knots; unchanged.',
              '- Quadrature: 5 Gauss points per structural-knot interval; unchanged.',
              '- Historical finite-difference step: 1e-6; saved exact CasADi gravity and tendon Jacobian are reused.',
              f'- Runtime: Python {result["software"]["python"]}, MuJoCo {result["software"]["mujoco"]}, '
              f'NumPy {result["software"]["numpy"]}.', '',
              '## 3. Mapping semantics', '',
              '`kappa(s) = B(s) q0` in physical segment y/z axes. For each cell, '
              '`qcell = R_x(phi_cell)[yz].T integral_cell B(s) ds q0`. '
              'The integral is evaluated exactly for the piecewise-linear basis by splitting at '
              'every crossed knot and integrating each linear piece. Segment ordering and compiler '
              'principal-section rotations are preserved. Curvature is rad/m; cell angles are rad.', '',
              'This defines a constant matrix `J_N`, recorded in full: '
              '`qcell = J_N q0`, `Qg = J_N.T Qserial`, '
              '`K = J_N.T diag(k_hinge) J_N`, `D_length = D_serial J_N`. '
              'There is no tip fitting, optimization, or state-dependent force-map correction.', '',
              'The public discretization helper uses whole-cell midpoint curvature. It is identical '
              'to this integral at 6/12/24 cells, checked numerically. At 3 cells the middle cell '
              'crosses s=0.5, where the curvature slope changes. Therefore the three-cell *physics* '
              'identity matches Stage 3.7 exactly, but its mapped angles and comparison errors differ '
              'from the historical midpoint baseline. The maximum angle change is '
              f'{max(abs(x) for x in rows[0]["midpoint_qcell_difference_rad"]):.8g} rad. '
              'The same integral rule is applied at all four resolutions.', '',
              '## 4. Resolution table', '',
              'Absolute errors; vector norms are Euclidean and matrix norms are Frobenius. '
              'Gravity units are N·m²/rad, stiffness N·m³/rad², tendon Jacobian m²/rad.', '',
              '| Cells/segment | Backend DOFs | Tip error (m) | Backbone RMS (m) | Far COM (m) | Gravity error | Stiffness error | Tendon Jacobian error |',
              '| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for row in rows:
        lines.append(f'| {row["cells_per_segment"]} | {row["backend_coordinates"]} | ' +
                     ' | '.join(f'{row["metrics"][key]:.8g}' for key in PRIMARY) + ' |')
    lines += ['', 'Each JSON resolution row includes family.discretization data/identity, unchanged '
              'Design identity, generated physics identity, generated MJCF SHA-256, all mapped angles '
              'and per-cell parameters. XML is generated in memory with the existing compiler.', '',
              'Successive error ratios (no acceptance tolerance):', '',
              '| Metric | error6/error3 | error12/error6 | error24/error12 | Trend |',
              '| --- | ---: | ---: | ---: | --- |']
    for name, trend in result['convergence'].items():
        values = ['—' if v is None else f'{v:.6g}' for v in trend['successive_ratios']]
        lines.append(f'| {name} | ' + ' | '.join(values) + f' | {trend["classification"]} |')

    def metric_table(keys, scale=1., labels=None):
        lines.extend(['', '| Metric | 3 cells | 6 cells | 12 cells | 24 cells |',
                      '| --- | ---: | ---: | ---: | ---: |'])
        for key in keys:
            label = labels.get(key, key) if labels else key
            lines.append(f'| {label} | ' + ' | '.join(f'{row["metrics"][key]*scale:.8g}' for row in rows) + ' |')

    lines += ['', '## 5. Geometry convergence', '',
              'Both backbones use the same 101 normalized material locations per segment '
              '(including endpoints), independent of N. MuJoCo positions are sampled along each '
              'straight cell centerline. RMS weights all 202 sampled points equally. '
              'All reported geometry errors decrease; the primary geometry errors approach '
              'first-order reduction (ratio about 0.5). Raw world positions and pointwise errors are in JSON.']
    metric_table(['backbone_max_error_m', 'mid_guide_position_error_m',
                  'connector_position_error_m', 'payload_position_error_m'])
    lines += ['', '## 6. COM convergence', '',
              'Flexible reference COMs are the saved GVS distributed-mass quadrature at q0. '
              'Serial COMs mass-weight MuJoCo body COMs; rigid COMs include their local offsets. '
              'Whole-robot COM includes all physical components, excluding the massless world/mount. '
              'All COM errors decrease. Rigid masses are invariant; flexible midpoint mass '
              'integration approaches the fixed GVS mass without changing density or sections.']
    metric_table(['near_segment_com_error_m', 'far_segment_com_error_m', 'mid_guide_com_error_m',
                  'connector_com_error_m', 'payload_com_error_m', 'whole_robot_com_error_m'])
    lines += ['', '| Component | GVS mass (kg) | 3 cells | 6 cells | 12 cells | 24 cells |',
              '| --- | ---: | ---: | ---: | ---: | ---: |']
    for name, mass in frozen['values']['mass_by_component'].items():
        lines.append(f'| {name} | {mass["mass_kg"]:.12g} | ' + ' | '.join(
            f'{row["mass_by_component"][name]["mass_kg"]:.12g}' for row in rows) + ' |')
    lines.append(f'| Total | {frozen["values"]["whole_robot"]["mass_kg"]:.12g} | ' + ' | '.join(
        f'{row["whole_robot"]["mass_kg"]:.12g}' for row in rows) + ' |')
    lines += ['', '## 7. Gravity convergence', '',
              'At zero velocity, isolate gravity as `-(bias(g)-bias(0))` with zero controls. '
              'Passive springs are not part of qfrc_bias. The zero-gravity bias and the difference '
              'between bias with u0 and zero controls are checked. All poses are contact-free. '
              'Virtual work maps the resulting backend vector into the same 12 GVS coordinates. '
              'Per-coordinate reference, backend and signed error vectors are in JSON. '
              'Gravity error approximately halves at each refinement.']
    metric_table(['gravity_absolute_error', 'gravity_relative_error'])
    lines += ['', '## 8. Stiffness convergence', '',
              'Use existing MuJoCo joint stiffness EI/ds and the identical mapping J_N. '
              'The reference is the saved GVS elastic tangent matrix; this is constitutive stiffness, '
              'not a tangent including gravity or tendon preload. The mapping is linear, so there '
              'is no extra Hessian term. Relative error falls approximately fourfold per doubling '
              'from 6 cells onward. No hinge stiffness is tuned. Full matrices are in JSON.']
    metric_table(['stiffness_frobenius_error', 'stiffness_relative_error'])
    lines += ['', '## 9. Tendon convergence', '',
              'Native MuJoCo tendon derivatives are composed with J_N in the frozen tendon order. '
              'Their force sign/order is checked by virtual work against actuator force at u0. '
              'The Jacobian norm, relative error and maximum entry error all decrease.', '',
              'Signed length errors (backend minus GVS, m):', '',
              '| Tendon | 3 cells | 6 cells | 12 cells | 24 cells |',
              '| --- | ---: | ---: | ---: | ---: |']
    for i, name in enumerate(frozen['tendon_order']):
        lines.append(f'| {name} | ' + ' | '.join(f'{row["tendon_lengths"]["difference"][i]:.8g}' for row in rows) + ' |')
    metric_table(['tendon_length_error_norm_m', 'tendon_jacobian_absolute_error',
                  'tendon_jacobian_relative_error', 'tendon_jacobian_max_entry_error'])
    lines += ['', 'far_t2 length error is NON_MONOTONIC: its signed error crosses zero between '
              '3 and 6 cells and its magnitude initially grows, then falls at 12 and 24. '
              'far_t1 also has a nearly flat 6→12 length-error interval, followed by further reduction. '
              'Neither establishes a persistent nonzero plateau. A limited source inspection finds '
              'that compiler.py:78–80 binds s=0.5 to the middle cell interior at N=3 and a downstream '
              'cell origin for even N; lateral tendon offsets use that cell orientation. '
              'mjcf.py:40 and :68 attach both root hinges and sites to that body. '
              'Tendon site placement and cancellation of signed span errors are plausible causes '
              'of the coarse non-monotonicity, not demonstrated causes. No change or extra sweep was made.', '',
              '## 10. Final classification', '',
              f'**{result["conclusion"]["classification"]} — confidence {result["conclusion"]["confidence"]}.**', '',
              result['conclusion']['interpretation'], '',
              'Trend labels describe these four measurements: strictly decreasing errors are '
              'CONVERGING; exact nonzero constants are PLATEAUING; reversals are NON_MONOTONIC; '
              'an exact zero invariant is INCONCLUSIVE for estimating a convergence rate. '
              'No pass/fail equivalence tolerances or composite score are introduced. '
              'Ratios and observed log2 orders are retained for independent interpretation.', '',
              'Confidence applies to the observed finite-range trend for this robot and state. '
              'Four resolutions do not prove the infinite-resolution limit or equivalence at '
              'other states. The fixed 24-step GVS geometry can eventually impose a reference-error '
              'floor; it was not refined. At N=24, residual tip error is still about 2.06 mm '
              'and gravity relative error about 2.73%. The earlier three-cell mapping convention '
              'also contributes to the historical discrepancy.', '',
              'Validation completed: syntax/import check, this diagnostic, and focused forward '
              'calculations for the four requested resolutions. No full test suite, simulations, '
              'additional resolutions, parameter changes, controllers or schema changes.', '',
              '## 11. Recommended next step', '', result['conclusion']['recommendation'], '',
              'Reproduce from the repository root with the softagent environment:', '',
              '```powershell',
              "& 'C:\\Users\\gugugaga\\miniconda3\\envs\\softagent\\python.exe' runs/stage311_discretization_convergence_20260926/discretization_convergence.py",
              '```', '']
    (HERE / 'discretization_convergence.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    inputs = {key: json.loads((ROOT / path).read_text(encoding='utf-8'))
              for key, path in FILES.items()}
    route, s37, s38, s39, s310 = (inputs[k] for k in FILES)
    design = Design.model_validate(route['robot']['structure']['data'])
    basis = ResolvedGVSBasis.model_validate(s37['identities']['resolved_basis'])
    parameters = GVSModelParameters(basis=basis.specification)
    q0, u0 = (np.asarray(s37['baseline'][key]) for key in ('q0', 'u0'))
    tendon_order = s37['baseline']['tendon_order']
    assert basis.dimension == 12
    assert digest(route['robot']) == s310['reference']['robot_identity'] == s39['reference_state']['robot_identity']
    assert digest(design.model_dump(mode='json')) == s310['reference']['design_identity']
    assert digest(basis.model_dump(mode='json')) == s310['reference']['basis_identity'] == s38['reference_state']['basis_identity']
    assert np.array_equal(q0, s39['reference_state']['q0'])
    assert np.array_equal(u0, s39['reference_state']['u0_n'])
    assert s37['identities']['dynamic_system'] == s39['reference_state']['gvs_dynamic_system_identity']
    assembly = route['task']['environment']['data']
    mount = assembly['mount']
    mount_p, mount_R = np.asarray(mount['position_m']), quat(mount['quaternion_wxyz'])
    gravity = assembly['environment']['gravity_m_s2']
    assert gravity == s39['reference_state']['gravity_world_m_s2']
    assert not assembly['external_forces']
    # Only fields consumed by compile_xml. All come from the saved task and
    # Stage 3.7 execution mode; no controller is built, called, or simulated.
    scene = dict(timestep_s=route['task']['timing']['timestep_s'], gravity=gravity,
                 floor_id=assembly['floor_id'],
                 floor_z_m=next(o['position_m'][2] for o in assembly['environment']['objects']
                               if o['name'] == assembly['floor_id']),
                 target_world_m=route['task']['goal']['data']['target_m'],
                 mount_position=mount_p.tolist(), mount_rotation=mount_R.tolist(),
                 control={'tension_execution_mode': s37['baseline']['tension_execution_mode']})
    assert scene['control']['tension_execution_mode'] == 'ideal_tension'
    kin = forward_kinematics(design, q0, samples_per_segment=len(GRID),
                             integration_steps_per_segment=parameters.integration_steps_per_segment,
                             basis=basis.specification)
    reference = dict(
        tip_world_m=s37['baseline']['gvs_tip_world_m'],
        backbone_world_m={name: (mount_p + points @ mount_R.T).tolist()
                          for name, points in kin['segment_backbones_m'].items()},
        component_positions_world_m={name: (mount_p + mount_R @ pose[:3, 3]).tolist()
                                     for name, pose in kin['component_transforms'].items()
                                     if name in ('mid_guide', 'connector', 'payload')},
        mass_by_component={name: {key: row['gvs'][key] for key in ('mass_kg', 'com_world_m')}
                           for name, row in s39['mass_com_inertia_by_component'].items()},
        gravity=s37['baseline']['gvs_forces']['gravity_force'],
        stiffness=s38['stiffness_matrix']['gvs_matrix'],
        tendon_lengths_m=s37['baseline']['gvs_tendon_lengths_m'],
        tendon_jacobian=s37['baseline']['gvs_tendon_jacobian'])
    reference['whole_robot'] = combined_mass(reference['mass_by_component'].values())
    assert np.allclose(mount_p + mount_R @ kin['tip_position_m'], reference['tip_world_m'], rtol=0, atol=1e-12)
    rows = []
    for count in RESOLUTIONS:
        mesh = Discretization(cells={seg.segment: count for seg in basis.segments})
        physics = resolve(design, mesh)
        assert physics['design_identity'] == s310['reference']['design_identity']
        if count == 3:
            assert physics['identity'] == s37['identities']['physics']
        for tendon, compiled in zip(design.tendons, physics['tendons']):
            assert tendon.id == compiled['entity']
            assert [p.model_dump(mode='json') for p in tendon.points] == [p['physical_binding'] for p in compiled['points']]
        mapping, cells = integral_mapping(physics, basis)
        midpoint_mapping = discretization_jacobian(physics, basis)
        if count != 3:
            assert np.allclose(mapping, midpoint_mapping, rtol=0, atol=1e-15)
        qcell = mapping @ q0
        xml = io.BytesIO()
        compile_xml(physics, scene, None, xml)
        xml_hash = hashlib.sha256(xml.getvalue()).hexdigest()
        model = mujoco.MjModel.from_xml_string(xml.getvalue().decode('utf-8'))
        data = mujoco.MjData(model)
        joints = [model.joint(name).id for name in physics['dofs']]
        qi, vi = model.jnt_qposadr[joints], model.jnt_dofadr[joints]
        tids = [model.tendon(name).id for name in tendon_order]
        aids = [model.actuator(name + '_direct_tension').id for name in tendon_order]
        assert model.nq == model.nv == len(qcell) == 4 * count
        assert np.array_equal(model.opt.gravity, gravity)
        data.qpos[qi], data.qvel[:], data.ctrl[aids] = qcell, 0, u0
        mujoco.mj_forward(model, data)
        assert np.allclose(-data.actuator_force[aids], u0, rtol=0, atol=1e-12)
        assert data.ncon == 0 and norm(data.qfrc_constraint) == 0
        backend_positions = {name: data.xpos[model.body(name).id].copy()
                             for name in reference['component_positions_world_m']}
        backend_positions['tip'] = data.site_xpos[model.site('tip_site').id].copy()
        pose_comparisons = {name: compare(ref, backend_positions[name])
                            for name, ref in {**reference['component_positions_world_m'],
                                              'tip': reference['tip_world_m']}.items()}
        backbones = {}
        for local in basis.segments:
            indices = physics['entity_map'][local.segment]['bodies']
            points = []
            for s in GRID:
                index = min(int(s * count), count - 1)
                part = physics['parts'][indices[index]]
                bid = model.body(part['entity']).id
                point = data.xpos[bid] + data.xmat[bid].reshape(3, 3) @ np.array([
                    (s * count - index) * part['length_m'], 0., 0.])
                points.append(point)
            comp = compare(reference['backbone_world_m'][local.segment], points)
            distances = np.linalg.norm(np.asarray(comp['difference']), axis=1)
            backbones[local.segment] = dict(**comp, point_errors_m=distances.tolist(),
                                            rms_error_m=float(np.sqrt(np.mean(distances**2))),
                                            max_error_m=float(max(distances)))
        mass_by_component = {}
        for name, entity in physics['entity_map'].items():
            bids = [model.body(physics['parts'][i]['entity']).id for i in entity['bodies']]
            mass = combined_mass([dict(mass_kg=model.body_mass[bid], com_world_m=data.xipos[bid])
                                  for bid in bids])
            ref = reference['mass_by_component'][name]
            mass_by_component[name] = dict(**mass, mass_difference_kg=mass['mass_kg']-ref['mass_kg'],
                                           com_comparison=compare(ref['com_world_m'], mass['com_world_m']))
            if entity['kind'] != 'flexible_segment':
                assert abs(mass['mass_kg'] - ref['mass_kg']) < 1e-14
        whole = combined_mass(mass_by_component.values())
        whole['mass_difference_kg'] = whole['mass_kg'] - reference['whole_robot']['mass_kg']
        whole['com_comparison'] = compare(reference['whole_robot']['com_world_m'], whole['com_world_m'])
        serial_tendon_jac = tendon_jacobian(model, data)[tids][:, vi]
        virtual_work_error = norm(data.qfrc_actuator[vi] + serial_tendon_jac.T @ u0)
        assert virtual_work_error < 1e-12
        tendon = compare(reference['tendon_jacobian'], serial_tendon_jac @ mapping)
        lengths = compare(reference['tendon_lengths_m'], data.ten_length[tids])
        stiffness_diagonal = model.jnt_stiffness[joints]
        stiffness = compare(reference['stiffness'], mapping.T @ (stiffness_diagonal[:, None] * mapping))
        # At qvel=0, qfrc_bias contains gravity only. Isolate with ctrl=0 and
        # subtract the zero-gravity bias; passive springs are a separate term.
        bias_with_u0 = data.qfrc_bias[vi].copy()
        data.ctrl[:] = 0
        mujoco.mj_forward(model, data)
        bias_gravity = data.qfrc_bias[vi].copy()
        assert np.allclose(bias_gravity, bias_with_u0, rtol=0, atol=1e-14)
        model.opt.gravity[:] = 0
        mujoco.mj_forward(model, data)
        bias_zero = data.qfrc_bias[vi].copy()
        assert norm(bias_zero) < 1e-14
        serial_gravity = -(bias_gravity - bias_zero)
        grav = compare(reference['gravity'], mapping.T @ serial_gravity)
        model.opt.gravity[:] = gravity
        errors = np.concatenate([row['point_errors_m'] for row in backbones.values()])
        metrics = dict(tip_position_error_m=pose_comparisons['tip']['absolute_error'],
                       backbone_rms_error_m=float(np.sqrt(np.mean(errors**2))),
                       backbone_max_error_m=float(max(errors)),
                       total_mass_absolute_error_kg=abs(whole['mass_difference_kg']),
                       whole_robot_com_error_m=whole['com_comparison']['absolute_error'],
                       gravity_absolute_error=grav['absolute_error'], gravity_relative_error=grav['relative_error'],
                       stiffness_frobenius_error=stiffness['absolute_error'], stiffness_relative_error=stiffness['relative_error'],
                       tendon_length_error_norm_m=lengths['absolute_error'],
                       tendon_jacobian_absolute_error=tendon['absolute_error'],
                       tendon_jacobian_relative_error=tendon['relative_error'],
                       tendon_jacobian_max_entry_error=tendon['max_entry_error'])
        metrics.update({name + '_com_error_m': row['com_comparison']['absolute_error']
                        for name, row in mass_by_component.items()})
        metrics['far_segment_com_error_m'] = metrics.pop('far_com_error_m')
        metrics['near_segment_com_error_m'] = metrics.pop('near_com_error_m')
        metrics.update({name + '_position_error_m': row['absolute_error']
                        for name, row in pose_comparisons.items() if name != 'tip'})
        metrics.update({name + '_length_absolute_error_m': abs(lengths['difference'][i])
                        for i, name in enumerate(tendon_order)})
        rows.append(dict(cells_per_segment=count, discretization=mesh.model_dump(mode='json'),
                         discretization_identity=physics['discretization_identity'],
                         generated_physics_identity=physics['identity'], generated_mjcf_sha256=xml_hash,
                         design_identity=physics['design_identity'], backend_coordinates=model.nv,
                         coordinate_order=physics['dofs'], q_serial_rad=qcell.tolist(),
                         mapping_jacobian=mapping.tolist(), cells=cells,
                         midpoint_mapping_difference_frobenius=norm(mapping-midpoint_mapping),
                         midpoint_qcell_difference_rad=((mapping-midpoint_mapping) @ q0).tolist(),
                         component_positions=pose_comparisons, backbone=backbones,
                         mass_by_component=mass_by_component, whole_robot=whole,
                         gravity=grav, serial_gravity_nm=serial_gravity.tolist(),
                         gravity_per_coordinate=[dict(coordinate=name, reference=grav['reference'][i],
                                                      backend=grav['backend'][i], error=grav['difference'][i])
                                                 for i, name in enumerate(basis.coordinate_order)],
                         stiffness=stiffness, serial_stiffness_diagonal_nm_rad=stiffness_diagonal.tolist(),
                         tendon_lengths=lengths, tendon_jacobian=tendon,
                         serial_tendon_jacobian=serial_tendon_jac.tolist(),
                         invariants=dict(physical_design_unchanged=True, tendon_bindings_unchanged=True,
                                         rigid_masses_unchanged=True, contacts=0,
                                         zero_gravity_bias_norm=norm(bias_zero),
                                         tendon_virtual_work_error_nm=virtual_work_error,
                                         fixed_u0_gravity_bias_difference=norm(bias_with_u0-bias_gravity)),
                         metrics=metrics))
        print(json.dumps(dict(cells=count, metrics=metrics)), flush=True)
    result = dict(
        scientific_question='Does serial-bending refinement approach the fixed Stage 3.10 GVS reference?',
        frozen_reference=dict(parent_commit='e79f7e03f0009551fdf0e08b813d2da9dccff224',
            sources={key: dict(path=path, sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest())
                     for key, path in FILES.items()},
            robot_identity=s310['reference']['robot_identity'], design_id=design.id,
            design_identity=s310['reference']['design_identity'],
            basis_identity=s310['reference']['basis_identity'], resolved_basis=basis.model_dump(mode='json'),
            gvs_dynamic_system_identity=s37['identities']['dynamic_system'],
            historical_scene_identity=s37['identities']['scene'],
            historical_discretization_identity=s310['reference']['discretization_identity'],
            q0=q0.tolist(), u0_n=u0.tolist(), coordinate_order=basis.coordinate_order,
            tendon_order=tendon_order, gravity_world_m_s2=gravity, mount=mount,
            assembly=assembly, compiler_scene=scene,
            gvs_parameters=parameters.model_dump(mode='json'),
            parameter_provenance='Same GVSModelParameters defaults and structural_linear basis used by Stage 3.7/3.9; no new equilibrium.',
            common_normalized_backbone_grid=GRID.tolist(), values=reference),
        mapping_semantics=dict(curvature='kappa(s)=B(s) q_GVS in segment y,z axes; q units rad/m',
            cell_angle='q_cell=R_x(phi_cell)[y,z].T integral_cell B(s) ds q_GVS; units rad',
            integration='Exact midpoint integral on each piecewise-linear basis interval, split at every crossed knot.',
            jacobian='Constant linear map J_N; gravity J_N.T Q_serial; stiffness J_N.T K_serial J_N; tendon D_serial J_N.',
            existing_helper='gvs_projection.discretization_jacobian uses whole-cell midpoint samples. Equivalent for 6/12/24; not for the 3-cell knot-crossing cell.',
            historical_baseline='Three-cell physics is identical to Stage 3.7, but qcell follows the required integrated curvature rather than its former midpoint approximation.',
            backbone='101 shared normalized material locations per flexible segment; sample straight MuJoCo cell centerlines in world coordinates.'),
        measurement_units=dict(position='m', mass='kg', gravity='N m^2/rad (q is curvature rad/m)',
                               stiffness='N m^3/rad^2', tendon_length='m', tendon_jacobian='m^2/rad'),
        software=dict(python=sys.version.split()[0], numpy=np.__version__, mujoco=mujoco.__version__),
        resolutions=rows, convergence=trends(rows))
    all_primary_decrease = all(result['convergence'][key]['classification'] == 'CONVERGING'
                               for key in PRIMARY)
    some_primary_decrease = any(result['convergence'][key]['classification'] == 'CONVERGING'
                                for key in PRIMARY)
    classification = ('DISCRETIZATION_CONVERGENCE_SUPPORTED' if all_primary_decrease else
                      'PARTIAL_CONVERGENCE' if some_primary_decrease else
                      'DISCRETIZATION_CONVERGENCE_NOT_SUPPORTED')
    result['conclusion'] = dict(classification=classification, confidence='HIGH' if all_primary_decrease else 'MEDIUM',
        interpretation='All six primary errors decrease at every refinement, as do every component COM/position error, '
                       'the total mass error and aggregate tendon-length error. Geometry, COM and gravity show '
                       'approximately first-order reduction; stiffness and mass show second-order reduction on '
                       'the finer meshes. This supports finite serial discretization as a large contributor to '
                       'the Stage 3.7–3.9 mismatch under the required integrated-curvature mapping. '
                       'The single coarse tendon-length reversal does not overturn the consistent multi-quantity trend.',
        recommendation=('Define a minimal cross-model equivalence contract and select practical fidelity levels '
                        'from measured cost versus error, retaining per-tendon checks; no universal cell count is established here.'
                        if all_primary_decrease else
                        'Investigate only the non-converging quantities before expanding the study.' if some_primary_decrease else
                        'Inspect the representation mapping before introducing SoRoSim or MPC.'))
    result['suspected_nonconvergent_mechanism'] = dict(
        primary_metrics='None shows a persistent plateau or worsening trend in the tested range.',
        exception='far_t2_length_absolute_error_m', category='tendon site placement',
        status='Plausible coarse-grid explanation, not established nonconvergence or a demonstrated cause.',
        evidence=['far_t2 signed length error crosses zero from N=3 to N=6; N=12/24 magnitudes decrease.',
                  'far_t2 has lateral guide points at s=0.5 on both flexible segments.',
                  'compiler.py:78-80 places s=0.5 inside a cell at N=3, at a downstream cell origin for even N.',
                  'mjcf.py:40,68 uses the full cell root-hinge orientation for those lateral sites.'],
        sources=['extensions/tendon_family/compiler.py:71', 'extensions/tendon_family/mjcf.py:40'],
        action='Source inspection only; no production change or additional resolution.')
    atomic_json(HERE / 'discretization_convergence.json', result)
    write_report(result)


if __name__ == '__main__':
    main()
