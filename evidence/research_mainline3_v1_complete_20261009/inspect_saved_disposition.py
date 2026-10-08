from pathlib import Path
from tools.state_io import read,atomic_json
from tools.platform_store import Store
from tools.platform_host import Host
from tools.research_investigations import InvestigationDispatcher
out=Path('evidence/research_mainline3_v1_complete_20261009');m=read(out/'validation_manifest.json');s=Store(Path(m['phases']['coordinated']['output']));h=Host(s.root,m['phases']['coordinated']['active_run_id']);n=s.session(h.run_id)['state']['investigations']['principal-coordinated-v2'];d=InvestigationDispatcher(h);r=d._decode(s.artifact(n['provider_response_refs'][-1]));atomic_json(out/'principal_last_expanded_return.json',r.model_dump(mode='json'));print([x.model_dump(mode='json') for x in r.dispositions]);print(r.interpretation)
