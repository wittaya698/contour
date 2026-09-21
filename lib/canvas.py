"""`contour canvas`: the sheet, in a browser, with somewhere to point (ADR 0018).

Runs launcher-side, never inside Blender. Serves one page and the sheet from
the standard library on localhost, takes marks from it, and stops when the page
says done — the first Contour command that waits rather than shoots.
"""
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from lib import marks as marks_store

PAGE = Path(__file__).resolve().parent / "canvas.html"


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass                                  # the page is chatty; the report is not

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            return self._bytes(PAGE.read_bytes(), "text/html; charset=utf-8")
        if self.path.split("?")[0] == "/sheet.png":
            return self._bytes(self.server.canvas.sheet.read_bytes(), "image/png")
        self.send_error(404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/marks":
            return self._json(self.server.canvas.record(body))
        if self.path == "/done":
            self._json({"done": True})
            return self.server.canvas.finish()
        self.send_error(404)

    def _json(self, payload):
        self._bytes(json.dumps(payload).encode(), "application/json")

    def _bytes(self, blob, content_type):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(blob)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(blob)


class Canvas:
    """One canvas session. `start` binds and serves; `stop` releases the port."""

    def __init__(self, sheet, marks):
        self.sheet = Path(sheet)
        self.marks = Path(marks)
        self.captured = []
        self._lock = threading.Lock()         # two posts can land at once
        self._done = threading.Event()
        self._server = None
        self._thread = None
        self._addr = None

    @property
    def url(self):
        """Stays readable after the server stops, so the report can name it."""
        host, port = self._addr
        return f"http://{host}:{port}"

    def start(self):
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self._server.canvas = self
        self._addr = self._server.server_address
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self.url

    def record(self, body):
        """Store one mark as it arrives, not at the end: an interrupted
        session then still leaves behind everything the user had said."""
        with self._lock:
            stored = marks_store.append(self.marks, {
                "view": body.get("view"),
                "pixel": body.get("pixel"),
                "text": body.get("text", "")})
            self.captured.append(stored)
        return stored

    def finish(self):
        """The page says it is done. The port closes from `wait`, on the
        caller's thread: shutting a server down from inside one of its own
        handlers deadlocks."""
        self._done.set()

    def wait(self):
        """Serve until the page says done, then stop and report."""
        self._done.wait()
        self.stop()
        n = len(self.captured)
        return {"ok": True, "lines": [
            f"ok   canvas  {marks_store.phrase(n)} captured" if n
            else "ok   canvas  no marks captured"]}

    def stop(self):
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)
        self._server = None


def serve(sheet, marks, open_browser=True):
    """One canvas session, start to report. Blocks until the page says done.

    The first Contour command that waits rather than shoots, so it is also the
    first that can be interrupted: Ctrl-C closes the port and keeps whatever
    marks already landed, because each one was written as it arrived.
    """
    sheet = Path(sheet)
    if not sheet.exists():
        return {"ok": False, "lines": [f"FAIL no sheet at {sheet} — run contour render first"]}
    canvas = Canvas(sheet, marks)
    url = canvas.start()
    print(f"canvas at {url}  —  click the sheet, then press Done", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        return canvas.wait()
    except KeyboardInterrupt:
        canvas.stop()
        return {"ok": True, "lines": [
            f"ok   canvas  interrupted, {marks_store.phrase(len(canvas.captured))} kept"]}
