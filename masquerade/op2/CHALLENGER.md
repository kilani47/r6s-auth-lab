# 🎭 Masquerade Operation 02 — Stolen Keys

**Attacker:** Zero &nbsp;⚔&nbsp; **Defender:** Vigil
**WSTG:** WSTG-SESS-03 — Testing for Session Fixation
**Target:** `http://localhost:8000/masquerade/op2/` (unlocks after Operation 01 is cleared)

**No solutions below.** Read [`DEBRIEF.md`](DEBRIEF.md) only once you're stuck, want to check
your work, or want the lesson spelled out after solving.

---

## Mission

**Meridian Tower** runs a guest portal for the hotel occupying its upper floors. Unlike Operation 01, this mission isn't about
reading or tampering with what's *inside* a session token — it's about a much simpler
question:

> **When does the server hand you a session identifier, and when — if ever — does it change?**

You have a real, working guest account, given to you directly below. This mission isn't about
cracking a password. It's about *timing*.

### What you're given

```
Guest ID: guest.stay
Password: Meridian2024!
```

### Objectives

This mission only makes sense once you stop thinking of it as one continuous login and start
thinking of it as **three separate visits, playing two different roles** — because that's
exactly what a real fixation attack looks like: an attacker sets something up, an unrelated
victim unknowingly triggers it, and the attacker walks in later without ever touching the
victim's password. Play all three, in order, on your own account:

**Phase 1 — you, as the attacker, plant a card.** Visit the guest portal *before* logging in
and note exactly what the server hands you, even unauthenticated. Then, separately, deliberately
choose your **own** identifier — invent it yourself, don't just reuse the server's — and make
sure it's the one attached to the browser/request you're about to use next.

**Phase 2 — you, as the victim, check in normally.** Submit the real, legitimate credentials
given below, in a request that's still carrying the identifier you chose in Phase 1. This step
is completely ordinary from the victim's side — a real victim has no idea anything's wrong,
because nothing about the login itself looks unusual.

**Phase 3 — you, as the attacker, come back later — with *nothing but the identifier*.**
This is the step that actually proves the vulnerability, and it's the one it's easiest to skim
past: open a **separate** request — a different tool, a fresh `curl`, an incognito tab, anything
that starts with no prior login state — present **only** the identifier from Phase 1, and go
**straight to My Reservation**. Do not submit a username. Do not submit a password. Do not touch
the login form at all in this step. If you reach an authenticated account this way, you've just
demonstrated the entire attack: the account was accessible to someone who never once provided a
credential.

There's a second, smaller finding sitting right next to the first one — the checklist in your
course notes calls it out specifically as its own testable item. Don't stop looking the moment
you find the first way in.

---

## Rules of Engagement

Attack it however you'd attack a real target: Burp Suite, browser DevTools, `curl`, Python
`requests`. You do **not** need a second person or a second real account — WSTG-SESS-03's own
testing methodology is built to be verified with a *single* test account, played across the
three phases above. You *do* need Phase 3 to happen as a genuinely separate request with no
carried-over login state — a second `curl` invocation, a fresh `requests.Session()`, or an
incognito tab all work fine; reusing the same authenticated browser tab you just logged in with
proves nothing, because of course a tab you're already logged into stays logged in.

Don't skip to reading `app.py`. This is a timing question — you have to actually watch what the
server sends across the login boundary to answer it.

---

## 💡 Hints (progressive — open only if stuck)

<details><summary>Hint 1 — look before you log in</summary>

Open the guest portal in a private/incognito window (or clear cookies first) and check
DevTools → Application → Cookies *before* you type anything into the login form. There's
already a cookie there. Write its exact value down.
</details>

<details><summary>Hint 2 — log in without losing it</summary>

Submit the login form normally, in that same browser session, then check the cookie again.
Has the value changed? Your course notes have a name for what it means if it hasn't: the
server never *regenerated* the session identifier at the moment it mattered most.
</details>

<details><summary>Hint 3 — turn an observation into an attack</summary>

If the identifier survives login unchanged, then the server never needed to issue you anything
new — it just started trusting whatever identifier you already had. That means the identifier
doesn't have to originate from the server at all. What happens if you manually set the cookie
to a value **you** invented, *before* submitting the login form, and then log in?
</details>

<details><summary>Hint 4 — Phase 3 has to be a genuinely separate request</summary>

If you check the reservations page in the *same* browser tab you just logged in with, you'll see
it worked — but that doesn't prove anything a normal login wouldn't. Of course a tab you're
logged into stays logged in. The proof is doing it from somewhere that was never logged in at
all: a brand-new `requests.Session()`, a second `curl` call, an incognito tab. Present *only* the
identifier from Phase 1 there — no login form, no credentials — and go straight to My
Reservation. Compare that against reaching the same page with zero identifier at all (a totally
fresh visitor). The app is explicit about the difference between "not checked in" and "checked
in, but this doesn't prove anything yet" — read both responses carefully.
</details>

<details><summary>Hint 5 — the second finding is hiding in how the identifier gets attached</summary>

A cookie isn't the only way a value travels with a request. Your notes' root-causes checklist
lists a second place a session identifier is sometimes accepted from. Try the guest portal's
URL directly with that identifier appended as a query parameter instead of setting a cookie at
all.
</details>

---

## Reporting

Once solved:
- **Finding** — what's actually broken, one sentence
- **Evidence** — the identifier value chosen in Phase 1, and a request/response pair from Phase
  3 showing it reached an authenticated page with no credentials submitted in that request
- **WSTG ID** — WSTG-SESS-03 (printed on the mission card at Command)
- **Impact** — what an attacker can do by getting a target to authenticate on an
  attacker-chosen identifier, before the target ever logs in, and never needing that target's
  credentials themselves
- **Fix** — how you'd remediate it

Good luck, operator. Command is waiting. 🎭
