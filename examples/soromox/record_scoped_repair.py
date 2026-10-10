"""One reviewed reporting repair; preserves the original admission result."""
import subprocess
from tools.research_soromox import host, RUN
from tools.platform_tasks import compile_input
from tools.platform_store import plain
from tools.state_io import atomic_json


def main():
    h=host(); old=h.store.session(h.run_id)['snapshot']; state=h.store.session(h.run_id)['state']
    assert state['soromox_freeze'].startswith('156b3de7')
    assert not state.get('soromox_numerical_pending')
    assert not subprocess.check_output(['git','status','--porcelain'],text=True).strip()
    after=compile_input(old['input'],h.reg)
    assert after['instance_identity']==old['instance_identity']
    changes={k:dict(before=v,after=after['dependencies'][k]) for k,v in old['dependencies'].items() if after['dependencies'][k]!=v}
    assert set(changes)<= {'math.soromox_describe@1.0.0','math.soromox_solve@1.0.0','math.soromox_replay@1.0.0'}
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    after.update(project_commit=commit,worktree_dirty=False)
    original=state['soromox_admission']; evidence=h.store.artifact(original)
    records=evidence['checks']['representative_states']; tol=evidence['checks']['tolerances']
    assert all(r['mapping_abs_error']<=tol['mapping_abs'] and r['state_jacobian_abs_error']<=tol['state_jacobian_abs']
        and r['virtual_work_sign_error']<=tol['state_jacobian_abs'] and all(f['passed'] for f in r['central_difference']) for r in records)
    assert evidence['checks']['native_factory_rejection'] and evidence['checks']['basis_mismatch']['max_abs_basis_error']>.1
    evidence['gate']='model_incompatible'; evidence['checks']['exact_mapping_passed']=True
    evidence['checks']['native_probe']['derivative_passed']=False
    evidence['original_admission_reference']=original
    evidence['reporting_repair_commit']=commit
    evidence['reasons']=[s for s in evidence['reasons'] if not s.startswith('Admission diagnostic failed;')]
    with h.store.transaction() as db:
        # The original empty byte-log with JSON media is retained; wrap its raw
        # bytes in a valid JSON record for evidence.read. No artifact is edited.
        raw=h.store.artifact(evidence['log_reference'],raw=True,db=db)
        evidence['original_log_reference']=evidence['log_reference']
        evidence['log_reference']=plain(h.store.put(db,dict(encoding='utf8',text=raw.decode('utf8',errors='replace'))))
        corrected=h.store.put(db,evidence); snapshot=h.store.put(db,after)
        detail=dict(commit=commit,changes=changes,science_changed=False,original_admission=original,
            corrected_admission=plain(corrected),new_numerical_checks=0,
            reasons=['Separate successful exact-routing checks from the failed native endpoint derivative',
                'Preserve the empty original log; expose a valid JSON wrapper'])
        ref=h.store.put(db,detail)
        db.execute('UPDATE sessions SET snapshot=? WHERE run_id=?',(snapshot.artifact_id,h.run_id))
        state['soromox_admission']=plain(corrected)
        h.store.update_state(db,h.run_id,state)
        h.store.event(db,h.run_id,'scoped_reporting_repair','recorded',outputs=[ref])
    atomic_json(RUN/'reporting_repair.json',detail)
    print(detail)


if __name__=='__main__':
    main()
