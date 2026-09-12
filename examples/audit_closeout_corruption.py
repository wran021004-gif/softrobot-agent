"""Verify a portable bundle with backends blocked, then reject a damaged copy."""
from pathlib import Path
import argparse
import sys
import tarfile
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('bundle');parser.add_argument('--output',required=True)
    args=parser.parse_args()
    # Import failures would expose any accidental audit dependency on a backend.
    sys.modules['mujoco']=None;sys.modules['matlab.engine']=None
    from tools.closeout_audit import audit,audit_bundle
    from tools.closeout_state import read,atomic_json
    from tools.artifact_tools import file_hash
    before=file_hash(args.bundle);normal=audit_bundle(args.bundle)
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        with tarfile.open(args.bundle,'r:xz') as archive:
            for member in archive:
                target=(root/member.name).resolve()
                assert member.isfile() and target.is_relative_to(root.resolve())
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(archive.extractfile(member).read())
        parent=read(root/'bundle_index.json')['parent_id'];summary=read(root/parent/'closeout_summary.json')
        path=root/summary['best']['run_id']/'mujoco_result.json';value=read(path)
        value['metrics']['tip_position_m'][0]+=.01;atomic_json(path,value)
        try:
            audit(root,parent)
        except (AssertionError,ValueError) as exc:
            corruption=dict(rejected=True,changed_artifact=path.relative_to(root).as_posix(),reason=str(exc))
        else:
            raise AssertionError('Damaged evidence was accepted')
    assert file_hash(args.bundle)==before
    result=dict(bundle_sha256=before,normal_audit=normal,corruption_test=corruption,
        original_unchanged=True,matlab_and_mujoco_imports_blocked=True)
    atomic_json(args.output,result);print(result)


if __name__=='__main__':main()
