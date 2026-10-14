"""Engineering-selected acceptance demonstration; never counted as LLM research."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile
from tools.research import core as core
from tools.platform_host import Host


def plan(action,refs=(),**choices):
    return dict(action=action,supporting_evidence=list(refs),
        hypothesis='Engineering integration or recorded-input repeatability check, selected by the authorized delivery protocol.',
        expected_observation='Usable, owned evidence and a connected tool path; scientific acceptance is not required.',
        weakening_observation='Unusable returned structure/schedule, failed execution, or unchanged/duplicate search coordinates.',
        fixed_conditions='Frozen reach-and-hold target, mount, gravity, zero physical initialization, timing, six ideal tensions, seed17 and production NMPC stopping; only declared coordinates vary.',
        stopping_condition='One bounded mechanics attempt, usable-schedule replay, and two distinct fixed-structure control configurations; diagnosis at most two local production solves.',
        interpretation='Engineering-selected action; outcomes do not establish autonomous discovery, improvement, robustness or a unique cause.',**choices)


def diagnostic(host):
    s=core.state(host)
    if s.get('historical_diagnostic_sources'): ref=s['historical_diagnostic_sources'][0]
    else:
        folder=core.ROOT/'evidence/research_core_20261011';summary=core.read(folder/'scientific_summary.json')
        old=summary['local_solve_outcomes'][0];source_ref=old['original_worker_input']
        path=folder/'immutable_artifacts.tar.gz';manifest=core.read(folder/'archive_manifest.json')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['archive_sha256']: raise ValueError('HISTORICAL_ARCHIVE_HASH')
        with tarfile.open(path) as archive:
            raw=archive.extractfile('artifacts/'+source_ref['artifact_id']+'.json').read()
        if hashlib.sha256(raw).hexdigest()!=source_ref['artifact_id']:raise ValueError('HISTORICAL_MEMBER_HASH')
        value=json.loads(raw)
        value.update(imported_historical_evidence=True,original_study=summary['study_id'],
            source_reference=source_ref,previous_execution_cost_s=old['charged_numerical_s'],
            additional_numerical_s=0.,confirmation_eligible=False,
            purpose='Existing complete input at original version2 first divergent update1; inspect reconstruction conditions before assigning cause.')
        ref=core.save(host,value,'imported_historical_diagnostic_input')
        core.update(host,historical_diagnostic_sources=[ref])
    return core.dispatch(host,plan('diagnose',[ref],diagnostic=dict(execution=ref,update_id=1,repetitions=2,
        mode='production',iteration_cap=8)),'engineering-repeatability',origin='engineering')


def integration(host):
    solve=core.dispatch(host,plan('mechanics',mechanics=dict(design_bounds=[-1.,1.],design_initial=0.,
        objective_mode='task_gap',position_weight=1.,speed_weight=1.,secondary_coefficient=0.,
        initialization='pretension_0_2',substeps=1)), 'engineering-mechanics',origin='engineering')
    result=solve['result'];value=host.store.artifact(result['reference'])
    if not value.get('candidate') or not result.get('handoff'):
        out=dict(status='incomplete_mechanics_handoff',mechanics=solve)
    else:
        replay=core.dispatch(host,plan('replay',[result['reference']],mechanics_source=result['reference']),
            'engineering-replay',origin='engineering')
        d=result['handoff']['structure']['d']
        search=core.dispatch(host,plan('search',[result['reference'],replay['result']['reference']],search=dict(
            variables=['holding_tip_speed_weight'],bounds={'holding_tip_speed_weight':[.025,.10]},
            fixed=dict(d=d,holding_tip_speed_weight=.10,terminal_tip_speed_weight=.10),
            max_evaluations=2,step=.25,mechanics_source=result['reference'])),
            'engineering-control-search',origin='engineering')
        tested=search['result'].get('actually_explored',{})
        out=dict(status='connected' if len(tested.get('holding_tip_speed_weight',[]))>=2 else 'incomplete_actual_control_search',
            mechanics=solve,replay=replay,control_search=search,
            classification='engineering-selected; native LLM decisions occur in a separate session')
    ref=core.save(host,out,'engineering_integration_demonstration')
    core.update(host,integration_demonstration=ref)
    return dict(reference=ref,status=out['status'],resources=core.packet(host)['resource_use'])


def reconcile_inspection(host):
    """Repair reporting from already-computed initial checks, without a solve."""
    core.guard(host);s=core.state(host)
    if s.get('diagnostic_inspection_repairs'):return s['diagnostic_inspection_repairs']
    refs=[];corrections=[]
    for ref in s.get('diagnostics',[]):
        value=host.store.artifact(ref)
        for row in value.get('rows',[]):
            inspection=row.get('problem_inspection')
            if not inspection or not row.get('exact_variable_order_equal'):continue
            row['original_pre_solve_inspection_report']=dict(inspection)
            d=row['diagnostics']
            inspection.update(initial_objective=d['initial_objective'],
                initial_objective_difference=d['initial_objective']-inspection['original_initial_objective'],
                initial_violation=d['initial_scaled_violation'],variable_order_equal=row['exact_variable_order_equal'],
                reporting_correction='Used the actual pre-solve evaluation at the recorded initialized vector in solver order; original mistaken JSON-order report remains preserved.')
        repaired=core.save(host,value,'diagnostic_inspection_reporting_correction');refs.append(repaired)
        corrections.append(dict(original=ref,corrected=repaired,additional_numerical_s=0.,additional_solves=0))
    core.update(host,diagnostics=refs,diagnostic_inspection_repairs=corrections)
    return dict(status='corrected_from_saved_initial_checks',corrections=corrections)


def archive_incomplete(host):
    """Preserve the known failed run, including its final temporary progress file."""
    s=core.state(host);records=list(s.get('incomplete_execution_evidence',[]))
    covered={r['original_result']['artifact_id'] for r in records}
    for ref in s['results']:
        r=host.store.artifact(ref)
        if r['status']=='evaluated' or ref['artifact_id'] in covered:continue
        receipt=r['execution']['receipts']['simulation'];execution_id=receipt['execution_id']
        folder=host.store.root/'sessions'/r['owner_run_id']/'executions'/execution_id/'backend'
        files=[];counts={}
        for path in sorted(folder.iterdir()):
            if not path.is_file() or path.suffix not in ('.json','.xml','.tmp'):continue
            raw_hash=hashlib.sha256();buffer=io.BytesIO()
            with path.open('rb') as inp,gzip.GzipFile(fileobj=buffer,mode='wb',mtime=0) as compressed:
                while block:=inp.read(1024*1024):raw_hash.update(block);compressed.write(block)
            with host.store.transaction() as db:
                blob=host.store.put(db,buffer.getvalue(),media='application/gzip')
            files.append(dict(filename=path.name,reference=core.plain(blob),raw_sha256=raw_hash.hexdigest(),
                compression='gzip; preserves exact original bytes'))
            if path.name.startswith('nmpc_updates'):
                data=core.read(path);counts[path.name]=dict(updates=len(data),complete_records=sum('complete_update_record' in o for o in data),
                    last_time_s=data[-1]['time_s'] if data else None)
        metadata=dict(original_result=ref,execution_id=execution_id,owner_run_id=r['owner_run_id'],
            owning_study=host.run_id,original_receipt=receipt,files=files,counts=counts,
            status='known_failed_launch; complete saved inputs preserved; no terminal/holding acceptance',
            last_command='Final temporary progress includes the computed command before MuJoCo control assignment/stepping; do not infer completed application.',
            additional_scientific_executions=0,additional_numerical_s=0.)
        if not counts and 'nmpc_problem_' in (receipt.get('error') or ''):
            metadata.update(computed_updates_before_failure=1,complete_record_gap=1,
                missing_evidence='First controller solve returned, but graph path creation failed before progress persistence; original vector/action cannot be recovered and is not fabricated.')
        evidence=core.save(host,metadata,'incomplete_execution_saved_files');records.append(dict(reference=evidence,**metadata))
    searches=core.state(host)['searches']
    for v in searches.values():
        if v['pending']:
            v['known_failed_pending_proposal']=v['pending'];v['pending']=None;v['termination']='known_incomplete_backend_execution'
    core.update(host,incomplete_execution_evidence=records,searches=searches)
    return dict(status='preserved_known_failure_no_relaunch',evidence=[r['reference'] for r in records])


def continue_control(host):
    core.guard(host);s=core.state(host)
    original=s['integration_demonstration'];demo=host.store.artifact(original)
    solve=demo['mechanics'];replay=demo['replay'];source=solve['result']['reference']
    d=host.store.artifact(source)['candidate']['d']
    attempt=sum(k.startswith('engineering-control-search-after-') for k in s['searches'])+1
    search=core.dispatch(host,plan('search',[source,replay['result']['reference'],*s['results']],search=dict(
        variables=['holding_tip_speed_weight'],bounds={'holding_tip_speed_weight':[.025,.10]},
        fixed=dict(d=d,holding_tip_speed_weight=.10,terminal_tip_speed_weight=.10),max_evaluations=2,step=.25,mechanics_source=source)),
        'engineering-control-search-after-storage-repair-'+str(attempt),origin='engineering')
    tested=search['result'].get('actually_explored',{})
    out=dict(status='connected' if len(tested.get('holding_tip_speed_weight',[]))>=2 else 'incomplete_actual_control_search',
        mechanics=solve,replay=replay,control_search=search,original_incomplete_demonstration=original,
        classification='Engineering-selected new launches after a known charged failure; exploratory after failed BDF gates. No repeated mechanics or BDF.')
    ref=core.save(host,out,'engineering_integration_demonstration');core.update(host,integration_demonstration=ref)
    return dict(reference=ref,status=out['status'],resources=core.packet(host)['resource_use'])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['diagnostic','integration','reconcile-inspection','archive-incomplete','continue-control'])
    parser.add_argument('--spec',type=Path,required=True);args=parser.parse_args()
    spec=core.read(args.spec);host=Host(core.ROOT/'runs'/spec['study_id'],spec['study_id'],actor='unified-research')
    value={'diagnostic':diagnostic,'integration':integration,'reconcile-inspection':reconcile_inspection,
        'archive-incomplete':archive_incomplete,'continue-control':continue_control}[args.command](host)
    core.atomic_json(host.store.root/(args.command+'_engineering_receipt.json'),value)
    print(json.dumps({'command':args.command,'status':value.get('status'),
        'receipt':str(host.store.root/(args.command+'_engineering_receipt.json'))}))


if __name__=='__main__':main()
