"""Program-generated facts; independent semantic reviews remain separate."""
from pathlib import Path
import json
import re
import subprocess
from tools.state_io import read,atomic_json,digest
from tools.platform_store import zero,now
from tools.context_assembly import _no_secrets

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent/'stages'


def reuse_gate(review):
    b=read(OUT/'reuse_bundle.json');m=read(OUT/'validation_manifest.json')
    historical=b['state'].get('historical_investigations',{});nodes=b['state'].get('investigations',{})
    events=b['events'];artifacts=b['artifacts']
    attempts=[e for e in events if e['kind']=='investigation_provider_attempt']
    responses=[e for e in events if e['kind']=='investigation_provider_response']
    charged=zero()
    for call in b['calls']:
        for k,v in (call.get('charged') or {}).items():charged[k]+=v
    decisions=[n.get('principal_disposition') for n in historical.values()]
    inspected=all(d and (d['decision']['disposition']!='accept' or bool(d['inspection_links']) and bool(d['decision']['adopted_claims'])) for d in decisions)
    settings=b['snapshot']['input']['policy']['model']
    wires=[artifacts[e['outputs'][0]['artifact_id']]['payload'] for e in attempts]
    checks=dict(historical_binding=len(historical)==2 and all(n['kind']=='historical_reuse' and not n['new_investigation_executed'] for n in historical.values()),
        new_principal_execution=len(nodes)==1 and all(n['status']=='completed' for n in nodes.values()) and 0<len(attempts)==len(responses),
        public_formal_dispositions=len(decisions)==2 and all(decisions) and sum(e['kind']=='principal_disposition' for e in events)==2,
        independently_inspected_acceptance=inspected,
        cumulative_accounting=len(attempts)==charged['model_calls'] and all(charged[k]<=m['phases']['reuse']['project_budget'][k] for k in charged)
            and not any(c['status'] in ('unknown','running') for c in b['calls']),
        logical_node_bounds=all(n['usage']['model_calls']<=8 and n['usage']['tool_calls']+len(b['state'].get('principal_investigation_reads',[]))<=12 for n in nodes.values())
            and b['state'].get('investigation_protocol_corrections_used',0)<=2,
        approved_settings=settings['base_url']=='https://api.deepseek.com' and settings['model']=='deepseek-flash'
            and all(w.get('model')=='deepseek-flash' and w.get('thinking')=={'type':'enabled'} and w.get('reasoning_effort')=='high' and w.get('tool_choice')=='auto' and w.get('max_tokens')==32768 for w in wires),
        independent_semantic_review=review['bundle_identity']==digest(b) and review['material_correctness']=='pass'
            and sorted(review['reports'])==sorted(n['result']['artifact_id'] for n in historical.values()),
        lifecycle=b['session_status']=='stopped' and read(OUT/'reuse_lifecycle.json')['all_submitted_nodes_drained'],
        historical_preservation=read(OUT/'historical_after.json')['unchanged'])
    result=dict(version='historical_disposition_gate@1.0.0',passed=all(checks.values()),checks=checks,
        bundle_identity=digest(b),review_identity=digest(review),accounting=dict(charged=charged,provider_attempts=len(attempts)),
        acceptance_scope='历史调查结果的新主模型处置验证；旧真实追读与新处置构成分段闭环，不代表全新无中断无人干预调查。')
    atomic_json(OUT/'reuse_material_review.json',review);atomic_json(OUT/'reuse_gate.json',result)
    return result


def audit():
    m=read(OUT/'validation_manifest.json');phases={};tokens={};wall=0.
    for mode,phase in m['phases'].items():
        result=dict(started=(OUT/(mode+'_launch.json')).exists(),budget=phase['project_budget'],used=zero(),
            provider_tokens={},billing_amount='unknown',protocol_corrections=0,scientific_operations={},
            application_wall_s=0.,backend_attempts=0,gate='not_run',protocol_corrections_sent=0)
        if (OUT/(mode+'_bundle.json')).exists():
            b=read(OUT/(mode+'_bundle.json'));events=b['events'];a=b['artifacts']
            for call in b['calls']:
                for key,value in (call.get('charged') or {}).items():result['used'][key]+=value
                tool=call.get('tool_id') or (call.get('receipt') or {}).get('tool_id')
                if tool and (tool.startswith('analysis.') or tool=='simulation.run'):
                    result['scientific_operations'][tool]=result['scientific_operations'].get(tool,0)+1
            result['unresolved_reservations']=[dict(request_id=c['request_id'],status=c['status'],reserved=c['reserved']) for c in b['calls'] if c['status'] in ('running','unknown')]
            result['protocol_corrections']=b['state'].get('investigation_protocol_corrections_used',0)
            result['corrections_by_role']=b['state'].get('investigation_corrections_by_role',{})
            result['nodes']={k:dict(role=n['order']['role'],status=n['status'],usage=n.get('usage'),failure=n.get('reason')) for k,n in b['state'].get('investigations',{}).items()}
            result['historical_reports']={k:dict(original=n['original'],original_execution_id=n['original_execution_id'],new_investigation_executed=False,
                disposition=(n.get('principal_disposition') or {}).get('decision')) for k,n in b['state'].get('historical_investigations',{}).items()}
            for event in events:
                if event['kind']=='investigation_provider_attempt':
                    payload=a[event['outputs'][0]['artifact_id']].get('payload',{})
                    last=payload.get('messages',[{}])[-1]
                    try:content=json.loads(last.get('content',''))
                    except (ValueError,TypeError):content={}
                    if content.get('error')=='INVALID_UNEXECUTED_REPORT' or content.get('kind')=='explicit_received_return_correction_turn':
                        result['protocol_corrections_sent']+=1
                if event['kind']=='investigation_token_accounting':
                    usage=a[event['outputs'][0]['artifact_id']].get('provider_usage')
                    for key,value in (usage or {}).items():result['provider_tokens'][key]=result['provider_tokens'].get(key,0)+value
            result['backend_attempts']=sum((c.get('receipt') or {}).get('tool_id')=='simulation.run' for c in b['calls'])
        if (OUT/(mode+'_lifecycle.json')).exists():result['application_wall_s']=read(OUT/(mode+'_lifecycle.json'))['application_wall_s']
        for supplemental in sorted(OUT.glob(mode+'_repair*_lifecycle.json')):
            result['application_wall_s']+=read(supplemental)['application_wall_s']
        if (OUT/(mode+'_gate.json')).exists():result['gate']=read(OUT/(mode+'_gate.json'))
        phases[mode]=result;wall+=result['application_wall_s']
        for key,value in result['provider_tokens'].items():tokens[key]=tokens.get(key,0)+value
    result=dict(timestamp=now(),activity_id=m['activity_id'],phases=phases,provider_tokens=tokens,billing_amount='unknown',
        application_wall_s=wall,ledger_wall_s=sum(p['used']['wall_s'] for p in phases.values()),
        implementation_repairs_used=m['implementation_repairs_used'],planned_interface_changes=1,
        paid_protocol_corrections=sum(p['protocol_corrections'] for p in phases.values()),
        old_history_unchanged=read(OUT/'historical_after.json')['unchanged'] if (OUT/'historical_after.json').exists() else read(OUT/'prelaunch_audit.json')['historical_unchanged'],
        intervention='Codex interface implementation, targeted offline verification, explicit historical handoff, independent semantic review and delivery. External egress confirmation separately recorded.',
        clock_scope='Application phase wall clock and cumulative execution ledger are separate. Active engineering CPU/billing not measured.',
        automatic_transport_retries=0,version2_implemented=False)
    from datetime import datetime
    created=datetime.fromisoformat(m['created_at'])
    result['inclusive_freeze_to_audit_s']=(datetime.fromisoformat(result['timestamp'])-created).total_seconds()
    result['non_application_inclusive_interval_s']=result['inclusive_freeze_to_audit_s']-wall
    result['non_application_interval_scope']='Inclusive engineering, offline verification, review, user authorization wait and delivery interval; not pure development CPU.'
    result['correction_accounting']=dict(scheduled=sum(p['protocol_corrections'] for p in phases.values()),
        actually_sent=sum(p['protocol_corrections_sent'] for p in phases.values()),
        maximum_total=6,unused_not_transferred=True)
    _no_secrets(result);atomic_json(OUT/'delivery_audit.json',result)
    print(json.dumps(dict(activity=m['activity_id'],phase_usage={k:v['used'] for k,v in phases.items()},tokens=tokens),ensure_ascii=False))
    return result


def publication():
    from evidence.research_v1_completion_20261008.publication_review import PATTERNS
    def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True,encoding='utf8').strip()
    base='9b2db8ab3f42a2147bd8eecee391e804072845cc'
    paths=sorted(set(git('diff','--name-only',base,'HEAD').splitlines()+git('ls-files','--others','--exclude-standard').splitlines()+git('diff','--name-only').splitlines()))
    allowed={'extensions/platform/manifest.py','tools/research_investigations.py','tools/research_mainline3.py','tools/research_validation_gate.py',
        'tools/investigation_contract.py','tools/investigation_handoff.py','tools/research_v1_resume.py','tests/test_investigation_contract.py',
        'docs/research_investigation_native_contract.md','docs/research_mainline3_v1_completion.md','docs/research_mainline3_v2_handoff.md'}
    issues=[]
    for p in paths:
        if p not in allowed and not p.startswith('evidence/research_v1_resume_20261008/'):
            issues.append(dict(path=p,issue='outside authorized task scope'));continue
        text=(ROOT/p).read_text(encoding='utf-8-sig')
        for index,pattern in enumerate(PATTERNS):
            if re.search(pattern,text):issues.append(dict(path=p,issue='potential secret',pattern_index=index))
        if p.endswith('.json'):
            try:_no_secrets(json.loads(text))
            except ValueError:issues.append(dict(path=p,issue='structured secret field or invalid JSON'))
    patch=git('diff',base,'HEAD')+git('diff')
    for index,pattern in enumerate(PATTERNS):
        if re.search(pattern,patch):issues.append(dict(issue='potential secret in commit interval',pattern_index=index))
    atomic_json(OUT/'publication_scope_review.json',dict(timestamp=now(),base=base,head=git('rev-parse','HEAD'),
        files=paths,scope_passed=not issues,secret_checks_passed=not issues,issues=issues,
        target='https://github.com/wran021004-gif/softrobot-agent.git',branch=git('branch','--show-current'),
        push_method='ordinary fast-forward; verify remote SHA separately',limitations='Heuristic patterns plus structured checks and explicit file scope review.'))
    if issues:raise ValueError('PUBLICATION_SCOPE_REVIEW_FAILED')
    print(json.dumps(dict(scope_passed=True,secret_checks_passed=True,files=len(paths))))


if __name__=='__main__':
    import sys
    publication() if '--publication' in sys.argv else audit()
