from pathlib import Path
from tools.state_io import read,atomic_json
from tools.platform_store import Store
from tools.platform_host import Host
from tools.research_investigations import InvestigationDispatcher,InvestigationOrder
out=Path('evidence/research_mainline3_v1_complete_20261009');m=read(out/'validation_manifest.json');s=Store(Path(m['phases']['coordinated']['output']))
n=s.session('mainline3-coordinated')['state']['investigations']['reach-holding-interpretation']
d=InvestigationDispatcher(Host(s.root,'mainline3-coordinated'));raw=s.artifact(n['provider_response_refs'][-1]);r=d._decode(raw)
try:d._validate_return(InvestigationOrder.model_validate(n['order']),r,n['reads'])
except ValueError as exc:
 issue=getattr(exc,'issue',dict(code=str(exc)))
 atomic_json(out/'reach_final_local_revalidation.json',dict(provider_requests=0,original=n['provider_response_refs'][-1],issue=issue,valid_report=False,disposition='Correction allowance and two consecutive correction limit exhausted; no relabeling or further request.'))
 print(issue)
print(dict(session_status=s.session('mainline3-coordinated')['status'],requests=n['requests_by_purpose']))
