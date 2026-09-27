# Python | keep_alive.py | threading + http.server | Render sleep fix

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"alive")

    # глушим логи сервера в консоль
    def log_message(self, format, *args):
        pass


def keep_alive(port: int = 8080) -> None:
    """Запускает HTTP-сервер в отдельном потоке. Render видит открытый порт — не засыпает."""
    server = HTTPServer(("0.0.0.0", port), PingHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
