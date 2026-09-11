"""Append evidence to a unique directory. Final records reference exact file bytes."""
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version, PackageNotFoundError
import json
from pathlib import Path
import platform
import subprocess
from uuid import uuid4
import yaml
from schemas.failure_taxonomy import failure_category
from schemas.run_record import RunRecord
from tools.spec_tools import ROOT
from tools.trace_tools import TraceWriter


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _plain(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


class RunArtifacts:
    def __init__(self, root, *, previous_run_id=None, relationship=None):
        now = datetime.now(timezone.utc)
        run_id = now.strftime("%Y%m%dT%H%M%S_%fZ_") + uuid4().hex[:8]
        self.path = Path(root).resolve() / run_id
        self.path.mkdir(parents=True, exist_ok=False)
        self.trace = []
        self.events = TraceWriter(self.path, previous_run_id=previous_run_id, relationship=relationship)
        def git(*args):
            try:
                return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
            except (OSError, subprocess.CalledProcessError):
                return None
        dirty = git("status", "--porcelain")
        try:
            mujoco_version = version("mujoco")
        except PackageNotFoundError:
            mujoco_version = None
        self.record = RunRecord(run_id=run_id, timestamp=now.isoformat(), git_commit=git("rev-parse", "HEAD"),
                                git_dirty=None if dirty is None else bool(dirty), python_version=platform.python_version(),
                                mujoco_version=mujoco_version)
        self.save("run.json", self.record)
        self.save("trace.json", self.trace)
        packages = {}
        for name in ("pydantic", "PyYAML", "numpy", "mujoco", "matlabengine"):
            try:
                packages[name] = version(name)
            except PackageNotFoundError:
                packages[name] = None
        self.save("runtime.json", {"platform": platform.platform(), "python": platform.python_version(), "packages": packages})

    def save(self, name, value):
        if self.events.closed and name != "run.json":
            raise ValueError("Run artifacts are sealed")
        target = self.path / name
        if Path(name).name != name or name in (".", ".."):
            raise ValueError("Artifact name must be a basename")
        value = _plain(value)
        text = yaml.safe_dump(value, sort_keys=False) if target.suffix == ".yaml" else json.dumps(value, indent=2, allow_nan=False, ensure_ascii=False)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(text + "\n", encoding="utf-8")
        temporary.replace(target)
        if name not in ("run.json", "trace.json"):
            self.events.emit("ARTIFACT_CREATED", "save_artifact", outputs={"artifact": name},
                             evidence_refs=self.events.refs(name))
        return target

    def update(self, **fields):
        self.record = RunRecord.model_validate({**self.record.model_dump(), **fields})
        self.save("run.json", self.record)

    def event(self, gate, status, **evidence):
        if self.events.closed:
            raise ValueError("Run trace is sealed")
        self.trace.append({"sequence": len(self.trace), "gate": gate, "status": status, **evidence})
        self.save("trace.json", self.trace)

    def invoke_tool(self, operation, name, call, *, input_paths=(), diagnostic=False):
        """Instrument the actual call; ToolResult stays in its own artifact."""
        with self.events.span(operation, kind="DIAGNOSTIC" if diagnostic else "TOOL", actor="tool",
                              inputs={"artifacts": list(input_paths)},
                              evidence_refs=self.events.refs(*input_paths)) as outcome:
            result = call()
            save_tool_result(self, name, result)
            summary = {k: v for k, v in result.metrics.items()
                       if v is None or type(v) in (bool, int, float) or (isinstance(v, str) and len(v) <= 256)}
            outcome.update(status="pass" if result.status == "pass" else "fail",
                           failure_code=result.failure_code, summary=dict(list(summary.items())[:24]),
                           outputs={"result": name}, evidence_refs=self.events.refs(name))
            return result


def create_run(root=ROOT / "runs", *, previous_run_id=None, relationship=None) -> RunArtifacts:
    if (previous_run_id is None) != (relationship is None) or relationship not in (None, "rerun", "repair"):
        raise ValueError("Run relationship requires previous_run_id and rerun/repair")
    if previous_run_id is not None:
        from tools.evidence import EvidenceStore
        EvidenceStore(root).run(previous_run_id)
    return RunArtifacts(root, previous_run_id=previous_run_id, relationship=relationship)


def save_tool_result(run: RunArtifacts, name: str, result):
    run.save(name, result)
    run.event(result.tool, result.status, artifact=name, failure_code=result.failure_code,
              failure_category=failure_category(result.failure_code))


def finalize_run(run: RunArtifacts, status, failure_code=None):
    run.events.close(status, failure_code)
    hashes = {p.name: file_hash(p) for p in sorted(run.path.iterdir()) if p.is_file() and p.name != "run.json"}
    run.update(final_status=status, failure_code=failure_code, failure_category=failure_category(failure_code), artifact_hashes=hashes)
    return run.record
