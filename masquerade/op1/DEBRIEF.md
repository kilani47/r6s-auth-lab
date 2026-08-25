# 🔓 Masquerade Operation 01 — The Teller's Trust · Iana ⚔ Alibi · WSTG-SESS-01

**Spoilers below.** If you haven't played yet, use [`CHALLENGER.md`](CHALLENGER.md) first.

## The one-sentence lesson

**A session token is only as trustworthy as whatever the server does with it on the way back
in — and a field that merely *looks* protected (encoded, hashed, checksum-shaped) is worthless
if the server never actually recomputes and compares it.**

This is the first operation in a whole new campaign, and it's deliberately the "clean, single
lesson" one — the same role Callsign Recon played for Shieldbreaker. Every future Masquerade
operation (session fixation, CSRF, JWT forgery, OAuth abuse, 2FA bypass) is a variation on the
exact question this mission asks: **once the app trusts a token, what — if anything — is
actually verifying that trust is deserved?**

---

## Why this bug exists (the mental model)

Session management exists because HTTP is stateless — the server needs *something* handed back
on every request to know who's asking. The textbook-correct answer is: hand the client an
**opaque, unguessable, server-verified reference** (a random ID that points to state kept
server-side, or a token whose contents are cryptographically signed so tampering is
detectable). The textbook-*common* mistake is building a token that instead **encodes the
actual authorization decision inside itself** — `username:role:something` — and trusting
whatever comes back, because decoding it feels like "checking" it.

This app's bug goes one step further, and it's worth naming precisely because it's an extremely
common real-world pattern: the token *has* a field that looks like a security control (an
8-character hex string sitting where a checksum or HMAC would sit) — but nothing on the read
path ever recomputes it and compares. A field that exists but is never verified provides
**zero** actual protection while still making the token *look* engineered and intentional to
anyone giving it a quick glance. That gap between "looks checked" and "is checked" is the
entire vulnerability, and it's exactly why your course notes' methodology insists on the same
question at every step: *does the server independently validate, or does it trust the client?*
You have to test it, not read the shape and assume.

---

## The R6 framing

Both operators this time are built around the exact same concept as the vulnerability: **a
false identity that's accepted as real.** **Iana's** Gemini Replicator projects a holographic
double of herself — a copy good enough to draw a defender's attention and trust, without being
her. **Alibi's** Prisma units do the inverse: they're decoys *she* deploys, designed to look
like a real intruder so a defending team reacts to something that isn't a threat. Both
operators' entire kits are "make something fake pass as authentic" — which is precisely what
forging `role: vault_manager` into a cookie does. Alibi's decoys exist to catch someone who's
lying about who they are; the irony of this mission is that Alibi's own bank never built that
detection into the one place it actually needed it — the session cookie itself.

---

## Walking through what you had to do (and what to notice)

### Step 1 — Establish a real session before you have anything to analyze

You can't reverse-engineer a token you don't have a sample of. Logging in with the provided
`j.doe` account isn't a formality — it's the "cookie collection" phase your course notes call
Step 1 of the whole methodology. Everything downstream depends on having a genuine, freshly
issued token to work from.

*What to pay attention to:* WSTG-SESS-01 testing always starts here — you need at least one
real sample before you can say anything about a token's structure, let alone its randomness.

### Step 2 — Decode before assuming anything is protected

The cookie value isn't random-looking noise — it's Base64. Decoding it (CyberChef, `base64
-d`, or just `atob()` in a browser console) immediately turns it into plain, readable text:
`j.doe:customer:<8 hex chars>`. This is your course notes' "clear-text vs. encoded vs. hashed"
distinction in miniature: Base64 is an *encoding*, not encryption — it hides nothing from
anyone who thinks to check.

*What to pay attention to:* never treat "I can't read it at a glance" as "it's protected."
Encoding, in practice, stops almost nobody — it's a speed bump for automated scanners at best.

### Step 3 — Map the structure to what you can already observe

Three colon-separated fields: a username you recognize (it matches your login and your account
page), a role (`customer` — also matches what your account page displays), and a third field
that doesn't map to anything visible in the UI at all. That third field's *shape* (short, fixed
length, hex characters) strongly suggests a hash or checksum — exactly the "does length/charset
suggest a hash" checklist item from your notes.

*What to pay attention to:* fields you can correlate against something you already know
(username, role) are the fastest way to confirm you're reading the structure correctly before
you start changing anything.

### Step 4 — Let the app tell you what it actually wants

Before tampering anything, request Vault Operations with your normal, unmodified customer
session. The response doesn't just refuse you — it names the exact role it's looking for. This
is not a lucky leak; it's a deliberately precise error message, and reading it closely is the
whole reason you don't need to guess a role name out of thin air. Real apps do this constantly
(precise 403 messages, verbose API errors) — WSTG methodology treats every error message as
evidence, not just a stop sign.

*What to pay attention to:* an access-denied response is still a response. Read it as carefully
as you'd read a 200.

### Step 5 — Tamper the field that matters, and test whether the "checksum" is real

Change `customer` to the role the app told you it wants, re-encode, replay — **without**
touching the third field at all. If the vault accepts it anyway, you've just proven that field
was decorative. This is the step your notes emphasize most directly: *"always test server-side
trust by tampering and re-sending, not just observing the structure."* Observing gets you a
hypothesis. Replaying gets you a finding.

*What to pay attention to:* the fact that you didn't need to know how the third field was
computed is itself the result. If forging privilege required also forging a valid integrity
check, that check would be doing its job. It isn't.

### Step 6 — There's a second finding sitting in plain sight

Inspect the `Set-Cookie` header from your login response (Burp, or `curl -v`) for the
attributes your course notes list explicitly: `HttpOnly`, `Secure`, `SameSite`. None of them are
present. This doesn't get you the flag on its own, but it's a real, independently reportable
finding — and it's *why* a future Masquerade operation about session hijacking or CSRF will be
able to reuse this exact same cookie as its starting point.

*What to pay attention to:* a mission's primary flag-granting bug is rarely the only finding
worth writing up. Checking the full WSTG checklist — not just the one item that gets you in —
is what separates a report from a single bullet point.

---

## The actual code behind it, in plain language

**1. The token is built from data the server already trusts, plus a field that looks checked**

```python
def masq1_make_cookie(username, role):
    checksum = hashlib.md5(f"{username}:{role}:{MASQ1_SALT}".encode()).hexdigest()[:8]
    raw = f"{username}:{role}:{checksum}"
    return base64.b64encode(raw.encode()).decode()
```

`MASQ1_SALT` is a fixed, secret-*looking* string baked into the server. The resulting hash
genuinely does depend on `username`, `role`, and the salt — so it's not fake, exactly. It's
*unused*. Nothing ever asks "does this checksum match what I'd compute for this username and
role?"

**2. The read path: parses structure, never re-verifies content**

```python
def masq1_decode_cookie(value):
    try:
        raw = base64.b64decode(value).decode()
        username, role, checksum = raw.split(":")
        return {"username": username, "role": role, "checksum": checksum}
    except Exception:
        return None
```

This function's only job is to split the string into three named pieces. It happily accepts
*any* three-field, colon-separated, Base64-wrapped string — the `checksum` variable is
extracted and then never looked at again anywhere in the app. Compare this to what a correct
version would do:

```python
# what SHOULD happen (not in this app):
expected = hashlib.md5(f"{username}:{role}:{MASQ1_SALT}".encode()).hexdigest()[:8]
if checksum != expected:
    return None   # reject -- the role has been tampered with
```

That single missing `if` is the entire vulnerability.

**3. Authorization trusts the decoded role directly**

```python
@app.route("/masquerade/op1/vault")
def masq1_vault():
    data = masq1_decode_cookie(request.cookies.get("bank_session", ""))
    ...
    if data["role"] != MASQ1_TARGET_ROLE:
        return ..., 403
    mark_masq_solved(1)
    return render_template("masq1_vault.html", granted=True, flag=MASQ1_FLAG)
```

`data["role"]` came straight from the client-supplied cookie, unverified. The comparison here
is real and correctly written — the problem happened one layer earlier, in *what* `data["role"]`
was allowed to contain.

**4. The secondary finding — issued with zero protective attributes**

```python
resp.set_cookie("bank_session", masq1_make_cookie(username, "customer"))
```

No `httponly=True`, no `secure=True`, no `samesite=`. Flask's `set_cookie()` supports all three
as keyword arguments — none are passed here.

---

## Self-check — can you explain these without looking back up?

1. Why is Base64-decoding a token the very first move, before you form any hypothesis about it?
2. The token has a field shaped like a checksum. Why doesn't its presence tell you anything about whether it's actually enforced?
3. Why was reading the *denied* Vault Operations response worth doing before ever tampering the cookie?
4. What's the one line of missing server-side logic that would have completely closed this bug, even with the exact same token format?
5. Why does the missing-cookie-flags finding matter even though it isn't what gets you the flag?

---

## Answer key (reference)

- **Test account:** `j.doe` : `Customer2024!` (given — not the point of this mission)
- **Cookie name:** `bank_session`
- **Structure:** `base64("username:role:checksum")`
- **Target role:** `vault_manager` (revealed directly by the Vault Operations denial message)
- **Flag:** `R6S{iana_forged_vault_manager_role}`
- **Automated:** `python3 masquerade/op1/solver.py http://localhost:8000`

### Manual walkthrough

```bash
# 1) log in with the given test account, capture the cookie
curl -s -c /tmp/masq1.cj -X POST http://localhost:8000/masquerade/op1/login \
  -d 'username=j.doe&password=Customer2024!' -o /dev/null
COOKIE=$(grep bank_session /tmp/masq1.cj | awk '{print $NF}')
echo "raw cookie: $COOKIE"
echo "decoded:    $(echo "$COOKIE" | base64 -d)"
# -> j.doe:customer:<8 hex chars>

# 2) confirm the vault names the exact role it wants
curl -s -b /tmp/masq1.cj http://localhost:8000/masquerade/op1/vault | grep -o 'requires the [a-z_]* role'

# 3) forge the role field, leave the checksum field untouched, re-encode
FORGED=$(echo -n "j.doe:vault_manager:$(echo "$COOKIE" | base64 -d | cut -d: -f3)" | base64)

# 4) replay it
curl -s -b "bank_session=$FORGED" http://localhost:8000/masquerade/op1/vault | grep -o 'R6S{[^}]*}'

# secondary finding: check the cookie's attributes
curl -sD - -o /dev/null -X POST http://localhost:8000/masquerade/op1/login \
  -d 'username=j.doe&password=Customer2024!' | grep -i set-cookie
# -> no HttpOnly / Secure / SameSite present
```

### Report language

- **Finding 1 (WSTG-SESS-01):** The application's session token is an unsigned,
  client-decodable structure (`base64("username:role:checksum")`) in which the authorization
  role is trusted directly from client-supplied data. Although the token includes a
  checksum-shaped field, the server never recomputes or validates it, allowing any
  authenticated user to escalate privileges by modifying the role field and replaying the
  token. *CWE-565 — Reliance on Cookies without Validation and Integrity Checking; CWE-639 —
  Authorization Bypass Through User-Controlled Key.*
- **Finding 2 (WSTG-SESS-01, secondary):** The session cookie is issued without the `HttpOnly`,
  `Secure`, or `SameSite` attributes, increasing its exposure to theft via XSS and unnecessary
  transmission over insecure channels or in cross-site contexts. *CWE-1004 — Sensitive Cookie
  Without 'HttpOnly' Flag; CWE-614 — Sensitive Cookie in HTTPS Session Without 'Secure' Flag.*
- **Impact:** Complete privilege escalation (customer → vault_manager) from a low-privilege,
  legitimately-issued session, with no need to compromise any additional credential.
- **Remediation:** Do not store authorization-relevant data (role, permissions, user ID) in a
  client-readable, client-modifiable token. Use an opaque session identifier that references
  server-side state, or — if a self-contained token is required — sign it (e.g., HMAC or JWT
  with a verified signature) and **actually verify that signature on every request** before
  trusting any field inside it. Set `HttpOnly`, `Secure`, and `SameSite` on all session cookies.

---

**Next in this campaign:** Operation 02, *Stolen Keys* — session hijacking & fixation. Locked
until this one's cleared, revealed on Command the moment it is.
