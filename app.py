#!/usr/bin/env python3
"""
OPERATION SHIELDBREAKER — a single-site, layered authentication CTF.
One website. Missions unlock one at a time: clear an operation to reveal the next.

Rosters are faction-accurate to Rainbow Six Siege:
  ATTACKERS (you play): IQ, Sledge, Dokkaebi, Thermite, Blitz, Nomad
  DEFENDERS (controls) : Mute, Castle, Clash, Oryx, Aruni, Kaid

DELIBERATELY VULNERABLE per-mission. Local educational lab only.
"""
import time
import random
import re
import json
import base64
import hashlib
import hmac
import secrets
from html.parser import HTMLParser
from flask import Flask, request, render_template, session, redirect, url_for, make_response, jsonify

app = Flask(__name__)
app.secret_key = "shieldbreaker-lab-dev-key"  # lab only; session tracks progress

# ---------------------------------------------------------------- campaign map
# built=False missions are revealed on clear but their challenge ships later.
MISSIONS = [
    {"id": 1, "code": "01", "name": "Callsign Recon",
     "wstg": "WSTG-IDNT-04", "topic": "Username Enumeration",
     "attacker": {"slug": "iq", "name": "IQ"},
     "defender": {"slug": "mute", "name": "Mute"},
     "blurb": "Mute jams your recon and the directory stays dark. Read the portal's "
              "tells — error text, timing, the recovery flow — to enumerate the roster "
              "and recover the admin's token.",
     "built": True, "path": "/op1/"},
    {"id": 2, "code": "02", "name": "Breach & Clear",
     "wstg": "WSTG-ATHN-07", "topic": "Dictionary Attack",
     "attacker": {"slug": "sledge", "name": "Sledge"},
     "defender": {"slug": "castle", "name": "Castle"},
     "blurb": "Castle's barricade follows a rigid company password format — and a rigid "
              "format is a blueprint. Read the exact rule, enumerate every password it "
              "allows, and hammer into the Operator Console. No lockout to stop you.",
     "built": True, "path": "/op2/"},
    {"id": 3, "code": "03", "name": "Hard Breach",
     "wstg": "WSTG-ATHN-03", "topic": "CAPTCHA Bypass",
     "attacker": {"slug": "dokkaebi", "name": "Dokkaebi"},
     "defender": {"slug": "clash", "name": "Clash"},
     "blurb": "Clash's perimeter terminal poses a fresh math challenge on every attempt — "
              "and nothing else stands in your way. Automate past it, then brute-force "
              "the access code Logic-Bomb style.",
     "built": True, "path": "/op3/"},
    {"id": 4, "code": "04", "name": "Lockdown Failure",
     "wstg": "WSTG-ATHN-03", "topic": "Lockout Bypass",
     "attacker": {"slug": "thermite", "name": "Thermite"},
     "defender": {"slug": "oryx", "name": "Oryx"},
     "blurb": "The lockdown is supposed to stop repeated failures cold. Cross the threshold "
              "on purpose and find out what it actually does instead of locking the account.",
     "built": True, "path": "/op4/"},
    {"id": 5, "code": "05", "name": "Ghost in the Panel",
     "wstg": "WSTG-ATHN-04", "topic": "Auth Schema Bypass",
     "attacker": {"slug": "blitz", "name": "Blitz"},
     "defender": {"slug": "aruni", "name": "Aruni"},
     "blurb": "Aruni's gate only checks that a signal exists, not what it means. Forge it, "
              "or find the leftover door nobody remembered to lock, and walk straight in "
              "with zero credentials.",
     "built": True, "path": "/op5/panel"},
    {"id": 6, "code": "06", "name": "Back Door",
     "wstg": "WSTG-ATHN-08", "topic": "Alternative Channels",
     "attacker": {"slug": "nomad", "name": "Nomad"},
     "defender": {"slug": "kaid", "name": "Kaid"},
     "blurb": "The web console is finally hardened — real lockout, generic errors, all of it. "
              "Every lesson from Operations 01-05 was fixed here. Find the channel where none "
              "of it was, and finish the job.",
     "built": True, "path": "/op6/"},
]

ATTACKERS = [m["attacker"] for m in MISSIONS]
DEFENDERS = [m["defender"] for m in MISSIONS]


def solved_set():
    return set(session.get("solved", []))


def mark_solved(mid):
    s = solved_set()
    s.add(mid)
    session["solved"] = sorted(s)
    session.modified = True


def next_unsolved():
    s = solved_set()
    for m in MISSIONS:
        if m["id"] not in s:
            return m["id"]
    return None  # campaign complete


# ============================================================ OPERATION MASQUERADE
# A second, INDEPENDENT campaign -- does not require clearing SHIELDBREAKER, and its
# own progress is tracked separately (session["masq_solved"], not "solved"). Covers
# the post-authentication topics: session management, tokens/JWT, OAuth, 2FA.
MASQUERADE_MISSIONS = [
    {"id": 1, "code": "01", "name": "The Teller's Trust",
     "wstg": "WSTG-SESS-01", "topic": "Cookie Tampering",
     "attacker": {"slug": "iana", "name": "Iana"},
     "defender": {"slug": "alibi", "name": "Alibi"},
     "blurb": "The bank issues a session cookie and trusts whatever it says. Decode it, "
              "learn its shape, and forge a new identity the vault has to believe.",
     "built": True, "path": "/masquerade/op1/"},
    {"id": 2, "code": "02", "name": "Stolen Keys",
     "wstg": "WSTG-SESS-03", "topic": "Session Fixation",
     "attacker": {"slug": "zero", "name": "Zero"},
     "defender": {"slug": "vigil", "name": "Vigil"},
     "blurb": "The hotel hands out a key card before you've even checked in — and never "
              "recuts it at the front desk. Plant your own card number, check in, and the "
              "card you planted is the one that ends up authenticated.",
     "built": True, "path": "/masquerade/op2/"},
    {"id": 3, "code": "03", "name": "One Click",
     "wstg": "WSTG-SESS-05", "topic": "CSRF",
     "attacker": {"slug": "ying", "name": "Ying"},
     "defender": {"slug": "melusi", "name": "Melusi"},
     "blurb": "The browser sends the cookie automatically, no questions asked. Build a page "
              "that fires itself the instant it loads, hand it to the admin, and their own "
              "browser resets their password for you.",
     "built": True, "path": "/masquerade/op3/"},
    {"id": 4, "code": "04", "name": "Signed, Not Sealed",
     "wstg": "WSTG-SESS-10", "topic": "JWT Authentication",
     "attacker": {"slug": "kali", "name": "Kali"},
     "defender": {"slug": "echo", "name": "Echo"},
     "blurb": "A token's signature only matters if something actually checks it. Tell the "
              "verifier there's nothing to check, and it believes you — no key, no victim, "
              "no password required.",
     "built": True, "path": "/masquerade/op4/"},
    {"id": 5, "code": "05", "name": "Exposed Claim",
     "wstg": "WSTG-SESS-10", "topic": "JWT Claims",
     "attacker": {"slug": "jackal", "name": "Jackal"},
     "defender": {"slug": "pulse", "name": "Pulse"},
     "blurb": "This one's signature checks out honestly, every time. The key it's checked "
              "against doesn't — crack it offline and you can sign anything you want.",
     "built": True, "path": "/masquerade/op5/"},
    {"id": 6, "code": "06", "name": "Delegated Trust",
     "wstg": "OAuth 2.0", "topic": "Attacking OAuth",
     "attacker": {"slug": "hibana", "name": "Hibana"},
     "defender": {"slug": "bandit", "name": "Bandit"},
     "blurb": "Three independent doors into one delegated-access flow: an unchecked "
              "redirect, a guessable client secret, and a token space small enough "
              "to brute-force outright.",
     "built": True, "path": "/masquerade/op6/"},
    {"id": 7, "code": "07", "name": "Unlimited Attempts",
     "wstg": "2FA", "topic": "Bypassing 2FA",
     "attacker": {"slug": "ash", "name": "Ash"},
     "defender": {"slug": "warden", "name": "Warden"},
     "blurb": "A second factor only helps if it has the same protections as the first.",
     "built": False, "path": "#"},
]

MASQ_ATTACKERS = [m["attacker"] for m in MASQUERADE_MISSIONS]
MASQ_DEFENDERS = [m["defender"] for m in MASQUERADE_MISSIONS]


def masq_solved_set():
    return set(session.get("masq_solved", []))


def mark_masq_solved(mid):
    s = masq_solved_set()
    s.add(mid)
    session["masq_solved"] = sorted(s)
    session.modified = True


def masq_next_unsolved():
    s = masq_solved_set()
    for m in MASQUERADE_MISSIONS:
        if m["id"] not in s:
            return m["id"]
    return None  # campaign complete


# ================================================================ HUB / COMMAND
@app.route("/")
def hub():
    s = solved_set()
    nxt = next_unsolved()
    # reveal cleared missions + the single next one; hide everything beyond.
    visible = [m for m in MISSIONS if m["id"] in s or m["id"] == nxt]
    more = any(m["id"] not in s and m["id"] != nxt for m in MISSIONS)

    # Masquerade campaign -- fully independent of Shieldbreaker's progress above.
    ms = masq_solved_set()
    mnxt = masq_next_unsolved()
    masq_visible = [m for m in MASQUERADE_MISSIONS if m["id"] in ms or m["id"] == mnxt]
    masq_more = any(m["id"] not in ms and m["id"] != mnxt for m in MASQUERADE_MISSIONS)

    return render_template("hub.html", attackers=ATTACKERS, defenders=DEFENDERS,
                           visible=visible, solved=s, nxt=nxt, more=more,
                           total_cleared=len(s),
                           masq_attackers=MASQ_ATTACKERS, masq_defenders=MASQ_DEFENDERS,
                           masq_visible=masq_visible, masq_solved=ms, masq_nxt=mnxt,
                           masq_more=masq_more, masq_total_cleared=len(ms))


@app.route("/reset-progress")
def reset_progress():
    session.pop("solved", None)
    return redirect(url_for("hub"))


@app.route("/masq-reset-progress")
def masq_reset_progress():
    session.pop("masq_solved", None)
    return redirect(url_for("hub"))


# Per-operation reset: clears just ONE mission's "cleared" badge and its own
# session-tracked state (login, stage progress), without touching any other
# mission's progress or the campaign-wide reset above. Custom, non-Flask-session
# cookies each op issues (bank_session, guest_sid) aren't swept by the generic
# session-key wipe below, so they're listed explicitly here.
MASQ_RESET_COOKIES = {1: ["bank_session"], 2: ["guest_sid"]}


@app.route("/masquerade/reset-op/<int:mid>")
def masq_reset_one(mid):
    s = masq_solved_set()
    s.discard(mid)
    session["masq_solved"] = sorted(s)
    prefix = f"masq{mid}_"
    for key in list(session.keys()):
        if key.startswith(prefix):
            session.pop(key, None)
    resp = make_response(redirect(request.referrer or url_for("hub")))
    for cookie_name in MASQ_RESET_COOKIES.get(mid, []):
        resp.delete_cookie(cookie_name)
    return resp


# ================================================ OPERATION 01 — vulnerable app
ROSTER = {
    "g.mendel":  {"display": "Gilles Mendel  [Montagne]", "target": True},
    "e.pichon":  {"display": "Emmanuelle Pichon  [Twitch]", "target": False},
    "r.tanaka":  {"display": "Rei Tanaka  [Hibana]", "target": False},
    "m.branca":  {"display": "Maria Branca  [Caveira]", "target": False},
}
LEVEL1_FLAG = "R6S{iq_scanned_past_mute_blackout_g.mendel}"


def fake_verify(password: str) -> None:
    # timing oracle: only valid users pay the hashing cost.
    for _ in range(120000):
        password = hashlib.sha256(password.encode()).hexdigest()


@app.route("/op1/")
def op1_index():
    return render_template("op1_login.html")


@app.route("/op1/login", methods=["POST"])
def op1_login():
    username = (request.form.get("username") or "").strip().lower()
    password = request.form.get("password") or ""
    if username in ROSTER:
        fake_verify(password)  # VULN: timing side-channel
        return render_template("op1_login.html",  # VULN: distinct message
            error=f"Incorrect password for operator {ROSTER[username]['display']}."), 401
    return render_template("op1_login.html",
        error="Callsign not found in the operator directory."), 401


@app.route("/op1/reset", methods=["GET", "POST"])
def op1_reset():
    if request.method == "GET":
        return render_template("op1_reset.html")
    username = (request.form.get("username") or "").strip().lower()
    if username in ROSTER:
        if ROSTER[username]["target"]:
            mark_solved(1)  # capturing the admin token clears Operation 01
            msg = ("Recovery packet dispatched to the registered address of "
                   f"{ROSTER[username]['display']}.\n\n"
                   f"[SIMULATED EMAIL BODY] Your recovery token: {LEVEL1_FLAG}")
            return render_template("op1_reset.html", ok=True, message=msg,
                                   flag=LEVEL1_FLAG)
        msg = ("Recovery packet dispatched to the registered address of "
               f"{ROSTER[username]['display']}.")
        return render_template("op1_reset.html", ok=True, message=msg)
    return render_template("op1_reset.html", ok=False,
        message="No operator is registered under that callsign.")


# ============================================ OPERATION 02 — weak password policy
# WSTG-ATHN-07. Target user (from Op1 recon) is the admin, g.mendel. The console
# login has NO lockout and NO CAPTCHA (that's the point of ATHN-07).
# The difficulty is the mechanics, not luck:
#   1. Generic failures + success only via a 302 redirect (no body keyword to grep),
#      so you must calibrate success by diffing against a known-failure baseline.
#   2. A per-session CSRF token the login POST requires (naive tools send none).
#   3. A candidate space large enough it must be scripted, with no lockout to slow you.
# The password policy is a RIGID FORMULA, not a vague composition rule — and that is
# itself the vulnerability: "Capitalized word + exactly 2 digits + exactly 1 symbol
# from {!,@,#,$}" fully determines the shape. Read the rule (the register page's JS
# states it exactly), take a small profiled base-word list, and enumerate the FULL
# cross-product (words x 100 x 4) — every candidate the policy allows. The real
# password is guaranteed to be in that set, so this is complete enumeration, not
# guessing. A rigid, formulaic policy narrows the search space instead of widening it.
OP2_USER = "g.mendel"
OP2_PASSWORD = "Barricade88$"   # follows the policy exactly: Word + 2 digits + 1 symbol
OP2_FLAG = "R6S{sledge_hammered_castle_Barricade88$}"
OP2_POLICY = {
    "min_len": 8,
    "digit_count": 2,                  # exactly two digits, not "at least one"
    "symbols": "!@#$",                 # exactly one, from this closed set — nothing else
    "structure": "Capitalized word + exactly 2 digits + exactly 1 symbol from ! @ # $",
}


def op2_new_csrf():
    tok = secrets.token_hex(8)
    session["op2_csrf"] = tok
    return tok


@app.route("/op2/")
def op2_index():
    return render_template("op2_login.html", csrf=op2_new_csrf())


@app.route("/op2/login", methods=["POST"])
def op2_login():
    token = request.form.get("csrf_token") or ""
    # VULN-adjacent realism: the token is required, but there is no rate limit, so an
    # attacker who establishes a session and reuses the token can guess forever.
    if not token or token != session.get("op2_csrf"):
        return render_template("op2_login.html", csrf=op2_new_csrf(),
                               error="Session expired — reload and try again."), 400
    username = (request.form.get("username") or "").strip().lower()
    password = request.form.get("password") or ""
    if username == OP2_USER and password == OP2_PASSWORD:
        session["op2_authed"] = True
        return redirect(url_for("op2_console"))        # success = 302, tiny body
    # generic failure (no username enumeration here — that was Op1's lesson).
    # Token is NOT rotated on failure: per-session-stable, so an attacker who grabs it
    # once can reuse it for the whole (unthrottled) run — that's the ATHN-07 weakness.
    return render_template("op2_login.html", csrf=session.get("op2_csrf"),
                           error="Invalid username or password."), 200


@app.route("/op2/console")
def op2_console():
    if not session.get("op2_authed"):
        return redirect(url_for("op2_index"))
    mark_solved(2)                                      # reaching the console clears Op02
    return render_template("op2_console.html", flag=OP2_FLAG, user=OP2_USER)


@app.route("/op2/register", methods=["GET", "POST"])
def op2_register():
    # ATHN-07 policy testing: the JS on this page enforces the EXACT structural rule
    # from OP2_POLICY, but the SERVER enforces nothing — a request sent past the
    # browser accepts any password (a finding on its own, CWE-602). Reading that JS
    # (or viewing the checklist below) is how you learn the real password's shape.
    if request.method == "GET":
        return render_template("op2_register.html", policy=OP2_POLICY)
    username = (request.form.get("username") or "").strip() or "test.op"
    password = request.form.get("password") or ""
    return render_template("op2_register.html", policy=OP2_POLICY, done=True,
                           created_user=username, pw_len=len(password))


# ================================================ OPERATION 03 — arithmetic CAPTCHA
# WSTG-ATHN-03. Target (confirmed via Op01 recon) is still g.mendel. This terminal has
# NO lockout and NO rate limit at all (that control is Op04's dedicated lesson) — the
# ONLY thing guarding the access code is a math challenge that regenerates on every
# request, using a randomly chosen operator (+ - *) each time -- a script can't assume
# addition, it has to actually parse which operator is shown. ("/" is deliberately left
# out: exact-integer division needs the challenge built backwards from the answer, and
# that extra machinery isn't worth it for what it teaches here.) The operands are
# 4-digit numbers (1000-9999), not single digits -- this makes the challenge LOOK more
# imposing on the page without adding any real difficulty for a script (eval() finds
# "4821+3912" exactly as trivial as "4+3"; only a human reading it by eye would notice
# a difference). Two independent findings live here:
#   1. The challenge is arithmetic and shown in plaintext -> trivially solved by a
#      script (eval()-the-string-you-just-scraped, straight out of the WSTG playbook)
#      regardless of which of the three operators comes up.
#   2. A classic guard-clause bug: `if captcha_raw:` treats a MISSING/EMPTY captcha
#      field as "nothing to check" instead of "invalid" -> omit the field entirely and
#      the check never runs at all, regardless of value (CWE-20).
# The access code itself is a plain 4-digit PIN (0000-9999) -> a small, fully bounded,
# completely enumerable space -- deterministic brute force, not a guessing game.
OP3_TARGET_DISPLAY = "Gilles Mendel  [Montagne]"
OP3_PIN = "4187"
OP3_FLAG = "R6S{dokkaebi_cracked_clash_perimeter_4187}"


def op3_new_challenge():
    op = random.choice(["+", "-", "*"])
    a, b = random.randint(1000, 9999), random.randint(1000, 9999)
    if op == "-" and b > a:
        a, b = b, a                      # keep the result non-negative
    answer = {"+": a + b, "-": a - b, "*": a * b}[op]
    session["op3_captcha"] = answer
    return a, op, b


@app.route("/op3/")
def op3_index():
    a, op, b = op3_new_challenge()
    return render_template("op3_login.html", a=a, op=op, b=b)


@app.route("/op3/login", methods=["POST"])
def op3_login():
    expected = session.get("op3_captcha")
    captcha_raw = request.form.get("captcha")
    pin = request.form.get("pin") or ""

    captcha_ok = True
    if captcha_raw:   # VULN: falsy check -- a missing/empty field skips validation entirely
        try:
            captcha_ok = int(captcha_raw) == expected
        except ValueError:
            captcha_ok = False

    a, op, b = op3_new_challenge()   # single-use: rotates whether this attempt passed or failed

    if captcha_ok and pin == OP3_PIN:
        session["op3_authed"] = True
        return redirect(url_for("op3_console"))     # success = 302, tiny body
    # generic failure -- doesn't reveal whether the PIN or the captcha was the problem
    return render_template("op3_login.html", a=a, op=op, b=b,
        error="Access code or challenge response incorrect."), 401


@app.route("/op3/console")
def op3_console():
    if not session.get("op3_authed"):
        return redirect(url_for("op3_index"))
    mark_solved(3)                                   # reaching the console clears Op03
    return render_template("op3_console.html", flag=OP3_FLAG, user=OP3_TARGET_DISPLAY)


# ============================================== OPERATION 04 — broken lockout mechanism
# WSTG-ATHN-03. Same confirmed admin, g.mendel. This is modeled directly on a real,
# publicly disclosed bug class (Tiki Wiki CMS, CWE-307): a lockout mechanism that is
# SUPPOSED to stop repeated failed logins instead responds to crossing its own threshold
# by silently blanking the stored password to an empty string. The "security control"
# firing is itself the vulnerability -- crossing the threshold makes the account MORE
# reachable, not less. There is no password to crack here; OP4_REAL_PASSWORD is random
# and never disclosed, on purpose, so there's nothing to waste time guessing.
#
# Failed-attempt count is tracked server-side, per ACCOUNT (not per session/cookie) --
# exactly how a real lockout should be scoped -- via a plain in-memory dict. That's the
# correct part of the design; the bug is entirely in what happens AT the threshold.
#
# Three response states as the count climbs (mirrors the real disclosed attack flow:
# generic failures, then a message shift partway in as a side-effect, then a second
# shift right at the threshold where the credential actually gets wiped):
OP4_TARGET_DISPLAY = "Gilles Mendel  [Montagne]"
OP4_USER = "g.mendel"
OP4_REAL_PASSWORD = secrets.token_hex(16)     # unknowable on purpose -- not the point of this op
OP4_MIDPOINT = 15                              # decoy message shift (no vuln yet, just a signal)
OP4_THRESHOLD = 50                             # credential gets blanked here
OP4_FLAG = "R6S{thermite_breached_oryx_broken_lockdown}"

OP4_ATTEMPT_COUNTS = {}    # username -> failed-attempt count, in-memory (resets on app restart)
OP4_BLANKED = set()        # usernames whose stored credential has been wiped to ""


@app.route("/op4/")
def op4_index():
    return render_template("op4_login.html")


@app.route("/op4/login", methods=["POST"])
def op4_login():
    username = (request.form.get("username") or "").strip().lower()
    password = request.form.get("password") or ""

    if username == OP4_USER and username in OP4_BLANKED:
        if password == "":                     # VULN: the wiped credential is an empty string
            session["op4_authed"] = True
            return redirect(url_for("op4_console"))
        return render_template("op4_login.html",
            error="Account requires administrator re-authentication."), 401

    if username == OP4_USER and password == OP4_REAL_PASSWORD:
        session["op4_authed"] = True
        return redirect(url_for("op4_console"))

    if username == OP4_USER:
        OP4_ATTEMPT_COUNTS[username] = OP4_ATTEMPT_COUNTS.get(username, 0) + 1
        count = OP4_ATTEMPT_COUNTS[username]
        if count >= OP4_THRESHOLD:
            OP4_BLANKED.add(username)           # "lockout" fires -> wipes the credential instead
            return render_template("op4_login.html",
                error="Account requires administrator re-authentication."), 401
        if count >= OP4_MIDPOINT:
            return render_template("op4_login.html",
                error="A security notification has been dispatched regarding this account."), 401

    return render_template("op4_login.html", error="Invalid username or password."), 401


@app.route("/op4/console")
def op4_console():
    if not session.get("op4_authed"):
        return redirect(url_for("op4_index"))
    mark_solved(4)                                   # reaching the console clears Op04
    return render_template("op4_console.html", flag=OP4_FLAG, user=OP4_TARGET_DISPLAY)


# ================================================ OPERATION 05 — broken auth schema
# WSTG-ATHN-04. Modeled directly on a real, publicly disclosed pattern (Online Airline
# Booking System, EDB-ID 39167): the real bug's check was "does a cookie named LoggedIn
# exist" -- not a signed session, not a server-side lookup, just presence. This app
# renames that same cookie to fit Aruni's actual gadget, the Surya Gate (an electrified
# barrier that's simply active or not) -- the vulnerability class is identical, only the
# cookie's name changed. Any value works. There is no login form on this mission at all
# -- the whole point is that one was never needed.
#
# Two independent findings, mirroring the source material's exact two vulnerabilities:
#   1. /op5/panel trusts request.cookies.get("GateOverride") for authorization outright.
#      Forge the cookie by hand (curl/Burp) and the check passes for anyone.
#   2. /op5/install is a leftover, undocumented provisioning endpoint (never linked from
#      anywhere in the UI -- only forced browsing finds it) that hands out a fresh
#      GateOverride cookie to any anonymous POST, no auth required to reach it at all.
# Note this app's OWN session cookie (Flask's signed session, used for mark_solved/
# campaign progress) is a completely separate, legitimately-secured cookie -- the
# vulnerability is specific to the app-under-test's home-rolled "GateOverride" cookie.
OP5_FLAG = "R6S{blitz_ghosted_arunis_gate_GateOverride=granted}"


@app.route("/op5/panel")
def op5_panel():
    if not request.cookies.get("GateOverride"):   # VULN: presence-only check, client-controlled
        return render_template("op5_panel.html", granted=False), 403
    mark_solved(5)                             # reaching the panel clears Op05
    return render_template("op5_panel.html", granted=True, flag=OP5_FLAG)


@app.route("/op5/install", methods=["GET", "POST"])
def op5_install():
    # VULN: leftover deployment/provisioning endpoint, reachable with ZERO authentication
    # of any kind, that mints the very cookie /op5/panel trusts.
    if request.method == "GET":
        return render_template("op5_install.html")
    callsign = (request.form.get("callsign") or "backdoor.op").strip() or "backdoor.op"
    resp = make_response(render_template("op5_install.html", done=True, callsign=callsign))
    resp.set_cookie("GateOverride", "granted")
    return resp


# ================================================== OPERATION 06 — alternative channel
# WSTG-ATHN-08, the finale. Same confirmed admin, g.mendel. THE WEB CONSOLE HERE IS
# GENUINELY HARDENED -- every lesson from Ops 01-05 was actually fixed: generic error
# messages (Op01), no crackable formula (Op02), a real CAPTCHA is implied by the copy,
# and a real, working, unbypassable lockout (Op04, done correctly this time -- crossing
# the threshold LOCKS the account, full stop, no credential blanking, no bypass). Attack
# this with wordlists/op6_passwords.txt and you WILL get locked out at attempt 5, long
# before reaching the real password at line 22. That failure is the point: it proves the
# web hardening works.
#
# But Rainbow-Corp also still runs a legacy REST API (/api/v1/login) for an old mobile
# client, sharing the exact same account -- and NONE of the hardening carried over to it.
# No lockout, no rate limit, and it even re-introduces Op01's username-enumeration bug
# via verbose JSON error codes. The SAME wordlist that gets you locked out in five tries
# against the web login walks straight through the API with zero resistance.
OP6_TARGET_DISPLAY = "Gilles Mendel  [Montagne]"
OP6_USER = "g.mendel"
OP6_PASSWORD = "Fallback2019"     # works on BOTH channels -- only reachable via the API
OP6_WEB_THRESHOLD = 5              # real lockout: fires long before the wordlist's real entry
OP6_FLAG = "R6S{nomad_flanked_kaid_via_the_forgotten_api}"

OP6_WEB_ATTEMPTS = {}    # username -> failed-attempt count on the HARDENED web channel only
OP6_WEB_LOCKED = set()   # usernames genuinely, permanently locked out on the web channel


@app.route("/op6/")
def op6_index():
    return render_template("op6_login.html")


@app.route("/op6/login", methods=["POST"])
def op6_login():
    username = (request.form.get("username") or "").strip().lower()
    password = request.form.get("password") or ""

    if username == OP6_USER and username in OP6_WEB_LOCKED:
        return render_template("op6_login.html",
            error="Account locked due to repeated failed attempts. Contact an administrator."), 423

    if username == OP6_USER and password == OP6_PASSWORD:
        session["op6_authed"] = True
        return redirect(url_for("op6_console"))     # a genuinely correct login always works

    if username == OP6_USER:
        OP6_WEB_ATTEMPTS[username] = OP6_WEB_ATTEMPTS.get(username, 0) + 1
        if OP6_WEB_ATTEMPTS[username] >= OP6_WEB_THRESHOLD:
            OP6_WEB_LOCKED.add(username)            # real lockout -- no bypass, unlike Op04
            return render_template("op6_login.html",
                error="Account locked due to repeated failed attempts. Contact an administrator."), 423

    # generic failure -- no username enumeration here either (Op01's lesson, actually fixed)
    return render_template("op6_login.html", error="Invalid username or password."), 401


@app.route("/api/v1/login", methods=["POST"])
def op6_api_login():
    # VULN: the "forgotten" alternative channel. No lockout tracking of any kind, and
    # VULN: verbose per-field errors reintroduce username enumeration (Op01's bug, back
    # again, because hardening one channel doesn't harden the other).
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""

    if username != OP6_USER:
        return jsonify(error="unknown_user", message="No account with that username."), 401
    if password != OP6_PASSWORD:
        return jsonify(error="invalid_password", message="Password incorrect."), 401

    session["op6_authed"] = True
    return jsonify(success=True, message="Authenticated.", next="/op6/console")


@app.route("/op6/console")
def op6_console():
    if not session.get("op6_authed"):
        return redirect(url_for("op6_index"))
    mark_solved(6)                                  # reaching the console clears Op06 -- campaign complete
    return render_template("op6_console.html", flag=OP6_FLAG, user=OP6_TARGET_DISPLAY)


# ====================================== MASQUERADE OP 01 — session schema / cookie tampering
# WSTG-SESS-01. The bank's session cookie is a home-rolled, unsigned token: just
# base64("username:role:checksum"). The "checksum" LOOKS like an integrity control (it's
# computed from a secret-looking salt) but the server never recomputes or compares it on
# read -- it just trusts whatever username/role the decoded cookie claims. Change "customer"
# to "vault_manager", re-encode, replay -- the stale/wrong checksum is never even inspected.
# This is deliberately the FIRST session-management op: one clean lesson (does the server
# independently validate, or trust the cookie?), same core question as every future op in
# this campaign will ask about a different token format (JWT, OAuth, OTP).
#
# Secondary/bonus finding (observe-and-report, not required for the flag): the cookie is
# set with none of WSTG-SESS-01's checklist flags -- no HttpOnly, no Secure, no SameSite.
MASQ1_USER = "j.doe"
MASQ1_PASSWORD = "Customer2024!"          # given directly -- this op is not about cracking it
MASQ1_SALT = "RC-BANK-2024"               # cosmetic; the "checksum" below is never re-verified
MASQ1_TARGET_ROLE = "vault_manager"
MASQ1_FLAG = "R6S{iana_forged_vault_manager_role}"


def masq1_make_cookie(username, role):
    checksum = hashlib.md5(f"{username}:{role}:{MASQ1_SALT}".encode()).hexdigest()[:8]
    raw = f"{username}:{role}:{checksum}"
    return base64.b64encode(raw.encode()).decode()


def masq1_decode_cookie(value):
    # VULN: parses the structure, but never recomputes/compares the checksum against
    # what it SHOULD be for (username, role) -- so a stale or simply wrong checksum
    # from a tampered cookie is accepted exactly the same as a freshly-issued one.
    try:
        raw = base64.b64decode(value).decode()
        username, role, checksum = raw.split(":")
        return {"username": username, "role": role, "checksum": checksum}
    except Exception:
        return None


@app.route("/masquerade/op1/")
def masq1_index():
    return render_template("masq1_login.html")


@app.route("/masquerade/op1/login", methods=["POST"])
def masq1_login():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    if username != MASQ1_USER or password != MASQ1_PASSWORD:
        return render_template("masq1_login.html", error="Invalid username or password."), 401
    resp = make_response(redirect(url_for("masq1_account")))
    # VULN: no HttpOnly / Secure / SameSite -- a real secondary finding on its own.
    resp.set_cookie("bank_session", masq1_make_cookie(username, "customer"))
    return resp


@app.route("/masquerade/op1/account")
def masq1_account():
    data = masq1_decode_cookie(request.cookies.get("bank_session", ""))
    if not data:
        return redirect(url_for("masq1_index"))
    return render_template("masq1_account.html", user=data["username"], role=data["role"])


@app.route("/masquerade/op1/vault")
def masq1_vault():
    data = masq1_decode_cookie(request.cookies.get("bank_session", ""))
    if not data:
        return redirect(url_for("masq1_index"))
    if data["role"] != MASQ1_TARGET_ROLE:
        return render_template("masq1_vault.html", granted=False, role=data["role"],
                               required=MASQ1_TARGET_ROLE), 403
    mark_masq_solved(1)                              # reaching the vault clears Masquerade Op01
    return render_template("masq1_vault.html", granted=True, flag=MASQ1_FLAG)


# ====================================== MASQUERADE OP 02 — session fixation (WSTG-SESS-03)
# The hotel's "key card" (session cookie) is created the moment ANYONE visits the portal --
# before login, before any identity is known -- and the server accepts a client-SUPPLIED
# value just as happily as one it generates itself, via either the cookie or a `guest_sid`
# URL parameter (WSTG-SESS-03's own checklist flags URL-carried session IDs separately).
# The core bug: logging in NEVER issues a new key card. Whatever card (sid) was already
# attached to the request when the login form is submitted is the exact same card that
# walks away authenticated. An attacker never has to steal anything -- they just need to
# hand a victim a pre-chosen card number and wait for the victim to check in with it.
#
# There's a real NPC victim, not a role you play yourself: the front desk lets the player
# hand a card number to R. VOSS (Meridian's regional director, arriving today), and the
# server plays Voss's part -- visits that card, checks in with Voss's OWN password, which
# the player is never shown. The player never needed that password either: reaching the
# flag only requires reusing the card AFTER Voss has checked in with it, in a request that
# carries no credentials of any kind. That's the whole attack, not a mental exercise.
#
# Every session tracks WHO authenticated it -- "guest" (the player, with their own real
# account, used as the harmless baseline: normal use isn't broken) vs "npc" (Voss, via the
# front-desk simulation). Only a card that Voss personally checked in on clears the mission;
# the player logging into their OWN account on a self-planted card proves nothing anymore --
# that shortcut is gone on purpose, because it let people "solve" this without ever
# demonstrating that a *different* person's credentials were the ones actually used.
#
# masq2_is_server_issued (below) still exists and is still correct -- a signed sid verifies
# forever, restart or not, exactly as before -- but it's no longer the win condition itself.
# WHO logged in (tracked per-sid, reset to nobody on every server restart, same as it should
# be) is what decides the flag now; the signature is kept as the honest, stateless way to
# recognize a genuinely server-issued card if anything else in this app needs to ask.
MASQ2_USER = "guest.stay"
MASQ2_PASSWORD = "Meridian2024!"          # your own real account -- baseline only, not the exploit
MASQ2_FLAG = "R6S{zero_planted_the_key_card_before_checkin}"
MASQ2_SIGNING_KEY = "meridian-front-desk-2024"   # fixed on purpose -- must survive restarts

MASQ2_NPC_NAME = "R. Voss"
MASQ2_NPC_TITLE = "Regional Director"
MASQ2_NPC_USER = "r.voss"
MASQ2_NPC_PASSWORD = secrets.token_hex(16)   # generated at startup -- the player never sees this

MASQ2_SESSIONS = {}    # sid -> {"authenticated": bool, "authenticated_as": "guest"|"npc"|None}
MASQ2_SID_RE = re.compile(r"[A-Za-z0-9._-]{1,64}")


def masq2_sign(raw):
    return hmac.new(MASQ2_SIGNING_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()[:16]


def masq2_make_sid():
    raw = secrets.token_hex(8)
    return f"{raw}.{masq2_sign(raw)}"


def masq2_is_server_issued(sid):
    raw, sep, sig = sid.rpartition(".")
    return bool(sep) and hmac.compare_digest(masq2_sign(raw), sig)


def masq2_get_session():
    """Reuse whatever sid the request already carries (cookie OR ?guest_sid=). Only mint a
    fresh, server-signed sid if truly none was supplied. VULN: never rotates the sid on
    login -- see masq2_authenticate below."""
    incoming = request.cookies.get("guest_sid") or request.args.get("guest_sid")
    if incoming:
        if incoming not in MASQ2_SESSIONS:
            MASQ2_SESSIONS[incoming] = {"authenticated": False, "authenticated_as": None}
        return incoming, MASQ2_SESSIONS[incoming]
    sid = masq2_make_sid()
    MASQ2_SESSIONS[sid] = {"authenticated": False, "authenticated_as": None}
    return sid, MASQ2_SESSIONS[sid]


def masq2_authenticate(sess, who):
    """VULN lives here: whoever calls this just flips the SAME sid to authenticated. Nothing
    ever calls masq2_get_session() again afterward with a freshly minted replacement -- the
    identifier that walks away authenticated is whatever was already attached going in."""
    sess["authenticated"] = True
    sess["authenticated_as"] = who


@app.route("/masquerade/op2/")
def masq2_index():
    sid, _ = masq2_get_session()
    resp = make_response(render_template("masq2_login.html",
        npc_name=MASQ2_NPC_NAME, npc_title=MASQ2_NPC_TITLE))
    resp.set_cookie("guest_sid", sid)
    return resp


@app.route("/masquerade/op2/login", methods=["POST"])
def masq2_login():
    sid, sess = masq2_get_session()          # whatever sid is already attached -- untouched
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    if username != MASQ2_USER or password != MASQ2_PASSWORD:
        resp = make_response(render_template("masq2_login.html",
            error="Invalid username or password.",
            npc_name=MASQ2_NPC_NAME, npc_title=MASQ2_NPC_TITLE), 401)
        resp.set_cookie("guest_sid", sid)
        return resp
    masq2_authenticate(sess, "guest")        # this is YOUR account -- the harmless baseline
    resp = make_response(redirect(url_for("masq2_reservations")))
    resp.set_cookie("guest_sid", sid)
    return resp


@app.route("/masquerade/op2/send-link", methods=["POST"])
def masq2_send_link():
    """The front desk, on the player's behalf, hands a chosen card number to R. Voss before
    Voss ever checks in. The server then plays Voss's part end-to-end: Voss visits that exact
    card and checks in with Voss's OWN password -- a real, valid, completely ordinary login
    the player never sees and could not have performed themselves."""
    raw = (request.form.get("sid") or "").strip()
    if not MASQ2_SID_RE.fullmatch(raw):
        return make_response(render_template("masq2_login.html",
            link_error="Card numbers: letters, digits, dot, dash, underscore -- 1 to 64 characters.",
            npc_name=MASQ2_NPC_NAME, npc_title=MASQ2_NPC_TITLE), 400)

    if raw not in MASQ2_SESSIONS:
        MASQ2_SESSIONS[raw] = {"authenticated": False, "authenticated_as": None}
    # Voss "visits" the card, then checks in with credentials the player is never given --
    # same masq2_authenticate() every real login goes through, just not the player's turn.
    masq2_authenticate(MASQ2_SESSIONS[raw], "npc")

    return render_template("masq2_login.html", link_sent=raw,
        npc_name=MASQ2_NPC_NAME, npc_title=MASQ2_NPC_TITLE)


@app.route("/masquerade/op2/reservations")
def masq2_reservations():
    sid, sess = masq2_get_session()
    resp = None
    if not sess["authenticated"]:
        resp = make_response(render_template("masq2_reservations.html", authed=False), 401)
    elif sess["authenticated_as"] != "npc":
        # you, logged into your OWN account -- functionally fine, proves nothing about fixation
        resp = make_response(render_template("masq2_reservations.html",
            authed=True, fixated=False))
    else:
        mark_masq_solved(2)                  # reaching this on Voss's card clears Op02
        resp = make_response(render_template("masq2_reservations.html",
            authed=True, fixated=True, flag=MASQ2_FLAG,
            npc_name=MASQ2_NPC_NAME, npc_title=MASQ2_NPC_TITLE))
    resp.set_cookie("guest_sid", sid)
    return resp


# ====================================== MASQUERADE OP 03 — CSRF (WSTG-SESS-05)
# Coastline Ops runs an internal ticket system for resort staff. Its password-change
# handler trusts exactly one thing: that the request carries a valid session cookie.
# It never asks for anything the browser wouldn't send automatically -- no per-request
# token, no re-entered current password, nothing tying the request to a page the user
# actually meant to submit. The browser doesn't ask permission before attaching a
# cookie to a request either way, so a page that has NOTHING to do with Coastline Ops
# can make a logged-in visitor's browser fire that exact request for them.
#
# D. CHO, the helpdesk administrator, is a real account, always logged in during
# business hours, whose password the player is never shown and can never learn any
# other way -- the only path to it is getting D. Cho's own browser to reset it via a
# forged request. The "Host a Malicious Page" panel is that delivery mechanism: the
# player writes real HTML (a hidden auto-submitting form, same shape as any real CSRF
# proof-of-concept), the app safely parses it (no execution -- html.parser only reads
# tags), and if it genuinely reproduces the vulnerable request, D. Cho's browser is
# modeled as visiting it and firing the form -- exactly as an unsuspecting admin's
# browser would in the real world.
MASQ3_USER = "support.agent"
MASQ3_PASSWORD = "Ticket2024!"                     # your own account -- baseline only

MASQ3_ADMIN_USER = "d.cho"
MASQ3_ADMIN_NAME = "D. Cho"
MASQ3_ADMIN_TITLE = "Helpdesk Administrator"

MASQ3_FLAG = "R6S{ying_reset_d_chos_password_with_one_click}"
MASQ3_VULN_PATH = "/masquerade/op3/ticket/"        # mirrors the real advisory's URL shape

MASQ3_PASSWORDS = {MASQ3_USER: MASQ3_PASSWORD, MASQ3_ADMIN_USER: secrets.token_hex(16)}


class Masq3PoCParser(HTMLParser):
    """Safe, read-only HTML tag-walker -- this NEVER executes anything (no eval, no
    JS engine, no real browser). It only reads a <form>'s action/method and its
    <input> fields, exactly what a real browser reads before submitting one."""
    def __init__(self):
        super().__init__()
        self.form_found = False
        self.method = None
        self.action = None
        self.fields = {}
        self._in_form = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        tag = tag.lower()
        if tag == "form":
            self.form_found = True
            self._in_form = True
            self.method = (attrs.get("method") or "get").strip().lower()
            self.action = attrs.get("action") or ""
        elif tag == "input" and self._in_form:
            name = attrs.get("name")
            if name:
                self.fields[name] = attrs.get("value", "")

    def handle_endtag(self, tag):
        if tag.lower() == "form":
            self._in_form = False


def masq3_check_poc(html_text):
    """Does the submitted HTML actually reproduce the real exploit's shape: an
    auto-submitting POST form targeting the vulnerable endpoint, with matching
    password fields? Returns (ok, new_password_or_error_message)."""
    if len(html_text) > 20000:
        return False, "That's a lot of HTML for a password-reset page -- keep it under 20,000 characters."
    parser = Masq3PoCParser()
    try:
        parser.feed(html_text)
    except Exception:
        return False, "Could not parse that as HTML."
    if not parser.form_found:
        return False, "No <form> found -- the real endpoint only accepts a form submission."
    if parser.method != "post":
        return False, f"Form method is {(parser.method or 'get').upper()}, but the vulnerable endpoint is a POST handler."
    if MASQ3_VULN_PATH not in (parser.action or ""):
        return False, f"Form action doesn't target {MASQ3_VULN_PATH} -- that's the real vulnerable endpoint."
    new_pw = parser.fields.get("new_password")
    confirm_pw = parser.fields.get("confirm_password")
    if not new_pw or not confirm_pw:
        return False, "Missing new_password / confirm_password hidden fields."
    if new_pw != confirm_pw:
        return False, "new_password and confirm_password don't match -- the real form requires both."
    if "submit" not in parser.fields:
        return False, "Missing the hidden 'submit' field -- the real handler checks for that too."
    if ".submit(" not in html_text:
        return False, ("Nothing auto-submits this form. A lure only ever gets ONE click -- on "
                        "whatever link opens your page. Add a script (or an onload handler) that "
                        "calls .submit() on the form itself.")
    return True, new_pw


@app.route("/masquerade/op3/")
def masq3_index():
    return render_template("masq3_login.html",
        admin_name=MASQ3_ADMIN_NAME, admin_title=MASQ3_ADMIN_TITLE)


@app.route("/masquerade/op3/login", methods=["POST"])
def masq3_login():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    if MASQ3_PASSWORDS.get(username) != password:
        return render_template("masq3_login.html", error="Invalid username or password.",
            admin_name=MASQ3_ADMIN_NAME, admin_title=MASQ3_ADMIN_TITLE), 401
    session["masq3_user"] = username
    return redirect(url_for("masq3_dashboard"))


@app.route("/masquerade/op3/logout")
def masq3_logout():
    session.pop("masq3_user", None)
    return redirect(url_for("masq3_index"))


@app.route("/masquerade/op3/host-poc", methods=["POST"])
def masq3_host_poc():
    """Not the vulnerable endpoint itself -- this is the challenge's delivery
    simulation: submit real PoC HTML, and if it's genuine, D. Cho's browser is
    modeled as visiting it and firing the form, exactly like a real lure would."""
    html_text = request.form.get("poc") or ""
    ok, result = masq3_check_poc(html_text)
    if not ok:
        return render_template("masq3_login.html", poc_error=result, poc_value=html_text,
            admin_name=MASQ3_ADMIN_NAME, admin_title=MASQ3_ADMIN_TITLE), 400
    MASQ3_PASSWORDS[MASQ3_ADMIN_USER] = result
    return render_template("masq3_login.html", poc_sent=True,
        admin_name=MASQ3_ADMIN_NAME, admin_title=MASQ3_ADMIN_TITLE)


@app.route(MASQ3_VULN_PATH, methods=["GET", "POST"])
def masq3_ticket():
    """THE vulnerable endpoint. Mirrors the real advisory's exact URL shape
    (?p=process_change_password&id=1) and form fields. VULN: no CSRF token anywhere
    below -- the only thing checked is that *someone* is logged in, via a cookie the
    browser would attach to this request whether the user meant to send it or not."""
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


@app.route("/masquerade/op3/dashboard")
def masq3_dashboard():
    who = session.get("masq3_user")
    if not who:
        return render_template("masq3_dashboard.html", authed=False), 401
    if who == MASQ3_ADMIN_USER:
        mark_masq_solved(3)                  # only reachable by knowing D. Cho's CURRENT password
        return render_template("masq3_dashboard.html", authed=True, is_admin=True,
            flag=MASQ3_FLAG, admin_name=MASQ3_ADMIN_NAME, admin_title=MASQ3_ADMIN_TITLE)
    return render_template("masq3_dashboard.html", authed=True, is_admin=False)


# ====================================== MASQUERADE OP 04 — the "none" algorithm (WSTG-SESS-10)
# The Chalet Concierge is stateless auth done the JWT way: no session, no server-side
# lookup, just a signed token the client carries and presents on every request. The
# server's whole job is to recompute that signature and compare -- EXCEPT this server
# reads which algorithm to use for that check from the token's own header. The header
# is just base64 -- attacker-controlled, exactly like every other part of the token.
# Set alg to "none" and the verifier skips the signature check entirely, trusting
# whatever role claim sits in the payload. No brute force, no stolen credential, no
# victim to trick -- unlike Ops 02 and 03, this one needs nobody else's account at all.
# An attacker manufactures a fully "valid" credential from nothing.
MASQ4_USER = "retreat.member"
MASQ4_PASSWORD = "Chalet2024!"                    # given directly -- this op is not about cracking it
MASQ4_MEMBER_ROLE = "member"
MASQ4_DIRECTOR_ROLE = "director"
MASQ4_FLAG = "R6S{kali_forged_alg_none_into_the_directors_role}"
MASQ4_SECRET = "chalet-director-2024"             # fixed HMAC key -- real, never shown to the player


def masq4_b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def masq4_b64url_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def masq4_sign(header_b64, payload_b64):
    signing_input = f"{header_b64}.{payload_b64}".encode()
    digest = hmac.new(MASQ4_SECRET.encode(), signing_input, hashlib.sha256).digest()
    return masq4_b64url_encode(digest)


def masq4_issue_token(username, role):
    header = {"typ": "JWT", "alg": "HS256"}
    payload = {"sub": username, "role": role, "iat": int(time.time())}
    h_b64 = masq4_b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p_b64 = masq4_b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    return f"{h_b64}.{p_b64}.{masq4_sign(h_b64, p_b64)}", header, payload


def masq4_verify_token(token):
    """Returns (ok, payload_dict_or_error). VULN: trusts the client-controlled `alg`
    field to decide HOW (or whether) to verify -- including "none", accepted
    case-insensitively, exactly like the real vulnerable libraries this bug class
    is named after."""
    parts = (token or "").split(".")
    if len(parts) != 3:
        return False, "Malformed token -- expected three dot-separated parts."
    h_b64, p_b64, sig_b64 = parts
    try:
        header = json.loads(masq4_b64url_decode(h_b64))
        payload = json.loads(masq4_b64url_decode(p_b64))
    except Exception:
        return False, "Header or payload isn't valid base64url-encoded JSON."
    alg = str(header.get("alg", "")).strip().lower()
    if alg == "none":
        return True, payload                          # VULN: zero signature verification
    if alg == "hs256":
        if hmac.compare_digest(masq4_sign(h_b64, p_b64), sig_b64):
            return True, payload
        return False, "Signature does not match."
    return False, f"Unsupported algorithm: {header.get('alg')!r}"


def masq4_pretty(obj):
    return json.dumps(obj, indent=2)


@app.route("/masquerade/op4/")
def masq4_index():
    return render_template("masq4_login.html")


@app.route("/masquerade/op4/login", methods=["POST"])
def masq4_login():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    if username != MASQ4_USER or password != MASQ4_PASSWORD:
        return render_template("masq4_login.html", error="Invalid username or password."), 401
    token, header, payload = masq4_issue_token(username, MASQ4_MEMBER_ROLE)
    return render_template("masq4_login.html", token=token,
        header_json=masq4_pretty(header), payload_json=masq4_pretty(payload))


def masq4_ledger_result(token):
    if not token:
        return None, "No token presented.", 401
    ok, result = masq4_verify_token(token)
    if not ok:
        return None, result, 401
    return result, None, 200


@app.route("/masquerade/op4/ledger")
def masq4_ledger():
    """The real protected resource -- a REST-style endpoint, exactly like the notes
    describe: Authorization: Bearer <token>, JSON in, JSON out, no session lookup."""
    auth = request.headers.get("Authorization", "")
    token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    payload, error, status = masq4_ledger_result(token)
    if error:
        return jsonify({"error": error}), status
    if payload.get("role") == MASQ4_DIRECTOR_ROLE:
        mark_masq_solved(4)
        return jsonify({"ok": True, "role": payload.get("role"), "flag": MASQ4_FLAG})
    return jsonify({"ok": True, "role": payload.get("role"), "sub": payload.get("sub")})


@app.route("/masquerade/op4/present-token", methods=["POST"])
def masq4_present_token():
    """Convenience wrapper for the SAME check as /ledger, for players working from
    the browser instead of curl/Burp -- not a separate, easier code path."""
    token = (request.form.get("token") or "").strip()
    payload, error, status = masq4_ledger_result(token)
    if error:
        return render_template("masq4_ledger.html", authed=False, error=error), status
    if payload.get("role") == MASQ4_DIRECTOR_ROLE:
        mark_masq_solved(4)
        return render_template("masq4_ledger.html", authed=True, is_director=True,
            flag=MASQ4_FLAG, payload_json=masq4_pretty(payload))
    return render_template("masq4_ledger.html", authed=True, is_director=False,
        payload_json=masq4_pretty(payload))


# ====================================== MASQUERADE OP 05 — exposed claim (WSTG-SESS-10)
# Op04 taught "the header can lie about whether to verify." This one is the opposite
# lesson: the Oregon relay's verifier does everything right -- it hard-codes HS256,
# it actually recomputes and compares the signature, every single time. The bug isn't
# in the verification logic at all. It's in what the signature is a promise ABOUT.
# A signature only proves "someone who knows the secret produced this" -- it says
# nothing about how easy that secret was to find. This one uses a short, guessable
# HMAC key (the kind real teams pick when a signing secret feels like an
# implementation detail, not a credential) and a payload that leaks a second claim
# that never should have been in a token that anyone holding it can read in plain
# text. Two different findings, same root cause: treating a JWT's contents and the
# key that signs them as less sensitive than they actually are.
MASQ5_USER = "field.agent"
MASQ5_PASSWORD = "Oregon2024!"                    # given directly -- this op is not about cracking it
MASQ5_FIELD_ROLE = "field_agent"
MASQ5_LEAD_ROLE = "dispatch_lead"
MASQ5_SUPPORT_PIN = "4821"          # secondary finding: sensitive data that never belonged in a JWT
MASQ5_FLAG = "R6S{jackal_tracked_the_weak_secret_to_dispatch_lead}"
MASQ5_SECRET = "relay41"            # weak on purpose -- sits in wordlists/op5_jwt_secrets.txt


def masq5_b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def masq5_b64url_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def masq5_sign(header_b64, payload_b64, secret):
    signing_input = f"{header_b64}.{payload_b64}".encode()
    digest = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return masq5_b64url_encode(digest)


def masq5_issue_token(username, role):
    header = {"typ": "JWT", "alg": "HS256"}
    payload = {"sub": username, "role": role, "support_pin": MASQ5_SUPPORT_PIN, "iat": int(time.time())}
    h_b64 = masq5_b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p_b64 = masq5_b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    return f"{h_b64}.{p_b64}.{masq5_sign(h_b64, p_b64, MASQ5_SECRET)}", header, payload


def masq5_verify_token(token):
    """Returns (ok, payload_dict_or_error). Unlike Op04, there is no algorithm
    confusion to exploit here -- only HS256 is ever accepted, and the signature is
    genuinely, unconditionally recomputed and compared. VULN: MASQ5_SECRET is weak
    enough to recover by trying candidates offline (see wordlists/op5_jwt_secrets.txt)
    -- once known, it signs any payload an attacker wants, correctly."""
    parts = (token or "").split(".")
    if len(parts) != 3:
        return False, "Malformed token -- expected three dot-separated parts."
    h_b64, p_b64, sig_b64 = parts
    try:
        header = json.loads(masq5_b64url_decode(h_b64))
        payload = json.loads(masq5_b64url_decode(p_b64))
    except Exception:
        return False, "Header or payload isn't valid base64url-encoded JSON."
    if str(header.get("alg", "")).strip().upper() != "HS256":
        return False, "Only HS256 is accepted."
    if not hmac.compare_digest(masq5_sign(h_b64, p_b64, MASQ5_SECRET), sig_b64):
        return False, "Signature does not match."
    return True, payload


def masq5_pretty(obj):
    return json.dumps(obj, indent=2)


@app.route("/masquerade/op5/")
def masq5_index():
    return render_template("masq5_login.html")


@app.route("/masquerade/op5/login", methods=["POST"])
def masq5_login():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    if username != MASQ5_USER or password != MASQ5_PASSWORD:
        return render_template("masq5_login.html", error="Invalid username or password."), 401
    token, header, payload = masq5_issue_token(username, MASQ5_FIELD_ROLE)
    return render_template("masq5_login.html", token=token,
        header_json=masq5_pretty(header), payload_json=masq5_pretty(payload))


def masq5_relay_result(token):
    if not token:
        return None, "No token presented.", 401
    ok, result = masq5_verify_token(token)
    if not ok:
        return None, result, 401
    return result, None, 200


@app.route("/masquerade/op5/relay")
def masq5_relay():
    """The real protected resource -- REST-style, Authorization: Bearer, JSON in/out."""
    auth = request.headers.get("Authorization", "")
    token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    payload, error, status = masq5_relay_result(token)
    if error:
        return jsonify({"error": error}), status
    if payload.get("role") == MASQ5_LEAD_ROLE:
        mark_masq_solved(5)
        return jsonify({"ok": True, "role": payload.get("role"), "flag": MASQ5_FLAG})
    return jsonify({"ok": True, "role": payload.get("role"), "sub": payload.get("sub")})


@app.route("/masquerade/op5/present-token", methods=["POST"])
def masq5_present_token():
    """Convenience wrapper for the SAME check as /relay, for players working from
    the browser instead of curl/Burp -- not a separate, easier code path."""
    token = (request.form.get("token") or "").strip()
    payload, error, status = masq5_relay_result(token)
    if error:
        return render_template("masq5_relay.html", authed=False, error=error), status
    if payload.get("role") == MASQ5_LEAD_ROLE:
        mark_masq_solved(5)
        return render_template("masq5_relay.html", authed=True, is_lead=True,
            flag=MASQ5_FLAG, payload_json=masq5_pretty(payload))
    return render_template("masq5_relay.html", authed=True, is_lead=False,
        payload_json=masq5_pretty(payload))


# ====================================== MASQUERADE OP 06 — attacking OAuth (WSTG-SESS / delegated auth)
# The Clubhouse runs a member photo gallery. A separate kiosk terminal -- "Print
# Kiosk" -- wants to fetch a member's photos on their behalf, so the club uses
# OAuth: a member never hands the kiosk their password, only a scoped, revocable
# token. That's the whole point of delegated authorization. Three independent
# weaknesses break it, each teaching a different lesson, each reachable on its own:
#
#   Stage 1 -- the authorize endpoint hands the authorization CODE to whatever
#   redirect_uri the request claims, without ever checking it's the kiosk's real,
#   registered callback. A link is all it takes -- the member never sees anything
#   wrong, because the consent screen looks completely normal either way.
#
#   Stage 2 -- exchanging a code for a token requires the kiosk's client_secret,
#   and that secret is short and guessable, with no rate limit on wrong guesses.
#   A stolen code plus a cracked secret is a real, working access token.
#
#   Stage 3 -- the access tokens themselves are small, low-entropy numbers, and
#   the resource endpoint that accepts them has no rate limit either. This one
#   doesn't even need Stages 1-2 -- it's a fully independent way in, exactly the
#   way a real assessment often finds several unrelated doors into the same room.
#
# Codes and tokens never expire in this app either -- worth noticing on its own.
MASQ6_USER = "club.member"
MASQ6_PASSWORD = "Clubhouse2024!"                  # your own account -- baseline only
MASQ6_CLIENT_ID = "print_kiosk"
MASQ6_CLIENT_SECRET = "kiosk41"                    # weak -- wordlists/op6_client_secrets.txt
MASQ6_SCOPE = "view_gallery"
MASQ6_LEGIT_REDIRECT = "/masquerade/op6/callback"  # the kiosk's real, registered callback
MASQ6_CATCHER_PATH = "/masquerade/op6/attacker-catch"
MASQ6_NPC_NAME = "N. Kruger"
MASQ6_NPC_TITLE = "Club Member"
MASQ6_FLAG = "R6S{hibana_burned_through_every_layer_of_delegated_trust}"

MASQ6_CODES = {}        # code -> {"redirect_uri":..., "consumed": bool, "owner": <whose consent this is>}
MASQ6_TOKENS = {}        # access_token -> {"scope":..., "owner": <whose gallery this unlocks>}
MASQ6_CAPTURED = []      # [{"code":..., "redirect_uri":...}] -- the "attacker's" access log

# Real gallery contents per member -- what a token for that owner actually unlocks.
# club.member's own gallery is just normal, boring club photos -- that's what
# legitimate access to your OWN resource looks like. N. Kruger's gallery has the
# same kind of normal photos PLUS one private item queued for kiosk pickup only --
# THAT'S the actual thing being protected, and the flag lives on it specifically.
# Reaching it is what "solved" means here, not merely holding any valid token.
MASQ6_GALLERIES = {
    MASQ6_USER: [
        {"emoji": "🍻", "caption": "clubhouse_bar.jpg", "desc": "Bar re-opening night"},
        {"emoji": "🎱", "caption": "league_table.jpg", "desc": "May pool league standings"},
        {"emoji": "🛠️", "caption": "patio_reno.jpg", "desc": "New patio furniture"},
    ],
    MASQ6_NPC_NAME: [
        {"emoji": "🍻", "caption": "clubhouse_bar.jpg", "desc": "Bar re-opening night"},
        {"emoji": "🤝", "caption": "back_room_meeting.jpg", "desc": "Committee back-room meeting"},
        {"emoji": "🎂", "caption": "n_kruger_bday.jpg", "desc": "N. Kruger's birthday"},
        {"private": True, "caption": "print_queue_private.jpg",
         "desc": "Queued for kiosk pickup only -- never shared with anyone else"},
    ],
}


def masq6_new_code():
    return secrets.token_hex(4)               # deliberately NOT low-entropy -- Stage 1 isn't about guessing codes


def masq6_new_token():
    return str(random.randint(1000, 9999))     # VULN: tiny, brute-forceable space -- Stage 3


@app.route("/masquerade/op6/")
def masq6_index():
    return render_template("masq6_index.html",
        npc_name=MASQ6_NPC_NAME, npc_title=MASQ6_NPC_TITLE,
        captured=list(reversed(MASQ6_CAPTURED)),
        me=session.get("masq6_user"),
        stage1=session.get("masq6_stage1", False),
        stage2=session.get("masq6_stage2", False))


@app.route("/masquerade/op6/login", methods=["POST"])
def masq6_login():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    if username != MASQ6_USER or password != MASQ6_PASSWORD:
        return render_template("masq6_index.html", error="Invalid username or password.",
            npc_name=MASQ6_NPC_NAME, npc_title=MASQ6_NPC_TITLE, captured=list(reversed(MASQ6_CAPTURED)),
            me=None, stage1=session.get("masq6_stage1", False),
            stage2=session.get("masq6_stage2", False)), 401
    session["masq6_user"] = username
    # Land the member ON their own gallery -- the normal, logged-in experience,
    # so "what a member actually sees" is concrete before any attack is attempted.
    return redirect(url_for("masq6_gallery_view"))


@app.route("/masquerade/op6/logout")
def masq6_logout():
    session.pop("masq6_user", None)
    return redirect(url_for("masq6_index"))


def masq6_generate_code(redirect_uri, owner):
    """owner is WHOSE consent this code represents -- the member who actually
    clicked Allow. Purely narrative bookkeeping (nothing gates on it), but it's
    what makes "whose account did I just compromise" a real, visible answer
    instead of an implied one."""
    code = masq6_new_code()
    MASQ6_CODES[code] = {"redirect_uri": redirect_uri, "consumed": False, "owner": owner}
    return code


@app.route("/masquerade/op6/oauth/authorize")
def masq6_authorize():
    """The real authorize endpoint -- shows a consent screen to whoever is
    logged in. VULN lives in masq6_approve below: redirect_uri is never checked
    against anything registered for client_id."""
    if not session.get("masq6_user"):
        return redirect(url_for("masq6_index"))
    client_id = request.args.get("client_id", "")
    redirect_uri = request.args.get("redirect_uri", "")
    scope = request.args.get("scope", "")
    response_type = request.args.get("response_type", "")
    return render_template("masq6_consent.html", client_id=client_id,
        redirect_uri=redirect_uri, scope=scope, response_type=response_type)


@app.route("/masquerade/op6/oauth/approve", methods=["POST"])
def masq6_approve():
    redirect_uri = request.form.get("redirect_uri", "")
    if request.form.get("decision") != "allow":
        return redirect(url_for("masq6_index"))
    code = masq6_generate_code(redirect_uri, owner=session.get("masq6_user", MASQ6_USER))
    return redirect(f"{redirect_uri}?code={code}")


@app.route("/masquerade/op6/reset-stage/<int:stage>")
def masq6_reset_stage(stage):
    """Redo a single stage's demonstration without resetting the whole
    operation -- clears just that stage's session-tracked 'cleared' flag."""
    if stage == 1:
        session.pop("masq6_stage1", None)
    elif stage == 2:
        session.pop("masq6_stage2", None)
    return redirect(request.referrer or url_for("masq6_index"))


@app.route("/masquerade/op6/callback")
def masq6_callback():
    """The kiosk's REAL, registered callback -- what a correctly-validated
    redirect_uri would always point back to. The kiosk itself holds the real
    client_secret and exchanges the code immediately, then fetches exactly one
    member's gallery -- whoever actually clicked Allow. This is what a normal,
    correctly-working OAuth flow looks like end to end, not just "code received"."""
    code = request.args.get("code", "")
    if not code:
        return render_template("masq6_callback.html", code=None)
    status, data = masq6_do_token_exchange("authorization_code", code,
        MASQ6_CLIENT_ID, MASQ6_CLIENT_SECRET, MASQ6_LEGIT_REDIRECT)
    if status != 200:
        return render_template("masq6_callback.html", code=code,
            exchange_error=data.get("error_description") or data.get("error"))
    owner = data["belongs_to"]
    return render_template("masq6_callback.html", code=code, owner=owner,
        gallery=MASQ6_GALLERIES.get(owner, []))


@app.route("/masquerade/op6/lure-member", methods=["POST"])
def masq6_lure_member():
    """Stage 1's delivery simulation: N. Kruger is always logged in and always
    approves -- exactly like a real unsuspecting member would. The redirect_uri
    the player supplies is NEVER checked against anything registered for the
    kiosk, which is the entire vulnerability."""
    redirect_uri = (request.form.get("redirect_uri") or "").strip()
    if not redirect_uri:
        return render_template("masq6_index.html", lure_error="Enter a redirect_uri to send.",
            npc_name=MASQ6_NPC_NAME, npc_title=MASQ6_NPC_TITLE, captured=list(reversed(MASQ6_CAPTURED)),
            stage1=session.get("masq6_stage1", False), stage2=session.get("masq6_stage2", False)), 400
    code = masq6_generate_code(redirect_uri, owner=MASQ6_NPC_NAME)
    if redirect_uri.startswith(MASQ6_CATCHER_PATH):
        MASQ6_CAPTURED.append({"code": code, "redirect_uri": redirect_uri})
        session["masq6_stage1"] = True
    return render_template("masq6_index.html",
        lure_sent=redirect_uri, npc_name=MASQ6_NPC_NAME, npc_title=MASQ6_NPC_TITLE,
        captured=list(reversed(MASQ6_CAPTURED)),
        stage1=session.get("masq6_stage1", False), stage2=session.get("masq6_stage2", False))


@app.route("/masquerade/op6/attacker-catch")
def masq6_attacker_catch():
    """A stand-in for 'your own server's access log' -- in a real attack this
    would just be whatever server you control at the redirect_uri you chose."""
    return render_template("masq6_catch.html", captured=list(reversed(MASQ6_CAPTURED)))


def masq6_do_token_exchange(grant_type, code, client_id, client_secret, redirect_uri):
    """The real exchange logic, shared by the real endpoint and the browser
    convenience form below -- one check, two ways to reach it. VULN:
    client_secret is weak and there is no rate limit on failed attempts --
    brute-forceable directly, online, as many times as an attacker likes."""
    if grant_type != "authorization_code":
        return 400, {"error": "unsupported_grant_type"}
    entry = MASQ6_CODES.get(code)
    if not entry or entry["consumed"]:
        return 400, {"error": "invalid_grant", "error_description": "Unknown or already-used code."}
    if redirect_uri != entry["redirect_uri"]:
        return 400, {"error": "invalid_grant", "error_description": "redirect_uri does not match the one used to obtain this code."}
    if client_id != MASQ6_CLIENT_ID:
        return 401, {"error": "invalid_client"}
    if client_secret != MASQ6_CLIENT_SECRET:
        return 401, {"error": "invalid_client", "error_description": "Client authentication failed."}
    entry["consumed"] = True
    token = masq6_new_token()
    MASQ6_TOKENS[token] = {"scope": MASQ6_SCOPE, "owner": entry["owner"]}
    return 200, {"access_token": token, "token_type": "bearer", "scope": MASQ6_SCOPE, "belongs_to": entry["owner"]}


@app.route("/masquerade/op6/oauth/token", methods=["POST"])
def masq6_token():
    status, data = masq6_do_token_exchange(
        request.form.get("grant_type", ""), request.form.get("code", ""),
        request.form.get("client_id", ""), request.form.get("client_secret", ""),
        request.form.get("redirect_uri", ""))
    if status == 200:
        session["masq6_stage2"] = True
    return jsonify(data), status


@app.route("/masquerade/op6/exchange-code", methods=["POST"])
def masq6_exchange_code_form():
    """Convenience wrapper for the SAME check as /oauth/token, for exploring one
    guess at a time from the browser -- not a separate, easier code path. Real
    brute-forcing happens by scripting many requests to the real endpoint."""
    code = (request.form.get("code") or "").strip()
    secret_guess = (request.form.get("secret") or "").strip()
    redirect_uri = MASQ6_CODES.get(code, {}).get("redirect_uri", "")
    _status, data = masq6_do_token_exchange("authorization_code", code, MASQ6_CLIENT_ID, secret_guess, redirect_uri)
    if _status == 200:
        session["masq6_stage2"] = True
    return render_template("masq6_index.html",
        exchange_result=data, npc_name=MASQ6_NPC_NAME, npc_title=MASQ6_NPC_TITLE,
        captured=list(reversed(MASQ6_CAPTURED)),
        stage1=session.get("masq6_stage1", False), stage2=session.get("masq6_stage2", False))


def masq6_authenticate():
    """THE authorization check for this resource -- the one and only place
    that decides whose gallery a request gets. Accepts EITHER a Bearer
    access_token (what Print Kiosk, or anyone holding a stolen/guessed token,
    presents) OR your own session cookie (the normal logged-in browser path).
    A token takes priority when one is supplied, since presenting one is an
    explicit request to act as whoever it belongs to. This is the real shape
    a lot of production resource servers have: one endpoint, first-party
    session clients and third-party OAuth clients both walking in the same
    door -- which is exactly why a weak token space (Stage 3) is enough to
    compromise it on its own, with no session and no OAuth flow involved.

    Accepts the token two ways, matching RFC 6750: the real
    Authorization: Bearer <token> header (what Burp, curl, and any real
    OAuth client actually send) takes priority, with ?access_token= as a
    fallback for testing straight from a browser address bar or form."""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else ""
    if not token:
        token = request.values.get("access_token", "")
    if token:
        entry = MASQ6_TOKENS.get(token)
        return (entry["owner"], "token") if entry else (None, None)
    me = session.get("masq6_user")
    return (me, "session") if me else (None, None)


@app.route("/masquerade/op6/photos/me")
def masq6_photos_me():
    """The real protected resource, JSON form -- what Print Kiosk (or an
    attacker with curl/Burp) actually calls. Runs through masq6_authenticate()
    above, same as the HTML view below: same check, same data, two renderings."""
    owner, via = masq6_authenticate()
    if not owner:
        return jsonify({"error": "invalid_token_or_session"}), 401
    gallery = MASQ6_GALLERIES.get(owner, [])
    resp = {"ok": True, "auth": via, "gallery_owner": owner,
        "photos": [p["caption"] for p in gallery]}
    if any(p.get("private") for p in gallery):
        mark_masq_solved(6)
        resp["flag"] = MASQ6_FLAG
    return jsonify(resp)


@app.route("/masquerade/op6/gallery", methods=["GET", "POST"])
def masq6_gallery_view():
    """The single HTML view onto this SAME resource -- reached either by
    clicking 'View My Gallery' as a logged-in member (GET, session cookie,
    no token needed) or by submitting an access_token at Stage 3 (POST,
    Bearer-token path). Both go through masq6_authenticate() above; nothing
    here re-implements or duplicates that check."""
    owner, via = masq6_authenticate()
    if not owner:
        return render_template("masq6_victory.html", authed=False), 401
    gallery = MASQ6_GALLERIES.get(owner, [])
    is_victim = any(p.get("private") for p in gallery)
    if is_victim:
        mark_masq_solved(6)
    if via == "session":
        return render_template("masq6_gallery.html", owner=owner,
            gallery=gallery, npc_name=MASQ6_NPC_NAME)
    return render_template("masq6_victory.html", authed=True,
        flag=MASQ6_FLAG if is_victim else None, owner=owner, is_victim=is_victim,
        gallery=gallery, npc_name=MASQ6_NPC_NAME, via=via)


@app.after_request
def hdr(resp):
    resp.headers["Server"] = "Rainbow-Corp Secure Portal"
    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
