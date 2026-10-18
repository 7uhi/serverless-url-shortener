"""Exercise the real local HTTP adapter without following external destinations."""
import json
import threading
from http.client import HTTPConnection
from local_server import make_server


def test_real_http_round_trip(tmp_path):
    server = make_server(0, tmp_path / 'http.sqlite3')
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        client = HTTPConnection('127.0.0.1', server.server_port, timeout=5)
        client.request('GET', '/')
        result = client.getresponse()
        assert result.status == 200
        assert b'Small Link' in result.read()
        client.request('POST', '/api/links', json.dumps({'url': 'https://example.com/hello'}), {'Content-Type': 'application/json'})
        result = client.getresponse()
        assert result.status == 201
        item = json.loads(result.read())
        client.request('GET', '/r/' + item['code'])
        result = client.getresponse()
        assert result.status == 302
        assert result.getheader('Location') == 'https://example.com/hello'
        result.read()
        client.request('GET', '/api/links/' + item['code'])
        result = client.getresponse()
        assert json.loads(result.read())['visits'] == 1
        client.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
