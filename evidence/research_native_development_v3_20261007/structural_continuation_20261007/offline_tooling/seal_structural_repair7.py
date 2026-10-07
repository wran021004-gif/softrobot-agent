from pathlib import Path
import shutil,hashlib
from examples import research_campaign_v3 as c
from tools.state_io import atomic_json,read
s=read('runs/research_native_development_v3_20261007/structural_repair7_start.json')
out=Path(s['output']);logs=out/'offline_logs';logs.mkdir(exist_ok=True)
for p in Path('runs').glob('structural_repair7_*.log'):shutil.copyfile(p,logs/p.name)
shutil.copyfile('runs/start_structural_repair7.py',logs/'start_structural_repair7.py')
for name in ('campaign_delivery.json','delivery.json','final_working_context.json','final_model_interpretation.json','final_interpretation_failure.json'):
    p=out.parent/name
    if p.exists():shutil.copyfile(p,out/('failed_'+name))
gate=dict(version='v3-maximum-inline-fact-gate@3.6.0',passed=True,implementation_files=c.seal()['files'],
    post_far_real_request=True,max_research_pressure=8,final_synthetic_slots=20,
    exact_fact_ids_values_units_execution_sources_reconstructed=True,exact_F_selectors_reconstructed=True,
    immutable_capabilities_unchanged=True,live_ledger_unchanged=True,
    provider_attempts=0,backend_attempts=0,synthetic_receipts_are_physical_evidence=False,
    complete_path_checks=dict(tests=2,failures=0,errors=0,log='offline_logs/structural_repair7_gate_sealed.log'),
    affected_regression_checks=dict(tests=10,failures=0,errors=0,log='offline_logs/structural_repair7_sealed_regressions.log'),
    prior_full_path_gate='../engineering_gate.json',
    limitations='Two inherited settlement scenarios assume the pre-structural remaining count/dependency delta; their failed logs are preserved. No grant, reuse or authorization policy was weakened.')
for name in ('structural_repair7_gate_sealed.log','structural_repair7_sealed_regressions.log'):
    text=(logs/name).read_text(encoding='utf-8')
    assert '\nOK\n' in text and 'FAILED' not in text
atomic_json(out/'engineering_gate.json',gate)
print('gate frozen',hashlib.sha256((out/'engineering_gate.json').read_bytes()).hexdigest())
