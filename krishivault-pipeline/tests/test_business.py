"""Buyers, bank loans, group storage, export and the profit calculator."""

import pytest

from src.engine import export_intel, financing, group_storage, market_access, profit


@pytest.fixture(autouse=True)
def temp_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("KV_EVENTS_PATH", str(tmp_path / "events.jsonl"))
    monkeypatch.setenv("KV_RUNTIME_DIR", str(tmp_path))


def test_small_lot_cannot_reach_big_buyers():
    data = market_access.compare_offers(3000, 16)
    exporter = next(o for o in data["offers"] if o["id"] == "b-exporter")
    assert exporter["eligible"] is False and "group" in exporter["why_not"]


def test_highest_quote_is_not_always_best():
    data = market_access.compare_offers(3000, 16)
    assert data["highest_quote"]["id"] != data["best"]["id"]


def test_loan_counts_cold_storage_first():
    e = financing.loan_estimate(36, 16, 3, 2027, 6, "bank-a")
    assert e["paid_first_to_cold_storage"] == 36 * (250 + 30)
    assert e["max_loan"] <= 0.6 * e["collateral_value"]
    assert e["careful_price"] <= 16


def test_loan_risk_is_higher_when_asking_too_much():
    small = financing.loan_estimate(36, 16, 3, 2027, 8, "bank-a", amount=10000)
    big = financing.loan_estimate(36, 16, 3, 2027, 8, "bank-a", amount=40000)
    assert big["chance_crop_worth_less_than_repayment"] > small["chance_crop_worth_less_than_repayment"]
    assert big["problems"]


def test_receipt_must_match():
    app = financing.apply("Demo", None, "Bogura", "cs-a", "DEMO-1", 36, 16, 3, 2027, 6, "bank-a")
    out = financing.confirm_receipt(app["id"], 30)
    assert out["receipt_checked"]["matches"] is False and "not 36" in out["status"]


def test_group_discount_counts_only_when_agreed():
    cmp = group_storage.compare("g-shibganj", 40)
    assert cmp["group_now"]["rent"] == 250            # offer reached but not agreed
    assert cmp["group_if_agreed"]["rent"] == 240
    group_storage.agree_offer("g-shibganj", 300)
    cmp = group_storage.compare("g-shibganj", 40)
    assert cmp["group_now"]["rent"] == 240


def test_export_costs_add_up_and_flag_losses():
    ev = export_intel.evaluate("ru", 16)
    assert round(sum(line["per_kg"] for line in ev["cost_lines"]), 1) == round(ev["landed_cost_per_kg"], 1)
    all_ = export_intel.evaluate_all(16)
    assert {"profitable", "loss"} <= {m["verdict"] for m in all_["markets"]}


def test_sourcing_is_real_bbs_data():
    rows = export_intel.sourcing(5)
    assert rows[0]["production_t"] >= rows[-1]["production_t"]
    assert any(r["district"] == "Bogura" for r in rows)


def test_profit_example():
    r = profit.example()
    assert r["total_cost"] == r["growing_cost"] + r["after_harvest_cost"]
    assert r["profit"] == r["income"] - r["total_cost"]
    assert r["if_all_sold_at_harvest"]["difference"] > 0
    assert abs(r["cost_per_sack"] - r["cost_per_kg"] * 84) <= 1
