"""The lobby's labelling act: topics proposed for every space with none, together
(ADR 0030, decision 7).

One agent session reads each unlabelled model's last sheet and proposes for all
of them, from one vocabulary, so the reuse rule means something: one run per
space would each propose against an empty one. It is not a run. It holds no
space, builds nothing and writes no run record of its own; each proposal is set
aside as an approval in its space, which is where the person answers it and what
refuses a request there until they have (ADR 0030, decision 6).

Above `lib/` for the approval store's reason: an approval is the console's, and
so is the agent that proposes.
"""
import json
import os
import secrets
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

from console import approvals, last_run
from console import run as run_lib
from lib import gate as gate_words, lock, survey, topics
from lib import space as space_lib

TOPICS_TOOL = run_lib.TOPICS_TOOL

LABEL = f"{run_lib.HERE / 'agent.py'}:label"
"""The driver the act runs, unless `$CONTOUR_CONSOLE_AGENT` replaces it."""


def taken(listing):
    """The spaces this act proposes for, by name, and why each other space with
    no topics is left out: there is no sheet to read, or a proposal set aside
    now would land under a run, a console or an approval already there."""
    spaces, skipped = {}, {}
    for s in listing["spaces"]:
        if s["topics"]:
            continue
        why = unready(s)
        if why:
            skipped[s["name"]] = why
        else:
            spaces[s["name"]] = s
    return spaces, skipped


def unready(row):
    """Why no proposal is made for this space now, or None."""
    rec = lock.holder(row["path"])
    if row["picture"] != "sheet":
        return "no sheet to read yet"
    if rec and lock.alive(rec):
        return "a run holds it"
    if any(p["kind"] == "console" for p in row["presence"]):
        return "a console is open on it"
    if row["approvals"]:
        return "approvals already wait in it"
    return None


def tools(vocabulary):
    """The act's proposal, as an SDK tool: the console's own, naming the model
    it is for. Reached only if the gate allows it, which it never does: every
    proposal is set aside for the person."""
    from claude_agent_sdk import tool
    said = run_lib.topics_proposer(vocabulary)
    schema = {**said["schema"], "required": ["model", *said["schema"]["required"]],
              "properties": {"model": {"type": "string"}, **said["schema"]["properties"]}}

    @tool(said["name"], said["description"].replace("this model", "the model named as model"),
          schema)
    async def topics_propose(args):
        return {"content": [{"type": "text", "text": "set aside for the user"}]}
    return [topics_propose]


def options():
    """Where the act's agent works: an empty directory, so no read is allowed
    without the gate; `Read` its only tool besides the proposal; and none of a
    space's settings or skills, since it works in no space."""
    return {"cwd": tempfile.mkdtemp(prefix="contour-label-"), "tools": ["Read"],
            "setting_sources": [], "env": dict(os.environ)}


def label(drive=None, planned=None):
    """Propose for every unlabelled space, in one agent session. `planned` is
    told which spaces it proposes for and why the others are skipped, before
    the agent starts. Answered with that plan and how it ended: None once it
    has proposed, and otherwise the agent's last words."""
    spaces, skipped = taken(survey.listing())
    plan = {"proposing": list(spaces), "skipped": skipped}
    if planned:
        planned(plan)
    if not spaces:
        return dict(plan, ended=None)    # nothing to propose for, so no agent is asked to
    act = "label-" + secrets.token_hex(4)

    proposed = set()

    def gate(tool, payload):
        why = allowed(spaces, proposed, tool, payload)
        if why:
            return False, why
        if tool != TOPICS_TOOL:
            return True, None
        proposed.add(payload["model"])
        return aside(spaces[payload["model"]]["path"], act, payload)

    words = []

    def say(kind, **said):
        if kind == "text":
            words.append(said["text"])

    working = options()
    try:
        (drive or run_lib.driver(os.environ.get("CONTOUR_CONSOLE_AGENT") or LABEL))(
            prompt(spaces, survey.vocabulary()), working, gate, say)
    finally:
        shutil.rmtree(working["cwd"], ignore_errors=True)
    if proposed:
        return dict(plan, ended=None)
    return dict(plan, ended="Claude suggested nothing: "
                + (words[-1] if words else "it said nothing either"))


def allowed(spaces, proposed, tool, payload):
    """Why the act's agent may not make this call, or None if it may: read a
    sheet it was given, or propose once for a model it was given. It edits and
    builds nothing, and reads nothing else of any model (ADR 0030, decision 8)."""
    if tool == "Read":
        sheets = {str(space_lib.layout(s["path"]).sheet.resolve()) for s in spaces.values()}
        if str(Path(payload.get("file_path") or "").resolve()) in sheets:
            return None
        return "this act reads the sheets it was given and nothing else"
    if tool != TOPICS_TOOL:
        return "this act proposes topics and does nothing else"
    model = payload.get("model")
    if model not in spaces:
        return f"{model} is not one of the models this act proposes for"
    if model in proposed:
        return f"{model} has its proposal already: one per model"
    return None


def prompt(spaces, vocabulary):
    """What the agent is asked: each model's name and its last sheet, and the
    words already in use, with the names carrying them and nothing else of
    another model (ADR 0030, decisions 3 and 8)."""
    in_use = "; ".join(f"{w} ({', '.join(names)})" for w, names in vocabulary.items())
    sheets = "\n".join(f"{name}: {space_lib.layout(s['path']).sheet}"
                       for name, s in spaces.items())
    return ("These models carry no topics yet: words to find a model by, such as "
            "creature or low-poly. Read each one's sheet, then propose topics for "
            "it with topics_propose, naming it as model: one call per model. "
            "Spell a word the same wherever it fits more than one of them.\n"
            f"{sheets}\n"
            + (f"Words in use: {in_use}. Reuse one wherever it fits."
               if in_use else "No model carries a topic yet."))


def aside(space, act, payload):
    """One proposal set aside in its space, as an unwatched run's is."""
    case = payload.get("case") or ""
    call = run_lib.topics_shown(space, {k: v for k, v in payload.items() if k != "model"})
    said = gate_words.say(topics.CATEGORY, space, TOPICS_TOOL, call, case)
    approvals.set_aside(space, act, topics.CATEGORY, TOPICS_TOOL, call, said, case)
    last_run.amend(space, **approvals.recorded(space))
    return False, "set aside for the user, who answers it on the lobby's page"


def shown():
    """Every topic proposal waiting next in a space, on one page: the space, and
    the proposal as its gate would have shown it."""
    return [{"name": s["name"], "path": s["path"], "id": a["id"],
             "words": a["call"]["words"], "new": a["call"].get("new") or [],
             "case": a["case"]}
            for s in survey.listing()["spaces"]
            for a in approvals.shown(s["path"])
            if a["category"] == topics.CATEGORY and a["next"]]


def answered(path, at, words):
    """One space's proposal answered on the page: `words` are kept, the rest
    struck. Only for a space the listing holds, and not while a run there may
    still be adding to what waits in it."""
    if path not in {s["path"] for s in survey.listing()["spaces"]}:
        return None
    rec = lock.holder(path)
    if rec and lock.alive(rec):
        return {"answered": False, "why": "a run holds it; answer it when the run has ended"}
    return approvals.labelled(path, at, words)


def main(argv):
    """The act as the lobby runs it, under the console's interpreter: `label`
    prints its plan as one line, then proposes; `shown` and `answer` are the
    page's reading and its answer, as JSON."""
    if argv[:1] == ["label"]:
        # Its plan, then one last line saying how it ended, which the page
        # shows: an act that dies must not leave it waiting with no word.
        try:
            ended = label(planned=lambda plan: print(json.dumps(plan), flush=True))["ended"]
        except Exception as e:
            traceback.print_exc()
            ended = f"it stopped: {e}"
        print(json.dumps({"ended": ended}), flush=True)
    elif argv[:1] == ["shown"]:
        print(json.dumps(shown()))
    elif argv[:1] == ["answer"]:
        asked = json.loads(sys.stdin.read())
        print(json.dumps(answered(asked.get("path"), asked.get("id"),
                                  asked.get("words") or [])))
    else:
        print("usage: python -m console.labelling label|shown|answer", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
