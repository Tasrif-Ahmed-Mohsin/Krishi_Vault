# KrishiVault: guide for Claude

Start every session by reading `docs/HANDOFF.md`: the plan, the prototype scope, what is real and what is not, the business model and the prioritized to-do list. Supporting documents:
- `docs/PLAN_DETAILS.md`: how the pillars move together, the demo story, call rules, the phone-line voice pipeline and its security, risks, and the judging-criteria map.
- `docs/DATA_SOURCES.md`: every data file and what is still to collect.
- `docs/START_CLOUD_SESSION.md`: the first message for a new cloud session.

This file is the short version.

## What KrishiVault is

**A farm business ecosystem, not an agricultural information centre.** It connects farmers who are left behind (button phones, little bargaining power, dadon debt) with buyers, cold storages, fertilizer and pesticide dealers, seed and machinery sellers, lenders, agriculture officers and government. AI and data find the best option for the farmer; the partner network makes it happen.

**Five pillars:**
1. **Sell for the best value:** sell now, part, store or as a group, in taka, with cold-storage bookings and group lots for buyers.
2. **Fertilizer and pesticide supply chain:** the right dose for the soil, the official fair price, on-time delivery; pesticide only when weather favours disease.
3. **Agricultural goods marketplace:** seeds (including seed potato), machinery to buy or rent, tools and other inputs, from verified sellers, with subsidy information.
4. **Danger alerts:** heavy rain, heat, cold and fog, floods, crop-disease weather, and price crashes.
5. **Fair credit:** loans from partner lenders instead of dadon.

**The backbone is the farmer's record (কৃষি খাতা),** filled by the businesses he deals with and confirmed by him by keypad.

**Channels:**
- **Farmers:** button phones, by voice call (keypad or speech), missed call and callback, and an SMS receipt.
- **Partners:** web screens for officers, cold storages, buyers, dealers, sellers, lenders and DAE.

**Vision:** the best value for farmers and honest stakeholders, and less financial, crop and sustainability loss. It must be financially solid (the farmer pays nothing; businesses pay small fees only when they gain; government pays for public-good alerts and dashboards) and practical.

**For the competition** we present the complete plan and a prototype of what works now. Hero crop: potato in Bogura (including the Sariakandi char); the data covers 13 crops and 544 upazilas.

## Repository map

- `krishivault-pipeline/`: the Python backend (FastAPI).
  - `src/main.py`: the API; serves `static/index.html`. Endpoints include `/api/decision/evaluate`, `/api/voice/webhook`, `/api/voice/synthesize`, `/api/prices/latest`, `/api/cold-storages`, `/api/buyers`.
  - `src/engine/decision_engine.py`: sell now / sell part / store / group sell, in taka, with dadon and the cash deadline. Has tests.
  - `src/voice/`:
    - `intent_parser.py`: Bangla numbers and units such as মণ, বস্তা;
    - `gemini_advisor.py`;
    - `tts_generator.py`: the Google Bangla voice;
    - `farmer_dialog.py`;
    - `call_simulator.py`.
  - `src/scrapers/dam_scraper.py`: **broken.** The DAM page moved to `https://market.dam.gov.bd/`.
  - `src/models/price_predictor.py`: SARIMA + LSTM, **never trained**.
  - `data/`: WFP monthly retail potato prices; `krishivault.db` with **sample** partners (made-up phone numbers).
  - `data/reference/mati_kohon/`: NASA alerts, flood, crop loss, soil, SRDI fertilizer cards, BBS crop statistics and crop traits, copied from Mati Kohon (see `docs/DATA_SOURCES.md`).
  - `tests/`: pytest.
- `reference/mati_kohon_code/`: Mati Kohon code to port to Python: SMS, Awaj calls, Google TTS, the number-lock validator, alert rules, the fertilizer-card fetcher. **Do not import it.**
- `docs/`: the plan documents, `readiness_check.html`, the farmer interview guide (PDF and HTML).
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
- **Number lock:** every taka figure, quantity and date a farmer hears comes from the engine. Gemini may reword but must never change a number; check it and fall back to the template.
- **No paid placement:** a partner's fee never changes what a farmer is advised; offers are ranked by value to the farmer.
- **Farmer safety:** no AI-chosen pesticide names or doses. Crop problems get safe first steps and an officer callback.
- **Honest claims:** demo partners, sellers and marketplace items are clearly fictional demo data, never real partners. Rename the sample buyer "PRAN Agro" and every sample partner. Check `docs/HANDOFF.md`, section 9, before claiming anything works.
- **Phone number = farmer key,** linked to an internal farmer ID (shared phones, SIM changes), with a keypad PIN for money matters.
- **Write plainly:** teammates are not computer-science students; docs, screens and slides use plain language.
- **Web design:** sharp corners, a subtle bevel and emboss, no floating top navigation bar.

## Sister project: Mati Kohon

`https://github.com/muhammadTasin/Mati-Kohon-/tree/feature/crop-loss` (the newest branch, commit `81704cb`; not merged into main yet). The files KrishiVault needs are already copied into this repository. Go to Mati Kohon only for something new. Use its outputs as data and port small pieces to Python; KrishiVault must not depend on its code.
