"""One held-out public diagnostic case, Knowledge off/on, zero scientific dispatch.

Reuses the production Harness/LiveBoundary and the existing isolated probe. The
only changing input is the optional procedural retrieval hint/tool; no solutions.
"""
import argparse
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from tests.research.flash_pro_decision_probe import run_case, INSTRUCTIONS
from tools.research.agent import load_credential
from tools.research.config import ROOT, resolve
from tools.state_io import read, atomic_json
from tools.platform_store import Store

OUT=ROOT/'runs/kdiag'
PUBLIC=ROOT/'evidence/research_knowledge_20261027'


def freeze():
    if (OUT/'frozen.json').exists():return read(OUT/'frozen.json')
    spec=resolve(ROOT/'configs/research/study_bf6_public.json')
    source='evidence/bf4_bf6_public_integration_20261027/summary.json'
    raw=read(ROOT/source)['physical_check']
    bf6={k:raw[k] for k in ('native_status','native_reason','native','independent_replay','protocol','acceptance_status','selected')}
    bf6.update(confirmed_completed_steps_lower_bound=450,attempted_physics_step_calls=451,
        contact_observation='First floor/payload contact recorded at 0.225 s; independent replay also records contact before numerical failure.',
        load_binding='Compiled actual 20 g rigid mass/COM/full inertia matched; no force surrogate.',
        missing='No saved per-physics-step acceleration or contact frame in this scalar projection; contact/instability cause unknown.')
    path='evidence/integration_research_next/bf5_engineering.json'
    raw5=read(ROOT/path)
    bf5={k:raw5[k] for k in ('acceptance_status','selected','protocol','physics_steps')}
    bf5.update(independent_execution_complete=True,unrounded_metrics='Not present in public engineering summary',numerical_s=raw5['resource_use']['numerical_s'])
    evidence=dict(bf5=bf5,bf6=bf6,
        sources=[dict(path=p,sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()) for p in (source,path)],
        question='Compare the failure classes; diagnose what is known, competing causes and the next discriminating saved-evidence reads. Describe a task-appropriate successful route and its prerequisites without promising success. Explain whether STOP is required with zero science authorization and what would justify future work. Do not infer unreported BF5 error magnitudes.')
    protocol=dict(models=['deepseek-v4-pro'],requests_per_case_model=4,max_tokens=8192,thinking='enabled',reasoning_effort='high',
        authorization='User 2026-10-27 explicitly requests one small Agent decision comparison with/without Knowledge, actual Token cost, historical public evidence and no scientific workers. At most eight Provider requests; no automatic retries or formal Study.',
        scientific_workers=0,physics_steps=0,reporter_requests=0)
    instructions=INSTRUCTIONS.format(requests=4)+(
        ' If an optional experience hint/tool is present, decide whether to retrieve relevant guidance by search/read; do not assume it is evidence of this case. '
        'Historical recipes do not authorize science or provide a current passing result. '
        'Use action stop if no authorized work remains, or diagnose to record read-only analysis; either must explain the stop boundary. '
        'Submit diagnostic analysis, competing hypotheses, discriminating observations and future route in the typed Plan interpretation; do not require another prose turn. '
        'No new Study, Native search, physical replay or training may run. All science allowances are zero.')
    frozen=dict(protocol=protocol,provider=spec['runtime']['provider'],credentials_reference=spec['runtime']['credentials_reference'],
        instructions=instructions,cases={arm:dict(task=read(ROOT/'tasks/bf6_sensor_oriented_tracking_v1.json')['task'],evidence=deepcopy(evidence)) for arm in ('off','on')})
    OUT.mkdir(parents=True,exist_ok=True);atomic_json(OUT/'frozen.json',frozen)
    PUBLIC.mkdir(parents=True,exist_ok=True)
    # Reviewable exact outbound public case and instructions; credentials stay local.
    atomic_json(PUBLIC/'protocol.json',dict(protocol=protocol,instructions=instructions,evidence=evidence,
        task_sources=['tasks/bf6_sensor_oriented_tracking_v1.json'],knowledge_sources='Only the six public procedure files in memory/diagnostics/research-*_v1.json via original search/read; no private Store or successful control/design. B successful outcomes are not the held-out A integration executions.',
        exclusions=['credentials','private Stores','raw Provider reasoning','successful structure coordinates','control arrays']))
    return frozen


async def main(live=False):
    frozen=freeze()
    if not live:print(json.dumps(dict(status='frozen',maximum_provider_requests=8,scientific_workers=0)));return
    load_credential(Path(frozen['credentials_reference']).expanduser())
    results=[]
    for arm in ('off','on'):
        result=await run_case(OUT,frozen,arm,'deepseek-v4-pro',experience_enabled=arm=='on')
        store=Store(OUT/(arm+'-deepseek-v4-pro'))
        run_id='probe-'+OUT.name+'-'+arm+'-deepseek-v4-pro'
        plans=[store.artifact(e['outputs'][0]) for e in store.events(run_id) if e['kind']=='probe_tool_check']
        result['public_decisions']=[r['input'] for r in plans if r['tool']=='research_plan']
        results.append(dict(arm=arm,**result))
        atomic_json(OUT/'summary.json',dict(results=results))
    output=dict(results=results,actual_requests=sum(r['actual_requests'] for r in results),
        usage={k:sum(r['usage'][k] for r in results) if all(r['usage'][k] is not None for r in results) else None for k in results[0]['usage']},
        scientific_workers=0,physics_steps=0,formal_studies=0,money=None,
        limitations='One ordered off/on case, no population or causal benefit claim; prompt/cache/order differ. Scientific admission not exercised; only schema/reference/intent checks and retrieval receipts.')
    atomic_json(PUBLIC/'decisions.json',output)
    print(json.dumps(output,ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--live',action='store_true')
    asyncio.run(main(parser.parse_args().live))
