"""Loopback origin and optional per-launch token protection for HTTP and PTYs."""
import hmac
import os
from urllib.parse import urlparse

from starlette.responses import JSONResponse


def local_origin(value):
    try:
        parsed = urlparse(value)
        return parsed.scheme in ('http', 'https') and parsed.hostname in ('127.0.0.1', 'localhost', '[::1]', '::1')
    except ValueError:
        return False


class LocalSecurity:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] not in ('http', 'websocket'):
            return await self.app(scope, receive, send)
        headers = {k.decode().lower(): v.decode() for k, v in scope.get('headers', [])}
        host = headers.get('host', '')
        origin = headers.get('origin')
        permitted = local_origin('http://' + host) and (not origin or local_origin(origin) and urlparse(origin).netloc == host)
        expected = os.environ.get('K_CREATIVE_TOKEN', '')
        if expected:
            cookie = dict(part.strip().split('=', 1) for part in headers.get('cookie', '').split(';') if '=' in part)
            presented = headers.get('x-k-creative-token', cookie.get('k_creative_session', ''))
            permitted = permitted and hmac.compare_digest(presented, expected)
        if not permitted:
            if scope['type'] == 'websocket':
                return await send({'type': 'websocket.close', 'code': 1008})
            return await JSONResponse({'detail': 'Local session authorization required'}, status_code=403)(scope, receive, send)
        await self.app(scope, receive, send)
