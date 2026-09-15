"""One-shot adapters retain existing numerical executors and scientific sources."""
from pathlib import Path
import gzip
import json
from schemas.platform import BackendResult, Payload, Signal, SignalSpec
from schemas.task_spec import TaskSpec
from schemas.environment_spec import EnvironmentSpec
from schemas.settings import RunSettings
from tools.task_context import TaskContext
from extensions.reference.contracts import LegacyData


class LegacyController:
    def __init__(self, parameters, period_s):
        self.parameters, self.period_s = parameters, period_s


class MujocoBackend:
    name = 'mujoco'
    phase = 'post_step'

    @staticmethod
    def check(inp, parameters, control):
        from tools.spec_tools import load_simulator, load_task_package
        _, original_env = load_task_package()
        if inp.task.environment.data != original_env.model_dump(mode='json'):
            raise ValueError('LEGACY_ENVIRONMENT_EXTENSION_REQUIRED: 当前适配保留原环境')
        if inp.task.timing.timestep_s != load_simulator().timestep_s:
            raise ValueError('LEGACY_TIMESTEP_ADAPTER_REQUIRED')
        if inp.task.timing.control_period_s != inp.task.timing.timestep_s or inp.task.timing.sample_period_s != inp.task.timing.timestep_s:
            raise ValueError('LEGACY_CONTROL_AND_SAMPLE_PERIOD_MUST_EQUAL_TIMESTEP')
        if inp.task.initializer.extension_id != 'initialize.legacy_zero':
            raise ValueError('LEGACY_INITIALIZER_UNSUPPORTED')

    def __init__(self):
        self.executor = None

    def compile(self, inp, reg):
        self.inp, self.reg = inp, reg
        self.ir = reg.parse(inp.robot.structure)

    def initialize(self, initial, controller):
        self.initial, self.controller = initial, controller

    def run(self, folder, timeout_s):
        from tools.reach_dynamics import DynamicsBackends
        from tools.spec_tools import load_task_package
        old_task, _ = load_task_package()
        inp = self.inp
        goal = self.reg.parse(inp.task.goal)
        evaluator = self.reg.parse(inp.task.evaluator.parameters)
        task = TaskSpec.model_validate({**old_task.model_dump(mode='json'), 'task_id': inp.task.task_id,
            'target_m': list(goal.target_m), 'position_error_max_m': evaluator.tolerance_m})
        context = TaskContext(task=task, environment=EnvironmentSpec.model_validate(inp.task.environment.data),
            run_settings=RunSettings(steps=round(inp.task.timing.duration_s / inp.task.timing.timestep_s), random_seed=inp.seed,
                provenance=inp.task.source), timestep_s=inp.task.timing.timestep_s, authority=inp.task.source)
        self.executor = DynamicsBackends()
        original = self.executor.simulate(self.name, self.ir, self.controller.parameters, folder,
            timeout_s=timeout_s, task_context=context)
        rows = json.loads(gzip.decompress((folder / 'trajectory.json.gz').read_bytes()))
        signals = []
        if rows and all('tip_m' in row for row in rows):
            signals.append(Signal(spec=SignalSpec(name='tip_position', entity='tip', dimension=3, units='m', frame='world', phase=self.phase),
                times_s=[r['time_s'] for r in rows], values=[r['tip_m'] for r in rows]))
        self.result = BackendResult(solver_status='completed' if original['complete'] else 'failed',
            backend_id='backend.' + self.name, model_id=original['model_id'], signals=signals,
            data=Payload(contract='legacy.backend_data', data=LegacyData(backend=self.name, original=original,
                exported_files=sorted(p.name for p in folder.iterdir() if p.is_file())).model_dump(mode='json')),
            limitations=original.get('omissions', []) + ['未标定数值模型；原始导出和求解证据保留。'], initial_state=self.initial, seed=inp.seed)
        return self.export()

    def export(self):
        if not hasattr(self, 'result'):
            raise ValueError('BACKEND_RESULT_NOT_AVAILABLE')
        return self.result

    def cancel(self):
        raise ValueError('ONE_SHOT_CANCELLATION_NOT_GUARANTEED: 查看后端时间覆盖声明')

    def close(self):
        if self.executor:
            self.executor.close()


class MatlabBackend(MujocoBackend):
    name = 'matlab'
    phase = 'sampled_state'

    @staticmethod
    def check(inp, parameters, control):
        MujocoBackend.check(inp, parameters, control)
        if abs(control.bend_y_rad) > 1e-8:
            raise ValueError('MATLAB_PLANAR_ONLY')
