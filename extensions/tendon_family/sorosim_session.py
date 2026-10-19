"""Experiment-owned MATLAB Engine; no desktop attachment or per-update launch."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

UPSTREAM = '24d573a3e864ffda87c42ee462a6ed620133cc7b'
ROOT = Path(__file__).resolve().parents[2]


def dependency_identity(root):
    root = Path(root).resolve()
    sha = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    if sha != UPSTREAM:
        raise ValueError('SOROSIM_PIN_MISMATCH: ' + sha)
    if subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain'], text=True).strip():
        raise ValueError('SOROSIM_DIRTY_DEPENDENCY')
    base = root / 'Differentiable_SoRoSim'
    # Record every eligible upstream source/binary, including indirectly called MEX.
    files = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(base.rglob('*')) if p.suffix in ('.m', '.mexw64')}
    if not files:
        raise ValueError('SOROSIM_SOURCE_MISSING')
    return dict(repository='GVSRobotics/SoRoSim', commit=sha, files=files)


class SorosimSession:
    def __init__(self, root=None, options='-nodesktop -nosplash'):
        self.root = root or os.environ.get('SOROSIM_ROOT')
        if not self.root:
            raise ValueError('SOROSIM_ROOT_REQUIRED')
        self.options = options
        self.engine = None
        self.model_identity = None
        self.startup_stage = 'not_started'
        self.timings = dict(startup_s=0., shutdown_s=0., calls=[])

    def __enter__(self):
        self.startup_stage = 'dependency'
        self.dependency = dependency_identity(self.root)
        import matlab.engine
        started = time.perf_counter()
        self.startup_stage = 'engine_start'
        self.engine = matlab.engine.start_matlab(self.options)
        self.timings['startup_s'] = time.perf_counter() - started
        try:
            self.startup_stage = 'gateway'
            self.engine.addpath(str(ROOT / 'matlab/sorosim_control'), nargout=0)
            self.environment = self.call('environment', dict(root=str(Path(self.root).resolve())))
            self.startup_stage = 'ready'
        except BaseException:
            self.close()
            raise
        return self

    def call(self, operation, payload=None):
        if self.engine is None:
            raise RuntimeError('MATLAB_SESSION_CLOSED')
        started = time.perf_counter()
        encoded = json.dumps(payload or {}, allow_nan=False)
        try:
            result = json.loads(self.engine.sr_gateway(operation, encoded, nargout=1))
        except Exception:
            self.timings['calls'].append(dict(operation=operation,wall_s=time.perf_counter()-started,
                matlab_s=None,transfer_and_dispatch_s=None,status='error'))
            raise
        elapsed = time.perf_counter() - started
        self.timings['calls'].append(dict(operation=operation, wall_s=elapsed,
            matlab_s=result.get('gateway_s'), transfer_and_dispatch_s=max(0., elapsed-result.get('gateway_s', 0.))))
        if 'error' in result:
            raise RuntimeError(result['error'])
        return result

    def construct(self, specification):
        if self.model_identity is not None:
            raise ValueError('ONE_CANDIDATE_PER_MATLAB_SESSION')
        result = self.call('construct', specification)
        self.model_identity = specification['identity']
        return result

    def evaluate(self, operation, payload):
        return self.call(operation, dict(payload, model_identity=self.model_identity))

    def close(self):
        engine, self.engine = self.engine, None
        self.model_identity = None
        if engine is not None:
            started = time.perf_counter()
            engine.quit()
            self.timings['shutdown_s'] = time.perf_counter() - started

    def __exit__(self, *exc):
        self.close()
