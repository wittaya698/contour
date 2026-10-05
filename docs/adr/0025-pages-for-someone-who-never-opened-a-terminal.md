# 0025 — Pages for someone who has never opened a terminal

**Status:** Proposed · 2026-10-05 · **amends [ADR 0019](0019-console-a-driven-agent-behind-a-gate.md) (decision 33's count, and decision 36 is tuned from the page), [ADR 0021](0021-the-lobby.md) (what a row shows) and [ADR 0024](0024-the-connector-desktop-reads-and-opens.md) (decisions 4 and 10)**

## Context

Every page Contour has was written by the person who designed it, for
themselves. The lobby's rows read *Space · Toolkit · Commits · Health*, and
health says *differs from the template: CLAUDE.md*. The console's gate shows a
category in capitals and a raw call — `SPEC-WRITE`, `Edit /Users/…/build.py`.
The vetoes panel offers *promote to a mark*. Spend reads *1.2M cached · 4.1k
fresh · 2.0k out · 30k weighted*. Each word is exact, and `docs/CONTEXT.md`
fought for most of them.

The toolkit is meant to be shared (open question 6). Wanted: that the pages
work for a person who knows what a game asset needs and has never used a
terminal, git, or an ADR — a creator who arrives from a Claude Desktop chat,
thinks in pictures, and says *make it taller*. Decided 2026-10-05, in a
grilling session over every page.

Five facts, measured that day, shape it:

- **No page says whether the model is right.** The console's panel labels
  which build the sheet is of (decision 13) and nothing else. The verdict sits
  per check in `.contour/last-build.json` (issue 58), read by the connector
  and by the agent's transcript only.
- **No page can produce or hand over a `.glb`.** Export — the one sanctioned
  way a model leaves (rule 8) — is reachable only by asking the agent, and lands
  in `exports/`, a directory this person has never seen.
- **A model made from the lobby gates every build.** The ask-list has no
  presets and a space it does not name lets nothing through (decision 36), so
  every `contour check` the agent runs is an *Allow* click until somebody edits
  `~/.contour/ask-list.yaml` by hand.
- **There is a door in and none back.** The lobby enters a console; nothing on
  a console or canvas page returns to the lobby.
- **A pasted picture is a dead end.** The connector asks for a file path
  (ADR 0024, decision 10), which this person often cannot produce — while the
  lobby's create form has taken dropped files since issue 65.

Out of scope, and recorded as open question 14: *getting in* — the clone,
hooks, venv and Desktop registration that happen before the first page. This
ADR starts at the first page and assumes someone installed.

## Decision

**1. Every page term falls in one of three tiers, by one rule.** A term is
*shown* if the user acts on it, *renamed* if they only decide about it, and
*hidden* if it only explains how something works. Shown terms — **reference**,
**sheet**, **mark**, **span**, **spec** — keep their exact word and are
explained in one line where they first appear, because the agent says them
too. Renamed terms appear as the act: a gate is *Claude wants to change the
spec — allow?*. Hidden terms — toolkit, commit, bundle, hold, presence,
revision, category — leave the page or become their outcome. A **model space**
is a *model* on the page. The sort lives in `docs/CONTEXT.md` under *On the
page*, and a term not yet sorted is sorted by the rule before a page shows it.
The glossary stays exact everywhere else: code, ADRs, commit messages.

**2. The agent speaks to the user by the same tiers, everywhere.** In a console
run and in a terminal session alike — *Save this version?*, not *commit?* — so
the page and the agent are one voice and there is no second vocabulary to keep
in step. It reaches the agent where decision 19 says everything does: the
space's own `CLAUDE.md` and skills, discovered and never declared by the
console. Existing spaces receive it through **update** (ADR 0026). The commit
message the agent then writes stays exact.

**3. A new model opens on the agent's interview, in plain words.** *How big is
it in real life? Where will it be seen?* — not *anchor*, *tolerance*,
*triangle budget*. Tolerances and the budget become the agent's proposals,
flagged as its own, which rule 1 already asks of every number the agent
chose. A change to the new-space prompt only; the page gains nothing. A
structured intake card was considered and not chosen: the interview already
exists and a second way in would be a second thing to keep in step.

**4. The verdict is on the console's page, beside the build label, and never
on the sheet.** Green is one quiet line, *matches the spec*. Red names each
failing check as one plain sentence — what, measured, wanted — from a wording
table keyed by check id; passing checks stay collapsed. Decision 13's refusal
to overlay a failure on the sheet stands: a check knows a number, not a place.

**5. Export has two ways in and one result.** A button on the console runs
`contour export` directly, spawning `./contour` as the console already does —
no agent turn, offered only when the last build is green, and disabled during
a run, since export takes the hold. The agent may still export inside a run,
where it is a `build`-category call and gated like one. Either way one card
shows the file: who exported it, the **round-trip** as *checked: it reopens the
same as it was built*, Download, Show in Finder, and *older than the last
build* when it is. A lobby download was rejected: the lobby cannot say whether
a file matches the build without reading each space.

**6. A gate says the act and what changes, and a build gate can be allowed for
good.** A spec change shows *seat depth 600 → 640 mm, measured on span m4*.
Build gates add *Always for this model*, which writes this space's ask-list
entry as the user's own act from the page — the per-space list replaces the
global one whole, so what is written is the resolved list plus `build`, never
`build` alone. Spec writes, reference writes and saving a version always ask;
push is never offered. Every *Always* is listed on the page with an undo.

This is decision 36 kept, not reversed. The list is still an allow-list with no
presets and silence still means ask; the user still decides each category. What
changes is where they decide it: decision 36 accepted that *the first session is
spent writing the file*, and for a person who cannot edit YAML that session
would never end. Builds unwatched by default was rejected because it is a
preset.

**7. The vetoes count leaves the page.** Decision 33's visible *n vetoes
uncommitted* is a sentence about commits, and commit is hidden. A veto still
rides the commit carrying the change it prevented, and the next *Save this
version* carries it as before; nothing counts it on the page. The panel becomes
*You said no to*, each line the gate's plain act and the user's reason, and
*promote to a mark* becomes *Pin this to a part*. The residual risk decision 33
stated — `git checkout .` loses uncommitted vetoes — is unchanged, and now not
signposted.

**8. The transcript shows activity, not calls.** The agent's words as they
are; each tool call becomes one plain activity line — *Changed the build
script*, *Built the model — 2 things don't match* — with the raw call one click
away, and consecutive quiet calls fold into one. Hiding calls entirely was
rejected: work visible between the agent's messages is what makes the console a
control surface rather than a progress bar.

**9. Spend is a quiet line.** *12 turns*, and, when gates cost turns, *3 stops
cost 4 extra turns* — linking to decision 6's list, which is decision 37's
*informed act* made one click long. Tokens sit behind it. Still a measurement
and never a limit. A money estimate was rejected: it is wrong for a
subscription and would replace the accounting's own units.

**10. A lobby row is a picture and a verdict.** The last sheet as a thumbnail,
or a reference before the first build; the name; the verdict in decision 4's
words; when it was last worked on; Open. Rename, *a new model from this one*
and delete move to a menu. Toolkit and commits are hidden. Health appears only
when something is wrong: *needs an update*, with the action ADR 0026 decides,
or a remote, which a model must never have.

**11. The connector answers in the same words, and a pasted picture opens the
drop form.** ADR 0024 decision 4's instructions gain a line saying the user
reads its answers as a page reads, in plain words, and `status` returns
decision 4's sentences beside the report lines. Decision 10's *ask for the
file's path* becomes: say a pasted picture cannot be kept as the file, and
open the lobby with the create form ready and the name filled in, where the
file itself can be dropped. A path offered is still taken.

**12. The pages share one stylesheet and a way back.** One stylesheet, served
by both hosts, holds the tokens, the type, the buttons and the verdict's
styles. Every page carries the same thin header — *Models › oak-chair* and the
verdict — and *Models* returns to the lobby, starting one if none is running.

## Consequences

- Most of this is wording, and wording needs a table: one per check id (4), one
  per tool and command (8), one per category (6, 7). Three tables, one owner, or
  the tiers drift page by page.
- The developer hears plain words too. The exact vocabulary stays where
  precision is the point — code, ADRs, commit messages — and in conversation
  between developers about the toolkit.
- `CLAUDE.md` changes in the template, so decision 2 reaches an existing space
  only through ADR 0026. Until it does, that space's agent speaks the old way.
- The console gains its first action that is not driving the agent. It is
  `./contour`, spawned, as everything the console does is.

## Rejected

- **A second, plain set of pages beside the exact ones.** Two pages for two
  audiences is ADR 0019's *bundler with a delay*, twice.
- **Glossary words on every page with a tooltip.** The *shown* tier does this
  for the words worth learning; for the rest it teaches a vocabulary of
  machinery to someone who never needs to operate it.
- **A console-only voice, by hook or by prompt.** A `SessionStart` hook keyed
  on `$CONTOUR_RUN` would keep two voices in step; a console system prompt
  reverses decision 19.
