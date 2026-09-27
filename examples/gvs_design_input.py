"""Write a frozen, bounded physical-design Route input; no provider or solves."""
import argparse
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from extensions.tendon_family.gvs_profile import candidate_reach_input
from tools.state_io import atomic_json


def experiment_input(run_id='gvs-length-design',*,target_m=(.29,.035,.19)):
    value=candidate_reach_input(run_id,target_m=target_m,
        timing=dict(duration_s=.35,control_period_s=.01,timestep_s=.0005,sample_period_s=.01))
    lengths={c['id']:c['length_m'] for c in value['robot']['structure']['data']['components'] if c['kind']=='flexible_segment'}
    if lengths!={'near':.16,'far':.12}:raise ValueError('BASELINE_LENGTHS_CHANGED')
    p=value['policy']
    bounds={'components/near/length_m':[.15,.17],'components/far/length_m':[.11,.13]}
    p['candidate_builder']['parameters']['data']['parameters']={k:dict(type='number',bounds=v) for k,v in bounds.items()}
    p['editable']=bounds
    p['budget']=dict(model_calls=24,tool_calls=60,backend_solves=3,worker_calls=0,wall_s=7200.)
    p['timeout_s']=1800.
    p['allowed_tools']=[]
    # Analysis tools that still resolve the parent robot are deliberately absent.
    p['tool_bindings']={k:'1.0.0' for k in ('route.advance','route.inspect','simulation.run',
        'evaluation.run','evidence.read','session.control','control.profile_report')}
    p['route']=dict(contract='family.route_policy',version='1.0.0',data=dict(
        source='User attachment: one genuine DeepSeek-selected bounded physical-design experiment; scoped task/design/tool/evidence transmission; at most 24 model requests, 60 tool calls, three fresh backend attempts including infrastructure retries, 7200 seconds.',
        combinations={'candidate_gvs_nmpc':{k:p[k] for k in ('dynamics_model','backend','controller')}},max_trials=3,
        guidance='Choose your own meaningful millimeter-scale physical modification: change near length (baseline 0.16 m, bounds 0.15–0.17) and/or far length (baseline 0.12 m, bounds 0.11–0.13); explain your engineering rationale. Use public build then run, cite prior node evidence for subsequent actions, read current evidence, and explicitly finish with your conclusion. No fixed decision sequence or candidate is supplied. Keep the supplied controller recipe, target, task duration, tolerance, initialization, materials, damping, scene, mesh and all acceptance rules frozen. Do not build or execute the unchanged baseline. At most three fresh backend attempts in total, including failed infrastructure attempts; stop early once a changed design passes the original evaluator and deliver it. A valid failed reach may be delivered honestly. Separate call-chain completion, changed-design execution, original reach success, sampled settling and real-time feasibility. Read profile_report_summary in the current run result/context before delivery and cite current evaluation/report references. Historical Stage 3.17 reach passed at about 8.473 mm with failed sampled settling (runs/stage317_live_route_20260927/implementation_report.md and behavior_audit.json); it validates only the old design. Stage 3.21 braking findings are historical limitations, not prerequisites. This input uses the bundled Stage 3.15/3.16/3.17 recipe, not the later braking recipe. Historical tensions are only a numerical guess: execution rebuilds candidate dynamics and regenerates states from measurement. Numerical preparation belongs to budgeted execution; build is solve-free. Reserve wall budget for evaluation/report (1800 s per-call reservation) and provider conclusion; do not spend the full remaining budget on simulation.'))
    return value


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--target',type=float,nargs=3,default=(.29,.035,.19))
    args=parser.parse_args()
    if args.output.exists():raise ValueError('INPUT_ALREADY_EXISTS: use a new path')
    atomic_json(args.output,experiment_input(target_m=args.target))
    print(str(args.output))
