"""The Claude Agent SDK, behind the console's one seam (ADR 0019, decision 1).

The only file in Contour that imports a dependency, and deliberately the
thinnest: everything that can be decided without the SDK is decided in `run.py`
next door, which is why the gate, the wait and the hold are provable on a clone
with nothing installed. What is left here is translation — the SDK's messages
into the transcript's vocabulary, and the console's gate into the SDK's
permission callback — and translation is all it is allowed to be. There is
nothing here to configure: `run.options` hands over what the agent is told, and
this passes it through rather than adding to it. The console's spec write is the
one tool it adds, and it too is `run.py`'s, put in the SDK's shape (ADR 0029).
"""
import anyio
from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions,
                             ClaudeSDKClient, ConversationResetMessage,
                             PermissionResultAllow, PermissionResultDeny,
                             ResultMessage, SystemMessage, TextBlock,
                             ToolUseBlock, create_sdk_mcp_server, tool)

from console.run import (QUESTION, SPEC_WRITER, TOPICS_TOOL, topics_proposer,
                         spec_written, topics_proposed)
from lib import survey


def drive(prompt, options, gate, say):
    """One agent session, over the seam `console/run.py` defines.

    Synchronous, because the console's run is a thread and the transcript is a
    list: the event loop belongs to this session and ends with it.
    """
    anyio.run(session, prompt, options, gate, say)


def label(prompt, options, gate, say):
    """The lobby's labelling act: the same session, serving the act's own
    proposal in place of the console's tools (ADR 0030, decision 7)."""
    from console import labelling
    anyio.run(session, prompt, options, gate, say,
              labelling.tools(survey.vocabulary()))


async def session(prompt, options, gate, say, served=None):
    async def can_use_tool(tool, payload, context):
        """The console's gate, in the shape the SDK asks for.

        `gate` blocks until the user answers — indefinitely, on purpose — so it
        runs on a worker thread. On the event loop it would stop the SDK reading
        the very messages the transcript is showing the person who has to decide.
        """
        allow, told = await anyio.to_thread.run_sync(gate, tool, payload)
        return result(tool, payload, allow, told)

    async with ClaudeSDKClient(
            ClaudeAgentOptions(**options, can_use_tool=can_use_tool,
                               mcp_servers={"contour": create_sdk_mcp_server(
                                   "contour", tools=served or tools(options["cwd"]))})
            ) as client:
        await client.query(prompt)
        async for message in client.receive_response():
            for kind, fields in said(message):
                say(kind, **fields)
            # What the turn cost, over the same seam and as its own kind: the
            # console records it and shows it, and neither is this file's
            # business (ADR 0019, decision 37). Per assistant message, because
            # that is the turn — `ResultMessage` carries a total, which arrives
            # once the run is over and informs nothing anybody can still act on.
            usage = getattr(message, "usage", None)
            if isinstance(message, AssistantMessage) and usage:
                say("usage", usage=dict(usage))


def tools(space):
    """The console's spec write and topic proposal, as SDK tools: what they say
    and do are `run.py`'s, and only reached once the gate has answered (ADR
    0029, ADR 0030)."""
    @tool(SPEC_WRITER["name"], SPEC_WRITER["description"], SPEC_WRITER["schema"])
    async def spec_write(args):
        return {"content": [{"type": "text", "text": spec_written(space, args)}]}

    proposer = topics_proposer(survey.vocabulary())

    @tool(proposer["name"], proposer["description"], proposer["schema"])
    async def topics_propose(args):
        return {"content": [{"type": "text", "text": topics_proposed(args)}]}
    return [spec_write, topics_propose]


def result(tool, payload, allow, told):
    """The gate's answer, in the shape the SDK takes it.

    The reason for a denial goes back as the call's result, which is the only
    place the agent will read it. No `updated_input` on a call: a gate cannot
    edit one. A question is the exception that is not one — what the person
    answered is the question's input filled in, which is how the SDK hands an
    answer to the session that asked (ADR 0027, decision 12).
    """
    if not allow:
        return PermissionResultDeny(message=told or "the user denied this call")
    if tool == QUESTION and told is not None:
        return PermissionResultAllow(updated_input={**payload, "answers": told})
    if tool == TOPICS_TOOL and told is not None:
        # The same exception, a second time: what the person kept is the
        # answer, and the tool can only say it if it arrives on the call.
        return PermissionResultAllow(updated_input={**payload, **told})
    return PermissionResultAllow()


def said(message):
    """One SDK message, in the transcript's words. Anything else is dropped:
    this is a control surface, and a surface showing everything shows nothing.

    A tool call goes over raw — its tool and its input — and the console words
    it (ADR 0025, decision 8): wording it here would be a second table."""
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock) and block.text.strip():
                yield "text", {"text": block.text.strip()}
            elif isinstance(block, ToolUseBlock):
                yield "call", {"tool": block.name, "call": dict(block.input)}
    elif isinstance(message, ConversationResetMessage):
        yield "limit", {"text": "the conversation was compacted — the run carries on"}
    elif isinstance(message, SystemMessage) and "compact" in (message.subtype or ""):
        # News, not an ending. A limit the user did not choose must not interrupt
        # work they were watching, which is the timeout argument again — and the
        # spec is read from disk rather than recalled precisely so that a
        # compacted run has not had its goalposts moved by the harness.
        yield "limit", {"text": "the conversation was compacted — the run carries on"}
    elif isinstance(message, ResultMessage) and message.is_error:
        yield "text", {"text": "the harness reported an error: "
                               f"{message.result or message.subtype}"}

