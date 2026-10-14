# KrishiVault handoff (14 October 2026, new plan)

The project's main plan document: start here in every session. Details that support it are in `PLAN_DETAILS.md`, the data in `DATA_SOURCES.md`, the screens in `SCREENS.md`.

**The plan changed on 14 October 2026.** KrishiVault no longer tries to cover everything (fertilizer, seed and machinery marketplace, weather alerts). It now focuses on one sector: **potato after the harvest: when and how much to sell, cold storage, loans against stored potatoes, buyers, export and group storage.** The earlier four-pillar plan is in the git history (commit `cd84b32`).

## 1. What KrishiVault is

**Goal:** Bangladeshi farmers earn more from their harvest through better predictions, smarter storage decisions, easier financing and better market access.

> আলু রাখবেন না বেচবেন, কবে বেচবেন: হিসাব করে বলে কৃষিভল্ট।
> Store or sell, and until when: KrishiVault does the sums.

**Hero crop:** potato in Bogura (10% of Bangladesh's potato, BBS 2024-25). Onion is the natural second crop. The production data already covers all 64 districts.

## 2. The problem, from the field

From the team's notes on how potato and onion storage works in Bangladesh:

- **The cold-storage sack is 84 kg. The rent is about ৳250 a sack for the season, up to 9 months.** Whether the sack stays 1, 2, 3 or 9 months, the rent is the same.
- A cold storage holds from 50,000 to 2 or 2.5 lakh sacks.
- **Cold storages lend farmers ৳200 to ৳300 a sack**; the stored sacks are the security if the money is not repaid on time.
- At home, a farmer can keep potatoes for up to about 3 months (onion 2 to 3 months).
- **Some years the crop is big, some years small.** A big crop means low prices; a small crop means high prices.
- **Farmers who store tend to sell within 1 to 3 months**, afraid the price will fall further. They have paid the full rent, but prices have not risen yet. The cold storage empties early and fills again with a new crop: **in a big-crop year the cold storage gains and the farmer loses**, because the farmer cannot decide well.
- Farmers sell in two ways: **retail** (shops and people they know in the village, upazila or district) and at the **haat**, where traders buy in bulk.
- **Traders are not farmers.** They buy at the haat, store in cold storages, and release potatoes across the country when prices rise. They have the money for storage and the information about the profit; farmers do not. **Farmers mostly store only seed potato.**

The data agrees. BBS production was 6-7% above its trend in 2016-17 and 2024-25; after 2024-25, WFP market prices stayed flat for the whole year. After the near-trend 2023-24 crop, prices almost doubled from February to November 2024.

## 3. The solution: seven parts

| # | Part | What it does | In the prototype |
|---|---|---|---|
| 1 | **Production and price prediction** | Predicts the season's potato production (history, area, weather) and the price 1 to 9 months after the harvest, with a range, by region | Built: production trend forecast (BBS, 13 seasons, all districts) with a range; price outlook driven by crop size and corrected by the season's own prices, 2,000 simulated paths; regional price levels (WFP). Weather not in yet |
| 2 | **Storage and selling-time engine** | Compares selling now with storing 1 to 9 months after rent, transport, loan interest and weight loss; recommends **Sell now**, **Store longer** or **Sell part, store the rest** | Built and tested: flat ৳250 rent, 84 kg sacks, losses, handling, loans; chance that storing beats selling now; the price at which storing pays |
| 3 | **Market access** | Market prices, demand, forecasts; risks of storing; buyers and offers compared; direct links to wholesalers, retailers, processors | Built: offers ranked by money in the farmer's hand (transport, grading losses, wait for payment); buyers are demo |
| 4 | **Crop-backed financing through banks** | Verifies stored quantity and receipts, values the crop, works out repayment risk, sends the loan application; the bank decides. KrishiVault does not lend | Built: receipt check by the cold storage, careful valuation, cold storage paid first, risk from the price paths, lender comparison, bank screen; banks are demo |
| 5 | **Export market intelligence** | Where to buy (big crop, low price) and which markets pay **after** every cost | Built: sourcing from real BBS and WFP data; markets after sorting, truck, port papers, freight, insurance, duty, rejects; foreign prices and costs are demo figures |
| 6 | **Group storage** | Neighbours combine sacks for a volume discount and shared transport | Built: groups, discount tiers that count only after the cold storage agrees, shared truck saving, join from a call or the dashboard; groups are demo |
| 7 | **Profit calculator** | Every cost, every sale, profit per kg, per sack, per maund and per harvest; actual against "sold everything at harvest" | Built: example bigha in Bogura, editable |

## 4. How people use it

**Farmers (button phones):** a voice call with keypad or speech, and an SMS receipt. The menu:

```
১ — আলু রাখবেন না বেচবেন: পরামর্শ        (store or sell advice)
২ — দামের পূর্বাভাস                        (price outlook)
৩ — একসাথে হিমাগারে রেখে খরচ কমান          (group storage)
৪ — হিমাগারের বস্তা জামানতে ব্যাংক ঋণ       (a loan against stored sacks)
৯ — আমাদের সহকারী ফোন করবেন                (a KrishiVault helper calls back)
```

Every number is read back for a keypad "yes"; every answer ends with "১ = আবার শুনুন, ০ = মূল মেনু, ৯ = সহকারী". **In the prototype there is no phone line**: the call is shown in the browser (`/call`, the call preview). **SMS can be sent** (REVE; dry run until switched on).

**Helpers and partners (web dashboard, `/`):** a KrishiVault helper or a farmer's family member can run the same engine with every cost visible. Cold storages, banks, buyers and exporters each have a screen; requests from calls appear there straight away.

## 5. Who gains, and the business model

| Stakeholder | What they gain | What they pay (to test in the pilot) |
|---|---|---|
| Farmers | Higher net income: no forced early sales, better buyers, cheaper storage, loans instead of selling at the bottom | Nothing |
| Banks and microfinance | Crop-backed loans with verified receipts, valuation and risk; new farm customers | A fee per verified, disbursed loan, or a data subscription |
| Cold storages | Group bookings that fill space early; receipt verification that brings loan customers | A fee per group booking |
| Buyers, processors, retailers | Sorted lots of known size and timing | A small fee per lot bought |
| Exporters | Sourcing regions and market margins after costs | A subscription for export intelligence |
| Government (DAM, DAE, Ministry of Commerce) | Production and price outlook, stored stock, early warning of gluts | A contract for the market-intelligence dashboard |

**Rule:** the farmer's advice is never for sale. A partner's fee never changes what KrishiVault advises; offers are ranked by money in the farmer's hand. KrishiVault is the data and connection platform; it does not lend its own money.

**Why it holds up:** one season's gain is large next to the fees. 36 sacks stored to December in a normal-crop year (the 2024 replay) earn about ৳29,000 more than selling at harvest; in a big-crop year (the 2025 replay) the engine's "sell now" avoids a loss of about ৳14,000.

## 6. AI and technology, and why

**"AI where uncertainty and language live; fixed rules where money lives."**

| Where | Method | Guardrail |
|---|---|---|
| Production forecast | Trend of BBS production per district and nationally; planted area when known; weather adjustment by hand for now | A range from past errors; known seasons use BBS figures |
| Price outlook | Usual seasonal shape × "rise strength" set by crop size (fitted on WFP 2024 and 2025 seasons), corrected by the season's own prices; 2,000 simulated paths | Ranges, not a single number; limits stated on every screen; frozen market reports dropped |
| Storage engine | Exact taka sums for every month and every path | Deterministic, explainable; costs editable |
| Loan risk | Chance the crop is worth less than the loan, from the same paths | The bank decides |
| Understanding the farmer | Bangla number parser (digits, words, মণ, বস্তা, northern dialect); Gemini only for what the parser cannot place | Every Gemini number must have been said |
| Wording | Gemini may reword the Bangla answer | **Number lock**: no number may change; otherwise the template is used |
| Voice | Browser speech recognition (prototype); Google Bangla voice | Keypad always works; numbers read back |

## 7. Execution and scale

| Stage | Scope |
|---|---|
| Prototype (now) | Section 8 |
| Pilot, one season (harvest March 2027) | 150 to 300 potato farmers in Bogura (Shibganj, Sariakandi), one cold storage, one bank or microfinance lender, one buyer, one exporter |
| District and country | All Bogura upazilas; then Rangpur, Dinajpur, Joypurhat, Munshiganj, Rajshahi (the six largest potato districts make up 61% of the crop); onion next |

**Measure in the pilot:** price received against the haat price and neighbours; months stored; rent paid per kg sold; loans taken instead of early sales and their repayment; group discounts actually agreed; forecast error against what happened.

## 8. The prototype (what we show)

| Part | Status | How to see it |
|---|---|---|
| Dashboard (`/`) | Built | Season overview, store or sell, forecasts, buyers, bank loan, group storage, export, profit calculator, partner screens (`docs/SCREENS.md`) |
| Call preview (`/call`) | Built | Keypad or speech in the browser; the same engine; requests reach the partner screens |
| SMS receipt | Ported to Python; dry run | "SMS me" on `/call` and "Send this advice by SMS" on the dashboard |
| Phone calls | Not in the prototype | No phone line; the Awaj port stays in `src/notify/awaj.py` for later |

**The season selector** replays real seasons: **March 2025** (big crop: the engine says sell now), **March 2024** (normal crop: store until December), plus **March 2027** (the next harvest, forecast) and **October 2026** (potatoes already in store).

**The demo moment:** a teammate calls as a farmer ("হামার ৮০ মণ আলু উঠছে, ফড়িয়া ১৬ টেকা দিবার চায়, ২৫ হাজার টেকা নাগবে ৪ দিনের মইধ্যে"), hears "sell 19 sacks now, store 17 until December" with the money and the risk, presses 2 for a cold-storage request, gets the SMS; the cold storage confirms the sacks on its screen and the bank sees a loan application with its risk.

## 9. What is real and what is not

**Real now:**
- BBS potato production for 64 districts, 2012-13 to 2024-25, and the production forecast built on it.
- WFP retail potato prices, February 2024 to July 2026 (19 usable months), and the price outlook fitted on them.
- The storage engine, market comparison, loan valuation, group storage, export cost build-up and profit calculator: all built and tested (`tests/`, 112 tests).
- The call preview with the Bangla number reader and the number lock; the SMS client (dry run).

**Not yet, or demo:**
- **The price outlook rests on two full seasons.** It is a careful statistical scenario, not a trained AI forecast. Say "statistical outlook with ranges".
- **No backtest** yet: needs the DAM price history (the DAM site moved; the downloader is broken).
- **Weather is not in the production forecast** yet.
- **Farm-gate prices:** the outlook moves the farmer's own price by the retail change; real farm-gate history is needed.
- **Costs and losses** other than the field notes (sack, carrying, selling, weight loss, interest rates) are assumptions to check.
- **All partners are demo:** cold storages, banks, buyers, exporters, groups. Export prices, freight and duties are demo figures.
- **Gemini and the Google voice** switch on with their keys but have not been tried with real keys in the call preview. Speech recognition has not been tried with a Bogura speaker.
- **No live SMS from KrishiVault's own code yet** (REVE worked from Mati Kohon on 8 October). From this cloud machine the REVE gateway did not answer; try from a laptop first.
- **No phone line.**

## 10. Prototype to-do, in order

1. **Rebuild around the new plan.** **Done, 14 October**: engine, forecasts, dashboard, call preview, docs.
2. **First live SMS**, only with the user's go-ahead: keys in the environment (`docs/CLOUD_SETUP.md`), `SMS_LIVE=1` for that one send, to a team member's phone.
3. **Field check in Bogura** (5 farmers, 2 cold storages): sack size and rent this season (some charge by kg), the cold-storage advance and its interest, weight loss, carrying and selling costs, when farmers sell and why. Replace the assumptions in `src/engine/facts.py`.
4. **Price history:** get DAM (or FAO GIEWS) monthly potato prices for 2010-2026, wholesale and retail, into `data/raw/price_history.csv` (`date, admin2, market, price`); the outlook refits itself. Then backtest it against "usual seasonal shape only".
5. **Weather in the production forecast:** NASA POWER season weather per district for 2012-2025 (Mati Kohon has the fetcher).
6. **Real partners:** one cold storage (group rate, receipt confirmation), one bank or microfinance lender (loan terms for stored potato), one buyer and one exporter. Replace the demo entries in `data/demo/demo_partners.json`.
7. **Export quotes:** real destination prices, freight and duties (Export Promotion Bureau, exporters, shipping lines).
8. **Gemini and the Google voice** with real keys in the call preview; test speech with a Bogura speaker.
9. **Update the pitch deck** (`krishivault-pitch-deck.html`) and the farmer interview guide to the new plan; both still describe the old four pillars.
10. **Onion** as the second crop (home storage 2 to 3 months, different season).

## 11. Prepared Q&A

| Question | Short answer |
|---|---|
| Can you really predict potato prices? | Not exactly, and we never say so. We give a range from 2,000 simulated paths, driven by the crop size; the engine recommends selling part when the range is wide. |
| What if the forecast is wrong? | Sell part, store part. The engine shows the bad case (1 in 10) and how likely storing is to beat selling now. |
| Why would cold storages join, when early sales let them re-let space? | Group bookings fill their space at the start of the season; verified receipts bring them loan customers; fees are paid only per booking. |
| Why would banks lend? | The potatoes are in a cold storage that confirms the sacks; the value is careful (the low price, not the middle); rent and the storage's own advance come off first; the risk is measured. |
| Isn't this just information? | Every answer ends with an action: a cold-storage request, a group join, a loan application, a lot sent to buyers. |
| Who pays? | Banks, cold storages, buyers, exporters and government, only when they gain. The farmer pays nothing. |
| Won't fees bias the advice? | No paid placement: offers are ranked by the money left to the farmer. |
| Why button phones and voice? | Most farmers who sell early have button phones and little reading time; the keypad always works. |
| Is the data real? | Production (BBS) and prices (WFP) are real; partners and export prices are demo, and every screen says so. |
| Why potato? | The biggest stored crop, with the clearest storage trap; the same engine fits onion. |
