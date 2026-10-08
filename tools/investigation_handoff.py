"""Public explicit reuse of sealed historical reports; no fabricated new nodes."""
from pathlib import Path
from pydantic import Field
from schemas.common import Contract
from schemas.platform import EvidenceRef
from tools.platform_store import Store, plain
from tools.state_io import digest


class HistoricalHandoff(Contract):
    source_directory: str
    source_run_id: str
    source_project_id: str
    source_database_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    source_node: str
    report: EvidenceRef
    historical_validation: EvidenceRef


def bind(ctx, args):
    from tools.research_investigations import InvestigationDispatcher, InvestigationReturn
    from tools.research_single_validation import sha
    from tools.spec_tools import ROOT
    dispatcher=InvestigationDispatcher(ctx.host)
    _,grant=dispatcher._grant();dispatcher._principal_authority()
    declared=grant.get('historical_handoffs',[])
    if plain(args) not in declared:raise ValueError('HISTORICAL_HANDOFF_NOT_GRANTED')
    source=(ROOT/args.source_directory).resolve()
    if not source.is_relative_to((ROOT/'runs').resolve()):raise ValueError('HISTORICAL_SOURCE_OUT_OF_WORKSPACE_RUNS')
    old=Store(source)
    if sha(old.db)!=args.source_database_sha256:raise ValueError('HISTORICAL_DATABASE_CHANGED')
    session=old.session(args.source_run_id)
    if session['status']!='stopped' or old.config()['project_id']!=args.source_project_id:raise ValueError('HISTORICAL_STOPPED_IDENTITY_REQUIRED')
    node=session['state']['investigations'][args.source_node]
    if node['status']!='completed' or node['result']!=plain(args.report):raise ValueError('HISTORICAL_COMPLETED_REPORT_BINDING_REQUIRED')
    report=old.artifact(args.report)
    InvestigationReturn.model_validate(report)
    current=ctx.store.artifact(args.report)
    if current!=report:raise ValueError('HISTORICAL_REPORT_CONTENT_CHANGED')
    validation=ctx.store.artifact(args.historical_validation)
    if validation['historical_node_identity']!=digest(node):raise ValueError('HISTORICAL_VALIDATION_BINDING_MISMATCH')
    entry=dict(status='completed',result=plain(args.report),kind='historical_reuse',
        original=plain(args),original_execution_id=old.lookup(node.get('request_run_id',args.source_run_id),'investigation-'+args.source_node)['execution_id'],
        old_validation=validation,new_investigation_executed=False)
    with ctx.store.transaction() as db:
        state=ctx.store.session(ctx.run_id,db)['state']
        if args.source_node in state.get('investigations',{}) or args.source_node in state.get('historical_investigations',{}):raise ValueError('HISTORICAL_NODE_COLLISION')
        state.setdefault('historical_investigations',{})[args.source_node]=entry
        ctx.store.update_state(db,ctx.run_id,state)
        ctx.store.event(db,ctx.run_id,'historical_investigation_handoff','bound',inputs=[args.report,args.historical_validation],outputs=[ctx.store.put(db,entry)])
    return dispatcher.recover(args.source_node)
