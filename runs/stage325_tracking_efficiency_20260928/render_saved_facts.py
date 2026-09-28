"""Read-only re-rendering of the two archived executions; never resumes them."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.platform_store import Store
from tools.state_io import atomic_json
from extensions.tendon_family import route
from extensions.tendon_family.candidate import candidate_facts
from extensions.tendon_family.delivery_facts import bound_tracking_facts
from extensions.tendon_family.gvs_reporting import markdown

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
source=ROOT/'runs/stage324_time_reference_tracking_20260928'
for label in ('deterministic','live'):
    store=Store(source/label)
    run=json.loads((source/label/'workflow.json').read_text())['run_id']
    saved=store.session(run)
    if label=='live':
        node=next(n for n in saved['state']['route']['nodes'] if n['action']=='run')
        trial=store.artifact(node['result'])
        candidate=route.trial_facts(store,saved['snapshot']['input'],trial)
    else:
        sim=json.loads((source/label/'simulate_receipt.json').read_text())
        ev=json.loads((source/label/'evaluate_receipt.json').read_text())
        report=json.loads((source/label/'report_receipt.json').read_text())
        config=saved['state']['result_executions'][sim['execution_id']]['candidate_input']
        built=store.artifact(config)
        candidate=candidate_facts(saved['snapshot']['input'],built,config,built['candidate_id'],run,sim['execution_id'])
        trial=dict(simulation=sim,evaluation=ev['output'],profile_report=dict(reference=report['output'],
            owner_run_id=run,execution_id=sim['execution_id'],request_id=report['request_id']))
    facts=bound_tracking_facts(store,trial,candidate)
    atomic_json(args.output/(label+'_factual_delivery.json'),facts)
    summary=store.artifact(trial['profile_report']['reference'])['detail']
    (args.output/(label+'_factual_delivery.md')).write_text(markdown(dict(summary,factual_result=facts)),encoding='utf8')
