# Data sources for the KrishiVault prototype

What we have, where it is, how fresh it is, what uses it, and what is still to collect. Mark demo data as demo on every screen.

## Used by the prototype now

| File (under `krishivault-pipeline/data/`) | What it holds | Dates | Used by |
|---|---|---|---|
| `reference/mati_kohon/crop_district_panel.csv` | BBS district crop statistics: 23 crops × 64 districts × 13 seasons (area, yield, production). Potato rows: `crop == "Potato"`, `variant == "total"` | 2012-13 to 2024-25 | Production forecast, crop gap, district supply, export sourcing |
| `processed/potato_prices_wfp.csv` (from `raw/wfp_food_prices_bgd.csv`) | WFP monthly **retail** potato prices (Holland, white), about 50 town markets | February 2024 to July 2026 | Price outlook, national price history, regional price levels |
| `demo/demo_partners.json` | **Made-up** cold storages, banks, buyers, groups, transport costs, export markets and export costs | none | Dashboard and call preview; every screen says DEMO |
| `runtime/` (not committed) | What people do in the prototype: requests, group joins, loan applications | created when used | Partner screens |

**Cleaning:** a market that reports the exact same price for 4 or more months running is dropped as a frozen report (Rajshahi Sadar reported ৳62.50 for 16 months). A month is used only with 4 or more market reports, which leaves 19 months.

**What the numbers say:**
- Potato production grew about 1.8% a year (BBS). 2016-17 (+7%) and 2024-25 (+6%) stand out above the trend.
- After the 2023-24 crop, retail prices went from ৳35 (February 2024) to ৳67.50 (November 2024). After the 2024-25 crop, they stayed between ৳20 and ৳25 from April to December 2025.
- The six biggest districts (Rangpur, Dinajpur, Bogura, Joypurhat, Munshiganj, Rajshahi) grow 61% of the crop.

## Field notes (team, 14 October 2026)

Cold-storage sack 84 kg; rent about ৳250 a sack (some ৳300) for up to 9 months, the same for any length of stay; a cold storage holds 50,000 to 2.5 lakh sacks; cold storages lend ৳200-300 a sack with the sacks as security; potatoes keep about 3 months at home (onion 2-3 months); farmers who store tend to sell within 1-3 months; traders, not farmers, store potatoes for sale; farmers mostly store seed potato. Check this season's rates in the field before the demo (some cold storages charge per kg).

## Kept for later (not used by the current plan)

`reference/mati_kohon/`: NASA weather, flood, soil and disease files, SRDI fertilizer cards, upazila profiles, crop parameters. They served the earlier alerts and fertilizer plan. `upazila_conditions.json` and `disease_weather.json` could feed the weather adjustment of the production forecast; `crop_parameters.csv` has potato's cost and net return per hectare (Agriculture Census 2019). Refresh them from Mati Kohon only if they are used again.

`krishivault.db`: the old SQLite sample database (WFP prices, a few weather points, sample partners now renamed to "Demo ..."). The current app does not use it.

`reference/mati_kohon_code/` (in the repository root): code ported to Python (`sms.ts` → `src/notify/sms.py`, `awaj.ts` → `src/notify/awaj.py`, `dual_gate_validator.ts` → `src/voice/number_lock.py`). Do not import it.

## To collect

| Need | Source | How | Status |
|---|---|---|---|
| Monthly potato prices, 2010-2026, wholesale and retail, by district | DAM (`https://market.dam.gov.bd/`); FAO GIEWS FPMA (Dhaka wholesale and retail) | Fix `src/scrapers/dam_scraper.py` for the new site, or download; save as `data/raw/price_history.csv` with `date, admin2, market, price` | To do (blocked from the cloud machine; do it on a laptop) |
| Farm-gate prices at harvest and later | DAM farm-gate reports; the field check | A few dated prices per month for Bogura | To do |
| Season weather per district, 2012-2025 | NASA POWER | Mati Kohon's fetcher; then add to the production model | To do |
| This season's planted area | DAE district reports (January) | Enter as "planted area" on the Forecasts page | At the season |
| Cold-storage rent, advance and interest, sack size, group rates | Two Bogura cold storages | Field check | To do |
| Storage and selling costs, weight loss | Five farmers | Field check (interview guide) | To do |
| Bank terms for loans against stored crops | One bank or microfinance lender; Bangladesh Bank agricultural credit rules | Meeting | To do |
| Export prices, freight, duties, requirements | Export Promotion Bureau, exporters, shipping lines, DAE Plant Quarantine Wing | Dated quotes | To do; demo figures until then |
| Cold-storage list for Bogura | DAE or the cold-storage association | Names and capacity from a published list | To do |

## Credits to show

BBS (crop statistics); WFP (market prices, via HDX); team field notes (cold-storage terms). Later: DAM (market prices), NASA POWER (weather).
