"""Exact new principal request and public expansion, explicitly offline substitute."""
import json
from pathlib import Path
from unittest.mock import patch
from tools.state_io import read,atomic_json
from tools.platform_store import encode
from tools.research_v1_resume import prepare,execute


def main():
    root=Path(__file__).resolve().parents[1]
    import sys
    out=root/'evidence/research_disposition_facts_20261008'/(sys.argv[1] if len(sys.argv)>1 else 'preflight')
    prepare(out,authorization=out.parent/'authorization_text.md',selectable=True)
    sends=[]
    def offline(adapter,config,payload):
        sends.append(payload)
        packet=json.loads(payload['messages'][1]['content'])
        cat=packet['fact_catalog']
        choices=[dict(**t,catalog=cat['reference'],catalog_version='1.0.0',disposition='defer',
            reason='Explicit offline fixture; no scientific review or real model decision.') for t in packet['disposition_targets']]
        return dict(offline_fixture=True,choices=[dict(finish_reason='tool_calls',message=dict(role='assistant',content=None,
            tool_calls=[dict(id='fixture',type='function',function=dict(name='investigation_return',
                arguments=json.dumps(dict(interpretation='OFFLINE SUBSTITUTION ONLY',dispositions=choices))))]))])
    with patch('tools.platform_models.DeepSeekAdapter._transport',new=offline),patch('examples.gvs_nmpc_route_experiment.load_credential'):
        execute(out,'reuse')
    bundle=read(out/'reuse_bundle.json');bundle['transport']='deterministic_offline_substitute'
    atomic_json(out/'reuse_bundle.json',bundle)
    from tools.context_assembly import check_outgoing_request
    cfg=read(out/'frozen_configuration.json')['policy']['model']
    atomic_json(out/'offline_request_checks.json',dict(offline_only=True,paid_provider_requests=0,
        result=read(out/'reuse_result.json'),settings={k:sends[0][k] for k in ('model','thinking','reasoning_effort','tool_choice','max_tokens')},
        measurements=[check_outgoing_request(p,cfg,'research_decision') for p in sends],
        history_unchanged=read(out/'historical_after.json'),previous_resume_unchanged=read(out/'previous_resume_after.json')))
    print(encode(dict(offline_only=True,paid_provider_requests=0,complete_requests=len(sends),result=read(out/'reuse_result.json')['status'])))


if __name__=='__main__':main()
