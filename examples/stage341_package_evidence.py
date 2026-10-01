"""Export compact Stage 3.41 facts; large plans/traces remain immutable local artifacts."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.platform_store import Store,plain
from tools.state_io import read,atomic_json,digest
from extensions.tendon_family.control_evidence import ControlEvidence,EvidenceQuery,ExecutionComparison
from examples.stage341_control_evidence_study import OUTPUT,SOURCE,EXECUTION

DEST=ROOT/'evidence/stage341_control_evidence_20261001'


def inventory(paths):
    return [dict(path=str(p.relative_to(ROOT)),size_bytes=p.stat().st_size,
        sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(set(paths)) if p.is_file()]


def offline():
    DEST.mkdir(parents=True,exist_ok=True)
    historical=ControlEvidence(Store(SOURCE));replay=read(OUTPUT/'recording_result.json')
    recording=ControlEvidence(Store(OUTPUT/'recording'));eid=replay['simulation']['execution_id']
    current=recording.resolve(eid);snapshots=recording.read_file(current,'control_snapshots.json')
    for name,reader,execution in [('historical_inspection',historical,EXECUTION),('recording_inspection',recording,eid)]:
        atomic_json(DEST/(name+'.json'),plain(reader.query(EvidenceQuery(execution_id=execution,operation='prediction',update_ids=[0,4,34]))))
    comparison=historical.compare(ExecutionComparison(baseline_execution_id=EXECUTION,variant_execution_id=eid,changed_factor='recording'),recording)
    atomic_json(DEST/'recording_comparison.json',comparison)
    local_path=next((ROOT/'runs/control_comparisons').glob('*/result.json'));local=read(local_path)
    validation=read(OUTPUT/'validation_result.json');vprofile=validation['profile']
    adopted=validation['adoption_gate_passed']
    correction=dict(changed_factor='horizon truncates at the official deadline; other recipe fields, physical problem and solve/feasibility limits unchanged',
        local_gate_passed=local['local_gate_passed'],adopted=adopted,
        local_shared_deadline_error_improvement_m=local['shared_deadline_error_improvement_m'],
        local_shared_tip_speeds_m_s=[r['metrics']['deadline']['tip_speed_m_s'] for r in local['rows']],
        fixed_design_terminal_error_m=vprofile['terminal_error_m'],baseline_terminal_error_m=.018349652058180982,
        fixed_design_official_reach=vprofile['official_task_success'],fixed_design_settling=vprofile['sampled_settling'],
        fixed_design_real_time=vprofile['real_time_demonstrated'],
        controller=read(OUTPUT/'validation_attempt.json')['frozen_input']['policy']['controller'] if adopted else current['configuration']['policy']['controller'],
        scope='One local snapshot pair and one fixed-design closed-loop comparison. No robustness or generalization claim.')
    overhead=[dict(update_id=s['update_id'],snapshot_id=s['snapshot_id'],capture_s=s['capture_wall_s'],
        bounded_verification_s=s['timing_s']['snapshot_verification'],callback_recording_s=s['timing_s']['callback_recording']) for s in snapshots]
    overhead_sum=sum(r['capture_s']+r['bounded_verification_s']+r['callback_recording_s'] for r in overhead)
    diagnosis=dict(schema_version='1.0.0',kind='deterministic_control_evidence_diagnosis',ready_for_live=True,
        source_execution=EXECUTION,recording_execution=eid,
        references=dict(historical_manifest=historical.resolve(EXECUTION)['manifest'],recording_manifest=current['manifest'],
            snapshots=current['files']['control_snapshots.json'],snapshot_ids=[s['snapshot_id'] for s in snapshots],
            local_comparison=str(local_path.relative_to(ROOT)),fixed_design_execution=validation['simulation']['execution_id']),
        observations=[
            'Stage 3.40 officially missed reach: 18.349652 mm versus 10 mm. It selected 26 noninitialization plans and 9 initialization plans; no constant-tension-throughout claim applies.',
            'At t=0.00 the retained initialization is feasible. Returned objective 5.6701 versus 27.9769 is lower but scaled violation 0.000385886 exceeds 1e-5; useful feasible improvement was not delivered at that update.',
            'At t=0.04 selected objective 3.65432 versus initialization 16.43270 is independently feasible (2.35932e-6). Predicted error 7.66761 mm at t=0.14 accompanies 0.35877 m/s speed. The official t=0.35 deadline lies outside this horizon.',
            'At t=0.34 selected initialization predicts 15.930070 mm error and 0.15258 m/s at t=0.35. Its horizon ends at t=0.44 with 13.693525 mm error. Returned plan predicts 8.336734 mm at t=0.44, but remains infeasible (0.017215765) and predicts 15.188747 mm at the actual deadline.',
            'The aligned t=0.34 to 0.35 prediction uses the actual applied input. The Euclidean tip discrepancy is 3.308744 mm; predicted target error 15.930070 mm versus actual 18.349652 mm. These are distinct norms, not additive error components.',
            'Late actual error falls by 5.817383 mm over 0.30 to 0.35 s while terminal speed is 0.15568 m/s; sampled settling fails. High speed alone does not prove that inadequate braking caused the reach miss.',
            'No applied force-bound violation and no historical upper-force proximity were recorded. One early optimized input was near zero. This does not rule out unilateral-input limitations for other useful plans.',
            'The frozen affine design score omits nonlinear closed-loop progress and braking and has zero straight-start world-x input row. Its approximately 2 mm local bound is advisory under its own witness, not contradicted as a mathematical bound by backend error.'
        ],supported_interpretation=[
            'Both selected-plan deadline insufficiency and same-input prediction discrepancy are observed; prediction mismatch alone cannot explain the failure because the selected plan already predicts a miss.',
            'Feasible improvement is sometimes found, but not at all retained updates within the unchanged stopping limits. Infeasible lower objectives cannot be treated as executable successes.',
            'The tested deadline truncation improves the shared local deadline error by 3.027269 mm, while increasing predicted speed and approaching upper force bounds; the tradeoff is explicit.',
            'Derivative evaluation dominates portions of solve time in retained statistics. That locates computation cost without identifying the cause of terminal error.'
        ],unresolved=[
            'Relative causal contributions of state projection, reduced-model dynamics and integration error in the one-step discrepancy.',
            'Whether longer-horizon or better-conditioned feasible search could find better plans under the same time budget.',
            'Braking/settling performance, input limitations across alternative plans, and robustness across designs remain unproven.',
            'A ranking improvement of the affine design score has not been tested; controller evidence is not a design-ranking validation.'
        ],correction=correction,
        recording_overhead=dict(measured_components=overhead,total_measured_s=overhead_sum,
            limitation='Direct measured capture, bounded verification and callback overhead only; warm-horizon copy and serialization were not separately timed. Cross-run timing difference is not an overhead estimate.',
            actual_command_artifact_identical=historical.resolve(EXECUTION)['files']['actual_commands.json']==current['files']['actual_commands.json']),
        replay_reporting=dict(status=replay['reporting_status'],rejections=replay['rejections'],
            interpretation='Sealed arrays support read-only inspection; no official replay evaluation is claimed. No reset, replacement replay or rejection bypass.'),
        usage=dict(recording_replays=1,local_nmpc_solves=read(ROOT/'runs/control_comparisons/usage.json')['local_solves'],
            local_preparation_solving_s=read(ROOT/'runs/control_comparisons/usage.json')['wall_s'],fixed_design_validations=1,
            offline_charged_and_local_s=replay['usage']['wall_s']+validation['usage']['wall_s']+read(ROOT/'runs/control_comparisons/usage.json')['wall_s'],workers=0),
        next_discriminating_comparison='Use the fresh autonomous workflow to test whether an eligible exact mathematical proposal reaches under the frozen adopted controller. If reach remains unmet, separate projected-start offset from one-step integration/dynamics discrepancy using saved input/state references before another physical search.')
    atomic_json(DEST/'diagnosis.json',diagnosis)
    for name,value in [('local_comparison',local),('recording_result',replay),('validation_result',validation),
        ('validation_comparison',read(OUTPUT/'validation_comparison.json')),('local_usage',read(ROOT/'runs/control_comparisons/usage.json')),
        ('validation_protocol',read(OUTPUT/'validation_attempt.json')),('recording_protocol',read(OUTPUT/'recording_attempt.json'))]:
        atomic_json(DEST/(name+'.json'),value)
    paths=list(OUTPUT.rglob('*.sqlite'))+list(OUTPUT.glob('*.json'))+list(OUTPUT.glob('*/sessions/*/executions/*/backend/*'))
    paths+=list(local_path.parent.glob('*'))+[ROOT/'runs/stage341_recording_console.log',ROOT/'runs/stage341_local_console.log',ROOT/'runs/stage341_validation_console.log']
    atomic_json(DEST/'raw_artifacts.json',dict(remotely_available=False,files=inventory(paths)))
    print('OFFLINE_EXPORTED adopted='+str(adopted),flush=True)


def live():
    from examples.stage341_autonomous_experiment import OUTPUT as source,export
    from tools.platform_host import Host
    host=Host(source,read(source/'freeze_manifest.json')['run_id']);outcome=export(host)
    audit=read(source/'stage341_audit.json');behavior=read(source/'behavior_audit.json')
    decisions=[dict(request_id=a['request_id'],decision=a.get('decision'),receipt=a.get('receipt')) for a in behavior['actions']]
    for name,value in [('live_outcome',outcome),('live_audit',audit),('live_decisions',dict(run_id=host.run_id,actions=decisions)),
        ('live_freeze_manifest',read(source/'freeze_manifest.json')),('live_prelaunch_verification',read(source/'prelaunch_verification.json')),
        ('live_frozen_input',read(source/'frozen_input.json')),('live_provider_configuration',read(source/'provider_configuration.json'))]:
        atomic_json(DEST/(name+'.json'),value)
    candidates=[]
    for row in audit['evaluated_candidates']:
        facts=row['candidate_facts'];cid=facts['candidate_id']
        build=next(n for n in audit['route_nodes'] if n['action']=='build' and host.store.artifact(n['result'])['candidate_id']==cid)
        built=host.store.artifact(build['result']);prov=built.get('proposal_provenance')
        optimizer=host.store.artifact(prov['optimizer_result']) if prov else {}
        selected=next((v for v in optimizer.get('evaluations',[]) if v['candidate_id']==prov['optimizer_candidate_id']),None) if prov else None
        candidates.append(dict(candidate_facts=facts,build_result=build['result'],proposal_provenance=prov,
            selected_evaluated_row=selected,optimizer_limitations=optimizer.get('limitations'),
            factual_result=row['factual_result'],profile=row['profile_report_summary']))
    atomic_json(DEST/'live_candidate_provenance.json',dict(candidates=candidates))
    paths=[source/'platform.sqlite']+list(source.glob('*.json'))+list(source.glob('sessions/*/executions/*/backend/*'))
    atomic_json(DEST/'live_raw_artifacts.json',dict(remotely_available=False,files=inventory(paths)))
    print('LIVE_EXPORTED',outcome['model_authored_finish'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['offline','live']);args=parser.parse_args()
    offline() if args.action=='offline' else live()
