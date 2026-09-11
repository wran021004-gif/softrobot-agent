"""Portable run-relative evidence references, never authority or executable paths."""
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated
from pydantic import Field, field_validator
from schemas.common import Contract

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$")]


def safe_relative_path(value: str) -> str:
    parts = value.split("/")
    if (not value or "\\" in value or PurePosixPath(value).is_absolute()
            or any(p in ("", ".", "..") or p.endswith((".", " "))
                   or ":" in p or "\x00" in p or PureWindowsPath(p).is_reserved() for p in parts)):
        raise ValueError("Expected a portable relative artifact path")
    return value


class ArtifactReference(Contract):
    run_id: Identifier
    path: str = Field(max_length=512)
    sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    pointer: str | None = Field(default=None, pattern=r"^/", max_length=512)

    _path = field_validator("path")(safe_relative_path)
