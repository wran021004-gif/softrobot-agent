"""Focused offline acceptance, saved history integrity and generated directory."""
import argparse
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='runs/public_interface_review')
    args=parser.parse_args()
    from tools.spec_tools import ROOT
    from tools.artifact_tools import file_hash
    from tools.state_io import atomic_json,read
    from tools.public_catalog import catalog
    output=Path(args.output).resolve();output.mkdir(parents=True,exist_ok=True)
    directory=catalog();atomic_json(output/'catalog.json',directory)
    protected=[ROOT/p for p in ('runs/round9_reach/state.json','runs/round9_reach/budget.json','runs/round9_budget.json',
        'tasks/reach_free/task.yaml','tasks/reach_free/environment.yaml','configs/experiments/round9_grant.json',
        'configs/run.yaml','configs/simulator.yaml','metrics/reach.py','tools/pcc_math.py','tools/reach_dynamics.py')]
    for manifest in (ROOT/'runs/round9_reach/observations/videos').glob('*/native_video.json'):
        protected.append(manifest)
        info=read(manifest)
        protected.extend(ROOT/'runs/round9_reach'/p for p in (*info['source_hashes'],*info['artifact_hashes']))
    before={p.relative_to(ROOT).as_posix():file_hash(p) for p in protected}
    modules=['tests.test_public_tools','tests.test_dynamic_runtime','tests.test_dynamic_context',
        'tests.test_dynamic_closeout','tests.test_round9','tests.test_workbench','tests.test_deepseek_design']
    suite=unittest.defaultTestLoader.loadTestsFromNames(modules)
    stream=io.StringIO()
    with patch('mujoco.mj_step',side_effect=AssertionError('Acceptance forbids new dynamics steps')), \
         patch('tools.reach_dynamics.DynamicsBackends.simulate',side_effect=AssertionError('Acceptance forbids new backend rollouts')):
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (output/'tests.log').write_text(stream.getvalue(),encoding='utf8')
    after={p:file_hash(ROOT/p) for p in before}
    # Check generated browser script syntax using installed Node, without opening a viewer.
    pages=sorted((ROOT/'runs/public_interface_tests').glob('*/observations/specimen_alpha_matlab.html'),key=lambda p:p.stat().st_mtime)
    js_check=None
    if pages:
        script=pages[-1].read_text(encoding='utf8').split('<script>',1)[1].split('</script>',1)[0]
        (output/'observation.js').write_text(script,encoding='utf8')
        checked=subprocess.run(['node','--check',str(output/'observation.js')],capture_output=True,text=True)
        js_check=dict(exit_code=checked.returncode,stderr=checked.stderr)
    declaration_errors=[t for t in directory['library'] if t['implementation_status']=='IMPLEMENTED' and t['declaration_check']!='ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED']
    report=dict(status='PASS' if result.wasSuccessful() and before==after and not declaration_errors and js_check and js_check['exit_code']==0 else 'FAIL',
        base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        python=sys.version,tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),modules=modules,
        test_log=str(output/'tests.log'),public_tool_count=len(directory['tools']),library_count=len(directory['library']),
        library_declaration_errors=declaration_errors,history_and_frozen_files_unchanged=before==after,protected_sha256=after,
        browser_script_syntax=js_check,
        evidence_levels=dict(code='Schemas, native adapters, durable receipts, permissions, failure mapping, finite-difference Jacobian and JS syntax.',
            synthetic='Injected provider responses and workers; independent non-task geometry and shifted-time saved fixture.',
            real_backend='MuJoCo XML/model and mj_forward static checks only; actual saved MATLAB/MuJoCo video/source bytes reused and hash checked.',
            not_performed='No new MATLAB dynamics, MuJoCo mj_step, live LLM API, fresh native video render or visual-understanding acceptance.'),
        new_dynamics_steps=0,new_backend_rollouts=0,live_model_calls=0)
    atomic_json(output/'validation.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='protected_sha256'},ensure_ascii=False,indent=2))
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
