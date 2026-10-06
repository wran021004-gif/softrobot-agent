"""Versioned metric references and rendering; interpretation still needs review."""
import re
from tools.state_io import digest

VERSION = 'evidence_bound_reporting@3.0.0'


def model_packet(packet):
    """Transmit each execution's immutable source metadata once, not per fact."""
    result={k:v for k,v in packet.items() if k not in ('facts','executions','selected','latest')}
    result['selected_execution_id']=packet['selected']['execution_id']
    result['latest_execution_id']=packet['latest']['execution_id']
    result['executions']=[]
    for row in packet['executions']:
        sources={name:packet['facts'][ref]['source_artifact'] for name,ref in row['facts'].items()}
        result['executions'].append(dict(**row,source_artifacts={digest(v)[:16]:v for v in sources.values()},
            metric_sources={name:digest(v)[:16] for name,v in sources.items()}))
    result['facts']={ref:{k:f[k] for k in ('execution_id','metric','unit','value')} for ref,f in packet['facts'].items()}
    result['binding_resolution']='Each fact joins its execution row by execution_id; row supplies structure/scientific identities and metric_sources->source_artifacts. Full expanded immutable ledger retained locally.'
    return result


def ledger(summary):
    facts = {}
    executions = []
    for row in summary['results']:
        eid = row['execution_id']
        source = row['metrics']['source']
        if source['execution_id'] != eid:
            raise ValueError('CROSS_EXECUTION_SOURCE')
        refs = {}
        for name, value in row['metrics'].items():
            if not isinstance(value, (int, float, bool)):
                continue
            unit = 'm/s' if name.endswith('_m_s') else 'm' if name.endswith('_m') else 's' if name.endswith('_s') else '1'
            artifact = source['evaluation'] if name == 'terminal_error_m' else source['profile']
            binding = dict(execution_id=eid, metric=name, unit=unit,
                           structure_identity=row['structure_identity'],
                           scientific_configuration_identity=row['scientific_configuration_identity'],
                           source_artifact=artifact)
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
