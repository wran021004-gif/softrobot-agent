"""One nonbaseline robot per backend through public Host tools; no LLM or search."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from examples.platform_fixtures import reach_input, project, binding, payload, budget
from extensions.robot_domain.contracts import RodDesign
from tools.platform_host import Host
from tools.platform_store import Store
from tools.state_io import atomic_json

CHANGES = {'design.total_length_m': .32, 'design.body_radius_m': .019,
    'design.tendon_routing_radius_m': .016, 'physics.line_density_kg_m': 1.1,
    'physics.root_ei_nm2': .0042, 'physics.bending_viscosity_nm2_s': .004,
    'physics.natural_total_angle_rad': .05, 'physics.tendon_servo_kp_n_per_m': 1200.,
    'physics.tendon_force_limit_n': 22., 'controller.bend_z_rad': .9, 'controller.bias_fraction': .005}


def session_input(backend):
    inp = reach_input('domain-' + backend, backend)
    inp['robot']['structure'] = payload('domain.rod_design', RodDesign().model_dump(mode='json'))
    inp['robot']['assumptions'] = ['Existing equivalent_rod_v2; uncalibrated; fixed single section and eight-segment grid']
    inp['robot']['sources'] = ['physics_contracts/equivalent_rod_v2.md']
    inp['policy']['candidate_builder'] = binding('candidate.rod_design', 'domain.empty')
    inp['policy']['editable'] = {
        'design.total_length_m': [.25, .35], 'design.body_radius_m': [.018, .025],
        'design.tendon_routing_radius_m': [.012, .02], 'physics.line_density_kg_m': [.5, 2.],
        'physics.root_ei_nm2': [.002, .008], 'physics.bending_viscosity_nm2_s': [.002, .008],
        'physics.natural_total_angle_rad': [-.1, .1], 'physics.tendon_servo_kp_n_per_m': [800., 1600.],
        'physics.tendon_force_limit_n': [10., 30.], 'controller.bend_z_rad': [.5, 1.2], 'controller.bias_fraction': [0., .01]}
    inp['policy']['allowed_tools'] = []
    inp['policy']['tool_bindings'] = {name: '1.0.0' for name in
        ('simulation.run', 'evaluation.run', 'signals.read', 'evidence.read', 'visualization.saved_replay')}
    inp['policy']['tool_bindings'].update({'diagnostics.saved_trajectory': '2.0.0', 'diagnostics.signal_rule': '2.0.0'})
    inp['policy']['budget'] = budget(tool_calls=20, backend_solves=1, wall_s=300.)
    inp['policy']['timeout_s'] = 60.
    return inp


def prepare(root):
    root = Path(root).resolve()
    directory = root / 'inputs'
    directory.mkdir(parents=True, exist_ok=False)
    config = project()
    config['authorization_source'] = '用户本轮公共平台领域接入授权：一个非基线候选，每个既有后端各一次短求解'
    config['budget'] = budget(tool_calls=50, backend_solves=2, wall_s=700.)
    atomic_json(directory / 'project.json', config)
    for backend in ('mujoco', 'matlab'):
        atomic_json(directory / (backend + '.json'), session_input(backend))
    atomic_json(directory / 'simulation.json', dict(request_id='domain-solve', tool_id='simulation.run',
        tool_version='1.0.0', arguments=dict(candidate_id='nonbaseline', changes=CHANGES),
        cache='new', reason='One nonbaseline candidate; existing physical definition and score unchanged'))
    return dict(inputs=str(directory))


def run(root, backend):
    root = Path(root).resolve()
    read = lambda name: json.loads((root / 'inputs' / name).read_text(encoding='utf8'))
    store = Store(root)
    if not store.db.exists():
        store.create(read('project.json'))
    inp = read(backend + '.json')
    host = Host(root, inp['run_id'])
    with store.connect(True) as db:
        exists = db.execute('SELECT 1 FROM sessions WHERE run_id=?', (host.run_id,)).fetchone()
    if not exists:
        host.create(inp)
    record = dict(backend=backend, run_id=host.run_id, changes=CHANGES, receipts={})
    report_path = root / (backend + '_record.json')

    def keep(name, request):
        receipt = host.invoke(request)
        record['receipts'][name] = receipt
        atomic_json(report_path, record)
        if receipt['execution_status'] != 'completed':
            raise ValueError(name + ': ' + str(receipt))
        return receipt

    def call(name, tool, arguments):
        return keep(name, dict(request_id='domain-' + name, tool_id=tool,
            tool_version=inp['policy']['tool_bindings'][tool], arguments=arguments, reason='Saved result reuse; no new dynamics'))

    simulation = keep('simulation', read('simulation.json'))
    if simulation['solver_status'] != 'completed':
        raise ValueError('SOLVER_NOT_COMPLETE; saved receipt retained')
    source = dict(result=simulation['output'], execution_id=simulation['execution_id'])
    evaluation = call('evaluation', 'evaluation.run', source)
    phase = 'sampled_state' if backend == 'matlab' else 'pre_step_solver'
    call('signal', 'signals.read', dict(result=simulation['output'], name='actuator_force', entity='tendon_0', phase=phase))
    diagnosis = call('diagnosis', 'diagnostics.saved_trajectory', {**source, 'entity': 'all'})
    call('rule', 'diagnostics.signal_rule', source)
    call('replay', 'visualization.saved_replay', source)
    outcome = store.artifact(evaluation['output'])
    product = store.artifact(diagnosis['output'])
    # Read the archived compile/export values through the platform evidence API.
    data = store.session(host.run_id)['state']['result_executions'][simulation['execution_id']]
    candidate = call('candidate', 'evidence.read', dict(reference=data['candidate_input'], pointer='/effective/robot/structure/data'))
    record.update(evaluation=outcome, diagnosis=product, candidate=store.artifact(candidate['output'])['content'],
        usage=store.remaining(host.run_id), report=str(report_path))
    atomic_json(report_path, record)
    return dict(report=str(report_path), task_success=outcome['task_success'], usage=record['usage']['used'])


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'run'])
    parser.add_argument('root', type=Path)
    parser.add_argument('--backend', choices=['mujoco', 'matlab'], default='mujoco')
    args = parser.parse_args()
    print(json.dumps(prepare(args.root) if args.action == 'prepare' else run(args.root, args.backend), ensure_ascii=False, indent=2))
