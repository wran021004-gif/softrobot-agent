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


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _plain(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


class RunArtifacts:
    def __init__(self, root):
        now = datetime.now(timezone.utc)
        run_id = now.strftime("%Y%m%dT%H%M%S_%fZ_") + uuid4().hex[:8]
        self.path = Path(root).resolve() / run_id
        self.path.mkdir(parents=True, exist_ok=False)
        self.trace = []
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
        target = self.path / name
        if Path(name).name != name or name in (".", ".."):
            raise ValueError("Artifact name must be a basename")
        value = _plain(value)
        text = yaml.safe_dump(value, sort_keys=False) if target.suffix == ".yaml" else json.dumps(value, indent=2, allow_nan=False, ensure_ascii=False)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(text + "\n", encoding="utf-8")
        temporary.replace(target)
        return target

    def update(self, **fields):
        self.record = RunRecord.model_validate({**self.record.model_dump(), **fields})
        self.save("run.json", self.record)

    def event(self, gate, status, **evidence):
        self.trace.append({"sequence": len(self.trace), "gate": gate, "status": status, **evidence})
        self.save("trace.json", self.trace)


def create_run(root=ROOT / "runs") -> RunArtifacts:
    return RunArtifacts(root)


def save_tool_result(run: RunArtifacts, name: str, result):
    run.save(name, result)
    run.event(result.tool, result.status, artifact=name, failure_code=result.failure_code,
              failure_category=failure_category(result.failure_code))


def finalize_run(run: RunArtifacts, status, failure_code=None):
    hashes = {p.name: file_hash(p) for p in sorted(run.path.iterdir()) if p.is_file() and p.name != "run.json"}
    run.update(final_status=status, failure_code=failure_code, failure_category=failure_category(failure_code), artifact_hashes=hashes)
    return run.record
