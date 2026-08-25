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
