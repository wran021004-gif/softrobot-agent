"""Read-only report audit of an existing Store; no Provider or science dispatch."""
import argparse
import hashlib
from pathlib import Path
from schemas.research_reporting import ScientificReport
from tools.platform_host import Host
from tools.research.core import read_evidence
from tools.research.reporter import assemble
from tools.research.state import state
from tools.state_io import atomic_json


def audit(directory, run_id):
    h=Host(directory,run_id,actor='read-only-reporting-audit')
    before=state(h);ledger=h.store.remaining();events=h.store.events(run_id)
    sha=hashlib.sha256(h.store.db.read_bytes()).hexdigest()
    counts={};pointers=0;examples=[]
    for key in ('results','physical_replays','mechanics_results','control_search_results'):
        counts[key]=0
        for ref in before.get(key,[]):
            report=assemble(h,[ref])
            ScientificReport.model_validate_json(report.model_dump_json())
            card=report.results[0]
            metrics=list(card.metrics)
            if card.control_search:
                search=card.control_search
                steps=[*search.baselines,*search.proposals,*([search.best] if search.best else [])]
                metrics.extend(m for step in steps for m in step.metrics)
            for metric in metrics:
                assert read_evidence(h,metric.source.model_dump(),record_read=False)==metric.value
                if metric.threshold_source:
                    assert read_evidence(h,metric.threshold_source.model_dump(),record_read=False)==metric.threshold
                pointers+=1
            counts[key]+=1
            if key in ('results','mechanics_results'):
                examples.append(dict(kind=key,report=report.model_dump()))
    assert state(h)==before and h.store.remaining()==ledger and h.store.events(run_id)==events
    assert hashlib.sha256(h.store.db.read_bytes()).hexdigest()==sha
    return dict(source_db_sha256=sha,report_count=sum(counts.values()),counts=counts,
        metric_pointer_checks=pointers,state_ledger_events_unchanged=True,
        new_science=0,provider_requests=0,examples=examples)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path);parser.add_argument('run_id')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=audit(args.directory,args.run_id)
    atomic_json(args.output,result)
    print({k:v for k,v in result.items() if k!='examples'})
