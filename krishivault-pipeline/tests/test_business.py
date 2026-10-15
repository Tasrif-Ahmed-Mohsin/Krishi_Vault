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
    assert e["paid_first_to_cold_storage"] == 36 * (300 + 30)       # the plan's ৳300 rent, then selling
    assert e["max_loan"] <= 0.6 * e["collateral_value"]
    assert e["careful_price"] <= 16


def test_loan_values_the_crop_after_the_full_season_loss():
    short = financing.loan_estimate(36, 16, 3, 2027, 2, "bank-a")
    assert short["crop"]["shrinkage_buffer"] == 0.0865
    assert short["crop"]["kg_at_end"] == round(36 * 84 * (1 - 0.0865))     # the 8.65% buffer, even for 2 months


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
    assert cmp["group_now"]["rent"] == 300            # offer reached but not agreed
    assert cmp["group_if_agreed"]["rent"] == 285
    group_storage.agree_offer("g-shibganj", 300)
    cmp = group_storage.compare("g-shibganj", 40)
    assert cmp["group_now"]["rent"] == 285


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


# ------------------------------------------------------------- receipts, the bank's hold, the split at sale

def test_cold_storage_issues_a_receipt_with_an_sms():
    from src.engine import receipts
    r = receipts.issue("cs-a", "Demo farmer", "01711998877", 36, grade="table")
    assert r["no"] == "CSA-0001" and r["kg"] == 36 * 84 and r["phone"] == "01711-XXX877"
    assert "CSA-0001" in r["sms"] and "৩৬ বস্তা" in r["sms"] and "৩,০২৪ কেজি" in r["sms"] and "ডেমো" in r["sms"]
    assert receipts.issue("cs-a", "Another", None, 10)["no"] == "CSA-0002"
    assert receipts.get("csa-০০০১")["sacks"] == 36          # Bangla digits and lower case still find it
    with pytest.raises(ValueError):
        receipts.issue("cs-a", "Demo", None, 5, advance_per_sack=400)     # above the cold storage's advance


def test_sale_pays_cold_storage_then_bank_then_farmer():
    from src.engine import receipts
    out = receipts.split_sale(60000, 1000, {"Rent": 9000}, {"Bank loan": 20000, "Bank interest": 1500})
    assert [l["to"] for l in out["lines"]] == ["buyer pays", "selling", "cold storage", "bank", "bank", "farmer"]
    assert out["farmer_gets"] == 60000 - 1000 - 9000 - 21500 and out["covered"]
    short = receipts.split_sale(25000, 1000, {"Rent": 9000}, {"Bank loan": 20000, "Bank interest": 1500})
    assert short["farmer_gets"] == 0 and short["unpaid"] == 6500 and not short["covered"]


def test_approved_loan_holds_the_receipt_until_the_sale():
    from src.engine import receipts
    r = receipts.issue("cs-a", "Demo farmer", None, 36)
    app = financing.apply("Demo farmer", None, "Bogura", "cs-a", r["no"], 36, 16, 3, 2027, 6, "bank-a")
    assert app["receipt"]["on_krishivault"] and app["receipt"]["enough"]
    with pytest.raises(ValueError):
        financing.settle_sale(app["id"], 25)                        # not approved yet
    financing.confirm_receipt(app["id"], 36)
    financing.bank_decision(app["id"], True)
    assert receipts.get(r["no"])["hold"]["bank"] == "Demo Bank A"
    out = financing.settle_sale(app["id"], 25)
    assert out["covered"] and out["farmer_gets"] > 0
    assert out["kg_sold"] == round(36 * 84 * (1 - 0.0865))
    assert receipts.get(r["no"])["hold"] is None
    assert next(a for a in financing.applications() if a["id"] == app["id"])["status"].startswith("repaid")


def test_loan_estimate_shows_the_split_at_sale():
    e = financing.loan_estimate(36, 16, 3, 2027, 9, "bank-a")
    to = [l["to"] for l in e["at_sale"]["lines"]]
    assert to.index("cold storage") < to.index("bank") < to.index("farmer")


# ------------------------------------------------------------- the government screen

def test_farmer_figures_need_consent_and_five_farmers():
    from src.engine import farmer_signals
    assert farmer_signals.district_figures() == []
    for i in range(4):
        farmer_signals.record("Bogura", 3, 2027, 36, 25000 if i < 3 else 0, 4, "no", "sell_part", "call")
    hidden = farmer_signals.district_figures()[0]
    assert hidden["shown"] is False and hidden["farmers"] == 4 and "need_cash_within_7_days" not in hidden
    farmer_signals.record("Bogura", 3, 2027, 20, 10000, 30, "no", "sell_now", "dashboard")
    shown = farmer_signals.district_figures()[0]
    assert shown["shown"] and shown["farmers"] == 5
    assert shown["need_cash_within_7_days"] == 0.6          # 3 of the 5 farmers at harvest
    assert shown["advised"]["sell_part"] == 0.8
    assert "phone" not in str(farmer_signals.district_figures())


def test_glut_warning_follows_the_crop():
    from src.engine import farmer_signals
    assert farmer_signals.glut_watch(3, 2025)["level"] == "high"            # the 2024-25 big crop
    assert farmer_signals.glut_watch(3, 2027, gap_override_pct=-8)["level"] == "low"
    view = farmer_signals.government_view(3, 2027)
    assert view["storage"] and all(c["demo"] for c in view["storage"])


# ------------------------------------------------------------- the business plan

def test_business_plan_reproduces_the_plan_document():
    from src.engine import business_model as bm
    fees = bm.unit_fees()
    assert fees["cold_storage_per_bag"] == 12 and fees["bank_per_financed_bag"] == 4.5 and fees["buyer_per_bag"] == 12
    y1, y2, y3 = bm.projection()
    assert y1["bags"] == 80_000 and y2["bags"] == 600_000 and y3["bags"] == 2_400_000
    assert y1["streams"] == {"telco_vas": 60_000, "cold_storage": 960_000, "bank": 216_000, "buyers": 288_000,
                             "government_media": 200_000}
    assert (y1["revenue"], y2["revenue"], y3["revenue"]) == (1_724_000, 12_630_000, 49_220_000)
    assert (y1["profit"], y2["profit"], y3["profit"]) == (-126_000, 6_830_000, 34_720_000)
    assert (y1["margin"], y2["margin"], y3["margin"]) == (-0.073, 0.541, 0.705)
    assert bm.startup_capital()["total"] == 2_000_000
    assert len(bm.notes()) == 4 and "৳300" in bm.notes()[0]


def test_curing_reminder_text():
    from src.voice.conversation import curing_sms
    assert "১-২ সপ্তাহ ছায়ায়" in curing_sms() and "হিমাগারে" in curing_sms()


def test_one_receipt_cannot_back_two_loans():
    from src.engine import receipts
    r = receipts.issue("cs-a", "Demo farmer", None, 36)
    first = financing.apply("Demo farmer", None, "Bogura", "cs-a", r["no"], 36, 16, 3, 2027, 6, "bank-a")
    second = financing.apply("Demo farmer", None, "Bogura", "cs-a", r["no"], 36, 16, 3, 2027, 6, "bank-b")
    financing.bank_decision(first["id"], True)
    with pytest.raises(ValueError):
        financing.bank_decision(second["id"], True)
    assert financing.bank_decision(second["id"], False)["status"].startswith("declined")


# ------------------------------------------------------------- the rest of the plan's loop

def test_only_verified_cold_storages_issue_receipts():
    from src.engine import receipts
    with pytest.raises(ValueError, match="generator"):
        receipts.issue("cs-c", "Demo", None, 10)          # no backup generator: not a partner yet (plan rule)


def test_bank_approval_pays_out_and_messages_the_farmer():
    from src import contacts
    from src.engine import receipts
    r = receipts.issue("cs-a", "Demo farmer", "01711998877", 36)
    app = financing.apply("Demo farmer", None, "Bogura", "cs-a", r["no"], 36, 16, 3, 2027, 6, "bank-a")
    assert contacts.get(f"application:{app['id']}") == "01711998877"    # from the receipt, never shown
    out = financing.bank_decision(app["id"], True)
    assert out["paid_out"]["amount"] == app["estimate"]["loan"] and "mobile" in out["paid_out"]["to"]
    assert r["no"] in financing.decision_sms(out) and "ডেমো" in financing.decision_sms(out)


def test_price_window_alerts_say_sell_or_hold():
    from src.engine import alerts, receipts
    receipts.issue("cs-a", "Demo farmer", "01711998877", 36, month=3, year=2026)
    found = alerts.price_window(10, 2026, 22)
    a = found[0]
    assert a["action"] in ("sell", "hold") and a["receipt"] == "CSA-0001" and "ডেমো" in a["sms"]
    if a["action"] == "sell":
        assert a["sell_sacks"] > 0 and a["buyer"]["money_total"] > 0
    sent = alerts.send(found, lambda phone, text: {"dry_run": True, "to": phone})
    assert sent[0]["sms_result"]["to"] == "01711998877"


def test_group_sell_reaches_big_buyers():
    s = group_storage.group_sale("g-shibganj", 16)
    assert s["lot_per_kg"] > s["haat_per_kg"] and s["total_gain"] > 0
    assert any(x["min_kg"] >= 5000 for x in s["shares"])           # a buyer one farmer alone cannot reach
    assert sum(x["kg"] for x in s["shares"]) == s["lot_kg"]


def test_full_cold_storage_counts_for_government():
    from src.engine import farmer_signals
    from src import demo_data
    cs = demo_data.cold_storage("cs-a")
    assert farmer_signals.free_sacks(cs) == cs["capacity_sacks"] - cs["booked_sacks"]
