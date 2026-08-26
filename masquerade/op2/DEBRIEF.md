# 🔓 Masquerade Operation 02 — Stolen Keys · Zero ⚔ Vigil · WSTG-SESS-03

**Spoilers below.** If you haven't played yet, use [`CHALLENGER.md`](CHALLENGER.md) first.

## The one-sentence lesson

**A session identifier that survives the moment of authentication unchanged was never actually
issued by login at all — it was just adopted, which means anyone who can hand a target an
identifier *before* they log in can walk in on it *after* they do.**

Operation 01 asked whether the server verifies what's *inside* a token. This operation asks a
narrower, sneakier question: does the server even control *which* token gets trusted in the
first place — or does it just keep using whatever identifier happened to already be sitting on
the request?

---

## Why this bug exists (the mental model)

Session fixation is not about stealing a session — that's hijacking, a different bug with a
different fix. Fixation is about **planting** one. The distinction matters because the fix for
each is different, and mixing them up leads to reports that recommend the wrong remediation.

| | Hijacking | Fixation |
|---|---|---|
| When | *After* a victim is already logged in | *Before* the victim logs in |
| How | Steal an existing, already-authenticated identifier (sniffing, XSS, log leakage) | Hand the victim an identifier of your choosing, then wait for them to authenticate on it |
| Root cause | Weak transport/storage of a valid session | Server never issues a *new* identifier at the moment privilege changes |

The mental model for fixation specifically: think of the session identifier as a **hotel key
card**. A secure hotel cuts you a brand-new card the moment you check in — the front desk would
never hand you a card that was just sitting in the lobby rack, unassigned, and let it become
*your* card the instant you show ID. A vulnerable hotel does exactly that: the card in the rack
becomes valid the moment anyone checks in while holding it — it never gets recut. If an
attacker can slip a guest a specific card number *before* they check in (a link with the ID
embedded, a cookie planted via a subdomain, a QR code at the counter), that attacker already
knows the number of the card that will become active the second the guest hands over their ID.

The server-side root cause is always the same missing step, no matter how the identifier
arrives: **authentication changed the user's privilege level, but nothing rotated the
identifier that privilege is attached to.**

---

## The R6 framing

**Zero's** entire kit is built around *taking over something that already exists* rather than
deploying something new: his Argus cameras let him silently hack into an enemy's *own* Bulletproof
Cameras, Nest launchers, and Evil Eyes — turning the defenders' existing infrastructure against
them without ever needing to plant new hardware of his own inside their perimeter. That's
precisely what session fixation is: Zero doesn't need to forge a session from nothing (that's a
different mission) — he just needs the resort to keep using an identifier that was already
sitting there, one he quietly nominated in advance.

**Vigil** is a detection specialist — his entire kit exists to keep him invisible to enemy
drones and camera feeds the instant he's spotted, evading the very systems built to flag
intruders. The irony of this mission mirrors Operation 01's: Vigil's whole purpose is *evading
detection*, but the resort's own session-management logic doesn't even attempt detection in the
first place. There's no distinction on the server between "an identifier I minted for this
visitor" and "an identifier this visitor showed up already holding." Zero's planted key card
isn't evading a check — it's walking through a door that was never checking at all.

---

## Walking through what you had to do (and what to notice)

### Step 1 — Observe the identifier *before* authentication exists

Visiting the guest portal pre-login already gets you a `resort_sid` cookie. This by itself
isn't the bug — plenty of correctly-built apps assign a pre-auth session for things like CSRF
tokens or cart state. The bug is only provable by what happens *next*.

*What to pay attention to:* WSTG-SESS-03 testing always starts by establishing a baseline
identifier pre-auth — you can't detect "did this change on login" without first recording what
it was before login.

### Step 2 — Log in while continuing to present that same identifier

Submit valid credentials without ever clearing or replacing the cookie you already had. Check
it again afterward.

*What to pay attention to:* the identifier is byte-for-byte the same value before and after.
That's the entire test. No decoding, no tampering with fields — just checking whether a value
survived a privilege boundary it should never have survived.

### Step 3 — Turn "it didn't change" into "I get to choose it"

If the server accepts whatever identifier was already present and simply upgrades its trust
level on login, the identifier never had to be server-issued at all. Manually set `resort_sid`
to a value of your own choosing *before* visiting the login page, then authenticate while still
presenting it.

*What to pay attention to:* this is the pivot from an observation to an exploit. "The server
doesn't rotate the identifier" is a finding. "I can pre-select the identifier that will become
authenticated" is the *impact* of that finding — the part that makes it worth reporting instead
of just noting.

### Step 4 — Confirm the app can tell the difference, and that you crossed it

Reaching the reservations page fails outright pre-auth, and succeeds — but *without* proof of
anything — if you're authenticated on an identifier the server minted itself. It only confirms
the actual vulnerability when the identifier that ends up authenticated is one that
demonstrably originated on your side of the connection, before login ever happened.

*What to pay attention to:* this app is deliberately built so that "I'm logged in" alone proves
nothing about fixation — plenty of totally secure apps let you log in fine. The finding is
specifically about *which* identifier ends up trusted, not whether login works.

### Step 5 — The second, smaller finding: it's not even cookie-only

Your notes' root-causes checklist lists session identifiers accepted via URL query parameters
as its own separate, testable item — and for good reason: a URL is far easier to hand a victim
than a raw cookie write (a shared link, a bookmark, a QR code, a referer header leak). Try
`?resort_sid=<value>` on the portal URL instead of setting a cookie.

*What to pay attention to:* this succeeds through the exact same underlying flaw — the server
never distinguishes "an identifier I chose" from "an identifier that showed up in the request,"
regardless of which channel it arrived through.

---

## The actual code behind it, in plain language

**1. The session lookup adopts whatever identifier already arrived — cookie or URL**

```python
def masq2_get_session():
    incoming = request.cookies.get("resort_sid") or request.args.get("resort_sid")
    if incoming:
        if incoming not in MASQ2_SESSIONS:
            MASQ2_SESSIONS[incoming] = {"authenticated": False, "origin": "client"}
        return incoming, MASQ2_SESSIONS[incoming]
    sid = secrets.token_hex(8)
    MASQ2_SESSIONS[sid] = {"authenticated": False, "origin": "server"}
    return sid, MASQ2_SESSIONS[sid]
```

Any identifier the client presents — whether it was ever issued by this server or not — is
accepted and tracked. A brand-new, server-random identifier is only minted as a last resort,
when the request carries *nothing* at all.

**2. Login flips a flag on whatever identifier was already in play — it never mints a new one**

```python
@app.route("/masquerade/op2/login", methods=["POST"])
def masq2_login():
    sid, sess = masq2_get_session()          # whatever sid is already attached -- untouched
    ...
    sess["authenticated"] = True             # VULN: flips the flag on the SAME sid -- no rotation
    resp = make_response(redirect(url_for("masq2_reservations")))
    resp.set_cookie("resort_sid", sid)
    return resp
```

This is the exact missing step. A correct version would discard `sid` entirely at this point
and mint a fresh one:

```python
# what SHOULD happen (not in this app):
sess["authenticated"] = True
new_sid = secrets.token_hex(16)
MASQ2_SESSIONS[new_sid] = MASQ2_SESSIONS.pop(sid)   # migrate state to a FRESH identifier
resp.set_cookie("resort_sid", new_sid)               # old sid is now dead, unusable by anyone
```

That regeneration — issuing a brand-new identifier and invalidating the old one at the exact
moment privilege changes — is the entire fix, and it's the one-line (well, few-line) intervention
your course notes call out directly.

**3. The flag only fires when the authenticated identifier can be proven to have originated
client-side**

```python
@app.route("/masquerade/op2/reservations")
def masq2_reservations():
    sid, sess = masq2_get_session()
    if not sess["authenticated"]:
        ...                                            # 401 -- not checked in
    elif sess["origin"] != "client":
        ...                                            # authed, but proves nothing
    else:
        mark_masq_solved(2)                             # reaching this with a client-planted sid clears Op02
        ...
```

`origin` is bookkeeping that exists purely to make this challenge gradeable — it records
whether *this* identifier was first proposed by the client or minted by the server. It's not
something a real attacker gets to see; it's the app's own ground truth for "was this a fixation
exploit, or just an ordinary login," used only to decide when to award the flag.

---

## Self-check — can you explain these without looking back up?

1. In one sentence, what's the difference between session hijacking and session fixation — and
   why does mixing them up in a report lead to recommending the wrong fix?
2. Why does merely observing "the identifier didn't change across login" not, by itself, prove
   the vulnerability — what's the extra step that turns it into a confirmed finding?
3. What's the single missing server-side action that would close this bug completely, even with
   every other line of the app unchanged?
4. Why is the URL-parameter acceptance path worth reporting separately from the cookie-based
   fixation, even though both stem from the same root cause?
5. Why does this challenge track whether a session identifier's `origin` was `"server"` or
   `"client"` — what real-world signal is that standing in for?

---

## Answer key (reference)

- **Test account:** `guest.stay` : `Coastline2024!` (given — not the point of this mission)
- **Cookie name:** `resort_sid`
- **Root cause:** the server never regenerates the session identifier at the moment
  authentication succeeds; it also accepts that identifier from a `?resort_sid=` URL parameter,
  not just a cookie
- **Flag:** `R6S{zero_planted_the_key_card_before_checkin}`
- **Automated:** `python3 masquerade/op2/solver.py http://localhost:8000`

### Manual walkthrough

```bash
# 1) plant our own session id BEFORE ever logging in
SID="PWNED-BY-ZERO-4471"
curl -s -o /dev/null -b "resort_sid=$SID" http://localhost:8000/masquerade/op2/

# 2) log in, presenting the SAME planted id -- never accept a server-issued one
curl -s -o /dev/null -b "resort_sid=$SID" -X POST http://localhost:8000/masquerade/op2/login \
  -d 'username=guest.stay&password=Coastline2024!'

# 3) replay the planted id -- it's now authenticated
curl -s -b "resort_sid=$SID" http://localhost:8000/masquerade/op2/reservations | grep -o 'R6S{[^}]*}'

# secondary finding: same trick, via URL parameter instead of a cookie at all
curl -s -c /tmp/masq2.cj -o /dev/null "http://localhost:8000/masquerade/op2/?resort_sid=URL-PLANTED-9999"
curl -s -b /tmp/masq2.cj -c /tmp/masq2.cj -o /dev/null -X POST http://localhost:8000/masquerade/op2/login \
  -d 'username=guest.stay&password=Coastline2024!'
curl -s -b /tmp/masq2.cj http://localhost:8000/masquerade/op2/reservations | grep -o 'R6S{[^}]*}'
```

### Report language

- **Finding 1 (WSTG-SESS-03):** The application does not regenerate the session identifier
  upon successful authentication. An identifier presented by the client prior to login remains
  valid and becomes authenticated after login, allowing an attacker to fixate a victim's
  session by supplying them a pre-chosen identifier in advance (e.g., via a crafted link) and
  later replaying that same identifier as an authenticated session once the victim logs in.
  *CWE-384 — Session Fixation.*
- **Finding 2 (WSTG-SESS-03, secondary):** The session identifier is additionally accepted via
  a `resort_sid` URL query parameter, not just the `resort_sid` cookie, making fixation
  significantly easier to deliver (a plain link is sufficient — no cookie-setting mechanism is
  required) and increasing the identifier's exposure through browser history, referer headers,
  and server access logs. *CWE-598 — Use of GET Request Method With Sensitive Query Strings.*
- **Impact:** An attacker who can get a target to visit a crafted URL or load a planted cookie
  before that target logs in can subsequently access the target's authenticated session,
  without ever needing to observe, guess, or steal the target's actual credentials.
- **Remediation:** Regenerate the session identifier immediately upon any change in privilege
  level — most importantly, upon successful login — and invalidate the prior identifier
  entirely. Never accept a session identifier from a URL parameter; sessions should travel
  exclusively via a cookie flagged `HttpOnly`, `Secure`, and `SameSite`.

---

**Next in this campaign:** Operation 03, *One Click* — CSRF. Locked until this one's cleared,
revealed on Command the moment it is.
