"""Read-only validation of saved Round 6 evidence. Never starts MATLAB or MuJoCo."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import unquote
from urllib.request import urlopen
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from PIL import Image
from tools.spec_tools import ROOT, load_yaml
from tools.state_io import atomic_json, read, digest
from tools.artifact_tools import file_hash
from tools.workbench import Workbench, owner
from tools.closeout_state import verify_run

out = Path(__file__).resolve().parent
books = {}
for name in ('round6_compute', 'round6_ready'):
    book = Workbench(ROOT / 'runs' / name)
    with owner(book.root):
        book.load()
    with zipfile.ZipFile(book.root / 'source_snapshot.zip') as archive:
        assert all(hashlib.sha256(archive.read(p)).hexdigest() == h for p, h in book.state['request']['sources'].items())
    books[name] = dict(status=book.state['status'], remaining=book.remaining(), evidence_count=len(book.state['evidence']))
    if name == 'round6_ready':
        assert book.state['status'] == 'WAITING_FOR_KEY' and not book.state['model_calls'] and not book.state['attempts']
root = ROOT / 'runs/round6_compute'
state = read(root / 'state.json')
attempt = next(a for a in state['attempts'] if a['tool'] == 'evaluate_candidate')
result = attempt['result']['data']
run = root / result['run']
verify_run(run)
assert digest(load_yaml(run / 'design_input.yaml')) == result['design_hash'] == state['candidates'][0]['design_hash']
events = [json.loads(line) for line in (run / 'trace.jsonl').read_text(encoding='utf-8').splitlines()]
starts = [e['operation'] for e in events if e['event_type'] == 'TOOL_STARTED']
counts = {name: starts.count(name) for name in ('matlab_session', 'analyze_workspace', 'plan_pcc_reach', 'pcc_centerline', 'run_task')}
assert counts == dict(matlab_session=1, analyze_workspace=1, plan_pcc_reach=1, pcc_centerline=1, run_task=1)
assert result['canonical_task_status'] == 'FAIL' and result['evidence_role'] == 'new_computation'
class Links(HTMLParser):
    links = []
    def handle_starttag(self, tag, attrs):
        self.links.extend(unquote(v) for k,v in attrs if k in ('href', 'src'))
links = Links()
links.feed((root / 'index.html').read_text(encoding='utf-8'))
assert all((root / name).is_file() for name in links.links)
gif = root / 'attempts/003_observe_candidate/motion.gif'
with Image.open(gif) as image:
    frames = image.n_frames
    for index in range(frames):
        image.seek(index)
        image.load()
process = subprocess.Popen([sys.executable, 'examples/workbench.py', 'observe', str(root), '--port', '8767'], cwd=ROOT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
try:
    page = ''
    for _ in range(25):
        try:
            page = urlopen('http://127.0.0.1:8767', timeout=2).read().decode('utf-8')
            break
        except OSError:
            time.sleep(.2)
    assert '模型与候选设计' in page and 'c000' in page and '0.17116166894090315' in page
finally:
    process.terminate()
    process.wait(timeout=10)
frozen = subprocess.check_output(['git', 'diff', '5fe79f8', '--name-only', '--', 'tasks', 'benchmarks', 'metrics', 'physics_contracts',
                                 'docs/evidence/round5', 'docs/evidence/round4'], cwd=ROOT, text=True).strip()
assert not frozen
record = dict(status='PASS', books=books, actual_compute=counts,
              development_totals=dict(matlab_session_start_attempts=3, matlab_start_successes=2,
                                      matlab_mathematical_calls=3, mujoco_simulations=1, live_deepseek_calls=0),
              result=dict(candidate_id='c000', position_error_m=result['position_error_m'],
                          predicted_position_error_m=result['predicted_position_error_m'], canonical_task_status=result['canonical_task_status'],
                          evidence_role='new_computation', run=result['run']),
              focused_tests=dict(distinct_tests=3, executions=4, backend_calls=0,
                                 note='Three focused tests; only candidate-result identity test repeated after fixing mutable metadata alias'),
              observation=dict(local_http=200, links_verified=len(links.links), gif_frames=frames),
              delivery=dict(integration_code_completed=True, real_computation_restored=True,
                            live_model_feedback_loop_verified=False, robot_task_achieved=False, blocker='DEEPSEEK_API_KEY not provided'),
              frozen_truth_diff=frozen, user_untracked_file_sha256=file_hash(ROOT / 'round3_total_codex_prompt_6d857fb.md'))
atomic_json(out / 'verification.json', record)
print(json.dumps(record, ensure_ascii=True, indent=2))
