# 🔓 Masquerade Operation 07 — The Second Factor · Ash ⚔ Warden

**Spoilers below.** If you haven't played yet, use [`CHALLENGER.md`](CHALLENGER.md) first.

## The one-sentence lesson

**Two-factor authentication almost never fails because someone broke the code — it fails because
the *process around the code* was weak: no throttling on guesses, no enforcement on every
endpoint, and a recovery path softer than the factor it replaces. Test the edges, not the happy
path.**

This mission has three stages on purpose, and — unlike a chained exploit — they are three
*parallel* doors. None of them attacks the one-time code's math. Each attacks a different piece
of the machinery bolted around it, and each on its own is enough to walk in.

---

## First, the fundamentals — worth being precise about

**2FA = proving identity with evidence from two different _categories_**, so a stolen password
alone isn't enough:

| Category | Example |
|---|---|
| **Something you know** | Password, PIN |
| **Something you have** | Phone, hardware token, authenticator app |

One-line rule: **two passwords ≠ 2FA. Password + OTP = 2FA.** The factors must come from
different categories, or you've just added a second thing to guess.

### The strength ladder of "something you have"

| Type | How it works | Why it's ranked here |
|---|---|---|
| **SMS OTP** | code texted to you | *Weakest* — the mobile network is an external channel: SIM-swap, interception, SS7 |
| **Email OTP** | code/link emailed | *Weak* — only as strong as the email account, itself often just password-protected |
| **TOTP / authenticator app** | code derived locally from a shared secret + current time | *Strongest* of these — the code is **generated on-device, never transmitted to be delivered**, so there's no delivery channel to intercept |

**Exam takeaway:** SMS/email 2FA depends on an *external delivery channel* that can be hijacked;
TOTP generates the code **locally**, so there's nothing in transit to steal. That's the whole
reason authenticator apps outrank texts.

> Kafe's portal uses a delivered OTP ("sent to the duty phone") — the SMS/email family. But
> notice: **not one of this mission's three findings even cares which type it is.** They'd all
> work identically against gold-standard TOTP, because none of them attacks the code channel.
> That's the point — and it's why they matter more than the SMS-vs-TOTP debate.

---

## The R6 framing

**Ash** blows openings — Breaching Rounds, fired from range, fast and direct, several quick
holes rather than one clever pick. That's this mission exactly: three forceful, low-subtlety
openings in the same wall, taken in whatever order you like.

**Warden's** Glance Smart Glasses let him *see through* smoke and flashes — clarity where the
enemy expects a blind spot. A second factor is supposed to be that clarity for a defender: even
if the password's gone, you still see who's real. Here it's the opposite — the 2FA is a
smokescreen that only *looks* protective, and anyone who bothers to look sees straight through
it. Hence the flag: `warden_saw_through_the_second_factor`.

---

## Stage 1 — No rate limiting / lock-out (WSTG-ATHN-03)

### The bug

The OTP is 4 digits — 10,000 values — and `POST /api/verify-otp` does **nothing** on a wrong
guess except say "wrong." No delay, no lock-out after N failures, no invalidation of the
challenge. So the entire space is searchable online, and the average attacker lands the real
code in ~5,000 requests and a few seconds.

```bash
# logged in (first factor done), cookie in cookies.txt:
for i in $(seq -w 0 9999); do
  curl -s -X POST http://localhost:8000/masquerade/op7/api/verify-otp \
       -b cookies.txt -d "otp=$i" | grep -q '"ok": true' && { echo "CODE $i"; break; }
done
```

### Why length is a red herring

A 6-digit code (1,000,000 values) falls to the *identical* attack — it just runs longer. The
vulnerability is not the code's size, it's that **nothing watches for the brute force.** From
your notes: *"No rate limiting on a 6-digit OTP = a brute-forceable password in disguise."*

### The fix

Rate-limit verification (exponential backoff), lock the *challenge* (not just the account —
watch for lock-out-as-DoS) after a handful of failures, expire the code in ~30–60s, and make it
strictly single-use. Any one of those alone kills the online brute force; real systems layer
them.

---

## Stage 2 — 2FA not enforced server-side (forced browsing)

### First you have to *find* it — that's half the finding

This is forced browsing, and forced browsing only means anything when the door is actually
hidden. The app never links `/masquerade/op7/staff/export` anywhere in its UI — you discover it
by recon, the same way you would on a real engagement:

- **`/robots.txt`** disallows `/masquerade/op7/staff/` — the classic case of a site's own
  "please don't crawl this" file handing an attacker the exact paths worth looking at.
- **The portal's client JS** (`/static/js/op7-portal.js`, loaded on the two-step page) names the
  endpoint outright in its config, with a leftover dev comment admitting it "isn't behind the
  second-factor check yet."
- **Content discovery** (`ffuf`/`gobuster` with a common wordlist) would turn up `staff` and
  `export` on their own.

If the app had simply shown you a button, none of that skill would be exercised — which is why it
doesn't.

### The bug — and why it's the most important one here

The vault (`/vault`) is correctly gated: reach it without finishing 2FA and it bounces you with
a 403. But the internal export (`/masquerade/op7/staff/export`) checks only that you cleared the
**password** step — it never checks whether the **OTP** step happened:

```python
# /masquerade/op7/staff/export
if not session.get("masq7_login"):   # proof of the FIRST factor only
    return redirect(...)
# ... hands over the protected data. It never checks `verified`.
```

So a signed-in attacker who has entered *no code at all* simply requests the endpoint and gets
the goods. This is **forced browsing** past a control that exists but was applied inconsistently.

This is the finding that matters most, because it's the most common one in the real world: 2FA
gets added as a screen in the login *flow*, and every endpoint is silently trusted to have "come
through" that flow. The moment one sensitive endpoint can be reached directly, the second factor
is decorative. It ties straight to your notes' **server-side vs client-side validation** point:
if the "2FA passed" decision isn't re-checked at the resource itself, the flow can be skipped by
calling the resource directly.

### The fix

Enforce the *full* authentication state (`verified == True`) as a check on **every** protected
endpoint — ideally one middleware/decorator applied centrally, so no route can forget. Never
treat "passed step 1" as "authenticated."

---

## Stage 3 — Weak recovery path

### The bug

"Lost your phone? Use a backup code." Backup codes here are `KAFE-0000`…`KAFE-9999` — a tiny,
**unthrottled** space, and any valid one skips the OTP entirely:

```bash
for i in $(seq -w 0 9999); do
  curl -s -X POST http://localhost:8000/masquerade/op7/api/backup \
       -b cookies.txt -d "backup=KAFE-$i" | grep -q '"ok": true' && { echo "KAFE-$i"; break; }
done
```

### Why this is a *separate* lesson from Stage 1

Even if you fixed Stage 1 — strong 6-digit TOTP, aggressive rate-limiting — this door is
**still open**, because the recovery path exists *specifically to bypass the factor*. A fallback
weaker than the thing it falls back from means the factor's strength never mattered. From your
notes: *"2FA is only as strong as its weakest recovery/fallback path,"* and *"backup codes are
often weaker than the 2FA itself."*

### The fix

Backup codes must be long, high-entropy, single-use, generated in a small fixed batch, and
throttled/lockable exactly like the primary factor. The same discipline applies to *every*
fallback: security questions (guessable/OSINT-able — treat as public), email-reset paths, and
"call support" flows (vishing bait).

---

## The secondary findings (report these too)

- **Missing single-use / replay:** a correct OTP here is never invalidated after use — present
  it again and it still works. OTP security rests on *two* properties, short lifespan **and**
  single-use enforcement; this app has neither. (Notes: *Token Replay*.)
- **Session not regenerated after 2FA:** the pre-2FA session is promoted in place rather than
  reissued — the same trust-boundary failure as **Operation 02 (session fixation)**. A session
  ID fixed *before* the victim completes 2FA stays valid *after* it.
- **Scope:** an OTP validated for login should never be accepted for a different sensitive action
  (payment, password change). OTPs must be bound to their purpose.

---

## Where this sits in the full 2FA-bypass map

Your notes group bypasses into three families. It's worth seeing which ones a *web* lab can
demonstrate hands-on, and which are situational/social:

| Family | Techniques | In this lab? |
|---|---|---|
| **Social engineering** | phishing (real-time proxy / Evilginx), vishing, SMiShing | No — these need a human victim; understand them conceptually |
| **Flaws in implementation** | weak recovery, session fixation before 2FA, poor token validation (replay), **no rate limiting**, **no server-side enforcement** | **Yes — this is Stages 1–3 plus the secondaries** |
| **Token interception** | MITM on plaintext, SIM-swap, SSL-stripping | No — channel/network attacks; know the risk of SMS specifically |

This lab lives entirely in the middle column — **implementation flaws** — because that's where a
web pentester actually operates, and where the highest-value findings almost always are.

---

## Pentester checklist (from the notes, mapped to this lab)

- [x] Is the OTP short and/or predictable? — 4 digits (**Stage 1**)
- [x] Is rate limiting / lock-out enforced on OTP submission? — no (**Stage 1**)
- [x] Is OTP validation enforced **server-side on every endpoint**? — no (**Stage 2**)
- [x] Are backup/recovery codes as strong as the primary factor? — no (**Stage 3**)
- [x] Is the OTP single-use (rejected on reuse)? — no (**secondary**)
- [x] Is the session ID regenerated after full 2FA? — no (**secondary**)
- [ ] Can the OTP for one action be replayed for another? — scope check, if the app has other actions
- [ ] Can an alternate login path (OAuth/SSO) skip 2FA entirely? — see Operation 06's SSO angle
- [ ] Is the OTP transmitted only over HTTPS, never HTTP? — channel/transport check

The mental model to carry out of here: **attackers rarely break the TOTP algorithm — they break
the process around it.** Rate limiting, enforcement, recovery, session handling, single-use.
Test the edges.

---

## Reference (official docs)

- NIST SP 800-63B — Digital Identity Guidelines (authenticators & OTP): https://pages.nist.gov/800-63-3/sp800-63b.html
- OWASP Authentication Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
- OWASP Multifactor Authentication Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html
- OWASP WSTG — Testing for Weak Lock-Out Mechanism: https://owasp.org/www-project-web-security-testing-guide/stable/4-Web_Application_Security_Testing/04-Authentication_Testing/03-Testing_for_Weak_Lock_Out_Mechanism.html

Good work, operator. 🎭
