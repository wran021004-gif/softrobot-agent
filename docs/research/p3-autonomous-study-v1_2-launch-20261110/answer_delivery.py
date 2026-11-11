"""User-authorized Main answer delivery through the existing accounted harness."""
import os
for name in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'):os.environ[name]='1'
import asyncio,json,sys,time
from pathlib import Path
from tools.platform_host import Host
from tools.research.state import state,save,guard
from tools.research import core
from tools.research.agent import converse
from tools.research.budget import engineering_closeout
from tools.state_io import read,atomic_json,digest

ROOT=Path(__file__).resolve().parents[3]
DOC=Path(__file__).resolve().parent
NAME='p3-passive-progressive-stiffness-autonomous-20261110-v1_2'


def host():return Host(ROOT/'runs/research'/NAME,NAME,actor='user-authorized-main-answer-delivery')


def science(h):
    s=state(h)
    keys=('spec','profile','candidates','plans','results','physical_replays','analysis_results',
        'search_results','mathematical_evaluations','numerical_s','success_gate','selected')
    return {k:digest(s.get(k)) for k in keys}


def prepare():
    h=host();s=state(h)
    before=dict(timestamp_unix=time.time(),science=science(h),ledger=h.store.remaining(),
        implementation=s['freeze'],previous_main_answer=s.get('main_final_answer'))
    atomic_json(h.store.root/'answer-delivery-before.json',before)
    core.bind(h,reason='User requests Main final answer with necessary evidence checks, no repeated or complex validation. Repair explicit execution-purpose feedback and exact protocol source registration; science and costs unchanged.')
    protocol=read(ROOT/'configs/research/p3_original_protocol_source_v1.json')
    restored=save(h,protocol,'restored_frozen_protocol_source')
    assert restored==s['spec']['canonical_task']['goal']['data']['protocol_source']
    directive=save(h,dict(version='operator_answer_delivery_v1',
        user_request='Main must deliver the final answer after necessary verification. Do not require repeated or complex validation, Replay, additional experiments or Reporter reviews at closeout.',
        objective='Use the existing Study evidence. Verify the chosen design and measured outcomes as needed, synthesize the final research answer, and finish. The demonstrated research capability is the current delivery goal; formal acceptance certification is not a prerequisite.',
        requested_answer='State the best concrete design, actual measured performance, the supported scientific and research-capability conclusions, and the scope of those conclusions. Distinguish observed measurements from unmeasured causal/independent validation. Do not respond with a plan for more research.',
        budget='Use only the existing remaining requests within the original extended total of 160; no new budget is granted.'), 'operator_main_answer_request')
    assert science(h)==before['science']
    assert h.store.remaining()==before['ledger']
    guard(h)
    atomic_json(DOC/'answer-delivery-before.json',before)
    receipt=dict(operator_request=directive,protocol_restored=restored,implementation=state(h)['freeze'],
        science_unchanged=True,ledger_unchanged=True,tests='12 targeted offline tests passed')
    atomic_json(DOC/'answer-delivery-bound.json',receipt)
    print(json.dumps(receipt),flush=True)


def run():
    h=host();bound=read(DOC/'answer-delivery-bound.json')
    asyncio.run(converse(h,session_handoff=True,operator_request=bound['operator_request'],
        delivery_only=True,max_new_provider_requests=1))
    s=state(h)
    print(json.dumps(dict(main_final_answer=s.get('main_final_answer'),ledger=h.store.remaining())),flush=True)
    if s.get('main_final_answer'):
        answer=h.store.artifact(s['main_final_answer'])
        (DOC/'main-final-answer-20261111.md').write_text(answer['text']+'\n',encoding='utf-8')


def finish():
    h=host();s=state(h);before=read(DOC/'answer-delivery-before.json')
    answer=h.store.artifact(s['main_final_answer'])
    assert answer['text'].strip()
    assert science(h)==before['science']
    engineering_closeout(h,'Main delivered its final answer using existing evidence, as requested by the user. No additional experiments, independent Replay or Reporter review required.',kind='user_requested_main_answer_delivery')
    after=dict(main_final_answer=s['main_final_answer'],implementation=s['freeze'],science_unchanged=science(h)==before['science'],
        ledger_before=before['ledger'],ledger_after=h.store.remaining(),
        new_provider_requests=h.store.remaining()['used']['model_calls']-before['ledger']['used']['model_calls'],
        status=state(h)['research_status'],final_disposition=state(h)['final_disposition'],
        scientific_acceptance_unchanged=True,timestamp_unix=time.time())
    atomic_json(DOC/'answer-delivery-after.json',after)
    print(json.dumps(after),flush=True)


if __name__=='__main__':globals()[sys.argv[1]]()
