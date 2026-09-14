"""Small, explicit framework acceptance. --real runs 140 MuJoCo steps total."""
import argparse
import json
from pathlib import Path
import sys
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.spec_tools import ROOT
from tools.state_io import read,atomic_json
from tools.artifact_tools import file_hash

CALLER=dict(actor_id='framework-native-acceptance',origin='agent',transport='offline_native_fixture')


def native(session,name,args):
    from tools.public_catalog import native_tools
    definition=next(t['function'] for t in native_tools('services') if t['function']['name']==name)
    result=session.apply_tool_call(dict(name=definition['name'],arguments=json.dumps({**args,
        'reason':'Framework extension acceptance','evidence':[]})),caller=CALLER)
    assert result['execution_status']=='completed',result
    return result


def config(mode,task_path):
    from schemas.design_spec import DesignSpec
    from schemas.exploration import ExplorationControl
    from tools.task_context import development_context
    return dict(authorization='User request: small real framework acceptance, 2026-09-14',
        permissions=['simulate'],backends=['mujoco'],controller_modes=[mode],
        controller_id='open_loop_length' if mode=='C1' else 'pcc_tip_feedback',
        task_context=development_context(task_path),
        design=DesignSpec(robot_family='tendon_driven_continuum',sections=1,segments=8,total_length_m=.3,
            body_radius_m=.02,tendon_count=4,tendon_routing_radius_m=.018),
        control=ExplorationControl(mode=mode),bounds={'control.bend_z_rad':[-1.5,1.5]},
        max_evaluations=2 if mode=='C1' else 1,max_calls=6,wall_s=30.,per_evaluation_timeout_s=10.)


def saved_views(root,source,outcome,label):
    from tools.public_services import ServiceSession
    from tools.dynamic_view import render_candidate
    folder=Path(outcome.evidence_ref).parent
    refs=[(folder/name).as_posix() for name in ('result.json','shared_input.json','trajectory.json.gz')]
    session=ServiceSession(root/label)
    session.create(dict(profile_id=label,permissions=['read_evidence'],tool_calls=4),source_root=source,evidence_refs=refs)
    r=native(session,'diagnostics__signal_rule',dict(result_ref=refs[0],backend='mujoco'))
    d=native(session,'diagnostics__saved_trajectory',dict(result_ref=refs[0],backend='mujoco',entity='all'))
    diagnosis=read(session.root/d['details_ref'])
    # Display reuses the already sealed diagnostic output. No diagnostic rerun.
    atomic_json(session.root/folder/'diagnosis.json',diagnosis)
    result=read(session.root/refs[0]);shared=read(session.root/folder/'shared_input.json')
    c=dict(candidate_id=label,design={'total_length_m':shared['length']},control=shared['control'],results={'mujoco':result})
    page=render_candidate(session.root,c,'mujoco')
    payload=json.loads(page.read_text(encoding='utf8').split('const D=',1)[1].split(';const rows=',1)[0])
    assert payload['target_m']==shared['task_context']['task']['target_m']
    assert payload['declared_duration_s']==shared['duration']
    assert abs(diagnosis['numerical']['remaining_duration_s'])<1e-9
    return dict(rule_result=r,diagnostic_result=d,target_m=payload['target_m'],duration_s=payload['declared_duration_s'],
        last_time_s=diagnosis['numerical']['last_valid_time_s'],html=str(page.relative_to(root)),html_sha256=file_hash(page))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--real',action='store_true')
    parser.add_argument('--output',type=Path);parser.add_argument('--history-root',type=Path,default=ROOT/'runs/round9_reach')
    args=parser.parse_args();root=(args.output or ROOT/'runs/framework_acceptance'/uuid4().hex).resolve()
    from tools.public_services import ServiceSession
    s=ServiceSession(root/'math');s.create(dict(profile_id='framework-math',permissions=['analysis','read_evidence'],tool_calls=4))
    result=native(s,'analysis__pcc_condition',dict(length_m=1.,bend_rad=[0.,0.]))
    cache=native(s,'analysis__pcc_condition',dict(length_m=1.,bend_rad=[0.,0.]))
    page=native(s,'evidence__read_json',dict(evidence_ref=result['details_ref'],pointer='/singular_values_m_per_rad'))
    assert cache['cost']['cache_hit'] and read(s.root/page['details_ref'])['content']==[.5,.5]
    report=dict(baseline='1a0081b6822ccf802cfd08ce8d1ecb9c5049a69b',root=str(root),
        math=dict(validation_type='actual isolated math + offline native provider response',result=result,read=page,cache=cache),
        real_backend=[],model_api_calls=0,matlab_dynamic_solves=0,limitations=['No live LLM API decision; native adapter uses an explicit provider-response fixture.'])
    if args.history_root.exists():
        state=read(args.history_root/'state.json')
        eligible=[c['results']['matlab'] for c in state['candidates'] if c.get('results',{}).get('matlab',{}).get('complete')]
        if eligible:
            old=eligible[0];folder=Path(old['result_ref']).parent
            refs=[(folder/name).as_posix() for name in ('result.json','shared_input.json','trajectory.json.gz')]
            h=ServiceSession(root/'historical_signals');h.create(dict(profile_id='saved-matlab-only',permissions=['read_evidence'],tool_calls=2),
                source_root=args.history_root,evidence_refs=refs)
            report['saved_data_reuse']=dict(validation_type='hash-verified saved MATLAB signals; zero new solves',
                result=native(h,'diagnostics__signal_rule',dict(result_ref=refs[0],backend='matlab')))
    if args.real:
        from tools.evaluation_runtime import EvaluationSession
        from tools.optimization_interfaces import ParameterSpace
        from tools.search_runtime import search
        for mode,task_path in (('C1','reach_dev.yaml'),('C2','reach_dev_shifted.yaml')):
            cfg=config(mode,ROOT/'configs/framework'/task_path);runtime=EvaluationSession(root/mode);runtime.create(cfg)
            try:
                if mode=='C1':
                    space=ParameterSpace(['control.bend_z_rad'],cfg['bounds'])
                    study=search(runtime.root/'search.json',space,{'control.bend_z_rad':cfg['control'].bend_z_rad},runtime,max_trials=2)
                    outcome=runtime.evaluate(study['trials'][0]['parameters'],'saved-validation')
                    assert outcome.actual_evaluations==0
                    report['search']=dict(method='bounded_coordinate_pattern_local_v1; Python adapter of existing MATLAB proposal formula',
                        validation_type='two real MuJoCo evaluations, then cache reuse',study=study)
                else:outcome=runtime.evaluate({})
                assert outcome.status=='VALID',outcome
                out=read(runtime.root/outcome.evidence_ref)
                context=cfg['task_context'];assert out['controller_diagnostics']['lifecycle']=='finished'
                assert out['controller_diagnostics']['steps']==context.run_settings.steps
                import math
                assert abs(outcome.score-math.dist(out['tip_m'],context.task.target_m))<1e-12
                views=saved_views(root,runtime.root,outcome,'views_'+mode)
                report['real_backend'].append(dict(controller=mode,validation_type='real MuJoCo rollout',outcome=outcome.model_dump(mode='json'),
                    controller_diagnostics=out['controller_diagnostics'],ledger=runtime.load()[0]['used'],views=views))
            finally:runtime.close()
    atomic_json(root/'acceptance.json',report)
    print(json.dumps(dict(report=str(root/'acceptance.json'),real_evaluations=sum(r['ledger']['evaluations'] for r in report['real_backend']),
        model_api_calls=0,matlab_dynamic_solves=0),indent=2))


if __name__=='__main__':main()
