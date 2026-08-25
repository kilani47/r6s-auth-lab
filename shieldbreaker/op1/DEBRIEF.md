# Operation 01 — Callsign Recon · IQ ⚔ Mute · WSTG-IDNT-04

## The one-sentence lesson

**A login form can refuse to give you a password, and still tell you everything else about
who has an account — if the app treats "wrong username" and "wrong password" as different
enough events to leak the difference.**

That's it. That's the whole vulnerability. Everything else below is learning to *notice* that
difference, because in the real world it's rarely as loud as it was here.

---

## Why this bug exists in the first place (the mental model)

Nobody sets out to build this vulnerability. It falls out of the most natural way to write a
login check:

```
IF username exists in database:
    check password
    IF wrong: say "wrong password"
ELSE:
    say "user not found"
```

That reads like completely reasonable code. It's also WSTG-IDNT-04, fully formed. The bug
isn't a typo or a missing check — it's the *default shape* of authentication logic when nobody
has deliberately flattened it. That's the real lesson: **this isn't a bug you stumble into by
being careless, it's a bug you avoid only by being deliberate.** Every login form you ever test
starts as a suspect for this until proven otherwise.

The fix requires actively fighting that natural shape — forcing both branches to look, sound,
and *take the same amount of time* regardless of which path executed. That's unnatural to
write, which is exactly why this is one of the most common findings in real pentests.

---

## One term worth locking in: what's an "oracle"?

You'll see this word constantly from here on, so pin it down now. An **oracle** is any place a
system tells you the answer to a question it was never supposed to answer — not by stating it
outright, but through some side signal you can read. The name comes from asking a
fortune-teller a yes/no question: they won't say the words, but their behavior gives it away.
"Does this account exist?" is a yes/no question `/op1/` is *supposed* to hide behind a generic
failure — but two different parts of its behavior answer it anyway:

- **Message oracle** — the signal is the *words* in the response.
  ```
  fake user → "Callsign not found in the operator directory."
  real user → "Incorrect password for operator Gilles Mendel."
  ```
  You never learn a password, but the text alone already answered the real question.

- **Timing oracle** — the signal is *how long the server takes*, not what it says.
  ```
  fake user → ~1ms   (rejected immediately, nothing to check)
  real user → ~30-48ms (server did real work: hashed/checked a password)
  ```
  Even if the wording were made identical, the leftover time gap still answers the question —
  because the server ran extra code that only executes when the account is real.

Both are the same underlying idea wearing a different disguise: **a true/false fact leaking
through a channel nobody thought to guard.** The general name for that class of bug is a
**side-channel** — the same root idea behind padding-oracle attacks in cryptography, and
timing attacks against raw `password == input` string comparisons in real code. You'll meet
more of these as the campaign goes on; the channel changes, the pattern doesn't.

### Seeing these in Burp Suite (not just curl)

If you're working this in Burp instead of scripting it:

- **Message oracle** → **Repeater**. Send the same request twice (once per candidate username),
  diff the response bodies by eye — the text difference is loud enough to just read.
- **Timing oracle** → don't trust a single Repeater send; a 30ms gap is smaller than normal
  network jitter on one-off requests. Two better options:
  - **Intruder**: run your wordlist as an attack, then click **Columns** at the top of the
    results table and enable **Response received** / **Response completed** — now every
    request in the sweep has a timing column you can sort.
  - **Request Timer** (free BApp, Extender → BApp Store): logs timing for every request across
    Proxy/Repeater/Intruder into one persistent, filterable table.
  - Note: **Proxy → HTTP History**'s "Time" column is a *timestamp* (when the request was
    sent), not a duration — it's the place most people look first and find nothing, because
    it was never built to show round-trip time.

---

## The R6 framing, and why it's not just flavor

**Mute** jams signals in a radius — but a jammer has an edge. Right at the boundary, or through
a code path Mute's coverage wasn't designed for (the reset flow, not just the login form), the
signal leaks through.

**IQ's** entire kit is a scanner built to detect gadgets that are otherwise invisible —
electronics hidden behind walls, giving off a signal too faint to notice by eye. That is
*exactly* the skill this operation tests: the vulnerability was never visually obvious. Nothing
on the login page looks broken. You have to go looking for a signal that's leaking beneath
what's visible — timing, byte-for-byte response diffs, a second endpoint nobody thought to
harden the same way as the first.

Keep that framing for the rest of the campaign: **every operation is "the front door looks
fine — where's the leak?"**

---

## Walking back through what you did (and what to notice at each step)

### Step 1 — You needed a baseline before you needed a target

Before you can tell "real account" apart from "fake account," you need to know what a
**guaranteed-fake** response looks like. This is the single most transferable skill in this
whole exercise — it's the same move behind blind SQL injection, timing attacks against crypto,
and cache-based side channels. You never attack a signal you haven't first measured against a
control.

*What to pay attention to:* the very first request you send in any oracle-hunting task should
be one where you **already know the answer**, so you have something to diff everything else
against.

### Step 2 — You compared two responses that were supposed to look identical

Both `admin` (fake) and `g.mendel` (real) get **HTTP 401** and both say "you didn't get in."
From a glance, they're the same failure. The attack only exists because you looked *past* the
status code and diffed the actual content:

- `Callsign not found in the operator directory.`
- `Incorrect password for operator Gilles Mendel  [Montagne].`

*What to pay attention to, generally, on any login form:*
| Signal | Why it leaks |
|---|---|
| **Exact response text** | Easiest and loudest — devs write different strings for different code branches without thinking about it. |
| **Response length in bytes** | Even when text *looks* the same, whitespace, dynamic tokens, or a name being interpolated in (like here) changes the byte count. |
| **HTTP status code** | 200 vs 401 vs 403 vs 404 across different inputs is a dead giveaway. |
| **Response time** | Covered in Step 3. |
| **Headers** (`Set-Cookie`, `Location`, cache headers) | Some apps set a session cookie *only* on the "user exists" branch. |

### Step 3 — The timing gap was the same bug wearing a disguise

Even if the message text had been identical (`Invalid username or password` both times), the
server still did **different amounts of work**: real accounts pay the cost of hashing/checking
a password (~30ms here), fake ones bail out immediately (~1ms). This is why the official fix
for WSTG-IDNT-04 isn't just "use the same error string" — it's "run the *same code path*
regardless of outcome." A message fix alone is cosmetic; a real fix has to be structural.

*What to pay attention to:* timing differences are invisible to a human eye reading a page, but
trivial for a script to measure. Any time you're testing an oracle, measure time even if the
text already gave it away — it teaches you whether the fix (if there is one) is real or just a
patched string.

### Step 4 — You didn't stop at the login form

This is the step most people skip, and it's the one that actually got you the flag. The
password-reset flow (`/op1/reset`) is a **separate code path** written by (in spirit) a
different part of the app — and it re-implemented the same existence check independently,
except *more generously*: it didn't just confirm the account was real, it told you what got
sent to it.

*What to pay attention to:* one hardened endpoint tells you nothing about its siblings.
Registration forms, "forgot username," 2FA setup, API variants of the same login — every one of
them is a fresh chance for the same logic to be re-implemented slightly worse. **Enumeration
findings live disproportionately in the secondary flows, not the front door**, because the
front door is what everyone remembers to test.

**A correction worth being precise about:** reset isn't "unlocked" by login, and it doesn't
depend on login's oracle at all. It's a fully separate, independently vulnerable endpoint with
its own existence check against the same roster (`dispatched` vs. `No operator registered`
— an oracle in its own right). You only fed it the 4 confirmed names instead of all 40 for
*efficiency* — if login had been perfectly patched, brute-forcing all 40 candidates straight
against `/op1/reset` would still have found the same 4 accounts. Never assume a patched
endpoint protects a different endpoint that re-implements the same check — test each one on
its own merits.

Login's oracles also don't distinguish *which* of the 4 is the admin — all four get the exact
same `Incorrect password for operator X` shape. That distinction lives only in reset: it checks
one extra flag (`target`) that's true for exactly one account, and only that account's response
embeds the flag. Login tells you *who's real*; reset tells you *who matters*. That's a third,
independent oracle — not a continuation of the first two.

### Step 5 — Enumeration was recon, not the finish line

In this lab, the reset flow handed you the flag directly, so it felt like the objective. In a
real engagement, confirming `g.mendel` is a real account isn't the win — it's what lets you
stop guessing usernames and start a **targeted** attack (password spray, credential stuffing,
social engineering that specific person) instead of a blind one against the whole internet.
Operation 01's real output wasn't "a flag," it was "a confirmed target list of size 4 instead
of size 40." Keep that framing going into Operation 02: recon feeds exploitation, and the
campaign is built to chain that way on purpose.

---

## The actual code behind it, in plain language

Everything above described *behavior*. This is the few lines of `app.py` that produced it —
the real version of the pseudocode from earlier, worth seeing once so the concept stops being
abstract.

**1. The roster is just a dictionary — the "truth" you were reverse-engineering blind**

```python
ROSTER = {
    "g.mendel": {"display": "Gilles Mendel  [Montagne]", "target": True},
    "e.pichon": {"display": "Emmanuelle Pichon  [Twitch]", "target": False},
    ...
}
```

Nothing fancier than this. Every request you sent was really just asking, one guess at a time,
"is this key in that dictionary?" — the app was never going to *tell* you, so you had to make
it show through its behavior instead.

**2. The login route — the pseudocode from earlier, for real this time**

```python
if username in ROSTER:
    fake_verify(password)                                          # costs time — only here
    return ..., error=f"Incorrect password for operator {ROSTER[username]['display']}.", 401
return ..., error="Callsign not found in the operator directory.", 401
```

`if username in ROSTER:` is the entire vulnerability's branch point. Both paths return the same
`401` — that's why status code alone didn't help you. But only the `if` branch (a) builds a
different error string, and (b) calls `fake_verify()` before answering. One line, two oracles.

**3. `fake_verify()` — literally the timing oracle**

```python
def fake_verify(password: str) -> None:
    for _ in range(120000):
        password = hashlib.sha256(password.encode()).hexdigest()
```

This hashes the submitted password 120,000 times and throws the result away — a stand-in for
what a real app does (check a password against a stored hash, using something deliberately
slow like bcrypt). Slow hashing itself isn't the bug; **doing it only when the account is real
is.** If this call happened for every attempt, real or fake, the timing gap would vanish —
which is exactly the fix described in Step 3.

**4. The reset route — a second, independent copy of the same branch, plus one more layer**

```python
if username in ROSTER:
    if ROSTER[username]["target"]:
        # ...embeds LEVEL1_FLAG in the response...
    # ...else: generic "dispatched" message, no flag...
    return ...
return ..., message="No operator is registered under that callsign."
```

Same `if username in ROSTER:` shape as login, written completely separately in the file — this
is the code-level proof of Step 4's point that reset doesn't inherit login's leak, it has its
own. The nested `if ROSTER[username]["target"]:` is the one line that decides "just a valid
account" vs. "the admin" — login has no equivalent check anywhere, which is why it treated all
four the same.

---

## Self-check — can you explain these without looking back up?

1. Why does the *natural* way to write a login check produce this bug, without anyone intending it?
2. Name three response signals (besides the message text) that can leak account existence.
3. Why is a timing difference a *structural* bug and not just a wording bug?
4. Why did the reset endpoint leak more than the login endpoint, even though both check the same roster?
5. In a real pentest, what do you *do* with a confirmed list of valid usernames — what's the next move?

If any of those are shaky, that's the part worth re-reading above — not the request/response
bytes in the answer key below, which you've already proven you can reproduce.

---

## Answer key (reference)

### Ground truth

| Callsign | Display name | Admin / flag target |
|---|---|---|
| `g.mendel` | Gilles Mendel | ✅ yes — flag here |
| `e.pichon` | Emmanuelle Pichon | no |
| `r.tanaka` | Rei Tanaka | no |
| `m.branca` | Maria Branca | no |

Everything else in `wordlists/callsigns.txt` is a decoy.

### Exact requests

```bash
# message oracle
curl -s -X POST localhost:8000/op1/login -d 'username=admin&password=x' \
  | grep -Eo 'Callsign not found|Incorrect password[^<]*'
curl -s -X POST localhost:8000/op1/login -d 'username=g.mendel&password=x' \
  | grep -Eo 'Callsign not found|Incorrect password[^<]*'

# sweep the wordlist
while read -r u; do
  r=$(curl -s -X POST localhost:8000/op1/login -d "username=$u&password=x")
  echo "$r" | grep -q "Incorrect password" && echo "[VALID] $u"
done < wordlists/callsigns.txt

# timing oracle
for u in a.smith g.mendel; do
  echo -n "$u  "; curl -s -o /dev/null -w "%{time_total}s\n" \
    -X POST localhost:8000/op1/login -d "username=$u&password=x"
done

# reset/recovery oracle -> flag
for u in g.mendel e.pichon r.tanaka m.branca; do
  echo "== $u =="
  curl -s -X POST localhost:8000/op1/reset -d "username=$u" \
    | grep -Eo 'R6S\{[^}]*\}|dispatched|No operator'
done
```

Flag: **`R6S{iq_scanned_past_mute_blackout_g.mendel}`**

Automated: `python3 shieldbreaker/op1/solver.py http://localhost:8000` (reads the same
`wordlists/callsigns.txt` you were handed).

### Report language

- **Finding (WSTG-IDNT-04):** The authentication and password-recovery endpoints return
  observably different responses for valid vs. invalid usernames — distinct error text,
  response timing, and reset messaging. *CWE-204 — Observable Response Discrepancy.*
- **Impact:** An attacker compiles a confirmed list of valid accounts, turning an untargeted
  brute force into a targeted one.
- **Remediation:** Single generic message for all auth failures (`Invalid username or
  password`); always execute the password-hash path regardless of user existence (constant
  time); generic reset messaging (`If that account exists, a recovery packet has been sent`)
  regardless of input; rate-limit and/or CAPTCHA the reset endpoint.

---
