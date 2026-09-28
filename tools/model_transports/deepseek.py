"""DeepSeek Chat Completions transport; no workbench or platform state."""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('DEEPSEEK_REDIRECT_REFUSED')


def request_completion(config, payload, key):
    url = config['base_url'].rstrip('/') + '/chat/completions'
    request = Request(url, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                      headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    try:
        with build_opener(NoRedirect).open(request, timeout=config['timeout_s']) as response:
            return json.loads(response.read().decode('utf-8'))
    except HTTPError as exc:
        # Preserve endpoint rejection evidence, never headers or credentials.
        body=exc.read().decode('utf-8',errors='replace').replace(key,'[REDACTED]')
        error=RuntimeError(f'DEEPSEEK_HTTP_{exc.code}')
        error.provider_response=dict(status_code=exc.code,body=body)
        raise error from None
    except URLError:
        raise RuntimeError('DEEPSEEK_NETWORK_ERROR') from None


