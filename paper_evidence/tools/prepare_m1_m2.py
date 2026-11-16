"""Bounded T07 paired-design audit and exact replay preparation; no physics run."""
import json
import sqlite3
from pathlib import Path
from build_evidence import *


def prepare():
    selected=source(A,MASTER+'SOURCE_DATA/SELECTED_RESEARCH_EVENTS.json')
    event=next(e for e in selected if e['stage_id']=='T07-074')
    trace_path=Path(event['decision']['source'])
    trace=[json.loads(s) for s in trace_path.read_text('utf-8-sig').splitlines() if s.strip()]
    events={e['event_id']:e for e in trace}
    gen1=events['T07-074-test-original-radius-boundary-on-best-root']
    root_trial=events['T07-060-test-isotropic-root-mechanism']
    # Actual stored design records, not a reconstruction from labels.
    db=Path(gen1['store_id'])
    refs=['0a8368b21bd33a1902f18765b7afbd505b53583812697087e8e225c400a402a3',
          '5b531f7c25e21d2146837681b4d0f95d505720cd2b94fe6b4f986a2cd40ee67e']
    designs=[]
    with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as conn:
        for role,ref in zip(['d0','d1'],refs):
            row=conn.execute('select body from artifacts where id=?',(ref,)).fetchone()
            body=json.loads(row[0]);designs.append(dict(role=role,original_candidate_id=ref,body=body))
    # Inspect configuration shape explicitly before declaring channel compatibility.
    fields=[]
    for d in designs:
        b=d['body'];data=b.get('data',b)
        fields.append(dict(role=d['role'],candidate_id=d['original_candidate_id'],keys=list(data)))
    evo=[x for x in source(A,MASTER+'CANDIDATE_EVOLUTION.csv') if x['task_id']=='T07']
    d0=next(x for x in evo if refs[0] in x['candidate_artifact_refs'])
    d1=next(x for x in evo if refs[1] in x['candidate_artifact_refs'])
    channels=[]
    for d in designs:
        b=d['body'].get('data',d['body'])
        # Candidate body may wrap the resolved configuration.
        resolved=b['resolved_parameters']
        channels.append(dict(actuator_order=resolved['actuator_order'],tendon_order=resolved['tendon_order'],
            actuators=resolved['actuators'],task_channels=b['configuration']['robot']['channels']))
    conditions=['M1_A','M1_B','M1_C','M5']
    protocols=source(A,MASTER+'SOURCE_DATA/PROTOCOLS.json')['T07']
    requests=[]
    for e in trace:
        if e.get('kind') not in ['tool_call','native_tool_call']:continue
        args=original_arguments(e)
        if e.get('event_id') in ['T07-061-adapt-current-A-control-to-root-trial','T07-062-native-isotropic-root-A',
                                 'T07-075-adapt-best-root-A-to-boundary-radius','T07-076-native-boundary-radius-best-root-A',
                                 'T07-077-independent-boundary-radius-root-A']:
            requests.append(dict(event_id=e['event_id'],tool=e['tool_name'],arguments=args,
                                 result_reference=portable(str(trace_path))+'#'+e['event_id']))
    plan=dict(protocol_id='T07-paired-M1-M2-preparation-20261116',status='PREPARED_NOT_EXECUTED',
        task_id='T07',source_store=portable(str(db)),
        d0_candidate_id=refs[0],d1_candidate_id=refs[1],
        d0_configuration_record='task_metrics/candidate_evolution.csv#candidate_artifact_refs contains '+refs[0],
        d1_configuration_record='task_metrics/candidate_evolution.csv#candidate_artifact_refs contains '+refs[1],stored_candidate_body_keys=fields,
        same_tendon_count=d0['tendon_count']==d1['tendon_count']=='4',same_segment_count=d0['segment_count']==d1['segment_count']=='2',
        required_conditions=conditions,original_protocol_reference=locator(A,MASTER+'SOURCE_DATA/PROTOCOLS.json','#/T07'),
        original_channel_observations=channels,
        same_named_channel_contract=channels[0]==channels[1],
        structure_difference='ellipse root to 8 mm circular root; legal routing radius 14.1 mm to 14 mm; lengths 158.5/109 mm unchanged between selected d0 and d1',
        three_modes=[dict(mode='A',design='d0',control='condition-specific U0_star'),
                     dict(mode='B',design='d1',control='identical condition-specific U0_star; no re-optimization'),
                     dict(mode='C',design='d1',control='condition-specific U1_star after bounded re-optimization')],
        matching_rules=['original named channels must be identical in order, units and physical meaning; no arbitrary mapping',
                        'same zero generalized state and speed per original condition, initial actuator semantics, loads, timing, integrator, timestep and thresholds',
                        'all four required conditions on each shared design; no condition-wise morphology change',
                        'a diagnostic optimization or input adaptation is not independent full replay'],
        execution_recipe=[
          'Open the source Store read-only; create an isolated new experiment Store with the same original Core/runtime and original T07 protocol.',
          'Recreate exactly d0 and d1 from the stored configurations. Compare actual model segment geometry, ordered tendons/actuators, initialized qpos/qvel, actuator units and limits.',
          'Resolve a complete candidate-owned U0_star for each of M1_A/M1_B/M1_C/M5. Existing partial/local optimizer outcomes cannot substitute. If a complete d0 result/source is absent, run one bounded original native optimization for that condition on d0, preserving failure.',
          'A: independently replay d0 with U0_star from the identical original initial state. Reuse only an exact same-contract complete replay.',
          'B: use the existing initialize_control source+parent mechanism with identity named channels to copy tension values only onto d1; independently replay the full original condition, without any optimization.',
          'C: optimize on d1 starting from the same U0_star under the original bounded native optimizer settings, then independently replay. Exact historical final d1 controls/evaluations can serve as a separately marked existing reference, not a matched new initialization experiment.',
          'Report all failure/qualification outcomes. Do not launch further structural search or change a threshold. Stop at two designs × three modes × four required conditions.'
        ],
        missing_items=[
          'A matched all-four-condition complete d0 U0_star set and independent d0 acceptance has not been established by this preparation.',
          'B fixed-input complete independent d1 replays are absent from the final tables; recorded adaptations were followed by re-optimization.',
          'The complete control/initial-state bindings must be resolved via the exact saved Store records before executing. No d0 source is inferred from a local candidate label.',
          'Exact initial state and physical solver settings need equality checks for each A/B/C condition; no matched physical result is claimed here.'
        ],
        original_request_templates=requests,
        requested_metrics=['normalized constraint violation','terminal/holding errors','tension extrema','tendon speed and stroke','control effort only if complete recorded input exists','physical evaluation cost'],
        source_reference=portable(str(trace_path)))
    write_json('supplementary_experiments/m1_m2/executable_plan.json',plan)
    rows=[]
    for condition in conditions:
        for mode in ['A','B','C']:
            rows.append(dict(protocol_id=plan['protocol_id'],task_id='T07',study_id='T07-M1M2-paired',condition_id=condition,
                comparison_mode=mode,design='d0' if mode=='A' else 'd1',control='U1_star' if mode=='C' else 'U0_star',
                evaluation_status='NOT_EXECUTED',normalized_constraint_violation=UNKNOWN,terminal_error_m=UNKNOWN,
                holding_error_m=UNKNOWN,tension_max_n=UNKNOWN,tendon_speed_m_s=UNKNOWN,tendon_stroke_m=UNKNOWN,
                control_effort=UNKNOWN,physical_evaluation_cost=UNKNOWN,
                source_reference='paper_evidence/supplementary_experiments/m1_m2/executable_plan.json',
                missing_reason='Matched complete input/initial-state replay bindings must first be established; historical reoptimized results are a separate reference.'))
    write_csv('task_metrics/m1_m2_comparison.csv',rows)
    write_csv('figure_data/fig04_m1_m2_comparison.csv',rows)
    print(json.dumps(dict(status=plan['status'],same_tendon_count=plan['same_tendon_count'],same_segment_count=plan['same_segment_count'],rows=len(rows))))


if __name__=='__main__':prepare()
