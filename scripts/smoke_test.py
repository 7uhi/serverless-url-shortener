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
    parser.add_argument('--expected-short-url-base', help='API canonical URL when testing through a proxy')
    parser.add_argument('--head-counts-as-get', action='store_true', help='Verify Netlify proxy behavior: HEAD is forwarded as GET')
    args = parser.parse_args()
    base = args.base_url.rstrip('/')
    canonical = (args.expected_short_url_base or base).rstrip('/')
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

    for path, expected_types in [('/', ('text/html',)), ('/styles.css', ('text/css',)),
                                 ('/app.js', ('text/javascript', 'application/javascript'))]:
        status, headers, body = request(path)
        assert status == 200 and body and any(mime in headers['Content-Type'] for mime in expected_types), (path, status)
    destination = 'https://docs.aws.amazon.com/lambda/latest/dg/welcome.html'
    status, _, body = request('/api/links', 'POST', {'url': destination})
    assert status == 201, (status, body)
    link = json.loads(body)
    assert link['visits'] == 0 and link['short_url'] == canonical + '/r/' + link['code']
    status, headers, _ = request('/r/' + link['code'])
    assert status == 302 and headers['Location'] == destination
    assert headers['Cache-Control'] == 'no-store'
    status, _, body = request('/api/links/' + link['code'])
    assert status == 200 and json.loads(body)['visits'] == 1
    status, headers, _ = request('/r/' + link['code'])
    assert status == 302 and headers['Location'] == destination
    status, _, body = request('/api/links/' + link['code'])
    assert status == 200 and json.loads(body)['visits'] == 2
    status, _, _ = request('/r/' + link['code'], 'HEAD')
    assert status == 302
    status, _, body = request('/api/links/' + link['code'])
    final_visits = 3 if args.head_counts_as_get else 2
    assert status == 200 and json.loads(body)['visits'] == final_visits, (status, body)
    status, _, _ = request('/api/links', 'POST', {'url': 'http://127.0.0.1/private'})
    assert status == 400
    status, _, _ = request('/r/invalid')
    assert status == 404
    print(json.dumps({'result': 'PASS', 'short_url': base + '/r/' + link['code'], 'visits': final_visits,
                      'checks': ['frontend assets', 'create', 'redirect', 'statistics',
                                 'HEAD counts as GET through proxy' if args.head_counts_as_get else 'HEAD does not count',
                                 'repeated redirect not cached', 'private URL rejected', 'unknown link rejected']}, indent=2))


if __name__ == '__main__':
    main()
