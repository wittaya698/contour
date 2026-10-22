# 147 — The agent's questions are a form

**Type:** AFK · **Source:** ADR 0034, decisions 1–3 — [The agent's questions are a form](../adr/0034-questions-are-a-form-the-chat-can-fill.md)

## What to build

The agent asks with `ask`, and the console page shows its questions as a form
with every field already filled. No MCP yet: this is the console and its page.

- **`ask`, a console tool** beside `spec_write` in `console/run.py`. Each
  question has `question`, `suggested`, `basis` and optionally `is_size`.
  A suggestion without a basis is refused. So is a second `is_size` question.
- **`AskUserQuestion` is refused under a console**, with *under this console a
  question is asked with `ask`*, as a spec write made another way is.
- **The form on the console page.** One field per question, prefilled, each
  labelled *Claude's guess*, *from the chat* or *yours*; an edit makes it
  *yours*. The basis shows under the field. One Approve.
- **Attended:** the run waits at the form, and Approve hands it the answers.
  **Unattended:** the form is set aside as a question is today (ADR 0028
  decision 2), and approving it starts a run whose first message is the
  questions and the answers.
- **The approved answers are kept with their sources** in `.contour/`, beside
  `approvals.json`, for 148 to read.
- **The new-space prompt says to ask with `ask`**, never in a closing.

## Acceptance criteria

- [ ] An `ask` with a suggestion and no basis is refused, and nothing waits
- [ ] `AskUserQuestion` under a console is refused and names `ask`
- [ ] The page shows each question prefilled and labelled *Claude's guess*; an edited field says *yours*
- [ ] Approve under an attended run hands the run every answer with its source
- [ ] An unattended run's `ask` is set aside, and approving it starts a run with the questions and answers
- [ ] The approved answers and their sources are on disk after Approve
- [ ] Looked at in a real console: a new space's questions arrive as a form, not prose

## Blocked by

- 146
