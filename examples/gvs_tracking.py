"""Freeze a timed tracking input, then use the existing public execution chain."""
import argparse
import json
import os
import sys
import io
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[name]='1'

from schemas.platform import SessionInput
from tools.platform_store import plain
from tools.state_io import atomic_json, digest
from extensions.tendon_family.gvs_profile import reach_input, load_profile
from extensions.tendon_family.tracking import CartesianReference, TrackingControl, checked_tracking


def initialized_tip(value):
    """MuJoCo forward kinematics only; no control solve or integration."""
    import mujoco
    from extensions.tendon_family.backends import physics_for
    from extensions.tendon_family.scene import assemble
    from extensions.tendon_family.mjcf import compile_xml
    from tools.platform_registry import registry
    inp=SessionInput.model_validate(value)
    physics=physics_for(inp);scene=assemble(inp,physics)
    xml=io.BytesIO()
    compile_xml(physics,scene,registry().parse(inp.policy.backend.parameters),xml)
    model=mujoco.MjModel.from_xml_string(xml.getvalue().decode());data=mujoco.MjData(model)
    ids=[model.joint(j).id for j in physics['dofs']]
    data.qpos[model.jnt_qposadr[ids]]=scene['qpos_rad']
    data.qvel[model.jnt_dofadr[ids]]=scene['qvel_rad_s']
    mujoco.mj_forward(model,data)
    return data.site_xpos[model.site('tip_site').id].tolist()


def tracking_input(run_id='gvs-time-tracking',reference=None):
    value=reach_input(run_id,timing=dict(duration_s=.4,control_period_s=.01,sample_period_s=.01,timestep_s=.0005))
    if reference is None:
        start=initialized_tip(value)
        reference=CartesianReference(interpolation='quintic',start_s=0.,end_s=.4,
            start_m=start,end_m=[start[0]-.002,start[1]+.024,start[2]-.008],
            provenance='Baseline MuJoCo mj_forward at task initializer; no integration. robot sha256 '+digest(value['robot'])+'; frozen for every candidate.')
    else:reference=CartesianReference.model_validate(reference)
    task=value['task']
    task.update(task_id='gvs-cartesian-tracking',task_version='1.0.0',name='Short world-frame quintic tracking',
        source='Stage 3.24 predeclared path and sampled acceptance; no trajectory reused',family='task.tracking',
        goal=dict(contract='family.cartesian_reference',version='1.0.0',data=plain(reference)),
        evaluator=dict(extension_id='evaluate.tracking',version='1.0.0',parameters=dict(contract='family.tracking_evaluation',version='1.0.0',data=dict(max_position_error_m=.01,
            tension_limits_n={t['id']:t['force_limit_n'] for t in value['robot']['structure']['data']['tendons']}))),
        objectives=[dict(metric='max_position_error',direction='minimize',units='m',weight=1.)])
    task['sampling']['window_s']=[.01,.4]
    recipe=load_profile()['parameters']
    recipe.update(velocity_weight=.01,terminal_velocity_weight=.01,recover_returned_tensions=True)
    value['policy']['controller']=dict(extension_id='controller.gvs_nmpc',version='5.0.0',
        parameters=dict(contract='family.gvs_tracking_control',version='1.0.0',data=plain(TrackingControl(recipe=recipe))))
    checked_tracking(SessionInput.model_validate(value))
    return value


def live_input(frozen):
    from copy import deepcopy
    value=deepcopy(frozen);p=value['policy']
    bounds={'components/near/length_m':[.15,.17],'components/far/length_m':[.11,.13]}
    p['candidate_builder']['parameters']['data']['parameters']={k:dict(type='number',bounds=v) for k,v in bounds.items()}
    p['editable']=bounds
    p['budget']=dict(model_calls=24,tool_calls=60,backend_solves=3,worker_calls=0,wall_s=7200.)
    p['timeout_s']=1800.
    p['allowed_tools']=[]
    p['tool_bindings']={k:'1.0.0' for k in ('route.advance','route.inspect','simulation.run','evaluation.run',
        'evidence.read','session.control','control.profile_report','analysis.gvs_candidate_evaluate')}
    p['route']=dict(contract='family.route_policy',version='1.0.0',data=dict(source='User authorized Stage 3.24 bounded live DeepSeek tracking regression',
        combinations={'tracking':{k:p[k] for k in ('dynamics_model','backend','controller')}},max_trials=3,
        guidance='Choose your own changed length candidate, at least 1 mm change in near or far from baseline 0.160/0.120 m. Build, then call analysis.gvs_candidate_evaluate with that explicit build source_node BEFORE its run. Analyze zero q/qdot using the structural-linear controller basis coordinate count (12) and all six tendon tensions (names in robot); this is a real mathematical calculation, not execution evidence. Interpret candidate-bound analysis, execute/evaluate through run, revise only if justified. Keep reference, scoring interval, tolerance, controller recipe, initializer, physics and all other design values frozen. Maximum 3 fresh backend attempts including retries, 24 requests, 60 tools, 7200 seconds. Stop early on changed-candidate tracking pass and explicitly finish with exact design_statement from candidate_facts and evidence-linked explanation. Read current report summary before delivery. Distinguish interval tracking acceptance, valid execution, feasible plan acceptance, optimizer convergence, cost, and lack of real-time demonstration. Do not invent settling criteria or execution identifiers for analysis.'))
    return value


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['make-input','prepare','run','live-input'])
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--input',type=Path)
    args=parser.parse_args()
    if args.action in ('make-input','live-input'):
        if args.output.exists():raise ValueError('FROZEN_INPUT_ALREADY_EXISTS')
        value=tracking_input() if args.action=='make-input' else live_input(json.loads(args.input.read_text(encoding='utf8')))
        atomic_json(args.output,value)
        print(args.output)
    else:
        if args.input is None:parser.error('--input required; execution never re-anchors reference')
        from examples.gvs_parameterized_reach import prepare,run
        (prepare if args.action=='prepare' else run)(args.output.resolve(),args.input)
