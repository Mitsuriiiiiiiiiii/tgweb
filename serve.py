import http.server, socketserver, os

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'www'))


class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def log_message(self, *a):
        pass


socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(('127.0.0.1', 8080), H) as s:
    s.serve_forever()
