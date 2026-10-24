"""Mass-only diagnostic: Mr(q) qdd = original GVS Fg(x,u); never a production model.

Reuse S146's bounded native evaluator, readouts, lifecycle and Store audit.
Two root solves only; the incompatible original velocity bias stays unchanged.
"""
import argparse
from pathlib import Path
import sys
import time
import traceback

import casadi as ca
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO))
from s145_gvs_prediction_diagnosis import maxabs,norm,read
from s146_constrained_dynamics import Experiment as ConstrainedExperiment,VirtualWork
from extensions.tendon_family.gvs_trajectory import implicit_step_residual


class MassOnly(VirtualWork):
    """Reuse the numerical mass callback, discard its force, retain symbolic Fg."""
    def __init__(self,name,evaluate,scales,implicit_terms):
        super().__init__(name,evaluate,scales)
        self.gvs_terms = implicit_terms

    def implicit_residual(self,x,u,acceleration):
        mass,_discarded = self(x/self.scales,u)
        _original_mass,force = self.gvs_terms(x,u)
        return mass @ acceleration-force


def check_wiring():
    """Synthetic fixture: native force is deliberately wrong and must be ignored."""
    scales = np.r_[np.full(12,10.),np.full(12,1000.)]
    mass = np.diag(np.linspace(1.,2.,12))*1e-6
    x,u = ca.MX.sym('fixture_x',24),ca.MX.sym('fixture_u',6)
    force = -ca.DM(np.linspace(1.,2.,12)*1e-3)*x[:12]-.0001*x[12:]+u[0]
    terms = ca.Function('fixture_gvs_terms',[x,u],[2*ca.DM(mass),force])
    callback = MassOnly('fixture_mass_only',lambda xx,uu:(mass,np.full(12,999.)),scales,terms)
    residual = implicit_step_residual(callback,12,6,.01,'implicit_euler')
    z,old = ca.MX.sym('fixture_z',24),ca.MX.sym('fixture_old',24)
    y = z*scales
    actual = residual(old,y,u)
    expected = ca.vertcat((y[:12]-old[:12]-.01*y[12:])/10.,
        (ca.DM(mass) @ ((y[12:]-old[12:])/.01)-terms(y,u)[1])/.001)
    test = ca.Function('mass_only_wiring',[z,old,u],
        [actual-expected,ca.jacobian(actual,z)-ca.jacobian(expected,z)],{'ad_weight':1.})
    error,jac_error = (np.asarray(v) for v in test(np.linspace(-.02,.03,24),
                                                  np.linspace(.1,.2,24),np.arange(6)/10.))
    assert maxabs(error)<1e-12 and maxabs(jac_error)<1e-5
    print('SYNTHETIC MASS-ONLY WIRING PASS',maxabs(error),maxabs(jac_error),flush=True)


class Experiment(ConstrainedExperiment):
    def __init__(self,output):
        super().__init__(output)
        self.reference = read(REPO.parent/'s146-constrained-dynamics/runs/s146/result.json')
        self.mass_archive = read(REPO.parent/'s147-mass-matrix-diagnosis/runs/s147/result.json')
        assert self.reference['status']=='completed'
        assert self.reference['physics_identity']==self.mass_archive['physics_identity']==self.d.physics['identity']
        assert self.reference['basis']==self.mass_archive['basis']==self.d.basis.model_dump(mode='json')
        self.ledger.update(mass_root=0,gvs_implicit_terms=0,independent_mass_residual=0)
        self.result['protocol'].update(model='Mr(q) qdd = unchanged GVS Fg(x,u)',
            native_force_discarded=True,physically_self_consistent=False,
            stop_after_two_intervals=True)
        self.result['reference_results'] = str(REPO.parent/'s146-constrained-dynamics/runs/s146/result.json')

    def terms(self,x,u):
        mass,_native_force = super().terms(x,u)  # Includes the inherited 1600-call limit.
        self.trace[-1]['discarded_native_force_norm_nm2'] = self.trace[-1].pop('reduced_force_norm_nm2')
        return mass,np.zeros(12)  # Auxiliary output unused by MassOnly.

    def force_audit(self,x,u):
        functions = self.d.functions
        mg,fg = (np.asarray(v) for v in functions.implicit_terms(x,u))
        self.ledger['gvs_implicit_terms'] += 1
        fg = fg.ravel()
        explicit = {k:np.asarray(v).squeeze() for k,v in functions.evaluate(x,u).items()}
        self.ledger['gvs_dynamics'] += 1
        # Check the production definition; this sum is never used as a model evaluator.
        expected = (explicit['tendon_generalized_force']+explicit['gravity_force']-
                    explicit['velocity_bias']-explicit['elastic_force']-explicit['damping_force'])
        original_zero_acceleration = np.asarray(functions.implicit_residual(x,u,np.zeros(12))).ravel()
        self.ledger['gvs_implicit_residual'] += 1
        checks = dict(force_definition_max_nm2=maxabs(fg-expected),
            implicit_zero_acceleration_max_nm2=maxabs(original_zero_acceleration+fg),
            mass_definition_max_kg_m4=maxabs(mg-explicit['mass_matrix']))
        assert max(checks.values())<1e-12
        return mg,fg,checks

    def interval(self,start_index):
        d = self.d
        before,after = d.rows[start_index],d.rows[start_index+1]
        initial,c = self.projected(before),self.projected(after)
        ref = next(e for e in self.reference['intervals'] if abs(e['interval_s'][0]-before['time_s'])<1e-12)
        record = d.updates[start_index+1]['complete_update_record']
        u,scales = np.asarray(after['tension_n']),np.asarray(record['state_scales'])
        assert after['tension_n']==ref['actual_tension_n']==record['actual_applied_action_n']
        assert record['tendon_order']==ref['tendon_order']
        assert np.array_equal(initial,np.asarray(ref['initial_state']))
        assert np.array_equal(c,np.asarray(ref['C_state']))
        assert maxabs(initial-record['measured_state'])<1e-10
        assert np.array_equal(initial/scales,np.asarray(ref['scaled_initial_guess']))
        assert np.array_equal(scales,np.r_[np.full(12,10.),np.full(12,1000.)])
        for key,value in (('h_s',.01),('abstol',1e-10),('max_iter',30),('method','implicit_euler')):
            assert self.reference['protocol'][key]==value
        assert d.spec['effective_parameters']['integration_method']=='implicit_euler'
        assert d.spec['effective_parameters']['root_tolerance']==1e-10
        assert d.spec['effective_parameters']['substeps']==1
        self.sample_time = after['engine_time_s']
        calls_before = self.ledger['virtual_work_evaluations']
        mr,_ = self.terms(initial,u)
        mg,fg,checks = self.force_audit(initial,u)
        archive = next(s for s in self.mass_archive['states'] if abs(s['time_s']-before['time_s'])<1e-12)
        assert maxabs(mr-np.asarray(archive['discrete']))<1e-17
        assert maxabs(mg-np.asarray(archive['continuum']))<1e-17
        callback = MassOnly('s148_mass_'+str(start_index),self.terms,scales,d.functions.implicit_terms)
        residual = implicit_step_residual(callback,12,6,.01,'implicit_euler')
        y,old,uu = ca.MX.sym('next',24),ca.MX.sym('old',24),ca.MX.sym('u',6)
        scaled = ca.Function('s148_residual_'+str(start_index),[y,old,uu],
            [residual(old,y*scales,uu)],{'ad_weight':1.})
        solver = ca.rootfinder('s148_step_'+str(start_index),'newton',scaled,
            {'abstol':1e-10,'max_iter':30,'error_on_fail':True})
        entry = dict(interval_s=ref['interval_s'],actual_tension_n=u,tendon_order=ref['tendon_order'],
            initial_state=initial,scaled_initial_guess=initial/scales,C_state=c,
            G_state=ref['A_state'],G_source=ref['A_source'],R_state=ref['B_state'],
            force_audit=checks,initial_gvs_force_nm2=fg,
            G_max_scaled_residual=ref['A_max_scaled_residual'],R_max_scaled_residual=ref['max_scaled_residual'])
        self.result['intervals'].append(entry)
        assert self.ledger['mass_root']<2
        self.ledger['mass_root'] += 1
        self.save()
        started = time.perf_counter()
        try:
            m = np.asarray(solver(initial/scales,initial,u)).ravel()*scales
        except RuntimeError as error:
            entry.update(status='root_failed',error=str(error),traceback=traceback.format_exc(),
                         root_stats=solver.stats(),root_wall_s=time.perf_counter()-started)
            raise
        entry.update(root_stats=solver.stats(),root_wall_s=time.perf_counter()-started)
        assert entry['root_stats']['success'] and entry['root_stats']['iter_count']<=30
        mr,_ = self.terms(m,u)
        _,force = (np.asarray(v) for v in d.functions.implicit_terms(m,u))
        self.ledger['gvs_implicit_terms'] += 1
        independent = np.r_[(m[:12]-initial[:12]-.01*m[12:])/10.,
                           (mr @ ((m[12:]-initial[12:])/.01)-force.ravel())/.001]
        self.ledger['independent_mass_residual'] += 1
        graph_defect = np.asarray(residual(initial,m,u)).ravel()
        assert np.isfinite(m).all() and maxabs(independent)<1e-10
        assert maxabs(graph_defect-independent)<1e-12
        states = dict(G=np.asarray(ref['A_state']),M=m,R=np.asarray(ref['B_state']),C=c)
        readouts = {name:self.readout(x) for name,x in states.items()}
        for name,old_name in (('G','A'),('R','B'),('C','C')):
            for key,value in readouts[name].items():
                assert maxabs(value-np.asarray(ref['readouts'][old_name][key]))<1e-14
        errors = {}
        for name in ('G','M','R'):
            delta = states[name]-c
            error = dict(q_norm_rad_m=norm(delta[:12]),rate_norm_rad_m_s=norm(delta[12:]),
                         q_error_rad_m=delta[:12],rate_error_rad_m_s=delta[12:])
            for model in ('gvs','discrete'):
                velocity = readouts[name][model+'_velocity_m_s']
                error[model+'_velocity_vs_C_m_s'] = velocity-readouts['C'][model+'_velocity_m_s']
                error[model+'_velocity_vs_C_norm_m_s'] = norm(error[model+'_velocity_vs_C_m_s'])
                error[model+'_velocity_vs_actual_norm_m_s'] = norm(velocity-after['tip_velocity_m_s'])
            errors[name] = error
        metrics = ('q_norm_rad_m','rate_norm_rad_m_s','gvs_velocity_vs_C_norm_m_s','discrete_velocity_vs_C_norm_m_s')
        ratios = {k:errors['M'][k]/errors['G'][k] for k in metrics}
        entry.update(status='converged',M_state=m,errors=errors,readouts=readouts,
            actual_tip_velocity_m_s=after['tip_velocity_m_s'],M_over_G_errors=ratios,
            clear_improvement=all(v<=.8 for v in ratios.values()),
            independent_scaled_residual=independent,max_scaled_residual=maxabs(independent),
            numerical_evaluations=self.ledger['virtual_work_evaluations']-calls_before,
            G_minus_M_over_G_minus_R={k:(errors['G'][k]-errors['M'][k])/(errors['G'][k]-errors['R'][k]) for k in metrics})
        print('INTERVAL',entry['interval_s'],'M/G ratios',ratios,
              'stats',entry['root_stats'],'evaluations',entry['numerical_evaluations'],flush=True)
        self.save()


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-wiring',action='store_true')
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--output',type=Path,default=REPO/'runs/s148')
    args = parser.parse_args()
    if args.check_wiring:
        check_wiring()
    if args.execute:
        Experiment(args.output).run()
    if not (args.check_wiring or args.execute):
        parser.error('choose --check-wiring or --execute')
