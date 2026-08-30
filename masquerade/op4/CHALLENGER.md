# 🎭 Masquerade Operation 04 — Signed, Not Sealed

**Attacker:** Kali &nbsp;⚔&nbsp; **Defender:** Echo
**WSTG:** WSTG-SESS-10 — Testing JSON Web Tokens
**Target:** `http://localhost:8000/masquerade/op4/` (unlocks after Operation 03 is cleared)

**No solutions below.** Read [`DEBRIEF.md`](DEBRIEF.md) only once you're stuck, want to check
your work, or want the lesson spelled out after solving.

---

## Mission

**Chalet Concierge** is the Alpine retreat's internal access system, and it works
differently from every mission before this one: there's no session cookie at all. You sign
in once, the server hands you a token, and from then on *you* carry that token yourself —
in an `Authorization: Bearer` header — on every request. The server never looks anything
up. It just checks the token.

Every other mission in this campaign has asked you to steal, plant, or forge a *reference*
to something the server was tracking. This one is different, and it's worth sitting with
that difference before you start:

> **What if you didn't need a session at all — what if you could just write your own?**

### What you're given

```
Your Member ID: retreat.member
Your Password:  Chalet2024!
```

That's a real, working login. It gets you a real token with real, correctly-checked access
— which is exactly why it's worth using first.

### Objectives

1. **Sign in and get your token.** Don't just glance at it — decode it. Every part of a JWT
   except the final segment is just base64url. Read what's actually inside yours.
2. **Present that real token to The Director's Ledger** — either with `curl`/Burp against
   `/masquerade/op4/ledger` (`Authorization: Bearer <token>`), or by pasting it into the
   in-page panel. Confirm what a completely honest, unmodified request gets you.
3. **Ask what's actually protecting that third segment.** The header names an algorithm.
   Nothing about the token *forces* the server to use it — that's just what the token
   claims about itself. What happens if you claim something else?
4. **Build a token where you control every field, including whether it gets checked at
   all.** You don't have the signing key. You were never going to get it by guessing.
5. **Reach The Director's Ledger as the Director** — a role you were never granted, using
   a signature that was never computed.

---

## Rules of Engagement

Attack it however you'd attack a real target — `curl`, Burp, Postman, Python `requests`,
or jwt.io for the decode/encode busywork. There is no HTML form that can forge an
`Authorization` header for you (browsers don't let a plain `<form>` set custom headers) —
this one genuinely requires a real HTTP client, not just a browser tab. The in-page "present
a token" panel is there as a convenience so you can see the result rendered nicely, but it
runs through the exact same check as the real endpoint — it isn't a separate, easier path.

Don't skip to reading `app.py`. Everything you need is written in the token itself, in
plain text, the moment you decode it.

---

## 💡 Hints (progressive — open only if stuck)

<details><summary>Hint 1 — decode before you assume anything</summary>

Take your real token to jwt.io, or just base64url-decode the first two segments by hand
(`python3 -c "import base64,sys; print(base64.urlsafe_b64decode(sys.argv[1]+'=='))" <segment>`
works — note the two extra `=` for padding). The header is tiny. Read exactly what it says.
</details>

<details><summary>Hint 2 — the header is asking you to trust it</summary>

The header names the algorithm the *token* claims was used to sign it. That's not a neutral
fact stamped on by the server after checking something — it's just another field, exactly as
editable as the payload. Ask yourself: does the server independently know what algorithm to
expect, or does it read that from here?
</details>

<details><summary>Hint 3 — one specific algorithm value means "don't bother"</summary>

JWT's own spec defines an algorithm literally called "none" — meant for cases where a token
doesn't need integrity protection at all. A verifier that honors this value on a token that
absolutely does need protection has a bug, not a feature. What would a token look like if you
set the algorithm to that value yourself?
</details>

<details><summary>Hint 4 — the signature segment isn't optional, but it can be empty</summary>

A JWT is always three dot-separated segments, even when the third one is intentionally blank.
Don't drop the trailing dot — `header.payload.` is a complete, correctly-shaped token with an
empty signature. `header.payload` (two segments, no trailing dot) is just malformed.
</details>

<details><summary>Hint 5 — you already know what field name grants access</summary>

You decoded your own real token in Objective 1. One field in that payload is the one the
ledger actually checks. You're not guessing its name — you already have it written down.
</details>

---

## Reporting

Once solved:
- **Finding** — what's actually broken, one sentence
- **Evidence** — your forged token (all three segments), and the request/response proving it
  was accepted
- **WSTG ID** — WSTG-SESS-10 (printed on the mission card at Command)
- **Impact** — what an attacker can do without ever obtaining a valid credential, a signing
  key, or another user's session
- **Fix** — how you'd remediate it

Good luck, operator. Command is waiting. 🎭
