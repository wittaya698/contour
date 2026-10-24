# 161 — `measure` says what colour is there

**Type:** AFK · **Source:** the console run that checked issue 160, 2026-10-24

## What to build

Asked to sample the walkie-talkie's body colours, a run wrote its own PNG
decoder in Python, with `zlib` and `numpy`, because the `python3` it had has no PIL,
and ran it on `refs/walkie.png`. It was gated as a change to the
reference, since a script from a file is not one ADR 0036 lets through.

Nothing in the toolkit answered the question first. Every colour option
`contour measure` has takes a colour the agent must already know: `--region
HEX`, `--of HEX`, `--profile HEX`. None says what colour is at a place, or
which colours the figure is made of, so the agent reads the pixels itself.

Two read-only forms of `contour measure`:

- `--sample X,Y` gives the colour at a pixel as sRGB hex, averaged over a
  small patch (`--patch PX`, default 5), with the patch's spread, so a
  reading off a shaded or noisy photo says how sure it is. Rows count from
  the top, as a mark's pixel does.
- `--palette` gives the figure's main colours, background left out, each
  as hex with its share of the figure and its bounding box. `--region` and
  `--of` take these hexes as they are.

Both read the image the way `measure` already does (sRGB, colorspace Raw),
so a hex from `--sample` matches what `--region` finds. The new-space skill
says to sample colour with these, not a script.

## Acceptance criteria

- [ ] `contour measure refs/x.png --sample X,Y` prints the patch's hex and spread, on a fixture with known colours (tested)
- [ ] `contour measure refs/x.png --palette` lists the fixture's colours, background left out, each with its share and box (tested)
- [ ] A hex from `--palette` passed to `--region` finds that colour's region (tested)
- [ ] Neither writes anything, and neither is gated under a console (tested)
- [ ] The new-space and build-model skills name `--sample` and `--palette` for colour
- [ ] On a real console, a run asked for a photo's colours uses them and writes no script

## Blocked by

None - can start immediately
