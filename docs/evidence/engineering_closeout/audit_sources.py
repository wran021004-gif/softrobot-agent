"""Reproduce byte-level correspondence; never rewrite the historical manifest."""
import collections
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
COMMIT = 'f2df1b0ee50ce633b39df6b187798f6f87d73605'
MANIFEST = ROOT/'docs/evidence/framework/source_manifest.json'


def sha(data):return hashlib.sha256(data).hexdigest()
def lf(data):return data.replace(b'\r\n',b'\n')


def main():
    manifest=json.loads(MANIFEST.read_text(encoding='utf8'))
    archive=OUT/'original_source_representations.zip'
    originals={}
    if archive.exists():
        with zipfile.ZipFile(archive) as z:originals={p:z.read(p) for p in z.namelist()}
    records=[];counts=collections.Counter()
    for path,expected in manifest.items():
        blob=subprocess.run(['git','show',COMMIT+':'+path],cwd=ROOT,capture_output=True,check=True).stdout
        work=(ROOT/path).read_bytes()
        original=work if sha(work)==expected else originals.get(path)
        if sha(blob)==expected:
            original=blob;status='EXACT_GIT_BYTES'
        elif original is not None and sha(original)==expected:
            status='LINE_ENDINGS_ONLY' if lf(original)==lf(blob) else 'CONTENT_DIFFERENCE'
            originals[path]=original
        else:status='ORIGINAL_BYTES_UNRECOVERABLE'
        counts[status]+=1
        records.append(dict(path=path,status=status,historical_sha256=expected,git_raw_sha256=sha(blob),
            git_lf_sha256=sha(lf(blob)),original_lf_sha256=sha(lf(original)) if original is not None else None,
            original_crlf_count=original.count(b'\r\n') if original is not None else None,
            original_bare_lf_count=original.count(b'\n')-original.count(b'\r\n') if original is not None else None))
    if not archive.exists():
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for path,data in sorted(originals.items()):z.writestr(path,data)
    report=dict(commit=COMMIT,manifest_sha256=sha(MANIFEST.read_bytes()),counts=dict(counts),records=records,
        normalization='CRLF -> LF only for comparison; original SHA256 values remain unchanged.',
        original_archive_sha256=sha(archive.read_bytes()),
        conclusion='No computation replay needed when all differences are byte-identical or line-endings-only.')
    (OUT/'source_correspondence.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(dict(counts))


if __name__=='__main__':main()
