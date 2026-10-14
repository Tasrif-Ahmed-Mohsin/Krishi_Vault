# KrishiVault handoff (14 October 2026)

Everything decided so far, in one place, so work can continue in a cloud session.

## 1. The idea

**KrishiVault is a free voice line that protects a farmer's money through the whole season.** A farmer with a button phone talks or presses keys. KrishiVault warns him before weather or disease costs him money, tells him in taka what to buy, when to sell and when to store, and connects him to the cold storage, buyer, fertilizer group or lender that makes it happen.

> ফোনে বলুন — ফসলের দাম আর টাকা দুটোই বাঁচান।

**Why this design:** research shows market-price information alone rarely raises what farmers are paid (Fafchamps and Minten, India; Aker and Fafchamps, Niger). Gains come when information changes bargaining or lets the farmer act (Shimamoto and others, Cambodia). So every piece of advice ends with something the farmer can do.

**Three money leaks:** buying inputs (fertilizer overcharged, doses guessed), protecting the crop (calendar spraying, late blight), selling (glut, dadon, no storage). **Two barriers:** button phones and literacy; no way to act on information.

## 2. The plan (the complete product)

| Service | What the farmer hears | What he can do in the call |
|---|---|---|
| 1. Danger alerts | Late blight, rain before harvest, heat on stored potato, cold and fog, flood, price crash; "no spray needed" in quiet weeks | Repeat; officer callback |
| 2. Sell / store / group | Taka for each option, his cost-of-production floor, a sell-part safety net | Book cold storage; join a group lot |
| 3. Inputs | Fertilizer sacks for his crop and soil, fair price, buy-by date; spray only when weather says so | Join a group buy; report the price paid |
| 4. Credit instead of dadon | A loan offer from a partner lender, based on his khata | Request the loan |
| 5. কৃষি খাতা | Season summary: spent, saved, sold, owed | Confirm entries; becomes his credit history |

Plus **farmer reports by keypad** (price got, fertilizer price paid, disease seen) feeding the forecasts and a DAE map.

**How farmers use it:** free (missed call, then we call back), keypad menu (১ দাম ও পরামর্শ, ২ সার, ৩ আমার খাতা, ৯ কর্মকর্তা), Bangla voice, an SMS receipt after each call. **The farmer never types.** Dealers, cold storages, buyers and the SAAO record against his phone number and he confirms by keypad.

**Phone number as ID:** the number links to an internal farmer record. One number can hold several farmers (shared phone menu); a SIM change moves the record; a 4-digit keypad PIN protects the khata and bookings; every entry made by a helper needs the farmer's keypad confirmation.

**Helper portals (web, not for farmers):** SAAO desk, cold storage, buyer, dealer, lender, DAE map. All write to the same farmer record.

**AI, and why:** "AI where language and uncertainty live; fixed rules where money and safety live."
- Speech recognition (Bangla), always with keypad fallback and number read-back.
- Gemini for understanding colloquial Bangla, with fixed output fields.
- Price forecast only if it beats simple seasonality in a backtest; uncertainty said out loud; sell-part advice.
- NASA satellite and climate rules for alerts (published thresholds).
- Gemini wording with a **number lock**; Google Bangla voice.
- The decision engine is deterministic and explainable.

**Phone line architecture (production):** licensed IPTSP SIP trunk (096 number) into Asterisk on a Linux cloud server; Python voice service talks to Asterisk through ARI. The pipeline: turn detection, speech-to-text, Bangla parser and Gemini, engine, number check, Google voice. Awaj broadcast stays for one-way alerts; REVE for SMS. Do not use GSM/SIM gateways (treated as illegal VoIP in Bangladesh). Secure the server before connecting a trunk (firewall SIP to the provider's IPs, fail2ban, no guest calls, outbound cap). Incoming calls cost the farmer, so use missed call and callback.

**Execution:** prototype now; pilot of 150 to 300 potato farmers in Bogura through the upazila agriculture office with one cold storage, one buyer, one dealer and one lender; then district; then national with DAE and a2i. Data already covers 544 upazilas and 13 crops. Calls cost about ৳10 per farmer per season (about 20 minutes at ৳0.4 to 0.55 a minute).

**Impact to measure:** price received against the DAM benchmark and neighbours, share sold in glut weeks, fertilizer price paid, sprays per season, storage loss, dadon share, how often callers press "repeat".

## 3. The prototype (what we show now)

| Part | Status | How we show it |
|---|---|---|
| Voice conversation | Build | In-app screen: speak Bangla, see the transcript, see what was understood, see the decision, hear the Bangla reply |
| Keypad flow | Build | Same screen, keypad mode (১ ২ ৩ ৯) |
| Phone calls | Waiting on Awaj | Awaj broadcast call to a judge's phone |
| SMS | Ready | REVE SMS (two real sends worked on 8 October from Mati Kohon) |
| Danger alerts | Ready (data) | Pick an upazila: today's NASA alerts (from Mati Kohon's daily files) |
| Sell / store decision | Ready | KrishiVault's engine, driven by the conversation |
| Fertilizer need | Small work | Bogura SRDI cards still to fetch |
| Khata, credit view | Mock | Officer page and lender view update after the call |
| Partner portals | Mock | Cold storage, buyer, dealer with clearly fictional demo data |

**The demo moment:** a judge's phone rings with a Bangla alert; a teammate speaks to the app as a farmer and gets a taka decision and a cold-storage booking; the SMS arrives; the officer page updates.

## 4. What is real and what is not (checked 13 October)

Full detail in `docs/readiness_check.html`. Summary: 13 claims ready, 5 small work, 1 waiting, 3 example data only, 10 plan only.

**Ready:** NASA late-blight and flood alerts for 544 upazilas; the decision engine; SMS; the Bangla voice; crop data for 13 crops; Bogura potato facts (BBS 2024-25: 56,657 ha, 1.18 million tonnes); cost of production (Agriculture Census 2019, about ৳157,532 per hectare in 2019 prices); official fertilizer prices (urea and TSP ৳27/kg or ৳1,350 a bag, DAP ৳21, MoP ৳20, the 2023 schedule; confirm with the Ministry's current order); overcharging evidence (Joypurhat, August 2026: urea ৳1,900 to ৳1,950 a bag).

**Must not be claimed as done:**
- The AI price forecast: never trained; too little data. Say "seasonal pattern plus latest prices today".
- Daily DAM prices: the downloader is broken (site moved). Say "monthly prices now".
- Fertilizer advice for every union: only 6 pilot unions fetched. Say "from SRDI's official union cards".
- Partners and loans: demo data and an idea only.
- Talking to the AI on a real phone call: plan only.

**Fix before sharing anything:** rename the sample buyer "PRAN Agro" (and every sample partner) to clearly fictional names.

## 5. Prototype to-do, in order

1. **KrishiVault conversation screen** (mobile web): mic, then speech-to-text, then `intent_parser` + Gemini, then decision engine, then number check, then Google Bangla voice. Show transcript, understood values ("৫০ মণ, ২০,০০০ টাকা, ৩ দিন") and the decision. Add keypad mode, and "SMS me" / "Call me" buttons. Browser speech recognition needs HTTPS outside localhost; downsample to 8 kHz before speech-to-text when testing phone realism.
2. **Real Awaj test call** once the broadcast permission arrives (text-to-speech broadcast `/broadcasts/direct-tts`, or audio broadcast `/broadcasts/direct` with a public audio URL). Port `awaj.ts` from Mati Kohon. Live only with the user's go-ahead.
3. **SMS:** port `sms.ts` (REVE `GET /sendtext`, numbers as 8801XXXXXXXXX, Unicode Bangla in 70 and 67-character parts). Dry run by default.
4. **Bogura SRDI fertilizer cards** for the potato unions, including Sariakandi, using Mati Kohon's `research/acquire/srdi_frs.py` approach.
5. **Potato alerts:** rain before harvest, heat on stored potato, cold and fog, from the forecast and temperatures in Mati Kohon's `upazila_conditions.json`. Late blight is already there.
6. **DAM price downloader** to the new site.
7. **Refresh the NASA alert and flood files** a day before the demo (in Mati Kohon).
8. **Potato safe first steps** for pests and disease, from BARI's guidance.
9. **Example screens:** officer record (khata), cold storage, buyer, lender.

## 6. Field work and slides

`docs/KrishiVault_Farmer_Interview_Guide.pdf` holds the consent script, 26 questions (Bangla with English), a one-page answer form per farmer, a tally sheet, and slide templates. Only real farmer answers go on the slides; never invent quotes or numbers.

The judging criteria: clarity, depth of problem understanding, solution strength and differentiation, AI application and technical rationale, feasibility and scalability, impact (societal, environmental, business), Q&A.

## 7. Prepared Q&A

| Question | Short answer |
|---|---|
| Why would farmers trust an AI? | It calls with useful alerts first; numbers come from a checked engine; an officer is one keypress away. |
| What if the price forecast is wrong? | We never say "store everything": sell part, say the uncertainty, use forecasts only when they beat seasonality. |
| Bangla dialect speech recognition? | Keypad works for everything; speech is added stepwise and tested on Bogura voices; numbers confirmed. |
| How do you get partners? | Each gets something: bookings, ready lots, verified borrowers. One of each in Bogura through the agriculture office. |
| Won't dadon lenders and dealers resist? | Overcharge reports go to DAE; the farmer chooses; we add a cheaper option. |
| How is this different from the Krishi Call Centre (16123)? | We call first, scale with AI, give taka decisions with actions, and hand over to officers. |
| Who pays? | Alerts by government or NGO partners; booking, group-sale and loan-referral fees. About ৳10 per farmer per season. |
| Privacy? | Consent in every call; PIN for money matters; masked numbers in portals; individual data never sold. |
| Why potato only? | Potato is the demo hero; the data and engine already cover 13 crops and 544 upazilas. |
