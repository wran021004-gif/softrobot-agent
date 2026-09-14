"""Public JSON adapter to an already loaded, owner-locked legacy runner.

The host owns loading, isolation and caller identity; submit owns all budgets,
permissions, caching and recovery. Never call the raw dispatch via this gateway.
"""
import json
from uuid import uuid4
from schemas.public_tools import ToolCall, Caller
from tools.public_feedback import normalize
from tools.state_io import read, atomic_json


def _record(book, result):
    """Separate invocation receipt, including preflight rejections and cache hits."""
    ref='public_calls/'+uuid4().hex+'/result.json'
    result={**result,'call_id':ref}
    atomic_json(book.root/ref,result)
    book.register(book.root/ref)
    book.save()
    return result


def invoke_bound(book, value, *, caller):
    from tools.public_catalog import entries
    from tools.dynamic_campaign import DynamicCampaign
    runtime = 'dynamics' if isinstance(book, DynamicCampaign) else 'workbench'
    caller = Caller.model_validate(caller).model_dump(mode='json')
    tool_id = value.get('tool_id', 'unknown') if isinstance(value, dict) else 'unknown'
    if not isinstance(tool_id,str):
        tool_id='unknown'
    resolved_version=None
    try:
        call = ToolCall.model_validate_json(json.dumps(value, allow_nan=False), strict=True)
        entry = entries().get(call.tool_id)
        if entry is None or entry['runtime'] != runtime:
            raise ValueError('UNKNOWN_TOOL: use the catalog for this bound runtime')
        resolved_version=entry['tool_version']
        if call.tool_version is not None and call.tool_version not in entry['accepted_versions']:raise ValueError('TOOL_VERSION_MISMATCH')
        arguments = entry['schema'].model_validate_json(json.dumps(call.arguments, allow_nan=False), strict=True).model_dump(mode='json')
    except (ValueError, TypeError) as exc:
        return _record(book,normalize(tool_id, dict(status='rejected', failure_code='INVALID_INPUT', message=str(exc)),
            call_id=uuid4().hex, caller=caller,tool_version=resolved_version, cost={'charged':{},'billing_owner':runtime,'stage':'public preflight; runner not invoked'}))
    previous = getattr(book, 'public_caller', None)
    book.public_caller = caller
    before=book.remaining()
    try:
        if runtime == 'dynamics':
            result, ref = book.submit(entry['wire_name'], arguments, call.reason, call.evidence)
        else:
            terminal={'stop_design':'stop','capability_missing':'capability_missing'}.get(entry['wire_name'])
            book.submit(dict(action=terminal or 'continue', tool=None if terminal else entry['wire_name'], arguments=arguments, reason=call.reason, evidence=call.evidence))
            row = book.state['decisions'][-1]
            ref = row.get('result_ref')
            if ref:
                result = read(book.root/ref)
            elif terminal and row.get('status')=='accepted':
                result=dict(status='completed', data={'workflow_status':book.state['status']})
            else:
                result = dict(status='rejected', failure_code='INVALID_INPUT', public=row.get('public'),message=row.get('failure_code', book.state.get('stop_reason','Rejected by runner')))
        # Old/reused receipts stay byte-for-byte historical; normalize this view.
        public = result.get('public')
        if public:
            public = normalize(call.tool_id,result,call_id=ref or uuid4().hex,caller=caller,
                tool_version=resolved_version,
                evidence=public.get('evidence',[]),details_ref=public.get('details_ref',ref),cost=public.get('cost',{}),
                provenance={**public.get('provenance',{}),'historical_feedback_version':public.get('tool_version')})
        else:
            public = normalize(call.tool_id, result, call_id=ref or uuid4().hex, caller=caller, details_ref=ref,
                tool_version=resolved_version,
                cost={'billing_owner':runtime,'accounting':'Inspect original runner decision/reservation; no additional adapter charge.'})
        if runtime == 'workbench' and book.state['decisions'][-1].get('status') == 'reused':
            public = {**public, 'cost':dict(billing_owner=runtime, cache_hit=True, charged={'decisions':1},
                accounting='Historical result reused; no new tool/backend charge.'),
                'provenance':{**public.get('provenance',{}),'reused_result_ref':ref}}
        public['provenance']['requested_tool_version']=call.tool_version
        return _record(book,public)
    except Exception as exc:
        remaining=book.remaining()
        return _record(book,normalize(call.tool_id,dict(status='failed',failure_code='TOOL_ERROR',message=str(exc)),
            call_id=uuid4().hex,caller=caller,tool_version=resolved_version,cost=dict(billing_owner=runtime,
                charged={k:before[k]-remaining[k] for k in before},accounting='Runner reservations retained; inspect partial decisions and receipts.')))
    finally:
        book.public_caller = previous
