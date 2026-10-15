# KrishiVault: slides and speech (7 minutes)

The deck: `presentation material/KrishiVault_FutureMakers_Pitch.pptx` (10 slides, GP FutureMakers 2026, Round 2). This file is a copy of its speaker notes, built from `scripts/pitch_deck/speaker_notes.js`: edit that file and rebuild the deck, then refresh this one.

3 speakers (A, B, C: put names in). About 770 spoken words at 145 a minute, plus the 34-second farmer clip and a 50-second live demo: about 6:40. The run of show, the evidence and the full Q&A playbook are in `docs/presentation_plan.md`.

Rules on stage: say "statistical outlook", never "AI forecast"; say "demo partners"; say the year with any 2016 figure; never "we destroy the syndicate".

---

## Slide 1: The farmer (field video)

[0:00-0:45 · Speaker A]
**DO:** The slide opens and the clip plays by itself (34 s, English subtitles). Say nothing and do not click while it plays: a click jumps to slide 2. When it ends, the caption fades in. Test the sound on the venue laptop.

**SAY (after the clip):**

"He grows the crop. Someone else gets paid for waiting.
And he can't read a text message, but he takes every call.
We are KrishiVault: we make sure the farmer can wait, with one phone call."

**IF THE VIDEO FAILS:** hold up a button phone. "This is the only device the farmer in our story owns. Everything we show you today works on it." Then click to the next slide.

**ABOUT THE CLIP:** our own field interview, recorded 14 October 2026 (cut from presentation material/IMG_4781.MOV; cuts and subtitles in scripts/pitch_deck/hook_cuts.json). He grows potatoes, maize and rice; uses a button phone and cannot read SMS; sells at the haat and "never makes the money we should"; "some years profit, some years loss". Do not name him without his consent.

---

## Slide 2: The price rise never reaches the farmer

[0:45-1:20 · Speaker A]
**SAY:**

"Every March, a potato farmer in Bogura asks one question: store or sell, and until when?
After a normal crop, the price nearly doubles: 35 taka a kilo in February 2024, 67 and a half by November.
But farmers sell 64 percent of their crop right at harvest, and traders end up with almost everything in cold storage.
The rise is real. It goes to whoever can afford to wait.
And after a big crop, like 2025, it never comes at all."

**POINT AT:** the green line (2024) climbing, the red line (2025) flat.

**IF ASKED:**
- "The study is from 2016?" Yes, and we say so. Today's prices and production are our own data (WFP 2024-26, BBS 2024-25); the field check updates the rest.
- "Why retail prices?" WFP publishes retail; farm-gate moves with it. Real farm-gate history is on our data list.

---

## Slide 3: Three traps

[1:20-2:00 · Speaker A]
**SAY:**

"Why does he sell at the bottom? Three traps.
Cash: his loans and the trader's advance, dadon, fall due the week he harvests.
Flat rent: about 300 taka a sack, for one month or nine. Fear makes him sell after two, having paid for nine.
A blind bet: is this a 2024 or a 2025? Nobody tells him. Storing 36 sacks in 2025 lost up to 25 thousand taka.
A price alert does not pay today's debt. Traders have the cash, the sums and the information. He has none of the three."

**IF ASKED:**
- "Why don't existing apps solve this?" They give information. Information without cash changes nothing at harvest.
- "Where is ৳300 from?" Our field notes and the team plan; some cold storages charge ৳250. Every cost is editable in the engine.

---

## Slide 4: One call: the loop

[2:00-2:40 · Speaker B]
**SAY:**

"KrishiVault gives the farmer what the trader has, in one loop.
He calls with two numbers: sacks harvested and cash needed.
The engine answers in taka: sell 19 sacks now, which covers his 25 thousand, and store 17 until December. Net profit about 13 thousand instead of five and a half.
The cold storage issues a digital receipt in his name. A bank lends against it, so he can wait.
When the price is right, an alert by call or SMS says how many sacks to sell, and to whom. The sale repays the storage, then the bank, then him.
We never lend or hold money. Banks do."

**IF ASKED:**
- "Do you give loans?" No. The bank decides and pays; we verify, value and connect.
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
No deep learning yet: two seasons of prices would overfit.
It's live. Let me show you."

**DEMO (click koryu.ninja, about 50 s):**
1. Top bar: "Live Voice Call". Press the first "Try" sentence: "হামার ৮০ মণ আলু উঠছে, ফড়িয়া ১৬ টেকা দিবার চায়, ২৫ হাজার টেকা নাগবে ৪ দিনের মইধ্যে". Say: "Dialect, understood; every number read back."
2. Press 1. The answer: "Sell 19 sacks now, store 17 until December." Say: "It also tells him the bad case. Nobody else tells a farmer that."
3. Press 2 (cold-storage request) or send the SMS / place the phone call to a teammate's phone.
4. If time: USSD preview, ask a judge for two numbers.
**FALLBACK:** the screen recording in a second tab; if anything stalls 5 s, switch without comment.
Back to the slides with Alt+Tab.

**IF ASKED:**
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

## Slide 8: Execution, scale, business model

[5:10-5:45 · Speaker C]
**SAY:**

"Next harvest we start in Kahaloo, Bogura: 50 to 100 farmers, one or two cold storages, one lender. Then Bogura and Munshiganj, then the country, with onion next.
Farmers never pay a fee. Partners pay only when they gain: 4 percent of the rent from cold storages, one and a half from banks, 1 from buyers, and a share of the voice line with Grameenphone.
20 lakh taka runs the first year. We project break-even around month 15, and the pilot tests it."

**IF ASKED:**
- "Who are your partners?" The prototype uses demo partners, labelled. BKB, BRAC, PKSF, Himadri and PRAN are organizations we will approach, not partners yet.
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
