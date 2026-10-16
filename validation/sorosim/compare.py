"""Evaluate declared tolerances and retain every discrepancy, including failures."""

import argparse
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def array(obj, key):
    value = np.asarray(obj[key], dtype=float)
    if not np.all(np.isfinite(value)):
        raise ValueError(f'Nonfinite mathematical evidence: {key}')
    return value


def error(a, b, key):
    left, right = array(a,key).reshape(-1), array(b,key).reshape(-1)
    if left.size != right.size:
        raise ValueError(f'Evidence dimensions disagree: {key}')
    return float(np.max(np.abs(left-right)))


def differences(a, b):
    pa, pb = array(a,'pose'), array(b,'pose')
    return dict(
        pose_position_m=float(np.linalg.norm(pa[:3,3]-pb[:3,3])),
        pose_rotation_fro=float(np.linalg.norm(pa[:3,:3]-pb[:3,:3])),
        tip_jacobian_max_abs=error(a,b,'tip_jacobian'),
        generalized_force_nm2=max(error(a,b,'gravity_force'),error(a,b,'tendon_force')),
        residual_jacobian_max_abs=error(a,b,'residual_jacobian'),
        stiffness_max_abs=error(a,b,'stiffness'),
        tendon_length_m=error(a,b,'tendon_lengths'),
        tendon_length_jacobian_max_abs=error(a,b,'tendon_length_jacobian'),
        force_map_max_abs=error(a,b,'tendon_force_map'),
        gravity_force_max_abs=error(a,b,'gravity_force'),
        residual_max_abs=error(a,b,'residual'),
    )


def checks(row, cfg, matlab=False):
    failures = []
    for i, p in enumerate(row['probes']):
        for fd in p['fd']:
            for field, tolerance in [('tip_max_abs','fd_tip_jacobian_max_abs'),
                                     ('residual_max_abs','fd_residual_jacobian_max_abs'),
                                     ('tendon_max_abs','fd_tendon_jacobian_max_abs')]:
                if fd[field] > cfg['tolerances'][tolerance]:
                    failures.append(dict(probe=i, step=fd['step_rad_m'], quantity=field,
                                         error=fd[field], tolerance=cfg['tolerances'][tolerance]))
    eq = row['equilibrium']
    assert eq['residual_norm'] < cfg['solver_residual_tolerance_nm2']
    assert eq['exitflag'] > 0 if matlab else eq['success']
    for fd in eq['sensitivity_fd']:
        flags = fd['exitflags'] if matlab else fd['statuses']
        assert np.min(flags) > 0
        assert np.max(fd['residual_norms']) < cfg['solver_residual_tolerance_nm2']
        tol = cfg['tolerances']['fd_equilibrium_tip_sensitivity_m_n']
        if fd['max_abs'] > tol:
            failures.append(dict(quantity='equilibrium_tip_sensitivity', step=fd['step_n'],
                                 error=fd['max_abs'], tolerance=tol))
    return failures


def compare(directory, case_id, cfg):
    gvs = json.loads((directory/f'gvs_{case_id}.json').read_text(encoding='utf-8'))
    matlab = json.loads((directory/f'matlab_{case_id}.json').read_text(encoding='utf-8'))
    result = dict(case_id=case_id,levels=[],tolerances=cfg['tolerances'])
    for g, m in zip(gvs['levels'],matlab['levels'],strict=True):
        assert g['setting'] == m['setting']
        row = dict(setting=g['setting'],probes=[])
        for gp,mp in zip(g['probes'],m['probes'],strict=True):
            assert np.array_equal(np.ravel(gp['q']),np.ravel(mp['q']))
            diff = differences(gp['terms'],mp['terms'])
            native = array(mp['terms'],'native_guided_tendon_force_map')
            chord = array(mp['terms'],'tendon_force_map')
            diff['native_guided_vs_chord_force_map_max_abs'] = float(np.max(np.abs(native-chord)))
            row['probes'].append(diff)
        ge, me = g['equilibrium'],m['equilibrium']
        row['equilibrium'] = differences(ge['terms'],me['terms'])
        row['equilibrium']['equilibrium_curvature_rad_m'] = error(ge,me,'q')
        row['equilibrium']['tip_sensitivity_m_n_max_abs'] = error(ge,me,'tip_sensitivity_m_n')
        row['gvs_derivative_failures'] = checks(g,cfg)
        row['matlab_derivative_failures'] = checks(m,cfg,True)
        row['numpy_kernel_check'] = g['numpy_kernel_check']
        row['gvs_cost_seconds'] = dict(build=g['build_seconds'],equilibrium=ge['seconds'],
                                      probe_mean=float(np.mean([p['seconds'] for p in g['probes']])))
        row['matlab_cost_seconds'] = dict(build=m['build_seconds'],equilibrium=me['seconds'],
                                         probe_mean=float(np.mean([p['seconds'] for p in m['probes']])))
        result['levels'].append(row)
    fine = result['levels'][-1]
    failures = []
    for i,diff in enumerate([*fine['probes'],fine['equilibrium']]):
        for key,value in diff.items():
            if key in cfg['tolerances'] and value > cfg['tolerances'][key]:
                failures.append(dict(probe_or_equilibrium=i,quantity=key,error=value,
                                     tolerance=cfg['tolerances'][key]))
    result['correspondence_failures'] = failures
    result['correspondence_pass'] = not failures
    result['derivatives_pass'] = not fine['gvs_derivative_failures'] and not fine['matlab_derivative_failures']
    result['refinement'] = []
    for name, data in [('gvs',gvs),('matlab',matlab)]:
        for a,b in zip(data['levels'],data['levels'][1:]):
            result['refinement'].append(dict(
                model=name,coarse=a['setting'],fine=b['setting'],
                equilibrium_q_max_abs=error(a['equilibrium'],b['equilibrium'],'q'),
                equilibrium_terms=differences(a['equilibrium']['terms'],b['equilibrium']['terms']),
                variable_probe_terms=differences(a['probes'][-1]['terms'],b['probes'][-1]['terms']),
            ))
    (directory/f'comparison_{case_id}.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(case_id=case_id,correspondence_pass=result['correspondence_pass'],
                          derivatives_pass=result['derivatives_pass'],
                          correspondence_failures=failures,
                          finest_equilibrium=fine['equilibrium']),indent=2))
    if not result['correspondence_pass']:
        raise SystemExit('Model correspondence not established; do not extend to the next case.')
    if not result['derivatives_pass']:
        raise SystemExit('Analytical derivative tolerances failed; see the retained discrepancies.')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case',required=True,choices=['one_segment','two_segment'])
    p.add_argument('--output',required=True,type=Path)
    args = p.parse_args()
    compare(args.output,args.case,json.loads((HERE/'cases.json').read_text()))
