"""Trusted adapters over existing tools. Called only by the workbench worker."""
from pathlib import Path
from schemas.workbench import WorkbenchResult
from tools.spec_tools import ROOT, load_yaml, validate_design
from tools.state_io import read


def execute(name, arguments, root, folder, state):
    from tools.workbench_catalog import DESIGN_TOOLS
    if name in DESIGN_TOOLS:
        from tools.design_actions import execute as design_execute
        return design_execute(name, arguments, root, folder, state)
    request = state['request']
    def completed(data, artifacts=()):
        return WorkbenchResult(status='completed', tool=name, data=data,
                               artifacts=[str(Path(p).relative_to(root).as_posix()) for p in artifacts])

    if name == 'read_evidence':
        ref = state['evidence'][arguments['evidence_id']]
        return completed({'evidence_id': arguments['evidence_id'], 'content': read(root / ref['path'])})

    if name in ('inspect_task', 'analyze_design'):
        from tools.task_contract_tools import resolve_task_contract
        from tools.capability_resolver import resolve_capability
        from tools.design_compiler import build_robot_ir
        resolved = resolve_task_contract(ROOT / request['task'])
        design = validate_design(load_yaml(root / 'inputs/design.yaml'))
        resolution = resolve_capability(design, ('analyze_workspace', 'plan_pcc_reach', 'compile_mujoco', 'run_task'), grammar=resolved.grammar)
        if resolution.state.value not in ('SUPPORTED', 'PARAMETRICALLY_SUPPORTED'):
            return WorkbenchResult(status='capability_missing', tool=name, failure_code='CAPABILITY_MISSING',
                                   message=resolution.reason, data=resolution.model_dump(mode='json'))
        if name == 'inspect_task':
            return completed(dict(contract=resolved.reference_view(), design=design.model_dump(mode='json'),
                                  capability=resolution.model_dump(mode='json'), controller='C1'))
        from tools.pcc_math import pcc_sensitivity
        result = pcc_sensitivity(build_robot_ir(design), 0., 0.)
        return completed(result.model_dump(mode='json'))

    if name == 'evaluate_design':
        if request.get('replay'):
            run = root / request['replay']['path']
            gate = read(run / 'gate_summary.json')
            return completed(dict(run=request['replay']['path'], final_status=read(run / 'run.json')['final_status'],
                                  canonical_task_status=gate['canonical_result'], evidence_role='historical_replay',
                                  current_task_status='NOT_RUN', original_run=request['replay']['origin'],
                                  trajectory_available=(run / 'trajectory.json.gz').exists(),
                                  metrics=read(run / 'metrics.json'), backend_solves=0), [run / 'run.json', run / 'gate_summary.json'])
        from tools.harness import run_reach
        run = run_reach(task_package=ROOT / request['task'], design_path=root / 'inputs/design.yaml',
                        run_root=folder / 'execution', controller_level=arguments['controller'], record_trajectory=True)
        gate = read(run.path / 'gate_summary.json')
        if gate['canonical_result'] == 'NOT_RUN':
            return WorkbenchResult(status='failed', tool=name, failure_code=run.record.failure_code or 'TOOL_ERROR',
                                   message='Harness 未完成 canonical 评价；查看原门控和错误证据',
                                   data=dict(run=str(run.path.relative_to(root).as_posix()), canonical_task_status='NOT_RUN'),
                                   artifacts=[(run.path / 'gate_summary.json').relative_to(root).as_posix()])
        return completed(dict(run=str(run.path.relative_to(root).as_posix()), final_status=run.record.final_status,
                              canonical_task_status=gate['canonical_result'],
                              trajectory_available=(run.path / 'trajectory.json.gz').exists(),
                              metrics=read(run.path / 'metrics.json') if (run.path / 'metrics.json').exists() else {},
                              execution_completed=gate['canonical_result'] != 'NOT_RUN'), [run.path / 'run.json', run.path / 'gate_summary.json'])

    evaluation = next(a['result']['data'] for a in reversed(state['attempts'])
                      if a['tool'] == 'evaluate_design' and a.get('result', {}).get('status') == 'completed')
    run = root / evaluation['run']
    if name == 'diagnose':
        source = run / 'diagnostic_summary.json'
        if not source.exists():
            source = run / 'gate_summary.json'
        return completed(dict(canonical_task_status=evaluation['canonical_task_status'],
                              diagnostics=read(source), failure_attribution='UNKNOWN'), [source])
    if name == 'observe':
        if not evaluation['trajectory_available']:
            return WorkbenchResult(status='capability_missing', tool=name, failure_code='CAPABILITY_MISSING',
                                   message='没有完整保存轨迹；参见 gate_summary.json 和 error.json')
        return completed(dict(backend_solves=0, observer='tools.observation_viewer.ObservationViewer'), render_observation(run, folder))
    raise ValueError('Unknown adapter')


def render_observation(run, folder):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from tools.observation_viewer import ObservationViewer
    viewer = ObservationViewer([run])
    try:
        viewer.seek(viewer.times[-1])
        png = viewer.snapshot(path=folder / 'curves.png')
        gif = viewer.export(path=folder / 'motion.gif')
    finally:
        plt.close(viewer.figure)
    return [png, gif]
