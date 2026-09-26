"""The Claude Agent SDK, behind the console's one seam (ADR 0019, decision 1).

The only file in Contour that imports a dependency, and deliberately the
thinnest: everything that can be decided without the SDK is decided in `run.py`
next door, which is why the gate, the wait and the hold are provable on a clone
with nothing installed. What is left here is translation — the SDK's messages
into the transcript's vocabulary, and the console's gate into the SDK's
permission callback — and translation is all it is allowed to be. There is
nothing here to configure: `run.options` hands over what the agent is told, and
this passes it through rather than adding to it.
"""
import json

import anyio
from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions,
                             ClaudeSDKClient, ConversationResetMessage,
                             PermissionResultAllow, PermissionResultDeny,
                             ResultMessage, SystemMessage, TextBlock,
                             ToolUseBlock)


def drive(prompt, options, gate, say):
    """One agent session, over the seam `console/run.py` defines.

    Synchronous, because the console's run is a thread and the transcript is a
    list: the event loop belongs to this session and ends with it.
    """
    anyio.run(session, prompt, options, gate, say)


async def session(prompt, options, gate, say):
    async def can_use_tool(tool, payload, context):
        """The console's gate, in the shape the SDK asks for.

        `gate` blocks until the user answers — indefinitely, on purpose — so it
        runs on a worker thread. On the event loop it would stop the SDK reading
        the very messages the transcript is showing the person who has to decide.
        """
        allow, reason = await anyio.to_thread.run_sync(gate, tool, payload)
        if allow:
            return PermissionResultAllow()
        # The reason goes back as the call's result, which is the only place the
        # agent will read it. No `updated_input`: a gate cannot edit the call.
        return PermissionResultDeny(message=reason or "the user denied this call")

    async with ClaudeSDKClient(
            ClaudeAgentOptions(**options, can_use_tool=can_use_tool)) as client:
        await client.query(prompt)
        async for message in client.receive_response():
            for kind, text in said(message):
                say(kind, text=text)


def said(message):
    """One SDK message, in the transcript's words. Anything else is dropped:
    this is a control surface, and a surface showing everything shows nothing."""
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock) and block.text.strip():
                yield "text", block.text.strip()
            elif isinstance(block, ToolUseBlock):
                yield "call", f"{block.name}  {brief(block.input)}"
    elif isinstance(message, ConversationResetMessage):
        yield "limit", "the conversation was compacted — the run carries on"
    elif isinstance(message, SystemMessage) and "compact" in (message.subtype or ""):
        # News, not an ending. A limit the user did not choose must not interrupt
        # work they were watching, which is the timeout argument again — and the
        # spec is read from disk rather than recalled precisely so that a
        # compacted run has not had its goalposts moved by the harness.
        yield "limit", "the conversation was compacted — the run carries on"
    elif isinstance(message, ResultMessage) and message.is_error:
        yield "text", f"the harness reported an error: {message.result or message.subtype}"


def brief(call):
    """A tool's input as one line. The call is shown, never offered."""
    if not isinstance(call, dict):
        return str(call)
    return str(call.get("command") or call.get("file_path") or json.dumps(call))[:400]
