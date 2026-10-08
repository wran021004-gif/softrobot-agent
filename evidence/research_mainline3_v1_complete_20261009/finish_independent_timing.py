from pathlib import Path
from tools import research_v1_continue as activity
from tools.state_io import atomic_json
from tools.research_single_validation import stop
from tools.research_validation_activity import export
activity.OUT=(Path.cwd()/'evidence/research_mainline3_v1_complete_20261009').resolve()
host,m,p=activity.host_for('coordinated')
if host.store.session(host.run_id)['state']['investigations']['reach-holding-interpretation']['status']!='failed':raise ValueError('EXPECTED_CONFIRMED_REACH_FAILURE')
# Application stop after one independent role failed is not a user stop. No old
# activity or failed node is reopened, and no allowance or deadline is reset.
host.resume()
with host.store.transaction() as db:
 host.store.event(db,host.run_id,'independent_missing_role_continuation','authorized',outputs=[host.store.put(db,dict(role='timing-integrity-limits',same_activity_and_grant=True,failed_reach_node_retried=False,reason='Finish independently authorized missing report; B and C still require the absent reach report.'))])
from examples.gvs_nmpc_route_experiment import load_credential
load_credential(Path.home()/'.codex/.env')
child=next(c for c in p['authorized_children'] if c['investigation_id']=='timing-integrity-limits')
try:
 if child['investigation_id'] not in host.store.session(host.run_id)['state']['investigations']:activity.submit(host,child)
 result=activity.collect(host,child['investigation_id'])
 atomic_json(activity.OUT/'independent_timing_result.json',dict(report=result,completed=True,B_passed=False,blocked_gate='Valid new reach/holding report absent; its correction allowance exhausted'))
finally:
 stop(host,'B required reach-report gate exhausted; preserve independent timing result. C not authorized to pass missing B gate.')
 export(activity.OUT,'coordinated')
