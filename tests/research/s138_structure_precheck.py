"""Two independent Reach conditions, three generated structures, affine A/B/C.

Run with --output <new path>. No Study grant, Provider, MuJoCo steps or PPO.
Evaluators score explicitly labelled model predictions, never physical evidence.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time
import numpy as np

from schemas.platform import SessionInput, BackendResult
from schemas.platform_analysis import EndpointLinearizedModel, TaskAnalysisProtocol, TaskAnalysisRequirement
from tools.platform_store import plain
from tools.platform_registry import registry
from tools.state_io import digest
from tools.research.analysis import calculate
from tools.research.design import resolved_configuration, source_lengths
from tools.research.optimal_capability import CONIC
from extensions.tendon_family.gvs_basis import resolve_basis
from extensions.math_analysis.task_capability import task_capability

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'evidence/s129_math_capability/gvs_pair.json'


def evaluate_prediction(configuration, model, result):
    """Feed complete saved model outputs to the existing independent evaluator."""
    replay=result.get('replay',{})
    if not replay.get('numerically_valid'):
        return dict(status='unavailable',task_success=None,reason='No independently replayed finite control witness')
    inp=SessionInput.model_validate(configuration)
    output=next(o for o in model.endpoint_outputs if o.name=='tip_position')
    states=np.asarray(replay['states'])[1:]
    delta=np.asarray(result['applied_input_n'])-model.u0
    positions=np.asarray(output.value0)+states@np.asarray(output.C).T+delta@np.asarray(output.D).T
    predicted=BackendResult(solver_status='completed',backend_id='offline.local_affine_prediction',
        model_id=model.binding['model_identity'],seed=inp.seed,
        signals=[dict(spec=inp.task.observations[0],times_s=[(i+1)*inp.task.timing.sample_period_s for i in range(len(states))],
            values=positions.tolist())],initial_state=dict(contract='platform.empty',data={}),
        data=dict(contract='platform.empty',data={}),limitations=['Local affine prediction only; no physical execution'])
    ref=dict(artifact_id=digest(plain(predicted)),media_type='application/json')
    evaluator=registry().get(inp.task.evaluator.extension_id,kind='evaluator').resolve()
    return dict(scope='independent Reach evaluator on affine prediction, not physical task acceptance',
        prediction=plain(predicted),evaluation=plain(evaluator(inp.task,predicted,ref,registry(),digest(plain(inp.task)))))


def run():
    started=time.perf_counter()
    saved=json.loads(SOURCE.read_text(encoding='utf8'))
    baseline=saved['baseline'];candidate=saved['supporting_artifacts'][baseline['candidate']['artifact_id']]
    source=candidate['configuration'];parameters=candidate['parameters']
    original_control=baseline['trajectory']['applied_input_n']
    first=list(source['task']['goal']['data']['target_m']);second=[first[0],-first[1],first[2]]
    result=dict(version='s138_offline_structure_precheck_v1',
        scope='Three real generated soft-arm structures, two separate Reach TaskDefinitions; local affine predictions only',
        source=dict(path=SOURCE.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            original_control_pointer='/baseline/trajectory/applied_input_n',
            original_control_meaning='Frozen S129 baseline mathematical control witness; not a recorded NMPC execution'),
        comparison='A: baseline + frozen original control; B: baseline + independently reoptimized control per target; C: changed structure + independently reoptimized control per target',
        selection='Two predeclared mirror targets; root length +/-2 mm with fixed total length, no result-dependent target/threshold selection',
        task_acceptance='unmeasured',cases=[],comparisons=[],
        budgets=dict(provider_calls=0,mujoco_steps=0,ppo_training=0,formal_studies=0,model_builds=0,conic_solves=0,fixed_control_replays=0))
    for label,offset in (('baseline',0.),('root_shorter',-.002),('root_longer',.002)):
        params=deepcopy(parameters)
        params['segments']['near']['length_m']+=offset
        params['segments']['distal1']['length_m']-=offset
        for index,target in enumerate((first,second)):
            base=deepcopy(source);base['task']['task_id']+='-s138-'+str(index)
            base['task']['goal']['data']['target_m']=target
            cfg=resolved_configuration(source,base,params,'s138-offline-'+label+'-'+str(index))
            config_ref=dict(artifact_id=digest(cfg),media_type='application/json')
            tendons=cfg['robot']['structure']['data']['tendons'];basis=cfg['policy']['controller']['parameters']['data']['recipe']['basis']
            binding=dict(candidate_id=digest(dict(configuration=cfg,parameters=params)),configuration=config_ref,
                candidate=config_ref,source_identity=digest(source),effective_configuration_identity=digest(cfg),
                task_identity=digest(cfg['task']),basis=basis,
                coordinate_order=list(resolve_basis(cfg['robot']['structure']['data'],basis).coordinate_order),
                tendon_order=[t['id'] for t in tendons],tension_limits_n=[t['force_limit_n'] for t in tendons])
            query=dict(candidate=config_ref,operation='task_capability',operating_point='controller_start_input',
                protocol=baseline['protocol'],capability_method=CONIC)
            raw=calculate(cfg,binding,query)
            result['budgets']['model_builds']+=1
            trajectory=raw.get('trajectory',{})
            result['budgets']['conic_solves']+=int(bool(trajectory.get('solver',{}).get('status')))
            row=dict(structure=label,target_index=index,target_m=target,configuration=cfg,parameters=params,
                lengths_m=source_lengths(cfg),mathematics=raw,reoptimized_score=trajectory.get('replayed_violation'))
            if raw.get('model'):
                model=EndpointLinearizedModel.model_validate(raw['model'])
                row['reoptimized_evaluator']=evaluate_prediction(cfg,model,trajectory)
                if offset==0:
                    original=task_capability(model,TaskAnalysisRequirement.model_validate(raw['task_analysis']),
                        TaskAnalysisProtocol.model_validate(raw['protocol']),applied_input_n=original_control)
                    result['budgets']['fixed_control_replays']+=1
                    row.update(original_control_replay=original,original_evaluator=evaluate_prediction(cfg,model,original))
            result['cases'].append(row)
            print(json.dumps(dict(structure=label,target=index,score=row['reoptimized_score'],
                optimality=trajectory.get('optimality_status'),evaluator_pass=row.get('reoptimized_evaluator',{}).get('evaluation',{}).get('task_success'))),flush=True)
    for row in result['cases'][2:]:
        baseline_row=result['cases'][row['target_index']]
        a,b=row['reoptimized_score'],baseline_row['reoptimized_score']
        result['comparisons'].append(dict(structure=row['structure'],target_index=row['target_index'],
            C_minus_B=None if a is None or b is None else a-b,
            meaning='Reoptimized model-witness difference; negative is better. No structural necessity or physical improvement claim.'))
    result['elapsed_s']=time.perf_counter()-started
    result['implementation_sha256']={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [Path(__file__),ROOT/'tools/research/analysis.py',ROOT/'tools/research/task_constraints.py',
            ROOT/'extensions/tendon_family/math_analysis.py',ROOT/'extensions/math_analysis/conic_capability.py']}
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    output=parser.parse_args().output
    if output.exists():parser.error('Output exists; preserve previous results.')
    result=run();output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2,allow_nan=False)
