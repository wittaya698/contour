"""Blender-side dispatcher. Run only through ./contour (ADR 0008).

    blender --background --python lib/entry.py -- <command> [args]

Each command lives in lib/cmd_<command>.py and exposes run(args) -> report, where
report is {"ok": bool, "lines": [str, ...]}. Anything a command prints goes to the
log; only the report reaches the conversation.
"""
import importlib
import json
import os
import sys
import traceback

ROOT = os.environ["CONTOUR_ROOT"]
sys.path.insert(0, ROOT)


def write_report(rep):
    with open(os.environ["CONTOUR_REPORT"], "w") as f:
        json.dump(rep, f)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    cmd, args = argv[0], argv[1:]
    try:
        rep = importlib.import_module(f"lib.cmd_{cmd}").run(args)
    except BaseException:
        tb = traceback.format_exc().strip().splitlines()
        rep = {"ok": False, "lines": ["FAIL exception", *tb[-10:]]}
    write_report(rep)


main()
