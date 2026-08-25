# 🎭 Masquerade Operation 01 — The Teller's Trust

**Attacker:** Iana &nbsp;⚔&nbsp; **Defender:** Alibi
**WSTG:** WSTG-SESS-01 — Testing for Session Management Schema
**Target:** `http://localhost:8000/masquerade/op1/` (always available — no other campaign progress required)

**No solutions below.** Read [`DEBRIEF.md`](DEBRIEF.md) only once you're stuck, want to check
your work, or want the lesson spelled out after solving.

---

## Mission

**Rainbow-Corp National Bank** runs an online customer portal. You have a real, working
customer account — given to you directly below, because this mission has nothing to do with
finding a password. Once you're logged in, the app trusts you for the rest of your visit using
a **session token**. Your job is to answer one question about that token, and then exploit the
answer:

> **Does the server actually verify what's inside the token, or does it just trust whatever the
> token claims?**

You are not trying to log in as someone else. You're trying to become someone *more* — without
ever presenting a credential for that identity at all.

### What you're given

```
Customer ID: j.doe
Password:    Customer2024!
```
That's a real, valid login. Use it normally first — you need an active session before there's
anything to analyze.

### Objectives

1. **Log in** and observe exactly what the server hands you afterward to prove who you are.
2. **Analyze that token's structure.** Is it plaintext? Encoded? Hashed? A mix? (Your course
   notes' own checklist — decode everything before assuming anything is "protected.")
3. **Identify what data lives inside it**, and which piece of that data is the one the app
   actually checks when deciding what you're allowed to do.
4. **Tamper with it** and replay it. If the server re-issues you the same trust without you ever
   authenticating as anything more privileged, you've found the bug.
5. Reach **Vault Operations** with elevated access.

---

## Rules of Engagement

Same as always — attack it however you'd attack a real target: Burp Suite, `curl`, browser
DevTools, CyberChef for quick decode/hash-identification, Python `requests`. This is a
whitebox-friendly mission in the sense that WSTG-SESS-01 testing is inherently about
*inspecting* what the app hands you — that's not cheating here, that's the actual test.

Don't skip to reading `app.py` — figure out the token's shape the way you'd have to against a
real target: by collecting it, decoding it, and testing what happens when you change it.

---

## 💡 Hints (progressive — open only if stuck)

<details><summary>Hint 1 — start with the token itself</summary>

After logging in, check what your browser is holding onto (DevTools → Application → Cookies,
or just read the `Set-Cookie` header in Burp/curl). You'll find one cookie that didn't exist
before you logged in. That's your target. Copy its value somewhere you can work with it.
</details>

<details><summary>Hint 2 — decode before you assume</summary>
Take the cookie value to CyberChef (or `base64 -d` on the command line). Does it come back as
readable text? Your course notes are explicit about this: encoding is not encryption, and the
first move is always to check whether a token is just obfuscated, not actually protected. Look
closely at the decoded structure — how many fields, separated by what?
</details>

<details><summary>Hint 3 — one of those fields is about you, specifically</summary>

One part of the decoded value describes *who you are logged in as* on the customer side. Your
"My Account" page and this token should visibly agree with each other. If you change that
field to something else and re-encode, log back in with the tampered cookie and see what the
app assumes about you — without you ever proving it.
</details>

<details><summary>Hint 4 — the app will tell you exactly what it wants, if you ask</summary>

Try reaching Vault Operations with your normal customer session first, before tampering
anything. Read the response closely — a well-written access-denied message often names the
*exact* requirement you're missing. That's not a hint you have to guess; it's one the app hands
you directly if you just try the thing that isn't allowed yet.
</details>

<details><summary>Hint 5 — does the third field actually matter?</summary>

If the token has more than two fields, ask what the extra one is *for*. It might look like an
integrity check (a hash, a signature-shaped string) — but looking like a check and *being* one
are different things. After you tamper the field from Hint 3, try replaying the token **without
recomputing** that extra field at all. See what happens.
</details>

---

## Reporting

Once solved:
- **Finding** — what's actually broken, one sentence
- **Evidence** — the exact before/after token values
- **WSTG ID** — WSTG-SESS-01 (printed on the mission card at Command)
- **Impact** — what an attacker gains, and from what starting position (zero valid privileged
  credentials)
- **Fix** — how you'd remediate it

Good luck, operator. Command is waiting. 🎭
