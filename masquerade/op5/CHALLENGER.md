# 🎭 Masquerade Operation 05 — Exposed Claim

**Attacker:** Jackal &nbsp;⚔&nbsp; **Defender:** Pulse
**WSTG:** WSTG-SESS-10 — Testing JSON Web Tokens
**Target:** `http://localhost:8000/masquerade/op5/` (unlocks after Operation 04 is cleared)

**No solutions below.** Read [`DEBRIEF.md`](DEBRIEF.md) only once you're stuck, want to check
your work, or want the lesson spelled out after solving.

---

## Mission

**Oregon Relay** runs field dispatch for a remote outpost — same stateless, Bearer-token
authentication model as Chalet Concierge before it. Before you assume this is Operation 04
again: it isn't. Read the header on your own token carefully once you have one. This
verifier does not make that mistake.

> **If the signature check is actually correct, what's left to attack?**

### What you're given

```
Your Field ID: field.agent
Your Password: Oregon2024!
```

That's a real, working login. It gets you a real token, correctly signed, correctly
verified on every request. Use it — both to see honest behavior, and to get a genuine sample
of exactly what you're up against.

### Objectives

1. **Sign in and decode your token.** Read every field in the payload, not just the ones you
   expect to be there.
2. **Confirm the verifier is actually doing its job.** Tamper the payload without redoing the
   signature and present it. Watch what happens — this is not Operation 04's bug, and
   ruling that out is worth doing on purpose, not by accident.
3. **A signature proves someone who holds the key produced it. It says nothing about how
   hard that key was to find.** You have a candidate list of keys the size of a normal
   password wordlist: `wordlists/op5_jwt_secrets.txt`. One of them is real.
4. **Recover the real key**, offline, without sending a single request to the server for the
   cracking itself — this is math you can do entirely on your own machine, the same way a
   real `jwt_tool` or `hashcat` run against a captured token works.
5. **Sign a brand-new token yourself**, with whatever claims you want, using the key you
   recovered — and reach the Dispatch Lead Channel with a role nobody granted you.

There's a second, much quieter finding sitting in your own token's payload the moment you
decode it in Objective 1. It won't get you the flag. Report it anyway — a real assessment
doesn't stop looking the moment it finds the loudest bug.

---

## Rules of Engagement

Attack it however you'd attack a real target — `curl`, Burp, Postman, Python `requests`,
jwt.io for quick decode/encode busywork. As with Operation 04, there's no HTML form that can
forge a custom `Authorization` header for you; this needs a real HTTP client, not just a
browser tab. The in-page "present a token" panel is a convenience for viewing results, not a
separate or easier verification path — it runs the exact same check as the real endpoint.

The wordlist is genuinely all you need — no answers, but a bounded, honest search space.
Writing a ten-line script to try each candidate is the entire "hard" part of this mission, and
it's also exactly the real-world skill being tested.

Don't skip to reading `app.py`. Confirm what you can observe from the outside before you go
looking for the reason behind it.

---

## 💡 Hints (progressive — open only if stuck)

<details><summary>Hint 1 — decode everything, not just what you expect</summary>

Your token's payload has more fields in it than the ones from Operation 04. Decode the whole
thing and read every key, not just `role`.
</details>

<details><summary>Hint 2 — rule out the easy bypass on purpose</summary>

Try Operation 04's trick here — `alg:none`, empty signature. Read the response carefully. This
verifier is doing something different, and confirming exactly what before you move on will
save you time.
</details>

<details><summary>Hint 3 — a correct signature check still trusts something</summary>

If tampering a payload without recomputing the signature fails, and skipping the signature
entirely also fails, then the signature really is being checked, every time, against something
real. The only way to produce a *new*, valid signature is to know what that something is.
</details>

<details><summary>Hint 4 — you don't need the server for this part</summary>

HMAC-SHA256 is math you can run entirely on your own machine: sign `header.payload` with each
candidate key from the wordlist, compare the result to the third segment of your real token.
No requests to the app required until you already know the answer. Python's `hmac` and
`hashlib` modules are all you need.
</details>

<details><summary>Hint 5 — once you have the key, you have the whole thing</summary>

A recovered signing key doesn't just let you validate old tokens — it lets you *produce* new
ones. Build a fresh header and payload with whatever claims you want, sign that exact string
with the key you found, and present the result like any other token.
</details>

---

## Reporting

Once solved:
- **Finding 1** — what's actually broken, one sentence, plus the recovered key as evidence
- **Finding 2** — the secondary claim-exposure finding from Objective 1, reported separately
- **WSTG ID** — WSTG-SESS-10 (printed on the mission card at Command)
- **Impact** — what an attacker can do once a signing key this weak is recovered, and how that
  differs from Operation 04's impact even though both reach the same category of outcome
- **Fix** — how you'd remediate each finding

Good luck, operator. Command is waiting. 🎭
