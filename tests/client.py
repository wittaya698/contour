"""Talking to a canvas the way its page does (ADR 0019 decision 31).

The server authenticates every request, so a test that reaches it has to hold
the session's token — which is the point: a helper that could not would be
testing a server nobody ships. Fetches send the token as a header, exactly as
the page does, so these exercise the path that a cross-site request cannot take.
"""
import json
import urllib.request

from lib.canvas import TOKEN_HEADER


def url(canvas, path):
    """An absolute URL for `path` on this canvas, with no token in it."""
    return canvas.origin + path


def open_url(canvas, path, timeout=5):
    """The raw response, for tests that care about bytes or content type."""
    req = urllib.request.Request(url(canvas, path),
                                 headers={TOKEN_HEADER: canvas.token})
    return urllib.request.urlopen(req, timeout=timeout)


def get(canvas, path, timeout=5):
    with open_url(canvas, path, timeout) as r:
        return r.status, json.loads(r.read() or b"null")


def post(canvas, path, payload, timeout=5):
    req = urllib.request.Request(
        url(canvas, path), data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 TOKEN_HEADER: canvas.token},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read() or b"null")
