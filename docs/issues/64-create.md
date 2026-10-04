# 64 — `create`

**Type:** AFK · **Source:** ADR 0024, decisions 2 and 10 — [the connector: Desktop reads and opens, never drives](../adr/0024-the-connector-desktop-reads-and-opens.md)

## What to build

A connector tool that starts a model from pictures already on disk: the lobby's
**create**, plus the references, and nothing else.

`create` takes a name and the paths of reference images. It refuses any path that
is not a readable image file, before anything is made. It runs `contour init
--new` where the lobby would, copies each file byte for byte into the new space's
`refs/`, and starts the space's console on the new-space flow through the lobby's
own path. With no console environment the space is still made, and the result
says how to go on from a terminal, in the lobby's words. It never sees the
console's URL.

It drafts no spec and writes nothing else into the space. The anchor, the spans
and the tolerances are the console's, under its gates.

The connector's instructions say that a picture pasted into the chat is not a
reference, and to ask for the file's path instead: the model holds what it saw,
not the file, and anything it wrote out would be made up.

## Acceptance criteria

- [x] `create` with image paths makes a space whose `refs/` files match the originals byte for byte
- [x] A path that is missing, unreadable or not an image is refused, and no space is made
- [x] A name `contour init --new` refuses is refused in its words
- [x] The new space's console starts on the new-space flow, and no URL is returned
- [x] With no console environment, the space is made and the result says how to go on
- [x] Nothing but `init`'s own files and the copied references is written
- [x] The instructions say a pasted picture is answered with a request for a path

## What it came to

The lobby's create and the connector's are one function now, `lobby.made`:
`contour init --new`, then the references written into `refs/`, then the
console on its flow, or the line that says how to go on from a terminal. The
lobby's `location` moved out of the page with it, so `create` makes its space
where the lobby would offer to, with no page running. Issue 65 hands `made` the
dropped files the same way.

`create` reads every path before anything is made, and refuses one that cannot
be read or is not an image, by `lobby.image`: a PNG, JPEG or WebP whose first
bytes and name agree, since the name is what the canvas serves it as. It lives
in the lobby and not `lib/refs.py`, which offers a listing and the bytes and
nothing else. It also refuses two references with one filename, since one would
overwrite the other in `refs/`, which the issue did not say.

The instructions are four lines, not three: the fourth says a pasted picture
is not a reference, and to ask for the file's path. ADR 0024's decision 4 says
four now too.

## Blocked by

- [57](57-the-connector-answers-spaces.md)
