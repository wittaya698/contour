# 01 — The canvas server authenticates

**Type:** AFK · **Source:** ADR 0019 decision 39

## What to build

`contour canvas` serves state-changing POSTs on localhost with no authentication
today. *Localhost is private* is false for a server that takes them: a page on
any site can send a simple cross-site POST without a preflight, and DNS
rebinding defeats a hostname check used alone.

Four mechanisms, all in the launcher's own server so the console inherits them
rather than reimplementing them:

- a per-session secret, minted at startup, carried in the URL the command opens,
  and checked on every request
- an explicit bind to `127.0.0.1`
- an `Origin` / `Sec-Fetch-Site` check
- a required JSON content type, so a simple cross-site POST cannot reach a
  handler at all

This changes shipped behaviour. The blast radius today is why the gap was
acceptable — an unauthenticated mark is noise that gets noticed and deleted. It
stops being acceptable the moment the same server carries an *allow*, which is a
spec write or a commit the user did not make, arriving through the one mechanism
built to prevent exactly that.

A Unix socket would isolate better and is not available: browsers cannot connect
to one, and the point is a page.

## Acceptance criteria

- [x] A request without the session secret is refused, GET and POST alike
- [x] A POST with a non-JSON content type is refused before any handler runs
- [x] A POST carrying a foreign `Origin` is refused
- [x] The server binds `127.0.0.1` explicitly, not all interfaces
- [x] The secret differs between two runs of the command
- [x] `contour canvas` still works end to end: the page opens, a mark round-trips
      to disk, the command prints its report and exits
- [x] The secret never reaches a log or the terse report

## Blocked by

None — can start immediately. Worth having whether or not the console ever ships.
