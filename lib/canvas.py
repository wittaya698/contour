"""`contour canvas`: the sheet, in a browser, with somewhere to point (ADR 0018).

Runs launcher-side, never inside Blender. Serves one page, the sheet and the
identity mask from the standard library on localhost, takes marks from it, and
stops when the page says done or its tab goes — the first Contour command that
waits rather than shoots.

The page keeps its own copy of the mask so hover costs no request, but what a
mark *records* is resolved here, from the mask on disk. Hover is a convenience;
the record is evidence, and it has one source.
"""
import json
import threading
import webbrowser
from pathlib import Path

from lib import panel as panel_state
from lib import marks as marks_store
from lib import mask as mask_store
from lib import refs as refs_store
from lib import signals
from lib import span
from lib.page import TOKEN_HEADER, TOKEN_PARAM, Blob, Page  # noqa: F401  (re-exported)

PAGE = Path(__file__).resolve().parent / "canvas.html"

GRACE_S = 10          # beats are seconds apart; this is several missed ones
HIDDEN_GRACE_S = 60 * 60   # a background tab's timers may stop; a quit browser
                           # is caught here
RELOAD_S = 5          # a reload says going, then beats again within this

MARKS_ONLY = ("marks",)
"""What a host with no console can do, which is what a bare clone can do.

The whole of the launcher's answer to `/can`. Named here rather than defaulted
inline so the containment is one readable line: anything a console adds is a
name this tuple does not hold (ADR 0019).
"""


class Canvas(Page):
    """One canvas session: a `Page` serving one space's sheet and marks
    (slice 29). `start` binds and serves; `stop` releases the port."""

    def __init__(self, sheet, marks, mask=None, parts=None, resolve=None,
                 refs=None, can=MARKS_ONLY, routes=None, views=None,
                 blend=None, verdict=None, name=None, grace=None,
                 hidden_grace=None, reload_grace=0):
        # What this host can do, for the page to ask about. The caller's to
        # declare and not the Canvas's to infer: the console's extra surface
        # is the console's, and a Canvas that guessed would guess wrong for
        # every host added after this one.
        # What this host serves beyond the sheet and the marks, as
        # {(method, path): handler}. The console's run lives here rather than in
        # this file: the launcher is stdlib-only and knows nothing about agents,
        # and `canvas.html` outgrowing one file was to be answered by serving
        # the console's extra views *beside* it, never by bundling them in
        # (ADR 0019). A capability the host declares comes with the endpoints
        # that capability implies, and they arrive together.
        # The graces are the launcher's: under a console the console owns the
        # page's lifetime, and gives none (issue 110).
        super().__init__(PAGE, can=can, routes=routes, grace=grace,
                         hidden_grace=hidden_grace, reload_grace=reload_grace)
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
        # The space's name, for the header every page carries: *Models ›
        # oak-chair* (ADR 0025, decision 12).
        self.name = name
        self.captured = []
        self.pruned = None
        self._lock = threading.Lock()         # two posts can land at once

    def served(self):
        """The sheet, the mask, the references and the marks: what the canvas
        page reads and writes, under every host that serves it."""
        return {("GET", "/marks"): lambda q: self.listing(),
                ("GET", "/mask.png"): lambda q: png(self.mask_bytes()),
                ("GET", "/ref"): lambda q: self.ref(q.get("name", "")),
                ("GET", "/refs.json"): lambda q: refs_store.listing(self.refs),
                ("GET", "/sheet.json"): lambda q: dict(panel_state.state(
                    self.views, self.blend, self.verdict, self.marks), model=self.name),
                ("GET", "/parts.json"): lambda q: self.parts_table(),
                # Absent is an answer: a space that has never built has no
                # picture yet, and a panel with nothing in it is the truth about
                # it. Raising here instead would put a traceback where a first
                # run belongs.
                ("GET", "/sheet.png"): lambda q: png(
                    self.sheet.read_bytes() if self.sheet.exists() else None),
                ("POST", "/marks"): self.record,
                ("POST", "/close"): lambda b: self.close(b.get("id")) or None,
                # The user's three answers to an agent span (ADR 0022,
                # decision 5). Here, so every host that serves the page has them.
                ("POST", "/adopt"): lambda b: self.answer(
                    marks_store.adopt, b.get("id")),
                ("POST", "/correct"): lambda b: self.answer(
                    self.corrected, b.get("id"), b.get("pixel"), b.get("to")),
                ("POST", "/reject"): lambda b: self.answer(
                    marks_store.reject, b.get("id"), b.get("why")),
                # The header's *Models* (ADR 0025, decision 12): the lobby, shown
                # if one is running and started if not — `contour lobby` decides
                # which, so the page and a terminal cannot disagree.
                ("POST", "/models"): lambda b: models()}

    def ref(self, name):
        """One of the user's photographs, or None when there is no such one."""
        got = refs_store.blob(self.refs, name)
        return Blob(got) if got else None

    def start(self):
        self.pruned = marks_store.prune(self.marks)   # before the page reads
        return super().start()

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
        with self._lock:
            if body.get("ref"):
                stored = marks_store.on_reference(self.marks, body["ref"], pixel,
                                                  text, to=body.get("to"))
            else:
                stored = marks_store.on_sheet(self.marks, body.get("view"), pixel,
                                              text, part=self.part_at(pixel))
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

    def answer(self, transition, *args):
        """The user's answer to an agent span: the mark as it now stands, or
        `{"refused": why}`. Only ever reached from the page, as `close` is."""
        with self._lock:
            said = transition(self.marks, *args)
        return said.get("mark") or said

    def corrected(self, marks, mark_id, a, b):
        """The user's correction: their ends, read afresh at the scale the
        agent's reading was taken at. The ends are the user's, so no image is
        read; the scale is the span's own, so no anchor is asked again."""
        found = span.marked(marks, mark_id) or {}
        if not (a and b and a != b):
            said = ""                       # refused by the record, with why
        elif "scale" not in found:
            said = span.unscaled(a, b, f"drawn before spans kept their scale: "
                                       f"contour measure --span {mark_id} reads "
                                       f"it in millimetres")
        else:
            said = span.reads(a, b, found["scale"])
        return marks_store.correct(marks, mark_id, a, b, said)

    def wait(self):
        """Serve until the page says done or its tab goes, then stop, anchor,
        and report. A closed tab is said as one, so whoever started the canvas
        never takes it for the user saying they were finished."""
        self._done.wait()
        self.stop()
        n = len(self.captured)
        if self.ended:
            return self.report(f"the tab closed, {marks_store.phrase(n)} kept",
                               self.anchor())
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
        resolves the instant it approves one (ADR 0019, decisions 10 and 14).
        """
        if not self.resolve or not marks_store.unresolved(marks_store.load(self.marks)):
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



def models():
    """Start `contour lobby`, which shows the running lobby or becomes it."""
    from lib import enter
    enter.page(Path.home(), "lobby")    # every space's page stands in none
    return {"lobby": True}


def png(blob):
    """Bytes as a PNG answer, or None for a 404 when there are none."""
    return Blob((blob, "image/png")) if blob else None



def serve(sheet, marks, mask=None, parts=None, resolve=None, refs=None,
          views=None, blend=None, verdict=None, name=None, open_browser=True,
          grace=GRACE_S, hidden_grace=HIDDEN_GRACE_S, reload_grace=RELOAD_S):
    """One canvas session, start to report. Blocks until the page says done,
    or its tab goes: a chat that opened it for the user told them of no Done to
    press, and each mark was written as it arrived (issue 110).

    The first Contour command that waits rather than shoots, so it is also the
    first that can be interrupted: Ctrl-C closes the port and keeps whatever
    marks already landed, because each one was written as it arrived. A
    terminated canvas or a closed terminal ends the same way, once the caller
    has had them raised (issue 30).
    """
    sheet = Path(sheet)
    if not sheet.exists():
        return {"ok": False, "lines": [f"FAIL no sheet at {sheet} — run contour render first"]}
    # The label is the canvas's, not the console's: this page can show a sheet
    # the build has moved past just as easily, and resolution already refuses one
    # (ADR 0018). Said while the user is looking rather than when they press Done.
    canvas = Canvas(sheet, marks, mask, parts, resolve, refs,
                    views=views, blend=blend, verdict=verdict, name=name,
                    grace=grace, hidden_grace=hidden_grace, reload_grace=reload_grace)
    url = canvas.start()
    print(f"canvas at {url}  —  click the sheet, then press Done", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        return canvas.wait()
    except (KeyboardInterrupt, signals.Arrived):
        canvas.stop()
        return canvas.report(
            f"interrupted, {marks_store.phrase(len(canvas.captured))} kept",
            canvas.anchor())
