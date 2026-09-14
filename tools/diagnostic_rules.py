"""Rules declare required signals and applicability, separate from observations."""
from dataclasses import dataclass
from importlib import import_module
from tools.artifact_tools import file_hash
from tools.spec_tools import ROOT


@dataclass(frozen=True)
class Rule:
    version: str
    signal: str
    entity: str
    backends: tuple[str,...]
    binding: str


RULES={'contact_presence':Rule('1.0.0','solver_contact_count','contact',('matlab','mujoco'),
    'tools.rules.contact_presence:evaluate')}


def run_saved_rule(root, registry, arguments):
    from tools.observation_contract import SavedObservation
    args=arguments;rule=RULES.get(args['rule_id'])
    if rule is None:raise ValueError('UNKNOWN_RULE')
    if rule.version!=args['rule_version']:raise ValueError('RULE_VERSION_MISMATCH')
    source=rule.binding.split(':')[0].replace('.','/')+'.py'
    report=dict(rule_id=args['rule_id'],rule_version=rule.version,rule_sha256=file_hash(ROOT/source),
        status='NOT_APPLICABLE',events=[],backend_solves=0,rescoring=False,
        semantics='Saved observations, rule judgments and causal hypotheses are separate fields.')
    if args['backend'] not in rule.backends or args['entity']!=rule.entity:
        report['reason']='Rule backend/entity requirements not met';return report
    observation=SavedObservation(root,registry,args['result_ref'],args['backend'])
    query=observation.query(rule.signal,args['t_start_s'],args['t_end_s'])
    report.update(query=query,source_hashes=observation.hashes,model=observation.model.capabilities())
    if query['status']=='MISSING_DATA':report['status']='MISSING_DATA';return report
    try:
        module,fn=rule.binding.split(':')
        events=getattr(import_module(module),fn)(query,observation.shared)
        report.update(status='EVENTS_FOUND' if events else 'NO_EVENT',events=events)
    except (ValueError,TypeError,KeyError) as exc:
        report.update(status='EXECUTION_FAILED',reason=str(exc))
    return report
