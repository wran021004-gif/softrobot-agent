"""Read-only paired request projection at an original R2 handoff boundary."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import httpx
from tools.platform_host import Host
from tools.research import agent
from tools.research.config import ROOT
from tools.research.research_context import agent_decision_brief, research_decision_brief_v3
from tools.research.provider_context import official_tokenizer, TOKENIZER_SHA256
from tools.state_io import atomic_json, digest


def audit(source, *, study='m5-main-off-experience-r2-20261028',handoff_event=110,request_event=115,
        policy='on_demand_tools_v2',reserve_policy=None,proposed_budget=None):
    h=Host(source,study)
    events=h.store.events(h.run_id)
    handoff=next(e for e in events if e['sequence']==handoff_event)
    preparation=h.store.artifact(handoff['outputs'][0])
    s=h.store.artifact(preparation['source_state'])
    source_identity=digest(s)
    sent=next(e for e in events if e['sequence']==request_event)
    old=h.store.artifact(h.store.artifact(sent['outputs'][0])['request'])
    s['pilot'].update(handoff=handoff['outputs'][0],framework_session_id=preparation['next_session'])
    # Scientific state, knowledge scope and ledger are held fixed. Only routing
    # policy and its current projection change; no private card is translated.
    s['spec']['research_decisions']['tool_schema_policy']={'version':policy}
    budget=deepcopy(preparation['budget'])
    if reserve_policy:s['spec']['budgets']['provider_reserve_policy']=reserve_policy
    if proposed_budget is not None:
        s['spec']['budgets']['provider_requests']=proposed_budget
        budget['limit']['model_calls']=proposed_budget;budget['used']['model_calls']=0
        budget['remaining']['model_calls']=proposed_budget
    session={**h.store.session(h.run_id),'state':s}
    prefix=[e for e in events if e['sequence']<request_event]
    with patch.object(h.store,'session',return_value=session), \
         patch.object(h.store,'events',return_value=prefix), \
         patch.object(h.store,'remaining',return_value=budget), \
         patch.object(h.store,'transaction',side_effect=AssertionError('Read-only audit')):
        brief=agent_decision_brief(h)
        packet=dict(study_id=h.run_id,research=research_decision_brief_v3(brief,
            complete_interpretations=s['spec']['research_decisions']['role_policy']['version']=='research_roles_v2'))
        registry={name:SimpleNamespace(tool_spec=deepcopy(schema)) for name,schema in preparation['tool_schemas'].items()}
        spec=s['spec']
        registry['research_plan']=SimpleNamespace(tool_spec=dict(name='research_plan',description=agent.DECISION_PLAN_DESCRIPTION,
            inputSchema={'json':agent.plan_schema(spec['allowed_plan_actions'],decision_required=True,
                family_version=spec['family_space']['version'])}))
        directory=deepcopy(s['pilot']['tool_directory'])
        if not brief['budget']['closeout']['next_request_will_protect']:
            # A historical closeout projection may already have replaced the
            # directory before this snapshot. Restore its earlier native catalog
            # from a saved pre-boundary request, never from future outcomes.
            restore_directory=not any('generate' in r.get('actions',[]) for r in directory)
            for event in (reversed(prefix) if restore_directory else []):
                if event['kind']!='r3_request':continue
                prior=h.store.artifact(h.store.artifact(event['outputs'][0])['request'])
                tail=prior['messages'][-1].get('content')
                if not isinstance(tail,str) or not tail.startswith('CURRENT_RESEARCH_PACKET\n'):continue
                prior_directory=json.loads(tail.split('\n',1)[1])['research'].get('tool_directory',[])
                if any('generate' in r.get('actions',[]) for r in prior_directory):
                    directory=deepcopy(prior_directory);break
            next(r for r in directory if r['tool']=='research_plan')['actions']=brief['actions']
        if brief['budget']['closeout']['next_request_will_protect']:
            from tools.research.budget import closeout_operations
            directory=[r for r in directory if r['tool'] in ('research_plan','evidence_read','research_rl')]
            next(r for r in directory if r['tool']=='research_plan')['actions']=closeout_operations(h)['research_plan']
        if policy=='research_information_flow_v1':
            # Read literal production descriptions without constructing an SDK
            # session or maintaining another tool description catalog.
            import ast
            descriptions={}
            for node in ast.walk(ast.parse(Path(agent.__file__).read_text(encoding='utf8'))):
                if isinstance(node,ast.Tuple) and len(node.elts)>=2 and all(isinstance(v,ast.Constant) and isinstance(v.value,str) for v in node.elts[:2]):
                    descriptions[node.elts[0].value]=node.elts[1].value
                if isinstance(node,ast.Call):
                    fields={k.arg:k.value.value for k in node.keywords if isinstance(k.value,ast.Constant)}
                    if 'name' in fields and 'description' in fields:descriptions[fields['name']]=fields['description']
            from tools.research.contracts import EvidenceQuery, ExperienceQuery, ResearchRecallQuery
            from tools.research.reporter import InvestigationRequest
            for name,contract in (('evidence_read',EvidenceQuery),('experience_retrieve',ExperienceQuery),
                    ('research_recall',ResearchRecallQuery),('research_investigate',InvestigationRequest)):
                if any(r['tool']==name for r in directory):
                    registry[name]=SimpleNamespace(tool_spec=dict(name=name,description=descriptions[name],inputSchema={'json':contract.model_json_schema()}))
        loaded=agent.load_selected_tool_schema(h,registry,directory)
        packet['research'].update(tool_directory=directory,loaded_tool=loaded,
            tool_loading='Choose research_route to load one tool/action. Reuse the loaded tool for consecutive operations; switch only when needed; submit the loaded tool to act. No selection grants execution authority.')
        packet['research']['generation_contract']=dict(family_space_identity=spec['family_space_identity'],
            version='serial_family_generation_v2' if spec['family_space']['version']=='serial_family_space_v2' else 'serial_family_generation_v1',
            domain_query=dict(reference=s['family_space_reference'],view='full',pointer=''),
            scope='Frozen generation inputs and domain query; choose your own legal parameters. No candidate or Plan is submitted.')
        if policy in ('on_demand_tools_v3','research_information_flow_v1'):
            from tools.research.research_context import compact_tool_delivery
            compact_tool_delivery(packet['research'])
        if policy=='research_information_flow_v1':
            from tools.research.research_context import information_flow_brief
            packet['research']=information_flow_brief(brief,packet['research'])
        projected=deepcopy(old)
        projected['messages'][-1]['content']='CURRENT_RESEARCH_PACKET\n'+json.dumps(packet,separators=(',',':'))
        projected['tools']=[dict(type='function',function=dict(name=name,description=tool.tool_spec.get('description',''),
            parameters=tool.tool_spec['inputSchema']['json'])) for name,tool in registry.items()]
        from tools.research.provider import provider_schema
        for tool in projected['tools']:tool['function']['parameters']=provider_schema(tool['function']['parameters'])
    def measure(wire):
        body=httpx.Request('POST','http://offline.invalid',json=wire).content
        def metric(value):
            text=json.dumps(value,separators=(',',':'),ensure_ascii=False)
            return dict(bytes=len(text.encode()),tokens=len(official_tokenizer().encode(text,add_special_tokens=False).ids))
        packet=json.loads(wire['messages'][-1]['content'].split('\n',1)[1])['research']
        from tools.research.session_handoff import packet_feedback
        feedback=packet_feedback(packet)
        l0=deepcopy(packet)
        for key in ('research_state','tool_continuation'):l0.get(key,{}).pop('pending_feedback',None)
        return dict(total=dict(bytes=len(body),tokens=len(official_tokenizer().encode(body.decode(),add_special_tokens=False).ids)),
            components=dict(system=metric([m for m in wire['messages'] if m['role']=='system']),
                history=metric(wire['messages'][1:-1]),l0_without_feedback=metric(l0),
                schema=metric(wire.get('tools',[])),feedback=metric(feedback)),
            request_identity=digest(wire),schema_names=[t['function']['name'] for t in wire['tools']],
            loaded_plan_actions=[a for t in wire['tools'] if t['function']['name']=='research_plan'
                for a in t['function']['parameters']['properties']['action']['enum']],
            pending_feedback_tool_ids=[r['tool_id'] for r in (feedback or {}).get('items',[])])
    return dict(boundary=dict(study=h.run_id,handoff_event=handoff_event,request_event=request_event,source_state_identity=source_identity),
        old=measure(old),v2=measure(projected),
        token_estimator=dict(kind='pinned DeepSeek V4 serialized JSON tokenizer; offline estimate, not API usage',sha256=TOKENIZER_SHA256),
        limitation='This controls scientific state, original instructions, history, model and private experience scope. Component serializations are diagnostic and do not add to total framing. It is not a matched model behavior trial.'),old,projected


if __name__=='__main__':
    import sys
    result,old,v2=audit(Path(sys.argv[1]))
    output=ROOT/'runs/p4-context';output.mkdir(parents=True,exist_ok=True)
    atomic_json(output/'old_request.json',old);atomic_json(output/'v2_request.json',v2)
    atomic_json(ROOT/'docs/research/p4_context_metrics.json',result)
    print(json.dumps(result))
