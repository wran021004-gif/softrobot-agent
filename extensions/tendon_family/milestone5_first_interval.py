"""One shared historical first interval; no backend advancement or controller solve."""
import time
import numpy as np
from tools.platform_registry import Extension
from .diagnostic_evidence import DiagnosticEvidence
from .diagnostic_math import NonlinearModel,charge_units
from .milestone5_preview import PreviewRequest
from .milestone5_recovery import motion,norm

STEPS=(.01,.0005,.00025,.000125,.0000625,.00003125)
TOLERANCE=1e-4


def integrate(model,state,input_n,deadline):
    """Diagnostic-only cap: <=320 substeps on this declared .01 s interval."""
    count=round(.01/model.step_s)
    if not 1<=count<=320 or abs(count*model.step_s-.01)>1e-12:raise ValueError('FIRST_INTERVAL_GRID')
    x=np.asarray(state).copy();maximum=0.;start=time.perf_counter()
    for _ in range(count):
        if time.perf_counter()>deadline:raise RuntimeError('FIRST_INTERVAL_DEADLINE')
        following=np.asarray(model.step(x/model.scales,x,input_n)).ravel()*model.scales
        residual=float(np.max(abs(np.asarray(model.residual(x,following,input_n)))))
        if not np.isfinite(following).all() or residual>1e-5:raise ValueError('FIRST_INTERVAL_RESIDUAL')
        maximum=max(maximum,residual);x=following
    return dict(state=x.tolist(),**motion(model,x),step_s=model.step_s,step_count=count,
        max_scaled_residual=maximum,root_status='finite_root_residual_verified',integration_s=time.perf_counter()-start)


def differences(results):
    return [dict(coarse_step_s=a['step_s'],fine_step_s=b['step_s'],
        position_m=norm(a['position_m'],b['position_m']),velocity_m_s=norm(a['velocity_m_s'],b['velocity_m_s']),
        speed_m_s=abs(a['speed_m_s']-b['speed_m_s'])) for a,b in zip(results,results[1:])]


def stable(results):
    # The production .01 step is a reproduction baseline, not part of the fine-reference test.
    fine=[r for r in results if r['step_s']<.01];d=differences(fine)
    return len(d)>=2 and all(x['velocity_m_s']<=TOLERANCE and x['speed_m_s']<=TOLERANCE for x in d[-2:])


def output_accounting(predicted,projected,backend):
    result={}
    for key in ('position_m','velocity_m_s'):
        a=np.asarray(predicted[key])-projected[key];b=np.asarray(projected[key])-backend[key];total=np.asarray(predicted[key])-backend[key]
        result[key]=dict(evolution=a.tolist(),projection_output=b.tolist(),total=total.tolist(),evolution_norm=float(np.linalg.norm(a)),
            projection_output_norm=float(np.linalg.norm(b)),total_norm=float(np.linalg.norm(total)),identity_residual=float(np.max(abs(total-a-b))))
    return result


def execute(ctx,args):
    spec=ctx.artifact(args.protocol);results=[];model=None
    # Reuse exact saved subresults after an interrupted outer call; no calculation is repeated.
    completed=spec.get('completed_results',[])
    for step in STEPS:
        if len(results)>=4 and stable(results):break
        prior=[r for r in completed if r['step_s']==step]
        if prior:
            if len(prior)!=1:raise ValueError('DUPLICATE_FIRST_INTERVAL_RESULT')
            result=prior[0]
        else:
            charge_units(ctx,'prediction_evaluations',1);start=time.perf_counter()
            model=NonlinearModel(spec['configuration'],spec['state'],spec['input_n'],step)
            result=integrate(model,spec['state'],spec['input_n'],time.perf_counter()+180.)
            result.update(complete_cost_s=time.perf_counter()-start,
                position_error_norm_m=norm(result['position_m'],spec['observed']['position_m']),
                velocity_error_norm_m_s=norm(result['velocity_m_s'],spec['observed']['velocity_m_s']),
                speed_error_m_s=result['speed_m_s']-spec['observed']['speed_m_s'])
            ctx.save_artifact(dict(specification_identity=spec['identity'],result=result),'first_interval_resolution_completed')
        results.append(result)
        if step==.01:
            saved=spec['saved_coarse'];reproduction=dict(state_max=float(np.max(abs(np.asarray(result['state'])-saved['state']))),
                position_m=norm(result['position_m'],saved['position_m']),velocity_m_s=norm(result['velocity_m_s'],saved['velocity_m_s']))
            if reproduction['state_max']>1e-7 or reproduction['velocity_m_s']>1e-8 or reproduction['position_m']>1e-9:
                raise ValueError('COARSE_REPRODUCTION_MISMATCH_STOP')
    # If every result was recovered, building the output map does not propagate state or charge an integration.
    if model is None:model=NonlinearModel(spec['configuration'],spec['state'],spec['input_n'],results[-1]['step_s'])
    initial_projected=motion(model,spec['state']);endpoint_projected=motion(model,spec['observed_projected_state'])
    initial_accounting=output_accounting(initial_projected,initial_projected,spec['initial_backend_motion'])
    endpoint_accounting=[dict(step_s=r['step_s'],accounting=output_accounting(r,endpoint_projected,spec['observed'])) for r in results]
    coarse,fine=results[0],results[-1];change=coarse['velocity_error_norm_m_s']-fine['velocity_error_norm_m_s']
    report=dict(specification_identity=spec['identity'],shared_with=spec['cases'],results=results,coarse_reproduction=reproduction,
        numerical_stability_supported=stable(results),fine_differences=differences(results[1:]),reporting_tolerance_m_s=TOLERANCE,
        measured_uncertainty=differences(results)[-1],initial_projected_output=initial_projected,observed_projected_output=endpoint_projected,
        initial_accounting=initial_accounting,endpoint_accounting=endpoint_accounting,
        vector_error_change=dict(coarse_error_m_s=coarse['velocity_error_norm_m_s'],finest_tested_error_m_s=fine['velocity_error_norm_m_s'],
            absolute_reduction_m_s=change,relative_reduction=change/coarse['velocity_error_norm_m_s'],
            finest_status='locally supported successive-resolution reference' if stable(results) else 'finest tested only; numerical stability unresolved'),
        integration_attempts=len(results),backend_advances=0,controller_attempts=0,complete_previews=0,
        limits='Output accounting is exact but not a unique causal attribution. Evolution term includes reduced state representation and unresolved numerical effects; instantaneous output term does not identify a projection bug. First-interval retrospective evidence does not validate full-history screening.')
    return DiagnosticEvidence(detail=report)


def preflight(inp,args,reg):return dict(cost=dict(wall_s=500.))


DEFINITION=Extension('analysis.milestone5_first_interval','tool','1.0.0',PreviewRequest,DiagnosticEvidence,
    'extensions.tendon_family.milestone5_first_interval:execute','Single shared historical first-interval resolution and output accounting.',
    sources=('extensions/tendon_family/milestone5_first_interval.py',),side_effects='artifact_store',
    capabilities=dict(preflight='extensions.tendon_family.milestone5_first_interval:preflight'))
