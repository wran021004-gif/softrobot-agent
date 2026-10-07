"""Effective discovery projected from executable registry and builder declarations."""
from schemas.common import Contract
from tools.platform_store import plain


class CatalogRequest(Contract):
    pass


class CatalogResult(Contract):
    catalog: dict


def effective_capabilities(configuration, *, remaining=None, permission=None, validation=None, reg=None):
    from tools.platform_registry import registry
    from tools.parameter_catalog import effective_catalog
    from tools.research_tasks import task_adapter
    inp=plain(configuration); reg=reg or registry(); policy=inp['policy']
    permission=permission or {}; remaining=remaining or policy['budget']
    compatibility=task_adapter(inp).check_compatibility()['technical_compatibility']
    allowed=policy['tool_bindings']; parameters=effective_catalog(inp)
    operations=[]
    for _, definition in sorted(reg.extensions.items()):
        if definition.kind not in ('task','controller','backend','search','tool','linearizer','solver'):continue
        status=reg.inspect(definition,allowed)
        selected=any((policy.get(k) or {}).get('extension_id')==definition.extension_id and
            (policy.get(k) or {}).get('version')==definition.version for k in ('controller','backend','search'))
        computation=definition.kind in ('search','solver','linearizer') or definition.capabilities.get('category') in ('analysis','optimization')
        cost=dict(tool_calls=int(definition.kind=='tool'),
            backend_solves=int(definition.extension_id=='simulation.run'),
            model_calls=definition.capabilities.get('model_calls',0),
            mathematical_computation=computation)
        permitted=status['permitted'] if definition.kind=='tool' else selected
        resources=all(permission.get('resources',{}).get(r,0)>0 for r in definition.resources)
        budget=all(remaining.get(k,0)>=cost[k] for k in ('tool_calls','backend_solves','model_calls'))
        reasons=[]
        if not status['implementation_exists']:reasons.append('not_integrated')
        if not status['dependencies_available']:reasons.extend(status['reasons'])
        if compatibility['status']!='supported' and (selected or definition.kind in ('search','tool')):reasons.append('incompatible: '+compatibility['reason'])
        if not permitted:reasons.append('not_authorized')
        if inp['task']['family'] not in definition.capabilities.get('task_families',[inp['task']['family']]):
            reasons.append('incompatible: operation is outside this task family')
        if not budget or not resources:reasons.append('resource_unavailable')
        evidence=(validation or {}).get(definition.extension_id+'@'+definition.version,
            dict(status='not_yet_validated',scope='Registry declaration is implementation evidence only'))
        operations.append(dict(id=definition.extension_id,version=definition.version,kind=definition.kind,
            purpose=definition.description,implementation=dict(supported=status['implementation_exists'],dependencies_available=status['dependencies_available']),
            public_entry=dict(integrated=definition.kind=='tool' or selected,
                entry=definition.extension_id if definition.kind=='tool' else 'simulation.run' if selected else 'requires_bound_adapter',binding=definition.binding),
            compatibility=compatibility if selected else dict(status='requires_invocation_specific_bindings'),
            activity_permission=dict(permitted=permitted),resource_availability=dict(available=budget and resources),
            validation=evidence,unavailability_reasons=reasons,executable=not reasons,
            input_contract=definition.input_schema.__name__,output_contract=definition.output_schema.__name__,
            restrictions=definition.capabilities,cost=cost,cache=dict(enabled=definition.cache,
                rule='Exact dependencies, candidate, task and upstream evidence required; changed geometry invalidates scientific results')))
    return dict(version='research.effective_catalog@1.0.0',parameters=parameters,operations=operations,
        task=task_adapter(inp).describe(),compatibility=compatibility,
        authority='Discovery is not an activity grant. Host rechecks frozen policy, deadlines, dependency seals and ledger at invocation.')


def discover(ctx,args):
    return CatalogResult(catalog=effective_capabilities(ctx.input,
        remaining=ctx.store.spendable(ctx.run_id)['remaining'],
        permission=dict(resources=ctx.store.config()['exclusive_resources']),reg=ctx.reg))
