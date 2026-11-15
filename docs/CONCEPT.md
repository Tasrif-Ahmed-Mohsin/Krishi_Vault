# KrishiVault: the concept, brainstormed (15 November 2026)

What KrishiVault is really for, where the farmer still loses, what was built in this pass, and what to
build next, in order. Plain language; every figure from the engine or the data.

## 1. The concept in one line

> **KrishiVault gives a potato farmer the right to wait.**
> The sums say whether waiting pays; the cold storage's receipt and a bank give the cash to wait;
> the alerts say when to stop waiting.

"Store or sell, and until when" is the question the farmer asks. The answer only helps if the farmer
can afford to follow it and keeps following it for nine months. So the product is not a forecast: it is
**a decision, the cash to act on it, and a promise to keep**.

## 2. The jobs the farmer hires KrishiVault for

| Job | When | What stops him today |
|---|---|---|
| **Cash now without selling at the harvest low** | February to April | Debts and the trader's advance (dadon) fall due the week he harvests |
| **Know whether waiting pays, and how long** | At the harvest | Some years prices double, some years they never rise; nobody tells him which year it is |
| **Keep waiting when the fear comes** | April to July | Flat rent is already paid; a falling price and village talk make him sell after 1-3 months |
| **A fair price when he sells** | Any time | The trader knows the market; he knows the haat |

## 3. Why he loses money, and what answers each cause

| Root cause | Already in KrishiVault | New in this pass | Next (section 5) |
|---|---|---|---|
| **The cash trap**: debts and dadon due at harvest | Bank loan against the digital receipt; cold-storage advance | **What the trader's advance really costs** | Cash within 48 hours of the receipt |
| **Fear and flat rent**: selling after 1-3 months | Price-window alerts | **The hold plan**: "do not sell before", and the price that makes an earlier sale pay | A monthly check-in call |
| **He cannot read the SMS** (the farmer in our field video) | Call preview; outbound "Call me" | **Price-window alerts by voice call** | Every SMS also as a call |
| **Information gap with traders** | Buyers ranked by money in hand | | Farm-gate price board from farmers' own reports |
| **The blind bet**: glut or normal year | Crop-size outlook; "sell now" in a glut; 50% loan cap | | Forward sale of part of the crop to a processor |
| **Trust**: why believe a phone line? | Fair replays; backtest; number lock | The whole loop in one click | Advice ledger: what happened after each advice |

## 4. Built in this pass

**What the trader's advance really costs (দাদনের আসল খরচ).** The dashboard's Bank loan page, and `POST /api/finance/dadon`.
Before the harvest a faria lends cash and is repaid in potatoes at harvest, below the market. No interest is
named, so the cost is invisible. Example: ৳20,000 for 3 months, repaid with 80 maunds at ৳14 when the market
pays ৳16, costs about **৳6,000: like 119% interest a year**. The same ৳20,000 from the demo bank against stored
sacks costs about **৳650**. This is pure arithmetic, so it is safe to say on stage. It turns the plan's first
ground-level challenge into one number the farmer can bargain with.

**The hold plan (ধরে রাখার পরিকল্পনা).** It's on the Store or sell page, sent as an SMS, given out with the
receipt in the one-click loop, and added as one line to the advice SMS. For the demo call it says: sell the 17
stored sacks in December; **not before July**, because April to June lose money on average (−৳11,980,
−৳7,700, −৳3,210). If cash forces an earlier sale, sell only above ৳22.2 a kg in July, ৳22.8 in September or
৳23.3 in November. These are the engine's own break-even prices, so the plan is the condition under which
storing paid, not a forecast. In a glut year there is no hold plan, because the advice is to sell now.

**Price-window alerts by voice.** It's on Partner screens → Field agent → "… or call them (voice)". It sends
the same words and numbers as the SMS, as an outbound call, within the same limits as "Call me" (allow-list,
daily cap, calls per address). The farmer in our own field video uses a button phone and cannot read an SMS.
Until now, every message after the call reached him only as text.

**Also:** `SMS_ALLOWED_NUMBERS` keeps live SMS to listed phones on a public server. The field agent's button
no longer says "dry run" when the SMS is live.

## 5. Next, in recommended order (not built)

1. **Every SMS also as a call.** The receipt, the hold plan and the loan decision should go out as calls,
   not only the alerts. It is the same code path, and the call line exists. This is cheap and matters most
   to the farmers who need KrishiVault most.
2. **The farm-gate price board ("অন্যরা কত পাচ্ছে").** The call already asks the price he is offered. With
   his consent (press 8), keep the offer by district and week, and show the median once 5 or more farmers
   have reported, the same rule as the government figures. In the call: "This week in Shibganj, farmers
   were offered ৳17-18". This closes the information gap with traders. It also builds the farm-gate price
   history the price model lacks (HANDOFF, section 10). It needs pilot farmers; until then it says "not
   enough reports".
3. **The advice ledger and a follow-up call.** Keep each advice (with consent) and, after the sale, ask what
   he got. This gives the pilot's north-star number (extra taka per stored sack against the haat). It
   calibrates the outlook on real farm-gate outcomes, and it becomes the trust story ("last season,
   farmers who followed the plan got …").
4. **A forward sale for part of the crop.** A processor commits to a December price for, say, a third of
   the stored sacks. This cuts the bad case, and a bank can lend more against a contracted lot. It needs
   one real processor. PRAN, ACI and Square are targets, not partners.
5. **Cash within 48 hours of the receipt.** It can start as a pre-approved limit per partner cold storage, so
   the bank decides fast enough to beat the trader's advance. This is a bank-partnership question more than
   code.
6. **Onion** as the second crop (home storage 2-3 months; a different season). The engine is the same; the
   facts and seasons are new.

**Not in the plan, so not proposed:** fertilizer and pesticide supply, the seed and machinery marketplace,
weather danger alerts, a phone-number ID with a PIN.

## 6. How to use this in the pitch

- **The problem in one number:** the dadon example ("119% a year, hidden in the price").
- **The behaviour change in one sentence:** "We don't just say store until December; we give him a plan he
  can keep: not before July, and the price that makes an earlier sale pay."
- **Inclusion:** "The farmer in our video can't read an SMS, so KrishiVault calls him."
