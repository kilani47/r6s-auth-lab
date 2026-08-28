# 🎭 Masquerade Operation 02 — Stolen Keys

**Attacker:** Zero &nbsp;⚔&nbsp; **Defender:** Vigil
**WSTG:** WSTG-SESS-03 — Testing for Session Fixation
**Target:** `http://localhost:8000/masquerade/op2/` (unlocks after Operation 01 is cleared)

**No solutions below.** Read [`DEBRIEF.md`](DEBRIEF.md) only once you're stuck, want to check
your work, or want the lesson spelled out after solving.

---

## Mission

**Meridian Tower** runs a guest portal for the hotel occupying its upper floors. Unlike
Operation 01, this mission isn't about reading or tampering with what's *inside* a session
token — it's about a much simpler question:

> **When does the server hand you a session identifier, and when — if ever — does it change?**

You have a real, working guest account, given to you directly below. This mission isn't about
cracking a password. It's about *timing* — and, this time, about a real second party: the front
desk is expecting an actual VIP arrival today, and the portal will let you hand that guest a
card number of your choosing *before they ever check in*.

### What you're given

```
Your Guest ID: guest.stay
Your Password: Meridian2024!
```

That's a real, working login — but it's not how you win this one. It's there so you can confirm
what *normal, honest use* of the portal looks like, which matters later.

### Objectives

1. **Establish the baseline.** Log into your own account normally. Note what the reservations
   page looks like when everything about your session is completely legitimate.
2. **Choose a card number.** Not one the server hands you — one you invent yourself.
3. **Route it to the front desk.** The portal has a second panel below the login form:
   *"Front Desk — Route a Check-In."* Send your chosen card number there. Read carefully what
   the app tells you happens next, and to whom.
4. **Come back for it — with nothing but the card number.** Open a request that has never
   logged in — a private/incognito tab, a fresh `curl`, a new `requests.Session()` — and present
   *only* the card number from step 2. No username. No password. Go straight to **My
   Reservation**. If you land on an authenticated account this way, you've just reached
   somewhere you were never given credentials for.

There's a second, smaller finding sitting right next to the first one — the checklist in your
course notes calls it out specifically as its own testable item. Don't stop looking the moment
you find the first way in.

---

## Rules of Engagement

Attack it however you'd attack a real target: Burp Suite, browser DevTools, `curl`, Python
`requests`. Step 4 has to be a genuinely separate request with no carried-over login state — a
second `curl` invocation, a fresh `requests.Session()`, or an incognito tab all work fine;
reusing the same browser tab you just used for anything else proves nothing, because of course a
tab that's already doing something stays doing it.

Don't skip to reading `app.py`. This is a timing question — you have to actually watch what the
server sends across the check-in boundary to answer it.

---

## 💡 Hints (progressive — open only if stuck)

<details><summary>Hint 1 — look before anyone logs in</summary>

Open the guest portal in a private/incognito window and check DevTools → Application → Cookies
*before* you type anything into either form. There's already a cookie there. That's the card
number you're currently holding — and nothing about the page required you to log in to get it.
</details>

<details><summary>Hint 2 — the front desk panel is not decoration</summary>

Read exactly what it says: it's going to hand *whatever card number you type* to a specific
named guest, before that guest ever checks in. That's not flavor text — submitting that form
really does perform a check-in, on your behalf, for someone else's account. You are never shown
that guest's password, and the form doesn't ask you for it.
</details>

<details><summary>Hint 3 — the card doesn't stop being valid once you're done with it</summary>

After the front desk confirms delivery, that exact card number is now attached to a real,
authenticated account — just not one you logged into. What happens if you set your *own*
browser's cookie to that same value and revisit the portal?
</details>

<details><summary>Hint 4 — step 4 has to be a genuinely separate request</summary>

If you check the reservations page in the same browser tab you just used to send the check-in
link, of course it might look like it worked — but that doesn't distinguish anything. The proof
is reaching it from somewhere that has done *nothing* else first: no cookies, no prior requests,
nothing but the card number. Compare that against reaching the same page with no card at all (a
totally fresh visitor, never sent anywhere). The app is explicit about the difference between
"not checked in" and "checked in, but this doesn't prove anything yet" — read both responses
carefully, and notice whose name ends up on the reservation.
</details>

<details><summary>Hint 5 — the second finding is hiding in how the card gets attached</summary>

A cookie isn't the only way a value travels with a request. Your notes' root-causes checklist
lists a second place a session identifier is sometimes accepted from. Try the guest portal's
URL directly with your card number appended as a query parameter instead of setting a cookie at
all — both for visiting the portal *and* for the front-desk form.
</details>

---

## Reporting

Once solved:
- **Finding** — what's actually broken, one sentence
- **Evidence** — the card number you chose, confirmation the front desk routed it to a real
  guest, and a request/response pair showing that card reached an authenticated page with zero
  credentials submitted in that request
- **WSTG ID** — WSTG-SESS-03 (printed on the mission card at Command)
- **Impact** — what an attacker can do by getting a target to authenticate on an
  attacker-chosen identifier, before the target ever logs in, and never needing that target's
  credentials themselves
- **Fix** — how you'd remediate it

Good luck, operator. Command is waiting. 🎭
