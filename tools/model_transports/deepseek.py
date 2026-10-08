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
    value = re.sub(r'(?i)([a-z][a-z0-9+.-]*://)[^/\s@]+@', r'\1[REDACTED]@', value)
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
    try:
        with build_opener(NoRedirect).open(request, timeout=config['timeout_s']) as response:
            state.update(stage='response_read', response_received=True,
                         http_status=getattr(response, 'status', None),
                         provider_request_id=response_identifiers(getattr(response, 'headers', None)))
            body = response.read()
            state['response_body_received']=True
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
            body=sanitize_provider_text(exc.read().decode('utf-8',errors='replace'), key)
            state['response_body_received']=True
        except Exception:body=None  # HTTP reception is known even when body reading fails.
        error=RuntimeError(f'DEEPSEEK_HTTP_{exc.code}')
        error.provider_response=dict(status_code=exc.code,body=body,
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


