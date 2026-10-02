#!/usr/bin/env python3
"""Per-iteration token accounting for a Contour session.

Reads the Claude Code transcript for this project and reports what each
iteration cost, where an iteration is one user prompt and every assistant
message and tool call it caused.

Usage:
    tools/tokens.py              # current project, latest session
    tools/tokens.py --all        # every session for this project
    tools/tokens.py --session ID
    tools/tokens.py --json
"""
import argparse, json, os, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from console import spend
from lib.space import transcripts as transcript_dir

# Wrappers the CLI injects around a prompt; none of them are what the user typed.
NOISE = re.compile(
    r"<(ide_opened_file|ide_selection|system-reminder|local-command-stdout|"
    r"command-name|command-message|command-args|pasted_content)\b.*?"
    r"(</\1>|$)", re.S)

# What a turn cost, and what the SDK's usage keys are called, both come from
# `console/spend.py` — the module the console weighs a turn with for the page.
# Nothing here re-expresses either. One definition, because a run read here and
# watched there must not come out as two prices, and a key the SDK renames must
# not break one reader while silently miscounting the other (ADR 0019,
# decision 37).


def load(path: Path):
    for line in path.open():
        line = line.strip()
        if line:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def prompt_text(msg):
    """Return (label, n_images) for a real user prompt, or None."""
    content = msg.get("message", {}).get("content")
    if isinstance(content, str):
        blocks = [{"type": "text", "text": content}]
    elif isinstance(content, list):
        blocks = content
    else:
        return None
    if any(b.get("type") == "tool_result" for b in blocks):
        return None  # tool output, not a prompt
    images = sum(1 for b in blocks if b.get("type") == "image")
    text = " ".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    raw = text
    text = " ".join(NOISE.sub(" ", text).split())
    if not text:
        # A slash command carries its payload inside the wrapper tags; name it
        # rather than dropping the iteration and losing its cost.
        m = re.search(r"<command-name>/?([^<]+)</command-name>", raw)
        if m:
            text = "/" + m.group(1).strip()
        elif raw.strip():
            text = " ".join(raw.split())
    if not text and not images:
        return None
    return text[:58] or f"<{images} image(s)>", images


def iterations(events):
    """Group assistant usage under the user prompt that triggered it."""
    out, cur = [], None
    for e in events:
        t = e.get("type")
        if t == "user" and not e.get("isMeta"):
            p = prompt_text(e)
            if p:
                cur = {
                    "prompt": p[0], "images": p[1], "time": e.get("timestamp", ""),
                    "branch": e.get("gitBranch", ""), "turns": 0,
                    **{k: 0 for k in spend.FIGURES}, "thinking": 0, "tools": 0,
                }
                out.append(cur)
        elif t == "assistant" and cur is not None:
            m = e.get("message", {})
            u = m.get("usage", {}) or {}
            cur["turns"] += 1
            # Translated by the console's own reader, so the four figures mean
            # here exactly what they mean on the page — including a figure the
            # SDK sends as `null` rather than leaving out, which is nothing
            # spent and not a crash.
            for k, n in spend.counts(u).items():
                cur[k] += n
            cur["thinking"] += spend.thinking(u)
            cur["tools"] += sum(
                1 for b in m.get("content", []) if isinstance(b, dict)
                and b.get("type") == "tool_use"
            )
    out = [i for i in out if i["turns"]]
    for it in out:
        it["weighted"] = spend.weigh(it)
    return out


def console_runs(project: Path):
    """The console's own runs for this project, as iterations.

    A run is one prompt and every turn it caused, which is what an iteration has
    always meant here — so a console run and a terminal one land in one table in
    one set of units, and the second stated priority is served by one number
    (ADR 0019, decision 37).
    """
    out = {}
    for turn in spend.load(project):
        it = out.setdefault(turn.get("run", "?"), {
            "prompt": (turn.get("prompt") or turn.get("run", "?"))[:58],
            "images": 0,
            "time": turn.get("at", ""), "branch": "console", "turns": 0,
            **{k: 0 for k in spend.FIGURES}, "thinking": 0, "tools": 0,
            # How many gates the run stopped at, and what the turns after one
            # cost. A gate buys a turn of re-explanation, and this is the figure
            # that makes tuning the ask-list a decision rather than a mood.
            "gates": 0, "after_gates": 0,
        })
        it["turns"] += 1
        for k in spend.FIGURES:
            it[k] += turn.get(k, 0)
        it["gates"] = max(it["gates"], turn.get("gates", 0))
        if turn.get("gates", 0):
            it["after_gates"] += spend.weigh(turn)
    for it in out.values():
        it["weighted"] = spend.weigh(it)
    return list(out.values())


def human(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)


def report(its, name):
    print(f"\n{name}  —  {len(its)} iterations")
    print(f"{'#':>3} {'branch':<10} {'turns':>5} {'tool':>4} "
          f"{'fresh':>7} {'cached':>7} {'written':>7} {'out':>7} {'weighted':>8}  prompt")
    print("-" * 118)
    for i, it in enumerate(its, 1):
        tag = it["prompt"] + (f"  [{it['images']} img]" if it["images"] else "")
        print(f"{i:>3} {it['branch'][:10]:<10} {it['turns']:>5} {it['tools']:>4} "
              f"{human(it['input']):>7} {human(it['cache_read']):>7} "
              f"{human(it['cache_write']):>7} {human(it['output']):>7} "
              f"{human(it['weighted']):>8}  {tag}")
    tot = {k: sum(i[k] for i in its) for k in
           ("input", "cache_read", "cache_write", "output", "thinking", "weighted")}
    print("-" * 118)
    print(f"{'':>3} {'TOTAL':<10} {sum(i['turns'] for i in its):>5} "
          f"{sum(i['tools'] for i in its):>4} "
          f"{human(tot['input']):>7} {human(tot['cache_read']):>7} "
          f"{human(tot['cache_write']):>7} {human(tot['output']):>7} "
          f"{human(tot['weighted']):>8}")
    print(f"\n  thinking tokens: {human(tot['thinking'])} of {human(tot['output'])} output")
    gates = sum(i.get("gates", 0) for i in its)
    if gates:
        # Only where there were gates. A line saying *0 gates, 0 weighted* on
        # every terminal report is furniture, and furniture is what stops being
        # read (ADR 0019).
        after = sum(i.get("after_gates", 0) for i in its)
        print(f"  gates: {gates}, and {after} weighted spent in the turns after "
              f"one — the ask-list is what shortens this")
    print(f"  weighted = fresh + {spend.CACHE_READ_MULT:g}*cached "
          f"+ {spend.CACHE_WRITE_MULT:g}*written + {spend.OUTPUT_MULT:g}*out "
          f"(relative units, not dollars — use /cost for billing)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=os.getcwd())
    ap.add_argument("--session")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    project = Path(a.project).resolve()
    # The console's runs first, because a space may have those and no transcript
    # at all: the console is a second way of working and the accounting has to
    # cover it whether or not anyone has also worked here from a terminal.
    console = console_runs(project)
    d = transcript_dir(project)
    if not d.is_dir():
        if not console:
            sys.exit(f"no transcripts at {d}")
        d = None
    files = sorted(d.glob("*.jsonl"), key=lambda p: p.stat().st_mtime) if d else []
    if a.session:
        files = [p for p in files if p.stem.startswith(a.session)]
    elif not a.all:
        files = files[-1:]
    if not files and not console:
        sys.exit("no matching session")

    payload = {}
    if console:
        payload["console"] = console
        if not a.json:
            report(console, "console runs")
    for f in files:
        its = iterations(load(f))
        if not its:
            continue
        payload[f.stem] = its
        if not a.json:
            report(its, f.stem[:8])
    if a.json:
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
