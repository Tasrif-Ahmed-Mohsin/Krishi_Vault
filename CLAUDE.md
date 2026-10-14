# KrishiVault: guide for Claude

Start every session by reading `docs/HANDOFF.md`: the plan, the prototype scope, what is real and what is not, the business model and the prioritized to-do list. Supporting documents:
- `docs/PLAN_DETAILS.md`: how the engine and forecasts decide, the demo story, partner screens, call rules, the phone-line plan, risks, and the judging-criteria map.
- `docs/DATA_SOURCES.md`: every data file, what uses it, and what is still to collect.
- `docs/SCREENS.md`: the dashboard and the call preview, how to open them, real against demo.
- `docs/START_CLOUD_SESSION.md` and `docs/CLOUD_SETUP.md`: starting a cloud session and adding keys.

This file is the short version.

## What KrishiVault is (plan of 14 October 2026)

**One focus: potato after the harvest.** "Store or sell, and until when?" KrishiVault helps Bangladeshi farmers earn more through better predictions, smarter storage decisions, easier financing and better market access.

**The problem (field notes):** the cold-storage sack is 84 kg and the rent is about ৳250 a sack for up to 9 months, the same for 1 month or 9. Cold storages lend ৳200-300 a sack against the sacks. Big crops bring low prices; afraid, farmers sell within 1-3 months, after paying the full rent. Traders, with the cash and the information, store and sell later. Farmers mostly store only seed.

**Seven parts:**
1. **Production and price prediction** with ranges (BBS production trend; price outlook driven by crop size; regional prices).
2. **Storage and selling-time engine:** sell now / store until month X / sell part and store the rest, after rent, losses, transport and interest, with the chance that storing pays.
3. **Market access:** buyers and offers ranked by money in the farmer's hand.
4. **Crop-backed financing through banks:** receipt confirmed by the cold storage, careful value, repayment risk, application; the bank decides. KrishiVault does not lend.
5. **Export market intelligence:** sourcing districts and market margins after every cost.
6. **Group storage:** combined sacks; a discount counts only after the cold storage agrees.
7. **Profit calculator:** costs, sales, profit per kg, sack, maund and harvest.

**Not in the current plan:** fertilizer and pesticide supply, the seed and machinery marketplace, weather danger alerts, a phone-number ID with a PIN. Their data stays in `data/reference/mati_kohon/` for later. Do not build them unless the user asks.

**Channels:** farmers by voice call (keypad or speech) and SMS; **in the prototype there is no phone line**, so the call is previewed in the browser (`/call`), and **SMS can be sent** (dry run until switched on). Helpers, cold storages, banks, buyers and exporters use the web dashboard (`/`).

**Hero crop:** potato in Bogura; data covers 64 districts. Onion is next.

## Repository map

- `krishivault-pipeline/`: the Python backend (FastAPI).
  - `src/main.py`: the API; serves `static/index.html` (the dashboard, `/`) and `static/call.html` (the call preview, `/call`).
  - `src/models/production_forecast.py` (BBS trend, crop gap, district supply) and `price_outlook.py` (crop-size price outlook, simulated ranges, regional index, model card).
  - `src/engine/`: `storage_plan.py` (the store-or-sell engine), `facts.py` (sack, rent and cost defaults with sources), `market_access.py`, `financing.py`, `group_storage.py`, `export_intel.py`, `profit.py`.
  - `src/voice/`: `conversation.py` (the call: menu, questions, read-back, answer, action, helper; signed SMS and actions), `understanding.py`, `intent_parser.py`, `bangla_numbers.py`, `number_lock.py`, `gemini.py`, `tts_generator.py`.
  - `src/notify/`: `sms.py` (REVE), `awaj.py` (calls, kept for later); dry run by default.
  - `src/demo_data.py` + `data/demo/demo_partners.json`: made-up partners. `src/events.py`: requests for partner screens (`data/runtime/`, not committed).
  - `data/`: WFP prices (`processed/potato_prices_wfp.csv`), BBS statistics (`reference/mati_kohon/crop_district_panel.csv`). Optional longer price history: `data/raw/price_history.csv`.
  - `src/scrapers/dam_scraper.py`: **broken**, the DAM site moved to `https://market.dam.gov.bd/`.
  - `tests/`: pytest.
- `reference/mati_kohon_code/`: Mati Kohon code that was ported. **Do not import it.**
- `docs/`: the plan documents, `readiness_check.html`, the farmer interview guide (still the old plan).
- `krishivault-pitch-deck.html`, `slide-images/`: the pitch deck (**still the old four-pillar plan**; update before use).

## Running it

```bash
cd krishivault-pipeline
pip install -r requirements-cloud.txt     # the SessionStart hook does this in cloud sessions
python -m pytest -q
uvicorn src.main:app --port 8000
# dashboard: http://localhost:8000/   call preview: http://localhost:8000/call
```

Secrets come from environment variables (names in `krishivault-pipeline/.env.example`). In a cloud session the hook writes the Google voice key to `/tmp/gcp-tts.json` from `GOOGLE_TTS_JSON_B64`.

## Rules

- **Never commit secrets:** `.env`, `env materials.txt`, any service-account JSON. `.gitignore` covers them; check before every commit.
- **Work on a feature branch and open a pull request. Never commit to `main`.** The user merges.
- **Real SMS only when the user says so** for that send. SMS stays in dry-run mode (`SMS_LIVE=0`) by default; calls (`AWAJ_LIVE=0`) are not part of the prototype.
- **Number lock:** every taka figure, quantity and date a farmer hears comes from the engine. Gemini may reword but must never change a number; check it and fall back to the template.
- **Honest forecasts:** always give a range, never a promise. The price outlook rests on two seasons of WFP prices; say "statistical outlook", not "AI forecast", until it is backtested on a longer history.
- **No paid placement:** a partner's fee never changes what a farmer is advised; offers are ranked by money in the farmer's hand.
- **KrishiVault does not lend.** It verifies, values and connects; the bank decides.
- **Honest claims:** cold storages, banks, buyers, groups and export prices are clearly fictional demo data, never real partners. Check `docs/HANDOFF.md`, section 9, before claiming anything works.
- **Write plainly:** teammates are not computer-science students; docs, screens and slides use plain language.
- **Web design:** sharp corners, a subtle bevel and emboss, no floating top navigation bar.

## Sister project: Mati Kohon

`https://github.com/muhammadTasin/Mati-Kohon-/tree/feature/crop-loss` (commit `81704cb`). The files KrishiVault used are copied here. Go to Mati Kohon only for something new (for example the NASA POWER fetcher for the weather to-do). KrishiVault must not depend on its code.
