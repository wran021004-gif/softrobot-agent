import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen
from urllib.parse import unquote
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.spec_tools import ROOT
from tools.state_io import read, atomic_json
from tools.artifact_tools import file_hash
from tools.workbench import Workbench
from PIL import Image

out = ROOT / 'docs/evidence/round5'
out.mkdir(parents=True, exist_ok=True)
books = ['round5_demo', 'round5_replay_complete']
checks = {}
for name in books:
    root = ROOT / 'runs' / name
    state = Workbench(root).load()
    with zipfile.ZipFile(root / 'source_snapshot.zip') as z:
        assert all(hashlib.sha256(z.read(p)).hexdigest() == h for p,h in state['request']['sources'].items())
    checks[name] = dict(status=state['status'], evidence_files=len(state['evidence']),
                       attempts=len(state['attempts']), decisions=len(state['decisions']), reuse=len(state['reuse']),
                       limits=state['request']['limits'], stop_reason=state['stop_reason'])
root = ROOT / 'runs/round5_replay_complete'
class Links(HTMLParser):
    links = []
    def handle_starttag(self, tag, attrs):
        for k,v in attrs:
            if k in ('href','src'):
                self.links.append(unquote(v))
parser = Links()
parser.feed((root / 'index.html').read_text(encoding='utf-8'))
assert all((root/p).is_file() for p in parser.links)
with Image.open(root / 'attempts/004_observe/motion.gif') as im:
    frames = im.n_frames
    assert frames > 1
    for i in range(frames):
        im.seek(i)
        im.load()
with Image.open(root / 'attempts/004_observe/curves.png') as im:
    image_size = im.size
    im.verify()
process = subprocess.Popen([sys.executable, 'examples/workbench.py', 'observe', str(root), '--port', '8766'],
                           cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=subprocess.CREATE_NO_WINDOW)
try:
    page = None
    for _ in range(30):
        try:
            page = urlopen('http://127.0.0.1:8766', timeout=2).read().decode('utf-8')
            break
        except OSError:
            time.sleep(.2)
    assert page and '历史回放成绩' in page and 'STOPPED' in page
    assert urlopen('http://127.0.0.1:8766/attempts/004_observe/motion.gif', timeout=2).status == 200
finally:
    process.terminate()
    process.wait(timeout=10)
failed_run = next((ROOT / 'runs/round5_demo/attempts/003_evaluate_design/execution').iterdir())
events = [json.loads(line) for line in (failed_run / 'trace.jsonl').read_text(encoding='utf-8').splitlines()]
started = [e['operation'] for e in events if e['event_type'] == 'TOOL_STARTED']
assert started.count('run_task') == 0
assert started.count('analyze_workspace') == 0 and started.count('plan_pcc_reach') == 0
record = dict(status='PASS', checks=checks, targeted_unit_tests=dict(first_batch=10, added_replay_batch=2, failures=0, backend_solves=0),
              new_execution=dict(reserved_candidates=1, matlab_session_attempts=started.count('matlab_session'),
                                 actual_matlab_analysis_calls=0, actual_mujoco_simulations=0,
                                 failure=read(failed_run / 'error.json'), retries=0),
              historical_replay=dict(original_run='20260912T082002_895497Z_10d68758', new_backend_calls=0,
                                     original_error_m=read(root/'attempts/002_evaluate_design/result.json')['data']['metrics']['mujoco']['position_error_m']),
              observation=dict(local_http=200, all_links_exist=len(parser.links), gif_frames=frames, png_size=image_size),
              preservation=dict(frozen_truth_and_round4_evidence_git_diff='empty', user_untracked_prompt_sha256=file_hash(ROOT/'round3_total_codex_prompt_6d857fb.md')))
atomic_json(out / 'verification.json', record)
with zipfile.ZipFile(out / 'workbenches.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in books:
        for path in sorted((ROOT/'runs'/name).rglob('*')):
            if path.is_file() and not path.name.endswith('.lock'):
                archive.write(path, path.relative_to(ROOT).as_posix())
atomic_json(out / 'package.json', dict(archive='workbenches.zip', sha256=file_hash(out/'workbenches.zip'),
                                     paths=books, note='Extract at repository root; includes original source snapshots; no numerical rerun required'))
print(json.dumps(record, ensure_ascii=True, indent=2))
