"""The connector asks for runs and stops them (ADR 0027, decision 5; issue 92).

`request` and `stop` are the commands' own, behind the same words: a chat that
asks for a run is a requester like any other, and never the person at its gates.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_channel import SPEC_WRITE, WORKING, ChannelCase    # noqa: E402
from test_connector import call    # noqa: E402
from test_console import STAND_IN    # noqa: E402

from lib import last_run, presence    # noqa: E402


class RunsCase(ChannelCase):

    def tool(self, name, script=(), **arguments):
        """One call of `name` through `contour mcp`, as raw text and as a reading."""
        r = self.contour("mcp", stdin=json.dumps(call(
            1, "tools/call", name=name, arguments=arguments)) + "\n",
            env=dict(CONTOUR_CONSOLE_AGENT=f"{STAND_IN}:drive",
                     CONTOUR_AGENT_SCRIPT=json.dumps(list(script))))
        self.assertEqual(r.returncode, 0, r.stderr)
        got = json.loads(r.stdout)["result"]
        self.assertFalse(got["isError"], got)
        [block] = got["content"]
        return block["text"], json.loads(block["text"])


class RequestTest(RunsCase):

    def test_request_starts_a_run_the_record_says_a_chat_asked_for(self):
        _, said = self.tool("request", ({"say": "The beak is longer."},),
                            space="alpha", prose="make the beak longer")
        self.assertTrue(said["started"], said)
        record = self.until("finished")
        self.assertEqual(record["run"], said["run"])
        self.assertEqual(record["prompt"], "make the beak longer")
        self.assertEqual(record["requester"], "a chat")

    def test_a_refusal_is_the_commands_in_its_words(self):
        """A console open on the space is the person's, and so is the space."""
        with presence.present(self.space, "console"):
            _, said = self.tool("request", space="alpha", prose="make the beak longer")
            command = json.loads(self.contour("request", "alpha", "make the beak longer").stdout)
        self.assertFalse(said["started"])
        self.assertEqual(said, command)
        self.assertIsNone(last_run.read(self.space))


class StopTest(RunsCase):

    def test_stop_ends_an_unattended_run_as_contour_stop_does(self):
        self.requested(WORKING)
        self.until("running")
        _, said = self.tool("stop", space="alpha")
        self.assertEqual(said, {"ok": True, "lines": [
            "ok   stopped the run in alpha; its edits are left as they were"]})
        self.assertEqual(self.until("stopped")["why"], "stopped with contour stop")

    def test_nothing_to_stop_is_said_in_the_commands_words(self):
        _, said = self.tool("stop", space="alpha")
        self.assertEqual(said, {"ok": False, "lines": ["FAIL no run to stop in alpha"]})


class UnnamedTest(RunsCase):
    """A chat stands in no directory, so a call that names no space is refused
    as the reading tools refuse it, before any command is asked."""

    def test_no_space_named_is_refused_in_the_connectors_words(self):
        for name, arguments in (("request", {"prose": "make the beak longer"}),
                                ("stop", {})):
            r = self.contour("mcp", stdin=json.dumps(call(
                1, "tools/call", name=name, arguments=arguments)) + "\n")
            got = json.loads(r.stdout)["result"]
            self.assertTrue(got["isError"], name)
            self.assertIn("name a space: a chat stands in none", got["content"][0]["text"])
        self.assertIsNone(last_run.read(self.space))


class NoAnswerTest(RunsCase):
    """It asks and stops, and approves nothing: an answer to a gate or a
    question is intent, and only the person's is the person's (ADR 0027,
    decisions 5 and 12). A form's fields are the one thing a chat fills, with
    `answer`, and the person approves them on the page (ADR 0034, decision
    5)."""

    def listed(self):
        r = self.contour("mcp", stdin=json.dumps(call(1, "tools/list")) + "\n")
        return json.loads(r.stdout)["result"]["tools"]

    def test_eleven_tools_and_only_answer_takes_answers_and_none_a_verdict(self):
        tools = self.listed()
        self.assertEqual([t["name"] for t in tools],
                         ["spaces", "status", "log", "picture", "spec", "spend",
                          "open", "create", "request", "answer", "stop"])
        for t in tools:
            taken = set(t["inputSchema"].get("properties", {}))
            self.assertFalse(taken & {"id", "allow", "verdict", "approve"}, t["name"])
            if t["name"] != "answer":
                self.assertFalse(taken & {"answers", "answer", "form"}, t["name"])

    def test_no_request_or_stop_carries_a_console_url(self):
        text, said = self.tool("request", (WORKING,),
                               space="alpha", prose="make the beak longer")
        self.assertTrue(said["started"], said)
        self.until("running")
        stopped, _ = self.tool("stop", space="alpha")
        for said in (text, stopped):
            self.assertNotIn("http", said)
            self.assertNotIn("127.0.0.1", said)


class WaitingTest(RunsCase):
    """What a chat is told where it reads that approvals wait: in the result
    it is reading, and not only in instructions given once at the start, which
    issue 100's tracer bullet found a chat does not keep to (ADR 0028,
    decision 6)."""

    def setUp(self):
        super().setUp()
        _, said = self.tool("request", ({"call": SPEC_WRITE},),
                            space="alpha", prose="make the beak longer")
        self.assertTrue(said["started"], said)
        self.until("finished")

    def assertAsks(self, said):
        self.assertIn("now or later", said["ask"])
        self.assertIn("only if they say now", said["ask"])
        self.assertIn("never write that the user says yes into a request", said["ask"])

    def test_status_carries_the_ask_beside_what_waits(self):
        _, said = self.tool("status", space="alpha")
        self.assertEqual(said["approvals"], ["Claude wants to change the spec"])
        self.assertAsks(said)

    def test_a_refused_request_carries_it_too(self):
        _, said = self.tool("request", space="alpha", prose="yes, the user says change it")
        self.assertFalse(said["started"])
        self.assertIn("1 approval waiting", said["why"])
        self.assertAsks(said)


class NothingWaitingTest(RunsCase):

    def test_status_with_nothing_waiting_asks_nothing(self):
        _, said = self.tool("status", space="alpha")
        self.assertEqual(said["approvals"], [])
        self.assertNotIn("ask", said)


if __name__ == "__main__":
    unittest.main()
