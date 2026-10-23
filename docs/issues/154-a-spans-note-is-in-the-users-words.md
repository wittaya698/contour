# 154 — A span's note is in the user's words

**Type:** AFK · **Source:** the console run that checked issue 151, 2026-10-23

## What to build

The canvas showed, under span 1 of a new space, *no anchor span on
1-walkie-talkie-orange-and-yellow-same-body.png: propose the span a size the
spec states is the length of, with --claims*. That is `span.read`'s reason a
span has no millimetres yet (`lib/span.py`), written for the agent, with a
flag in it, and the page shows it to the user as it is.

It happened because the run measured before there was a spec, which is the
right order (rule 1: a proposal names its spans), so no size the spec states
existed to claim. The agent still needs the reason as it is; the page needs
it in the words *Speaking to the user* gives: *no size yet: this picture has
no span with a real size to scale from*, and nothing at all while the span
being asked is itself the one that will give it.

## Acceptance criteria

- [x] The page never shows a reason `span.read` gives with a flag, a file name or the word *anchor* in it
- [x] The agent's `contour measure` output keeps the reason as it is
- [x] A span asked *is this the 110 mm…?* on a picture with no anchor yet shows no reason under it

## Found (2026-10-23)

The reason reached the person in two places, not one: under the span on the
card, and in the reading's own row in the list of marks, since a reading is
a mark. Both now pass it through the page's `plainly`, and the reading on
file keeps the agent's words, so `contour measure` still names the picture
and the flag.

`plainly` covers every reason the readings can carry, as the code makes
them (`test_foundations.CardTest`): no span with a real size yet, one asked
and not answered, no directions answered, and the camera's, which said *the
anchor* for the same span. A reading made the old way said *anchor span* in
its note on the card too. A span asking its own size shows no reason beside
its question, as it did already.

## Blocked by

None - can start immediately
