# 🎭 Masquerade Operation 02 — Stolen Keys

**Attacker:** Zero &nbsp;⚔&nbsp; **Defender:** Vigil
**WSTG:** WSTG-SESS-03 — Testing for Session Fixation
**Target:** `http://localhost:8000/masquerade/op2/` (unlocks after Operation 01 is cleared)

**No solutions below.** Read [`DEBRIEF.md`](DEBRIEF.md) only once you're stuck, want to check
your work, or want the lesson spelled out after solving.

---

## Mission

**Coastline Resort** runs a guest portal. Unlike Operation 01, this mission isn't about
reading or tampering with what's *inside* a session token — it's about a much simpler
question:

> **When does the server hand you a session identifier, and when — if ever — does it change?**

You have a real, working guest account, given to you directly below. This mission isn't about
cracking a password. It's about *timing*.

### What you're given

```
Guest ID: guest.stay
Password: Coastline2024!
```

### Objectives

1. Visit the guest portal **before** logging in, and note exactly what the server hands you at
   that point — even though you're not authenticated yet.
2. Log in normally, keeping whatever you were holding from step 1 attached to the request.
3. Compare: is the identifier you're holding *after* login the same one you were holding
   *before* it?
4. If it is — you never needed to be handed anything by the server *after* authenticating at
   all. Figure out what that means if you could get a target to visit the portal using an
   identifier *you* chose, before they ever log in.
5. Prove it: reach **My Reservation** authenticated on a session identifier that originated on
   your side, not the server's.

There's a second, smaller finding sitting right next to the first one — the checklist in your
course notes calls it out specifically as its own testable item. Don't stop looking the moment
you find the first way in.

---

## Rules of Engagement

Attack it however you'd attack a real target: Burp Suite, browser DevTools, `curl`, Python
`requests`. You do **not** need a second browser, a second person, or any kind of victim
simulation — WSTG-SESS-03's own testing methodology is built to be verified with a *single*
test account: you playing both roles, before and after authentication, in sequence.

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

<details><summary>Hint 4 — the portal will tell you if it worked, and if it didn't</summary>

Reach the reservations page two different ways with a self-invented identifier: once without
ever logging in, and once after logging in while presenting that same self-invented value.
Read both responses carefully — the app is explicit about the difference between "not checked
in" and "checked in, but this doesn't prove anything yet."
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
- **Evidence** — the identifier value before login, and confirmation it's still valid *and now
  authenticated* after login
- **WSTG ID** — WSTG-SESS-03 (printed on the mission card at Command)
- **Impact** — what an attacker can do by getting a target to authenticate on an
  attacker-chosen identifier, before the target ever logs in
- **Fix** — how you'd remediate it

Good luck, operator. Command is waiting. 🎭
