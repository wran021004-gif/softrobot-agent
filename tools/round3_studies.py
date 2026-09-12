"""Small staged surrogate study using ExperimentSession, existing runs and budgets."""
import json
import math
import random
from pathlib import Path

from capabilities.registry import get_robot_family_grammar
from schemas.design_spec import DesignSpec
from tools.artifact_tools import create_run, finalize_run, file_hash
from tools.design_envelope import load_envelope
from tools.experiment_tools import _execute
from tools.harness import _snapshot_sources
from tools.pcc_math import analytic_target_matching_length
from tools.spec_tools import ROOT, load_yaml, load_task_package


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def policy_for_subset(baseline_source, variables, *, purpose='DESIGN_SEARCH', total=30, mujoco=10, name='subset'):
    """Engineer choices reference one existing approval; no invented variable bounds."""
    envelope, _ = load_envelope(get_robot_family_grammar('tendon_driven_continuum'))
    return dict(policy_id='round3_final_'+name, authorization_mode='ENVELOPE_SUBSET', purpose=purpose,
        physics_profile=envelope['physics_profile'], task_contract_id='reach_free_v1',
        task_contract_source='tasks/reach_free/contract.yaml', baseline_design=baseline_source,
        scientific_status='HUMAN_APPROVED', approval_status='HUMAN_APPROVED',
        approval_source=envelope['approval_source'], variables=[dict(name=n,unit=envelope['fields'][n]['unit'],
            lower_bound=envelope['fields'][n]['lower_bound'],upper_bound=envelope['fields'][n]['upper_bound'],
            constraints=envelope['fields'][n]['constraints']) for n in variables],
        objective_metric_refs=['model.predicted_position_error_m','mujoco.position_error_m'],
        evaluation_budget=total, mujoco_validation_budget=mujoco, seed=17,
        allowed_model_levels=['M0','M1'],allowed_controller_levels=['C1'],
        repair_iteration_budget=0,repair_actions=[],stop_conditions=['budget_exhausted','actions_exhausted'])


def design_key(design):
    return tuple(DesignSpec.model_validate(design).model_dump().items())


def unique_designs(designs):
    seen = set()
    for design in designs:
        key = design_key(design)
        if key not in seen:
            seen.add(key)
            yield dict(key)


def joint_candidates(baseline, length, radius, count, analytic_length, limit=20, seed=17):
    """Prior evidence first, then a small seeded sample; no Cartesian grid."""
    best_l = {**baseline,'total_length_m':length}
    best_r = {**best_l,'tendon_routing_radius_m':radius}
    guided = [baseline,best_l,best_r,{**best_r,'tendon_count':count}]
    guided += [{**best_r,'tendon_count':n} for n in range(3,9)]
    guided += [{**best_r,'total_length_m':v,'tendon_count':count} for v in (analytic_length,.30,.32,.35)]
    rng = random.Random(seed)
    result = list(unique_designs(guided))[:limit]
    # Evidence-guided proposal distribution; policy continues to authorize the full envelope.
    while len(result) < limit:
        candidate = {**baseline,'total_length_m':rng.uniform(min(length,.29),max(length,.40)),
                     'tendon_routing_radius_m':rng.uniform(.002,.018),'tendon_count':rng.randint(3,8)}
        result = list(unique_designs([*result,candidate]))
    return result


class StudyLedger:
    """Reuse exact, verified evaluations within this invocation, across study parents."""
    def __init__(self, matlab_factory, run_root):
        self.matlab_factory, self.run_root = matlab_factory, Path(run_root)
        self.cache = {}
        self.rows = {}
        self.reuse_count = 0

    def evaluate(self, session, design, fidelity):
        design = session.experiment.validate_candidate(design)
        key = (design_key(design), fidelity)
        bindings = session.experiment.resolved.source_hashes
        reused = key in self.cache
        if reused:
            result, source_bindings = self.cache[key]
            if source_bindings != bindings or file_hash(self.run_root/result.run_id/'run.json') != result.run_manifest_hash:
                raise ValueError('Cached execution provenance changed')
            self.reuse_count += 1
            name = f'reused_{self.reuse_count:04d}.json'
            session.run.save(name, {'role':'REUSED_COMPLETED_EVALUATION','source_evaluation':result.model_dump(mode='json'),
                'source_bindings':bindings,'design':design.model_dump(),
                'new_numerical_evaluations':0,'current_policy_hash':session.experiment.policy_hash})
            session.decision('reuse_completed_evaluation',[name],
                'Exact design/fidelity and task/source hashes match; use the sealed original evidence without another rollout.')
        else:
            session.debug = fidelity == 'MUJOCO'
            result = session.evaluate(design, fidelity)
            if result.status not in ('MODEL_ONLY','PASS','TASK_FAILED','DESIGN_INFEASIBLE'):
                raise RuntimeError(f'Unexpected candidate execution failure: {result.model_dump()}')
            self.cache[key] = (result, bindings)
        child = self.run_root/result.run_id
        def metrics(name):
            return read(child/name).get('metrics',{}) if (child/name).is_file() else {}
        shape = metrics('shape_comparison.json')
        row = {'design':design.model_dump(),'fidelity':fidelity,'reused':reused,
            'source_parent_experiment_id':result.parent_experiment_id,'source_candidate_id':result.candidate_id,
            'run_id':result.run_id,'run_manifest_hash':result.run_manifest_hash,'robot_ir_hash':result.robot_ir_hash,
            'status':result.status,'canonical_task_status':result.canonical_task_status,
            'model':result.model_metrics,'actuation':metrics('actuation_result.json'),
            'shape':{k:v for k,v in shape.items() if k not in ('per_sample_differences','comparison_context')},
            'canonical_error_m':result.canonical_metrics.get('position_error_m'),
            'tracking':metrics('check_tendon_tracking.json'),'force':metrics('check_actuator_limits.json'),
            'numerics':metrics('inspect_numerics.json'),
            'disposition':'REJECTED_HARD_GEOMETRY' if result.status=='DESIGN_INFEASIBLE' else result.status}
        if result.status == 'DESIGN_INFEASIBLE':
            row['rejection_reason'] = read(child/'gate_summary.json')['stopped_by']
        if fidelity == 'MUJOCO':
            if shape.get('evidence_status') != 'available':
                raise ValueError('Normal shape evidence missing: '+str(shape))
            parameters = result.canonical_metrics['execution_evidence']['compiled_parameter_evidence']
            row['mass_inertia'] = {k:parameters[k] for k in ('body_mass','body_inertia')}
            row['total_mass_kg'] = sum(parameters['body_mass']['value'])
            if read(child/'debug/status.json')['errors']:
                raise ValueError('Representative debug artifacts failed')
        self.rows.setdefault(session.run.record.run_id, []).append(row)
        session.run.save('study_rows.json', self.rows[session.run.record.run_id])
        return row


def best_canonical(rows):
    rows = [r for r in rows if r['canonical_error_m'] is not None]
    return min(rows, key=lambda r:(r['canonical_task_status']!='PASS',r['canonical_error_m']))


def run_round3_final(*, matlab_factory, run_root=ROOT/'runs'):
    """Single MATLAB session is provided by caller. No C2 or physics mutation."""
    report = create_run(run_root)
    _snapshot_sources(report)
    ledger = StudyLedger(matlab_factory,run_root)
    baseline = load_yaml(ROOT/'configs/design_tendon_arm.yaml')
    task, _ = load_task_package()
    analytic = analytic_target_matching_length(task.target_m)
    summaries = {}
    status = 'ERROR'

    def stage(name, reference, variables, callback, *, total, mujoco, purpose='DESIGN_SEARCH'):
        ref = report.save(name+'_reference.yaml',reference)
        policy = report.save(name+'_policy.yaml',policy_for_subset(ref.relative_to(ROOT).as_posix(),variables,
            purpose=purpose,total=total,mujoco=mujoco,name=name))
        def execute(session):
            session.decision('study_plan',['optimization_policy.yaml'],
                'Human envelope permits this subset; deterministic study choices are frozen before candidate execution. No new physics.')
            return callback(session)
        parent = _execute(policy,name,execute,run_root=run_root,matlab_factory=matlab_factory)
        summaries[name] = {'parent_run_id':parent.record.run_id,'manifest_hash':file_hash(parent.path/'run.json'),
            'summary':read(parent.path/(name+'_summary.json')),'budget':read(parent.path/'experiment_summary.json'),
            'rows':ledger.rows.get(parent.record.run_id,[])}
        report.save('study_index.json',summaries)
        print(name, parent.record.final_status, parent.path, flush=True)
        if parent.record.final_status != 'PASS':
            raise RuntimeError(summaries[name]['summary'])
        return summaries[name]

    try:
        def length_study(session):
            values = sorted(set([.05,.10,.20,.25,.29,.30,analytic['total_length_m'],.32,.35,.40,.50,.60,.80]))
            session.run.save('study_plan.json',{'lengths_m':values,'analytic_target_match':analytic,
                'mujoco_lengths_m':[.4,.29,.30,analytic['total_length_m'],.32,.35,.60],
                'selection':'baseline, near necessary bound, analytic/M1 minimum and both neighbors, previous boundary, clearly longer point'})
            for value in values:
                ledger.evaluate(session,{**baseline,'total_length_m':value},'M1')
            rows = [ledger.evaluate(session,{**baseline,'total_length_m':v},'MUJOCO')
                    for v in [.4,.29,.30,analytic['total_length_m'],.32,.35,.60]]
            assert rows[0]['canonical_error_m'] == .17116166894090315
            assert rows[0]['model']['predicted_position_error_m'] == .08714456960728613
            assert rows[0]['canonical_task_status'] == 'TASK_FAILED'
            return {'best_observed':best_canonical(rows),'analytic_target_match':analytic}
        lengths = stage('length',baseline,['total_length_m'],length_study,total=20,mujoco=7)
        best_l = lengths['summary']['best_observed']['design']

        def radius_study(session):
            values = [.002,.004,.006,.008,.010,.012,.015,.018]
            selected = [.002,.006,.010,.015,.018]
            session.run.save('study_plan.json',{'routing_radii_m':values,'mujoco_radii_m':selected,
                'selection':'geometric stroke scale coverage including both endpoints and legacy radius; M1 tip error is not the sole ranking signal'})
            for value in values:
                ledger.evaluate(session,{**best_l,'tendon_routing_radius_m':value},'M1')
            rows = [ledger.evaluate(session,{**best_l,'tendon_routing_radius_m':v},'MUJOCO') for v in selected]
            return {'best_observed':best_canonical(rows),'selection_basis':'canonical comparison among geometrically diverse representatives'}
        radii = stage('routing_radius',best_l,['tendon_routing_radius_m'],radius_study,total=13,mujoco=5)
        best_r = radii['summary']['best_observed']['design']

        def count_study(session):
            session.run.save('study_plan.json',{'tendon_counts':[3,4,5,6,7,8],
                'scope':'surrogate topology exploration; not manufacturing optimality'})
            rows = [ledger.evaluate(session,{**best_r,'tendon_count':n},'MUJOCO') for n in range(3,9)]
            return {'best_observed':best_canonical(rows)}
        counts = stage('tendon_count',best_r,['tendon_count'],count_study,total=6,mujoco=6)
        best_n = counts['summary']['best_observed']['design']

        def joint_study(session):
            candidates = joint_candidates(baseline,best_l['total_length_m'],best_r['tendon_routing_radius_m'],
                                          best_n['tendon_count'],analytic['total_length_m'])
            session.run.save('study_plan.json',{'candidates':candidates,'screening_cap':30,'mujoco_cap':10,
                'selection':'prior canonical representatives, best M1, radius/count coverage, then M1 ordering; seeded evidence-guided proposals within full envelope'})
            models = [ledger.evaluate(session,c,'M1') for c in candidates]
            models = [r for r in models if r['status']=='MODEL_ONLY']
            ranked = sorted(models,key=lambda r:r['model']['predicted_position_error_m'])
            selected = [baseline,best_l,best_r,best_n,ranked[0]['design']]
            for key in ('tendon_routing_radius_m','tendon_count'):
                selected.extend([min(models,key=lambda r:r['design'][key])['design'],
                                 max(models,key=lambda r:r['design'][key])['design']])
            selected = list(unique_designs([*selected,*(r['design'] for r in ranked)]))[:10]
            session.run.save('selected_for_mujoco.json',selected)
            rows = [ledger.evaluate(session,c,'MUJOCO') for c in selected]
            return {'best_observed_surrogate_design':best_canonical(rows),
                'screened_designs':len(candidates),'canonical_comparisons':len(rows),'global_optimum_claimed':False}
        joint = stage('joint_search',baseline,['total_length_m','tendon_routing_radius_m','tendon_count'],
                      joint_study,total=40,mujoco=10)
        best_joint = joint['summary']['best_observed_surrogate_design']['design']

        def segments_study(session):
            session.run.save('study_plan.json',{'segments':[4,6,8,12,16,24],
                'scope':'NUMERICAL_SENSITIVITY_ONLY','limitation':'Per-joint stiffness/damping are not scaled with segment length; changing segments changes effective surrogate mechanics and capsule mass/inertia.'})
            rows = [ledger.evaluate(session,{**best_joint,'segments':n},'MUJOCO') for n in [4,6,8,12,16,24]]
            # No min/error-based segment selection or design optimum.
            return {'rows':rows,'purpose':'NUMERICAL_SENSITIVITY_ONLY',
                'physical_design_ranking':None,'failure_attribution':'UNKNOWN'}
        stage('segments',best_joint,['segments'],segments_study,total=6,mujoco=6,purpose='NUMERICAL_SENSITIVITY')
        report.save('round3_final_summary.json',{'studies':summaries,'analytic_target_match':analytic,
            'best_observed_surrogate_design':joint['summary']['best_observed_surrogate_design'],
            'reused_evaluations':ledger.reuse_count,'new_evaluations':len(ledger.cache),
            'new_mujoco_evaluations':sum(k[1]=='MUJOCO' for k in ledger.cache),
            'failure_attribution':'UNKNOWN','scope':'SURROGATE_EXPLORATION_ENVELOPE_V1'})
        status = 'PASS'
    except Exception as exc:
        report.save('study_error.json',{'message':str(exc)})
        raise
    finally:
        finalize_run(report,status,None if status=='PASS' else 'UNKNOWN')
        print('Round 3 final study:',report.path,flush=True)
    return report
