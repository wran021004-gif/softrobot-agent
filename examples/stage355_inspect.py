"""Offline working-state inspector: existing stores only, no Host invocation."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.platform_store import Store, plain
from tools.working_state import project_working_state
from tools.runtime_identity import require_softagent_runtime


def inspect(root, run_id):
    return plain(project_working_state(Store(root),run_id))


if __name__=='__main__':
    require_softagent_runtime()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('store');parser.add_argument('--run-id')
    args=parser.parse_args();store=Store(args.store)
    if args.run_id:
        print(json.dumps(inspect(args.store,args.run_id),ensure_ascii=True,indent=2))
    else:
        with store.connect(True) as db:
            print(json.dumps([dict(row) for row in db.execute('SELECT run_id,status FROM sessions')],indent=2))
