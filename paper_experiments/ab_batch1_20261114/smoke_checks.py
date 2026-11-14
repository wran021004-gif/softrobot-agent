"""Issue #1's bounded checks; no Provider requests or physical execution."""
import csv
import json
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_batch as runner

subprocess.run([sys.executable,str(HERE/'summarize.py')],check=True,capture_output=True)
rows=list(csv.DictReader((HERE/'batch1_results_repaired.csv').open(encoding='utf-8-sig')))
expected=dict(T01='codex-expert-T01-20261113-s1',T04='codex-expert-T04-20261113-core029-interior',
              T07='codex-expert-T07-20261113',**{'PHS-2D':'psd2d-core-fresh-20261112'})
for task,run in expected.items():
    row=next(r for r in rows if r['task_id']==task and r['method']=='C')
    assert row['cost_match_run_id']==run
    assert all(r['run_id']==run for r in json.loads(row['cost_records']))
phs=next(r for r in rows if r['task_id']=='PHS-2D' and r['method']=='C')
assert phs['integration_steps']=='1248000' and json.loads(phs['topology'])['flexible_segments']==7
assert next(r for r in rows if r['task_id']=='T04' and r['method']=='B')['scientific_result']=='INITIAL_CONDITION_FAILED'
assert all(r['scientific_result']=='QUALIFICATION_FAILED' for r in rows if r['task_id']=='PHS-2D' and r['method']!='C')

math=dict(operation='math',arguments=dict(candidate='c1',operation='jacobian'))
runner.validate_step(dict(decision='Explicit primitive',commands=[math]),'B')
for malformed in [dict(decision='No math for A',commands=[math]),dict(decision=7,commands=[]),
                  dict(decision='Wrong arguments',commands=[dict(operation='evaluate',arguments=[])]),
                  dict(decision='Unknown operation',commands=[dict(operation='shell',arguments={})])]:
    try:runner.validate_step(malformed,'A')
    except runner.CommandError:pass
    else:raise AssertionError('Invalid command admitted')
r=runner.Run.__new__(runner.Run);r.method='A';r.task='T02';r.s=dict(candidate_count=0)
r.base,r.space,r.protocol=runner.inputs('T02');r.guard=lambda *args:None
try:r.generate(dict(generation=dict(segment_count=-1)))
except ValueError:pass
else:raise AssertionError('Invalid GenerationRequest admitted')
assert r.s['candidate_count']==0

dense=dict(candidate='c1',condition='both_directions',validity='invalid',accepted=None,diagnostics=dict(observations=['dense']*10000),
           required_case_results=dict(plus_x=dict(validity='qualification_failed',failed_checks=['static_balance'])))
assert len(json.dumps(runner.compact_feedback(dense)))<1500
assert 'observations' not in runner.compact_feedback(dense)
assert runner.inputs('T04')[2]['cases'][0]['acceptance']['parameters']['initial_static_balance_max_nm']==1e-7
reservation=runner.token_reservation(dict(messages=[dict(role='user',content='abc123 '*100)]))
assert reservation['estimated_input_tokens']<len(json.dumps(dict(messages=[dict(role='user',content='abc123 '*100)])))

checks=[runner.check_task(t) for t in runner.BATCH2]
t10=next(c for c in checks if c['task']=='T10')
assert [c['condition'] for c in t10['cases'] if c['role']=='required']==['positive_y','negative_y','no_impulse']
assert len([c for c in t10['cases'] if c['role']=='control'])==2
assert next(c for c in checks if c['task']=='T08')['source_classification']=='development_not_registered_SELECT'
print(json.dumps(dict(summary='PASS: four exact FULL run IDs; seed excluded; raw/scientific states separate',
                     runner='PASS: command contract, invalid generation count, compact passive feedback, A/B permissions, unchanged 1e-7 threshold',
                     token_estimator=reservation['estimator'],task_loading=checks,provider_requests=0,physics_executions=0)))
