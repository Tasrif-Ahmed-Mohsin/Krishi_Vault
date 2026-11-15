# KrishiVault: product and engineering review (15 November 2026)

A review of the whole project as it stands after Round 2 selection: what was fixed in this pass, what to do
before the next round, and the questions the plan still has to answer. Written for the team; no computer
science needed.

## 1. Where KrishiVault stands

The idea is strong and the prototype is unusually honest: real BBS and WFP data, ranges instead of promises,
"sell now" in a glut year, a number lock on everything the farmer hears, and demo partners labelled as demo.
The weak points are not in the idea but in **running it live** (a public site that can ring real phones) and in
**a few plan figures judges will test** (section 4).

## 2. Fixed in this pass

| Problem | Why it mattered | What changed |
|---|---|---|
| Anyone on the public site could make the call line ring **any** Bangladeshi number and **say any text**, with any caller ID | Harassment or scam calls in KrishiVault's name, and a bill | The call now speaks only the engine's answer from that call, signed by the server like the SMS; the page can no longer send text, a caller ID or an audio file. Without an answer, a fixed welcome |
| The per-address call limit trusted the first `X-Forwarded-For` entry | Anyone could pretend to be a new address on every request | Only the address nginx adds (the last entry) counts, and only when the request really came through nginx |
| The call history showed full phone numbers to every visitor | Privacy; every other screen masks numbers | Numbers masked (`01712-XXX678`) |
| **The tests could place real calls.** A laptop `.env` with `VOICEBLAST_LIVE=1` made the call tests dial for real (7 failed attempts to the made-up test number on 15 November) | Real, billed calls from `pytest` | `tests/conftest.py` switches every live line off before the app loads; the call client re-reads its live switch on every use |
| The server runs **4 workers**, each with its own random signing key | Unless `KV_STATE_SECRET` was set, "SMS me" could fail on the live site (one worker signs the answer, another checks it); call limits were 4 times looser | One shared key kept in `data/runtime/state_secret`; the deployment runs 1 worker (plenty for a demo); `.env.example` lists the call limits |
| The pre-loaded demo call on `/call` was a frozen snapshot with an old signature | "SMS me" failed on it, and "Call me" could not read its advice | The page shows the snapshot at once, then gets the same answer freshly signed from the server (about 1 second) |
| The first answer after a restart waited **15.7 seconds** for Gemini (the full model timed out, then the lite one answered) | Silence on a phone call; a judge's first try is the slow one | Gemini gets at most 5 seconds, then the template answer is used (same numbers); the faster lite model is tried first |
| Price-window alerts promised money for the **weighed** kg, ignoring 8.65% storage loss | The SMS overstated the money by about 9% | The alert now counts the kg left after the months in store, the same as the sale |
| The three screens looked dated and different from each other; nine tabs wrapped onto two rows; long intros | First impressions for judges; "too cluttered, old-fashioned" (the team) | One clean, modern look from `static/kv.css`: a shared header that switches between Dashboard, Call and USSD, the pages on one row of tabs, rounded cards, big numbers, one-line intros |
| Old labels: "Today: October 2026", "phone calls are a preview only" | Wrong on 15 November, and calls can now be live | "In store: October 2026"; the footer and `/api/status` say what is really switched on |
| Two different `SaleIn` classes in `main.py` | A trap for the next change | Renamed `ProfitSaleIn` |

**New: the whole loop in one click** (Season overview → "Run the loop"). One demo farmer goes through the
plan's loop: harvest call → digital receipt → bank loan with the hold → price-window alert → the sale that pays
the cold storage, the bank, then the farmer, with the bad-case price beside it. The records appear on the
partner screens. In the 2025 glut replay it stops at step 1 with "sell now", which is the honest answer.
This replaces a dozen clicks across four screens in the demo, and it answers "does the loop really work?" in
one screen.

## 3. Before the next round (in order)

1. **Redeploy koryu.ninja** from this branch once merged, with `-w 1` (`docs/AZURE_VM_DEPLOYMENT.md`).
2. **Lock the call line** in the server's `.env`: `CALL_ALLOWED_NUMBERS=` the team's and judges' numbers,
   `CALL_DAILY_CAP=10`, and `SMS_ALLOWED_NUMBERS=` the same numbers (the site sends live SMS to any number typed on the dashboard otherwise). Check the VoiceBlast balance.
3. **Rehearse on the live site, not a laptop:** open `/call`, press "Call me" to a teammate's phone, and
   listen to the whole answer once (the reworded Bangla is checked for numbers, not meaning).
4. **Run the loop on the live site** and keep the Partner screens tab open for the Q&A.
5. **Do not run the app on a laptop with the live `.env`** unless you mean to: `SMS_LIVE=1` and
   `VOICEBLAST_LIVE=1` are on there. The tests are now safe; `uvicorn` is not.

## 4. What judges will push on, and what to answer

**a. "Your cold-storage fee is most of your revenue."** It is 56% in year 1 and 59% in year 3
(`/api/business/plan`: ৳9.6 of ৳17.24 lakh). Two checks before the pitch:
- The projection charges the 4% fee on **40 sacks per farmer**. The engine itself never stores the whole crop
  at harvest: in the demo call 17 of 36 sacks go in. If "40 sacks" means sacks harvested, the cold-storage
  line is roughly a third too high. Say which it is.
- Cold storages gain from early exits today (they re-let the space). Our answer is group bookings that fill
  them early and fees collected at the sale; one cold storage saying yes in Kahaloo is worth more than any slide.

**b. "70% margin in year 3?"** Year-3 running costs are ৳1.45 crore for 60,000 farmers and 100 cold storages:
about ৳240 a farmer a year, with field agents, onboarding and support. Most agri-services firms spend far more
on the ground. Either show the cost per farmer the pilot will measure, or present the margin as a range.

**c. "Can you predict prices?"** No, and the prototype says so: two seasons of WFP retail prices, backtested on
two seasons. The loop and the glut replay show the guardrail (sell 30-40% at harvest; "sell now" in a big-crop
year). The single most valuable data task is still the long DAM price history (HANDOFF to-do 4).

**d. "A bank lends against potatoes?"** The loop shows it at the bad-case price: the stored sacks still cover
the loan and the cold storage, and the farmer still gets something. Use that screen.

**e. "Will a farmer listen to a minute of advice?"** No longer asked of him. The store-or-sell answer was
about 110 words (around 50 seconds). It now leads with the decision, the cash in hand, the average gain over
selling everything now and the bad case (42 words in the demo call, about 20 seconds); **press 3** for the full
sums and the net profit. The bad case stays in the short answer: a range, never a promise. Try both versions
with the 5 farmers of the field check and keep the one they repeat back correctly.

## 5. What to measure in the pilot

One number to steer by: **extra taka per stored sack** compared with the haat price on the day the farmer
would have sold. Beside it: share of farmers who follow the split; loans taken instead of a harvest sale and
repaid; alerts acted on within a week; forecast error against what happened; farmers who agree to be counted.

## 6. Engineering notes for later

- Records are JSON files in `data/runtime/`: fine for one server and a demo. Before a pilot with real farmers,
  move them to the SQLite database already in `src/database.py`, with backups.
- Call limits live in the server's memory: correct with one worker; move them to the database if it ever
  runs more.
- `audioop` (used for the phone audio) is removed in Python 3.13; keep the server on 3.12 or use the
  built-in fallback already in `voiceblast.py`.
- The VoiceBlast client logs in to a web portal and reads its pages; if the portal changes, calls stop.
  Ask SysTech for an API key for the pilot.
