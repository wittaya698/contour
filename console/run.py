"""One run: prose in, a driven agent, every call gated (ADR 0019, decisions 1,
3, 13, 17, 20).

The console's half of the run and not the SDK's. Everything here is standard
library, which is what makes the gate, the wait and the lock provable on a clone
with nothing installed; the one file that imports `claude-agent-sdk` is
`agent.py` beside this, and it is reached through `driver` below.
"""
import importlib.util
import os
import secrets
import threading
import time
from pathlib import Path

from console import approvals, last_run, launcher, seed, spend, vetoes
from lib import (activity, form, gate as gate_words, intent, lock, locked, marks, policy,
                 prose, survey, topics, worksheet)
from lib.last_run import ENDED



class Stopped(Exception):
    """The user ended the run while the agent was still working.

    Raised out of the two callbacks a driver holds, so that a driver which has
    not noticed unwinds at the next thing it tries to do rather than needing to
    be asked whether it should still be running. A thread cannot be killed, and
    a run whose ending depended on the agent agreeing to stop would not be an
    ending.
    """


HERE = Path(__file__).resolve().parent
DEFAULT = f"{HERE / 'agent.py'}:drive"

PASSING = ("act", "form")
RELAY_S = 0.25
"""How often a form waiting looks for what a chat filled in it."""
"""What the run record says only while the state that set it lasts."""

QUESTION = "AskUserQuestion"
"""The harness's own question tool, refused under a console: its fields hold no
suggestion with a basis, and the page could show no form (ADR 0034, decision
1)."""

SPEC_TOOL = "mcp__contour__spec_write"
"""The console's own spec write, which carries its case: three runs argued
theirs only in their thinking, where no gate or person reads it (ADR 0029)."""

TOPICS_TOOL = "mcp__contour__topics_propose"
"""The console's topic proposal: words for the person to keep or strike one by
one (ADR 0030, decision 2)."""

SPANS = "spans"
"""A run waiting on the person's answers to its by-eye spans (ADR 0035)."""

SPANS_ACT = "Claude has questions about your pictures"
"""What that wait is, in the words the canvas's card says them."""

ANSWERED = {"adopted": "adopted", "corrected": "moved", "rejected": "rejected"}
"""A span's answer, as the transcript says it once the park ends."""

ASK_TOOL = "mcp__contour__ask"
"""The console's question: each with a suggested answer and its basis, shown
to the person as a form already filled (ADR 0034, decision 1)."""

TOPICS = topics.CATEGORY

MADE_WITH = "made with spec_write: the whole new spec.yaml as its content"
"""How a refused spec write is told to make it, in the tool's own words."""

THE_CASE = ("your case for it as its case, naming each number it sets, and the "
            "span if you measured one")
"""What a refused spec write is told its case is: an argument, since what was
said before it never reached anyone (ADR 0029)."""



def driver(spec=None):
    """The thing that drives one agent session: `<file>:<name>`.

    `$CONTOUR_CONSOLE_AGENT` replaces it, the way `$BLENDER` replaces the
    interpreter the launcher runs and `$CONTOUR_CONSOLE_PYTHON` the one the
    console runs under — a path, because that is the shape of every other hatch
    in this toolkit. A test that drove the real SDK would spend money and need a
    network to prove something that is about neither.
    """
    where, _, name = (spec or os.environ.get("CONTOUR_CONSOLE_AGENT")
                      or DEFAULT).rpartition(":")
    loaded = importlib.util.spec_from_file_location("contour_console_agent", where)
    module = importlib.util.module_from_spec(loaded)
    loaded.loader.exec_module(module)
    return getattr(module, name)


def options(space, record):
    """What the agent is told about where it is working, and nothing else.

    Deliberately no prompt of our own: the driver is pointed at the space and
    discovers what Claude Code discovers there — the space's own rules, its
    settings, its skills. Writing them out here would yield an agent following
    whichever of the eight rules this file's author remembered, in a second place
    that drifts (ADR 0019, decision 19).

    Two things about the environment, both of which the agent needs in order for
    the toolkit's own mechanisms to work on it rather than around it:

    - the toolkit is on `PATH`, so the space's settings resolve `contour` and its
      guard is the installed one. Without this the hook that denies a reference
      write would simply fail to run, and rule 1 would stop being enforced at
      exactly the layer that drives the agent.
    - `$CONTOUR_RUN` names this run, so the agent's own builds join the hold this
      run already has instead of being refused by it (slice 02).

    And `setting_sources`, which is the discovery itself: the default is to read
    nothing off the filesystem, and a driver given that would discover none of
    the space's configuration and none of its skills. All three are named because
    all three are what Claude Code itself reads, and the point of discovering
    rather than declaring is that this layer adds nothing and subtracts nothing.
    The key is spelled the way the SDK spells it so the driver has nothing left
    to decide — but it is decided *here*, where it can be checked on a clone with
    no SDK installed.
    """
    toolkit = str(HERE.parent)
    return {"cwd": str(space),
            "setting_sources": ["user", "project", "local"],
            "env": dict(os.environ,
                        PATH=os.pathsep.join([toolkit, os.environ.get("PATH", "")]),
                        CONTOUR_RUN=record["run"])}


SPEC_WRITER = {
    "name": "spec_write",
    "description": ("Change this model's spec: the whole new spec.yaml as content, "
                    "revision bumped, and your case for the change as case. The "
                    "case is the only place the person reads your case: what you "
                    "think is not shown to them, and they answer this write with "
                    "its diff and its case in front of them. Name each number it "
                    "sets, why, and the span if you measured one."),
    "schema": {"type": "object", "required": ["content", "case"],
               "properties": {"content": {"type": "string"},
                              "case": {"type": "string"}}},
}
"""The console's spec write, as the driver hands it to the agent: the one way
a spec changes under a console, so that its case cannot be left in thinking
(ADR 0029). `console/agent.py` puts it in the SDK's shape and nothing more."""


ASKER = {
    "name": "ask",
    "description": ("Ask the person questions: each with your suggested answer "
                    "and its basis, what the suggestion rests on. The page shows "
                    "them as a form already filled with your suggestions, each "
                    "labelled as your guess, and the person edits what is wrong "
                    "and approves the form once; you are given the answers, each "
                    "with where it came from. Ask every question here, together, "
                    "and never in your closing or in prose. Mark is_size on the "
                    "one question, if any, whose answer is the model's real size."),
    "schema": {"type": "object", "required": ["questions"],
               "properties": {"questions": {"type": "array", "items": {
                   "type": "object", "required": ["question", "suggested", "basis"],
                   "properties": {"question": {"type": "string"},
                                  "suggested": {"type": "string"},
                                  "basis": {"type": "string"},
                                  "is_size": {"type": "boolean"}}}}}},
}
"""The console's question, as the driver hands it to the agent: the one way an
agent asks under a console, so that every question arrives as a field with a
guess and its basis (ADR 0034, decision 1)."""


def asked(payload):
    """What the agent is told once the person has approved its form: each
    answer and where it came from. The console kept them already."""
    return form.told(payload.get("answers") or [])


def topics_proposer(vocabulary):
    """The console's topic proposal, as the driver hands it to the agent: the
    one way an agent labels a model under a console (ADR 0030, decision 2).
    It carries every word in use and the names carrying it, and nothing else
    of another model, so a word that fits is reused (ADR 0030, decisions 3, 8)."""
    in_use = "; ".join(f"{w} ({', '.join(names)})" for w, names in vocabulary.items())
    return {
        "name": "topics_propose",
        "description": (
            "Suggest topics for this model: free words to find this model "
            "by, such as creature or low-poly, as words, and why as case. "
            "The person keeps or strikes each word. "
            "A topic labels the model and nothing else: it decides "
            "nothing about the build and argues for no spec change. "
            + (f"Words in use: {in_use}. Reuse one wherever it fits; a word "
               f"no model carries is shown to the person as new."
               if in_use else "No model carries a topic yet: every word is new.")),
        "schema": {"type": "object", "required": ["words", "case"],
                   "properties": {"words": {"type": "array", "items": {"type": "string"}},
                                  "case": {"type": "string"}}},
    }


def topics_shown(space, payload):
    """A proposal as the person is shown it, copied as the gate keeps one: the
    words they have not already struck for this model, and which of those no
    model carries yet, so growing the vocabulary is a choice the user sees
    being made (ADR 0030, decision 3)."""
    words, before = topics.offered(space, payload.get("words") or [])
    in_use = survey.vocabulary()
    return {**payload, "words": words, "struck_before": before,
            "new": [w for w in words if w not in in_use]}


def topics_proposed(answer):
    """What the agent is told once the person has answered its proposal: the
    words kept, the words struck, and any held back because they were struck
    before. The console wrote them already; this only says so."""
    lines = [f"kept: {', '.join(answer.get('kept') or []) or 'none'}",
             f"struck: {', '.join(answer.get('struck') or []) or 'none'}"]
    if answer.get("struck_before"):
        lines.append(f"not offered, struck for this model before: "
                     f"{', '.join(answer['struck_before'])}")
    return "\n".join(lines)


def spec_written(space, payload):
    """What an allowed `spec_write` does: write the spec as the gate showed it,
    and say so to the agent. The gate has already answered; the guard has
    nothing to say to it, as it is never a reference."""
    (Path(space) / "spec.yaml").write_text(payload.get("content") or "", encoding="utf-8")
    return "spec.yaml written"


def spec_edit(space, content):
    """A `spec_write` as the call the gate, the approvals and the guard read:
    an `Edit` of the whole spec as it reads now, so one answered after the spec
    moved no longer applies rather than undoing what moved it (ADR 0029). A
    `Write` where there is no spec yet, as there is nothing it could undo."""
    spec = Path(space) / "spec.yaml"
    was = spec.read_text(encoding="utf-8") if spec.is_file() else ""
    if not was:
        return "Write", {"file_path": str(spec), "content": content}
    return "Edit", {"file_path": str(spec), "old_string": was, "new_string": content}


QUIET = 15
"""Seconds without an event before the line says how long it has been."""


def working(quiet):
    """The line while the agent works, `quiet` seconds after the transcript
    last grew. A measurement and never a verdict, as the idle timeout and
    spend are: no warning, no colour, nothing ends (issue 130)."""
    if quiet < QUIET:
        return "Claude is working"
    minutes, seconds = divmod(int(quiet), 60)
    return ("Claude is working · quiet for "
            + (f"{minutes}m {seconds:02d}s" if minutes else f"{seconds}s"))


class Run:
    """One agent session, from the first prompt to the agent stopping.

    A run and not a build: what races over a space is the `build.py` editing
    *between* builds, and the transcript is a cursor over a list so that a
    reloaded tab reads the same thing the first one did.
    """

    def __init__(self, space, drive=None):
        self.space = Path(space)
        self.drive = drive
        self.events = []
        self.pending = None                   # the gate waiting for a verdict
        self.heard = time.monotonic()         # when the transcript last grew
        self.record = None                    # the hold on the space, while live
        self.stopped = False                  # the user said the run is over
        self.seeded = []                      # the marks this run was started from
        self.gates = 0                        # gates this run has stopped at
        self.prompt = ""                      # what this run was asked to do
        self.latest = None                    # what the space's run record says
        self.ceiling = None                   # the weighted spend it stops at
        self.requester = None                 # who asked, if nobody is watching
        self.chat_size = None                 # the size a chat said, for the first form
        self.asked_spans = set()              # by-eye spans this run has parked on
        self.skipped = set()                  # those the person put off for now
        self._lock = threading.Lock()
        self._thread = None

    def start(self, prompt, marks_selected=(), ceiling=None, requester=None,
              chat_size=None):
        """Begin. The prompt is the transcript's first line, because it is the
        first turn and the page is showing a conversation — so what is said there
        is the composed prompt and not the prose, because the composed one is
        what the agent was actually given (ADR 0019, decision 21).

        `ceiling` is what an unattended run may spend, in weighted tokens, before
        it is stopped (ADR 0027, decision 13). A run somebody is watching carries
        none: the stop is the person (ADR 0019, decision 37).

        `requester` is who asked for a run nobody is watching, as it described
        itself; a run started with one is unattended to its end (ADR 0027,
        decision 11).

        `chat_size` is the size a chat that made the space said, as *300 mm
        wide*: it fills the size field of this run's first form, as *from the
        chat* (ADR 0034, decision 6)."""
        prompt, self.seeded = seed.compose(self.space, prompt, marks_selected)
        # Hold the space first: a run whose transcript had started and whose
        # hold had been refused would be a run the user was watching happen
        # somewhere they had been told it would not.
        self.stopped = False
        self.gates = 0
        self.ceiling = ceiling
        self.requester = requester
        self.chat_size = chat_size
        # Asked once per run, and a new run asks again (ADR 0035, decision 5).
        self.asked_spans, self.skipped = set(), set()
        self.record = lock.take(self.space, "console run")
        # A first green said to nobody is said to this run, and spent only
        # once the run has the space (issue 121).
        prompt = topics.reminded(self.space, prompt)
        self.prompt = prompt
        self.latest = {"run": self.record["run"], "prompt": prompt,
                       "requester": requester, "vetoes": []}
        # What waits in the space is the space's, not the run's that set it
        # aside: a run started past it carries it on (ADR 0028, decision 5).
        if approvals.acts(self.space):
            self.latest.update(approvals.recorded(self.space))
        self.now("running")
        self.say("prompt", text=prompt)
        if requester is not None:
            # On the page, in its first lines: who asked, and that opening it
            # changes nothing about what still asks (ADR 0027, decision 11).
            self.say("asked", text=f"this run was asked for by {requester}; "
                                   f"some actions always ask you")
        self._thread = threading.Thread(target=self._go, args=(prompt,),
                                        daemon=True)
        self._thread.start()

    @property
    def over(self):
        """Has a run begun here and ended, however it ended?"""
        return (self.latest or {}).get("state") in ENDED

    @property
    def live(self):
        """Is an agent working right now? What `POST /run` has to ask before it
        starts another, because the space's own lock cannot tell these apart —
        two runs from one console share a run id, and the lock is deliberately
        re-entrant within one."""
        return self._thread is not None and self._thread.is_alive() \
            and not self.stopped

    def _go(self, prompt):
        """The session, and the end of it whatever the end was.

        The hold is given back here and not by whoever started the run: a driver
        that raised would otherwise leave the space held by a run that is no
        longer running, and the next caller would meet a lock with nobody behind
        it. `ended` on the transcript because the page is showing a
        conversation, and a conversation that stops without saying so reads as
        one still going.
        """
        try:
            (self.drive or driver())(prompt, options(self.space, self.record),
                                     self.gate, self.say)
            self.told()
            self.now("finished", closing=self.proposal())
            self.say("ended", text="the agent stopped")
        except Stopped:
            pass                              # `end` already said so, once
        except Exception as e:
            self.now("stopped", why=f"the run failed: {e}")
            self.say("ended", text=f"the run failed: {e}")
        finally:
            self.stop()

    def told(self):
        """Say what became of the marks this run was seeded with, if any.

        Before the run is declared over, on every way of being over: the last
        line of a conversation is *ended*, and a report arriving after it reads
        as something that happened later.
        """
        lines = seed.report(self.space, self.seeded)
        if lines:
            self.say("seeds", text=lines)

    def end(self, why="you ended the run", aside=False):
        """The user ends the run. Not the console: a run that ends and starts
        again never reaches compaction, so ending one is a thing to do often.

        The gate that may be waiting is answered by nobody: the call never
        happens and the agent is not told no, which it would work around. It is
        let go and stopped, and nothing is kept as a veto, because nobody
        refused anything (ADR 0027, decision 9). Ended from outside the page,
        `aside`, by somebody who never saw that gate, its call is set aside to
        wait for the person, as an unattended run's would (ADR 0031, decision
        3). From here on the agent's words are dropped and its calls refused,
        and the space is given back at once rather than when a thread notices.
        """
        # Before `stopped`, because after it the transcript takes nothing but
        # the ending itself — and this ending is the one where the report matters
        # most, the run stopped with work still outstanding.
        self.told()
        waiting = self.pending
        if aside and waiting is not None and waiting["category"] == approvals.QUESTION:
            self.asked(waiting["call"], waiting["said"]["fields"])
        elif aside and waiting is not None and waiting["category"] != SPANS:
            # A span is not set aside: it already waits in `marks.json`.
            self.aside(waiting["category"], waiting["tool"], waiting["call"],
                       waiting["case"])
        self.stopped = True
        self.now("stopped", why=why)
        self.say("ended", text=why)
        waiting, self.pending = self.pending, None
        if waiting is not None:
            waiting["answered"].set()
        self.stop()
        return {"ended": True}

    def stop(self):
        """Give the space back. The one place that does, for every way a run can
        be over — the agent stopped, it raised, the user ended it, or the process
        is going down with the run still parked at a gate nobody will answer. A
        hold that outlives its run wedges the space behind a file the user would
        have to know about, so there is one line to get right and it is here.
        """
        lock.release(self.space, self.record)
        self.record = None

    def now(self, state, **said):
        """Rewrite the space's run record in a new state (ADR 0027, decision
        8): what a requester reads to learn where a run it asked for is."""
        # Under the transcript's lock: the gate's thread and the page's both
        # write it, and a run the page ended must not be revived by the gate
        # it ended letting go a moment later.
        with self._lock:
            if self.latest.get("state") in ENDED:
                return                        # how a run ended is how it ended
            kept = {k: v for k, v in self.latest.items() if k not in PASSING}
            self.latest = {**kept, "state": state, **said}
            last_run.write(self.space, self.latest)

    def gate(self, tool, payload):
        """Stop, and wait for the user — or, in a run nobody is watching, set the
        call aside for them. Returns (allow, reason) — or, for a form
        the person approved, (True, the answers with their sources).

        The launcher is asked what the call *means* and the answer is a category
        — a build, a spec write, a commit — because one intent has four
        spellings and a glob list is brittle exactly where the stakes are.
        A call carrying no intent at all is not a gate: an agent makes dozens of
        reads a turn, and gating those is how the user ends up clicking rather
        than watching.
        """
        if self.stopped:
            raise Stopped()
        if policy.rewrites(tool, payload):
            # Not a gate: one the user allowed by reflex would be the agent
            # granting itself builds, or a bigger budget, by the user's hand.
            # The list is written from the page, by the user (ADR 0025,
            # decision 6), and the ceiling from a terminal (ADR 0027,
            # decision 13).
            why = ("the ask-list and the ceiling are the user's to change: the "
                   "list from the page's Always and Undo, the ceiling from their "
                   "terminal; ask them instead")
            self.say("refused", text=why)
            return False, why
        why = self.unlabelled(tool, payload)
        if why:
            self.say("refused", text=why)
            return False, why
        if tool == ASK_TOOL:
            return self.form(payload)
        if tool == QUESTION:
            # Its fields are fixed: no suggestion with a basis, and no field
            # for the person to find filled (ADR 0034, decision 1).
            why = ("under this console a question is asked with `ask`: each "
                   "question with your suggested answer and its basis")
            self.say("refused", text=why)
            return False, why
        if tool == "Bash" and activity.verb(payload.get("command") or "") == "worksheet":
            self.spans()
        case = None
        if tool == SPEC_TOOL:
            # The case comes with it rather than from what was said (ADR 0029).
            case = payload.get("case") or ""
            tool, payload = spec_edit(self.space, payload.get("content") or "")
        if tool == TOPICS_TOOL:
            case = payload.get("case") or ""
            payload = topics_shown(self.space, payload)
        # Here as well as in the guard: a script let through reads a picture it
        # cannot write, whether or not the space's hook ran first (ADR 0036).
        locked.lock(self.space, intent.references(tool, payload))
        category = TOPICS if tool == TOPICS_TOOL else intent.classify(tool, payload)
        if category is None:
            return True, None
        if category == "spec-write" and case is None:
            # Made any other way, its case is whatever was said before it, and
            # three runs said it only in their thinking, which no gate and no
            # person reads (ADR 0029). A script could not be read before it ran
            # anyway (issue 101). Refused, watched or not, before the ask-list:
            # one allowed in advance would still come with no case.
            why = (f"under this console a spec write is {MADE_WITH}, with "
                   f"{THE_CASE}; make it with that")
            self.say("refused", text=why)
            return False, why
        if category == "spec-write" and gate_words.partial(self.space / "spec.yaml",
                                                           tool, payload):
            # Part of a change: the revision alone moves nothing a page could
            # show, and a field alone turns the check red (issue 104).
            why = ("a spec write is the whole change, revision bump included, so "
                   "the person can read all it changes at once; make it again "
                   f"{MADE_WITH}, with {THE_CASE}")
            self.say("refused", text=why)
            return False, why
        unargued = (gate_words.unargued(self.space / "spec.yaml", tool, payload,
                                        case)
                    if category == "spec-write" else [])
        if unargued:
            # A case that does not name what the write sets is narration, which
            # passed for one before (issue 106). The numbers are what a gate can
            # check; whether they are argued well is the person's.
            why = (f"your case names what it sets: {', '.join(unargued)}; say "
                   f"why, with them, in its case, and make it again {MADE_WITH}")
            self.say("refused", text=why)
            return False, why
        # Unattended, the floor asks whatever the list says, and goes on asking
        # with the page open: a tab is presence, not attention (ADR 0027,
        # decisions 10 and 11).
        if category != TOPICS and not policy.gated(category, self.space) and not (
                self.requester is not None and category in policy.FLOOR):
            # The user allowed this in advance. Allowed, not unsupervised: it
            # leaves by the same door an answered gate leaves by, so what has to
            # happen before an approved call still happens.
            return self.approved(True, None, category)
        if self.requester is not None:
            # Nobody to wait for: the act waits instead, and the run goes on
            # (ADR 0028, decision 1).
            return self.aside(category, tool, payload, case)
        # The gate carries its own id rather than its place in the transcript.
        # The page can only learn it from the event, so a verdict cannot arrive
        # before there is something to receive it, and a stale one from a
        # reloaded tab cannot land on a later gate by arithmetic.
        # The call is kept on the gate rather than looked up when the verdict
        # lands: what a veto records is what the user was shown, and a second
        # reading of the agent's own dict could differ from it by then.
        waiting = self.waited(category, tool, payload, case)
        return self.approved(waiting["allow"], waiting["reason"], category)

    def waited(self, category, tool, payload, case, said=None):
        """Stop at a gate until the person answers it, shown as `said` or as
        the gate's words say it. Returns the gate, answered."""
        waiting = {"id": secrets.token_hex(8), "answered": threading.Event(),
                   "allow": None, "reason": None, "category": category,
                   "tool": tool, "call": dict(payload), "case": case}
        self.pending = waiting
        # A copy of the call, not the call. The transcript is served to the page
        # and answered from it, and the agent is holding this dict: shared, it
        # would be a route from a verdict back into the call, which is the one
        # thing a gate must not be able to do.
        if case:
            # Watched, the case is read where rule 1 puts it, as Claude's words
            # just before the gate: carried, it was not said (ADR 0029).
            self.say("text", text=case)
        # After the case is said: it is the proposal the gate names a span from.
        said = said or gate_words.say(category, self.space, tool, payload, self.proposal())
        waiting["said"] = said
        self.say("gate", id=waiting["id"], category=category, tool=tool,
                 call=dict(payload), said=said)
        # The act and nothing under it: the call and what it would change are
        # the page's, where the argument for them is (rule 1).
        # A form, as a chat may read it from `status` (ADR 0034, decision 5).
        self.parked(said["act"], **({"form": form.relayable(waiting["id"], payload["questions"])}
                                    if category == approvals.QUESTION else {}))
        while not waiting["answered"].wait(RELAY_S):
            if category == approvals.QUESTION:
                self.refilled(waiting)
        if self.stopped:
            raise Stopped()
        self.now("running")
        # Counted here and not at an ask-list allow: what costs a turn is the
        # stopping and the asking. A call the user allowed in advance cost the
        # agent nothing to have made.
        self.gates += 1
        return waiting

    def spans(self):
        """Before the worksheet, wait for the person's answers to the run's
        by-eye spans (ADR 0035, decision 1): their numbers cannot be proposed
        until then, and the worksheet is where the agent believes its reading
        is finished. Ends when each is answered on the canvas, or skipped."""
        if self.requester is not None:
            # Nobody to answer, and a span already waits in `marks.json`: the
            # worksheet says which are unanswered (ADR 0035, decision 6).
            return
        held = self.space / marks.NAME
        waiting_on = [m["id"] for m in marks.by_eye(marks.load(held))
                      if m["id"] not in self.asked_spans]
        if not waiting_on:
            return
        self.asked_spans.update(waiting_on)
        park = {"id": secrets.token_hex(8), "answered": threading.Event(),
                "category": SPANS, "spans": waiting_on}
        self.pending = park
        n = len(waiting_on)
        self.say("spans", id=park["id"], spans=waiting_on,
                 text=f"{SPANS_ACT}: {n} span{'s' if n != 1 else ''} it placed by eye. "
                      f"Answer {'them' if n != 1 else 'it'}, or skip for now, and "
                      f"the run goes on")
        self.parked(SPANS_ACT)
        while not park["answered"].wait(RELAY_S):
            still = {m["id"] for m in marks.by_eye(marks.load(held))} - self.skipped
            if not still & set(waiting_on):
                break
        if self.stopped:
            raise Stopped()
        self.pending = None
        # What was answered, kept in the transcript as a form keeps its
        # answers; the page closes the card on it (issue 158).
        self.say("spans-answered", id=park["id"], text=self.answered_spans(waiting_on))
        self.now("running")
        self.gates += 1

    def answered_spans(self, ids):
        """The park's spans as answered, by what each measures."""
        kept = {m["id"]: m for m in marks.load(self.space / marks.NAME)}
        said = [f"{marks.text(kept[i])} {ANSWERED.get(kept[i].get('answer'), 'skipped for now')}"
                for i in ids if i in kept]
        return "You answered Claude's spans: " + ", ".join(said)

    def skip(self, mark_id):
        """*skip for now*, on a span the run waits on: answered nothing, so it
        stays unanswered and its number still cannot be proposed, but the park
        no longer waits on it (ADR 0035, decision 4)."""
        park = self.pending
        if park is None or park["category"] != SPANS or mark_id not in park["spans"]:
            return {"refused": f"the run is not waiting on {mark_id}"}
        self.skipped.add(mark_id)
        # Where the worksheet this run is about to call can read it.
        worksheet.skip(self.space / ".contour", self.record["run"], self.skipped)
        return {"skipped": mark_id}

    def form(self, payload):
        """The agent's questions, as a form already filled (ADR 0034). Watched,
        the run waits at it; unwatched, it is set aside. Never on the ask-list
        and never a veto: nobody allows a question in advance, and an answer
        refuses nothing."""
        why = form.refused(payload)
        if why:
            self.say("refused", text=why)
            return False, why
        if self.requester is not None:
            return self.asked(payload)
        # The first form only: a later one asks again, and a size said once
        # in a chat is not an answer to it.
        size, self.chat_size = self.chat_size, None
        said = {"act": "Claude has questions",
                "fields": form.fields(payload["questions"], size)}
        waiting = self.waited(approvals.QUESTION, ASK_TOOL, payload, None, said)
        return True, waiting["reason"]

    def refilled(self, waiting):
        """What a chat filled in the form this run waits at, said to the page
        as `filled` when it changes anything (ADR 0034, decision 5). The page
        fills only the fields the person has not edited."""
        fields = waiting["said"]["fields"]
        now = form.filled(self.space, waiting["id"], waiting["call"]["questions"], fields)
        if now != fields:
            waiting["said"] = {**waiting["said"], "fields": now}
            self.say("filled", id=waiting["id"], fields=now)

    def unlabelled(self, tool, payload):
        """Why this call may not label the model, or None. Refused before any
        gate, watched or not (ADR 0030, decision 2)."""
        if topics.by_hand(tool, payload):
            # Not a gate, for the ask-list's reason: an Allow by reflex would
            # put back a word the person struck, and no word would be answered.
            return ("a model's topics are the person's to set: suggest them with "
                    "topics_propose, and they keep or strike each word")
        if tool != TOPICS_TOOL:
            return None
        words, before = topics.offered(self.space, payload.get("words") or [])
        if words:
            return None
        # Nothing left to put to the person, so nobody is asked.
        return (f"the user struck {', '.join(before) or 'every word'} for this "
                f"model before; it is not offered again")

    def aside(self, category, tool, payload, case=None):
        """Set a call aside for the person, in a run nobody is watching, and
        tell the agent so (ADR 0028, decision 1). Returns (False, why).

        Not a park: the run goes on, and the call waits in the space with what
        its gate would have shown, for whenever the person looks. Not a veto
        either, because nobody refused it; the agent is told it waits, so that
        it does not read a no and try the same thing another way.
        """
        case = self.proposal() if case is None else case
        said = gate_words.say(category, self.space, tool, payload, case)
        kept = approvals.set_aside(self.space, self.record["run"], category, tool,
                                   payload, said, case)
        # The act and nothing under it, as for a veto: the call, the diff and
        # the case are the page's (rule 1).
        with self._lock:
            self.latest.update(approvals.recorded(self.space))
            self.latest["set_aside"] = True
        self.say("aside", id=kept["id"], category=category, act=said["act"],
                 text=f"set aside for you to answer later: {said['act']}")
        return False, (f"set aside for the user, who will answer it later on the "
                       f"page ({said['act']}): carry on with what does not depend "
                       f"on it, do not try it another way, and say in your closing "
                       f"what waits on it, and not why: its case is on the page "
                       f"with it")

    def parked(self, act, **said):
        """Wait for the person, and say so in the record (ADR 0027, decision
        8). Nothing is posted on the machine: no banner (ADR 0028, decision 4)."""
        self.now("waiting for you", act=act, **said)

    def asked(self, payload, fields=None):
        """Set a question aside for the person, in a run nobody is watching,
        and tell the agent so (ADR 0028, decision 2). Returns (False, why).

        Not parked: nothing resumes, so the run finishes what does not depend
        on the answer, and the answer starts a run of its own later. And only
        the person answers it, because an answer becomes intent — *the anchor
        is 300 mm* from an agent reaches a spec write whose gate shows the diff
        and not where the number came from (ADR 0027, decision 12).
        """
        questions = [dict(q) for q in payload.get("questions") or ()]
        asking = " ".join(q.get("question", "") for q in questions)
        # As the page showed it, if it did: a field the chat filled stays
        # the chat's (ADR 0034, decision 6).
        said = {"act": "Claude has questions", "fields": fields or form.fields(questions)}
        kept = approvals.set_aside(self.space, self.record["run"], approvals.QUESTION,
                                   ASK_TOOL, payload, said, self.proposal())
        # The question's text and nothing else: it is the act, and what a
        # requester relays is that one waits, never an answer to it.
        with self._lock:
            self.latest.update(approvals.recorded(self.space))
            self.latest["set_aside"] = True
        self.say("aside", id=kept["id"], category=approvals.QUESTION, act=asking,
                 text=f"set aside for you to answer later: {asking}")
        return False, ("set aside: the user will answer it later on the page, "
                       "which starts a new run with the answer. Finish what "
                       "does not depend on it, and say in your closing what you "
                       "could not do without one")

    def proposal(self):
        """What the agent last said, which before a spec write is the case
        for it (rule 1): the gate names the span it measured on."""
        with self._lock:
            return next((e["text"] for e in reversed(self.events)
                         if e["kind"] == "text"), "")

    def approved(self, allow, reason, category):
        """The one way out of the gate for a call that is about to happen.

        Both allows leave by here — the one the user just clicked and the one
        they granted in advance in the ask-list — because the ask-list buys not
        being *asked*, and never permission for a rebuild to invalidate a mark
        mid-typing (ADR 0019, decision 14).
        """
        if allow:
            self.before(category)
        return allow, reason

    def before(self, category):
        """What has to happen before a call the user approved actually runs.

        One thing so far, and it is the reason a build is gated at all: a mark
        carries the pixel it was clicked on, and a ray through that pixel must
        hit the geometry the sheet was drawn from. The console owns the build, so
        this is the instant before geometry changes — a strictly better place to
        cast rays than session close, which is where ADR 0018 had to put them
        (ADR 0019, decisions 10 and 14).
        """
        if category != "build":
            return
        # Asked here rather than paid for blindly: most approvals have no new pin
        # waiting, and a Blender startup on every one of them would add a second
        # to the most-pressured gate in the system for nothing. Read by importing
        # `lib/`, which is the half of ADR 0019's decision 31 this process may do itself.
        if not marks.unresolved(marks.load(self.space / marks.NAME)):
            return
        _ok, lines = launcher.run(self.space, "resolve",
                                  held_by=self.record["run"])
        # On the transcript, in the launcher's own words. A mark changes shape at
        # this moment — its pixel is spent and an anchor takes its place — and
        # the transcript is the only place a run is visible, so this is where the
        # reason a later pin sits where it does gets recorded.
        for line in lines:
            self.say("resolved", text=line)

    def answer(self, at, allow, reason=None, always=False, kept=None, answers=None):
        """The user's verdict on the gate that is waiting, or None if none is.

        On the transcript, because the decision is as much a part of the run as
        the call was: a veto is why two builds differ, and slice 11 makes this
        the record. Note what is *not* read here — the call. A gate cannot edit
        it, because editing it would make the user the author of a change
        attributed to the agent, in the commit and in every later reading of why
        two builds differ (ADR 0019, decision 13).
        """
        waiting = self.pending
        if waiting is None or waiting["id"] != at or waiting["category"] == SPANS:
            # A wait on spans is answered span by span, on the canvas.
            return None
        waiting["allow"], waiting["reason"] = bool(allow), reason
        self.pending = None
        if waiting["category"] == approvals.QUESTION:
            # Approved, the answers are what the agent is told, each with
            # where its text came from (ADR 0034, decisions 2 and 3).
            waiting["reason"] = form.answered(waiting["said"]["fields"], answers or [])
            form.keep(self.space, self.record["run"], waiting["reason"])
            form.forget(self.space, at)
            self.say("verdict", id=at, allowed=True, text="")
            waiting["answered"].set()
            return {"answered": True}
        if waiting["category"] == TOPICS:
            # Answered word by word, and no veto either way: a struck word
            # refuses a word, not a call (ADR 0030, decision 5). What was kept
            # is what the agent is told, as a question's answers are.
            words = waiting["call"].get("words") or []
            kept = [w for w in words if w in (kept or [])] if allow else []
            topics.answered(self.space, words, kept)
            # Denied, the SDK hands the agent a sentence and not a record.
            waiting["reason"] = topics.told(
                words, kept, waiting["call"].get("struck_before", [])) if allow else \
                f"the user struck every word: {', '.join(words)}"
            self.say("verdict", id=at, allowed=bool(allow), text=", ".join(kept))
            waiting["answered"].set()
            return {"answered": True}
        if allow and always and waiting["category"] in policy.ALWAYS:
            # The user's own act, by the page's door to the command that writes
            # the list: the next build in this space runs without asking. Done
            # before the call is let go, so it is in force for the next one.
            launcher.run(self.space, "asks", "--always", waiting["category"], "--json")
        if not allow:
            # The transcript dies with the tab; this does not. A denial is why
            # two builds differ, so it is kept in the space and reaches git with
            # the change it prevented (ADR 0019, decisions 15 and 33).
            vetoes.record(self.space, waiting["category"], waiting["tool"],
                          waiting["call"], reason)
            # The act and the user's reason, never the call (rule 1).
            act = gate_words.WORDS.get(waiting["category"], (waiting["category"],))[0]
            with self._lock:
                self.latest["vetoes"].append({"act": act, "reason": reason})
        self.say("verdict", id=at, allowed=bool(allow), text=reason or "")
        waiting["answered"].set()
        return {"answered": True}

    def say(self, kind, **fields):
        """Append one line to the transcript. Numbered as it lands, so a cursor
        into it means the same thing to every reader."""
        if self.stopped and kind != "ended":
            raise Stopped()
        if kind == "usage":
            # Not a line of the conversation: what a turn cost is not something
            # the agent said. It leaves by this seam because usage is the
            # driver's to report and the file is the console's to keep, and one
            # seam of two callbacks is what makes the rest of this file provable
            # without the SDK.
            here = self.record["run"]
            spend.record(self.space, here, fields["usage"], self.gates,
                         self.prompt)
            # And on the transcript, as a running total: the page is where the
            # cost is watched, and it reads the transcript from a cursor — so a
            # reloaded tab gets the figure back with everything else instead of
            # whatever was spent after it reconnected.
            spent = spend.total(self.space, here)
            event = self.say("spend", **spent)
            if self.ceiling is not None and spent["weighted"] >= self.ceiling:
                # The stop the user would have made, decided in advance: no gate
                # answered, the edits kept (ADR 0027, decisions 9 and 13).
                self.end(f"reached your limit of {self.ceiling}")
                raise Stopped()
            return event
        if kind == "call":
            # What the call did, in words, beside the call itself, which the
            # page keeps one click away (ADR 0025, decision 8).
            fields["activity"] = activity.line(fields.get("tool"), fields.get("call") or {})
            fields["fold"] = None
        if kind == "text":
            # The words as the agent formatted them, beside the words as it
            # wrote them: the page draws the one and nothing that reads the
            # other changes (issue 128).
            fields["blocks"] = prose.blocks(fields["text"])
        with self._lock:
            event = {"n": len(self.events), "kind": kind, **fields}
            if kind == "call" and fields["tool"] in activity.QUIET:
                self.fold(event)
            self.events.append(event)
            self.heard = time.monotonic()
        return event

    def fold(self, event):
        """Fold a read into the reads just before it. The event names the
        first of them, and says the line as it now stands — so the page
        redraws one line, and a reloaded tab, replaying every event, ends on
        the same words. Spend between them is not a line, so it breaks
        nothing; anything else said in between starts a new fold."""
        last = next((e for e in reversed(self.events) if e["kind"] != "spend"), None)
        event["fold"] = (last["fold"] if last and last["kind"] == "call"
                         and last.get("fold") is not None else event["n"])
        event["activity"] = activity.looked(
            1 + sum(1 for e in self.events if e.get("fold") == event["fold"]))

    def since(self, n):
        """The transcript from a cursor, and the cursor to ask with next."""
        with self._lock:
            return {"events": self.events[n:], "next": len(self.events),
                    "now": self.status()}

    def status(self):
        """The line under the transcript: whether the agent is working, never
        how far along it is (issue 130; ADR 0019, decision 4). The console's to
        say and not the tab's, so a reloaded tab that started nothing is told
        the same as the one that did."""
        # Over once the transcript says so, though the thread is still winding
        # down: the line and the transcript are one reply, and must not be two
        # answers to whether the run is going.
        latest = next((e["kind"] for e in reversed(self.events)
                       if e["kind"] in ("prompt", "ended")), None)
        if not self.live or latest == "ended":
            return {"state": "idle", "said": "no run"}
        if self.pending is not None and self.pending["category"] == SPANS:
            return {"state": "waiting", "said": f"Waiting for you: {SPANS_ACT}"}
        if self.pending is not None:
            return {"state": "waiting", "said": "Waiting for you: answer above"}
        return {"state": "working", "said": working(time.monotonic() - self.heard)}
