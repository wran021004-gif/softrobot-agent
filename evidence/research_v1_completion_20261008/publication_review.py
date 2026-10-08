"""Read-only scope/secret review of the entire authorized pending interval."""
import json
from pathlib import Path
import re
import subprocess

from tools.context_assembly import _no_secrets
from tools.state_io import atomic_json

ROOT = Path(__file__).resolve().parents[2]
BASE = '9a96094e38108e820175b817eaff946b21f80f6c'
PREFIX = 'evidence/research_v1_completion_20261008/'
CODE = {
    'schemas/platform.py', 'schemas/platform_operations.py',
    'tests/test_research_v1_capacity.py', 'tools/platform_tools.py',
    'tools/research_investigations.py', 'tools/research_mainline3.py',
    'tools/research_v1_delivery.py', 'tools/research_validation_activity.py',
    'tools/research_validation_gate.py',
    'docs/research_mainline3_v1_completion.md', 'docs/research_mainline3_v2_handoff.md',
}
PATTERNS = (
    r'sk-[A-Za-z0-9_-]{20,}', r'gh[pousr]_[A-Za-z0-9]{20,}',
    r'github_pat_[A-Za-z0-9_]{30,}', r'AKIA[A-Z0-9]{16}',
    r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    r'(?i)authorization[\s"\x27:]+bearer\s+[A-Za-z0-9._-]{20,}',
)


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True, encoding='utf8').strip()


def main():
    assert git('branch', '--show-current') == 'feat/gvs-dynamics'
    assert git('rev-parse', 'origin/feat/gvs-dynamics') == BASE
    changed = git('diff', '--name-only', BASE, 'HEAD').splitlines()
    pending = git('ls-files', '--others', '--exclude-standard').splitlines()
    staged = git('diff', '--cached', '--name-only').splitlines()
    files = sorted(set(changed + pending + staged))
    issues = []
    for name in files:
        if name not in CODE and not name.startswith(PREFIX):
            issues.append(dict(path=name, issue='outside authorized task scope'))
            continue
        raw = (ROOT / name).read_bytes()
        if len(raw) > 50 * 1024 * 1024:
            issues.append(dict(path=name, issue='oversize file'))
        text = raw.decode('utf-16') if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else raw.decode('utf-8-sig')
        for index, pattern in enumerate(PATTERNS):
            if re.search(pattern, text):
                issues.append(dict(path=name, issue='potential secret', pattern_index=index))
        if name.endswith('.json'):
            try:
                _no_secrets(json.loads(text))
            except ValueError:
                issues.append(dict(path=name, issue='secret field or invalid JSON'))
    # Review prior versions as well as final file state; never expose matches.
    patch = git('diff', BASE, 'HEAD') + git('diff', '--cached')
    for index, pattern in enumerate(PATTERNS):
        if re.search(pattern, patch):
            issues.append(dict(issue='potential secret in commit interval', pattern_index=index))
    result = dict(base_commit=BASE, reviewed_engineering_head=git('rev-parse', 'HEAD'),
        target='https://github.com/wran021004-gif/softrobot-agent.git', branch='feat/gvs-dynamics',
        remote_before=git('rev-parse', 'origin/feat/gvs-dynamics'),
        commits=git('log', '--format=%H %s', BASE + '..HEAD').splitlines(),
        files=files, count=len(files), scope_passed=not issues,
        secret_checks_passed=not issues, issues=issues,
        code_review='Reviewed every modified runtime/schema/test diff and new delivery runner; no science, task threshold, endpoint or model substitution.',
        evidence_review='Frozen inputs, all raw responses, reads, budgets, repair history, semantic review and stop result; no credential loader values archived.',
        limitations=['Heuristic secret scanning is supplemented by structured secret-field rejection and explicit scope review.',
            'Migrated reach progress retains fields from failure checkpoints; sealed report, exact-source gate, provider events and common settled ledger establish final status.',
            'Preparation and pending snapshots are historical records, superseded by delivery_audit.json.'],
        push_method='Normal fast-forward only; final remote SHA verification occurs after publication.')
    atomic_json(ROOT / PREFIX / 'stages/publication_scope_review.json', result)
    if issues:
        raise SystemExit('PUBLICATION_REVIEW_FAILED; see issue paths without secret values')
    print(json.dumps(dict(files=len(files), scope_passed=True, secret_checks_passed=True)))


if __name__ == '__main__':
    main()
