"""The agent's questions, as a form the person approves (ADR 0034).

Standard library only, and in `lib/`: the console asks with it, and what was
approved is read back by the half that writes an anchor span's question
(issue 148), which never imports the console.
"""
import time

from lib import last_run, space as space_lib, store

RELAYED = "relayed.json"
"""What a chat filled in a waiting form, by form and question id: the newest
text for each, until the form is approved (ADR 0034, decision 5)."""

NAME = "answers.json"
"""Every form the person approved in a space, beside its approvals: the
answers and where each came from (ADR 0034, decision 4)."""


def refused(payload):
    """Why this `ask` cannot be put to the person, or None. A suggestion with
    no basis is refused as a spec write with no case is (ADR 0034, decision
    1)."""
    questions = payload.get("questions") if isinstance(payload, dict) else None
    if not isinstance(questions, list) or not questions:
        return "ask carries its questions: each a question, a suggested answer and its basis"
    for q in questions:
        asked = (q or {}).get("question") if isinstance(q, dict) else None
        if not asked:
            return "each question has its question's text"
        if not q.get("suggested"):
            return f"{asked!r} has no suggested answer: suggest one, and say its basis"
        if not q.get("basis"):
            return (f"{asked!r} suggests {q['suggested']!r} with no basis: say what "
                    f"the suggestion rests on, so the person can weigh it")
    if sum(1 for q in questions if q.get("is_size")) > 1:
        return ("only one question is the size: the anchor is one number, so mark "
                "is_size on the question whose answer it is")
    return None


def fields(questions, size=None):
    """The form as the page first shows it: every field filled with Claude's
    guess, and the basis under it (ADR 0034, decision 2). `size` is what a
    chat said the size is, which fills the size field instead, as *from the
    chat*: it beats a guess, and one identical to the guess stays Claude's,
    since the agreement says nothing the page can check (ADR 0034, decision 3)."""
    return [_field(q, size if q.get("is_size") else None) for q in questions]


def _field(q, chat):
    chat = chat if chat and chat != q["suggested"] else None
    return {"question": q["question"], "text": chat or q["suggested"],
            "source": "chat" if chat else "guess", "basis": q["basis"],
            **({"is_size": True} if q.get("is_size") else {})}


def source(field, text):
    """Where an approved field's text came from: wherever it was filled from,
    if it still reads as filled, and the person's otherwise (ADR 0034,
    decision 3)."""
    return field["source"] if text == field["text"] else "yours"


def answered(fields, texts):
    """The form as approved, from the fields the page showed: each question,
    its answer, and the answer's source. A field the page sent nothing for is
    what it was filled with."""
    texts = list(texts) + [None] * len(fields)
    return [{"question": f["question"], "answer": f["text"] if t is None else t,
             "source": source(f, f["text"] if t is None else t),
             **({"is_size": True} if f.get("is_size") else {})}
            for f, t in zip(fields, texts)]


TOLD = {"guess": "Claude's guess, approved", "chat": "from the chat", "yours": "yours"}
"""An answer's source, as the agent is told it: a guess approved is still a
guess, and is named as one wherever it is used (ADR 0034, decision 4)."""


def told(answers):
    """The approved form, as the agent reads it: each question, and its answer
    with where it came from."""
    return "\n".join(f"{a['question']}\n  {a['answer']} ({TOLD[a['source']]})"
                     for a in answers)


def relayable(at, questions):
    """A waiting form as a chat may read it: its id, and each question's id and
    text, and never Claude's suggestions or their basis, so a chat cannot hand
    a guess back as the user's (ADR 0034, decision 5)."""
    return {"id": at, "questions": [{"id": f"q{n}", "question": q["question"]}
                                    for n, q in enumerate(questions, 1)]}


def path(space):
    return space_lib.layout(space).dot / NAME


def approved(space):
    """Every form approved in this space, oldest first."""
    return store.load(path(space), [])


def keep(space, run, answers):
    """Keep one approved form's answers with their sources. Returns it."""
    kept = {"run": run, "at": time.time(), "answers": answers}
    store.save(path(space), approved(space) + [kept])
    return kept


def sized(space):
    """Where the size the user last approved came from: its answer's source,
    or None when no approved form has answered the size. The anchor span
    reads it, so a guess approved is asked as one (ADR 0034, decision 4)."""
    said = [a for kept in approved(space) for a in kept["answers"] if a.get("is_size")]
    return said[-1]["source"] if said else None


FILLED = ("the user approves on the page, and nothing is answered until they do: "
          "say the fields are filled for them to check, never that the questions "
          "are answered")
"""What `answer` says when it fills, so a chat tells the user what is so."""


def relay(space, at, answers):
    """A chat's answers to the form `at`, one text per question id, kept for
    the console to fill its fields with, as *from the chat* (ADR 0034,
    decision 5). Approves nothing and starts nothing. Refused, in plain words,
    unless `at` waits and every id is one of its questions."""
    waiting = next((f for f in last_run.forms(space) if f["id"] == at), None)
    if waiting is None:
        return {"filled": False, "said": f"no form {at} waits in this space: it was "
                                         f"approved, or never asked. status says what waits"}
    ids = [q["id"] for q in waiting["questions"]]
    if not isinstance(answers, dict) or not answers:
        return {"filled": False, "said": f"answer one text per question id: {', '.join(ids)}"}
    for qid, text in answers.items():
        if qid not in ids:
            return {"filled": False, "said": f"{qid} is not one of its questions: "
                                             f"{', '.join(ids)}"}
        if not isinstance(text, str) or not text.strip():
            return {"filled": False, "said": f"{qid}'s answer is the user's words, as text"}
    relays = store.load(relayed(space), {})
    store.save(relayed(space), {**relays, at: {**relays.get(at, {}),
                                               **{q: t.strip() for q, t in answers.items()}}})
    return {"filled": True, "said": f"filled {len(answers)} field"
                                    f"{'s' if len(answers) > 1 else ''} as from the chat; "
                                    + FILLED}


def relayed(space):
    return space_lib.layout(space).dot / RELAYED


def filled(space, at, questions, fields):
    """The form's fields with what a chat filled: a later relay replaces an
    earlier one, and one identical to Claude's guess stays Claude's guess,
    since the agreement says nothing the page can check (ADR 0034, decision
    3). A field the person edited is theirs, and the page keeps it."""
    relays = store.load(relayed(space), {}).get(at) or {}
    kept = []
    for n, (q, f) in enumerate(zip(questions, fields), 1):
        text = relays.get(f"q{n}")
        if text is not None:
            guess = text == q["suggested"]
            f = {**f, "text": text, "source": "guess" if guess else "chat"}
        kept.append(f)
    return kept


def forget(space, at):
    """A form approved: what a chat filled in it is spent."""
    relays = store.load(relayed(space), {})
    if at in relays:
        store.save(relayed(space), {k: v for k, v in relays.items() if k != at})
