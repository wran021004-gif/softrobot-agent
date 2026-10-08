"""DeepSeek Chat Completions transport; no workbench or platform state."""
import json
import errno
import re
import socket
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('DEEPSEEK_REDIRECT_REFUSED')


def sanitize_provider_text(value, key, limit=8192):
    """Retain useful error text without headers, keys or URL credentials."""
    value = str(value).replace(key, '[REDACTED]') if key else str(value)
    value = re.sub(r'(?i)authorization\s*[:=]\s*[^\r\n]+', 'Authorization: [REDACTED]', value)
    value = re.sub(r'(?i)bearer\s+[^\s"\'<>]+', 'Bearer [REDACTED]', value)
    value = re.sub(r'(?i)((?:cookie|set-cookie|x-api-key)\s*[:=]\s*)[^\r\n]+', r'\1[REDACTED]', value)
    value = re.sub(r'(?i)(?<![a-z0-9+.-])([a-z][a-z0-9+.-]*://)[^/\s@]+@', r'\1[REDACTED]@', value)
    value = re.sub(r'(?<![\w])[^:\s/@]+:[^@\s/]+@', '[REDACTED]@', value)
    value = re.sub(r'(?i)((?:api[_-]?key|access_token|password|token)["\']?\s*[:=]\s*["\']?)[^\s"\'&,}]+', r'\1[REDACTED]', value)
    return value if limit is None else value[:limit]


def failure_details(exc, config, started, key):
    reason = exc.reason if isinstance(exc, URLError) else exc
    category = 'unknown'
    if isinstance(exc, HTTPError):
        category = 'http'
    elif isinstance(reason, socket.gaierror):
        category = 'dns'
    elif isinstance(reason, ssl.SSLError):
        category = 'tls'
    elif isinstance(reason, TimeoutError) or getattr(reason, 'errno', None) == errno.ETIMEDOUT:
        category = 'timeout'
    elif isinstance(reason, ConnectionError) or getattr(reason, 'errno', None) in (
            errno.ECONNREFUSED, errno.ECONNRESET, errno.ECONNABORTED, errno.ENETUNREACH, errno.EHOSTUNREACH):
        category = 'connection'
    elif isinstance(reason, str) and 'tunnel connection failed' in reason.lower():
        category = 'proxy'
    return dict(exception_type=type(exc).__name__, reason_type=type(reason).__name__,
                os_error_number=getattr(reason, 'errno', None), windows_error_number=getattr(reason, 'winerror', None),
                category=category, elapsed_s=time.monotonic()-started,
                endpoint_hostname=urlsplit(config['base_url']).hostname,
                reason_message=sanitize_provider_text(reason, key))


def response_identifiers(headers):
    """Only provider request identifiers; never copy a header dictionary."""
    for name in ('x-request-id', 'x-ds-request-id', 'request-id'):
        value = headers.get(name) if headers else None
        if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9._:-]{1,128}', value):
            return value
    return None


ERROR_BODY_LIMIT=8192
ERROR_FIELDS=('code','type','param','message')
ERROR_OMISSIONS={'missing','too_large','invalid_encoding','invalid_json','invalid_shape',
    'sensitive','request_echo','unexpected_fields','invalid_field','message_over_limit','read_failed'}


def safe_server_error(body,key='',payload=None):
    """Allowlisted structured error only. Never retain raw or redacted bodies."""
    empty={k:None for k in ERROR_FIELDS}
    def omit(reason):return dict(fields=empty,omission_reasons=[reason],raw_body_saved=False)
    if body is None:return omit('missing')
    if isinstance(body,bytes):
        if len(body)>ERROR_BODY_LIMIT:return omit('too_large')
        try:body=body.decode('utf-8')
        except UnicodeError:return omit('invalid_encoding')
    if isinstance(body,str):
        try:size=len(body.encode('utf-8'))
        except UnicodeError:return omit('invalid_encoding')
        if size>ERROR_BODY_LIMIT:return omit('too_large')
        try:body=json.loads(body)
        except (ValueError,RecursionError):return omit('invalid_json')
    if not isinstance(body,dict):return omit('invalid_shape')
    from tools.context_assembly import _no_secrets
    try:_no_secrets(body)
    except (ValueError,RecursionError):return omit('sensitive')
    if key and key in json.dumps(body,ensure_ascii=False):return omit('sensitive')
    error=body.get('error',body)
    if not isinstance(error,dict):return omit('invalid_shape')
    if set(body)-({'error'} if 'error' in body else set(ERROR_FIELDS)) or set(error)-set(ERROR_FIELDS):
        return omit('unexpected_fields')  # Includes nested request/header echoes.
    fields=dict(empty);reasons=[]
    for name in ERROR_FIELDS:
        value=error.get(name)
        if value is None:continue
        if name=='code' and type(value) is int:
            if abs(value)<=2**31:fields[name]=value
            else:reasons.append('invalid_field')
            continue
        if not isinstance(value,str):reasons.append('invalid_field');continue
        if sanitize_provider_text(value,key,None)!=value:
            reasons.append('sensitive');continue
        if name!='message':
            if re.fullmatch(r'[A-Za-z0-9_.:/\[\]-]{1,128}',value):fields[name]=value
            else:reasons.append('invalid_field')
            continue
        if len(value)>512:reasons.append('message_over_limit');continue
        # Messages containing structured/text request echoes are not diagnostics.
        echoed=any(c in value for c in '{}\r\n')
        def inspect(v):
            if isinstance(v,dict):return any(inspect(x) for x in v.values())
            if isinstance(v,list):return any(inspect(x) for x in v)
            if isinstance(v,str):
                if len(v)>=16 and v in value:return True
                if v.lstrip().startswith(('{','[')):
                    try:return inspect(json.loads(v))
                    except (ValueError,RecursionError):return False
            return False
        if echoed or (payload and inspect(payload.get('messages',[]))):
            reasons.append('request_echo');continue
        fields[name]=value
    return dict(fields=fields,omission_reasons=sorted(set(reasons)),raw_body_saved=False)


def safe_failure_metadata(exc, config, started, *, classify_transport=False):
    """Reuse the transport classifier, filtering exception attributes by allowlist.

    No arbitrary exception text/body/headers or environment is archived here.
    Classification says nothing about sending, billing or retry permission.
    """
    supplied = getattr(exc, 'provider_response', None)
    supplied = supplied if isinstance(supplied, dict) else {}
    details = supplied.get('failure_details')
    if not isinstance(details, dict):
        details = failure_details(exc, config, started, '') if classify_transport else {}
    safe = {}
    for field in ('exception_type', 'reason_type'):
        value = details.get(field)
        safe[field] = value if isinstance(value, str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]{0,99}', value) else None
    safe['category'] = details.get('category') if details.get('category') in (
        'unknown', 'http', 'dns', 'tls', 'timeout', 'connection', 'proxy') else 'unknown'
    for field in ('os_error_number', 'windows_error_number'):
        value = details.get(field)
        safe[field] = value if type(value) is int else None
    value = details.get('reason_message')
    # Only the existing classifier's sanitized, bounded message is retained.
    safe['reason_message'] = sanitize_provider_text(value, '', 512) if isinstance(value, str) else None
    state = getattr(exc, 'transport_state', {})
    state = state if isinstance(state, dict) else {}
    status = supplied.get('status_code',state.get('http_status'))
    safe['http_status'] = status if type(status) is int and 100 <= status <= 599 else None
    safe['provider_request_id'] = response_identifiers({'x-request-id':state.get('provider_request_id')})
    for field in ('transport_attempted', 'response_received', 'response_body_received'):
        safe[field] = state.get(field) if type(state.get(field)) is bool else None
    safe['transport_stage'] = state.get('stage') if state.get('stage') in (
        'request_preparation', 'transport', 'response_read', 'response_parse') else None
    server=supplied.get('server_error')
    if isinstance(server,dict):
        filtered=safe_server_error(server.get('fields'))
        reasons=server.get('omission_reasons')
        reasons=reasons if isinstance(reasons,list) else []
        filtered['omission_reasons']=sorted(set(filtered['omission_reasons']) | {
            r for r in reasons if isinstance(r,str) and r in ERROR_OMISSIONS})
        safe['server_error']=filtered
    else:safe['server_error']=safe_server_error(None)
    return safe


class CompletionResponse(dict):
    """Ordinary response body plus allowlisted transport observations out of band."""
    def __init__(self, body, metadata):
        super().__init__(body)
        self.transport_metadata = metadata


def request_completion(config, payload, key):
    if config.get('context_guard'):
        from tools.context_assembly import check_outgoing_request
        check_outgoing_request(payload,config,config.get('context_purpose','final_report'))
    url = config['base_url'].rstrip('/') + '/chat/completions'
    request = Request(url, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                      headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    started = time.monotonic()
    state = dict(stage='transport', transport_attempted=True, response_received=None,
                 response_body_received=None,http_status=None, provider_request_id=None)
    observer=config.get('_response_observer')
    def observe(body=None):
        if observer is None:return
        text=None;omission=None
        if body is not None:
            try:text=body.decode('utf-8',errors='strict')
            except UnicodeError:omission='body_not_utf8; original bytes not retained'
            if text is not None and sanitize_provider_text(text,key,None)!=text:
                text=None;omission='sensitive_response_text; original body not retained'
        observer(dict(state),text,omission)
        if omission and omission.startswith('sensitive_response_text'):
            raise ValueError('INVESTIGATION_RESPONSE_SECRET_TEXT')
    try:
        with build_opener(NoRedirect).open(request, timeout=config['timeout_s']) as response:
            state.update(stage='response_read', response_received=True,
                         http_status=getattr(response, 'status', None),
                         provider_request_id=response_identifiers(getattr(response, 'headers', None)))
            observe()  # Reception facts survive a later read, parse or body write failure.
            body = response.read()
            state['response_body_received']=True
            observe(body)  # Safe original representation is durable before business decoding.
            state['stage'] = 'response_parse'
            parsed = json.loads(body.decode('utf-8'))
            if not isinstance(parsed, dict):
                raise ValueError('DEEPSEEK_RESPONSE_OBJECT_REQUIRED')
            return CompletionResponse(parsed, {**state, 'elapsed_s':time.monotonic()-started})
    except HTTPError as exc:
        # Preserve endpoint rejection evidence, never headers or credentials.
        state.update(response_received=True, http_status=exc.code,
                     provider_request_id=response_identifiers(exc.headers))
        try:
            body=exc.read(ERROR_BODY_LIMIT+1)
            state['response_body_received']=True if len(body)<=ERROR_BODY_LIMIT else None
            server=safe_server_error(body,key,payload)
        except Exception:
            server=dict(fields={k:None for k in ERROR_FIELDS},omission_reasons=['read_failed'],raw_body_saved=False)
        error=RuntimeError(f'DEEPSEEK_HTTP_{exc.code}')
        error.provider_response=dict(status_code=exc.code,body=None,server_error=server,
            failure_details=failure_details(exc, config, started, key))
        error.transport_state=state
        raise error from exc
    except (URLError, OSError) as exc:
        error=RuntimeError('DEEPSEEK_NETWORK_ERROR')
        error.provider_response=dict(failure_details=failure_details(exc, config, started, key))
        error.transport_state=state
        raise error from exc
    except Exception as exc:
        # Preserve reception facts on JSON/decode/read failures without saving raw body.
        error=RuntimeError('DEEPSEEK_RESPONSE_PROCESSING_FAILED')
        details=failure_details(exc, config, started, key)
        details['reason_message']=None  # Parser messages can echo response content.
        error.provider_response=dict(status_code=state['http_status'],failure_details=details)
        error.transport_state=state
        raise error from exc


