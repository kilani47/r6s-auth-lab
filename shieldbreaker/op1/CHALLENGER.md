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
