"""Exactly one missing resolution, with the repaired guard; no backend steps."""
import time
from tools.platform_registry import Extension
from .diagnostic_evidence import DiagnosticEvidence
from .diagnostic_math import NonlinearModel, charge_units
from .milestone5_preview import PreviewRequest
from .milestone5_first_interval import integrate, stable, differences

STEP = .00000390625
GUARD_S = 800.
RESERVATION_S = 1200.


def execute(ctx, args):
    p = ctx.artifact(args.protocol)
    spec = p['specification']
    results = list(p['completed_results'])
    if len(results) != 8 or results[-1]['step_s'] != 2*STEP:
        raise ValueError('EXACT_EIGHT_PREDECESSOR_RESOLUTIONS_REQUIRED')
    if any(spec['state']) or spec['interval_s'] != [0., .01]:
        raise ValueError('ORIGINAL_SHARED_INTERVAL_REQUIRED')
    charge_units(ctx, 'reference_integrations', 1)
    start = time.perf_counter()
    model = NonlinearModel(spec['configuration'], spec['state'], spec['input_n'], STEP)
    end = integrate(model, spec['state'], spec['input_n'], time.perf_counter()+GUARD_S,
                    max_substeps=2560)
    end['complete_cost_s'] = time.perf_counter()-start
    ctx.save_artifact(dict(specification_identity=spec['identity'], result=end),
                      'reference_continuation_completed')
    results.append(end)
    finite_residual = all(r['root_status']=='finite_root_residual_verified' and
                          r['max_scaled_residual'] <= 1e-5 for r in results)
    return DiagnosticEvidence(detail=dict(results=results, specification_identity=spec['identity'],
        numerical_stability_supported=finite_residual and stable(results),
        continuous_differences=differences(results), reused_integrations=8, new_integrations=1,
        integration_guard_s=GUARD_S, outer_reservation_s=RESERVATION_S,
        scope='Original zero-state held-input .00-.01 s, continuous output only; serial mapping assessed separately',
        backend_steps=0, controller_attempts=0))


def preflight(inp, args, reg):
    return dict(cost=dict(wall_s=RESERVATION_S))


DEFINITION = Extension('analysis.milestone5_campaign_reference', 'tool', '1.0.0',
    PreviewRequest, DiagnosticEvidence,
    'extensions.tendon_family.milestone5_campaign_reference:execute',
    'One authorized missing 2560-substep original reference integration.',
    sources=('extensions/tendon_family/milestone5_campaign_reference.py',
             'extensions/tendon_family/milestone5_first_interval.py',
             'extensions/tendon_family/diagnostic_math.py'), side_effects='artifact_store',
    capabilities=dict(preflight='extensions.tendon_family.milestone5_campaign_reference:preflight'))
