"""Public RL functions and CLI, without agent runtime or model services."""
import argparse
from contextlib import contextmanager
import ctypes
import json
import math
import os
from pathlib import Path
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs/rl"
PYTHON = Path(r"D:\softrobot-agent\.rl-pilot-env\Scripts\python.exe")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    pending = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with pending.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(pending, path)


def process_birth(pid):
    """Creation time distinguishes the launched worker from a reused PID."""
    if os.name == "nt":
        from ctypes import wintypes
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.OpenProcess.restype = wintypes.HANDLE
        api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        api.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        api.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = api.OpenProcess(0x1000, False, pid)
        if not handle:
            return None
        try:
            times = [wintypes.FILETIME() for _ in range(4)]
            if not api.GetProcessTimes(handle, *(ctypes.byref(t) for t in times)):
                return None
            if times[1].dwLowDateTime or times[1].dwHighDateTime:
                return None
            return (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
        finally:
            api.CloseHandle(handle)
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().split(") ", 1)[1].split()
        return None if fields[0] == "Z" else fields[19]
    except (FileNotFoundError, ProcessLookupError):
        return None


def worker_alive(directory):
    if not (directory / "launch.json").exists():
        return False
    identity = read_json(directory / "launch.json")
    state = read_json(directory / "state.json")
    return (identity["token"] == state["worker_token"] and identity["birth"] is not None
            and process_birth(identity["pid"]) == identity["birth"])


@contextmanager
def locked(directory):
    path = directory / "lifecycle.lock"
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise RuntimeError("Another lifecycle operation holds this run's lock") from None
    try:
        os.close(fd)
        yield
    finally:
        path.unlink()


def run_path(run_id):
    if not run_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in run_id):
        raise ValueError("run_id must contain only letters, digits, underscores and hyphens")
    return RUNS / run_id


def resolve_config(config=None):
    import copy
    resolved = copy.deepcopy(config) if isinstance(config, dict) else read_json(config or Path(__file__).with_name("config.json"))
    if resolved["mode"] not in ("direct", "residual"):
        raise ValueError("Only direct and residual tension control are supported")
    budget = resolved["budget"]
    if (type(budget["actions"]) is not int or budget["actions"] <= 0
            or not math.isfinite(budget["active_seconds"]) or budget["active_seconds"] <= 0):
        raise ValueError("Budget must be positive, finite; actions must be an integer")
    boundary = resolved.get("stop_at_boundary")
    if boundary is not None and (not 0 < boundary < budget["actions"] or boundary % resolved["ppo"]["n_steps"]):
        raise ValueError("stop_at_boundary must be an interior rollout boundary")
    if resolved["mode"] == "residual" and not resolved.get("reference"):
        raise ValueError("Residual requires a complete compatible tension reference")
    if resolved["mode"] == "direct" and resolved.get("reference") is not None:
        raise ValueError("Direct mode uses no reference")
    if resolved["mode"] == "residual":
        import hashlib
        reference = resolved["reference"]
        path = Path(reference["path"])
        path = path if path.is_absolute() else ROOT / path
        current = hashlib.sha256(path.read_bytes()).hexdigest()
        if reference.get("sha256", current) != current:
            raise ValueError("Reference digest mismatch")
        reference["sha256"] = current
        reference["path"] = str(path.resolve())
    return resolved


def reconcile(directory):
    state = read_json(directory / "state.json")
    if state["status"] in ("starting", "running", "stopping") and not worker_alive(directory):
        reservation = state.get("reservation", {})
        state["known_consumption_lower_bound"] = state["consumed"].copy()
        for key, amount in reservation.items():
            state["consumed"][key] = state["consumed"].get(key, 0) + amount
        state["reservation"] = {}
        state["consumption_uncertain"] = bool(reservation) or state.get("consumption_uncertain", False)
        state.update(status="interrupted", stop_reason="worker_missing; outstanding reservation conservatively charged")
        write_json(directory / "state.json", state)
    return state


def status(run_id):
    directory = run_path(run_id)
    with locked(directory):
        state = reconcile(directory)
    config = read_json(directory / "config.json")
    result = dict(state, run_id=run_id, artifacts=str(directory), worker_alive=worker_alive(directory))
    result["remaining"] = {"actions": max(0, config["budget"]["actions"] - state["consumed"]["attempted_actions"]),
                           "active_seconds": max(0, config["budget"]["active_seconds"] - state["consumed"]["active_seconds"])}
    return result


def launch(directory, state, interpreter):
    token = uuid.uuid4().hex
    state.update(status="starting", worker_token=token, reservation={
        "active_seconds": max(0, read_json(directory / "config.json")["budget"]["active_seconds"] - state["consumed"]["active_seconds"])})
    write_json(directory / "state.json", state)
    (directory / "stop.json").unlink(missing_ok=True)
    # Read only OS paths needed by Python/DLL loading. No credential or model
    # service environment variables are inspected or forwarded explicitly.
    env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "PATH", "TEMP", "TMP", "USERPROFILE",
           "APPDATA", "LOCALAPPDATA", "COMSPEC", "PATHEXT") if key in os.environ}
    env.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    process = None
    try:
        with (directory / "worker.log").open("a", encoding="utf-8") as log:
            process = subprocess.Popen([str(interpreter), "-m", "tools.rl.run", "_worker", "--run-id", directory.name, "--token", token],
                                       cwd=ROOT, env=env, stdout=log, stderr=log,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        write_json(directory / "launch.json", dict(pid=process.pid, birth=process_birth(process.pid), token=token))
    except BaseException:
        if process is None:
            state.update(status="failed", stop_reason="worker_launch_failed", reservation={})
        else:
            # Identity publication failed after process creation. Reap this
            # exact process and retain/charge its unknown setup consumption.
            process.terminate()
            process.wait()
            state["known_consumption_lower_bound"] = state["consumed"].copy()
            for key, amount in state["reservation"].items():
                state["consumed"][key] = state["consumed"].get(key, 0) + amount
            state.update(status="interrupted", stop_reason="worker_launch_identity_failed; reservation charged",
                         reservation={}, consumption_uncertain=True)
        write_json(directory / "state.json", state)
        raise
    return dict(run_id=directory.name, status="starting", pid=process.pid, artifacts=str(directory))


def start(config=None, run_id=None, interpreter=PYTHON):
    resolved = resolve_config(config)
    directory = run_path(run_id or uuid.uuid4().hex)
    directory.mkdir(parents=True, exist_ok=False)
    write_json(directory / "config.json", resolved)
    state = dict(status="stopped", worker_token=None, consumed=dict(attempted_actions=0, completed_actions=0,
                 attempted_physics_steps=0, complete_episodes=0, failed_episodes=0, active_seconds=0.0),
                 reservation={}, consumption_uncertain=False, checkpoints={"current": None, "previous": None}, workers=[])
    with locked(directory):
        return launch(directory, state, interpreter)


def stop(run_id):
    directory = run_path(run_id)
    state = status(run_id)
    if not state["worker_alive"]:
        raise RuntimeError("No live worker to stop")
    write_json(directory / "stop.json", dict(token=state["worker_token"], reason="user_stop"))
    return dict(run_id=run_id, status="stopping", stop_request=str(directory / "stop.json"))


def resume(run_id, interpreter=PYTHON):
    directory = run_path(run_id)
    with locked(directory):
        state = reconcile(directory)
        if worker_alive(directory):
            raise RuntimeError("Duplicate worker rejected: previous worker has not exited")
        config = read_json(directory / "config.json")
        if (state["consumed"]["attempted_actions"] >= config["budget"]["actions"]
                or state["consumed"]["active_seconds"] >= config["budget"]["active_seconds"]):
            raise RuntimeError("Original shared campaign budget exhausted; verification may be incomplete" +
                               ("; unflushed consumption remains uncertain" if state["consumption_uncertain"] else ""))
        from tools.rl.train import valid_checkpoint
        valid_checkpoint(directory, config)
        return launch(directory, state, interpreter)


def evaluate(policy, output, source_root=None):
    from tools.rl.checks import evaluate as check
    return check(Path(policy), Path(output), source_root)


def diagnose(capture, output=None, replay=False, config=None):
    from tools.rl.checks import diagnose as check
    return check(Path(capture), Path(output) if output else None, replay, config)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["start", "status", "stop", "resume", "evaluate", "diagnose", "_worker"])
    parser.add_argument("--run-id")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--token")
    args = parser.parse_args()
    if args.command == "_worker":
        started = time.perf_counter()  # includes heavy module imports
        from tools.rl.train import worker
        worker(run_path(args.run_id), args.token, started)
        return
    if args.command == "start":
        result = start(args.config, args.run_id)
    elif args.command in ("status", "stop", "resume"):
        result = globals()[args.command](args.run_id)
    elif args.command == "evaluate":
        result = evaluate(args.policy, args.output, args.source_root)
    else:
        result = diagnose(args.capture, args.output, args.replay, args.config)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
