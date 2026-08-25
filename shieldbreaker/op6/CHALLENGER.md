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
