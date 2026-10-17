# 128 — The agent's words keep their formatting

**Type:** AFK · **Source:** design session 2026-10-17, on a `nexus-probe` new-space interview; ADR 0025, decision 8

## What to build

The agent writes Markdown, and the transcript shows it as the symbols that
wrote it: `**1. What is it?**`, `*nexus-probe*`, and every line break collapsed,
so five numbered questions with their options read as one paragraph. The page
sets the text with `textContent` and no `white-space` rule. Worst of all is
the spec draft the new-space flow ends on: a whole `spec.yaml` in a fence,
arriving as one line at the moment rule 1 asks the person to confirm it.

ADR 0025 decision 8's *the agent's words as they are* means with the formatting the
agent gave them (`docs/CONTEXT.md`, *transcript*). The console parses each
`text` event into a tree of blocks and spans, and the page draws the tree. The
console does it because the page has no tests (there is no browser in this
suite), the same reason the console words calls (`lib/activity.py`).

- **A stdlib parser in `lib/`.** The README promises a stdlib launcher, and a
  Markdown library hands back an HTML string, which the page must never take.
- **The event keeps `text`, the raw words, and gains the tree beside it.**
  Nothing that reads `text` changes, and a reloaded tab replays the same tree.
- **The page draws the tree with `createElement` and `textContent` only,
  never `innerHTML`.** It cannot inject anything because of how it is built,
  not because a sanitiser is kept right.

What it understands, and how each is drawn:

| Written | Drawn |
|---|---|
| blank line | a new paragraph |
| single line break | kept |
| `**bold**`, `*italic*`, `_italic_` | bold, italic |
| `` `code` `` | monospace |
| `-`, `*`, `1.` lists, one level of nesting | lists |
| fenced block | monospace, whitespace kept |
| `# heading` | a bold paragraph |
| table | a monospace block, as written |
| `[text](url)` | `text (url)`, not a link: the agent chooses the URL |
| anything else | the characters as written |

When in doubt, it shows the characters. A word is never lost: apart from the
markers it consumed, every character of `text` is in the tree.

Decided and not to be reopened here:

- **No prompt rule against Markdown the page does not render.** Everything
  above degrades readably. A template change reaches an existing space only
  through ADR 0026. Revisit only if raw syntax shows up in real transcripts.
- **No ADR.** This is presentation, cheap to reverse, and the raw `text` is
  kept. The surprising parts (a hand-written parser, a tree and not HTML,
  links that do not click) say why in a comment where they live, citing this
  issue.

## Acceptance criteria

- [ ] A `text` event carries the raw `text` and a tree beside it
- [ ] `<script>alert(1)</script>` in the agent's words comes out as text in the tree, and the page sets no `innerHTML` from an event
- [ ] A fenced `spec.yaml` draft keeps every line and its indentation
- [ ] The interview from the session above, numbered questions with nested options, comes out as one list with sub-lists
- [ ] `[x](javascript:alert(1))` comes out as the text `x (javascript:alert(1))`, and nothing on the page is a link
- [ ] For any input, every character of `text` other than consumed markers appears in the tree, in order
- [ ] An unclosed `**` or fence is shown as written, not swallowed

## Blocked by

None - can start immediately
