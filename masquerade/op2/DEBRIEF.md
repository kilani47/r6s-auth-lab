# 🔓 Masquerade Operation 02 — Stolen Keys · Zero ⚔ Vigil · WSTG-SESS-03

**Spoilers below.** If you haven't played yet, use [`CHALLENGER.md`](CHALLENGER.md) first.

## The one-sentence lesson

**A session identifier that survives the moment of authentication unchanged was never actually
issued by login at all — it was just adopted, which means anyone who can hand a target an
identifier *before* they log in can walk in on their account *after* they do, without ever
knowing, guessing, or needing the target's password.**

This mission has a real second party built in — R. Voss, Meridian's regional director, whose
check-in you route yourself but whose password you're never given and never need. That's not a
narrative flourish; it's the whole point made unambiguous. You supply Voss's login exactly once
(Step 2), by routing a card number to the front desk — never a credential. Every credential Voss
ever uses belongs to the app's own NPC logic, never to you.

Operation 01 asked whether the server verifies what's *inside* a token. This operation asks a
narrower, sneakier question: does the server even control *which* token gets trusted in the
first place — or does it just keep using whatever identifier happened to already be sitting on
the request, no matter who put it there?

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
becomes valid the moment anyone checks in while holding it — it never gets recut. If an attacker
can slip a guest a specific card number *before* they check in (a link with the ID embedded, a
cookie planted via a subdomain, a QR code at the counter), that attacker already knows the
number of the card that will become active the second the guest hands over their ID — and this
mission's front desk plays that guest's part for real, with its own separate account, so there's
no ambiguity about whose login actually happened.

The server-side root cause is always the same missing step, no matter how the identifier
arrives, and no matter who checks in on it: **authentication changed the user's privilege level,
but nothing rotated the identifier that privilege is attached to.**

---

## The R6 framing

**Zero's** entire kit is built around *taking over something that already exists* rather than
deploying something new: his Argus cameras let him silently hack into an enemy's *own*
Bulletproof Cameras, Nest launchers, and Evil Eyes — turning the defenders' existing
infrastructure against them without ever needing to plant new hardware of his own inside their
perimeter. That's precisely what session fixation is: Zero doesn't need to forge a session from
nothing (that's a different mission) — he just needs the hotel to keep using an identifier that
was already sitting there, one he quietly nominated in advance, then let R. Voss's own
legitimate check-in do the rest.

**Vigil** is a detection specialist — his entire kit exists to keep him invisible to enemy
drones and camera feeds the instant he's spotted, evading the very systems built to flag
intruders. The irony of this mission mirrors Operation 01's: Vigil's whole purpose is *evading
detection*, but the hotel's own session-management logic doesn't even attempt detection in the
first place. There's no distinction on the server between "an identifier I minted for this
visitor" and "an identifier this visitor showed up already holding." Zero's planted key card
isn't evading a check — it's walking through a door that was never checking at all.

---

## Walking through what you had to do (and what to notice)

### Step 1 — Establish the baseline with your own, honest login

Log into your own account (`guest.stay` / `Meridian2024!`) normally and look at what the
reservations page shows. Nothing about this step is broken — that's the point of doing it first.
A vulnerability report is stronger when it can show what *correct* behavior looks like right
next to what's wrong.

*What to pay attention to:* WSTG-SESS-03 testing always starts by establishing a baseline before
looking for the deviation. "I'm logged in and it works" is not, by itself, evidence of anything.

### Step 2 — Route a card you invented to a guest you don't control

The front-desk panel isn't flavor text. Type a card number of your own choosing and submit it.
The app's response tells you plainly what just happened: R. Voss, a real account with a real
password you are never shown, has checked in using exactly the card you typed.

*What to pay attention to:* this is the step that makes the whole mission unambiguous. You did
not log in as Voss. You could not have — you don't have Voss's password, and the form never asks
for one. All you controlled was which card number Voss's (simulated) legitimate check-in would
land on.

### Step 3 — Reuse that same card yourself

Set your own cookie (or URL parameter) to the exact card number you routed in Step 2, and visit
the guest portal again.

*What to pay attention to:* nothing you do in this step involves a password either. You're
simply presenting a value.

### Step 4 — Reach the reservation with *zero* credentials

Open a request that has never logged in anywhere — a private/incognito tab, a fresh `curl`, a
brand-new `requests.Session()` — and go straight to `/reservations` carrying only the card
number. No login form touched in this request at all.

*What to pay attention to:* this is the step that actually proves the vulnerability, and it's
easy to blur into Step 3 by accident. Reaching the reservations page from the *same* session you
just used to send the check-in link proves nothing — of course a session stays whatever it was
doing. What proves the vulnerability is that a request carrying **zero credentials of any kind**
still reaches an authenticated account belonging to *someone else*, purely because it happened
to present a card that a real login elsewhere had already validated. Check whose name is on the
reservation — it should be Voss's, not yours.

*What to notice about the app's own responses:* reaching the reservations page fails outright
with no card at all, and succeeds — but *without* proof of anything — if you're authenticated on
your own, ordinary login. It only confirms the vulnerability when the account reached belongs to
someone whose credentials you never submitted in this process. "I'm logged in" alone proves
nothing about fixation — plenty of totally secure apps let you log in fine. The finding is about
*whose* trust you're standing on, and whether reaching it required a credential at all.

### Step 5 — The second, smaller finding: it's not even cookie-only

Your notes' root-causes checklist lists session identifiers accepted via URL query parameters as
its own separate, testable item — and for good reason: a URL is far easier to hand a victim than
a raw cookie write (a shared link, a bookmark, a QR code, a referer header leak). Try
`?guest_sid=<value>` both when visiting the portal *and* when routing a card to the front desk,
instead of setting a cookie at all.

*What to pay attention to:* this succeeds through the exact same underlying flaw — the server
never distinguishes "an identifier I minted" from "an identifier that showed up in the request,"
regardless of which channel it arrived through, and regardless of who authenticated it.

---

## The actual code behind it, in plain language

**1. The session lookup adopts whatever identifier already arrived — cookie or URL**

```python
def masq2_get_session():
    incoming = request.cookies.get("guest_sid") or request.args.get("guest_sid")
    if incoming:
        if incoming not in MASQ2_SESSIONS:
            MASQ2_SESSIONS[incoming] = {"authenticated": False, "authenticated_as": None}
        return incoming, MASQ2_SESSIONS[incoming]
    sid = masq2_make_sid()
    MASQ2_SESSIONS[sid] = {"authenticated": False, "authenticated_as": None}
    return sid, MASQ2_SESSIONS[sid]
```

Any identifier the client presents — whether it was ever issued by this server or not — is
accepted and tracked. A brand-new, server-issued identifier is only minted as a last resort,
when the request carries *nothing* at all.

**2. Both real logins funnel through the exact same authentication step**

```python
def masq2_authenticate(sess, who):
    sess["authenticated"] = True
    sess["authenticated_as"] = who         # "guest" (you) or "npc" (R. Voss)
```

`masq2_login` (your own login) and `masq2_send_link` (the front desk routing a card to Voss)
both end by calling this on whatever `sid` was already attached to that request. Neither one
mints a replacement. That's the entire vulnerability, in one function: authentication changes
what a session is trusted to do, but never changes *which* session that trust attaches to —
regardless of whether it's you or Voss doing the authenticating.

```python
@app.route("/masquerade/op2/send-link", methods=["POST"])
def masq2_send_link():
    raw = (request.form.get("sid") or "").strip()
    ...
    if raw not in MASQ2_SESSIONS:
        MASQ2_SESSIONS[raw] = {"authenticated": False, "authenticated_as": None}
    masq2_authenticate(MASQ2_SESSIONS[raw], "npc")     # Voss checks in on YOUR chosen card
    ...
```

A correct version would discard the card number entirely at authentication time and mint a
fresh one instead:

```python
# what SHOULD happen (not in this app):
masq2_authenticate(sess, who)
new_sid = secrets.token_hex(16)
MASQ2_SESSIONS[new_sid] = MASQ2_SESSIONS.pop(sid)   # migrate state to a FRESH identifier
resp.set_cookie("guest_sid", new_sid)                # old sid is now dead, unusable by anyone
```

That regeneration — issuing a brand-new identifier and invalidating the old one at the exact
moment privilege changes, no matter who is authenticating — is the entire fix, and it's the
one-line (well, few-line) intervention your course notes call out directly.

**3. The flag only fires when the authenticated identifier belongs to someone else's login**

```python
@app.route("/masquerade/op2/reservations")
def masq2_reservations():
    sid, sess = masq2_get_session()
    if not sess["authenticated"]:
        ...                                            # 401 -- not checked in
    elif sess["authenticated_as"] != "npc":
        ...                                             # you, on your own account -- proves nothing
    else:
        mark_masq_solved(2)                             # reaching this on Voss's card clears Op02
        ...
```

`authenticated_as` is bookkeeping that exists purely to make this challenge gradeable — it
records *who* actually performed the login that authenticated this particular card: you
(`"guest"`) or the front desk's simulated victim (`"npc"`). It's not something a real attacker
gets to see; it's the app's own ground truth for "did this card end up trusted because someone
*else's* real credentials were used on it," which is exactly the capability a real fixation
attack grants.

This app also keeps `masq2_sign()` / `masq2_is_server_issued()` around (further up in `app.py`)
— a fixed-key signature that tells you whether a given card was ever minted by the server at
all, and does so *statelessly*, so it stays correct even across a process restart (Docker's
`restart: unless-stopped` will restart this app on any crash, wiping `MASQ2_SESSIONS` — a plain
"have I seen this card before" dict would otherwise forget a genuinely server-issued card and
misclassify it after every restart). It's no longer what decides the flag — `authenticated_as`
is a more direct signal now that there's a real second party to attribute a login to — but it's
worth reading, because "make a stateful check restart-proof by signing instead of remembering"
is a generally useful pattern well beyond this one mission.

---

## Self-check — can you explain these without looking back up?

1. In one sentence, what's the difference between session hijacking and session fixation — and
   why does mixing them up in a report lead to recommending the wrong fix?
2. Why does establishing your own normal login first strengthen a fixation report, rather than
   just being a warm-up step?
3. What's the single missing server-side action that would close this bug completely, even with
   every other line of the app unchanged?
4. This mission gives you a real second account (R. Voss) whose password you're never shown. Why
   does that matter more than it might first seem — what would be weaker about a version of this
   mission where you played both the attacker and the victim yourself, on one account?
5. Why is the URL-parameter acceptance path worth reporting separately from the cookie-based
   fixation, even though both stem from the same root cause?
6. What does `authenticated_as` track that a plain "is this card authenticated: yes/no" flag
   couldn't have told you? And separately — what does `masq2_is_server_issued()` protect against
   that `authenticated_as` alone does not?

---

## Answer key (reference)

- **Your test account:** `guest.stay` : `Meridian2024!` (baseline only — not the exploit)
- **NPC victim:** R. Voss, Regional Director — real account, password never shown to the player
- **Cookie name:** `guest_sid`
- **Root cause:** the server never regenerates the session identifier at the moment
  authentication succeeds, for either account; it also accepts that identifier from a
  `?guest_sid=` URL parameter, not just a cookie
- **Flag:** `R6S{zero_planted_the_key_card_before_checkin}`
- **Automated:** `python3 masquerade/op2/solver.py http://localhost:8000`

### Manual walkthrough

```bash
# 1) choose a card number yourself
SID="PWNED-BY-ZERO-4471"

# 2) route it to the front desk -- R. Voss checks in on this card with Voss's OWN password,
#    which this command never supplies, because it doesn't have it
curl -s -o /dev/null -X POST http://localhost:8000/masquerade/op2/send-link \
  -d "sid=$SID"

# 3) THE PROOF: a brand-new curl invocation, no cookie jar, no prior requests, no -d at all --
#    just the card number. This is the whole attack: an authenticated account (Voss's, not
#    ours) reached with zero credentials submitted, in this process.
curl -s -b "guest_sid=$SID" http://localhost:8000/masquerade/op2/reservations | grep -o 'R6S{[^}]*}'

# secondary finding: same trick, via URL parameter instead of a cookie at all
curl -s -o /dev/null -X POST "http://localhost:8000/masquerade/op2/send-link" -d "sid=URL-PLANTED-9999"
curl -s "http://localhost:8000/masquerade/op2/reservations?guest_sid=URL-PLANTED-9999" | grep -o 'R6S{[^}]*}'
```

### Report language

- **Finding 1 (WSTG-SESS-03):** The application does not regenerate the session identifier upon
  successful authentication, for any account. An identifier presented by the client prior to
  login remains valid and becomes authenticated after login, allowing an attacker to fixate a
  victim's session by supplying them a pre-chosen identifier in advance (e.g., via a crafted
  link) and later replaying that same identifier as an authenticated session once the victim
  logs in — without the attacker ever needing to know, guess, or intercept the victim's
  credentials. *CWE-384 — Session Fixation.*
- **Finding 2 (WSTG-SESS-03, secondary):** The session identifier is additionally accepted via a
  `guest_sid` URL query parameter, not just the `guest_sid` cookie, making fixation significantly
  easier to deliver (a plain link is sufficient — no cookie-setting mechanism is required) and
  increasing the identifier's exposure through browser history, referer headers, and server
  access logs. *CWE-598 — Use of GET Request Method With Sensitive Query Strings.*
- **Impact:** An attacker who can get a target to authenticate (by any means — a phished link, a
  planted cookie) on an attacker-chosen identifier can subsequently access that target's
  authenticated session, without ever needing to observe, guess, or steal the target's actual
  credentials.
- **Remediation:** Regenerate the session identifier immediately upon any change in privilege
  level — most importantly, upon successful login, for every account without exception — and
  invalidate the prior identifier entirely. Never accept a session identifier from a URL
  parameter; sessions should travel exclusively via a cookie flagged `HttpOnly`, `Secure`, and
  `SameSite`.

---

**Next in this campaign:** Operation 03, *One Click* — CSRF. Locked until this one's cleared,
revealed on Command the moment it is.
