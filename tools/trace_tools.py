"""Local append-only logical trace, with bounded events and causal span validation."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from time import perf_counter
import yaml
from schemas.trace import TraceEvent, EventType
from schemas.evidence import ArtifactReference

STARTS = {"RUN_STARTED", "STAGE_STARTED", "TOOL_STARTED", "DIAGNOSTIC_STARTED"}
FINISHES = {"RUN_FINISHED": "RUN_STARTED", "STAGE_FINISHED": "STAGE_STARTED",
            "TOOL_FINISHED": "TOOL_STARTED", "TOOL_FAILED": "TOOL_STARTED",
            "DIAGNOSTIC_FINISHED": "DIAGNOSTIC_STARTED"}


def resolve_local_reference(ref, run_path):
    root = Path(run_path).resolve()
    if ref.run_id != root.name:
        raise ValueError("Trace reference must belong to this run")
    target = (root / ref.path).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise ValueError(f"Missing or escaping artifact: {ref.path}")
    return target


def validate_trace(events, run_path=None, *, complete=True):
    events = [TraceEvent.model_validate(e.model_dump(mode="json") if isinstance(e, TraceEvent) else e) for e in events]
    seen, open_spans, artifacts = {}, set(), {}
    if not events or events[0].event_type != "RUN_STARTED":
        raise ValueError("Trace must begin with RUN_STARTED")
    if run_path is not None and events[0].run_id != Path(run_path).name:
        raise ValueError("Trace run ID differs from artifact directory")
    for index, event in enumerate(events):
        if event.sequence != index or event.event_id in seen or event.run_id != events[0].run_id:
            raise ValueError("Invalid sequence, duplicate event ID or mixed runs")
        if index == 0:
            if event.parent_event_id is not None:
                raise ValueError("Root cannot have a parent")
        elif event.parent_event_id not in open_spans:
            raise ValueError("Parent must be an earlier, open span (no cycles)")
        if index and event.timestamp < events[index - 1].timestamp:
            raise ValueError("Timestamps must be ordered")
        kind = event.event_type.value
        if index and kind == "RUN_STARTED":
            raise ValueError("Only one run root is permitted")
        if kind in STARTS:
            if event.status != "started":
                raise ValueError("Start event must have started status")
            open_spans.add(event.event_id)
        elif kind in FINISHES:
            parent = seen.get(event.parent_event_id)
            if (not parent or parent.event_type != FINISHES[kind] or parent.operation != event.operation
                    or parent.actor != event.actor or event.duration_s is None
                    or event.status not in ("pass", "fail", "not_run")):
                raise ValueError("Invalid start/finish pairing")
            if kind == "TOOL_FAILED" and event.status != "fail":
                raise ValueError("TOOL_FAILED requires fail status")
            if any(seen[s].parent_event_id == parent.event_id for s in open_spans):
                raise ValueError("Cannot close span with active children")
            open_spans.remove(parent.event_id)
        elif event.status == "started":
            raise ValueError("Non-start event has started status")
        if run_path is not None:
            refs = event.evidence_refs + (event.decision.evidence_refs if event.decision else ())
            for ref in refs:
                target = resolve_local_reference(ref, run_path)
                if ref.sha256 or ref.pointer:
                    if ref.path not in artifacts:
                        artifacts[ref.path] = target.read_bytes()
                    raw = artifacts[ref.path]
                    if ref.sha256 and hashlib.sha256(raw).hexdigest() != ref.sha256:
                        raise ValueError("Trace artifact hash mismatch")
                    if ref.pointer:
                        try:
                            value = yaml.safe_load(raw) if ref.path.endswith((".yaml", ".yml")) else json.loads(raw)
                            for part in ref.pointer[1:].split("/"):
                                part = part.replace("~1", "/").replace("~0", "~")
                                value = value[int(part)] if isinstance(value, list) and part.isdecimal() else value[part]
                        except (KeyError, IndexError, ValueError, TypeError) as exc:
                            raise ValueError("Trace artifact pointer does not resolve") from exc
        seen[event.event_id] = event
    if complete and (events[-1].event_type != "RUN_FINISHED" or open_spans):
        raise ValueError("Incomplete trace")
    return events


def read_trace(path, *, validate=True):
    path = Path(path)
    events = [TraceEvent.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines()]
    return validate_trace(events, path.parent) if validate else events


class TraceWriter:
    def __init__(self, run_path, *, previous_run_id=None, relationship=None):
        self.path = Path(run_path) / "trace.jsonl"
        self.run_id = self.path.parent.name
        self.events, self.stack = [], []
        self.closed = False
        self.started = perf_counter()
        # No persistent file handle: callers may abandon an unfinalized run.
        self.path.touch(exist_ok=False)
        metadata = {} if previous_run_id is None else {"previous_run_id": previous_run_id, "relationship": relationship}
        root = self.emit("RUN_STARTED", "run", status="started", metadata=metadata)
        self.stack.append(root.event_id)

    def refs(self, *paths):
        return tuple(ArtifactReference(run_id=self.run_id, path=p) for p in paths)

    def emit(self, event_type, operation, *, actor="harness", status="recorded", parent_event_id=None, **fields):
        if self.closed:
            raise ValueError("Trace is sealed")
        event = TraceEvent(event_id=f"{self.run_id}_e{len(self.events):06d}", run_id=self.run_id,
                           parent_event_id=parent_event_id or (self.stack[-1] if self.stack else None),
                           sequence=len(self.events), timestamp=datetime.now(timezone.utc), actor=actor,
                           event_type=event_type, operation=operation, status=status, **fields)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(event.model_dump_json() + "\n")
        self.events.append(event)
        return event

    @contextmanager
    def span(self, operation, *, kind="STAGE", actor="harness", inputs=None, evidence_refs=()):
        started = perf_counter()
        event = self.emit(kind + "_STARTED", operation, actor=actor, status="started",
                          inputs=inputs or {}, evidence_refs=evidence_refs)
        self.stack.append(event.event_id)
        outcome = {"status": "pass"}
        try:
            yield outcome
        except Exception as exc:
            outcome.update(status="fail", failure_code="UNKNOWN", summary={"exception_type": type(exc).__name__})
            raise
        finally:
            finish = "TOOL_FAILED" if kind == "TOOL" and outcome["status"] == "fail" else kind + "_FINISHED"
            self.emit(finish, operation, actor=actor, duration_s=perf_counter() - started, **outcome)
            self.stack.pop()

    def close(self, status, failure_code=None):
        if self.closed:
            raise ValueError("Trace already sealed")
        if len(self.stack) != 1:
            raise ValueError("Trace has active spans")
        self.emit("RUN_FINISHED", "run", status="pass" if status == "PASS" else "fail",
                  failure_code=failure_code, summary={"final_status": status}, duration_s=perf_counter() - self.started)
        self.closed = True
        validate_trace(self.events, self.path.parent)
        # Validate the persisted representation before it enters the manifest.
        read_trace(self.path)
