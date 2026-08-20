# 🛡️ OPERATION SHIELDBREAKER — Challenger Briefing

Welcome, operator. This is your mission briefing. **No solutions below** — just what you need
to start the engagement like it's a real one. Read [`DEBRIEF.md`](DEBRIEF.md) only if
you're truly stuck, want to check your work, or — after you've solved it — want the lesson
spelled out (what to actually pay attention to, and why the fix isn't just "change the string").

---

## Rules of Engagement

- Everything runs **locally** — `http://localhost:8000`. Attack it however you'd attack a real
  target: Burp Suite, `curl`, `ffuf`/`dirb`, Python `requests`, `hydra` — your call.
- Each operation is **one WSTG test case**. Work it the way you would on a real engagement:
  recon first, then exploit.
- Flags look like `R6S{...}`. Capturing one **auto-unlocks the next operation** on the Command
  screen (`/`) — you don't need to do anything else, just refresh Command.
- Don't skip ahead by reading the source (`app.py`, `templates/`) unless you're ready to treat
  this as a whitebox exercise instead of blackbox. Playing it blackbox first is the point.

---

## Start here

```bash
docker compose up --build      # from the repo root
```
Then open **`http://localhost:8000`** — that's **Command**, your mission board.

Only **Operation 01** is visible right now. That's intentional — the rest are classified until
you clear it.

---

## 🎯 Operation 01 — Callsign Recon

**Attacker:** IQ &nbsp;⚔&nbsp; **Defender:** Mute
**Target:** `http://localhost:8000/op1/`

### Mission

Rainbow-Corp runs a **Secure Operator Portal**. You have **no valid credentials** and **no
confirmed user list** — only a directory of *candidate* callsigns compiled from OSINT-style
recon (naming convention guesses, common defaults, partial leaks). Your job:

1. **Determine which candidate callsigns are real accounts** on the portal.
2. **Identify which one is the high-value target** — the site administrator.
3. **Recover the flag** from that account.

### What you're given

A candidate wordlist — like a real recon deliverable, most entries are noise:

```
wordlists/callsigns.txt      # ~39 candidate callsigns, most are fake
```

### Where to look

The portal has a login form (`/op1/login`) and a password-recovery flow (`/op1/reset`). Real
authentication systems often behave *slightly* differently depending on whether an account
exists — that's usually where enumeration lives. Compare responses carefully: message text,
status codes, response timing, and what each flow tells you when you feed it a name from your
wordlist.

You do **not** need a valid password to complete this operation.

---

## 💡 Hints (progressive — open only if stuck)

<details><summary>Hint 1</summary>

Submit a login for `admin` and separately for a wordlist entry you suspect is real. Read the
two error messages **character by character**. WSTG calls this class of bug "Account
Enumeration" — the fix is always a single generic message; the bug is when it isn't.
</details>

<details><summary>Hint 2</summary>

Script the login form against the whole wordlist and watch for **any** response that differs
from the baseline — text, length, status code, or timing. You should end up with a short list
of confirmed-valid callsigns.
</details>

<details><summary>Hint 3</summary>

Once you have valid callsigns, don't stop at the login form — the **password recovery** flow
(`/op1/reset`) is a separate attack surface and often leaks differently (or more) than login
does. Try every valid callsign there.
</details>

<details><summary>Hint 4</summary>

One of your valid callsigns is not like the others — the recovery response for the actual
administrator account contains something the rest don't. That's your flag.
</details>

---

## 🎯 Operation 02 — Breach & Clear

**Attacker:** Sledge &nbsp;⚔&nbsp; **Defender:** Castle
**Target:** `http://localhost:8000/op2/` (unlocks after Op01)

### Mission

Recon is done — from Operation 01 you know the admin is **`g.mendel`**. Now you break in for
real. The **Operator Console** login has **no account lockout and no CAPTCHA**, so nothing stops
you from guessing forever. Rainbow-Corp has a company-wide password format, published right on
the account-provisioning page. Your job is to read that format precisely, and use it to build a
candidate list that is *guaranteed* to contain the real password.

1. **Find the exact password format** Rainbow-Corp enforces (not just "must be strong" — the
   *precise* structure).
2. **Get a small list of company/target words** and generate every candidate the format allows.
3. Get past the two things that stop a *naive* attack (a hidden token, and no obvious success
   message), and run your full candidate set against `g.mendel`.
4. Reach the console and capture the flag.

This is **not** a guessing exercise. Read the format precisely enough and your candidate list
is complete — the real password is mathematically guaranteed to be in it. Nothing here rewards
a lucky pick; it rewards reading the rule correctly and enumerating it fully.

### What you're given

```
wordlists/op2_base_words.txt     # ~35 words profiled from the company/target.
                                 # Not full passwords — you build the shape yourself
                                 # from the format you find, applied to these words.
```

### Three things the login does *not* make easy

- **The format looks like a vague "strong password" policy at a glance — it isn't.** Go read
  it carefully (`/op2/register`, and its page source/JS). It is far more specific than
  "contains upper/lower/digit/symbol." Get the *exact* shape — including how many digits, and
  exactly which symbols are allowed — or your candidate list will be incomplete and you'll miss
  the real password even after trying thousands of guesses.
- **A hidden token in the form.** Fire raw login POSTs and they'll all be rejected *before*
  your password is even checked — so "0 hits" can mean "none of my requests were even valid,"
  not "password not in list." Inspect the login form's fields and work out what the server
  expects on every submission.
- **No "Error" keyword to grep.** Op01 told you success/failure in the page text. This one
  doesn't. Don't *assume* what success looks like — **measure it.** Send one login with a
  password you *know* is wrong, record exactly what that failure looks like (status code,
  response size, whether it redirects), then treat *any* response that differs from that
  baseline as a possible hit.

### A second, separate finding to poke at

Try submitting a password to `/op2/register` that the displayed format says it shouldn't
accept. That's a distinct ATHN-07 finding (client-side-only enforcement) — and it's *why* you
can trust the format itself: it's real company policy, just not actually checked server-side.

---

## 💡 Op02 Hints (progressive — open only if stuck)

<details><summary>Hint 1 — reading the format precisely</summary>

`/op2/register` shows a checklist, but the real rule lives in the page's JavaScript (view
source). Find the regular expression that decides whether the submit button unlocks. A regex
is unambiguous — it tells you exactly how many digits are required (not "at least one" —
*exactly* how many) and exactly which symbol characters are allowed (a short, closed list, not
"any special character"). Write down the precise shape before you generate anything.
</details>

<details><summary>Hint 2 — turning the format into a complete list</summary>

Once you have the exact shape (e.g. `Word` + a fixed number of digits + one symbol from a small
fixed set), the candidate space is just a cross-product: **every base word × every digit
combination in that range × every allowed symbol.** Generate *all* of it, not a sample. Because
the format is exact and closed, this full set is guaranteed to contain the real password — you
don't need to pick which digits or symbols "seem likely."
</details>

<details><summary>Hint 3 — the token</summary>

The login form has a hidden `csrf_token` field tied to your session. Every POST to `/op2/login`
must include a valid one or you get `400 Session expired` — your password never even gets
checked. The pattern: **GET `/op2/` first (in a session that keeps cookies), scrape the token,
then reuse it on your POSTs.** It doesn't rotate per attempt, so grab it once and run the list.
</details>

<details><summary>Hint 4 — detecting success without assuming what it looks like</summary>

Don't hardcode "success = 302" or "success = some word" — you don't know that in advance, and
assuming it *is* a form of guessing. Instead: send one attempt with a deliberately wrong
password and record its **fingerprint** — status code, response length, and `Location` header.
Then flag any candidate whose fingerprint **differs** from that baseline. (Use "don't follow
redirects" so a redirect shows up as a difference.) In Burp Intruder this is the same move:
run the list, sort by length or status, and look for the one row that doesn't match the crowd.
`solvers/op2.py` shows the full version if you want to compare after you've done your own.
</details>

---

## 🎯 Operation 03 — Hard Breach

**Attacker:** Dokkaebi &nbsp;⚔&nbsp; **Defender:** Clash
**Target:** `http://localhost:8000/op3/` (unlocks after Op02)

### Mission

The web console is behind you — Rainbow-Corp also runs a **Perimeter Access Terminal**
(think: a physical door keypad) for the same confirmed operator, `g.mendel`. It's guarded by a
**4-digit access code** and, on every single attempt, a **math verification challenge** that
changes each time — not just the numbers, the *operation itself* varies too. There is **no
account lockout** — the challenge is the *only* thing standing between you and the door.

1. **Work out what the verification challenge actually is**, and whether a script can solve it
   — for *any* operation it might throw at you, not just one.
2. **Get your request shape right** — the challenge is single-use, so it has to be handled
   correctly on *every* attempt, not just once.
3. **Brute-force the access code.** It's a plain 4-digit number: `0000`–`9999` — 10,000
   possibilities, fully bounded, nothing to guess about the shape of it.
4. Reach the terminal console and capture the flag.

### Two things to test — this mission has two independent bypasses

- **Is the challenge actually hard?** Look at what it presents you with. If it's something a
  simple script can resolve on its own without any external help, solving it programmatically
  removes it as a control entirely — no different from it not being there.
- **Is the challenge actually *required*?** Don't just solve it — also test what happens if you
  simply don't send an answer at all. Many real implementations of "verify this value" logic
  have a bug lurking in how they handle a *missing* value, as opposed to a *wrong* one. Those
  are two different code paths, and it's worth checking both.

---

## 💡 Op03 Hints (progressive — open only if stuck)

<details><summary>Hint 1 — the challenge itself</summary>

View the terminal page's source. The "verification challenge" is plain arithmetic, rendered as
plaintext HTML (`4821 + 3912 = ?`, or `9924 - 3881 = ?`, or `5303 * 5070 = ?` — the numbers and
the operator both vary). There's no image, no distortion, nothing hidden — a script can read the
numbers *and the operator* straight out of the page and compute the answer itself, whichever of
the three shows up. Notice the operands are 4-digit numbers, not single digits — that makes the
challenge *look* more serious, but ask yourself honestly whether it changes anything for a
script versus a human trying to solve it in their head.
</details>

<details><summary>Hint 2 — don't hardcode the operator</summary>

If your script assumes every challenge is addition, it'll get roughly 2 in 3 wrong. Parse
whichever symbol is actually shown and act on it — don't just extract the two numbers and add.
</details>

<details><summary>Hint 3 — it's single-use</summary>

Solve one challenge and it won't work for your next attempt — a new one is generated after
every response, success or failure. So your automation can't solve once and replay; it has to
**fetch a fresh challenge immediately before every single submission.**
</details>

<details><summary>Hint 4 — the brute force itself</summary>

With the challenge handled, the access code is just `0000` through `9999` — generate all 10,000
and try each one. There's no lockout, so nothing stops a full sweep; a script that fetches a
challenge, solves it, and submits a candidate code in a loop will get there.
</details>

<details><summary>Hint 5 — the second bug (don't stop after the first solve)</summary>

Try a request that omits the challenge-answer field completely — not a wrong answer, no field
at all. Compare that response to one with a deliberately *wrong* answer. If they behave
differently, you've found a second, separate bypass — and it might mean you never needed to
solve any math in the first place.
</details>

---

## 🎯 Operation 04 — Lockdown Failure

**Attacker:** Thermite &nbsp;⚔&nbsp; **Defender:** Oryx
**Target:** `http://localhost:8000/op4/` (unlocks after Op03)

### Mission

Same confirmed operator, `g.mendel`, on yet another system — the **Operator Console**. This one
has a real, working account-lockout mechanism, unlike the previous three operations. It genuinely
tracks repeated failed logins against this exact account and **does something** once you cross
its threshold.

There is **no password to find here.** The real one is random and was never disclosed to
anyone, on purpose — don't waste time trying to crack or guess it. The entire mission is about
one question: **what actually happens when the lockout mechanism triggers?** "It locks the
account" is the assumption. Test it.

1. **Attack the account on purpose** — submit wrong passwords repeatedly and deliberately.
   You're not hunting for the right one; you're trying to *reach the threshold*.
2. **Watch the responses as you go.** Real lockout testing means paying attention to *when*
   and *how* the behavior changes, not just spamming blindly — OWASP's own methodology for this
   test is literally "try 3, try 4, try 5... and see what's different each time."
3. Once something changes, **work out exactly what changed** — and try the one thing an
   attacker doesn't normally think to submit.

### What you're given

Nothing extra — no wordlist, no token to manage. This mission is entirely about *behavioral
observation*: sending requests and reading what comes back closely enough to notice the moment
the server's behavior shifts.

---

## 💡 Op04 Hints (progressive — open only if stuck)

<details><summary>Hint 1 — don't look for a password</summary>

Seriously — there isn't one to find. `g.mendel`'s real access code on this system is random and
was never given to you or hardcoded anywhere findable. If you're building a wordlist for this
mission, you're solving the wrong problem. The vulnerability isn't in what the password is.
</details>

<details><summary>Hint 2 — attack the account on purpose, and keep count</summary>

Submit wrong passwords against `g.mendel` in a loop — dozens of them, back to back. Print or log
the response text for every single attempt as you go. You're looking for the *response itself*
to change at some point, not for a login to succeed.
</details>

<details><summary>Hint 3 — the response changes more than once</summary>

There isn't just one behavior shift — there are two, at different points as your failure count
climbs. The first one is a **decoy**: it tells you something happened server-side, but it is not
itself exploitable. Don't stop there. Keep going until you see a *second*, different message.
</details>

<details><summary>Hint 4 — the second shift is the real one</summary>

When the message changes a second time, that's the lockout mechanism actually firing. The
assumption is "now the account is locked." Test that assumption directly: what happens if you
try to log in right now — not with a guess, but with **nothing at all in the password field**?
</details>

---

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

## 🎯 Operation 06 — Back Door (Finale)

**Attacker:** Nomad &nbsp;⚔&nbsp; **Defender:** Kaid
**Target:** `http://localhost:8000/op6/` (unlocks after Op05)

### Mission

Same confirmed operator, `g.mendel`, on the **Operator Console** — but this time, read the login
page carefully. It advertises exactly what it fixed: generic error messages, a real account
lockout, rate limiting. If you've done Operations 01–05, you'll recognize every one of those as
a direct fix for something you already broke. **This console is not lying to you. It's actually
hardened.**

You are given a candidate password list. Use it.

1. **Test the web console's claims for real** — attack it with the provided wordlist and see
   what actually happens. Don't assume the banner is telling the truth *or* lying; verify it.
2. **Notice what that test just told you** — and don't walk away thinking the mission is a dead
   end. Every account is reachable through more than one door. Find the other one.
3. **Run the exact same wordlist against whatever you find.** The interesting result isn't a new
   password — it's what changes when you point the same attack at a different channel.

### What you're given

```
wordlists/op6_passwords.txt      # ~30 candidate passwords. The real one is in here.
```

### One thing worth sitting with before you start

This is the last operation. Every prior lesson is still true here — enumeration, dictionary
attacks, reading page source for what's not rendered, checking whether a control that *looks*
correct actually *is*. Nothing new needs inventing. The only new question is: **is this the only
place this account can be reached from?**

---

## 💡 Op06 Hints (progressive — open only if stuck)

<details><summary>Hint 1 — take the hardening seriously, and test it</summary>

Actually run the wordlist against `/op6/login`. Don't skip this step assuming it won't work —
*watching* it fail, and specifically *how* it fails, is informative. Pay attention to the exact
HTTP status code you get back once something changes.
</details>

<details><summary>Hint 2 — a real lockout looks different from Operation 04's</summary>

If you hit a wall partway through the list, ask: is this the *same kind* of wall as Operation
04, or a different one? Try the account's real credentials (if you ever find them) against this
console after the wall appears. The answer to that test tells you whether this lockout is
"broken like before" or "actually working this time."
</details>

<details><summary>Hint 3 — the account isn't only reachable from here</summary>

You already know this technique from Operation 05: **View Source** on the login page, don't just
read what's rendered. Look for anything that reads like an internal note — a comment a developer
left in that was never meant to ship, describing something *else* that also talks to this
account.
</details>

<details><summary>Hint 4 — same list, different channel</summary>

Once you've found the alternative channel, don't build a new wordlist — run the **exact same
one** against it. It's a JSON API, not an HTML form, so your requests need to look different
(`Content-Type: application/json`, a JSON body), but the credentials you're trying are identical.
Compare how many attempts each channel lets you make before something stops you — or doesn't.
</details>

---

## Reporting (optional, but do it like a real test)

For each operation, once solved, jot down:
- **Finding** — what's actually broken (one sentence)
- **Evidence** — the request/response pair that proves it
- **CWE / WSTG ID** — printed on the mission card at Command
- **Impact** — what an attacker gains
- **Fix** — how you'd remediate it

This is what turns "I got the flag" into an eWPTX-relevant skill.

---

Good luck, operator. Command is waiting. 🎮
