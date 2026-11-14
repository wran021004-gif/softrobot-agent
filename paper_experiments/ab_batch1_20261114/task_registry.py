"""Original local task inputs only; no selected FULL candidates or control gains."""
import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAMES = dict(T01='T01_M1_reach_hold', T02='T02_M2_loaded_hold', T03='T03_M3_fast_reach',
             T04='T04_figure_eight_tracking', T05='T05_M5_tool_axis', T06='T06_M6_loaded_scan',
             T07='T07_C1_four_tendon', T08='T08_P3_progressive_stiffness',
             T09='T09_spring_button', T10='T10_M7_impact_recovery')
BATCH2 = ['T02', 'T03', 'T05', 'T06', 'T08', 'T09', 'T10']


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def source(task):
    return ROOT / 'paper_experiments/ten_task_codex_solve_20261112' / NAMES[task]


def inputs(task):
    if task == 'PHS-2D':
        spec = read(ROOT / 'runs/psd2d-core-only-20261112/fresh-store/resolved_configuration.json')
        return spec['configuration'], spec['family_space'], None
    directory = source(task)
    spec = read(directory / 'RESOLVED_STUDY_CONFIG.json')
    space = read(directory / 'FAMILY_SPACE.json')
    # Open the generator's declared legal domain; retain task-specific bounds
    # (notably T08's passive domain), rather than forcing the active-task range.
    lo, hi = space['segment_count_bounds']
    space['executable_segment_counts'] = list(range(lo, hi + 1))
    space['executable_tendon_count_bounds'] = space['tendon_count_bounds']
    protocol_path = (ROOT / 'paper_experiments/five_task_completion_20261113' / NAMES[task]
                     if task in ('T01', 'T04', 'T07') else directory) / 'TASK_PROTOCOL.json'
    return deepcopy(spec['configuration']), space, read(protocol_path)


def controller(task, condition, frozen_task):
    from tools.research.config import controller_configuration
    if task == 'T10':
        # The descriptor admits the existing native feedback execution route.
        # Its automatic prepare/LQR constructor is NEVER instantiated by this runner.
        from extensions.tendon_family.native_feedback import NativeFeedbackControl
        return dict(extension_id='controller.native_state_feedback', version='1.0.0',
                    parameters=dict(contract='family.native_feedback_control', version='1.0.0',
                                    data=NativeFeedbackControl().model_dump(mode='json')))
    original = read(source(task) / ('TASK_' + condition + '.json'))
    original['task'] = frozen_task
    return controller_configuration(read(source(task) / ('CONTROL_' + condition + '.json')), original)
