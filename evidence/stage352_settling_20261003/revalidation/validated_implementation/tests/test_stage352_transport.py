"""Focused mocked transport diagnostics; no provider requests or numerical work."""
import errno
import io
import json
import socket
import ssl
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from tools.model_transports.deepseek import request_completion


class TransportDetailsTests(unittest.TestCase):
    def test_failure_details_and_sanitization(self):
        key = 'test-secret-352'
        config = dict(base_url='https://api.deepseek.com', timeout_s=1)
        cases = [(URLError(socket.gaierror(-2, 'DNS lookup failed')), 'dns'),
                 (URLError(TimeoutError('timed out')), 'timeout'),
                 (TimeoutError('direct timeout'), 'timeout'),
                 (URLError(ConnectionRefusedError(errno.ECONNREFUSED, 'refused')), 'connection'),
                 (URLError(ssl.SSLError('certificate error')), 'tls'),
                 (URLError('Tunnel connection failed: https://alice:secret@proxy.invalid'), 'proxy'),
                 (URLError('unclassified '+key+' https://alice:secret@proxy.invalid token=hidden'), 'unknown'),
                 (HTTPError(config['base_url'], 401, 'Rejected', {}, io.BytesIO(
                     ('Authorization: Bearer '+key+'\nhttps://alice:secret@proxy.invalid token=hidden').encode())), 'http')]
        for exc, category in cases:
            with self.subTest(category=category), patch('tools.model_transports.deepseek.build_opener') as opener:
                opener.return_value.open.side_effect = exc
                with self.assertRaises(RuntimeError) as raised:
                    request_completion(config, dict(messages=[]), key)
                error = raised.exception
                self.assertEqual(str(error), 'DEEPSEEK_HTTP_401' if category == 'http' else 'DEEPSEEK_NETWORK_ERROR')
                detail = error.provider_response['failure_details']
                self.assertEqual(detail['exception_type'], type(exc).__name__)
                self.assertEqual(detail['category'], category)
                self.assertEqual(detail['endpoint_hostname'], 'api.deepseek.com')
                self.assertGreaterEqual(detail['elapsed_s'], 0)
                encoded = json.dumps(error.provider_response)
                for secret in (key, 'alice', 'secret@', 'hidden'):
                    self.assertNotIn(secret, encoded)
                if category == 'connection':self.assertEqual(detail['os_error_number'], errno.ECONNREFUSED)
                if category == 'http':self.assertEqual(error.provider_response['status_code'], 401)
                opener.return_value.open.assert_called_once()
