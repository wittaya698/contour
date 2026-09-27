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
import secrets
import time
import urllib.parse
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from lib import anchor
from lib import panel as panel_state
from lib import marks as marks_store
from lib import mask as mask_store
from lib import refs as refs_store

PAGE = Path(__file__).resolve().parent / "canvas.html"
TOKEN_HEADER = "X-Contour-Token"
TOKEN_PARAM = "t"

MARKS_ONLY = ("marks",)
"""What a host with no console can do, which is what a bare clone can do.

The whole of the launcher's answer to `/can`. Named here rather than defaulted
inline so the containment is one readable line: anything a console adds is a
name this tuple does not hold (ADR 0019).
"""


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass                                  # the page is chatty; the report is not

    def _authorised(self):
        """Every request proves it belongs to this session, or gets nothing.

        Two ways in, because the page has two kinds of caller. A fetch sends
        the token as a header, which is what makes the request non-simple and
        so unreachable from another site without a preflight. An `<img src>`
        cannot set a header at all, so those carry it in the query — safe
        because an image GET changes nothing.
        """
        header = self.headers.get(TOKEN_HEADER)
        asked = urllib.parse.parse_qs(
            urllib.parse.urlparse(self.path).query).get(TOKEN_PARAM, [None])[0]
        wanted = self.server.canvas.token
        return any(got is not None and secrets.compare_digest(got, wanted)
                   for got in (header, asked))

    def _is_json(self):
        """A POST says JSON, or it never reaches a handler.

        A form or text POST is a *simple* request: another page can send one
        at this server with no preflight and no permission. Demanding a
        content type that only a preflighted request can set turns that whole
        class of request away at the door, before any body is read.
        """
        got = (self.headers.get("Content-Type") or "").split(";")[0].strip()
        return got.lower() == "application/json"

    def _same_origin(self):
        """A request that says where it came from says here, or gets nothing.

        The token alone is not the whole story: DNS rebinding hands another
        site this address, so a request can arrive at the right port while
        belonging to a page the user never opened. A browser attaches `Origin`
        to exactly the requests that matter, and cannot be talked out of it.
        Absent is not a failure — a non-browser caller sends none, and the
        token is what stands behind it there.
        """
        origin = self.headers.get("Origin")
        if origin is not None and origin != self.server.canvas.origin:
            return False
        # The browser's own account of where the request came from, which a
        # page cannot forge. `none` is the address bar, `same-origin` is this
        # page's own fetches; everything else is somebody else's page.
        site = self.headers.get("Sec-Fetch-Site")
        return site is None or site in ("none", "same-origin")

    def do_GET(self):
        if not self._authorised() or not self._same_origin():
            return self.send_error(403)
        self.server.canvas.touched()
        if self.path == "/" or self.path.startswith("/?"):
            return self._bytes(PAGE.read_bytes(), "text/html; charset=utf-8")
        if self.path.split("?")[0] == "/can":
            return self._json({"can": list(self.server.canvas.can)})
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
        if self.path.split("?")[0] == "/sheet.json":
            return self._json(panel_state.state(self.server.canvas.views,
                                                self.server.canvas.blend,
                                                self.server.canvas.verdict,
                                                self.server.canvas.marks))
        if self.path.split("?")[0] == "/parts.json":
            return self._json(self.server.canvas.parts_table())
        if self.path.split("?")[0] == "/sheet.png":
            # Absent is an answer: a space that has never built has no picture
            # yet, and a panel with nothing in it is the truth about it. Raising
            # here instead would put a traceback where a first run belongs.
            sheet = self.server.canvas.sheet
            return (self._bytes(sheet.read_bytes(), "image/png")
                    if sheet.exists() else self.send_error(404))
        return self._extra("GET", {k: v[0] for k, v in urllib.parse.parse_qs(
            urllib.parse.urlparse(self.path).query).items()})

    def do_POST(self):
        if not self._authorised() or not self._same_origin():
            return self.send_error(403)
        if not self._is_json():
            return self.send_error(415)
        if self.path != "/beat":
            self.server.canvas.touched()      # a beat is not somebody being here
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/marks":
            return self._json(self.server.canvas.record(body))
        if self.path == "/close":
            closed = self.server.canvas.close(body.get("id"))
            return self._json(closed) if closed else self.send_error(404)
        if self.path == "/beat":
            return self._json(self.server.canvas.beat())
        if self.path == "/done":
            self._json({"done": True})
            return self.server.canvas.finish()
        return self._extra("POST", body)

    def _extra(self, verb, payload):
        """Whatever this host added, or 404. Last, so a host cannot quietly
        replace `/marks` — the shared endpoints are the canvas's and mean the
        same thing under every host, which is the whole of decision 33."""
        handler = self.server.canvas.routes.get(
            (verb, urllib.parse.urlparse(self.path).path))
        if handler is None:
            return self.send_error(404)
        answer = handler(payload)
        return self._json(answer) if answer is not None else self.send_error(404)

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
                 refs=None, can=MARKS_ONLY, routes=None, views=None,
                 blend=None, verdict=None):
        self.sheet = Path(sheet)
        self.marks = Path(marks)
        self.mask = Path(mask) if mask else None
        self.parts = Path(parts) if parts else None
        self.resolve = resolve
        self.refs = Path(refs) if refs else None
        # What the sheet is a picture of: the cameras that drew it and the build
        # they drew. Both paths and not a fingerprint, because the build on disk
        # moves while the page is open and the label has to move with it.
        self.views = Path(views) if views else None
        self.blend = Path(blend) if blend else None
        # What the last build came to. A build that raised leaves the previous
        # `.blend` in place, so the fingerprints alone cannot tell a current
        # picture from one of a build that never finished.
        self.verdict = Path(verdict) if verdict else None
        # What this host can do, for the page to ask about. The caller's to
        # declare and not the Canvas's to infer: the console's extra surface
        # is the console's, and a Canvas that guessed would guess wrong for
        # every host added after this one.
        self.can = tuple(can)
        # What this host serves beyond the sheet and the marks, as
        # {(method, path): handler}. The console's run lives here rather than in
        # this file: the launcher is stdlib-only and knows nothing about agents,
        # and `canvas.html` outgrowing one file was to be answered by serving
        # the console's extra views *beside* it, never by bundling them in
        # (ADR 0019). A capability the host declares comes with the endpoints
        # that capability implies, and they arrive together.
        self.routes = dict(routes or {})
        self.token = secrets.token_urlsafe(32)
        self.last_beat = None                 # nothing has said it is watching
        self.last_touch = time.monotonic()    # opening the thing counts as use
        self.captured = []
        self.pruned = None
        self._lock = threading.Lock()         # two posts can land at once
        self._done = threading.Event()
        self._server = None
        self._thread = None
        self._addr = None

    @property
    def origin(self):
        """Where the server is. Stays readable after it stops, so the report
        can name it."""
        host, port = self._addr
        return f"http://{host}:{port}"

    @property
    def url(self):
        """What the browser is pointed at: the origin, carrying this session's
        token. The page reads it back out of its own location and sends it as a
        header from then on, so the secret stops appearing in request URLs."""
        return f"{self.origin}/?{TOKEN_PARAM}={self.token}"

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

    @property
    def done(self):
        """Has this session ended? Asked by a caller that owns the lifetime —
        the console watches for a silence and must stop watching when the
        session stops."""
        return self._done.is_set()

    def touched(self):
        """Somebody did something. Every request but a beat, because a beat is
        the page breathing and this is the clock an idle timeout reads."""
        self.last_touch = time.monotonic()

    def beat(self):
        """The page saying it is still on screen.

        Recorded and nothing more: a server that acted on this would decide the
        caller's lifetime for it, and the canvas's lifetime is the Done button
        (ADR 0018). The console reads the same beat and ends when it stops,
        because a page that went quiet is a tab that closed.
        """
        self.last_beat = time.monotonic()
        return {"beat": True}

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

        Here and not per click: a ray per click would pay a Blender startup per
        mouse press. And here rather than at a build, for this host, because
        this host has no build to hang it off: `contour canvas` shows a sheet and
        cannot know when the next build is coming, so Done is the last moment it
        knows about. A console can do better, and does — it owns the build, so it
        resolves the instant it approves one (ADR 0019, decisions 8 and 14).
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
          views=None, blend=None, verdict=None, open_browser=True):
    """One canvas session, start to report. Blocks until the page says done.

    The first Contour command that waits rather than shoots, so it is also the
    first that can be interrupted: Ctrl-C closes the port and keeps whatever
    marks already landed, because each one was written as it arrived.
    """
    sheet = Path(sheet)
    if not sheet.exists():
        return {"ok": False, "lines": [f"FAIL no sheet at {sheet} — run contour render first"]}
    # The label is the canvas's, not the console's: this page can show a sheet
    # the build has moved past just as easily, and resolution already refuses one
    # (ADR 0018). Said while the user is looking rather than when they press Done.
    canvas = Canvas(sheet, marks, mask, parts, resolve, refs,
                    views=views, blend=blend, verdict=verdict)
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
