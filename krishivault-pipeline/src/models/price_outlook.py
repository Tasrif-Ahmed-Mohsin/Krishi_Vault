"""
Potato price outlook, 0 to 9 months ahead, with a range
=======================================================
In plain words:

1. **The usual season.** Potato is cheapest at the March harvest and dearest
   in November-December, when the cold storages are emptying. `SEASON_CURVE`
   is that usual shape (March = 0.72, November = 1.35: almost double).
2. **Crop size changes the shape.** In a big-crop year the rise shrinks or
   disappears; in a small-crop year it is steeper. We measure each season's
   "rise strength" k (1 = the usual rise, 0 = flat, below 0 = prices fall)
   from WFP market prices, and link k to the crop gap from the BBS production
   trend (`production_forecast.py`):
     - 2023-24 crop, about the trend  -> prices rose about 1.9 times (k near 1)
     - 2024-25 crop, 6% above trend   -> prices stayed flat or fell (k below 0)
3. **This season's prices so far** correct the guess: once three or more
   months of the season are known, the curve is fitted to them too.
4. **The range.** We simulate 2,000 possible price paths: the crop gap is
   uncertain, and prices wander month to month. The outlook shows the middle
   path and the range that 8 paths in 10 fall inside.

Honest limits (also returned in `model_card()`): only two full seasons of
prices (WFP, February 2024 to July 2026, retail, about 50 town markets). The
link between crop size and price is fitted to those two seasons, so treat the
outlook as a careful scenario, not a promise. Adding the DAM price history
(to-do) refits everything automatically: put a CSV with columns
`date, admin2, market, price` (retail ৳/kg) at `data/raw/price_history.csv`.

Prices are retail in town markets. The storage engine applies the outlook's
*change* to the farmer's own price today (farm-gate), which assumes farm-gate
prices move in step with retail. That is conservative: farm-gate prices
usually swing more.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from src.engine.facts import MONTHS_EN, MONTHS_BN, month_after
from src.models.production_forecast import crop_gap, production_forecast, load_panel

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
WFP_PATH = DATA_DIR / "processed" / "potato_prices_wfp.csv"
EXTRA_PATH = DATA_DIR / "raw" / "price_history.csv"

# The usual price shape over the calendar year (1.0 = the year's average).
# KrishiVault's starting pattern; it matches the WFP 2024 season (Feb -> Nov x1.93).
SEASON_CURVE = {1: 0.85, 2: 0.70, 3: 0.72, 4: 0.80, 5: 0.90, 6: 1.00,
                7: 1.10, 8: 1.15, 9: 1.20, 10: 1.25, 11: 1.35, 12: 1.40}
SEASON_MONTHS = list(range(2, 13))   # February to December belong to one crop
MIN_REPORTS = 4                      # a month needs prices from 4+ markets
K_LIMITS = (-0.6, 1.8)
SIGMA_MONTH_FLOOR = 0.06             # prices wander at least 6% a month (log), per month
K_SPREAD_FLOOR = 0.25                # the crop-size link is uncertain even when the gap is known
SIMULATIONS = 2000
# Used only when fewer than two seasons are known, so the crop-size link cannot be fitted: k falls by 1.5
# for every 10% bigger crop. An assumption, close to what the two WFP seasons give (1.3).
SLOPE_ASSUMED = -15.0


def log_s(month: int) -> float:
    return math.log(SEASON_CURVE[month])


def season_of(year: int, month: int) -> Optional[int]:
    """The crop season (start year) a calendar month belongs to. 2026-05 -> 2025 (the 2025-26 crop)."""
    if month == 1:
        return None   # January mixes old stock and the early new crop
    return year - 1


STALE_RUN = 4   # the same price from one market 4+ months running is a frozen report, not a price


def drop_stale(df: pd.DataFrame) -> pd.DataFrame:
    """Remove frozen reports: a market repeating the exact same price for STALE_RUN or more months."""
    df = df.sort_values(["market", "date"]).copy()
    change = (df.price != df.groupby("market").price.shift()) | (df.market != df.market.shift())
    run_id = change.cumsum()
    run_len = df.groupby(run_id).price.transform("size")
    return df[run_len < STALE_RUN]


@lru_cache(maxsize=1)
def market_reports() -> pd.DataFrame:
    """Every usable retail report: WFP, plus `data/raw/price_history.csv` if present, frozen reports removed."""
    frames = [pd.read_csv(WFP_PATH, usecols=["date", "admin2", "market", "price"])]
    if EXTRA_PATH.exists():
        frames.append(pd.read_csv(EXTRA_PATH, usecols=["date", "admin2", "market", "price"]))
    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df.date)
    df = drop_stale(df.drop_duplicates(["date", "market"]))
    df["period"] = df.date.dt.to_period("M")
    return df


@lru_cache(maxsize=1)
def monthly_prices() -> pd.DataFrame:
    """National monthly median retail price (৳/kg) and the number of market reports behind it."""
    df = market_reports()
    g = df.groupby("period").price.agg(["median", "count"]).reset_index()
    g["year"] = g.period.dt.year
    g["month"] = g.period.dt.month
    g["season"] = [season_of(y, m) for y, m in zip(g.year, g.month)]
    return g


def _season_k(rows: pd.DataFrame) -> Optional[tuple[float, float, int]]:
    """Fit log price = c + k * log(curve) for one season. Returns (k, its standard error, months used)."""
    rows = rows[rows["count"] >= MIN_REPORTS]
    if len(rows) < 3:
        return None
    x = np.array([log_s(m) for m in rows.month])
    y = np.log(rows["median"].values.astype(float))
    if np.ptp(x) < 0.1:
        return None
    k, c = np.polyfit(x, y, 1)
    resid = y - (c + k * x)
    dof = max(len(x) - 2, 1)
    s = math.sqrt((resid ** 2).sum() / dof) if len(x) > 2 else 0.1
    se = s / math.sqrt(((x - x.mean()) ** 2).sum())
    return float(k), float(max(se, 0.05)), int(len(x))


def _gap_history() -> dict[int, float]:
    hist = production_forecast(None)["history"]
    return {h["start_year"]: h["gap_pct"] / 100.0 for h in hist}


@dataclass
class Calibration:
    k0: float                 # rise strength in a trend-size crop
    slope: float              # change in k for each +1.0 (100%) of crop gap
    k_spread: float           # how far a season's k strays from the line
    sigma_month: float        # monthly price wander (log)
    seasons: list             # what it was fitted on


@lru_cache(maxsize=16)
def calibrate(exclude: tuple = (), slope_assumed: float = SLOPE_ASSUMED) -> Calibration:
    """Fit the crop-size link on every season with prices, except the seasons in `exclude` (the backtest)."""
    prices = monthly_prices()
    gaps = _gap_history()
    seasons, resid_all = [], []
    for season, rows in prices[prices.season.notna()].groupby("season"):
        season = int(season)
        if season in exclude:
            continue
        fit = _season_k(rows[rows.month.isin(SEASON_MONTHS)])
        if fit is None or season not in gaps:
            continue
        k, se, n = fit
        seasons.append({"season": f"{season}-{str(season + 1)[-2:]}", "start_year": season,
                        "k": round(k, 2), "k_se": round(se, 2), "months": n,
                        "gap_pct": round(gaps[season] * 100, 1)})
        used = rows[(rows["count"] >= MIN_REPORTS) & rows.month.isin(SEASON_MONTHS)]
        x = np.array([log_s(m) for m in used.month])
        y = np.log(used["median"].values.astype(float))
        resid_all.extend(list(y - y.mean() - k * (x - x.mean())))

    if len(seasons) >= 2:
        g = np.array([s["gap_pct"] / 100 for s in seasons])
        kk = np.array([s["k"] for s in seasons])
        slope, k0 = np.polyfit(g, kk, 1)
        spread = float(np.sqrt(((kk - (k0 + slope * g)) ** 2).sum() / max(len(g) - 2, 1))) if len(g) > 2 else 0.0
    elif len(seasons) == 1:
        slope, spread = slope_assumed, 0.4
        k0 = seasons[0]["k"] - slope * seasons[0]["gap_pct"] / 100   # the line through the one known season
    else:
        k0, slope, spread = 0.8, slope_assumed, 0.4
    sigma = float(np.std(resid_all, ddof=1)) if len(resid_all) > 3 else SIGMA_MONTH_FLOOR
    return Calibration(k0=float(k0), slope=float(slope), k_spread=max(spread, K_SPREAD_FLOOR),
                       sigma_month=max(sigma / math.sqrt(2), SIGMA_MONTH_FLOOR), seasons=seasons)


def _clamp_k(k: float) -> float:
    return min(max(k, K_LIMITS[0]), K_LIMITS[1])


def season_for_decision(year: int, month: int) -> int:
    """The crop a farmer is deciding about in a given month. January counts as the end of last year's crop."""
    return year - 2 if month == 1 else year - 1


def seasons_unfinished(decision_year: int) -> tuple:
    """Seasons with prices that had not finished by a decision in `decision_year` (a season ends in December)."""
    p = monthly_prices()
    return tuple(sorted(int(s) for s in p.season.dropna().unique() if s + 1 >= decision_year))


def rise_strength(season_start: int, area_ha: Optional[float] = None, gap_override_pct: Optional[float] = None,
                  weather_adjust_pct: float = 0.0, decision_year: Optional[int] = None,
                  decision_month: Optional[int] = None, use_season_prices: bool = True,
                  cal: Optional[Calibration] = None) -> dict:
    """
    k for a season: from the crop gap, corrected by the season's own prices so far.

    Only what was known on the decision date is used, so a replay of a past season is fair: the crop-size
    link is learned from the seasons that had finished by then, and a crop whose final BBS figure came out
    later is estimated from its planted area and the earlier yield trend.
    """
    if cal is None:
        cal = calibrate(seasons_unfinished(decision_year)) if decision_year else calibrate()
    as_known = bool(decision_year) and decision_year <= season_start + 1
    gap, gap_sd = crop_gap(season_start, area_ha, weather_adjust_pct, gap_override_pct, as_known_at_harvest=as_known)
    prior = cal.k0 + cal.slope * gap
    prior_sd = math.sqrt((cal.slope * gap_sd) ** 2 + cal.k_spread ** 2)
    result = {"gap_pct": round(gap * 100, 1), "gap_sd_pct": round(gap_sd * 100, 1),
              "learned_from": [s["season"] for s in cal.seasons],
              "crop_link": "fitted" if len(cal.seasons) >= 2 else "assumed",
              "sigma_month": cal.sigma_month,
              "k_from_crop": round(_clamp_k(prior), 2), "k_from_crop_sd": round(prior_sd, 2),
              "season_months_used": 0, "k_from_prices": None}
    k, sd = prior, prior_sd
    if use_season_prices and gap_override_pct is None:
        p = monthly_prices()
        rows = p[(p.season == season_start) & p.month.isin(SEASON_MONTHS)]
        if decision_year and decision_month:
            cutoff = pd.Period(year=decision_year, month=decision_month, freq="M")
            rows = rows[rows.period <= cutoff]
        fit = _season_k(rows)
        if fit:
            k_obs, se_obs, n = fit
            w_prior, w_obs = 1 / prior_sd ** 2, 1 / se_obs ** 2
            k = (prior * w_prior + k_obs * w_obs) / (w_prior + w_obs)
            sd = math.sqrt(1 / (w_prior + w_obs))
            result.update({"season_months_used": n, "k_from_prices": round(k_obs, 2)})
    result.update({"k": round(_clamp_k(k), 3), "k_sd": round(sd, 3)})
    return result


def simulate(decision_month: int, horizon: int, k: float, k_sd: float,
             n: int = SIMULATIONS, seed: int = 7, sigma: Optional[float] = None) -> np.ndarray:
    """
    Price paths relative to today's price: an (n x horizon+1) array, column 0 is 1.0.
    Each path draws its own rise strength and its own monthly wander.
    """
    rng = np.random.default_rng(seed)
    ks = np.clip(rng.normal(k, k_sd, size=n), *K_LIMITS)
    sigma = calibrate().sigma_month if sigma is None else sigma
    base = log_s(decision_month)
    shape = np.array([log_s(month_after(decision_month, h)) - base for h in range(horizon + 1)])
    shocks = np.concatenate([np.zeros((n, 1)), rng.normal(0, sigma, size=(n, horizon)).cumsum(axis=1)], axis=1)
    return np.exp(ks[:, None] * shape[None, :] + shocks)


def real_path(decision_year: int, decision_month: int, horizon: int) -> Optional[list]:
    """
    For a past decision date: what really happened to the national retail price afterwards, as a ratio to its
    level at the decision (the last month with prices from 4+ markets at or before it, back to February).
    None when no later month is known yet. Used to show a replay against the real prices.
    """
    p = monthly_prices()
    p = p[p["count"] >= MIN_REPORTS]
    known = {(int(r.year), int(r.month)): float(r["median"]) for _, r in p.iterrows()}
    base = next((known[(decision_year, m)] for m in range(decision_month, 1, -1) if (decision_year, m) in known), None)
    if base is None:
        return None
    out = []
    for h in range(horizon + 1):
        year = decision_year + (decision_month - 1 + h) // 12
        price = known.get((year, month_after(decision_month, h)))
        out.append(round(price / base, 4) if price is not None else None)
    return out if any(r is not None for r in out[1:]) else None


def outlook(price_today: float, decision_month: int, decision_year: int, horizon: int = 9,
            season_start: Optional[int] = None, area_ha: Optional[float] = None,
            gap_override_pct: Optional[float] = None, weather_adjust_pct: float = 0.0) -> dict:
    """The month-by-month outlook in ৳/kg from today's price, with the 80% range."""
    season = season_start if season_start is not None else season_for_decision(decision_year, decision_month)
    rs = rise_strength(season, area_ha, gap_override_pct, weather_adjust_pct, decision_year, decision_month)
    paths = simulate(decision_month, horizon, rs["k"], rs["k_sd"], sigma=rs["sigma_month"]) * price_today
    months = []
    for h in range(horizon + 1):
        col = paths[:, h]
        m = month_after(decision_month, h)
        months.append({
            "h": h, "month": m, "month_en": MONTHS_EN[m], "month_bn": MONTHS_BN[m],
            "mid": round(float(np.median(col)), 2), "mean": round(float(col.mean()), 2),
            "low": round(float(np.percentile(col, 10)), 2), "high": round(float(np.percentile(col, 90)), 2),
            "chance_above_today": round(float((col > price_today).mean()), 2),
        })
    real = real_path(decision_year, decision_month, horizon)
    if real:
        for m, ratio in zip(months, real):
            m["real"] = round(price_today * ratio, 2) if ratio is not None else None
    return {"price_today": price_today, "decision_month": decision_month, "decision_year": decision_year,
            "season": f"{season}-{str(season + 1)[-2:]}", "rise": rs, "months": months, "replay": bool(real)}


def model_card() -> dict:
    cal = calibrate()
    p = monthly_prices()
    used = p[p["count"] >= MIN_REPORTS]
    return {
        "name": "Crop-size price outlook (statistical, with simulated ranges)",
        "trained_on": {
            "prices": f"WFP retail potato prices, {len(used)} months with 4+ markets "
                      f"({used.period.min()} to {used.period.max()})",
            "production": "BBS potato production, 13 seasons (2012-13 to 2024-25)",
        },
        "seasons_fitted": cal.seasons,
        "rise_in_trend_crop": round(cal.k0, 2),
        "rise_change_per_10pct_bigger_crop": round(cal.slope * 0.10, 2),
        "monthly_wander_pct": round(cal.sigma_month * 100, 1),
        "range": "80%: 8 of 10 simulated price paths fall inside",
        "limits": [
            "Only two full price seasons: the crop-size link is fitted to two points. A scenario, not a promise.",
            "Retail town-market prices; the farmer's own price today anchors the outlook.",
            "Weather is not in the production model yet (needs NASA POWER season history).",
            "Backtested on two seasons only (12 months): it beat the usual seasonal shape on both, but that is far "
            "too little to judge it; the DAM price history is needed (to-do). See /api/forecast/backtest.",
        ],
    }


# ---------------------------------------------------------------- regional prices

@lru_cache(maxsize=1)
def regional_index() -> list[dict]:
    """
    How each district's retail price compares with the national price in the same month,
    from WFP market reports. Districts with few reports are pulled towards 1.0 (the national level).
    """
    df = market_reports()
    nat = df.groupby("period").price.median().rename("national")
    df = df.join(nat, on="period")
    df["ratio"] = df.price / df.national
    out = []
    shrink = 3.0
    for district, rows in df.groupby("admin2"):
        n = len(rows)
        raw = float(rows.ratio.median())
        idx = (n * raw + shrink * 1.0) / (n + shrink)
        latest = rows.sort_values("date").iloc[-1]
        out.append({"district": _wfp_display(district), "index": round(idx, 2), "raw_index": round(raw, 2),
                    "reports": n, "latest_price": float(latest.price), "latest_date": str(latest.date)[:10]})
    return sorted(out, key=lambda r: r["index"])


def _wfp_display(name: str) -> str:
    fixes = {"Bogra": "Bogura", "Chittagong": "Chattogram", "Cox'S Bazar": "Cox's Bazar", "Comilla": "Cumilla",
             "Jessore": "Jashore", "Barisal": "Barishal", "Brahamanbaria": "Brahmanbaria"}
    return fixes.get(name, name)


def national_latest() -> dict:
    p = monthly_prices()
    p = p[p["count"] >= MIN_REPORTS].sort_values("period")
    last = p.iloc[-1]
    return {"month": str(last.period), "median": float(last["median"]), "reports": int(last["count"])}


def national_history() -> list[dict]:
    p = monthly_prices().sort_values("period")
    return [{"month": str(r["period"]), "median": round(float(r["median"]), 2), "reports": int(r["count"]),
             "used": bool(r["count"] >= MIN_REPORTS)} for _, r in p.iterrows()]
