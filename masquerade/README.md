# 🎭 OPERATION MASQUERADE

**WSTG-SESS + Token/OAuth/2FA — everything that happens *after* login.** A second,
independent campaign under the same Command hub as [Shieldbreaker](../shieldbreaker/README.md)
— clearing that campaign is **not required** to play this one. Full site setup lives in the
[repo root README](../README.md); this page is the mission index for this campaign only.

Shieldbreaker asked "can you get in?" Masquerade asks the question that matters just as much:
**once you're in — as *anyone* — can the app tell who you actually are?** Sessions, tokens,
OAuth delegation, and 2FA are all, underneath, the same problem: proving an identity across
multiple requests without a way for an attacker to forge, steal, or skip that proof.

Same structure as Shieldbreaker: each operation folder has a `CHALLENGER.md` (no spoilers),
a `DEBRIEF.md` (spoilers, full answer key), and a `solver.py` reference solver.

---

## Mission Index

| # | Operation | Matchup | Topic | Briefing | Debrief |
|---|-----------|---------|-------|----------|---------|
| 01 | The Teller's Trust | Iana ⚔ Alibi | WSTG-SESS-01 · Cookie Tampering | [CHALLENGER](op1/CHALLENGER.md) | [DEBRIEF](op1/DEBRIEF.md) |
| 02 | Stolen Keys | Zero ⚔ Vigil | Session Hijacking & Fixation | *classified* | *classified* |
| 03 | One Click | Ying ⚔ Melusi | CSRF | *classified* | *classified* |
| 04 | Signed, Not Sealed | Kali ⚔ Echo | JWT Authentication | *classified* | *classified* |
| 05 | Exposed Claim | Jackal ⚔ Pulse | JWT Claims | *classified* | *classified* |
| 06 | Delegated Trust | Hibana ⚔ Bandit | Attacking OAuth | *classified* | *classified* |
| 07 | Unlimited Attempts | Ash ⚔ Warden | Bypassing 2FA | *classified* | *classified* |

Only **Operation 01** is built and playable right now. The rest reveal on Command as they
ship, one at a time, exactly like Shieldbreaker did.

---

## Start here

```bash
docker compose up --build      # from the repo root
```
Then open **`http://localhost:8000`** — scroll down past Shieldbreaker's roster to find
**🎭 Operation Masquerade** on the same Command screen.

👉 [**Operation 01 — The Teller's Trust**](op1/CHALLENGER.md)
