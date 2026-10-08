"""Read-only scoped publication review; records no matched sensitive values."""
import re
import subprocess
from pathlib import Path
from tools.context_assembly import _no_secrets
from tools.research_direct_validation import ROOT, BASE, sha, history
from tools.state_io import atomic_json, read

OUT=Path(__file__).resolve().parent
pending=subprocess.check_output(['git','diff','--name-only',BASE,'HEAD'],cwd=ROOT,text=True).splitlines()
working=subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT,text=True).splitlines()
untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
paths=sorted(set(pending+working+untracked))
specific={'docs/research_mainline3_v1_capabilities.md','tools/research_direct_validation.py','tools/research_mainline3.py',
    'tools/research_validation_gate.py','tests/test_research_direct_validation.py','tests/test_research_validation_gate.py'}
prefixes=('evidence/research_direct_validation_20261008/','evidence/research_direct_validation_20261008_offline/')
assert paths and all(p in specific or p.startswith(prefixes) for p in paths)
rules={
    'provider_key_shape':re.compile(r'\bsk' + r'-[A-Za-z0-9_-]{16,}\b'),
    'authorization_value':re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._-]{16,}'),
    'private_key':re.compile('-'*5+r'BEGIN [A-Z ]*PRIVATE KEY'+'-'*5),
    'github_token':re.compile(r'\b(?:gh[pousr]' + r'_[A-Za-z0-9]{30,}|github_pat_' + r'[A-Za-z0-9_]{40,})\b')}
findings=[]
for path in paths:
    p=ROOT/path
    assert p.is_file() and not path.endswith(('.env','.pem','.key','.sqlite','.db'))
    body=p.read_text(encoding='utf8')
    if p.suffix=='.json':_no_secrets(read(p))
    for label,rule in rules.items():
        if rule.search(body):findings.append(dict(path=path,rule=label))
assert not findings, 'SECRET_SHAPE_REVIEW_BLOCKED'
assert history()==read(OUT/'historical_before.json')
atomic_json(OUT/'publication_review.json',dict(baseline_remote_sha=BASE,
    reviewed_code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
    pending_commits=subprocess.check_output(['git','log','--format=%H %s',BASE+'..HEAD'],cwd=ROOT,text=True).splitlines(),
    scoped_file_inventory={p:dict(sha256=sha(ROOT/p),bytes=(ROOT/p).stat().st_size) for p in paths
        if not p.endswith(('publication_review.json','sha256_manifest.json'))},
    secret_findings=findings,existing_json_secret_field_check=True,string_rules=list(rules),
    manual_review='All code/test/doc changes since the reviewed remote baseline inspected; only bounded direct wrapper, '
                  'collection/provenance gate, scoped offline failures and real stopped evidence. '
                  'No credential files, authentication headers, environment values or raw HTTP error bodies staged. '
                  'Raw normal responses are authorized non-secret scientific-history investigation evidence, including invalid partial returns.',
    unrelated_changes=False,old_evidence_and_ledgers_unchanged=True,
    runtime_code_frozen=True,production_changes_after_launch=False,
    real_activity_stopped=True,followup_model_requests=0,
    publish='Ordinary authorized feat/gvs-dynamics push; verify remote SHA afterwards. No force/history rewrite.',
    boundary='Pattern and field scans reduce publication risk; no claim of an infallible secret scanner.'))
print('SCOPED_PUBLICATION_REVIEW_PASSED',len(paths),'files; sensitive values not printed')
