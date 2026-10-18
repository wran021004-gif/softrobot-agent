"""Explicit S5.8 preparation/live/recovery driver; no alternative Agent loop."""
import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import time
from copy import deepcopy
from pathlib import Path

import numpy as np

from tools.platform_host import Host
from tools.research import core, rl
from tools.research.agent import converse, decision_packet, pending, load_credential
from tools.research.feedback import import_experiment, experiment_preflight, result_view
from tools.research.numerics import archived, execution_source
from tools.research.nmpc_prediction_diagnostic import archive_index
from tools.research.state import state, save, update
from tools.research.contracts import Plan, RLRequest
from tools.state_io import read, atomic_json
from tests.research.sorosim_s56_refinement import plan

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'evidence/sorosim_s58'
SPEC=ROOT/'configs/research/study_sorosim_s58_agent.json'


def projection_audit():
    """Saved joint states + mj_forward/jacobian only; no dynamics or provider."""
    import mujoco
    from extensions.tendon_family.gvs_projection import project, discretize
    started=time.perf_counter()
    folder='evidence/sorosim_s56/physics/study'
    reference=read(ROOT/'evidence/sorosim_s56/physics/summary.json')['nmpc']
    index=archive_index(folder,reference,(19,29))
    source=execution_source(dict(reference=reference),folder)
    physics=archived(folder,source['files']['resolved_physics.json'])
    cfg=archived(folder,source['result']['candidate'])['configuration']
    model=mujoco.MjModel.from_xml_string(archived(folder,source['files']['robot.xml'],raw=True).decode())
    joints=[model.joint(name).id for name in physics['dofs']]
    qi=model.jnt_qposadr[joints];vi=model.jnt_dofadr[joints]
    tip=model.site('tip_site').id
    summary57=read(ROOT/'evidence/sorosim_s57/summary.json')
    rows=[]
    for case in index['cases']:
        q=case['physical_state_before']['qpos_rad'];v=case['physical_state_before']['qvel_rad_s']
        binding=dict(basis=index['projector']['resolved_basis']['specification'],convention=index['projector']['id'])
        p=project(physics,cfg['robot']['structure']['data'],q,v,**binding)
        qr,vr=discretize(physics,cfg['robot']['structure']['data'],p['q_gvs'],p['qdot_gvs'],**binding)
        outputs=[]
        for position,velocity in ((q,v),(qr,vr)):
            data=mujoco.MjData(model);data.qpos[qi]=position;data.qvel[vi]=velocity
            mujoco.mj_forward(model,data)
            jac=np.zeros((3,model.nv));mujoco.mj_jacSite(model,data,jac,None,tip)
            outputs.append(dict(position=data.site_xpos[tip].copy(),velocity=jac@data.qvel))
        old=next(r for r in summary57['cases'] if r['update_index']==case['update_index'])
        raw=archived('evidence/sorosim_s57/study',old['resolutions']['1']['reference'])['raw']
        math=dict(position=raw['tip_positions_m'][0],velocity=raw['tip_velocities_m_s'][0])
        errors={}
        for field,key in (('position','tip_position_m'),('velocity','tip_velocity_m_s')):
            original,reconstructed=(o[field] for o in outputs)
            if not np.allclose(original,case['before'][key],rtol=0,atol=1e-10):
                raise ValueError('ARCHIVED_MUJOCO_KINEMATICS_MISMATCH')
            reduction=reconstructed-original;kinematic=np.asarray(math[field])-reconstructed
            errors[field]=dict(original=original.tolist(),reconstructed=reconstructed.tolist(),
                mathematical_start=math[field],reduction_vector=reduction.tolist(),
                reduction_norm=float(np.linalg.norm(reduction)),
                remaining_cross_kinematic_vector=kinematic.tolist(),remaining_cross_kinematic_norm=float(np.linalg.norm(kinematic)),
                original_cross_model_norm=float(np.linalg.norm(np.asarray(math[field])-original)))
        roundtrip=project(physics,cfg['robot']['structure']['data'],qr,vr,**binding)
        if not np.allclose(roundtrip['q_gvs']+roundtrip['qdot_gvs'],case['initial_state'],rtol=0,atol=1e-10):
            raise ValueError('PROJECTION_INVERSE_BINDING_MISMATCH')
        rows.append(dict(update_index=case['update_index'],time_s=case['time_s'],errors=errors,
            original_joint_state=dict(qpos_rad=q,qvel_rad_s=v),reconstructed_joint_state=dict(qpos_rad=qr.tolist(),qvel_rad_s=vr.tolist()),
            projection=p,coordinate_order=index['coordinate_order']))
    result=dict(source=reference,source_files=source['files'],rows=rows,physics_steps=0,provider_requests=0,
        full_nlp=0,elapsed_s=time.perf_counter()-started,implementation_error_detected=False,
        interpretation='Exact archived MuJoCo output and projection/inverse binding checks pass. Signed output difference splits algebraically into reduced representation loss and remaining kinematic difference; norms are not additive. No unique dynamics cause inferred.')
    atomic_json(DEST/'projection_preflight.json',result)
    return result


def prepare():
    host=core.prepare(SPEC)
    if 'freeze' not in state(host):core.bind(host)
    if state(host).get('s58_prepared'):return host
    s=state(host)
    load_credential(Path(s['spec']['runtime']['credentials_reference']).expanduser())
    provider=s['pilot']['provider']
    if provider['base_url']!='https://api.deepseek.com' or provider['model']!='deepseek-flash':
        raise ValueError('FROZEN_PROVIDER_MISMATCH')
    old=read(ROOT/'evidence/sorosim_s56/physics/summary.json')
    params=deepcopy(archived('evidence/sorosim_s56/physics/study',old['candidate'])['parameters'])
    params['family_space_identity']=s['spec']['family_space_identity']
    candidate=core.dispatch(host,plan('generate',generation=params),'s58-engineering-design-B',origin='engineering')['result']['candidate']
    if not candidate:raise ValueError('REFERENCE_CANDIDATE_GENERATION_FAILED')
    source_index=read(ROOT/'evidence/sorosim_s5a/summary.json')
    source=save(host,archived('evidence/sorosim_s5a/study',source_index['source']),'historical_exact_mathematical_reference')
    relation=rl.import_mathematical_reference(host,candidate,source)
    context=[]
    for stage in ('s55','s56','s57'):
        path=ROOT/f'evidence/sorosim_{stage}/agent_feedback_packet.json'
        ref=save(host,dict(stage=stage,source_path=str(path.relative_to(ROOT)),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            original=read(path),ownership='historical read-only; not fresh development evidence'),'imported_s58_context')
        context.append(dict(stage=stage,reference=ref))
    history=[]
    for stage in ('s5a','s5b','s5rl','s56/physics','s56/rl'):
        summary=read(ROOT/f'evidence/sorosim_{stage}/summary.json');folder=f'evidence/sorosim_{stage}/study'
        rows=[(v['evaluation'],'rl') for v in summary['routes']] if 'routes' in summary else (
            [(summary['open_loop'],'fixed_tension'),(summary['nmpc'],'nmpc')] if stage=='s56/physics' else
            [(summary['result'],'fixed_tension' if stage=='s5a' else 'nmpc')])
        for ref,route in rows:
            if ref:history.append(import_experiment(host,folder,ref,route))
    context.append(dict(stage='historical_experiments',reference=save(host,history,'historical_experiment_index')))
    parents=[]
    parent_id='sorosim-s56-rl-20261017'
    parent=Host(ROOT/'runs/research'/parent_id,parent_id)
    for row in read(ROOT/'evidence/sorosim_s56/rl/summary.json')['routes']:
        parents.append(rl.import_continuation_source(host,parent,row['run_id']))
    update(host,stage_context=context,scoped_context=[*s.get('scoped_context',[]),*[v['reference'] for v in context],*history],
        preseeded_candidate=candidate,preseeded_mathematical_reference=relation)
    from extensions.tendon_family.sorosim_control import resolve_control
    from extensions.tendon_family.backends import physics_for
    from extensions.tendon_family.sorosim_session import dependency_identity
    from schemas.platform import SessionInput
    inp=SessionInput.model_validate(host.store.artifact(candidate)['configuration'])
    control=resolve_control(inp,physics_for(inp))
    if control['specification']['design_identity']!=host.store.artifact(source)['trajectory']['design_identity']:
        raise ValueError('HISTORICAL_REFERENCE_DESIGN_CHANGED')
    packet=decision_packet(host)
    check=experiment_preflight(host,candidate,'nmpc')
    if check['admitted']:raise ValueError('HISTORICAL_S56_REPEAT_NOT_BLOCKED')
    preflight=dict(status='prepared_without_provider_send',candidate=candidate,history=history,parents=parents,
        repeated_reference_preflight=check,decision_packet=packet,provider_requests=state(host)['pilot']['live_model_requests'],
        backend_launches=host.store.remaining()['used']['backend_solves'],source_freeze=state(host)['freeze'],
        dependency=dependency_identity(os.environ['SOROSIM_ROOT']),
        environment={k:os.environ.get(k) for k in ('PYTHONPATH','SOROSIM_ROOT','OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')},
        tool_schemas=dict(research_plan=Plan.model_json_schema(),research_rl=RLRequest.model_json_schema()),
        controller_prepared_without_launch=control['identity'],credentials_present=True)
    save(host,preflight,'s58_provider_free_preflight')
    atomic_json(host.store.root/'s58_preflight.json',preflight)
    atomic_json(host.store.root/'s58_initial_research_packet.json',packet)
    update(host,s58_prepared=True)
    return host


def export(host, blocker=None):
    s=state(host);events=host.store.events(host.run_id)
    actions=[];reads=[]
    for event in events:
        if event['kind']=='model_original_tool_request':
            use=host.store.artifact(event['outputs'][0])['tool_use']
            actions.append(dict(tool_use=use,prior_evidence_reads=list(reads)))
            if use['name']=='evidence_read':reads.append(use['input'])
        elif event['kind']=='model_original_tool_feedback' and actions:
            actions[-1]['feedback']=host.store.artifact(event['outputs'][0])['result']
    results=[dict(reference=r,**result_view(host,r)) for r in [*s['results'],*s.get('physical_replays',[]),*s.get('rl_evaluations',[])]]
    audit=dict(engineering_actions=['saved-state projection audit','historical reference materialization','sealed history and continuation import','provider-free preflight'],
        agent_actions=actions,classification='Only original model tool requests are Agent-selected; numerical tools and evaluator are deterministic.',
        source_freeze=s.get('freeze'),historical_experiments=s.get('historical_experiments',[]))
    summary=dict(study_id=host.run_id,source_freeze=s.get('freeze'),research_status=s['research_status'],
        selected=s.get('selected'),selected_solution=s.get('selected_solution'),final_disposition=s.get('final_disposition'),
        provider_requests=s['pilot']['live_model_requests'],live_tool_counts={name:sum(a['tool_use']['name']==name for a in actions) for name in sorted({a['tool_use']['name'] for a in actions})},
        results=results,resource_use=host.store.remaining(),numerical_s=s['numerical_s'],
        nmpc_launches=s.get('nmpc_launches',0),physical_replay_launches=s.get('physical_replay_launches',0),
        offline_nlp=s['offline_nlp'],mathematical_replays=s['bdf_replays'],mathematical_analyses=s.get('mathematical_evaluations',0),
        rl=rl.allocation_feedback(host),blocker=blocker,pending_science=s.get('pending'),pending_provider=pending(host))
    save(host,audit,'s58_decision_audit');save(host,summary,'s58_delivery_summary')
    core.export(host,DEST/'study')
    atomic_json(DEST/'preflight.json',read(host.store.root/'s58_preflight.json'))
    atomic_json(DEST/'initial_research_packet.json',read(host.store.root/'s58_initial_research_packet.json'))
    atomic_json(DEST/'summary.json',summary);atomic_json(DEST/'decision_audit.json',audit)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('results','rl')}),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['projection','prepare','live','export'])
    args=parser.parse_args()
    if args.phase=='projection':
        result=projection_audit();print(json.dumps(dict(rows=result['rows'],elapsed_s=result['elapsed_s'])))
        return
    if args.phase=='export':
        name=read(SPEC)['study_id'];export(Host(ROOT/'runs/research'/name,name,actor='unified-research'));return
    host=prepare()
    if args.phase=='prepare':return
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise ValueError('CLEAN_COMMITTED_SOURCE_REQUIRED_BEFORE_LIVE')
    blocker=None
    try:asyncio.run(converse(host))
    except Exception as exc:
        blocker=dict(error_type=type(exc).__name__,reason=str(exc))
        save(host,blocker,'s58_live_blocker')
    export(host,blocker)


if __name__=='__main__':main()
