"""
Backtest of the price outlook
=============================
In plain words: for every past season with real prices, stand at the start of the season (the first month
from February to April with prices from 4+ markets) and make the outlook again with a model that has NOT seen
that season's prices: the crop-size link is fitted on the other seasons only. Then compare it with the prices
that really followed, month by month, up to December.

Three ways of guessing are compared:
  outlook      KrishiVault's outlook: the crop size sets how much prices rise; 2,000 paths give the range
  usual shape  the usual seasonal rise every year, whatever the crop (rise strength always 1), same range
  no change    the price stays where it is at the start

Scores:
  miss         how far the middle guess was from the real price, as % of the real price (smaller is better)
  in range     how often the real price fell inside the 8-in-10 range (about 80% is right; much lower means
               the range is too narrow)
  store/sell   whether the guess got "does storing one sack until the best month pay the rent?" right,
               and the taka a sack it would have gained or lost against selling at the start

Run it:  python -m src.models.backtest   (or GET /api/forecast/backtest)

Honest limits (also in the result):
  - The model is given the real crop size (BBS). At a real harvest the crop size is an estimate, so real
    results would be somewhat worse.
  - With few seasons, a season is predicted from the others, including later ones. With a long history in
    data/raw/price_history.csv, use only_past=True (each season predicted from earlier seasons only).
  - Prices are the national median of retail town-market prices. The store-or-sell check applies the real
    price change to a farm-gate price of half the retail price (the dashboard's example prices are about half).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

import numpy as np

from src.engine.facts import MONTHS_EN, LAST_SALE_MONTH, StorageTerms
from src.models.price_outlook import (MIN_REPORTS, SEASON_MONTHS, SLOPE_ASSUMED, _gap_history, calibrate,
                                      monthly_prices, rise_strength, simulate)

START_MONTHS = (2, 3, 4)      # the harvest decision: the first of these months with prices from 4+ markets
FARM_GATE_SHARE = 0.5         # assumption: the farmer's price is about half the town retail price
METHODS = ("outlook", "usual", "no_change")
METHOD_NAMES = {"outlook": "KrishiVault outlook", "usual": "Usual seasonal shape only", "no_change": "No change"}
SLOPES_TO_CHECK = (-5.0, -8.0, -10.0, -15.0, -20.0)   # the rise falls by 0.5 ... 2.0 for every 10% bigger crop


def _season_prices(season: int) -> dict[int, float]:
    """The season's usable national monthly prices, {month: ৳/kg}."""
    p = monthly_prices()
    rows = p[(p.season == season) & (p["count"] >= MIN_REPORTS) & p.month.isin(SEASON_MONTHS)]
    return {int(r.month): float(r["median"]) for _, r in rows.iterrows()}


def seasons_to_test() -> list[int]:
    """Seasons with a start price, at least one later price and a known BBS crop size."""
    gaps = _gap_history()
    p = monthly_prices()
    out = []
    for season in sorted(int(s) for s in p.season.dropna().unique()):
        prices = _season_prices(season)
        start = next((m for m in START_MONTHS if m in prices), None)
        if season in gaps and start is not None and any(m > start for m in prices):
            out.append(season)
    return out


def _sack_values(terms: StorageTerms, farm_start: float, ratios: np.ndarray, h: int) -> np.ndarray:
    """Money from one sack stored in cold storage and sold h months later, for each price ratio."""
    kept = terms.sack_kg * (1 - terms.monthly_weight_loss) ** h * (1 - terms.exit_sorting_loss)
    costs = terms.rent_per_sack + terms.handling_per_sack() + terms.sell_from_store_per_sack
    return kept * farm_start * ratios - costs


def _storage_call(terms: StorageTerms, farm_start: float, ratio_paths: dict[int, np.ndarray]) -> dict:
    """What a method says: store until its best month (by average money), or sell at the start."""
    sell_now = terms.sack_kg * farm_start - terms.sell_now_per_sack
    best_h, best_gain = None, 0.0
    for h, ratios in ratio_paths.items():
        gain = float(_sack_values(terms, farm_start, ratios, h).mean()) - sell_now
        if gain > best_gain:
            best_h, best_gain = h, gain
    return {"store": best_h is not None, "best_h": best_h, "expected_gain": round(best_gain)}


def backtest_season(season: int, only_past: bool = False, terms: Optional[StorageTerms] = None,
                    slope_assumed: float = SLOPE_ASSUMED) -> dict:
    terms = terms or StorageTerms()
    prices = _season_prices(season)
    start = next(m for m in START_MONTHS if m in prices)
    year = season + 1
    p0 = prices[start]
    horizon = LAST_SALE_MONTH - start

    all_seasons = seasons_to_test()
    exclude = tuple(s for s in all_seasons if s >= season) if only_past else (season,)
    cal = calibrate(exclude, slope_assumed)
    rs = rise_strength(season, decision_year=year, decision_month=start, cal=cal)
    k_by_method = {"outlook": rs["k"], "usual": 1.0}
    paths = {m: simulate(start, horizon, k, rs["k_sd"], sigma=cal.sigma_month) for m, k in k_by_method.items()}
    paths["no_change"] = np.ones((1, horizon + 1))

    months = []
    for h in range(1, horizon + 1):
        m = start + h
        if m not in prices:
            continue
        actual = prices[m]
        row = {"h": h, "month": m, "month_en": MONTHS_EN[m], "actual": round(actual, 2)}
        for method, ratios in paths.items():
            col = ratios[:, h] * p0
            mid = float(np.median(col))
            row[method] = {"mid": round(mid, 2), "miss_pct": round(abs(mid - actual) / actual * 100, 1)}
            if method != "no_change":
                low, high = float(np.percentile(col, 10)), float(np.percentile(col, 90))
                row[method].update({"low": round(low, 2), "high": round(high, 2), "inside": low <= actual <= high})
        months.append(row)

    # Store or sell, one sack: each method's call, scored on the real prices of the months that have them
    farm_start = p0 * FARM_GATE_SHARE
    sell_now = terms.sack_kg * farm_start - terms.sell_now_per_sack
    real_ratio = {r["h"]: np.array([r["actual"] / p0]) for r in months}
    real_gain = {h: float(_sack_values(terms, farm_start, v, h)[0]) - sell_now for h, v in real_ratio.items()}
    real_best_h = max(real_gain, key=real_gain.get) if real_gain else None
    storing_paid = bool(real_gain) and real_gain[real_best_h] > 0
    storage = {"real": {"storing_paid": storing_paid, "best_month_en": MONTHS_EN[start + real_best_h] if real_best_h else None,
                        "best_gain_per_sack": round(real_gain[real_best_h]) if real_gain else None}}
    for method, ratios in paths.items():
        call = _storage_call(terms, farm_start, {h: ratios[:, h] for h in range(1, horizon + 1)})
        if call["store"]:
            # Score the call at its own month, or the nearest later month with a real price
            later = [h for h in real_gain if h >= call["best_h"]]
            h_used = min(later) if later else max(real_gain)
            result = round(real_gain[h_used])
        else:
            h_used, result = 0, 0
        storage[method] = {
            "says": f"store until {MONTHS_EN[start + call['best_h']]}" if call["store"] else "sell at the start",
            "right": call["store"] == storing_paid,
            "real_gain_per_sack": result,
            "scored_at": MONTHS_EN[start + h_used] if h_used else MONTHS_EN[start],
        }

    return {
        "season": f"{season}-{str(year)[-2:]}", "start_year": season,
        "start": f"{MONTHS_EN[start]} {year}", "start_price": round(p0, 2), "farm_gate_start": round(farm_start, 2),
        "crop_gap_pct": rs["gap_pct"], "rise_used": round(rs["k"], 2),
        "trained_on": [s["season"] for s in cal.seasons],
        "crop_link": "assumed (one season only)" if len(cal.seasons) < 2 else "fitted",
        "months": months, "storage": storage,
    }


def slope_check(seasons: list[int], only_past: bool = False) -> list[dict]:
    """
    When a left-out season leaves fewer than two to learn from, the crop-size link is an assumption. This
    re-runs the store-or-sell calls with gentler and steeper assumed links, to show how much they depend on it.
    """
    out = []
    for slope in SLOPES_TO_CHECK:
        runs = [backtest_season(s, only_past, slope_assumed=slope) for s in seasons]
        right = sum(r["storage"]["outlook"]["right"] for r in runs)
        out.append({"rise_change_per_10pct_bigger_crop": round(slope / 10, 1), "store_or_sell_right": f"{right} of {len(runs)}",
                    "calls": {r["season"]: r["storage"]["outlook"]["says"] for r in runs}})
    return out


@lru_cache(maxsize=2)
def backtest(only_past: bool = False) -> dict:
    """Every testable season, and a summary per method."""
    seasons = [backtest_season(s, only_past) for s in seasons_to_test()]
    seasons = [s for s in seasons if s["trained_on"] or not only_past]
    assumed = any(s["crop_link"] != "fitted" for s in seasons)
    summary = {}
    for method in METHODS:
        misses = [r[method]["miss_pct"] for s in seasons for r in s["months"]]
        inside = [r[method]["inside"] for s in seasons for r in s["months"] if "inside" in r[method]]
        calls = [s["storage"][method] for s in seasons]
        summary[method] = {
            "name": METHOD_NAMES[method],
            "average_miss_pct": round(float(np.mean(misses)), 1) if misses else None,
            "in_range_pct": round(100 * float(np.mean(inside))) if inside else None,
            "store_or_sell_right": f"{sum(c['right'] for c in calls)} of {len(calls)}",
            "gain_per_sack_total": sum(c["real_gain_per_sack"] for c in calls),
        }
    n_months = sum(len(s["months"]) for s in seasons)
    return {
        "seasons": seasons, "summary": summary, "months_scored": n_months, "slope_check": slope_check([s["start_year"] for s in seasons], only_past) if assumed else None,
        "rise_cut_per_10pct": {"assumed": round(-SLOPE_ASSUMED / 10, 1), "fitted_on_all": round(-calibrate().slope / 10, 1)},
        "training": "only earlier seasons" if only_past else "the other seasons (earlier and later)",
        "enough_data": len(seasons) >= 5 and n_months >= 30,
        "limits": [
            f"Only {len(seasons)} season(s) and {n_months} months with prices from 4+ markets: far too few to "
            "judge the outlook. Add the DAM price history (data/raw/price_history.csv) and run it again.",
            "When a season is left out, the crop-size link cannot be fitted from one season; an assumed slope is "
            "used (the rise falls by 1.5 for every 10% bigger crop), set by the team after seeing both seasons. "
            "The slope check shows how the store-or-sell calls change with other slopes.",
            "The model is given the real crop size (BBS); at a real harvest it is an estimate.",
            "National median retail prices; the store-or-sell check assumes the farm-gate price is half the "
            "retail price and moves with it.",
        ],
    }


def _print(result: dict) -> None:
    print(f"Backtest of the price outlook ({result['training']}; {result['months_scored']} months scored)\n")
    for s in result["seasons"]:
        print(f"Season {s['season']}: start {s['start']} at ৳{s['start_price']}/kg retail, crop {s['crop_gap_pct']:+}% "
              f"against the trend, rise used {s['rise_used']} (trained on {', '.join(s['trained_on']) or 'nothing'}; "
              f"crop link {s['crop_link']})")
        print(f"  {'month':<6}{'real':>7}{'outlook (range)':>24}{'usual shape':>13}{'no change':>11}")
        for r in s["months"]:
            o = r["outlook"]
            rng = f"{o['mid']:.1f} ({o['low']:.0f}-{o['high']:.0f}){'' if o['inside'] else ' out'}"
            print(f"  {r['month_en'][:3]:<6}{r['actual']:>7.1f}{rng:>24}{r['usual']['mid']:>13.1f}{r['no_change']['mid']:>11.1f}")
        st = s["storage"]
        print(f"  Store or sell (one sack, farm-gate ৳{s['farm_gate_start']}/kg at the start): storing "
              f"{'paid' if st['real']['storing_paid'] else 'did not pay'} (best: {st['real']['best_month_en']}, "
              f"৳{st['real']['best_gain_per_sack']} a sack)")
        for m in METHODS:
            print(f"    {METHOD_NAMES[m]:<28} said {st[m]['says']:<22} {'right' if st[m]['right'] else 'WRONG':<6} "
                  f"result ৳{st[m]['real_gain_per_sack']} a sack")
        print()
    print("Summary")
    for m, v in result["summary"].items():
        rng = f"{v['in_range_pct']}% in range" if v["in_range_pct"] is not None else "no range"
        print(f"  {v['name']:<28} average miss {v['average_miss_pct']}%, {rng}, store-or-sell right "
              f"{v['store_or_sell_right']}, ৳{v['gain_per_sack_total']} a sack in all")
    if result["slope_check"]:
        print("\nSlope check (the crop-size link is assumed when a season is left out):")
        for c in result["slope_check"]:
            calls = "; ".join(f"{k}: {v}" for k, v in c["calls"].items())
            print(f"  rise {c['rise_change_per_10pct_bigger_crop']:+} per 10% bigger crop: right {c['store_or_sell_right']} ({calls})")
    print("\nLimits:")
    for line in result["limits"]:
        print("  - " + line)


if __name__ == "__main__":
    import sys
    _print(backtest(only_past="--only-past" in sys.argv))
