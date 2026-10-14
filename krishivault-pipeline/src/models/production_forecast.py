"""
Potato production forecast
==========================
Predicts a season's potato production, for Bangladesh and for each district,
from the BBS crop statistics in `data/reference/mati_kohon/crop_district_panel.csv`
(13 seasons, 2012-13 to 2024-25, 64 districts).

How it works, in plain words:
- Production has grown about 1.8% a year. We fit that trend (a straight line
  through the logarithm of production) and read the next season off it.
- The range comes from how far real seasons fell from the trend in the past.
- If the planted area for the new season is known (DAE reports it in
  January), area times the yield trend replaces the trend guess.
- "Crop gap" = how far a season is above (+) or below (-) the trend. Big
  positive gaps (2016-17: +7%, 2024-25: +6%) were the glut years when prices
  collapsed; the price outlook uses the gap.

Not yet in the model: weather. That needs season weather for 2012-2025
(NASA POWER), which is a to-do; a weather adjustment can be entered by hand.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

PANEL_PATH = Path(__file__).resolve().parents[2] / "data" / "reference" / "mati_kohon" / "crop_district_panel.csv"

Z80 = 1.2816  # 80% range: 1 season in 10 below, 1 in 10 above

# BBS spellings, and the names people use
DISTRICT_ALIASES = {
    "bogura": "Bogra", "bogra": "Bogra", "chattogram": "Chittagong", "chittagong": "Chittagong",
    "cumilla": "Comilla", "comilla": "Comilla", "jashore": "Jessore", "jessore": "Jessore",
    "barishal": "Barisal", "barisal": "Barisal", "chapainawabganj": "Nawabganj",
    "chapai nawabganj": "Nawabganj", "nawabganj": "Nawabganj", "brahmanbaria": "Brahamanbaria",
    "cox's bazar": "Cox's Bazar", "coxs bazar": "Cox's Bazar", "moulvibazar": "Maulvibazar",
    "jhalakathi": "Jhalokati", "netrokona": "Netrakona",
}
DISPLAY_NAMES = {"Bogra": "Bogura", "Chittagong": "Chattogram", "Comilla": "Cumilla",
                 "Jessore": "Jashore", "Barisal": "Barishal", "Nawabganj": "Chapai Nawabganj"}


def bbs_district(name: str) -> str:
    key = (name or "").strip().lower()
    if key in DISTRICT_ALIASES:
        return DISTRICT_ALIASES[key]
    return (name or "").strip().title()


def display_district(bbs_name: str) -> str:
    return DISPLAY_NAMES.get(bbs_name, bbs_name)


def season_label(start_year: int) -> str:
    return f"{start_year}-{str(start_year + 1)[-2:]}"


@lru_cache(maxsize=1)
def load_panel() -> pd.DataFrame:
    df = pd.read_csv(PANEL_PATH)
    df = df[(df.crop == "Potato") & (df.variant == "total")].copy()
    df["start_year"] = df.year.str[:4].astype(int)
    return df[["district", "year", "start_year", "area_ha", "production_t", "yield_t_ha"]]


def district_names() -> list[str]:
    return sorted(display_district(d) for d in load_panel().district.unique())


@dataclass
class TrendFit:
    intercept: float
    slope: float          # log units a year
    resid_sd: float       # log units
    n: int
    x_mean: float
    sxx: float

    def predict_log(self, year: float) -> float:
        return self.intercept + self.slope * year

    def prediction_sd(self, year: float) -> float:
        """Spread of a new season around the trend, including the trend's own uncertainty."""
        return self.resid_sd * math.sqrt(1 + 1 / self.n + (year - self.x_mean) ** 2 / self.sxx)


def _fit(years: np.ndarray, values: np.ndarray) -> TrendFit:
    y = np.log(values)
    slope, intercept = np.polyfit(years, y, 1)
    resid = y - (intercept + slope * years)
    dof = max(len(years) - 2, 1)
    return TrendFit(
        intercept=float(intercept), slope=float(slope),
        resid_sd=float(math.sqrt((resid ** 2).sum() / dof)), n=len(years),
        x_mean=float(years.mean()), sxx=float(((years - years.mean()) ** 2).sum()),
    )


def _series(district: Optional[str]) -> pd.DataFrame:
    df = load_panel()
    if district and district.lower() not in ("bangladesh", "national", "all"):
        df = df[df.district == bbs_district(district)]
        if df.empty:
            raise KeyError(f"No potato data for district {district}")
    g = df.groupby("start_year")[["area_ha", "production_t"]].sum().sort_index()
    g = g[(g.production_t > 0) & (g.area_ha > 0)]
    g["yield_t_ha"] = g.production_t / g.area_ha
    return g


def production_forecast(district: Optional[str] = None, season_start: Optional[int] = None,
                        area_ha: Optional[float] = None, weather_adjust_pct: float = 0.0) -> dict:
    """
    History and a forecast for one season.
    district: None for all Bangladesh. season_start: 2026 means the 2026-27 crop
    (harvested February-March 2027); default is the season after the last BBS year.
    area_ha: the planted area if known. weather_adjust_pct: a hand-entered yield change.
    """
    g = _series(district)
    years = g.index.values.astype(float)
    prod_fit = _fit(years, g.production_t.values)
    yield_fit = _fit(years, g.yield_t_ha.values)
    area_fit = _fit(years, g.area_ha.values)
    last = int(years.max())
    target = int(season_start) if season_start else last + 1

    history = []
    for yr, row in g.iterrows():
        trend = math.exp(prod_fit.predict_log(yr))
        history.append({
            "season": season_label(int(yr)), "start_year": int(yr),
            "production_t": round(float(row.production_t)), "area_ha": round(float(row.area_ha)),
            "yield_t_ha": round(float(row.yield_t_ha), 2),
            "trend_t": round(trend), "gap_pct": round((row.production_t / trend - 1) * 100, 1),
        })

    trend_t = math.exp(prod_fit.predict_log(target))
    adjust = 1 + weather_adjust_pct / 100.0
    if target in g.index:
        actual = float(g.loc[target, "production_t"])
        mid, sd_log, basis = actual, 0.0, "BBS figure for this season"
    elif area_ha:
        yield_mid = math.exp(yield_fit.predict_log(target)) * adjust
        mid = area_ha * yield_mid
        sd_log = yield_fit.prediction_sd(target)
        basis = "planted area entered x the yield trend"
    else:
        mid = trend_t * adjust
        sd_log = prod_fit.prediction_sd(target)
        basis = "the 13-season trend"
    if weather_adjust_pct and target not in g.index:
        basis += f", weather adjustment {weather_adjust_pct:+.0f}%"

    gap = mid / trend_t - 1
    return {
        "area": display_district(bbs_district(district)) if district else "Bangladesh",
        "season": season_label(target), "start_year": target,
        "harvest": f"February-March {target + 1}",
        "basis": basis,
        "production_t": round(mid),
        "low_t": round(mid * math.exp(-Z80 * sd_log)),
        "high_t": round(mid * math.exp(Z80 * sd_log)),
        "trend_t": round(trend_t),
        "gap_pct": round(gap * 100, 1),
        "gap_sd_pct": round(sd_log * 100, 1),
        "trend_growth_pct_year": round((math.exp(prod_fit.slope) - 1) * 100, 2),
        "area_trend_ha": round(math.exp(area_fit.predict_log(target))),
        "yield_trend_t_ha": round(math.exp(yield_fit.predict_log(target)), 2),
        "history": history,
        "source": "BBS Yearbook of Agricultural Statistics, potato (all varieties), 2012-13 to 2024-25",
    }


def crop_gap(season_start: int, area_ha: Optional[float] = None, weather_adjust_pct: float = 0.0,
             gap_override_pct: Optional[float] = None) -> tuple[float, float]:
    """
    The national crop gap for a season as (mean, spread), both as fractions.
    A known BBS season has no spread. gap_override_pct lets a user try "what if the crop is 10% big".
    """
    if gap_override_pct is not None:
        return gap_override_pct / 100.0, 0.0
    f = production_forecast(None, season_start, area_ha, weather_adjust_pct)
    return f["gap_pct"] / 100.0, f["gap_sd_pct"] / 100.0


def district_supply(season_start: Optional[int] = None) -> list[dict]:
    """Each district's potato production and share of the country, latest BBS season."""
    df = load_panel()
    year = season_start or int(df.start_year.max())
    d = df[df.start_year == year]
    total = float(d.production_t.sum())
    rows = []
    for _, r in d.iterrows():
        if r.production_t <= 0:
            continue
        rows.append({
            "district": display_district(r.district), "season": season_label(year),
            "production_t": round(float(r.production_t)), "area_ha": round(float(r.area_ha)),
            "yield_t_ha": round(float(r.yield_t_ha), 2), "share_pct": round(r.production_t / total * 100, 2),
        })
    return sorted(rows, key=lambda r: -r["production_t"])
