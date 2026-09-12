"""Resolve provenance against finalized run manifests; no historical database."""
import hashlib
import json
from pathlib import Path
import yaml
from pydantic import TypeAdapter
from schemas.evidence import ArtifactReference, Identifier
from schemas.run_record import RunRecord


class EvidenceStore:
    """One validation-session cache avoids repeatedly hashing large artifacts."""
    def __init__(self, run_root):
        self.root = Path(run_root).resolve()
        self._runs, self._files = {}, {}

    def run(self, run_id):
        TypeAdapter(Identifier).validate_python(run_id)
        if run_id not in self._runs:
            folder = (self.root / run_id).resolve()
            if not folder.is_relative_to(self.root):
                raise ValueError("Run escapes evidence root")
            try:
                record = RunRecord.model_validate_json((folder / "run.json").read_text(encoding="utf-8"))
            except OSError as exc:
                raise ValueError(f"Nonexistent run: {run_id}") from exc
            if record.run_id != run_id or record.final_status == "RUNNING":
                raise ValueError("Evidence requires a matching finalized run")
            self._runs[run_id] = record
        return self._runs[run_id]

    def resolve(self, reference, *, require_hash=True):
        ref = ArtifactReference.model_validate(reference)
        if ref.path.casefold().startswith("debug/"):
            raise ValueError("DEBUG_ONLY / NON_CANONICAL artifacts cannot enter evidence admission")
        record = self.run(ref.run_id)
        expected = record.artifact_hashes.get(ref.path)
        if not expected or (require_hash and ref.sha256 is None) or (ref.sha256 and ref.sha256 != expected):
            raise ValueError("Evidence hash missing or different from manifest")
        key = (ref.run_id, ref.path)
        if key not in self._files:
            folder = (self.root / ref.run_id).resolve()
            path = (folder / ref.path).resolve()
            if not path.is_relative_to(folder) or not path.is_file():
                raise ValueError("Missing or escaping evidence artifact")
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError("Evidence artifact hash mismatch")
            self._files[key] = data
        data = self._files[key]
        if ref.pointer is None:
            return data
        try:
            value = yaml.safe_load(data) if ref.path.endswith((".yaml", ".yml")) else json.loads(data)
            for part in ref.pointer[1:].split("/"):
                part = part.replace("~1", "/").replace("~0", "~")
                value = value[int(part)] if isinstance(value, list) and part.isdecimal() else value[part]
            return value
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ValueError(f"Nonexistent evidence metric/pointer: {ref.pointer}") from exc

    def reference(self, run_id, path, pointer=None):
        record = self.run(run_id)
        ref = ArtifactReference(run_id=run_id, path=path, sha256=record.artifact_hashes.get(path), pointer=pointer)
        self.resolve(ref)
        return ref
