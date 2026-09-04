# 🎭 Masquerade Operation 07 — The Second Factor

**Attacker:** Ash &nbsp;⚔&nbsp; **Defender:** Warden
**WSTG:** WSTG-ATHN-03 (Weak Lock-Out) · Bypassing Two-Factor Authentication
**Target:** `http://localhost:8000/masquerade/op7/` (unlocks after Operation 06 is cleared)

**No solutions below.** The app deliberately tells you *nothing* about its weaknesses — finding
them is the mission. Read [`DEBRIEF.md`](DEBRIEF.md) only once you've solved it, or want the full
lesson afterward.

---

## Mission

**Kafe Dostoyevsky** fronts a staff operations portal. Sign-in takes two things: a staff
password, and a **one-time code** sent to the on-duty phone. That's two-factor authentication —
*something you know* plus *something you have* — and it's supposed to mean a stolen password
alone gets an attacker nowhere.

You have the password. You do **not** have the phone. Get into the portal anyway.

Unlike the earlier missions, **this app doesn't label its own flaws.** There are no "Stage 1 /
Stage 2" panels explaining what's wrong and how to exploit it — it looks like an ordinary login.
Your job is to *explore* it like a real target and find the ways through. There are **three
completely independent ones**, and a thorough tester finds all three and writes each up as a
separate finding.

### What you're given

```
Staff ID:  night.duty
Password:  KafeNight2024!
```

A real, working password — first factor already solved. Everything interesting is what happens
after it.

---

## Objective

Reach the staff area behind the two-step prompt. Then keep going: **find every independent way
past the second factor you can.** (There are three. None of them needs the others, and none of
them is hinted at anywhere in the UI.)

Think like someone testing a real 2FA implementation. Your notes list where these things break —
work through them against this target:

- **The code itself** — how long is it, and more importantly, *what happens when you get it
  wrong*? Try. Watch what the server does (and doesn't do) on repeated failures.
- **The attack surface you can't see** — a web app is more than the pages it links to. Which
  endpoints exist that the menu never shows you, and how would you enumerate them? What does a
  found endpoint check before it hands over data — both factors, or just the first?
- **The way back in** — every real 2FA system has an answer to "I lost my device." Find this
  one's, and ask whether it's as strong as the factor it replaces.

---

## Rules of Engagement

Attack it like a real target — `curl`, Burp, a browser with DevTools open, Python `requests`,
and a content-discovery tool (`ffuf`/`gobuster`) if you reach for one. Two of the three ways in
need genuinely repeated requests (a loop, or Burp Intruder); the third needs no brute-forcing at
all, just finding the right door.

**Recon first.** Before you brute anything, look at what the app already hands you: the HTML it
serves, the JavaScript it loads, and the well-known files every site has. The most important
finding here isn't something you break — it's something you *find*.

Don't read `app.py` until you've solved it. Everything is reachable from the outside.

---

## 💡 Hints (progressive — open only if genuinely stuck)

<details><summary>Hint 1 — the code prompt: length is not the point</summary>

Submit a few wrong codes in a row. Does the server slow you down, lock the account, or change
its response after several failures — or does it just say "incorrect" every time and let you keep
going? If nothing stops you, then a short numeric code is simply a short password, and the whole
space is searchable. Loop it (the prompt posts to a JSON endpoint you can see in your proxy).
</details>

<details><summary>Hint 2 — the hidden surface: read what the browser loads</summary>

The portal isn't only the pages you can click to. Open DevTools and read the JavaScript the
two-step page pulls in — client code often names internal endpoints the UI never links. And
check the one file almost every site publishes that lists paths it would rather you didn't visit.
Both point at the same place here.
</details>

<details><summary>Hint 3 — the hidden surface: what does that endpoint actually check?</summary>

Once you've found the unlinked endpoint, request it in the state you're in *right after entering
your password* — before touching any code. Does it care that you never finished 2FA? An endpoint
that's happy with the first factor alone is a second factor that isn't enforced.
</details>

<details><summary>Hint 4 — the way back in: attack the fallback, not the factor</summary>

The two-step prompt offers a way in for someone who lost their device. Follow it. Note the
*shape* of what it asks for (the page shows you the format), then ask the same question you asked
about the code: is this space small, and does anything throttle guesses against it? A recovery
path weaker than the factor it replaces makes the factor's strength irrelevant.
</details>

---

## Beyond the three — worth checking and reporting

- **Single-use / replay:** once a correct code is accepted, is it invalidated? Try presenting the
  same correct code again.
- **Session regeneration:** is your session identifier rotated after full 2FA, or is the pre-2FA
  session promoted in place? (Same root cause you met in Operation 02.)
- **Scope:** should a code that authorises *login* also authorise a different sensitive action?

None of these needs a working exploit to report — noticing them is the job.

---

## Reporting

- **Finding 1** — no rate limiting / lock-out on OTP verification
- **Finding 2** — an unlinked sensitive endpoint that doesn't enforce 2FA (how you *found* it
  matters — name the recon step)
- **Finding 3** — a weak recovery path (the backup-code space)
- **Secondary** — missing single-use / replay, if you confirmed it
- **WSTG area** — Weak Lock-Out Mechanism / Two-Factor Authentication testing
- **Impact & Fix** — per finding

Good luck, operator. Command is waiting. 🎭
