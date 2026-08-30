# 🔓 Masquerade Operation 04 — Signed, Not Sealed · Kali ⚔ Echo · WSTG-SESS-10

**Spoilers below.** If you haven't played yet, use [`CHALLENGER.md`](CHALLENGER.md) first.

## The one-sentence lesson

**A signature only protects a token if the verifier is the one who decides how to check it —
the instant the verifier lets the token's own header pick the algorithm, the token is
grading its own homework.**

Every other mission in this campaign gave you something real to steal, plant, or wait for: a
tampered field, a planted identifier, someone else's forged login. This one gives you none of
that. There's no victim, no password to guess, no signing key to crack. You manufacture a
fully "valid" credential entirely from your own head — which is exactly why this bug class
consistently ranks among the most severe JWT findings a real assessment turns up.

---

## Why this bug exists (the mental model)

A JWT's three segments exist for a reason, and it's worth being precise about what each one
actually is:

- **Header** — metadata *about* the token: which algorithm, what type. Base64url. Readable
  by anyone. Editable by anyone.
- **Payload** — the actual claims: who this token represents, what they're allowed to do.
  Base64url. Readable by anyone. Editable by anyone.
- **Signature** — the *only* segment that isn't just "readable text with extra steps." It's
  a cryptographic proof, computed by someone who holds a secret the attacker doesn't have.

The entire security model of a JWT rests on that third segment, and *only* on that third
segment. Header and payload are exactly as trustworthy as a Post-it note someone could have
written themselves — which is fine, as long as the signature is checked against something the
attacker can't produce.

The "none" algorithm vulnerability happens when a verifier reads the `alg` field from the
header — attacker-controlled, remember — and uses *that* to decide how to check the
signature. JWT's own spec (RFC 7518) defines `"none"` as a real, legal algorithm value, meant
for contexts where a token's integrity genuinely doesn't need protecting. A verifier that
honors `"none"` unconditionally — on tokens that absolutely do need protecting — has handed
the attacker a checkbox that says "please don't verify this." The attacker checks it. Every
time.

Think of it like a wax seal on an envelope, except the envelope also has a sticky note on the
outside that says "seal type: none, please don't check for a seal." A trustworthy mail carrier
reads the letter's *own claim* about whether it should be trusted. That's not verification.
That's the honor system, and attackers don't participate in the honor system.

---

## The R6 framing

**Kali's** CSRX 300 is a hard-hitting, precision one-shot weapon — she doesn't need to
negotiate, brute-force, or wear down a target with volume. One correctly placed shot ends the
engagement. That's this mission exactly: no password spray, no session to wait for, no
victim's browser to trick into anything. One correctly forged token, built once, ends it.

**Echo's** Yokai drone exists to sense what's happening remotely — a sonar pulse that reveals
and disrupts intruders from a distance, entirely independent of anyone physically checking a
door. It's a *remote verification* tool by design. The irony matches Operation 03's Melusi
before it: Echo's entire kit is built around confirming presence without trusting a claim at
face value — but the Chalet's own token verifier does the opposite. It asks the token to
report on itself, and takes the answer at face value. A defender built entirely around
independent verification is standing guard over a system with none.

---

## Walking through what you had to do (and what to notice)

### Step 1 — Get a real token and actually read it

Signing in with the provided account gets you a genuinely valid, correctly-signed HS256
token. Decode the header and payload yourself (or let the login page do it for you, which it
does specifically so you can't skip this step by accident). You should see something close
to:

```json
{"typ": "JWT", "alg": "HS256"}
{"sub": "retreat.member", "role": "member", "iat": 1788109248}
```

*What to pay attention to:* nothing here required a key. You read this exactly as easily as
the server did. WSTG-SESS-10 testing always starts by confirming that "encoded" really does
mean "not hidden from anyone" — the notes' own golden rule.

### Step 2 — Confirm the honest path works, and prove nothing on its own

Present your real token to `/masquerade/op4/ledger`. It works — you get your own `member`
role back, no flag. That's expected, and it's worth doing anyway: a report is stronger when
it shows the verifier behaving *correctly* right next to the case where it doesn't.

*What to pay attention to:* "the token got me in" isn't a finding by itself. Plenty of
completely secure JWT implementations authenticate you just fine. The question is what
happens to a token whose signature was never actually computed.

### Step 3 — Notice what `alg` actually is

The header field naming the algorithm isn't a server-side setting reflected back at you —
it's part of the same base64url blob you just decoded, sitting in a segment the client
produced. Ask directly: does the verifier hard-code which algorithm it expects, or does it
read the expectation from the very input it's supposed to be skeptical of?

*What to pay attention to:* this is the step that turns "I can read this token" into "I can
possibly control how it's checked." Reading a token's contents is table stakes. Controlling
the *rules* for verifying it is the actual vulnerability.

### Step 4 — Build a token that tells the verifier not to bother

Set `alg` to `"none"` in the header. Set whatever claims you want in the payload — most
importantly, the role field you already know from Step 1. Base64url-encode both segments
yourself (or with a tool), join them with a dot, and leave the signature segment **empty but
present**: `header.payload.` — three segments, the last one just happens to be zero bytes.

*What to pay attention to:* you never touched a signing key, because there was nothing to
touch. This isn't a weak-secret or cracked-signature attack — it's a token that pre-emptively
tells the verifier "there's nothing here to check," and a broken verifier that agrees.

### Step 5 — Present it exactly like a real client would

`Authorization: Bearer <forged token>`, same header a legitimate client would send, same
endpoint. No cookie, no session, no server-side state to manipulate — the entire attack
surface is the string you're holding.

*What to pay attention to:* the response tells you the role the server believes you hold.
If that role is one you were never granted, by anyone, using any real credential — that's the
proof. Compare it against Step 2's honest response side by side in your report.

---

## The actual code behind it, in plain language

**1. Issuing a real token — nothing wrong here, this is the baseline**

```python
def masq4_issue_token(username, role):
    header = {"typ": "JWT", "alg": "HS256"}
    payload = {"sub": username, "role": role, "iat": int(time.time())}
    h_b64 = masq4_b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p_b64 = masq4_b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    return f"{h_b64}.{p_b64}.{masq4_sign(h_b64, p_b64)}", header, payload
```

A real login gets a real HMAC-SHA256 signature, computed with a secret the player never sees.
Nothing here is the bug.

**2. Verifying a token — this is the entire vulnerability, in one branch**

```python
def masq4_verify_token(token):
    ...
    alg = str(header.get("alg", "")).strip().lower()
    if alg == "none":
        return True, payload                          # VULN: zero signature verification
    if alg == "hs256":
        if hmac.compare_digest(masq4_sign(h_b64, p_b64), sig_b64):
            return True, payload
        return False, "Signature does not match."
    return False, f"Unsupported algorithm: {header.get('alg')!r}"
```

That `if alg == "none": return True, payload` line is the entire bug. Everything else in this
function is *correct* — HS256 tokens really do get their signature checked, byte for byte,
against the real secret. The vulnerability isn't sloppy crypto. It's a single unconditional
trust decision, made using a value the attacker supplied.

A correct version doesn't ask the token what algorithm to use at all:

```python
# what SHOULD happen (not in this app):
ALLOWED_ALGS = {"HS256"}          # hard-coded by the server, never read from the token
alg = str(header.get("alg", "")).strip()
if alg not in ALLOWED_ALGS:
    return False, "Unsupported or disallowed algorithm."
if not hmac.compare_digest(masq4_sign(h_b64, p_b64), sig_b64):
    return False, "Signature does not match."
return True, payload
```

The fix isn't "add better none-handling." It's "stop asking the token how to verify itself,"
full stop — the server should have a fixed, hard-coded expectation regardless of what the
header claims.

**3. Reaching the flag requires that exact bypass, and nothing else**

```python
if payload.get("role") == MASQ4_DIRECTOR_ROLE:
    mark_masq_solved(4)
    return jsonify({"ok": True, "role": payload.get("role"), "flag": MASQ4_FLAG})
```

There's no admin backdoor, no seeded director account, no alternate path. The only way
`payload.get("role")` ever equals `"director"` is if a token carrying that claim was accepted
— and the only way a token gets accepted without a correct HS256 signature is the `alg:none`
branch above.

---

## Self-check — can you explain these without looking back up?

1. In one sentence, why is a JWT's header just as attacker-controlled as its payload — and
   why does that matter specifically for the `alg` field?
2. What's the single missing design decision that would close this bug completely, even with
   every other line of the verifier unchanged?
3. Why does successfully presenting your own *real* token first strengthen a report about
   this vulnerability, even though that request isn't the finding?
4. This mission is the first in the campaign with no victim, no session to plant, and no
   password to guess. Why does that make it, if anything, more severe than Operations 02 and
   03 — not less?
5. The notes mention algorithm-confusion attacks (tricking an RS256 verifier into checking a
   signature with HS256, using the public key as the HMAC secret) as a related but distinct
   bug. Why doesn't that attack apply here, even though this app also only implements HS256?

---

## Answer key (reference)

- **Test account:** `retreat.member` : `Chalet2024!` (given — not the point of this mission)
- **Vulnerable check:** `masq4_verify_token()` in `app.py` — `alg == "none"` skips signature
  verification entirely, matched case-insensitively
- **Role claim:** `role` — `"member"` on your real token, `"director"` is the target
- **Real endpoint:** `GET /masquerade/op4/ledger`, header `Authorization: Bearer <token>`
- **Flag:** `R6S{kali_forged_alg_none_into_the_directors_role}`
- **Automated:** `python3 masquerade/op4/solver.py http://localhost:8000`

### Manual walkthrough

```bash
# 1) log in, capture a real token
TOKEN=$(curl -s -X POST http://localhost:8000/masquerade/op4/login \
  -d 'username=retreat.member&password=Chalet2024!' \
  | grep -oP '(?<=select-all">)[^<]+')
echo "real token: $TOKEN"

# 2) decode it yourself -- note the two extra "=" padding characters base64url strips
echo "$TOKEN" | cut -d. -f1 | tr -- '-_' '+/' | base64 -d 2>/dev/null; echo
echo "$TOKEN" | cut -d. -f2 | tr -- '-_' '+/' | base64 -d 2>/dev/null; echo

# 3) forge a token: alg=none, role=director, empty signature (mind the trailing dot)
HEADER=$(echo -n '{"typ":"JWT","alg":"none"}' | base64 | tr -- '+/' '-_' | tr -d '=')
PAYLOAD=$(echo -n '{"sub":"kali","role":"director","iat":1}' | base64 | tr -- '+/' '-_' | tr -d '=')
FORGED="$HEADER.$PAYLOAD."
echo "forged token: $FORGED"

# 4) present it to the real endpoint -- no signing key involved anywhere
curl -s http://localhost:8000/masquerade/op4/ledger \
  -H "Authorization: Bearer $FORGED"
```

### Report language

- **Finding (WSTG-SESS-10):** The JWT verification logic trusts the `alg` field from the
  token's own (client-controlled) header to determine whether and how the signature is
  checked. Submitting a token with `"alg":"none"` — matched case-insensitively — causes the
  server to skip signature verification entirely and trust the payload's claims outright,
  allowing an attacker to forge a token asserting arbitrary claims (including elevated roles)
  without possessing any valid credential or the server's signing key.
  *CWE-347 — Improper Verification of Cryptographic Signature.*
- **Impact:** Complete authentication and authorization bypass. An attacker who has never
  logged in, and who possesses no valid credential of any kind, can forge a token granting
  themselves the highest privilege level the application defines, with zero interaction from
  any legitimate user.
- **Remediation:** Never derive the verification algorithm from the token itself. The server
  should hard-code exactly which algorithm(s) it accepts and reject any token specifying
  anything else — including `"none"` — before attempting verification. Most modern JWT
  libraries (PyJWT, `jsonwebtoken`, etc.) require the caller to explicitly pass an
  `algorithms=[...]` allow-list; omitting it, or including `"none"` in that list, reintroduces
  this exact bug.

---

**Next in this campaign:** Operation 05, *Exposed Claim* — JWT claims. Locked until this
one's cleared, revealed on Command the moment it is.
