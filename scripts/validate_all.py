"""Typed dispatch: unchanged ten active exports plus eleven passive PHS traces."""
import argparse
import json
from pathlib import Path
from phs2d_io import read,write,require,forbid_integration,TASK_DIR
import validate_package
import validate_phs2d


def validate(root):
    forbid_integration()
    active = validate_package.validate(root)
    manifest = read(root/'manifest.json')
    entries = manifest.get('passive_benchmarks',[])
    require(len(entries) == 1 and entries[0]['type'] == 'passive_fixed_payout_v1' and
            entries[0]['benchmark'] == TASK_DIR, 'EXPLICIT_PASSIVE_DISPATCH')
    passive = validate_phs2d.validate(root)
    baseline = read(root/TASK_DIR/'evidence/legacy_hash_snapshot.json')
    from phs2d_io import sha
    preserved = {name:sha(root/name)==identity for name,identity in baseline['files'].items()
                 if name not in baseline['mutable_root_files']}
    require(all(preserved.values()), 'LEGACY_IMMUTABLE_FILE_HASH_CHANGED')
    return dict(status='passed' if active['status']==passive['status']=='passed' else 'failed',
        active=active, passive=passive, legacy_preserved_files=len(preserved),
        all_legacy_immutable_hashes_preserved=True, physics_steps=0)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--report',type=Path)
    args=p.parse_args()
    try: report=validate(args.package.resolve())
    except Exception as exc: report=dict(status='failed',failures=[str(exc)],physics_steps=0)
    if args.report: write(args.report,report)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if report['status']!='passed': raise SystemExit(1)


if __name__=='__main__':main()
