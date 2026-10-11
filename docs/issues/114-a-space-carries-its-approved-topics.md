# 114 — A space carries the topics its user approved

**Type:** AFK · **Source:** ADR 0030, decisions 1, 2, 5 and 6 — [topics label a model for finding](../adr/0030-topics-label-a-model-for-finding.md)

## What to build

The thinnest whole path for a **topic**. The agent proposes topics for its
model through one gated call; the page shows them word by word, and the user
approves some and strikes others. Approved words are a tracked record in the
space, saved with the next version like `marks.json`, never in the spec. A
struck word is remembered against the model, with no reason asked, and is not
proposed for it again. The user can add or strike a topic directly, ungated.

In an **unattended run** the proposal is an **approval waiting**: the run goes
on, and the space refuses a new request until it is answered.

## Acceptance criteria

- [x] A proposal of three words, one struck, leaves two topics in the space's record
- [x] A later proposal containing the struck word is refused for that word, and says so to the agent
- [x] The user adds a word the agent never proposed, and strikes an approved one, with no gate
- [x] Unattended, a proposal waits as an approval; a request to the space is refused while it does; answered later on the page, it applies
- [x] `spec.yaml` and its `revision:` are untouched by any of the above
- [x] A topic is not counted, shown or recorded as a veto

## Blocked by

None - can start immediately
