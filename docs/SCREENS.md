# The screens: dashboard and call preview

Two web screens, one engine. Both run from the same server.

```bash
cd krishivault-pipeline
pip install -r requirements-cloud.txt
uvicorn src.main:app --port 8000
```

- **Dashboard:** http://localhost:8000/
- **Call preview:** http://localhost:8000/call
- **USSD preview:** http://localhost:8000/ussd

## The dashboard (`/`)

For helpers, partners, judges and the team. Pick a **season** at the top; every page follows it:

| Season | What it shows |
|---|---|
| Next harvest: March 2027 | A forecast: the crop size is not known, so the price range is wide |
| Today: October 2026 | Potatoes already in cold storage since March; two months left |
| Replay March 2025 | The big crop (6% above trend): real prices stayed flat afterwards. A fair replay: only what was known in March 2025, then what really happened |
| Replay March 2024 | A normal crop: real prices nearly doubled by November. A fair replay: only what was known in March 2024, then what really happened |

"Crop size" lets you try "what if the crop is 10% bigger".

| Page | What it does |
|---|---|
| Season overview | The crop, the price outlook with its range, what storing 36 sacks gains or loses month by month, and why farmers lose money in cold storage; in a replay, what really happened and the net profit against selling everything at the harvest |
| Store or sell | The engine: the farmer's quantity, price, cash need and costs → sell now, sell part and store the rest, or store until a month (already stored); the plan's staggered exit beside it; the chance, the bad case, the price at which storing pays; the net profit after the growing cost (own or the ৳14 benchmark); the glut cap on loans; send the advice by SMS; send the curing reminder; ask the cold storage for space; a box to count the farmer (with consent) in the district figures |
| Forecasts | Production by district (BBS) with a range; the price outlook table; WFP prices so far; how the model works and its limits; the backtest (the outlook on past seasons it had not seen, against the usual seasonal shape); regional price levels and the biggest districts |
| Buyers | Offers ranked by money in the farmer's hand; add the farmer's own offers; send the lot to the buyers' screen |
| Bank loan | How much 36 sacks can borrow, from which lender, at what risk (valued after the 8.65% weight loss); what the bank sees; who is paid when the potatoes are sold; apply with a receipt number |
| Group storage and selling | Groups, discount tiers, alone against the group; join; "Sell together": the group's lot shared out to the buyers that pay most per kg, against the haat; send the group lot to buyers |
| Export | Markets after every cost (demo figures); where to buy (real data) |
| Profit calculator | Costs and sales of one bigha → profit per kg, per sack, per maund, per harvest |
| Partner screens | What the cold storage, bank, buyer, field agent and government see: issue a digital storage receipt (SMS; verified partners only), confirm sacks, approve a loan (payout SMS; the receipt is then held for the bank), record the sale and its split, agree a group rate (demo); the field agent's price-window alerts (sell how many to whom, or hold; SMS); the government's glut warning, cold-storage fill with partner checks, requests that found no space, and farmer figures by district |

## The call preview (`/call`)

A farmer's phone call, played in the browser, because the prototype has no phone line. A teammate speaks (or presses keys) as the farmer; the screen shows what was heard, what KrishiVault understood, the answer from the engine, the number check, and the SMS receipt.

1. **Greeting and menu:** ১ store or sell, ২ price outlook, ৩ group storage, ৪ loan against stored sacks, ৯ a helper calls back. Or just speak.
2. **Questions,** only for what was not said: how many maunds (or sacks), today's price, whether the potatoes are already in cold storage (not asked at harvest), cash needed and within how many days. One sentence can answer several: "হামার ৮০ মণ আলু উঠছে, ফড়িয়া ১৬ টেকা দিবার চায়, ২৫ হাজার টেকা নাগবে ৪ দিনের মইধ্যে".
3. **Read-back** of every number; "ঠিক হলে ১, ভুল হলে ২". A spoken correction ("না, ৯০ মণ") is read back again.
4. **The answer** in taka, with the chance and the bad case.
5. **One action, press 2:** a cold-storage request, a group join, a loan application, or the lot sent to buyers. It appears on the dashboard's partner screens with a number.
6. **Press 8 to be counted** (after the store-or-sell answer only): the answers go, without name or number, into the district figures on the government screen. Nothing is counted otherwise.
7. **Every answer ends with** "১ = আবার শুনুন, ০ = মূল মেনু, ৯ = সহকারী".

**SMS me** sends the receipt (REVE). It is a **dry run** unless the server has `SMS_LIVE=1` and the keys: the screen then shows the exact request that would go out. The SMS text is signed by the server, so the page cannot change what is sent.

### Speaking to it

The microphone uses the browser's own speech recognition (Chrome). It works on `localhost`; on a phone it needs HTTPS:

```bash
# Windows, once:  winget install --id Cloudflare.cloudflared
cloudflared tunnel --url http://localhost:8000
```

Open the printed `https://….trycloudflare.com/call` in Chrome on Android. Anyone with the address can use it while the tunnel runs: keep `SMS_LIVE=0`, and stop the tunnel after the demo. Without HTTPS, typing, the "Try" buttons and the keypad still work.

### Switching on Gemini and the Google voice

Set before starting the server (names in `krishivault-pipeline/.env.example`; values never in the repository): `GEMINI_API_KEY` (understanding and rewording, always number-checked) and `GOOGLE_APPLICATION_CREDENTIALS` (the Bangla voice). The strip under the phone shows what is on.

## Real and demo

| Part | Status |
|---|---|
| Production and prices behind the forecasts | Real data (BBS, WFP) |
| The engine, loan valuation, group and export sums, profit calculator | Real code, tested; costs partly assumptions (editable) |
| Cold storages, banks, buyers, groups, export prices, receipts, cold-storage fill | **Demo**, made up, labelled on every screen |
| Glut warning on the government screen | Real data (BBS crop against its trend, the price outlook) |
| Farmer figures on the government screen | Only from prototype use, with consent; hidden under 5 farmers a district |
| Payments (loan paid out, sale settled) | Not in the prototype: the split is worked out only; KrishiVault never holds money |
| Gemini | Tried with the real key (14 October): understanding and rewording, number-checked |
| Speech, Google voice | Work with keys; not yet tried with real keys here |
| SMS | Dry run until switched on |
| Phone calls | Preview only |
| USSD | Preview only (no short code); the handler speaks the gateway format |
| Price-window alerts, group selling, the bank's payout | Real code; demo partners; SMS dry run; no money moves |

## The USSD preview (`/ussd`)

The plan's text menu for any phone, played on a button phone drawn in the browser. Press **Dial / Send**, type a number, **Send**.

1. **Menu:** 1 store or sell, 2 price outlook, 3 loan against stored sacks, 4 group storage and selling.
2. **Store or sell asks only the plan's two numbers:** how many sacks, and how much cash is needed now. The local price and the ৳14 a kg cost benchmark are pre-loaded.
3. **The answer on one screen:** how many sacks to sell now and to store until when, the net profit against selling everything now, then 1 = details by SMS, 2 = ask for cold-storage space, 8 = be counted without name or number.
4. The right side shows what a USSD gateway would send ("1*36*25000") and get back ("CON …" or "END …"), and each screen's length. Bangla USSD screens hold fewer characters than English ones; the limit must be confirmed with Grameenphone.

## Where the code is

- `krishivault-pipeline/static/index.html` (dashboard), `static/call.html` (call preview).
- `src/main.py`: the API.
- `src/engine/`: `storage_plan.py`, `market_access.py`, `financing.py`, `receipts.py` (digital receipts, the bank's hold, the split at sale), `farmer_signals.py` (the government screen), `group_storage.py`, `export_intel.py`, `profit.py`, `business_model.py` (the plan's income and projection), `facts.py`.
- `src/models/`: `production_forecast.py`, `price_outlook.py`.
- `src/voice/`: `conversation.py` (the call), `ussd.py` (the USSD menu), `understanding.py`, `intent_parser.py`, `bangla_numbers.py`, `number_lock.py`, `gemini.py`, `tts_generator.py`.
- `src/notify/sms.py` (REVE), `src/notify/awaj.py` (calls, for later); `src/events.py`, `src/demo_data.py`.
