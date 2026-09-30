"""Thin public tools: trusted implementation selection and common results."""
import importlib.util
import numpy as np
from schemas.platform_analysis import (AnalysisProtocol, TaskAnalysisProtocol, OutputLinearizedModel,
    EndpointLinearizedModel, EndpointTarget, AnalysisResult)
from tools.state_io import digest
from tools.platform_store import plain
from .kernels import normalized, raw_scipy, summarize, versions, bounded_endpoint, LIMITATIONS


def preflight(inp,args,reg):
    if args.implementation=='matlab':
        from importlib.metadata import version
        if importlib.util.find_spec('matlab.engine') is None:
            raise RuntimeError('MATLAB_ENGINE_UNAVAILABLE')
        version('matlabengine')
        return dict(resources=['matlab'])
    return {}


def _protocol(ctx,args):
    value=ctx.artifact(args.protocol)
    return (TaskAnalysisProtocol if ctx.request.tool_version=='2.0.0' else AnalysisProtocol).model_validate(value)


def _model(value):
    if value.get('analysis_version')=='2.0.0': return EndpointLinearizedModel.model_validate(value)
    return OutputLinearizedModel.model_validate(value)


def control_metrics(ctx,args):
    p=_protocol(ctx,args)
    models=[_model(ctx.artifact(r)) for r in args.models]
    if any(m.time_domain!='continuous' for m in models):
        raise ValueError('CONTINUOUS_INPUT_MODEL_REQUIRED')
    if any(m.protocol_identity!=digest(plain(p)) for m in models): raise ValueError('MODEL_PROTOCOL_MISMATCH')
    records=[]
    def calculate(m,backend=None):
        A,B,C,D=normalized(m); drift=np.asarray(m.drift)/m.state_scales
        raw=raw_scipy(A,B,C,D,drift,p) if backend is None else backend.calculate(A,B,C,D,drift,p)
        return summarize(m,p,raw,dict(name=args.implementation,versions=versions(),
            matlab=None if backend is None else backend.environment))
    if args.implementation=='matlab':
        from .matlab import MatlabBatch
        with MatlabBatch() as backend:
            for m in models: records.append(calculate(m,backend))
    else:
        records=[calculate(m) for m in models]
    for r,ref in zip(records,args.models): r['model_reference']=plain(ref)
    return AnalysisResult(kind='control_metrics',protocol=args.protocol,bindings=[m.binding for m in models],
        records=records,evidence=args.models,limitations=LIMITATIONS)


def bounded_endpoint_analysis(ctx,args):
    p=TaskAnalysisProtocol.model_validate(ctx.artifact(args.protocol))
    target=EndpointTarget.model_validate(ctx.artifact(args.target)); models=[]
    for ref in args.models:
        model=EndpointLinearizedModel.model_validate(ctx.artifact(ref))
        if model.time_domain!='continuous': raise ValueError('CONTINUOUS_INPUT_MODEL_REQUIRED')
        if model.protocol_identity!=digest(plain(p)): raise ValueError('MODEL_PROTOCOL_MISMATCH')
        models.append(model)
    records=[]
    for ref,model in zip(args.models,models):
        position=bounded_endpoint(model,p,target,braking=False)
        warm=None
        if position.get('delta_input_n') is not None: warm=np.asarray(position['delta_input_n']).reshape(-1)
        braking=bounded_endpoint(model,p,target,braking=True,warm_start=warm)
        records.append(dict(binding=model.binding,operating_point=model.operating_point,model_reference=plain(ref),
            target_contract=plain(target),position_only=position,position_and_braking=braking))
    return AnalysisResult(kind='bounded_endpoint',protocol=args.protocol,bindings=[m.binding for m in models],
        records=records,evidence=[*args.models,args.target],limitations=LIMITATIONS+[
            'A feasible witness is local-model evidence only; undetermined is not infeasible.',
            'The speed constraint is a terminal braking diagnostic and does not alter the reach evaluator or establish settling.'])


def compare_case_metrics(ctx,args):
    results=[AnalysisResult.model_validate(ctx.artifact(r)) for r in args.results]
    if any(r.protocol!=args.protocol for r in results): raise ValueError('COMPARISON_PROTOCOL_MISMATCH')
    grouped={}
    for result in results:
        for record in result.records:
            binding=record.get('binding',result.bindings[0]); key=(binding['source_session_id'],binding['execution_id'])
            row=grouped.setdefault(key,dict(binding=binding,saved=None,operating_regions=[]))
            if result.kind=='saved_case': row['saved']=record
            if result.kind=='control_metrics':
                row['operating_regions'].append(dict(point=record['operating_point'],validity=record['validity'],
                    unstable_modes=record['poles']['unstable'],windows=record['windows'],
                    authority=record['authority'],tension_headroom_n=record['tension_headroom_n']))
    for row in grouped.values():
        sampled=[r for r in row['operating_regions'] if r['point'].get('actual_time_s') is not None]
        values=[r['windows'][-1]['continuous']['output']['eigenvalues'][0] for r in sampled]
        row['sampled_statistics']=dict(sample_count=len(sampled),locations=[r['point'] for r in sampled],
            minimum_output_eigenvalue=None if not values else dict(min=min(values),max=max(values),mean=float(np.mean(values)),units='normalized Gramian'),
            aggregation='equal-weight requested saved locations, not time-integrated trajectory statistics')
    return AnalysisResult(kind='comparison',protocol=args.protocol,bindings=[r['binding'] for r in grouped.values()],
        records=list(grouped.values()),evidence=args.results,
        limitations=LIMITATIONS+['Nine retrospective cases and one pass cannot establish causality or universal thresholds.'])


def design_screen(ctx,args):
    """Aggregate candidate-bound deterministic evidence without a fitted score."""
    from extensions.tendon_family.candidate_analysis import resolve_candidate
    inp,binding=resolve_candidate(ctx,args.source_node)
    p=TaskAnalysisProtocol.model_validate(ctx.artifact(args.protocol))
    linear=AnalysisResult.model_validate(ctx.artifact(args.linearization))
    metrics=AnalysisResult.model_validate(ctx.artifact(args.metrics))
    endpoint=AnalysisResult.model_validate(ctx.artifact(args.endpoint))
    for result,kind in ((linear,'candidate_linearization'),(metrics,'control_metrics'),(endpoint,'bounded_endpoint')):
        if result.kind!=kind or result.protocol!=args.protocol: raise ValueError('SCREEN_INPUT_KIND_OR_PROTOCOL_MISMATCH')
        if not result.bindings or any(item['configuration']!=binding['configuration'] for item in result.bindings):
            raise ValueError('SCREEN_CANDIDATE_BINDING_MISMATCH')
    header=linear.records[0]; applicability=header['applicability']
    metric_by_model={row['model_reference']['artifact_id']:row for row in metrics.records}
    endpoint_by_model={row['model_reference']['artifact_id']:row for row in endpoint.records}
    points=[]
    for row in linear.records[1:]:
        if 'model' not in row:
            points.append(dict(point=row.get('name'),available=False,reason=row.get('reason'),construction=row.get('construction'))); continue
        mid=row['model']['artifact_id']; metric=metric_by_model.get(mid); bound=endpoint_by_model.get(mid)
        if metric is None or bound is None: raise ValueError('SCREEN_MODEL_EVIDENCE_INCOMPLETE')
        nominal=metric['windows'][-1]
        points.append(dict(point=row['point'],available=True,construction=row.get('construction'),
            local_directions=dict(continuous_output=nominal['continuous']['output'],held_output=nominal['held']['output'],
                interpretation='Position-only local directions; frequency position channels are not stacked with derivative-related velocity channels.'),
            nominal_window=dict(window_s=nominal['window_s'],continuous_minimum_energy=nominal['continuous']['minimum_energy'],
                held_minimum_energy=nominal['held']['minimum_energy']),
            task_time=dict(position_only=bound['position_only'],position_and_braking=bound['position_and_braking']),
            tension_headroom_n=metric['tension_headroom_n'],equilibrium_frequency_applicability=metric['validity'],
            authority=metric['authority'],model_evidence=row['model']))
    feasible_position=sum(row.get('available') and row['task_time']['position_only']['status']=='feasible_in_local_model' for row in points)
    feasible_braking=sum(row.get('available') and row['task_time']['position_and_braking']['status']=='feasible_in_local_model' for row in points)
    report=dict(candidate_build_binding=binding,configuration_only_identity=header['configuration_only_identity'],
        execution_data_used=False,reachability_evidence=dict(model_scope=applicability['uses']['reachability'],
            hard_rejection=False,reason='No necessary global reach violation is established by these local calculations.'),
        operating_points=points,operating_point_availability=dict(requested=3,available=sum(r.get('available',False) for r in points)),
        applicability=applicability,metric_evidence_references=[plain(args.linearization),plain(args.metrics),plain(args.endpoint)],
        priority_reasoning=dict(position_feasible_witnesses=feasible_position,braking_feasible_witnesses=feasible_braking,
            priority='conditional_support' if feasible_position else 'insufficient_evidence',
            ties='Compare structured directions and witnesses; no scalar score or fitted threshold is defined.',
            warning='Local bounded linear witnesses cannot certify nonlinear task success; rank-two straight output controllability is not a global reach rejection.'),
        hard_rejection=None)
    return AnalysisResult(kind='design_screen',protocol=args.protocol,bindings=[binding],records=[report],
        evidence=[args.linearization,args.metrics,args.endpoint],limitations=LIMITATIONS+[
            'Screening is conditional and retrospective; no weights or thresholds were fitted to historical outcomes.'])
