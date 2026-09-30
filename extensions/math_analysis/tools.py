"""Thin public tools: trusted implementation selection and common results."""
import numpy as np
from schemas.platform_analysis import AnalysisProtocol, OutputLinearizedModel, AnalysisResult
from tools.state_io import digest
from tools.platform_store import plain
from .kernels import normalized, raw_scipy, summarize, versions, LIMITATIONS


def preflight(inp,args,reg):
    if args.implementation=='matlab':
        from importlib.metadata import version
        version('matlabengine')
        return dict(resources=['matlab'])
    return {}


def control_metrics(ctx,args):
    p=AnalysisProtocol.model_validate(ctx.artifact(args.protocol))
    models=[OutputLinearizedModel.model_validate(ctx.artifact(r)) for r in args.models]
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
