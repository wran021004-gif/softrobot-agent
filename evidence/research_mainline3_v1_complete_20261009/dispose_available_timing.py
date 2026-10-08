from pathlib import Path
from tools import research_v1_continue as activity
from tools.research_single_validation import stop
from tools.research_validation_activity import export
from tools.state_io import read,atomic_json
activity.OUT=(Path.cwd()/'evidence/research_mainline3_v1_complete_20261009').resolve()
host,m,p=activity.host_for('coordinated');host.resume()
sources=m['historical_parent']['order']['evidence'];timing=read(activity.OUT/'independent_timing_result.json')['report']
queries=[dict(reference=timing,pointer='',limit=100,byte_limit=65536)]
queries.extend(dict(reference=sources[0],pointer='',offset=i,limit=15,byte_limit=4096) for i in (0,15,30))
queries.extend(dict(reference=sources[1],pointer='/'+key,limit=100,byte_limit=4096) for key in ('holding','reach','official','limitations'))
order=activity.root_order(p,'principal-coordinated-v2','principal',
 'Independently inspect and formally dispose of the available new timing/integrity report. The separate reach/holding investigator exhausted its correction allowance without a valid report; no combined synthesis exists and B is not complete. This is an incremental disposition of the available report only. Read the complete report and original evidence, inspect each proposed adopted claim and its applicability, and select accept/defer/reject yourself. Distinguish recorded official historical reach/holding failures, Boolean recomputed test results, availability of recomputation, timing observations, and missing evidence. Do not equate a false test result with a computation not having been performed. Preserve explicit uncertainty and one-step prediction limitations; do not infer a dominant physical cause or real robot capability. No favorable verdict is required.',
 [*sources,timing],queries)
order['disposition_ids']=['timing-integrity-limits']
from examples.gvs_nmpc_route_experiment import load_credential
load_credential(Path.home()/'.codex/.env')
try:
 if order['investigation_id'] not in host.store.session(host.run_id)['state']['investigations']:activity.submit(host,order)
 report=activity.collect(host,order['investigation_id'])
 atomic_json(activity.OUT/'partial_principal_result.json',dict(report=report,targets=[dict(investigation_id='timing-integrity-limits',report=timing)],coordinator_synthesis=None,B_passed=False,missing_gate='Valid new reach report, two-report synthesis and corresponding full disposition chain'))
finally:
 stop(host,'Partial principal result preserved; failed reach node never retried, full B and C gates remain unmet')
 export(activity.OUT,'coordinated')
