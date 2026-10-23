import http.server, socketserver, os

here = os.path.dirname(os.path.abspath(__file__))
www = os.path.join(here, 'www')
os.chdir(www if os.path.isdir(www) else here)


class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def log_message(self, *a):
        pass


class S(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


with S(('127.0.0.1', 8080), H) as s:
    s.serve_forever()
