"""The launcher's commands, as data (issue 24).

One row per subcommand, saying what it takes and what it needs before it may
run. `lib/cli.py` applies the columns in one place and resolves each row's
handler by name; this module is data only and imports nothing from it, because
`lib/intent.py` reads the table too and is deliberately three imports wide —
the console consults it on every call and must not acquire the launcher's
dispatcher by the back door.

The columns:

    name      what is typed after `contour`
    arity     how many words may follow it, `(least, most)`; `most` is None
              for as many as are given
    space     whether it must be run inside a model space (ADR 0015)
    holds     whether it takes the space's hold for as long as it runs. Open
              question 11 decided this per command, and a column is how that
              decision stays visible: `canvas` and `mark` holding nothing is
              a `False` somebody wrote, not an arm somebody forgot
    category  the intent a call to it carries, for the console's gate
              (ADR 0019, decision 22), or None
    usage     `(arguments, help)` lines for `contour --help`, which is
              rendered from them — so a command cannot be undocumented and a
              removed one cannot linger
    handler   the name of the function in `lib/cli.py` that runs it
"""
from collections import namedtuple

Command = namedtuple("Command", "name arity space holds category usage handler")

ANY = (1, None)
NONE = (0, 0)

TABLE = (
    Command("check", NONE, True, True, "build",
            (("check", "build + verify, and redraw the sheet"),), "on_build"),
    Command("render", NONE, True, True, "build",
            (("render", "4-view sheet -> sheet.png, + mask, + mark badges"),), "on_build"),
    Command("export", NONE, True, True, "build",
            (("export", ".glb + round-trip re-measure"),), "on_build"),
    Command("filmstrip", (0, 1), True, True, None,
            (("filmstrip [clip]", "a clip as six side and six front frames -> "
                                  "out/filmstrip.png"),), "on_filmstrip"),
    Command("api", ANY, False, False, None,
            (("api <symbol>...", "real signature from the installed Blender"),), "on_api"),
    Command("measure", ANY, True, False, None,
            (("measure <ref> ...", "real pixel geometry from a reference image"),
             ("measure --span <m>", "read the distance two pins on a reference mean"),
             ("measure <ref> --runs A,B", "draw an agent span between two runs of a scanline"),
             ("measure <ref> --extent across|up", "draw an agent span across the silhouette or a colour"),
             ("measure --again <m>", "ask a snapped span's question again"),
             ("measure <ref> --by-eye --from X,Y --to X,Y",
              "draw an agent span by eye, where nothing snaps"),
             ("measure --standing <m>", "say whether a span's number may be proposed")),
            "on_measure"),
    Command("worksheet", NONE, True, False, None,
            (("worksheet", "every span drawn onto its reference -> worksheet.png"),),
            "on_worksheet"),
    Command("canvas", NONE, True, False, None,
            (("canvas", "the sheet and the references in a browser, to mark on"),),
            "on_canvas"),
    Command("resolve", NONE, True, True, None,
            (("resolve", "anchor marks against this build, before it changes"),),
            "on_resolve"),
    Command("mark", ANY, True, False, None,
            (('mark --part <p> "..."', "pin a finding on the sheet, for the user to see"),),
            "on_mark"),
    Command("run", ANY, True, True, None,
            (("run <cmd>...", "hold this space for one run, then release it"),), "on_run"),
    Command("selftest", NONE, False, False, None,
            (("selftest", "fixture pipeline test"),), "on_selftest"),
    Command("install-hooks", NONE, False, False, None,
            (("install-hooks", "install the pre-push guard (ADR 0011)"),),
            "on_install_hooks"),
    Command("init", (1, 5), False, False, None,
            (("init <name> [--to <dir>]", "create a model space here, or in <dir>; --new "
                                          "refuses an existing directory, --json says "
                                          "it for a client"),), "on_init"),
    Command("doctor", NONE, True, False, None,
            (("doctor", "is this space in step with the toolkit"),), "on_doctor"),
    Command("update", (0, 2), True, False, None,
            (("update", "bring this space's rules in step with the toolkit, where "
                        "nobody edited them; --dry-run says what it would do, --json "
                        "says it for a client"),), "on_update"),
    Command("migrate-marks", NONE, True, False, None,
            (("migrate-marks", "rewrite this space's marks into one spelling"),),
            "on_migrate_marks"),
    Command("spaces", (0, 1), False, False, None,
            (("spaces [name]", "list model spaces, or print one's path"),
             ("spaces --json", "the same list and its health, for a client to read")),
            "on_spaces"),
    Command("mcp", (0, 1), False, False, None,
            (("mcp", "the connector: Claude Desktop reads the spaces over stdio"),
             ("mcp --config", "the block to paste into Desktop's config; writes nothing")),
            "on_mcp"),
    Command("lobby", (0, 2), False, False, None,
            (("lobby", "every space on this machine, on one page"),
             ("lobby --create [name]", "the same, opened on its create form")),
            "on_lobby"),
    Command("rename", (1, 3), True, False, "spec-write",
            (("rename <name>", "propose renaming this space; --yes does it, --json "
                               "says it for a client"),), "on_rename"),
    Command("delete", (1, 3), True, False, "ref-write",
            (("delete <name>", "propose deleting this space; --yes deletes it, leaving "
                               "a bundle, --json says it for a client"),), "on_delete"),
    Command("restore", (1, 4), False, False, None,
            (("restore <id> [--to <dir>]", "clone a deleted space back from its bundle; "
                                           "--json says it for a client"),), "on_restore"),
    Command("purge", (1, 3), False, False, "ref-write",
            (("purge <id>", "propose removing a deleted space's bundle; --yes removes "
                            "it for good, --json says it for a client"),), "on_purge"),
    Command("intents", NONE, False, False, None,
            (("intents", "the call categories a gate can ask about"),), "on_intents"),
    Command("asks", (0, 3), False, False, None,
            (("asks", "what this space lets through, and what asks"),
             ("asks --always build", "let builds through in this space without asking; "
                                     "for the page, not the agent"),
             ("asks --undo <category>", "ask about it again in this space; --json says "
                                        "it for a client")), "on_asks"),
    Command("hook", ANY, False, False, None,
            (("hook <name>", "run a guard; for hooks to call, not you"),), "on_hook"),
)
