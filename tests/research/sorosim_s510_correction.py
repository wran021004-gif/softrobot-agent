"""Explicit finite S5.10 experiment; numerical tools own all actual executions."""
from copy import deepcopy
from pathlib import Path
import json
import numpy as np
from scipy.optimize import least_squares

from tools.research import core
from tools.research.control_correction import (corrected_tensions, task_outputs,
    task_measure, fitting_residual, output_error_budget, improvement_test)
from tools.research.feedback import task_gap
from tools.research_tasks import task_adapter
from tools.research.numerics import archived
from tools.research.state import state, save, update
from tools.state_io import atomic_json, read, digest
from tests.research.sorosim_s56_refinement import plan

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'evidence/sorosim_s510'
SOURCE={'artifact_id':'56b45d790a53529977d037c33e844ddc76a6df824d2f33298bc44774fba41fde','media_type':'application/json'}


class SearchFinished(Exception):
    pass


def main():
    host=core.prepare(ROOT/'configs/research/study_sorosim_s510_correction.json')
    if 'freeze' not in state(host):core.bind(host)
    if state(host)['research_status']=='stopped':
        print(json.dumps(dict(status='sealed',summary=str(DEST/'summary.json'))));return
    original=archived('evidence/sorosim_s59/study',SOURCE)
    old=archived('evidence/sorosim_s59/study',original['design_candidate'])
    parameters=deepcopy(old['parameters']);parameters['family_space_identity']=state(host)['spec']['family_space_identity']
    candidate=core.dispatch(host,plan('generate',generation=parameters),'s510-design-B',origin='engineering')['result']['candidate']
    cfg=host.store.artifact(candidate)['configuration']
    if cfg['robot']!=old['configuration']['robot'] or cfg['task']!=old['configuration']['task']:
        raise ValueError('REFERENCE_ROBOT_OR_TASK_CHANGED')
    raw_source=save(host,original,'s510_immutable_reference_import')
    trajectory=deepcopy(original['trajectory'])
    trajectory['times_s']=trajectory['times_s'][::4];trajectory['states']=trajectory['states'][::4]
    trajectory['design_candidate']=candidate
    settings=state(host)['spec']['correction_search'];knots=settings['knots_s']
    reference=np.asarray(trajectory['tensions_n']);n=len(knots)*reference.shape[1]
    times=np.asarray(trajectory['times_s'][:-1]);limits=host.store.artifact(candidate)['resolved_parameters']['force_limits_n']
    adapter=task_adapter(cfg);ranking=adapter.ranking_limits()
    target=np.asarray(cfg['task']['goal']['data']['target_m'])
    hold=adapter.holding_start_s();pl=ranking['holding_max_error_m'];vl=ranking['holding_max_speed_m_s']
    rows=read(DEST/'progress.json')['candidates'] if (DEST/'progress.json').exists() else []
    cache={row['sequence_identity']:row for row in rows}
    math_rows=read(DEST/'mathematics.json') if (DEST/'mathematics.json').exists() else {}
    surrogate=None

    def controls(x):return corrected_tensions(reference,times,knots,x,limits)

    def schedule(x,outputs=None):
        tr={**trajectory,'tensions_n':controls(x).tolist()}
        value=dict(source_kind='explicit_control_schedule_v1',trajectory=tr,task_acceptance='unmeasured',
            provenance=dict(original_s59_result=SOURCE,imported_reference=raw_source,candidate=candidate,
                correction_knots_s=knots,correction_coefficients_n=np.asarray(x).tolist(),
                physical_clipping='componentwise to candidate tendon force bounds'))
        if outputs is not None:value['mathematical_outputs']=dict(outputs,model_identity=tr['model_identity'],samples=len(outputs['times_s']))
        return save(host,value,'s510_bound_control_schedule')

    def measure(out):return task_measure(out,target,hold,pl,vl)

    def residual(out):return fitting_residual(out,target,hold,pl,vl)

    def integrate(x,count,label):
        if label in math_rows:return math_rows[label]
        source=schedule(x)
        result=core.dispatch(host,plan('refine',refinement=dict(candidate=candidate,source=source,substeps=count)),
            's510-math-'+label,origin='engineering')['result']
        row=dict(reference=result['reference'],source=source,coefficients_n=np.asarray(x).tolist(),substeps=count)
        value=host.store.artifact(row['reference'])
        row.update(complete=value.get('complete',False),status=value['status'])
        if row['complete']:
            row.update(outputs=task_outputs(value['raw']),measure=measure(task_outputs(value['raw'])),
                maximum_root_residual_inf=float(np.max(np.asarray(value['raw']['roots'])[:,2])))
        math_rows[label]=row;atomic_json(DEST/'mathematics.json',math_rows)
        print(json.dumps(dict(mathematics=label,complete=row['complete'],measure=row.get('measure'))),flush=True)
        if not row['complete']:raise RuntimeError('INCOMPLETE_MATHEMATICAL_INTEGRATION: '+label)
        return row

    def simulation(x,label):
        identity=digest(controls(x).tolist())
        if identity in cache:return cache[identity]
        if len(rows)>=state(host)['spec']['budgets']['physical_launches']:raise SearchFinished('physical count ceiling')
        prediction=surrogate(x) if surrogate else None
        source=schedule(x)
        result=core.dispatch(host,plan('physical_replay',physical_replay=dict(candidate=candidate,source=source),
            supporting_evidence=[raw_source]),'s510-sim-'+identity[:20],origin='engineering')['result']
        core.read_evidence(host,dict(reference=result['reference']))
        actual=task_gap(result);raw=host.store.artifact(result['raw_reference'])
        row=dict(sequence_identity=identity,label=label,coefficients_n=np.asarray(x).tolist(),
            source=source,reference=result['reference'],valid=actual['valid_complete'],accepted=result['acceptance']['accepted'],
            registered_task_gap=actual,measure=measure(task_outputs(raw)) if actual['valid_complete'] else None,
            predicted_measure=measure(prediction) if prediction else None,
            prediction_kind='32-grid-anchor_plus_4-grid_one-sided_response_not_certified' if prediction else None)
        rows.append(row);cache[identity]=row
        atomic_json(DEST/'progress.json',dict(candidate=candidate,candidates=rows))
        print(json.dumps(dict(simulations=len(rows),label=label,valid=row['valid'],measure=row['measure'])),flush=True)
        if row['accepted']:
            core.dispatch(host,plan('select',selected_execution=row['reference'],supporting_evidence=[row['reference']]),
                's510-select',origin='engineering')
            raise SearchFinished('first original task pass')
        return row

    def outputs(row):return task_outputs(host.store.artifact(host.store.artifact(row['reference'])['raw_reference']))

    zero=np.zeros(n);stop_reason=None
    try:
        coarse=integrate(zero,4,'reference-4');fine=integrate(zero,32,'reference-32')
        saved_states=np.asarray(original['trajectory']['states'])[::4]
        replay=host.store.artifact(coarse['reference'])['raw']
        atomic_json(DEST/'reference_validation.json',dict(source=SOURCE,independent_4=coarse['reference'],
            independent_32=fine['reference'],sampled_state_difference_native_inf=float(np.max(abs(np.asarray(replay['states'])-saved_states))),
            state_difference_scope='Mixed native curvature and rate coordinates, not Cartesian units',
            numerical_grid_differences=dict(position_m=float(np.max(np.linalg.norm(np.asarray(fine['outputs']['tip_positions_m'])-coarse['outputs']['tip_positions_m'],axis=1))),
                speed_m_s=float(np.max(np.linalg.norm(np.asarray(fine['outputs']['tip_velocities_m_s'])-coarse['outputs']['tip_velocities_m_s'],axis=1)))),
            continuous_time_error_bound=None))
        base=simulation(zero,'reference-alone')
        step=settings['model_difference_step_n'];columns=[]
        for j in range(n):
            x=zero.copy();x[j]=step
            r=integrate(x,4,'response-'+str(j))
            columns.append((np.stack([r['outputs']['tip_positions_m'],r['outputs']['tip_velocities_m_s']])-
                np.stack([coarse['outputs']['tip_positions_m'],coarse['outputs']['tip_velocities_m_s']]))/step)
        matrix=np.stack(columns,axis=-1)
        def surrogate(x):
            a=np.stack([fine['outputs']['tip_positions_m'],fine['outputs']['tip_velocities_m_s']])+matrix@x
            return dict(times_s=fine['outputs']['times_s'],tip_positions_m=a[0].tolist(),tip_velocities_m_s=a[1].tolist())
        bound=settings['guided_step_limit_n']
        proposed=least_squares(lambda x:residual(surrogate(x)),zero,bounds=(-bound,bound),max_nfev=60).x
        atomic_json(DEST/'mathematical_recommendation.json',dict(coefficients_n=proposed.tolist(),
            baseline=measure(fine['outputs']),predicted=measure(surrogate(proposed)),
            method='one-sided finite-difference response, affine output correction anchored at 32-grid baseline',
            scope='Uncertified local heuristic; input clipping, nonlinear response and grid effects not bounded'))
        guided=simulation(proposed,'mathematical-recommendation')
        integrate(proposed,32,'recommended-32')
        best=min((r for r in rows if r['valid']),key=lambda r:(r['measure']['normalized_gap'],r['measure']['sum_normalized_excess']))
        x0=np.asarray(best['coefficients_n']);cap=settings['coefficient_limit_n']
        def fun(x):
            row=simulation(x,'simulation-correction')
            return residual(outputs(row)) if row['valid'] else np.full(len(residual(fine['outputs'])),1e3)
        def jac(x):
            center=fun(x);columns=[];h=settings['simulation_difference_step_n']
            for j in range(n):
                q=x.copy();delta=h if x[j]+h<=cap else -h;q[j]+=delta
                columns.append((fun(q)-center)/delta)
            return np.column_stack(columns)
        solved=least_squares(fun,x0,jac=jac,bounds=(-cap,cap),max_nfev=settings['optimizer_iterations'],
            xtol=1e-6,ftol=1e-6,gtol=1e-6,x_scale=.25)
        stop_reason='optimizer termination: '+solved.message
    except SearchFinished as exc:stop_reason=str(exc)
    ranked=sorted((r for r in rows if r['valid']),key=lambda r:(not r['accepted'],r['measure']['normalized_gap'],r['measure']['sum_normalized_excess']))
    if not state(host).get('success_gate') and ranked:
        integrate(np.asarray(ranked[0]['coefficients_n']),32,'best-32')
    paired={}
    for label,row in [('reference-32',rows[0] if rows else None),
            ('recommended-32',next((r for r in rows if r['label']=='mathematical-recommendation'),None)),
            ('best-32',ranked[0] if ranked else None)]:
        if label in math_rows and row and row['valid']:
            m=math_rows[label];sim=outputs(row)
            paired[label]=dict(mathematical=m['reference'],physical=row['reference'],
                model_measure=m['measure'],simulation_measure=row['measure'],
                error_budget=output_error_budget(m['outputs'],sim,hold,pl,vl))
    comparisons={}
    if 'reference-32' in paired:
        b=paired['reference-32']
        for label,a in paired.items():
            if label!='reference-32':comparisons[label]=improvement_test(b['model_measure'],a['model_measure'],b['simulation_measure'],a['simulation_measure'],b['error_budget'],a['error_budget'])
    summary=dict(study_id=host.run_id,freeze=state(host)['freeze'],candidate=candidate,
        reference_source=SOURCE,stop_reason=stop_reason,selected=state(host).get('selected'),
        original_task_passed=bool(state(host).get('success_gate')),ranked_candidates=ranked,
        invalid_candidates=[r for r in rows if not r['valid']],paired_error_budgets=paired,
        exact_paired_direction_checks=comparisons,prospective_regional_bound='not_established',
        guarantee_missing_conditions=['uniform output discrepancy bound on the candidate region',
            'independent integration/roundoff bounds to exact model solutions'],
        next_structure_basis='If control search fails, compare proximal length +/-1 mm and modulus +/-5 percent with equal control-adaptation budgets; static sensitivity only nominates candidates, not rankings.',
        used=host.store.remaining()['used'],mathematical_replays=state(host).get('bdf_replays',0))
    ref=save(host,summary,'s510_search_summary')
    if state(host)['research_status']!='stopped':
        s=state(host)
        core.dispatch(host,plan('stop',next_step='stop',supporting_evidence=[ref,*s['mechanics_results'],*s['physical_replays']]),'s510-stop',origin='engineering')
    update(host,s510_summary=ref)
    core.export(host,DEST/'study');atomic_json(DEST/'summary.json',dict(summary,summary_reference=ref))
    print(json.dumps(dict(status='delivered',passed=summary['original_task_passed'],simulations=len(rows),best=ranked[0]['measure'] if ranked else None)),flush=True)


if __name__=='__main__':main()
