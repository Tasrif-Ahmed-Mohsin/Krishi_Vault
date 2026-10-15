# KrishiVault handoff (15 October 2026, synced with the plan document)

The project's main plan document: start here in every session. Details that support it are in `PLAN_DETAILS.md`, the data in `DATA_SOURCES.md`, the screens in `SCREENS.md`.

**The team's plan document** is the Google Doc "Krishi Vault" (`https://docs.google.com/document/d/1C0Pk6GlYDNaAy5TH6EU6t3VfRdoLo2idiwT59-bgnck/edit`). It has the problem with a value-chain study's figures, how KrishiVault is different, the execution and feasibility plan for Round 2 of **Grameenphone FutureMakers**, the ground-level challenges, the money (start-up capital, income, a 3-year projection) and the seven parts in Bangla. On 15 October the repository was brought in line with it; section 13 lists what changed and what the team still has to decide. When the Google Doc changes, update this file first.

**The plan changed on 14 October 2026.** KrishiVault no longer tries to cover everything (fertilizer, seed and machinery marketplace, weather alerts). It focuses on one sector: **potato after the harvest: when and how much to sell, cold storage, loans against stored potatoes, buyers, export and group storage.** The earlier four-pillar plan is in the git history (commit `cd84b32`).

## 1. What KrishiVault is

**Goal:** Bangladeshi farmers earn more from their harvest through better predictions, smarter storage decisions, easier financing and better market access. The plan calls it a farm decision and profit-management service that helps the farmer:

| Step | What it means | Where in KrishiVault |
|---|---|---|
| **Know** | Market, buyer and storage conditions | Price and production outlook, buyers, cold-storage space |
| **Calculate** | Production cost, storage cost, weight loss and the expected net profit | Storage engine, profit calculator |
| **Decide** | Sell now, store, sell part, or sell or store with a group | The engine's three answers; group storage |
| **Act** | Book storage, reach buyers, get a crop-backed loan | Cold-storage request and receipt, buyer lot, loan application, group join |

> আলু রাখবেন না বেচবেন, কবে বেচবেন: হিসাব করে বলে কৃষিভল্ট।
> Store or sell, and until when: KrishiVault does the sums.

**The big idea (plan):** the biggest opportunity is not producing more potatoes; it is **capturing more of the value of the potatoes farmers already grow.**

**Hero crop:** potato in Bogura (10% of Bangladesh's potato, BBS 2024-25). Onion is the natural second crop; the plan adds maize later. The production data already covers all 64 districts.

## 2. The problem

**From the field (team notes, 14 October):**

- **The cold-storage sack is 84 kg. The rent is about ৳250 a sack for the season (some charge ৳300), up to 9 months.** Whether the sack stays 1, 2, 3 or 9 months, the rent is the same.
- A cold storage holds from 50,000 to 2 or 2.5 lakh sacks.
- **Cold storages lend farmers ৳200 to ৳300 a sack**; the stored sacks are the security if the money is not repaid on time.
- At home, a farmer can keep potatoes for up to about 3 months (onion 2 to 3 months).
- **Some years the crop is big, some years small.** A big crop means low prices; a small crop means high prices.
- **Farmers who store tend to sell within 1 to 3 months**, afraid the price will fall further. They have paid the full rent, but prices have not risen yet. The cold storage empties early and fills again with a new crop: **in a big-crop year the cold storage gains and the farmer loses**, because the farmer cannot decide well.
- Farmers sell in two ways: **retail** (shops and people they know in the village, upazila or district) and at the **haat**, where traders buy in bulk.
- **Traders are not farmers.** They buy at the haat, store in cold storages, and release potatoes across the country when prices rise. They have the money for storage and the information about the profit; farmers do not. **Farmers mostly store only seed potato.**

**From a value-chain study (as quoted in the plan document).** The study looked at Kahaloo (Bogura) and Munshiganj Sadar; the closest match is a BRAC University thesis with fieldwork in February to April 2016 (`DATA_SOURCES.md`). Only the 33.13% figure has been checked against its abstract. **The taka figures are about ten years old**: say the year when quoting them.

| What the study found | Figure |
|---|---|
| Share of the harvest farmers sell straight away | **64.07%** |
| Share farmers store for later sale | **13.60%** |
| Share of cold-stored potatoes bought by traders (beparis, wholesalers) | **97.6%** |
| Value added taken by wholesalers (the biggest share; farias 14.23%) | **33.13%** |
| Loss at the farm and in home stores | 16.60% |
| Weight lost in cold storage | **8.65%** (now the engine's default, section 7) |
| Harvest price, then off-season retail | ৳5.90-6.03 a kg, then ৳17.50-20.40 a kg (about 3 times) |
| Production cost; cultivation cost | ৳3.50-3.66 a kg; ৳1.23-1.29 lakh a hectare |
| Cold-storage charge; transport | ৳1.50 a kg (৳126 an 84 kg sack, then); about ৳6,000 a hectare |
| Cold storages in Bangladesh (then) | 320, about 2 million tonnes of space |
| Written cost records | Most farmers keep none; about 60% have secondary education or less |

**The chain the plan describes:** the farmer harvests → needs cash at once (input debts, often an advance from a trader, *dadon*) → sells at the harvest low → traders with capital store → prices rise in the off-season → the farmer misses the rise → with no cost records, the farmer cannot even see the loss.

**The data agrees, for recent seasons.** BBS production was 6-7% above its trend in 2016-17 and 2024-25; after 2024-25, WFP market prices stayed flat for the whole year. After the near-trend 2023-24 crop, prices almost doubled from February to November 2024. Bangladesh grew **11.6 million tonnes** of potato in 2024-25 (BBS); the plan's "8.6 million tons" is the 2012-13 figure.

**The core problem:** farmers lack market intelligence, a view of their net profit, and crop-backed cash, so they sell when they are desperate. A price alert alone does not help: the farmer still cannot wait, because an alert does not pay today's debt.

## 3. The solution: seven parts

| # | Part | What it does | In the prototype |
|---|---|---|---|
| 1 | **Production and price prediction** | Predicts the season's potato production (history, area, weather) and the price 1 to 9 months after the harvest, with a range, by region (the plan's "spatio-temporal price and supply" model) | Built: production trend forecast (BBS, 13 seasons, all districts) with a range; price outlook driven by crop size and corrected by the season's own prices, 2,000 simulated paths; regional price levels (WFP). Weather not in yet |
| 2 | **Storage and selling-time engine** | Compares selling now with storing 1 to 9 months after rent, transport, loan interest and weight loss; recommends **Sell now**, **Store longer** or **Sell part, store the rest** | Built and tested: flat ৳250 rent, 84 kg sacks, the plan's 8.65% season weight loss, handling, loans; chance that storing beats selling now; the price at which storing pays; net profit in the season replays |
| 3 | **Market access** | Market prices, demand, forecasts; risks of storing; buyers and offers compared; direct links to wholesalers, retailers, processors | Built: offers ranked by money in the farmer's hand (transport, grading losses, wait for payment); small lots pointed to a group lot; buyers are demo |
| 4 | **Crop-backed financing through banks** | Verifies stored quantity and receipts, values the crop, works out repayment risk, sends the loan application; the bank decides. KrishiVault does not lend | Built: **digital storage receipt** from the cold storage (weighed, graded, sent by SMS), careful valuation after an 8.65% weight-loss buffer, cold storage paid first, risk from the price paths, lender comparison, bank screen, **the bank's hold** on the receipt, and **the split when the potatoes are sold** (cold storage, then bank, then farmer); banks are demo |
| 5 | **Export market intelligence** | Where to buy (big crop, low price) and which markets pay **after** every cost | Built: sourcing from real BBS and WFP data; markets after sorting, truck, port papers, freight, insurance, duty, rejects; foreign prices and costs are demo figures |
| 6 | **Group storage** | Neighbours combine sacks for a volume discount and shared transport (the plan: a lower per-sack fee than storing alone) | Built: groups, discount tiers that count only after the cold storage agrees, shared truck saving, join from a call or the dashboard; groups are demo |
| 7 | **Profit calculator** | Every cost, every sale, profit per kg, per sack, per maund and per harvest; actual against "sold everything at harvest" | Built: example bigha in Bogura, editable |

**Around the seven parts (from the plan's execution and challenges):**
- **The government screen:** a glut warning from the crop size (real BBS data and the outlook), cold-storage fill (demo), and farmer figures by district, counted only with the farmer's consent (section 5).
- **Curing reminder:** an SMS before the harvest: cure the potatoes in shade for 1-2 weeks, sort out cut and rotten ones, then store (the plan's answer to storage loss).

## 4. How it works on the ground

**The plan's four-step loop, and what the prototype does at each step:**

| Step | The plan | In the prototype |
|---|---|---|
| 1. Harvest check-in (February to April) | The farmer calls the Bangla voice line (or a Grameenphone USSD code, or with a field agent at a haat such as Dhaper Hat or Bibir Pukur in Kahaloo) and gives two numbers: **sacks harvested** and **cash needed now**. KrishiVault uses local cost benchmarks to advise the split: how many sacks to sell now and how many to store, until when | The call preview (`/call`) asks for the quantity, today's price, the cash needed and within how many days, reads them back, and answers with the engine's split. No phone line or USSD yet |
| 2. Digital vaulting at the cold storage (February to May) | The cold storage weighs and grades the sacks, records them on its KrishiVault screen and issues a **verified digital storage receipt** to the farmer by SMS | Partner screens → Cold storage → "Issue a storage receipt" (receipt number such as `CSA-0001`, SMS in dry run) |
| 3. Crop-backed loan | With the farmer's consent the receipt goes to a bank or microfinance lender; the sacks are the security; the farmer gets cash (the plan: 50-60% of the harvest-time value) by bank or mobile money to clear input debts instead of selling | Bank loan page and the bank's screen: application with the receipt, careful value, risk; approval puts a **hold** on the receipt (the sacks leave only with the bank's agreement; a held receipt cannot back a second loan). Disbursement is not part of the prototype |
| 4. Market alert and settlement (July to December) | When prices are good, KrishiVault alerts the farmer and connects buyers (wholesalers, processors). The buyer pays; the cold-storage fee and the loan with interest are deducted; the rest goes to the farmer | The engine names the best month; buyers are ranked; the bank's screen records the sale and shows **the split** (cold storage, bank, farmer). Alerts by SMS are to do. **KrishiVault works out the split; a bank or mobile-money account pays it: KrishiVault never holds the money** |

**Farmers (button phones):** a voice call with keypad or speech, and an SMS receipt. The menu:

```
১ — আলু রাখবেন না বেচবেন: পরামর্শ        (store or sell advice)
২ — দামের পূর্বাভাস                        (price outlook)
৩ — একসাথে হিমাগারে রেখে খরচ কমান          (group storage)
৪ — হিমাগারের বস্তা জামানতে ব্যাংক ঋণ       (a loan against stored sacks)
৯ — আমাদের সহকারী ফোন করবেন                (a KrishiVault helper calls back)
```

Every number is read back for a keypad "yes"; every answer ends with "১ = আবার শুনুন, ০ = মূল মেনু, ৯ = সহকারী". After the store-or-sell answer the farmer may press **৮** to let the answers be counted, without name or number, in the district figures (opt-in: the greeting promises that what the farmer says is used only to advise them). **In the prototype there is no phone line**: the call is shown in the browser (`/call`, the call preview). **SMS can be sent** (REVE; dry run until switched on). The plan's channels for later: Grameenphone SMS, USSD and a Bangla voice IVR.

**Helpers and partners (web dashboard, `/`):** a KrishiVault helper, a field agent or a farmer's family member can run the same engine with every cost visible. Cold storages (the plan's check-in point for farmers who cannot use a phone menu), banks, buyers, exporters and government each have a screen; requests from calls appear there straight away.

## 5. Why KrishiVault is different

**Existing help covers pieces:** most agritech in Bangladesh helps before the harvest (seed, fertilizer, advice) or matches buyers on the spot market. None of it solves the **post-harvest cash trap**: a farmer told "prices will triple by December" still cannot wait, because the alert does not pay today's debt.

**KrishiVault joins three things in one loop (the plan's "cash plus cold storage" wedge):** market timing with a range, the cold-storage sums (flat rent, weight loss, interest), and crop-backed cash through a bank. The stored sacks become security, so the farmer can keep the crop until the price is right.

| | Traders (faria, bepari, aratdar) | Price and market apps | Banks and microfinance | KrishiVault |
|---|---|---|---|---|
| Cash at harvest | Yes, at a cost: buy at the harvest low or lend against the crop before harvest | No | No: want land or other security smallholders lack | **Yes, through a bank:** a loan against sacks confirmed by the cold storage |
| Price outlook 1-9 months | No (they keep the information) | Today's or past prices | No | **Yes, with a range**, driven by the crop size |
| Store-or-sell sums after every cost | No | No | No | **Yes**: rent, weight loss, interest, per sack |
| Cold-storage link | Traders hold 97.6% of cold-stored potatoes (study) | No | Cannot check rural stock | **Digital receipts, the bank's hold, group bookings** |
| What the farmer gets | The harvest-low price | A little more, still sold at harvest | Usually nothing | **In the 2024 replay, net profit 2.3 times** selling at harvest; in the 2025 big-crop year, no loss from storing |

**The plan's "2x to 3x net profit", tested honestly:** with a growing cost of ৳12.67 a kg (the profit calculator's example bigha, an assumption), the March 2024 replay (36 sacks at ৳18) earns ৳15,760 net profit if everything is sold at the harvest and ৳36,240 with the advice (**2.3 times**; storing every sack until November would have been 2.9 times, but the engine could not know that then). In the big-crop year (March 2025 at ৳14) the right answer was **sell now**: storing every sack would have turned a ৳3,660 profit into a loss of ৳11,650 to ৳19,820. So: "up to 2-3 times in a normal year, and no storage loss in a glut year", never a promise.

**Government gets something new (plan):** today policy makers see prices and production. With farmers' consent and proper anonymization, KrishiVault can add **ground-level farmer figures**: the share of farmers in a district who needed cash within 7 days of the harvest, the cash they needed, what storing really cost, how many could not get cold-storage space. Say **"direct, farmer-originated, timestamped data with an auditable trail"**, not "no human hand, so no manipulation": verification, data quality and sampling still matter. In the prototype: Partner screens → Government.

**Bottom line (plan):** other platforms tell a farmer *where* to sell today; KrishiVault gives the farmer the *sums and the cash to wait for the right month*, and helps them act on it.

## 6. Who gains, and the business model

**KrishiVault charges farmers no fee.** It earns when value is created (the plan's figures, worked out in `src/engine/business_model.py`, `/api/business/plan`):

| Income stream | How it is charged | Per unit |
|---|---|---|
| 1. Telco VAS call revenue | The voice line at a value-added-service call rate (৳2-3 a minute), split 50/50 with Grameenphone | About ৳30 per active farmer a year |
| 2. Cold storages | 4% booking and digitization commission on the ৳300 storage fee | ৳12 per sack through KrishiVault |
| 3. Banks and microfinance | 1.5% digital collateral fee on a loan of about ৳300 a sack | ৳4.50 per financed sack |
| 4. Buyers and processors | 1% sourcing fee on sorted lots bought from cold storage | About ৳12 per sack |
| 5. Government and media | Subscriptions to the cold-storage fill and glut analytics (DAM, DAE, Ministry of Agriculture, news media) | Year 1: ৳2 lakh |

(The plan's earlier, simpler list gave cold storages 2-3% of the storage fee, banks 1-1.5%, buyers 1-2%; the table above is the plan's updated version.) Exporters: export intelligence and an export marketplace come in phase 3.

**Start-up money (first 12 months): ৳20 lakh** (about 17,000 US dollars): tech, AI and telco integration ৳7 lakh (35%); field operations and onboarding ৳6 lakh (30%); legal, bank API and compliance ৳3 lakh (15%); rural marketing ৳2 lakh (10%); servers and buffer ৳2 lakh (10%). **One funding stage:** a pre-seed round or grant of ৳20-25 lakh (Grameenphone FutureMakers prize, ICT Division iDEA grant, or angels) for a pilot with 2,000 farmers and 5 cold storages; break-even in year 2 (about month 14-16).

**The 3-year projection** (40 sacks per active farmer; the plan's table implies 60% of sacks financed and 30% sold through KrishiVault to buyers; checked in `tests/test_business.py`):

| | Year 1 (Bogura and Munshiganj) | Year 2 (4 districts) | Year 3 (national) |
|---|---|---|---|
| Active farmers; cold storages | 2,000; 5 | 15,000; 35 | 60,000; 100 |
| Sacks managed | 80,000 | 6,00,000 | 24,00,000 |
| Revenue | ৳17.24 lakh | ৳1.26 crore | ৳4.92 crore |
| Operating costs | ৳18.5 lakh | ৳58 lakh | ৳1.45 crore |
| Profit (EBITDA) | −৳1.26 lakh (−7.3%) | +৳68.3 lakh (54.1%) | +৳3.47 crore (70.5%) |

These are **projections**, not results; the pilot tests whether partners will pay these fees.

**Rule:** the farmer's advice is never for sale. A partner's fee never changes what KrishiVault advises; offers are ranked by money in the farmer's hand. KrishiVault is the data and connection platform; it does not lend its own money and does not hold farmers' money.

**Why partners say yes (plan):** cold storages compete to fill their space ("unhealthy competition" among 320 plants in the study) and get grouped farmer volume, digital stock records for KrishiVault-tagged sacks only (no full accounting software, which owners reject over tax worries) and fees collected at the sale. Banks get security they can check: the sacks sit in a partner cold storage and leave only with the bank's agreement (warehouse-receipt financing), valued after weight loss.

## 7. AI and technology, and why

**"AI where uncertainty and language live; fixed rules where money lives."**

| Where | Method | Guardrail |
|---|---|---|
| Production forecast | Trend of BBS production per district and nationally; planted area when known; weather adjustment by hand for now | A range from past errors; known seasons use BBS figures |
| Price outlook | Usual seasonal shape × "rise strength" set by crop size (fitted on WFP 2024 and 2025 seasons), corrected by the season's own prices; 2,000 simulated paths | Ranges, not a single number; limits stated on every screen; frozen market reports dropped. The plan names XGBoost, LSTM or Prophet: those need the long DAM price history first (to-do 4); with two seasons they would overfit |
| Storage engine | Exact taka sums for every month and every path; weight loss 8.65% over a full season (the plan) | Deterministic, explainable; costs editable |
| Loan risk | Chance the crop is worth less than the loan, from the same paths; value after the 8.65% weight-loss buffer | The bank decides |
| Receipts, hold, split at sale | Fixed rules: who is paid first (cold storage, bank, farmer) | KrishiVault never holds money |
| Government figures | Counts by district, only with consent, no names or numbers, hidden under 5 farmers | Glut warning from real BBS data; fill rates labelled demo |
| Understanding the farmer | Bangla number parser (digits, words, মণ, বস্তা, northern dialect); Gemini only for what the parser cannot place | Every Gemini number must have been said |
| Wording | Gemini may reword the Bangla answer | **Number lock**: no number may change; otherwise the template is used |
| Voice | Browser speech recognition (prototype); Google Bangla voice | Keypad always works; numbers read back |

## 8. Execution, feasibility and risks

**The plan's phased rollout:**

| Phase | When and where | Scope | Milestone |
|---|---|---|---|
| 1. Pilot | Months 1-4: **Kahaloo upazila, Bogura** (the plan: 9,016 ha of potato, 23 cold storages) | 50-100 farmers, 1-2 cold storages, 1 bank or microfinance lender | Check the outlook against real prices, digitize receipts, first 100 tonnes of crop-backed loans in the February-May storage window |
| 2. District | Months 5-12: **Bogura and Munshiganj Sadar** | 1,000+ farmers, 10 cold storages, group storage and buyer matching | Lower per-sack fees for groups; stored lots straight to city wholesalers and processors |
| 3. National | Year 2 on: Rangpur, Dinajpur, Cumilla, Thakurgaon | The country's cold storages; onion and maize | Buyer and export marketplace (the plan: about 103,000 tonnes of potato exports, to Malaysia, Singapore and Sri Lanka) |

The six biggest districts (Rangpur, Dinajpur, Bogura, Joypurhat, Munshiganj, Rajshahi) grow 61% of the crop (BBS 2024-25). Organizations the plan names as examples (Himadri Ltd. or Ejab Group cold storage; Bangladesh Krishi Bank, BRAC, PKSF; PRAN, ACI, Square) are **organizations to approach, not partners**.

**Measure in the pilot:** price received against the haat price and neighbours; months stored; rent paid per kg sold; loans taken instead of early sales and their repayment; group discounts actually agreed; forecast error against what happened; how many farmers agree to be counted.

**Feasibility (the plan's four tests):**
- **Technical:** public data exists (DAM and BBS prices and production, DAE area, cold-storage occupancy); light models; works on a button phone (voice, SMS, later USSD); cold storages use a web screen.
- **Operational:** cold storages need volume and fee collection; KrishiVault brings grouped farmers and records only its own tagged sacks.
- **Financial and legal:** warehouse-receipt lending with a hold and a weight-loss buffer; a loan of 50-60% of the harvest-time value leaves a margin because off-season prices have usually risen.
- **Sustainability:** free for farmers; fees from partners (section 6).

**Risks and the ground-level challenges (plan), with how the prototype answers them:**

| Challenge | Why the usual answers fail | KrishiVault's answer | In the prototype |
|---|---|---|---|
| Pre-harvest debt (*dadon*) forces sales at harvest | A price app cannot stop a trader demanding his money | A crop-backed loan from the first day in cold storage pays off the trader; the farmer keeps the crop | Cash need in the call; loan against the receipt |
| Cold-storage owners hide figures (tax worries) | Full accounting software is rejected | Only KrishiVault-tagged sacks are tracked; KrishiVault helps fill space | Receipts for KrishiVault sacks only |
| Uncured potatoes and power cuts cause storage loss | Banks will not lend against a crop that may rot | Curing reminders before harvest; partner only with generator-backed cold storages and separate seed and table chambers; the 8.65% loss in every sum | Curing SMS; 8.65% in the engine and loan valuation |
| In 1 year of 3-4 off-season prices stay flat | "Store until December" for everyone can ruin farmers in a glut year | Glut warning from the crop size and storage fill; split selling (the plan: sell 30-40% at harvest; or exits 30% / 40% / 30%); a careful loan share (the plan: 50%) | "Sell now" in big-crop years (2025 replay); "sell part" with a 25-50% safety share when unsure; demo banks lend 50-60% of a careful value |
| No written cost records | Apps that need bookkeeping are not used | Local cost benchmarks, entered once by a helper or the cold storage | Profit calculator example bigha; editable costs |
| Farmers' reading and phones | Smartphone apps leave them out | Voice and keypad; the cold storage or a field agent checks the farmer in | Call preview, keypad first |
| A wrong "store" call costs a farmer money | | Ranges, the bad case shown, "sell part" when unsure | The engine never says "store everything" when the chance of gain is low |

## 9. The prototype (what we show)

| Part | Status | How to see it |
|---|---|---|
| Dashboard (`/`) | Built | Season overview, store or sell, forecasts, buyers, bank loan, group storage, export, profit calculator, partner screens (`docs/SCREENS.md`) |
| Call preview (`/call`) | Built | Keypad or speech in the browser; the same engine; requests reach the partner screens; press 8 to be counted |
| Digital storage receipt, bank hold, split at sale | Built (demo partners) | Partner screens → Cold storage (issue), Bank loan (apply with the number), Bank (approve, record the sale) |
| Government screen | Built (glut warning real; fill demo) | Partner screens → Government |
| SMS: advice, receipt, curing reminder | Ported to Python; dry run | "SMS me" on `/call`; "Send this advice by SMS" and "Send the curing reminder" on the dashboard; receipts SMS on issue |
| Business plan sums | Built | `/api/business/plan` |
| Phone calls, USSD | Not in the prototype | No phone line; the Awaj port stays in `src/notify/awaj.py` for later |

**The season selector** replays real seasons: **March 2025** (big crop: the engine says sell now), **March 2024** (normal crop: sell a safety share, store the rest until December), plus **March 2027** (the next harvest, forecast) and **October 2026** (potatoes already in store).

**The demo moment:** a teammate calls as a farmer ("হামার ৮০ মণ আলু উঠছে, ফড়িয়া ১৬ টেকা দিবার চায়, ২৫ হাজার টেকা নাগবে ৪ দিনের মইধ্যে"), hears "sell 19 sacks now, store 17 until December" with the money and the risk, presses 2 for a cold-storage request, gets the SMS; the cold storage issues the digital receipt; the bank sees a loan application with its risk, approves, and later the sale pays the cold storage, the bank and the farmer.

## 10. What is real and what is not

**Real now:**
- BBS potato production for 64 districts, 2012-13 to 2024-25, and the production forecast built on it.
- WFP retail potato prices, February 2024 to July 2026 (19 usable months), and the price outlook fitted on them.
- The storage engine, market comparison, loan valuation, receipts with the hold and the split at sale, group storage, export cost build-up, profit calculator, government figures and the business-plan sums: all built and tested (`tests/`, 143 tests).
- The call preview with the Bangla number reader and the number lock; the SMS client (dry run).

**Not yet, or demo:**
- **The price outlook rests on two full seasons.** It is a careful statistical scenario, not a trained AI forecast. Say "statistical outlook with ranges".
- **The backtest covers only two seasons** (12 months with prices from 4+ markets; `python -m src.models.backtest`, the Forecasts page). Predicting each season with a model that had not seen it, and estimating each crop from its planted area as at the harvest, the outlook missed by 11% on average against 52% for "usual seasonal shape only", the real price fell inside its 8-in-10 range in 92% of months, and it got store-or-sell right in both seasons (the usual shape: 1 of 2). That is far too little to judge it, and with one season left to learn from, the crop-size link is an assumption: the calls stay right if a 10% bigger crop cuts the rise by 0.8 or more; at 0.5 one goes wrong. Say "tested on two past seasons", not "proven".
- **The replays are fair:** "Replay March 2025" and "Replay March 2024" use only what was known on that date. The price link is learned from seasons that had finished by then (none for March 2024, so the starting assumptions; 2023-24 for March 2025), and the crop is estimated from its planted area and the earlier yield trend. The dashboard then shows what really happened, with the 8.65% weight loss: in March 2024 the advice ("sell 9 sacks, store 27 until December") brought ৳20,480 more than selling everything at the harvest (net profit 2.3 times, with the example growing cost); in March 2025 storing every sack would have lost ৳15,310 to ৳23,480, whichever month they were sold.
- **The study figures in the plan** (64.07%, 13.60%, 97.6%, 8.65%, ৳6 a kg and so on) come from a value-chain study with 2016 fieldwork; only 33.13% has been checked. Find the study and check each figure before putting it on a slide (to-do 11).
- **The 8.65% weight loss** is the study's figure, now the engine's default; the field check should confirm it for this season.
- **WFP has gaps:** no month from March to August 2024 has prices from 4 or more markets.
- **Weather is not in the production forecast** yet.
- **Farm-gate prices:** the outlook moves the farmer's own price by the retail change; real farm-gate history is needed.
- **Costs and losses** other than the field notes and the plan (sack, carrying, selling, home-store loss, interest rates) are assumptions to check.
- **All partners are demo:** cold storages, banks, buyers, exporters, groups, receipts, cold-storage fill rates. Export prices, freight and duties are demo figures. Farmer figures on the government screen come only from prototype use.
- **Money does not move:** no loan is paid out and no sale is settled; the split is worked out only. A pilot needs a bank or mobile-money partner for payments.
- **The business plan is a projection** from the plan's assumptions (section 6), not results.
- **Gemini was tried with the real key on 14 October** (cloud session): it fills in what the parser cannot place ("ফড়িয়া ১৬ টেকা দিবার চায়" → ৳16 a kg) and rewords the answer; the number check kept every number in the test calls. The number check compares numbers and banned words, not meaning, so listen to a reworded answer before a demo.
- **The Google voice has not been tried with its key yet**: the key (`GOOGLE_TTS_JSON_B64`) was not in the cloud environment. Speech recognition has not been tried with a Bogura speaker.
- **No live SMS from KrishiVault's own code yet** (REVE worked from Mati Kohon on 8 October). From cloud sessions the REVE gateway (`smpp.revesms.com:7790`) closes the connection, tried twice on 14 October: the request leaves the cloud machine and REVE hangs up, so it is likely an address allow-list on REVE's side. Send the first live SMS from a laptop, or ask REVE whether they allow only listed addresses. The SMS keys were also not in the cloud environment. The dry run works: the demo receipt is 168 Bangla characters, 3 SMS parts. One send can go to up to 5 numbers (comma-separated); REVE's format for several numbers in one request is not confirmed, so make the first live send to one number. On 15 October the SMS variables were still not in the cloud session.
- **No phone line, no USSD.**

## 11. Prototype to-do, in order

1. **Rebuild around the new plan.** **Done, 14 October**: engine, forecasts, dashboard, call preview, docs. **Synced with the plan document, 15 October** (section 13).
2. **First live SMS**, only with the user's go-ahead: keys in the environment (`docs/CLOUD_SETUP.md`), `SMS_LIVE=1` for that one send, to a team member's phone. **Blocked from the cloud** (14 October): REVE closes the connection; do it from a laptop.
3. **Field check in Kahaloo and the rest of Bogura** (5 farmers, 2 cold storages; use `docs/farmer_interview_guide.html`, printed): sack size and rent this season (some charge by kg), the cold-storage advance and its interest, weight loss (is it near 8.65%?), carrying and selling costs, when farmers sell and why, pre-harvest debts, cash needed in the first week. Replace the assumptions in `src/engine/facts.py`.
4. **Price history:** get DAM (or FAO GIEWS) monthly potato prices for 2010-2026, wholesale and retail, into `data/raw/price_history.csv` (`date, admin2, market, price`); the outlook refits itself. Then backtest it against "usual seasonal shape only". **Backtest built, 14 October** (`python -m src.models.backtest`; it re-runs on any new history; use `--only-past` once there are 5 or more seasons). **The download is blocked from the cloud:** the environment's network list does not allow `market.dam.gov.bd`, `fpma.fao.org` or `data.humdata.org`. Add them (cloud environment settings → Network access), or download on a laptop.
5. **Weather in the production forecast:** NASA POWER season weather per district for 2012-2025 (Mati Kohon has the fetcher).
6. **Real partners:** for phase 1, one or two Kahaloo cold storages (receipts, group rate), one bank or microfinance lender (loan terms, the hold, how the sale repays it), one buyer and later one exporter. Replace the demo entries in `data/demo/demo_partners.json`.
7. **Export quotes:** real destination prices, freight and duties (Export Promotion Bureau, exporters, shipping lines).
8. **Gemini and the Google voice** with real keys in the call preview; test speech with a Bogura speaker. Gemini: **done, 14 October** (it needed a 10-second wait and new model names). Google voice: add `GOOGLE_TTS_JSON_B64` to the cloud environment, then check `/api/voice/speak`.
9. **Update the pitch deck** (`krishivault-pitch-deck.html`) and the farmer interview guide. **Both done, 15 October**, and **updated to the plan document the same day** (study figures with their year, the four-step loop, the differentiation table, income streams and projection, the phased rollout; new questions in the guide).
10. **Onion** as the second crop (home storage 2 to 3 months, different season); maize later (plan).
11. **Check the study figures:** find the value-chain study the plan quotes (likely the BRAC University thesis on Bogura and Munshiganj, `DATA_SOURCES.md`) and confirm 64.07%, 13.60%, 97.6%, 16.60% and 8.65%, with the year of each taka figure.
12. **Market alerts by SMS:** when the engine's best month comes, send the farmer a reminder with the buyers' offers (step 4 of the loop).
13. **Decide the open points** in section 13 with the team.

## 12. Prepared Q&A

| Question | Short answer |
|---|---|
| Can you really predict potato prices? | Not exactly, and we never say so. We give a range from 2,000 simulated paths, driven by the crop size; the engine recommends selling part when the range is wide. |
| What if the forecast is wrong, or prices stay flat (1 year in 3 or 4)? | Sell part, store part. The engine shows the bad case (1 in 10) and how likely storing is to beat selling now. In the 2025 glut replay it said "sell now", and storing would really have lost up to ৳23,500. |
| You say 2x to 3x profit? | In a normal year, yes: the 2024 replay took net profit from ৳15,760 to ৳36,240 (2.3 times) on 36 sacks. In a big-crop year the gain is avoiding a loss. It is a range, never a promise. |
| How is this different from a price app? | A price alert does not pay today's debt. We join the sums, the cold storage and crop-backed cash in one loop, so the farmer can afford to wait. |
| Why would cold storages join, when early sales let them re-let space? | Group bookings fill their space at the start of the season; verified receipts bring them loan customers; fees are collected at the sale; we track only KrishiVault sacks. |
| Why would banks lend? | The potatoes are in a cold storage that issues the receipt and releases the sacks only with the bank's agreement; the value is careful (the low price, after 8.65% weight loss); rent and the storage's own advance come off first; the risk is measured. |
| Do you lend, or hold the money? | No. The bank lends and a bank or mobile-money account pays; KrishiVault verifies, values, connects and works out the split. |
| Isn't this just information? | Every answer ends with an action: a cold-storage request, a receipt, a group join, a loan application, a lot sent to buyers. |
| Who pays, and when do you break even? | Cold storages, banks, buyers and government (and a share of the call rate); the farmer pays no fee. The plan's projection breaks even in year 2 (about month 14-16). |
| Won't fees bias the advice? | No paid placement: offers are ranked by the money left to the farmer. |
| What does the government get? | A glut warning from the crop size, cold-storage fill, and farmer figures by district, only with consent and without names. Direct, timestamped, auditable data, not a claim that nothing can be manipulated. |
| Why button phones and voice? | Most farmers who sell early have button phones and little reading time; the keypad always works. |
| Is the data real? | Production (BBS) and prices (WFP) are real; partners, receipts and export prices are demo, and every screen says so. |
| Why potato? | The biggest stored crop, with the clearest storage trap; the same engine fits onion. |

## 13. Plan sync, 15 October: what changed, and what the team must decide

**Brought in line with the plan document:**
- Weight loss in cold storage is now the plan's **8.65% a season** (was an assumed 0.5% a month plus 2% at exit, about 6.4%), and the loan valuation applies it as a buffer whatever the loan's length. The demo answers did not change; the taka figures moved a little (the call: ৳55,600 on average, was ৳56,500; the 2024 replay: ৳20,480 more, was ৳22,280).
- New: digital storage receipts with an SMS, the bank's hold, the split at sale, the government screen with consent (press 8), the curing reminder, net profit in the replays, and the business-plan sums.
- Docs, the readiness check, the pitch deck and the field check guide now carry the plan's problem figures (with their year), differentiation, four-step loop, rollout, risks and money.

**Open points: the plan says two different things, or differs from the data.** `business_model.checks()` lists the money ones:
1. **Free for farmers, or a VAS call rate?** The plan says KrishiVault is free for farmers, and also earns ৳2-3 a minute from farmers' calls; the call rule here is a missed call, then KrishiVault calls back. Pick one before the pitch.
2. **Pilot size:** phase 1 is 50-100 farmers and 1-2 cold storages, phase 2 adds 1,000+ farmers and 10 cold storages within year 1, but the year-1 projection and the funding goal use 2,000 farmers and 5 cold storages.
3. **Rent:** the projection uses ৳300 a sack; the field notes and the engine use ৳250 (some charge ৳300). At ৳250 the cold-storage fee is ৳10 a sack, not ৳12.
4. **Loan per sack:** "about ৳300 a sack, 50% of the value" fits the study's ৳6 a kg prices; at ৳16 a kg a sack is worth about ৳1,340, so 50% would be about ৳670. ৳300 is what cold storages already advance.
5. **Old figures:** "8.6 million tons" (BBS 2012-13; 2024-25 is 11.6 million), ৳6 a kg harvest prices, ৳3.50 a kg production cost and ৳1.50 a kg storage are from a decade ago; 320 cold storages and 2 million tonnes of space should be checked against today's list.
6. **"Store everything":** the plan says never gamble the whole crop on one month (sell 30-40% at harvest, or exits 30/40/30). The engine stores every sack only when storing wins in 8 of 10 price paths and the bad case loses at most 5%; otherwise it sells a 25-50% safety share. Decide whether "store" should always keep a share for earlier sale.
7. **AI wording:** the plan names XGBoost, LSTM and Prophet and says "AI forecasting"; the rule here is "statistical outlook" until the outlook is backtested on a longer history.
8. **Named organizations** (Himadri, Ejab, BKB, BRAC, PKSF, PRAN, ACI, Square) are targets, not partners.
9. The Google Doc still contains chatbot replies ("It looks like you forgot to paste…", "Paste your draft…"): remove them before sharing it.
