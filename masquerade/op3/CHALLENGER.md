# 🎭 Masquerade Operation 03 — One Click

**Attacker:** Ying &nbsp;⚔&nbsp; **Defender:** Melusi
**WSTG:** WSTG-SESS-05 — Testing for Cross Site Request Forgery
**Target:** `http://localhost:8000/masquerade/op3/` (unlocks after Operation 02 is cleared)

**No solutions below.** Read [`DEBRIEF.md`](DEBRIEF.md) only once you're stuck, want to check
your work, or want the lesson spelled out after solving.

---

## Mission

**Coastline Ops** runs an internal ticket system for resort staff — maintenance requests,
Wi-Fi complaints, the usual. You have a real, working staff account, given to you directly
below. This mission isn't about that account at all. It's about a much more senior one.

**D. Cho**, the helpdesk administrator, keeps the ticket system open in a browser tab all
shift. D. Cho's password is real, and you are never shown it, and you never will be — not by
this mission's design, but because there's genuinely no way to learn it by looking. The only
way in is getting D. Cho's own browser to change it for you, without D. Cho ever meaning to.

> **Can you make someone else's browser do something they never clicked "submit" on?**

### What you're given

```
Your Staff ID: support.agent
Your Password: Ticket2024!
```

That's a real, working login — but it's not how you win this one. It's there so you can
confirm what normal, honest use of the ticket system looks like.

### Objectives

1. **Sign in as yourself.** Confirm the ticket queue works exactly as expected. Nothing here
   is broken — that matters for your report later.
2. **Find the password-change request.** Somewhere in this app, a logged-in user can change
   their own password. Work out exactly what that request looks like: the URL, the method,
   every field it sends.
3. **Ask yourself what that request actually proves.** What does the server check, beyond
   "is someone logged in"? Is there anything in that request that *only* a real user,
   intentionally filling out a real form, could have produced?
4. **Build a page that fires that request by itself.** Not a page the admin has to fill
   anything out on — one that submits itself, the instant it loads, with values *you* chose.
5. **Deliver it.** The portal has a second panel: *"PoC Lab — Host a Malicious Page."* Hand
   your page to D. Cho there and see what happens.
6. **Walk in the front door.** If your page worked, you now know a password for a real
   account you were never given credentials for. Use it.

---

## Rules of Engagement

Attack it however you'd attack a real target: Burp Suite, browser DevTools, `curl`, Python
`requests`, or by hand-writing the HTML yourself. The PoC Lab panel parses whatever HTML you
give it exactly like a browser would — it does not execute anything, and it does not accept
shortcuts. A page that would not actually work against a real browser will not work here
either.

Don't skip to reading `app.py`. Everything you need is visible from the request itself — this
is exactly the kind of finding you're meant to spot by *reading a request*, not by reading
source.

---

## 💡 Hints (progressive — open only if stuck)

<details><summary>Hint 1 — find the request first</summary>

Sign in as yourself and look for anywhere the app lets a logged-in user change their password.
Capture that exact request in Burp or DevTools — method, full URL (including any query
string), and every field in the body.
</details>

<details><summary>Hint 2 — ask what's missing, not what's there</summary>

Compare that request against your course notes' checklist. Is there a token anywhere in it —
a hidden field with a long random value that isn't one of the password fields? If you don't
see one, that's not you missing something. Keep looking at the *response* to the page, too —
does anything there change per visit, the way a real anti-CSRF token would?
</details>

<details><summary>Hint 3 — a link only gets you one click</summary>

A victim who's genuinely being attacked doesn't fill out your form for you. They click a link,
your page loads, and that's the only interaction they ever give you. Your PoC needs a hidden
form with the exact fields the real request needs, and something that submits that form
automatically the moment the page finishes loading — no button, no second click.
</details>

<details><summary>Hint 4 — match the request exactly</summary>

The PoC Lab reads your HTML the way a real browser would before submitting it: it checks the
form's `action` and `method`, and the name/value of every field inside it. If any of those
don't match what the real request actually needs, nothing happens — same as a real forged
request that's missing a required field. Read your captured request from Hint 1 again,
carefully.
</details>

<details><summary>Hint 5 — the payoff isn't visible on the page you build</summary>

Delivering the page won't show you D. Cho's new password on screen — you already know it,
because you're the one who put it in the form. The proof is somewhere else entirely: try
signing in.
</details>

---

## Reporting

Once solved:
- **Finding** — what's actually broken, one sentence
- **Evidence** — the exact PoC HTML that worked, and the request it forged (method, URL,
  fields)
- **WSTG ID** — WSTG-SESS-05 (printed on the mission card at Command)
- **Impact** — what an attacker gains by getting a privileged user's browser to fire one
  specific request, and what that user had to do to make it happen
- **Fix** — how you'd remediate it

Good luck, operator. Command is waiting. 🎭
