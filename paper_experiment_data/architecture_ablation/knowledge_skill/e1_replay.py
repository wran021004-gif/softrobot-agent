"""E1: immutable historical extraction and six decision-only provider sessions.

Never dispatches a Study, scientific operation, robot worker, or memory write.
The historical reference is explicitly an authored Core Plan, not an LLM run.
"""
import argparse
import copy
import csv
import datetime
import json
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORK = Path('D:/softrobot-agent')
HISTORY = WORK / 'paper_experiments/five_task_completion_20261113'
PREVIOUS = WORK / 'paper_experiment_data/architecture_ablation/reporter_on_off'
DATA = ROOT / 'figure_data'
CORE = WORK / '.worktrees/core-five-task-figure-eight-evaluator-20261113'
sys.path.insert(0, str(CORE))
import httpx
import jsonschema
from tools.research.agent import plan_schema
from tools.research.contracts import Plan, ExperienceQuery, EvidenceQuery
from tools.research.provider import credential, provider_schema

TASKS = {
    'T04': 'T04_figure_eight_tracking/T04_RUN_03',
    'T07': 'T07_C1_four_tendon',
}
CONDITIONS = {'K+S-': (True, False), 'K-S+': (False, True), 'K-S-': (False, False)}
SYSTEM = '''You are Softrobot-Agent Main at the supplied frozen research checkpoint.
Submit exactly one concrete next research decision through the existing research_plan
Core Plan/ResearchDecision interface. No proposed action will be executed in this session.
Use English. Explain in the Plan's hypothesis, interpretation, supporting_evidence,
expected_observation, weakening_observation, fixed_conditions, stopping_condition and
typed decision: (1) the key research question, (2) the next research route, (3) why,
(4) which supplied historical experience, if any, you use, (5) whether an existing
research method needs to be consulted, (6) the concrete proposed scientific action,
and (7) expected results and observations that would refute or weaken the hypothesis.
Use only the supplied task, family, registered interfaces, evidence and permitted
experience. All permitted archived experience read results are already delivered below;
you may read them again with experience_retrieve if necessary. Unavailable material
must remain unavailable; do not infer its contents or claim to have read it.
Give experience_disposition only for resources actually delivered to you. Do not invent
historical measurements. Current feasibility, acceptance and executable admission must
not be inferred from historical success or the presence of a schema. Respect the frozen
domain, current candidate state, research budgets and physical initial-state semantics.
Do not reward or prefer complexity for its own sake. A scoped diagnosis or generation
decision can be appropriate. State future procedural steps as plans, not completed work.
No mathematics, control optimization, structure generation, simulation, code execution,
Reporter or persistent memory is available. At most four Provider requests, ending at the
first schema-valid Plan. Do not mention experimental conditions or ablation factors.
Transport: return ONLY JSON {"tool":"research_plan","arguments":<Core Plan>} or
{"tool":"experience_retrieve","arguments":<Core ExperienceQuery>} or
{"tool":"evidence_read","arguments":<Core EvidenceQuery>}. No markdown or extra text.
These are the existing tool schemas:
'''


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def csv_rows(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(values[0]))
        writer.writeheader()
        writer.writerows({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in row.items()} for row in values)


def tools_for(study):
    actions = study['allowed_plan_actions']
    schema = plan_schema(actions, decision_required=True, study={})
    return [
        dict(type='function', function=dict(name='research_plan', description='Record the next proposed Core research Plan and end the session. No execution.', parameters=provider_schema(schema))),
        dict(type='function', function=dict(name='experience_retrieve', description='Read/search only the permitted immutable archived experience already supplied in this session. Disabled resources cannot be accessed.', parameters=provider_schema(ExperienceQuery.model_json_schema()))),
        dict(type='function', function=dict(name='evidence_read', description='Read only raw evidence at this checkpoint. Never reads experience, reports, future results or historical final outcomes.', parameters=provider_schema(EvidenceQuery.model_json_schema()))),
    ]


def messages_for(snapshot, condition):
    if condition == 'K+S+':
        k_on, s_on = True, True
    else:
        k_on, s_on = CONDITIONS[condition]
    available = [x for x in snapshot['experience_records'] if (k_on if x['role'] == 'knowledge' else s_on)]
    supplied = dict(checkpoint=snapshot['base_context'],
                    permitted_archived_experience_read_results=[x['archived_result'] for x in available],
                    experience_delivery='Exact archived read results, delivered once in this isolated context. Not new experience generation. An empty list means no experience is supplied.')
    return [dict(role='system', content=SYSTEM + json.dumps(snapshot['tools'], separators=(',', ':'))),
            dict(role='user', content=json.dumps(supplied, separators=(',', ':')))], available


def prepare():
    if (ROOT/'execution_schedule.json').exists():
        raise RuntimeError('Preparation already exists; do not overwrite frozen inputs.')
    DATA.mkdir(parents=True, exist_ok=True)
    final = read(HISTORY/'FINAL_RESULTS.json')
    provider_cfg = read(PREVIOUS/'replay_configuration.json')
    configuration = dict(provider=provider_cfg['provider'], credentials_reference=provider_cfg['credentials_reference'],
                         effective_reasoning='gateway_default_not_exposed', transport='existing_text_only_gateway',
                         provider_budget_per_session=4, reporter=False, new_main_sessions=6,
                         historical_reference='authored_surrogate_Core_Plan; formal_main_executed=false; provider_calls=0',
                         historical_matching='not a strictly matched four-cell LLM experiment',
                         enabled_delivery='Controlled delivery of exact previously read entries; optional reads restricted to the same permitted set.',
                         tokenizer='Reuse existing local o200k_base installation/cache; new estimates explicitly separated from actual usage.')
    write(ROOT/'replay_configuration.json', configuration)
    manifest = []
    schedule = []
    for task, directory in TASKS.items():
        folder = HISTORY/directory
        study = read(folder/'RESOLVED_STUDY_CONFIG.json')
        trace = [json.loads(line) for line in (folder/'STUDY_TRACE.jsonl').read_text(encoding='utf-8').splitlines()]
        projection = read(folder/'MAIN_REPLAY_INPUT/RESEARCH_INTENT_PROJECTION.json')
        first_plan = projection[0]
        read_events = [(i+1, e) for i, e in enumerate(trace) if e.get('tool_name') == 'experience_retrieve']
        assert read_events and trace[0]['new_candidate'] is False
        assert all(e['status'] == 'completed' for _, e in read_events)
        expected = read(folder/'ACTUAL_KNOWLEDGE_READS.json')
        experiences = []
        for line, event in read_events:
            assert len(event['output']['results']) == 1
            result = event['output']['results'][0]
            key = result['content_key']
            entry = read(HISTORY/'KNOWLEDGE_LIBRARY'/(key+'.json'))
            assert result['content'] == entry['content']
            experiences.append(dict(key=key, role=result['resource_role'], archived_result=result,
                                    source_file=(folder/'STUDY_TRACE.jsonl').as_posix(), line_1_based=line,
                                    event_id=event['event_id'], output_reference=event['output']['reference'],
                                    library_file=(HISTORY/'KNOWLEDGE_LIBRARY'/(key+'.json')).as_posix()))
        assert [x['key'] for x in experiences] == expected
        base_keys = ['canonical_task', 'family_space', 'topology_scope', 'task_conditions', 'analysis_protocol',
                     'confirmation', 'nmpc_limits', 'rl_limits', 'mathematical_methods', 'capabilities',
                     'candidate_initialization', 'scoring_window_s', 'registry_tools']
        base = {key: study[key] for key in base_keys if key in study}
        # Whitelist construction: no old messages, policies, experience indexes,
        # summaries, candidate producer outputs or end-of-study state are restored.
        base.update(task_id=task, current_candidate=None, current_structure=None,
                    current_mathematical_evidence=[], current_physical_evidence=[],
                    checkpoint_description='After immutable task/family preparation and before the first archived experience read and first scientific candidate.',
                    source_research_budget_remaining=copy.deepcopy(read_events[0][1]['budget_before']['remaining']),
                    frozen_scientific_budgets=study['budgets'],
                    replay_authorization={'provider_requests':4,'execute_research_actions':False},
                    original_execution_instructions=study['execution_instructions'])
        # Source provider_requests=0 describes the historical surrogate run,
        # separate from this explicitly authorized six-session decision replay.
        base['frozen_scientific_budgets'] = {k:v for k,v in base['frozen_scientific_budgets'].items() if k not in ['provider_requests','protected_provider_requests']}
        interface_schemas = {}
        if task == 'T04':
            for filename in ['T04-211-construct-native-frozen-reference-bank.json', 'T04-217-qualify-local-interior-bank-time-zero.json']:
                item = read(folder/'MAIN_REPLAY_INPUT'/filename)
                interface_schemas[item['request']['tool_id']] = item['input_schema']
        base['registered_initial_state_interface_schemas'] = interface_schemas
        snapshot = dict(task_id=task, base_context=base, experience_records=experiences,
                        tools=tools_for(study), source_directory=folder.as_posix(),
                        checkpoint_source=dict(trace_file=(folder/'STUDY_TRACE.jsonl').as_posix(),
                                               before_line_1_based=read_events[0][0],
                                               preparation_event=trace[0]),
                        reconstruction_status='No historical LLM prompt/session exists; reconstructed pre-read state from frozen configuration and preparation trace.',
                        reporter=False)
        # Verify all serialized base-context values exclude every entry's actual
        # content object and all current FULL acceptance output references.
        base_text=json.dumps(base, separators=(',', ':'))
        for entry in experiences:
            assert json.dumps(entry['archived_result']['content'], separators=(',', ':')) not in base_text
        task_final = next(x for x in final['tasks'] if x['task_id']==task)
        for case in task_final['cases']:
            assert case['reference']['artifact_id'] not in base_text
        write(ROOT/'snapshots'/f'{task}.json',snapshot)
        # Preserve original authored first Plan, separate from later real actions.
        historical = dict(task_id=task, condition='K+S+', source='historical_authored_Core_Plan_not_LLM',
                          formal_main_executed=False, provider_requests=0, decision=first_plan['formal_arguments'],
                          original_intent=first_plan['original_concise_intent'],
                          source_file=(folder/'MAIN_REPLAY_INPUT/RESEARCH_INTENT_PROJECTION.json').as_posix(), json_pointer='/0',
                          actual_experience_reads=experiences, subsequent_actual_actions=projection[1:],
                          final_result_file=(folder/'FINAL_RESULT.md').as_posix(),
                          final_results_file=(HISTORY/'FINAL_RESULTS.json').as_posix(), final_full_result=task_final,
                          comparability='Historical authored reference only; no previous Main model/reasoning/context or measured Main tokens exist. Subsequent actions and final acceptance are never sent to replays or the blind decision reviewer.')
        write(ROOT/'historical_reference'/f'{task}.json',historical)
        manifest.append(dict(task_id=task,checkpoint='pre_first_experience_read_pre_first_candidate',
                             snapshot_file=(ROOT/'snapshots'/f'{task}.json').as_posix(),
                             source_directory=folder.as_posix(), trace_before_line=read_events[0][0],
                             actual_knowledge_reads=[x['key'] for x in experiences if x['role']=='knowledge'],
                             actual_skill_reads=[x['key'] for x in experiences if x['role']=='skill'],
                             read_event_locators=[dict(source_file=x['source_file'],line_1_based=x['line_1_based'],event_id=x['event_id']) for x in experiences],
                             historical_plan_source=historical['source_file']+'#/0/formal_arguments',
                             historical_plan=historical['decision'], historical_actor='codex_surrogate_main',
                             historical_formal_main_executed=False, historical_provider_requests=0,
                             subsequent_actions_source=(ROOT/'historical_reference'/f'{task}.json').as_posix()+'#/subsequent_actual_actions',
                             full_result_file=historical['final_result_file'],full_results_source=historical['final_results_file'],
                             full_status=task_final['status'],independent_acceptance=[dict(condition_id=x['condition_id'],accepted=x['accepted'],reference=x['reference'],metrics=x['acceptance']['metrics']) for x in task_final['cases']],
                             matching_status='historical_reference_not_strictly_matched',context_reconstruction=snapshot['reconstruction_status']))
        # Balanced order, fixed before observing outputs.
        order=['K+S-','K-S-','K-S+'] if task=='T04' else ['K-S+','K-S-','K+S-']
        for condition in order:
            schedule.append(dict(task_id=task,condition=condition,session_id=str(uuid.uuid4()),ordinal=len(schedule)+1))
            messages,available=messages_for(snapshot,condition)
            input_folder=ROOT/'sessions'/schedule[-1]['session_id']
            write(input_folder/'initial_messages.json',messages)
            write(input_folder/'delivery_manifest.json',dict(task_id=task,condition=condition,
                   delivered_entry_keys=[e['key'] for e in available],delivery='exact_archived_read_results_preloaded',
                   old_message_history_restored=False,reporter=False,task_and_schemas_shared=True))
    csv_rows(DATA/'snapshot_manifest.csv',manifest)
    write(ROOT/'execution_schedule.json',schedule)
    write(ROOT/'matching_and_leakage_notes.json',dict(
        historical_reference_differences=['Both historical FULLs explicitly used codex_surrogate_main, zero Provider calls; authored Core Plans are not historical LLM outputs.',
          'No historical Main messages or reasoning setting exist. The same gpt-5.6-sol/default gateway configuration is used for all six new replays.',
          'Pre-read configuration reconstruction rather than recovery of an old LLM context. Current candidate/evidence are empty at this early checkpoint.',
          'Existing library entries are not semantically orthogonal: Knowledge can include procedures; Skills can cross-reference Knowledge. Entries are delivered unchanged, and disabled entries cannot be read.',
          'K+S+ is not rerun. Effects involving its score, including interaction, are descriptive and confounded by authored-vs-LLM origin.',
          'All proposed actions are recorded only. No robot/mathematical operation is called.'],
        controls=dict(fresh_isolated_messages=True,reporter=False,same_model_reasoning_within_replays=True,
                      same_task_candidate_evidence_schemas_within_task=True,same_provider_budget=4,
                      no_future_outcomes_delivered=True,no_disabled_entry_body_delivery=True),
        prohibition='No experiment is permitted to imply robot success-rate improvement or statistically established synergy.'))
    print(json.dumps(dict(prepared=True,new_sessions=6,historical_reference_sessions=0,
                          initial_message_bytes={x['session_id']:len(json.dumps(read(ROOT/'sessions'/x['session_id']/'initial_messages.json')).encode()) for x in schedule})),flush=True)


def run():
    cfg=read(ROOT/'replay_configuration.json');provider=cfg['provider']
    key=credential(provider,cfg['credentials_reference'])
    output=DATA/'decision_results.jsonl'
    done={x['session_id'] for x in [json.loads(l) for l in output.read_text(encoding='utf-8').splitlines()]} if output.exists() else set()
    with httpx.Client(timeout=provider['timeout_s'],trust_env=False,follow_redirects=False) as client:
        for item in read(ROOT/'execution_schedule.json'):
            if item['session_id'] in done:continue
            folder=ROOT/'sessions'/item['session_id']
            if list(folder.glob('request_*.json')):
                raise RuntimeError('An unresolved attempt exists; inspect it before sending anything else: '+str(folder))
            snapshot=read(ROOT/'snapshots'/f"{item['task_id']}.json")
            messages=read(folder/'initial_messages.json')
            _, available=messages_for(snapshot,item['condition'])
            allowed={e['key']:e for e in available}
            record=dict(**item,status='no_valid_decision',decision=None,requests=[],experience_reads=[],errors=[],
                        delivered_entry_keys=list(allowed),transport='text_serialized_existing_Core_Plan',effective_reasoning=cfg['effective_reasoning'],
                        new_studies=0,new_reporter_requests=0,new_mathematical_solves=0,new_physics_runs=0,new_candidates=0)
            started=time.perf_counter()
            print(json.dumps(dict(event='main_session_started',**item)),flush=True)
            for turn in range(1,5):
                wire=dict(model=provider['model'],stream=False,messages=messages)
                if len(json.dumps(wire).encode())>provider['model_capabilities']['max_request_bytes']:
                    raise RuntimeError('Request exceeds configured capacity before send.')
                write(folder/f'request_{turn}.json',wire)
                request=dict(turn=turn,sent_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
                start=time.perf_counter()
                try:
                    response=client.post(provider['base_url'].rstrip('/')+'/chat/completions',json=wire,headers={'Authorization':'Bearer '+key})
                    (folder/f'response_{turn}.txt').write_text(response.text,encoding='utf-8')
                    request.update(http_status=response.status_code,wall_s=time.perf_counter()-start)
                    record['requests'].append(request)
                    if response.status_code!=200:
                        record['status']='gateway_rejected_stop_all';write(folder/'result.json',record)
                        raise RuntimeError('Gateway rejected the request. Stop all sending; inspect saved response and repair only the incompatible transport parameter.')
                    body=response.json();request.update(usage=body.get('usage'),response_id=body.get('id'),model=body.get('model'))
                    message=body['choices'][0]['message'];messages.append(message)
                    content=message['content'].strip()
                    if content.startswith('```'):content='\n'.join(content.splitlines()[1:-1])
                    call=json.loads(content)
                    if 'action' in call:call={'tool':'research_plan','arguments':call}
                    name,args=call['tool'],call['arguments']
                    if name=='research_plan':
                        jsonschema.Draft202012Validator(snapshot['tools'][0]['function']['parameters']).validate(args)
                        Plan.model_validate(args)
                        assert args.get('decision') is not None
                        record.update(status='completed',decision=args,original_decision_text=message['content'])
                        break
                    if name=='experience_retrieve':
                        query=ExperienceQuery.model_validate(args)
                        if query.operation=='read':
                            entry_key=(query.entry_id or query.key or '')
                            if '@' not in entry_key:entry_key+='@'+str(query.revision or '1')
                            value=dict(status='available',results=[allowed[entry_key]['archived_result']]) if entry_key in allowed else dict(status='unavailable',reason='Entry is not permitted in this isolated session.')
                        else:
                            value=dict(status='available',results=[e['archived_result'] for e in available])
                        record['experience_reads'].append(dict(request=args,response=value))
                    elif name=='evidence_read':
                        EvidenceQuery.model_validate(args)
                        value=dict(status='unavailable',reason='No scientific candidate or raw execution artifact exists at this pre-candidate checkpoint. Task and family facts are already supplied; no experience or future artifact can be accessed through this reader.')
                    else:
                        value=dict(status='unavailable',reason='This session only records a research_plan; scientific execution is disabled.')
                    messages.append(dict(role='user',content=name+' result: '+json.dumps(value,separators=(',',':'))))
                except (json.JSONDecodeError,jsonschema.ValidationError,ValueError,KeyError) as exc:
                    record['errors'].append(type(exc).__name__+': '+str(exc)[:1500])
                    messages.append(dict(role='user',content='Invalid tool/Plan arguments: '+str(exc)[:1500]+'. Correct the existing Core Plan schema and submit research_plan; no research action is executed.'))
                write(folder/'result.json',record)
            record.update(wall_s=time.perf_counter()-started,provider_requests=len(record['requests']))
            write(folder/'result.json',record)
            if record['status']!='completed':raise RuntimeError('Four-request cap reached without a valid decision; do not create another session.')
            with output.open('a',encoding='utf-8') as stream:stream.write(json.dumps(record,ensure_ascii=False)+'\n')
            print(json.dumps(dict(event='main_session_completed',task_id=item['task_id'],condition=item['condition'],provider_requests=record['provider_requests'],action=record['decision']['action'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['prepare','run']);args=parser.parse_args()
    {'prepare':prepare,'run':run}[args.mode]()
