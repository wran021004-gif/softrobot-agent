"""Development task definitions, independent of frozen benchmark TaskSpec."""
from typing import Literal
from pydantic import Field, model_validator
from schemas.common import Contract


class TaskInstance(Contract):
    version: Literal['round4_development_v1'] = 'round4_development_v1'
    family: Literal['reach_free', 'reach_obstacle', 'tip_stability_external_force']
    split: Literal['development', 'evaluation']
    seed: int = Field(ge=0)
    target_frame: Literal['world'] = 'world'
    target_m: tuple[float,float,float]
    package: str
    initial_state: Literal['zero_joint_position_and_velocity'] = 'zero_joint_position_and_velocity'
    duration_s: Literal[2.] = 2.
    evaluation_start_s: float = Field(ge=0,lt=2)
    tolerance_m: float = Field(gt=0)
    disturbance: dict | None = None
    authority: Literal['DEVELOPMENT_ONLY_NOT_BENCHMARK_APPROVAL'] = 'DEVELOPMENT_ONLY_NOT_BENCHMARK_APPROVAL'

    @model_validator(mode='after')
    def semantics(self):
        expected='tests/fixtures/reach_window_dev' if self.family=='reach_obstacle' else 'tasks/reach_free'
        if self.package != expected:
            raise ValueError('Task family must reference its declared source package')
        if (self.split == 'development' and not 0 <= self.seed < 1000 or
            self.split == 'evaluation' and not 10000 <= self.seed < 11000):
            raise ValueError('Disjoint fixed seed partitions required')
        if self.family == 'tip_stability_external_force':
            d=self.disturbance
            if not d or d.get('coordinate_frame')!='world' or d.get('body')!='segment_7':
                raise ValueError('World external tip-body force required; base motion is a different task')
            if not 0 <= d['start_s'] < d['end_s'] <= 2 or len(d['force_n'])!=3:
                raise ValueError('Invalid disturbance interval/vector')
            import math
            if any(not math.isfinite(v) or abs(v)>5 for v in d['force_n']):
                raise ValueError('Finite bounded external forces required')
        elif self.disturbance is not None:
            raise ValueError('Disturbance only belongs to external-force stability family')
        return self
