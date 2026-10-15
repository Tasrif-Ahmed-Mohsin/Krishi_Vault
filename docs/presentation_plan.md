# KrishiVault Pitch Plan

15 October 2026. A copy of the team's pitch-plan doc (https://claude.ai/artifact/6tvpNSkMzzKk8DggXh4nfc); edit the doc, then refresh this file. Built from the plan document and the prototype in this repository; every figure comes from the engine, our data or a source listed at the end.

A 7-minute story and 3 minutes of Q&A: open on the farmer's own voice, prove the trap with numbers, run the loop live, and close on the one thing the syndicate never let farmers do: wait.

## The story in one line

**Thesis:** Bangladesh does not have a potato problem; it has a waiting problem. Farmers grew 11.6 million tonnes last season, but the rise after the harvest goes to whoever can afford to wait, and that is not the farmer.

**The villain, said carefully:** the syndicate runs on three levers: the farmer's cash need at harvest, the information gap, and stored stock nobody can trace. A 2023 commerce ministry study blamed a cold-storage owners' syndicate and found stored potatoes behind paper slips with no owner's name (the cold storage association denied it). We do not accuse anyone on stage; we take the levers away.

**The promise:** KrishiVault gives the farmer what the trader has: the sums, the cash to wait, and a receipt with his own name on it.

**The arc:** one farmer (the video) → the trap (why he sold) → the turn (one phone call) → the proof (two real seasons) → the system (the loop, the AI, the money) → back to the same farmer, next March.

**Closing line (Bangla):** আলু রাখবেন না বেচবেন, কবে বেচবেন: হিসাব করে বলে কৃষিভল্ট।

## Run of show: 7 minutes

Three speakers, two hand-overs (at 2:10 and 5:30). Rehearse to 6:40 so 20 seconds of slack remain. A, B and C are placeholders: put names in.

| Time | Beat | On screen | Who | Appeal | Criterion |
| --- | --- | --- | --- | --- | --- |
| 0:00–0:35 | **Hook:** the farmer's own voice, then one line from us | Field video with English subtitles; freeze on one number | A | Pathos | 1 Clarity |
| 0:35–1:45 | **Three traps:** flat rent (৳300 for 1 month or 9); crop size sets the price (2024 doubled, 2025 flat); cash at harvest (64% sold at once, traders hold 97.6% of stored stock) | WFP price chart 2024 against 2025; three traps | A | Logos, pathos | 2 Problem |
| 1:45–2:10 | **The turn:** "not a production problem, a waiting problem"; the syndicate's three levers | Cash · Information · Untraceable stock | A | Ethos (ministry study) | 2, 3 |
| 2:10–2:30 | **The answer in one breath:** Know, Calculate, Decide, Act, on a button phone | Four words and a button phone | B | Logos | 1, 3 |
| 2:30–4:15 | **Live demo:** dialect call → split and net profit → receipt → bank → price alert; a judge's two numbers on USSD | Call preview, USSD preview, partner screens | B | Ethos (it works) | 3, 4 |
| 4:15–4:55 | **Proof without hindsight:** 2024 net profit 2.5 times; 2025 "sell now" avoided a ৳17,100–25,300 loss; 11% vs 52% price miss | Replay slide | B | Logos, ethos | 3, 4 |
| 4:55–5:30 | **Why this AI:** AI listens and speaks; fixed rules do the money; the number lock | Simple architecture picture | B | Ethos | 4 AI |
| 5:30–6:15 | **Execution:** Kahaloo pilot → Bogura and Munshiganj → national; partners pay only when they gain; ৳20 lakh, break-even in year 2 | Rollout line and money tiles | C | Logos | 5 Feasibility |
| 6:15–6:45 | **Impact:** farmer income, less waste, stock the government can see, the levers gone | Three impact numbers | C | Pathos, logos | 6 Impact |
| 6:45–7:00 | **Close:** back to the farmer; tagline; the ask | Freeze frame of the farmer and the tagline | A | Pathos | 1 |

## The hook: the first 35 seconds

No title slide and no "good morning, we are team…". The judges meet the farmer before they meet us.

1. **Dark screen, the clip plays (20–25 s).** Cut the field video to the one line with a price, a debt or a forced sale in it, in his own dialect. Burn in large English subtitles so it works even if the sound fails.
2. **Freeze frame, one number on it.** Use his number if the clip has one. If not: "৳18 a kg in March 2024. ৳67.50 in the shops by November." (WFP).
3. **Speaker A, two sentences:** "He grew the potatoes. Someone else got paid for waiting." Then: "We are KrishiVault, and we make sure the farmer can wait."

**How to pick the clip:** concrete (a taka figure), personal (his loss, not the market's), his words (dialect, unscripted), and it ends on a question our demo answers.

**Fallback if the video fails:** Speaker A holds up a button phone: "This is the only device the farmer in this story owns. Everything we show today works on it." Then the freeze-frame number on a slide.

**The callback:** the close (6:45) returns to the same freeze frame, now with his answer from KrishiVault beside it.

## The live demo: 105 seconds

The demo is the proof that this is not a slide-ware idea. Speaker B drives; one teammate plays the farmer's voice.

1. **0:00–0:30, the call (`/call`, season "Next harvest").** Press the first "Try" sentence: “হামার ৮০ মণ আলু উঠছে, ফড়িয়া ১৬ টেকা দিবার চায়, ২৫ হাজার টেকা নাগবে ৪ দিনের মইধ্যে”. Point at the dialect understood and every number read back; press 1.
2. **0:30–0:55, the answer.** Sell 19 sacks now (৳25,000 in hand), store 17 until December; ৳54,700 on average; net profit ৳12,900 against ৳5,600 if he sells everything today. Say: "It also tells him the bad case. Nobody else tells a farmer that."
3. **0:55–1:05, one action.** Press 2: a cold-storage space request; show the SMS receipt.
4. **1:05–1:25, the receipt and the bank (Partner screens).** The cold storage issues a digital receipt (his name, the weight, by SMS); the bank approves, the sacks are held for the bank, the payout SMS goes. Say: "The ministry found stock hidden behind slips with no name. This one has his."
5. **1:25–1:45, a judge's own numbers on USSD (`/ussd`).** Ask one judge: "How many sacks, and how much cash does he need?" Dial, enter the two numbers, read the answer screen. Say: "Two numbers, any phone, no internet."

**If there is time left:** season "Today: October 2026", Field agent → "Check price windows": the SMS says how many sacks to sell and to which buyer.

**Fallback:** a 90-second screen recording of the same run, open in a second tab. If anything stalls for more than 5 seconds, switch without comment and keep talking.

**Setup:** run the server on the laptop; SMS in dry run. With Gemini on (needs internet; use a phone hotspot), the dialect sentence fills all four numbers. Without it, the call asks for today's price: type 16# on the keypad and say "the keypad always works"; clear yesterday's demo data; browser zoom 125%; every other tab closed.

## Evidence bank

Every number said on stage comes from this table. "Real" means it is in our own data or engine; "verify" means a news or study figure we found but have not yet opened at the source; open it before it goes on a slide.

| Claim | Number | Source | Status |
| --- | --- | --- | --- |
| The farmer in our video | His own price, debt or loss | Our field visit (add date and village) | Real: primary evidence, say when and where |
| Potato grown, 2024-25 | 11.6 million tonnes; Bogura 10% | BBS (our data) | Real. Never "8.6 million": that is 2012-13 |
| Prices after a normal crop | ৳35 (Feb 2024) → ৳67.50 (Nov 2024), retail | WFP via HDX (our data) | Real |
| Prices after a big crop | ৳20–25 a kg, April to December 2025 | WFP via HDX (our data) | Real |
| Glut years | Crop 6–7% above trend in 2016-17 and 2024-25 | BBS (our data) | Real |
| Sold at harvest; stored for sale | 64.07%; 13.60% | Value-chain study, Kahaloo and Munshiganj, 2016 fieldwork | Verify; say "a 2016 field study" |
| Traders' share of cold-stored potatoes | 97.6% | Same study | Verify |
| Wholesalers' share of value added | 33.13% | [BRAC University thesis](https://dspace.bracu.ac.bd/xmlui/handle/10361/7723) | Checked against the abstract |
| The syndicate finding | Stored stock 90% owned by cold-storage owners or traders, behind slips with no owner's name; record prices | [Commerce ministry study, The Financial Express, 2023](https://thefinancialexpress.com.bd/trade/cold-storage-syndication-blamed-for-record-potato-price-hike) | Verify; always add "the cold storage association denied it" |
| Price below cost, 2025 | Farm-gate ৳5–8 a kg against a ৳12–14 cost | [Dhaka Stream](https://dhakastream.rsi-lab.com/node/182776), [The Financial Express](https://thefinancialexpress.com.bd/national/country/bogura-farmers-take-a-hit-as-potato-price-drops-55pc) | Verify |
| Storage loss | 8.65% of the weight a season | 2016 study; the engine's default | Verify in the field check |
| Our 2024 replay | Net profit 2.5 times (৳11,740 → ৳29,450) on 36 sacks | KrishiVault engine, WFP prices, ৳14 a kg cost | Real, shown live |
| Our 2025 replay | "Sell now"; storing would have lost ৳17,100–25,300 | KrishiVault engine | Real, shown live |
| Backtest | 11% vs 52% average price miss; 2 of 2 calls right | KrishiVault engine | Real; always add "two seasons only" |

## Defensibility: why this survives copycats and the syndicate

Our strongest line: **we do not fight the syndicate; we remove its levers.** Each point below is one sentence on stage and a full answer in Q&A.

- **The loop is the product.** A price app gives information, a bank gives money, a cold storage gives space; only the loop (sums, receipt, loan, alert, split at sale) lets a farmer wait. Copying one piece does not break the trap.
- **It takes away four levers.** Cash at harvest → a loan against the receipt. The information gap → the outlook and price-window alerts. Untraceable stock → a receipt with a name and a weight. The trader's hold on buying → group lots that reach processors and exporters directly.
- **Both sides are paid to stay.** Cold storages get filled space and fees collected at the sale; banks get stock they can check, held for them. Every partner in an upazila makes the next farmer's loan easier.
- **Trust is in the code.** Ranges, never promises; the bad case said aloud; the number lock. In the 2025 glut it told farmers to sell, not store: an advisor that turns away its own storage business is believable.
- **The data compounds.** Every consented call adds district figures nobody else has (cash needs in the first week, storage access, real costs), which sharpen forecasts and become a government product.
- **It works on any phone.** Voice, USSD and SMS through Grameenphone: no app, no data plan, no reading beyond numbers.
- **Honest by default.** Demo partners are labelled and the replays use only what was known that day, so a judge cannot catch us overclaiming.

## Criteria map

Each criterion has one moment where it is won and one trap that loses it.

| Criterion | Where we win it | What the judges see | The trap to avoid |
| --- | --- | --- | --- |
| 1 Clarity | The hook, the one-line thesis, one question: "store or sell, and until when?" | One farmer, one number, one question; clean hand-overs | Listing every feature |
| 2 Problem depth | 0:35–2:10 | His words, the WFP price chart, BBS glut years, the 2016 study, the ministry's syndicate finding | Quoting 2016 taka figures as today's |
| 3 Solution and differentiation | 2:10–4:55 | The loop running live; traders, price apps and banks each in one line | Sounding like "another agri app" |
| 4 AI and technical rationale | 4:55–5:30, and inside the demo | Dialect understood, the number lock, 2,000 price paths, the backtest | "Our AI predicts prices" |
| 5 Feasibility and scalability | 5:30–6:15 | A working prototype (157 tests), Kahaloo first, partners paid only when they gain, ৳20 lakh, break-even in year 2, Grameenphone channels | Calling target organizations partners |
| 6 Impact | 6:15–6:45 | Per farmer: net profit 2.5 times in a normal year, no storage loss in a glut year. At year-3 scale (2.4 million sacks), the 2024 replay's ৳490 a sack would be about ৳118 crore more to farmers in a normal year: an illustration, not a forecast. Less waste (curing, sell-now in gluts); stock the government can see | Totals without the word "illustration" |
| 7 Q&A | The last 3 minutes | Named owners, 20-second answers, each bridged back to the demo | Long answers, arguing with a judge |

## Q&A playbook: 3 minutes

Expect 5 or 6 questions. Rules: the answer in the first sentence, one number, under 25 seconds, then a bridge back to something they saw ("as you saw in the call…"). If we do not know: "we don't know yet; the pilot measures it this way." Never argue; thank the judge for the hard ones.

| Question | Answer in 20 seconds | Owner |
| --- | --- | --- |
| If every farmer stores, won't the price rise disappear? | Partly, and that is the point: today the rise goes to whoever holds stock. As farmers hold, the gap shrinks and moves to them, and buyers see smoother prices. We never advise the whole crop, and the government screen watches stored stock for gluts. | B |
| Cold storages earn from early turnover, and some owners were named in the syndicate study. Why would they join? | We bring filled space early, fees collected at the sale and loan customers, and we track only our tagged sacks, not their books. We start with cold storages that compete for volume and have generators. | C |
| Two seasons of prices: why trust the forecast? | We don't ask you to. It gives a range, not a price; the replays use only what was known then; 11% vs 52% miss, 2 of 2 calls. Next: 15 years of DAM prices, the same test. | B |
| Banks won't lend against potatoes. | They lend against warehouse receipts: a named, weighed receipt from a verified cold storage, sacks held for the bank, valued at the low price after the 8.65% loss, and the sale repays the bank first. | C |
| What if the syndicate refuses to buy from your farmers? | The best buyer is often not the haat trader: processors, supermarkets and exporters reach farmers through group lots. And with a bank loan, the farmer no longer has to sell to anyone at harvest. | A |
| How much of this is real? | Real: BBS and WFP data, the engine, the call and USSD menus, 157 tests, our field video. Demo and labelled: partner names. The pilot signs one cold storage and one lender in Kahaloo. | C |
| What exactly is the AI? | Speech recognition and Gemini understand dialect and phrase the answer; the decision is exact sums over 2,000 simulated price paths; the number lock stops any AI from changing a number. | B |
| A farmer follows you and loses money. Then what? | He hears the bad case before he decides, at least 30% is sold at harvest, and the advice is a range, never a guarantee. The pilot measures results against neighbours. | A |
| How do you make money, and when do you break even? | Cold storages 4% of rent (৳12 a sack), banks 1.5% (৳4.50 a financed sack), buyers 1% (about ৳12 a sack), a Grameenphone call-revenue share, and data for government and media. ৳20 lakh runs year 1; break-even in year 2 (projection). | C |
| Why would a farmer trust a phone call? | It speaks his dialect, reads every number back, and a person is one key away. Farmers meet it through the cold storage and field agents at the haat. | A |
| Why not just send price SMS? | A price alert does not pay today's debt. Without cash and a receipt, information changes nothing, which is why existing apps have not broken the trap. | A |
| Privacy? | Numbers masked on partner screens; counted for government only after pressing 8, no names, districts under 5 hidden; a bank sees data only when the farmer applies. | B |
| Beyond potato and Bogura? | Our data covers 64 districts, the engine fits any stored crop, onion is next and maize later; Grameenphone's channels are national. | C |
| Your study numbers are from 2016. | Yes, and we say so. Today's numbers come from our own data (WFP, BBS 2024-25) and our field visit; the field check updates the rest. | A |

## Lines we never say

Punch without overclaiming: every line below survives a hostile follow-up.

| Don't say | Say instead |
| --- | --- |
| "We are destroying the potato syndicate." | "We break the syndicate's hold by taking away its levers: the forced sale, the information gap, stock nobody can trace." |
| "Cold-storage owners are the syndicate." | "A government study blamed a syndicate and the association denies it. Either way, our receipts make stock traceable." |
| "Our AI predicts potato prices." | "A statistical outlook with ranges, tested on two seasons it had not seen." |
| "Farmers will double or triple their profit." | "In the 2024 replay, net profit rose 2.5 times; in the 2025 glut, the farmer avoided the storage loss." |
| "We have partnered with BKB, BRAC, PRAN, Himadri." | "Those are the partners we will approach; the screens show demo partners, labelled so." |
| "Farmers can call us today." | "Here are the call and the USSD menu on the same engine; the phone line comes with the pilot." |
| "KrishiVault gives loans." | "Banks lend against the receipt; we verify, value and connect, and never hold the money." |
| "Bangladesh grows 8.6 million tonnes." | "11.6 million tonnes in 2024-25 (BBS)." |

## Assets and rehearsal checklist

- [ ] Cut the farmer clip to 20–25 seconds, burn in English subtitles, note the date and village, and confirm he agreed to be shown.
- [ ] Pick the freeze-frame number: his own, or ৳18 in March → ৳67.50 in November 2024 (WFP).
- [ ] Turn this run of show into slides (about 10 visuals; the repo's 10-slide deck is the starting point, its slide 1 becomes the video).
- [ ] Record the 90-second demo fallback.
- [ ] Laptop kit: server running locally, demo data cleared, phone hotspot for Gemini, Chrome zoom 125%, HDMI adapter, sound checked.
- [ ] Open the four "verify" sources in the evidence bank and keep screenshots.
- [ ] Print the evidence bank on one sheet for the Q&A table.
- [ ] Put names on speakers A, B, C and on every Q&A owner.
- [ ] Rehearse three full runs against a timer (target 6:40), then one run with a teammate firing hard questions for 3 minutes.
- [ ] Bring a button phone as the prop.
- [ ] Remove the chatbot text from the Google Doc before anyone outside the team sees it.
- [ ] Merge the prototype pull request so the demo runs from the main branch.

## Sources

Every figure on stage comes from one of these. Say the year with any taka figure from the 2016 study.

- **Value-chain study, Bogura and Munshiganj (2016 fieldwork):** farmers sell 64% at harvest, traders buy 97.6% of cold-stored potatoes, 8.65% weight loss in cold storage. [BRAC University thesis](https://dspace.bracu.ac.bd/xmlui/handle/10361/7723)
- **Syndicate evidence (2023):** a commerce ministry study found about 90% of stored potatoes held by cold-storage owners and traders, behind slips with no owner's name; the cold storage association denied it. [The Financial Express, 2023](https://thefinancialexpress.com.bd/trade/cold-storage-syndication-blamed-for-record-potato-price-hike)
- **Glut year (2025):** Bogura farmers took a hit as the potato price dropped about 55%; DAE Bogura put the growing cost near ৳14 a kg. [The Financial Express, 2025](https://thefinancialexpress.com.bd/national/country/bogura-farmers-take-a-hit-as-potato-price-drops-55pc)
- **Farmers' side of the story:** [Dhaka Stream](https://dhakastream.rsi-lab.com/node/182776)
- **Prices:** WFP food prices for Bangladesh (Humanitarian Data Exchange), two seasons, in the repo as `data/processed/potato_prices_wfp.csv`. This is why we say "statistical outlook", not "AI forecast".
- **Production:** BBS yearbook figures by district, in the repo as `data/reference/mati_kohon/crop_district_panel.csv`.
- **Our own field video:** the farmer interview (date, village, consent to be noted on the clip).
- **The prototype:** [pull request #6](https://github.com/Tasrif-Ahmed-Mohsin/Krishi_Vault/pull/6): the dashboard (`/`), the call preview (`/call`), the USSD preview (`/ussd`) and the 157 tests.
- **AI and voice architecture, now and after the pilot:** [architecture page](https://claude.ai/artifact/CgcMRqmLPQnercdCchXEUY)

> **Check before the day:** the three news pages were found by search and could not be opened from this environment. One teammate opens each link, checks the quoted figure and saves a screenshot for Q&A.
