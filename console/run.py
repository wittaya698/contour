"""One run: prose in, a driven agent, every call gated (ADR 0019, decisions 1,
3, 13, 17, 22).

The console's half of the run and not the SDK's. Everything here is standard
library, which is what makes the gate, the wait and the lock provable on a clone
with nothing installed; the one file that imports `claude-agent-sdk` is
`agent.py` beside this, and it is reached through `driver` below.
"""
import importlib.util
import os
import secrets
import threading
from pathlib import Path

from console import launcher, seed, vetoes
from lib import anchor, intent, lock, marks, policy


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
    that drifts (ADR 0019, decision 21).

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
        self.record = None                    # the hold on the space, while live
        self.stopped = False                  # the user said the run is over
        self.seeded = []                      # the marks this run was started from
        self._lock = threading.Lock()
        self._thread = None

    def start(self, prompt, marks_selected=()):
        """Begin. The prompt is the transcript's first line, because it is the
        first turn and the page is showing a conversation — so what is said there
        is the composed prompt and not the prose, because the composed one is
        what the agent was actually given (ADR 0019, decision 19)."""
        prompt, self.seeded = seed.compose(self.space, prompt, marks_selected)
        # Hold the space first: a run whose transcript had started and whose
        # hold had been refused would be a run the user was watching happen
        # somewhere they had been told it would not.
        self.stopped = False
        self.record = lock.take(self.space, "console run")
        self.say("prompt", text=prompt)
        self._thread = threading.Thread(target=self._go, args=(prompt,),
                                        daemon=True)
        self._thread.start()

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
            self.say("ended", text="the agent stopped")
        except Stopped:
            pass                              # `end` already said so, once
        except Exception as e:
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

    def end(self):
        """The user ends the run. Not the console: a run that ends and starts
        again never reaches compaction, so ending one is a thing to do often.

        The gate that may be waiting is answered as a denial, because the agent
        asked a question and *no* is the true answer to it now. From here on the
        agent's words are dropped and its calls refused, and the space is given
        back at once rather than when a thread notices.
        """
        # Before `stopped`, because after it the transcript takes nothing but
        # the ending itself — and this ending is the one where the report matters
        # most, the run stopped with work still outstanding.
        self.told()
        self.stopped = True
        self.say("ended", text="you ended the run")
        waiting, self.pending = self.pending, None
        if waiting is not None:
            waiting["allow"], waiting["reason"] = False, "the run was ended"
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

    def gate(self, tool, payload):
        """Stop, and wait for the user. Returns (allow, reason).

        The launcher is asked what the call *means* and the answer is a category
        — a build, a spec write, a commit — because one intent has four
        spellings and a glob list is brittle exactly where the stakes are.
        A call carrying no intent at all is not a gate: an agent makes dozens of
        reads a turn, and gating those is how the user ends up clicking rather
        than watching.
        """
        if self.stopped:
            raise Stopped()
        category = intent.classify(tool, payload)
        if category is None:
            return True, None
        if not policy.gated(category, self.space):
            # The user allowed this in advance. Allowed, not unsupervised: it
            # leaves by the same door an answered gate leaves by, so what has to
            # happen before an approved call still happens.
            return self.approved(True, None, category)
        # The gate carries its own id rather than its place in the transcript.
        # The page can only learn it from the event, so a verdict cannot arrive
        # before there is something to receive it, and a stale one from a
        # reloaded tab cannot land on a later gate by arithmetic.
        # The call is kept on the gate rather than looked up when the verdict
        # lands: what a veto records is what the user was shown, and a second
        # reading of the agent's own dict could differ from it by then.
        waiting = {"id": secrets.token_hex(8), "answered": threading.Event(),
                   "allow": None, "reason": None, "category": category,
                   "tool": tool, "call": dict(payload)}
        self.pending = waiting
        # A copy of the call, not the call. The transcript is served to the page
        # and answered from it, and the agent is holding this dict: shared, it
        # would be a route from a verdict back into the call, which is the one
        # thing a gate must not be able to do.
        self.say("gate", id=waiting["id"], category=category, tool=tool,
                 call=dict(payload))
        waiting["answered"].wait()
        return self.approved(waiting["allow"], waiting["reason"], category)

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
        (ADR 0019, decisions 8 and 14).
        """
        if category != "build":
            return
        # Asked here rather than paid for blindly: most approvals have no new pin
        # waiting, and a Blender startup on every one of them would add a second
        # to the most-pressured gate in the system for nothing. Read by importing
        # `lib/`, which is the half of decision 28 this process may do itself.
        if not anchor.unresolved(marks.load(self.space / marks.NAME)):
            return
        _ok, lines = launcher.run(self.space, "resolve",
                                  held_by=self.record["run"])
        # On the transcript, in the launcher's own words. A mark changes shape at
        # this moment — its pixel is spent and an anchor takes its place — and
        # the transcript is the only place a run is visible, so this is where the
        # reason a later pin sits where it does gets recorded.
        for line in lines:
            self.say("resolved", text=line)

    def answer(self, at, allow, reason=None):
        """The user's verdict on the gate that is waiting, or None if none is.

        On the transcript, because the decision is as much a part of the run as
        the call was: a veto is why two builds differ, and slice 11 makes this
        the record. Note what is *not* read here — the call. A gate cannot edit
        it, because editing it would make the user the author of a change
        attributed to the agent, in the commit and in every later reading of why
        two builds differ (ADR 0019, decision 13).
        """
        waiting = self.pending
        if waiting is None or waiting["id"] != at:
            return None
        waiting["allow"], waiting["reason"] = bool(allow), reason
        self.pending = None
        if not allow:
            # The transcript dies with the tab; this does not. A denial is why
            # two builds differ, so it is kept in the space and reaches git with
            # the change it prevented (ADR 0019, decisions 15 and 25).
            vetoes.record(self.space, waiting["category"], waiting["tool"],
                          waiting["call"], reason)
        self.say("verdict", id=at, allowed=bool(allow), text=reason or "")
        waiting["answered"].set()
        return {"answered": True}

    def say(self, kind, **fields):
        """Append one line to the transcript. Numbered as it lands, so a cursor
        into it means the same thing to every reader."""
        if self.stopped and kind != "ended":
            raise Stopped()
        with self._lock:
            event = {"n": len(self.events), "kind": kind, **fields}
            self.events.append(event)
        return event

    def since(self, n):
        """The transcript from a cursor, and the cursor to ask with next."""
        with self._lock:
            return {"events": self.events[n:], "next": len(self.events)}
