# Data sources for the KrishiVault prototype

What we have, where it is, how fresh it is, what uses it, and what is still to collect. Mark demo data as demo on every screen.

## Used by the prototype now

| File (under `krishivault-pipeline/data/`) | What it holds | Dates | Used by |
|---|---|---|---|
| `reference/mati_kohon/crop_district_panel.csv` | BBS district crop statistics: 23 crops × 64 districts × 13 seasons (area, yield, production). Potato rows: `crop == "Potato"`, `variant == "total"` | 2012-13 to 2024-25 | Production forecast, crop gap, district supply, export sourcing |
| `processed/potato_prices_wfp.csv` (from `raw/wfp_food_prices_bgd.csv`) | WFP monthly **retail** potato prices (Holland, white), about 50 town markets | February 2024 to July 2026 | Price outlook, national price history, regional price levels |
| `demo/demo_partners.json` | **Made-up** cold storages, banks, buyers, groups, transport costs, export markets and export costs | none | Dashboard and call preview; every screen says DEMO |
| `runtime/` (not committed) | What people do in the prototype: requests, storage receipts, group joins, loan applications, farmer figures counted with consent (no names or numbers) | created when used | Partner screens, government screen |

**Cleaning:** a market that reports the exact same price for 4 or more months running is dropped as a frozen report (Rajshahi Sadar reported ৳62.50 for 16 months). A month is used only with 4 or more market reports, which leaves 19 months. **Gaps:** March to August 2024 and March and November 2025 have fewer than 4 reports (the backtest starts each season in February and skips missing months).

**What the numbers say:**
- Potato production grew about 1.8% a year (BBS). 2016-17 (+7%) and 2024-25 (+6%) stand out above the trend.
- After the 2023-24 crop, retail prices went from ৳35 (February 2024) to ৳67.50 (November 2024). After the 2024-25 crop, they stayed between ৳20 and ৳25 from April to December 2025.
- The six biggest districts (Rangpur, Dinajpur, Bogura, Joypurhat, Munshiganj, Rajshahi) grow 61% of the crop.

## Field notes (team, 14 October 2026)

Cold-storage sack 84 kg; rent about ৳250 a sack (some ৳300) for up to 9 months, the same for any length of stay; a cold storage holds 50,000 to 2.5 lakh sacks; cold storages lend ৳200-300 a sack with the sacks as security; potatoes keep about 3 months at home (onion 2-3 months); farmers who store tend to sell within 1-3 months; traders, not farmers, store potatoes for sale; farmers mostly store seed potato. Check this season's rates in the field before the demo (some cold storages charge per kg).

## The plan document and the value-chain study (15 October 2026)

The team's plan document (Google Doc "Krishi Vault", `HANDOFF.md`) quotes figures from a potato value-chain study of **Kahaloo (Bogura) and Munshiganj Sadar**, with haats such as Dhaper Hat and Bibir Pukur. The closest match found is a BRAC University thesis, "Value chain analysis of potato in selected areas of Bogra and Munshigonj districts of Bangladesh" (fieldwork February to April 2016; 20 farmers, 40 traders, 3 cold-storage owners; `https://dspace.bracu.ac.bd/xmlui/handle/10361/7723`). A related paper on Kahaloo (Akter, Rahman and Miah, Asian Journal of Agricultural Extension, Economics & Sociology, 2016, 2012 fieldwork) reports ৳338.12 of value added per 40 kg.

| Figure in the plan | Value | Checked? | Used where |
|---|---|---|---|
| Value added by wholesalers (the largest share; farias 14.23%) | 33.13% | Yes, in the thesis abstract | Docs, deck |
| Harvest sold at once; stored for later sale | 64.07%; 13.60% | Not yet | Docs, deck (with the study's year) |
| Cold-stored potatoes bought by traders | 97.6% | Not yet | Docs, deck |
| Loss at farm and home-store level | 16.60% | Not yet | Docs |
| Weight loss in cold storage | 8.65% | Not yet | **The engine's default** (`src/engine/facts.py`); confirm in the field check |
| Harvest price; off-season retail; lowest chain price | ৳5.90-6.03/kg; ৳17.50-20.40/kg; ৳480.38 per 40 kg | Not yet; prices of about 2016 | Docs only, with the year |
| Production cost; cultivation cost; storage charge; transport | ৳3.50-3.66/kg; ৳1.23-1.29 lakh/ha; ৳1.50/kg; about ৳6,000/ha | Not yet; prices of about 2016 | Docs only, with the year. Not used in the engine: today's costs are higher (the profit calculator's example bigha: ৳15.59/kg in all) |
| Cold storages; capacity | 320; 2.0 million tonnes | Old: check against today's list | Docs only |
| Kahaloo potato area; cold storages | 9,016 ha; 23 | Not yet | Docs (pilot site) |
| Potato exports | 103,000 tonnes (Malaysia, Singapore, Sri Lanka) | Not yet; year unknown | Docs (phase 3) |
| Bangladesh potato production | 8.6 million tons | **Out of date**: that is BBS 2012-13 (8,603,122 t); BBS 2024-25 is 11.6 million tonnes | Use the BBS figure |

The plan's business figures (fees, start-up money, the 3-year projection) are worked out in `src/engine/business_model.py` from the plan's own assumptions; they are projections, not data.

## Kept for later (not used by the current plan)

`reference/mati_kohon/`: NASA weather, flood, soil and disease files, SRDI fertilizer cards, upazila profiles, crop parameters. They served the earlier alerts and fertilizer plan. `upazila_conditions.json` and `disease_weather.json` could feed the weather adjustment of the production forecast; `crop_parameters.csv` has potato's cost and net return per hectare (Agriculture Census 2019). Refresh them from Mati Kohon only if they are used again.

`krishivault.db`: the old SQLite sample database (WFP prices, a few weather points, sample partners now renamed to "Demo ..."). The current app does not use it.

`reference/mati_kohon_code/` (in the repository root): code ported to Python (`sms.ts` → `src/notify/sms.py`, `awaj.ts` → `src/notify/awaj.py`, `dual_gate_validator.ts` → `src/voice/number_lock.py`). Do not import it.

## To collect

| Need | Source | How | Status |
|---|---|---|---|
| Monthly potato prices, 2010-2026, wholesale and retail, by district | DAM (`https://market.dam.gov.bd/`); FAO GIEWS FPMA (Dhaka wholesale and retail) | Fix `src/scrapers/dam_scraper.py` for the new site, or download; save as `data/raw/price_history.csv` with `date, admin2, market, price`; then run `python -m src.models.backtest` | To do. Blocked from the cloud: the network list does not allow `market.dam.gov.bd`, `fpma.fao.org`, `data.humdata.org` (add them, or do it on a laptop) |
| Farm-gate prices at harvest and later | DAM farm-gate reports; the field check | A few dated prices per month for Bogura | To do |
| Season weather per district, 2012-2025 | NASA POWER | Mati Kohon's fetcher; then add to the production model | To do |
| This season's planted area | DAE district reports (January) | Enter as "planted area" on the Forecasts page | At the season |
| Cold-storage rent, advance and interest, sack size, group rates | Two Bogura cold storages | Field check | To do |
| Storage and selling costs, weight loss (is it near the study's 8.65%?) | Five farmers | Field check (interview guide) | To do |
| The value-chain study's figures | The study itself (BRAC University library) | Read the thesis; confirm each figure and its year | To do |
| Cold-storage fill rates by district | Cold storages; the cold-storage association | Monthly fill from partner cold storages (government screen) | To do; demo figures until then |
| Bank terms for loans against stored crops | One bank or microfinance lender; Bangladesh Bank agricultural credit rules | Meeting | To do |
| Export prices, freight, duties, requirements | Export Promotion Bureau, exporters, shipping lines, DAE Plant Quarantine Wing | Dated quotes | To do; demo figures until then |
| Cold-storage list for Bogura | DAE or the cold-storage association | Names and capacity from a published list | To do |

## Credits to show

BBS (crop statistics); WFP (market prices, via HDX); team field notes (cold-storage terms); the value-chain study of Bogura and Munshiganj (weight loss, market shares, with its year). Later: DAM (market prices), NASA POWER (weather).
