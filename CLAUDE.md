# KrishiVault: guide for Claude

Start every session by reading `docs/HANDOFF.md`: the plan, the prototype scope, what is real and what is not, the business model and the prioritized to-do list. The team's plan document is the Google Doc "Krishi Vault" (link in `docs/HANDOFF.md`); the repository was synced with it on 15 October 2026, and `docs/HANDOFF.md`, section 13, lists the open points the team must decide. Supporting documents:
- `docs/PLAN_DETAILS.md`: how the engine and forecasts decide, the demo story, partner screens, call rules, the phone-line plan, risks, and the judging-criteria map.
- `docs/DATA_SOURCES.md`: every data file, what uses it, and what is still to collect.
- `docs/SCREENS.md`: the dashboard and the call preview, how to open them, real against demo.
- `docs/START_CLOUD_SESSION.md` and `docs/CLOUD_SETUP.md`: starting a cloud session and adding keys.

This file is the short version.

## What KrishiVault is (plan of 14 October 2026, plan document of 15 October)

**One focus: potato after the harvest.** "Store or sell, and until when?" KrishiVault helps Bangladeshi farmers earn more through better predictions, smarter storage decisions, easier financing and better market access: **Know, Calculate, Decide, Act**. The wedge: market timing, the cold-storage sums and crop-backed cash through a bank, in one loop.

**The problem (field notes and the plan document):** the cold-storage sack is 84 kg and the rent is about ৳300 a sack for up to 9 months (the plan; some charge ৳250), the same for 1 month or 9. Cold storages lend ৳200-300 a sack against the sacks. Big crops bring low prices; afraid, farmers sell within 1-3 months, after paying the full rent. Traders, with the cash and the information, store and sell later. Farmers mostly store only seed. **The plan's value-chain study** (Bogura and Munshiganj, 2016 fieldwork): farmers sell 64% at harvest, traders buy 97.6% of cold-stored potatoes, cold storage loses 8.65% of the weight (the engine's default). Quote its taka figures with their year; they are a decade old.

**Seven parts:**
1. **Production and price prediction** with ranges (BBS production trend; price outlook driven by crop size; regional prices).
2. **Storage and selling-time engine:** sell now / sell part and store the rest / store until month X (already-stored potatoes), after rent, losses, transport and interest, with the chance that storing pays and the net profit after the growing cost (the farmer's own, or the local benchmark: ৳14 a kg, DAE Bogura 2024-25). At the harvest it never stores the whole crop: it sells 30-40% (the plan's rule) and compares the plan's staggered exit (30/40/30). In a glut year banks lend at most 50%.
3. **Market access:** buyers and offers ranked by money in the farmer's hand.
4. **Crop-backed financing through banks:** a digital storage receipt from the cold storage (SMS), careful value after the 8.65% loss, repayment risk, application; the bank decides; approval holds the receipt; the sale pays the cold storage, the bank, then the farmer. KrishiVault does not lend or hold money.
5. **Export market intelligence:** sourcing districts and market margins after every cost.
6. **Group storage and group selling:** combined sacks; a discount counts only after the cold storage agrees; the group's lot reaches big buyers (shared out by money per kg, against the haat).
7. **Profit calculator:** costs, sales, profit per kg, sack, maund and harvest.

**The plan's loop, all running with demo partners:** harvest call or USSD (two numbers: sacks and cash needed) → digital receipt from a verified cold storage (generator, separate seed and table chambers) → bank loan, paid out by the bank (SMS) → price-window alerts by SMS (sell how many, to whom, or hold) → the sale pays the cold storage, the bank, then the farmer.

**Around the seven parts:** the government screen (glut warning from real data; farmer figures by district only with consent, press 8 in the call; hidden under 5 farmers), the curing reminder SMS, the business plan (`src/engine/business_model.py`: five income streams, ৳20 lakh start-up, 3-year projection). Rollout: Kahaloo (Bogura) pilot, then Bogura and Munshiganj, then national.

**Not in the current plan:** fertilizer and pesticide supply, the seed and machinery marketplace, weather danger alerts, a phone-number ID with a PIN. Their data stays in `data/reference/mati_kohon/` for later. Do not build them unless the user asks.

**Channels (the plan):** Grameenphone voice line (VAS rate, no other fee for farmers), USSD and SMS; **in the prototype there is no phone line or USSD code**, so the call is previewed in the browser (`/call`) and the USSD menu too (`/ussd`), and **SMS can be sent** (dry run until switched on). The AI and voice architecture, today and after the pilot: `docs/ai_architecture.html`. Helpers, cold storages, banks, buyers and exporters use the web dashboard (`/`).

**Hero crop:** potato in Bogura; data covers 64 districts. Onion is next.

## Repository map

- `krishivault-pipeline/`: the Python backend (FastAPI).
  - `src/main.py`: the API; serves `static/index.html` (the dashboard, `/`) and `static/call.html` (the call preview, `/call`).
  - `src/models/production_forecast.py` (BBS trend, crop gap, district supply) and `price_outlook.py` (crop-size price outlook, simulated ranges, regional index, model card).
  - `src/engine/`: `storage_plan.py` (the store-or-sell engine), `facts.py` (sack, rent, 8.65% loss and cost defaults with sources), `market_access.py`, `financing.py`, `receipts.py` (digital receipts, the bank's hold, the split at sale), `alerts.py` (price-window SMS), `farmer_signals.py` (the government screen), `group_storage.py` (incl. group selling), `export_intel.py`, `profit.py`, `business_model.py`. `src/contacts.py` keeps phone numbers for later SMS, never shown.
  - `src/voice/`: `conversation.py` (the call: menu, questions, read-back, answer, action, helper; signed SMS and actions), `ussd.py` (the USSD menu, gateway format), `understanding.py`, `intent_parser.py`, `bangla_numbers.py`, `number_lock.py`, `gemini.py`, `tts_generator.py`.
  - `src/notify/`: `sms.py` (REVE), `awaj.py` (calls, kept for later); dry run by default.
  - `src/demo_data.py` + `data/demo/demo_partners.json`: made-up partners. `src/events.py`: requests for partner screens (`data/runtime/`, not committed).
  - `data/`: WFP prices (`processed/potato_prices_wfp.csv`), BBS statistics (`reference/mati_kohon/crop_district_panel.csv`). Optional longer price history: `data/raw/price_history.csv`.
  - `src/scrapers/dam_scraper.py`: **broken**, the DAM site moved to `https://market.dam.gov.bd/`.
  - `tests/`: pytest.
- `reference/mati_kohon_code/`: Mati Kohon code that was ported. **Do not import it.**
- `docs/`: the plan documents, `ai_architecture.html` (AI and voice, now and after the pilot), `readiness_check.html`, `presentation_plan.md` (the 7-minute pitch and Q&A plan, a copy of the team's pitch-plan doc), the field check guide for farmers and cold storages (`farmer_interview_guide.html` and its PDF; to-do 3).
- `presentation material/KrishiVault_FutureMakers_Pitch_v2.pptx`: the Round 2 pitch deck, 10 slides for 7 minutes plus 3 of Q&A (16 October 2026; `..._Pitch.pptx` is the first version): the farmer video opens it, then checked news and research cards; slide 3 says what KrishiVault is; the AI slide links to the live prototype (`https://koryu.ninja/`); the speech, the sources and likely questions are in the speaker notes. Built by `scripts/pitch_deck/` (`build_deck.js`, `speaker_notes.js`, `finish_deck.ps1`); the speech is also in `docs/presentation_script.md`. Every figure on it comes from the engine or the data; update it when they change.

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
- **KrishiVault does not lend and does not hold money.** It verifies, values, connects and works out the split; the bank decides and pays.
- **Farmer figures only with consent:** nothing a farmer says is counted for government figures unless they agree (press 8; a ticked box); no names or numbers; districts under 5 farmers hidden.
- **Honest claims:** cold storages, banks, buyers, groups, receipts and export prices are clearly fictional demo data, never real partners; organizations the plan names (BKB, BRAC, PRAN, Himadri and others) are targets, not partners. Check `docs/HANDOFF.md`, section 10, and `docs/readiness_check.html` before claiming anything works.
- **Write plainly:** teammates are not computer-science students; docs, screens and slides use plain language.
- **Web design:** sharp corners, a subtle bevel and emboss, no floating top navigation bar.

## Sister project: Mati Kohon

`https://github.com/muhammadTasin/Mati-Kohon-/tree/feature/crop-loss` (commit `81704cb`). The files KrishiVault used are copied here. Go to Mati Kohon only for something new (for example the NASA POWER fetcher for the weather to-do). KrishiVault must not depend on its code.
