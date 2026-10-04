"""The connector: Contour as Claude Desktop sees it (ADR 0024).

A stdio MCP server speaking the three methods it needs — `initialize`,
`tools/list`, `tools/call` — as newline-delimited JSON-RPC, with no resources,
prompts or sampling. Stdlib only, because it is part of the launcher and a bare
clone has to serve it (ADR 0024, decision 1).

This module is the protocol and the tools' definitions. What a tool does is
handed to `serve` by `lib/cli.py`, which owns the readings, so the connector
imports nothing of the launcher's and cannot reach a write the launcher has.
"""
import json

LATEST = "2025-06-18"

INSTRUCTIONS = "\n".join((
    "This connector reads Contour's model spaces and opens their pages; it changes nothing in a space.",
    "A spec changes only inside its space, argued from a span the user can see on the canvas.",
    "To change a model, open its console.",
))
"""Facts about the connector, not a copy of the rules (ADR 0024, decision 4): what it
cannot do needs no rule here, and what it can say is steered to a span."""


TOOLS = (
    {"name": "spaces",
     "description": "Every Contour model space on this machine and its health: "
                    "toolkit drift, scaffold, remotes, who is in it, and the trash.",
     "inputSchema": {"type": "object", "properties": {}}},
)
"""Every tool's definition, coarse on purpose: each one sits in Desktop's
context on every turn (ADR 0024, decision 3)."""


def config(link):
    """The block to paste into `claude_desktop_config.json` (ADR 0024, decision 7).

    The link rather than the checkout, so moving the toolkit stays a relink —
    and the link alone, with its shebang choosing the interpreter, because any
    interpreter named here could be one inside the checkout.
    """
    return {"mcpServers": {"contour": {"command": str(link), "args": ["mcp"]}}}


def result(n, said):
    return {"jsonrpc": "2.0", "id": n, "result": said}


def error(n, code, text):
    return {"jsonrpc": "2.0", "id": n, "error": {"code": code, "message": text}}


def answer(message, tools):
    """The response to one message, or None for a notification — JSON-RPC
    answers nothing that carries no id, known method or not."""
    if "id" not in message:
        return None
    n, method = message["id"], message.get("method")
    if method == "initialize":
        return result(n, {"protocolVersion": (message.get("params") or {}).get(
                              "protocolVersion", LATEST),
                          "capabilities": {"tools": {}},
                          "serverInfo": {"name": "contour", "version": "1"},
                          "instructions": INSTRUCTIONS})
    if method == "tools/list":
        return result(n, {"tools": [t for t in TOOLS if t["name"] in tools]})
    if method == "tools/call":
        params = message.get("params") or {}
        run = tools.get(params.get("name"))
        if run is None:
            return error(n, -32602, f"no tool {params.get('name')!r}")
        try:
            said, failed = json.dumps(run(params.get("arguments") or {})), False
        except Exception as e:      # a finding for the chat, never a dead pipe
            said, failed = f"{params['name']} failed: {e}", True
        return result(n, {"content": [{"type": "text", "text": said}],
                          "isError": failed})
    return error(n, -32601, f"no method {method!r}: the connector speaks "
                            f"initialize, tools/list and tools/call")


def serve(stdin, stdout, tools):
    """Answer each line Desktop writes until it closes the pipe."""
    for line in stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except ValueError:
            said = error(None, -32700, "not JSON")
        else:
            said = answer(message, tools) if isinstance(message, dict) \
                else error(None, -32600, "not a request")
        if said is not None:
            stdout.write(json.dumps(said) + "\n")
            stdout.flush()
