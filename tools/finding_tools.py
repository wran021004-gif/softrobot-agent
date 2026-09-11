"""Finding proposal validation and optional exact-metric extraction, without inference."""
import json
from schemas.finding import CandidateFinding, Observation
from tools.evidence import EvidenceStore


def validate_finding(finding, run_root):
    finding = CandidateFinding.model_validate(finding)
    store = EvidenceStore(run_root)
    for run_id in finding.source_runs:
        store.run(run_id)
    refs = (*finding.evidence_refs, *(o.evidence for o in (*finding.observation, *finding.ruled_out)))
    for ref in refs:
        if ref.run_id not in finding.source_runs:
            raise ValueError("Finding evidence must belong to source runs")
        store.resolve(ref)
    if set(finding.source_runs) - {r.run_id for r in refs}:
        raise ValueError("Every finding source run needs evidence")
    for observation in (*finding.observation, *finding.ruled_out):
        if observation.evidence.pointer is None:
            raise ValueError("Observation requires an exact evidence pointer")
        if json.dumps(store.resolve(observation.evidence), sort_keys=True) != json.dumps(observation.value, sort_keys=True):
            raise ValueError("Observation contradicts its evidence")
    return finding


def extract_diagnostic_finding(run_id, run_root):
    """Explicit post-run interface; unavailable diagnostics produce no finding.

    No automatic persistence or Skill proposal. No invented acceptance thresholds.
    """
    store = EvidenceStore(run_root)
    store.run(run_id)
    fields = (
        ("compare_model_sim", "model_predicts_tolerance_failure", "M1 predicted tolerance failure"),
        ("compare_model_sim", "tip_discrepancy_m", "Observed endpoint discrepancy in metres; no mismatch criterion"),
        ("check_actuator_limits", "max_pull_limit_observed", "Maximum-pull limit reached in sampled execution"),
        ("check_tendon_tracking", "max_absolute_error_m", "Maximum final tendon length error in metres"),
        ("inspect_numerics", "anomaly_indicators", "Recorded numerical anomaly indicators"),
    )
    observations = []
    try:
        for tool, metric, description in fields:
            available = store.reference(run_id, tool + ".json", "/metrics/evidence_status")
            if store.resolve(available) != "available":
                return None
            ref = store.reference(run_id, tool + ".json", "/metrics/" + metric)
            observations.append(Observation(evidence=ref, value=store.resolve(ref), description=description))
    except ValueError:
        return None
    excluded = tuple(o for o in observations if
                     (o.evidence.pointer == "/metrics/max_pull_limit_observed" and o.value is False)
                     or (o.evidence.pointer == "/metrics/anomaly_indicators" and o.value == []))
    finding = CandidateFinding(finding_id="diagnostic_observation_" + run_id,
        title="Recorded model, actuator, tracking and numerical observations", category="MODEL_SIM_COMPARISON",
        observation=tuple(observations), conditions={"scope": "This run and sampled execution only"},
        evidence_refs=tuple(o.evidence for o in observations), source_runs=(run_id,), ruled_out=excluded,
        unresolved=("Causal attribution UNKNOWN; no validated repair", "No approved mismatch/tracking thresholds",
                    "Absent saturation does not establish actuator correctness; finite states do not establish stability"),
        created_by="harness")
    return validate_finding(finding, run_root)
