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
- **Automated:** `python3 shieldbreaker/op4/solver.py http://localhost:8000` — spams wrong passwords, watches
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
