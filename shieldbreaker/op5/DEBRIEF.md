# Operation 05 — Ghost in the Panel · Blitz ⚔ Aruni · WSTG-ATHN-04

## The one-sentence lesson

**"Is this request authenticated?" and "does this request contain a cookie that looks like it
came from an authenticated session?" are two completely different questions — and a server that
only ever answers the second one has no real authentication at all.**

Operations 01–04 all made you deal with *something* — a password, a PIN, a challenge, a failure
threshold. This mission has none of that. There is no login form anywhere in it. That's not a
missing feature; it's the finding.

---

## This mission is a real, disclosed bug — not a hypothetical

This rebuilds a pattern from a real, publicly documented vulnerability in the **Online Airline
Booking System** (Exploit-DB ID 39167) — the exact lab your course notes cover. The real
application's admin panel ran this check, in PHP, verbatim:

```php
if(!isset($_COOKIE['LoggedIn'])) die("You are not logged in!");
```

That's the *entire* authorization check. Not "is this cookie's value correct." Not "does this
cookie match a session record on the server." Just: does a cookie with this *name* exist at all.
An attacker who has never sent a username or password in their life can open dev tools, add
`LoggedIn=yes`, and reload — full admin access. This app's `/op5/panel` route is a direct,
line-for-line rebuild of that exact logic, translated into Python — with the cookie renamed to
`GateOverride` to match Aruni's actual gadget (more on that below). Same bug, same shape, a name
that fits the theme instead of the real disclosure's literal `LoggedIn`.

The same real disclosure had a second bug sitting right next to it: an installer script
(`application/install.php`) that was supposed to be removed after first-time setup, wasn't, and
let anyone — no login required to reach it — create a brand-new admin account from scratch.
`/op5/install` in this mission is that bug, faithfully rebuilt.

---

## Why this bug exists (the mental model)

Somewhere in a real development process, "check if the user is logged in" got implemented as
"check if a variable that *represents* being logged in is set" — and the two got conflated
because, from inside the application's own code, they look identical. `isset($_COOKIE['LoggedIn'])`
reads exactly like "verify the user's login" if you don't stop to ask *where that cookie value
came from* and *whether anything server-side ever actually vouches for it*. A cookie is just a
string the client hands back to you on every request — the server is fully responsible for
proving that string means what it claims to mean (via a signature, a server-side session store,
anything). This code skipped that step entirely. It didn't check the cookie was *valid*; it
checked the cookie *existed*, and "existed" is something any client can manufacture for free.

The installer being left reachable is a different mechanism but the same underlying failure:
**access control that exists in the UI (no link to the page) instead of in the server.** If the
only thing stopping you from reaching a page is that nobody put a button for it, you haven't
implemented an access control — you've implemented an inconvenience. WSTG-ATHN-04's own
categories name both of these directly: "unprotected authentication endpoints... often exposed
by accident (leftover setup pages, missing route guards)" and "parameter manipulation... auth
state stored/trusted client-side."

---

## The R6 framing

**Aruni's** signature gadget is the **Surya Gate** — an electrified barrier that's either active
or it isn't. That binary, presence-based nature is exactly the bug, which is why this app's
vulnerable cookie is literally named `GateOverride` instead of the real disclosure's generic
`LoggedIn`: the panel's check isn't "who are you," it's "is the gate switch flipped" — and a
switch has no memory of who flipped it or why. **Blitz** doesn't pick locks or crack codes; his
whole kit is a shield that blinds whoever's looking and lets him walk straight through the
opening. That's this mission, mechanically: you're not defeating a check, you're walking through
a gate that was never really checking anything to begin with.

---

## Walking through what you had to do (and what to notice)

### Step 1 — Read the denial message as information, not just as a rejection

`"You are not logged in!"` is oddly specific for a generic access-denied page. It's not "403
Forbidden" or "Access restricted." It names a *state* — "logged in" — which implies the check is
looking for evidence of that state somewhere in your request, rather than doing anything more
sophisticated like validating a token's signature or looking you up in a database.

*What to pay attention to:* denial messages are rarely meaningless. Precise, unusual wording is
often a direct hint about the mechanism behind the check, not just its outcome.

### Step 2 — Ask what "logged in" would even leave behind, then supply it yourself

A real login flow's job is ultimately to hand the client *something* to prove authentication on
future requests — almost always a cookie. The critical follow-up question, and the entire
content of WSTG-ATHN-04, is: **does the server cryptographically trust that cookie, or does it
just check that the cookie exists?** The only way to find out is to try supplying one yourself —
and the exact name isn't something you're meant to guess blind. It's discoverable two
independent ways: a leftover developer comment sitting in the denial page's raw HTML source
(view-source it, don't just read what's rendered), or the `Set-Cookie` response header handed
back by the leftover installer endpoint (Step 3). Once you have the name, there's no cleverness
to the value — `GateOverride=granted`, `GateOverride=1`, `GateOverride=banana` — all of them
pass, because the check never looks at the *value* at all.

*What to pay attention to:* any time authentication state lives in something the client
possesses (a cookie, a hidden form field, a query parameter) rather than something the server
looks up, that state is a hypothesis to test, not a fact to trust.

### Step 3 — Go looking for what isn't linked

The second finding can't be stumbled into by clicking around the UI — nothing points at
`/op5/install`. This is the first mission in the campaign where **forced browsing** (trying
paths that aren't advertised anywhere, using a wordlist of common names) is the only way to find
part of the attack surface. This matters because a real application's *linked* pages are not its
*entire* attack surface — old setup tools, debug endpoints, and admin bootstrapping scripts
routinely outlive their intended lifespan without ever being referenced by a single link or
button.

*What to pay attention to:* "I can't find a way to it in the app" is not the same claim as "it
doesn't exist." Directory/endpoint enumeration is how you close that gap.

### Step 4 — Confirm you have two separate findings, not one

Both paths land you on the same panel with the same flag, which could make it tempting to report
this as a single bug. It isn't. Fixing the cookie check (making `/op5/panel` validate a real
signed session) would do *nothing* to close `/op5/install` — that endpoint hands out valid
sessions to anyone regardless of how the panel itself is protected afterward. Independently,
fixing the installer without fixing the cookie check leaves the forgeable-cookie bypass fully
intact. Each is exploitable completely on its own.

*What to pay attention to:* two bugs that produce the same *outcome* are not necessarily the same
*bug*. Test each bypass in isolation before concluding they're duplicates — a fix for one
frequently leaves the other completely untouched.

---

## The actual code behind it, in plain language

**1. The entire access check — presence, not proof**

```python
@app.route("/op5/panel")
def op5_panel():
    if not request.cookies.get("GateOverride"):   # VULN: presence-only check, client-controlled
        return render_template("op5_panel.html", granted=False), 403
    mark_solved(5)
    return render_template("op5_panel.html", granted=True, flag=OP5_FLAG)
```

`request.cookies.get("GateOverride")` reads whatever the client sent, with whatever value the
client chose, completely unsigned and unverified. There's no comparison against a stored
session, no signature check, nothing server-side backing this decision at all. This is the
Python translation of `isset($_COOKIE['LoggedIn'])` from the real disclosure — same bug, same
shape, renamed to match Aruni's Surya Gate instead of the original's generic name.

(Worth noting separately: the campaign's *own* progress-tracking cookie — Flask's `session`,
used by `mark_solved()` — is properly signed with a secret key and cannot be forged this way.
The vulnerability is specific to the app-under-test's home-rolled `GateOverride` cookie, not to
cookies in general. Don't walk away thinking "cookies are insecure" — the lesson is "an
*unverified* cookie is insecure.")

**2. The leftover endpoint — zero auth required to reach it, and it mints the trusted cookie**

```python
@app.route("/op5/install", methods=["GET", "POST"])
def op5_install():
    if request.method == "GET":
        return render_template("op5_install.html")
    callsign = (request.form.get("callsign") or "backdoor.op").strip() or "backdoor.op"
    resp = make_response(render_template("op5_install.html", done=True, callsign=callsign))
    resp.set_cookie("GateOverride", "granted")
    return resp
```

No decorator, no check, no gate of any kind guards this route — it's a plain Flask endpoint like
any other, distinguished only by not being linked from `hub.html` or any other template. Anyone
who finds the path can POST to it and walk away with exactly the cookie `/op5/panel` trusts.

**3. How you were meant to find the name — a leftover comment, not a guess**

```html
<!-- TODO(dev): Surya Gate integration is still using the legacy check (raw
     GateOverride cookie presence) instead of a real signed session. ... -->
```

This sits in `op5_panel.html`'s denied-state markup — never rendered on screen (HTML comments
are invisible to the browser's rendered output), but sitting in plain text in the raw response
body. `curl`, "View Source," or Burp's response viewer all show it immediately. This is the same
principle as Operation 02's exact policy regex sitting in client-side JS: the ground truth is
*discoverable by inspection*, never something you're supposed to brute-force blind.

---

## Self-check — can you explain these without looking back up?

1. What's the actual difference between "a cookie exists" and "a cookie is valid," and why does only one of those provide real security?
2. Why was the denial message ("You are not logged in!") worth reading closely instead of just noting that access was denied?
3. Why does fixing `/op5/panel`'s cookie check do nothing to close `/op5/install`, and vice versa?
4. Why can't the second finding be discovered by browsing the app's UI, and what technique closes that gap?
5. The campaign's own session cookie (used to track your progress at Command) is not vulnerable to this attack. What's structurally different about it compared to `GateOverride`?
6. Name the two independent, non-guessing ways to discover the exact cookie name this mission relies on.

---

## Answer key (reference)

- **Target:** `/op5/panel` — no credentials exist to find; the check is bypassable entirely.
- **Flag:** `R6S{blitz_ghosted_arunis_gate_GateOverride=granted}`
- **Path A (forge the cookie):** discover the name via the leftover HTML comment on the denial
  page, then set `Cookie: GateOverride=granted` (any value works) and request the panel
  directly. No other endpoint needed at all.
- **Path B (leftover installer):** `POST` to `/op5/install` with any `callsign` value — no auth
  required to reach it — which hands back a working `GateOverride` cookie via `Set-Cookie`.
- **Automated:** `python3 shieldbreaker/op5/solver.py http://localhost:8000` — demonstrates both paths
  independently (each discovering the cookie name its own way), confirming each works standalone.

### Manual walkthrough

```bash
# confirm the denial, its exact wording, AND view-source the leftover comment
curl -s http://localhost:8000/op5/panel | grep -o 'You are not logged in!'
curl -s http://localhost:8000/op5/panel | grep -o 'raw[^)]*cookie presence'

# Path A -- forge the discovered cookie directly, zero other requests
curl -s -b 'GateOverride=granted' http://localhost:8000/op5/panel | grep -o 'R6S{[^}]*}'

# Path B -- the leftover, unlinked installer (found via forced browsing / dirb)
curl -s -c /tmp/op5.cj -X POST http://localhost:8000/op5/install -d 'callsign=backdoor.op' \
  | grep -o 'Provisioning complete'
curl -s -b /tmp/op5.cj http://localhost:8000/op5/panel | grep -o 'R6S{[^}]*}'
```

A real forced-browsing pass would look like:
```bash
dirb http://localhost:8000/op5/ /usr/share/dirb/wordlists/common.txt
```

### Report language

- **Finding 1 (WSTG-ATHN-04):** The Operator Command Panel's authorization check verifies only
  the *presence* of a client-supplied `GateOverride` cookie, not its integrity or origin. Any
  client can set this cookie to an arbitrary value and gain full access with no valid
  credentials. *CWE-287 — Improper Authentication; CWE-565 — Reliance on Cookies without
  Validation.*
- **Finding 2 (WSTG-ATHN-04):** An unauthenticated, unlinked deployment/provisioning endpoint
  (`/op5/install`) remains reachable in production and issues a valid `GateOverride` cookie to
  any anonymous request, independently bypassing all access control. *CWE-284 — Improper Access
  Control; CWE-1188 — Insecure Default Initialization of Resource.*
- **Impact:** Full administrative panel access with zero legitimate credentials, via either of
  two independent paths.
- **Remediation:** Replace the cookie-presence check with a server-side session store (or a
  signed/encrypted session token the server can cryptographically verify); remove or disable all
  installation/setup endpoints immediately after deployment, or gate them behind a
  one-time-use, expiring installation token; audit the full route table for endpoints reachable
  without authentication, not just the ones linked from the UI.

---
