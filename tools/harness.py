"""Deterministic orchestration. Numerical predictions never override task truth."""
from pathlib import Path
import shutil
import zipfile
from tools.artifact_tools import create_run, save_tool_result, finalize_run, file_hash
from tools.capability_resolver import resolve_capability, CapabilityState
from tools.design_compiler import build_robot_ir
from tools.spec_tools import ROOT, load_yaml, load_task_package, validate_design, load_simulator, load_run_settings


def _snapshot_sources(run):
    paths = []
    for folder in ("schemas", "tools", "controllers", "metrics", "matlab", "capabilities", "physics_contracts", "tasks", "benchmarks", "agents", "configs"):
        paths.extend(p for p in (ROOT / folder).rglob("*") if p.is_file() and p.suffix in (".py", ".m", ".yaml", ".md", ".xml"))
    paths.extend((ROOT / name) for name in ("requirements.txt", "examples/run_reach_pipeline.py"))
    hashes = {}
    with zipfile.ZipFile(run.path / "source_snapshot.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            relative = path.relative_to(ROOT).as_posix()
            archive.write(path, relative)
            hashes[relative] = file_hash(path)
    run.update(source_hashes=hashes)


def run_reach(task_package=ROOT / "tasks/reach_free", design_path=ROOT / "configs/design_tendon_arm.yaml",
              run_root=ROOT / "runs", *, matlab_factory=None):
    run = create_run(run_root)
    matlab = None
    final_status, failure_code = "ERROR", "UNKNOWN"
    stage = "spec_gate"
    try:
        _snapshot_sources(run)
        package = Path(task_package)
        for source, name in ((package / "task.yaml", "task.yaml"), (package / "environment.yaml", "environment.yaml"),
                             (Path(design_path), "design_input.yaml"), (package / "mujoco.xml", "environment.xml")):
            shutil.copyfile(source, run.path / name)
        run.update(task_hash=file_hash(run.path / "task.yaml"), environment_hash=file_hash(run.path / "environment.yaml"),
                   design_hash=file_hash(run.path / "design_input.yaml"))
        # Execute the exact copied bytes whose hashes are recorded, so source edits
        # during a run cannot silently change its task/environment/design inputs.
        task, environment = load_task_package(run.path, representation="environment.xml")
        if task.task_type != "reach":
            raise ValueError("CAPABILITY_MISSING: no canonical evaluator for task type")
        design = validate_design(load_yaml(run.path / "design_input.yaml"))
        simulator, settings = load_simulator(), load_run_settings()
        run.save("simulator.yaml", simulator)
        run.save("run_settings.yaml", settings)
        run.update(random_seed=settings.random_seed)
        run.event(stage, "pass")
        stage = "design_grammar_gate"
        resolution = resolve_capability(design, ("analyze_workspace", "plan_pcc_reach", "compile_mujoco", "run_task"))
        run.save("capability_resolution.json", resolution)
        if resolution.state not in (CapabilityState.SUPPORTED, CapabilityState.PARAMETRICALLY_SUPPORTED):
            final_status = failure_code = resolution.state.value
            run.event(stage, "fail", failure_code=failure_code, reason=resolution.reason)
            return run
        robot_ir = build_robot_ir(design)
        run.save("robot_ir.yaml", robot_ir)
        run.save("physics.yaml", robot_ir.mechanics)
        run.save("design_final.yaml", design)
        run.update(robot_ir_hash=file_hash(run.path / "robot_ir.yaml"))
        run.event(stage, "pass")
        run.save("provenance.json", {
            "task": "task.yaml (frozen package)", "environment": "environment.yaml (sole semantic source)",
            "design": "design_input.yaml; design_final.yaml is identical validated design, no optimization",
            "robot": "robot_ir.yaml derived by tools/design_compiler.py",
            "physics_model_and_actuator": "physics.yaml from physics_contracts/legacy_v1_surrogate.yaml",
            "controller": "controller.json; PCC targets held constant, no feedback",
            "simulator": "simulator.yaml from configs/simulator.yaml; other engine defaults pinned by mujoco_version",
            "run": "run_settings.yaml from configs/run.yaml; seed recorded, no random sampling",
            "compiler_representation_constants": "tools/mujoco_tools.py in source_snapshot.zip: unit gear, hinge axes, contact masks, marker sizes/colors",
            "model_algorithm": "matlab/plan_pcc_reach.m in source_snapshot.zip: fminbnd defaults, theta in [0,pi], straight threshold 1e-8",
            "metrics": "metrics/reach.py in source_snapshot.zip; final Euclidean distance <= frozen task tolerance",
        })
        stage = "model"
        if matlab_factory is None:
            from tools.matlab_tools import MatlabTools
            matlab_factory = MatlabTools
        matlab = matlab_factory()
        run.update(matlab_version=matlab.version())
        workspace = matlab.analyze_workspace(robot_ir, task, environment)
        save_tool_result(run, "workspace_result.json", workspace)
        if workspace.status != "pass":
            final_status = failure_code = workspace.failure_code or "UNKNOWN"
            return run
        plan = matlab.plan_pcc_reach(robot_ir, task, environment)
        save_tool_result(run, "model_result.json", plan)
        if plan.status != "pass":
            final_status = failure_code = plan.failure_code or "UNKNOWN"
            return run
        from controllers.open_loop_length import OpenLoopLength
        controller = OpenLoopLength(plan.metrics["tendon_target_lengths_m"])
        run.save("tendon_command.json", controller.target)
        run.save("controller.json", controller.result())
        stage = "compilation"
        from tools.mujoco_tools import compile_mujoco, run_task
        compiled = compile_mujoco(robot_ir, task, run.path / "robot.xml", environment, simulator)
        save_tool_result(run, "compile_result.json", compiled)
        if compiled.status != "pass":
            final_status = failure_code = compiled.failure_code or "UNKNOWN"
            return run
        stage = "physics_sanity_gate"
        result = run_task(compiled.artifacts["mjcf_path"], task, controller, settings)
        save_tool_result(run, "mujoco_result.json", result)
        run.save("metrics.json", {"model": plan.metrics, "mujoco": result.metrics})
        if "final_state" in result.artifacts:
            run.save("simulation_state.json", result.artifacts["final_state"])
        completed = "task_success" in result.metrics
        run.event(stage, "pass" if completed else "fail", failure_code=None if completed else result.failure_code)
        run.event("task_metric_gate", result.status if completed else "not_run", artifact="mujoco_result.json")
        failure_code = result.failure_code
        final_status = "PASS" if result.status == "pass" else (failure_code or "UNKNOWN")
        return run
    except Exception as exc:
        code = str(exc).split(":", 1)[0]
        failure_code = code if code in ("CAPABILITY_MISSING", "PHYSICS_ASSUMPTION_REQUIRED", "IMPLEMENTATION_REQUIRED") else ("INVALID_SPEC" if stage == "spec_gate" else "UNKNOWN")
        if code in ("CAPABILITY_MISSING", "PHYSICS_ASSUMPTION_REQUIRED", "IMPLEMENTATION_REQUIRED"):
            final_status = code
        run.event(stage, "fail", exception_type=type(exc).__name__, message=str(exc), failure_code=failure_code)
        run.save("error.json", {"stage": stage, "exception_type": type(exc).__name__, "message": str(exc)})
        return run
    finally:
        if matlab is not None:
            try:
                matlab.close()
            except Exception as exc:
                run.event("matlab_cleanup", "fail", exception_type=type(exc).__name__, message=str(exc))
        finalize_run(run, final_status, failure_code)
