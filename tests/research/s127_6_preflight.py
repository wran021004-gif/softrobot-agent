"""Read-only historical diagnosis and capacity audit; no Provider/scientific run."""
from copy import deepcopy
import json
import httpx
from tools.platform_host import Host
from tools.research.config import ROOT,resolve
from tools.research.state import state
from tools.research.agent import provider_outcome,pending
from tools.state_io import read,atomic_json,digest


def audit():
    old=Host(ROOT/'runs/research/s127-4b-sdk-20261021','s127-4b-sdk-20261021')
    original=deepcopy(state(old));events=old.store.events(old.run_id);ledger=old.store.remaining()
    outcome=provider_outcome(old,original['pilot']['unconsumed_response'])
    assert outcome['finish_reasons']==['length'] and not outcome['outcome_unknown']
    assert ledger['used']['model_calls']==1 and not pending(old)
    atomic_json(ROOT/'evidence/s127_5_provider/classification.json',dict(
        original_study=old.run_id,provider=outcome,original_output_capacity=original['pilot']['provider']['max_tokens'],
        saved_unconsumed_response_retained=True,same_frozen_request_resent=False,new_provider_requests=0,
        raw_reasoning_preserved=True,source_state_identity=digest(original),source_ledger=ledger,
        wrapping_chain='LiveBoundary ValueError -> AsyncOpenAI._base_client.AsyncAPIClient.request generic Exception handler -> APIConnectionError -> AccountedDeepSeekModel restores incomplete-output diagnosis from original durable bytes',
        sdk_installations_modified=False))
    manifest=read(ROOT/'evidence/s127_6_decision/manifest.json');source=Host(manifest['store'],manifest['run_id'])
    capacities=[]
    for case in manifest['cases']:
        wire=source.store.artifact(case['request']);size=len(httpx.Request('POST','https://api.deepseek.com/chat/completions',json=wire).content)
        capacities.append(dict(name=case['name'],arm=case['arm'],serialized_utf8_bytes=size,
            max_output_tokens=65536,framing_headroom=8192,conservative_total_capacity_estimate=size+65536+8192,
            context_limit_tokens=1000000,fits=size+65536+8192<=1000000,actual_tokens=None))
    runtime=read(ROOT/'configs/research/runtime.json');trial=resolve(ROOT/'configs/research/study_s127_6_handoff.json')
    p=trial['runtime']['provider'];assert p['max_tokens']==65536
    assert not trial['research_decisions']['history'] and not trial['research_decisions']['mathematics'] and not trial['research_decisions']['control_seeds']
    old_research=Host(ROOT/'runs/research/s126-cold-live-20261020','s126-cold-live-20261020')
    s=state(old_research)
    report=dict(status='offline_prepared_live_authorization_pending',verified_date='2026-10-21',
        official_sources=['https://api-docs.deepseek.com/api/create-chat-completion/','https://api-docs.deepseek.com/quick_start/pricing/','https://api-docs.deepseek.com/guides/thinking_mode/'],
        official_limits=dict(model='deepseek-flash',context='1M',maximum_output_tokens=393216,thinking_default_output=65536),
        production_runtime_unchanged_max_tokens=runtime['provider']['max_tokens'],validation_provider=p,
        capacities=capacities,capacity_scope='Serialized UTF-8 byte count is a conservative guard estimate, not actual tokens. Reserve max output and framing on every new send. Provider usage remains authoritative.',
        sdk_context=dict(offload='tool_results truncate, preview_tokens=500 above threshold=1500; no auxiliary model calls',
            reasoning='All assistant reasoning_content retained by DeepSeekModel.format_request_messages; no history deletion',
            session='Continuous Strands default; handoff production gate closed pending actual live validation'),
        historical_usage=dict(study_id=old_research.run_id,state_identity=digest(s),ledger=old_research.store.remaining(),
            method_counts={k:s.get(k,0) for k in ('mathematical_evaluations','offline_nlp','bdf_replays','nmpc_launches','physical_replay_launches','admitted_training_stages')},
            scientific_executions_are_not_new_s128_evidence=True),
        s128_proposal=dict(status='discussion_only_requires_new_separate_authorization',
            provider_requests=96,protected_provider_requests=8,public_operations=300,protected_public_operations=20,
            shared_physical_launches=64,mathematical_evaluations=8,offline_nlp=4,bdf_replays=4,nmpc_executions=4,
            ppo_training_stages=2,ppo_total_actions=131072,ppo_actions_per_trial=65536,rl_evaluation_episodes=2,
            max_tokens=65536,context_limit_tokens=1000000,session_strategy='Continuous Strands until live handoff formally admitted',
            methods='All original structure/mathematics/NLP/NMPC/explicit control/response/pattern/Direct PPO/Residual PPO entries remain optional',
            initial_state='New Study ID, Store and SDK; empty experiments/mathematics/control seeds/external scientific evidence',
            task='tasks/reach_hold_mirror_v1.json unchanged; original independent MuJoCo acceptance'),
        new_provider_requests=0,new_physical_launches=0,new_s128_study_started=False)
    assert state(old)==original and old.store.events(old.run_id)==events and old.store.remaining()==ledger
    atomic_json(ROOT/'evidence/s127_8_preflight/preflight.json',report)
    return report


if __name__=='__main__':
    value=audit();print(json.dumps(dict(status=value['status'],all_initial_wires_fit=all(r['fits'] for r in value['capacities']),new_provider_requests=0)))
