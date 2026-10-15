# KrishiVault: slides and speech (7 minutes)

10 slides, 3 speakers (A, B, C: put names in). About 900 words in total, at a calm 130 words a minute. Rehearse to 6:40. The run of show, the evidence and the Q&A answers are in `docs/presentation_plan.md`.

Rules on stage: say "statistical outlook", never "AI forecast"; say "demo partners"; say the year with any 2016 figure; never "we destroy the syndicate".

---

## Slide 1: the farmer (0:00–0:35) · Speaker A

**On screen:** dark screen; the field video (20–25 s, his own words, English subtitles). Freeze on his face with one number:
- his own number, if the clip has one; otherwise:
- **"In the shops: about ৳35 a kg in February 2024. ৳67.50 by November." (WFP)**

**Speech (after the clip):**
> He grew the potatoes. Someone else got paid for waiting.
> We are KrishiVault, and we make sure the farmer can wait.

---

## Slide 2: three traps (0:35–1:45) · Speaker A

**On screen:** three columns.
1. **Flat rent:** ৳300 a sack, for 1 month or 9.
2. **Crop size sets the price:** 2024 prices doubled; 2025, a big crop, stayed at ৳20–25 all year (WFP price chart, 2024 against 2025).
3. **Cash at harvest:** 64% sold at harvest; traders hold 97.6% of cold-stored potatoes (field study, 2016).

**Speech:**
> Every March, a potato farmer in Bogura asks one question: store or sell, and until when?
> He is caught in three traps.
> First, the rent. A cold storage charges about 300 taka a sack, the same for one month or nine. So if fear makes him sell after two months, he has paid for nine.
> Second, he can't see the price coming. In 2024 prices doubled after the harvest. In 2025 the crop was big and prices stayed flat all year. Storing was a gamble he could win or lose by thousands of taka.
> Third, cash. Loans and school fees fall due at harvest. A field study found farmers sell 64 percent of their crop at once, and traders end up holding almost all of the stored potatoes.
> So the rise after the harvest exists. It just doesn't reach him.

---

## Slide 3: the turn (1:45–2:10) · Speaker A

**On screen:** "Not a production problem. A waiting problem." Under it, three levers: **Cash · Information · Untraceable stock.**

**Speech:**
> Bangladesh grew 11.6 million tonnes of potato last season. This is not a production problem. It is a waiting problem.
> In 2023 a commerce ministry study blamed a cold-storage syndicate and found stored potatoes behind slips with no owner's name. The association denied it. We don't accuse anyone. We take away the levers: the forced sale, the information gap and stock nobody can trace.
> [Hand over:] B will show you how.

---

## Slide 4: the answer (2:10–2:30) · Speaker B

**On screen:** four words: **Know · Calculate · Decide · Act.** Speaker B holds up a button phone.

**Speech:**
> KrishiVault gives the farmer what the trader has: the sums, the cash to wait, and a receipt with his own name on it.
> Know the price outlook. Calculate rent, losses and interest. Decide how much to sell and when. Act: book space, get a bank loan, find the best buyer.
> All of it works on this phone. No app, no internet.

---

## Slide 5: live demo (2:30–4:15) · Speaker B

**On screen:** the prototype. A teammate speaks as the farmer. Fallback: the 90-second recording in a second tab; switch without comment if anything stalls 5 seconds.

| Time | Do | Say |
| --- | --- | --- |
| 0:00 | `/call`, season "Next harvest". Press the first "Try" sentence (36 sacks, ফড়িয়া ১৬ টেকা, ২৫ হাজার, ৪ দিনে). | "He speaks in his own dialect. It understands, and reads every number back to him." Press 1. |
| 0:30 | The answer. | "Sell 19 sacks now: that pays the 25,000 he needs. Store 17 until December. On average 54,700 taka; net profit 12,900 against 5,600 if he sells everything today. And it tells him the bad case. Nobody else tells a farmer that." |
| 0:55 | Press 2: cold-storage space; show the SMS. | "One key books his space." |
| 1:05 | Dashboard, Partner screens: issue the receipt, the bank approves, payout SMS. | "The ministry found stock behind slips with no name. This receipt has his name and the weight. The bank lends against it, and when he sells, the bank is repaid first, then he is paid." |
| 1:25 | `/ussd`: ask a judge "How many sacks, and how much cash does he need?" Type the two numbers. | "Two numbers, any phone, no internet." |

Setup: Gemini on through a phone hotspot. Without it, the call asks for the price: type 16# and say "the keypad always works". SMS in dry run. Demo data cleared. Zoom 125%.

---

## Slide 6: proof without hindsight (4:15–4:55) · Speaker B

**On screen:** two cards and one line.
- **2024 (normal crop):** sell 11, store 25 → net profit **৳11,740 → ৳29,450 (2.5×)**.
- **2025 (big crop):** "Sell now." Storing would have lost **৳17,100–25,300**.
- Price miss: **11% vs 52%** for "same as today". Two seasons only.

**Speech:**
> Does it work? We replayed two real seasons, using only what was known on harvest day.
> In 2024, a normal crop, it said store part. The farmer's net profit was two and a half times higher.
> In 2025, a big crop, it said sell now. Storing would have lost him 17 to 25 thousand taka. An advisor that tells you not to use storage is one you can trust.
> Its price outlook missed by 11 percent on average, against 52 for "the price stays the same". It's two seasons, so we call it a statistical outlook, and we will test it on fifteen years of government prices next.

---

## Slide 7: why this AI (4:55–5:30) · Speaker B

**On screen:** simple picture: **Farmer's voice → AI understands → engine does the sums → number lock → AI speaks.** Below it: Today: browser speech recognition (Bangla), Gemini, Google voice, SMS. Pilot: Grameenphone voice line, USSD and SMS.

**Speech:**
> We use AI where it is strong, and rules where money is at stake.
> AI listens to Bangla dialect and speaks the answer. The decision is exact sums over 2,000 simulated price paths, with rent, the 8.65 percent storage loss and interest.
> And a number lock: if any AI changes a single taka figure, the answer is thrown out and the fixed wording is used. A farmer never hears a number the engine did not produce.
> [Hand over:] C will show how we get it to farmers.

---

## Slide 8: execution and money (5:30–6:15) · Speaker C

**On screen:** a rollout line: **Kahaloo pilot → Bogura and Munshiganj → national.** Money tiles: cold storage 4% of rent (৳12 a sack) · bank 1.5% (৳4.50 a financed sack) · buyer 1% (about ৳12 a sack) · Grameenphone call-revenue share · data for government and media. **৳20 lakh start-up · break-even in year 2 (projection).** A small line: working prototype, 157 tests.

**Speech:**
> We start in Kahaloo, Bogura: one cold storage, one lender, our field agents at the haat. Then Bogura and Munshiganj, then the country.
> Farmers pay nothing beyond the call. Partners pay only when they gain: cold storages get full space and fees collected at the sale, banks get stock they can check, buyers get clean lots.
> We need 20 lakh taka to run the first year, and we break even in year two. That's a projection.
> The prototype you just saw is real: the engine, the call, the USSD menu, with demo partners clearly labelled.

---

## Slide 9: impact (6:15–6:45) · Speaker C

**On screen:** three numbers.
- **2.5×** net profit for a farmer in a normal year; **no storage loss** in a glut year.
- **About ৳118 crore** more to farmers at year-3 scale (2.4 million sacks × the 2024 replay): *an illustration, not a forecast.*
- **Stock the government can see:** a glut warning and district figures from farmers who agreed.

**Speech:**
> For one farmer: two and a half times the profit in a normal year, and no storage loss in a glut year.
> At our year-three scale, the 2024 replay would mean about 118 crore taka more in farmers' hands. That's an illustration, not a forecast.
> Less waste, because nobody stores into a glut. And for the first time, the government sees stored stock and farmers' cash needs, district by district, with the farmer's consent.

---

## Slide 10: close (6:45–7:00) · Speaker A

**On screen:** the same frozen frame of the farmer from slide 1, now with his answer beside it: "Sell 19 now, store 17 until December." The line: **আলু রাখবেন না বেচবেন, কবে বেচবেন: হিসাব করে বলে কৃষিভল্ট।**

**Speech:**
> Next March, this farmer will ask the same question. This time, he gets an answer, the cash to wait and a receipt with his name on it.
> আলু রাখবেন না বেচবেন, কবে বেচবেন: হিসাব করে বলে কৃষিভল্ট।
> Thank you. We'd like your help to open the first cold storage and the first lender in Kahaloo.

---

### Before the day
- If his clip has no number, use the WFP shop prices on slide 1. WFP has shop prices only; a farm-gate figure must come from the video or a source you have opened.
- Check the news figures on slides 2–3 (links in `docs/presentation_plan.md`, Sources).
- If the demo season or data changes, re-read the numbers on slides 5, 6 and 10 from the screen.
