# Data sources for the KrishiVault prototype

What we have, where it is, how fresh it is, and what is still to collect. Mark demo data as demo on every screen.

## Already in this repository

### `krishivault-pipeline/data/reference/mati_kohon/`: snapshot from the Mati Kohon project

Copied on 14 October 2026 from `github.com/muhammadTasin/Mati-Kohon-`, branch `feature/crop-loss`, commit `81704cb`. Use as data; refresh from Mati Kohon before the demo.

| File | What it holds | Date of the reading | Feeds |
|---|---|---|---|
| `upazila_conditions.json` | For all 544 upazilas: NASA POWER daily weather; GPM IMERG rain; 30-day rain against normal; soil wetness; potato late-blight and rice-blast weather in the last 7 days; a `field` record with paddy water, temperatures and Open-Meteo's 7-day forecast (rain, maximum and minimum temperature) | NASA POWER to 5 Oct 2026; forecast from 8 Oct 2026 | Danger alerts (heavy rain, heat, cold, disease) |
| `flood_now.json` | NASA OPERA (Landsat and Sentinel-2) flood water per upazila, with the same weeks of 2025 by radar | 14 Sep to 8 Oct 2026 | Flood alerts |
| `crop_loss.json` | Share of last year's Aman land not green this year (NASA HLS) | 10 Sep to 8 Oct 2026 | Damage checks, partner and DAE screens |
| `smap_upazila.json` | NASA SMAP root-zone soil moisture percentile | 2 Oct 2026 | Dry-soil alerts |
| `soil_atlas.json` | SRDI soil fertility classes (pH, organic matter, P, K, S, Zn, B) for 544 upazilas | SRDI atlas 2020 | Fertilizer need |
| `srdi_frs_doses.csv`, `srdi_frs_cards.csv` | SRDI's official union fertilizer cards (frs-bd.com, with Katalyst): doses per crop, soil type and land type, and how to apply them (Bangla) | Fetched Sep 2026, 6 pilot unions | Fertilizer need |
| `upazila_profile.json` | Land type, BRRI cropping patterns, salinity, OPERA water and drain dates, HLS winter cropping, per upazila | Built Oct 2026 | Context, flood drain dates |
| `disease_weather.json` | 25-season disease-weather climatology (late blight: Bogura median 40 days a season) | 2001 to 2025 | "How bad is this week" context |
| `groundwater_budget.json` | GRACE groundwater fall and the Boro land to move per district | 2003 to 2025 | Sustainability story |
| `crop_parameters.csv` | 13 crops: calendar, duration, water use, heat limit, flood and salt tolerance, yields, area, harvest price, cost and net return per hectare (Agriculture Census 2019 costs) | Various, cited in the file | Cost floor, crop calendar |
| `crop_district_panel.csv` | BBS district crop statistics: 23 crops × 64 districts × 13 seasons (area, yield, production) | 2012-13 to 2024-25 | Supply outlook, potato facts |
| `upazilas.csv` | The 544 upazilas with district and centre coordinates | none | Place lookup |

### `reference/mati_kohon_code/`: code to port to Python

Read for porting; do not import.

| File | Use |
|---|---|
| `sms.ts` | REVE SMS client: dry run by default, keys masked |
| `awaj.ts` | Awaj Digital calls: text-to-speech broadcast, audio broadcast, keypad surveys, balance |
| `tts.ts` | Google Cloud Text-to-Speech with a service-account key (signs its own token; Bangla MP3 and 8 kHz WAV for calls) |
| `dual_gate_validator.ts` | The number lock: checks an AI-worded reply keeps every number and term from the engine |
| `field_alerts.ts` | Crop-stage alert rules: dry spell, heat at flowering, cold on seedbeds, AWD, flood |
| `disease_weather.py` | Late-blight (Hutton) and blast rules from daily weather |
| `field_weather.py` | Paddy water balance and Open-Meteo forecast fetch |
| `srdi_frs.py` | Fetches SRDI union fertilizer cards for any union |

### Other data already in `krishivault-pipeline/data/`

- `raw/wfp_food_prices_bgd.csv`, `processed/potato_prices_wfp.csv`: WFP monthly **retail** potato prices, Feb 2024 to Jul 2026, 51 markets. Retail is higher than the farm-gate price.
- `processed/weather_all_districts.csv`: 5 district points, Jul to Oct 2026.
- `krishivault.db`: **sample** cold storages, buyers and farmers with made-up phone numbers. Rename sample partners to clearly fictional names.

## To collect for the prototype

| Need | Source | How | Status |
|---|---|---|---|
| Daily market prices | DAM (`https://market.dam.gov.bd/`, home page links `daily_price_report`) | Fix `dam_scraper.py` for the new site | To do |
| Official fertilizer prices | Ministry of Agriculture's current order. News (2026) gives urea and TSP ৳1,350 a 50 kg bag, DAP ৳1,050, MoP ৳1,000 or ৳1,050. | Find the order; store with its date | Confirm |
| Fertilizer cards for Bogura potato unions (incl. Sariakandi) | SRDI frs-bd.com | `reference/mati_kohon_code/srdi_frs.py` approach, one request a second | To do |
| Seed varieties for the marketplace | BARI (potato varieties), BRRI (rice), BADC (certified seed and seed potato sales) | Names and seasons from their published lists; prices only from a dated notice | To do |
| Machinery and subsidy facts | DAE's farm mechanization programme (machinery subsidy, higher in haor and coastal areas) | Find the current project terms and rates before quoting a percentage | To verify |
| Cold storage list for Bogura | DAE or the cold storage association | Names and capacity only from a published list | To do |
| Partner sellers, buyers, lenders | none yet | **Demo data, clearly fictional** | Demo |

## Refreshing the NASA data (in the Mati Kohon project)

The daily update and flood reading run in Mati Kohon (`research/live/daily_update.py`, `flood_now.py`; the flood reading needs an Earthdata login). After a refresh, copy the files listed above into `krishivault-pipeline/data/reference/mati_kohon/` and update the dates in this file.

## Credits to show

NASA POWER, GPM IMERG, SMAP, OPERA, HLS (NASA Earthdata); Open-Meteo (weather model forecast, not NASA); SRDI and Katalyst (fertilizer cards); BBS (crop statistics); WFP (market prices); DAM (daily prices).
