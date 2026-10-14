# The screens: dashboard and call preview

Two web screens, one engine. Both run from the same server.

```bash
cd krishivault-pipeline
pip install -r requirements-cloud.txt
uvicorn src.main:app --port 8000
```

- **Dashboard:** http://localhost:8000/
- **Call preview:** http://localhost:8000/call

## The dashboard (`/`)

For helpers, partners, judges and the team. Pick a **season** at the top; every page follows it:

| Season | What it shows |
|---|---|
| Next harvest: March 2027 | A forecast: the crop size is not known, so the price range is wide |
| Today: October 2026 | Potatoes already in cold storage since March; two months left |
| Replay March 2025 | The big crop (6% above trend): real prices stayed flat afterwards |
| Replay March 2024 | A normal crop: real prices nearly doubled by November |

"Crop size" lets you try "what if the crop is 10% bigger".

| Page | What it does |
|---|---|
| Season overview | The crop, the price outlook with its range, what storing 36 sacks gains or loses month by month, and why farmers lose money in cold storage |
| Store or sell | The engine: the farmer's quantity, price, cash need and costs → sell now, store until a month, or sell part; the chance, the bad case, the price at which storing pays; send the advice by SMS; ask the cold storage for space |
| Forecasts | Production by district (BBS) with a range; the price outlook table; WFP prices so far; how the model works and its limits; the backtest (the outlook on past seasons it had not seen, against the usual seasonal shape); regional price levels and the biggest districts |
| Buyers | Offers ranked by money in the farmer's hand; add the farmer's own offers; send the lot to the buyers' screen |
| Bank loan | How much 36 sacks can borrow, from which lender, at what risk; what the bank sees; apply |
| Group storage | Groups, discount tiers, alone against the group; join |
| Export | Markets after every cost (demo figures); where to buy (real data) |
| Profit calculator | Costs and sales of one bigha → profit per kg, per sack, per maund, per harvest |
| Partner screens | What the cold storage, bank, buyer and helper see; confirm sacks, approve a loan, agree a group rate (demo) |

## The call preview (`/call`)

A farmer's phone call, played in the browser, because the prototype has no phone line. A teammate speaks (or presses keys) as the farmer; the screen shows what was heard, what KrishiVault understood, the answer from the engine, the number check, and the SMS receipt.

1. **Greeting and menu:** ১ store or sell, ২ price outlook, ৩ group storage, ৪ loan against stored sacks, ৯ a helper calls back. Or just speak.
2. **Questions,** only for what was not said: how many maunds (or sacks), today's price, whether the potatoes are already in cold storage (not asked at harvest), cash needed and within how many days. One sentence can answer several: "হামার ৮০ মণ আলু উঠছে, ফড়িয়া ১৬ টেকা দিবার চায়, ২৫ হাজার টেকা নাগবে ৪ দিনের মইধ্যে".
3. **Read-back** of every number; "ঠিক হলে ১, ভুল হলে ২". A spoken correction ("না, ৯০ মণ") is read back again.
4. **The answer** in taka, with the chance and the bad case.
5. **One action, press 2:** a cold-storage request, a group join, a loan application, or the lot sent to buyers. It appears on the dashboard's partner screens with a number.
6. **Every answer ends with** "১ = আবার শুনুন, ০ = মূল মেনু, ৯ = সহকারী".

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
| Cold storages, banks, buyers, groups, export prices | **Demo**, made up, labelled on every screen |
| Gemini | Tried with the real key (14 October): understanding and rewording, number-checked |
| Speech, Google voice | Work with keys; not yet tried with real keys here |
| SMS | Dry run until switched on |
| Phone calls | Preview only |

## Where the code is

- `krishivault-pipeline/static/index.html` (dashboard), `static/call.html` (call preview).
- `src/main.py`: the API.
- `src/engine/`: `storage_plan.py`, `market_access.py`, `financing.py`, `group_storage.py`, `export_intel.py`, `profit.py`, `facts.py`.
- `src/models/`: `production_forecast.py`, `price_outlook.py`.
- `src/voice/`: `conversation.py` (the call), `understanding.py`, `intent_parser.py`, `bangla_numbers.py`, `number_lock.py`, `gemini.py`, `tts_generator.py`.
- `src/notify/sms.py` (REVE), `src/notify/awaj.py` (calls, for later); `src/events.py`, `src/demo_data.py`.
