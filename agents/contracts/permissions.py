"""Deny-by-default policy for a future executor, not an OS security boundary."""
from pathlib import Path, PureWindowsPath
from tools.spec_tools import ROOT

HUMAN_OWNED = ("tasks", "benchmarks", "physics_contracts", "schemas", "capabilities", "metrics", "agents/contracts", "configs", "mujoco/environments")
WRITE_SCOPES = {
    "engineer": ("proposals/engineer",),
    "coding": ("tools", "controllers", "tests", "examples", "matlab", "proposals/coding"),
    "diagnosis": ("proposals/diagnosis",),
}


def can_write(role: str, path: str | Path, root=ROOT) -> bool:
    root = Path(root).resolve()
    raw = str(path).replace("\\", "/")
    windows = PureWindowsPath(raw)
    # Reject traversal even when it would normalize back into an allowed scope.
    # ADS, device paths, drive-relative paths and Win32 trailing-dot aliases are
    # ambiguous write targets and are never accepted by this application contract.
    if (not raw or "\x00" in raw or ".." in raw.split("/")
            or raw.startswith("//") or (windows.drive and not windows.is_absolute())
            or any(p.endswith((".", " ")) or ":" in p
                   or PureWindowsPath(p).is_reserved()
                   for p in raw.split("/") if p and p != windows.drive)):
        return False
    if windows.drive and not Path(raw).is_absolute():
        return False
    path = Path(raw)
    try:
        candidate = (path if path.is_absolute() else root / path).resolve()
    except (OSError, ValueError, RuntimeError):
        return False
    try:
        relative = candidate.relative_to(root).as_posix().casefold()
    except ValueError:
        return False
    def within(scope):
        return relative == scope or relative.startswith(scope + "/")
    if role == "human":
        return True
    if any(within(scope) for scope in HUMAN_OWNED):
        return False
    return any(within(scope) for scope in WRITE_SCOPES.get(role, ()))


def require_write_permission(role, path, root=ROOT):
    if not can_write(role, path, root):
        raise PermissionError(f"{role} cannot modify {path}; submit a proposal for Human review")
