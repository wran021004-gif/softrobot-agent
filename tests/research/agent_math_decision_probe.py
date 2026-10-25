"""Two frozen paired decisions, using production Plan and accounted LiveBoundary.

Only Provider I/O runs. No Host/research Study, scientific dispatch or Reporter.
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
    'This is a read-only decision probe, not a new Study. Submit exactly one research_plan '
    'tool call using the production Plan/ResearchDecision contract. Use action=diagnose '
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


async def live(out=OUT, *, test_transport=None):
    frozen = read(out / 'frozen.json')
    if frozen['instructions'] != INSTRUCTIONS or frozen['cases'] != read(Path(frozen.get('cases_source',CASES))):
        raise ValueError('FROZEN_INPUT_CHANGED')
    authorization=frozen['authorization'];ceiling=frozen['request_ceiling']
    if authorization.startswith('PENDING_EXPLICIT_APPROVAL'):
        raise ValueError('EXPLICIT_PROBE_APPROVAL_REQUIRED_BEFORE_PROVIDER')
    if frozen['cases'].get('binding_status') not in (None,'bound_verified_input_v1'):
        raise ValueError('VERIFIED_CANDIDATE_STATE_AND_EVIDENCE_BINDING_REQUIRED')
    if (out / 'provider/platform.sqlite').exists():
        raise ValueError('EXISTING_PROVIDER_ATTEMPT_NO_AUTOMATIC_RESEND')
    store = Store(out / 'provider')
    host = SimpleNamespace(store=store, run_id='agent-math-decision-probe')
    project = ProjectConfig(project_id=host.run_id, grant_id=out.name + '-provider-'+str(ceiling),
        authorization_source=authorization, budget=dict(model_calls=ceiling, tool_calls=0,
        backend_solves=0, worker_calls=0, wall_s=None), exclusive_resources={'provider_request': 1})
    store.create(project)
    # A platform transport session, with no Research Study/spec/candidate lifecycle.
    store.create_session(dict(input=dict(run_id=host.run_id, policy=dict(budget=plain(project.budget))),
                              purpose='read-only Provider accounting; not a Study'))
    update(host, pilot=dict(provider=frozen['provider'], live_model_requests=0))
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
    parser.add_argument('mode', choices=('freeze', 'live','c3-template','review'))
    parser.add_argument('--results',type=Path,help='Read-only review of saved original probe results')
    parser.add_argument('--cases',type=Path,default=CASES)
    parser.add_argument('--out',type=Path)
    parser.add_argument('--approval-file',type=Path,help='Future explicit approval text; cannot authorize an unbound draft')
    args = parser.parse_args()
    out=args.out or OUT
    if args.out:SUMMARY=out/'summary.json'
    if args.mode=='c3-template':
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
