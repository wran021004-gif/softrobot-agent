"""Inspect sealed control evidence by execution/update/snapshot ID, never raw paths."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
from tools.platform_store import Store,plain
from tools.state_io import read
from extensions.tendon_family.control_evidence import ControlEvidence,EvidenceQuery,ExecutionComparison


def local_comparison(reader,execution_id,snapshot_id):
    from extensions.tendon_family.control_comparison import LocalComparisonRequest,freeze_comparison,run_comparison
    from tools.state_io import atomic_json
    from tools.workbench import owner
    from tools.platform_store import zero
    import time
    root=ROOT/'runs/control_comparisons';root.mkdir(parents=True,exist_ok=True)
    with owner(root,'.comparison.lock'):
        ledger_path=root/'usage.json'
        ledger=read(ledger_path) if ledger_path.exists() else dict(local_solves=0,wall_s=0.,attempts=[])
        if ledger['local_solves']+2>4 or ledger['wall_s']+300>1200:raise RuntimeError('LOCAL_EXPLICIT_LIMIT_EXHAUSTED')
        request=LocalComparisonRequest(execution_id=execution_id,snapshot_id=snapshot_id,
            changed_factor='truncate_horizon_at_deadline')
        protocol=freeze_comparison(reader,request)
        if snapshot_id in ledger['attempts']:raise RuntimeError('COMPARISON_ALREADY_ATTEMPTED')
        store=Store(root/snapshot_id);budget=zero()
        store.create(dict(project_id='local-'+snapshot_id,grant_id='local-'+snapshot_id,budget=budget,
            authorization_source='Explicitly requested bounded comparison, Stage 3.41; offline limits in parent usage ledger.'))
        atomic_json(store.root/'protocol.json',protocol);ledger['attempts'].append(snapshot_id);atomic_json(ledger_path,ledger)
        start=time.perf_counter()
        def charge(role,elapsed):
            ledger['local_solves']+=1;ledger['last_started_role']=role;atomic_json(ledger_path,ledger)
        def save(value):
            with store.transaction() as db:return plain(store.put(db,value))
        try:
            result=run_comparison(reader,request,protocol,save,charge)
            atomic_json(store.root/'result.json',result)
        finally:
            ledger['wall_s']+=time.perf_counter()-start;atomic_json(ledger_path,ledger)
        return result


def resolve_reader(execution_id):
    found=[]
    for source in read(ROOT/'evidence/control_evidence_catalog.json')['sources']:
        store=Store(ROOT/source['store'])
        if not store.db.is_file():continue
        with store.connect(True) as db:
            ids=[json.loads(row['state']).get('result_executions',{}) for row in db.execute('SELECT state FROM sessions')]
        if any(execution_id in values for values in ids):found.append(ControlEvidence(store))
    if len(found)!=1:raise ValueError('CATALOG_EXECUTION_MISSING_OR_AMBIGUOUS')
    return found[0]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['inspect','plans','prediction','compare','local-compare'])
    parser.add_argument('--execution',required=True)
    parser.add_argument('--updates',type=int,nargs='*',default=[])
    parser.add_argument('--snapshot')
    parser.add_argument('--variant')
    parser.add_argument('--changed-factor',choices=['recording','controller','design'])
    args=parser.parse_args();reader=resolve_reader(args.execution)
    if args.operation=='local-compare':
        if not args.snapshot:parser.error('local-compare requires --snapshot and explicitly runs two bounded solves')
        result=local_comparison(reader,args.execution,args.snapshot)
    elif args.operation=='compare':
        if not args.variant or not args.changed_factor:parser.error('compare requires --variant and --changed-factor')
        result=reader.compare(ExecutionComparison(baseline_execution_id=args.execution,
            variant_execution_id=args.variant,changed_factor=args.changed_factor),resolve_reader(args.variant))
    else:
        result=plain(reader.query(EvidenceQuery(execution_id=args.execution,operation=args.operation,
            update_ids=args.updates,snapshot_id=args.snapshot)))
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__':main()
