## 🎯 Operation 03 — Hard Breach

**Attacker:** Dokkaebi &nbsp;⚔&nbsp; **Defender:** Clash
**Target:** `http://localhost:8000/op3/` (unlocks after Op02)

### Mission

The web console is behind you — Rainbow-Corp also runs a **Perimeter Access Terminal**
(think: a physical door keypad) for the same confirmed operator, `g.mendel`. It's guarded by a
**4-digit access code** and, on every single attempt, a **math verification challenge** that
changes each time — not just the numbers, the *operation itself* varies too. There is **no
account lockout** — the challenge is the *only* thing standing between you and the door.

1. **Work out what the verification challenge actually is**, and whether a script can solve it
   — for *any* operation it might throw at you, not just one.
2. **Get your request shape right** — the challenge is single-use, so it has to be handled
   correctly on *every* attempt, not just once.
3. **Brute-force the access code.** It's a plain 4-digit number: `0000`–`9999` — 10,000
   possibilities, fully bounded, nothing to guess about the shape of it.
4. Reach the terminal console and capture the flag.

### Two things to test — this mission has two independent bypasses

- **Is the challenge actually hard?** Look at what it presents you with. If it's something a
  simple script can resolve on its own without any external help, solving it programmatically
  removes it as a control entirely — no different from it not being there.
- **Is the challenge actually *required*?** Don't just solve it — also test what happens if you
  simply don't send an answer at all. Many real implementations of "verify this value" logic
  have a bug lurking in how they handle a *missing* value, as opposed to a *wrong* one. Those
  are two different code paths, and it's worth checking both.

---

## 💡 Op03 Hints (progressive — open only if stuck)

<details><summary>Hint 1 — the challenge itself</summary>

View the terminal page's source. The "verification challenge" is plain arithmetic, rendered as
plaintext HTML (`4821 + 3912 = ?`, or `9924 - 3881 = ?`, or `5303 * 5070 = ?` — the numbers and
the operator both vary). There's no image, no distortion, nothing hidden — a script can read the
numbers *and the operator* straight out of the page and compute the answer itself, whichever of
the three shows up. Notice the operands are 4-digit numbers, not single digits — that makes the
challenge *look* more serious, but ask yourself honestly whether it changes anything for a
script versus a human trying to solve it in their head.
</details>

<details><summary>Hint 2 — don't hardcode the operator</summary>

If your script assumes every challenge is addition, it'll get roughly 2 in 3 wrong. Parse
whichever symbol is actually shown and act on it — don't just extract the two numbers and add.
</details>

<details><summary>Hint 3 — it's single-use</summary>

Solve one challenge and it won't work for your next attempt — a new one is generated after
every response, success or failure. So your automation can't solve once and replay; it has to
**fetch a fresh challenge immediately before every single submission.**
</details>

<details><summary>Hint 4 — the brute force itself</summary>

With the challenge handled, the access code is just `0000` through `9999` — generate all 10,000
and try each one. There's no lockout, so nothing stops a full sweep; a script that fetches a
challenge, solves it, and submits a candidate code in a loop will get there.
</details>

<details><summary>Hint 5 — the second bug (don't stop after the first solve)</summary>

Try a request that omits the challenge-answer field completely — not a wrong answer, no field
at all. Compare that response to one with a deliberately *wrong* answer. If they behave
differently, you've found a second, separate bypass — and it might mean you never needed to
solve any math in the first place.
</details>

---
