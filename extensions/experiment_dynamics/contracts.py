"""SI inputs and resolved data; no engine imports or solver-owned scene fields."""
from typing import Literal
from pydantic import Field, model_validator
from schemas.common import Contract
from schemas.environment_spec import EnvironmentSpec, Vec3

Matrix3 = tuple[Vec3, Vec3, Vec3]


class Part(Contract):
    entity: str
    parent: str
    origin_parent_m: Vec3
    length_m: float
    radius_m: float
    mass_kg: float
    com_local_m: Vec3
    inertia_com_local_kg_m2: Matrix3
    joint_axes_local: tuple[Vec3, Vec3] = ((0., 1., 0.), (0., 0., 1.))
    stiffness_nm_rad: tuple[float, float]
    damping_nm_s_rad: tuple[float, float]
    natural_rad: tuple[float, float]


class Tendon(Contract):
    entity: str
    actuator: str
    offset_yz_m: tuple[float, float]
    kp_n_m: float
    force_limit_n: float
    route_entities: tuple[str, ...]


class ResolvedPhysics(Contract):
    version: Literal['equivalent_rod_physics_v1'] = 'equivalent_rod_physics_v1'
    source_ir_identity: str
    source_contracts: tuple[str, ...]
    identity: str
    frame: Literal['body_local_x_forward; inertia_about_com'] = 'body_local_x_forward; inertia_about_com'
    parts: tuple[Part, ...]
    tendons: tuple[Tendon, ...]
    derivation: str


class Mount(Contract):
    robot_id: Literal['robot'] = 'robot'
    mount_id: Literal['fixed_base'] = 'fixed_base'
    parent_frame: Literal['world'] = 'world'
    position_m: Vec3 = (0., 0., 0.)
    quaternion_wxyz: tuple[float, float, float, float] = (1., 0., 0., 0.)

    @model_validator(mode='after')
    def unit_quaternion(self):
        if abs(sum(x*x for x in self.quaternion_wxyz) - 1) > 1e-10:
            raise ValueError('MOUNT_QUATERNION_MUST_BE_UNIT_WXYZ')
        return self


class Initial(Contract):
    # Order: joint_0_y, joint_0_z, ..., joint_7_y, joint_7_z.
    qpos_rad: tuple[float, ...] = Field(default=(0.,)*16, min_length=16, max_length=16)
    qvel_rad_s: tuple[float, ...] = Field(default=(0.,)*16, min_length=16, max_length=16)


class TimedForce(Contract):
    robot_id: Literal['robot'] = 'robot'
    entity: str = Field(pattern=r'^segment_[0-7]$')
    point: Literal['center_of_mass'] = 'center_of_mass'
    frame: Literal['world'] = 'world'
    force_n: Vec3
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)

    @model_validator(mode='after')
    def window(self):
        if self.start_s >= self.end_s:
            raise ValueError('FORCE_WINDOW_MUST_BE_NONEMPTY')
        return self


class Assembly(Contract):
    environment: EnvironmentSpec
    floor_id: str
    mount: Mount = Field(default_factory=Mount)
    external_forces: tuple[TimedForce, ...] = ()


class Scene(Contract):
    version: Literal['rod_experiment_v1'] = 'rod_experiment_v1'
    identity: str
    physics_identity: str
    assembly: Assembly
    initial: Initial
    target_world_m: Vec3
    task_identity: str
    duration_s: float
    sources: tuple[str, ...]


class SpatialParameters(Contract):
    model: Literal['spatial_rigid_link_v1'] = 'spatial_rigid_link_v1'
    solver: Literal['RK45'] = 'RK45'
    rtol: float = Field(default=1e-6, gt=0, le=.001)
    atol: float = Field(default=1e-8, gt=0, le=.00001)
    max_step_s: float = Field(default=.0002, gt=0)
    contact_stiffness_n_m: float = Field(default=5000., gt=0)
    contact_damping_n_s_m: float = Field(default=5., ge=0)
    contact_taper_m: float = Field(default=.0001, gt=0)


class PlanarParameters(Contract):
    model: Literal['matlab_tdcr_planar_dynamic_v1'] = 'matlab_tdcr_planar_dynamic_v1'


class MujocoParameters(Contract):
    model: Literal['mujoco_assembled_rod_v1'] = 'mujoco_assembled_rod_v1'
    integrator: Literal['Euler', 'implicitfast'] = 'implicitfast'


class DynamicsData(Contract):
    backend: str
    physics_identity: str
    scene_identity: str
    model_version: Literal['1.0.0'] = '1.0.0'
    solver_configuration: SpatialParameters | PlanarParameters | MujocoParameters
    exported_files: list[str]
    controller_mode: Literal['C1', 'C2']
    controller_updates: int | None
    numerical_steps: int
    reason: str | None = None
