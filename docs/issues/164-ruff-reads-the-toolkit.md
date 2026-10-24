# 164 — ruff reads the toolkit

**Type:** AFK · **Source:** a scan of the toolkit for tools and libraries, 2026-10-24

## What to build

About 13 000 lines of `lib/`, `console/` and `tools/` are read by nothing but
the tests. An unused import, a variable assigned and never read, or a name
shadowed by a later one passes the suite as long as the behaviour holds.

[ruff](https://docs.astral.sh/ruff/) is one binary that finds those in well
under a second. It is a tool for whoever works on the toolkit, never a
dependency: nothing in `./contour`, the console or a model space imports it or
needs it installed.

A `ruff.toml` at the root picks the rules (the default set to start), excludes
`project/`, `fixtures/` and `.venv/`, and allows what `build.py` files and the
Blender half of `lib/` do on purpose. The toolkit is made clean against it, one
finding at a time, each fix behaviour-free. A test runs ruff when it is
installed and skips, saying why, when it is not, so a bare clone's suite is
unchanged.

## Acceptance criteria

- [ ] `ruff check .` is clean on the toolkit (tested, skipped without ruff)
- [ ] `project/` is never read by it (tested)
- [ ] No shipped code imports or requires ruff (tested)
- [ ] Every fix leaves the suite green and changes no behaviour

## Blocked by

None - can start immediately
