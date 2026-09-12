"""Deterministic orchestration. Numerical predictions never override task truth."""
from pathlib import Path
import math
import hashlib
import shutil
import zipfile
from tools.artifact_tools import create_run, finalize_run, file_hash
from tools.capability_resolver import resolve_capability, CapabilityState
from tools.design_compiler import build_robot_ir
from tools.spec_tools import ROOT, load_yaml, load_task_package, validate_design, load_simulator, load_run_settings
from tools.provenance import parameter_provenance
from schemas.gate import GateType, gate_action


def _record_check(run, name, gate_type, passed, metric, value, threshold, authority, paths, comparison="=="):
    decision = "PASS" if passed else "FAIL"
    run.events.emit("GATE_EVALUATED", name, actor="gate", status="pass" if passed else "fail",
        gate=dict(gate=name, gate_type=gate_type, input_metric=metric, value=value, threshold=threshold,
                  comparison=comparison, decision=decision, authority=authority),
        evidence_refs=run.events.refs(*paths))
    return gate_action(gate_type, decision)


def _save_gate_summary(run, final_status, failure_code, stage, environment):
    gates = [{"operation": e.operation, **e.gate.model_dump(mode="json"),
              "action": gate_action(e.gate.gate_type, e.gate.decision),
              "evidence_refs": [ref.model_dump(mode="json") for ref in e.evidence_refs]}
             for e in run.events.events if e.gate is not None]
    hard = [g["operation"] for g in gates if g["action"] == "STOP"]
    canonical = [g for g in gates if g["gate_type"] == "CANONICAL" and g["decision"] != "NOT_RUN"]
    run.save("gate_summary.json", {
        "policy_authority": "Human-owned schemas/gate.py; Agents cannot override type, threshold or decision",
        "final_status": final_status, "failure_code": failure_code,
        "task_truth_status": environment.truth_status if environment is not None else None,
        "task_contract_id": run.record.task_contract_id, "task_contract_status": run.record.task_contract_status,
        "termination": "HARD_FAIL" if hard else "CANONICAL_RESULT" if canonical else "MODEL_ONLY" if final_status == "MODEL_ONLY" else "EXECUTION_ERROR",
        "stopped_by": hard, "last_stage": stage,
        "screening_failures": [g["operation"] for g in gates if g["gate_type"] == "SCREENING" and g["decision"] == "FAIL"],
        "canonical_result": ("FAIL" if any(g["decision"] == "FAIL" for g in canonical) else "PASS") if canonical else "NOT_RUN",
        "benchmark_approval": "Gate type is not promotion; consult task/environment authority and benchmark registry",
        "gates": gates,
    })


def _snapshot_sources(run, extra_paths=()):
    paths = []
    for folder in ("schemas", "tools", "controllers", "metrics", "matlab", "capabilities", "physics_contracts", "tasks", "benchmarks", "agents", "configs", "skills", "memory"):
        paths.extend(p for p in (ROOT / folder).rglob("*") if p.is_file() and p.suffix in (".py", ".m", ".yaml", ".md", ".xml", ".json"))
    paths.extend((ROOT / name) for name in ("requirements.txt", "examples/run_reach_pipeline.py", "examples/run_experiment.py"))
    paths.extend(p for p in (ROOT / "tests/fixtures/reach_window_dev").rglob("*") if p.is_file())
    paths.extend(extra_paths)
    hashes = {}
    with zipfile.ZipFile(run.path / "source_snapshot.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(paths)):
            relative = path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            archive.writestr(relative, data)
            hashes[relative] = hashlib.sha256(data).hexdigest()
    run.update(source_hashes=hashes)
    run.events.emit("ARTIFACT_CREATED", "source_snapshot", evidence_refs=run.events.refs("source_snapshot.zip"))


def run_reach(task_package=ROOT / "tasks/reach_free", design_path=ROOT / "configs/design_tendon_arm.yaml",
              run_root=ROOT / "runs", *, matlab_factory=None, previous_run_id=None, relationship=None,
              fidelity="MUJOCO", experiment_path=None, controller_level="C1", experiment_context=None,
              debug=False, visualize=False, viewer_launcher=None):
    run = create_run(run_root, previous_run_id=previous_run_id, relationship=relationship)
    matlab = None
    environment = None
    clearance = None
    resolved_contract = None
    experiment = None
    controller = None
    observability = None
    if debug or visualize:
        from tools.debug_tools import DebugObservability
        observability = DebugObservability(run.path / "debug", debug=debug, visualize=visualize,
                                           viewer_launcher=viewer_launcher)
    final_status, failure_code = "ERROR", "UNKNOWN"
    stage = "spec_gate"
    try:
        package = Path(task_package)
        if (package / "contract.yaml").is_file():
            from tools.task_contract_tools import resolve_task_contract
            resolved_contract = resolve_task_contract(package)
        if fidelity not in ("M0", "M1", "MUJOCO") or controller_level not in ("C1", "C2"):
            raise ValueError("CAPABILITY_MISSING: unsupported evaluation route")
        if experiment_path is not None:
            from tools.experiment_policy_tools import validate_experiment_policy
            experiment = validate_experiment_policy(experiment_path)
            if not resolved_contract or resolved_contract.manifest_hash != experiment.resolved.manifest_hash:
                raise ValueError("Experiment TaskContract mismatch")
            model_level = "M0" if fidelity == "M0" else "M1"
            if model_level not in experiment.policy.allowed_model_levels or controller_level not in experiment.policy.allowed_controller_levels:
                raise ValueError("Evaluation route is not authorized by policy")
            if fidelity == "MUJOCO" and experiment.policy.mujoco_validation_budget == 0:
                raise ValueError("No authorized MuJoCo validation budget")
            (run.path / "optimization_policy.yaml").write_bytes(experiment.path.read_bytes())
            run.save("experiment_context.json", {"policy_hash": experiment.policy_hash,
                "scope": experiment.policy.scientific_status, **(experiment_context or {})})
        elif fidelity != "MUJOCO" or controller_level != "C1":
            raise ValueError("BLOCKED_FOR_HUMAN_APPROVAL: optional routes require ExperimentPolicy")
        extra = (resolved_contract.manifest_path, *resolved_contract.source_paths.values()) if resolved_contract else ()
        if experiment:
            extra += tuple(experiment.input_hashes)
        _snapshot_sources(run, extra)
        if resolved_contract:
            resolved = resolved_contract
            with zipfile.ZipFile(run.path / "source_snapshot.zip") as archive:
                def source_bytes(path, expected_hash):
                    data = archive.read(path.relative_to(ROOT).as_posix())
                    if hashlib.sha256(data).hexdigest() != expected_hash:
                        raise ValueError("TaskContract source changed during resolution; rerun against stable inputs")
                    return data
                manifest = source_bytes(resolved.manifest_path, resolved.manifest_hash)
                for key, path in resolved.source_paths.items():
                    source_bytes(path, resolved.source_hashes[key])
                (run.path / "task_contract.yaml").write_bytes(manifest)
                run.update(task_contract_id=resolved.contract.contract_id,
                           task_contract_status=resolved.contract.status, task_contract_hash=file_hash(run.path / "task_contract.yaml"))
                run.events.emit("ARTIFACT_CREATED", "task_contract_snapshot", evidence_refs=run.events.refs("task_contract.yaml"))
                run.save("task_contract_resolved.json", resolved.reference_view())
                run.events.emit("SPEC_VALIDATED", "task_contract_resolved", status="pass",
                    summary={"contract_id": resolved.contract.contract_id, "contract_status": resolved.contract.status},
                    evidence_refs=run.events.refs("task_contract.yaml", "task_contract_resolved.json"))
                if resolved.contract.status == "PROPOSED_NOT_APPROVED":
                    raise ValueError("CAPABILITY_MISSING: proposal contract is resolvable for discussion, not executable or approved")
                for key, name in (("task_source", "task.yaml"), ("environment_source", "environment.yaml"),
                                  ("environment_representation_source", "environment.xml")):
                    (run.path / name).write_bytes(source_bytes(resolved.source_paths[key], resolved.source_hashes[key]))
        else:
            # Existing local tests and legacy packages remain an explicit,
            # non-benchmark compatibility route, with no invented contract ID.
            run.update(task_contract_status="DEVELOPMENT_ONLY")
            run.events.emit("SPEC_VALIDATED", "task_contract_compatibility", status="pass",
                            summary={"mode": "legacy_no_contract", "contract_status": "DEVELOPMENT_ONLY"})
            for source, name in ((package / "task.yaml", "task.yaml"), (package / "environment.yaml", "environment.yaml"),
                                 (package / "mujoco.xml", "environment.xml")):
                shutil.copyfile(source, run.path / name)
        shutil.copyfile(Path(design_path), run.path / "design_input.yaml")
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
            run.save("acceptance.json", {
                "truth_status": environment.truth_status,
                "source": "task.yaml acceptance" if task.acceptance else "Round 2 development default in schemas/task_spec.py; not approved benchmark truth",
                **task.window_acceptance().model_dump(mode="json"),
            })
        design = validate_design(load_yaml(run.path / "design_input.yaml"))
        if experiment:
            experiment.validate_candidate(design)
        run.events.emit("SPEC_VALIDATED", "design_loaded", status="pass", evidence_refs=run.events.refs("design_input.yaml"))
        if resolved_contract:
            simulator, settings = resolved_contract.simulator_settings, resolved_contract.run_settings
            if design.robot_family != resolved_contract.grammar["family_name"]:
                raise ValueError("CAPABILITY_MISSING: candidate family differs from TaskContract design envelope")
        else:
            simulator, settings = load_simulator(), load_run_settings()
        run.save("simulator.yaml", simulator)
        run.save("run_settings.yaml", settings)
        run.update(random_seed=settings.random_seed)
        run.event(stage, "pass")
        run.events.emit("GATE_EVALUATED", stage, actor="gate", status="pass",
            gate=dict(gate=stage, gate_type="HARD", input_metric="specs_valid", value=True, threshold=True, comparison="==",
                      decision="PASS", authority="Task/Environment/Design contracts and frozen package"),
            evidence_refs=run.events.refs("task.yaml", "environment.yaml", "design_input.yaml"))
        stage = "design_grammar_gate"
        requested = ("analyze_workspace", "plan_pcc_reach", "compile_mujoco", "run_task")
        if fidelity == "M0":
            requested = ("analyze_workspace",)
        elif fidelity == "M1":
            requested = ("analyze_workspace", "plan_pcc_reach")
        if controller_level == "C2":
            requested += ("synthesize_feedback",)
        if constrained:
            requested += ("analyze_clearance", "check_collision")
        resolution = resolve_capability(design, requested,
            **({"grammar": resolved_contract.grammar} if resolved_contract else {}))
        run.save("capability_resolution.json", resolution)
        run.events.emit("CAPABILITY_RESOLVED", "resolve_capability", summary={"state": resolution.state.value},
                        evidence_refs=run.events.refs("capability_resolution.json", "design_input.yaml"))
        supported = resolution.state in (CapabilityState.SUPPORTED, CapabilityState.PARAMETRICALLY_SUPPORTED)
        run.events.emit("GATE_EVALUATED", stage, actor="gate", status="pass" if supported else "fail",
            gate=dict(gate=stage, gate_type="HARD", input_metric="capability_supported", value=supported, threshold=True, comparison="==",
                      decision="PASS" if supported else "FAIL", authority="Human-owned family grammar and capability manifests"),
            evidence_refs=run.events.refs("capability_resolution.json"))
        if gate_action(GateType.HARD, "PASS" if supported else "FAIL") == "STOP":
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
        provenance["task_contract"] = {
            "contract_id": run.record.task_contract_id, "status": run.record.task_contract_status,
            "manifest_hash": run.record.task_contract_hash,
            "source": "task_contract_resolved.json" if resolved_contract else "legacy_no_contract compatibility; not a formal benchmark run",
        }
        if resolved_contract:
            provenance["simulator"] = "simulator.yaml <- " + resolved_contract.contract.simulator_settings_source
            provenance["run"] = "run_settings.yaml <- " + resolved_contract.contract.run_settings_source
            provenance["metrics"] = resolved_contract.contract.evaluator + " from task_contract.yaml"
        if constrained:
            provenance["task"] = "task.yaml; " + environment.truth_status
            provenance["environment_representation"] = "environment.xml and robot.xml <- tools.spec_tools.environment_xml <- environment.yaml; window bars shared with MATLAB via tools.window_geometry.window_boxes"
            provenance["metrics"] = "metrics/reach.py: target tolerance AND required initial side AND final full-slab aperture crossing AND no forbidden sampled window contact; " + environment.truth_status
        if resolved_contract:
            provenance["metrics"] = resolved_contract.contract.evaluator + " <- task_contract.yaml; exact evaluator source in source_snapshot.zip"
        if experiment:
            provenance["experiment"] = {"policy_hash": experiment.policy_hash,
                "policy_source": "optimization_policy.yaml", "context_source": "experiment_context.json",
                "scope": experiment.policy.scientific_status, "requested_fidelity": fidelity}
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
            workspace_completed = workspace.status == "pass" or (workspace.failure_code == "DESIGN_INFEASIBLE" and workspace.metrics.get("target_reachable") is False)
            if _record_check(run, "workspace_execution_gate", "HARD", workspace_completed,
                    "workspace_analysis_completed", workspace_completed, True,
                    "Executable M0 result required; a completed geometric rejection is not a tool runtime failure",
                    ("workspace_result.json",)) == "STOP":
                final_status = failure_code = workspace.failure_code or "UNKNOWN"
                model_stage.update(status="fail", failure_code=failure_code)
                return run
            # M0's exact-point test ignores tolerance. The task necessary bound is
            # norm(target) <= fixed inextensible arm length + frozen tolerance.
            distance = math.dist(robot_ir.base_position_m, task.target_m)
            bound = robot_ir.total_length_m + task.position_error_max_m
            if _record_check(run, "workspace_gate", "HARD", distance <= bound,
                    "target_distance_m", distance, bound,
                    "Fixed-base inextensible RobotIR; segmented_mujoco_mapping_v1.md plus TaskSpec tolerance (triangle inequality); not sufficient for reach",
                    ("workspace_result.json", "robot_ir.yaml", "task.yaml"), comparison="<=") == "STOP":
                final_status = failure_code = "DESIGN_INFEASIBLE"
                model_stage.update(status="fail", failure_code=failure_code)
                return run
            if fidelity == "M0":
                run.save("metrics.json", {"model": workspace.metrics, "mujoco": {}})
                run.update(model_level="M0", control_level="C0")
                final_status, failure_code = "MODEL_ONLY", None
                return run
            def plan_call():
                result = matlab.plan_pcc_reach(robot_ir, task, environment)
                return result.model_copy(update={"metrics": {**result.metrics, "comparison_context": comparison_context}})
            plan = run.invoke_tool("plan_pcc_reach", "model_result.json", plan_call,
                                   input_paths=("robot_ir.yaml", "task.yaml", "environment.yaml"))
            if _record_check(run, "model_execution_gate", "HARD", plan.status == "pass",
                    "valid_PCC_commands_available", plan.status == "pass", True,
                    "PCC executable-command contract; tool completion is separate from predicted task success",
                    ("model_result.json",)) == "STOP":
                final_status = failure_code = plan.failure_code or "UNKNOWN"
                model_stage.update(status="fail", failure_code=failure_code)
                return run
            _record_check(run, "model_prediction_gate", "SCREENING", plan.metrics["model_task_success"],
                "predicted_position_error_m", plan.metrics["predicted_position_error_m"], task.position_error_max_m,
                "tendon_driven_pcc_v1.md low-fidelity prediction; TaskSpec tolerance; failure continues to MuJoCo",
                ("model_result.json", "task.yaml"), comparison="<=")
            if constrained:
                clearance = run.invoke_tool("analyze_clearance", "clearance_result.json",
                    lambda: matlab.analyze_clearance(robot_ir, task, environment, plan),
                    input_paths=("robot_ir.yaml", "task.yaml", "environment.yaml", "model_result.json"))
                if _record_check(run, "clearance_execution_gate", "HARD", clearance.status == "pass",
                        "clearance_analysis_completed", clearance.status == "pass", True,
                        "Executable clearance result required; not a geometric feasibility criterion",
                        ("clearance_result.json",)) == "STOP":
                    final_status = failure_code = clearance.failure_code or "UNKNOWN"
                    model_stage.update(status="fail", failure_code=failure_code)
                    return run
                feasible = not clearance.metrics["predicted_clearance_violation"]
                run.events.emit("GATE_EVALUATED", "model_clearance_gate", actor="gate", status="pass" if feasible else "fail",
                    gate=dict(gate="model_clearance", gate_type="SCREENING", input_metric="predicted_clearance_violation",
                              value=not feasible, threshold=False, comparison="==",
                              decision="PASS" if feasible else "FAIL", authority="Geometric screening only; continue simulation for evidence, no canonical override"),
                    evidence_refs=run.events.refs("clearance_result.json", "environment.yaml"))
        if observability is not None:
            observability.plot_matlab(matlab, run.path, visible=visualize)
        if fidelity == "M1":
            run.save("metrics.json", {"model": plan.metrics, "mujoco": {},
                                      **({"clearance": clearance.metrics} if clearance else {})})
            run.update(control_level="C0")
            final_status, failure_code = "MODEL_ONLY", None
            return run
        from controllers.open_loop_length import OpenLoopLength
        controller = OpenLoopLength(plan.metrics["tendon_target_lengths_m"])
        if controller_level == "C2":
            from controllers.pcc_tip_feedback import synthesize_feedback
            controller = synthesize_feedback(robot_ir, task, plan, experiment)
            run.save("feedback_controller.json", controller.artifact)
            run.update(control_level="C2")
            provenance["controller"] = "feedback_controller.json; actual MuJoCo tip feedback; parameters from optimization_policy.yaml"
        run.save("tendon_command.json", controller.target)
        run.save("controller.json", controller.result())
        run.events.emit("CONTROL_SELECTED", controller.spec.controller, status="pass", summary={"control_level": controller.spec.level},
                        evidence_refs=run.events.refs("model_result.json", "controller.json", "tendon_command.json"))
        provenance["parameters"] = parameter_provenance(design, robot_ir, task, environment, simulator, settings, controller.target)
        run.save("provenance.json", provenance)
        stage = "compilation"
        from tools.mujoco_tools import compile_mujoco, run_task
        with run.events.span("mujoco") as sim_stage:
            compiled = run.invoke_tool("compile_mujoco", "compile_result.json",
                lambda: compile_mujoco(robot_ir, task, run.path / "robot.xml", environment, simulator),
                input_paths=("robot_ir.yaml", "task.yaml", "environment.yaml", "simulator.yaml"))
            if _record_check(run, "compilation_gate", "HARD", compiled.status == "pass",
                    "model_compiled", compiled.status == "pass", True,
                    "RobotIR/environment compilation contract; execution legality only",
                    ("compile_result.json",)) == "STOP":
                final_status = failure_code = compiled.failure_code or "UNKNOWN"
                sim_stage.update(status="fail", failure_code=failure_code)
                return run
            run.events.emit("ARTIFACT_CREATED", "compile_mujoco_artifact", evidence_refs=run.events.refs("robot.xml"))
            stage = "physics_sanity_gate"
            def simulation_call():
                result = run_task(compiled.artifacts["mjcf_path"], task, controller, settings,
                                  **({"environment": environment} if constrained else {}),
                                  **({"evaluator": resolved_contract.evaluator} if resolved_contract else {}),
                                  **({"observability": observability} if observability else {}))
                return result.model_copy(update={"metrics": {**result.metrics, "comparison_context": comparison_context}})
            result = run.invoke_tool("run_task", "mujoco_result.json", simulation_call,
                input_paths=("robot.xml", "task.yaml", "controller.json", "run_settings.yaml") + (("environment.yaml",) if constrained else ()))
            # A failed task can still be a completed simulation stage.
            sim_stage.update(status="pass" if "task_success" in result.metrics else "fail")
            if "actuator_controls" in result.metrics:
                run.events.emit("CONTROL_APPLIED", controller.spec.controller, status="pass",
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
            gate=dict(gate="physics_sanity", gate_type="HARD", input_metric="task_success_available", value=completed, threshold=True,
                      comparison="available", decision="PASS" if completed else "FAIL", authority="run_task finite-state execution checks"),
            evidence_refs=run.events.refs("mujoco_result.json"))
        tip_passed = result.metrics.get("target_reached", result.metrics.get("task_success"))
        run.events.emit("GATE_EVALUATED", "target_metric_gate" if constrained else "task_metric_gate", actor="gate",
            status=("pass" if tip_passed else "fail") if completed else "not_run",
            failure_code=None if tip_passed else result.failure_code,
            gate=dict(gate="target_reached" if constrained else "task_success", gate_type="CANONICAL", input_metric="position_error_m", value=result.metrics.get("position_error_m"),
                      threshold=task.position_error_max_m, comparison="<=",
                      decision=("PASS" if tip_passed else "FAIL") if completed else "NOT_RUN",
                      authority=("TaskSpec: task.yaml; contract status " + run.record.task_contract_status) if run.record.task_contract_status != "FROZEN" else "frozen TaskSpec: task.yaml; metrics/reach.py"),
            evidence_refs=run.events.refs("task.yaml", "mujoco_result.json"))
        if constrained:
            for metric, expected in (("initial_required_side_satisfied", True), ("aperture_constraint_satisfied", True), ("obstacle_contact_occurred", False), ("task_success", True)):
                passed = result.metrics.get(metric) == expected if completed else False
                run.events.emit("GATE_EVALUATED", metric + "_gate", actor="gate",
                    status=("pass" if passed else "fail") if completed else "not_run",
                    gate=dict(gate=metric, gate_type="CANONICAL", input_metric=metric, value=result.metrics.get(metric), threshold=expected,
                              comparison="==", decision=("PASS" if passed else "FAIL") if completed else "NOT_RUN",
                              authority="metrics/reach.py constrained evaluation; " + environment.truth_status),
                    evidence_refs=run.events.refs("task.yaml", "environment.yaml", "mujoco_result.json"))
        failure_code = result.failure_code
        if completed:
            final_status = "PASS" if result.metrics["task_success"] else gate_action(GateType.CANONICAL, "FAIL")
            failure_code = None if final_status == "PASS" else "TASK_FAILED"
        else:
            final_status = failure_code or "UNKNOWN"
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
                gate=dict(gate=stage, gate_type="HARD", input_metric="specs_valid", value=False, threshold=True, comparison="==",
                          decision="FAIL", authority="Task/Environment/Design contracts and frozen package"),
                evidence_refs=run.events.refs("error.json"))
        else:
            _record_check(run, "execution_gate", "HARD", False, "stage_executable", False, True,
                "Harness executable input/tool contract; runtime failure is not scientific design infeasibility",
                ("error.json",))
        return run
    finally:
        if observability is not None:
            observability.attempt("debug_finalize", observability.finish)
        if controller is not None and hasattr(controller, "updates"):
            run.save("feedback_updates.json", controller.updates)
            run.events.emit("CONTROL_APPLIED", "feedback_update_summary", status="recorded",
                summary={"updates": len(controller.updates)},
                evidence_refs=run.events.refs("feedback_controller.json", "feedback_updates.json"))
        if matlab is not None:
            try:
                with run.events.span("matlab_cleanup", kind="TOOL", actor="tool"):
                    matlab.close()
            except Exception as exc:
                run.event("matlab_cleanup", "fail", exception_type=type(exc).__name__, message=str(exc))
        _save_gate_summary(run, final_status, failure_code, stage, environment)
        finalize_run(run, final_status, failure_code)
