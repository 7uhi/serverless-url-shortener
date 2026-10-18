import base64
import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from backend.app import Application, InputError, validate_url


def event(method, path, data=None, **extra):
    return {'version': '2.0', 'rawPath': path, 'requestContext': {'http': {'method': method}},
            'headers': {'content-type': 'application/json'}, 'body': json.dumps(data) if data is not None else '', **extra}


def create(app, url='https://example.com/a/long/path?hello=world'):
    result = app.handle(event('POST', '/api/links', {'url': url}))
    assert result['statusCode'] == 201
    return json.loads(result['body'])


def test_create_redirect_and_stats(app):
    item = create(app)
    assert len(item['code']) == 8
    assert item['visits'] == 0
    assert item['short_url'] == f"https://short.example.com/r/{item['code']}"
    redirect = app.handle(event('GET', '/r/' + item['code']))
    assert redirect['statusCode'] == 302
    assert redirect['headers']['Location'] == item['url']
    assert redirect['headers']['Cache-Control'] == 'no-store'
    for _ in range(2):
        stats = app.handle(event('GET', '/api/links/' + item['code']))
        assert json.loads(stats['body'])['visits'] == 1


@pytest.mark.parametrize('url', [
    '', None, 12, [], 'javascript:alert(1)', 'ftp://example.com/a', '//example.com',
    'https://user:password@example.com', 'http://localhost', 'http://localhost.local',
    'http://127.0.0.1', 'http://10.0.0.1', 'http://169.254.169.254/latest/meta-data',
    'http://[::1]', 'http://[fe80::1]', 'http://2130706433', 'http://0x7f000001',
    'http://127.1', 'https://example.com:3000', 'https://example.com:bad',
    'https://example.com/\r\nX-Injected:yes', 'https://example.com/%0d%0aevil',
    'https://example.com\\@127.0.0.1', 'https://example.com/a b',
    'https://short.example.com/r/abcdefgh', 'https://example.com/' + 'a' * 2048,
    'https://[broken', 'https://a.internal', 'https://a.invalid',
])
def test_unsafe_urls_rejected(app, url):
    assert app.handle(event('POST', '/api/links', {'url': url}))['statusCode'] == 400


@pytest.mark.parametrize('url', ['https://example.com', 'http://example.com:80/a', 'https://docs.aws.amazon.com/path?q=a%20b#section', 'https://8.8.8.8/', 'https://example.com/café'])
def test_valid_urls(url):
    assert validate_url(url).startswith(('http://', 'https://'))


def test_allowlist():
    assert validate_url('https://example.com/a', allowed_hosts=('example.com',))
    with pytest.raises(InputError):
        validate_url('https://other.example.com', allowed_hosts=('example.com',))


@pytest.mark.parametrize('body', ['{broken', 'null', '[]', '{"extra": 1}', '{"url":"https://example.com","extra":1}'])
def test_bad_json(app, body):
    assert app.handle(event('POST', '/api/links', body=body))['statusCode'] == 400


def test_body_limit_and_content_type(app):
    assert app.handle(event('POST', '/api/links', body='x' * 9000))['statusCode'] == 413
    assert app.handle(event('POST', '/api/links', headers={}))['statusCode'] == 415


def test_base64_body(app):
    body = base64.b64encode(json.dumps({'url': 'https://example.com'}).encode()).decode()
    assert app.handle(event('POST', '/api/links', body=body, isBase64Encoded=True))['statusCode'] == 201
    assert app.handle(event('POST', '/api/links', body='!invalid', isBase64Encoded=True))['statusCode'] == 400


def test_not_found_and_expiration(app, store):
    for path in ['/r/abcdefgh', '/r/invalid', '/api/links/abcdefgh', '/missing', '/../../app.py']:
        assert app.handle(event('GET', path))['statusCode'] == 404
    item = create(app)
    app.clock = lambda: item['expires_at']
    assert app.handle(event('GET', '/r/' + item['code']))['statusCode'] == 404
    assert app.handle(event('GET', '/api/links/' + item['code']))['statusCode'] == 404
    assert store.get(item['code'])['visits'] == 0


def test_head_does_not_count(app, store):
    item = create(app)
    assert app.handle(event('HEAD', '/r/' + item['code']))['statusCode'] == 302
    assert store.get(item['code'])['visits'] == 0


def test_collision_retry_and_exhaustion(app, store):
    app.code_factory = lambda: 'abcdefgh'
    first = create(app)
    codes = iter(['abcdefgh', 'abcd1234'])
    app.code_factory = lambda: next(codes)
    assert create(app)['code'] == 'abcd1234'
    app.code_factory = lambda: 'abcdefgh'
    assert app.handle(event('POST', '/api/links', {'url': 'https://different.com'}))['statusCode'] == 503
    assert store.get('abcdefgh')['url'] == first['url']


def test_minute_limit_and_reset(app):
    for _ in range(20):
        create(app)
    denied = app.handle(event('POST', '/api/links', {'url': 'https://example.com'}))
    assert denied['statusCode'] == 429
    assert 0 < int(denied['headers']['Retry-After']) <= 60
    app.clock = lambda: 1700000060
    create(app)


def test_daily_limit(app, store):
    now = int(app.clock())
    key = f'rate#86400#{now // 86400}'
    store.create({'pk': key, 'count': 500, 'expires_at': now + 86400})
    assert app.handle(event('POST', '/api/links', {'url': 'https://example.com'}))['statusCode'] == 429


def test_concurrent_visits(app, store):
    item = create(app)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: app.handle(event('GET', '/r/' + item['code'])), range(50)))
    assert all(r['statusCode'] == 302 for r in results)
    assert store.get(item['code'])['visits'] == 50


def test_concurrent_creation_limit(app):
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: app.handle(event('POST', '/api/links', {'url': 'https://example.com'})), range(30)))
    assert sum(r['statusCode'] == 201 for r in results) == 20
    assert sum(r['statusCode'] == 429 for r in results) == 10


def test_persistence(app, store):
    from backend.storage import SQLiteStore
    item = create(app)
    assert SQLiteStore(store.path).get(item['code'])['url'] == item['url']


def test_storage_failure_is_sanitized(app, monkeypatch, caplog):
    def broken(*args):
        raise RuntimeError('sensitive-destination-and-secret')
    monkeypatch.setattr(app.store, 'consume_limit', broken)
    result = app.handle(event('POST', '/api/links', {'url': 'https://example.com'}))
    assert result['statusCode'] == 503
    assert 'sensitive-destination-and-secret' not in result['body'] + caplog.text


@pytest.mark.parametrize('path,mime', [('/', 'text/html'), ('/app.js', 'text/javascript'), ('/styles.css', 'text/css')])
def test_frontend_assets(app, path, mime):
    result = app.handle(event('GET', path))
    assert result['statusCode'] == 200
    assert mime in result['headers']['Content-Type']
    assert result['body']
    assert "frame-ancestors 'none'" in result['headers']['Content-Security-Policy']
