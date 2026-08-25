# 🛡️ OPERATION SHIELDBREAKER

**WSTG-ATHN + WSTG-IDNT — Authentication Testing.** Six operations, each modeled on a real
disclosed vulnerability pattern. Full campaign overview, setup, and how to run it all lives in
the [repo root README](../README.md) — this page is just the mission index.

Welcome, operator. **No solutions below** — just what you need to start each engagement like
it's a real one. Each operation's folder has two files:

- **`CHALLENGER.md`** — mission briefing, rules of engagement, progressive hints. **No spoilers.**
- **`DEBRIEF.md`** — the lesson explained, code walkthrough, self-check, full answer key.
  **Spoilers.** Read it only if you're stuck, checking your work, or reviewing after solving.

Each folder also has a `solver.py` reference solver.

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

## Mission Index

| # | Operation | Matchup | WSTG | Attack | Briefing | Debrief |
|---|-----------|---------|------|--------|----------|---------|
| 01 | Callsign Recon | IQ ⚔ Mute | IDNT-04 | Username enumeration | [CHALLENGER](op1/CHALLENGER.md) | [DEBRIEF](op1/DEBRIEF.md) |
| 02 | Breach & Clear | Sledge ⚔ Castle | ATHN-07 | Dictionary attack | [CHALLENGER](op2/CHALLENGER.md) | [DEBRIEF](op2/DEBRIEF.md) |
| 03 | Hard Breach | Dokkaebi ⚔ Clash | ATHN-03 | CAPTCHA bypass | [CHALLENGER](op3/CHALLENGER.md) | [DEBRIEF](op3/DEBRIEF.md) |
| 04 | Lockdown Failure | Thermite ⚔ Oryx | ATHN-03 | Lockout bypass | [CHALLENGER](op4/CHALLENGER.md) | [DEBRIEF](op4/DEBRIEF.md) |
| 05 | Ghost in the Panel | Blitz ⚔ Aruni | ATHN-04 | Auth-schema bypass | [CHALLENGER](op5/CHALLENGER.md) | [DEBRIEF](op5/DEBRIEF.md) |
| 06 | Back Door (Finale) | Nomad ⚔ Kaid | ATHN-08 | Alternative-channel auth | [CHALLENGER](op6/CHALLENGER.md) | [DEBRIEF](op6/DEBRIEF.md) |

Missions unlock one at a time — clear Operation 01 to reveal 02, and so on.

---

## Start here

```bash
docker compose up --build      # from the repo root
```
Then open **`http://localhost:8000`** — that's **Command**, your mission board. Only
**Operation 01** is visible at first. That's intentional.

👉 [**Operation 01 — Callsign Recon**](op1/CHALLENGER.md)

---

## Reporting (optional, but do it like a real test)

For each operation, once solved, jot down:
- **Finding** — what's actually broken (one sentence)
- **Evidence** — the request/response pair that proves it
- **CWE / WSTG ID** — printed on the mission card at Command
- **Impact** — what an attacker gains
- **Fix** — how you'd remediate it

This is what turns "I got the flag" into a real, transferable pentesting skill.

---

Good luck, operator. Command is waiting. 🎮
