"""Saved public-chain gate; material review is supplied by the coding agent."""
import json
from tools.state_io import read,digest
from tools.research_v1_continue import OUT,ROOT
from tools.platform_store import zero,Store
from tools.research_investigations import InvestigationDispatcher,InvestigationOrder,InvestigationReturn,SourceFact

def correction_consistency(authorization,phase,*,grant=None,orders=()):
    """Existing offline/public gate: frozen authority must match the executor."""
    from tools.research_v1_continue import task_allocations,correction_policy
    allocations=task_allocations();policy=correction_policy()
    shared=policy['version']=='mainline3.shared_completion@2.0.0'
    checks=dict(authorization=authorization.get('task_allocations')==allocations and authorization.get('correction_policy')==policy,
        frozen_tasks=phase['allocations']==allocations,frozen_corrections=phase.get('correction_policy')==policy,
        common_requests=phase['project_budget']['model_calls']==40,
        node_envelope=phase['node_budget']==(allocations['coordinator-summary']['budget'] if shared else {**zero(),'model_calls':18,'tool_calls':24,'wall_s':3600.}),
        aggregate_envelope=phase['total_node_budget']==({**zero(),'model_calls':40,'tool_calls':256,'wall_s':28200.} if shared else {**zero(),'model_calls':40,'tool_calls':60,'wall_s':10200.}))
    if grant is not None:
        checks['actual_grant']=(grant.get('correction_policy')==policy and grant.get('delivery_allocations')==allocations
            and grant['per_node_budget']==phase['node_budget'] and grant['total_budget']==phase['total_node_budget']
            and grant.get('sequential_reservations')==phase.get('sequential_reservations'))
    checks['actual_orders']=all(o['investigation_id'] in allocations and o['budget']==allocations[o['investigation_id']]['budget']
        and o['timeout_s']==allocations[o['investigation_id']]['timeout_s'] for o in orders if not shared or o['role']!='investigator')
    return dict(passed=all(checks.values()),checks=checks,policy_version=policy['version'])

def generate_b(out=None):
    if out is None:
        from tools.research_v1_continue import OUT as out
    OUT=out
    manifest=read(OUT/'validation_manifest.json');p=manifest['phases']['coordinated']
    shared=p.get('correction_policy',{}).get('version')=='mainline3.shared_completion@2.0.0'
    bundle=read(OUT/'coordinated_bundle.json');result=read(OUT/'coordinated_result.json')
    nodes=bundle['state']['investigations'];historical=bundle['state'].get('historical_investigations',{});reports={**historical,**nodes}
    events=bundle['events'];arts=bundle['artifacts'];store=Store(ROOT/p['output'])
    attempts=[e for e in events if e['kind']=='investigation_provider_attempt']
    calls=bundle['calls'];used=store.remaining()['used'];unknown=[c['request_id'] for c in calls if c['status'] in ('running','unknown')]
    settings=[]
    for e in attempts:
        r=arts[e['outputs'][0]['artifact_id']];w=r['payload']
        settings.append(w['model']=='deepseek-flash' and w['thinking']=={'type':'enabled'} and w['tool_choice']=='auto' and r['measurement']['passed']
            and any(w['reasoning_effort']==v['reasoning_effort'] and w['max_tokens']==v['max_tokens'] and v['supported'] for v in manifest['conditional_length_recovery']['configurations']))
    chains=[]
    for target in result['targets']:
        key=target['investigation_id'];node=reports[key];reads=node['reads'];proof=[]
        report=arts[node['result']['artifact_id']]
        if node.get('kind')=='historical_reuse':
            for r in reads:
                cited=[f for f in [*report['facts'],*report['counterevidence']] if f['reference']==r['reference'] and InvestigationDispatcher._visible(None,SourceFact.model_validate(f),r)]
                if cited:proof.append(dict(read_identity=r.get('content_identity',digest(r['page'])),cited_pointers=[f['pointer'] for f in cited],origin='preserved_original_historical_read',new_public_operation=False))
        for e in attempts:
            if not e.get('request_id','').startswith('investigation-'+key):continue
            wire=arts[e['outputs'][0]['artifact_id']]['payload']
            from tools.context_assembly import expand_investigation_context
            initial=expand_investigation_context(json.loads(wire['messages'][1]['content']))
            for r in initial.get('reads',[]):
                cited=[f for f in [*report['facts'],*report['counterevidence']] if f['reference']==r['reference'] and InvestigationDispatcher._visible(None,SourceFact.model_validate(f),r)]
                if cited:proof.append(dict(attempt_sequence=e['sequence'],read_identity=r.get('content_identity',digest(r['page'])),cited_pointers=[f['pointer'] for f in cited],origin=r.get('inspection_origin','prefetch')))
            for message in wire['messages']:
                if message.get('role')!='tool':continue
                try:page=json.loads(message['content'])
                except ValueError:continue
                matching=[r for r in reads if r['page']==page and not r.get('metadata_only')]
                for r in matching:
                    cited=[f for f in [*report['facts'],*report['counterevidence']] if f['reference']==r['reference'] and (f['pointer']==r['pointer'] or f['pointer'].startswith(r['pointer']+'/'))]
                    if cited:proof.append(dict(attempt_sequence=e['sequence'],read_identity=r['content_identity'],cited_pointers=[f['pointer'] for f in cited]))
        chains.append(dict(investigation_id=key,selected_report=node['result'],origin='historical_reuse' if node.get('kind')=='historical_reuse' else 'new',native_selected_read_followup_and_citation=bool(proof),proof=proof))
    bounds=all(n['order']['budget']==p['allocations'][k]['budget'] and n['usage']['model_calls']<=n['order']['budget']['model_calls'] and n['usage']['tool_calls']<=n['order']['budget']['tool_calls'] for k,n in nodes.items())
    principal=nodes['principal-coordinated-v2'];principal_report=arts[principal['result']['artifact_id']]
    synthesis=arts[result['coordinator_synthesis']['artifact_id']]
    synthesis_sources={f['reference']['artifact_id'] for f in [*synthesis['facts'],*synthesis['counterevidence']]}
    dispositions=[store.artifact(store.artifact(r['output'])['disposition_record']) for r in result['receipts']]
    inspected=all(d['decision']['disposition']!='accept' or d['inspection_links'] for d in dispositions)
    protections=all((not p['allocations'][k].get('request_purposes') or sum(p['allocations'][k]['request_purposes'].values())==n['order']['budget']['model_calls']) and
        p['allocations'][k]['exploration_requests']<=n['order']['budget']['model_calls']-p['allocations'][k]['protected_delivery_requests'] and
        p['allocations'][k]['protected_delivery_requests']>=1
        for k,n in nodes.items())
    category_bounds=all(sum(n.get('requests_by_purpose',{}).values())==n['usage']['model_calls'] and
        all(n.get('requests_by_purpose',{}).get(c,0)<=limit for c,limit in p['allocations'][k].get('request_purposes',{}).items()) for k,n in nodes.items())
    target_bounds=True
    if p.get('correction_policy'):
        grant=bundle['state']['role_context']['investigation_grant']
        target_bounds=correction_consistency(read(OUT/'authorization.json'),p,grant=grant,orders=[n['order'] for n in nodes.values()])['passed']
        with store.connect(True) as db:
            row=db.execute("SELECT value FROM meta WHERE key='investigation_target_accounting'").fetchone()
        accounting=json.loads(row[0]) if row else None
        target_bounds=target_bounds and accounting is not None and all(t['used']<=p['correction_policy']['maximum'] for t in accounting['targets'].values())
    gates=dict(preserved_A='pass' if read(OUT/'A_preserved.json')['accepted'] else 'fail',
        historical_plan_import='pass' if bundle['state']['historical_investigations']['coordinator-plan']['new_investigation_executed'] is False else 'fail',
        cumulative_report_coverage='pass' if len(chains)==2 and all(reports[t['investigation_id']]['status']=='completed' and c['native_selected_read_followup_and_citation'] for t,c in zip(result['targets'],chains))
            and (reports['reach-holding-interpretation'].get('kind')=='historical_reuse' if shared else reports['reach-holding-interpretation'].get('kind')!='historical_reuse')
            and (reports['timing-integrity-limits'].get('kind')=='historical_reuse' or result.get('necessary_timing_revision')) else 'fail',
        actual_synthesis='pass' if nodes['coordinator-summary']['status']=='completed' and nodes['coordinator-summary']['result']==result['coordinator_synthesis']
            and all(t['report']['artifact_id'] in synthesis_sources for t in result['targets']) else 'fail',
        public_dispositions='pass' if len(dispositions)==2 and len(principal_report['dispositions'])==2 and all(r['execution_status']=='completed' for r in result['receipts']) else 'fail',
        original_evidence_inspection='pass' if inspected and bundle['state'].get('principal_investigation_reads') else 'fail',
        material_audit='pass' if result['material_review']['report']==result['report'] and result['material_review']['material_correctness']=='pass' else 'fail',
        exact_allocation_and_protection='pass' if bounds and protections else 'fail',
        request_capacity_and_settings='pass' if settings and all(settings) else 'fail',
        accounting='pass' if not unknown and used['model_calls']==len(attempts) and all(used[k]<=p['project_budget'][k] for k in used) else 'fail',
        correction_and_probe_caps='pass' if category_bounds and target_bounds and bundle['state'].get('recovery_probes_used',0)<=2 else 'fail',
        preparation_and_reservations='pass' if p.get('sequential_reservations',{}).get('preparation_s')==manifest['preparation_wall_s'] and
            sum(c['charged']['wall_s'] for c in calls if c['request_id']=='offline-preparation')==manifest['preparation_wall_s'] and
            all(n.get('reserved_wall_s',n['order']['timeout_s'])<=n['order']['timeout_s'] for n in nodes.values()) else 'fail')
    return dict(version='mainline3.continue_gate@1.0.0',gates=gates,passed=all(v=='pass' for v in gates.values()),new_requests=len(attempts),usage=used,
        unknown_reservations=unknown,chains=chains,manifest_identity=digest(manifest),bundle_identity=digest(bundle),separate_material_audit=result['material_review'])
