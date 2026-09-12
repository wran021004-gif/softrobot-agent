"""Retain real backend regression evidence; optional experiments are TEST_ONLY."""
import argparse
import json
from pathlib import Path
import sys
import zipfile
import hashlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.spec_tools import ROOT
from tools.harness import run_reach, _snapshot_sources
from tools.experiment_tools import optimize_design, run_parameter_sensitivity, run_repair_loop
from tools.artifact_tools import create_run, finalize_run, file_hash
from tools.trace_tools import read_trace, validate_trace


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def numerical(value):
    if isinstance(value,dict):
        return {k:numerical(v) for k,v in value.items() if k!='comparison_context'}
    if isinstance(value,list):
        return [numerical(v) for v in value]
    return value


def audit(path):
    manifest=read(path/'run.json')
    for name,expected in manifest['artifact_hashes'].items():
        assert file_hash(path/name)==expected,(path,name)
    events=read_trace(path/'trace.jsonl')
    validate_trace(events,path)
    if (path/'source_snapshot.zip').is_file():
        with zipfile.ZipFile(path/'source_snapshot.zip') as archive:
            for name,expected in manifest['source_hashes'].items():
                assert hashlib.sha256(archive.read(name)).hexdigest()==expected
    return {'run_id':manifest['run_id'],'run_manifest_hash':file_hash(path/'run.json'),
            'final_status':manifest['final_status'],'artifact_hashes':manifest['artifact_hashes'],
            'artifact_count':len(manifest['artifact_hashes']),'trace_count':len(events),
            'gate_count':sum(e.gate is not None for e in events)}


def compare(before,after):
    names=('task.yaml','environment.yaml','design_input.yaml','design_final.yaml','robot_ir.yaml',
           'physics.yaml','robot.xml','controller.json','tendon_command.json','simulation_state.json')
    identical={name:file_hash(before/name)==file_hash(after/name) for name in names}
    assert all(identical.values()),identical
    a,b=read(before/'metrics.json'),read(after/'metrics.json')
    assert numerical(a)==numerical(b),'Legacy model/simulation/clearance metrics changed'
    return {'before':audit(before),'after':audit(after),'byte_identical':identical,
            'all_metrics_equal_excluding_comparison_context':True,
            'predicted_error_m':b['model']['predicted_position_error_m'],
            'actual_error_m':b['mujoco']['position_error_m']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before',required=True)
    parser.add_argument('--before-window',required=True)
    parser.add_argument('--include-synthetic',action='store_true')
    args=parser.parse_args()
    from tools.matlab_tools import MatlabTools
    matlab=MatlabTools()
    class Shared:
        def __getattr__(self,name):
            return getattr(matlab,name)
        def close(self):
            pass
    report=create_run()
    status='ERROR'
    try:
        _snapshot_sources(report,(Path(__file__).resolve(),))
        baseline=run_reach(matlab_factory=Shared)
        window=run_reach(task_package=ROOT/'tests/fixtures/reach_window_dev',matlab_factory=Shared)
        result={'reach_free':compare(ROOT/'runs'/args.before,baseline.path),
                'reach_window_dev':compare(ROOT/'runs'/args.before_window,window.path)}
        blocked=optimize_design(ROOT/'proposals/engineer/round3_experiment_policy.yaml')
        assert blocked.record.final_status=='BLOCKED_FOR_HUMAN_APPROVAL'
        result['real_experiment_approval']=audit(blocked.path)
        if args.include_synthetic:
            fixture=ROOT/'tests/fixtures/round3/policy.yaml'
            result['synthetic_only']={'scope':'TEST_ONLY; DEVELOPMENT_ONLY; never benchmark evidence',
                                      'policy_hash':file_hash(fixture)}
            for name,call in (('optimization',optimize_design),('sensitivity',run_parameter_sensitivity),('repair',run_repair_loop)):
                run=call(fixture,matlab_factory=Shared)
                assert run.record.final_status=='PASS',read(run.path/(name+'_summary.json'))
                children=[]
                for reference in sorted(run.path.glob('candidate_*_run_reference.json')):
                    ref=read(reference)
                    child=ROOT/'runs'/ref['run_id']
                    assert file_hash(child/'run.json')==ref['run_manifest_hash']
                    children.append(audit(child))
                result['synthetic_only'][name]={'parent':audit(run.path),'children':children,
                    'summary':read(run.path/(name+'_summary.json')),
                    'budget':read(run.path/'experiment_summary.json')}
        report.save('round3_validation.json',result)
        status='PASS'
        print('Validation report:',report.path)
        print('Legacy baseline and development metrics and 10 numerical artifact files per run are unchanged.')
        print('Real reach_free experiments: BLOCKED_FOR_HUMAN_APPROVAL. Synthetic evidence is TEST_ONLY.')
    except Exception as exc:
        report.save('validation_error.json',{'message':str(exc)})
        raise
    finally:
        matlab.close()
        finalize_run(report,status,None if status=='PASS' else 'UNKNOWN')


if __name__=='__main__':
    main()
