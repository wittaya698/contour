"""Judge a built scene against its spec (ADR 0002, 0005).

The path ADR 0002 and ADR 0009 name, and what is left of it once the judgement
moved to `lib/checks.py` and the gather to `lib/measure.py` (ADR 0020): `run`
gathers a measurement and hands it to the checks, and `report` and `stats` turn
the verdicts into the terse lines ADR 0005 budgets.

The spec is the definition of correct and nothing here reads it directly. Every
check returns {"id", "ok", "info", "msg"}: `info` is the compact reading shown
on a pass, `msg` the detail shown on a failure. A spec field this toolkit cannot
enforce FAILS as unsupported. It is never skipped, because a silently ignored
constraint is the same failure as a weakened one.

This file imports no Blender at module level — the gather it needs is imported
inside `run`. That is what lets `report` and `stats` be tested at all, which is
where ADR 0005's token budget becomes checkable rather than merely intended.
"""
from lib import checks


def run(spec, variant, only=None):
    """All checks against the current scene -> list of results.

    The one call that needs Blender, and the only one: it gathers a measurement
    and everything after it is arithmetic. `only` narrows to a set of check ids
    (the export round-trip re-measures a subset).
    """
    from lib import measure

    return checks.run(spec, variant, measure.scene(), only=only)


def stats(spec, results):
    """Compact readings for the report and the commit-message stamp."""
    return {r["id"]: r["info"] for r in results}


def report(variant, results):
    """Results -> terse report lines (ADR 0005: ~50 tokens on green)."""
    n, ok = len(results), sum(r["ok"] for r in results)
    fails = [r for r in results if not r["ok"]]
    info = {r["id"]: r["info"] for r in results}
    if fails:
        lines = [f"{variant} FAIL {ok}/{n}"]
        lines += [f"  FAIL {r['id']:<9} {r['msg']}" for r in fails]
        return lines
    stamp = f"verify {ok}/{n}"
    if "tris" in info:
        stamp += f" | tris {info['tris'].split('/')[0]}"
    if "height" in info:
        stamp += f" | height {info['height'].split('.')[0]}mm"
    rest = [f"{k} {info[k]}" for k in ("width", "depth", "quads", "parts", "mat_slots", "origin",
                                       "seams", "pivots")
            if k in info]
    return [f"{variant} PASS  {stamp}", "  " + " | ".join(rest)] if rest else [f"{variant} PASS  {stamp}"]
