"""Bounded offline predictor development; no backend stepping or control mutation."""
import time
import numpy as np
from tools.platform_registry import Extension
from .diagnostic_evidence import DiagnosticEvidence
from .diagnostic_math import NonlinearModel, charge_units
from .milestone5_preview import PreviewRequest
from .milestone5_first_interval import integrate, stable, differences, output_accounting
from .milestone5_recovery import norm

CONTINUATION_STEPS=(.000015625,.0000078125,.00000390625)
PREDICTOR_VERSION='represented_serial_output@1.0.0'


def reference(ctx,p):
    spec=p['specification'];results=list(p['completed_results']);new=[]
    for step in CONTINUATION_STEPS:
        if stable(results):break
        charge_units(ctx,'reference_integrations',1);start=time.perf_counter()
        model=NonlinearModel(spec['configuration'],spec['state'],spec['input_n'],step)
        end=integrate(model,spec['state'],spec['input_n'],time.perf_counter()+800.,max_substeps=2560)
        end.update(complete_cost_s=time.perf_counter()-start,
            position_error_norm_m=norm(end['position_m'],spec['observed']['position_m']),
            velocity_error_norm_m_s=norm(end['velocity_m_s'],spec['observed']['velocity_m_s']),
            speed_error_m_s=end['speed_m_s']-spec['observed']['speed_m_s'])
        ctx.save_artifact(dict(specification_identity=spec['identity'],result=end),'reference_continuation_completed')
        results.append(end);new.append(end)
    return dict(specification_identity=spec['identity'],shared_identity=spec['shared_identity'],results=results,
        new_integrations=len(new),reused_integrations=len(p['completed_results']),fine_differences=differences(results[1:]),
        numerical_stability_supported=stable(results),residual_limit=1e-5,
        measured_uncertainty=differences(results)[-1],reference_scope='Shared original .00-.01 s ONLY; two successive differences, not a proven error bound',
        endpoint_accounting=output_accounting(results[-1],p['projected_observed_output'],spec['observed']),
        backend_steps=0,controller_attempts=0)


def execute(ctx,args):
    p=ctx.artifact(args.protocol)
    if p['operation']=='reference':result=reference(ctx,p)
    else:
        from examples.milestone5_predictor_development import analyze
        result=analyze(ctx,p)
    return DiagnosticEvidence(detail=result)


def preflight(inp,args,reg):
    return dict(cost=dict(wall_s=1200.))


DEFINITION=Extension('analysis.milestone5_predictor','tool','1.0.1',PreviewRequest,DiagnosticEvidence,
    'extensions.tendon_family.milestone5_predictor:execute','Bounded reference continuation and predictor-only output development.',
    sources=('extensions/tendon_family/milestone5_predictor.py','examples/milestone5_predictor_development.py',
        'extensions/tendon_family/milestone5_serial_output.py','extensions/tendon_family/milestone5_first_interval.py',
        'extensions/tendon_family/diagnostic_math.py','extensions/tendon_family/gvs_projection.py'),side_effects='artifact_store',
    capabilities=dict(preflight='extensions.tendon_family.milestone5_predictor:preflight'))
