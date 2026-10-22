"""Capture actual current-process health without sending or settling work."""
import json
import time
from tools.platform_host import Host
from tools.research.config import ROOT
from tools.research.agent import pending
from tools.research.state import state, core_hashes, science_hashes
from tools.rl.run import process_birth
from tools.state_io import atomic_json, read

h = Host(ROOT / 'runs/research/f3-autonomous-20261022-01',
         'f3-autonomous-20261022-01', actor='unified-research')
s = state(h)
supervision = read(ROOT / 'runs/f3-formal-supervision.json')
value = dict(
    study_id=h.run_id, captured_unix=time.time(), status=s['research_status'],
    supervision=supervision,
    supervisor_alive=process_birth(supervision['pid']) == supervision['birth'],
    heartbeat_age_s=round(time.time() - supervision['updated_unix'], 1),
    first_main_alive=bool(supervision.get('first_birth')) and process_birth(supervision['first_pid']) == supervision['first_birth'],
    supervised_cli_alive=bool(supervision.get('cli_birth')) and process_birth(supervision['cli_pid']) == supervision['cli_birth'],
    ledger=h.store.remaining(), nmpc_launches=s.get('nmpc_launches', 0),
    pending_owner=(s.get('pending') or {}).get('owner'),
    pending_provider_calls=[dict(request_id=r['request_id'], status=r['status']) for r in pending(h)],
    freeze=s['freeze'],
    protected_source_unchanged=core_hashes() == s['core_hashes'] and science_hashes() == s['profile']['science_hashes'],
    publication=read(ROOT / 'runs/f3-raw-publication-hold.json'),
)
atomic_json(ROOT / 'runs/f3-recovered-current.json', value)
print(json.dumps(value))
