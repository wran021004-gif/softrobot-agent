"""Read-only event census and conservative Evidence-to-Action joins."""

import argparse
import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPERIMENTS = Path("paper_experiments")
DATA = Path("paper_experiment_data")
FULL = ("ten_task_codex_solve_20261112", "five_task_completion_20261113")
BATCHES = ("ab_batch1_20261114", "ab_batch2_20261114")
ROOTS = [
    *(EXPERIMENTS / name for name in (*FULL, *BATCHES, "direct_math_only_20261114",
                                      "knowledge_skill_codex_replay_20261116")),
    DATA / "architecture_ablation",
    DATA / "m1-core-full-20261111",
    *(Path("runs") / name for name in ("phs2d-main-reproduction-20261112-01",
       "phs2d-initialization-successor-20261105", "phs2d-knowledge-autonomy-20261105", "psd2d-core-only-20261112")),
    Path(".worktrees/passive-research-capabilities-20261107/runs/research/"
         "p3-passive-progressive-stiffness-autonomous-20261110-v1_2"),
]
INDEXES = [
    EXPERIMENTS / "paper_results_master_20261113/SOURCE_DATA/SELECTED_RESEARCH_EVENTS.json",
    EXPERIMENTS / "paper_results_master_20261113/SOURCE_DATA/DECISION_CATALOG.json",
    EXPERIMENTS / "paper_results_master_20261113/RAW_RESULT_INDEX.csv",
    EXPERIMENTS / "FINAL_ABC_DATASET_P0_20261114/D3_ABC_EVIDENCE_ACTIONS.csv",
    EXPERIMENTS / "FINAL_ABC_DATASET_P0_20261114/SOURCE_MANIFEST.csv",
    Path("runs/multitask-paper-data-20261118/SUPPLEMENTARY/complete_decision_index.csv"),
]
SKIP = {"analyses", "artifacts", "runtime", "physical_replay", "OPERATION_STDOUT",
        "MAIN_REPLAY_INPUT", "REQUESTS", "__pycache__", "blind_review", "prior_figure_data"}
MATH = {"candidate_analysis_result", "direct_mathematical_result", "direct_gvs_equilibrium",
        "mathematical_result", "mechanical_analysis", "mechanism_evidence"}
PHYSICS = {"physical_playback_result", "independent_evaluation", "physical_execution",
           "task_acceptance", "evaluation", "physical_execution_result", "physical_profile"}
STATUSES = ("Proposed", "Selected", "Dispatched", "Executed", "Validated")
EXCLUDE = {"diagnose", "read", "select", "stop", "report", "route", "inspect",
    "bind", "aggregate", "trace", "schema", "none", "unknown", "unresolved_selected_scientific_tool"}
GOOD = {"computed", "evaluated", "generated", "completed", "succeeded", "ready",
        "qualified", "feasible", "first_original_task_pass"}
BAD = {"failed", "error", "execution_incomplete", "unsupported", "needs_choice",
       "not_applicable", "unavailable", "incomplete", "rejected"}


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def loc(path, suffix):
    return f"{path}#{suffix}"


def artifact_id(value):
    value = value.get("artifact_id") if isinstance(value, dict) else value
    return value if isinstance(value, str) and re.fullmatch("[a-f0-9]{64}", value) else ""


def refs(value):
    if isinstance(value, dict):
        if identifier := artifact_id(value):
            yield identifier
        for nested in value.values():
            yield from refs(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from refs(nested)
    elif identifier := artifact_id(value):
        yield identifier


def task_for(path, event):
    task = event.get("task_id")
    if task:
        return task
    if "m1-core-full-20261111" in path:
        return "T01"
    if "p3-passive-progressive-stiffness-autonomous" in path:
        return "T08"
    if "phs2d" in path.lower() or "psd2d" in path.lower() or "PHS-2D" in path:
        return "PHS-2D"
    if match := re.search(r"(?:^|/)T(\d\d)(?:[/_]|$)", path):
        return "T" + match[1]
    snapshot = event.get("snapshot_id") or ""
    if snapshot.upper().startswith("PHS"):
        return "PHS-2D"
    if snapshot.startswith("P3"):
        return "T08"
    if snapshot.startswith("M1"):
        return "T01"
    return "UNMAPPED"


def actor_for(event, kind, path):
    actor = event.get("actor") or event.get("agent_id") or event.get("caller") or ""
    lowered = str(actor).lower()
    if "reporter" in lowered or kind == "research_report" or "reporter_" in kind:
        return "Reporter"
    if any(key in lowered for key in ("human", "operator", "manual")) or kind.startswith("operator_"):
        return "Human/operator"
    if "codex" in lowered or "codex" in kind or kind.startswith("codex_"):
        return "External Codex"
    if "subagent" in lowered or "child" in lowered or kind.startswith("worker_agent"):
        return "Sub-agent"
    if lowered in ("main", "main_agent", "unified-research", "research-provider"):
        return "Main Agent"
    if kind in {"research_decision", "model_original_tool_request", "model_original_tool_feedback"} and (
            "/ab_batch" in path or kind.startswith("model_original_")):
        return "Main Agent"
    if lowered in ("host", "batch1", "batch2", "program", "fixed_program"):
        return "Fixed program"
    return "Unknown"


def action_type(tool, args):
    if tool in ("research.math", "research_math", "research_analysis", "math"):
        operation = args.get("operation") or args.get("domain")
        return "control_optimization" if operation and ("control" in operation or "capability" in operation) else "mathematical_analysis"
    if tool in ("research.dispatch", "research_plan", "research_plan_replay"):
        return args.get("action") or "none"
    if tool in ("generate", "evaluate", "execute", "physical_replay", "initialize_control", "propose"):
        return tool
    return "none"


def result_parts(result):
    data = result.get("data", result) if isinstance(result, dict) else {}
    inner = data.get("result", data)
    return data, inner if isinstance(inner, dict) else {}


def arguments(event):
    request = event.get("exact_input") or event.get("request") or {}
    return (request.get("arguments") or {}) if isinstance(request, dict) else {}


def scientific_refs(args):
    fields = ("evidence", "supporting_evidence", "physical_replay", "control_seed",
              "control_optimization", "source_selection")
    return set(refs([args.get(key) for key in fields]))


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


class Audit:
    def __init__(self, root):
        self.root = root
        self.events, self.actions, self.sources = [], [], []
        self.science = defaultdict(set)
        self.science_locators = defaultdict(set)
        self.by_scope = defaultdict(list)
        self.stores = {}
        self.input_records = []
        self.validation = defaultdict(list)
        self.cli_records = []
        self.seen_actions = set()
        self.gaps = Counter()

    def add_science(self, identifier, kind, locator):
        if identifier:
            self.science[identifier].add(kind)
            self.science_locators[identifier].add(locator)

    def path(self, path):
        return path.relative_to(self.root).as_posix()

    def event(self, path, key, row, default=""):
        kind = row.get("kind") or row.get("type") or row.get("event") or default
        locator = loc(path, key)
        out = set(refs([row.get("outputs"), row.get("output_artifact_ids"), row.get("artifact_reference"),
                        row.get("output_reference")]))
        actor = actor_for(row, kind, path)
        self.events.append(dict(task_id=task_for(path, row), trace_id=path,
            event_id=row.get("event_id") or row.get("request_id") or row.get("call_id") or row.get("tool_use_id") or key, event_type=kind,
            source=locator, actor=actor, raw_actor=row.get("actor") or row.get("agent_id") or row.get("caller") or "",
            status=row.get("status") or row.get("execution_status") or "", run_id=row.get("run_id") or row.get("study_id") or "",
            request_id=row.get("request_id") or "", execution_id=row.get("execution_id") or "",
            parent_id=row.get("parent_id") or "", tool=row.get("tool_name") or row.get("tool_id") or row.get("tool") or "",
            candidate_id=artifact_id(row.get("candidate_id")) or artifact_id(row.get("candidate")),
            artifact_ids=";".join(sorted(out))))
        return kind, locator, out

    def store(self, path):
        relative = self.path(path)
        if not path.stat().st_size:
            self.gaps["empty_store"] += 1
            self.sources.append(dict(path=relative, scope="empty_store", sha256=sha(b""), records=0))
            return
        wal = path.with_name(path.name + "-wal")
        if wal.exists() and wal.stat().st_size:
            self.gaps["nonempty_wal_store_skipped"] += 1
            self.sources.append(dict(path=relative, scope="nonempty_wal_skipped", sha256="", records=0))
            return
        db = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)
        tables = {name for name, in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"events", "calls", "artifacts"} <= tables:
            db.close()
            self.gaps["unrecognized_store"] += 1
            self.sources.append(dict(path=relative, scope="unrecognized_store", sha256="", records=0))
            return
        self.stores[relative] = db
        digest = hashlib.sha256()
        counts = 0
        for seq, raw in db.execute("SELECT seq,body FROM events ORDER BY seq"):
            digest.update(f"{seq}\t{raw}\n".encode())
            row = json.loads(raw)
            kind, locator, output = self.event(relative, f"events:{seq}", row)
            if kind in MATH | PHYSICS and row.get("status") not in BAD:
                for identifier in output:
                    self.add_science(identifier, "mathematical" if kind in MATH else "physical", locator)
            if kind in {"model_original_tool_request", "model_original_tool_feedback", "analysis_request_binding",
                        "scientific_intent_compilation", "plan_choice_resolution", "replay_choice_resolution",
                        "scientific_result_choice_resolution", "candidate_analysis_result", "physical_playback_result",
                        "candidate_control_initialization"}:
                self.by_scope[relative].append((seq, kind, locator, row, sorted(output)))
            counts += 1
        for run, request, execution, caller, status, raw in db.execute(
                "SELECT run_id,request_id,execution_id,caller,status,receipt FROM calls ORDER BY run_id,request_id"):
            digest.update(json.dumps([run, request, execution, caller, status, raw], ensure_ascii=False).encode() + b"\n")
            row = json.loads(raw) if raw else {}
            self.event(relative, f"calls:{run}/{request}", dict(row, run_id=run, request_id=request,
                execution_id=execution, caller=caller, status=status, outputs=[row.get("output")]), "store_call")
            counts += 1
        self.sources.append(dict(path=relative, scope="sqlite_events_and_calls_logical_sha256", sha256=digest.hexdigest(), records=counts))

    def body(self, store, identifier):
        if not identifier:
            return {}
        row = self.stores[store].execute("SELECT media, body FROM artifacts WHERE id=?", (identifier,)).fetchone()
        if row is None or row[0] != "application/json":
            return {}
        return json.loads(row[1])

    def js(self, path):
        relative = self.path(path)
        raw = path.read_bytes()
        rows = []
        for line, content in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
            if not content.strip():
                continue
            try:
                row = json.loads(content)
            except ValueError:
                self.gaps["unparseable_jsonl_row"] += 1
                continue
            if not isinstance(row, dict):
                self.gaps["nonobject_jsonl_row"] += 1
                continue
            kind, locator, output = self.event(relative, f"L{line}", row, path.stem)
            rows.append((line, kind, locator, row, output))
        self.sources.append(dict(path=relative, scope="jsonl_sha256", sha256=sha(raw), records=len(rows)))
        self.input_records.append((relative, rows))

    def add_action(self, path, source, row, decision, event_id, tool, action, stage, evidence, *,
                   artifact="", candidate="", evaluation="", actor=None, outcome="", execution="", match=""):
        action = action or "unknown"
        run = row.get("run_id") or row.get("study_id") or row.get("session_id") or path
        actor = actor or actor_for(row, row.get("kind") or "", path)
        key = (run, event_id, actor)
        if key in self.seen_actions:
            return
        self.seen_actions.add(key)
        science = sorted(set(evidence) & self.science.keys())
        types = "+".join(sorted({kind for ref in science for kind in self.science[ref]}))
        self.actions.append(dict(task_id=task_for(path, row), trace_id=path, decision_id=decision,
            action_id=event_id, evidence_id=";".join(science), evidence_type=types or "UNCONFIRMED",
            action_type=action, action_tool=tool, execution_status=stage, artifact_id=artifact,
            candidate_id=candidate, evaluation_id=evaluation, actor=actor, outcome=outcome,
            decision_locator=source, execution_locator=execution, validation_locator="",
            source_scope="decision_only_replay" if tool == "research_plan_replay" else "operational_archive",
            explicit_refs=";".join(sorted(evidence)), link_basis=match,
            evidence_locator=";".join(sorted({item for ref in science for item in self.science_locators[ref]})),
            denominator="yes" if science and decision and action not in EXCLUDE and actor != "Reporter" else "no"))
        return self.actions[-1]

    def index_science(self):
        seeds = []
        for path, entries in self.by_scope.items():
            for seq, kind, locator, row, identifiers in entries:
                for identifier in identifiers:
                    if kind == "candidate_control_initialization":
                        value = self.body(path, identifier)
                        source = artifact_id(value.get("provenance", {}).get("source"))
                        if source and value.get("trajectory"):
                            seeds.append((identifier, source, locator))
                    if kind not in {"candidate_analysis_result", "physical_playback_result"}:
                        continue
                    value = self.body(path, identifier)
                    if kind == "candidate_analysis_result" and value.get("status") == "computed":
                        for output in refs([value.get("control_schedule_reference"),
                                            value.get("optimized_schedule_reference")]):
                            if self.body(path, output):
                                self.add_science(output, "mathematical", locator)
                    if kind == "physical_playback_result" and value.get("status") == "evaluated":
                        source = artifact_id(value.get("source_reference"))
                        evaluation = artifact_id(value.get("evaluation_reference"))
                        candidate = artifact_id(value.get("candidate"))
                        if evaluation and self.body(path, evaluation):
                            self.add_science(evaluation, "physical", locator)
                            if source and value.get("acceptance", {}).get("accepted") is True:
                                self.validation[(path, source, candidate)].append((seq, evaluation, locator))
        while seeds:
            pending = []
            for identifier, source, locator in seeds:
                if source in self.science:
                    for kind in self.science[source]:
                        self.add_science(identifier, kind, locator)
                    self.science_locators[identifier].update(self.science_locators[source])
                else:
                    pending.append((identifier, source, locator))
            if len(pending) == len(seeds):
                break
            seeds = pending

    def main_actions(self):
        for path, entries in self.by_scope.items():
            received, resolution = {}, defaultdict(list)
            for seq, kind, locator, row, output in entries:
                if not output or kind not in {"model_original_tool_feedback", "analysis_request_binding",
                        "scientific_intent_compilation", "plan_choice_resolution", "replay_choice_resolution",
                        "scientific_result_choice_resolution"}:
                    continue
                body = self.body(path, output[0])
                if kind == "model_original_tool_feedback" and (call := body.get("tool_use", {}).get("toolUseId")):
                    received[(row.get("run_id"), call)] = (locator, body)
                elif call := body.get("tool_use_id"):
                    resolution[(row.get("run_id"), call)].append(body)
            for seq, kind, locator, row, output in entries:
                if kind != "model_original_tool_request" or not output:
                    continue
                use = self.body(path, output[0]).get("tool_use") or {}
                call, tool, args = use.get("toolUseId"), use.get("name"), use.get("input")
                if not call or not isinstance(args, dict):
                    continue
                action = action_type(tool, args)
                if action in EXCLUDE:
                    continue
                key = (row.get("run_id"), call)
                feedback_locator, feedback = received.get(key, ("", {}))
                assert not feedback or feedback["tool_use"] == use
                reply = feedback.get("result") or {}
                text = next((item["text"] for item in reply.get("content", []) if "text" in item), "")
                try:
                    result = json.loads(text)
                except ValueError:
                    result = {}
                if not isinstance(result, dict):
                    result = {}
                linked = scientific_refs(args) | scientific_refs(args.get("control") or {})
                for binding in resolution[key]:
                    for field in ("expanded_plan", "compiled_question", "full_request"):
                        resolved = binding.get(field) or {}
                        if isinstance(resolved, dict):
                            linked |= scientific_refs(resolved) | scientific_refs(resolved.get("control") or {})
                    linked |= set(refs(binding.get("selected_result")))
                identifier = artifact_id(result.get("scientific_result_reference")) or artifact_id(result.get("wrapper_reference"))
                value = self.body(path, identifier)
                _, inner = result_parts(value)
                status = result.get("scientific_result_status") or result.get("status") or inner.get("status")
                candidate = artifact_id(inner.get("candidate") or result.get("operation_outcome", {}).get("candidate"))
                eval_id = artifact_id(inner.get("evaluation_reference"))
                nested_failure = (inner.get("nonlinear_capability") or {}).get("stop_reason") or ""
                ok = (reply.get("status") == "success" and value and
                      result.get("execution_status", "completed") == "completed" and status not in BAD and
                      not nested_failure.startswith("numerical_failure") and
                      (status in GOOD or (action == "initialize_control" and candidate and artifact_id(inner.get("source")))))
                entry = self.add_action(path, locator, row, call, call, tool, action, "Executed" if ok else "Dispatched",
                    linked, artifact=identifier if value else "", candidate=candidate, evaluation=eval_id,
                    actor="Main Agent", outcome=status or ("receipt_without_verified_result" if feedback else "no_feedback"),
                    execution=feedback_locator, match="original toolUseId + exact tool request + explicit resolved refs")
                if ok and entry:
                    self.mark_validation(search_stores=[path], sequence=seq, candidate=candidate, row=entry,
                        handoff=inner.get("control_schedule_reference"))

    def mark_validation(self, search_stores, sequence, candidate, row, handoff):
        for store in search_stores:
            downstream = self.validation.get((store, artifact_id(handoff), candidate), [])
            later = next((value for value in downstream if sequence is None or value[0] > sequence), None)
            if later:
                _, evaluation, locator = later
                row.update(execution_status="Validated", evaluation_id=evaluation, validation_locator=locator)
                return

    def surrogate_actions(self, path, entries):
        decisions = {(e.get("study_id"), e.get("event_id")): (e, locat)
                     for _, kind, locat, e, _ in entries if kind == "decision"}
        used = set()
        for line, kind, locator, row, outputs in entries:
            if kind not in {"tool_call", "native_tool_call"}:
                continue
            tool = row.get("tool_name") or ""
            args = arguments(row)
            action = action_type(tool, args)
            if action in EXCLUDE:
                continue
            request_id = row.get("event_id") or str(line)
            exact = row.get("exact_input") or {}
            run = row.get("study_id")
            decision_key = (run, request_id + "-decision")
            choice, decision_locator = decisions.get(decision_key, ({}, ""))
            bound = (bool(choice) and exact.get("request_id") == request_id and
                     arguments(choice).get("selected_tool") == tool and
                     choice.get("actor") == row.get("actor"))
            if bound:
                used.add(decision_key)
            path_source = str(row.get("store_id") or "").replace("\\", "/")
            prefix = path.rsplit("/", 1)[0]
            stores = [key for key in self.stores if key.startswith(prefix + "/") and
                      (not path_source or path_source.lower().endswith(key.lower()))]
            data, inner = result_parts(row.get("output"))
            ids = sorted(outputs)
            out = next((identifier for identifier in ids if any(self.body(store, identifier) for store in stores)), "")
            status = inner.get("status") or data.get("status") or row.get("status")
            computed = inner.get("scientific_computation") or {}
            solver_stop = (inner.get("nonlinear_capability") or {}).get("stop_reason") or ""
            ok = (out and row.get("status") == "completed" and status not in BAD and
                  not solver_stop.startswith("numerical_failure") and
                  (action not in {"control_optimization", "mathematical_analysis"} or
                   (status == "computed" and computed.get("complete") is not False)) and
                  (action not in {"physical_replay", "execute"} or status in {"evaluated", "completed"}))
            linked = (scientific_refs(arguments(choice)) | scientific_refs(args) |
                      set(refs([row.get("evidence_refs"), exact.get("evidence")])))
            candidate = artifact_id(inner.get("candidate")) or artifact_id(row.get("candidate_id"))
            entry = self.add_action(path, decision_locator or locator, row, choice.get("event_id", "") if bound else "",
                request_id, tool, action, "Executed" if ok else "Dispatched", linked if bound else set(),
                artifact=out, candidate=candidate, evaluation=artifact_id(inner.get("evaluation_reference")),
                outcome=status or "unknown", execution=locator,
                match="exact request ID, selector, actor and Store output" if bound else "no verified decision join")
            handoff = (inner.get("native_analysis") or {}).get("control_schedule_reference") or inner.get("source")
            if ok and entry and artifact_id(handoff):
                for store in stores:
                    if self.body(store, artifact_id(handoff)):
                        producer = next((seq for seq, type_, _, _, identifiers in self.by_scope[store]
                            if type_ == "candidate_analysis_result" and artifact_id(inner.get("reference")) in identifiers), None)
                        if producer is not None:
                            self.mark_validation([store], producer, candidate, entry, handoff)
        for key, (choice, locator) in decisions.items():
            if key in used:
                continue
            args = arguments(choice)
            tool = args.get("selected_tool") or ""
            if tool in ("research.math", "research.dispatch"):
                self.add_action(path, locator, choice, choice["event_id"], choice["event_id"], tool,
                    "unresolved_selected_scientific_tool", "Selected", scientific_refs(args),
                    outcome="no verified dispatch join", match="explicit decision reference only")

    def other_actions(self, path, entries):
        for line, kind, locator, row, output in entries:
            if kind == "research_decision" and isinstance(row.get("commands"), list):
                for index, command in enumerate(row["commands"], 1):
                    tool = command.get("operation", "")
                    if tool in EXCLUDE:
                        continue
                    self.add_action(path, locator, row, locator, f"{locator}:{index}", tool, tool, "Selected",
                        scientific_refs(command.get("arguments") or {}),
                        outcome="authored command; no exact receipt join", actor="Main Agent",
                        match="prose evidence is not an artifact edge")
            elif "/architecture_ablation/" in path and isinstance(row.get("decision"), dict):
                args = row["decision"]
                action = args.get("action") or args.get("next_research_action") or "none"
                if action == "diagnose":
                    action = args.get("next_research_action") or "none"
                if action not in EXCLUDE:
                    self.add_action(path, locator, row, row.get("session_id") or locator, locator, "research_plan_replay",
                        action, "Selected", scientific_refs(args), actor="Main Agent",
                        outcome="decision-only replay; no native dispatch", match="explicit reference in replay decision")
            elif kind in {"operation_error", "evaluation", "final_acceptance_complete", "candidate_frozen",
                          "initial_qualification", "recover_authored_evaluation"}:
                tool = (row.get("command") or {}).get("operation") or kind
                actor = actor_for(row, kind, path)
                if actor == "Unknown" and "/ab_batch" in path:
                    actor = "Fixed program"
                stage = ("Proposed" if kind == "recover_authored_evaluation" else
                         "Executed" if output and kind != "operation_error" else "Dispatched")
                self.add_action(path, locator, row, "", locator, tool, tool, stage, set(),
                    artifact=next(iter(sorted(output)), ""), outcome="error" if kind == "operation_error" else
                    "archived result, evidence-to-decision edge unconfirmed", actor=actor, execution=locator)

    def index_cli(self, path, entries):
        directory = (self.root / path).parent
        for _, _, locator, row, _ in entries:
            tool = row.get("tool", "")
            if tool.startswith("research_plan "):
                action = tool.split()[1]
            elif tool.startswith("research_analysis /"):
                action = "mathematical_analysis"
            else:
                continue
            if action in EXCLUDE:
                continue
            output = row.get("output") or {}
            record = row.get("input") or {}
            args, value, out_locator = {}, {}, ""
            for name, destination in ((record.get("plan") or record.get("query"), "input"),
                                      (output.get("stdout"), "output")):
                if not isinstance(name, str):
                    continue
                file = (directory / name).resolve()
                if not file.is_relative_to(directory) or not file.is_file():
                    continue
                payload = file.read_bytes()
                fingerprint = sha(payload)
                if destination == "output" and (output.get("stdout_sha256") != fingerprint or output.get("exit_code") != 0):
                    continue
                try:
                    parsed = json.loads(payload)
                except ValueError:
                    continue
                role = "cli_exact_input" if destination == "input" else "cli_sha_verified_output"
                self.sources.append(dict(path=self.path(file), scope=role, sha256=fingerprint, records=1))
                if destination == "input":
                    args = parsed
                else:
                    _, value = result_parts(parsed)
                    out_locator = self.path(file)
            identifier = artifact_id(value.get("reference")) or artifact_id(value.get("candidate"))
            evaluated = value.get("status") in GOOD and bool(identifier) and bool(out_locator)
            if evaluated and action in {"physical_replay", "mathematical_analysis"}:
                evidence_kind = "physical" if action == "physical_replay" else "mathematical"
                self.add_science(identifier, evidence_kind, out_locator)
            self.cli_records.append((path, locator, row, action, tool, args, value, identifier, evaluated, out_locator))

    def cli_actions(self):
        for path, locator, row, action, tool, args, value, identifier, ok, output in self.cli_records:
            candidate = artifact_id(value.get("candidate"))
            evaluation = artifact_id(value.get("evaluation_reference"))
            self.add_action(path, locator, row, row["call_id"] if args else "", row["call_id"], tool, action,
                "Executed" if ok else "Dispatched", scientific_refs(args), artifact=identifier if ok else "",
                candidate=candidate, evaluation=evaluation, outcome=value.get("status") or row.get("status") or "",
                actor="External Codex", execution=output or locator,
                match="call record, exact input file, archived stdout SHA256")

    def run(self):
        for prefix in ROOTS:
            folder = self.root / prefix
            if not folder.is_dir():
                self.gaps["missing_archive_root"] += 1
            for path in sorted(folder.rglob("platform.sqlite")):
                relative = path.relative_to(folder)
                if set(relative.parts) & SKIP or (prefix.parts[0] == "runs" and any(
                        part.startswith(("s125-preflight", "p63a-fixture", "u3-wire")) for part in relative.parts)):
                    continue
                self.store(path)
            for path in sorted(folder.rglob("*.jsonl")):
                if set(path.relative_to(folder).parts) & SKIP:
                    continue
                if re.search(r"trace|events|invocation|decision|replay_results|transport_rejections", path.name, re.I):
                    self.js(path)
        for relative in INDEXES:
            path = self.root / relative
            if path.is_file():
                self.sources.append(dict(path=relative.as_posix(), scope="index_only", sha256=sha(path.read_bytes()), records=""))
            else:
                self.gaps["missing_index"] += 1
        ablation = self.root / DATA / "architecture_ablation"
        for path in sorted(ablation.glob("*/snapshots/*.json")):
            self.sources.append(dict(path=self.path(path), scope="snapshot_index_only",
                sha256=sha(path.read_bytes()), records=""))
        self.index_science()
        for path, entries in self.input_records:
            if path == "runs/psd2d-core-only-20261112/TOOL_TRACE.jsonl":
                self.index_cli(path, entries)
        self.main_actions()
        self.cli_actions()
        for path, entries in self.input_records:
            if "/STUDY_TRACE" in path:
                self.surrogate_actions(path, entries)
            else:
                self.other_actions(path, entries)
        for db in self.stores.values():
            db.close()


def summarize(actions):
    eligible = [row for row in actions if row["denominator"] == "yes"]
    counts = Counter(row["execution_status"] for row in eligible)
    stages = {status.lower(): sum(counts[stage] for stage in STATUSES[index:])
              for index, status in enumerate(STATUSES)}
    assert list(stages.values()) == sorted(stages.values(), reverse=True)
    assert all(row["artifact_id"] for row in eligible if row["execution_status"] in STATUSES[3:])
    assert all(row["evaluation_id"] and row["validation_locator"] for row in eligible if row["execution_status"] == "Validated")
    total, executed, validated = stages["proposed"], stages["executed"], stages["validated"]
    return dict(**stages, execution_conversion_rate=executed / total if total else None,
                validation_conversion_rate=validated / executed if executed else None,
                proposal_to_validation_rate=validated / total if total else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive_root", type=Path)
    parser.add_argument("--output", type=Path, default=HERE)
    args = parser.parse_args()
    audit = Audit(args.archive_root.resolve())
    audit.run()
    assert audit.events and audit.actions
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "trace_event_ledger.csv", audit.events, list(audit.events[0]))
    write_csv(out / "evidence_to_action.csv", audit.actions, list(audit.actions[0]))
    write_csv(out / "source_manifest.csv", audit.sources, list(audit.sources[0]))
    summary = summarize(audit.actions)
    tables = []
    for column in ("task_id", "action_type", "evidence_type", "actor"):
        groups = defaultdict(list)
        for row in audit.actions:
            groups[row[column]].append(row)
        table = [dict(group=group, **summarize(rows),
                      unconfirmed=sum(row["denominator"] == "no" for row in rows))
                 for group, rows in sorted(groups.items())]
        write_csv(out / f"by_{column}.csv", table, list(table[0]))
        tables.append((column, {item["group"]: {key: value for key, value in item.items() if key != "group"} for item in table}))
        for stage in ("proposed", "selected", "dispatched", "executed", "validated"):
            assert sum(item[stage] for item in table) == summary[stage]
    write_csv(out / "funnel.csv", [dict(stage=stage.title(), count=summary[stage])
              for stage in ("proposed", "selected", "dispatched", "executed", "validated")], ["stage", "count"])
    groups = defaultdict(list)
    joint = defaultdict(list)
    for row in audit.actions:
        groups[(row["task_id"], row["actor"])].append(row)
        joint[(row["task_id"], row["action_type"])].append(row)
    task_actor = [dict(task_id=task, actor=actor, **summarize(rows))
                  for (task, actor), rows in sorted(groups.items())]
    write_csv(out / "by_task_actor.csv", task_actor, list(task_actor[0]))
    task_action = [dict(task_id=task, action_type=kind, **summarize(rows))
                   for (task, kind), rows in sorted(joint.items())]
    write_csv(out / "by_task_action_type.csv", task_action, list(task_action[0]))
    delegated = summarize([row for row in audit.actions if row["actor"] in ("Main Agent", "External Codex", "Human/operator")])
    scope_counts = {scope: summarize([row for row in audit.actions if row["source_scope"] == scope])
                    for scope in ("operational_archive", "decision_only_replay")}
    result = dict(**summary, historical_trace_rows=len(audit.events), historical_sources=len(audit.sources),
                  action_rows=len(audit.actions), new_runs=0,
                  unconfirmed_action_rows=sum(row["denominator"] == "no" for row in audit.actions),
                  coverage_gaps=dict(audit.gaps), main_role_rollup_including_external_operators=delegated,
                  by_source_scope=scope_counts, **dict(tables))
    (out / "summary.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({key: result[key] for key in (*summary, "historical_trace_rows", "action_rows", "coverage_gaps")}))


if __name__ == "__main__":
    main()
