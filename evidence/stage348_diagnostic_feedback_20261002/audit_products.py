"""Read-only artifact review; writes review/usage records, never model products."""
import json
import hashlib
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.state_io import read,atomic_json
from tools.platform_store import Store
from tools.platform_handoff import validate_selector,pointer
from tools.diagnostic_inventory import validate_gaps
from schemas.platform_handoff import EvidenceSelector,InventoryGap

cfg=read(ROOT/'examples/stage348_experiment.json');base=Path(cfg['run_directory']);dest=Path(cfg['evidence_directory'])
labels=[cfg['suffix_label'],cfg['pilot_label'],'pair1_single_context','pair1_dual_context','pair2_dual_context','pair2_single_context']
total=dict(model_calls=0,tool_calls=0,backend_solves=0,worker_calls=0,wall_s=0.)
tokens={};runs=[]
for label in labels:
    directory=base/label
    if not (directory/'outcome.json').exists():continue
    result=read(directory/'outcome.json');store=Store(directory);freeze=read(directory/'freeze.json')
    validation=[]
    for call in read(dest/label/'resolved_calls.json'):
        inv=call['invocation']
        for inv in inv.get('batch',[inv]):
            if inv['tool_id']!='diagnosis.submit':continue
            args=inv['arguments'];errors=[];count=0
            for name,selectors in args['fact_selectors'].items():
                for selector in selectors:
                    count+=1
                    try:validate_selector(store,EvidenceSelector.model_validate(selector))
                    except Exception as exc:
                        error=dict(fact=name,error=str(exc),submitted=selector)
                        try:error['actual']=pointer(store.artifact(selector['reference']),selector['pointer'])
                        except Exception:pass
                        errors.append(error)
            gaps=[]
            try:validate_gaps([InventoryGap.model_validate(g) for g in args['missing_evidence']],freeze['inventory'])
            except Exception as exc:gaps.append(str(exc))
            receipts=read(dest/label/'receipts.json')
            with store.connect(True) as db:
                row=db.execute('SELECT receipt FROM calls WHERE run_id=? AND request_id=?',(call['run_id'],inv['request_id'])).fetchone()
            receipt=json.loads(row[0]) if row and row[0] else None
            validation.append(dict(request_id=inv['request_id'],revised=bool(args.get('previous_report')),selector_count=count,
                selector_errors=errors,gap_errors=gaps,execution_status=receipt['execution_status'] if receipt else None))
    usage=result['usage']['used']
    for key,value in usage.items():total[key]+=value
    run_tokens={}
    for row in result['provider_usage']:
        for key,value in row.items():
            if isinstance(value,(int,float)):run_tokens[key]=run_tokens.get(key,0)+value
    for key,value in run_tokens.items():tokens[key]=tokens.get(key,0)+value
    receipts=read(dest/label/'receipts.json')
    failures=[dict(tool=r['tool_id'],request_id=r['request_id'],status=r['execution_status'],error=r.get('error'))
              for r in receipts if r['execution_status']!='completed']
    runs.append(dict(label=label,classification=result['classification'],mode=result['mode'],status=result['status'],
        stop_reason=result['stop_reason'],legal_completion=result['status']=='completed',
        feedback_path_complete=result['feedback_complete'],early_finish=result['status']=='completed' and not result['feedback_complete'],
        numerical_check_status=result['numerical_check_status'],usage=usage,tokens=run_tokens,elapsed_s=result['elapsed_s'],
        numerical_work=result['numerical_work']['used'],protocol_corrections=result['protocol_corrections'],
        provider_failures=[f for f in failures if f['tool'].startswith('model.')],
        business_failures=[f for f in failures if not f['tool'].startswith('model.')],report_validation=validation,monetary_cost=None))
record=dict(runs=runs,total_usage=total,total_tokens=tokens,limits=cfg['overall_limits'],
    within_limits=all(total[k]<=v for k,v in cfg['overall_limits'].items()),
    monetary_cost=None,cost_reason='Provider supplies tokens but no monetary cost.',
    historical_usage='Excluded from new totals; retained in suffix continuation_provenance.json',
    review_limit='Selector and structured gap checks do not certify scientific prose; delivery_review.json records implementer review.')
atomic_json(dest/'structured_review_and_usage.json',record)
integrity=[]
for run in runs:
    label=run['label'];freeze=read(base/label/'freeze.json')
    mismatches=[name for name,want in freeze['implementation']['files'].items()
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=want]
    manifest=read(dest/label/'sha256_manifest.json')
    export_errors=[name for name,want in manifest.items()
        if hashlib.sha256((dest/label/name).read_bytes()).hexdigest()!=want]
    integrity.append(dict(label=label,implementation_hash_mismatches=mismatches,
        exported_files_checked=len(manifest),export_hash_mismatches=export_errors,
        source_preserved=read(base/label/'outcome.json')['source_preserved']))
atomic_json(dest/'preservation_verification.json',dict(runs=integrity,
    all_passed=all(not r['implementation_hash_mismatches'] and not r['export_hash_mismatches'] and r['source_preserved'] for r in integrity)))
print(json.dumps(dict(runs=len(runs),new_usage=total,total_tokens=tokens.get('total_tokens'),integrity=integrity),indent=2))
