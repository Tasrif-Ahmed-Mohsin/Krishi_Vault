# KrishiVault: slides and speech (7 minutes)

The deck: `presentation material/KrishiVault_FutureMakers_Pitch_v4.pptx` (10 slides, GP FutureMakers 2026, Round 2). This file is a copy of its speaker notes, built from `scripts/pitch_deck/speaker_notes.js`: edit that file and rebuild the deck, then refresh this one.

3 speakers (A, B, C: put names in). About 790 spoken words at 145 a minute, plus the 34-second farmer clip and a 50-second live demo: about 6:45. The run of show, the evidence and the full Q&A playbook are in `docs/presentation_plan.md`.

Rules on stage: say "statistical outlook", never "AI forecast"; say "demo partners"; say the year with any 2016 figure; never "we destroy the syndicate".

---

## Slide 1: The farmer (field video), then the news and research

[0:00-0:55 · Speaker A]
**DO:** The slide opens and the clip plays by itself (34 s, English subtitles). Say nothing and do not click while it plays: a click jumps to slide 2. When it ends, the caption fades in, then seven cards (four news reports, two studies, our promise), one by one. Start speaking as the first card appears. Test the sound on the venue laptop.

**SAY (after the clip, as the cards come in):**

"He grows the crop. Someone else gets paid for waiting.
And he is not alone. February 2025: farmers selling at half their cost. October: prices crash, and unsold sacks pass to the cold storage. This July: rents up again.
Research has said it since 2014: high rent, an uncertain price, no cash.
We are KrishiVault, and we make sure the farmer can wait."

**IF THE VIDEO FAILS:** hold up a button phone. "This is the only device the farmer in our story owns. Everything we show you today works on it." Click once: the cards still appear.

**THE CARDS (all opened and checked on 16 October 2026):**
- The Business Standard, 13 Feb 2025, "Farmers strain under losses, selling potatoes at half the production cost": farm gate ৳7-9 a kg; cost ৳17.26 (Department of Agricultural Marketing).
- bdnews24, 23 Apr 2025, "Surplus potatoes, empty pockets": record area, cold storages full; farmers allege middlemen bought storage booking slips in advance (a manager denied local farmers were displaced).
- The Daily Star, 15 Oct 2025, "Potato farmers left in the lurch as prices crash": ৳8 a kg wholesale; DAE cost in the north ৳14.5-16; after 15 November unsold stock passes to the cold-storage owners.
- Dhaka Tribune, 1 Jul 2026, "Potato farmers protest cold storage rent hike in Rangpur": rent raised to ৳450 a 50-kg sack; potatoes at ৳14-15 a kg against a ৳25-26 cost.
- BRAC University value-chain study (Bogura, Munshiganj; 2016 fieldwork): farmer ৳480.38, retailer ৳818.50 per 40 kg. Study-period prices; the gap also pays transport, labour and losses, so never call it all trader profit.
- Hajong, Moniruzzaman, Mia, Rahman (2014), "Storage System of Potato in Bangladesh", Universal Journal of Agricultural Research 2(1): Rangpur, 10 cold storages, 20 traders, 30 farmers; farmers cannot use cold storage because of high charges, an uncertain future price and financial insolvency; prices lowest at harvest, peak in December.

**ABOUT THE CLIP:** our own field interview, recorded 14 October 2026 (cut from presentation material/IMG_4781.MOV; cuts and subtitles in scripts/pitch_deck/hook_cuts.json). He grows potatoes, maize and rice; uses a button phone and cannot read SMS; sells at the haat and "never makes the money we should"; "some years profit, some years loss". Do not name him without his consent.

---

## Slide 2: The problem: the numbers and the three traps

[0:55-1:35 · Speaker A]
**SAY:**

"Every March, a potato farmer asks one question: store or sell, and until when?
After a normal crop the shop price nearly doubles. Yet farmers sell 64 percent at harvest, and traders buy almost all that goes into cold storage.
Three traps hold him. Cash: loans and the trader's advance fall due the week he harvests. Flat rent: 300 taka a sack for one month or nine, so fear makes him pay for nine and sell after two. And a blind bet: 2024 doubled, 2025 never rose. Nobody tells him which year it is.
A price alert does not pay today's debt."

**IF ASKED:**
- "The study is from 2016?" Yes, and we say so. Today's prices and production are our own data (WFP 2024-26, BBS 2024-25), and the 2025 news shows the same pattern.
- "Why retail prices?" WFP publishes retail; farm-gate moves with it. Real farm-gate history is on our data list.
- "The news says ৳450 a sack, you say ৳300?" ৳300 for an 84-kg sack is the plan's figure; rents differ by district and sack size and are rising. Every cost is editable in the engine, and the field check sets this season's.

---

## Slide 3: What KrishiVault is

[1:35-2:10 · Speaker A]
**SAY:**

"So what is KrishiVault? A voice-first service for potato farmers. It tells him how many sacks to sell now and how many to store, until when, and lets a bank lend against the stored sacks, so he can afford to wait.
Every trap gets an answer: cash without selling, the sums sack by sack, an outlook with a range, and a voice call, because he can't read an SMS.
Farmers never pay. Cold storages, banks and buyers do."
**HAND OVER:** "B will walk you through one season."

**IF ASKED:**
- "Isn't this just another agri app?" No app: a voice call, USSD and SMS on any phone, and the cash through a bank. An app gives information; information without cash changes nothing at harvest.
- "Do you give loans?" No. The bank decides and pays; we verify, value and connect, and never hold money.

---

## Slide 4: One farmer, one season (the loop)

[2:10-2:40 · Speaker B]
**SAY:**

"One farmer, one season. He calls with two numbers: 36 sacks, and 25 thousand taka needed this week.
The engine answers: sell 19 now, which covers his 25 thousand; store 17 until December. Net profit about 13 thousand, not five and a half.
The cold storage issues a receipt in his name; a bank lends against it.
When the price is right, an alert says how many to sell and to whom. The sale repays the storage, then the bank, then him."

**IF ASKED:**
- "Where do these numbers come from?" The engine, with the plan's costs (৳300 rent, 8.65% weight loss) and a ৳14 a kg growing cost (DAE Bogura 2024-25); the farmer's own figures replace them.
- "Won't partner fees bias the advice?" No paid placement: buyers are ranked by money left in the farmer's hand.

---

## Slide 5: AI and technical rationale, live demo

[2:40-4:05 · Speaker B · about 35 s talk, then a 50 s demo]
**SAY:**

"The farmer in our video can't read an SMS, so KrishiVault starts with his voice.
AI where language and uncertainty live; fixed rules where money lives.
AI listens: Google's Bangla speech and our own dialect parser. Gemini only fills gaps, and every number must have been said.
The decision is statistics and exact sums: 2,000 simulated price paths driven by the crop size, then rent, weight loss and interest.
AI speaks under a number lock: change one figure and the answer is thrown out.
It's live. Let me show you."

**DEMO (click koryu.ninja, about 50 s):**
1. Top bar: "Live Voice Call". Press the first "Try" sentence: "হামার ৮০ মণ আলু উঠছে, ফড়িয়া ১৬ টেকা দিবার চায়, ২৫ হাজার টেকা নাগবে ৪ দিনের মইধ্যে". Say: "Dialect, understood; every number read back."
2. Press 1. The answer: "Sell 19 sacks now, store 17 until December." Say: "It also tells him the bad case. Nobody else tells a farmer that."
3. Press 2 (cold-storage request) or send the SMS / place the phone call to a teammate's phone.
4. If time: USSD preview, ask a judge for two numbers.
**FALLBACK:** the screen recording in a second tab; if anything stalls 5 s, switch without comment.
Back to the slides with Alt+Tab.

**IF ASKED:**
- "Why not deep learning?" Two seasons of clean prices: XGBoost or LSTM would overfit. They come once 15 years of DAM prices are loaded and they beat today's outlook on past seasons.
- "Which AI exactly?" Google speech-to-text and text-to-speech (Bangla), Gemini Flash for understanding and rewording; the outlook is a statistical simulation; the decision is deterministic.
- "Can the AI get a number wrong?" It cannot reach the farmer: numbers must have been said on the way in, are read back for a keypad yes, and the number lock checks every figure on the way out.
- "Is it a chatbot?" No, a guided call: it asks only what it needs, reads it back, answers in taka with the risk.

---

## Slide 6: Proof: two real seasons

[4:05-4:40 · Speaker B]
**SAY:**

"Does it work? We replayed two real seasons with only what was known at harvest.
2024, a normal crop: sell 11, store 25. Net profit two and a half times higher.
2025, a big crop: sell now. Storing would have lost up to 25 thousand taka. An advisor that says 'don't store' is one you can trust.
The outlook missed by 11 percent, against 52 for the usual seasonal pattern. Two seasons is a first test, not proof."

**IF ASKED:**
- "Two seasons: why trust it?" We don't ask you to. It gives a range, shows the bad case, never bets the whole crop on one month (30-40% sold at harvest), and in a glut year banks lend at most 50%.
- "Storing everything in 2024 would have made more?" Yes, about 3.4 times, but nobody could know that in March. Our rule never bets the whole crop.

---

## Slide 7: Differentiation and defensibility

[4:40-5:10 · Speaker B]
**SAY:**

"Traders give cash, but at the harvest low. Price apps give a price, but no cash. Banks have cash, but can't check a farmer's potatoes.
Only KrishiVault closes the loop, and that is hard to copy: cold storages and banks both earn by staying in it, and every consented call adds data nobody else has.
Receipt lending already lets farmers wait in India. Bangladesh already has the cold storages."

**IF ASKED:**
- "Why would cold storages join, when early turnover helps them?" Group bookings fill space early, verified receipts bring them loan customers, fees are collected at the sale, and we track only our tagged sacks, not their books.
- "Why would banks lend against potatoes?" A named, weighed receipt from a verified cold storage, sacks held for the bank, valued at the low price after the 8.65% loss, and the sale repays the bank first.

---

## Slide 8: Execution: potato first, then expand; the business model

[5:10-5:45 · Speaker C]
**SAY:**

"We start with potato, the biggest stored crop with the clearest trap, in Kahaloo, Bogura: 50 to 100 farmers, one or two cold storages, one lender. Then Bogura and Munshiganj, then the country.
After potato, the same engine takes onion, then maize and any stored crop: only the costs and prices change.
Farmers never pay a fee. Partners pay only when they gain: 4 percent of the rent from cold storages, one and a half from banks, 1 from buyers, and a share of the voice line with Grameenphone.
20 lakh taka runs the first year. We project break-even around month 15, and the pilot tests it."

**IF ASKED:**
- "Who are your partners?" The prototype uses demo partners, labelled. BKB, BRAC, PKSF, Himadri and PRAN are organizations we will approach, not partners yet.
- "Why potato first?" It is the biggest stored crop (11.6 million tonnes, BBS 2024-25), with the clearest storage trap, and Bogura alone grows 10% of it. Onion is next: home storage of 2 to 3 months and a different season, but the same sums. Our production data already covers all 64 districts.
- "What could kill this?" Partners refusing the fees. The pilot measures it: price received against neighbours, loans used instead of early sales, and repayment.

---

## Slide 9: Impact

[5:45-6:15 · Speaker C]
**SAY:**

"For one farmer: two and a half times the profit in a normal year, and no storage loss in a glut.
At year-three scale, about 118 crore taka more to farmers in a normal year. An illustration, not a forecast.
Less food wasted, because nobody stores into a glut. And stock the government can finally see, with the farmer's consent.
All on a button phone like his, in his own dialect."

**IF ASKED:**
- "If every farmer stores, won't the rise disappear?" Partly, and that is the point: the gap shrinks and moves to farmers, and consumers see smoother prices. We never advise the whole crop, and the government screen watches stored stock.
- "Privacy?" Counted only after the farmer presses 8; no names or numbers; districts with fewer than 5 farmers are hidden.

---

## Slide 10: Close and the ask

[6:15-6:35 · Speaker A; about 20 s spare]
**SAY:**

"Next March, he will ask the same question. This time he gets the sums, the cash to wait, and a receipt with his own name on it.
আলু রাখবেন না বেচবেন, কবে বেচবেন: হিসাব করে বলে কৃষিভল্ট।
Help us open the first cold storage and the first lender in Kahaloo. Thank you."

**Q&A RULES (3 minutes):** the answer in the first sentence, one number, under 25 seconds, then bridge back to something they saw. If we don't know: "We don't know yet; the pilot measures it this way." Never argue. Full playbook: docs/presentation_plan.md.

---
