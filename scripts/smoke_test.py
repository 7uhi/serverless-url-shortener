"""Verify a deployed app. Creates ONE expiring demo link; never deletes data."""
import argparse
import json
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base_url', help='Application URL from CloudFormation outputs')
    args = parser.parse_args()
    base = args.base_url.rstrip('/')
    if urlsplit(base).scheme != 'https':
        parser.error('Use the HTTPS application URL.')
    opener = build_opener(NoRedirect)

    def request(path, method='GET', data=None):
        body = json.dumps(data).encode() if data is not None else None
        req = Request(base + path, data=body, method=method,
                      headers={'Content-Type': 'application/json'} if body else {})
        try:
            result = opener.open(req, timeout=30)
        except HTTPError as error:
            result = error
        with result:
            return result.code, result.headers, result.read()

    for path, expected_type in [('/', 'text/html'), ('/styles.css', 'text/css'), ('/app.js', 'text/javascript')]:
        status, headers, body = request(path)
        assert status == 200 and body and expected_type in headers['Content-Type'], (path, status)
    destination = 'https://docs.aws.amazon.com/lambda/latest/dg/welcome.html'
    status, _, body = request('/api/links', 'POST', {'url': destination})
    assert status == 201, (status, body)
    link = json.loads(body)
    assert link['visits'] == 0 and link['short_url'] == base + '/r/' + link['code']
    status, headers, _ = request('/r/' + link['code'])
    assert status == 302 and headers['Location'] == destination
    assert headers['Cache-Control'] == 'no-store'
    status, _, body = request('/api/links/' + link['code'])
    assert status == 200 and json.loads(body)['visits'] == 1
    status, _, _ = request('/r/' + link['code'], 'HEAD')
    assert status == 302
    status, _, body = request('/api/links/' + link['code'])
    assert status == 200 and json.loads(body)['visits'] == 1
    status, _, _ = request('/api/links', 'POST', {'url': 'http://127.0.0.1/private'})
    assert status == 400
    status, _, _ = request('/r/invalid')
    assert status == 404
    print(json.dumps({'result': 'PASS', 'short_url': link['short_url'], 'visits': 1,
                      'checks': ['frontend assets', 'create', 'redirect', 'statistics', 'HEAD does not count',
                                 'private URL rejected', 'unknown link rejected']}, indent=2))


if __name__ == '__main__':
    main()
