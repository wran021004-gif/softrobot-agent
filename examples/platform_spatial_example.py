"""Small public-tool example. Preparation and math never read engine model files."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CHANGES = {'design.total_length_m':.32, 'design.body_radius_m':.019,
           'design.tendon_routing_radius_m':.016, 'controller.bend_y_rad':.5, 'controller.bend_z_rad':.8}


def session_input(backend, mode='C2'):
    from examples.platform_fixtures import reference_input, payload, binding, budget
    from extensions.robot_domain.contracts import RodDesign
    from schemas.exploration import ExplorationControl
    from tools.spec_tools import load_environment, load_task
    from extensions.experiment_dynamics.contracts import Assembly, Mount, TimedForce, Initial
    value = reference_input('spatial-'+backend)
    env, task = load_environment(), load_task()
    assembly = Assembly(environment=env, floor_id=next(o.name for o in env.objects if o.kind == 'plane'),
        mount=Mount(position_m=(.01, -.01, .03), quaternion_wxyz=(math.cos(.075),0.,0.,math.sin(.075))),
        external_forces=(TimedForce(entity='segment_7', force_n=(0.,.2,.1), start_s=.006, end_s=.014),))
    initial = Initial(qpos_rad=tuple([-.003,.002]*8), qvel_rad_s=tuple([0.,.01]*8))
    value['task'].update(task_id='assembled-reach-dev',name='统一场景空间到达短验证',family='task.reach',
        source='本轮授权的独立开发配置；原 reach 容差；短运行不要求达到目标',
        goal=payload('reference.reach_goal',dict(target_m=[.30,.04,.08])),
        environment=payload('experiment.assembly',assembly.model_dump(mode='json')),
        robot_families=['tendon_driven_continuum'],initializer=binding('initialize.experiment','experiment.initial',initial.model_dump(mode='json')),
        evaluator=binding('evaluate.reach','reference.reach_evaluation',dict(tolerance_m=task.position_error_max_m)),
        timing=dict(timestep_s=.002,control_period_s=.002,sample_period_s=.002,duration_s=.02,termination=['duration','numerical_failure']),
        observations=[dict(name='tip_position',entity='tip',dimension=3,units='m',frame='world',phase='post_step')],
        objectives=[dict(metric='position_error',direction='minimize',units='m')],
        sampling=dict(split='development',seeds=[17],window_s=[0.,.02]))
    value['robot'] = dict(family='tendon_driven_continuum',structure=payload('domain.rod_design',RodDesign().model_dump(mode='json')),
        channels=['tendon_target_lengths_m'],units='SI',frame='world_base_x_forward_yz_cross_section',
        assumptions=['equivalent_rod_v2; uncalibrated; single section, eight links, four tendons'],
        sources=['physics_contracts/equivalent_rod_v2.md'],unsupported=['axial extension','shear','material twist','tendon friction','self collision'])
    contract = {'math_spatial':'spatial_parameters','math_planar':'planar_parameters','scene_mujoco':'mujoco_parameters'}[backend]
    value['policy'].update(policy_id='independent-spatial-development',backend=binding('backend.'+backend,'experiment.'+contract),
        controller=binding('controller.experiment_length','legacy.control',ExplorationControl(mode=mode,bend_y_rad=.3,bend_z_rad=.6).model_dump(mode='json')),
        candidate_builder=binding('candidate.rod_design','domain.empty'),search=None,allowed_tools=[],
        tool_bindings={'simulation.run':'1.0.0','evaluation.run':'1.0.0','signals.read':'1.0.0','evidence.read':'1.0.0','diagnostics.sample_exceeds':'1.1.0'},
        editable={'design.total_length_m':[.25,.35],'design.body_radius_m':[.018,.025],
            'design.tendon_routing_radius_m':[.012,.02],'controller.bend_y_rad':[0.,1.],'controller.bend_z_rad':[.5,1.2]},
        budget=budget(tool_calls=12,backend_solves=1,wall_s=240.),timeout_s=180.)
    if backend == 'math_planar':
        value['task']['environment'] = payload('experiment.assembly',Assembly(environment=env,floor_id=assembly.floor_id).model_dump(mode='json'))
        value['task']['initializer'] = binding('initialize.experiment','experiment.initial',Initial().model_dump(mode='json'))
        value['task']['goal']['data']['target_m'][1] = 0.
        value['task']['observations'][0]['phase'] = 'sampled_state'
        value['policy']['controller']['parameters']['data']['bend_y_rad'] = 0.
    return value


def prepare(root, mode='C2'):
    from examples.platform_fixtures import project, budget
    from tools.state_io import atomic_json
    root = Path(root).resolve()
    directory = root/'inputs'; directory.mkdir(parents=True,exist_ok=False)
    config = project()
    config['authorization_source'] = '本轮独立三维数学与同场景物理仿真短验证授权'
    config['budget'] = budget(tool_calls=30,backend_solves=2,wall_s=550.)
    atomic_json(directory/'project.json',config)
    for backend in ('math_spatial','scene_mujoco','math_planar'):
        atomic_json(directory/(backend+'.json'),session_input(backend,mode))
    atomic_json(directory/'simulation.json',dict(request_id='spatial-solve',tool_id='simulation.run',tool_version='1.0.0',
        arguments=dict(candidate_id='spatial-nonbaseline',changes=CHANGES),cache='new',reason='同一非基线设计和装配场景的独立短运行'))
    return dict(inputs=str(directory))


def run(root, backend, blocked=False):
    from tools.platform_store import Store
    from tools.platform_host import Host
    from tools.state_io import atomic_json
    root = Path(root).resolve()
    read = lambda name: json.loads((root/'inputs'/name).read_text(encoding='utf8'))
    store = Store(root)
    if not store.db.exists(): store.create(read('project.json'))
    inp = read(backend+'.json'); host = Host(root,inp['run_id'])
    # A new directory/run is intentional; never silently replay an old solve.
    host.create(inp)
    record = dict(backend=backend,mujoco_import_blocked=blocked,receipts={})
    def invoke(name, request):
        r = host.invoke(request); record['receipts'][name] = r
        atomic_json(root/(backend+'_record.json'),record)
        if r['execution_status'] != 'completed': raise RuntimeError(str(r))
        return r
    request = read('simulation.json')
    if backend == 'math_planar': request['arguments']['changes']['controller.bend_y_rad'] = 0.
    sim = invoke('simulation',request)
    if sim['solver_status'] != 'completed': raise RuntimeError('Solver failed; receipt and partial evidence retained')
    def call(name,tool,args):
        return invoke(name,dict(request_id='spatial-'+name,tool_id=tool,tool_version=inp['policy']['tool_bindings'][tool],
            arguments=args,reason='复用保存结果，无额外动力学求解'))
    ev = call('evaluation','evaluation.run',dict(result=sim['output'],execution_id=sim['execution_id']))
    sig = call('tip','signals.read',dict(result=sim['output'],name='tip_position',entity='tip'))
    call('tension','signals.read',dict(result=sim['output'],name='tendon_tension',entity='tendon_0'))
    call('diagnostic','diagnostics.sample_exceeds',dict(result=sim['output'],signal='tendon_tension',entity='tendon_0',units='N',threshold=10.))
    rd = call('result','evidence.read',dict(reference=sim['output'],pointer='/data/data'))
    record.update(evaluation=store.artifact(ev['output']),tip=store.artifact(sig['output'])['signal'],
        result_data=store.artifact(rd['output'])['content'],usage=store.remaining(host.run_id)['used'],
        loaded_mujoco_modules=[n for n in sys.modules if n == 'mujoco' or n.startswith('mujoco.')])
    if blocked and record['loaded_mujoco_modules']: raise AssertionError('MuJoCo was imported')
    atomic_json(root/(backend+'_record.json'),record)
    return record


def block_mujoco():
    import importlib.abc
    class DenyMujoco(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname == 'mujoco' or fullname.startswith('mujoco.'):
                raise ModuleNotFoundError('MUJOCO_IMPORT_BLOCKED_FOR_INDEPENDENCE_PROOF')
    sys.meta_path.insert(0,DenyMujoco())
    def audit(event,args):
        if event == 'open' and isinstance(args[0],(str,bytes)):
            name = str(args[0]).lower()
            if name.endswith(('.xml','.mjb')):
                raise RuntimeError('ENGINE_MODEL_FILE_ACCESS_BLOCKED: '+name)
    sys.addaudithook(audit)


def compare(root):
    from tools.state_io import atomic_json
    root = Path(root)
    records = [json.loads((root/(b+'_record.json')).read_text(encoding='utf8')) for b in ('math_spatial','scene_mujoco')]
    a,b = records
    for key in ('physics_identity','scene_identity'):
        if a['result_data'][key] != b['result_data'][key]: raise ValueError('COMPARISON_SOURCE_MISMATCH: '+key)
    x,y = a['tip']['values'][-1], b['tip']['values'][-1]
    result = dict(physics_identity=a['result_data']['physics_identity'],scene_identity=a['result_data']['scene_identity'],
        tip_difference_m=math.dist(x,y),records=[dict(backend=r['backend'],final_tip_m=r['tip']['values'][-1],
        evaluation=r['evaluation'],usage=r['usage'],execution=r['receipts']['simulation']['execution_id']) for r in records],
        saved_checks=[verify_saved(root,r) for r in records],
        meaning='不同积分与接触模型的短轨迹差异；不视任一模型为物理真值，不合并不同模型的评价身份')
    atomic_json(root/'comparison.json',result)
    return result


def verify_saved(root, record):
    """Inspect immutable exports only; never compile, integrate or re-evaluate."""
    import gzip
    import numpy as np
    from tools.platform_store import Store
    store = Store(root)
    receipt = record['receipts']['simulation']
    bundles = []
    for event in store.events('spatial-'+record['backend']):
        if event['execution_id'] != receipt['execution_id'] or event['kind'] != 'simulation': continue
        for ref in event['outputs']:
            if ref['media_type'] != 'application/json': continue
            value = store.artifact(ref)
            if isinstance(value,dict) and value.get('result') == receipt['output'] and 'files' in value: bundles.append(value)
    if len(bundles) != 1: raise AssertionError('Unique source export required')
    files = {f['filename']:store.artifact(f['reference'],raw=True) for f in bundles[0]['files']}
    physics,scene = (json.loads(files[n]) for n in ('resolved_physics.json','experiment_scene.json'))
    rows = json.loads(gzip.decompress(files['trajectory.json.gz']))
    saved = store.artifact(receipt['output'])
    signals = saved['signals']
    assert len([s for s in signals if s['spec']['name']=='joint_position']) == 16
    assert len([s for s in signals if s['spec']['name']=='tendon_tension']) == 4
    qdelta = np.array(rows[-1]['qpos_rad'])-np.array(scene['initial']['qpos_rad'])
    assert np.linalg.norm(qdelta[::2]) > 1e-5 and np.linalg.norm(qdelta[1::2]) > 1e-5
    force_times = [r['solver_time_s'] for r in rows if np.linalg.norm(r['external_torque_nm']) > 1e-12]
    assert np.allclose(force_times,[.006,.008,.010,.012])
    assert all(math.isclose(r['time_s']-r['solver_time_s'],.002) for r in rows)
    observations = json.loads(files['controller_observations.json'])
    assert len(observations) == len(rows)
    if record['backend'] == 'scene_mujoco':
        compiled = json.loads(files['compiled_physics.json'])
        np.testing.assert_allclose(compiled['mass_kg'],[p['mass_kg'] for p in physics['parts']],atol=1e-14)
        np.testing.assert_allclose(compiled['com_local_m'],[p['com_local_m'] for p in physics['parts']],atol=1e-14)
        np.testing.assert_allclose(np.sort(compiled['inertia_principal_kg_m2'],axis=1),
            np.sort([np.linalg.eigvalsh(p['inertia_com_local_kg_m2']) for p in physics['parts']],axis=1),atol=1e-14)
        np.testing.assert_allclose(compiled['stiffness_nm_rad'],[k for p in physics['parts'] for k in p['stiffness_nm_rad']])
        np.testing.assert_allclose(compiled['damping_nm_s_rad'],[c for p in physics['parts'] for c in p['damping_nm_s_rad']])
        np.testing.assert_allclose(compiled['initial_qpos'],scene['initial']['qpos_rad'])
        np.testing.assert_allclose(compiled['initial_qvel'],scene['initial']['qvel_rad_s'])
    else:
        assert record['mujoco_import_blocked'] and not record['loaded_mujoco_modules']
        assert not any(name.endswith(('.xml','.mjb')) for name in files)
    assert record['usage']['backend_solves'] == 1
    assert all(r['charged']['backend_solves']==0 for n,r in record['receipts'].items() if n != 'simulation')
    return dict(backend=record['backend'],bundle_verified=True,signal_count=len(signals),
        q_y_change_norm_rad=float(np.linalg.norm(qdelta[::2])),q_z_change_norm_rad=float(np.linalg.norm(qdelta[1::2])),
        active_force_sample_times_s=force_times,controller_observations=len(observations),
        physics_identity=physics['identity'],scene_identity=scene['identity'],extra_backend_solves=0)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','run','compare'])
    parser.add_argument('root',type=Path)
    parser.add_argument('--backend',choices=['math_spatial','scene_mujoco','math_planar'],default='math_spatial')
    parser.add_argument('--control',choices=['C1','C2'],default='C2')
    parser.add_argument('--blocked-child',action='store_true',help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.blocked_child: block_mujoco()
    if args.action == 'prepare': output = prepare(args.root,args.control)
    elif args.action == 'compare': output = compare(args.root)
    elif args.backend.startswith('math_') and not args.blocked_child:
        # Fresh process; all candidate/preflight/assembly/solve/evaluation work is inside it.
        return subprocess.call([sys.executable,str(Path(__file__).resolve()),'run',str(args.root),'--backend',args.backend,'--blocked-child'])
    else: output = run(args.root,args.backend,args.blocked_child)
    print(json.dumps(output,ensure_ascii=False,indent=2))
    return 0


if __name__ == '__main__':
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf8')
    raise SystemExit(main())
