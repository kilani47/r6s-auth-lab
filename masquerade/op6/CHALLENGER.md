# 🎭 Masquerade Operation 06 — Delegated Trust

**Attacker:** Hibana &nbsp;⚔&nbsp; **Defender:** Bandit
**WSTG:** Testing OAuth 2.0 delegated authorization
**Target:** `http://localhost:8000/masquerade/op6/` (unlocks after Operation 05 is cleared)

**No solutions below.** Read [`DEBRIEF.md`](DEBRIEF.md) only once you're stuck, want to check
your work, or want the lesson spelled out after solving.

---

## Mission

**The Clubhouse** runs a member photo gallery. A separate terminal — **Print Kiosk** — wants
to fetch a member's photos and print them, so instead of members handing Print Kiosk their
password, The Clubhouse uses OAuth: a member approves a scoped, limited token, and Print
Kiosk never sees a credential at all. That's the entire point of delegated authorization —
and this mission is about three genuinely separate ways it can fail anyway.

This is a bigger mission than the ones before it — three independent findings, each one a
real vulnerability class on its own, each reachable without needing the others. Play them in
order the first time through; by the end you'll understand why a real assessment report would
list them as three separate bugs, not one.

### What you're given

```
Your Member ID: club.member
Your Password:  Clubhouse2024!
```

That's a real, working login. Use it to see the *honest* OAuth flow first — there's a link on
the mission page that walks you through it exactly as designed: sign in, approve a consent
screen, land back at Print Kiosk's real callback with a code. Nothing about that flow is
broken. Everything after it is.

---

## Objectives

### Stage 1 — Steal a code that was never meant for you

1. Look closely at the request your browser makes when you approve access in the honest flow.
   One of its parameters says where the resulting code should be sent.
2. Ask what happens if that destination isn't the real Print Kiosk callback at all.
3. The mission page has a way to send a link to **N. Kruger**, a club member who's always
   logged in. Use it — with a destination you control.
4. Check that destination. If a code shows up there, you've just proven an authorization code
   can be redirected anywhere an attacker points it.

### Stage 2 — Turn a stolen code into a real access token

5. A code by itself isn't a token. Exchanging one requires Print Kiosk's own credentials —
   `client_id` and `client_secret` — at the token endpoint.
6. You don't have that secret. But you have a candidate list the size of a normal password
   wordlist, and nothing about the token endpoint stops you from trying all of them.
7. Recover the real secret, and use it — with your Stage 1 code — to get a genuine, working
   access token back.

### Stage 3 — Reach the gallery on a token nobody gave you

8. Access tokens have a shape too. Look at one you've actually been issued. How large is the
   space of things it could have been?
9. That space might be smaller than you think — small enough to search directly, without
   touching Stage 1 or Stage 2 at all.
10. Reach the protected resource with a token you found this way, and notice what that
    means: this isn't a follow-up step to the first two findings. It's a completely separate
    door.

---

## Rules of Engagement

Attack it however you'd attack a real target — `curl`, Burp, Postman, Python `requests`. Stage
2 and Stage 3 both require scripting genuinely repeated requests; there's a single-guess
convenience form for each on the mission page so you can test your understanding, but neither
one is how you're meant to actually search a whole wordlist or a whole token space — that part
needs a real loop.

Don't skip to reading `app.py`. Every one of these three findings is visible from the outside:
by reading what a request actually contains, and by testing what the server actually checks.

---

## 💡 Hints (progressive — open only if stuck)

<details><summary>Hint 1 — Stage 1: read the honest flow's own request</summary>

Use the "Authorize Print Kiosk yourself" link, but before clicking Allow, look at the full URL
you were sent to. One query parameter names a callback address. Nothing about the consent
screen itself tells you whether that address is checked against anything — you have to test
that directly.
</details>

<details><summary>Hint 2 — Stage 1: you don't need your own account for this part</summary>

The lure doesn't use your session at all — it simulates a completely different member,
already logged in, encountering a link for the first time. Give it a `redirect_uri` you can
actually check afterward. The mission page tells you exactly which path that is.
</details>

<details><summary>Hint 3 — Stage 2: read the real token request's shape</summary>

Capture the POST your browser makes when you complete the honest flow's token exchange (or
just read the mission page's description of the endpoint). `grant_type`, `code`,
`redirect_uri`, `client_id`, `client_secret` — five fields, one of which you're missing, all
of which the endpoint expects every time.
</details>

<details><summary>Hint 4 — Stage 2: this needs a script, not the form</summary>

The "Exchange a Code" panel is for testing one guess. Real recovery means posting to
`/masquerade/op6/oauth/token` in a loop, once per line of
`wordlists/op6_client_secrets.txt`, and checking which response actually contains an
`access_token`.
</details>

<details><summary>Hint 5 — Stage 3: look at the shape of a token you already have</summary>

However you got your first real access token, look at it. It's short. It's numeric. Ask what
the entire space of possible values that shape represents — and whether anything stops you
from just trying all of them against the resource endpoint directly.
</details>

<details><summary>Hint 6 — Stage 3: this one doesn't need Stage 1 or 2 at all</summary>

If you're stuck thinking this stage requires a token *from* Stage 2, try skipping straight to
it: pick numbers in the range you identified in Hint 5 and send them to
`/masquerade/op6/photos/me?access_token=` directly, with no code and no secret involved
anywhere.
</details>

---

## Beyond these three — what else is worth checking

A full OAuth assessment covers more ground than any one lab can hands-on demonstrate. Once
you've cleared all three stages, it's worth going back and asking about a few properties of
this exact app that you can observe without any further exploitation, and writing them up
alongside your three main findings:

- Do authorization codes or access tokens ever expire? Try reusing an old one after a long
  wait.
- Is there any check that a code redeemed at the token endpoint was originally requested by
  the *same* client now presenting it?
- Is the OAuth flow itself protected against CSRF (a `state` parameter, checked on return)?
  You've seen this exact category of bug already, from a different angle, in an earlier
  mission this campaign.

None of these need a working exploit to report. Noticing and describing them accurately is
the job.

---

## Reporting

Once solved:
- **Finding 1** — the redirect_uri issue: root cause, PoC link, evidence of a captured code
- **Finding 2** — the weak client_secret: the recovered value, and the request that used it
- **Finding 3** — the weak access token: the token space, and evidence it's reachable
  independently of Findings 1–2
- **WSTG area** — OAuth 2.0 delegated authorization testing (printed on the mission card at
  Command)
- **Impact** — for each finding, what an attacker gains and what they needed to get there
- **Fix** — how you'd remediate each one

Good luck, operator. Command is waiting. 🎭
