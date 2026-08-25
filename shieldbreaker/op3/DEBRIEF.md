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
- **Automated (intended path):** `python3 shieldbreaker/op3/solver.py http://localhost:8000` — GETs a fresh
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
