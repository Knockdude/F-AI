import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


PROJECT_DIR = Path(__file__).resolve().parent


class WebHandler(BaseHTTPRequestHandler):
    def _send_response(self, status, body, content_type, extra_headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        files = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/style.css": ("style.css", "text/css; charset=utf-8"),
        }
        if path not in files:
            self._send_response(404, b"No se encontro la pagina solicitada.", "text/plain; charset=utf-8")
            return

        filename, content_type = files[path]
        try:
            body = (PROJECT_DIR / filename).read_bytes()
        except OSError:
            self._send_response(500, f"No se pudo cargar {filename}.".encode("utf-8"), "text/plain; charset=utf-8")
            return

        self._send_response(200, body, content_type)


def main():
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", 10000))

    server = ThreadingHTTPServer((host, port), WebHandler)

    print(f"Fabiola.AI está disponible en http://localhost:{port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
