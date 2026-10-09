"""Compact factual report plus one content-addressed immutable archive."""
from pathlib import Path
import hashlib
import io
import json
import tarfile
import time
from tools.platform_store import plain
from tools.state_io import atomic_json,digest


def summarize(h):
    state=h.store.session(h.run_id)['state'];searches=list(state.get('design_searches',{}).values())
    with h.store.connect(True) as db:
        calls=[dict(r) for r in db.execute('SELECT * FROM calls')]
    attempts=[r for r in calls if r['request_id']=='complete-simulation']
    events=h.store.events(h.run_id);responses={};sends=[]
    for e in events:
        if e['kind']=='r3_request' and e['status']=='sent':sends.append(e)
        if e['kind']=='r3_response':responses[e['request_id']]=h.store.artifact(e['outputs'][0])
    rows=[r for s in searches for r in s['evaluated']];confirmations=state['mixed_confirmations']
    from tools.research_mixed_design import result_from_state
    public_searches=[r for r in calls if r.get('receipt') and json.loads(r['receipt'])['tool_id']=='search.design_mixed']
    support=[]
    signatures=sorted(set((r['resolved']['segment_count'],r['resolved']['parameters']['proximal_tendons'],
        r['resolved']['parameters']['distal_tendons']) for r in rows))
    for n,p,d in signatures:
        support.append(dict(segment_count=n,proximal_tendons=p,distal_tendons=d,declared=True,constructed=True,
            numerically_prepared=True,fully_executed=any(r['resolved']['segment_count']==n and
                r['resolved']['parameters']['proximal_tendons']==p and r['resolved']['parameters']['distal_tendons']==d and
                r['execution_status'] in ('accepted','valid_failure') for r in rows)))
    updates=0
    for r in rows+confirmations:updates+=r['evidence'].get('feedback',{}).get('actual_applied_control_updates') or 0
    return dict(activity_id=h.run_id,status=state['mixed_status'],implementation_commit=state.get('mixed_freeze'),
        specification=state['mixed_spec'],problems=[s['problem'] for s in searches],
        optimization_results=[result_from_state(h,s) for s in searches],confirmations=confirmations,
        original_principal_decisions=[dict(reference=ref,content=h.store.artifact(ref)) for ref in state['mixed_decisions']],
        support=dict(declared_segment_counts=[2,3,4],declared_group_counts=[3,4],constructed_and_executed=support,
            additional_offline_constructed=[[2,3,3],[3,4,4],[4,3,4]],unexecuted_domain_is_not_validated=True),
        demonstrated=dict(generated_beyond_T0_T3=any(r['resolved']['segment_count']==4 or r['resolved']['tendon_count']==7 for r in rows),
            segment_count_explored=len({r['resolved']['segment_count'] for r in rows})>1,
            tendon_count_explored=len({r['resolved']['tendon_count'] for r in rows})>1,
            feedback_generated_continuous_proposal=any(r['phase']=='feedback_coordinate' and r['used_feedback'] for r in rows),
            fixed_and_coupled_constraints_respected=bool(rows) and all(r['constraint_outcomes']['length_sum'] and
                r['constraint_outcomes']['individual_length_bounds'] for r in rows),
            joint_physical_acceptance=any(r['feasible'] for r in rows),fresh_confirmation_executed=bool(confirmations),
            confirmation_accepted=any(r['feasible'] for r in confirmations),principal_consumed_feedback=bool(state['mixed_decisions'])),
        resources=dict(ledger=h.store.remaining(),actual_provider_sends=len(sends),
            conservative_provider_reservations=sum(r['request_id'].startswith('r3-request-') for r in calls),
            development_backend_attempts=sum(not r['run_id'].startswith('confirm-') for r in attempts),
            confirmation_backend_attempts=sum(r['run_id'].startswith('confirm-') for r in attempts),
            total_backend_attempts=len(attempts),technical_replacements=0,public_search_operations=len(public_searches),
            public_math_operations=0,internal_nmpc_updates=updates,additional_model_workers=0,
            elapsed_s=time.time()-state['mixed_spec']['started_unix'],provider_responses=responses,
            provider_reported_tokens={k:sum((r.get('usage') or {}).get(k,0) for r in responses.values()) for k in
                ('prompt_tokens','completion_tokens','total_tokens')},monetary_cost=None),
        limitations=['Bounded, single-seed integration study; unsearched configurations remain open.',
            'Ideal independent tensions; actuator travel/velocity and motor dynamics/mass are not validated.',
            'Sampled reach-and-hold acceptance, no continuous-time guarantee, robustness, statistical superiority, real-time performance or global optimum.',
            'Archived executed-radius profiles are the fixed source recipe; baseline Young moduli are 7.2 MPa proximal and 5.4 MPa distal.',
            'Guide counts, routing, reduced dimensions, total force-limit sum and wall-bounded solver selection confound cross-topology attribution.',
            'No arbitrary tendon graphs or coupled actuation; historical outcomes retain original versions and owners.'])


def export(h,destination=None):
    from tools.research_mixed_design import OUT
    destination=Path(destination or OUT);destination.mkdir(parents=True,exist_ok=True)
    summary=summarize(h);atomic_json(destination/'result_summary.json',summary)
    with h.store.connect(True) as db:
        artifacts=[dict(r) for r in db.execute('SELECT id,media,body FROM artifacts ORDER BY id')]
        calls=[dict(r) for r in db.execute('SELECT * FROM calls')]
        sessions=[dict(r) for r in db.execute('SELECT * FROM sessions')]
        events=[dict(r) for r in db.execute('SELECT * FROM events')]
    members=[];artifact_index=[]
    archive=destination/'immutable_artifacts.tar.gz';temp=destination/'immutable_artifacts.tmp.tar.gz'
    with tarfile.open(temp,'w:gz') as tf:
        def add(name,body):
            item=tarfile.TarInfo(name);item.size=len(body);item.mtime=0;tf.addfile(item,io.BytesIO(body))
            members.append(dict(path=name,bytes=len(body),sha256=hashlib.sha256(body).hexdigest()))
        for a in artifacts:
            body=bytes(a['body'])
            if hashlib.sha256(body).hexdigest()!=a['id']:raise ValueError('STORE_ARTIFACT_HASH_MISMATCH')
            path='store/artifacts/'+a['id']+('.json' if a['media']=='application/json' else '.blob')
            add(path,body);artifact_index.append(dict(artifact_id=a['id'],media_type=a['media'],archive_member=path,bytes=len(body)))
        for name,value in [('sessions.json',sessions),('events.json',events),('calls.json',calls)]:
            add('metadata/'+name,json.dumps(value,ensure_ascii=False,sort_keys=True).encode('utf8'))
        folder=h.store.root/'framework_sessions'
        if folder.exists():
            for path in sorted(folder.rglob('*')):
                if path.is_file():add('framework_sessions/'+path.relative_to(folder).as_posix(),path.read_bytes())
        for name in ('implementation_freeze.json','framework_configuration.json','historical_comparison.json'):
            path=h.store.root/name
            if path.exists():add('metadata/'+name,path.read_bytes())
    temp.replace(archive)
    atomic_json(destination/'archive_manifest.json',dict(archive=archive.name,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
        bytes=archive.stat().st_size,members=members))
    atomic_json(destination/'store_manifest.json',dict(artifacts=artifact_index,original_owners_preserved=True,
        retrieval='Extract store/artifacts/<sha>.json or .blob; verify against archive_manifest member hash. Live recovery uses original Store.'))
    atomic_json(destination/'ledger.json',dict(config=h.store.config(),usage=h.store.remaining(),calls=calls))
    # One focused integrity pass: validate every archived member and every new
    # completed execution's evidence references, without another backend launch.
    expected={m['path']:m for m in members}
    with tarfile.open(archive,'r:gz') as tf:
        for m in tf:
            body=tf.extractfile(m).read()
            if m.name not in expected or hashlib.sha256(body).hexdigest()!=expected[m.name]['sha256']:raise ValueError('EXPORT_MEMBER_INTEGRITY')
    def references(value):
        if isinstance(value,dict):
            if set(('artifact_id','media_type'))<=set(value):yield {k:value[k] for k in ('artifact_id','media_type')}
            else:
                for v in value.values():yield from references(v)
        elif isinstance(value,list):
            for v in value:yield from references(v)
    checked=set()
    for s in summary['optimization_results']:
        for r in s['evaluated']:
            for ref in references(r['evidence']):h.store.artifact(ref,raw=True);checked.add(ref['artifact_id'])
    for r in summary['confirmations']:
        for ref in references(r['evidence']):h.store.artifact(ref,raw=True);checked.add(ref['artifact_id'])
    integrity=dict(status='passed',archive_members=len(members),evidence_references=len(checked),
        sealed_simulations=len([c for c in calls if c['request_id']=='complete-simulation' and c['receipt']]),new_backend_launches=0)
    atomic_json(destination/'delivery_integrity.json',integrity)
    return integrity
