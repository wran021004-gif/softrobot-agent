"""Retain the nonpass STOP and activate the already authorized expanded segment."""
from copy import deepcopy
import json
import subprocess
from tools.platform_host import Host
from tools.research.config import ROOT
from tools.research import core
from tools.research.provider import pending, record
from tools.research.state import state, save, update, require_research_authorization, guard
from tools.research.contracts import REGISTERED_MATHEMATICS_SCOPE
from tools.state_io import digest


def main():
    run='m1-elevated-auth-checked-20261101-b824e6d1'
    h=Host(ROOT/'runs/research'/run,run,actor='unified-research')
    old=state(h);ledger=h.store.remaining()
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise ValueError('COMMIT_REPAIR_BEFORE_BINDING')
    if (old['spec']['resolved_identity']!='a223bacab4fd10f3e6b9b5f020d250a0b4cbfd1e3c541b8b2d25aee2bf93b0fe'
            or old['research_status']!='stopped' or old.get('success_gate') or old.get('selected')
            or old['pending'] or pending(h) or ledger['occupied'] or old['pilot'].get('unconsumed_response')
            or ledger['used']['model_calls']!=36 or ledger['used']['tool_calls']!=34
            or old['mathematical_evaluations']!=16 or len(old['analysis_results'])!=7):
        raise ValueError('EXACT_SETTLED_EXPANDED_NONPASS_STOP_REQUIRED')
    with h.store.connect(True) as db:
        if db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]:
            raise ValueError('UNSEALED_RESERVATIONS')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    previous=save(h,old,'sealed_expanded_nonpass_state')
    approval=save(h,dict(user_approval=True,source='Current explicit user messages in this chat',
        approval_text='不要限制数学评估的次数，预算要充足。\n扩展他们的预算，然后继续study',
        previous_state=previous,previous_final_disposition=old['final_disposition'],
        repair_commit=commit,scope='Continue the same already expanded Study after clearing the historical STOP selector and correcting its stale allowance description. All costs and STOP evidence retained; science and budgets unchanged.'),
        'authorized_nonpass_continuation')
    current=deepcopy(old)
    current.update(research_status='ready',count_closeout=False,validation_extension_pending_binding=True,
        pending_authorized_continuation=approval)
    current.pop('final_disposition');current.pop('closed_unix',None)
    current.setdefault('research_continuations',[]).append(approval)
    with h.store.transaction() as db:h.store.update_state(db,run,current)
    prior=next(h.store.artifact(e['outputs'][0]) for e in reversed(h.store.events(run)) if e['kind']=='formal_study_authorization')
    scope=deepcopy(prior['scope']);assert REGISTERED_MATHEMATICS_SCOPE in scope['execution_scopes']
    scope.update(implementation_commit=commit,research_continuation=approval)
    ref=record(h,'formal_study_authorization',dict(user_approval=True,source='Current explicit user continuation directive',
        approval_text='扩展他们的预算，然后继续study',scope=scope,scope_identity=digest(scope)))
    core.bind(h,reason='Authorized same-Study continuation: clear historical STOP tool selector and describe current frozen grants accurately; all science, expanded budgets, costs and both STOP records retained')
    require_research_authorization(h);guard(h);now=state(h)
    assert h.store.remaining()['used']==ledger['used'] and now['profile']==old['profile']
    for key in ('spec','candidates','analysis_results','physical_replays','control_initializations'):
        assert now[key]==old[key]
    print(json.dumps(dict(study_id=run,previous_stop=old['final_disposition'],continuation=approval,
        approval=ref,approval_scope=digest(scope),resolved=now['spec']['resolved_identity'],freeze=now['freeze'],
        budgets=now['spec']['budgets'],used=ledger['used'],math_used=now['mathematical_evaluations'])))


if __name__=='__main__':main()
