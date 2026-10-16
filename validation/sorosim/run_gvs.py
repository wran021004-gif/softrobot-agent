"""Read-only adapter to the pinned repository kernels for this validation only."""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

import casadi as ca
import numpy as np
import scipy
from scipy.optimize import root

from extensions.tendon_family.contracts import (
    Design, GVSContinuousDynamicsExpression, GVSModelParameters,
)
from extensions.tendon_family.gvs import (
    _topology, constitutive_forces, coordinate_order, forward_kinematics,
    gravity_force, tendon_kinematics,
)
from extensions.tendon_family.gvs_casadi import (
    GVSStaticCasadiExpressions, _SymbolicKinematics, _angular_jacobian,
)


def plain(value):
    if isinstance(value, (np.ndarray, np.generic)):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(type(value).__name__)


def write_json(path, value):
    path.write_text(json.dumps(value, default=plain, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def make_design(cfg, model):
    components = []
    for k, (length, radius) in enumerate(zip(model['lengths_m'], model['radii_m'])):
        components.append(dict(
            id=f's{k}', kind='flexible_segment', length_m=length,
            connection=dict(part='fixed_base' if k == 0 else f's{k-1}', s=0 if k == 0 else 1),
            sections=[dict(s=0, section=dict(kind='circle', parameters=dict(radius_m=radius)))],
            physics=dict(mode='material', density_kg_m3=cfg['density_kg_m3'], young_pa=cfg['young_pa']),
        ))
    tip = dict(part=f's{len(components)-1}', s=1)
    tendons = [dict(
        id=f't{k}', diameter_m=.0005, length_servo_gain_n_m=100, force_limit_n=5,
        points=[dict(role='start', attachment=dict(part='fixed_base', position_m=d)),
                dict(role='anchor', attachment=dict(**tip, position_m=d))],
    ) for k, d in enumerate(cfg['tendon_offsets_m'])]
    return Design.model_validate(dict(
        id=model['id'], components=components, tendons=tendons, tip=tip,
        actuators=[dict(id=f'a{k}', transmission=[dict(tendon=t['id'], ratio=1)],
                        limits=[-.1, .1], velocity_limit=.1) for k, t in enumerate(tendons)],
    ))


def build(cfg, model, level):
    design = make_design(cfg, model)
    params = GVSModelParameters(integration_steps_per_segment=level['gvs_steps'],
                                quadrature_points_per_segment=level['gauss'])
    recipe = GVSContinuousDynamicsExpression(
        design=design, parameters=params, gravity_robot_base_m_s2=cfg['gravity_m_s2'],
        coordinate_order=coordinate_order(design), tendon_order=[t.id for t in design.tendons],
        tendon_force_limits_n=[t.force_limit_n for t in design.tendons],
    )
    native = GVSStaticCasadiExpressions(recipe)
    q, u = native.q_symbol, native.u_symbol
    state = _SymbolicKinematics(_topology(design), q, level['gvs_steps'], recipe.resolved_basis)
    pose = state.attachment_pose(design.tip)
    J = ca.vertcat(_angular_jacobian(pose[:3, :3], q), ca.jacobian(pose[:3, 3], q))
    offsets = cfg['tendon_offsets_m']
    ell = ca.vertcat(*[ca.norm_2(pose[:3, 3]+pose[:3, :3]@ca.DM(d)-ca.DM(d)) for d in offsets])
    dl = ca.jacobian(ell, q)
    residual = ca.substitute(native.static_residual_expression, u, ca.DM.zeros(len(offsets)))
    A = ca.jacobian(residual, q)
    # Obtain the constant constitutive matrix from the actual kernel.
    n = q.numel()
    K = np.column_stack([constitutive_forces(design, np.eye(n)[k], np.zeros(n), level['gauss'])[0]
                         for k in range(n)])
    names = ['pose', 'tip_jacobian', 'residual', 'residual_jacobian', 'stiffness',
             'gravity_force', 'tendon_lengths', 'tendon_length_jacobian', 'tendon_force_map', 'tendon_force']
    function = ca.Function('validation_terms', [q],
        [pose, J, residual, A, ca.DM(K), residual+K@q, ell, dl, -dl.T,
         -dl.T@ca.DM(cfg['probe_tensions_n'])], ['q'], names)

    def terms(v):
        return {key: np.asarray(value) for key, value in function(q=v).items()}

    return design, params, terms


def fd(fn, q, h):
    eye = np.eye(len(q))*h
    return np.column_stack([(fn(q+e)-fn(q-e)).ravel()/(2*h) for e in eye])


def pose_fd(terms, q, h, T):
    raw = fd(lambda v: terms(v)['pose'], q, h)
    cols = []
    for col in raw.T:
        dt = col.reshape(4, 4)
        W = dt[:3, :3]@T[:3, :3].T
        W = (W-W.T)/2
        cols.append(np.r_[W[2, 1], W[0, 2], W[1, 0], dt[:3, 3]])
    return np.column_stack(cols)


def maxabs(a):
    return float(np.max(np.abs(a)))


def solve(terms, n, cfg, initial=None, u=None):
    initial = np.zeros(n) if initial is None else initial
    def residual(q):
        t = terms(q)
        return (t['residual']+(0 if u is None else t['tendon_force_map']@u[:, None])).ravel()
    start = perf_counter()
    sol = root(residual, initial,
               jac=(lambda q: terms(q)['residual_jacobian']) if u is None else None,
               method='hybr', options=dict(xtol=1e-10, maxfev=500))
    seconds = perf_counter()-start
    norm = maxabs(residual(sol.x))
    if not sol.success or norm >= cfg['solver_residual_tolerance_nm2']:
        raise RuntimeError(f'equilibrium failed: {sol.message}; residual={norm}')
    return dict(q=sol.x, residual_norm=norm, status=int(sol.status), success=bool(sol.success),
                message=str(sol.message), function_evaluations=sol.nfev, seconds=seconds)


def run(cfg, model):
    result = dict(case_id=model['id'], levels=[])
    start_all = perf_counter()
    for level in model['levels']:
        start = perf_counter()
        design, params, terms = build(cfg, model, level)
        row = dict(setting=level, build_seconds=perf_counter()-start, probes=[])
        n = 4*len(model['lengths_m'])
        for q in np.asarray(model['probes_rad_m'], dtype=float):
            start = perf_counter(); t = terms(q)
            sample = dict(q=q, terms=t, seconds=perf_counter()-start, fd=[])
            for h in cfg['fd_steps_rad_m']:
                sample['fd'].append(dict(
                    step_rad_m=h,
                    tip_max_abs=maxabs(pose_fd(terms, q, h, t['pose'])-t['tip_jacobian']),
                    residual_max_abs=maxabs(fd(lambda v: terms(v)['residual'], q, h)-t['residual_jacobian']),
                    tendon_max_abs=maxabs(fd(lambda v: terms(v)['tendon_lengths'], q, h)-t['tendon_length_jacobian']),
                ))
            row['probes'].append(sample)
        # Independent existing NumPy paths guard against validation-only AD mistakes.
        q = np.asarray(model['probes_rad_m'][-1], dtype=float)
        t = terms(q)
        pose = forward_kinematics(design,q,samples_per_segment=2,
                                 integration_steps_per_segment=level['gvs_steps'])['tip_transform']
        elastic, _ = constitutive_forces(design,q,np.zeros(n),level['gauss'])
        grav = gravity_force(design,q,cfg['gravity_m_s2'],params)
        _, ell, dl = tendon_kinematics(design,q,params)
        row['numpy_kernel_check'] = dict(
            pose_max_abs=maxabs(pose-t['pose']),
            residual_max_abs=maxabs(grav-elastic-t['residual'].ravel()),
            length_max_abs=maxabs(ell-t['tendon_lengths'].ravel()),
            tendon_jacobian_max_abs=maxabs(dl-t['tendon_length_jacobian']),
        )
        eq = solve(terms,n,cfg)
        t = terms(eq['q']); eq['terms'] = t
        eq['tangent_condition'] = float(np.linalg.cond(t['residual_jacobian']))
        dqdu = -np.linalg.solve(t['residual_jacobian'],t['tendon_force_map'])
        sens = t['tip_jacobian'][3:]@dqdu
        eq['tip_sensitivity_m_n'] = sens; eq['sensitivity_fd'] = []
        for h in cfg['sensitivity_forward_steps_n']:
            measured = np.empty_like(sens); statuses = []; residuals = []
            for a in range(len(cfg['tendon_offsets_m'])):
                poses = []
                for m in (1,2):
                    u = np.zeros(len(cfg['tendon_offsets_m'])); u[a] = m*h
                    sol = solve(terms,n,cfg,eq['q'],u)
                    poses.append(terms(sol['q'])['pose'][:3,3])
                    statuses.append(sol['status']); residuals.append(sol['residual_norm'])
                measured[:,a] = (-3*t['pose'][:3,3]+4*poses[0]-poses[1])/(2*h)
            eq['sensitivity_fd'].append(dict(step_n=h,tip_sensitivity_m_n=measured,
                                             max_abs=maxabs(measured-sens),statuses=statuses,
                                             residual_norms=residuals))
        row['equilibrium'] = eq
        result['levels'].append(row)
        print(f"{model['id']} steps={level['gvs_steps']} Gauss={level['gauss']}: "
              f"status={eq['status']} residual={eq['residual_norm']:.3g} build={row['build_seconds']:.3f}s", flush=True)
    result['elapsed_seconds'] = perf_counter()-start_all
    return result


def provenance(cfg):
    # Verify every imported local source belongs to the requested starting tree.
    files = [REPO/'extensions/tendon_family'/name for name in
             ('gvs.py','gvs_basis.py','gvs_casadi.py','contracts.py','pcc.py','sections.py')]
    hashes = {}
    for path in files:
        rel = path.relative_to(REPO).as_posix()
        blob = subprocess.check_output(['git','show',f"{cfg['source_sha']}:{rel}"],cwd=REPO)
        actual = path.read_bytes().replace(b'\r\n',b'\n')
        if actual != blob.replace(b'\r\n',b'\n'):
            raise RuntimeError(f'Pinned kernel changed: {rel}')
        hashes[rel] = hashlib.sha256(actual).hexdigest()
    return dict(source_sha=cfg['source_sha'], python=platform.python_version(),executable=sys.executable,
                numpy=np.__version__, scipy=scipy.__version__,casadi=ca.__version__,kernel_sha256_lf=hashes)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', required=True, choices=['one_segment','two_segment'])
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    cfg = json.loads((HERE/'cases.json').read_text())
    model = next(c for c in cfg['cases'] if c['id']==args.case)
    args.output.mkdir(parents=True, exist_ok=True)
    prov = provenance(cfg)
    result = run(cfg,model); result['environment'] = prov
    write_json(args.output/f'gvs_{args.case}.json', result)
