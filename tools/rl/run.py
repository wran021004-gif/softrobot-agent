"""Public RL functions and CLI, without agent runtime or model services."""
import argparse
import csv
from collections import deque
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
    if not resolved.get('candidate') or not resolved.get('control_object') or not resolved.get('task'):
        raise ValueError('Explicit candidate XML/assets, control_object and frozen task required; no historical fallback')
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


def training_summary(directory, state=None):
    """Read recorded facts only; no policy imports, simulator or cost aggregation."""
    directory = Path(directory)
    state = state if state is not None else read_json(directory / 'state.json')
    config = read_json(directory / 'config.json')
    sources = [directory / name for name in ('state.json', 'config.json')]
    checkpoint = None
    pointer = directory / 'checkpoint.json'
    if pointer.exists():
        sources.append(pointer)
        generation = read_json(pointer).get('current')
        if generation:
            if Path(generation).name != generation: raise ValueError('Invalid published generation')
            path = directory / 'checkpoints' / generation / 'metadata.json'
            sources.append(path)
            checkpoint = dict(generation=generation, policy_present=path.with_name('policy.zip').is_file(), **read_json(path))
    metrics = ['train/' + name for name in ('learning_rate', 'approx_kl', 'clip_fraction', 'entropy_loss',
               'policy_gradient_loss', 'value_loss', 'explained_variance')] + ['rollout/ep_rew_mean']
    workers = []
    records = {w['token']: w for w in state.get('workers', [])}
    tokens = list(records)
    if state.get('worker_token') and state['worker_token'] not in tokens: tokens.append(state['worker_token'])
    for token in tokens:
        path = directory / token / 'progress.csv'
        recent, first, latest, rows, incomplete = deque(maxlen=5), {}, {}, 0, 0
        if path.exists():
            sources.append(path)
            lines = path.read_text(encoding='utf-8').splitlines(keepends=True)
            if lines and not lines[-1].endswith('\n'):
                lines.pop(); incomplete += 1
            for row in csv.DictReader(lines, strict=True):
                if None in row or any(v is None for v in row.values()):
                    raise ValueError('Malformed progress.csv row: ' + str(path))
                step = float(row['time/total_timesteps'])
                if not math.isfinite(step): raise ValueError('Nonfinite logged step')
                values = {k: float(row[k]) for k in metrics if row.get(k) not in (None, '')}
                if any(not math.isfinite(v) for v in values.values()): raise ValueError('Nonfinite logged metric')
                record = dict(logged_step=step, metrics=values)
                for key, value in values.items():
                    first.setdefault(key, dict(logged_step=step, value=value))
                    latest[key] = dict(logged_step=step, value=value)
                rows += 1; recent.append(record)
        worker = records.get(token, {})
        workers.append(dict(token=token, current_worker=token == state.get('worker_token'),
            before_step=worker.get('before', {}).get('num_timesteps'),
            after_step=worker.get('after', {}).get('num_timesteps'), attempted_actions=worker.get('attempted_actions'),
            source=str(path.relative_to(directory)), available_rows=rows, incomplete_tail_rows=incomplete,
            first=first, latest=latest, recent=list(recent), not_recorded=[k for k in metrics if k not in latest]))
    failures = sorted((directory / 'failures').glob('**/failure_episode_*.json'), key=lambda p: p.stat().st_mtime)
    failure_index = []
    for path in failures[-5:]:
        sources.append(path)
        value = read_json(path)
        failure_index.append(dict(source=str(path.relative_to(directory)),
            **{k: value.get(k) for k in ('episode_number', 'cumulative_action', 'episode_action', 'failed_substep', 'warnings', 'pre_step_time_s')}))
    cost = state['consumed']
    failed, complete = cost.get('failed_episodes'), cost.get('complete_episodes')
    ended = None if failed is None or complete is None else failed + complete
    candidate = config.get('candidate', {})
    return dict(run_id=directory.name, candidate={k: candidate.get(k) for k in ('identity', 'reference', 'provenance')},
        task_identity=candidate.get('task_identity'), task=config.get('task'), scope='Recorded training evidence; task acceptance requires independent evaluation',
        mode=config['mode'], ppo=state.get('effective_ppo', config['ppo']), reward=config['reward'], allocation=config['budget'],
        status=state['status'], stop_reason=state.get('stop_reason'), error=state.get('error'),
        recorded_failure_stage=state.get('failure_stage'), last_known_stage=state.get('last_known_stage', state.get('failure_stage')),
        consumed=cost, reservation=state.get('reservation', {}), consumption_uncertain=state.get('consumption_uncertain', False),
        known_consumption_lower_bound=state.get('known_consumption_lower_bound'),
        episode_failure_fraction=dict(numerator=failed, denominator=ended, value=failed / ended if ended else None),
        checkpoint=checkpoint, workers=workers, failure_index=dict(recorded_files=len(failures), recent=failure_index),
        sources=[str(p.relative_to(directory)) for p in sources], observed_at_unix=time.time(),
        coverage='CSV may lag checkpoint optimizations; worker step ranges can overlap. Missing metrics are not recorded. '
                 'Physical steps are attempted, not verified completed substeps. Complete episodes are not task passes; '
                 'reward is training-only and cannot be compared across different weights. Historical stage labels are preserved.')


def status(run_id):
    directory = run_path(run_id)
    with locked(directory):
        state = reconcile(directory)
    config = read_json(directory / "config.json")
    result = dict(state, run_id=run_id, artifacts=str(directory), worker_alive=worker_alive(directory))
    result["remaining"] = {"actions": max(0, config["budget"]["actions"] - state["consumed"]["attempted_actions"]),
                           "active_seconds": max(0, config["budget"]["active_seconds"] - state["consumed"]["active_seconds"])}
    result['training_summary'] = training_summary(directory, state)
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


def merge_overrides(training=None, reward=None):
    """Single owner for public override validation and default resolution."""
    import copy
    defaults=read_json(Path(__file__).with_name('config.json'))
    training, reward = training or {}, reward or {}
    supported=set(defaults['ppo'])-{'device','verbose','use_sde','sde_sample_freq'}
    if set(training)-supported or set(reward)-set(defaults['reward']):
        raise ValueError('Unknown or unsupported PPO/reward override')
    result=copy.deepcopy(defaults)
    result['ppo'].update(training); result['reward'].update(reward)
    p=result['ppo']
    for key in ('n_steps','batch_size','n_epochs'):
        if type(p[key]) is not int or p[key]<1: raise ValueError('Positive integer PPO '+key+' required')
    if p['n_steps']<2 or p['batch_size']<2 or p['batch_size']>p['n_steps'] or p['n_steps']%p['batch_size']:
        raise ValueError('PPO minibatches must divide single-environment rollout')
    for key in ('gamma','gae_lambda'):
        if not isinstance(p[key],(int,float)) or not math.isfinite(p[key]) or not 0<=p[key]<=1:
            raise ValueError('PPO '+key+' must be in [0,1]')
    for key in ('learning_rate','clip_range','clip_range_vf','ent_coef','vf_coef','max_grad_norm','target_kl'):
        v=p[key]
        if v is None and key in ('clip_range_vf','target_kl'): continue
        if isinstance(v,dict) and key in ('learning_rate','clip_range','clip_range_vf'):
            if set(v)!={'kind','initial','final'} or v['kind']!='linear': raise ValueError('Invalid linear schedule')
            values=[v['initial'],v['final']]
        else: values=[v]
        if any(not isinstance(x,(float,int)) or not math.isfinite(x) or x<0 for x in values):
            raise ValueError('Invalid PPO '+key)
    if type(p['normalize_advantage']) is not bool: raise ValueError('normalize_advantage must be boolean')
    kwargs=p['policy_kwargs']
    if set(kwargs)-{'net_arch','log_std_init'}: raise ValueError('Unsupported policy_kwargs')
    arch=kwargs.get('net_arch',{})
    if set(arch)!={'pi','vf'} or any(not isinstance(v,list) or not v or any(type(n)is not int or not 1<=n<=256 for n in v) for v in arch.values()):
        raise ValueError('policy net_arch requires bounded pi/vf layer widths')
    if not math.isfinite(kwargs.get('log_std_init',0)): raise ValueError('Invalid log_std_init')
    for key,v in result['reward'].items():
        if not isinstance(v,(int,float)) or not math.isfinite(v) or (v>0 if key=='failure_penalty' else v<0):
            raise ValueError('Invalid reward weight '+key)
    result['requested_overrides']=dict(training=training,reward=reward)
    return result


def start(config=None, run_id=None, interpreter=PYTHON):
    resolved = resolve_config(config)
    directory = run_path(run_id or uuid.uuid4().hex)
    if directory.exists(): raise FileExistsError('Run already exists; use recorded receipt/status')
    from tools.rl.env import TensionEnv
    env=TensionEnv(resolved)
    env.close()  # Compile and validate; zero physical steps, before worker launch.
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
        directory=run_path(args.run_id)
        state=read_json(directory/'state.json');state['failure_stage']='launch/dependency import';write_json(directory/'state.json',state)
        from tools.rl.train import worker
        worker(directory, args.token, started)
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
