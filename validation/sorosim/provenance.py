"""Capture source identities and hashes, without copying upstream code/binaries."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def git(directory, *args):
    return subprocess.check_output(['git','-C',str(directory),*args],text=True).strip()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args = p.parse_args()
    cfg = json.loads((HERE/'cases.json').read_text(encoding='utf-8'))
    assert git(args.reference,'rev-parse','HEAD') == cfg['upstream_sha']
    assert not git(args.reference,'status','--porcelain')
    tracked = git(args.reference,'ls-tree','-r','--name-only','HEAD').splitlines()
    submodules = []
    for line in git(args.reference,'ls-tree','-r','HEAD','external').splitlines():
        metadata, name = line.split('\t',1)
        mode, kind, sha = metadata.split()
        if mode == '160000':
            submodules.append(dict(path=name,sha=sha,initialized=(args.reference/name/'.git').exists()))
    licenses = [name for name in tracked if any(word in Path(name).name.lower()
                                               for word in ('license','licence','copying','copyright'))]
    # Hash the executed module tree and top-level startup, excluding codegen duplicates.
    sources = {}
    for rel in tracked:
        path = args.reference/rel
        if (rel.startswith('Differentiable_SoRoSim/') and '/codegen/' not in rel
                and path.suffix.lower() in ('.m','.mexw64')):
            sources[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    scripts = {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
               for p in HERE.iterdir() if p.suffix in ('.m','.py','.ps1','.json','.md') or p.name=='.gitattributes'}
    academic_headers = [name for name in tracked if name.startswith('Differentiable_SoRoSim/Basic_functions/codegen/')
                        and name.endswith('.h') and 'Academic License' in (args.reference/name).read_text(encoding='utf-8')]
    evidence = {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                for p in args.output.iterdir() if p.suffix in ('.json','.log') and p.name!='provenance.json'}
    result = dict(
        source_sha=cfg['source_sha'],validation_source_sha=git(REPO,'rev-parse','HEAD'),upstream_sha=cfg['upstream_sha'],
        upstream_remote=git(args.reference,'remote','get-url','origin'),
        upstream_clean=True,upstream_submodules=submodules,
        license_named_files=licenses,
        academic_license_headers=academic_headers,
        redistribution_conclusion='No project-wide redistribution grant found. Generated C headers carry institution-specific MathWorks Academic License restrictions. This validation grants no implementation reuse permission.',
        upstream_module_sha256=sources,validation_scripts_sha256=scripts,evidence_sha256=evidence,
    )
    (args.output/'provenance.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(f'Pinned clean upstream; hashed {len(sources)} upstream files, {len(scripts)} validation inputs/scripts.')
