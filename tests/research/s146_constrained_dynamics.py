"""Two saved-state virtual-work predictions; no physics steps or production changes.

Use --check-wiring for a synthetic callback/Jacobian check, then --execute once.
Raw numerical evidence stays in ignored runs/s146; source worktrees are read-only.
"""
import argparse
from pathlib import Path
import sys
import time
import traceback

import casadi as ca
import mujoco
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from s145_gvs_prediction_diagnosis import Diagnosis, audit, maxabs, norm, read, write
from extensions.tendon_family.gvs_projection import discretize, project
from extensions.tendon_family.gvs_trajectory import implicit_step_residual


class VirtualWork(ca.Callback):
    """Local CasADi adapter for M_r/F_r; finite differences use scaled states."""

    def __init__(self, name, evaluate, scales):
        ca.Callback.__init__(self)
        self.evaluate_terms = evaluate
        self.scales = np.asarray(scales)
        self.construct(name, {'enable_fd': True, 'fd_method': 'forward'})

    def get_n_in(self):
        return 2

    def get_n_out(self):
        return 2

    def get_sparsity_in(self, i):
        return ca.Sparsity.dense(24 if i == 0 else 6, 1)

    def get_sparsity_out(self, i):
        return ca.Sparsity.dense(12, 12 if i == 0 else 1)

    def eval(self, args):
        x = np.asarray(args[0]).ravel() * self.scales
        u = np.asarray(args[1]).ravel()
        return list(self.evaluate_terms(x, u))

    def implicit_residual(self, x, u, acceleration):
        mass, force = self(x / self.scales, u)
        return mass @ acceleration - force


def check_wiring():
    """Fabricated linear mechanics fixture; not research evidence or a root solve."""
    scales = np.r_[np.full(12,10.), np.full(12,1000.)]
    mass = np.diag(np.linspace(1.,2.,12)) * 1e-6
    stiffness = np.linspace(1.,3.,12) * 1e-3
    damping = np.linspace(1.,2.,12) * 1e-4
    inputs = np.arange(72).reshape(12,6) * 1e-5
    def terms(x,u):
        return mass, inputs @ u-stiffness*x[:12]-damping*x[12:]
    callback = VirtualWork('synthetic_virtual_work', terms, scales)
    step = implicit_step_residual(callback,12,6,.01,'implicit_euler')
    y, old, u = ca.MX.sym('y',24), ca.MX.sym('old',24), ca.MX.sym('u',6)
    following = y*scales
    actual = step(old,following,u)
    expected = ca.vertcat((following[:12]-old[:12]-.01*following[12:])/10.,
        (ca.DM(mass) @ ((following[12:]-old[12:])/.01)-
         (ca.DM(inputs) @ u-ca.DM(stiffness)*following[:12]-ca.DM(damping)*following[12:]))/.001)
    test = ca.Function('synthetic_wiring',[y,old,u],
        [actual-expected, ca.jacobian(actual,y)-ca.jacobian(expected,y)], {'ad_weight':1.})
    error, derivative_error = test(np.linspace(-.02,.03,24),np.linspace(.1,.2,24),np.arange(6)/10.)
    assert maxabs(np.asarray(error)) < 1e-12
    assert maxabs(np.asarray(derivative_error)) < 1e-5
    print('SYNTHETIC WIRING PASS',maxabs(np.asarray(error)),maxabs(np.asarray(derivative_error)))


class Experiment:
    def __init__(self, output):
        self.output = output.resolve()
        source = REPO.parent/'s142-reach-hold-autonomous/runs/research/s142-reach-hold-coldstart-20261023'
        paired = REPO.parent/'s144-terminal-control-diagnosis/runs/s144'
        self.d = Diagnosis(source.resolve(),paired.resolve(),self.output)
        self.s145 = read(REPO.parent/'s145-gvs-prediction-diagnosis/runs/s145/verified/result.json')
        assert self.s145['physics_identity'] == self.d.physics['identity']
        self.ledger = self.d.ledger
        self.ledger.update(constrained_root=0, virtual_work_evaluations=0,
                           project=0, discretize=0, finite_difference_fixture_root=0)
        self.result = self.d.result
        self.result.update(intervals=[], evaluation_trace=[], protocol=dict(
            h_s=.01, method='implicit_euler', root='casadi.newton', abstol=1e-10,
            max_iter=30, error_on_fail=True, fd_method='forward', max_forward_evaluations=1600,
            kinematic_residual_scale=10., force_residual_scale=.001,
            primary_start_s=.34, independent_start_s=.33,
            clear_improvement_rule='at least 20% lower q/rate error and same-readout endpoint-projection velocity error in both intervals'))
        self.trace = self.result['evaluation_trace']
        self.mass = np.empty((48,48))
        self.sample_time = None
        m = self.d.model
        assert m.neq == 0 and m.na == 0
        assert not np.any(m.dof_frictionloss) and not np.any(m.dof_armature)
        assert np.all(m.actuator_gainprm[self.d.aids,0] == -1)
        assert np.all(m.actuator_gear[self.d.aids,0] == 1)
        assert m.actuator_trnid[self.d.aids,0].tolist() == self.d.tids
        self.result['mapping'] = dict(rank=int(np.linalg.matrix_rank(self.d.mapping)),
            shape=self.d.mapping.shape, condition_number=float(np.linalg.cond(self.d.mapping)))
        assert self.result['mapping']['rank'] == 12

    def terms(self, x, u):
        """Virtual work after reconstructing qpos/qvel; never uses P @ qacc."""
        if self.ledger['virtual_work_evaluations'] >= 1600:
            raise RuntimeError('S146_ZERO_STEP_DYNAMICS_BUDGET_EXHAUSTED')
        self.ledger['virtual_work_evaluations'] += 1
        m, d, t = self.d.model, self.d.data, self.d.mapping
        d.time = self.sample_time
        d.qpos[self.d.qi] = t @ x[:12]
        d.qvel[self.d.vi] = t @ x[12:]
        d.ctrl[self.d.aids] = u
        assert np.isfinite(x).all() and np.isfinite(u).all()
        mujoco.mj_forward(m,d)
        self.ledger['mujoco_forward'] += 1
        assert d.time == self.sample_time and d.ncon == d.nefc == 0
        assert maxabs(d.qfrc_constraint) == 0
        assert maxabs(d.qfrc_applied) == 0 and maxabs(d.xfrc_applied) == 0
        assert all(w.number == 0 for w in d.warning)
        assert maxabs(-d.actuator_force[self.d.aids]-u) < 1e-12
        mujoco.mj_fullM(m,d,self.mass)
        self.ledger['mujoco_full_mass'] += 1
        mass = self.mass[np.ix_(self.d.vi,self.d.vi)]
        force = (d.qfrc_actuator+d.qfrc_passive-d.qfrc_bias)[self.d.vi]
        balance = maxabs(mass @ d.qacc[self.d.vi]-force)
        assert balance < 1e-10
        mr = t.T @ mass @ t
        fr = t.T @ force
        assert maxabs(mr-mr.T) < 1e-18
        eigenvalues = np.linalg.eigvalsh(mr)
        assert eigenvalues[0] > 0
        self.trace.append(dict(call=self.ledger['virtual_work_evaluations'],
            sample_time_s=self.sample_time, mass_condition_number=float(eigenvalues[-1]/eigenvalues[0]),
            min_mass_eigenvalue_kg_m4=float(eigenvalues[0]),
            full_force_balance_max_nm=balance, reduced_force_norm_nm2=norm(fr)))
        return mr,fr

    def projected(self, row):
        p = project(self.d.physics,self.d.basis,row['qpos_rad'],row['qvel_rad_s'])
        self.ledger['project'] += 1
        x = np.r_[p['q_gvs'],p['qdot_gvs']]
        q,v = discretize(self.d.physics,self.d.basis,x[:12],x[12:])
        self.ledger['discretize'] += 1
        assert maxabs(q-self.d.mapping @ x[:12]) < 1e-14
        assert maxabs(v-self.d.mapping @ x[12:]) < 1e-14
        return x

    def readout(self, x):
        gp,gv = self.d.motion(x)
        dp,jac = self.d.position(self.d.mapping @ x[:12],self.d.mapping @ x[12:])
        return dict(gvs_position_m=gp,gvs_velocity_m_s=gv,
                    discrete_position_m=dp,discrete_velocity_m_s=jac @ (self.d.mapping @ x[12:]))

    def interval(self, start_index):
        d = self.d
        before,after = d.rows[start_index],d.rows[start_index+1]
        initial,endpoint = self.projected(before),self.projected(after)
        record = d.updates[start_index+1]['complete_update_record']
        u = np.asarray(after['tension_n'])
        assert maxabs(initial-record['measured_state']) < 1e-10
        assert after['tension_n'] == record['actual_applied_action_n']
        assert after['tension_n'] == d.commands[start_index+1]['desired_tension_n']
        assert record['tendon_order'] == [t['entity'] for t in d.physics['tendons']]
        scales = np.asarray(record['state_scales'])
        assert np.array_equal(scales,np.r_[np.full(12,10.),np.full(12,1000.)])
        assert d.spec['effective_parameters']['root_tolerance'] == 1e-10
        assert d.spec['effective_parameters']['integration_method'] == 'implicit_euler'
        assert d.spec['effective_parameters']['substeps'] == 1
        if start_index == 33:
            a = np.asarray(d.paired['predictions']['A']['one']['state'])
            assert after['tension_n'] == d.paired['A']['actual_tension_n']
            source = 'S144 A root prediction'
        else:
            saved = d.updates[start_index+1]['one_step_prediction']
            assert saved['applied_tension_n'] == after['tension_n']
            assert abs(saved['time_s']-after['time_s']) < 1e-12
            a = np.asarray(saved['state'])
            source = 'S142 accepted-plan prediction'
        self.sample_time = after['engine_time_s']
        calls_before = self.ledger['virtual_work_evaluations']
        # One same-state check against archived S145 virtual-work acceleration.
        mr,fr = self.terms(initial,u)
        archive = next(z for z in self.s145['mechanics'] if abs(z['time_s']-before['time_s']) < 1e-12)
        assert maxabs(mr-np.asarray(archive['represented']['mass_matrix'])) < 1e-18
        qdd = np.linalg.solve(mr,fr)
        assert maxabs(qdd-np.asarray(archive['represented']['constrained_qacc_rad_m_s2'])) < 1e-6
        assert maxabs(mr @ qdd-fr) < 1e-12
        callback = VirtualWork('s146_terms_'+str(start_index),self.terms,scales)
        residual = implicit_step_residual(callback,12,6,.01,'implicit_euler')
        y,old,uu = ca.MX.sym('scaled_next',24),ca.MX.sym('previous',24),ca.MX.sym('tension',6)
        scaled = ca.Function('s146_residual_'+str(start_index),[y,old,uu],
            [residual(old,y*scales,uu)],{'ad_weight':1.})
        solver = ca.rootfinder('s146_step_'+str(start_index),'newton',scaled,
            {'abstol':1e-10,'max_iter':30,'error_on_fail':True})
        entry = dict(interval_s=[before['time_s'],after['time_s']],
            actual_tension_n=u,tendon_order=record['tendon_order'],initial_state=initial,
            A_state=a,A_source=source,C_state=endpoint,
            initial_virtual_work_qdd_rad_m_s2=qdd,scaled_initial_guess=initial/scales)
        self.result['intervals'].append(entry)
        self.ledger['constrained_root'] += 1
        self.save()
        start = time.perf_counter()
        try:
            b = np.asarray(solver(initial/scales,initial,u)).ravel()*scales
        except RuntimeError as error:
            entry.update(status='root_failed',error=str(error),traceback=traceback.format_exc(),
                         root_stats=solver.stats(),root_wall_s=time.perf_counter()-start)
            raise
        entry.update(root_wall_s=time.perf_counter()-start,root_stats=solver.stats())
        assert entry['root_stats']['success']
        assert entry['root_stats']['iter_count'] <= 30
        defect = np.asarray(residual(initial,b,u)).ravel()
        assert np.isfinite(b).all() and maxabs(defect) < 1e-10
        a_defect = np.asarray(implicit_step_residual(d.functions,12,6,.01,'implicit_euler')(initial,a,u)).ravel()
        self.ledger['gvs_implicit_residual'] += 1
        entry.update(status='converged',B_state=b,scaled_residual=defect,
            max_scaled_residual=maxabs(defect),A_max_scaled_residual=maxabs(a_defect),
            numerical_evaluations=self.ledger['virtual_work_evaluations']-calls_before,
            kinematic_defect_rad_m=maxabs(b[:12]-initial[:12]-.01*b[12:]))
        # The same output model is used on A, B, C in each comparison.
        readouts = {name:self.readout(x) for name,x in [('A',a),('B',b),('C',endpoint)]}
        entry['readouts'] = readouts
        errors = {}
        for name,x in [('A',a),('B',b)]:
            errors[name] = dict(q_norm_rad_m=norm(x[:12]-endpoint[:12]),
                rate_norm_rad_m_s=norm(x[12:]-endpoint[12:]),
                q_scaled_norm=norm((x[:12]-endpoint[:12])/scales[:12]),
                rate_scaled_norm=norm((x[12:]-endpoint[12:])/scales[12:]),
                q_error_rad_m=x[:12]-endpoint[:12],rate_error_rad_m_s=x[12:]-endpoint[12:])
            for model in ('gvs','discrete'):
                velocity = readouts[name][model+'_velocity_m_s']
                target = readouts['C'][model+'_velocity_m_s']
                errors[name][model+'_velocity_vs_C_m_s'] = velocity-target
                errors[name][model+'_velocity_vs_C_norm_m_s'] = norm(velocity-target)
                errors[name][model+'_velocity_vs_actual_norm_m_s'] = norm(velocity-after['tip_velocity_m_s'])
        entry.update(errors=errors,actual_tip_velocity_m_s=after['tip_velocity_m_s'])
        metrics = ('q_norm_rad_m','rate_norm_rad_m_s','gvs_velocity_vs_C_norm_m_s','discrete_velocity_vs_C_norm_m_s')
        entry['B_over_A_errors'] = {key:errors['B'][key]/errors['A'][key] for key in metrics}
        entry['clear_improvement'] = all(ratio <= .8 for ratio in entry['B_over_A_errors'].values())
        print('INTERVAL',entry['interval_s'],'ratios',entry['B_over_A_errors'],
              'stats',entry['root_stats'],'evaluations',entry['numerical_evaluations'],flush=True)
        self.save()

    def save(self):
        write(self.output/'result.json',self.result)

    def run(self):
        # Prevent accidental repeated use of the two-root budget in this run folder.
        with (self.output/'started.json').open('x',encoding='utf8') as stream:
            stream.write('{"max_root_solves":2,"max_zero_step_dynamics":1600}')
        self.result['status'] = 'running'
        started = time.perf_counter()
        try:
            self.d.prepare_functions()
            self.interval(33)  # Primary; fixed order declared before seeing new results.
            self.interval(32)  # Independent adjacent control interval.
            self.result['status'] = 'completed'
            self.result['both_intervals_clear_improvement'] = all(z['clear_improvement'] for z in self.result['intervals'])
        except Exception:
            self.result['status'] = 'failed'
            self.result['failure_traceback'] = traceback.format_exc()
            raise  # Persist the failure, never substitute a numerical result.
        finally:
            self.result['wall_s'] = time.perf_counter()-started
            self.result['store_after'] = audit(self.d.source)
            self.result['store_unchanged'] = self.result['store_after'] == self.result['store_before']
            self.save()
            assert self.result['store_unchanged']
            print('FINAL',self.result['status'],self.ledger,'wall_s',self.result['wall_s'],flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-wiring',action='store_true')
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--output',type=Path,default=REPO/'runs/s146')
    args = parser.parse_args()
    if args.check_wiring:
        check_wiring()
    if args.execute:
        Experiment(args.output).run()
    if not (args.check_wiring or args.execute):
        parser.error('choose --check-wiring or --execute')


if __name__ == '__main__':
    main()
