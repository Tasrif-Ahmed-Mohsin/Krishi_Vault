# KrishiVault plan details

The parts of the plan that `HANDOFF.md` only summarizes. Read `HANDOFF.md` first.

## 1. One farmer, one calendar, one record, pillars that move together

```
                  Farmer: upazila, plots (crop, area, sowing date, land type), dadon
                                              │
     Crop knowledge base (13 crops' traits)   │   Place: soil, flood exposure, dealers, cold storages, sellers
                          └───────────────────┼────────────────────┘
                                   Crop calendar (stage of every plot today)
                                              │
   ┌───────────────┬──────────────────┬───────┴──────────┬────────────────┬──────────────┐
 Sell for best   Fertilizer and     Seeds, machinery   Danger alerts     Fair credit
 value           pesticide supply   marketplace        (weather, flood,  (instead of
                                                        disease, price)   dadon)
   └───────────────┴──────────────────┴───────┬──────────┴────────────────┴──────────────┘
                     The farmer's record (কৃষি খাতা) and an event bus: one event updates every pillar
```

**The marketplace in the season:**
- **Before planting:** certified seed potato and improved varieties, fertilizer as a group order, a power tiller to rent.
- **At harvest:** a harvester, reaper or digger to rent, booked by the bigha.
- **After harvest:** storage bags, and the cold-storage booking.

Machinery owners and operators get steady bookings, and smallholders get machines they could never buy. Subsidy information comes from the DAE machinery programme; verify current terms before quoting a rate.

**How one event moves every module:**

| Event | Danger alert | Inputs | Market and storage | Ledger |
|---|---|---|---|---|
| Flood water rising | "25% of your upazila under water" | Hold fertilizer purchase and top-dressing; seed order moves to the drain date | Home-stored potato and seed at risk: move it or sell part; transport may be cut | Loss avoided; damage note for dadon talks |
| Late-blight weather | "Walk your potato field" | Fungicide only if spots are seen; buy one pack, not a season's stock | Residue clock for premium buyers | Spray saved, or spray cost |
| Heat wave (April) | "Heat on stored potato" | none | Spoilage up, so store-or-sell is recalculated | Loss avoided |
| Rain before harvest | "Dig before Thursday" | none | Wet tubers stored are marked higher-risk | none |
| Urea overcharging reported | none | Fair-price message; group buy offered | Production cost up, so the floor price rises | Extra cost recorded |

**Depth by crop:** potato is the hero (all modules, deepest). The 13 crops with full traits get fertilizer need, crop-stage alerts, market prices and the ledger: Boro, Aman, Aus, wheat, maize, mustard, lentil, mungbean, grass pea, jute, dhaincha and fodder, as well as potato. All 23 crops in the BBS district table are catalogue information.

## 2. Demo story: Abdur Rahim in Sariakandi (char land, button phone)

Real reading from Mati Kohon's NASA OPERA data on 1 October 2026: 25% of Sariakandi's land under water, against 14% by radar at the same time last year; in 2025, 80% of the monsoon water drained only by 19 January.

| When | On his phone | Behind it |
|---|---|---|
| Oct | Flood alert; plant after the water leaves; keep seed in cold storage | OPERA flood reading; storage cost added to his plan |
| Nov | Fertilizer need for 2 bigha; fair price; press 1 to join a group buy | Dealer delivers and records the sale; SMS receipt; ledger entry |
| Dec–Jan | Late-blight weather alerts; "no spray needed" in quiet weeks | Disease weather; spray saved |
| Feb | Rain before harvest; sell/store call with his cost floor | Decision engine; cold-storage booking |
| Apr | Heat wave: selling 20 maunds now is better by ৳Y | Heat-aware spoilage |
| Season end | "This season KrishiVault saved you ৳Z" | Ledger summary |

## 3. The ledger fills itself (the farmer never types)

Each entry comes from the easiest reliable source, in this order:

1. The system: alerts sent, advice given, sprays skipped, losses avoided, the day's price.
2. The other side of the deal: dealer sale, cold-storage slip, buyer or group-leader sale, recorded against his phone number.
3. A keypad confirmation in a call: "Recorded 2 bags of urea at ৳X. Correct? Press 1."
4. Keypad numbers, only for what nobody else knows (a private sale, dadon).
5. A short spoken answer, always read back and confirmed by keypad.
6. Assisted entry by the SAAO, union digital centre or group leader, with the farmer's consent.

Each entry stores its source and whether the farmer confirmed it.

## 4. Rules for every call

- One action per call, 60 to 90 seconds; numbers in bigha, maund, bosta and taka.
- Keypad first, speech second; every number read back.
- Every call ends with "১ = আবার শুনুন, ৯ = কর্মকর্তা ফোন করবেন" (1 to hear it again, 9 for an officer to call back).
- Never ask what a dealer, cold storage or buyer can record instead.
- Urgent alerts go out at once; others in the evening, when farmers are home.
- The farmer pays nothing: missed call, then we call back.

## 5. The phone line where the AI listens

**Why Awaj alone can't do it:** Awaj gives one-way calls (its own voice or our audio) and keypad surveys with pre-recorded prompts. It has no speech recognition and no live audio stream. Keep Awaj for mass alerts; add our own voice server for conversations.

**Telephony options:**

| Option | How | Use |
|---|---|---|
| A. Local SIP trunk (production) | Licensed Bangladeshi IPTSP gives a 096 number over a SIP trunk into our Asterisk server | Local number, local rates; needs provider KYC (NID, licence or project letter, static IP) |
| B. Twilio | Twilio Media Streams sends live call audio to our server | Prototype only: about $0.06/min to Bangladeshi mobiles, roughly 13 times Awaj; local number stock unclear |
| C. Hybrid | An Awaj call ends with "press 1 to talk to KrishiVault" and transfers to our number | Awaj for volume, our server for conversation |

**Do not use** a GSM gateway (GoIP) with a GP or Teletalk SIM: treated as illegal VoIP in Bangladesh, operators block such SIMs, and it handles one call at a time.

**The listening pipeline:**

```
Farmer's phone → SIP trunk → Asterisk (ARI from Python) → live audio + keypad presses
→ turn detection (~0.7 s silence; the farmer can interrupt)
→ speech-to-text: Google bn-BD (chirp_2), Whisper large-v3 tested on the same audio
→ understanding: KrishiVault's Bangla parser for numbers and units, then Gemini with fixed output fields
→ dialogue state machine: asks for missing values, reads numbers back, keypad always works,
  two failures → keypad menu → officer callback
→ engine (decision, alerts, fertilizer, ledger) → Bangla template filled with the engine's numbers
→ number check (Gemini may reword, never change a number) → Google bn-BD voice → back into the call
```

About 2 to 4 seconds per turn; a short filler ("একটু শুনুন, হিসাব করছি…") covers the wait. Use this step-by-step pipeline, not one speech-to-speech AI, because every taka figure must be checked before the farmer hears it. Google lists bn-BD on chirp_2; phone-audio and streaming support for Bangla were not confirmed, so recognize each answer after the farmer stops speaking first.

**Build steps:**

| Step | What | Done when |
|---|---|---|
| V0 | Awaj one-way calls and keypad surveys; `call_simulator.py` as the test harness | Keypad flows work end to end on real phones |
| V1 | Record-and-reply on Twilio (prototype) or Asterisk with a SIP trunk | 200 consented answers from Bogura farmers, measured for word error and task success |
| V2 | Live streaming, turn detection, barge-in, filler audio, keypad in parallel | A full harvest-decision call without keypad fallback for most farmers |
| V3 | Phrase hints, a fine-tuned Whisper on farmer audio, a Gemini Live trial | Measured gain over V1 |

**Security before connecting a trunk:** firewall SIP and call-audio ports to the provider's IPs only; fail2ban; no guest calls; strong credentials; ARI bound to localhost; a daily outbound-minutes cap. A hijacked trunk can run up large call bills.

**Reliability:** auto-restart (Docker or systemd), health checks, daily backups; if the server is down, the trunk forwards to an officer's phone (ask the provider); if the AI fails, fall back to the keypad menu.

**Testing without a telecom line:** a small cloud Linux VM with Asterisk plus the Zoiper softphone on a phone gives real SIP and phone-quality audio. A browser "phone" page is fine for demos, but needs HTTPS for the microphone and 8 kHz downsampling for realistic speech tests. Skip ADB dialing from a personal SIM.

## 6. Risks, and how we answer them

| Risk | Fix |
|---|---|
| No action partners: advice alone changes little | Sign one buyer and one cold storage before scaling |
| A wrong "store" call | Sell part, store part; say the uncertainty; forecasts only if they beat seasonality |
| Too wide for a small team | Build the prototype scope first; the rest is the roadmap |
| Helpers won't use portals | Each gets a reason: volume for dealers, bookings for cold storages, lots for buyers; overcharge reports go to DAE |
| Bangla speech on phone lines | Keypad first; voice added stepwise and measured |
| Who pays | Alerts by government or NGO; fees on bookings, group sales and loan referrals |
| Rules and trust | Consent in every call, BTRC-compliant numbers, officer callback always available |

**Go/no-go after one pilot harvest:** pilot farmers' price against the DAM benchmark and neighbours, share sold in glut weeks, fertilizer price paid, sprays, storage losses, "repeat" presses. If the money numbers don't move, change the actions offered, not the features.

## 7. How the plan covers the judging criteria

| Criterion | Where we win it |
|---|---|
| Clarity | One sentence, three leaks, five services, one demo |
| Problem depth | Three money leaks plus two barriers; research on why information alone fails; real Bogura numbers |
| Differentiation | Decision plus action in the same call; button-phone voice; the khata as credit history against dadon; NASA alerts per upazila |
| AI rationale | AI where language and uncertainty live, fixed rules where money and safety live; number lock; honest forecast backtest |
| Feasibility and scale | Working prototype; Bogura pilot with named partner types; about ৳10 per farmer a season; data for 544 upazilas and 13 crops |
| Impact | Income, environment (fewer sprays, right fertilizer, less food waste), climate resilience, inclusion, business revenue |
| Q&A | The prepared answers in `HANDOFF.md` |

## 8. Three upgrades that make the idea stronger

1. **Break the dadon trap:** the khata (verified dealer sales, cold-storage slips, crop sales) becomes a credit history a partner lender can use for a pre-harvest or storage loan cheaper than dadon.
2. **Advice and action in the same call:** every piece of advice ends with something to press (book, join, request a loan, call an officer).
3. **Farmers become the sensors:** keypad reports of prices received, fertilizer prices paid and disease seen join NASA data, giving DAE ground truth and improving forecasts and alerts as more farmers use it.
