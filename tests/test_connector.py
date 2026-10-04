"""The connector, as Claude Desktop meets it (ADR 0024, issue 57).

No Desktop is needed: the protocol is newline-delimited JSON-RPC over stdio, so
a test writes the lines Desktop would write and reads what comes back. Most of
these drive `connector.serve` over in-memory pipes; the ones that matter end to
end run `contour mcp` as Desktop runs it.
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTOUR = ROOT / "contour"
sys.path.insert(0, str(ROOT))

from lib import connector  # noqa: E402


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

    def test_the_instructions_describe_the_connector_in_three_lines(self):
        """ADR 0024, decision 4: it reads and opens and changes nothing; a spec changes
        inside its space, from a span on the canvas; the console is where the
        model changes."""
        [got] = talk(call(1, "initialize", protocolVersion=connector.LATEST))
        said = got["result"]["instructions"].splitlines()
        self.assertEqual(len(said), 3)
        self.assertIn("changes nothing", said[0])
        self.assertIn("span", said[1])
        self.assertIn("canvas", said[1])
        self.assertIn("console", said[2])

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


class LauncherTest(unittest.TestCase):
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
        self.assertEqual([t["name"] for t in listed["result"]["tools"]], ["spaces"])
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


if __name__ == "__main__":
    unittest.main()
