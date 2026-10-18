"""Local-only HTTP adapter. Never imports boto3 or loads AWS credentials."""
import argparse
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from backend.app import Application, MAX_BODY, response
from backend.storage import SQLiteStore


def make_server(port=8000, db_path='.local/links.sqlite3'):
    app = Application(SQLiteStore(db_path), f'http://127.0.0.1:{port}')

    class Handler(BaseHTTPRequestHandler):
        def dispatch(self):
            try:
                length = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                length = -1
            if length < 0 or length > MAX_BODY:
                result = response(413, {'error': 'Request body is too large or invalid.'})
            else:
                try:
                    body = self.rfile.read(length).decode('utf-8')
                except UnicodeError:
                    result = response(400, {'error': 'Use UTF-8 JSON.'})
                else:
                    result = app.handle({'version': '2.0', 'rawPath': urlsplit(self.path).path,
                                         'requestContext': {'http': {'method': self.command}},
                                         'headers': dict(self.headers), 'body': body, 'isBase64Encoded': False})
            data = result['body'].encode()
            self.send_response(result['statusCode'])
            for key, value in result['headers'].items():
                self.send_header(key, value)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(data)

        do_GET = do_POST = do_HEAD = do_PUT = do_DELETE = do_OPTIONS = dispatch

        def log_message(self, format, *args):
            pass  # Application logs omit URLs and request bodies.

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    app.base_url = f'http://127.0.0.1:{server.server_port}'
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--db', default='.local/links.sqlite3')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    server = make_server(args.port, args.db)
    print(f'Local app: http://127.0.0.1:{server.server_port} (SQLite; no AWS calls)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
