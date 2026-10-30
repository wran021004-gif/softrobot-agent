"""Read saved P6.3-H receipts and histories; never solve, integrate or charge."""
import argparse
import csv
import json
from pathlib import Path

from tools.platform_host import Host
from tools.research.config import ROOT
from tools.research.state import state
from tools.state_io import atomic_json, read


def history_curve(rows, *, steps_per_rollout):
    """Cost axis uses confirmed equal-size full rollouts, never invented wall time."""
    best=None;curve=[]
    for i,row in enumerate(rows,1):
        j=row['measure']['signed_maximum_excess']
        best=j if best is None else min(best,j)
        curve.append(dict(callback=i,physics_steps=i*steps_per_rollout,J=j,best_found_J=best))
    return curve


def report(h):
    s=state(h);analyses={};replays={}
    for ref in s['analysis_results']:
        raw=h.store.artifact(ref)
        key=raw['operation_key'].removeprefix('p63h-').removesuffix('-analysis')
        analyses[key]=(ref,raw)
    for ref in s['physical_replays']:
        raw=h.store.artifact(ref);replays[raw['operation_key'].removeprefix('p63h-')]=(ref,raw)
    rows={};curves={}
    for key,(ref,raw) in analyses.items():
        if not raw.get('requested_operation',{}).get('control_optimization'):continue
        t=raw.get('nonlinear_capability',{});native=raw.get('native_dynamics',{})
        cost=native.get('cost',raw.get('native_progress',{}).get('cost',{}))
        rows[key]=dict(reference=ref,status=raw['status'],reason=raw.get('reason'),
            initial_metrics=t.get('initial_metrics'),best_metrics=t.get('best_metrics'),
            stop_reason=t.get('stop_reason',raw.get('reason')),callbacks_complete=t.get('callbacks',0),
            rollout_attempts=cost.get('rollouts'),cost=cost,worker_elapsed_s=raw['charged_numerical_s'],
            input_saturation=t.get('input_saturation'),coefficient_boundary=t.get('coefficient_boundary'),
            local_responses=t.get('local_responses'),failure=raw.get('native_diagnostic'))
        history=native.get('optimization',{}).get('candidates',[])
        if history:
            assert cost['physics_steps']%len(history)==0
            curves[key]=history_curve(history,steps_per_rollout=cost['physics_steps']//len(history))
        else:curves[key]=[]
    conic_ref,conic=analyses['conic'];tr=conic['trajectory']
    sensitivity_ref,raw=analyses['sensitivity'];sensitivity=raw['optimal_sensitivity']
    structures={key:dict(reference=ref,**v['nonlinear_response']) for key,(ref,v) in analyses.items() if key.startswith('structure-')}
    replay_rows={key:dict(reference=ref,acceptance=v['acceptance'],worker_elapsed_s=v['charged_numerical_s'],
        raw_reference=v['raw_reference'],physics_steps=h.store.artifact(v['raw_reference']).get('physics_steps')) for key,(ref,v) in replays.items()}
    a=rows['direct']['worker_elapsed_s']+replay_rows['replay-direct']['worker_elapsed_s']
    b=conic['charged_numerical_s']+rows['guided']['worker_elapsed_s']
    analysis_s=sum(v['charged_numerical_s'] for _,v in analyses.values())
    replay_s=sum(v['charged_numerical_s'] for _,v in replays.values())
    summary=dict(study_id=h.run_id,freeze=s['freeze'],status=s['research_status'],
        scope='Operator-owned controlled numerical research; no Main discovery or formal Benchmark claim.',
        provider_requests=h.store.remaining()['used']['model_calls'],ledger=h.store.remaining(),
        mathematical_evaluations=s['mathematical_evaluations'],numerical_s=s['numerical_s'],
        cost_reconciliation=dict(analysis_receipts_s=analysis_s,replay_receipts_s=replay_s,
            aggregate_control_initialization_s=s['control_initialization_s'],
            generation_and_other_preparation_s=s['numerical_s']-analysis_s-replay_s-s['control_initialization_s'],
            per_source_initialization_timers='Unavailable after documented runtime-side-file recovery; do not infer zero.',
            direct_worker_plus_final_replay_s=a,guided_gvs_conic_plus_failed_native_worker_s=b,
            isolated_gvs_build_s=None,isolated_gvs_build_reason='Original production receipts do not time model construction independently from worker import, diagnostics and serialization.',
            guided_final_replay_s=None,guided_final_replay_reason='Native failed before producing an optimized source; none launched.',
            conic_only_replay_s=replay_rows['replay-conic']['worker_elapsed_s'],
            conic_only_replay_counted_in_guided_total=False,
            attribution='Arm worker subtotals exclude shared generation and the separately measured initialization pool; full Study numerical total includes all original charges.'),
        conic=dict(reference=conic_ref,worker_elapsed_s=conic['charged_numerical_s'],kernel_s=tr['kernel_elapsed_s'],
            solver=tr['solver'],actual_calls=conic['actual_mathematical_calls'],J=tr['replayed_violation'],
            replay=tr['replay'],task_acceptance=conic['task_acceptance'],model_scope=conic['analysis_applicability']),
        native=rows,replays=replay_rows,sensitivity=dict(reference=sensitivity_ref,**sensitivity),structure=structures,
        time_to_independent_success=None,independent_task_pass=False,
        callback_wall_time_curves=None,callback_wall_time_reason='Original history cost_s is zero for Native callbacks; worker progress side files partially lost. Only confirmed callback/physics-step curves are exported.',
        source_side_file_recovery='See runtime_recovery.json; immutable scientific results, identities and cumulative charges retained, completed pending Worker settled without relaunch.')
    return summary,curves


def plot(summary, curves, destination):
    """Optional publication figure from saved numbers; no new simulation."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,(ax,bx)=plt.subplots(1,2,figsize=(11,4.2),layout='constrained')
    colors=['#233c70','#cc5b48','#edb553','#8f629a','#168677']
    labels=['baseline 160 mm','156 mm','164 mm','158 mm','162 mm']
    valid=[(k,v) for k,v in curves.items() if v]
    for (key,rows),color,label in zip(valid,colors,labels):
        ax.step([r['callback'] for r in rows],[r['best_found_J'] for r in rows],
            where='post',label=label,color=color,lw=1.5)
    ax.set(yscale='log',xlabel='Completed Native callback',ylabel='Best-found signed J (all > 0)',
        title='Saved Native histories; equal 200 callback caps')
    ax.legend(frameon=False,fontsize=8);ax.grid(alpha=.15)
    ax.text(.98,.98,'Guided: no complete callback\nContact at 0.186 s',transform=ax.transAxes,
        ha='right',va='top',fontsize=8,color='#a63432')
    points=summary['sensitivity']['numerical_optimality']
    x=sorted(points,key=lambda p:p['value'])
    bx.plot([p['value']*1000 for p in x],[p['result']['replayed_violation'] for p in x],
        's--',color='#168677',label='Conic local affine model')
    keys=['native-minus','native-minus-half','direct','native-plus-half','native-plus']
    bx.plot([p['value']*1000 for p in x],
        [summary['native'][k]['best_metrics']['signed_maximum_excess'] for k in keys],
        'o-',color='#233c70',label='Native reoptimized, finite budget')
    bx.axhline(0,color='#888888',lw=.8)
    bx.set(xlabel='First segment length (mm)',ylabel='Signed J',
        title='Model direction does not predict Native response')
    bx.legend(frameon=False,fontsize=8);bx.grid(alpha=.15)
    fig.suptitle('P6.3-H controlled numerical study | no independently accepted task',fontsize=12)
    fig.savefig(destination,dpi=180);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--plot',action='store_true');args=p.parse_args()
    h=Host(ROOT/'runs/p63h/store','p63h-conic-native-20261030',actor='read-only-report')
    summary,curves=report(h);args.output.mkdir(parents=True,exist_ok=True)
    atomic_json(args.output/'numerical_summary.json',summary)
    with (args.output/'best_found_J.csv').open('w',newline='',encoding='utf8') as stream:
        writer=csv.DictWriter(stream,fieldnames=['arm','callback','physics_steps','J','best_found_J']);writer.writeheader()
        for arm,values in curves.items():
            for row in values:writer.writerow(dict(arm=arm,**row))
    if args.plot:plot(summary,curves,args.output/'research_curves.png')
    print(json.dumps(dict(costs=summary['cost_reconciliation'],native={k:v['best_metrics'] for k,v in summary['native'].items()})))
