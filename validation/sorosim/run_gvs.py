"""Read-only adapter to the pinned repository kernels for this validation only."""

import argparse
import copy
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


def build(cfg, model, level, v2=False):
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
    if v2:
        r = -native.static_residual_expression
        a = ca.jacobian(r, q)
        ru = ca.jacobian(r, u)
        p = native.tip_position_expression
        function = ca.Function('v2_terms', [q,u],
            [r,a,ru,p,ca.jacobian(p,q),ca.substitute(a,u,ca.DM.zeros(u.numel()))],
            ['q','u'], ['R','Rq','Ru','p','J','A0'])
        static = ca.Function('v2_static', [q,u], [r,a], ['q','u'], ['R','Rq'])
        def terms(v, tension):
            return {k: np.asarray(x) for k,x in function(q=v,u=tension).items()}
        terms.static = lambda v,tension: {k: np.asarray(x) for k,x in static(q=v,u=tension).items()}
        return design, params, terms
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


def v2_solve(terms, cfg, initial, u):
    start = perf_counter()
    sol = root(lambda q: terms.static(q,u)['R'].ravel(), initial,
               jac=lambda q: terms.static(q,u)['Rq'], method='hybr',
               options=dict(xtol=1e-10, maxfev=500))
    seconds = perf_counter()-start
    t = terms(sol.x,u)
    return dict(q=sol.x, p=t['p'].ravel(), R=t['R'].ravel(),
                residual_norm=maxabs(t['R']), status=int(sol.status), success=bool(sol.success),
                message=str(sol.message), function_evaluations=sol.nfev, seconds=seconds,
                condition=float(np.linalg.cond(t['Rq'])))


def run_v2(cfg, model):
    """Bounded local IFT experiment; all design partials hold physical q_g fixed."""
    v = cfg['v2']; level = model['levels'][-1]; start_all = perf_counter()
    start = perf_counter(); _,_,terms = build(cfg,model,level,v2=True)
    result = dict(schema=v['schema'], case_id=model['id'], setting=level,
                  model=model, units=v['units'], build_seconds=perf_counter()-start,
                  derivative_method='CasADi AD Rq/Ru/J; rebuilt centered FD design partials',
                  baselines=[], designs=[])
    n = 4*len(model['lengths_m'])
    for tension in v['baseline_tensions_n']:
        u = np.asarray(tension); eq = v2_solve(terms,cfg,np.zeros(n),u)
        row = dict(u=u, equilibrium=eq, tangent_fd=[], input_fd=[])
        result['baselines'].append(row)
        if not eq['success'] or eq['residual_norm'] >= v['tolerances']['residual_nm2']:
            continue
        q = eq['q']; t = terms(q,u); row['terms'] = t
        row['tendon_tangent'] = t['Rq']-t['A0']
        row['static_call_seconds'] = []
        for _ in range(v['repeated_calls']):
            start = perf_counter(); terms.static(q,u)
            row['static_call_seconds'].append(perf_counter()-start)
        for h in cfg['fd_steps_rad_m']:
            start = perf_counter(); matrix = fd(lambda x: terms.static(x,u)['R'],q,h)
            row['tangent_fd'].append(dict(step=h, Rq=matrix, seconds=perf_counter()-start))
        start = perf_counter(); dqdu = -np.linalg.solve(t['Rq'],t['Ru'])
        row['dqdu'] = dqdu; row['dpdu'] = t['J']@dqdu
        row['omitted_dpdu'] = -t['J']@np.linalg.solve(t['A0'],t['Ru'])
        row['input_ift_seconds'] = perf_counter()-start
        row['linear_solve_relative'] = maxabs(t['Rq']@dqdu+t['Ru'])/maxabs(t['Ru'])
        for h in v['input_steps_n']:
            qs = []; ps = []; solves = []
            for a in range(len(u)):
                pair = []
                for sign in (-1,1):
                    up = u.copy(); up[a] += sign*h
                    sol = v2_solve(terms,cfg,q,up); sol['u'] = up; solves.append(sol); pair.append(sol)
                qs.append((pair[1]['q']-pair[0]['q'])/(2*h))
                ps.append((pair[1]['p']-pair[0]['p'])/(2*h))
            row['input_fd'].append(dict(step_n=h,dqdu=np.array(qs).T,dpdu=np.array(ps).T,solves=solves,
                Ru=fd(lambda up: terms.static(q,up)['R'],u,h)))
    base = result['baselines'][0]
    if 'terms' not in base:
        return result
    q = base['equilibrium']['q']; p = base['equilibrium']['p']; u = base['u']; t = base['terms']
    for param in v['design_parameters']:
        key,ix = param['key'],param['index']
        value = cfg[key] if ix < 0 else model[key][ix]
        row = dict(parameter=param,value=value,partials=[],predictions=[])
        for fraction in sorted(set(v['partial_relative_steps']+v['prediction_relative_steps'])):
            delta = fraction*value; pair = []; partial_terms = []; build_times = []; partial_times = []
            for sign in (-1,1):
                c,m = copy.deepcopy(cfg),copy.deepcopy(model)
                if ix < 0: c[key] = value+sign*delta
                else: m[key][ix] = value+sign*delta
                start = perf_counter(); _,_,changed = build(c,m,level,v2=True)
                build_times.append(perf_counter()-start)
                start = perf_counter(); partial_terms.append(changed(q,u)); partial_times.append(perf_counter()-start)
                if fraction in v['prediction_relative_steps']:
                    pair.append(v2_solve(changed,c,q,u))
            if fraction in v['partial_relative_steps']:
                start = perf_counter()
                rd = (partial_terms[1]['R']-partial_terms[0]['R'])/(2*delta)
                pd = (partial_terms[1]['p']-partial_terms[0]['p'])/(2*delta)
                dq = -np.linalg.solve(t['Rq'],rd); dp = pd+t['J']@dq
                row['partials'].append(dict(fraction=fraction,Rd=rd,pd=pd,dqdd=dq,dpdd=dp,
                                            ift_seconds=perf_counter()-start,build_seconds=build_times,
                                            evaluation_seconds=partial_times))
            if pair:
                dp = np.ravel(row['partials'][0]['dpdd'])
                for sign,sol in zip((-1,1),pair):
                    row['predictions'].append(dict(fraction=fraction,delta=sign*delta,
                        predicted=sign*delta*dp,actual=sol['p']-p,solve=sol,build_seconds=build_times))
        result['designs'].append(row)
    result['elapsed_seconds'] = perf_counter()-start_all
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', required=True, choices=['one_segment','two_segment'])
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--v2', action='store_true')
    args = parser.parse_args()
    cfg = json.loads((HERE/'cases.json').read_text())
    model = next(c for c in cfg['cases'] if c['id']==args.case)
    args.output.mkdir(parents=True, exist_ok=True)
    prov = provenance(cfg)
    target = args.output/f'gvs_{args.case}.json'
    if target.exists():
        raise FileExistsError(f'Preserve evidence: {target}')
    result = (run_v2 if args.v2 else run)(cfg,model); result['environment'] = prov
    result['source_sha'] = subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    write_json(target, result)
