"""Two frozen paired decisions, using production Plan and accounted LiveBoundary.

Only Provider I/O runs, optionally accounted in an authorized formal Study.
No scientific dispatch or Reporter.
Raw wire/body and the existing provider ledger live in ignored runs/.
"""
import argparse
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
from types import SimpleNamespace

import httpx
from schemas.platform import ProjectConfig
from tools.platform_store import Store, plain
from tools.research.agent import LiveBoundary, load_credential, plan_schema, record
from tools.research.contracts import Plan
from tools.research.state import update
from tools.research.task_constraints import METHOD_MEANINGS
from tools.state_io import atomic_json, read

ROOT = Path(__file__).resolve().parents[2]
CASES = Path(__file__).with_name('agent_math_decision_cases.json')
OUT = ROOT / 'runs/agent-math-decision-probe-protocol-fixed'
SUMMARY = ROOT / 'evidence/agent_math_decision_probe/summary.json'
ARMS = ('baseline', 'evidence')
AUTHORIZATION = (
    'User attachment 4a906846-0f46-433c-8bf8-e0d482a4506e, sections 6 and 14: '
    'authorizes at most 8 real main Agent Provider requests with original egress admission; '
    'only necessary frozen task, mathematical scalars, physical diagnostics and evidence summaries; '
    'same C1 Provider/model. No scientific workers or Reporter requests.'
    ' Supplemental user instruction on 2026-10-25 authorizes repairing unexpected '
    'protocol errors and rerunning; initial requests do not consume the new eight-request '
    'comparison allowance, but their actual billed usage remains separately recorded.'
)
INSTRUCTIONS = (
    'You are the Softrobot research decision Agent. Choose the next scientific question '
    'and method autonomously from the frozen task, legal domain, engineering defaults, '
    'method descriptions, costs and visible evidence. Keep mathematical scope, numerical '
    'status, physical observation and independent task acceptance distinct. '
    'This is a read-only decision probe. In EVERY independent evaluation turn submit '
    'exactly one NEW research_plan tool call using the production Plan/ResearchDecision '
    'contract. An earlier turn\'s Plan never satisfies the current turn. Use action=diagnose '
    'to DESCRIBE any chosen scientific method, or stop; no payload is dispatched. '
    'Put the current question and at least two competing mechanisms with evidence IDs in '
    'hypothesis; the next specific experiment, measured quantities and outcome branches '
    'in expected_observation/interpretation; state fixed_conditions, a falsifying '
    'weakening_observation, stopping_condition, requested_budget with its unit and total '
    'cost justification. selected_method names your actual chosen method. Cite only '
    'visible source/fact IDs in prose; supporting_evidence may be empty because these '
    'excerpts are not new registered Store artifacts. Do not invent artifact references. '
    'No hidden file reads or tools are available. Scheduled next-round observations are '
    'historical and independent of your choice, not results of executing your proposal. '
    'Emit only the properties advertised in the schema, and only ResearchDecision '
    'properties inside decision; do not add explanatory or execution-only keys. '
    'When they arrive, explicitly reassess the earlier hypotheses and explain what '
    'changes, what remains unknown and the next discriminating action. Respond in Chinese.'
)


def decision_schema():
    """Project the existing Plan to its descriptive decision fields, without a new contract."""
    schema = plan_schema(['diagnose', 'stop'], decision_required=True)
    fields = {'action', 'hypothesis', 'decision', 'supporting_evidence', 'expected_observation',
              'weakening_observation', 'fixed_conditions', 'stopping_condition', 'interpretation'}
    schema['properties'] = {k: v for k, v in schema['properties'].items() if k in fields}
    schema['$defs'] = {k: v for k, v in schema['$defs'].items() if k in ('ResearchDecision', 'EvidenceRef')}
    schema.pop('allOf')  # Payload ownership branches are unused by descriptive diagnose/stop.
    return schema


def packet(data, case, arm, turn):
    scenario = data['cases'][case]
    value = {k: deepcopy(data[k]) for k in ('task', 'engineering_prior', 'costs')}
    value.update(question=scenario['question'], proposed_next_action_budget=scenario['proposed_next_action_budget'],
                 visible_facts=deepcopy(scenario['common']), diagnostic_evidence=[])
    if arm == 'evidence':
        value['diagnostic_evidence'] = deepcopy(scenario['evidence'])
    if turn == 2:
        value['new_observations'] = deepcopy(scenario['round2'])
    return value


def wire(provider, data, case, arm, turn, history=()):
    # The method descriptions are the actual production catalog, not scoring hints.
    content = packet(data, case, arm, turn)
    prior = [call for message in history for call in message.get('tool_calls', [])
             if call['function']['name'] == 'research_plan']
    content['evaluation_turn'] = dict(turn_id=f'{case}:turn-{turn}', turn=turn,
        previous_plan_tool_ids=[call['id'] for call in prior],
        question_to_reassess=content['question'],
        submission='Submit exactly one NEW research_plan for THIS turn; previous Plans remain context only.')
    content['mathematical_methods'] = METHOD_MEANINGS
    return dict(model=provider['model'], max_tokens=provider['max_tokens'],
                reasoning_effort=provider['reasoning_effort'], thinking={'type': provider['thinking']},
                stream=False, tool_choice='auto',
                tools=[dict(type='function', function=dict(name='research_plan',
                    description='Record one production research decision only; no scientific action executes.',
                    parameters=decision_schema()))],
                messages=[dict(role='system', content=INSTRUCTIONS), *deepcopy(history),
                          dict(role='user', content=json.dumps(content, ensure_ascii=False))])


def parse(message):
    calls = message.get('tool_calls') or []
    if len(calls) != 1 or calls[0]['function']['name'] != 'research_plan':
        raise ValueError('ONE_RESEARCH_PLAN_REQUIRED')
    plan = Plan.model_validate_json(calls[0]['function']['arguments'])
    if plan.action not in ('diagnose', 'stop') or plan.decision is None:
        raise ValueError('READ_ONLY_PLAN_WITH_DECISION_REQUIRED')
    return plain(plan)


def freeze(out=OUT,*,cases_path=CASES,provider=None,authorization=None):
    if out.exists():
        raise ValueError('EXISTING_PROBE_DIRECTORY_NO_REFREEZE_OR_AUTOMATIC_RETRY')
    data = read(cases_path)
    authorization=authorization or (AUTHORIZATION if Path(cases_path).resolve()==CASES.resolve() else data.get('authorization','PENDING_EXPLICIT_APPROVAL'))
    provider = provider or read(ROOT / 'evidence/mujoco_c1_autonomous/configuration.json')['runtime']['provider']
    ceiling=4*len(data['cases'])
    cohort='protocol-fixed' if Path(cases_path).resolve()==CASES.resolve() else data['version']
    out.mkdir(parents=True)
    frozen = dict(cohort=cohort, cases=data, provider=provider, instructions=INSTRUCTIONS,
                  authorization=authorization, request_ceiling=ceiling, reporter_requests=0,cases_source=str(Path(cases_path).resolve()),
                  scientific_execution='disabled; proposals only')
    atomic_json(out / 'frozen.json', frozen)
    for case in data['cases']:
        for arm in ARMS:
            for turn in (1, 2):
                atomic_json(out / f'{case}-{arm}-{turn}-input.json',
                            wire(provider, data, case, arm, turn))
    summary = dict(status='B1_frozen_provider_zero', cohort=cohort,
                   prior_cohort='evidence/agent_math_decision_probe/initial_summary.json' if cohort=='protocol-fixed' else None,
                   baseline=data.get('baseline_commit'),
                   provider=provider, authorization=authorization, request_ceiling=ceiling,
                   actual_requests=0, reporter_requests=0, physics_steps=0,
                   scientific_workers=0, formal_studies=0, cases=data['cases'],
                   sources=data['sources_offline_only'], rubric=data['rubric_offline_only'],
                   results=[], manual_review=None, money=None)
    atomic_json(SUMMARY, summary)
    return frozen


def provider_usage(host):
    # r3_response has two persistence events for one HTTP response; count request IDs.
    responses = {}
    sends = [e for e in host.store.events(host.run_id) if e['kind'] == 'r3_request']
    for e in host.store.events(host.run_id):
        if e['kind'] == 'r3_response':
            responses[e['request_id']] = host.store.artifact(e['outputs'][0])
    usages = [r.get('usage') for r in responses.values()]
    totals = {key: sum(u[key] for u in usages) if usages and all(u and key in u for u in usages) else None
              for key in ('prompt_tokens', 'completion_tokens', 'total_tokens', 'prompt_cache_hit_tokens',
                          'prompt_cache_miss_tokens')}
    reasoning = [(u or {}).get('completion_tokens_details', {}).get('reasoning_tokens') for u in usages]
    totals['reasoning_tokens'] = sum(reasoning) if reasoning and all(v is not None for v in reasoning) else None
    return dict(actual_requests=len(sends), confirmed_responses=len(responses), usage=totals,
                money=None, provider_ledger=host.store.remaining())


C3_ARMS=('control','treatment')
C3_ROOTS=dict(control=ROOT.parent/'b3-r0-decision-efficiency',treatment=ROOT)
C3_COMMITS=dict(control='c153e1731ae0925e756467f75a783b28abce2873',treatment='5d73965e1ed52afed689a182976064a2af80ffac')
C3_SCOPE=(
    'C3 is an isolated read-only decision experiment. The packet is a frozen historical '
    'boundary, not a live Study. You may evidence_read first or propose your next action '
    'with research_plan/research_analysis. No proposal, including local_diagnostic, '
    'executes science here; no new physical/mathematical result will be supplied. '
    'Choose the method freely, considering the task violation, competing explanations, '
    'what different outcomes would change, evidence scope and real cost. State unknowns. '
    'There are at most two Provider turns for this case; use the advertised production '
    'contracts. No hidden context retrieval or Reporter is available. Respond in Chinese.'
)


def c3_boundary(case,arm,output,tool_input=None,*,source=None,roots=None):
    """The same small archive audit runs against either frozen production checkout."""
    import subprocess,sys
    script=Path(__file__).with_name('c3_readiness_audit.py')
    command=[sys.executable,'-c',
        'import runpy,sys;sys.path.insert(0,".");p=sys.argv.pop(1);runpy.run_path(p,run_name="__main__")',
        str(script),'--decision-efficiency',case,'--evidence-root',str(ROOT),'--output',str(output)]
    if tool_input:command+=['--tool-input',str(tool_input)]
    if source:command+=['--source-folder',source[0],'--source-sequence',str(source[1])]
    subprocess.run(command,cwd=(roots or C3_ROOTS)[arm],check=True)


def c3_freeze(out):
    import subprocess
    if out.exists():raise ValueError('EXISTING_C3_DIRECTORY_NO_REFREEZE')
    for arm,root in C3_ROOTS.items():
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
        # The C3 delivery commit may add tests/reports on top of Treatment.
        if arm=='control' and head!=C3_COMMITS[arm]:raise ValueError('C3_FROZEN_COMMIT_MISMATCH: '+arm)
        subprocess.run(['git','merge-base','--is-ancestor',C3_COMMITS[arm],head],cwd=root,check=True)
        subprocess.run(['git','diff','--quiet',C3_COMMITS[arm],'--','tools','schemas','extensions','configs','tasks'],cwd=root,check=True)
    out.mkdir(parents=True)
    provider=read(ROOT/'evidence/b3_r1_history_assisted_050/configuration.json')['runtime']['provider']
    rows=[]
    for case in ('A','B','C'):
        for arm in C3_ARMS:
            path=out/f'{case}-{arm}.json';c3_boundary(case,arm,path)
            row=read(path)
            if not (row['state_unchanged'] and row['final_r1_refs_absent']):raise ValueError('C3_TEMPORAL_AUDIT_FAILED')
            if any(q['status']=='failed' and not q['historical_read_query'] for q in row['query_checks']):raise ValueError('C3_ADVERTISED_QUERY_FAILED: '+str(path))
            rows.append({k:row[k] for k in ('case','sizes','source_state','preparation','event_boundary','methods','error_replay','query_checks','final_r1_refs_absent','state_unchanged')}|dict(arm=arm))
        left,right=[read(out/f'{case}-{a}.json') for a in C3_ARMS]
        if left['source_state']!=right['source_state'] or set(left['methods'])!=set(right['methods']):
            raise ValueError('C3_PAIR_EVIDENCE_OR_METHOD_MISMATCH')
    authorization=('User C3 attachment 80d34de2-8762-4fad-aca6-6d5ebbacf361, sections 2/5/10: '
        'at most 12 real Provider requests, independent ledger, original DeepSeek configuration; '
        'only necessary frozen scientific task/evidence/tools, no unrelated private data. '
        'Zero formal Study, Reporter, scientific worker, training or physical evaluation. '
        'Commit/push authorized; no use of R1 remaining budget. No retries or alternate models.')
    atomic_json(out/'frozen.json',dict(provider=provider,scope=C3_SCOPE,commits=C3_COMMITS,
        authorization=authorization,request_ceiling=12,offline_passed=True,offline=rows,
        order=[(c,a) for c,arms in [('A',C3_ARMS),('B',C3_ARMS[::-1]),('C',C3_ARMS)] for a in arms]))
    return rows


async def c3_live(out,followup=False):
    """Reuse the original probe's transport/ledger; two bounded rounds, no dispatch."""
    frozen=read(out/'frozen.json')
    if not frozen['offline_passed'] or frozen['scope']!=C3_SCOPE:raise ValueError('C3_OFFLINE_GATE_REQUIRED')
    summary_path=out/'summary.json'
    if summary_path.exists() and not followup:raise ValueError('C3_NO_AUTOMATIC_RESEND')
    if followup:
        summary=read(summary_path)
        if (summary['status']!='first_six_complete' or summary['actual_requests']!=6 or
                summary['confirmed_responses']!=6 or any(r['turn']==2 or r.get('error') for r in summary['results'])):
            raise ValueError('C3_FOLLOWUP_REQUIRES_EXACT_COMPLETED_FIRST_SIX')
        host=SimpleNamespace(store=Store(out/'provider'),run_id='c3-agent-decision-efficiency')
    else:
        if (out/'provider/platform.sqlite').exists():raise ValueError('C3_EXISTING_LEDGER_NO_RESEND')
        host=SimpleNamespace(store=Store(out/'provider'),run_id='c3-agent-decision-efficiency')
        project=ProjectConfig(project_id=host.run_id,grant_id=host.run_id+'-12',authorization_source=frozen['authorization'],
            budget=dict(model_calls=12,tool_calls=0,backend_solves=0,worker_calls=0,wall_s=None),exclusive_resources={'provider_request':1})
        host.store.create(project)
        host.store.create_session(dict(input=dict(run_id=host.run_id,policy=dict(budget=plain(project.budget))),purpose='isolated read-only C3 Provider accounting; not a Study'))
        update(host,pilot=dict(provider=frozen['provider'],live_model_requests=0))
        record(host,'provider_egress_authorization',dict(user_approval=frozen['authorization'],endpoint=frozen['provider']['base_url']+'/chat/completions',ceiling=12))
        summary=dict(status='running',results=[],scientific_workers=0,formal_studies=0,physics_steps=0,reporter_requests=0)
    provider=frozen['provider'];boundary=LiveBoundary(host);turn=2 if followup else 1
    try:
        for case,arm in (reversed(frozen['order']) if followup else frozen['order']):
            base=read(out/f'{case}-{arm}.json');wire=deepcopy(base['handoff_wire'])
            wire['tools']=[t for t in wire['tools'] if t['function']['name'] in ('research_plan','evidence_read','research_analysis')]
            wire['messages'][0]['content']+='\n\n'+C3_SCOPE
            if followup:
                prior=read(out/f'{case}-{arm}-1-request.json');body=read(out/f'{case}-{arm}-1-response.json')
                feedback=read(out/f'{case}-{arm}-1-feedback.json')
                wire['messages']=prior['messages']+[body['choices'][0]['message']]+[
                    dict(role='tool',tool_call_id=r['tool_call_id'],content=json.dumps(r,ensure_ascii=False)) for r in feedback]
                wire['messages'].append(dict(role='user',content='This is the second and final C3 turn. Reassess the actual read-only feedback and submit your next decision. No scientific proposal was executed.'))
            # Provider configuration is identical to the original R1 model, both arms.
            wire.update(model=provider['model'],max_tokens=provider['max_tokens'],reasoning_effort=provider['reasoning_effort'],thinking={'type':provider['thinking']},stream=False,tool_choice='auto')
            label=f'{case}-{arm}-{turn}';atomic_json(out/f'{label}-request.json',wire)
            result=dict(case=case,arm=arm,turn=turn,scientific_execution='not_dispatched',input_bytes=len(httpx.Request('POST','https://offline.invalid',json=wire).content))
            summary['results'].append(result)
            try:
                response=await boundary.handle_async_request(httpx.Request('POST',provider['base_url'].rstrip('/')+'/chat/completions',json=wire,
                    headers={'Authorization':'Bearer '+os.environ['DEEPSEEK_API_KEY']},extensions={'timeout':dict(connect=30,read=provider['timeout_s'],write=30,pool=30)}))
                response.raise_for_status();body=response.json();atomic_json(out/f'{label}-response.json',body)
                calls=body['choices'][0]['message'].get('tool_calls') or []
                result.update(request_id=boundary.last_request,usage=body.get('usage'),finish_reason=body['choices'][0].get('finish_reason'),tool_calls=len(calls),
                    evidence_reads=sum(c['function']['name']=='evidence_read' for c in calls))
                atomic_json(out/f'{label}-tools.json',calls)
                c3_boundary(case,arm,out/f'{label}-feedback.json',out/f'{label}-tools.json')
                result['feedback']=read(out/f'{label}-feedback.json')
                result['message']=body['choices'][0]['message']
                boundary.consumed()
                print(label+': '+str(len(calls))+' tool calls',flush=True)
            except BaseException as exc:
                result.update(request_id=boundary.last_request,error=type(exc).__name__+': '+str(exc));raise
            finally:
                summary.update(provider_usage(host));summary['status']='partial'
                atomic_json(summary_path,summary)
        summary['status']='second_round_complete' if followup else 'first_six_complete'
    finally:
        await boundary.aclose();atomic_json(summary_path,summary)
    return summary


def c32_freeze(out):
    """Additional saved boundaries using the C3 archive/projection, with no live entry point."""
    import subprocess
    from tools.research.provider_context import official_tokenizer
    protocol=read(Path(__file__).with_name('fixtures')/'c32_scientific_decision_protocol.json')
    roots={arm:ROOT.parent/protocol['checkouts'][arm] for arm in C3_ARMS}
    if out.exists():raise ValueError('EXISTING_C32_DIRECTORY_NO_REFREEZE')
    for arm,root in roots.items():
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
        if head!=protocol['commits'][arm]:raise ValueError('C32_BASELINE_MISMATCH: '+arm)
        subprocess.run(['git','diff','--quiet',head,'--','tools','schemas','extensions','configs','tasks'],cwd=root,check=True)
    out.mkdir(parents=True)
    provider=read(ROOT/'evidence/b3_r1_history_assisted_050/configuration.json')['runtime']['provider']
    scope=C3_SCOPE.replace('C3 is','C3.2 is')
    tokenizer=official_tokenizer();rows=[]
    def measure(value):
        body=httpx.Request('POST','https://offline.invalid',json=value).content
        return dict(bytes=len(body),offline_serialized_tokens=len(tokenizer.encode(body.decode(),add_special_tokens=False).ids))
    for case,definition in protocol['cases'].items():
        pair=[]
        for arm in C3_ARMS:
            path=out/f'{case}-{arm}.json'
            c3_boundary(case,arm,path,source=(definition['folder'],definition['sequence']),roots=roots)
            d=read(path);pair.append(d)
            if d['source_state']['artifact_id']!=definition['source_state']:raise ValueError('C32_SOURCE_STATE_MISMATCH')
            if (not d['state_unchanged'] or not d['final_r1_refs_absent'] or
                    d['future_only_outputs']!=d['future_only_outputs_denied']):raise ValueError('C32_TEMPORAL_GATE_FAILED')
            if any(q['status']=='failed' and not q['historical_read_query'] for q in d['query_checks']):
                raise ValueError('C32_EVIDENCE_ENTRY_FAILED: '+str(path))
            wire=deepcopy(d['handoff_wire'])
            wire['tools']=[t for t in wire['tools'] if t['function']['name'] in ('research_plan','evidence_read','research_analysis')]
            wire['messages'][0]['content']+='\n\n'+scope
            wire.update(model=provider['model'],max_tokens=provider['max_tokens'],reasoning_effort=provider['reasoning_effort'],
                thinking={'type':provider['thinking']},stream=False,tool_choice='auto')
            atomic_json(out/f'{case}-{arm}-1-request.json',wire)
            rows.append(dict(case=case,arm=arm,**{k:d[k] for k in ('source_state','preparation','source_archive','event_boundary',
                'original_next_request','methods','allowed_artifact_count','future_only_outputs','future_only_outputs_denied','source_facts')},
                method_permissions={name:{k:row.get(k) for k in ('study_authorized','formal_execution_authorized',
                    'planning_status','execution_status','missing')} for name,row in d['packet']['research']['mathematical_capabilities']['methods'].items()},
                sizes=dict(probe_first_request=measure(wire),dynamic=measure(wire['messages'][-1]),
                    tool_schema=measure(wire['tools']),all_production_context=d['sizes']),
                query_count=len(d['query_checks']),current_queries_readable=True))
        if (pair[0]['source_state']!=pair[1]['source_state'] or pair[0]['source_facts']!=pair[1]['source_facts'] or
                pair[0]['allowed_artifact_count']!=pair[1]['allowed_artifact_count'] or set(pair[0]['methods'])!=set(pair[1]['methods']) or
                pair[0]['packet']['research']['task']!=pair[1]['packet']['research']['task'] or
                {k:v for k,v in pair[0]['packet'].items() if k!='research'}!={k:v for k,v in pair[1]['packet'].items() if k!='research'}):
            raise ValueError('C32_PAIR_FACT_OR_METHOD_MISMATCH')
        catalog=lambda d:d['packet']['research']['mathematical_capabilities']
        if catalog(pair[0])!=catalog(pair[1]):raise ValueError('C32_METHOD_PERMISSION_MISMATCH')
        # The rubric is never part of the Provider packet.
        for arm in C3_ARMS:
            wire=read(out/f'{case}-{arm}-1-request.json')
            if 'rubric_offline_only' in json.dumps(wire):raise ValueError('C32_RUBRIC_LEAK')
    summary=dict(status='offline_frozen_pending_explicit_c32_egress_authorization',verdict='insufficient_evidence',
        commits=protocol['commits'],provider=provider,scope=scope,authorization='PENDING_EXPLICIT_C32_APPROVAL',
        request_ceiling_proposed=12,offline_passed=True,offline=rows,protocol=protocol,
        actual_requests=0,usage=dict(prompt_tokens=0,completion_tokens=0,total_tokens=0),money=None,public_tool_calls=0,evidence_reads=0,
        scientific_workers=0,physics_steps=0,formal_studies=0,reporter_requests=0,provider_ledger_created=False,
        second_turn_size=None,second_turn_size_scope='Depends on the actual first response and read-only feedback; no synthetic response or observation is supplied.',
        order=[(case,arm) for i,case in enumerate(protocol['cases']) for arm in (C3_ARMS if i%2==0 else C3_ARMS[::-1])])
    atomic_json(out/'frozen.json',summary)
    return summary


async def live(out=OUT, *, test_transport=None, host=None):
    frozen = read(out / 'frozen.json')
    if frozen['instructions'] != INSTRUCTIONS or frozen['cases'] != read(Path(frozen.get('cases_source',CASES))):
        raise ValueError('FROZEN_INPUT_CHANGED')
    authorization=frozen['authorization'];ceiling=frozen['request_ceiling']
    if authorization.startswith('PENDING_EXPLICIT_APPROVAL'):
        raise ValueError('EXPLICIT_PROBE_APPROVAL_REQUIRED_BEFORE_PROVIDER')
    if frozen['cases'].get('binding_status') not in (None,'bound_verified_input_v1'):
        raise ValueError('VERIFIED_CANDIDATE_STATE_AND_EVIDENCE_BINDING_REQUIRED')
    if host is None and (out / 'provider/platform.sqlite').exists():
        raise ValueError('EXISTING_PROVIDER_ATTEMPT_NO_AUTOMATIC_RESEND')
    if host is None:
        store = Store(out / 'provider')
        host = SimpleNamespace(store=store, run_id='agent-math-decision-probe')
        project = ProjectConfig(project_id=host.run_id, grant_id=out.name + '-provider-'+str(ceiling),
            authorization_source=authorization, budget=dict(model_calls=ceiling, tool_calls=0,
            backend_solves=0, worker_calls=0, wall_s=None), exclusive_resources={'provider_request': 1})
        store.create(project)
        # Legacy read-only probes use a platform transport session.
        store.create_session(dict(input=dict(run_id=host.run_id, policy=dict(budget=plain(project.budget))),
                                  purpose='read-only Provider accounting; not a Study'))
        update(host, pilot=dict(provider=frozen['provider'], live_model_requests=0))
    else:
        from tools.research.state import guard
        guard(host)
        if provider_usage(host)['actual_requests']:
            raise ValueError('EXISTING_PROVIDER_ATTEMPT_NO_AUTOMATIC_RESEND')
    record(host, 'provider_egress_authorization', dict(user_approval=authorization,
        endpoint=frozen['provider']['base_url'] + '/chat/completions', ceiling=ceiling,
        data_scope='frozen task/scalars/diagnostics/evidence summaries; no credentials or unrelated files'))
    boundary = LiveBoundary(host, test_transport)
    provider = frozen['provider']
    summary = read(SUMMARY)
    histories = {(case, arm): [] for case in frozen['cases']['cases'] for arm in ARMS}
    try:
        for case in frozen['cases']['cases']:
            for turn in (1, 2):
                for arm in ARMS:
                    history = histories[case, arm]
                    request = wire(provider, frozen['cases'], case, arm, turn, history)
                    label = f'{case}-{arm}-{turn}'
                    atomic_json(out / f'{label}-request.json', request)
                    result = dict(case=case, arm=arm, turn=turn, scientific_execution='not_dispatched')
                    summary['results'].append(result)
                    try:
                        response = await boundary.handle_async_request(httpx.Request('POST',
                            provider['base_url'].rstrip('/') + '/chat/completions', json=request,
                            headers={'Authorization': 'Bearer ' + os.environ['DEEPSEEK_API_KEY']},
                            extensions={'timeout': dict(connect=30, read=provider['timeout_s'], write=30, pool=30)}))
                        response.raise_for_status()
                        body = response.json()
                        atomic_json(out / f'{label}-response.json', body)
                        message = body['choices'][0]['message']
                        result.update(request_id=boundary.last_request, usage=body.get('usage'),
                                      finish_reason=body['choices'][0].get('finish_reason'))
                        try:
                            result['plan'] = parse(message)
                            result['schema_check'] = 'passed'
                        except ValueError as exc:
                            result.update(schema_check='failed', schema_error=str(exc))
                        boundary.consumed()
                        history.extend([request['messages'][-1], message])
                        for call in message.get('tool_calls') or []:
                            history.append(dict(role='tool', tool_call_id=call['id'], content=json.dumps(dict(
                                scientific_execution='disabled', observation=None,
                                decision_schema_check=result['schema_check']))))
                        print(label + ': ' + result['schema_check'], flush=True)
                    except Exception as exc:
                        result.update(request_id=boundary.last_request, error=type(exc).__name__ + ': ' + str(exc))
                        raise  # Retain the failure; no alternate ID or repair request.
                    finally:
                        summary.update(provider_usage(host))
                        summary['status'] = 'B3_partial'
                        atomic_json(SUMMARY, summary)
        summary['status'] = 'B3_completed_unscored'
    finally:
        await boundary.aclose()
        atomic_json(SUMMARY, summary)
    return summary


def main():
    global SUMMARY
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('freeze', 'live','c3-template','review','c3-freeze','c3-live','c32-freeze'))
    parser.add_argument('--results',type=Path,help='Read-only review of saved original probe results')
    parser.add_argument('--cases',type=Path,default=CASES)
    parser.add_argument('--out',type=Path)
    parser.add_argument('--approval-file',type=Path,help='Future explicit approval text; cannot authorize an unbound draft')
    parser.add_argument('--c3-followup',action='store_true',help='One bounded second turn after the first six; shares the hard 12-request ledger')
    args = parser.parse_args()
    out=args.out or OUT
    if args.out:SUMMARY=out/'summary.json'
    if args.mode=='c32-freeze':
        if args.out is None:parser.error('C3.2 requires an independent --out directory')
        result=c32_freeze(out.resolve())
        print('C3.2 offline pairs: '+str(len(result['offline']))+'; Provider=0; science=0; explicit egress approval pending')
    elif args.mode.startswith('c3-') and args.mode!='c3-template':
        if args.out is None:parser.error('C3 requires an independent --out directory')
        if args.mode=='c3-freeze':
            rows=c3_freeze(out.resolve());print('C3-A passed: '+str(len(rows))+' frozen inputs; Provider=0; science=0')
        else:
            load_credential(Path('~/.codex/.env').expanduser())
            result=asyncio.run(c3_live(out.resolve(),args.c3_followup))
            print(json.dumps({k:result[k] for k in ('status','actual_requests','usage')},ensure_ascii=False))
    elif args.mode=='c3-template':
        data=read(Path(__file__).with_name('fixtures')/'c3_math_decision_template.json')
        provider=read(ROOT/'configs/research/runtime_c3_ab.json')['provider']
        print(json.dumps(dict(status=data['binding_status'],authorization=data['authorization'],
            packets=[dict(arm=arm,turn=turn,wire=wire(provider,data,'c3_next_decision',arm,turn))
                for turn in (1,2) for arm in ARMS]),ensure_ascii=False))
    elif args.mode=='review':
        if args.results is None:parser.error('review requires --results')
        data=read(args.results);rows=[]
        for row in data.get('results',[]):
            value=dict(case=row.get('case'),arm=row.get('arm'),turn=row.get('turn'),request_id=row.get('request_id'))
            try:
                p=Plan.model_validate(row['plan']);value.update(schema='passed',
                    hypothesis=p.hypothesis,decision=plain(p.decision),expected_observation=p.expected_observation,
                    weakening_observation=p.weakening_observation,interpretation=p.interpretation)
            except (ValueError,KeyError) as exc:value.update(schema='failed',reason=str(exc))
            rows.append(value)
        print(json.dumps(dict(decisions=rows,usage=data.get('usage'),actual_requests=data.get('actual_requests'),
            scoring='Human blind review using frozen rubric; no automatic correctness/direction answer'),ensure_ascii=False))
    elif args.mode == 'freeze':
        provider=read(ROOT/'configs/research/runtime_c3_ab.json')['provider'] if args.cases!=CASES else None
        freeze(out,cases_path=args.cases,provider=provider,
            authorization=args.approval_file.read_text(encoding='utf8') if args.approval_file else None)
        print('B1 frozen; Provider=0; science=0')
    else:
        # Only the existing credential loader reads the private file; never serialize it.
        load_credential(Path('~/.codex/.env').expanduser())
        result = asyncio.run(live(out))
        print(json.dumps({k: result[k] for k in ('status', 'actual_requests', 'usage')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
