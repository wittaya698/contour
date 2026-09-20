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

# Wrappers the CLI injects around a prompt; none of them are what the user typed.
NOISE = re.compile(
    r"<(ide_opened_file|ide_selection|system-reminder|local-command-stdout|"
    r"command-name|command-message|command-args|pasted_content)\b.*?"
    r"(</\1>|$)", re.S)

# Anthropic cache pricing multipliers, relative to a normal input token.
CACHE_READ_MULT = 0.10
CACHE_WRITE_MULT = 1.25
# Output tokens cost more than input; this ratio is only used for the
# single "weighted" column, to keep one comparable number per iteration.
OUTPUT_MULT = 5.0


def transcript_dir(project: Path) -> Path:
    slug = "-" + str(project).lstrip("/").replace("/", "-")
    return Path.home() / ".claude" / "projects" / slug


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
                    "input": 0, "cache_read": 0, "cache_write": 0,
                    "output": 0, "thinking": 0, "tools": 0,
                }
                out.append(cur)
        elif t == "assistant" and cur is not None:
            m = e.get("message", {})
            u = m.get("usage", {})
            cur["turns"] += 1
            cur["input"] += u.get("input_tokens", 0)
            cur["cache_read"] += u.get("cache_read_input_tokens", 0)
            cur["cache_write"] += u.get("cache_creation_input_tokens", 0)
            cur["output"] += u.get("output_tokens", 0)
            cur["thinking"] += u.get("output_tokens_details", {}).get("thinking_tokens", 0)
            cur["tools"] += sum(
                1 for b in m.get("content", []) if isinstance(b, dict)
                and b.get("type") == "tool_use"
            )
    out = [i for i in out if i["turns"]]
    for it in out:
        it["weighted"] = round(
            it["input"]
            + it["cache_read"] * CACHE_READ_MULT
            + it["cache_write"] * CACHE_WRITE_MULT
            + it["output"] * OUTPUT_MULT
        )
    return out


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
    print("  weighted = fresh + 0.10*cached + 1.25*written + 5*out "
          "(relative units, not dollars — use /cost for billing)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=os.getcwd())
    ap.add_argument("--session")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    d = transcript_dir(Path(a.project).resolve())
    if not d.is_dir():
        sys.exit(f"no transcripts at {d}")
    files = sorted(d.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    if a.session:
        files = [p for p in files if p.stem.startswith(a.session)]
    elif not a.all:
        files = files[-1:]
    if not files:
        sys.exit("no matching session")

    payload = {}
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
