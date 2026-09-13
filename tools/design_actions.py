"""Trusted candidate adapters, using the existing Harness and saved-data viewer."""
from pathlib import Path
import yaml
from schemas.workbench import WorkbenchResult
from tools.spec_tools import ROOT, load_yaml
from tools.state_io import read, atomic_json, digest
from tools.design_session import candidate, evaluation, summary


def execute(name, arguments, root, folder, state):
    def output(data, artifacts=(), status='completed', failure_code=None, message=''):
        return WorkbenchResult(tool=name, status=status, failure_code=failure_code, message=message, data=data,
                               artifacts=[Path(p).relative_to(root).as_posix() for p in artifacts])
    if name == 'create_candidate':
        parent = candidate(state, arguments['parent_id'])
        design = {**parent['design'], **arguments['changes']}
        path = folder / 'design.yaml'
        path.write_text(yaml.safe_dump(design), encoding='utf-8')
        c = dict(candidate_id=f'c{len(state["candidates"]):03d}', parent_id=parent['candidate_id'], design=design,
                 design_hash=digest(design), path=path.relative_to(root).as_posix(), changes=arguments['changes'])
        atomic_json(folder / 'candidate.json', c)
        return output({'candidate': c}, [path, folder / 'candidate.json'])
    if name == 'compare_candidates':
        rows = [r for r in summary(state)['candidates'] if r['candidate_id'] in arguments['candidate_ids']]
        rows.sort(key=lambda r: (r['canonical_task_status'] != 'PASS', r['position_error_m']))
        return output(dict(ranked=rows, best_candidate_id=rows[0]['candidate_id'], authority='original canonical evaluator'),
                      [root / r['evaluation_ref'] for r in rows])
    c = candidate(state, arguments['candidate_id'])
    design_path = root / c['path']
    if name == 'check_candidate':
        from tools.design_envelope import validate_envelope_design
        from tools.design_compiler import build_robot_ir
        from tools.capability_resolver import resolve_capability
        from tools.pcc_math import pcc_sensitivity
        design = validate_envelope_design(load_yaml(design_path), read(root / 'inputs/task_context.json')['envelope'])
        resolution = resolve_capability(design, ('analyze_workspace', 'plan_pcc_reach', 'compile_mujoco', 'run_task'))
        if resolution.state.value not in ('SUPPORTED', 'PARAMETRICALLY_SUPPORTED'):
            return output(dict(candidate_id=c['candidate_id'], design_hash=c['design_hash']), status='capability_missing',
                          failure_code=resolution.state.value, message=resolution.reason)
        ir = build_robot_ir(design)
        (folder / 'robot_ir.yaml').write_text(yaml.safe_dump(ir.model_dump(mode='json')), encoding='utf-8')
        return output(dict(candidate_id=c['candidate_id'], design_hash=c['design_hash'], design=design.model_dump(mode='json'),
                           capability=resolution.model_dump(mode='json'), pcc_local_analysis=pcc_sensitivity(ir, 0., 0.).metrics), [folder / 'robot_ir.yaml'])
    if name == 'evaluate_candidate':
        from tools.harness import run_reach
        run = run_reach(task_package=ROOT / state['request']['task'], design_path=design_path, run_root=folder / 'execution',
                        experiment_path=root / 'inputs/experiment.yaml', controller_level='C1', record_trajectory=True,
                        experiment_context=dict(candidate_id=c['candidate_id'], design_hash=c['design_hash'],
                                                parent_id=c['parent_id'], workbench=root.name))
        gate = read(run.path / 'gate_summary.json')
        metrics = read(run.path / 'metrics.json') if (run.path / 'metrics.json').exists() else {}
        diagnostic = read(run.path / 'diagnostic_summary.json') if (run.path / 'diagnostic_summary.json').exists() else {}
        error = read(run.path / 'error.json') if (run.path / 'error.json').exists() else None
        data = dict(candidate_id=c['candidate_id'], design_hash=c['design_hash'], run=run.path.relative_to(root).as_posix(),
                    evidence_role='new_computation', canonical_task_status=gate['canonical_result'],
                    position_error_m=metrics.get('mujoco', {}).get('position_error_m'),
                    predicted_position_error_m=metrics.get('model', {}).get('predicted_position_error_m'),
                    actual_tip_m=metrics.get('mujoco', {}).get('tip_position_m'),
                    model_tip_m=metrics.get('model', {}).get('predicted_tip_m'),
                    final_status=run.record.final_status, failure_code=run.record.failure_code,
                    stopped_by=gate['stopped_by'], error=error,
                    diagnostics={k: dict(status=v['status'], failure_code=v.get('failure_code'),
                                         metrics={key: value for key, value in v['metrics'].items()
                                                  if value is None or isinstance(value, (str, int, float, bool))})
                                 for k, v in diagnostic.get('diagnostics', {}).items()},
                    failure_attribution='UNKNOWN', trajectory_available=(run.path / 'trajectory.json.gz').exists())
        artifacts = [run.path / n for n in ('run.json', 'gate_summary.json', 'mujoco_result.json', 'diagnostic_summary.json', 'error.json') if (run.path / n).exists()]
        return output(data, artifacts, status='completed' if gate['canonical_result'] != 'NOT_RUN' else 'failed',
                      failure_code=run.record.failure_code, message=str(error or run.record.final_status))
    if name == 'observe_candidate':
        ev = evaluation(state, c['candidate_id'])['result']['data']
        if not ev.get('trajectory_available'):
            return output(dict(candidate_id=c['candidate_id'], backend_solves=0), status='capability_missing',
                          failure_code='NO_TRAJECTORY', message='没有可用轨迹；计算与任务成绩请查看评价证据')
        from tools.workbench_actions import render_observation
        return output(dict(candidate_id=c['candidate_id'], backend_solves=0), render_observation(root / ev['run'], folder))
    raise ValueError('Unknown design tool')
