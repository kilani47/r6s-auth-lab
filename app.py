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
import hashlib
import secrets
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


# ================================================================ HUB / COMMAND
@app.route("/")
def hub():
    s = solved_set()
    nxt = next_unsolved()
    # reveal cleared missions + the single next one; hide everything beyond.
    visible = [m for m in MISSIONS if m["id"] in s or m["id"] == nxt]
    more = any(m["id"] not in s and m["id"] != nxt for m in MISSIONS)
    return render_template("hub.html", attackers=ATTACKERS, defenders=DEFENDERS,
                           visible=visible, solved=s, nxt=nxt, more=more,
                           total_cleared=len(s))


@app.route("/reset-progress")
def reset_progress():
    session.pop("solved", None)
    return redirect(url_for("hub"))


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


@app.after_request
def hdr(resp):
    resp.headers["Server"] = "Rainbow-Corp Secure Portal"
    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
