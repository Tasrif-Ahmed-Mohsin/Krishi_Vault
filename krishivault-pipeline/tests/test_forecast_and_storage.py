"""Production forecast, price outlook and the storage engine."""

import pytest

from src.engine.facts import StorageTerms, month_after
from src.engine.storage_plan import FarmerLot, StoragePlanner, months_left, quick_plan
from src.models.price_outlook import (
    calibrate, drop_stale, model_card, outlook, regional_index, rise_strength, season_for_decision,
)
from src.models.production_forecast import bbs_district, production_forecast


# ------------------------------------------------------------- production

def test_national_history_and_forecast():
    f = production_forecast()
    assert len(f["history"]) == 13
    assert f["season"] == "2025-26"
    assert f["low_t"] < f["production_t"] < f["high_t"]
    gaps = {h["season"]: h["gap_pct"] for h in f["history"]}
    # the two glut years stand out above the trend
    assert gaps["2016-17"] > 5 and gaps["2024-25"] > 5


def test_district_forecast_and_aliases():
    assert bbs_district("Bogura") == "Bogra"
    f = production_forecast("Bogura")
    assert f["area"] == "Bogura"
    assert 900_000 < f["production_t"] < 1_600_000


def test_known_season_has_no_range():
    f = production_forecast(None, 2024)
    assert f["low_t"] == f["production_t"] == f["high_t"]


def test_planted_area_changes_the_forecast():
    base = production_forecast(None, 2026)
    big = production_forecast(None, 2026, area_ha=base["area_trend_ha"] * 1.1)
    assert big["gap_pct"] > 8


# ------------------------------------------------------------- prices

def test_frozen_reports_are_dropped():
    import pandas as pd
    df = pd.DataFrame({"market": ["A"] * 5 + ["B"] * 2,
                       "date": pd.to_datetime(["2025-01-15", "2025-02-15", "2025-03-15", "2025-04-15", "2025-05-15",
                                               "2025-01-15", "2025-02-15"]),
                       "price": [62.5] * 5 + [20, 21]})
    assert set(drop_stale(df).market) == {"B"}


def test_calibration_tells_the_glut_story():
    cal = calibrate()
    k = {s["season"]: s["k"] for s in cal.seasons}
    assert k["2023-24"] > 0.7          # normal crop: prices nearly doubled
    assert k["2024-25"] < 0.2          # big crop: prices stayed flat
    assert cal.slope < 0               # a bigger crop means a smaller rise


def test_outlook_has_ranges_and_rises_in_a_normal_year():
    o = outlook(16.0, 3, 2027)
    months = o["months"]
    assert len(months) == 10 and months[0]["mid"] == 16.0
    for m in months[1:]:
        assert m["low"] <= m["mid"] <= m["high"]
    assert months[-1]["mid"] > 20
    assert months[-1]["high"] - months[-1]["low"] > months[1]["high"] - months[1]["low"]


def test_big_crop_flattens_the_outlook():
    normal = outlook(16.0, 3, 2027)["months"][-1]["mid"]
    big = outlook(16.0, 3, 2027, gap_override_pct=10)["months"][-1]["mid"]
    assert big < 16.0 < normal


def test_season_prices_correct_the_guess():
    rs = rise_strength(2025, decision_year=2026, decision_month=10)
    assert rs["season_months_used"] >= 3
    assert rs["k_sd"] < rs["k_from_crop_sd"]


def test_season_for_decision():
    assert season_for_decision(2026, 10) == 2025
    assert season_for_decision(2027, 1) == 2025
    assert month_after(11, 2) == 1


def test_model_card_states_limits():
    card = model_card()
    assert card["seasons_fitted"] and card["limits"]


def test_regional_index_is_sane():
    rows = regional_index()
    assert rows and all(0.5 < r["index"] < 1.6 for r in rows)


# ------------------------------------------------------------- storage engine

def test_months_left():
    assert months_left(FarmerLot(1000, 16, decision_month=3)) == 9
    assert months_left(FarmerLot(1000, 16, decision_month=10)) == 2
    assert months_left(FarmerLot(1000, 16, decision_month=10, stored="cold", stored_since_month=3)) == 2
    assert months_left(FarmerLot(1000, 16, decision_month=1)) == 0


def test_sacks_are_84_kg():
    assert FarmerLot(84 * 36, 16).sacks == 36
    assert FarmerLot(84 * 36 + 1, 16).sacks == 37


def test_big_crop_year_says_sell_now():
    r = quick_plan(3000, 14, decision_month=3, decision_year=2025)   # the 2024-25 crop
    assert r["recommendation"]["key"] == "sell_now"


def test_normal_crop_year_says_store():
    r = quick_plan(3000, 18, decision_month=3, decision_year=2024)   # the 2023-24 crop
    assert r["recommendation"]["key"] == "store"
    assert r["best_month"]["month_en"] in ("November", "December")
    assert r["options"]["store"]["gain_vs_now"] > 10000


def test_flat_rent_makes_early_sale_a_loss():
    r = quick_plan(3000, 18, decision_month=3, decision_year=2024)
    first = r["by_month"][1]
    assert first["gain_vs_now"] < 0            # paying a full season's rent for one month
    assert first["break_even_price"] > 18


def test_uncertain_year_suggests_selling_part():
    r = quick_plan(3000, 16, decision_month=3, decision_year=2027)
    assert r["recommendation"]["key"] == "sell_part"
    part = r["options"]["sell_part"]
    assert part["sell_sacks_now"] + part["store_sacks"] == 36


def test_cash_need_sells_enough_sacks_or_borrows():
    r = quick_plan(3000, 16, decision_month=3, decision_year=2027, cash_needed_tk=25000, cash_days=4)
    part = r["options"]["sell_part"]
    assert part["cash_now"] >= 25000
    store = r["options"]["store"]
    assert store["loan"]["source"] == "bank"    # 36 sacks x ৳250 advance is too little


def test_cash_need_too_big_for_any_loan():
    r = quick_plan(3000, 18, decision_month=3, decision_year=2024, cash_needed_tk=40000, cash_days=4)
    assert r["options"]["store"] is None
    assert r["recommendation"]["key"] == "sell_part"


def test_already_stored_rent_is_sunk():
    r = quick_plan(3000, 20, decision_month=10, decision_year=2026, stored="cold", stored_since_month=3)
    assert r["months_left"] == 2
    assert "owed either way" in r["notes"][0]


def test_group_rent_discount_helps():
    normal = quick_plan(3000, 16, decision_month=3, decision_year=2027)
    cheaper = quick_plan(3000, 16, decision_month=3, decision_year=2027, terms=StorageTerms(rent_per_sack=230))
    assert cheaper["options"]["store"]["money_mean"] > normal["options"]["store"]["money_mean"]


def test_cost_floor():
    r = quick_plan(3000, 12, decision_month=3, decision_year=2025, production_cost_per_kg=14)
    assert r["cost_floor"]["below_cost_today"] is True


def test_plan_is_repeatable():
    a = quick_plan(3000, 16, decision_month=3, decision_year=2027)
    b = quick_plan(3000, 16, decision_month=3, decision_year=2027)
    assert a["options"] == b["options"]
