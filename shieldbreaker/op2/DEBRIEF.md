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
- **Automated:** `python3 shieldbreaker/op2/solver.py http://localhost:8000` (session + token + baseline-diff detection + full cross-product enumeration)

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

For the full enumerated run: `python3 shieldbreaker/op2/solver.py` builds every `word + 2 digits + symbol`
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
