# 🎭 Masquerade Operation 07 — The Second Factor

**Attacker:** Ash &nbsp;⚔&nbsp; **Defender:** Warden
**WSTG:** WSTG-ATHN-03 (Weak Lock-Out) · Bypassing Two-Factor Authentication
**Target:** `http://localhost:8000/masquerade/op7/` (unlocks after Operation 06 is cleared)

**No solutions below.** Read [`DEBRIEF.md`](DEBRIEF.md) only once you're stuck, want to check
your work, or want the lesson spelled out after solving.

---

## Mission

**Kafe Dostoyevsky** fronts a staff operations portal. Signing in takes two things: a staff
password, and a **4-digit one-time code** sent to the on-duty phone. That's two-factor
authentication — *something you know* plus *something you have* — and on paper it means a
stolen password alone gets an attacker nowhere.

You have the password. You do **not** have the phone. The entire mission is getting past the
second factor anyway — and there are **three completely separate ways to do it**, each a real
failure a pentester finds in the field, none of them requiring the others. A real assessment
report would list all three as distinct findings with distinct fixes.

### What you're given

```
Staff ID:  night.duty
Password:  KafeNight2024!
```

A real, working password — first factor already solved. It "sends" a one-time code to a device
you can't see. Everything interesting is what happens next.

---

## Objectives

### Stage 1 — Outlast a code that never gets tired of being wrong

1. Sign in. You'll hit the one-time-code prompt. You don't have the code.
2. Look at the code's shape. How many digits? How large is the space of possible values?
3. Now ask the question that matters more than its length: **what happens on a wrong guess?**
   Does the server slow you down, lock you out, or invalidate anything — or does it just say
   "wrong" and let you try again, forever?
4. If nothing stops you, then the whole space is searchable. Search it.

### Stage 2 — Reach the goods without reaching the second factor

5. The vault behind this login isn't the only thing your session can touch. Map the app — what
   other endpoints exist for a signed-in staff member (roster, exports, reports)?
6. For each one, ask a precise question: does *this* endpoint check that you passed **both**
   factors, or only that you passed the **password**?
7. If any sensitive endpoint is satisfied by the first factor alone, you never need the code at
   all. Walk straight to it.

### Stage 3 — Take the door the second factor left open on purpose

8. Real 2FA always ships an escape hatch: *"Lost your device? Use a backup code."* Find it.
9. A backup code exists specifically to **bypass** the OTP. So the only question worth asking is
   whether the backup path is as strong as the factor it replaces — or weaker.
10. If the backup codes come from a small, unthrottled space, they're a second brute-force door
    — one that makes the strength of the OTP itself completely irrelevant.

---

## Rules of Engagement

Attack it like a real target — `curl`, Burp Intruder, Python `requests`. Stage 1 and Stage 3
both need genuinely repeated requests; the mission page has a single-guess form for each so you
can test your understanding, but neither one is how you actually search a whole space — that's a
loop against the JSON API endpoints (`/api/verify-otp`, `/api/recover`). Stage 2 needs no
brute-forcing at all — just one request to the right place.

Don't skip to reading `app.py`. Every finding here is visible from the outside: by reading a
code's shape, by testing what a wrong guess actually does, and by asking each endpoint which
factors it really checks.

---

## 💡 Hints (progressive — open only if stuck)

<details><summary>Hint 1 — Stage 1: length is not the point</summary>

Four digits is only 10,000 values, yes — but a six-digit code (a million) would fall to the
same attack. The real vulnerability isn't the length, it's that **nothing throttles wrong
guesses**. Confirm that first: submit several wrong codes and watch for a slow-down, a lockout,
or a changed response. If none comes, the length is just how long your loop runs.
</details>

<details><summary>Hint 2 — Stage 1: script the JSON endpoint, not the form</summary>

The on-page code box is for one guess. Real brute-forcing loops
`POST /masquerade/op7/api/verify-otp` with `otp=0000`…`9999`, carrying your logged-in cookie,
and watches for the response that says `"ok": true`. Burp Intruder or a five-line script both
do it.
</details>

<details><summary>Hint 3 — Stage 2: enumerate the signed-in surface</summary>

After the password step you already hold a session. What can it reach *before* you enter any
code? The mission page names one such endpoint outright — a duty-roster export. Request it
directly, in the state you're in right after logging in, and see whether it cares that you never
finished 2FA.
</details>

<details><summary>Hint 4 — Stage 2: the bug is an inconsistency, not a missing check</summary>

The vault page *does* check for full 2FA — try it without verifying and you're bounced. The
export endpoint doesn't. That difference **is** the finding: 2FA enforced in one place and
forgotten in another is the single most common way real apps leak past a second factor.
</details>

<details><summary>Hint 5 — Stage 3: attack the fallback, not the factor</summary>

Backup codes here look like `KAFE-0000` through `KAFE-9999`. That's the same size of space as
the OTP, with the same lack of throttling — and any valid one skips the code entirely. Loop
`POST /masquerade/op7/api/recover` with `backup=KAFE-0000`… and you'll land one.
</details>

---

## Beyond these three — what else is worth checking

Once all three doors are open, notice a few more properties of this exact app you can observe
without further exploitation, and write them up alongside your findings:

- **Single-use:** after a correct OTP is accepted, is it invalidated? Try presenting the same
  correct code a second time. (This is the classic *token replay* check from your notes.)
- **Scope:** the code that authorises login — would the app accept the same code to authorise a
  *different* sensitive action, if one existed? OTPs should be bound to their purpose.
- **Session regeneration:** is your session identifier rotated after full 2FA completion, or is
  the pre-2FA session simply promoted in place? (Same root cause you met in Operation 02.)

None of these needs a working exploit to report — noticing and describing them accurately is
the job.

---

## Reporting

Once solved:
- **Finding 1** — no rate limiting / lock-out on OTP verification: the code space, and evidence
  that the full space is searchable online
- **Finding 2** — 2FA not enforced server-side on a sensitive endpoint (forced browsing): the
  endpoint, and proof it returns protected data on the first factor alone
- **Finding 3** — weak recovery path: the backup-code space, and the recovered code
- **Secondary** — missing single-use / replay on a correct OTP, if you confirmed it
- **WSTG area** — Weak Lock-Out Mechanism / Two-Factor Authentication testing
- **Impact & Fix** — for each finding, what an attacker gains, and how you'd remediate it

Good luck, operator. Command is waiting. 🎭
