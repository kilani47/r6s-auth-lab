## 🎯 Operation 05 — Ghost in the Panel

**Attacker:** Blitz &nbsp;⚔&nbsp; **Defender:** Aruni
**Target:** `http://localhost:8000/op5/panel` (unlocks after Op04)

### Mission

There's a restricted **Operator Command Panel**. There is **no login form anywhere in this
mission.** Read that twice — you will not find a username/password box to attack. Access to the
panel is controlled by *something else entirely*, and your job is to work out what, then supply
it yourself without ever authenticating through any conventional flow.

1. **Visit the panel directly.** It'll refuse you — read exactly *how* it refuses you, and think
   about what that implies about how it decides who's allowed in.
2. **Inspect what a "logged in" state would actually look like from the client's side** — every
   piece of state your browser holds after a real login (cookies, headers, local storage) is
   worth examining, because one of them might be *all* the server actually checks.
3. **There's a second, completely independent way in, too** — this app has more than one
   endpoint, and not all of them are linked from anywhere you can click. Go looking.

### What you're given

Nothing — no wordlist, no credentials, no hints about specific paths beyond the panel itself.
This mission is pure **Burp/curl territory**: inspect, hypothesize, tamper, retry.

---

## 💡 Op05 Hints (progressive — open only if stuck)

<details><summary>Hint 1 — read the denial message literally, then read the page's actual source</summary>

The panel doesn't say "invalid credentials" or "access denied" — it says something more
specific. That specific wording is a clue about *what the server is actually checking for*, not
just that a check failed. Don't stop at the rendered page, either — **View Source** (or
`curl` it directly) on the denial response. Rendered HTML and raw HTML are not the same
document; things get left in the source that never show up on screen.
</details>

<details><summary>Hint 2 — cookies aren't just for sessions</summary>

A real login usually leaves you holding some kind of token afterward — most commonly a cookie.
Ask yourself: does this app's protected page verify that cookie *cryptographically* (a signed
session it can trust), or does it just check that *a cookie with a certain name showed up at
all*? Those are very different levels of security, and only one of them requires you to have
ever actually authenticated. You should be able to find the **exact** cookie name this check
relies on without guessing it — it's sitting in the response somewhere, if you know to look
past what's rendered on screen. Once you have it, set it by hand (Burp, or `curl -b`) and see
what happens.
</details>

<details><summary>Hint 3 — the second path: nothing is ever really deleted</summary>

Real applications accumulate leftovers — setup scripts, install wizards, admin bootstrapping
tools — that get used once during deployment and then, in theory, get removed or locked down.
In practice, that second step is often skipped. Try forced-browsing this app for common
leftover-endpoint names (a standard wordlist like `dirb`'s default list, or a quick manual guess
at words like "install" or "setup," will get you there). Nothing in the UI links to it.
</details>

<details><summary>Hint 4 — confirm the two paths are actually independent</summary>

Once you've found both ways in, verify they really are separate bugs and not the same one wearing
two names — try each on its own, in a fresh session/incognito window, without the other. If both
work standalone, you have two distinct findings to report, not one.
</details>

---
