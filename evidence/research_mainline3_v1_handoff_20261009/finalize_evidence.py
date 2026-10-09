"""Close the actual saved V1 chain; reads only, no model or scientific calls."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import base64
import hashlib
import json
import time
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.state_io import read, atomic_json, digest
from tools.research_single_validation import sha

OUT = Path(__file__).resolve().parent

manifest = read(OUT/'validation_manifest.json')
b = read(OUT/'coordinated_bundle.json')
c = read(OUT/'fixed_bundle.json')
result = read(OUT/'fixed_result.json')
gate_b = read(OUT/'coordinated_gate.json')
usage = read(OUT/'provider_usage.json')
receipts = result['receipts']
evaluation = c['artifacts'][receipts[5]['output']['artifact_id']]
profile = c['artifacts'][receipts[6]['output']['artifact_id']]['detail']
joint = result['joint_acceptance']
geometry = read(OUT/'geometry_review.json')
configuration = c['artifacts'][profile['configuration']['artifact_id']]
effective = configuration['effective']
from extensions.tendon_family.gvs_profile import execution_scope

checks = dict(
    B_accepted=gate_b['passed'],
    eight_completed_public_components=len(receipts)==8 and all(r['execution_status']=='completed' for r in receipts),
    one_primary_backend=read(OUT/'fixed_ledger.json')['used']['backend_solves']==1,
    execution_complete_valid=profile['valid_complete_execution'] and profile['complete'] and evaluation['validity']=='valid',
    simulation_evaluation_profile_joint_binding=(receipts[4]['execution_id']==evaluation['source_execution_id']==profile['execution_id']==joint['execution_id']
        and evaluation['source']==receipts[4]['output'] and profile['simulation']==receipts[4]['output'] and profile['evaluation']==receipts[5]['output']),
    prepared_and_executed_configuration=profile['configuration']==geometry['configuration'],
    profile_reports_executed_scope=profile['execution_scope']==execution_scope(effective),
    unchanged_fixed_changes=configuration['changes']==manifest['fixed_changes'],
    physical_outcome_recorded=joint['status'] in ('accepted','valid_failure') and not joint['missing'] and not joint['issues'],
    binary_archive_lossless=all(hashlib.sha256(base64.b64decode(v['base64_bytes'])).hexdigest()==key for key,v in c['binary_artifacts'].items()),
)
assert all(checks.values()), checks
atomic_json(OUT/'fixed_gate.json', dict(passed=True, checks=checks,
    meaning='Complete valid fixed C interface execution; joint physical failure is preserved and does not authorize a retry.',
    physical_acceptance=joint['accepted'], joint_status=joint['status'], backend_execution_id=profile['execution_id'],
    configuration=profile['configuration'], receipts=receipts,
    mathematical_validity='Three complete public operations; three available local models, one unavailable halfway construction, one undetermined initial braking diagnostic. No global/nonlinear feasibility claim.',
    timing_demonstrated=profile['real_time_demonstrated']))

atomic_json(OUT/'fixed_evaluation.json', evaluation)
atomic_json(OUT/'fixed_profile.json', profile)
atomic_json(OUT/'fixed_joint_acceptance.json', joint)
atomic_json(OUT/'C_material_review.json', dict(passed=True, checks=checks,
    review='Inspect actual sealed evaluation/profile/joint records and geometry/controller bindings; no new solver, experiment or paid judge.',
    observed=dict(reach=evaluation['task_success'], reach_error_m=evaluation['metrics'][0]['value'],
        holding_position_passed=joint['components']['holding_position']['passed'],
        holding_speed_passed=joint['components']['holding_speed']['passed'],
        holding_max_error_m=joint['metrics']['holding_max_error_m'], holding_max_speed_m_s=joint['metrics']['holding_max_speed_m_s'],
        solver_error_count=profile['solver_error_count'], force_bound_violation_n=profile['force_bound_violation_n'],
        updates=profile['updates'], deadline_misses=profile['deadline_misses'], mean_update_s=profile['mean_update_s'],
        accepted_noninitialization_plans=profile['accepted_noninitialization_plans'], initialization_selected=profile['initialization_selected'],
        projection_residual_max_rad_m=profile['max_projection_residual_rad_m']),
    limitations=['Sampled holding only; no continuous-time guarantee or real-robot validation',
        'Real time not demonstrated', 'Local mathematics is distinct from nonlinear/physical acceptance',
        'No paired comparison or causal improvement claim relative to Stage 3.36',
        'No unique physical diagnosis, controller weight search or optimality proof']))

sealed = read(OUT/'sealed_history.json')
unchanged = all(sha(ROOT/p)==expected for p,expected in sealed.items())
assert unchanged
atomic_json(OUT/'sealed_history_check.json', dict(passed=True, files=len(sealed),
    original_activities_and_Stage336_unchanged=True, method='Single exact-byte manifest check; no historical execution/regression suite.'))

phase_usage = {key:read(OUT/(key+'_ledger.json'))['used'] for key in ('coordinated','fixed')}
engineering = []
for bundle in (b,c):
    for row in bundle['calls']:
        if row['caller'].startswith('coding-agent'):
            engineering.append(dict(run_id=row['run_id'],request_id=row['request_id'],kind=row['receipt']['tool_id'],wall_s=row['charged']['wall_s']))
wall = max(0,time.time()-read(OUT/'activity_start.json')['started_unix'])
node_wall = sum(row['charged']['wall_s'] for row in b['calls'] if row['caller']=='investigation-dispatcher')
workflow_wall = sum(phase_usage[p]['wall_s'] for p in phase_usage)
elapsed_unallocated = max(0,wall-workflow_wall)
stamp = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).isoformat()
facts = dict(status='authorized_V1_scope_complete',completed_at_shanghai=stamp,A_preserved=True,A_new_requests=0,
    B=dict(accepted=True,both_reports_reused=True,new_investigator_requests=0,new_planning_requests=0,
        synthesis=read(OUT/'coordinated_result.json')['coordinator_synthesis'],principal=read(OUT/'coordinated_result.json')['report'],
        dispositions='Two model-authored partial accept decisions',receipts=read(OUT/'coordinated_result.json')['receipts'],
        material_review='material_audit.json',unsupported_interpretations_excluded=True),
    C=dict(interface_complete=True,backend_executions=1,backend_execution_id=profile['execution_id'],configuration=profile['configuration'],
        mathematical_operations=3,available_models=3,unavailable_halfway_point=True,
        initial_position_and_braking='undetermined',execution_validity='valid_complete',
        physical_acceptance=joint['accepted'],joint_status=joint['status'],official_reach=evaluation['task_success'],
        terminal_error_m=joint['metrics']['terminal_error_m'],holding_max_error_m=joint['metrics']['holding_max_error_m'],
        holding_max_speed_m_s=joint['metrics']['holding_max_speed_m_s'],timing=joint['timing'],
        reporting_recovery='Original six preparation/analysis/simulation/evaluation receipts reused; one failed profile preserved and one corrected profile plus joint acceptance recorded.',
        second_backend_executed=False),
    resources=dict(new_provider_requests=17,provider_reported_tokens=usage['provider_reported_tokens'],
        purposes={'ordinary':12,'model_correction':5,'engineering_recovery':0},unknown_new_usage_requests=0,
        public_workflow_operations=sum(v['tool_calls'] for v in phase_usage.values()),provider_request_ceiling=40,
        public_operation_ceiling=512,mathematical_operations=3,backend_executions=1,monetary_cost=None,
        phase_ledger_usage=phase_usage,engineering_records=engineering,model_node_wall_s=node_wall,
        total_elapsed_s_at_closeout=wall,engineering_recorded_wall_s=sum(r['wall_s'] for r in engineering),
        additional_unallocated_elapsed_s=elapsed_unallocated,
        elapsed_rule='Overall wall clock includes all preparation/repairs/review/wait/delivery; ledger intervals and residual are reported without equating reservations, estimates or tokens. Residual includes final review/delivery overhead.'),
    code_versions=dict(B_first13_requests='1dbdb2d01fc0fefbaa75159fec2a49b20b807cea',B_last4_requests=result['backend_code_commit'],
        C_backend=result['backend_code_commit'],C_reporting=result['code_commit'],manifest_identity=digest(manifest)),
    focused_verification=['Saved over-3000-character synthesis parses; exact complete correction request passes actual outgoing path',
        'Both reports imported without investigators; native fixture synthesis, two dispositions, mocked automatic C and incomplete B guard; receipt recovery',
        'Exact saved principal catalog feedback and original-event recovery; no request replay',
        'Saved C candidate ownership/scope check; lossless binary export and exact report-only dependency migration'],
    limitations=read(OUT/'C_material_review.json')['limitations'],remaining_blocker=None,V2_implemented=False,
    V2_entry='Limited tendon counts/routing/actuator layouts; then segment count with state/input/projection/initialization adaptation; then necessary representative combinations.')
assert facts['resources']['public_workflow_operations']<=512
atomic_json(OUT/'delivery_facts.json',facts)
print(json.dumps(dict(status=facts['status'],C=joint['status'],requests=17,tokens=usage['provider_reported_tokens'],operations=facts['resources']['public_workflow_operations'],elapsed_s=wall)))
