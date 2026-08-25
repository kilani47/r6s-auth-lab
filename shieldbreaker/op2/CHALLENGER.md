## 🎯 Operation 02 — Breach & Clear

**Attacker:** Sledge &nbsp;⚔&nbsp; **Defender:** Castle
**Target:** `http://localhost:8000/op2/` (unlocks after Op01)

### Mission

Recon is done — from Operation 01 you know the admin is **`g.mendel`**. Now you break in for
real. The **Operator Console** login has **no account lockout and no CAPTCHA**, so nothing stops
you from guessing forever. Rainbow-Corp has a company-wide password format, published right on
the account-provisioning page. Your job is to read that format precisely, and use it to build a
candidate list that is *guaranteed* to contain the real password.

1. **Find the exact password format** Rainbow-Corp enforces (not just "must be strong" — the
   *precise* structure).
2. **Get a small list of company/target words** and generate every candidate the format allows.
3. Get past the two things that stop a *naive* attack (a hidden token, and no obvious success
   message), and run your full candidate set against `g.mendel`.
4. Reach the console and capture the flag.

This is **not** a guessing exercise. Read the format precisely enough and your candidate list
is complete — the real password is mathematically guaranteed to be in it. Nothing here rewards
a lucky pick; it rewards reading the rule correctly and enumerating it fully.

### What you're given

```
wordlists/op2_base_words.txt     # ~35 words profiled from the company/target.
                                 # Not full passwords — you build the shape yourself
                                 # from the format you find, applied to these words.
```

### Three things the login does *not* make easy

- **The format looks like a vague "strong password" policy at a glance — it isn't.** Go read
  it carefully (`/op2/register`, and its page source/JS). It is far more specific than
  "contains upper/lower/digit/symbol." Get the *exact* shape — including how many digits, and
  exactly which symbols are allowed — or your candidate list will be incomplete and you'll miss
  the real password even after trying thousands of guesses.
- **A hidden token in the form.** Fire raw login POSTs and they'll all be rejected *before*
  your password is even checked — so "0 hits" can mean "none of my requests were even valid,"
  not "password not in list." Inspect the login form's fields and work out what the server
  expects on every submission.
- **No "Error" keyword to grep.** Op01 told you success/failure in the page text. This one
  doesn't. Don't *assume* what success looks like — **measure it.** Send one login with a
  password you *know* is wrong, record exactly what that failure looks like (status code,
  response size, whether it redirects), then treat *any* response that differs from that
  baseline as a possible hit.

### A second, separate finding to poke at

Try submitting a password to `/op2/register` that the displayed format says it shouldn't
accept. That's a distinct ATHN-07 finding (client-side-only enforcement) — and it's *why* you
can trust the format itself: it's real company policy, just not actually checked server-side.

---

## 💡 Op02 Hints (progressive — open only if stuck)

<details><summary>Hint 1 — reading the format precisely</summary>

`/op2/register` shows a checklist, but the real rule lives in the page's JavaScript (view
source). Find the regular expression that decides whether the submit button unlocks. A regex
is unambiguous — it tells you exactly how many digits are required (not "at least one" —
*exactly* how many) and exactly which symbol characters are allowed (a short, closed list, not
"any special character"). Write down the precise shape before you generate anything.
</details>

<details><summary>Hint 2 — turning the format into a complete list</summary>

Once you have the exact shape (e.g. `Word` + a fixed number of digits + one symbol from a small
fixed set), the candidate space is just a cross-product: **every base word × every digit
combination in that range × every allowed symbol.** Generate *all* of it, not a sample. Because
the format is exact and closed, this full set is guaranteed to contain the real password — you
don't need to pick which digits or symbols "seem likely."
</details>

<details><summary>Hint 3 — the token</summary>

The login form has a hidden `csrf_token` field tied to your session. Every POST to `/op2/login`
must include a valid one or you get `400 Session expired` — your password never even gets
checked. The pattern: **GET `/op2/` first (in a session that keeps cookies), scrape the token,
then reuse it on your POSTs.** It doesn't rotate per attempt, so grab it once and run the list.
</details>

<details><summary>Hint 4 — detecting success without assuming what it looks like</summary>

Don't hardcode "success = 302" or "success = some word" — you don't know that in advance, and
assuming it *is* a form of guessing. Instead: send one attempt with a deliberately wrong
password and record its **fingerprint** — status code, response length, and `Location` header.
Then flag any candidate whose fingerprint **differs** from that baseline. (Use "don't follow
redirects" so a redirect shows up as a difference.) In Burp Intruder this is the same move:
run the list, sort by length or status, and look for the one row that doesn't match the crowd.
`shieldbreaker/op2/solver.py` shows the full version if you want to compare after you've done your own.
</details>

---
