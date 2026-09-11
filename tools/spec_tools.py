"""Human-owned package loaders. Loading never rewrites frozen representations."""
from pathlib import Path
import warnings
import xml.etree.ElementTree as ET
import yaml
from schemas.design_spec import DesignSpec
from schemas.environment_spec import EnvironmentSpec, Plane, Window
from schemas.settings import PhysicsSpec, SimulatorSpec, RunSettings
from schemas.task_spec import TaskSpec

ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path):
    with Path(path).open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def load_task(path=ROOT / "tasks/reach_free") -> TaskSpec:
    path = Path(path)
    if path.resolve() == (ROOT / "configs/task_reach.yaml").resolve():
        warnings.warn("Use tasks/reach_free; configs/task_reach.yaml is a checked compatibility copy", DeprecationWarning, stacklevel=2)
        legacy = validate_task_spec(load_yaml(path))
        canonical = load_task()
        if legacy != canonical:
            raise ValueError("Legacy task differs from frozen task")
        return canonical
    return validate_task_spec(load_yaml(path / "task.yaml" if path.is_dir() else path))


def validate_task_spec(value) -> TaskSpec:
    return TaskSpec.model_validate(value)


def validate_design(value) -> DesignSpec:
    return DesignSpec.model_validate(value)


def validate_environment(value) -> EnvironmentSpec:
    return EnvironmentSpec.model_validate(value)


def load_environment(path=ROOT / "tasks/reach_free/environment.yaml") -> EnvironmentSpec:
    return validate_environment(load_yaml(path))


def load_physics() -> PhysicsSpec:
    return PhysicsSpec.model_validate(load_yaml(ROOT / "physics_contracts/legacy_v1_surrogate.yaml"))


def load_simulator() -> SimulatorSpec:
    return SimulatorSpec.model_validate(load_yaml(ROOT / "configs/simulator.yaml"))


def load_run_settings() -> RunSettings:
    return RunSettings.model_validate(load_yaml(ROOT / "configs/run.yaml"))


def environment_xml(environment: EnvironmentSpec) -> ET.Element:
    """Render supported environment semantics only; timestep is composed later."""
    def vector(values):
        return " ".join(str(v) for v in values)
    root = ET.Element("mujoco", model=environment.environment_id)
    ET.SubElement(root, "option", gravity=vector(environment.gravity_m_s2))
    world = ET.SubElement(root, "worldbody")
    for obj in environment.objects:
        if isinstance(obj, Window):
            from tools.window_geometry import window_boxes
            for name, position, size in window_boxes(obj):
                ET.SubElement(world, "geom", name=name, type="box", size=vector(size),
                              pos=vector(position), contype=str(obj.contype), conaffinity=str(obj.conaffinity))
            continue
        if not isinstance(obj, Plane):
            raise ValueError(f"IMPLEMENTATION_REQUIRED: environment component {obj.kind}")
        ET.SubElement(world, "geom", name=obj.name, type="plane", size=vector(obj.half_size_m),
                      pos=vector(obj.position_m), contype=str(obj.contype), conaffinity=str(obj.conaffinity))
    for light in environment.lights:
        ET.SubElement(world, "light", pos=vector(light.position_m), dir=vector(light.direction))
    return root


def validate_frozen_environment(environment: EnvironmentSpec, path: Path) -> None:
    expected = environment_xml(environment)
    actual = ET.parse(path).getroot()
    def semantic(node):
        if node.text and node.text.strip():
            raise ValueError("Unexpected XML text")
        def value(v):
            try:
                return tuple(float(x) for x in v.split())
            except ValueError:
                return v
        return (node.tag, {k: value(v) for k, v in node.attrib.items()}, [semantic(c) for c in node])
    if semantic(expected) != semantic(actual):
        raise ValueError("Frozen MuJoCo representation differs from EnvironmentSpec")


def load_task_package(path=ROOT / "tasks/reach_free", *, representation="mujoco.xml"):
    path = Path(path)
    task, environment = load_task(path), load_environment(path / "environment.yaml")
    if task.environment_id != environment.environment_id:
        raise ValueError("Task/environment identity mismatch")
    if task.task_type == "reach_window" and environment.truth_status != "NON_CANONICAL_DEVELOPMENT_ONLY":
        if environment.truth_status != "HUMAN_APPROVED" or task.acceptance is None:
            raise ValueError("Formal reach_window requires HUMAN_APPROVED environment and explicit task acceptance")
    validate_frozen_environment(environment, path / representation)
    return task, environment
