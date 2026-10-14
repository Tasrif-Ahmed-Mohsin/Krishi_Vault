# KrishiVault handoff (14 October 2026)

Everything decided so far, in one place. This is the project's main plan document: start here in every new session. Details that support it are in `PLAN_DETAILS.md`, data in `DATA_SOURCES.md`.

## 1. What KrishiVault is

**KrishiVault is a farm business ecosystem, not an agricultural information centre.** It connects farmers who are left behind (button phones, little bargaining power, dadon debt) with everyone who buys from them, sells to them, stores for them and supports them: buyers, cold storages, fertilizer and pesticide dealers, seed and machinery sellers, agriculture officers and government. AI and data find the best option for the farmer; the network makes it happen.

**Vision:** the best possible value for farmers and for every honest stakeholder, and less agricultural loss of every kind:
- **financial loss:** forced sales in the glut, overcharged inputs, dadon interest;
- **crop and food loss:** disease, extreme weather, floods, rot in storage;
- **sustainability loss:** excess fertilizer and pesticide, wasted food, depleted groundwater.

**It must be financially solid and practical:** every service either saves the farmer money or earns it, and the ecosystem pays for itself through fees from the businesses that gain from it, never from the farmer's advice.

> ফোনে বলুন — ফসলের দাম আর টাকা দুটোই বাঁচান।

**Hero crop for the demo:** potato in Bogura, including the Sariakandi char. The data already covers 13 crops and all 544 upazilas.

## 2. The four pillars

| Pillar | What the farmer gets | Who he is connected to |
|---|---|---|
| **1. Sell for the best value** | AI advice in taka: sell now, sell part, store or sell as a group, with his cost-of-production floor and a sell-part safety net | Buyers and aggregators (group lots), cold storages (bookings) |
| **2. Fertilizer and pesticide supply chain** | The right dose for his crop and soil, the official fair price, delivered on time before the planting rush; pesticide only when the weather favours disease | Dealers (group orders, stock), DAE (fair-price reports, a weekly fertilizer demand calendar) |
| **3. Seeds and machinery marketplace** | Seeds (certified seed potato, improved varieties), machinery to buy or rent (tillers, reapers, harvesters, pumps), tools and other inputs, from verified sellers at fair prices, with government subsidy information | Seed sellers, machinery owners and dealers, service providers |
| **4. Danger alerts** | Warnings before heavy rain, heat waves, cold waves and fog, floods, crop-disease weather, and a **price crash**; "nothing needed this week" in quiet weeks | Agriculture officers (callback) |

**Web screens for partners (not for farmers):** agriculture officer desk, cold storage, buyer, dealer and seller screens, and a government (DAE) dashboard with alerts, floods and the fertilizer demand calendar. Bookings, group lots and orders made in a farmer's call appear on the right partner's screen straight away. Officers register farmers (phone number, upazila, crops) so KrishiVault can call them.

**Not in this plan (decided 14 October):** a farmer money record (খাতা), loans instead of dadon and a lender screen, a phone-number ID with a PIN, farmer keypad reports, and a spray record.

## 3. How a farmer uses it

The farmer has a button phone, so KrishiVault comes to him by **voice call and SMS**:

- **Free for him:** he gives a missed call and KrishiVault calls back, or KrishiVault calls him when there is an alert or it is time to act.
- **Keypad menu:**

```
১ — ফসল বেচা: দাম আর পরামর্শ    (selling: price and advice)
২ — সার ও কীটনাশক               (fertilizer and pesticide)
৩ — বীজ ও যন্ত্রপাতি             (seeds and machinery)
৯ — কৃষি কর্মকর্তা ফোন করবেন      (an agriculture officer calls back)
```

- **Voice:** he can also speak; the AI listens, answers in a Bangla voice, and confirms every number by keypad.
- **An SMS receipt** after every call, which a family member can read.

**Every piece of advice ends with something to press:** book a cold-storage slot, join a group sale, join a group fertilizer order, order seed, book a harvester, call an officer. Research shows market information alone rarely raises farmers' prices (Fafchamps and Minten, India; Aker and Fafchamps, Niger); gains come when the farmer can act (Shimamoto and others, Cambodia). This is why KrishiVault is an ecosystem, not an information service.

## 4. Who gains, and what they give

| Stakeholder | What they gain | What they give |
|---|---|---|
| Farmers | Better prices, fair and on-time inputs, better seed, machinery access, early warnings | Their crop and purchases |
| Buyers and aggregators | Ready, sorted group lots; traceable, residue-checked produce | A fee on each group lot |
| Cold storages | Filled capacity, advance bookings | A fee per booking |
| Fertilizer and pesticide dealers | Bulk group orders, a demand forecast, verified customers | A subscription or a fee per group order; fair prices |
| Seed and machinery sellers, machinery owners | Verified customers; rental bookings that keep machines busy | A commission per sale or rental booking |
| Agricultural workers and machinery operators | Steady bookings through the season | Their service |
| Government and DAE | Early-warning map, fertilizer demand by week, overcharge and shortage reports, data for policy | A contract for alerts and dashboards; officers as the human contact |

## 5. Business model

**Rule:** advice and alerts are free for farmers and never for sale. A seller's fee never changes what KrishiVault advises; group sales and orders go to the best offer for the farmer.

**Revenue lines (rates to test in the pilot):**
- Group-sale fee paid by the buyer, a small share of the lot value.
- Cold-storage booking fee.
- Marketplace commission on seeds, machinery and inputs, paid by the seller.
- Machinery rental booking fee.
- Dealer subscription or group-order fee.
- Government and NGO contracts for alerts, the officer desk and the DAE dashboard.

**Costs:** calls and SMS (about ৳10 per farmer per season: about 20 minutes at ৳0.4 to 0.55 a minute), servers, the phone line, and field agents for onboarding.

**Why it holds up:**
- The farmer pays nothing.
- Each business pays only when it gains a sale, booking or customer.
- Government pays for the public-good part (alerts, dashboards).

The illustrative farmer gain is large: selling 100 maunds at ৳24 instead of ৳19 a kg is ৳5 × 3,732 kg ≈ ৳18,660 more in one season. Fees are a small share of that value.

## 6. AI and technology, and why

**"AI where language and uncertainty live; fixed rules where money and safety live."**

| Where AI is used | Why it is needed | Guardrail |
|---|---|---|
| Bangla speech recognition | Farmers cannot type | Keypad always works; numbers read back |
| Language understanding (Gemini + Bangla parser) | Colloquial speech: "৫০ মণ উঠছে, ২০ হাজার লাগবে" | Fixed output fields; the parser checks numbers |
| Price forecast and price-crash alerts | Glut and shortage cycles | Used only if it beats simple seasonality in a backtest; uncertainty said out loud; sell-part advice |
| Satellite and weather rules (NASA POWER, IMERG, SMAP, OPERA, HLS) | Alerts for every upazila | Physical rules and published thresholds |
| Demand forecast for dealers and DAE | Fertilizer and seed on time | Crop area × dose × crop calendar |
| Matching (lots to buyers, orders to dealers, rentals to machines) | The best offer for the farmer | Transparent ranking, no paid placement |
| Bangla narration (Gemini + Google voice) | Advice that sounds natural | **Number lock:** the AI cannot change any number from the engine |
| Decision engine | Exact taka outcomes | Deterministic and explainable |

**Safety:** no AI-chosen pesticide names or doses; crop problems get safe first steps and an officer callback. Consent at the start of every call.

**The phone line (production):** a licensed 096 number from a Bangladeshi IP-telephony provider into our own Asterisk call server, with the voice AI on it. Awaj broadcast calls for one-way alerts, REVE for SMS. Details in `PLAN_DETAILS.md`, section 5.

## 7. Execution and scale

| Stage | Scope |
|---|---|
| Prototype (now) | What we show in the competition (section 8) |
| Pilot, one season | 150 to 300 potato farmers in Bogura through the upazila agriculture office, with one buyer, one cold storage, one fertilizer dealer, one seed seller and one machinery service provider |
| District | All Bogura potato upazilas; our own phone line for voice conversation |
| National | With DAE and a2i; more crops (data already covers 13) and districts (data covers all 544 upazilas) |

**Impact to measure in the pilot:**
- **Income:** price received against the DAM benchmark and neighbours; share sold in glut weeks.
- **Inputs:** fertilizer and seed prices paid, and on-time delivery.
- **Crop safety:** sprays per season; storage loss; losses avoided by alerts.
- **Machinery:** hours booked.
- **Understanding:** how often callers press "repeat".

If the money numbers do not move, change the actions offered before adding features.

## 8. The prototype (what we show now)

| Part | Status | How we show it |
|---|---|---|
| Voice conversation | Build | In-app screen: speak Bangla, see the transcript, what was understood and the decision; hear the Bangla reply |
| Keypad flow | Build | The same screen in keypad mode (১ ২ ৩ ৯) |
| Phone calls | Waiting on Awaj | Awaj broadcast call to a judge's phone (text-to-speech or our audio) |
| SMS | Ready to port | REVE SMS (two real sends worked on 8 October from Mati Kohon) |
| Danger alerts | Ready (data) | Pick an upazila: today's NASA alerts from `data/reference/mati_kohon/`; price-crash alert shown as a demo |
| Sell / store decision | Ready | KrishiVault's engine, driven by the conversation |
| Fertilizer need and fair price | Small work | SRDI union cards (6 pilot unions in the data; Bogura to fetch); official prices |
| Seed and machinery marketplace | Mock | A catalog screen: real variety names (BARI and BRRI), clearly fictional demo sellers, a machinery rental booking with the subsidy note |
| Partner screens | Mock | Officer, cold storage, buyer, dealer and seller screens with fictional demo data, updating after a call |
| Government dashboard | Shown | Mati Kohon's NASA map layers as proof the national data exists |

**The demo moment:**
1. A judge's phone rings with a Bangla alert.
2. A teammate speaks to the app as a farmer and gets a taka decision and a cold-storage booking.
3. The SMS arrives.
4. The officer desk and the cold-storage screen update together.

## 9. What is real and what is not

Full check in `docs/readiness_check.html` (updated 14 October). Do not present plan items as finished.

**Real now:**
- NASA late-blight and flood alerts for 544 upazilas.
- The decision engine; SMS; the Bangla voice.
- Crop data for 13 crops, and Bogura potato facts (BBS 2024-25: 56,657 ha, 1.18 million tonnes).
- Cost of production: Agriculture Census 2019, about ৳157,532 per hectare in 2019 prices.
- Official fertilizer prices: urea and TSP ৳27/kg (৳1,350 a bag), DAP ৳21, MoP ৳20. This is the 2023 schedule; confirm the current order.
- Overcharging evidence: Joypurhat, August 2026, urea at ৳1,900 to ৳1,950 a bag.

**Not yet:**
- **AI price forecast:** never trained, too little data. Say "seasonal pattern plus latest prices today".
- **Daily DAM prices:** the downloader is broken because the site moved.
- **Fertilizer cards:** for 6 pilot unions only.
- **The marketplace and partners:** demo data and plan only.
- **Talking to the AI on a real phone call:** plan only.

**Fix before sharing anything:** rename the sample buyer "PRAN Agro", and every sample partner, to clearly fictional names.

## 10. Prototype to-do, in order

1. **Conversation screen** (mobile web):
   - The pipeline: mic → speech-to-text → `intent_parser` + Gemini → decision engine → number check → Google Bangla voice.
   - On screen: transcript, the understood values and the decision.
   - Keypad mode, plus "SMS me" and "Call me" buttons.
   - Browser speech recognition needs HTTPS outside localhost.
2. **SMS and calls:** port `reference/mati_kohon_code/sms.ts` and `awaj.ts` to Python. Dry run by default; live only with the user's go-ahead.
3. **Danger alerts:** read `data/reference/mati_kohon/upazila_conditions.json` and `flood_now.json`.
   - Show today's alerts for any upazila.
   - Add the potato rules (rain before harvest, heat on stored potato, cold and fog) by porting `field_alerts.ts`; late blight is already in the data.
   - Show a price-crash alert as a demo.
4. **Fertilizer:** need from `srdi_frs_doses.csv` and soil classes; the official price; a "price you paid" report. Fetch Bogura cards with the `srdi_frs.py` approach.
5. **Marketplace screens:** seeds (BARI and BRRI variety names; seed potato), machinery rental booking with the subsidy note, clearly fictional demo sellers.
6. **Partner screens:** officer, cold storage, buyer, dealer and seller, each updating straight after a call (a booking, a group lot, an order).
7. **DAM price downloader** to the new site (`https://market.dam.gov.bd/`).
8. **Rename sample partners** to fictional names.
9. **Refresh the NASA files** a day before the demo (in Mati Kohon), then copy them into `data/reference/mati_kohon/`.

## 11. Field work and slides

`docs/KrishiVault_Farmer_Interview_Guide.pdf`: consent script, 26 questions in Bangla with English, a one-page answer form per farmer, a tally sheet, slide templates. Only real farmer answers go on slides.

**Judging criteria:** clarity, depth of problem understanding, solution strength and differentiation, AI application and technical rationale, feasibility and scalability, impact (societal, environmental, business), Q&A. How the plan covers each: `PLAN_DETAILS.md`, section 7.

## 12. Prepared Q&A

| Question | Short answer |
|---|---|
| Isn't this just another agri-information app? | No. It is an ecosystem where every piece of advice ends in an action: a group sale, a booking, an order, a rental. Information alone does not raise farmers' prices; action does. |
| How is it financially sustainable? | The farmer pays nothing. Buyers, cold storages, dealers and sellers pay small fees only when they gain business; government pays for public-good alerts and dashboards. |
| Won't paid sellers bias the advice? | No paid placement: fees never change what the farmer is told; offers are ranked by value to the farmer. |
| Why would farmers trust an AI? | It calls with useful alerts first; numbers come from a checked engine; an officer is one keypress away. |
| What about dadon? | The decision engine accounts for the farmer's dadon debt; group sales and cold-storage bookings give him options beyond selling to his lender at harvest. |
| What if the price forecast is wrong? | We never say "store everything": sell part, say the uncertainty, use forecasts only when they beat seasonality. |
| Bangla dialect speech recognition? | Keypad works for everything; speech is added stepwise and tested on Bogura voices; numbers confirmed. |
| How do you get partners? | Each gets a reason to join: lots, bookings, orders, rentals. One of each in Bogura through the agriculture office. |
| Won't dadon lenders and dealers resist? | Overcharge reports go to DAE; the farmer chooses; we add a cheaper option. |
| How is this different from the Krishi Call Centre (16123)? | We call first, scale with AI, give taka decisions with actions, and hand over to officers. |
| Privacy? | Consent in every call; masked phone numbers on partner screens; individual data never sold. |
| Why potato only? | Potato is the demo hero; the data and engine already cover 13 crops and 544 upazilas. |
