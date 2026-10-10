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
from pathlib import Path

from console import approvals, last_run, launcher, seed, spend, vetoes
from lib import activity, gate as gate_words, intent, lock, marks, policy
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

PASSING = ("act", "questions")
"""What the run record says only while the state that set it lasts."""

QUESTION = "AskUserQuestion"
"""The tool an agent asks the person a question with (ADR 0027, decision 12)."""


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
        self.gates = 0                        # gates this run has stopped at
        self.prompt = ""                      # what this run was asked to do
        self.latest = None                    # what the space's run record says
        self.ceiling = None                   # the weighted spend it stops at
        self.requester = None                 # who asked, if nobody is watching
        self._lock = threading.Lock()
        self._thread = None

    def start(self, prompt, marks_selected=(), ceiling=None, requester=None):
        """Begin. The prompt is the transcript's first line, because it is the
        first turn and the page is showing a conversation — so what is said there
        is the composed prompt and not the prose, because the composed one is
        what the agent was actually given (ADR 0019, decision 21).

        `ceiling` is what an unattended run may spend, in weighted tokens, before
        it is stopped (ADR 0027, decision 13). A run somebody is watching carries
        none: the stop is the person (ADR 0019, decision 37).

        `requester` is who asked for a run nobody is watching, as it described
        itself; a run started with one is unattended to its end (ADR 0027,
        decision 11)."""
        prompt, self.seeded = seed.compose(self.space, prompt, marks_selected)
        # Hold the space first: a run whose transcript had started and whose
        # hold had been refused would be a run the user was watching happen
        # somewhere they had been told it would not.
        self.stopped = False
        self.gates = 0
        self.prompt = prompt
        self.ceiling = ceiling
        self.requester = requester
        self.record = lock.take(self.space, "console run")
        self.latest = {"run": self.record["run"], "prompt": prompt,
                       "requester": requester, "vetoes": []}
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

    def end(self, why="you ended the run"):
        """The user ends the run. Not the console: a run that ends and starts
        again never reaches compaction, so ending one is a thing to do often.

        The gate that may be waiting is answered by nobody: the call never
        happens and the agent is not told no, which it would work around. It is
        let go and stopped, and nothing is kept as a veto, because nobody
        refused anything (ADR 0027, decision 9). From here on the agent's words
        are dropped and its calls refused, and the space is given back at once
        rather than when a thread notices.
        """
        # Before `stopped`, because after it the transcript takes nothing but
        # the ending itself — and this ending is the one where the report matters
        # most, the run stopped with work still outstanding.
        self.told()
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
        call aside for them. Returns (allow, reason) — or, for a
        question in a run nobody is watching, (True, the person's answers).

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
        if tool == QUESTION and self.requester is not None:
            return self.asked(payload)
        category = intent.classify(tool, payload)
        if category is None:
            return True, None
        # Unattended, the floor asks whatever the list says, and goes on asking
        # with the page open: a tab is presence, not attention (ADR 0027,
        # decisions 10 and 11).
        if not policy.gated(category, self.space) and not (
                self.requester is not None and category in policy.FLOOR):
            # The user allowed this in advance. Allowed, not unsupervised: it
            # leaves by the same door an answered gate leaves by, so what has to
            # happen before an approved call still happens.
            return self.approved(True, None, category)
        if self.requester is not None:
            # Nobody to wait for: the act waits instead, and the run goes on
            # (ADR 0028, decision 1).
            return self.aside(category, tool, payload)
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
        said = gate_words.say(category, self.space, tool, payload, self.proposal())
        self.say("gate", id=waiting["id"], category=category, tool=tool,
                 call=dict(payload), said=said)
        # The act and nothing under it: the call and what it would change are
        # the page's, where the argument for them is (rule 1).
        self.parked(said["act"])
        waiting["answered"].wait()
        if self.stopped:
            raise Stopped()
        self.now("running")
        # Counted here and not at an ask-list allow: what costs a turn is the
        # stopping and the asking. A call the user allowed in advance cost the
        # agent nothing to have made.
        self.gates += 1
        return self.approved(waiting["allow"], waiting["reason"], category)

    def aside(self, category, tool, payload):
        """Set a call aside for the person, in a run nobody is watching, and
        tell the agent so (ADR 0028, decision 1). Returns (False, why).

        Not a park: the run goes on, and the call waits in the space with what
        its gate would have shown, for whenever the person looks. Not a veto
        either, because nobody refused it; the agent is told it waits, so that
        it does not read a no and try the same thing another way.
        """
        case = self.proposal()
        said = gate_words.say(category, self.space, tool, payload, case)
        kept = approvals.set_aside(self.space, self.record["run"], category, tool,
                                   payload, said, case)
        # The act and nothing under it, as for a veto: the call, the diff and
        # the case are the page's (rule 1).
        with self._lock:
            self.latest.setdefault("approvals", []).append(said["act"])
        self.say("aside", id=kept["id"], category=category, act=said["act"],
                 text=f"set aside for you to answer later: {said['act']}")
        return False, (f"set aside for the user, who will answer it later on the "
                       f"page ({said['act']}): carry on with what does not depend "
                       f"on it, do not try it another way, and say in your closing "
                       f"what waits on it")

    def parked(self, act, **said):
        """Wait for the person, and say so in the record (ADR 0027, decision
        8). Nothing is posted on the machine: no banner (ADR 0028, decision 4)."""
        self.now("waiting for you", act=act, **said)

    def asked(self, payload):
        """Park on a question in a run nobody is watching, and return
        (True, the person's answers) once they have given them on the page.

        Parked and not ended: nothing resumes, so a run that ended on a question
        would throw its working context away over a one-word answer. And only
        the person answers it, because an answer becomes intent — *the anchor is
        300 mm* from an agent reaches a spec write whose gate shows the diff and
        not where the number came from (ADR 0027, decision 12).
        """
        questions = [dict(q) for q in payload.get("questions") or ()]
        waiting = {"id": secrets.token_hex(8), "answered": threading.Event(),
                   "answers": None, "question": True}
        self.pending = waiting
        self.say("question", id=waiting["id"], questions=questions)
        # The text, so a requester can relay it; never an answer, which only
        # the page takes.
        self.parked("Claude has a question",
                    questions=[q.get("question", "") for q in questions])
        waiting["answered"].wait()
        if self.stopped:
            raise Stopped()
        self.now("running")
        return True, waiting["answers"]

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

    def answer(self, at, allow, reason=None, always=False):
        """The user's verdict on the gate that is waiting, or None if none is.

        On the transcript, because the decision is as much a part of the run as
        the call was: a veto is why two builds differ, and slice 11 makes this
        the record. Note what is *not* read here — the call. A gate cannot edit
        it, because editing it would make the user the author of a change
        attributed to the agent, in the commit and in every later reading of why
        two builds differ (ADR 0019, decision 13).
        """
        waiting = self.pending
        if waiting is None or waiting["id"] != at or waiting.get("question"):
            return None                       # a question has no *allow*
        waiting["allow"], waiting["reason"] = bool(allow), reason
        self.pending = None
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

    def reply(self, at, answers):
        """The person's answers to the question that is waiting, or None if
        none is. The page's alone: there is no command or connector spelling
        of this, because an answer becomes intent (ADR 0027, decision 12)."""
        waiting = self.pending
        if waiting is None or waiting["id"] != at or not waiting.get("question"):
            return None
        waiting["answers"] = {str(q): str(a) for q, a in dict(answers).items()}
        self.pending = None
        self.say("answer", id=at, answers=waiting["answers"])
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
        with self._lock:
            event = {"n": len(self.events), "kind": kind, **fields}
            if kind == "call" and fields["tool"] in activity.QUIET:
                self.fold(event)
            self.events.append(event)
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
            return {"events": self.events[n:], "next": len(self.events)}
