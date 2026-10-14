# KrishiVault: guide for Claude

Read `docs/HANDOFF.md` before starting work: it holds the plan, the prototype scope, what is real and what is not, and the prioritized to-do list. `docs/PLAN_DETAILS.md` has the rest: how the modules move together, the demo story, call rules, the phone-line voice pipeline and security, risks, and the judging-criteria map. This file is the short version.

## What KrishiVault is

A free phone service for potato farmers in Bangladesh who have only button phones. The farmer listens and answers by keypad or voice. KrishiVault warns him before weather or disease costs him money, tells him in taka when to sell, store or group-sell and what fertilizer to buy at a fair price, and connects him to a cold storage, buyer, fertilizer group or lender. Hero crop: potato in Bogura (including the Sariakandi char). The data for 13 crops and all 544 upazilas comes from the sister project Mati Kohon.

It is being prepared for an idea competition. Two things are presented:
- **The plan:** the complete product (five services, partner portals, our own phone line with a voice AI).
- **The prototype:** what we can show now (in-app voice conversation, real SMS, real Awaj voice broadcast calls, live NASA alerts, the sell/store engine, simple example screens).

## Repository map

- `krishivault-pipeline/`: the Python backend (FastAPI).
  - `src/main.py`: the API, and serves `static/index.html`. Endpoints include `/api/decision/evaluate`, `/api/voice/webhook`, `/api/voice/synthesize`, `/api/prices/latest`, `/api/cold-storages`, `/api/buyers`.
  - `src/engine/decision_engine.py`: sell now / sell part / store / group sell, in taka, with dadon and cash deadline. Has tests.
  - `src/voice/`: `intent_parser.py` (Bangla numbers and units such as মণ, বস্তা), `gemini_advisor.py` (Gemini), `tts_generator.py` (Google Cloud Bangla voice), `farmer_dialog.py`, `call_simulator.py`.
  - `src/scrapers/dam_scraper.py`: government daily prices. **Broken:** the old DAM page returns 404; the site moved to `https://market.dam.gov.bd/` (its home page links `daily_price_report`).
  - `src/models/price_predictor.py`: SARIMA + LSTM. **Never trained**; only ~29 months of monthly prices exist.
  - `data/`: WFP monthly retail potato prices (Feb 2024 to Jul 2026, 51 markets); `krishivault.db` holds **sample** data (5 cold storages, 5 buyers, 2 farmers with made-up phone numbers).
  - `tests/`: pytest.
- `docs/`: `HANDOFF.md` (start here), `CLOUD_SETUP.md`, `readiness_check.html` (every claim checked), the farmer interview guide (PDF and its HTML source).
- `krishivault-pitch-deck.html`, `slide-images/`, `*.jpg`: the current pitch deck and images.

## Running it

```bash
cd krishivault-pipeline
pip install -r requirements-cloud.txt     # the SessionStart hook does this in cloud sessions
python -m pytest -q
uvicorn src.main:app --reload --port 8000
```

Secrets come from environment variables (names in `krishivault-pipeline/.env.example`). In a cloud session the hook writes the Google voice key to `/tmp/gcp-tts.json` from `GOOGLE_TTS_JSON_B64`.

## Rules

- **Never commit secrets:** `.env`, `env materials.txt`, any service-account JSON. `.gitignore` covers them; check before every commit.
- **Work on a feature branch and open a pull request. Never commit to `main`.** The user merges.
- **Real SMS or calls only when the user says so** for that send. SMS and Awaj stay in dry-run mode (`SMS_LIVE=0`, `AWAJ_LIVE=0`) by default.
- **Number lock:** every taka figure, quantity and date a farmer hears comes from the engine. Gemini may reword but must never change a number; check and fall back to the template.
- **Farmer safety:** no AI-chosen pesticide names or doses. Crop problems get safe first steps and an officer callback.
- **Honest claims:** example cold storages, buyers and partners are demo data, never real partners. The sample buyers include the real company name "PRAN Agro"; rename all sample partners to clearly fictional names.
- **Phone number = farmer key,** linked to an internal farmer ID (shared phones, SIM changes), with a keypad PIN for private things (khata, bookings).
- **Write plainly:** teammates are not computer-science students; docs and slides use plain language.
- **Web design:** sharp corners, a subtle bevel and emboss, no floating top navigation bar.

## Sister project: Mati Kohon (data source, optional)

`https://github.com/muhammadTasin/Mati-Kohon-.git`. The newest work is on branches `feature/field-alerts` and `feature/crop-loss` (not merged into main yet). Use its **outputs as data** and port small rules to Python; do not make KrishiVault depend on its code. Useful files (on `feature/crop-loss`):

- `services/api/data/live/upazila_conditions.json`: daily NASA weather, 7-day forecast, potato late-blight and rice-blast weather for all 544 upazilas.
- `services/api/data/live/flood_now.json`: NASA OPERA flood water per upazila. `crop_loss.json`: where this year's Aman is not green.
- `packages/rotation-engine/src/data/`: `soil_atlas.json` (SRDI soil classes, 544 upazilas), `upazila_profile.json`, `disease_weather.json`, `national_replay.json`, `groundwater_budget.json`.
- `research/soil/srdi_frs_doses.csv` and `research/acquire/srdi_frs.py`: SRDI official union fertilizer cards (frs-bd.com), fetched for 6 pilot unions; the script can fetch any union.
- `research/crops/crop_parameters.csv` (13 crops) and `research/bbs/crop_district_panel.csv` (BBS, 23 crops x 64 districts).
- `research/live/disease_weather.py`: the late-blight rule (Hutton criteria) in Python.
- `services/api/src/sms.ts`, `awaj.ts`, `providers/tts.ts`: working REVE SMS, Awaj and Google TTS clients to port.
