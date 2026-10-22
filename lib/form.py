"""The agent's questions, as a form the person approves (ADR 0034).

Standard library only, and in `lib/`: the console asks with it, and what was
approved is read back by the half that writes an anchor span's question
(issue 148), which never imports the console.
"""
import time

from lib import space as space_lib, store

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


def fields(questions):
    """The form as the page first shows it: every field filled with Claude's
    guess, and the basis under it (ADR 0034, decision 2)."""
    return [{"question": q["question"], "text": q["suggested"], "source": "guess",
             "basis": q["basis"], **({"is_size": True} if q.get("is_size") else {})}
            for q in questions]


def source(question, text):
    """Where an approved field's text came from: Claude's guess if it still
    reads as suggested, and the person's otherwise (ADR 0034, decision 3)."""
    return "guess" if text == question["suggested"] else "yours"


def answered(questions, texts):
    """The form as approved: each question, its answer, and the answer's
    source. A field the page sent nothing for is the guess it was filled
    with."""
    texts = list(texts) + [None] * len(questions)
    return [{"question": q["question"], "answer": q["suggested"] if t is None else t,
             "source": source(q, q["suggested"] if t is None else t),
             **({"is_size": True} if q.get("is_size") else {})}
            for q, t in zip(questions, texts)]


TOLD = {"guess": "Claude's guess, approved", "chat": "from the chat", "yours": "yours"}
"""An answer's source, as the agent is told it: a guess approved is still a
guess, and is named as one wherever it is used (ADR 0034, decision 4)."""


def told(answers):
    """The approved form, as the agent reads it: each question, and its answer
    with where it came from."""
    return "\n".join(f"{a['question']}\n  {a['answer']} ({TOLD[a['source']]})"
                     for a in answers)


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
