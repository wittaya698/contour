# 35 — Restore a deleted space

**Type:** AFK · **Source:** [ADR 0021](../adr/0021-the-lobby.md) decision 6

## What to build

The **lobby** lists deleted spaces, the bundles in the trash, beside the live
ones, and can restore one. Restoring is a clone of its bundle back into a space
root. It is also a `contour` command, so it can be done without a page.

A restored space is a space: its marker, pre-push stub and scaffolding are all
checked. Its `pre-push` stub lives in `.git/hooks`, which a clone does not carry,
so it is reinstalled rather than assumed. A restored space that could push would
break rule 8 in the one place nobody would think to look.

## Acceptance criteria

- [x] The lobby and a `contour` command both list deleted spaces, with name and date, separately from live ones
- [x] Restore recreates the space at its old location, or a chosen one, with tracked content byte-identical to what was deleted
- [x] The restored space refuses every push, and `contour doctor` in it is all `ok`
- [x] Restore refuses when the name or path is taken, and changes nothing
- [x] After a restore, the bundle stays in the trash until the user removes it
- [x] A deleted space with a live space standing where it stood is listed as restored, live at that path, and offers no Restore
- [x] The user can remove a bundle: `contour purge <id>` proposes and changes nothing, `--yes` removes the bundle and its record; the proposal says whether a live space still stands where it stood or this is the only copy
- [x] In the lobby, removing a bundle is confirmed by typing its id, and the button is enabled only once it matches

Added after the first run, by the user: a restored space and its bundle both
listed with nothing to tell them apart, and nothing could remove a bundle, so
the trash only grew. A purge is the one irreversible act in the trash, so it is
confirmed the way a delete is.

## What it came to

- `contour restore <id> [--to <dir>] [--json]`, run from anywhere. `<id>` is
  the bundle's file name in the trash, e.g. `alpha-2026-10-02`.
- `contour delete` now writes a record beside each bundle,
  `<id>.json`, holding the name, the old path and the date. The bundle carries
  history and not the path, so without the record "its old location" could not
  be known. A bundle whose record is lost still restores: the name and date come
  from its file name, and `--to` is required.
- `--to` is the folder the space goes **into**, not its new name. A space's
  name is its directory and its spec says the same, so it always comes back
  under the name it was deleted with. Coming back under another name is
  `contour rename` afterwards.
- A restore refuses, changing nothing, when the path exists (even as an empty
  directory, which git would clone into), when a live space already has the
  name, or when the trash holds no such id.
- The clone's `origin`, which points at the bundle, is removed, and the
  `pre-push` stub is reinstalled. `init` and `restore` share one function for
  that. Tested: a push to a bare repository is refused and reaches it with no
  refs, and `contour doctor` in the restored space is all `ok`.
- `contour spaces --json` carries the trash as `deleted`, apart from
  `spaces`, and the plain list prints it under the live spaces with the
  restore command. The lobby shows it as its own table with a Restore button and
  an optional folder, and shows refusals as worded.
- The bundle stays in the trash after a restore. When a space stands again
  where it stood, restored or made anew, the list says `restored, live at
  <path>`, and neither the plain list nor the lobby offers a restore the path
  would refuse.
- `contour purge <id>` proposes removing a bundle and changes nothing; `--yes`
  removes the bundle and its record, and nothing else. The proposal says
  whether a live space still stands where it stood (though the bundle may hold
  history it no longer has) or this is the only copy. The id is the first word
  whatever it says, as with `delete`. The console's gate reads it as
  `ref-write`, as `delete` is read, since a bundle holds the references.
- In the lobby, Remove bundle… shows that proposal above a box the id is typed
  into, and the button is enabled only on an exact match. `contour purge` takes
  any id it is given, so the lobby's server refuses a typed id that is not the
  bundle the page showed. Otherwise, typing another bundle's id would remove
  that one.
- `contour spaces` now reads `~/.contour`, so the tests that list spaces set
  `$CONTOUR_HOME` to their own. One of them was reading the user's real trash.
- The console's gate treats `restore` as intentless: it creates a space as
  `init` does and overwrites nothing.

## Blocked by

- [34](34-delete-leaves-a-bundle.md)
