# KrishiVault plan details

The parts of the plan that `HANDOFF.md` only summarizes. Read `HANDOFF.md` first.

## 1. How the storage engine decides

Code: `krishivault-pipeline/src/engine/storage_plan.py`, costs in `src/engine/facts.py`.

**Inputs:** how much potato (maunds, 84 kg sacks or kg), the price offered today, the month, whether the potatoes are already in cold storage, any cash needed and by when, the farmer's own cost per kg (optional), and the costs below.

**Costs per sack (editable):**

| Cost | Default | Source |
|---|---|---|
| Rent for the season (up to 9 months) | ৳250 | Field notes |
| Sack size | 84 kg | Field notes |
| Empty sack, carrying to the cold storage, loading and unloading | ৳40 + ৳25 + ৳15 | Assumption |
| Selling from the store / selling at the field | ৳30 / ৳10 | Assumption |
| Weight loss in cold storage | 0.5% a month, plus 2% sorted out as rotten at exit | Assumption |
| Home store | 4% loss a month, at most 3 months | Assumption (field notes: about 3 months) |
| Cold-storage advance | ৳250 a sack at 14% a year | Field notes (৳200-300); rate assumed |
| Bank loan | up to 60% of a careful value, 11% a year | Assumption; set by the bank |

**For every month from today to December** (when the cold storages empty), and for each of 2,000 simulated price paths, it works out the money left in the farmer's hand: kilos left after weight loss × the price that month − rent − sacks, carrying and selling − loan interest.

- **Rent is flat**, so storing is a big fixed cost: the engine shows the **price needed** ("pays above ৳X/kg") for every month. Selling stored potatoes after 1 or 2 months usually loses money.
- If the potatoes are **already in cold storage**, the rent is owed either way, so holding on costs only weight loss and interest.
- **Cash needed soon:** storing means borrowing against the stored sacks (the cheaper of the cold-storage advance and a bank loan that covers it), or selling part now.

**The three options and the rule:**

| Recommendation | When |
|---|---|
| **Sell now** | Storing to the best month adds less than ৳500 or 3% on average, or beats selling now in fewer than 55 of 100 paths, or no loan can cover the cash need and selling part does not help |
| **Store, sell in month X** | Storing beats selling now in at least 80 of 100 paths and the bad case (1 in 10) loses at most 5% |
| **Sell part, store the rest** | In between. It sells enough sacks for the cash need, and at least a safety share (25%, 40% or 50% as the chance of gain falls) |

## 2. How the forecasts work

**Production** (`src/models/production_forecast.py`): a straight-line trend through the logarithm of BBS production, 2012-13 to 2024-25 (about 1.8% growth a year nationally). The range comes from how far real seasons fell from the trend (±3.6% a year nationally, wider for single districts). If DAE's planted area is known, area × the yield trend replaces the trend. The **crop gap** (production against the trend) is what drives prices.

**Price** (`src/models/price_outlook.py`):
1. The usual shape of the year: cheapest in February-March, dearest in November-December (March to December ×1.9).
2. Each season's "rise strength" (1 = the usual rise, 0 = flat) is measured from WFP prices: 2023-24 (crop 1% below trend) 0.93; 2024-25 (6% above trend) 0.0. A straight line through these two gives the rise for any crop gap: 0.77 for a trend-size crop, falling by 1.3 for every 10% bigger crop.
3. Once three months of the current season are known, their own rise is blended in.
4. 2,000 paths: each draws its own rise (crop uncertainty) and a monthly wander of about 6%. The outlook gives the middle and the 8-in-10 range.
5. The farmer's own price today anchors the path. Retail and farm-gate prices are assumed to move together (a conservative assumption; farm-gate prices usually swing more).

**Backtest** (`src/models/backtest.py`, the Forecasts page, `/api/forecast/backtest`): each past season is replayed from its first month with prices, with a model fitted on the other seasons only and the crop estimated from its planted area, against "usual seasonal shape only" and "no change". Scores: average miss, how often the real price fell inside the 8-in-10 range, and whether "store until the best month" or "sell now" was right for one sack. A slope check shows how much the calls depend on the assumed crop-size link. With a long history, `only_past=True` predicts each season from earlier seasons only.

**Honest limits** (also on the dashboard): two full price seasons, backtested on 12 months only; no weather in production; retail prices. Adding a longer price history refits it automatically (`data/raw/price_history.csv`).

## 3. Demo story (5 minutes)

| Step | Screen | What the judges see |
|---|---|---|
| 1. The trap | Dashboard → Season overview, season "Replay March 2025" | A fair replay: only what was known in March 2025. A big crop (about 7% above trend at the harvest); the outlook stays flat, and so did the real prices (dark squares); storing 36 sacks loses money in every month: "sell now". What really happened: storing would have lost about ৳11,000 to ৳20,000 |
| 2. A normal year | Season "Replay March 2024" | A fair replay with no earlier price season to learn from: "sell 9 sacks now, store 27 until December"; selling after one month still loses (flat rent). Prices really nearly doubled; the advice brought about ৳22,000 more than selling everything at the harvest |
| 3. The farmer's call | `/call`, season "Next harvest", the first "Try" sentence | Dialect speech understood, numbers read back, "sell 19 sacks now, store 17 until December", the money and the risk; press 2: cold-storage request; SMS receipt |
| 4. The bank | Dashboard → Bank loan, then Partner screens | The cold storage confirms 36 sacks; the bank sees the value, the careful price, the risk and approves (demo) |
| 5. Group and export | Group storage, Export | A shared truck saves money now; the discount counts only when the cold storage agrees. The UAE quotes most, Singapore pays most after costs |
| 6. Profit | Profit calculator | One bigha: cost ৳15.59/kg; storing part added about ৳10,400 against selling everything at harvest |

## 4. What partners see

- **Cold storage:** space requests (with the advice behind them), receipts to confirm for banks, group offers to agree.
- **Bank or microfinance lender:** loan applications with the crop, value today, careful price, what the cold storage is owed first, the most it can lend, the repayment risk and the repayment plan; approve or decline.
- **Buyer:** lots with quantity and today's price; offers go back to the farmer, ranked by money in hand.
- **Exporter:** sourcing districts and market margins after costs (the Export page).
- **KrishiVault helper:** callback requests with what the call already collected.

Phone numbers are masked on every partner screen.

## 5. Rules for every call

- One question per call, 60 to 90 seconds; numbers in maunds, sacks and taka.
- Keypad first, speech second; every number read back for a keypad "yes".
- Every answer ends with "১ = আবার শুনুন, ০ = মূল মেনু, ৯ = সহকারী".
- Never ask what a cold storage, bank or buyer can record instead.
- The farmer pays nothing: missed call, then we call back (when there is a phone line).
- The answer always says it is an estimate, never a promise.

## 6. The phone line (after the prototype)

There is no phone line in the prototype; the call preview runs the same steps in the browser.

**Options:** a licensed Bangladeshi IP-telephony 096 number over a SIP trunk into our own Asterisk server (production); Twilio Media Streams (testing only, about 13 times Awaj's cost); or a hybrid where an Awaj broadcast call ends with "press 1 to talk to KrishiVault". **Do not use** a GSM gateway with a GP or Teletalk SIM (treated as illegal VoIP, blocked by operators).

**The listening steps:** phone → SIP trunk → Asterisk → live audio and keypad → turn detection → Google bn-BD speech to text (Whisper tested on the same audio) → Bangla parser, then Gemini with fixed fields → the call steps (`src/voice/conversation.py`) → the engine → Bangla template → number lock → Google Bangla voice. About 2 to 4 seconds a turn.

**Security before a trunk:** firewall the SIP and audio ports to the provider; fail2ban; strong credentials; a daily outbound-minutes cap.

## 7. Risks, and how we answer them

| Risk | Answer |
|---|---|
| A wrong "store" call costs a farmer money | Ranges, the bad case shown, "sell part" when unsure; the engine never says "store everything" when the chance of gain is low |
| Cold storages gain from early sales and may resist | They gain filled space from group bookings and loan customers from verified receipts; fees only per booking |
| Banks will not lend against potatoes | Start with one lender and small loans; careful values; the cold storage confirms the sacks and is paid first |
| Too little price data | Say so; get the DAM history (to-do 4); the model refits |
| Farmers do not trust a machine | Numbers read back, a helper one keypress away, SMS receipts, results compared with neighbours in the pilot |
| Export claims look inflated | Every market shown after costs; demo figures labelled until real quotes |

**Go or no-go after the pilot harvest:** net price received against the haat and neighbours, months stored against advice, loans used instead of early sales and repaid, discounts agreed. If the money does not move, change the actions offered.

## 8. How the plan covers the judging criteria

| Criterion | Where we win it |
|---|---|
| Clarity | One question: "store or sell, and until when?" |
| Problem depth | The flat-rent trap, the big-crop years (BBS and WFP data), traders' cash and information advantage, from field notes |
| Differentiation | Not information alone: a decision in taka with its risk, plus the action (booking, loan, group, buyer) |
| AI rationale | Statistics and simulation where the future is uncertain; exact sums where money is; the number lock |
| Feasibility and scale | Working prototype on real national data; 64 districts covered; partners paid only when they gain |
| Impact | Farmers keep more of the post-harvest price rise; fewer forced sales; less storage waste |
| Q&A | `HANDOFF.md`, section 11 |
