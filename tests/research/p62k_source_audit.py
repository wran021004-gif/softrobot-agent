"""Recheck local historical source hashes only; never open a scientific worker.

Run from the integration checkout. Missing local sources are reported explicitly;
the portable index and traces remain usable without the original private Stores.
"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def file_hash(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def audit():
    manifest=json.loads((ROOT/'docs/research/p62k_source_audit.json').read_text(encoding='utf8'))
    sources=dict(manifest['sources'])
    for case in manifest['cases'].values():
        trace=json.loads((ROOT/case['path']).read_text(encoding='utf8'))
        identity=trace.get('source_identity',{})
        if identity.get('original_store_sha256'):
            source=identity['original_store']
            sources[source]=dict(path=source,sha256=identity['original_store_sha256'])
    results=[]
    for source in sources.values():
        path=Path(source['path'])
        actual=file_hash(path) if path.is_file() else None
        results.append(dict(path=str(path),expected_sha256=source['sha256'],actual_sha256=actual,
            status='unavailable_local_source' if actual is None else 'match' if actual==source['sha256'] else 'changed'))
    return dict(version='p62k_source_recheck_v1',source_files=len(results),
        matched=sum(r['status']=='match' for r in results),
        changed=sum(r['status']=='changed' for r in results),
        unavailable=sum(r['status']=='unavailable_local_source' for r in results),
        results=results,scientific_executions=0,provider_requests=0,
        scope='Read-only raw file hashes. Original Store identities and curated source chains; no new scientific validity or task acceptance claim.')


if __name__=='__main__':
    result=audit()
    output=ROOT/'docs/research/p62k_source_recheck.json'
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({k:v for k,v in result.items() if k!='results'}))
    raise SystemExit(1 if result['changed'] or result['unavailable'] else 0)
