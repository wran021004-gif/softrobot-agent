"""One focused delivery check; no model request or backend execution."""
import hashlib
import argparse
import json
from pathlib import Path
import re
import subprocess
import tarfile
from tools.state_io import read,atomic_json
from tools import research_mainline5_services as s


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--scope-base',default='HEAD');args=parser.parse_args()
    out=s.OUT;manifest=read(out/'archive_manifest.json');archive=out/manifest['archive']
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['sha256']
    verified=0;secret_pattern=re.compile(rb'\bsk-[A-Za-z0-9]{24,}\b')
    with tarfile.open(archive,'r:gz') as tf:
        assert len(tf.getmembers())==len(manifest['members'])
        for row in manifest['members']:
            stream=tf.extractfile(row['path']);assert stream is not None
            body=stream.read();assert len(body)==row['bytes']
            assert hashlib.sha256(body).hexdigest()==row['sha256']
            assert not secret_pattern.search(body),'Unexpected credential-shaped value in '+row['path']
            verified+=1
    metadata=read(out/'metadata_archive_index.json')
    for row in metadata['members']:
        assert row in manifest['members']
        assert not (out/Path(row['path']).name).exists()
    w=s.restore();result=read(out/'result_summary.json');uses=result['resources'];usage=w.store.remaining()
    assert uses['provider_requests']==usage['used']['model_calls']<=60
    assert uses['overall_backend_attempts']==usage['used']['backend_solves']<=10
    assert uses['development_backend_attempts']<=6
    assert uses['verification_backend_attempts']<=2
    assert uses['public_mathematical_and_search_operations']<=48
    assert usage['used']['tool_calls']<=1024 and usage['used']['worker_calls']==0
    assert result['status']==w.status=='model_stopped'
    assert w.rounds[-1].get('stop_processed') and not usage['occupied']
    if w.verification:assert w.rounds[-1].get('verification_feedback_consumed')
    assert result['entry'] in ('T2','T3')
    assert result['dimensions']['new_feedback_consumed_by_principal']
    assert result['outcomes']
    from extensions.tendon_family.finite_templates import selected_space,validate_constructed,template_id
    from schemas.platform import SessionInput
    from extensions.tendon_family.gvs_profile import execution_scope
    for outcome in result['outcomes']:
        cfg=w.store.artifact(outcome['candidate']['configuration'])['effective'];inp=SessionInput.model_validate(cfg)
        assert template_id(cfg['robot']['structure']['data'])==result['entry']
        _,space=selected_space(inp,inp.policy.candidate_builder.parameters.data,{})
        validate_constructed(inp,space)
        recipe=cfg['policy']['controller']['parameters']['data']['recipe']
        assert outcome['applied_values']=={k:recipe[k] for k in outcome['applied_values']}
        assert outcome['candidate']['owner_run_id'].startswith('batch-')
    for v in w.verification:
        actual=w.store.artifact(w.store.artifact(v['result'])['configuration'])['effective']
        original=w.store.artifact(v['source']['configuration'])['effective']
        assert execution_scope(actual)==execution_scope(original)
    direct=[o for o in result['outcomes'] if o['applied_values']==dict(holding_tip_speed_weight=.0375,terminal_tip_speed_weight=.1)]
    assert result['transfer_reporting']['direct_parameter_transfer_tested']==bool(direct)
    for path in out.glob('*.json'):assert not secret_pattern.search(path.read_bytes()),str(path)
    staged=subprocess.check_output(['git','diff','--cached','--name-only',args.scope_base],cwd=s.ROOT,text=True).splitlines()
    assert all(p.startswith(('tools/','docs/','evidence/research_mainline5_20261009/')) for p in staged),staged
    subprocess.check_call(['git','diff','--cached','--check',args.scope_base],cwd=s.ROOT)
    atomic_json(out/'delivery_integrity.json',dict(status='passed',archive_members=verified,
        archive_sha256=manifest['sha256'],cumulative_limits_checked=True,applied_parameters_and_owners_checked=True,
        selected_template_actual_domains_checked=True,sealed_verification_science_identity_checked=True,
        direct_transfer_distinction_checked=True,staged_scope=staged,scientific_or_provider_operations=0))
    print(json.dumps(dict(status='passed',archive_members=verified,provider_requests=uses['provider_requests'],
        backend_attempts=uses['overall_backend_attempts'])))


if __name__=='__main__':main()
