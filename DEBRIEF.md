# 🔓 OPERATION SHIELDBREAKER — After-Action Debrief

**Spoilers below.** This file explains *why* each operation works, not just what the flag is.
If you haven't played yet, use [`CHALLENGER.md`](CHALLENGER.md) first.

Each operation gets two parts: a **debrief** (the lesson, in plain language, with the "what
should I have been paying attention to" walkthrough) and an **answer key** (exact requests,
ground truth, report language) for reference.

---

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

Automated: `python3 solvers/op1.py http://localhost:8000` (reads the same
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

# Operation 02 — Breach & Clear · Sledge ⚔ Castle · WSTG-ATHN-07

## The one-sentence lesson

**A password policy that describes an *exact, rigid structure* (not "contains a symbol
somewhere," but "exactly N digits, exactly one symbol from this closed set") doesn't protect
the password — it hands you the complete blueprint to enumerate it.**

Operation 01 was about *finding out who exists*. Operation 02 is about *getting in*. The
difficulty here isn't cleverness — it's reading a specification precisely and then trusting the
math, against a login that fights back with a token and gives you no success message.

---

## "Not guessy" — why complete enumeration isn't luck

Two earlier designs of this mission got this wrong in opposite ways, and it's worth knowing why,
because the fix generalizes.

**Attempt 1** used a password like `Rainbow2024!`, "protected" by a vague policy ("must contain
upper/lower/digit/symbol"). That's a trap: the policy tells you *what kinds* of characters must
appear, but not *how many*, *where*, or *from what set*. You end up improvising — maybe try a
year, maybe try `!`, maybe not — and if you didn't happen to include `2024` in your guesses,
you'd fail through no fault of method. That's luck wearing a lab coat: an **open-ended** rule
forces you to invent boundaries yourself.

**Attempt 2** dropped the policy connection entirely and used a common password
(`1qaz2wsx`) from a plain wordlist. Deterministic, but it made the *policy itself* pointless —
reading it taught you nothing useful, since the real password violated it anyway.

**This version** fixes both: the policy is now a **closed, exact specification** —

```
Capitalized word + exactly 2 digits + exactly 1 symbol from ! @ # $
```

Every slot is bounded: the digit count is fixed (not "at least one"), and the symbol set is a
short, *named* list (not "any special character"). That means the set of everything the policy
allows is a small, fully countable cross-product:

```
(base words) × (100 two-digit combinations) × (4 symbols)
```

Generate literally all of it — not a sample, not "the ones that seem likely" — and the real
password is **guaranteed** to be somewhere in that set, because it was built following this
exact rule. You're not picking a plausible subset and hoping. You're covering 100% of a space
you can prove is complete. That's what makes it deterministic: **the policy's precision is what
makes the space small enough to fully enumerate, instead of open-ended enough to require guessing.**

---

## Why this bug exists (the mental model)

A rigid, formulaic policy *feels* stricter than a vague one — "exactly 2 digits and 1 of these 4
symbols" sounds more controlled than "contains a digit." But strictness about *shape* is not the
same as strength. A closed, well-known formula is **more** predictable than an open one, because
an attacker who identifies the formula has identified the *entire* keyspace, not just a
direction to search in. This is a real, documented failure mode: companies that adopt a
memorable password convention (often for helpdesk/onboarding convenience — "reset passwords
follow WordNN$") inadvertently publish their own keyspace the moment that convention leaks or is
inferred, which is exactly what happened here via the registration page's client-side rule.

Layer on **no lockout, no rate limit** (the ATHN-03 controls, deliberately absent so this stays
a pure ATHN-07 lesson) and a space of ~14,000 candidates is trivial to exhaust in seconds.

---

## The R6 framing

**Castle** reinforces a doorway with an armored barricade — but it's still just a barricade, and
**Sledge's** hammer ("The Caber") exists for exactly one purpose: to smash reinforced surfaces
open in a couple of hits. A rigid password formula is Castle's barricade with the blueprints
taped to the front of it: it looks reinforced, but the exact structure is right there to read.
Sledge doesn't need to guess where to hit — the shape tells him.

---

## Walking through what you had to do (and what to notice)

### Step 1 — Read the rule precisely, not approximately

`/op2/register` shows a checklist ("starts with a capitalized word," "exactly 2 digits," "exactly
1 symbol from ! @ # $"). The *exact* wording matters enormously here — "exactly 2" is a much
smaller, more useful fact than "at least 1." The real rule, in full precision, lives in the
page's client-side JavaScript as a regular expression: view source and find it. A regex is
unambiguous by construction — it can't be misread the way prose can.

*What to pay attention to:* when a spec gives you a number or a closed set, that's a gift —
it bounds your search. Don't round it off to a vaguer version in your head ("some digits, some
symbol") or you throw away the thing that makes this solvable by enumeration instead of guessing.

### Step 2 — Turn the rule into a complete candidate list

Once you have the precise shape, generating candidates is mechanical, not creative:

```
for each base word:
    Capitalize it
    for each 2-digit value 00-99:
        for each symbol in "!@#$":
            yield Word + digits + symbol
```

`35 words × 100 × 4 = 14,000` candidates — **every single one the policy allows.** No candidate
is more "likely" than another from a pure enumeration standpoint; you're not ranking guesses,
you're covering the space. This is the core move that separates "dictionary attack" from
"brute force": you're not trying *every possible string* (that's brute force, and it doesn't
scale) — you're trying *every string a known rule permits* (that's a targeted dictionary attack,
and it's small enough to be fast).

*What to pay attention to:* the moment you can describe a password's shape with a regex, you can
describe its entire keyspace with a loop. That's true whether you found the regex in a client-
side validator (like here) or inferred it from a company's known convention on a real engagement.

### Step 3 — Get past the token before you can test a single password

Naive brute-forcing (`hydra`, a bare Intruder, a loop of raw POSTs) fails instantly here, and
that's the point. The login carries a per-session `csrf_token`; a POST without a matching one is
rejected `400` *before* the password is checked. So "0 hits" doesn't mean the password wasn't in
your list — it means **none of your requests were even valid.**

The fix in your tooling: establish a session, `GET /op2/`, scrape the token, and send it with
every POST. This is the single most common reason a brute-force "doesn't work" against a real
app, and spotting it is worth more than the flag.

### Step 4 — Define "success" by measuring failure, not by assuming

Op01 handed you a keyword. This login never says "welcome," and you must **not** hardcode
"success = 302" — you don't know that in advance, and assuming it is its own kind of guessing.

The non-guessy technique: send one attempt with a password you *know* is wrong and record its
**fingerprint** — status code, response length, `Location` header. Here that baseline is
`200, ~3656 bytes, no redirect`. Then flag any candidate whose fingerprint **differs** from it.
When `Barricade88$` lands, the response is `302, 211 bytes, Location: /op2/console` — different
on all three axes, so it's flagged without you ever having encoded what "success" looks like.

*What to pay attention to:* this is the exact same "baseline before you attack" move from Op01,
pointed at the win condition. In Burp Intruder it's "run the list, sort by length/status, find
the row that doesn't match the crowd."

### Step 5 — The policy was theater on the server (a second, separate finding)

`/op2/register` refuses non-conforming passwords... in the browser only. POST straight to it
(curl/Burp) with `123` and it's accepted — the server never checks. That's a standalone finding
(client-side-only validation): the company *has* a real, exact password rule, they just never
enforce it, which is how an account could exist that follows the rule but was never actually
gated by it.

*What to pay attention to:* client-side validation is a suggestion, not a control — but here it
doubled as *useful reconnaissance*, because the rule it encodes is genuine. Always re-send past
the browser to see what the server actually accepts, and separately, always read what the client
*claims*, because that claim can leak real information even when unenforced.

### Step 6 — Chaining: Op01's output was Op02's input

You didn't brute-force a username here — you already *had* `g.mendel` from Operation 01's recon.
Enumeration narrows the target to one account; the credential attack lands on it. That's exactly
why enumeration matters in a real engagement: it makes the search *targeted* instead of hopeless.

---

## The actual code behind it, in plain language

**1. A password that exactly satisfies its own rigid formula**

```python
OP2_PASSWORD = "Barricade88$"
OP2_POLICY = {
    "min_len": 8,
    "digit_count": 2,          # exactly two — not "at least one"
    "symbols": "!@#$",         # exactly one, from this closed set — nothing else
    "structure": "Capitalized word + exactly 2 digits + exactly 1 symbol from ! @ # $",
}
```

Unlike the earlier design, the real password *does* follow the stated rule precisely. That's
what makes the rule worth reading: it's true, and its precision is exactly what shrinks the
keyspace down to something enumerable.

**2. Client-side-only enforcement of that exact rule (the register bypass)**

```python
@app.route("/op2/register", methods=["GET", "POST"])
def op2_register():
    ...
    password = request.form.get("password") or ""
    # the server NEVER checks password against OP2_POLICY — only the page's JS regex does
    return render_template("op2_register.html", done=True, pw_len=len(password), ...)
```

The template carries a regex (`^[A-Z][a-z]+\d{2}[!@#$]$`) that enforces the rule visually; the
route has no equivalent check. Reading that regex is how you get the *exact* structure instead
of an approximation.

**3. The token gate — why naive tools get 0 hits**

```python
if not token or token != session.get("op2_csrf"):
    return ..., error="Session expired — reload and try again.", 400   # password never checked
```

This runs *first*. No valid token → `400`, and your credential guess is discarded unread.

**4. Success is a redirect, failure is generic — so you diff, not assume**

```python
if username == OP2_USER and password == OP2_PASSWORD:
    session["op2_authed"] = True
    return redirect(url_for("op2_console"))          # 302 + Location, tiny body
return ..., error="Invalid username or password.", 200    # generic, identical for every wrong try
```

No username enumeration (generic failure — Op01's lesson, "fixed" here). Success and failure
differ only in status/length/redirect, which is why the baseline-diff technique in Step 4 is the
right way to detect it.

---

## Self-check — can you explain these without looking back up?

1. Why does a *more specific* password rule ("exactly 2 digits, exactly 1 of these 4 symbols") make a password easier to crack than a vague one ("must contain a digit and a symbol")?
2. What's the actual difference between "brute force" and a "dictionary/rule-based attack" in terms of the size and definition of the candidate space?
3. Why does finding an *exact regex* on a page beat reading a plain-English checklist, even if they describe "the same" rule?
4. You run your whole 14,000-candidate list and get zero hits. Name two reasons that have nothing to do with your digit/symbol coverage being wrong.
5. Why is it useful to read a client-side validation rule even after you've proven the server doesn't enforce it?

---

## Answer key (reference)

- **Target / credential:** `g.mendel` : `Barricade88$`
- **Flag:** `R6S{sledge_hammered_castle_Barricade88$}`
- **Automated:** `python3 solvers/op2.py http://localhost:8000` (session + token + baseline-diff detection + full cross-product enumeration)

### Manual walkthrough

```bash
# 1) prove the policy is client-side only (server accepts a non-conforming password)
curl -s -X POST localhost:8000/op2/register -d 'username=hax&password=123' \
  | grep -Eo 'created with a [0-9]+-character password'

# 2) establish a session + grab the CSRF token (save cookies!)
TOK=$(curl -s -c /tmp/op2.cj localhost:8000/op2/ | grep -oE '[0-9a-f]{16}' | head -1)

# 3) measure the failure baseline, then confirm the real password differs from it
curl -s -b /tmp/op2.cj -o /dev/null -w "wrong:        %{http_code} %{size_download}b\n" \
  -X POST localhost:8000/op2/login -d "csrf_token=$TOK&username=g.mendel&password=nope000"
curl -s -b /tmp/op2.cj -o /dev/null -w "Barricade88\$: %{http_code} %{size_download}b\n" \
  -X POST localhost:8000/op2/login -d "csrf_token=$TOK&username=g.mendel&password=Barricade88\$"
# wrong -> 200 ~3656b ; Barricade88$ -> 302 211b  (the difference IS the detection)
```

For the full enumerated run: `python3 solvers/op2.py` builds every `word + 2 digits + symbol`
combination from `wordlists/op2_base_words.txt` (14,000 candidates) and walks them all.

### Report language

- **Finding (WSTG-ATHN-07):** The Operator Console's administrative account uses a password that
  exactly follows the company's own published password format (`Capitalized word + 2 digits + 1
  symbol from a 4-character set`), which is enforced client-side only on account provisioning.
  Because the format is rigid and fully disclosed (readable in client-side JavaScript), the
  entire valid password space is small and fully enumerable; credentials were recovered via
  complete enumeration of that space, with no lockout or rate limiting to prevent it.
  *CWE-521 — Weak Password Requirements; CWE-307 — Improper Restriction of Excessive
  Authentication Attempts; CWE-602 — Client-Side Enforcement of Server-Side Security.*
- **Impact:** Full administrative account takeover from an unauthenticated position.
- **Remediation:** Enforce password rules **server-side**; replace the rigid formulaic policy
  with a length minimum (12+) plus a check against known-breached/common-password lists (e.g.
  the HaveIBeenPwned range API) — per NIST 800-63B, avoid composition rules that create a
  predictable, guessable structure; add rate limiting and account lockout (see Operation 04);
  consider MFA on admin accounts.

---

# Operation 03 — Hard Breach · Dokkaebi ⚔ Clash · WSTG-ATHN-03

## The one-sentence lesson

**A CAPTCHA only works as a control if solving it requires something an attacker's script
*doesn't have* — and "do the arithmetic printed right there in the page" is something every
script already has.**

This is the mission your own course notes walked through almost exactly (`crunch` wordlist,
`bb.py` recon, `b.py` attack, `eval()` on the scraped challenge text) — you're now rebuilding
that exact pattern from scratch, against a fresh target, without the answer key open.

---

## Why this bug exists (the mental model)

A CAPTCHA is supposed to separate "a human is doing this" from "a script is doing this." The
whole design depends on presenting a problem that's *easy for a person, hard for a machine* —
warped text, a "select all the traffic lights" grid, a behavioral score. **Arithmetic fails that
test in exactly the wrong direction:** it's *harder* to make a script fail at `6 + 4` than to
make it succeed. There is no version of "parse two numbers and add them" that a computer finds
difficult. OWASP's own guidance (the CAPTCHA flaw list in your course notes) puts this at the
very top: *"easily defeated challenge (e.g., simple arithmetic, or a limited/small question
set)"* — this mission is that bullet point, built and running.

Randomizing the *operator* (`+ - *`) on top of the numbers doesn't change that verdict — it
only tests whether you noticed. A defender might reasonably believe "the numbers change every
time, so it can't be scripted" — but varying which of three trivial operations gets used adds
zero real difficulty for a machine; a computer finds `7 * 3` exactly as effortless as `6 + 4`.
It *does* break a lazy script that hardcoded `a + b` and never checked what symbol was actually
shown — which is precisely why testing this kind of control means confirming your automation
handles *every* variant it can produce, not just the first one you happened to see.

The operands here are also 4-digit numbers (`4821 + 3912 = ?`) instead of single digits, and
that's worth sitting with for a second, because it cuts exactly one direction. A script parses
`"4821"` and `"3912"` out of the page exactly as easily as it parses `"4"` and `"3"` — there is
*no* additional cost to `eval()` for bigger numbers. A **human**, on the other hand, absolutely
notices the difference: adding two 4-digit numbers in your head is real mental effort compared
to single digits, and multiplying two of them (`5303 * 5070`) is well past what most people can
do without a pen. So making the numbers bigger doesn't raise the bar for the thing this control
is supposed to stop (bots) — it only raises the bar for the thing it's supposed to let through
(legitimate users). That's not a hypothetical edge case; it's a real, common way CAPTCHAs get
*worse* while looking more secure: a defender sees "bigger numbers, harder problem" and ships it,
without asking *harder for whom*.

The second bug is a different flavor entirely, and arguably more serious: it's not that the
*challenge* is weak, it's that the *validation code* has a gap. A guard clause written to avoid
crashing on a missing field (`if captcha_raw: ...`) accidentally treats "nothing to check" as
"passed the check" — a missing value and a valid value both fall through to the same "don't
reject" outcome. This is a real, common class of bug: **treating the absence of input as
equivalent to correct input**, rather than as its own explicitly-invalid case. It's why "what if
the field just isn't there at all" is always worth testing separately from "what if I answer
wrong" — they can, and often do, hit different code paths.

Layer on **zero lockout** (deliberately absent here — that's Operation 04's dedicated lesson)
and either bug alone is enough to make the access code fall to a full sweep.

---

## "Not guessy" — why 10,000 is a complete search, not a hopeful one

Same principle as Operation 02: the access code is a **plain 4-digit number**. That space is
exactly `0000`–`9999` — fully bounded, fully known in advance, nothing about its shape left to
intuit. Iterating all 10,000 *is* the complete keyspace, not a sample of it. You are not hoping
the code resembles something common; you are exhausting every value it could possibly be. The
only question this mission asks is whether you can get a script *into position* to try all
10,000 — i.e., whether you can defeat the thing that's supposed to stop automation in the first
place.

---

## The R6 framing

**Dokkaebi's** entire kit — Logic Bomb — is built around hacking a *specific* target's phone:
she doesn't brute-force the whole world, she goes after one confirmed device with tools built
for exactly that job. That's this mission precisely: `g.mendel` was already confirmed back in
Operation 01, and now you're hacking their access terminal the way Dokkaebi would — with a
script, not a lockpick.

**Clash's** shield is a *physical, electrified barrier* — imposing, but it's still just a shield
with logic underneath. A perimeter terminal guarded only by "solve this sum" is Clash's shield
with a screen door for a lock: looks tough, folds to anyone who reads the fine print.

---

## Walking through what you had to do (and what to notice)

### Step 1 — Recognize the challenge is solvable by inspection, not brute intelligence

The verification challenge renders as literal text in the HTML: `4821 + 3912 = ?`. No image, no
distortion, no server-side-only secret — the *entire problem and everything needed to solve it*
is sitting in the response body. The moment you can read a challenge's answer straight out of
what it gave you, it has stopped being a meaningful barrier — and that stays true no matter how
big or intimidating the numbers look.

*What to pay attention to:* ask, for any CAPTCHA/challenge you meet, "what does the attacker
need that they don't already have?" If the answer is "nothing — it's derivable from the
challenge itself," the control is cosmetic regardless of how official it looks.

### Step 2 — Notice the challenge is single-use, and build your loop around that

Solve one challenge, and the *next* response — success or failure — carries a brand new one.
Reusing an old answer fails. This forces the exact shape your course material already showed
you: **GET the page fresh, extract the current challenge, solve it, POST immediately** — every
single attempt, no shortcuts, no solving once and looping the credential only.

*What to pay attention to:* this is a different failure mode than Operation 02's stable CSRF
token. There, one token served the whole run. Here, the token-equivalent (the challenge) expires
every time — so your loop has to do *more* work per attempt, not less. Recognizing which kind of
token you're dealing with (stable vs. single-use) changes how you have to script around it.

### Step 3 — Run the complete, bounded brute force

Once the per-attempt mechanics work, the credential attack itself is mechanical: 10,000
candidates, no lockout, done. This is the same "complete enumeration of a bounded space"
principle as Operation 02, just applied to digits instead of a password formula.

### Step 4 — Test the validation logic itself, not just the challenge

This is the step that separates "found *a* bug" from "found *every* bug." Solving the math
proves the challenge is weak. But does the server even *require* an answer? Sending a request
with the field simply missing — no value, not even an empty one — tests a completely different
code path than sending a wrong value. Here, they behave differently: a **wrong** answer is
correctly rejected; a **missing** one sails through unchecked.

*What to pay attention to:* "what happens if I answer wrong" and "what happens if I don't answer
at all" are two different tests. Real validation bugs love to hide specifically in the gap
between "invalid" and "absent" — always test both, on any field that's supposed to gate access.

### Step 5 — Chaining: the target never changed, the system did

`g.mendel` again — same confirmed operator from Operation 01, now targeted on an entirely
different system (a physical-access terminal instead of a web login). That's deliberate: a real
target's exposure isn't one login form, it's every system that trusts their identity. Recon
carries forward across systems, not just within one.

---

## The actual code behind it, in plain language

**1. A challenge that's genuinely arithmetic, stored server-side but shown in plaintext**

```python
def op3_new_challenge():
    op = random.choice(["+", "-", "*"])
    a, b = random.randint(1000, 9999), random.randint(1000, 9999)   # 4-digit, not single-digit
    if op == "-" and b > a:
        a, b = b, a                      # keep the result non-negative
    answer = {"+": a + b, "-": a - b, "*": a * b}[op]
    session["op3_captcha"] = answer         # the real, server-checked answer
    return a, op, b                          # ...and the same values go straight into the page
```

Bumping the operand range from `1-9` to `1000-9999` costs `eval()` nothing — a script that reads
`"4821"` off the page pays no more than it would for `"4"`. It's a change that only affects a
*human* trying to solve the same challenge by eye. Keep that in mind reading Finding 1 below.

The server *does* check against its own stored value (this isn't a fake check) — but because
`a`, `op`, and `b` are all rendered directly into the HTML, anyone reading the page already has
everything needed to compute what the server is going to compare against, regardless of which
operator was picked. (Division was deliberately left out of the operator set — making an exact,
integer-only division challenge means building it backwards from the answer instead of picking
random operands, and that extra machinery buys nothing beyond what `+ - *` already teach.)

**2. The guard-clause bug — absence treated as "nothing to check"**

```python
captcha_ok = True                      # innocent-looking default...
if captcha_raw:                        # ...only overridden when the field is present
    try:
        captcha_ok = int(captcha_raw) == expected
    except ValueError:
        captcha_ok = False
```

`captcha_raw` is `None` when the field is omitted entirely, and `None` is falsy — so the `if`
body never runs, and `captcha_ok` keeps its default of `True`. A **wrong** value (`"9999"`) *is*
truthy, so it *does* get checked and correctly fails. Only the **missing** case slips through.
This one default value, sitting above the `if`, is the entire second vulnerability.

**3. Single-use by design — regenerated regardless of outcome**

```python
a, op, b = op3_new_challenge()   # rotates whether this attempt passed or failed
```

This line runs unconditionally before the response is built, which is *why* Step 2 mattered —
there's no way to get two attempts out of one challenge.

**4. No lockout anywhere in this route** — no attempt counter, no per-IP tracking, nothing.
Compare that absence to Operation 04, where a *broken* lockout is the entire point.

---

## Self-check — can you explain these without looking back up?

1. Why does an arithmetic CAPTCHA fail at the one job a CAPTCHA has, structurally, not just because someone wrote lazy code?
2. Why doesn't randomizing the operator (`+ - *`) meaningfully raise the difficulty for a machine, even though it would trip up a script that assumed addition?
3. Using 4-digit operands instead of single digits makes the challenge look more serious. Who does it actually get harder for, and who does it stay exactly as easy for?
4. Why is testing "field missing" a genuinely different test from "field wrong," and why can real validation code treat them differently by accident?
5. Why is brute-forcing a 4-digit code "complete enumeration" and not a guess, in the same sense as Operation 02's password formula?
6. What made this mission's automation loop structurally different from Operation 02's (stable token vs. single-use challenge)?

---

## Answer key (reference)

- **Target / credential:** `g.mendel` (confirmed in Op01) : PIN `4187`
- **Flag:** `R6S{dokkaebi_cracked_clash_perimeter_4187}`
- **Automated (intended path):** `python3 solvers/op3.py http://localhost:8000` — GETs a fresh
  challenge, parses whichever operator is shown, `eval()`s it, POSTs a candidate PIN, repeats
  across the full 0000–9999 space. Verified run: cracked after **4,188 / 10,000** tries.

### Manual walkthrough — the intended path (solving the challenge)

```bash
# one round-trip, by hand, to see the mechanics:
CJ=/tmp/op3.cj
curl -s -c $CJ -b $CJ http://localhost:8000/op3/ | grep -o 'id="captcha-challenge"[^<]*<[^<]*'
# read the operands AND the operator shown, compute the answer yourself, then:
curl -s -c $CJ -b $CJ -X POST http://localhost:8000/op3/login \
  -d "pin=0000&captcha=<your computed answer>" -o /dev/null -w "%{http_code}\n"
# repeat with a fresh GET before every attempt -- the challenge is single-use,
# and the operator will very likely be different next time
```

### Manual walkthrough — the second bug (skipping the challenge entirely)

```bash
CJ=/tmp/op3b.cj
curl -s -c $CJ -b $CJ -o /dev/null http://localhost:8000/op3/
# correct PIN, captcha field OMITTED -- not empty, not wrong, just absent:
curl -s -c $CJ -b $CJ -X POST http://localhost:8000/op3/login \
  -d "pin=4187" -o /dev/null -w "%{http_code}\n"
# -> 302. No math was ever solved.
curl -s -c $CJ -b $CJ http://localhost:8000/op3/console | grep -o 'R6S{[^}]*}'
```

### Report language

- **Finding 1 (WSTG-ATHN-03):** The perimeter terminal's verification challenge is a
  plaintext arithmetic problem (operator randomized across `+ - *`, operands 4-digit, but always
  trivially computable), solvable by automation with no external knowledge required, and
  provides no meaningful resistance to brute force. Using larger operands increases the burden
  on legitimate users without adding any real difficulty for a script. *CWE-804 — Guessable
  CAPTCHA.*
- **Finding 2 (WSTG-ATHN-03):** The server's challenge-validation logic treats a missing
  `captcha` parameter as an implicit pass rather than an invalid submission, allowing the check
  to be skipped entirely regardless of the actual answer. *CWE-20 — Improper Input Validation.*
- **Impact:** Combined with the absence of any account lockout or rate limiting, both findings
  independently allow a full brute force of the 4-digit access code (10,000 requests, trivial
  locally) with zero legitimate credentials.
- **Remediation:** Replace arithmetic challenges with a CAPTCHA type that resists automated
  solving (image-based, behavioral, or a managed service like reCAPTCHA v3); validate the
  presence *and* correctness of the challenge response as one inseparable check (reject on
  missing exactly as on wrong, never default to "pass"); add real account lockout / rate
  limiting so no single control is the only thing standing between an attacker and the account
  (see Operation 04 for what happens when that lockout exists but is broken).

---

# Operation 04 — Lockdown Failure · Thermite ⚔ Oryx · WSTG-ATHN-03

## The one-sentence lesson

**A security control firing is not the same thing as a security control working — and the only
way to know which one you built is to actually trigger it and look at what happens next.**

Operations 01–03 all had a password or a PIN or a code *somewhere* for you to find. This one
doesn't. That's not a trick — it's the entire point. There is nothing to crack here, because the
vulnerability isn't in a credential. It's in what the app does the instant its own defense
mechanism activates.

---

## This mission is a real, disclosed bug — not a hypothetical

This is modeled directly on a publicly documented vulnerability in **Tiki Wiki CMS Groupware**
(the exact lab your course notes walked through): after roughly 50 failed logins against the
`admin` account, Tiki's lockout logic didn't lock the account. It **blanked the stored password
to an empty string.** Logging in afterward with `admin` and a *blank* password worked. Full
administrative access, achieved entirely through the feature that was supposed to prevent
exactly that. This isn't a contrived CTF puzzle pattern — it's *CWE-307* in the wild, in a real
product, found and fixed years after the vulnerable behavior shipped.

Rebuilding it here means you experience the same "wait, what?" moment a real researcher did:
you're not trying to sneak past the lockout. You're trying to **trigger it on purpose**, because
triggering it *is* the exploit.

---

## Why this bug exists (the mental model)

A developer implements account lockout with completely reasonable intentions: count failed
attempts, and *do something protective* once a threshold is crossed. Somewhere in translating
"do something protective" into code, the actual instruction became "reset this account's
credential state" instead of "prevent further login attempts." Those sound similar in a design
meeting and are worlds apart in an implementation — one closes the door, the other quietly
swaps the lock.

This is a specific, recurring failure mode worth naming: **treating "the control activated" as
equivalent to "the control worked."** A test plan that only checks *"does something happen at
the threshold?"* would see this bug and mark it as a pass — something clearly *did* happen. Only
a test plan that checks *"can I still get in after the threshold, and how?"* catches it. That
distinction — observable trigger vs. verified effect — is the whole lesson, and it generalizes
far past lockouts: rate limiters, WAF rules, and intrusion-prevention systems all have the same
failure shape available to them if nobody checks what "triggered" actually *does*.

---

## The R6 framing

**Oryx** doesn't defend a doorway by holding it shut — his entire kit is about smashing through
walls and floors himself, moving *through* obstacles rather than sealing them. A lockdown that,
once triggered, opens a new way in instead of closing the existing one is Oryx's whole philosophy
turned into a bug: the barrier becomes a hole the moment it activates.

**Thermite's** signature tool is a literal **Breach Charge** — exactly what you're using here,
conceptually: you're not picking a lock, you're deliberately detonating the control itself and
walking through what's left. The mission name in-universe (*"Breach Charge Detonated"*) isn't
flavor text layered on afterward — it's the accurate description of what the exploit *is*.

---

## Walking through what you had to do (and what to notice)

### Step 1 — Recognize there's nothing to find, only something to trigger

The instinct from Operations 02–03 is "there's a credential in here somewhere, go find it."
Here that instinct actively wastes your time. `g.mendel`'s real password on this system is
generated randomly at server start and handed to no one — it is, by design, not obtainable.

*What to pay attention to:* not every mission is a search problem. Sometimes the fastest path
to the answer is recognizing there's nothing to search for, and redirecting effort toward
*behavior* instead of *secrets*.

### Step 2 — Attack the account on purpose, methodically, and read every response

This flips the entire posture of the previous three operations. There, failing to get in was a
means to an end (or something to minimize). Here, **generating failures is the objective.**
OWASP's own test methodology for this exact WSTG item (straight from your course notes) is
explicit about doing this *incrementally and observantly*: try 3 times, check; try 4, check; try
5, check — not "spam blindly and hope." Reading the response text on *every single attempt*, not
just the first and last, is what surfaces a mid-sequence signal you'd otherwise miss entirely.

*What to pay attention to:* when a mission's goal is to reach a state (not find a value), your
job shifts from *guessing* to *instrumenting* — log everything, diff every response, and don't
assume the interesting moment is the last one.

### Step 3 — Notice there are two distinct signals, not one

Around the midpoint of the attempt range, the message shifts once — to something that sounds
like a side effect (a notification was sent, in the real bug this was mail-related). That shift
is real, and worth noting, but it is **not** the vulnerability. It's closer to background noise
that happens to be observable. The real event is a **second**, later shift, right at the actual
threshold.

*What to pay attention to:* don't stop investigating the moment you see *any* change. A system
under repeated abuse can have several observable side effects; only some of them are the actual
security-relevant one. Distinguishing "interesting" from "exploitable" is a skill in itself.

### Step 4 — Test the assumption behind the second signal, not just its existence

The message at the threshold ("Account requires administrator re-authentication") *reads* like
a lockout confirmation. It would be easy to log that as "confirmed: lockout triggers at N
attempts" and move on — technically true, and exactly the kind of test-plan gap described above.
The actual next step: try to log in anyway. Not with a guess — with the one input an attacker
doesn't reflexively try: **nothing.** An empty password field is the natural probe once you
suspect a credential got reset rather than an account getting locked, because "reset to what?"
is the obvious follow-up question a reset implies and a lock does not.

*What to pay attention to:* whenever a message implies a security outcome ("locked," "blocked,"
"denied"), verify the outcome directly instead of trusting the message. The message is UI copy.
The outcome is whatever the code actually does.

### Step 5 — Chaining: same target, fourth system, same lesson repeating with a twist

`g.mendel` again — but notice this system's lockout is scoped correctly (tracked server-side,
per account, not per your session or IP, which is the *right* way to build it per your course
notes' own testing checklist). The scoping isn't the bug this time. That's worth sitting with:
a control can get the *architecture* right and still fail completely on *behavior*. Getting one
axis of a security control correct doesn't imply the others are.

---

## The actual code behind it, in plain language

**1. State tracked correctly — per account, not per session**

```python
OP4_ATTEMPT_COUNTS = {}    # username -> failed-attempt count, in-memory
OP4_BLANKED = set()        # usernames whose stored credential has been wiped to ""
```

This part is *not* the bug. Attempts are counted against the account being attacked, globally —
exactly what WSTG's own checklist asks you to verify ("does lockout apply per username, per IP,
or both?"). Dropping cookies or attacking from a fresh session doesn't reset this counter,
because it isn't stored in a cookie at all.

**2. The threshold firing — and what "firing" actually does**

```python
if count >= OP4_THRESHOLD:
    OP4_BLANKED.add(username)           # "lockout" fires -> wipes the credential instead
    return render_template("op4_login.html",
        error="Account requires administrator re-authentication."), 401
```

This is the entire vulnerability in two lines. `OP4_THRESHOLD` is crossed, and the response
`add()`s the username to a set representing "credential wiped" — not "locked out." Nothing here
stops further login attempts. Something here makes a *specific* further login attempt succeed.

**3. The blanked-credential check — why an empty password works**

```python
if username == OP4_USER and username in OP4_BLANKED:
    if password == "":                     # VULN: the wiped credential is an empty string
        session["op4_authed"] = True
        return redirect(url_for("op4_console"))
    return render_template("op4_login.html",
        error="Account requires administrator re-authentication."), 401
```

Once `username in OP4_BLANKED`, the *only* password that will ever work again is the empty
string — because that's what the "credential" now literally is. Every other password, including
the real original one, is checked against nothing (this branch never reaches the real-password
comparison at all once blanked), which is itself worth noticing: **the legitimate account owner
is now locked out by their own real password**, while an attacker who knows to send nothing
walks straight in. The control doesn't just fail to protect — it inverts who has access.

---

## Self-check — can you explain these without looking back up?

1. Why is "the control did something at the threshold" not sufficient evidence that the control worked?
2. Why was attacking `g.mendel` on purpose, repeatedly, the correct move here instead of something to avoid?
3. Why did this mission include two separate message shifts instead of one, and how do you tell which one matters?
4. Why does the legitimate account owner end up locked out by their *real* password once the credential is blanked, while an attacker who sends nothing gets in?
5. What part of this mechanism's design was actually correct, and why doesn't that save it from being a critical finding?

---

## Answer key (reference)

- **Target:** `g.mendel` (confirmed in Op01) — no password to find; the real one is random and
  never disclosed.
- **Trigger:** 50 consecutive failed login attempts against `g.mendel` (a decoy message shift
  happens at attempt 15 — real, but not itself exploitable).
- **Exploit:** log in with `g.mendel` and an **empty** password after the threshold.
- **Flag:** `R6S{thermite_breached_oryx_broken_lockdown}`
- **Automated:** `python3 solvers/op4.py http://localhost:8000` — spams wrong passwords, watches
  for both message shifts, then attempts the blank-password login.

### Manual walkthrough

```bash
# spam 50 wrong passwords against the confirmed admin account, on purpose
for i in $(seq 1 50); do
  curl -s -c /tmp/op4.cj -b /tmp/op4.cj -X POST http://localhost:8000/op4/login \
    -d "username=g.mendel&password=wrong$i"
done | grep -o 'security notification\|administrator re-authentication' | uniq -c
# -> shows the decoy shift once (~attempt 15), then the real one (attempt 50)

# now the actual exploit -- log in with NOTHING in the password field
curl -s -c /tmp/op4.cj -b /tmp/op4.cj -X POST http://localhost:8000/op4/login \
  -d "username=g.mendel&password=" -o /dev/null -w "%{http_code}\n"
# -> 302

curl -s -c /tmp/op4.cj -b /tmp/op4.cj http://localhost:8000/op4/console | grep -o 'R6S{[^}]*}'
```

### Report language

- **Finding (WSTG-ATHN-03):** Upon reaching the account-lockout failure threshold, the
  application does not restrict further authentication attempts. Instead, it resets the target
  account's stored credential to an empty string, after which the account can be accessed with
  a blank password. This mirrors a previously disclosed real-world vulnerability class (Tiki
  Wiki CMS Groupware). *CWE-307 — Improper Restriction of Excessive Authentication Attempts.*
- **Impact:** Critical. An attacker who deliberately triggers the intended defensive mechanism
  gains full account access with no knowledge of any valid credential. The legitimate account
  owner is simultaneously locked out by their own real password, since the stored credential no
  longer matches it.
- **Remediation:** On threshold breach, restrict further login attempts (true lockout, time-based
  or administrator-cleared) — never modify, reset, or clear the stored credential as a
  side effect of failed authentication. Add alerting on repeated failures so the threshold event
  itself is reviewed, not just silently actioned. Test lockout mechanisms by verifying the
  *actual post-threshold access state*, not just that a response message changed.

---

# Operation 05 — Ghost in the Panel · Blitz ⚔ Aruni · WSTG-ATHN-04

## The one-sentence lesson

**"Is this request authenticated?" and "does this request contain a cookie that looks like it
came from an authenticated session?" are two completely different questions — and a server that
only ever answers the second one has no real authentication at all.**

Operations 01–04 all made you deal with *something* — a password, a PIN, a challenge, a failure
threshold. This mission has none of that. There is no login form anywhere in it. That's not a
missing feature; it's the finding.

---

## This mission is a real, disclosed bug — not a hypothetical

This rebuilds a pattern from a real, publicly documented vulnerability in the **Online Airline
Booking System** (Exploit-DB ID 39167) — the exact lab your course notes cover. The real
application's admin panel ran this check, in PHP, verbatim:

```php
if(!isset($_COOKIE['LoggedIn'])) die("You are not logged in!");
```

That's the *entire* authorization check. Not "is this cookie's value correct." Not "does this
cookie match a session record on the server." Just: does a cookie with this *name* exist at all.
An attacker who has never sent a username or password in their life can open dev tools, add
`LoggedIn=yes`, and reload — full admin access. This app's `/op5/panel` route is a direct,
line-for-line rebuild of that exact logic, translated into Python — with the cookie renamed to
`GateOverride` to match Aruni's actual gadget (more on that below). Same bug, same shape, a name
that fits the theme instead of the real disclosure's literal `LoggedIn`.

The same real disclosure had a second bug sitting right next to it: an installer script
(`application/install.php`) that was supposed to be removed after first-time setup, wasn't, and
let anyone — no login required to reach it — create a brand-new admin account from scratch.
`/op5/install` in this mission is that bug, faithfully rebuilt.

---

## Why this bug exists (the mental model)

Somewhere in a real development process, "check if the user is logged in" got implemented as
"check if a variable that *represents* being logged in is set" — and the two got conflated
because, from inside the application's own code, they look identical. `isset($_COOKIE['LoggedIn'])`
reads exactly like "verify the user's login" if you don't stop to ask *where that cookie value
came from* and *whether anything server-side ever actually vouches for it*. A cookie is just a
string the client hands back to you on every request — the server is fully responsible for
proving that string means what it claims to mean (via a signature, a server-side session store,
anything). This code skipped that step entirely. It didn't check the cookie was *valid*; it
checked the cookie *existed*, and "existed" is something any client can manufacture for free.

The installer being left reachable is a different mechanism but the same underlying failure:
**access control that exists in the UI (no link to the page) instead of in the server.** If the
only thing stopping you from reaching a page is that nobody put a button for it, you haven't
implemented an access control — you've implemented an inconvenience. WSTG-ATHN-04's own
categories name both of these directly: "unprotected authentication endpoints... often exposed
by accident (leftover setup pages, missing route guards)" and "parameter manipulation... auth
state stored/trusted client-side."

---

## The R6 framing

**Aruni's** signature gadget is the **Surya Gate** — an electrified barrier that's either active
or it isn't. That binary, presence-based nature is exactly the bug, which is why this app's
vulnerable cookie is literally named `GateOverride` instead of the real disclosure's generic
`LoggedIn`: the panel's check isn't "who are you," it's "is the gate switch flipped" — and a
switch has no memory of who flipped it or why. **Blitz** doesn't pick locks or crack codes; his
whole kit is a shield that blinds whoever's looking and lets him walk straight through the
opening. That's this mission, mechanically: you're not defeating a check, you're walking through
a gate that was never really checking anything to begin with.

---

## Walking through what you had to do (and what to notice)

### Step 1 — Read the denial message as information, not just as a rejection

`"You are not logged in!"` is oddly specific for a generic access-denied page. It's not "403
Forbidden" or "Access restricted." It names a *state* — "logged in" — which implies the check is
looking for evidence of that state somewhere in your request, rather than doing anything more
sophisticated like validating a token's signature or looking you up in a database.

*What to pay attention to:* denial messages are rarely meaningless. Precise, unusual wording is
often a direct hint about the mechanism behind the check, not just its outcome.

### Step 2 — Ask what "logged in" would even leave behind, then supply it yourself

A real login flow's job is ultimately to hand the client *something* to prove authentication on
future requests — almost always a cookie. The critical follow-up question, and the entire
content of WSTG-ATHN-04, is: **does the server cryptographically trust that cookie, or does it
just check that the cookie exists?** The only way to find out is to try supplying one yourself —
and the exact name isn't something you're meant to guess blind. It's discoverable two
independent ways: a leftover developer comment sitting in the denial page's raw HTML source
(view-source it, don't just read what's rendered), or the `Set-Cookie` response header handed
back by the leftover installer endpoint (Step 3). Once you have the name, there's no cleverness
to the value — `GateOverride=granted`, `GateOverride=1`, `GateOverride=banana` — all of them
pass, because the check never looks at the *value* at all.

*What to pay attention to:* any time authentication state lives in something the client
possesses (a cookie, a hidden form field, a query parameter) rather than something the server
looks up, that state is a hypothesis to test, not a fact to trust.

### Step 3 — Go looking for what isn't linked

The second finding can't be stumbled into by clicking around the UI — nothing points at
`/op5/install`. This is the first mission in the campaign where **forced browsing** (trying
paths that aren't advertised anywhere, using a wordlist of common names) is the only way to find
part of the attack surface. This matters because a real application's *linked* pages are not its
*entire* attack surface — old setup tools, debug endpoints, and admin bootstrapping scripts
routinely outlive their intended lifespan without ever being referenced by a single link or
button.

*What to pay attention to:* "I can't find a way to it in the app" is not the same claim as "it
doesn't exist." Directory/endpoint enumeration is how you close that gap.

### Step 4 — Confirm you have two separate findings, not one

Both paths land you on the same panel with the same flag, which could make it tempting to report
this as a single bug. It isn't. Fixing the cookie check (making `/op5/panel` validate a real
signed session) would do *nothing* to close `/op5/install` — that endpoint hands out valid
sessions to anyone regardless of how the panel itself is protected afterward. Independently,
fixing the installer without fixing the cookie check leaves the forgeable-cookie bypass fully
intact. Each is exploitable completely on its own.

*What to pay attention to:* two bugs that produce the same *outcome* are not necessarily the same
*bug*. Test each bypass in isolation before concluding they're duplicates — a fix for one
frequently leaves the other completely untouched.

---

## The actual code behind it, in plain language

**1. The entire access check — presence, not proof**

```python
@app.route("/op5/panel")
def op5_panel():
    if not request.cookies.get("GateOverride"):   # VULN: presence-only check, client-controlled
        return render_template("op5_panel.html", granted=False), 403
    mark_solved(5)
    return render_template("op5_panel.html", granted=True, flag=OP5_FLAG)
```

`request.cookies.get("GateOverride")` reads whatever the client sent, with whatever value the
client chose, completely unsigned and unverified. There's no comparison against a stored
session, no signature check, nothing server-side backing this decision at all. This is the
Python translation of `isset($_COOKIE['LoggedIn'])` from the real disclosure — same bug, same
shape, renamed to match Aruni's Surya Gate instead of the original's generic name.

(Worth noting separately: the campaign's *own* progress-tracking cookie — Flask's `session`,
used by `mark_solved()` — is properly signed with a secret key and cannot be forged this way.
The vulnerability is specific to the app-under-test's home-rolled `GateOverride` cookie, not to
cookies in general. Don't walk away thinking "cookies are insecure" — the lesson is "an
*unverified* cookie is insecure.")

**2. The leftover endpoint — zero auth required to reach it, and it mints the trusted cookie**

```python
@app.route("/op5/install", methods=["GET", "POST"])
def op5_install():
    if request.method == "GET":
        return render_template("op5_install.html")
    callsign = (request.form.get("callsign") or "backdoor.op").strip() or "backdoor.op"
    resp = make_response(render_template("op5_install.html", done=True, callsign=callsign))
    resp.set_cookie("GateOverride", "granted")
    return resp
```

No decorator, no check, no gate of any kind guards this route — it's a plain Flask endpoint like
any other, distinguished only by not being linked from `hub.html` or any other template. Anyone
who finds the path can POST to it and walk away with exactly the cookie `/op5/panel` trusts.

**3. How you were meant to find the name — a leftover comment, not a guess**

```html
<!-- TODO(dev): Surya Gate integration is still using the legacy check (raw
     GateOverride cookie presence) instead of a real signed session. ... -->
```

This sits in `op5_panel.html`'s denied-state markup — never rendered on screen (HTML comments
are invisible to the browser's rendered output), but sitting in plain text in the raw response
body. `curl`, "View Source," or Burp's response viewer all show it immediately. This is the same
principle as Operation 02's exact policy regex sitting in client-side JS: the ground truth is
*discoverable by inspection*, never something you're supposed to brute-force blind.

---

## Self-check — can you explain these without looking back up?

1. What's the actual difference between "a cookie exists" and "a cookie is valid," and why does only one of those provide real security?
2. Why was the denial message ("You are not logged in!") worth reading closely instead of just noting that access was denied?
3. Why does fixing `/op5/panel`'s cookie check do nothing to close `/op5/install`, and vice versa?
4. Why can't the second finding be discovered by browsing the app's UI, and what technique closes that gap?
5. The campaign's own session cookie (used to track your progress at Command) is not vulnerable to this attack. What's structurally different about it compared to `GateOverride`?
6. Name the two independent, non-guessing ways to discover the exact cookie name this mission relies on.

---

## Answer key (reference)

- **Target:** `/op5/panel` — no credentials exist to find; the check is bypassable entirely.
- **Flag:** `R6S{blitz_ghosted_arunis_gate_GateOverride=granted}`
- **Path A (forge the cookie):** discover the name via the leftover HTML comment on the denial
  page, then set `Cookie: GateOverride=granted` (any value works) and request the panel
  directly. No other endpoint needed at all.
- **Path B (leftover installer):** `POST` to `/op5/install` with any `callsign` value — no auth
  required to reach it — which hands back a working `GateOverride` cookie via `Set-Cookie`.
- **Automated:** `python3 solvers/op5.py http://localhost:8000` — demonstrates both paths
  independently (each discovering the cookie name its own way), confirming each works standalone.

### Manual walkthrough

```bash
# confirm the denial, its exact wording, AND view-source the leftover comment
curl -s http://localhost:8000/op5/panel | grep -o 'You are not logged in!'
curl -s http://localhost:8000/op5/panel | grep -o 'raw[^)]*cookie presence'

# Path A -- forge the discovered cookie directly, zero other requests
curl -s -b 'GateOverride=granted' http://localhost:8000/op5/panel | grep -o 'R6S{[^}]*}'

# Path B -- the leftover, unlinked installer (found via forced browsing / dirb)
curl -s -c /tmp/op5.cj -X POST http://localhost:8000/op5/install -d 'callsign=backdoor.op' \
  | grep -o 'Provisioning complete'
curl -s -b /tmp/op5.cj http://localhost:8000/op5/panel | grep -o 'R6S{[^}]*}'
```

A real forced-browsing pass would look like:
```bash
dirb http://localhost:8000/op5/ /usr/share/dirb/wordlists/common.txt
```

### Report language

- **Finding 1 (WSTG-ATHN-04):** The Operator Command Panel's authorization check verifies only
  the *presence* of a client-supplied `GateOverride` cookie, not its integrity or origin. Any
  client can set this cookie to an arbitrary value and gain full access with no valid
  credentials. *CWE-287 — Improper Authentication; CWE-565 — Reliance on Cookies without
  Validation.*
- **Finding 2 (WSTG-ATHN-04):** An unauthenticated, unlinked deployment/provisioning endpoint
  (`/op5/install`) remains reachable in production and issues a valid `GateOverride` cookie to
  any anonymous request, independently bypassing all access control. *CWE-284 — Improper Access
  Control; CWE-1188 — Insecure Default Initialization of Resource.*
- **Impact:** Full administrative panel access with zero legitimate credentials, via either of
  two independent paths.
- **Remediation:** Replace the cookie-presence check with a server-side session store (or a
  signed/encrypted session token the server can cryptographically verify); remove or disable all
  installation/setup endpoints immediately after deployment, or gate them behind a
  one-time-use, expiring installation token; audit the full route table for endpoints reachable
  without authentication, not just the ones linked from the UI.

---

# Operation 06 — Back Door · Nomad ⚔ Kaid · WSTG-ATHN-08 (Finale)

## The one-sentence lesson

**A security fix only counts where it was actually deployed — every other door the same account
can be reached through still has the old bug, unless someone checked.**

This is the finale, and it's built to prove something experientially rather than just tell you
about it: you attack the exact same account, with the exact same wordlist, twice. Once it fails
almost immediately. Once it doesn't fail at all. Nothing about the account changed between those
two attempts — only the door you knocked on.

---

## This is real: alternative-channel auth bypass is one of the most common findings in modern engagements

Every earlier operation modeled a specific historical bug. This one models a *pattern*, because
it's less "one famous CVE" and more "the single most common gap" in real assessments today: an
organization hardens its flagship web login — real rate limiting, real lockout, generic errors,
maybe MFA — and never notices that a mobile app, a partner API, or a legacy integration
authenticates against the *same account store* with none of those controls. Your own course
notes name this directly: *"Even if the primary web app is perfectly hardened, a vulnerable API
endpoint that accepts the same credentials is a full bypass of everything."* That sentence is
this entire mission.

---

## Why this bug exists (the mental model)

Security hardening tends to get implemented *where the team is looking* — the main web app,
because that's the product, that's what gets audited, that's what shows up in a pen-test scope
document. A mobile backend API, an old integration endpoint, a partner-facing service: these get
built by a different team, at a different time, sometimes explicitly labeled "temporary" or
"legacy" and then never revisited, precisely because nobody's looking at them anymore. The
account data is shared (it has to be — it's the same users) but the *code path* that checks a
password is not shared at all. Fixing the login form's error messages doesn't touch the API's
error messages, because they're two completely separate functions that happen to enforce the
same business rule, written by different people, at different times, with different amounts of
care.

This is why WSTG-ATHN-08 is its own dedicated test category rather than a footnote on
WSTG-ATHN-03/07: **hardening is not a property of an account. It's a property of a code path.**
An account can be simultaneously "well protected" and "trivially compromised," depending
entirely on which door you're measuring.

---

## The R6 framing

**Kaid's** gadget, the *Rtila Electroclaw*, locks down electronic devices — a hardening tool,
thematically. But it only locks down what it's attached to; anything not wired into it stays
exactly as exposed as before. That's this mission's defender in one sentence: real protection,
incompletely deployed. **Nomad** doesn't attack the front door at all — her entire kit (Airjab
launchers) is about repositioning to hit from an angle the defense never accounted for. "Flank
the hardened position through the side nobody's covering" isn't a metaphor here; it's literally
what an HTTP client does when it talks to `/api/v1/login` instead of `/op6/login`.

---

## Walking through what you had to do (and what to notice)

### Step 1 — Take the claimed hardening seriously enough to test it, not assume it

The console's banner (generic errors ✔, real lockout ✔, rate limiting ✔) is not a lie, and it's
not a decoy to ignore either — it's a claim, and the correct move is exactly the same one WSTG
asks for on *every* control: verify it directly instead of trusting the copy. Running the
wordlist and watching a real `423 Locked` response (not a blanked credential, not a bypassable
message) confirms the claim is true. That confirmation is not wasted effort — it's what tells
you the web channel is a dead end and it's time to look elsewhere, instead of spending an hour
convinced you must be missing some trick against a target that was never going to give.

*What to pay attention to:* a control passing your test is a valid, useful result. Not every
mission ends with "and therefore this endpoint is broken" — sometimes it ends with "and
therefore I should test something else," and recognizing that moment is itself the skill.

### Step 2 — Recognize this lockout is a different animal from Operation 04's

Both return a "you're locked out" style response. The critical test — try the real credential
against the locked account — is the one that tells them apart. Operation 04's version let you
in with an empty password because the "lockout" secretly wiped the credential. This one refuses
*everything*, including the real password, because it's an actual lockout. Confirming that
difference is what tells you not to waste more time attacking this specific mechanism again.

*What to pay attention to:* two controls that produce the same rejected-request *symptom* can
have completely different underlying *mechanisms* — you met exactly this same distinction in
Operation 04, and recognizing the same shape of question reappearing (with a different, correct
answer this time) is worth noticing on its own.

### Step 3 — Go looking for the other door, using the exact technique Operation 05 taught

Nothing in the rendered page points anywhere else. View-source does. This is a direct callback
to Operation 05's central skill: the ground truth an application doesn't intend to expose is
often still sitting in the raw response, available to anyone who checks past what's rendered.
The fact that this technique reappears, solving a completely different kind of bug, is the
point — it's not an Operation-05-specific trick, it's a general habit worth having on every
target from now on.

*What to pay attention to:* skills from earlier operations are not single-use. The campaign
keeps reusing "read the source, not the render" and "measure a baseline, don't assume" because
real engagements reuse them constantly too.

### Step 4 — Run the identical attack against the new channel, and let the contrast be the evidence

This is the step that makes the finding undeniable rather than theoretical. You're not
hypothesizing that the API "might" be weaker — you have a direct, reproducible, side-by-side
result: same account, same 30 candidate passwords, same attacker, two outcomes. That contrast
*is* the impact statement. It's far more persuasive in a report than "the API lacks rate
limiting" on its own, because it demonstrates the hardening gap in terms of what an attacker
actually gains, not just what control is technically absent.

*What to pay attention to:* when you can demonstrate the same attack succeeding on one channel
and failing on another, always do the failing one first and document it. A finding that says
"and here's proof the *other* door is properly locked" makes the open one land harder.

### Step 5 — The API brings back a bug you already fixed once

The JSON error codes (`unknown_user` vs. `invalid_password`) are Operation 01's enumeration bug,
verbatim, on a channel that was never touched by whatever fixed it on the web login. This isn't
reused for novelty — it's making the mission's core point at a second layer: hardening doesn't
propagate automatically, *for any individual fix*, not just for lockout. Every lesson from this
whole campaign needs to be checked per-channel, not assumed campaign-wide.

---

## The actual code behind it, in plain language

**1. A genuinely correct lockout — contrast this with Operation 04's**

```python
if username == OP6_USER and username in OP6_WEB_LOCKED:
    return render_template("op6_login.html",
        error="Account locked due to repeated failed attempts. Contact an administrator."), 423

if username == OP6_USER and password == OP6_PASSWORD:
    session["op6_authed"] = True
    return redirect(url_for("op6_console"))     # a genuinely correct login always works

if username == OP6_USER:
    OP6_WEB_ATTEMPTS[username] = OP6_WEB_ATTEMPTS.get(username, 0) + 1
    if OP6_WEB_ATTEMPTS[username] >= OP6_WEB_THRESHOLD:
        OP6_WEB_LOCKED.add(username)            # real lockout -- no bypass, unlike Op04
```

Once `username in OP6_WEB_LOCKED`, that check fires *first*, before the password comparison ever
runs — meaning even the genuinely correct password is rejected. Nothing wipes the credential.
Nothing lets a blank value through. This is what Operation 04's bug should have looked like.

**2. The same account, a second code path, zero shared hardening**

```python
@app.route("/api/v1/login", methods=["POST"])
def op6_api_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""

    if username != OP6_USER:
        return jsonify(error="unknown_user", message="No account with that username."), 401
    if password != OP6_PASSWORD:
        return jsonify(error="invalid_password", message="Password incorrect."), 401

    session["op6_authed"] = True
    return jsonify(success=True, message="Authenticated.", next="/op6/console")
```

Notice what's absent: no `OP6_WEB_ATTEMPTS` lookup, no `OP6_WEB_LOCKED` check, nothing counting
failures at all. This function checks the password directly against `OP6_PASSWORD` — the exact
same constant `/op6/login` checks — proving it's the same account, reachable with none of the
same protection.

**3. The discovery mechanism — the same View Source pattern as Operation 05, again on purpose**

```html
<!-- TODO(dev): heads up for whoever's on call -- the legacy mobile client still hits
     /api/v1/login directly, bypassing this console entirely. ... -->
```

---

## Campaign retrospective — what the whole thing was building toward

Six operations, one throughline: **every stage tested whether a claimed or assumed security
property was actually true.**

| Op | What looked true | What was actually true |
|---|---|---|
| 01 | "Failed logins reveal nothing" | Timing and message differences revealed everything |
| 02 | "A password policy makes passwords hard to guess" | A rigid, disclosed formula makes them enumerable |
| 03 | "A math challenge stops bots" | It stops nothing; and the check could be skipped outright |
| 04 | "The lockout protects the account" | The lockout *was* the compromise |
| 05 | "You need to log in to reach the panel" | The panel was never checking who you were |
| 06 | "The hardened console means the account is safe" | Safety wasn't checked on every door it's reachable from |

If there's one instinct worth carrying out of this entire campaign, it's the one this finale
makes unavoidable: **don't verify that a control exists. Verify that it's the only way in.**

---

## Self-check — can you explain these without looking back up?

1. Why is it meaningful, not wasted effort, that the web login genuinely locked you out?
2. What specifically distinguishes this lockout from Operation 04's, and what single test tells them apart?
3. Why does the API bringing back Operation 01's enumeration bug matter beyond "it's a second bug" — what does it prove about how hardening actually gets applied?
4. Why is "same wordlist, two channels, two outcomes" a stronger piece of evidence than describing the API's missing rate limit on its own?
5. Across all six operations, what's the one investigative habit that shows up the most times, in the most different disguises?

---

## Answer key (reference)

- **Target:** `g.mendel` — same account across the whole campaign.
- **Web login:** genuinely hardened. Locks out permanently after 5 failed attempts (`423`), no
  bypass. Correct password succeeds instantly if tried directly.
- **Alternative channel:** `/api/v1/login`, JSON, discovered via a leftover dev comment in
  `/op6/`'s HTML source (View Source / curl, not rendered).
- **Password (works on both channels):** `Fallback2019` — position 22 of 30 in
  `wordlists/op6_passwords.txt`, deliberately placed past the web lockout's 5-attempt threshold.
- **Flag:** `R6S{nomad_flanked_kaid_via_the_forgotten_api}`
- **Automated:** `python3 solvers/op6.py http://localhost:8000` — runs the wordlist against the
  web login first (demonstrates the lockout firing at try 5), discovers the API, then runs the
  identical wordlist against it (succeeds at try 22).

### Manual walkthrough

```bash
# Part 1 -- confirm the web lockout is real (will take ~5 requests)
for pw in password123 Welcome1 'Passw0rd!' Summer2024 'Admin123!' Corp2024!; do
  curl -s -o /dev/null -w "%{http_code} " -X POST http://localhost:8000/op6/login \
    -d "username=g.mendel&password=$pw"
done; echo
# -> ends in 423 well before the wordlist runs out

# Part 2 -- find the alternative channel
curl -s http://localhost:8000/op6/ | grep -o '/api/[a-zA-Z0-9/]*'

# Part 3 -- same credential, different channel, no lockout
curl -s -X POST http://localhost:8000/api/v1/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"g.mendel","password":"Fallback2019"}'
# -> {"success": true, ...}

# grab the flag using the session cookie curl just received
curl -s -c /tmp/op6.cj -b /tmp/op6.cj -X POST http://localhost:8000/api/v1/login \
  -H 'Content-Type: application/json' -d '{"username":"g.mendel","password":"Fallback2019"}' >/dev/null
curl -s -b /tmp/op6.cj http://localhost:8000/op6/console | grep -o 'R6S{[^}]*}'
```

### Report language

- **Finding (WSTG-ATHN-08):** While the primary web console enforces generic error messages,
  account lockout, and rate limiting, a legacy REST API (`/api/v1/login`) authenticates against
  the identical account store with none of these controls, and additionally discloses account
  existence via distinct error codes. *CWE-307 — Improper Restriction of Excessive
  Authentication Attempts (absent on this channel); CWE-204 — Observable Response Discrepancy
  (username enumeration via API error codes).*
- **Impact:** Complete bypass of all authentication hardening applied to the primary channel.
  Demonstrated: an identical wordlist that triggers lockout against the web login in 5 attempts
  succeeds without resistance against the API.
- **Remediation:** Apply identical authentication controls (rate limiting, lockout, generic
  errors, MFA where applicable) to every code path that authenticates against a shared account
  store — not just the primary web application. Maintain an inventory of all authentication
  entry points (web, mobile API, partner integrations, legacy services) as part of the security
  review process, specifically so that a hardening pass has a checklist to verify against rather
  than relying on someone remembering every channel exists.

---

**Campaign complete.** All six operations, all six WSTG-ATHN test categories, one continuous
thread: verify, don't assume — on every channel, not just the one you were shown first.
