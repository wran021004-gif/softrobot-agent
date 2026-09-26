"""Cheap saved-matrix reproduction; no model build, backend or optimizer run."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import scipy
from extensions.tendon_family.contracts import LQRParameters
from extensions.tendon_family.gvs_sampled import DiscreteLQRController, zero_order_hold
from schemas.platform_math import LinearizedModel
from tools.state_io import atomic_json

HERE = Path(__file__).resolve().parent


def main(output):
    history = ROOT / 'runs/stage36_controller_attribution_20260924/controller_failure_attribution.json'
    saved = json.loads(history.read_text(encoding='utf8'))['chain']
    archive = json.loads((HERE / 'sampled_linear.json').read_text(encoding='utf8'))
    definitions = archive['discrete']
    linear = LinearizedModel(
        state_definition=definitions['state_definition'], input_definition=definitions['input_definition'],
        output_definition=definitions['output_definition'], x0=saved['x0'], u0=saved['u0'],
        A=saved['A'], B=saved['B'], time_domain='continuous')
    # This reproduces the homogeneous perturbation calculation. It does not
    # assert zero nonlinear drift or replace the public operating-point check.
    sampled = zero_order_hold(linear, archive['period_s'])
    controller = DiscreteLQRController(LQRParameters(
        Q=np.diag(saved['Q_diagonal']).tolist(), R=np.diag(saved['R_diagonal']).tolist(),
        tendon_order=saved['tendon_order'], force_limits_n=saved['force_limits_n']))
    Kd = controller.configure_model(sampled)
    A, B, K = map(np.asarray, (saved['A'], saved['B'], saved['K']))
    Ad, Bd = map(np.asarray, (sampled.A, sampled.B))
    measured = dict(
        continuous_max_real_eigenvalue=float(max(np.linalg.eigvals(A - B @ K).real)),
        historical_held_spectral_radius=float(max(abs(np.linalg.eigvals(Ad - Bd @ K)))),
        sampled_spectral_radius=controller.spectral_radius)
    np.testing.assert_allclose(list(measured.values()), [archive[k] for k in measured], rtol=1e-9)
    np.testing.assert_allclose(Kd, archive['K'], rtol=1e-8, atol=1e-10)
    result = dict(**measured, period_s=archive['period_s'], physics_step_s=archive['physics_step_s'],
        interpreter=sys.executable, python=sys.version, numpy=np.__version__, scipy=scipy.__version__,
        source=str(history.relative_to(ROOT)), saved_gain_max_difference=float(np.max(abs(Kd - archive['K']))),
        scope='Saved pure unsaturated linear feedback. No new nonlinear equilibrium or backend claim.',
        command='python runs/stage312_to_nmpc_20260926/verify_saved.py')
    if output:
        atomic_json(output, result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Optional new JSON evidence file; otherwise read-only.')
    main(parser.parse_args().output)
