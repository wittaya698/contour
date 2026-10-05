# 65 — References dropped on the lobby's create

**Type:** AFK · **Source:** ADR 0024, decision 11 — [the connector: Desktop reads and opens, never drives](../adr/0024-the-connector-desktop-reads-and-opens.md)

## What to build

The lobby's create form, and its **variation of this**, take reference images
dropped onto it — or picked with a file chooser, for anyone who does not drag.
The new space starts with them in `refs/`, byte for byte, before its console
opens on the new-space flow.

The page reads each file raw and sends it base64 inside the create request's
JSON, never drawing or resizing it first, since either would re-encode it. The
lobby checks every file — that it decodes, that its signature says it is an
image, that it is under the size cap — before `contour init` runs, so a bad drop
is refused whole and no space is made. Nothing else about create changes: the
lobby still drafts no spec.

Only on create. A space that exists gets no drop zone; adding a reference there
is a `ref-write`, and belongs in its console where that is gated.

## Acceptance criteria

- [x] Images dropped or chosen on create land in the new space's `refs/`, matching the originals byte for byte
- [x] The same works for **variation of this**
- [x] A file that is not an image, will not decode, or is over the cap is refused, named, and no space is made
- [x] The upload is JSON, through the same token and origin checks as every other POST
- [x] A request body over the cap is refused before it is read into memory
- [x] No drop zone appears on a space that already exists
- [x] Checked by hand once: drag two photos onto create, and compare their hashes with the copies in `refs/`

## Blocked by

None - can start immediately

## What it came to

The create form, and so **variation of this**, which is the same form, has a
drop zone that is also a file chooser. The page reads each file with
`arrayBuffer()` and sends it base64 under `references` in the create request,
and nowhere draws a picture. The lobby's `dropped` checks every file before
`lobby.made` runs: that its name is a plain filename (`../x.png` would write
outside `refs/`), that its base64 decodes, that it is no more than
`REFERENCE_CAP` (20 MB), and then `lobby.unfit`, which is the image and
duplicate-name check the connector's `create` now shares, worded the same.

The body cap is in `Page`, beside the other POST checks. A body whose
`Content-Length` is over `max_body` gets a 413 without being read: 4 MB for
every page, 128 MB for the lobby, which is the one page that sends files. The
form turns a 413 into a refusal it can show.

Nothing in `row` or `render` takes a drop, so a space that exists has no way to
take a reference from the lobby.

Checked by hand on 2026-10-05: two photos were dropped onto create as
`beaky-test-drop-ref`, and the copies landed in `refs/` with the same SHA-1 as
beaky's `side.jpg` (`0206126…`) and `front.jpg` (`10a4d64…`). Those are the
same two photos as the connector's tracer bullet (ADR 0024, Evidence).

