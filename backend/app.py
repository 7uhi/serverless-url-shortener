"""HTTP API v2 handler. The Application class is shared by local and Lambda runtimes."""
import base64
import binascii
import ipaddress
import json
import logging
import os
import re
import secrets
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)
CODE = re.compile(r'^[A-Za-z0-9_-]{8}$')
MAX_BODY = 4096
STATIC = Path(__file__).parent / 'static'
SECURITY_HEADERS = {
    'Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'no-referrer',
    'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
}


class InputError(ValueError):
    pass


def validate_url(value, own_host='', allowed_hosts=()):
    if not isinstance(value, str) or not value or len(value.encode('utf-8')) > 2048:
        raise InputError('Enter a URL of at most 2,048 bytes.')
    decoded = unquote(value)
    if any(ord(c) <= 32 or ord(c) == 127 for c in value) or any(ord(c) < 32 or ord(c) == 127 for c in decoded) or '\\' in value:
        raise InputError('URLs cannot contain whitespace, control characters, or backslashes.')
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or '').lower().rstrip('.')
        port = parsed.port
    except ValueError as exc:
        raise InputError('Enter a valid URL.') from exc
    if parsed.scheme.lower() not in {'https', 'http'} or not host or parsed.username is not None or parsed.password is not None:
        raise InputError('Use an http:// or https:// URL without embedded credentials.')
    if port not in (None, 80, 443):
        raise InputError('Only standard web ports (80 and 443) are supported.')
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        # Reject ambiguous numeric forms browsers may reinterpret as IPv4.
        labels = host.split('.')
        if len(labels) < 2 or not re.fullmatch(r'[a-z]{2,63}', labels[-1]) or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label) for label in labels):
            raise InputError('Use a public, ASCII hostname (international names must use punycode).')
        if host.endswith(('.localhost', '.local', '.internal', '.home', '.lan', '.test', '.invalid')):
            raise InputError('Local or private destinations are not allowed.')
    else:
        if not address.is_global:
            raise InputError('Local or private destinations are not allowed.')
    if host == own_host:
        raise InputError('A short link cannot point back to this application.')
    if allowed_hosts and host not in allowed_hosts:
        raise InputError('This destination is not on the configured allowed-host list.')
    # Percent-encode non-ASCII path/query/fragment characters for a valid Location header.
    from urllib.parse import quote
    return urlunsplit((parsed.scheme.lower(), parsed.netloc, quote(parsed.path, safe="/%:@!$&'()*+,;=-._~"), quote(parsed.query, safe="%/:?@!$&'()*+,;=-._~"), quote(parsed.fragment, safe="%/:?@!$&'()*+,;=-._~")))


def response(status, data=None, headers=None):
    return {'statusCode': status, 'headers': {**SECURITY_HEADERS, 'Content-Type': 'application/json; charset=utf-8', **(headers or {})},
            'body': json.dumps(data) if data is not None else ''}


class Application:
    def __init__(self, store, base_url, clock=time.time, code_factory=lambda: secrets.token_urlsafe(6), allowed_hosts=()):
        self.store, self.base_url = store, base_url.rstrip('/')
        self.clock, self.code_factory = clock, code_factory
        self.allowed_hosts = allowed_hosts

    def handle(self, event):
        try:
            result = self.route(event)
        except InputError as exc:
            result = response(400, {'error': str(exc)})
        except Exception as exc:
            # Do not log request bodies, destination URLs, client IPs, or exception messages.
            LOG.error(json.dumps({'event': 'request_failed', 'error_type': type(exc).__name__}))
            result = response(503, {'error': 'Service temporarily unavailable. Please try again later.'})
        LOG.info(json.dumps({'event': 'request_complete', 'status': result['statusCode']}))
        return result

    def public(self, item):
        return {'code': item['pk'], 'short_url': f"{self.base_url}/r/{item['pk']}",
                'url': item['url'], 'visits': int(item['visits']),
                'created_at': int(item['created_at']), 'expires_at': int(item['expires_at'])}

    def route(self, event):
        method = event.get('requestContext', {}).get('http', {}).get('method', '')
        path = event.get('rawPath', '')
        now = int(self.clock())
        static_files = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'), '/styles.css': ('styles.css', 'text/css')}
        if path in static_files and method in {'GET', 'HEAD'}:
            filename, mime = static_files[path]
            result = response(200, headers={'Content-Type': f'{mime}; charset=utf-8'})
            result['body'] = (STATIC / filename).read_text() if method == 'GET' else ''
            return result
        if path == '/api/links' and method == 'POST':
            headers = {k.lower(): v for k, v in event.get('headers', {}).items()}
            if headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json':
                return response(415, {'error': 'Send Content-Type: application/json.'})
            body = event.get('body') or ''
            if len(body.encode()) > MAX_BODY * 2:
                return response(413, {'error': 'Request body is too large.'})
            try:
                raw = base64.b64decode(body, validate=True) if event.get('isBase64Encoded') else body.encode()
                if len(raw) > MAX_BODY:
                    return response(413, {'error': 'Request body is too large.'})
                data = json.loads(raw)
            except (ValueError, UnicodeError, binascii.Error) as exc:
                raise InputError('Send a valid JSON object with a url field.') from exc
            if not isinstance(data, dict) or set(data) != {'url'}:
                raise InputError('Send a JSON object containing only the url field.')
            url = validate_url(data['url'], urlsplit(self.base_url).hostname, self.allowed_hosts)
            # Shared, atomic limits work across all Lambda execution environments.
            for duration, maximum in ((60, 20), (86400, 500)):
                window = now // duration
                if not self.store.consume_limit(f'rate#{duration}#{window}', maximum, (window + 2) * duration, now):
                    retry = (window + 1) * duration - now
                    return response(429, {'error': 'Demo creation limit reached. Try again later.'}, {'Retry-After': str(retry)})
            for _ in range(5):
                code = self.code_factory()
                item = {'pk': code, 'url': url, 'visits': 0, 'created_at': now, 'expires_at': now + 30 * 86400}
                if self.store.create(item):
                    return response(201, self.public(item))
            return response(503, {'error': 'Could not allocate a short code. Please try again.'})
        if path.startswith('/r/') and method in {'GET', 'HEAD'}:
            code = path.removeprefix('/r/')
            if not CODE.fullmatch(code):
                return response(404, {'error': 'Link not found or expired.'})
            item = self.store.visit(code, now) if method == 'GET' else self.store.get(code)
            if not item or int(item['expires_at']) <= now:
                return response(404, {'error': 'Link not found or expired.'})
            return response(302, headers={'Location': item['url']})
        if path.startswith('/api/links/') and method == 'GET':
            code = path.removeprefix('/api/links/')
            item = self.store.get(code) if CODE.fullmatch(code) else None
            if not item or int(item['expires_at']) <= now:
                return response(404, {'error': 'Link not found or expired.'})
            return response(200, self.public(item))
        return response(404, {'error': 'Route not found.'})


_application = None


def lambda_handler(event, context):
    global _application
    if _application is None:
        started = time.monotonic()
        LOG.info(json.dumps({'event': 'sdk_initialization_started'}))
        import boto3
        from botocore.config import Config
        from storage import DynamoStore
        LOG.info(json.dumps({'event': 'sdk_imported', 'elapsed_ms': round((time.monotonic() - started) * 1000)}))
        # Do not automatically retry non-idempotent counters after ambiguous network failures.
        db = boto3.resource('dynamodb', config=Config(connect_timeout=2, read_timeout=3, retries={'total_max_attempts': 1, 'mode': 'standard'}))
        # API Gateway supplies this context; never build links from the client Host header.
        base_url = f"https://{event['requestContext']['domainName']}"
        _application = Application(DynamoStore(db.Table(os.environ['TABLE_NAME'])), base_url,
                                   allowed_hosts=tuple(h.strip().lower() for h in os.environ.get('ALLOWED_HOSTS', '').split(',') if h.strip()))
        LOG.info(json.dumps({'event': 'sdk_initialized', 'elapsed_ms': round((time.monotonic() - started) * 1000)}))
    return _application.handle(event)
