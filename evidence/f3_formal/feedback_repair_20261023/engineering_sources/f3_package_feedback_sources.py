"""Publish only reviewable sources and deterministic summaries, never raw sessions."""
import hashlib
import shutil
from tools.research.config import ROOT
from tools.research.agent import load_credential
from tools.research.state import state
from tools.platform_host import Host
from tools.state_io import atomic_json
from pathlib import Path
h=Host(ROOT/'runs/research/f3-autonomous-20261022-01','f3-autonomous-20261022-01',actor='unified-research')
folder=ROOT/'evidence/f3_formal/feedback_repair_20261023'
target=folder/'engineering_sources';target.mkdir(exist_ok=True)
files=['f3_formal_followthrough.py','f3_formal_export.py','f3_continuous_healthcheck.py',
    'f3_feedback_repair_audit.py','f3_feedback_regression.py','f3_apply_feedback_migration.py','f3_package_feedback_sources.py']
manifest=[]
for name in files:
    source=ROOT/'runs'/name;dest=target/name;shutil.copyfile(source,dest)
    manifest.append(dict(source='runs/'+name,published=str(dest.relative_to(ROOT)),sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
load_credential(Path(state(h)['spec']['runtime']['credentials_reference']).expanduser())
import os
secret=os.environ['DEEPSEEK_API_KEY'].encode()
paths=[*folder.rglob('*'),ROOT/'docs/research/f3_feedback_repair.md']
assert not any(secret in p.read_bytes() for p in paths if p.is_file())
atomic_json(folder/'source_manifest.json',dict(files=manifest,actual_provider_credential_scan='no_matches',
    raw_store_or_sdk_export_included=False))
atomic_json(folder/'preliminary_validation_history.json',dict(
    initial_reporting_pass=dict(tests=26,failures=2,errors=6,
        corrected=['reporter priority mistakenly accessed host','legacy textual conclusion handling','missing-file navigation'],
        unavailable_historical_fixtures=2),
    second_reporting_pass=dict(tests=41,failures=0,errors=1,corrected='gzip synthetic fixture Store.put contract'),
    third_expanded_pass=dict(tests=51,failures=1,errors=1,
        corrected=['gzip original-artifact raw read','source edited while hash-bound recovery fixture running']),
    final_receipt='offline_tests.json',no_live_provider_or_physical_calls=True))
print('Source snapshots packaged; credential scan passed; raw Store/SDK exports excluded.')
