# 🔓 Masquerade Operation 06 — Delegated Trust · Hibana ⚔ Bandit

**Spoilers below.** If you haven't played yet, use [`CHALLENGER.md`](CHALLENGER.md) first.

## The one-sentence lesson

**OAuth answers "can this app act on my behalf," not "who is this" — and every place that
question gets answered (a redirect address, a client's own credentials, a token's own shape)
is a separate thing that can be gotten wrong, independently, even in an app that gets the
other two exactly right.**

This mission has three stages on purpose. Not because one bug needed three steps to exploit —
because OAuth implementations fail in three genuinely unrelated ways, and a real assessment
report lists them as three findings, with three different fixes, even when (like here) they
all happen to live in the same small app.

---

## First, the five roles and four flows — worth being precise about

Before the bugs, the vocabulary, because it's very easy to blur these together under pressure
and it matters for how you write a finding up:

| Role | Who it is in this mission |
|---|---|
| **Resource Owner** | The club member — the person whose photos these are |
| **Client** | Print Kiosk — the app that wants access, but never gets the password |
| **Resource Server** | The Clubhouse's `/photos/me` endpoint — hosts the actual data |
| **Authorization Server** | The Clubhouse's `/oauth/authorize` and `/oauth/token` endpoints |
| **User Agent** | Whatever browser or HTTP client is carrying the requests |

This app implements the **Authorization Code Grant** — the standard, most secure flow for a
web app: approve once, get a short-lived code, exchange that code (server-to-server, with the
client's own secret) for a token. Compare that to the other three grant types from your notes:
**Implicit** skips the code and hands back a token directly (legacy, discouraged, because the
token ends up sitting in a URL fragment); **Resource Owner Password Credentials** has the
client collect the actual password (only ever appropriate for a fully first-party app);
**Client Credentials** has no user in the picture at all (machine-to-machine). None of those
are what's running here, and knowing why the Authorization Code Grant is the "safe" one is
exactly what makes it interesting that this implementation still finds three ways to break it.

---

## The R6 framing

**Hibana's** X-KAIRO pellets don't force one big opening — they burn through reinforced
material at multiple points, methodically, each breach independent of the others. That's this
entire mission's structure: three separate weak points in the same wall, none of them needing
the others to work.

**Bandit's** Shock Wire exists to make reinforced walls *actively* resist tampering — a real,
proactive defense. The irony carries through the whole campaign: Bandit's kit is about
punishing exactly the kind of methodical, repeated probing this mission requires (multiple
lure attempts, hundreds of secret guesses, thousands of token guesses) — and nothing in The
Clubhouse's OAuth implementation does anything like that. No rate limiting anywhere in this
entire flow. Every stage's brute-force step succeeds specifically because nothing was watching
for it.

---

## Stage 1 — Unvalidated `redirect_uri`

### Why this is the most important finding in the whole mission

The authorization code is the single most sensitive thing this flow ever produces before a
token exists — whoever holds it can become the client, at least for one exchange. The
`redirect_uri` parameter is *where that code gets mailed*. If the authorization server doesn't
verify that address belongs to the client actually being authorized, then approving access
doesn't send the code to Print Kiosk at all — it sends the code wherever the request
*claimed* Print Kiosk's callback was. The consent screen looks completely normal either way,
because from N. Kruger's point of view, nothing about approving "Print Kiosk wants:
view_gallery" looks any different whether the code is about to go somewhere legitimate or
not.

### Walking through it

1. The honest flow's authorize URL has five parameters: `response_type=code`,
   `client_id=print_kiosk`, `redirect_uri=/masquerade/op6/callback`, `scope=view_gallery`. The
   consent screen renders using every one of them, including echoing `redirect_uri` back —
   which is itself a hint: if the server didn't need to remember and validate that value, it
   wouldn't need to carry it through the request at all.
2. The lure endpoint models exactly what changing one parameter and getting someone else to
   click the resulting link would do in the real world: N. Kruger visits an authorize URL with
   *your* redirect_uri, approves (because nothing on the consent screen looked wrong), and the
   code goes where you pointed it.
3. Checking `/attacker-catch` and finding a real code there is the proof — not "I understand
   this could work," but an actual authorization code, issued by the real server, sitting
   somewhere it was never supposed to end up.

*What to notice about the fix's shape:* the correct behavior isn't "encrypt the redirect_uri"
or "make it harder to guess" — it's "check it against a value registered for this client
ahead of time, and reject anything else outright." An exact allow-list match. Not a prefix
match, not a substring match — both of those are exactly what the open-redirect bypass tricks
in your notes (`%2f%2f`, `%5c%5c`, `@` tricks, and friends) are built to slip past. This app
does the simplest possible wrong thing — no check at all — but the fix is the same either way:
compare the whole string, exactly, against a pre-registered value.

---

## Stage 2 — Weak client_secret

### Why a stolen code alone isn't enough, and why that almost doesn't matter here

In a correctly-run flow, Stage 1 alone wouldn't be catastrophic — the code still needs to be
exchanged, and that exchange requires Print Kiosk's own `client_secret`, something an attacker
stealing a *user's* authorization flow was never given. This is real defense in depth: even a
fully stolen code should be inert without a second, separately-held secret.

It only works as defense in depth if that secret is actually hard to obtain. This one isn't.

### Walking through it

4. The token endpoint's shape comes straight from OAuth's own spec: `grant_type`, `code`,
   `redirect_uri`, `client_id`, `client_secret`, all as form fields on a POST. None of that is
   secret information by itself — it's the exact shape any client legitimately uses.
5. What makes `client_secret` guessable here isn't a flaw in *how* it's checked — the
   comparison itself is a normal, correct equality check. It's that the value being compared
   against is short and dictionary-adjacent, and nothing rate-limits how many times you're
   allowed to be wrong.
6. A real brute-force here means exactly what it means anywhere else: a loop, one HTTP request
   per candidate, checking which response actually contains an `access_token` instead of an
   `invalid_client` error.

*What to notice:* this is functionally identical to Operation 05's weak-HMAC-secret finding —
same root cause (a short, guessable value protecting something important), completely
different location (an OAuth client credential instead of a JWT signing key). Recognizing the
same underlying weakness class showing up in different parts of an app is exactly the kind of
pattern a real assessment is looking for.

---

## Stage 3 — Weak, brute-forceable access tokens

### Why this finding stands completely on its own

This is the stage most players expect to be "the payoff" of Stages 1 and 2 — use the token you
just earned, done. It's actually the opposite lesson: this token's weakness has *nothing to do
with* how it was issued. A 4-digit numeric access token is guessable by anyone, with zero
knowledge of the redirect_uri bug, zero knowledge of the client secret, zero interaction with
the authorization flow at all.

### Walking through it

7. Look at any access token you've been issued (from Stage 2, or from the honest flow). It's a
   short decimal number — a space of roughly 9,000 possibilities.
8. That's a small enough space to brute-force directly against `/masquerade/op6/photos/me`,
   which — like the token endpoint — has no rate limit on failed attempts either.
9. Reaching the flag this way, with a token you found by guessing rather than one you actually
   earned through Stages 1–2, is the proof that this is a genuinely separate door, not a
   continuation of the first two.

*What to notice:* your notes' checklist for this exact bug class explicitly mentions testing
the resource server directly, "especially if the client secret is compromised/not required" —
this app goes one step further and doesn't even need that. A resource server that trusts any
syntactically valid-looking token, at any volume, is vulnerable regardless of how well-guarded
the rest of the flow is.

---

## Beyond the three stages — the rest of your notes' checklist, applied to this app

You don't need a fourth exploit to understand these — recognizing them from what you can
already observe is the actual skill.

- **Everlasting codes and tokens:** nothing in this app ever expires a code or a token. Come
  back to a captured code or a cracked token an hour later and it still works. In a real
  assessment, this widens every other finding's attack window indefinitely — report it
  alongside Stage 1–3, not as a replacement for any of them.
- **Codes not bound to the requesting client:** this app only ever registers one client
  (`print_kiosk`), so there's no second, malicious client to swap a stolen code onto here —
  but the underlying question ("does the server verify the code is being redeemed by the same
  client it was issued to?") is worth asking on any real target with more than one registered
  client. This app *does* correctly check that the `redirect_uri` at exchange time matches the
  one used at authorize time — that's a real, working control, and noticing which checks exist
  and which don't is exactly the granularity a report needs.
- **`state` parameter / CSRF on the OAuth flow itself:** absent here, and worth flagging on any
  real target — an attacker who can make a victim's browser complete an authorization flow
  *for the attacker's own account* (rather than stealing the victim's) can trick a victim into
  unknowingly using attacker-controlled data. If that sounds familiar, it should: it's the same
  underlying mechanic as Operation 02's session fixation, applied to the OAuth handshake
  instead of a login form.
- **Insecure token storage:** whether tokens sit hashed or plaintext in a database isn't
  something a black-box test can observe directly — it's a code-review finding, or something a
  SQL/NoSQL injection elsewhere in the app would incidentally confirm. Worth asking about even
  when you can't test it yourself.

### A real-world case study worth knowing: chaining medium bugs into a critical one

A public disclosure against Open Bank Project's OAuth implementation is worth understanding in
full, because it's a genuinely instructive example of a pattern that shows up constantly in
real assessments: no single bug was catastrophic, but three ordinary-looking weaknesses,
chained, added up to full account takeover.

It started with a **reflected XSS** in a parameter on the OAuth flow's own "thanks" page — the
kind of parameter (`redirectUrl`) that often gets less scrutiny than the rest of an app's
inputs, precisely because it "belongs" to the OAuth implementation rather than the main
application. That XSS let an attacker run arbitrary JavaScript in the context of the real,
trusted site.

From there, the attacker's script created a hidden `<iframe>` pointing at the *same* site's own
login page. Framing a page from a different origin is normally blocked — but this page was
framing *itself*, and the site's `X-Frame-Options` header was set to `SAMEORIGIN` rather than
`DENY`. `SAMEORIGIN` exists specifically to allow a site to frame its own pages; it says
nothing about whether code already running on that origin (via the XSS) should be trusted to
do it. The header did exactly what it was configured to do — the configuration was just
answering the wrong question.

With the real login form now framed invisibly on the page, injected JavaScript walked every
form on the page (including inside the iframe) looking for a password field, and because
autocomplete had never been disabled on that field, a value could be present in the DOM for
the script to read the moment a browser had one cached — no keystroke logging required. The
harvested value was exfiltrated with a plain `GET` request to an attacker-controlled domain,
in a query string, in cleartext.

The lesson your notes draw from this is worth keeping word for word: *the rest of the
application sanitized input extremely well — the OAuth implementation was the only weak spot.*
OAuth flows carry extra parameters (`redirectUrl`, `redirect_uri`, `state`, `scope`) that don't
always get the same input-validation review as the rest of an app's forms, precisely because
they read as "OAuth plumbing" rather than user-facing input. They're still user-facing input.
Test them like it.

---

## Self-check — can you explain these without looking back up?

1. Why does an authorization code's *destination* matter as much as its *value* — what does an
   unvalidated `redirect_uri` actually hand an attacker?
2. Why is "the client_secret check is implemented correctly" not the same statement as "the
   client_secret is protected"?
3. Why does Stage 3 count as an independent finding rather than a continuation of Stages 1–2 —
   what's the one sentence that proves it?
4. In the Open Bank Project case study, `X-Frame-Options: SAMEORIGIN` wasn't misconfigured in
   the traditional sense — it did exactly what that header is supposed to do. So what was
   actually the mistake?
5. Why do OAuth-specific parameters (`redirect_uri`, `state`, `scope`) deserve the exact same
   input-validation scrutiny as any other form field, even though they "belong" to the
   authentication plumbing rather than the application's own features?

---

## Answer key (reference)

- **Your test account:** `club.member` : `Clubhouse2024!` (baseline only — not any of the three exploits)
- **Client:** `print_kiosk`, real registered callback `/masquerade/op6/callback`
- **Weak client_secret:** `kiosk41` (in `wordlists/op6_client_secrets.txt`)
- **Access token shape:** 4-digit decimal, ~9,000 possible values
- **Flag:** `R6S{hibana_burned_through_every_layer_of_delegated_trust}`
- **Automated:** `python3 masquerade/op6/solver.py http://localhost:8000`

### Manual walkthrough

```bash
# Stage 1 -- lure N. Kruger with a redirect_uri we control
curl -s -X POST http://localhost:8000/masquerade/op6/lure-member \
  --data-urlencode "redirect_uri=/masquerade/op6/attacker-catch"

CODE=$(curl -s http://localhost:8000/masquerade/op6/attacker-catch \
  | grep -oP '(?<=font-mono text-atk mt-1 break-all">)[^<]+' | head -1)
echo "stolen code: $CODE"

# Stage 2 -- brute-force client_secret against the real token endpoint
for SECRET in $(cat wordlists/op6_client_secrets.txt); do
  RESP=$(curl -s -X POST http://localhost:8000/masquerade/op6/oauth/token \
    --data-urlencode "grant_type=authorization_code" \
    --data-urlencode "code=$CODE" \
    --data-urlencode "redirect_uri=/masquerade/op6/attacker-catch" \
    --data-urlencode "client_id=print_kiosk" \
    --data-urlencode "client_secret=$SECRET")
  if echo "$RESP" | grep -q access_token; then
    echo "cracked secret: $SECRET -> $RESP"
    TOKEN=$(echo "$RESP" | grep -oP '(?<="access_token":")[0-9]+')
    break
  fi
done

# Stage 3 -- use the token (or brute-force a fresh one directly, see solver.py)
curl -s "http://localhost:8000/masquerade/op6/photos/me?access_token=$TOKEN"
```

### Report language

- **Finding 1 — Unvalidated redirect_uri (OAuth open redirect / authorization code theft):**
  The `/oauth/authorize` endpoint issues an authorization code to any `redirect_uri` supplied
  in the request, without validating it against a value registered for the requesting client.
  An attacker can craft an authorization link with an attacker-controlled `redirect_uri` and
  deliver it to a victim; upon approval, the resulting authorization code is sent directly to
  the attacker. *CWE-601 — URL Redirection to Untrusted Site.*
- **Finding 2 — Weak, brute-forceable client_secret:** The `/oauth/token` endpoint accepts a
  `client_secret` from a small, dictionary-guessable value space, with no rate limiting or
  lockout on failed attempts, allowing an attacker holding a stolen authorization code (e.g.,
  from Finding 1) to recover the client's secret via online brute-force and complete the token
  exchange. *CWE-521 — Weak Password Requirements / CWE-307 — Improper Restriction of
  Excessive Authentication Attempts.*
- **Finding 3 — Weak, brute-forceable access tokens:** Access tokens issued by
  `/oauth/token` are 4-digit decimal numbers (~9,000 possible values), and the resource
  endpoint `/photos/me` enforces no rate limiting on invalid tokens, allowing an attacker to
  obtain a valid access token via direct brute-force against the resource server, independent
  of Findings 1 and 2. *CWE-330 — Use of Insufficiently Random Values.*
- **Impact:** Chained, Findings 1 and 2 allow full compromise of any member's delegated
  access without their knowledge or consent, requiring only that they open a link. Finding 3
  independently allows the same level of access to any attacker, without needing a victim at
  all, purely from the resource server being reachable.
- **Remediation:** (1) Validate `redirect_uri` against an exact, pre-registered allow-list per
  client — reject any request whose value doesn't match exactly. (2) Generate `client_secret`
  values with a cryptographically secure random generator at sufficient length, and apply rate
  limiting/lockout to the token endpoint. (3) Generate access tokens with a CSPRNG at
  sufficient length (128 bits or more), and apply the same rate limiting to the resource
  endpoint. Across all three: expire codes and tokens, and bind codes to the client that
  requested them.

---

**Next in this campaign:** Operation 07, *Unlimited Attempts* — bypassing 2FA. Locked until
this one's cleared, revealed on Command the moment it is.
