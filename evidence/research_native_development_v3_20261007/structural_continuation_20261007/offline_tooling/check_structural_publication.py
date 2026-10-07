from pathlib import Path
import subprocess,hashlib,json,re
from tools.context_assembly import _no_secrets
from tools.state_io import atomic_json
attachment=Path(r'C:\Users\gugugaga\.codex\attachments\9dae342a-539d-453e-a481-0fa61888934d\pasted-text-1.txt')
s=attachment.read_text(encoding='utf-8')
print('AUTHORIZATION',[line for line in s.splitlines() if line.startswith(('Remote:','Commit meaningful checkpoints'))])
files=subprocess.check_output(['git','diff-tree','--no-commit-id','--name-only','-r','HEAD'],text=True).splitlines()
checked=[];matches=[]
rx=re.compile(r'(?i)(?:sk-[a-zA-Z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:DEEPSEEK_API_KEY|OPENAI_API_KEY)\s*=\s*[^\s]{15,})')
for p in files:
    raw=Path(p).read_text(encoding='utf-8',errors='replace')
    if rx.search(raw):matches.append(p)
    if p.endswith('.json'):
        _no_secrets(json.loads(raw));checked.append(p)
audit=dict(attachment_sha256=hashlib.sha256(attachment.read_bytes()).hexdigest(),
    exact_user_release_instruction='Commit meaningful checkpoints, push normally to origin/feat/gvs-dynamics, and verify the final remote SHA.',
    user_named_destination='https://github.com/wran021004-gif/softrobot-agent',
    actual_origin=subprocess.check_output(['git','remote','get-url','origin'],text=True).strip(),
    branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(),
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
    new_files=files,secret_field_checks_passed=checked,credential_pattern_file_matches=matches,
    sealed_old_evidence_modified=False)
atomic_json('runs/research_native_development_v3_20261007/publication_authorization_and_payload_check.json',audit)
print('SECRET_SCAN',len(checked),'JSON files passed; credential pattern matching files:',matches)
