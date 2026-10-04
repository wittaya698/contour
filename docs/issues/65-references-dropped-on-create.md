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

- [ ] Images dropped or chosen on create land in the new space's `refs/`, matching the originals byte for byte
- [ ] The same works for **variation of this**
- [ ] A file that is not an image, will not decode, or is over the cap is refused, named, and no space is made
- [ ] The upload is JSON, through the same token and origin checks as every other POST
- [ ] A request body over the cap is refused before it is read into memory
- [ ] No drop zone appears on a space that already exists
- [ ] Checked by hand once: drag two photos onto create, and compare their hashes with the copies in `refs/`

## Blocked by

None - can start immediately
