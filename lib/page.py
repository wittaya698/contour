"""A page served to one browser tab, and to nobody else (issue 01, slice 29).

What the canvas, the console and the lobby have in common, and the only place
issue 01's protections are written: a per-session secret, a bind to the
loopback address, an origin check, JSON-only POSTs under a size cap, and a
heartbeat. It knows nothing about sheets, marks or spaces. A host is a `Page`
that serves more — its own `routes()` — and a second copy of these checks for
a new host is the drift ADR 0019 served the canvas's own server to avoid.

The endpoints every page has, and which no host may replace:

    GET  /          the page itself
    GET  /can       what this host can do, for the page to ask about
    POST /beat      the tab saying it is still open, and whether it is hidden
    POST /going     the tab saying it is closing, as it closes
    POST /done      the page saying it is finished
"""
import json
import secrets
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from lib import taught

TOKEN_HEADER = "X-Contour-Token"
TOKEN_PARAM = "t"
POLL_S = 0.05
"""How often the serving loop looks up to see whether it was told to stop.
`shutdown` waits for that look, so this is how long every stop takes: the
default half second was a port still bound and a terminal not yet given back on
every Done, closed tab and signal (issue 95). Idle, it is twenty wake-ups a
second, which nothing notices."""

LOOK = Path(__file__).resolve().parent / "look.css"
"""The one stylesheet every page takes its look from (ADR 0025, decision 12)."""
SCRIPT = Path(__file__).resolve().parent / "teach.js"
"""What teaches a shown term on any page (issue 77)."""
LINKED = '<link rel="stylesheet" href="look.css">'
"""Where a page asks for it. Served in its place, inside the page, because a
`<link>` cannot carry this session's token and the stylesheet would otherwise
be the one request that proves nothing."""
TEACH = '<script src="teach.js"></script>'
"""Where a page asks for the shown terms' lines (issue 77), served in its
place for the same reason."""


class Blob(tuple):
    """An answer that is bytes of a given type rather than JSON: `Blob((bytes,
    content_type))`. A tuple, so a route can return one as plainly as a dict."""


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
        wanted = self.server.page.token
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
        if origin is not None and origin != self.server.page.origin:
            return False
        # The browser's own account of where the request came from, which a
        # page cannot forge. `none` is the address bar, `same-origin` is this
        # page's own fetches; everything else is somebody else's page.
        site = self.headers.get("Sec-Fetch-Site")
        return site is None or site in ("none", "same-origin")

    def do_GET(self):
        if not self._authorised() or not self._same_origin():
            return self.send_error(403)
        page = self.server.page
        page.touched()
        url = urllib.parse.urlparse(self.path)
        if url.path == "/":
            return self._bytes(page.body(), "text/html; charset=utf-8")
        if url.path == "/can":
            return self._json({"can": list(page.can)})
        if url.path == "/taught":
            return self._json({"closed": taught.closed()})
        return self._route("GET", url.path, {k: v[0] for k, v in
                                             urllib.parse.parse_qs(url.query).items()})

    def do_POST(self):
        if not self._authorised() or not self._same_origin():
            return self.send_error(403)
        if not self._is_json():
            return self.send_error(415)
        page = self.server.page
        if self.path != "/beat":
            page.touched()                    # a beat is not somebody being here
        n = int(self.headers.get("Content-Length") or 0)
        if n > page.max_body:
            # Asked of the length alone, so a body too large is never read.
            self.close_connection = True
            return self.send_error(413)
        body = json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/beat":
            return self._json(page.beat(hidden=bool(body.get("hidden"))))
        if self.path == "/going":
            return self._json(page.going())
        if self.path == "/taught":
            return self._json({"closed": taught.close(body.get("closed"))})
        if self.path == "/done":
            self._json({"done": True})
            return page.finish()
        return self._route("POST", self.path, body)

    def _route(self, verb, path, payload):
        """The host's content first, then whatever its caller added, or 404.

        After the shared endpoints, so a host cannot quietly replace `/done` —
        they mean the same thing under every host (ADR 0019, decision 23).
        """
        page = self.server.page
        handler = page.served().get((verb, path)) or page.routes.get((verb, path))
        if handler is None:
            return self.send_error(404)
        answer = handler(payload)
        if answer is None:
            return self.send_error(404)
        if isinstance(answer, Blob):
            return self._bytes(*answer)
        return self._json(answer)

    def _json(self, payload):
        self._bytes(json.dumps(payload).encode(), "application/json")

    def _bytes(self, blob, content_type):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(blob)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(blob)


class Page:
    """One session of one page. `start` binds and serves; `stop` releases the
    port.

    `html` is the page. `can` is what this host can do, the caller's to declare
    and not the page's to infer. `routes` is what a caller serves beyond the
    host's own content, as {(method, path): handler}. `grace`, when given, is
    how long a silence after the first beat may last before the session ends:
    a page that stopped beating is a tab that closed. None leaves the lifetime
    to whoever owns it. `hidden_grace` is the longer silence allowed a tab
    that said it is hidden, whose timers the browser may slow or stop
    (issue 39). `reload_grace` is how long after the tab says it is going a
    beat may still take that back: a reload says going, then beats again.
    """

    max_body = 4 * 2**20
    """The largest POST body a page reads; a host whose page sends files says
    how much more it takes."""

    def __init__(self, html, can=(), routes=None, grace=None, hidden_grace=None,
                 reload_grace=0):
        self.html = html
        self.can = tuple(can)
        self.routes = dict(routes or {})
        self.grace = grace
        self.hidden_grace = hidden_grace
        self.reload_grace = reload_grace
        self.hidden = False                   # the tab's last word on being seen
        self.gone = None                      # when the tab said it is closing
        self.ended = None                     # why it ended, for the last line
        self.token = secrets.token_urlsafe(32)
        self.last_beat = None                 # nothing has said it is watching
        self.last_touch = time.monotonic()    # opening the thing counts as use
        self._done = threading.Event()
        self._server = None
        self._thread = None
        self._addr = None

    def body(self):
        """The page as a browser gets it: its HTML with the one stylesheet in
        place of the link that asks for it."""
        html = self.html.read_text(encoding="utf-8")
        look = f'<style data-look>\n{LOOK.read_text(encoding="utf-8")}</style>'
        lines = json.dumps(taught.LINES).replace("</", "<\\/")
        teach = (f'<script data-teach>\nconst TAUGHT = {lines};\n'
                 f'{SCRIPT.read_text(encoding="utf-8")}</script>')
        return html.replace(LINKED, look, 1).replace(TEACH, teach, 1).encode()

    def served(self):
        """This host's own content, as {(method, path): handler}. A handler
        takes the query or the body and returns JSON, a `Blob`, or None for
        404."""
        return {}

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
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self._server.page = self
        self._addr = self._server.server_address
        self._thread = threading.Thread(target=self._server.serve_forever,
                                        args=(POLL_S,), daemon=True)
        self._thread.start()
        if self.grace is not None:
            threading.Thread(target=self._watch, daemon=True).start()
        return self.url

    def _watch(self):
        """End the session when the page stops beating. Only after a first
        beat: before one, nothing has opened the page yet, and ending then
        would make a slow browser look like a closed tab."""
        while not self.done:
            if self.closed(self.grace, self.hidden_grace):
                self.ended = "the page closed"
                return self.finish()
            time.sleep(min(0.25, self.grace / 4))

    def closed(self, grace, hidden_grace=None):
        """Has the tab closed? Yes once it said it is going, and no beat took
        that back within `reload_grace`; otherwise judged by its silence:
        `grace` for a tab on screen; `hidden_grace` for one that said it is hidden, because a
        browser slows or stops a background tab's timers and its silence is
        not a closed tab's. None for that leaves a hidden tab never closed by
        silence. Never before a first beat."""
        if self.gone is not None:
            return time.monotonic() - self.gone >= self.reload_grace
        beat = self.last_beat
        if beat is None:
            return False
        allowed = hidden_grace if self.hidden else grace
        return allowed is not None and time.monotonic() - beat > allowed

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

    def beat(self, hidden=False):
        """The page saying it is still open, and whether anybody can see it.
        Recorded; acted on only by a session given a `grace`, or by a caller
        asking `closed`."""
        self.last_beat = time.monotonic()
        self.hidden = hidden
        self.gone = None                      # a reload, and not a closed tab
        return {"beat": True}

    def going(self):
        """The tab saying it is closing — `pagehide`, sent so it outlives the
        page. Recorded, like a beat; acted on by whoever owns the lifetime."""
        self.gone = time.monotonic()
        return {"going": True}

    def finish(self):
        """The session is over. The port closes from `wait`, on the caller's
        thread: shutting a server down from inside one of its own handlers
        deadlocks."""
        self._done.set()

    def wait(self):
        """Serve until the session is over, then stop."""
        self._done.wait()
        self.stop()

    def stop(self):
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)
        self._server = None
