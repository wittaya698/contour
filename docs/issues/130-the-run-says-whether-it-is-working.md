# 130 — The run says whether it is working

**Type:** AFK · **Source:** design session 2026-10-17; ADR 0019, decision 4

## What to build

Between events the page looks frozen. The line under the transcript says
*running* only on the tab that started the run. A reload mid-run says *no run
yet*, and nothing tells a slow run from a stuck one. That line becomes one of
three states:

| State | When | Shows |
|---|---|---|
| Working | a run is live and nothing waits on you | a dot in `--agent` with a gentle pulse, *Claude is working*; after 15 s with no event, *Claude is working · quiet for 40s* |
| Waiting for you | a gate or question is open | a dot in `--pin` that does not pulse, *Waiting for you: answer above* |
| No run | nothing live | muted text, no dot |

- **The state comes from the events, not from the tab.** A `prompt` with no
  `ended` after it is live, and a gate with no verdict is open. A reloaded tab
  replays the run (issue 127), so it gets the state right too.
  As built, the console says the state with every page of the transcript
  (`now` on `/events`) and the page draws it: testable without a browser, as
  issue 128's tree is, and still not the tab's. The run is over once `ended`
  is on the transcript, though its thread is still winding down.
- **It does not name what the agent is doing.** The page cannot tell a tool
  running from the model thinking, since a call's result makes no event. The
  last activity line is already right above.
- **"quiet for" is a measurement and never a verdict:** no colour change, no
  warning, nothing ends. This is the idle timeout's symmetry, and spend's.
- **Under `prefers-reduced-motion` the dot does not pulse.**

ADR 0019 decision 4 still holds: this says whether the run is working, never
how far along it is.

## Acceptance criteria

- [x] A page reloaded mid-run shows *Claude is working*, not *no run yet*
- [x] A page reloaded while a gate waits shows *Waiting for you*, with no pulse
- [x] After 15 s without an event the line adds *quiet for N s*, and nothing else changes
- [x] An `ended` event returns the line to *no run*
- [x] Under `prefers-reduced-motion` the dot is still

## Blocked by

None - can start immediately
