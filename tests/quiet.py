"""No notification on the screen of whoever runs the suite, held by importing
this (issue 91).

A run nobody was watching posts a system notification when it parks (ADR 0027,
decision 7), and the suite parks a good many of them. `$CONTOUR_NOTIFIER` set
to `true` posts nothing, by the hatch `lib/notify.py` reads; a test about what
is posted points it at a recorder of its own. Imported by `test_console` and
`test_run_record`, which every test that starts a run builds on.
"""
import os

os.environ.setdefault("CONTOUR_NOTIFIER", "true")
