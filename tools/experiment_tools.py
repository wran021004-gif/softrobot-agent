"""Small deterministic Harness orchestration over the existing run/trace service."""
import json
import math
import random
from pathlib import Path

from schemas.candidate_evaluation import CandidateEvaluation
from tools.artifact_tools import create_run, finalize_run, file_hash
from tools.experiment_policy_tools import validate_experiment_policy, ApprovalRequired
from tools.harness import run_reach, _snapshot_sources
from tools.spec_tools import ROOT


class BudgetExhausted(ValueError):
    pass


def _read(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


class ExperimentSession:
    def __init__(self, run, experiment, matlab_factory=None, *, debug=False):
        self.run, self.experiment, self.matlab_factory = run, experiment, matlab_factory
        self.results = []
        self.debug = debug
        self.designs = {}
        self.mujoco_attempts = 0
        self.history = run.path / "optimization_history.jsonl"
        self.history.write_text("", encoding="utf-8")

    @property
    def remaining(self):
        return self.experiment.policy.evaluation_budget - len(self.results)

    @property
    def remaining_mujoco(self):
        return self.experiment.policy.mujoco_validation_budget - self.mujoco_attempts

    def evaluate(self, design, fidelity, controller_level="C1"):
        p = self.experiment.policy
        if fidelity not in ("M0", "M1", "MUJOCO"):
            raise ValueError("Unknown fidelity")
        if self.remaining <= 0 or (fidelity == "MUJOCO" and self.remaining_mujoco <= 0):
            raise BudgetExhausted("Explicit evaluation budget exhausted")
        self.experiment.check_unchanged()
        candidate_id = f"candidate_{len(self.results):04d}"
        snapshot = self.run.save(candidate_id + "_design.yaml", design)
        if fidelity == "MUJOCO":
            self.mujoco_attempts += 1
        identity = dict(candidate_id=candidate_id, parent_experiment_id=self.run.record.run_id,
            policy_id=p.policy_id, policy_hash=self.experiment.policy_hash,
            task_contract_id=p.task_contract_id, scope=p.scientific_status, fidelity=fidelity,
            controller_level=controller_level, design_hash=file_hash(snapshot))
        child = None
        with self.run.events.span("candidate_evaluation", inputs={"candidate_id": candidate_id, "fidelity": fidelity}) as outcome:
            try:
                design = self.experiment.validate_candidate(design)
                level = "M0" if fidelity == "M0" else "M1"
                if level not in p.allowed_model_levels or controller_level not in p.allowed_controller_levels:
                    raise ValueError("Route not authorized by policy")
                child = run_reach(self.experiment.resolved.manifest_path.parent, snapshot, self.run.path.parent,
                    matlab_factory=self.matlab_factory, fidelity=fidelity, experiment_path=self.experiment.path,
                    controller_level=controller_level, **({"debug": True} if self.debug else {}),
                    experiment_context={"parent_experiment_id": self.run.record.run_id, "candidate_id": candidate_id})
                # Preserve the completed child even if a subsequent integrity check
                # detects an input change; never orphan an attempted evaluation.
                child_hash = file_hash(child.path / "run.json")
                self.run.save(candidate_id + "_run_reference.json", {
                    "run_id": child.record.run_id, "run_manifest_hash": child_hash,
                    "artifact_hashes": child.record.artifact_hashes,
                    "diagnostics": _read(child.path / "diagnostic_summary.json")})
                self.experiment.check_unchanged()
                if child.record.design_hash != identity["design_hash"]:
                    raise ValueError("Candidate snapshot changed before execution")
                model = _read(child.path / "model_result.json").get("metrics", {})
                model = {**model, "workspace": _read(child.path / "workspace_result.json").get("metrics", {})}
                clearance = _read(child.path / "clearance_result.json").get("metrics")
                if clearance is not None:
                    model["clearance"] = clearance
                actual = _read(child.path / "mujoco_result.json").get("metrics", {})
                canonical = "NOT_RUN" if "task_success" not in actual else "PASS" if actual["task_success"] else "TASK_FAILED"
                result = CandidateEvaluation(**identity, run_id=child.record.run_id,
                    run_manifest_hash=child_hash, robot_ir_hash=child.record.robot_ir_hash,
                    status=child.record.final_status, model_metrics=model, canonical_metrics=actual,
                    canonical_task_status=canonical, failure_message=_read(child.path / "error.json").get("message"))
            except Exception as exc:
                result = CandidateEvaluation(**identity, status="REJECTED", failure_message=str(exc),
                    **({"run_id": child.record.run_id, "run_manifest_hash": file_hash(child.path / "run.json"),
                        "robot_ir_hash": child.record.robot_ir_hash} if child is not None else {}))
            self.designs[candidate_id] = design
            self.results.append(result)
            self.run.save(candidate_id + "_evaluation.json", result)
            with self.history.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(result.model_dump(mode="json"), allow_nan=False) + "\n")
            outcome.update(status="pass" if result.status in ("MODEL_ONLY", "PASS", "TASK_FAILED") else "fail",
                evidence_refs=self.run.events.refs(candidate_id + "_design.yaml", candidate_id + "_evaluation.json"))
            return result

    def decision(self, action, evidence, rule):
        # Refer to exact saved observations; no invented design/model/control cause.
        refs = self.run.events.refs("optimization_policy.yaml", *evidence)
        self.run.events.emit("DECISION_RECORDED", "experiment_route", actor="harness", decision={
            "actor": "harness", "decision": action, "rationale": rule,
            "requested_tools": (), "evidence_refs": refs, "next_action": action}, evidence_refs=refs)


def _execute(policy_path, operation, callback, *, run_root=ROOT / "runs", matlab_factory=None, debug=False):
    run = create_run(run_root)
    status, code = "ERROR", "UNKNOWN"
    session = None
    try:
        path = Path(policy_path).resolve()
        (run.path / "optimization_policy.yaml").write_bytes(path.read_bytes())
        experiment = validate_experiment_policy(path)
        _snapshot_sources(run, tuple(experiment.input_hashes))
        run.save("experiment_provenance.json", {"policy_id": experiment.policy.policy_id,
            "policy_hash": experiment.policy_hash, "scope": experiment.policy.scientific_status,
            "task_contract_id": experiment.policy.task_contract_id,
            "input_hashes": {p.relative_to(ROOT).as_posix(): h for p, h in experiment.input_hashes.items()},
            "artifact_role": "experimental evidence; canonical results live in referenced candidate runs"})
        session = ExperimentSession(run, experiment, matlab_factory, debug=debug)
        with run.events.span(operation):
            summary = callback(session)
        experiment.check_unchanged()
        run.save(operation + "_summary.json", summary)
        status, code = "PASS", None  # Orchestration success, never canonical task success.
    except Exception as exc:
        status = "BLOCKED_FOR_HUMAN_APPROVAL" if isinstance(exc, ApprovalRequired) else "ERROR"
        code = "PHYSICS_ASSUMPTION_REQUIRED" if isinstance(exc, ApprovalRequired) else "UNKNOWN"
        run.save(operation + "_summary.json", {"status": status,
            "executed": bool(session and session.results), "message": str(exc)})
    finally:
        if session is not None:
            run.save("experiment_summary.json", {"operation": operation, "scope": experiment.policy.scientific_status,
                "evaluations": len(session.results), "mujoco_attempts": session.mujoco_attempts,
                "evaluation_budget": experiment.policy.evaluation_budget,
                "mujoco_validation_budget": experiment.policy.mujoco_validation_budget,
                "causal_attribution": "UNKNOWN", "execution_status": status})
        finalize_run(run, status, code)
    return run


def evaluate_candidate(task_contract, design, policy_path, fidelity, *, controller_level="C1",
                       run_root=ROOT / "runs", matlab_factory=None):
    """Return a typed CandidateEvaluation and its finalized parent run artifacts."""
    result = []
    def evaluate(session):
        supplied = Path(task_contract).resolve()
        supplied = supplied / "contract.yaml" if supplied.is_dir() else supplied
        if supplied != session.experiment.resolved.manifest_path:
            raise ValueError("Candidate TaskContract differs from policy")
        result.append(session.evaluate(design, fidelity, controller_level))
        return result[0].model_dump(mode="json")
    run = _execute(policy_path, "candidate_evaluation", evaluate, run_root=run_root, matlab_factory=matlab_factory)
    return (result[0] if result else None), run


def _candidate_stream(experiment):
    """Baseline, coordinate endpoints, then seeded bounded samples; no dependency."""
    baseline = experiment.baseline.model_dump()
    yield experiment.baseline
    for variable in experiment.policy.variables:
        for value in (variable.lower_bound, variable.upper_bound):
            if "integer" in variable.constraints:
                value = int(value)
            yield {**baseline, variable.name: value}
    rng = random.Random(experiment.policy.seed)
    while experiment.policy.variables:
        candidate = dict(baseline)
        for variable in experiment.policy.variables:
            candidate[variable.name] = (rng.randint(int(variable.lower_bound), int(variable.upper_bound))
                if "integer" in variable.constraints else rng.uniform(variable.lower_bound, variable.upper_bound))
        yield candidate


def _metric(result, canonical=False):
    if canonical:
        value = result.canonical_metrics.get("position_error_m") if result.canonical_task_status != "NOT_RUN" else None
    else:
        value = result.model_metrics.get("predicted_position_error_m") if result.status == "MODEL_ONLY" else None
    return value if type(value) in (int, float) and math.isfinite(value) else math.inf


def _optimize(session):
    policy = session.experiment.policy
    if not policy.variables:
        raise ValueError("No approved design optimization variables selected")
    if "M1" not in policy.allowed_model_levels or "C1" not in policy.allowed_controller_levels:
        raise ValueError("Bounded design search requires the approved M1/C1 route")
    if "model.predicted_position_error_m" not in policy.objective_metric_refs:
        raise ValueError("Model ranking objective is not authorized")
    if session.remaining_mujoco and "mujoco.position_error_m" not in policy.objective_metric_refs:
        raise ValueError("Canonical comparison objective is not authorized")
    model_budget = session.remaining - min(session.remaining_mujoco, max(0, session.remaining - 1))
    models = []
    stream = _candidate_stream(session.experiment)
    for _ in range(model_budget):
        models.append(session.evaluate(next(stream), "M1"))
    ranked = sorted(models, key=lambda r: (_metric(r), r.candidate_id))
    canonical = []
    # A baseline measurement precedes other physical comparisons. Screening FAIL
    # remains eligible; only HARD/runtime failures lack a ranking model result.
    selected = [models[0]] + [r for r in ranked if r.candidate_id != models[0].candidate_id and _metric(r) != math.inf]
    for model in selected:
        if session.remaining <= 0 or session.remaining_mujoco <= 0:
            break
        session.decision("validate_candidate", [model.candidate_id + "_evaluation.json"],
            "Policy model objective ranks candidates; baseline first, then ascending model error; actual MuJoCo decides acceptance.")
        canonical.append(session.evaluate(session.designs[model.candidate_id], "MUJOCO"))
        if canonical[-1].canonical_task_status == "PASS" and "canonical_success" in policy.stop_conditions:
            break
    actual = [r for r in canonical if _metric(r, True) != math.inf]
    best_actual = min(actual, key=lambda r: (r.canonical_task_status != "PASS", _metric(r, True), r.candidate_id)) if actual else None
    best_model = next((r for r in ranked if _metric(r) != math.inf), None)
    baseline_actual = canonical[0] if canonical and _metric(canonical[0], True) != math.inf else None
    def boundary(result):
        if result is None:
            return []
        candidate = session.designs[result.candidate_id]
        candidate = candidate.model_dump() if hasattr(candidate, 'model_dump') else candidate
        return [v.name for v in policy.variables if candidate[v.name] in (v.lower_bound, v.upper_bound)]
    actual_boundary, model_boundary = boundary(best_actual), boundary(best_model)
    # Link repeated design evaluations explicitly; no inference from rounded lengths.
    candidate_table = []
    for model in models:
        validations = [r for r in canonical if r.design_hash == model.design_hash]
        candidate = session.designs[model.candidate_id]
        candidate = candidate.model_dump() if hasattr(candidate, 'model_dump') else candidate
        candidate_table.append({"candidate_id": model.candidate_id,
            "total_length_m": candidate['total_length_m'], "robot_ir_hash": model.robot_ir_hash,
            "m1_predicted_error_m": model.model_metrics.get('predicted_position_error_m'),
            "entered_mujoco": bool(validations), "parent_experiment_id": session.run.record.run_id,
            "model_run_id": model.run_id, "model_status": model.status,
            "canonical_task_status": validations[0].canonical_task_status if validations else "NOT_RUN",
            "mujoco_validations": [{"candidate_id": r.candidate_id, "run_id": r.run_id,
                "robot_ir_hash": r.robot_ir_hash, "actual_error_m": r.canonical_metrics.get('position_error_m'),
                "canonical_task_status": r.canonical_task_status} for r in validations]})
    session.run.save("candidate_comparison.json", candidate_table)
    return {"algorithm": "baseline_coordinate_endpoints_seeded_bounded_search", "seed": policy.seed,
        "boundary_result": "BOUNDARY_OPTIMUM_OBSERVED" if actual_boundary else "NO_CANONICAL_BOUNDARY_OPTIMUM_OBSERVED",
        "canonical_boundary_variables": actual_boundary, "model_boundary_variables": model_boundary,
        "bounds_expanded": False, "next_range_authority": "Human",
        "variables": [v.model_dump() for v in policy.variables], "bounds_source": "optimization_policy.yaml intersected with approved grammar",
        "best_model_candidate": best_model.candidate_id if best_model else None,
        "best_canonical_candidate": best_actual.candidate_id if best_actual else None,
        "model_metric_m": _metric(best_model) if best_model else None,
        "mujoco_metric_m": _metric(best_actual, True) if best_actual else None,
        "canonical_task_status": best_actual.canonical_task_status if best_actual else "NOT_RUN",
        "observed_canonical_improvement": bool(best_actual and baseline_actual and _metric(best_actual, True) < _metric(baseline_actual, True)),
        "scope": policy.scientific_status, "physical_validity": "MuJoCo surrogate evidence only; not real robot validation"}


def optimize_design(policy_path, *, run_root=ROOT / "runs", matlab_factory=None, debug=False):
    return _execute(policy_path, "optimization", _optimize, run_root=run_root, matlab_factory=matlab_factory, debug=debug)


def _sensitivity(session, fidelity="M1"):
    if not session.experiment.policy.variables:
        raise ValueError("Sensitivity requires approved variables and bounds")
    baseline = session.experiment.baseline.model_dump()
    observations = []
    for variable in session.experiment.policy.variables:
        rows = []
        for value in sorted(set((variable.lower_bound, baseline[variable.name], variable.upper_bound))):
            if session.remaining <= 0 or (fidelity == "MUJOCO" and session.remaining_mujoco <= 0):
                break
            if "integer" in variable.constraints:
                value = int(value)
            result = session.evaluate({**baseline, variable.name: value}, fidelity)
            score = _metric(result, fidelity == "MUJOCO")
            rows.append({"value": value, "delta_from_baseline": value - baseline[variable.name],
                         "candidate_id": result.candidate_id, "metric": score if math.isfinite(score) else None})
        scores = [r["metric"] for r in rows]
        trend = "UNKNOWN"
        if len(scores) >= 2 and all(x is not None for x in scores):
            trend = ("constant" if len(set(scores)) == 1 else "nondecreasing" if all(a <= b for a,b in zip(scores,scores[1:]))
                     else "nonincreasing" if all(a >= b for a,b in zip(scores,scores[1:])) else "non_monotonic")
        observations.append({"variable": variable.name, "unit": variable.unit, "observations": rows,
            "sampled_effect": trend, "causal_attribution": "UNKNOWN"})
    summary = {"fidelity": fidelity, "evidence": observations, "causal_attribution": "UNKNOWN",
               "limitation": "Finite one-at-a-time observations; no universal threshold or causal conclusion"}
    session.run.save("sensitivity_evidence.json", summary)
    return summary


def run_parameter_sensitivity(policy_path, *, fidelity="M1", run_root=ROOT / "runs", matlab_factory=None):
    return _execute(policy_path, "sensitivity", lambda s: _sensitivity(s, fidelity), run_root=run_root, matlab_factory=matlab_factory)


def _repair(session):
    policy = session.experiment.policy
    baseline = session.evaluate(session.experiment.baseline, "MUJOCO")
    current = baseline
    decisions = []
    stream = _candidate_stream(session.experiment)
    next(stream)
    for iteration, action in enumerate(policy.repair_actions[:policy.repair_iteration_budget]):
        if session.remaining <= 0 or (current.canonical_task_status == "PASS" and "canonical_success" in policy.stop_conditions):
            break
        evidence = [current.candidate_id + "_evaluation.json"]
        ref = current.candidate_id + "_run_reference.json"
        if (session.run.path / ref).is_file():
            evidence.append(ref)
        session.decision(action, evidence,
            "Explicit policy repair_actions order selects this bounded experiment after evaluation; diagnostics are observations, causal attribution remains UNKNOWN.")
        with session.run.events.span("repair_iteration", inputs={"iteration": iteration, "action": action}):
            before = len(session.results)
            if action in ("next_candidate", "synthesize_feedback") and session.remaining_mujoco <= 0:
                break
            if action == "next_candidate":
                try:
                    candidate = next(stream)
                except StopIteration:
                    break
                current = session.evaluate(candidate, "MUJOCO")
            elif action == "synthesize_feedback":
                current = session.evaluate(session.designs[current.candidate_id], "MUJOCO", "C2")
            elif action == "optimize_design":
                session.run.save(f"repair_{iteration:04d}_optimization.json", _optimize(session))
            else:
                session.run.save(f"repair_{iteration:04d}_sensitivity.json", _sensitivity(session))
            canonical = [r for r in session.results[before:] if r.canonical_task_status != "NOT_RUN"]
            if canonical:
                current = min(canonical, key=lambda r: (r.canonical_task_status != "PASS", _metric(r, True)))
            decisions.append({"iteration": iteration, "action": action, "authority": f"optimization_policy.yaml#repair_actions/{iteration}",
                              "evidence_read": evidence, "evaluations": len(session.results)-before, "causal_attribution": "UNKNOWN"})
            session.run.save("repair_decisions.json", decisions)
    return {"iterations": len(decisions), "iteration_budget": policy.repair_iteration_budget,
            "decisions": decisions, "last_canonical_task_status": current.canonical_task_status,
            "causal_attribution": "UNKNOWN"}


def run_repair_loop(policy_path, *, run_root=ROOT / "runs", matlab_factory=None):
    return _execute(policy_path, "repair", _repair, run_root=run_root, matlab_factory=matlab_factory)
