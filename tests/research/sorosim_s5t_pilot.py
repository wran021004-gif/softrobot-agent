"""One derivative preflight and scoped S5-T reliability decision without full NLP."""
import hashlib
import json
from pathlib import Path
import tarfile
import time

from extensions.tendon_family.sorosim_codesign import calculate
from tools.research import core
from tools.research.design import numerical_binding,verify_candidate
from tools.research.state import state,save,update
from tools.state_io import atomic_json,read

ROOT=Path(__file__).resolve().parents[2]
STUDY=ROOT/'configs/research/study_sorosim_s5_sensitivity.json'


def sealed(archive,reference):
    body=archive.extractfile('artifacts/'+reference['artifact_id']+'.json').read()
    if hashlib.sha256(body).hexdigest()!=reference['artifact_id']:
        raise ValueError('SEALED_ARTIFACT_HASH_MISMATCH')
    return json.loads(body)


def plan(action,**data):
    return dict(action=action,
        hypothesis='A solved task-capability KKT point is required for reoptimized structural sensitivity.',
        expected_observation='Signed task epigraph derivatives and available source optimality diagnostics.',
        weakening_observation='Nonconverged source optimizer or missing full-NLP multipliers.',
        fixed_conditions='Exact Design B mathematical model, frozen original task and fixed topology.',
        stopping_condition='One derivative preflight; no full reoptimization without a trustworthy KKT point.',
        interpretation='A fixed-command secant is not an envelope gradient or physical sensitivity.',**data)


def run(directory):
    host=core.prepare(STUDY,directory)
    if 'freeze' not in state(host):core.bind(host)
    old=read(ROOT/'evidence/sorosim_s4b/recovered_pilot/summary.json')['rows'][1]
    with tarfile.open(ROOT/'evidence/sorosim_s4b/recovered_pilot/immutable_artifacts.tar.gz') as archive:
        params=sealed(archive,old['candidate'])['parameters']
    candidate=core.dispatch(host,plan('generate',generation=params),'s5t-generate-B')['result']['candidate']
    current=verify_candidate(host,candidate)
    if numerical_binding(current['configuration'],state(host)['spec'])['physical_design_identity']!=old['physical_design_identity']:
        raise ValueError('S5T_DESIGN_B_MISMATCH')
    source_index=read(ROOT/'evidence/sorosim_s45/interior_summary.json')
    source_archive=ROOT/'evidence/sorosim_s45/final_study/immutable_artifacts.tar.gz'
    audit=read(ROOT/'evidence/sorosim_s45/posthoc_verification.json')
    if hashlib.sha256(source_archive.read_bytes()).hexdigest()!=audit['source_archive_sha256']:
        raise ValueError('S45_ARCHIVE_CHANGED')
    with tarfile.open(source_archive) as archive:
        solve=sealed(archive,source_index['solve']['reference'])
    if solve['mathematical_facts']['converged'] or audit['optimizer_converged']:
        raise ValueError('SOURCE_OPTIMALITY_CLASSIFICATION_CHANGED')
    source_ref=save(host,dict(source=source_index['solve']['reference'],audit=audit,
        mathematical_facts=solve['mathematical_facts'],task_requirements=solve['task_requirements']),
        's5t_sealed_source_optimality')
    request=dict(operation='solve',configuration=current['configuration'],design_candidate=candidate,
        arguments=dict(candidate=candidate,substeps=1,initialization='constant_0_2',warm_source=None,
            objective_mode='task_capability',position_weight=1.,speed_weight=1.,secondary_coefficient=0.),
        check_only=True)
    started=time.perf_counter()
    derivative=calculate(request)
    elapsed=time.perf_counter()-started
    if state(host)['mathematical_evaluations']>=state(host)['spec']['budgets']['mathematical_evaluations']:
        raise ValueError('S5T_DERIVATIVE_PREFLIGHT_BUDGET_EXHAUSTED')
    update(host,mathematical_evaluations=state(host)['mathematical_evaluations']+1,
        numerical_s=state(host)['numerical_s']+elapsed)
    derivative_ref=save(host,dict(mode='task_capability',check_only=True,full_optimization=False,
        derivative=derivative,charged_numerical_s=elapsed,candidate=candidate),
        's5t_task_capability_derivative_check')
    historical=read(ROOT/'evidence/sorosim_s45/historical_margins.json')['reports'][0]
    cross=read(ROOT/'evidence/sorosim_s45/summary.json')['cross_replays'][1]
    with tarfile.open(ROOT/'evidence/sorosim_s45/attempt01/immutable_artifacts.tar.gz') as archive:
        transferred=sealed(archive,cross['result_reference'])
    replay=transferred['replay'];assert replay['passed']
    def maximum(name,rows):
        return max(row['observed_norm'] for row in rows if row['constraint_id']==name)
    a=historical['samples'];b=replay['task'];delta=old['length_m']-historical['length_m']
    metrics=dict(terminal_error_m=(maximum('terminal_error_m',a),b['actual_norm'][0]),
        holding_max_error_m=(maximum('holding_max_error_m',a),max(b['actual_norm'][1:7])),
        holding_max_speed_m_s=(maximum('holding_max_speed_m_s',a),max(b['actual_norm'][7:])))
    secant={name:dict(design_A=value[0],design_B=value[1],difference=value[1]-value[0],
        quotient_per_m=(value[1]-value[0])/delta) for name,value in metrics.items()}
    classification=dict(stage='S5-T',candidate=candidate,source_optimality=source_ref,
        mathematical_model_identity=solve['trajectory']['model_identity'],
        task_identity=solve['trajectory']['task_identity'],
        task_constraints=solve['task_requirements']['constraints'],
        task_capability=dict(definition='minimum over legal U and complete dynamics of maximum squared-normalized original sampled task excess',
            epigraph='unrestricted rho in new task_capability mode; negative values represent strict sampled feasibility',
            derivative_preflight=derivative_ref,full_optimization_attempts=0),
        kkt=dict(reliability='solver_unresolved',source_converged=False,
            source_full_nlp_multipliers='not_saved_in_historical_solve',
            new_extractor='sr_codesign raw fmincon multipliers, complete-NLP stationarity/primal/dual/complementarity for future solves',
            envelope_gradient='unavailable',reason='No converged and validated base full-NLP KKT point; no perturbation reoptimizations admitted'),
        fixed_input_mathematical_secant=dict(source_A=historical['source_replay'],source_B=cross['result_reference'],
            physical_tensions='same historical U_A',proximal_length_difference_m=delta,metrics=secant,
            reliability='controlled_two_design_secant_not_local_derivative'),
        physical_closed_loop_sensitivity='unmeasured_no_paired_structural_MuJoCo_experiment',
        gradient_error_bound=None,gradient_lipschitz_bound=None,descent_certificate='unavailable',
        physical_acceptance='separately measured S5-A/S5-B failures',
        costs=dict(mathematical_evaluations=1,full_reoptimizations=0,physical_launches=0,numerical_s=state(host)['numerical_s']))
    ref=save(host,classification,'s5t_reliability_classification')
    core.dispatch(host,plan('stop',supporting_evidence=[source_ref,derivative_ref,ref]),'s5t-stop')
    exported=core.export(host,ROOT/'evidence/sorosim_s5t/study')
    atomic_json(ROOT/'evidence/sorosim_s5t/summary.json',dict(classification,stage_summary_reference=ref))
    return exported


if __name__=='__main__':
    import sys
    print(run(Path(sys.argv[1])))
