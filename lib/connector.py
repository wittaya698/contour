"""The connector: Contour as Claude Desktop sees it (ADR 0024).

A stdio MCP server speaking the three methods it needs — `initialize`,
`tools/list`, `tools/call` — as newline-delimited JSON-RPC, with no resources,
prompts or sampling. Stdlib only, because it is part of the launcher and a bare
clone has to serve it (ADR 0024, decision 1).

This module is the protocol, the tools' definitions, and the shapes a chat is
handed. What the reading tools say is the survey's, which writes nothing, so the
connector imports it directly (issue 84). The four that act — open, create,
request and stop, each the command's own (ADR 0027, decision 5) — are handed to `serve` by `lib/cli.py`, and nothing else of the launcher's is
reachable from here.
"""
import base64
import json

from . import space, survey

LATEST = "2025-06-18"

ASK = ("When a space has approvals waiting, tell the user what they are, in status's "
       "words, and ask whether to answer them now or later. Call open (the console) "
       "only if they say now; later is nothing. Only the user answers them, on the "
       "page: never answer one, never pass on the case for one, and never write that the "
       "user says yes into a request.")
"""What a chat is told about approvals waiting: once in the instructions, and
again in every result that says some wait, because a chat that read it once at
the start was found not to keep to it (issue 100's tracer bullet)."""

INSTRUCTIONS = "\n".join((
    "This connector reads Contour's model spaces, opens their pages, makes new ones, "
    "and asks for a run nobody watches (request) and ends one (stop); it never answers "
    "a gate or a question: the user answers those on the console's page, which open "
    "brings up when they ask for it.",
    "A spec changes only in a run inside its space, never by numbers a chat names: a number "
    "read off a reference is argued from a span the user can see on the canvas, and a change "
    "the user asked for needs no span.",
    "To change a model, request a run in it, even one that needs a spec change: the run "
    "sets that aside for the user to answer on the page. Open its console only when "
    "the user asks to watch, or says now to approvals waiting.",
    "A picture pasted into the chat is not a reference: you hold what you saw, not the file. "
    "Open the lobby on its create form (open, with create, and the name if one was given), "
    "where the user drops the file; a path they offer, create takes.",
    "Your answers are read as a page reads, in plain words: from status, say its plain "
    "sentences, not its report lines.",
    ASK,
))
"""Facts about the connector, not a copy of the rules (ADR 0024, decision 4): what it
cannot do needs no rule here, and what it can say is steered to a span."""


TOOLS = (
    {"name": "spaces",
     "description": "Every Contour model space on this machine and its health: "
                    "toolkit drift, scaffold, remotes, who is in it, and the trash.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "status",
     "description": "Is a space green, and if not why: its last check's verdict, "
                    "open marks, uncommitted vetoes, toolkit drift, and its latest run.",
     "inputSchema": {"type": "object", "required": ["space"],
                     "properties": {"space": {"type": "string"}}}},
    {"name": "log",
     "description": "The tail of a space's last Blender log, and which stage wrote it.",
     "inputSchema": {"type": "object", "required": ["space"],
                     "properties": {"space": {"type": "string"},
                                    "lines": {"type": "integer", "default": 40}}}},
    {"name": "picture",
     "description": "One of a space's pictures as an image, with the build it "
                    "was drawn from and whether that is still current.",
     "inputSchema": {"type": "object", "required": ["space", "picture"],
                     "properties": {"space": {"type": "string"},
                                    "picture": {"enum": ["sheet", "filmstrip",
                                                         "worksheet"]}}}},
    {"name": "spec",
     "description": "A space's spec.yaml, as text.",
     "inputSchema": {"type": "object", "required": ["space"],
                     "properties": {"space": {"type": "string"}}}},
    {"name": "spend",
     "description": "What each console run in a space cost, in tools/tokens.py's units.",
     "inputSchema": {"type": "object", "required": ["space"],
                     "properties": {"space": {"type": "string"}}}},
    {"name": "open",
     "description": "Open the page where the user acts: a space's console or "
                    "canvas, or the lobby — with create, on its create form, the "
                    "new model's name filled in if given. Says whether it opened, "
                    "never where.",
     "inputSchema": {"type": "object", "required": ["page"],
                     "properties": {"page": {"enum": ["console", "lobby", "canvas"]},
                                    "space": {"type": "string"},
                                    "create": {"type": "boolean"},
                                    "name": {"type": "string"}}}},
    {"name": "create",
     "description": "Make a new model space from reference pictures on disk, "
                    "and open its console to draft the spec. Takes their paths, "
                    "never a picture pasted into the chat.",
     "inputSchema": {"type": "object", "required": ["name", "references"],
                     "properties": {"name": {"type": "string"},
                                    "references": {"type": "array",
                                                   "items": {"type": "string"}}}}},
    {"name": "request",
     "description": "Ask for a run in a space nobody is watching: the prose is the "
                    "whole of what it is asked, what the user wants of the model in "
                    "their words. It may change the spec, but never name a spec's new "
                    "numbers: the run argues them, and the user confirms them on the "
                    "page. Says started and its run, or why not. "
                    "Once started there is nothing to open: what needs the user is "
                    "set aside, and status says when something waits.",
     "inputSchema": {"type": "object", "required": ["space", "prose"],
                     "properties": {"space": {"type": "string"},
                                    "prose": {"type": "string"},
                                    "as": {"type": "string",
                                           "description": "who is asking, for the record"}}}},
    {"name": "stop",
     "description": "End the run in a space, as `contour stop` does: answers no gate, "
                    "and leaves its edits as they were.",
     "inputSchema": {"type": "object", "required": ["space"],
                     "properties": {"space": {"type": "string"}}}},
)
"""Every tool's definition, coarse on purpose: each one sits in Desktop's
context on every turn (ADR 0024, decision 3)."""


class Content(list):
    """A tool's answer as MCP content blocks, handed over as they are. Any other
    answer is a reading, and goes to Desktop as its JSON text."""


def text(said):
    """Text Desktop reads as it is, rather than as a JSON string of it."""
    return Content([{"type": "text", "text": said}])


def image(png, reading):
    """A picture Desktop shows, and the reading that says what it is of."""
    return Content([{"type": "image", "mimeType": "image/png",
                     "data": base64.b64encode(png).decode("ascii")},
                    {"type": "text", "text": json.dumps(reading)}])


def naming(name):
    """The name a call gives. A chat stands in no directory, so it must give
    one (ADR 0024, decision 3); the acts take it from here to the command's own
    resolving, so a chat that names nothing is refused before any is asked."""
    if not name:
        raise LookupError("name a space: a chat stands in none")
    return str(name)


def named(name):
    """The space a call names, and a name that resolves to none or several
    refused in the words `contour spaces <name>` would print."""
    try:
        return space.named(naming(name), survey.TOOLKIT)
    except LookupError as e:
        raise LookupError(f"FAIL {e}") from None


def pictured(said):
    """The survey's picture as Desktop shows it: the image and what it is of,
    or, never drawn, the saying so."""
    if "path" not in said:
        return said
    return image(said["path"].read_bytes(), said["of"])


def asking(said):
    """A reading that says approvals wait, with the ask beside it, where the
    chat reads it as it decides what to say (ADR 0028, decision 6)."""
    return {**said, "ask": ASK} if said.get("approvals") else said


def specced(said):
    """The spec as text, and the one line that says where it changes: the
    instructions' own, so a chat arguing a tolerance is sent to draw a span
    rather than handed a file it could propose to (ADR 0024, decision 4)."""
    said = said if said is not None else \
        "no spec.yaml yet: a spec is drafted in the space's console\n"
    return text(said + ("" if said.endswith("\n") else "\n")
                + "\n" + INSTRUCTIONS.splitlines()[1] + "\n")


def readings():
    """Every tool that only reads, each the survey's answer in a chat's shape."""
    return {
        "spaces": lambda args: survey.listing(),
        "status": lambda args: asking(survey.status(named(args.get("space")))),
        "log": lambda args: survey.log(named(args.get("space")), args.get("lines", 40)),
        "picture": lambda args: pictured(survey.picture(named(args.get("space")),
                                                        args.get("picture"))),
        "spec": lambda args: specced(survey.spec(named(args.get("space")))),
        "spend": lambda args: survey.spent(named(args.get("space")))}


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
            said, failed = run(params.get("arguments") or {}), False
        except Exception as e:      # a finding for the chat, never a dead pipe
            said, failed = f"{params['name']} failed: {e}", True
        if not isinstance(said, Content):
            said = [{"type": "text",
                     "text": said if failed else json.dumps(said)}]
        return result(n, {"content": list(said), "isError": failed})
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
