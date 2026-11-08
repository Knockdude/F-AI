import json
import re
import secrets
import unicodedata
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


PROJECT_DIR = Path(__file__).resolve().parent
SESSIONS = {}
MAX_MESSAGE_LENGTH = 2000


def normalize(text):
    normalized = unicodedata.normalize("NFD", text.casefold())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def respond_to_message(message):
    normalized_message = normalize(message)

    if any(phrase in normalized_message for phrase in ("como has estado", "como haz estado", "como estas", "que tal estas")):
        return "Estoy bien, gracias por preguntar. ¿Qué te gustaría conversar? Recuerda que soy una IA y no soy Fabiola."

    if any(
        phrase in normalized_message
        for phrase in ("no estoy bien", "no me siento bien", "no me encuentro bien")
    ) or re.search(r"\b(mal|triste|ansioso|ansiosa|cansado|cansada|preocupado|preocupada)\b", normalized_message):
        return f"Siento que te sientas así. Me cuentas que «{message}». ¿Quieres hablar de qué pasó?"

    if re.search(r"\b(bien|feliz|contento|contenta|genial|emocionado|emocionada)\b", normalized_message):
        return f"Me alegra saberlo. Gracias por contarme: «{message}». ¿Qué fue lo mejor de eso?"

    if re.search(r"\b(gracias|agradezco)\b", normalized_message):
        return f"De nada, Mateo. Me alegra poder acompañarte. También me dijiste: «{message}»."

    if "?" in message or "¿" in message:
        return f"Sobre lo que preguntas —«{message}»—, puedo ayudarte a pensarlo. ¿Qué parte te interesa más?"

    return f"Entiendo, Mateo. Me cuentas que «{message}». ¿Qué es lo que más te gustaría explorar sobre eso?"


class WebHandler(BaseHTTPRequestHandler):
    def _session_id(self):
        cookies = SimpleCookie()
        cookies.load(self.headers.get("Cookie", ""))
        session_cookie = cookies.get("nexus_session")
        return session_cookie.value if session_cookie else None

    def _send_response(self, status, body, content_type, extra_headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self._send_response(status, body, "application/json; charset=utf-8")

    def do_GET(self):
        path = urlsplit(self.path).path
        files = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/style.css": ("style.css", "text/css; charset=utf-8"),
        }
        if path not in files:
            self._send_json(404, {"error": "No se encontró la página solicitada."})
            return

        filename, content_type = files[path]
        try:
            body = (PROJECT_DIR / filename).read_bytes()
        except OSError:
            self._send_json(500, {"error": f"No se pudo cargar {filename}."})
            return

        headers = {}
        if path == "/":
            session_id = self._session_id()
            if not session_id or session_id not in SESSIONS:
                session_id = secrets.token_urlsafe(24)
                SESSIONS[session_id] = False
            headers["Set-Cookie"] = f"nexus_session={session_id}; HttpOnly; SameSite=Lax; Path=/"

        self._send_response(200, body, content_type, headers)

    def do_POST(self):
        path = urlsplit(self.path).path
        if path not in ("/api/chat", "/api/reset"):
            self._send_json(404, {"error": "No se encontró el endpoint solicitado."})
            return

        session_id = self._session_id()
        if not session_id or session_id not in SESSIONS:
            self._send_json(403, {"error": "Sesión no válida. Recarga la página para continuar."})
            return

        if path == "/api/reset":
            SESSIONS[session_id] = False
            self._send_json(200, {"reply": "Dime tu nombre para comenzar."})
            return

        try:
            content_length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self._send_json(400, {"error": "La solicitud no tiene un tamaño válido."})
            return

        if content_length <= 0 or content_length > 16384:
            self._send_json(400, {"error": "El mensaje está vacío o es demasiado grande."})
            return

        try:
            data = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"error": "El contenido enviado no es JSON válido."})
            return

        if not isinstance(data, dict) or not isinstance(data.get("message"), str):
            self._send_json(400, {"error": "La solicitud debe incluir un mensaje de texto."})
            return

        message = data["message"].strip()
        if not message or len(message) > MAX_MESSAGE_LENGTH:
            self._send_json(400, {"error": "Escribe un mensaje de hasta 2000 caracteres."})
            return

        if not SESSIONS[session_id]:
            if normalize(message) == "mateo":
                SESSIONS[session_id] = True
                self._send_json(200, {"reply": "¡Hola, Mateo! :) ¿Cómo estás?"})
            else:
                self._send_json(200, {"reply": "Lo siento, esta conversación está configurada para Mateo."})
            return

        self._send_json(200, {"reply": respond_to_message(message)})


import os

def main():
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", 10000))

    server = ThreadingHTTPServer((host, port), WebHandler)

    print(f"Fabiola.AI está disponible en el puerto {port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server.server_close()
    print(f"Fabiola.AI está disponible en http://{address[0]}:{address[1]}")
    print("Presiona Ctrl+C para detener el servidor.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
