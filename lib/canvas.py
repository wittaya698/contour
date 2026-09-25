"""`contour canvas`: the sheet, in a browser, with somewhere to point (ADR 0018).

Runs launcher-side, never inside Blender. Serves one page, the sheet and the
identity mask from the standard library on localhost, takes marks from it, and
stops when the page says done — the first Contour command that waits rather
than shoots.

The page keeps its own copy of the mask so hover costs no request, but what a
mark *records* is resolved here, from the mask on disk. Hover is a convenience;
the record is evidence, and it has one source.
"""
import json
import urllib.parse
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from lib import anchor
from lib import marks as marks_store
from lib import mask as mask_store
from lib import refs as refs_store

PAGE = Path(__file__).resolve().parent / "canvas.html"


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass                                  # the page is chatty; the report is not

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            return self._bytes(PAGE.read_bytes(), "text/html; charset=utf-8")
        if self.path.split("?")[0] == "/marks":
            return self._json(self.server.canvas.listing())
        if self.path.split("?")[0] == "/mask.png":
            blob = self.server.canvas.mask_bytes()
            return self._bytes(blob, "image/png") if blob else self.send_error(404)
        if self.path.split("?")[0] == "/ref":
            asked = urllib.parse.parse_qs(
                urllib.parse.urlparse(self.path).query).get("name", [""])[0]
            got = refs_store.blob(self.server.canvas.refs, asked)
            return self._bytes(*got) if got else self.send_error(404)
        if self.path.split("?")[0] == "/refs.json":
            return self._json(refs_store.listing(self.server.canvas.refs))
        if self.path.split("?")[0] == "/parts.json":
            return self._json(self.server.canvas.parts_table())
        if self.path.split("?")[0] == "/sheet.png":
            return self._bytes(self.server.canvas.sheet.read_bytes(), "image/png")
        self.send_error(404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/marks":
            return self._json(self.server.canvas.record(body))
        if self.path == "/close":
            closed = self.server.canvas.close(body.get("id"))
            return self._json(closed) if closed else self.send_error(404)
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

    def __init__(self, sheet, marks, mask=None, parts=None, resolve=None,
                 refs=None):
        self.sheet = Path(sheet)
        self.marks = Path(marks)
        self.mask = Path(mask) if mask else None
        self.parts = Path(parts) if parts else None
        self.resolve = resolve
        self.refs = Path(refs) if refs else None
        self.captured = []
        self.pruned = None
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
        self.pruned = marks_store.prune(self.marks)   # before the page reads
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self._server.canvas = self
        self._addr = self._server.server_address
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self.url

    def record(self, body):
        """Store one mark as it arrives, not at the end: an interrupted
        session then still leaves behind everything the user had said.

        Two kinds land here. A **sheet mark** names one of our four views, and
        the mask is asked what part its pixel fell on. A **ref mark** names one
        of the user's photographs, which knows nothing about parts and was not
        drawn by any view of ours, so it carries the image and the pixel alone
        (ADR 0018).
        """
        pixel, text = body.get("pixel"), body.get("text", "")
        if body.get("ref"):
            mark = {"ref": body["ref"], "pixel": pixel, "text": text}
            if body.get("to"):
                mark = {**mark, "to": body["to"]}
        else:
            mark = {"view": body.get("view"), "pixel": pixel, "text": text}
            part = self.part_at(pixel)
            if part:
                mark["part"] = part
        with self._lock:
            stored = marks_store.append(self.marks, mark)
            self.captured.append(stored)
        return stored

    def part_at(self, pixel):
        """What the mask says is at this pixel. The page's own answer is never
        taken on trust: hover is a convenience, the record is evidence."""
        if not (self.mask and self.parts and pixel):
            return None
        return mask_store.part_at(self.mask, self.parts, pixel[0], pixel[1])

    def mask_bytes(self):
        """The mask itself, for the page's local copy. None when the space was
        rendered before masks existed — the page then simply does not hover."""
        return self.mask.read_bytes() if self.mask and self.mask.exists() else None

    def parts_table(self):
        """index -> part name, `{}` when there is no mask to index into."""
        return (json.loads(self.parts.read_text())
                if self.parts and self.parts.exists() else {})

    def listing(self):
        """Every mark on file, not just this session's: a mark outlives the
        session that made it, and the page has to show one before it can
        close it."""
        with self._lock:
            return marks_store.load(self.marks)

    def close(self, mark_id):
        """Close one mark. Only ever reached from the page: nothing else in
        the pipeline may move a mark to closed (ADR 0018)."""
        with self._lock:
            return marks_store.close(self.marks, mark_id)

    def finish(self):
        """The page says it is done. The port closes from `wait`, on the
        caller's thread: shutting a server down from inside one of its own
        handlers deadlocks."""
        self._done.set()

    def wait(self):
        """Serve until the page says done, then stop, anchor, and report."""
        self._done.wait()
        self.stop()
        n = len(self.captured)
        return self.report(f"{marks_store.phrase(n)} captured" if n
                           else "no marks captured", self.anchor())

    def anchor(self):
        """Turn this session's pixels into places on parts — one Blender run,
        at the end, and only if there is something to ask it (ADR 0018).

        Here and not per click: a ray per click would pay a Blender startup
        per mouse press, and a ray per build would be cast against geometry
        the user never looked at.
        """
        if not self.resolve or not anchor.unresolved(marks_store.load(self.marks)):
            return []
        return self.resolve().get("lines", [])

    def report(self, headline, extra=()):
        """The session in a few lines at most. Pruning gets its own, because
        it deleted from a tracked file and should not do that quietly, and so
        does anchoring, which rewrote every mark it could place."""
        lines = [f"ok   canvas  {headline}"]
        if self.pruned:
            lines.append(f"ok   canvas  {self.pruned}")
        return {"ok": True, "lines": lines + list(extra)}

    def stop(self):
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)
        self._server = None


def serve(sheet, marks, mask=None, parts=None, resolve=None, refs=None,
          open_browser=True):
    """One canvas session, start to report. Blocks until the page says done.

    The first Contour command that waits rather than shoots, so it is also the
    first that can be interrupted: Ctrl-C closes the port and keeps whatever
    marks already landed, because each one was written as it arrived.
    """
    sheet = Path(sheet)
    if not sheet.exists():
        return {"ok": False, "lines": [f"FAIL no sheet at {sheet} — run contour render first"]}
    canvas = Canvas(sheet, marks, mask, parts, resolve, refs)
    url = canvas.start()
    print(f"canvas at {url}  —  click the sheet, then press Done", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        return canvas.wait()
    except KeyboardInterrupt:
        canvas.stop()
        return canvas.report(
            f"interrupted, {marks_store.phrase(len(canvas.captured))} kept",
            canvas.anchor())
