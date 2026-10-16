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


def v2_checks(data, cfg):
    """Recompute gates from raw matrices, solved perturbations and frozen bounds."""
    v = cfg['v2']; tol = v['tolerances']; failures = []; metrics = []
    model = next(c for c in cfg['cases'] if c['id']==data['case_id']); n = 4*len(model['lengths_m'])
    def gate(label, value, bound):
        if not np.isfinite(value) or value > bound:
            failures.append(dict(quantity=label,error=float(value),tolerance=bound))
    def vector(obj, key, size):
        x = array(obj,key).ravel()
        if x.shape != (size,): raise ValueError(f'Wrong dimension: {key}')
        return x
    def matrix(obj,key,shape):
        x = array(obj,key)
        if x.shape != shape: raise ValueError(f'Wrong dimension: {key}')
        return x
    def relative(a,b):
        return float(np.max(np.abs(a-b))/max(np.max(np.abs(a)),1e-30))
    def solved(sol, reference=None):
        gate('solver_status',0 if sol['success'] and sol['status']>0 else 1,0)
        gate('solver_residual',max(sol['residual_norm'],np.max(np.abs(vector(sol,'R',n)))),tol['residual_nm2'])
        gate('condition',sol['condition'],tol['condition_max'])
        q = vector(sol,'q',n); vector(sol,'p',3)
        if reference is not None:
            gate('local_branch_guard',np.linalg.norm(q-reference)/max(1,np.linalg.norm(reference)),tol['branch_relative_q'])
        if 'u' in sol:
            u = vector(sol,'u',4); lo,hi = v['tension_bounds_n']
            gate('tension_bound',max(lo-u.min(),u.max()-hi,0),0)
    if data['units'] != v['units']: raise ValueError('Wrong derivative units')
    if len(data['baselines']) != len(v['baseline_tensions_n']): raise ValueError('Missing baselines')
    for b,row in enumerate(data['baselines']):
        solved(row['equilibrium']); q = vector(row['equilibrium'],'q',n)
        if 'terms' not in row: failures.append(dict(quantity='unusable_equilibrium')); continue
        np.testing.assert_array_equal(vector(row,'u',4),v['baseline_tensions_n'][b])
        t = row['terms']; A = matrix(t,'Rq',(n,n)); A0 = matrix(t,'A0',(n,n)); Ru = matrix(t,'Ru',(n,4))
        J = matrix(t,'J',(3,n)); vector(t,'R',n); vector(t,'p',3)
        gate('genuinely_curved',0 if np.linalg.norm(q)>0.1 else 1,0)
        gate('nonzero_chord_tangent',0 if np.max(np.abs(A-A0))>1e-10 else 1,0)
        gate('symmetry',relative(A,A.T),tol['symmetry_relative'])
        dq = matrix(row,'dqdu',(n,4)); dp = matrix(row,'dpdu',(3,4))
        gate('input_ift',relative(Ru,-A@dq),tol['linear_solve_relative'])
        gate('input_chain_rule',relative(dp,J@dq),tol['linear_solve_relative'])
        if len(row['tangent_fd'])!=len(cfg['fd_steps_rad_m']) or len(row['input_fd'])!=len(v['input_steps_n']):
            raise ValueError('Missing derivative steps')
        for step,h in zip(row['tangent_fd'],cfg['fd_steps_rad_m'],strict=True):
            if step['step'] != h: raise ValueError('Wrong tangent step')
            F = matrix(step,'Rq',(n,n)); absolute = float(np.max(np.abs(F-A)))
            gate('tangent_abs',absolute,tol['tangent_abs_nm3']); gate('tangent_relative',relative(A,F),tol['tangent_relative'])
            metrics.append(dict(baseline=b,step=h,tangent_abs=absolute,tangent_relative=relative(A,F),
                                omitted_tangent_relative=relative(A,F-(A-A0))))
        for step,h in zip(row['input_fd'],v['input_steps_n'],strict=True):
            if step['step_n']!=h or len(step['solves'])!=8: raise ValueError('Wrong input probes')
            gate('Ru_fd',relative(Ru,matrix(step,'Ru',(n,4))),tol['sensitivity_relative'])
            measured_q = np.zeros((n,4)); measured_p = np.zeros((3,4))
            for a in range(4):
                minus,plus = step['solves'][2*a:2*a+2]
                for sign,sol in zip((-1,1),(minus,plus)):
                    solved(sol,q); expected = np.asarray(row['u']).ravel().copy(); expected[a] += sign*h
                    np.testing.assert_allclose(vector(sol,'u',4),expected,rtol=0,atol=1e-15)
                measured_q[:,a] = (vector(plus,'q',n)-vector(minus,'q',n))/(2*h)
                measured_p[:,a] = (vector(plus,'p',3)-vector(minus,'p',3))/(2*h)
            gate('stored_input_q_fd',relative(measured_q,matrix(step,'dqdu',(n,4))),1e-12)
            gate('stored_input_tip_fd',relative(measured_p,matrix(step,'dpdu',(3,4))),1e-12)
            gate('input_q_fd',relative(dq,measured_q),tol['sensitivity_relative'])
            gate('input_tip_fd',np.max(np.abs(dp-measured_p)),tol['input_tip_abs_m_n'])
            gate('input_tip_relative',relative(dp,measured_p),tol['sensitivity_relative'])
    if 'designs' not in data or len(data['designs'])!=len(v['design_parameters']):
        failures.append(dict(quantity='missing_designs')); return dict(passed=False,failures=failures,metrics=metrics)
    base = data['baselines'][0]; q = vector(base['equilibrium'],'q',n); p = vector(base['equilibrium'],'p',3)
    A = array(base['terms'],'Rq'); J = array(base['terms'],'J')
    for design,param in zip(data['designs'],v['design_parameters'],strict=True):
        if design['parameter']!=param or len(design['partials'])!=2 or len(design['predictions'])!=4:
            raise ValueError('Wrong design probes')
        expected_value = cfg[param['key']] if param['index']<0 else model[param['key']][param['index']]
        if design['value']!=expected_value: raise ValueError('Wrong physical parameter value')
        part = design['partials'][0]; dq = vector(part,'dqdd',n); dp = vector(part,'dpdd',3)
        for item,fraction in zip(design['partials'],v['partial_relative_steps'],strict=True):
            if item['fraction']!=fraction: raise ValueError('Wrong partial step')
            rd = vector(item,'Rd',n); pd = vector(item,'pd',3); dqi = vector(item,'dqdd',n); dpi = vector(item,'dpdd',3)
            gate('design_ift',relative(rd,-A@dqi),tol['linear_solve_relative'])
            gate('explicit_design_chain_rule',relative(dpi,pd+J@dqi),tol['linear_solve_relative'])
            gate('design_partial_step_stability',relative(dp,dpi),tol['sensitivity_relative'])
        for i,fraction in enumerate(v['prediction_relative_steps']):
            pair = design['predictions'][2*i:2*i+2]; delta = fraction*design['value']
            for sign,pred in zip((-1,1),pair):
                if pred['delta']!=sign*delta or pred['fraction']!=fraction: raise ValueError('Wrong physical delta')
                solved(pred['solve'],q); actual = vector(pred['solve'],'p',3)-p; expected = sign*delta*dp
                gate('stored_actual',np.max(np.abs(vector(pred,'actual',3)-actual)),1e-14)
                gate('stored_prediction',np.max(np.abs(vector(pred,'predicted',3)-expected)),1e-14)
                err = float(np.max(np.abs(actual-expected))); scale = float(np.max(np.abs(actual)))
                gate('prediction',err,tol['prediction_abs_m']+tol['prediction_relative']*scale)
                meaningful = np.abs(actual)>tol['direction_floor_m']
                gate('prediction_direction',int(np.any(expected[meaningful]*actual[meaningful]<=0)),0)
                metrics.append(dict(parameter=param['key'],fraction=sign*fraction,prediction_abs_m=err,
                                    prediction_relative=err/max(scale,1e-30)))
            measured_q = (vector(pair[1]['solve'],'q',n)-vector(pair[0]['solve'],'q',n))/(2*delta)
            measured_p = (vector(pair[1]['solve'],'p',3)-vector(pair[0]['solve'],'p',3))/(2*delta)
            gate('design_q_fd',relative(dq,measured_q),tol['sensitivity_relative'])
            gate('design_tip_fd',relative(dp,measured_p),tol['sensitivity_relative'])
    return dict(passed=not failures,failures=failures,metrics=metrics)


def compare_v2(directory, case_id, cfg):
    data = {name:json.loads((directory/f'{name}_{case_id}.json').read_text(encoding='utf-8')) for name in ('gvs','matlab')}
    result = dict(tolerances=cfg['v2']['tolerances'],checks={name:v2_checks(d,cfg) for name,d in data.items()},cross=[])
    tol = cfg['v2']['tolerances']; g,m = data.values()
    for a,b in zip(g['baselines'],m['baselines'],strict=True):
        row = dict(tip_m=float(np.linalg.norm(array(a['equilibrium'],'p').ravel()-array(b['equilibrium'],'p').ravel())),
                   q_rad_m=error(a['equilibrium'],b['equilibrium'],'q'),tangent_abs_nm3=error(a['terms'],b['terms'],'Rq'),
                   input_relative=error(a,b,'dpdu')/np.max(np.abs(array(a,'dpdu'))))
        result['cross'].append(row)
    for a,b in zip(g['designs'],m['designs'],strict=True):
        result['cross'].append(dict(design=a['parameter']['key'],design_relative=error(a['partials'][0],b['partials'][0],'dpdd')/
                                   np.max(np.abs(array(a['partials'][0],'dpdd')))))
    bounds = dict(tip_m=tol['cross_tip_m'],q_rad_m=tol['cross_q_rad_m'],tangent_abs_nm3=tol['cross_tangent_abs_nm3'],
                  input_relative=tol['cross_sensitivity_relative'],design_relative=tol['cross_sensitivity_relative'])
    result['passed'] = all(c['passed'] for c in result['checks'].values()) and all(
        np.isfinite(value) and value<=bounds[key] for row in result['cross'] for key,value in row.items() if key in bounds)
    (directory/f'comparison_{case_id}.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
    if not result['passed']: raise SystemExit('V2 gate failed; retain evidence and inspect failures.')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case',required=True,choices=['one_segment','two_segment'])
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--v2',action='store_true')
    args = p.parse_args()
    (compare_v2 if args.v2 else compare)(args.output,args.case,json.loads((HERE/'cases.json').read_text()))
