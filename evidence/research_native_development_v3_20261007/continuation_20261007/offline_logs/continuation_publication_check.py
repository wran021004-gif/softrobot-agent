"""Inspect only the intended appended evidence and task documents for publication."""
from pathlib import Path
import gzip,hashlib,json,re,subprocess
from tools.state_io import atomic_json

root=Path('evidence/research_native_development_v3_20261007/continuation_20261007')
files=[p for p in root.rglob('*') if p.is_file()]
files += [Path(p) for p in ('docs/research_native_development_v3.md','docs/CURRENT_STATUS.md')]
# Exact credential comparisons happen only in memory; no credential is emitted.
env=Path.home()/'.codex/.env'
secrets=[]
for line in env.read_text(encoding='utf-8-sig').splitlines():
    key,sep,value=line.partition('=')
    if sep and key.strip().endswith(('_KEY','_TOKEN','_SECRET','_PASSWORD')):
        value=value.strip().strip('\"\'')
        if len(value)>12:secrets.append(value)
findings=[];compressed=0;content_addresses=0
def inspect(data,path):
    global compressed
    if data[:2]==b'\x1f\x8b':
        compressed+=1;inspect(gzip.decompress(data),path+'::<gzip>');return
    views=[]
    for encoding in ('utf-8-sig','utf-16-le','utf-16-be'):
        try:views.append(data.decode(encoding))
        except UnicodeError:pass
    for value in views:
        if any(s in value for s in secrets):findings.append(dict(path=path,reason='Credential value present'))
        if re.search(r'Bearer\s+[A-Za-z0-9_-]{15,}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----',value):
            findings.append(dict(path=path,reason='Secret-shaped credential material'))
    try:parsed=json.loads(data)
    except (ValueError,UnicodeError):return
    def walk(value):
        if isinstance(value,dict):
            for k,v in value.items():
                if k.lower() in ('authorization','api_key','access_token','password','private_key') and isinstance(v,str) and v:
                    findings.append(dict(path=path,reason='Populated secret field',field=k))
                walk(v)
        elif isinstance(value,list):
            for child in value:walk(child)
    walk(parsed)
for path in files:
    data=path.read_bytes();inspect(data,path.as_posix())
    if re.fullmatch('[a-f0-9]{64}',path.stem) and path.parent.name=='artifacts':
        assert hashlib.sha256(data).hexdigest()==path.stem,path
        content_addresses+=1
    if path.name=='sha256_manifest.json':
        for name,expected in json.loads(data).items():
            assert hashlib.sha256((path.parent/name).read_bytes()).hexdigest()==expected,(path,name)
old_root='evidence/research_native_development_v3_20261007'
old_changes=subprocess.check_output(['git','diff','--name-only','6094cb3','--',old_root],text=True).splitlines()
assert all(p.startswith(old_root+'/continuation_20261007/') for p in old_changes),old_changes
assert not findings,findings
result=dict(status='passed',scope='Appended continuation evidence and two task documents only',
    files_inspected=len(files),bytes_inspected=sum(p.stat().st_size for p in files),
    gzip_payloads_decoded=compressed,content_addresses_verified=content_addresses,
    encodings_checked=['utf-8','utf-16-le','utf-16-be'],credential_values_emitted=False,
    populated_secret_fields=0,old_sealed_evidence_changes=0,
    excluded=['Credential files','Unrelated workspace files','Executable ledger SQLite','Git internals'])
atomic_json(root/'publication_review.json',result)
print(json.dumps(result))
