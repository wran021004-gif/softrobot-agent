"""Deterministic orchestration. Numerical predictions never override task truth."""
from pathlib import Path
import shutil
import zipfile
from tools.artifact_tools import create_run, finalize_run, file_hash
from tools.capability_resolver import resolve_capability, CapabilityState
from tools.design_compiler import build_robot_ir
from tools.spec_tools import ROOT, load_yaml, load_task_package, validate_design, load_simulator, load_run_settings
from tools.provenance import parameter_provenance


def _snapshot_sources(run):
    paths = []
    for folder in ("schemas", "tools", "controllers", "metrics", "matlab", "capabilities", "physics_contracts", "tasks", "benchmarks", "agents", "configs", "skills", "memory"):
        paths.extend(p for p in (ROOT / folder).rglob("*") if p.is_file() and p.suffix in (".py", ".m", ".yaml", ".md", ".xml", ".json"))
    paths.extend((ROOT / name) for name in ("requirements.txt", "examples/run_reach_pipeline.py"))
    paths.extend(p for p in (ROOT / "tests/fixtures/reach_window_dev").rglob("*") if p.is_file())
    hashes = {}
    with zipfile.ZipFile(run.path / "source_snapshot.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            relative = path.relative_to(ROOT).as_posix()
            archive.write(path, relative)
            hashes[relative] = file_hash(path)
    run.update(source_hashes=hashes)
    run.events.emit("ARTIFACT_CREATED", "source_snapshot", evidence_refs=run.events.refs("source_snapshot.zip"))


def run_reach(task_package=ROOT / "tasks/reach_free", design_path=ROOT / "configs/design_tendon_arm.yaml",
              run_root=ROOT / "runs", *, matlab_factory=None, previous_run_id=None, relationship=None):
    run = create_run(run_root, previous_run_id=previous_run_id, relationship=relationship)
    matlab = None
    clearance = None
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
        for operation, artifact in (("task_loaded", "task.yaml"), ("environment_validated", "environment.yaml")):
            run.events.emit("SPEC_VALIDATED", operation, status="pass", evidence_refs=run.events.refs(artifact))
        if task.task_type not in ("reach", "reach_window"):
            raise ValueError("CAPABILITY_MISSING: no canonical evaluator for task type")
        constrained = task.task_type == "reach_window"
        if constrained:
            from tools.window_geometry import constrained_window
            constrained_window(environment, task)
        design = validate_design(load_yaml(run.path / "design_input.yaml"))
        run.events.emit("SPEC_VALIDATED", "design_loaded", status="pass", evidence_refs=run.events.refs("design_input.yaml"))
        simulator, settings = load_simulator(), load_run_settings()
        run.save("simulator.yaml", simulator)
        run.save("run_settings.yaml", settings)
        run.update(random_seed=settings.random_seed)
        run.event(stage, "pass")
        run.events.emit("GATE_EVALUATED", stage, actor="gate", status="pass",
            gate=dict(gate=stage, input_metric="specs_valid", value=True, threshold=True, comparison="==",
                      decision="PASS", authority="Task/Environment/Design contracts and frozen package"),
            evidence_refs=run.events.refs("task.yaml", "environment.yaml", "design_input.yaml"))
        stage = "design_grammar_gate"
        requested = ("analyze_workspace", "plan_pcc_reach", "compile_mujoco", "run_task")
        if constrained:
            requested += ("analyze_clearance", "check_collision")
        resolution = resolve_capability(design, requested)
        run.save("capability_resolution.json", resolution)
        run.events.emit("CAPABILITY_RESOLVED", "resolve_capability", summary={"state": resolution.state.value},
                        evidence_refs=run.events.refs("capability_resolution.json", "design_input.yaml"))
        supported = resolution.state in (CapabilityState.SUPPORTED, CapabilityState.PARAMETRICALLY_SUPPORTED)
        run.events.emit("GATE_EVALUATED", stage, actor="gate", status="pass" if supported else "fail",
            gate=dict(gate=stage, input_metric="capability_supported", value=supported, threshold=True, comparison="==",
                      decision="PASS" if supported else "FAIL", authority="Human-owned family grammar and capability manifests"),
            evidence_refs=run.events.refs("capability_resolution.json"))
        if resolution.state not in (CapabilityState.SUPPORTED, CapabilityState.PARAMETRICALLY_SUPPORTED):
            final_status = failure_code = resolution.state.value
            run.event(stage, "fail", failure_code=failure_code, reason=resolution.reason)
            return run
        robot_ir = build_robot_ir(design)
        run.save("robot_ir.yaml", robot_ir)
        run.save("physics.yaml", robot_ir.mechanics)
        run.save("design_final.yaml", design)
        run.update(robot_ir_hash=file_hash(run.path / "robot_ir.yaml"))
        run.events.emit("SPEC_VALIDATED", "robot_ir_built", status="pass",
                        evidence_refs=run.events.refs("robot_ir.yaml", "physics.yaml", "design_input.yaml"))
        run.event(stage, "pass")
        provenance = {
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
        }
        provenance["parameters"] = parameter_provenance(design, robot_ir, task, environment, simulator, settings)
        provenance["truth_status"] = environment.truth_status
        if constrained:
            provenance["task"] = "task.yaml; " + environment.truth_status
            provenance["environment_representation"] = "environment.xml and robot.xml <- tools.spec_tools.environment_xml <- environment.yaml; window bars shared with MATLAB via tools.window_geometry.window_boxes"
            provenance["metrics"] = "metrics/reach.py: target tolerance AND final full-slab aperture crossing AND no sampled window contact; " + environment.truth_status
        run.save("provenance.json", provenance)
        stage = "model"
        if matlab_factory is None:
            from tools.matlab_tools import MatlabTools
            matlab_factory = MatlabTools
        comparison_context = {
            "run_id": run.record.run_id, "task_hash": run.record.task_hash,
            "environment_hash": run.record.environment_hash, "robot_ir_hash": run.record.robot_ir_hash,
            "coordinate_frame": robot_ir.coordinate_frame,
        }
        with run.events.span("model") as model_stage:
            with run.events.span("matlab_session", kind="TOOL", actor="tool"):
                matlab = matlab_factory()
                run.update(matlab_version=matlab.version())
            workspace = run.invoke_tool("analyze_workspace", "workspace_result.json",
                lambda: matlab.analyze_workspace(robot_ir, task, environment),
                input_paths=("robot_ir.yaml", "task.yaml", "environment.yaml"))
            if workspace.status != "pass":
                final_status = failure_code = workspace.failure_code or "UNKNOWN"
                model_stage.update(status="fail", failure_code=failure_code)
                return run
            def plan_call():
                result = matlab.plan_pcc_reach(robot_ir, task, environment)
                return result.model_copy(update={"metrics": {**result.metrics, "comparison_context": comparison_context}})
            plan = run.invoke_tool("plan_pcc_reach", "model_result.json", plan_call,
                                   input_paths=("robot_ir.yaml", "task.yaml", "environment.yaml"))
            if plan.status != "pass":
                final_status = failure_code = plan.failure_code or "UNKNOWN"
                model_stage.update(status="fail", failure_code=failure_code)
                return run
            if constrained:
                clearance = run.invoke_tool("analyze_clearance", "clearance_result.json",
                    lambda: matlab.analyze_clearance(robot_ir, task, environment, plan),
                    input_paths=("robot_ir.yaml", "task.yaml", "environment.yaml", "model_result.json"))
                if clearance.status != "pass":
                    final_status = failure_code = clearance.failure_code or "UNKNOWN"
                    model_stage.update(status="fail", failure_code=failure_code)
                    return run
                feasible = not clearance.metrics["predicted_clearance_violation"]
                run.events.emit("GATE_EVALUATED", "model_clearance_gate", actor="gate", status="pass" if feasible else "fail",
                    gate=dict(gate="model_clearance", input_metric="predicted_clearance_violation",
                              value=not feasible, threshold=False, comparison="==",
                              decision="PASS" if feasible else "FAIL", authority="Geometric screening only; continue simulation for evidence, no canonical override"),
                    evidence_refs=run.events.refs("clearance_result.json", "environment.yaml"))
        from controllers.open_loop_length import OpenLoopLength
        controller = OpenLoopLength(plan.metrics["tendon_target_lengths_m"])
        run.save("tendon_command.json", controller.target)
        run.save("controller.json", controller.result())
        run.events.emit("CONTROL_SELECTED", "open_loop_length", status="pass", summary={"control_level": "C1"},
                        evidence_refs=run.events.refs("model_result.json", "controller.json", "tendon_command.json"))
        provenance["parameters"] = parameter_provenance(design, robot_ir, task, environment, simulator, settings, controller.target)
        run.save("provenance.json", provenance)
        stage = "compilation"
        from tools.mujoco_tools import compile_mujoco, run_task
        with run.events.span("mujoco") as sim_stage:
            compiled = run.invoke_tool("compile_mujoco", "compile_result.json",
                lambda: compile_mujoco(robot_ir, task, run.path / "robot.xml", environment, simulator),
                input_paths=("robot_ir.yaml", "task.yaml", "environment.yaml", "simulator.yaml"))
            if compiled.status != "pass":
                final_status = failure_code = compiled.failure_code or "UNKNOWN"
                sim_stage.update(status="fail", failure_code=failure_code)
                return run
            run.events.emit("ARTIFACT_CREATED", "compile_mujoco_artifact", evidence_refs=run.events.refs("robot.xml"))
            stage = "physics_sanity_gate"
            def simulation_call():
                result = run_task(compiled.artifacts["mjcf_path"], task, controller, settings,
                                  **({"environment": environment} if constrained else {}))
                return result.model_copy(update={"metrics": {**result.metrics, "comparison_context": comparison_context}})
            result = run.invoke_tool("run_task", "mujoco_result.json", simulation_call,
                input_paths=("robot.xml", "task.yaml", "controller.json", "run_settings.yaml") + (("environment.yaml",) if constrained else ()))
            # A failed task can still be a completed simulation stage.
            sim_stage.update(status="pass" if "task_success" in result.metrics else "fail")
            if "actuator_controls" in result.metrics:
                run.events.emit("CONTROL_APPLIED", "open_loop_length", status="pass",
                                evidence_refs=run.events.refs("controller.json", "mujoco_result.json"))
        if "execution_evidence" in result.metrics:
            provenance["compiled_engine_parameters"] = result.metrics["execution_evidence"]["compiled_parameter_evidence"]
            run.save("provenance.json", provenance)
        run.save("metrics.json", {"model": plan.metrics, "mujoco": result.metrics,
                                  **({"clearance": clearance.metrics} if clearance else {})})
        if "final_state" in result.artifacts:
            run.save("simulation_state.json", result.artifacts["final_state"])
        completed = "task_success" in result.metrics
        run.event(stage, "pass" if completed else "fail", failure_code=None if completed else result.failure_code)
        run.event("task_metric_gate", result.status if completed else "not_run", artifact="mujoco_result.json")
        run.events.emit("GATE_EVALUATED", "physics_sanity_gate", actor="gate", status="pass" if completed else "fail",
            failure_code=None if completed else result.failure_code,
            gate=dict(gate="physics_sanity", input_metric="task_success_available", value=completed, threshold=True,
                      comparison="available", decision="PASS" if completed else "FAIL", authority="run_task finite-state execution checks"),
            evidence_refs=run.events.refs("mujoco_result.json"))
        tip_passed = result.metrics.get("target_reached", result.metrics.get("task_success"))
        run.events.emit("GATE_EVALUATED", "target_metric_gate" if constrained else "task_metric_gate", actor="gate",
            status=("pass" if tip_passed else "fail") if completed else "not_run",
            failure_code=None if tip_passed else result.failure_code,
            gate=dict(gate="target_reached" if constrained else "task_success", input_metric="position_error_m", value=result.metrics.get("position_error_m"),
                      threshold=task.position_error_max_m, comparison="<=",
                      decision=("PASS" if tip_passed else "FAIL") if completed else "NOT_RUN",
                      authority=("TaskSpec: task.yaml; metrics/reach.py; " + environment.truth_status) if constrained else "frozen TaskSpec: task.yaml; metrics/reach.py"),
            evidence_refs=run.events.refs("task.yaml", "mujoco_result.json"))
        if constrained:
            for metric, expected in (("aperture_constraint_satisfied", True), ("obstacle_contact_occurred", False), ("task_success", True)):
                passed = result.metrics.get(metric) == expected if completed else False
                run.events.emit("GATE_EVALUATED", metric + "_gate", actor="gate",
                    status=("pass" if passed else "fail") if completed else "not_run",
                    gate=dict(gate=metric, input_metric=metric, value=result.metrics.get(metric), threshold=expected,
                              comparison="==", decision=("PASS" if passed else "FAIL") if completed else "NOT_RUN",
                              authority="metrics/reach.py constrained evaluation; " + environment.truth_status),
                    evidence_refs=run.events.refs("task.yaml", "environment.yaml", "mujoco_result.json"))
        failure_code = result.failure_code
        final_status = "PASS" if result.status == "pass" else (failure_code or "UNKNOWN")
        # Diagnostics cannot change the canonical task/physics gate decision.
        try:
            from tools.diagnostic_tools import save_diagnostic_summary
            with run.events.span("diagnostics"):
                save_diagnostic_summary(run, plan, result, task, clearance)
        except Exception as exc:
            run.event("diagnostics", "fail", failure_code="UNKNOWN", message=str(exc))
        return run
    except Exception as exc:
        code = str(exc).split(":", 1)[0]
        failure_code = code if code in ("CAPABILITY_MISSING", "PHYSICS_ASSUMPTION_REQUIRED", "IMPLEMENTATION_REQUIRED") else ("INVALID_SPEC" if stage == "spec_gate" else "UNKNOWN")
        if code in ("CAPABILITY_MISSING", "PHYSICS_ASSUMPTION_REQUIRED", "IMPLEMENTATION_REQUIRED"):
            final_status = code
        run.event(stage, "fail", exception_type=type(exc).__name__, message=str(exc), failure_code=failure_code)
        run.save("error.json", {"stage": stage, "exception_type": type(exc).__name__, "message": str(exc)})
        if stage == "spec_gate":
            run.events.emit("GATE_EVALUATED", stage, actor="gate", status="fail", failure_code=failure_code,
                gate=dict(gate=stage, input_metric="specs_valid", value=False, threshold=True, comparison="==",
                          decision="FAIL", authority="Task/Environment/Design contracts and frozen package"),
                evidence_refs=run.events.refs("error.json"))
        return run
    finally:
        if matlab is not None:
            try:
                with run.events.span("matlab_cleanup", kind="TOOL", actor="tool"):
                    matlab.close()
            except Exception as exc:
                run.event("matlab_cleanup", "fail", exception_type=type(exc).__name__, message=str(exc))
        finalize_run(run, final_status, failure_code)
