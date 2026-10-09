"""The connector, as Claude Desktop meets it (ADR 0024, issue 57).

No Desktop is needed: the protocol is newline-delimited JSON-RPC over stdio, so
a test writes the lines Desktop would write and reads what comes back. Most of
these drive `connector.serve` over in-memory pipes; the ones that matter end to
end run `contour mcp` as Desktop runs it.
"""
import base64
import io
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTOUR = ROOT / "contour"
sys.path.insert(0, str(ROOT))

from lib import connector  # noqa: E402
from lib import marks, views  # noqa: E402
from test_launcher import stub_blender  # noqa: E402
from executables import executable  # noqa: E402


def talk(*messages, tools=None):
    """What the connector says back to these messages, one dict per answer."""
    said = io.StringIO()
    connector.serve(io.StringIO("".join(
        (m if isinstance(m, str) else json.dumps(m)) + "\n" for m in messages)),
        said, tools or {})
    return [json.loads(line) for line in said.getvalue().splitlines()]


def call(n, method, **params):
    return {"jsonrpc": "2.0", "id": n, "method": method, "params": params}


class ProtocolTest(unittest.TestCase):
    def test_initialize_names_the_connector_and_offers_tools_only(self):
        """Tools, and no resources, prompts or sampling: three methods is all
        the connector speaks (ADR 0024, decision 1)."""
        [got] = talk(call(1, "initialize", protocolVersion="2025-06-18",
                          capabilities={}, clientInfo={"name": "t", "version": "0"}))
        self.assertEqual(got["id"], 1)
        self.assertEqual(got["result"]["serverInfo"]["name"], "contour")
        self.assertEqual(got["result"]["capabilities"], {"tools": {}})
        self.assertEqual(got["result"]["protocolVersion"], "2025-06-18")

    def test_the_instructions_describe_the_connector_in_five_lines(self):
        """ADR 0024, decision 4: it reads and opens and changes nothing; a spec changes
        inside its space, from a span on the canvas; the console is where the
        model changes. ADR 0025, decision 11: a pasted picture is answered with
        the lobby's create form, where the file can be dropped, and never by
        asking for a path; and what the connector says is read as a page reads."""
        [got] = talk(call(1, "initialize", protocolVersion=connector.LATEST))
        said = got["result"]["instructions"].splitlines()
        self.assertEqual(len(said), 5)
        self.assertIn("changes nothing", said[0])
        self.assertIn("span", said[1])
        self.assertIn("canvas", said[1])
        self.assertIn("console", said[2])
        self.assertIn("pasted", said[3])
        self.assertIn("create form", said[3])
        self.assertNotIn("ask for the file's path", said[3])
        self.assertIn("plain words", said[4])
        self.assertIn("status", said[4])

    def test_the_instructions_restate_none_of_the_rules(self):
        """Facts about the connector cannot drift from `CLAUDE.md`, because they
        are not a copy of it. No line of one may appear in the other."""
        [got] = talk(call(1, "initialize", protocolVersion=connector.LATEST))
        said = got["result"]["instructions"]
        rules = (ROOT / "CLAUDE.md").read_text()
        for line in said.splitlines():
            self.assertNotIn(line.strip(), rules)
        for line in rules.splitlines():
            line = line.strip(" -*0123456789.")
            if len(line) > 20:
                self.assertNotIn(line, said)

    def test_any_other_method_is_method_not_found(self):
        """No resources, no prompts: asked for one, the connector says so in
        the protocol's own error, not a traceback."""
        [got] = talk(call(7, "resources/list"))
        self.assertEqual(got["id"], 7)
        self.assertEqual(got["error"]["code"], -32601)
        self.assertNotIn("result", got)

    def test_a_notification_is_never_answered(self):
        """`notifications/initialized` carries no id, and JSON-RPC answers
        nothing that has none — known method or not."""
        self.assertEqual(talk({"jsonrpc": "2.0", "method": "notifications/initialized"},
                              {"jsonrpc": "2.0", "method": "notifications/whatever"}), [])

    def test_a_line_that_is_not_json_is_a_parse_error_and_the_next_is_answered(self):
        """One bad line does not end the session."""
        got = talk("{not json", call(2, "tools/list"))
        self.assertEqual(got[0]["error"]["code"], -32700)
        self.assertIsNone(got[0]["id"])
        self.assertEqual(got[1]["id"], 2)


class ToolsTest(unittest.TestCase):
    READING = {"roots": ["/r"], "spaces": [{"name": "beaky"}], "deleted": []}
    TOOLS = {"spaces": lambda args: ToolsTest.READING}

    def test_spaces_is_listed_with_a_schema_that_takes_nothing(self):
        [got] = talk(call(1, "tools/list"), tools=self.TOOLS)
        [tool] = got["result"]["tools"]
        self.assertEqual(tool["name"], "spaces")
        self.assertTrue(tool["description"])
        self.assertEqual(tool["inputSchema"], {"type": "object", "properties": {}})

    def test_calling_a_tool_returns_its_reading_as_text(self):
        [got] = talk(call(1, "tools/call", name="spaces", arguments={}),
                     tools=self.TOOLS)
        [content] = got["result"]["content"]
        self.assertEqual(content["type"], "text")
        self.assertEqual(json.loads(content["text"]), self.READING)
        self.assertIs(got["result"]["isError"], False)

    def test_calling_a_tool_that_does_not_exist_is_invalid_params(self):
        """Desktop only calls what it was listed, so this is a protocol error,
        not a tool's failure."""
        [got] = talk(call(1, "tools/call", name="build", arguments={}),
                     tools=self.TOOLS)
        self.assertEqual(got["error"]["code"], -32602)

    def test_a_tool_that_raises_is_a_tool_error_and_the_session_goes_on(self):
        """A space whose marker cannot be read is a finding for the chat, not
        a connector Desktop has to restart."""
        def broken(args):
            raise OSError("marker unreadable")
        got = talk(call(1, "tools/call", name="spaces", arguments={}),
                   call(2, "tools/list"), tools={"spaces": broken})
        self.assertIs(got[0]["result"]["isError"], True)
        self.assertIn("marker unreadable", got[0]["result"]["content"][0]["text"])
        self.assertEqual(got[1]["id"], 2)


class SpacesCase(unittest.TestCase):
    """`contour mcp` run as Desktop runs it, over spaces `contour init` made in
    a directory `$CONTOUR_SPACES` points at, as `SpacesTest` does."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.home = Path(tempfile.mkdtemp()).resolve()
        self.env = dict(os.environ, CONTOUR_SPACES=str(self.tmp),
                        CONTOUR_HOME=str(self.home))

    def contour(self, *args, stdin=""):
        return subprocess.run([sys.executable, str(CONTOUR), *args], input=stdin,
                              cwd=str(self.tmp), env=self.env,
                              capture_output=True, text=True, timeout=60)


class LauncherTest(SpacesCase):
    def test_spaces_says_what_contour_spaces_json_says(self):
        """One reading behind both, so a chat and a terminal cannot disagree
        about which spaces exist (ADR 0024, decision 3)."""
        for name in ("alpha", "beta"):
            self.assertEqual(self.contour("init", name).returncode, 0)
        r = self.contour("mcp", stdin="".join(json.dumps(m) + "\n" for m in (
            call(1, "initialize", protocolVersion=connector.LATEST),
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            call(2, "tools/list"),
            call(3, "tools/call", name="spaces", arguments={}))))
        self.assertEqual(r.returncode, 0, r.stderr)
        _, listed, called = [json.loads(l) for l in r.stdout.splitlines()]
        self.assertEqual([t["name"] for t in listed["result"]["tools"]],
                         [t["name"] for t in connector.TOOLS],
                         "every tool defined is served")
        said = json.loads(called["result"]["content"][0]["text"])
        self.assertEqual(said, json.loads(self.contour("spaces", "--json").stdout))
        self.assertEqual([s["name"] for s in said["spaces"]], ["alpha", "beta"])

    def config(self, *path):
        """`contour mcp --config` with only these directories on PATH, and a
        HOME of its own so anything it wrote there would show."""
        self.env.update(PATH=os.pathsep.join(map(str, path)), HOME=str(self.home))
        return self.contour("mcp", "--config")

    def test_config_names_the_symlink_and_writes_nothing(self):
        """ADR 0024, decision 7: the link, not the checkout, so moving the toolkit is
        still a relink; and the block is printed, because Desktop's config is
        the user's file."""
        bin_ = Path(tempfile.mkdtemp()).resolve()
        (bin_ / "contour").symlink_to(CONTOUR)
        r = self.config(bin_, "/usr/bin", "/bin")
        self.assertEqual(r.returncode, 0, r.stderr)
        server = json.loads(r.stdout)["mcpServers"]["contour"]
        self.assertEqual(server, {"command": str(bin_ / "contour"), "args": ["mcp"]})
        self.assertNotIn(str(ROOT), r.stdout)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_config_with_no_link_on_the_path_says_how_to_make_one(self):
        """The block still names where the README puts the link, and the
        missing link is said, not papered over with the checkout's path."""
        r = self.config("/usr/bin", "/bin")
        self.assertEqual(r.returncode, 1)
        server = json.loads(r.stdout)["mcpServers"]["contour"]
        self.assertEqual(server["command"], str(self.home / ".local/bin/contour"))
        self.assertIn("ln -s", r.stderr)


class InSpaceCase(SpacesCase):
    """One space, `alpha`, that a stubbed Blender can build in. A chat stands
    in no directory, so every call names its space."""

    def setUp(self):
        super().setUp()
        self.assertEqual(self.contour("init", "alpha").returncode, 0)
        self.space = self.tmp / "alpha"
        self.env["BLENDER"] = str(stub_blender(self.tmp))

    def run_in(self, *args, **stub):
        if stub:
            self.env["BLENDER"] = str(stub_blender(self.tmp, **stub))
        return subprocess.run([sys.executable, str(CONTOUR), *args],
                              cwd=str(self.space), env=self.env,
                              capture_output=True, text=True, timeout=60)

    def tool(self, name, **arguments):
        """One tool call over `contour mcp`: its text, parsed if it is a
        reading, and whether it was an error."""
        r = self.contour("mcp", stdin=json.dumps(
            call(1, "tools/call", name=name, arguments=arguments)) + "\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        got = json.loads(r.stdout)["result"]
        text = got["content"][0]["text"]
        return (text if got["isError"] else json.loads(text)), got["isError"]


class ReadingTest(InSpaceCase):
    """`status` and `log` (issue 59)."""

    def test_status_is_the_last_checks_verdict_after_a_later_stage(self):
        """The filmstrip ran last and its log says so; the verdict is the check's."""
        self.assertEqual(self.run_in("check", ok=False).returncode, 1)
        self.assertEqual(self.run_in("filmstrip", ok=True).returncode, 0)
        said, failed = self.tool("status", space="alpha")
        self.assertFalse(failed, said)
        self.assertIs(said["verdict"]["ok"], False)
        self.assertEqual(said["verdict"]["lines"], ["stub ran build"])
        self.assertEqual(said["verdict"]["results"], [{"id": "height", "ok": False, "info": "1640.0", "msg": "height 1640.0mm, want 1700±5"}])

    def test_status_says_the_verdict_in_the_words_the_pages_use(self):
        """Beside the report lines, never instead of them: issue 66's sentences,
        from the one table the console's panel reads (ADR 0025, decision 11)."""
        self.run_in("check", ok=False)
        said, _ = self.tool("status", space="alpha")
        self.assertEqual(said["plain"]["line"], "1 thing doesn't match the spec")
        self.assertEqual(said["plain"]["failing"],
                         ["Height is 1640 mm; the spec wants 1700, give or take 5."])
        self.assertIn("results", said["verdict"])

    def test_status_on_a_held_space_says_the_verdict_is_from_before_the_run(self):
        """Asked from inside `contour run`, so the hold is a real one and alive:
        whatever the run is doing to `build.py`, the verdict has not seen it."""
        self.assertEqual(self.run_in("check").returncode, 0)
        r = subprocess.run(
            [sys.executable, str(CONTOUR), "run", sys.executable, str(CONTOUR), "mcp"],
            input=json.dumps(call(1, "tools/call", name="status",
                                  arguments={"space": "alpha"})) + "\n",
            cwd=str(self.space), env=self.env, capture_output=True, text=True,
            timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        said = json.loads(json.loads(r.stdout)["result"]["content"][0]["text"])
        self.assertIs(said["verdict"]["ok"], True, "the verdict is still given")
        self.assertIn("running run", said["held"])
        self.assertIn("from before", " ".join(said["said"]))

    def test_status_on_an_idle_space_holds_nothing(self):
        self.assertEqual(self.run_in("check").returncode, 0)
        said, _ = self.tool("status", space="alpha")
        self.assertIsNone(said["held"])
        self.assertEqual(said["said"], [])

    def test_status_counts_the_open_marks(self):
        (self.space / "marks.json").write_text(json.dumps([
            {"id": "m1", "view": "front", "pixel": [3, 4], "text": "too tall",
             "author": "user", "status": "open"},
            {"id": "m2", "view": "front", "pixel": [5, 6], "text": "fine now",
             "author": "user", "status": "closed"},
            {"id": "m3", "view": "side", "pixel": [7, 8], "text": "a gap",
             "author": "user", "status": "open"}]))
        said, _ = self.tool("status", space="alpha")
        self.assertEqual(said["marks"], 2)

    def test_status_counts_the_vetoes_git_does_not_hold_yet(self):
        """A veto reaches git with the change it prevented; until then it is at
        risk, and the number is the console's whole say about it (ADR 0019)."""
        vetoes = self.space / "vetoes.json"
        v1 = {"id": "v1", "tool": "Edit", "reason": "not that tolerance"}
        vetoes.write_text(json.dumps([v1]))
        git = ["git", "-C", str(self.space), "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run([*git, "add", "vetoes.json"], check=True)
        subprocess.run([*git, "commit", "-qm", "v1"], check=True)
        vetoes.write_text(json.dumps([v1, {"id": "v2", "tool": "Bash", "reason": "no"},
                                      {"id": "v3", "tool": "Edit", "reason": "no"}]))
        said, _ = self.tool("status", space="alpha")
        self.assertEqual(said["vetoes"], 2)

    def test_status_says_what_doctor_finds_out_of_step(self):
        """How each copy stands, the one answer `doctor` and `spaces` read, so
        the three cannot disagree about a copy (issue 83)."""
        said, _ = self.tool("status", space="alpha")
        self.assertEqual(said["doctor"], {"toolkit": "current", "behind": [],
                                          "edited": [], "missing": []})
        with open(self.space / "CLAUDE.md", "a") as f:
            f.write("\nmy own rule\n")
        (self.space / ".claude" / "settings.json").unlink()
        said, _ = self.tool("status", space="alpha")
        self.assertEqual(said["doctor"]["edited"], ["CLAUDE.md"])
        self.assertEqual(said["doctor"]["missing"], [".claude/settings.json"])
        self.assertEqual(said["doctor"]["behind"], [])

    def test_a_space_spaces_does_not_resolve_is_refused_in_its_words(self):
        said, failed = self.tool("status", space="nope")
        self.assertTrue(failed)
        self.assertIn(self.contour("spaces", "nope").stdout.strip(), said)
        said, failed = self.tool("status")
        self.assertTrue(failed, "no space named is no space resolved")
        self.assertIn("name a space", said)

    def test_log_is_the_tail_asked_for_and_names_the_stage(self):
        """A check's log is the build and the render after it; the stub says
        nothing, so the tail is the stage lines alone."""
        self.assertEqual(self.run_in("check").returncode, 0)
        said, failed = self.tool("log", space="alpha", lines=1)
        self.assertFalse(failed, said)
        self.assertEqual(said["stage"], "check")
        self.assertEqual(said["lines"], ["$ render"])
        said, _ = self.tool("log", space="alpha")
        self.assertEqual(said["lines"], ["$ build", "$ render"])
        self.assertEqual(said["said"], [])

    def test_a_log_a_later_stage_wrote_is_not_passed_off_as_the_checks(self):
        """The check went red and the filmstrip ran after it: what is in the log
        now is the filmstrip's, and is no cause of that red."""
        self.assertEqual(self.run_in("check", ok=False).returncode, 1)
        self.assertEqual(self.run_in("filmstrip", ok=True).returncode, 0)
        said, _ = self.tool("log", space="alpha")
        self.assertEqual(said["stage"], "filmstrip")
        self.assertIn("this log is from filmstrip, not the last check",
                      " ".join(said["said"]))

    def test_log_on_a_space_nothing_has_run_in_says_so(self):
        said, failed = self.tool("log", space="alpha")
        self.assertFalse(failed, said)
        self.assertIsNone(said["stage"])
        self.assertEqual(said["lines"], [])
        self.assertIn("nothing has run", " ".join(said["said"]))

    def test_log_asked_for_no_lines_gives_none(self):
        """`[-0:]` is the whole list; at most none is none."""
        self.assertEqual(self.run_in("check").returncode, 0)
        said, _ = self.tool("log", space="alpha", lines=0)
        self.assertEqual(said["lines"], [])

    def test_status_on_a_space_never_checked_says_so(self):
        """No verdict is not a green one."""
        said, failed = self.tool("status", space="alpha")
        self.assertFalse(failed, said)
        self.assertIsNone(said["verdict"])
        self.assertIn("never checked", " ".join(said["said"]))



class PictureTest(InSpaceCase):
    """`picture` (issue 60): an image Desktop shows, and which build it is of —
    the panel's comparison, so a chat and the console agree about it."""

    PNG = b"\x89PNG\r\n\x1a\nsome pixels"

    def picture(self, which):
        """The content blocks a `picture` call returns, and whether it failed."""
        r = self.contour("mcp", stdin=json.dumps(call(
            1, "tools/call", name="picture",
            arguments={"space": "alpha", "picture": which})) + "\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        got = json.loads(r.stdout)["result"]
        return got["content"], got["isError"]

    def drawn(self):
        """A build on disk and the sheet `render` drew of it."""
        here = self.space / "out"
        here.mkdir(exist_ok=True)
        (here / "alpha.blend").write_bytes(b"a blend")
        (self.space / "sheet.png").write_bytes(self.PNG)
        views.record(here / "views.json", [64, 64], [], here / "alpha.blend")

    def test_the_sheet_is_an_image_with_the_build_it_is_of(self):
        self.drawn()
        content, failed = self.picture("sheet")
        self.assertFalse(failed, content)
        image, text = content
        self.assertEqual(image["type"], "image")
        self.assertEqual(image["mimeType"], "image/png")
        self.assertEqual(base64.b64decode(image["data"]), self.PNG)
        said = json.loads(text["text"])
        self.assertEqual(said["build"], views.fingerprint(self.space / "out" / "alpha.blend"))
        self.assertIs(said["current"], True)

    def test_a_sheet_the_build_moved_past_says_it_is_not_current(self):
        self.drawn()
        drawn = views.fingerprint(self.space / "out" / "alpha.blend")
        (self.space / "out" / "alpha.blend").write_bytes(b"a later blend")
        content, _ = self.picture("sheet")
        said = json.loads(content[1]["text"])
        self.assertEqual(said["build"], drawn, "the build it is a picture of")
        self.assertIs(said["current"], False)
        self.assertIn("moved on", said["why"])

    def test_the_filmstrip_is_of_the_build_it_was_drawn_from(self):
        """Its build is in its pixels, which no reader below Blender can read,
        so the launcher writes it down as the filmstrip succeeds. The stub
        draws nothing; the PNG is laid down where Blender would have put it."""
        blend = self.space / "out" / "alpha.blend"
        blend.parent.mkdir()
        blend.write_bytes(b"a blend")
        self.assertEqual(self.run_in("filmstrip").returncode, 0)
        (self.space / "out" / "filmstrip.png").write_bytes(self.PNG)
        content, failed = self.picture("filmstrip")
        self.assertFalse(failed, content)
        self.assertEqual(base64.b64decode(content[0]["data"]), self.PNG)
        said = json.loads(content[1]["text"])
        self.assertEqual(said["build"], views.fingerprint(blend))
        self.assertIs(said["current"], True, said)
        blend.write_bytes(b"a later blend")
        said = json.loads(self.picture("filmstrip")[0][1]["text"])
        self.assertIs(said["current"], False)
        self.assertIn("moved on", said["why"])

    def test_the_worksheet_is_of_its_spans_and_says_when_they_moved(self):
        """Drawn from the references and the spans on them, not from a build:
        so no build is named, and what it can fall behind is the spans."""
        spans = self.space / "marks.json"
        marks.on_reference(spans, "front.png", [10, 20], "height", to=[10, 200])
        self.assertEqual(self.run_in("worksheet").returncode, 0)
        (self.space / "worksheet.png").write_bytes(self.PNG)
        content, failed = self.picture("worksheet")
        self.assertFalse(failed, content)
        self.assertEqual(base64.b64decode(content[0]["data"]), self.PNG)
        said = json.loads(content[1]["text"])
        self.assertIsNone(said["build"])
        self.assertIs(said["current"], True, said)
        marks.on_reference(spans, "front.png", [30, 20], "width", to=[90, 20])
        said = json.loads(self.picture("worksheet")[0][1]["text"])
        self.assertIs(said["current"], False)
        self.assertIn("contour worksheet", said["why"])

    def test_a_picture_never_drawn_says_so_and_nothing_renders(self):
        """The stub Blender writes down every stage it is asked for; no line
        there means nothing was started to answer."""
        for which in ("sheet", "filmstrip", "worksheet"):
            content, failed = self.picture(which)
            self.assertFalse(failed, content)
            [text] = content
            self.assertEqual(json.loads(text["text"])["said"], "not drawn yet")
        self.assertFalse((self.tmp / "stages").exists(), "Blender was started")



class SpecSpendTest(InSpaceCase):
    """`spec` and `spend` (issue 61): two readings, and nothing written."""

    def text(self, name):
        """The one text block a call returns, as it came, and whether it failed."""
        r = self.contour("mcp", stdin=json.dumps(call(
            1, "tools/call", name=name, arguments={"space": "alpha"})) + "\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        got = json.loads(r.stdout)["result"]
        [block] = got["content"]
        return block["text"], got["isError"]

    def test_spec_is_the_file_unchanged_and_then_the_pointer(self):
        """The pointer is what sends a chat arguing a tolerance to the canvas
        (ADR 0024, decision 4), and it is the instructions' own line."""
        spec = "revision: 3\nname: alpha\nheight: 600 ±20  # mm\n"
        (self.space / "spec.yaml").write_text(spec)
        said, failed = self.text("spec")
        self.assertFalse(failed, said)
        self.assertTrue(said.startswith(spec), "the spec, byte for byte")
        self.assertEqual(said[len(spec):].strip(),
                         connector.INSTRUCTIONS.splitlines()[1])

    def test_a_space_with_no_spec_yet_says_so(self):
        """`contour init` writes none: the spec is drafted in the console."""
        said, failed = self.text("spec")
        self.assertFalse(failed, said)
        self.assertTrue(said.startswith("no spec.yaml yet"), said)
        self.assertIn(connector.INSTRUCTIONS.splitlines()[1], said)


    def spent(self, run, prompt, *turns):
        """Turns recorded the way the console records them."""
        from console import spend
        for gates, usage in turns:
            spend.record(self.space, run, usage, gates, prompt)

    def test_spend_is_per_run_in_the_units_tokens_reports(self):
        """One accounting: what a chat is told a run cost is what `tools/tokens.py`
        prints for it, figure for figure (ADR 0019, decision 37)."""
        self.spent("r1", "why is the neck 269",
                   (0, {"input_tokens": 900, "cache_read_input_tokens": 20000,
                        "cache_creation_input_tokens": 3000, "output_tokens": 400}),
                   (1, {"input_tokens": 50, "cache_read_input_tokens": 24000,
                        "output_tokens": 120}))
        self.spent("r2", "widen the base",
                   (0, {"input_tokens": 10, "output_tokens": 5}))
        said, failed = self.text("spend")
        self.assertFalse(failed, said)
        runs = json.loads(said)["runs"]
        tokens = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "tokens.py"), "--project",
             str(self.space), "--json"], capture_output=True, text=True,
            env=dict(self.env, HOME=str(self.home)))
        reported = json.loads(tokens.stdout)["console"]
        self.assertEqual(len(runs), 2)
        for run, row in zip(runs, reported):
            for k in ("prompt", "turns", "input", "cache_read", "cache_write",
                      "output", "gates", "after_gates", "weighted"):
                self.assertEqual(run[k], row[k], k)
        self.assertEqual(runs[0]["turns"], 2)
        self.assertEqual(json.loads(said)["said"], [])

    def test_neither_reading_writes_anything_in_the_space(self):
        """Every file, its bytes and its time, before and after: the connector
        changes nothing in a space that exists (ADR 0024, decision 2)."""
        (self.space / "spec.yaml").write_text("revision: 1\n")
        self.spent("r1", "p", (0, {"input_tokens": 1}))

        def tree():
            return {p: (p.read_bytes(), p.stat().st_mtime_ns)
                    for p in self.space.rglob("*") if p.is_file()}
        before = tree()
        for name in ("spec", "spend"):
            self.assertFalse(self.text(name)[1])
        self.assertEqual(tree(), before)

    def test_spend_where_no_console_has_run_says_so(self):
        said, failed = self.text("spend")
        self.assertFalse(failed, said)
        said = json.loads(said)
        self.assertEqual(said["runs"], [])
        self.assertIn("no console has run", " ".join(said["said"]))


class PagesCase(InSpaceCase):
    """Pages a call starts and leaves to the user. `$BROWSER` writes down the
    URL each page tried to open, and the pid that tried, so no tab opens and
    the test can see the page it would have shown."""

    def setUp(self):
        super().setUp()
        self.opened = self.tmp / "opened"
        browser = executable(self.tmp / "browser",       # `opened` is beside it
                             '#!/bin/sh\necho "$PPID $1" >> "$(dirname "$0")/opened"\n')
        self.env.update(BROWSER=str(browser), CONTOUR_CONSOLE_PYTHON=sys.executable)
        self.addCleanup(self.close_pages)

    def close_pages(self):
        from lib import presence
        pids = {p["pid"] for p in presence.live(self.space)}
        if self.opened.exists():
            pids |= {int(l.split()[0]) for l in self.opened.read_text().splitlines()}
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

    def urls(self):
        """Each page's URL, once its browser has been asked to show it."""
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if self.opened.exists() and self.opened.read_text().strip():
                return [l.split()[1] for l in self.opened.read_text().splitlines()]
            time.sleep(0.1)
        self.fail("no page asked for a browser")

    def serving(self, url):
        """The page answers at its URL, so the process behind it is alive."""
        with urllib.request.urlopen(url, timeout=30) as r:
            self.assertEqual(r.status, 200)

    def assertSecretless(self, text, url):
        """No URL, no port, no token: nothing that reaches the page."""
        origin, token = url.split("/?")[0], url.split("t=")[1]
        for leak in ("http", origin, origin.rsplit(":", 1)[1], token):
            self.assertNotIn(leak, text)



class OpenTest(PagesCase):
    """`open` (issue 62): the page where the user acts, started and left to
    them."""

    def open(self, page, **more):
        """One `open` call, as raw text and as a reading."""
        r = self.contour("mcp", stdin=json.dumps(call(
            1, "tools/call", name="open", arguments={"page": page, **more})) + "\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        got = json.loads(r.stdout)["result"]
        [block] = got["content"]
        self.assertFalse(got["isError"], block["text"])
        return block["text"], json.loads(block["text"])

    def test_open_console_starts_a_console_that_outlives_the_connector(self):
        text, said = self.open("console", space="alpha")
        self.assertIsNone(said["refused"], said)
        [url] = self.urls()
        self.serving(url)
        self.assertSecretless(text, url)

    def test_open_console_refuses_as_the_lobby_does(self):
        """The same two refusals, word for word as `test_lobby_enter` reads
        them: a console already here (this process stands for it), and no
        environment to start one in."""
        from lib import presence
        with presence.present(self.space, "console"):
            _, said = self.open("console", space="alpha")
        self.assertIn("already open in a console", said["refused"])
        self.assertIn(str(os.getpid()), said["refused"])
        self.env["CONTOUR_CONSOLE_PYTHON"] = str(self.tmp / "no-python")
        _, said = self.open("console", space="alpha")
        self.assertIn("no console environment; make one", said["refused"])
        time.sleep(1)                         # long enough for one started anyway to show
        self.assertFalse(self.opened.exists(), "a page was opened anyway")

    def test_open_canvas_returns_and_the_canvas_outlives_the_connector(self):
        """Done is the user's, on the page: the call is answered while the
        canvas still waits for it."""
        (self.space / "sheet.png").write_bytes(PictureTest.PNG)
        text, said = self.open("canvas", space="alpha")
        self.assertIsNone(said["refused"], said)
        [url] = self.urls()
        self.serving(url)
        from lib import presence
        self.assertEqual([p["kind"] for p in presence.live(self.space)], ["canvas"])
        self.assertSecretless(text, url)

    def test_open_canvas_on_a_space_a_console_serves_is_refused(self):
        """A second page would be a second writer to `marks.json`, and the
        console's page can mark already."""
        from lib import presence
        (self.space / "sheet.png").write_bytes(PictureTest.PNG)
        with presence.present(self.space, "console"):
            _, said = self.open("canvas", space="alpha")
        self.assertEqual(said["refused"], "already open in a console; its page can mark")
        time.sleep(1)                         # long enough for one started anyway to show
        self.assertFalse(self.opened.exists(), "a canvas was opened anyway")

    def test_open_lobby_needs_no_space_and_outlives_the_connector(self):
        """Every space on one page: there is none to name."""
        text, said = self.open("lobby")
        self.assertIsNone(said["refused"], said)
        [url] = self.urls()
        self.serving(url)
        self.assertSecretless(text, url)
        self.assertEqual(self.lobby_listing(url), ["alpha"])

    def test_open_lobby_on_its_create_form_with_the_name_filled_in(self):
        """Where a pasted picture is answered: the form it can be dropped on
        (ADR 0025, decision 11). The name rides in the fragment, which the page
        reads and the server never sees."""
        text, said = self.open("lobby", create=True, name="oak-chair")
        self.assertIsNone(said["refused"], said)
        [url] = self.urls()
        self.assertTrue(url.endswith("#create=oak-chair"), url)
        self.serving(url.split("#")[0])
        self.assertSecretless(text, url.split("#")[0])

    def test_a_running_lobby_is_shown_again_on_its_create_form(self):
        """One lobby lists every space, so the second ask is the same tab
        shown again — on the form this time."""
        self.open("lobby")
        [first] = self.urls()
        self.open("lobby", create=True)
        deadline = time.monotonic() + 30
        while len(self.opened.read_text().splitlines()) < 2:
            self.assertLess(time.monotonic(), deadline, "the lobby was not shown again")
            time.sleep(0.1)
        again = self.opened.read_text().splitlines()[1].split()[1]
        self.assertEqual(again, first + "#create")

    def lobby_listing(self, url):
        """The names the lobby lists, asked as its page asks."""
        from lib.page import TOKEN_HEADER
        origin, token = url.split("/?")[0], url.split("t=")[1]
        req = urllib.request.Request(origin + "/spaces", headers={TOKEN_HEADER: token})
        with urllib.request.urlopen(req, timeout=30) as r:
            return [s["name"] for s in json.loads(r.read())["spaces"]]


class CreateTest(PagesCase):
    """`create` (issue 64): the lobby's create, plus references already on disk.
    The console it starts is the real one, with the scripted stand-in for an
    agent, which writes down the prompt it was begun on."""

    JPEG = b"\xff\xd8\xff\xe0 a photo of the front"

    def setUp(self):
        super().setUp()
        self.prompt = self.tmp / "prompt"
        self.env.update(
            CONTOUR_CONSOLE_AGENT=str(ROOT / "tests" / "agent_stand_in.py") + ":drive",
            CONTOUR_AGENT_SCRIPT=json.dumps([{"keep_prompt": str(self.prompt)}]))
        self.pictures = Path(tempfile.mkdtemp()).resolve()
        self.front = self.pictures / "front.jpg"
        self.front.write_bytes(self.JPEG)
        self.side = self.pictures / "side.png"
        self.side.write_bytes(PictureTest.PNG)
        self.space = self.tmp / "beta"      # whose pages `close_pages` closes
        self.coming = False                 # whether a console is starting on it

    def create(self, name, *paths):
        r = self.contour("mcp", stdin=json.dumps(call(
            1, "tools/call", name="create",
            arguments={"name": name, "references": [str(p) for p in paths]})) + "\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        got = json.loads(r.stdout)["result"]
        [block] = got["content"]
        self.assertFalse(got["isError"], block["text"])
        said = json.loads(block["text"])
        self.coming = self.coming or not (said["refused"] or said["next"])
        return block["text"], said

    def close_pages(self):
        """A console a create started, once it is up: one that came up after
        the test ended would outlive it."""
        from lib import presence
        if getattr(self, "coming", False):
            deadline = time.monotonic() + 30
            while not presence.live(self.space) and time.monotonic() < deadline:
                time.sleep(0.1)
        super().close_pages()

    def begun_on(self):
        deadline = time.monotonic() + 30
        while not self.prompt.exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        return self.prompt.read_text()

    def test_create_copies_the_references_and_opens_the_new_space_flow(self):
        text, said = self.create("beta", self.front, self.side)
        self.assertIsNone(said["refused"], said)
        self.assertEqual(said["path"], str(self.space))
        refs = self.space / "refs"
        self.assertEqual(sorted(p.name for p in refs.iterdir()), ["front.jpg", "side.png"])
        self.assertEqual((refs / "front.jpg").read_bytes(), self.JPEG)
        self.assertEqual((refs / "side.png").read_bytes(), PictureTest.PNG)
        self.assertIn("new-space skill", self.begun_on())
        [url] = self.urls()
        self.assertSecretless(text, url)

    def test_a_path_that_is_no_readable_image_is_refused_and_nothing_is_made(self):
        """Missing, unreadable, or not an image by its bytes or its name: each
        is refused by name, before `contour init` runs."""
        notes = self.pictures / "notes.png"
        notes.write_text("not a picture at all")
        locked = self.pictures / "locked.jpg"
        locked.write_bytes(self.JPEG)
        locked.chmod(0)
        self.addCleanup(locked.chmod, 0o644)
        text_file = self.pictures / "front.txt"
        text_file.write_bytes(self.JPEG)
        for bad in (self.pictures / "gone.jpg", notes, locked, text_file):
            _, said = self.create("beta", self.front, bad)
            self.assertIn(str(bad), said["refused"])
            self.assertIsNone(said["path"])
            self.assertFalse(self.space.exists(), bad)
        time.sleep(1)                         # long enough for one started anyway to show
        self.assertFalse(self.opened.exists(), "a console was opened anyway")

    def test_two_references_of_one_name_are_refused(self):
        """In `refs/` one would overwrite the other."""
        other = Path(tempfile.mkdtemp()).resolve() / "front.jpg"
        other.write_bytes(self.JPEG + b" again")
        _, said = self.create("beta", self.front, other)
        self.assertIn("front.jpg", said["refused"])
        self.assertFalse(self.space.exists())

    def test_a_name_init_refuses_is_refused_in_its_words(self):
        said_by_init = json.loads(self.contour(
            "init", "alpha", "--new", "--json").stdout)["refused"]
        _, said = self.create("alpha", self.front)
        self.assertEqual(said["refused"], said_by_init)
        self.assertEqual(list((self.tmp / "alpha" / "refs").iterdir()), [])

    def test_nothing_but_inits_files_and_the_references_is_written(self):
        by_hand = Path(tempfile.mkdtemp()).resolve()
        r = subprocess.run([sys.executable, str(CONTOUR), "init", "beta"],
                           cwd=str(by_hand), env=self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.create("beta", self.front)
        self.begun_on()                     # the console is up, and has written its own

        def files(root):
            return {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()
                    and not p.relative_to(root).parts[0] in (".git", ".contour")}
        self.assertEqual(files(self.space), files(by_hand / "beta") | {"refs/front.jpg"})

    def test_with_no_console_environment_the_space_is_made_and_says_how_to_go_on(self):
        self.env["CONTOUR_CONSOLE_PYTHON"] = str(self.tmp / "no-python")
        _, said = self.create("beta", self.front)
        self.assertIsNone(said["refused"])
        self.assertEqual((self.space / "refs" / "front.jpg").read_bytes(), self.JPEG)
        self.assertIn("python3 -m venv .venv", said["next"])
        self.assertIn(f"cd {self.space}", said["next"])
        self.assertIn("contour-console --begin new-space", said["next"])
        time.sleep(1)                         # long enough for one started anyway to show
        self.assertFalse(self.opened.exists(), "a console was opened anyway")


if __name__ == "__main__":
    unittest.main()
