"""Versioned metric references and rendering; interpretation still needs review."""
import re
from tools.state_io import digest

VERSION = 'evidence_bound_reporting@3.0.0'
PROJECTION_VERSION = 'authoritative_metric_projection@1.0.0'


def authoritative_metrics(row, resolve):
    """New fact identities over original records; never edit legacy ledgers.

    Reach error belongs to evaluate.reach. Holding maxima belong to the
    profile's sampled-settling definition. Exact source/identity checks precede
    arithmetic; no approximate equality can rescue a foreign source.
    """
    eid = row['execution_id']; sources = row['sources']
    evaluation = resolve(sources['evaluation'])
    profile = resolve(sources['profile'])['detail']
    if (evaluation['source_execution_id'] != eid or
        evaluation['original_execution_id'] != eid or profile['execution_id'] != eid or
        profile['evaluation'] != sources['evaluation']):
        raise ValueError('CROSS_EXECUTION_SOURCE')
    if (evaluation['evaluator'], evaluation['evaluator_version']) != ('evaluate.reach', '1.0.0'):
        raise ValueError('WRONG_METRIC_DEFINITION')
    matches = [(i,m) for i,m in enumerate(evaluation['metrics']) if m['name']=='position_error']
    if len(matches)!=1 or matches[0][1]['units']!='m':
        raise ValueError('WRONG_METRIC_UNITS_OR_DEFINITION')
    i, metric = matches[0]
    definitions = {
        'terminal_error_m': (metric['value'], 'm', sources['evaluation'], f'/metrics/{i}/value'),
        'holding_max_error_m': (profile['sampled_settling']['max_error_m'], 'm', sources['profile'], '/detail/sampled_settling/max_error_m'),
        'holding_max_speed_m_s': (profile['sampled_settling']['max_speed_m_s'], 'm/s', sources['profile'], '/detail/sampled_settling/max_speed_m_s')}
    facts = {}; supersessions = []
    for name,(value,unit,source,pointer) in definitions.items():
        binding = dict(execution_id=eid, metric=name, unit=unit,
            structure_identity=row['structure_identity'],
            scientific_configuration_identity=row['scientific_configuration_identity'], source_artifact=source)
        legacy = 'f_' + digest(binding)[:20]
        corrected = dict(**binding, projection_version=PROJECTION_VERSION, source_pointer=pointer)
        ref = 'f_' + digest(corrected)[:20]
        facts[ref] = dict(**corrected, value=value)
        supersessions.append(dict(legacy_fact_id=legacy, corrected_fact_id=ref,
            legacy_value=row['legacy_metrics'][name], canonical_value=value,
            discrepancy_m=value-row['legacy_metrics'][name] if unit=='m' else None,
            reason='Value and pointer resolved from the same authoritative original record; distinct definitions retained'))
    return dict(version=PROJECTION_VERSION, facts=facts, supersessions=supersessions)


def model_packet(packet):
    """Transmit each execution's immutable source metadata once, not per fact."""
    result={k:v for k,v in packet.items() if k not in ('facts','executions','selected','latest')}
    result['selected_execution_id']=(packet.get('selected') or {}).get('execution_id')
    result['latest_execution_id']=(packet.get('latest') or {}).get('execution_id')
    result['executions']=[]
    for row in packet['executions']:
        sources={name:packet['facts'][ref]['source_artifact'] for name,ref in row['facts'].items()}
        result['executions'].append(dict(**row,source_artifacts={digest(v)[:16]:v for v in sources.values()},
            metric_sources={name:digest(v)[:16] for name,v in sources.items()}))
    result['facts']={ref:{k:f[k] for k in ('execution_id','metric','unit','value')} for ref,f in packet['facts'].items()}
    result['binding_resolution']='Each fact joins its execution row by execution_id; row supplies structure/scientific identities and metric_sources->source_artifacts. Full expanded immutable ledger retained locally.'
    return result


def render_text(report,facts):
    """Bound quantitative tokens for the compact diagnostic interpretation."""
    provenance=[]
    def paragraph(text):
        tokens=re.findall(r'\{\{([^{}]+)\}\}',text)
        remaining=re.sub(r'\{\{[^{}]+\}\}','',text)
        if re.search(r'\d',remaining):raise ValueError('UNBOUND_NUMBER_IN_PROSE')
        if '{' in remaining or '}' in remaining:raise ValueError('MALFORMED_BOUND_TOKEN')
        for key in tokens:
            if key not in facts:raise ValueError('UNRESOLVED_FACT')
            f=facts[key]
            provenance.append(dict(key=key,binding=f))
            text=text.replace('{{'+key+'}}',f"{f['value']!r} {f['unit']}")
        return text
    output={k:paragraph(report[k]) for k in ('report','recommendation')}
    output['unresolved']=[paragraph(t) for t in report['unresolved']]
    return dict(version=VERSION,report_identity=digest(report),fact_identity=digest(facts),
        provenance=provenance,rendered=output,interpretation_verified=False)


def ledger(summary, *, resolve=None):
    facts = {}
    executions = []
    for row in summary['results']:
        eid = row['execution_id']
        source = row['metrics']['source']
        if source['execution_id'] != eid:
            raise ValueError('CROSS_EXECUTION_SOURCE')
        refs = {}
        projection=None
        if resolve:
            projection=authoritative_metrics(dict(execution_id=eid,sources=source,
                structure_identity=row['structure_identity'],scientific_configuration_identity=row['scientific_configuration_identity'],
                legacy_metrics=row['metrics'].get('legacy_profile_metrics',row['metrics'])),resolve)
        for name, value in row['metrics'].items():
            if not isinstance(value, (int, float, bool)):
                continue
            unit = 'm/s' if name.endswith('_m_s') else 'm' if name.endswith('_m') else 's' if name.endswith('_s') else 'N' if name.endswith('_n') else '1'
            artifact = source['evaluation'] if name == 'terminal_error_m' else source['profile']
            binding = dict(execution_id=eid, metric=name, unit=unit,
                           structure_identity=row['structure_identity'],
                           scientific_configuration_identity=row['scientific_configuration_identity'],
                           source_artifact=artifact)
            if projection and name in ('terminal_error_m','holding_max_error_m','holding_max_speed_m_s'):
                ref,fact=next((key,f) for key,f in projection['facts'].items() if f['metric']==name)
                facts[ref]=fact;refs[name]=ref
                continue
            ref = 'f_' + digest(binding)[:20]
            facts[ref] = dict(**binding, value=value)
            refs[name] = ref
        executions.append({k:row[k] for k in ('execution_id','weights','structure_identity',
            'scientific_configuration_identity','observation_phase','replication_of') } | dict(facts=refs))
    return dict(version=VERSION, executions=executions, facts=facts,
        structure_definitions={row['structure_identity']:{k:v for k,v in row['decisions'].items() if not k.startswith('control/')} for row in summary['results']},
        replications=[{k:r[k] for k in ('original_execution_id','repeated_execution_id',
            'structure_identity','scientific_configuration_identity','measured_differences','comparison_scope')}
            for r in summary['replications']],
        selected=summary['selected'],latest=summary['latest'],
        counts={k:summary[k] for k in ('new_execution_count','novel_configuration_count','replication_count','batch_count')},
        usage=summary['usage'],stop=summary['stop'],limitations=summary['limits'])


def render(report, packet):
    """Never substitute a different reference to rescue a wrong claim."""
    facts=packet['facts']; rows={r['execution_id']:r for r in packet['executions']}
    if report['selected_execution_id'] != packet['selected']['execution_id']:
        raise ValueError('WRONG_SELECTION')
    if report['latest_execution_id'] != packet['latest']['execution_id']:
        raise ValueError('WRONG_LATEST')
    provenance=[]; lines=[]
    for claim in report['claims']:
        ref=claim['fact_ref']
        if ref not in facts:raise ValueError('UNRESOLVED_FACT')
        fact=facts[ref]
        if (claim['execution_id'],claim['metric']) != (fact['execution_id'],fact['metric']):
            raise ValueError('CROSS_EXECUTION_METRIC_BINDING')
        item=dict(claim=claim,binding=fact)
        value=fact['value'];display=str(value) if isinstance(value,bool) else format(value,'.6g')
        line=f"{fact['execution_id']} / {fact['metric']}: {display} {fact['unit']} (exact {value!r})"
        if claim.get('comparison_ref'):
            other=facts.get(claim['comparison_ref'])
            if other is None:raise ValueError('UNRESOLVED_COMPARISON')
            if (other['metric'],other['unit']) != (fact['metric'],fact['unit']):raise ValueError('COMPARISON_UNITS')
            if claim['relation'] not in ('less','greater','equal'):raise ValueError('COMPARISON_RELATION')
            actual='less' if value<other['value'] else 'greater' if value>other['value'] else 'equal'
            if actual!=claim['relation']:raise ValueError('CONTRADICTORY_COMPARISON')
            line+=f"; {actual} than {other['execution_id']}: {other['value']!r} {other['unit']}"
            item['comparison_binding']=other
        elif claim['relation']!='recorded':raise ValueError('COMPARISON_REFERENCE_REQUIRED')
        lines.append(line);provenance.append(item)
    grouped=[]
    for group in report['geometry_groups']:
        for eid in group['execution_ids']:
            if eid not in rows or rows[eid]['structure_identity']!=group['structure_identity']:
                raise ValueError('GEOMETRY_ATTRIBUTION')
            grouped.append(eid)
    if sorted(grouped)!=sorted(rows):raise ValueError('INCOMPLETE_OR_DUPLICATE_GEOMETRY_GROUPS')
    expected=[(r['original_execution_id'],r['repeated_execution_id']) for r in packet['replications']]
    actual=[(r['source_execution_id'],r['repeat_execution_id']) for r in report['replications']]
    if actual!=expected:raise ValueError('REPLICATION_BINDING')
    for a,b in actual:
        if rows[a]['scientific_configuration_identity']!=rows[b]['scientific_configuration_identity']:
            raise ValueError('REPLICATION_IDENTITY')
    text=report['interpretation']+'\n'+report['recommendation']+'\n'+'\n'.join(report['unresolved'])
    # Quantities belong in bound claims. Execution IDs belong in structured fields.
    if re.search(r'\d',text):raise ValueError('UNBOUND_NUMBER_IN_PROSE')
    return dict(version=VERSION,report_identity=digest(report),ledger_identity=digest(packet),
        provenance=provenance,rendered='\n'.join(lines)+'\n\n'+text,
        interpretation_verified=False)
