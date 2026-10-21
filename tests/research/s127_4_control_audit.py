"""Read-only measured-control audit; no provider, solver or simulator dispatch."""
from copy import deepcopy
import json
import numpy as np
from tools.platform_host import Host
from tools.research.config import ROOT
from tools.research.state import state
from tools.research.control_correction import correction_basis, corrected_tensions, task_outputs, constraint_vectors
from tools.research.research_context import physical_diagnostic
from tools.research.feedback import task_gap
from tools.research_tasks import task_adapter
from tools.state_io import read, atomic_json, digest
from tests.research.test_s127_working_set import historical_host

OUT=ROOT/'evidence/s127_4_control'


def intervals(mask,times):
    indices=np.flatnonzero(mask);runs=[]
    for group in np.split(indices,np.flatnonzero(np.diff(indices)>1)+1):
        if len(group):runs.append([float(times[group[0]]),float(times[group[-1]+1])])
    return runs


def options(cfg):
    adapter=task_adapter(cfg);limits=adapter.ranking_limits()
    return dict(target=cfg['task']['goal']['data']['target_m'],holding_start=adapter.holding_start_s(),
        position_limit=limits['holding_max_error_m'],terminal_position_limit=limits['terminal_error_m'],
        speed_limit=limits['holding_max_speed_m_s'])


def audit():
    old=historical_host();experiment=read(ROOT/'evidence/s127_control_handoff/experiment.json')
    h=Host(ROOT/'runs/research'/experiment['study_id'],experiment['study_id'])
    before=[(digest(state(x)),x.store.remaining(),digest(x.store.events(x.run_id))) for x in (old,h)]
    assert state(h)['research_status']=='stopped'
    refs=state(h)['physical_replays'];base,probe=[h.store.artifact(r) for r in refs]
    source=h.store.artifact(base['source_reference']);tr=source['trajectory']
    cfg=h.store.artifact(base['candidate'])['configuration'];opt=options(cfg)
    times=np.asarray(tr['times_s']);u=np.asarray(tr['tensions_n']);channels=len(tr['tendon_order'])
    force={t['id']:t['force_limit_n'] for t in cfg['robot']['structure']['data']['tendons']}
    limits=np.asarray([force[t] for t in tr['tendon_order']]);knots=[0.,.35]
    basis=correction_basis(times[:-1],knots,channels);directions=[]
    for j in range(basis.shape[1]):
        row=dict(coefficient=j,knot_s=knots[j//channels],tendon=tr['tendon_order'][j%channels],
            sampled_support_intervals_s=intervals(abs(basis[:,j].reshape(-1,channels)).max(axis=1)>1e-12,times),
            hold_start_weight=float(np.interp(opt['holding_start'],knots,np.eye(len(knots))[j//channels])),
            perturbations=[])
        for step in (.01,-.01):
            x=np.zeros(basis.shape[1]);x[j]=step
            delta=corrected_tensions(u,times[:-1],knots,x,limits)-u
            intended=(basis@x).reshape(u.shape)
            row['perturbations'].append(dict(step_n=step,effective_inf_n=float(abs(delta).max()),
                effective_l2_n=float(np.linalg.norm(delta)),clipped_entries=int((abs(delta-intended)>1e-12).sum()),
                effective_intervals_s=intervals(abs(delta).max(axis=1)>1e-12,times)))
        directions.append(row)
    perturbed=h.store.artifact(probe['source_reference']);coeff=np.asarray(perturbed['provenance']['search']['coefficients_n'])
    actual=np.asarray(perturbed['trajectory']['tensions_n'])-u;intended=(basis@coeff).reshape(u.shape)
    np.testing.assert_allclose(corrected_tensions(u,times[:-1],knots,coeff,limits),perturbed['trajectory']['tensions_n'],atol=0,rtol=0)
    raw=[h.store.artifact(r['raw_reference']) for r in (base,probe)];outputs=[task_outputs(v) for v in raw]
    residual=[constraint_vectors(o,**opt) for o in outputs];delta=residual[1]-residual[0]
    # Replay samples store the input for the interval ending at each sample.
    np.testing.assert_allclose([s['actual_tension_n'] for s in raw[0]['samples'][1:]],u,atol=0,rtol=0)
    np.testing.assert_allclose([s['actual_tension_n'] for s in raw[1]['samples'][1:]],u+actual,atol=0,rtol=0)
    diagnoses=[dict(study=old.run_id,reference=r,diagnostic=physical_diagnostic(old,r)) for r in state(old)['results']]
    diagnoses += [dict(study=h.run_id,reference=r,diagnostic=physical_diagnostic(h,r)) for r in refs]
    other=[]
    for path in ('evidence/control_search_p1/summary.json','evidence/s12_mirror/summary.json'):
        value=read(ROOT/path)
        other.append(dict(path=path,identity=digest(value),
            scope='Four-tendon algorithm capability reference only; different candidate/task, not a six-tendon Jacobian'))
    result=dict(stage='S12.7.4C',source_study=h.run_id,source_status='stopped',candidate=base['candidate'],
        baseline_source=base['source_reference'],probe_source=probe['source_reference'],task_options=opt,
        task_identity=tr['task_identity'],model_identity=tr['model_identity'],diagnoses=diagnoses,
        inputs=dict(times_s=tr['times_s'],tendon_order=tr['tendon_order'],tensions_n=tr['tensions_n'],
            sampling='pre-step ZOH commands; raw replay sample k+1 reports interval k applied input',
            bounds=[dict(tendon=t,limit_n=float(limits[j]),min_n=float(u[:,j].min()),max_n=float(u[:,j].max()),
                lower_intervals_s=intervals(u[:,j]<=1e-9,times),upper_intervals_s=intervals(abs(u[:,j]-limits[j])<=1e-9,times))
                for j,t in enumerate(tr['tendon_order'])]),
        basis=dict(knots_s=knots,dimension=basis.shape[1],flattening='knot-major then exact saved tendon order',
            interpolation='piecewise linear, sampled at interval start; final input begins 0.34 s, final knot at 0.35 s is not applied directly',
            coefficients=directions),
        measured_response=dict(coefficients_n=coeff.tolist(),coefficient_step_n=float(coeff[6]),
            input_delta_n=actual.tolist(),input_inf_n=float(abs(actual).max()),input_l2_n=float(np.linalg.norm(actual)),
            clipped_entries=int((abs(actual-intended)>1e-12).sum()),
            clipping_inf_n=float(abs(actual-intended).max()),
            output_times_s=outputs[0]['times_s'],
            position_delta_m=(np.asarray(outputs[1]['tip_positions_m'])-outputs[0]['tip_positions_m']).tolist(),
            velocity_delta_m_s=(np.asarray(outputs[1]['tip_velocities_m_s'])-outputs[0]['tip_velocities_m_s']).tolist(),
            constraint_vector_delta=delta.tolist(),one_sided_constraint_secant_per_n=(delta/coeff[6]).tolist(),
            task_gap_delta=task_gap(probe)['normalized_gap']-task_gap(base)['normalized_gap'],
            raw_metric_delta={k:probe['acceptance']['metrics'][k]-v for k,v in base['acceptance']['metrics'].items()},
            scope='Only coefficient 6 positive one-sided projected response. Other 11 coefficients unmeasured. No full Jacobian, cross-candidate ranking or guaranteed negative-direction improvement.'),
        algorithm_references=other,new_provider_requests=0,new_physical_launches=0,new_nmpc_launches=0,new_ppo_stages=0,
        recommendation='Test opposite coefficient 6 at -0.01 N to check local direction consistency; additional late-channel probes may be chosen from effective input supports, never from an unmeasured derivative ranking.',
        historical_state_ledger_events_unchanged=True)
    assert before==[(digest(state(x)),x.store.remaining(),digest(x.store.events(x.run_id))) for x in (old,h)]
    atomic_json(OUT/'audit.json',result)
    return result


if __name__=='__main__':
    value=audit();print(json.dumps(dict(dimension=value['basis']['dimension'],response={k:v for k,v in value['measured_response'].items()
        if k in ('input_inf_n','clipped_entries','task_gap_delta','raw_metric_delta')},bounds=value['inputs']['bounds'],
        late_directions=value['basis']['coefficients'][6:])))
