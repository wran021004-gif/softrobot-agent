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


def request_completion(config, payload, key):
    url = config['base_url'].rstrip('/') + '/chat/completions'
    request = Request(url, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                      headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    started = time.monotonic()
    try:
        with build_opener(NoRedirect).open(request, timeout=config['timeout_s']) as response:
            return json.loads(response.read().decode('utf-8'))
    except HTTPError as exc:
        # Preserve endpoint rejection evidence, never headers or credentials.
        body=sanitize_provider_text(exc.read().decode('utf-8',errors='replace'), key)
        error=RuntimeError(f'DEEPSEEK_HTTP_{exc.code}')
        error.provider_response=dict(status_code=exc.code,body=body,
            failure_details=failure_details(exc, config, started, key))
        raise error from None
    except (URLError, OSError) as exc:
        error=RuntimeError('DEEPSEEK_NETWORK_ERROR')
        error.provider_response=dict(failure_details=failure_details(exc, config, started, key))
        raise error from None


