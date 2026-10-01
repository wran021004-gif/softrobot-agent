"""Generate or verify SHA-256 records for exact committed Git blob bytes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.state_io import atomic_json


def git(*args):return subprocess.check_output(['git',*args])


def records(revision,root,excluded):
    names=git('ls-tree','-r','--name-only',revision,'--',root).decode('utf8').splitlines()
    result=[]
    for name in names:
        if name==excluded:continue
        body=git('cat-file','blob',revision+':'+name)
        result.append(dict(path=name,size_bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),
            git_object_id=git('rev-parse',revision+':'+name).decode().strip()))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['generate','verify'])
    parser.add_argument('--root',required=True);parser.add_argument('--revision',default='HEAD')
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    output=args.output.as_posix();actual=records(args.revision,args.root,output)
    if args.action=='generate':
        atomic_json(args.output,dict(algorithm='SHA-256',byte_domain='exact Git blob content',
            revision=subprocess.check_output(['git','rev-parse',args.revision],text=True).strip(),
            newline_policy='UTF-8 text with LF in Git; working-tree byte hashes remain a separate historical record.',
            manifest_self_excluded=True,files=actual))
        print('generated '+str(args.output)+' with '+str(len(actual))+' Git blob records')
        return
    expected=json.loads(args.output.read_text(encoding='utf8'))['files']
    if expected!=actual:raise ValueError('GIT_BLOB_MANIFEST_MISMATCH')
    print('verified '+str(args.output)+' against '+args.revision+' ('+str(len(actual))+' blobs)')


if __name__=='__main__':main()
