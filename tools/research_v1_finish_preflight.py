"""Exercise the entire new principal wire with a declared offline substitute."""
from copy import deepcopy
import json
from tools.research_v1_finish import OUT,ROOT,grant_evidence,historical_handoff,inspect,order
from tools.research_mainline3 import configuration
from tools.research_v1_delivery import model_configuration
from tools.research_investigations import InvestigationDispatcher
from tools.research_execution import invoke
from tools.platform_store import Store,plain,zero,encode
from tools.platform_host import Host
from tools.state_io import atomic_json
from tools.research_single_validation import stop
from tools.context_assembly import check_outgoing_request


def main():
    import sys
    suffix=sys.argv[1] if len(sys.argv)>1 else ''
    root=OUT/('preflight_store'+suffix)
    if root.exists():raise ValueError('NO_PREFLIGHT_REPLAY_IN_PLACE')
    tools={k:'1.0.0' for k in ('research.investigate','research.investigation_status','research.investigation_read','research.investigation_disposition','research.investigation_handoff')}
    budget={**zero(),'model_calls':12,'tool_calls':128,'wall_s':5000.}
    node={**zero(),'model_calls':12,'tool_calls':24,'wall_s':3600.}
    stage=dict(node_budget=node,total_node_budget=node,node_count=1,node_timeout_s=3600,project_budget=budget,
        protocol_correction_limit=4,protocol_correction_role_limits=dict(principal=4,other=0))
    cfg=model_configuration(configuration());cfg['run_id']='offline-principal'
    cfg['policy']['model'].update(adapter_version='8.0.0',parameters=dict(investigation_contract='selectable_facts_v3'))
    cfg['policy'].update(route=None,budget=budget,allowed_tools=list(tools),tool_bindings=tools,
        operation_allowances={t:dict(reserve_s=5.,timeout_s=30.) for t in tools})
    s=Store(root);s.create(dict(project_id='offline-only-preflight'+suffix,grant_id='offline-only-preflight'+suffix,authorization_source='OFFLINE TEST FIXTURE',budget=budget))
    h=Host(root,cfg['run_id']);h.create(cfg);h.resume()
    raw,view,_=grant_evidence(h,stage);targets=historical_handoff(h);inspect(h,[raw,view])
    sources=s.session(h.run_id)['state']['role_context']['investigation_grant']['evidence']
    value=order(stage,'offline-principal','principal','Explicit OFFLINE substitute: no real scientific judgment',[*sources,*[t['report'] for t in targets]],models=12,ops=22)
    value['disposition_ids']=[t['investigation_id'] for t in targets]
    sends=[]
    def transport(wire):
        sends.append(deepcopy(wire));packet=json.loads(wire['messages'][1]['content'])
        number=len(sends)
        if number<=2:
            name='evidence_read';args=dict(reference=targets[number-1]['report'],pointer='',limit=100,byte_limit=65536)
        elif suffix=='5' and number==3:
            name='evidence_read';args=dict(reference=sources[2],pointer='/constraints',limit=100,byte_limit=4096)
        else:
            name='investigation_return';cat=packet['fact_catalog']
            args=dict(interpretation='OFFLINE SUBSTITUTE ONLY; no material acceptance.',dispositions=[dict(**t,catalog=cat['reference'],catalog_version='1.0.0',disposition='defer',reason='Offline fixture tests structure only.') for t in targets])
            if suffix=='5':
                chosen=next(e['handle'] for e in cat['content']['entries'] if e['origin']=='principal_additional' and e['reference']==sources[2] and e['pointer']=='/constraints')
                for decision in args['dispositions']:decision['evidence_used']=[dict(handle=chosen)]
        return dict(offline_substitute=True,choices=[dict(finish_reason='tool_calls',message=dict(role='assistant',content=None,reasoning_content='offline fixture',tool_calls=[dict(id='offline-'+str(number),type='function',function=dict(name=name,arguments=json.dumps(args)))]))])
    d=InvestigationDispatcher(h);result=d.dispatch(value,transport=transport)
    if result.status!='completed':
        stop(h,'OFFLINE PREFLIGHT FAILURE SEALED; no paid requests')
        raise ValueError('NEW_EXACT_WIRE_PREFLIGHT_FAILED')
    receipts=[invoke(h,'research.investigation_disposition',decision,request_id='offline-dispose-'+str(i)) for i,decision in enumerate(s.artifact(result.result)['dispositions'])]
    if any(r['execution_status']!='completed' for r in receipts):raise ValueError('OFFLINE_PUBLIC_DISPOSITION_FAILED')
    # Catalog/archive detail remains callable under the same original node grant.
    from schemas.platform_operations import ReadEvidence
    n=s.session(h.run_id)['state']['investigations']['offline-principal']
    detail=d._query(__import__('tools.research_investigations',fromlist=['InvestigationOrder']).InvestigationOrder.model_validate(value),
        ReadEvidence(reference=n['fact_catalog'],pointer='/entries/0',limit=100,byte_limit=65536))
    stop(h,'OFFLINE SUBSTITUTE TERMINAL; paid requests zero')
    atomic_json(OUT/('preflight_result'+suffix+'.json'),dict(offline_only=True,paid_provider_requests=0,fixture_turns=len(sends),
        measurements=[check_outgoing_request(w,cfg['policy']['model'],'research_decision') for w in sends],
        receipts=receipts,catalog_detail=detail['page'],original_full_requests=[{'payload':w} for w in sends],
        settings={k:sends[0][k] for k in ('model','thinking','reasoning_effort','tool_choice','max_tokens')}))
    print(encode(dict(offline_only=True,paid_provider_requests=0,fixture_turns=len(sends),estimates=[check_outgoing_request(w,cfg['policy']['model'],'research_decision')['estimated_input_tokens'] for w in sends])))


if __name__=='__main__':main()
