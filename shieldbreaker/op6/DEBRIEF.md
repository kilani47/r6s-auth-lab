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
- **Automated:** `python3 shieldbreaker/op6/solver.py http://localhost:8000` — runs the wordlist against the
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
