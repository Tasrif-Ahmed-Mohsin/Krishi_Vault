"""The trader's advance (dadon) cost check and the hold plan against selling in fear."""

import pytest
from fastapi.testclient import TestClient

from src.engine import dadon, demo_loop, hold_plan
from src.engine.facts import MAUND_KG
from src.engine.storage_plan import FarmerLot, StoragePlanner
from src.voice.conversation import advice_sms

planner = StoragePlanner()


@pytest.fixture(autouse=True)
def temp_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("KV_EVENTS_PATH", str(tmp_path / "events.jsonl"))
    monkeypatch.setenv("KV_RUNTIME_DIR", str(tmp_path))


def _plan(**kw):
    lot = dict(quantity_kg=80 * MAUND_KG, price_today=16, decision_month=3, decision_year=2027)
    lot.update(kw)
    return planner.plan(FarmerLot(**lot))


# ------------------------------------------------------------------ dadon

def test_dadon_cost_is_the_price_gap_on_the_promised_potatoes():
    d = dadon.true_cost(20_000, 3, 80 * MAUND_KG, trader_price=14, market_price=16)
    assert d["hidden_cost"] == round(2 * 80 * MAUND_KG) == d["cost"]
    assert d["rate_year"] == pytest.approx(d["cost"] / 20_000 * 4, abs=1e-4)     # 3 months, 4 times a year
    assert d["rate_year"] > 1                                                     # over 100% a year
    assert d["bank"]["cost"] == round(20_000 * 0.11 * 3 / 12 + 20_000 * 0.005)   # demo bank: 11% + 0.5% fee
    assert d["saving_with_bank"] == d["cost"] - d["bank"]["cost"]
    assert "১১৯ শতাংশ" in d["say_bn"] and "৬,০০০" in d["say_bn"]


def test_dadon_with_no_discount_has_no_hidden_cost():
    d = dadon.true_cost(20_000, 3, 1000, trader_price=17, market_price=16)
    assert d["cost"] == 0 and d["rate_year"] == 0 and "লুকানো খরচ নেই" in d["say_bn"]


def test_dadon_fee_on_top_counts():
    d = dadon.true_cost(10_000, 2, 1000, trader_price=16, market_price=16, extra_tk=500)
    assert d["cost"] == 500 and d["rate_year"] == pytest.approx(0.3)


def test_dadon_api():
    from src.main import app
    c = TestClient(app)
    r = c.post("/api/finance/dadon", json={"advance_tk": 20000, "months": 3, "promised_maunds": 80,
                                           "trader_price": 14, "market_price": 16})
    assert r.status_code == 200 and r.json()["bank"]["demo"] is True
    assert c.post("/api/finance/dadon", json={"advance_tk": 0, "months": 3, "promised_maunds": 80,
                                              "trader_price": 14, "market_price": 16}).status_code == 422


# ------------------------------------------------------------------ hold plan

def test_hold_plan_says_not_before_the_first_month_that_pays():
    plan = _plan(cash_needed_tk=25_000, cash_days=4)          # the demo call: sell 19, store 17
    h = hold_plan.build(plan)
    assert h["sacks"] == 17 and h["sell_month_en"] == "December"
    first_pay = next(m for m in plan["by_month"] if m["h"] >= 1 and m["gain_vs_now"] >= 0)
    assert h["not_before_en"] == first_pay["month_en"]
    assert all(m["gain_vs_now"] < 0 for m in h["losing_months"])
    assert 1 <= len(h["checkpoints"]) <= hold_plan.MAX_CHECKPOINTS
    for c in h["checkpoints"]:                                  # the engine's own break-even prices
        m = next(x for x in plan["by_month"] if x["h"] == c["h"])
        assert c["sell_only_above"] == round(m["break_even_price"], 1)
    assert "বেচবেন না" in h["sms"] and "নিশ্চিত নয়" in h["sms"]


def test_no_hold_plan_when_the_advice_is_sell_now():
    plan = _plan(price_today=14, decision_year=2025)           # the 2024-25 glut
    assert plan["recommendation"]["key"] == "sell_now"
    assert hold_plan.build(plan) is None


def test_advice_sms_carries_the_not_before_line():
    plan = _plan(cash_needed_tk=25_000, cash_days=4)
    h = hold_plan.build(plan)
    assert f"{h['not_before_bn']} মাসের আগে বেচবেন না" in advice_sms(plan)


def test_hold_plan_api_and_sms():
    from src.main import app
    c = TestClient(app)
    body = {"quantity": 80, "unit": "maund", "price_today": 16, "month": 3, "year": 2027,
            "cash_needed_tk": 25000, "cash_days": 4}
    plan = c.post("/api/storage/plan", json=body).json()
    assert plan["hold_plan"]["sacks"] == 17
    r = c.post("/api/sms/hold-plan", json={**body, "phone": "01711998877"}).json()
    assert r["dry_run"] is True and r["text"] == plan["hold_plan"]["sms"]
    glut = {**body, "price_today": 14, "year": 2025, "phone": "01711998877"}
    assert c.post("/api/sms/hold-plan", json=glut).status_code == 400


def test_the_loop_hands_over_the_hold_plan_with_the_receipt():
    step2 = demo_loop.run()["steps"][1]
    assert step2["hold_sms_bn"] and any("not before" in line for line in step2["lines"])


# ------------------------------------------------------------------ alerts by voice, and the SMS allow-list

def _voice_alerts(client):
    return client.post("/api/alerts/price-window", json={"month": 12, "year": 2027, "price_today": 26,
                                                         "send": True, "channel": "voice"}).json()


def test_price_window_alert_by_voice_reads_the_alert():
    from unittest.mock import MagicMock, patch
    from src.engine import receipts
    from src.main import app, reset_call_limits
    reset_call_limits()
    receipts.issue("cs-a", "Demo farmer", "01711998877", 17, month=3, year=2027)
    vb = MagicMock(live=True, default_audio_id=1106)      # a mock: nothing is dialled
    vb.send_call.return_value = {"success": True, "phone": "01711998877"}
    with patch("src.main.get_broadcast_api_client", return_value=MagicMock(live=False)), \
         patch("src.main.get_voiceblast_client", return_value=vb), \
         patch("src.notify.call_audio.voiceblast_audio_id", return_value=77) as audio:
        out = _voice_alerts(TestClient(app))
    assert out[0]["action"] == "sell" and out[0]["call_result"]["success"] is True
    assert out[0]["call_result"]["phone"] == "01711-XXX877"                # masked in the answer
    spoken = audio.call_args.args[0]
    assert "১৭ বস্তা বেচুন" in spoken and "(ডেমো)" not in spoken and "ডেমো বার্তা" in spoken
    vb.send_call.assert_called_once_with("01711998877", audio_file_id=77, caller_id=None)


def test_voice_alerts_keep_the_call_limits(monkeypatch):
    from src.engine import receipts
    from src.main import app, reset_call_limits
    monkeypatch.setenv("CALL_ALLOWED_NUMBERS", "01812345679")
    reset_call_limits()
    receipts.issue("cs-a", "Demo farmer", "01711998877", 17, month=3, year=2027)
    out = _voice_alerts(TestClient(app))
    assert "restricted" in out[0]["call_result"]["error"].lower()


def test_live_sms_only_to_allowed_numbers(monkeypatch):
    from src.notify import sms
    for k, v in {"SMS_LIVE": "1", "SMS_API_KEY": "k", "SMS_SECRET_KEY": "s", "SMS_SENDER_ID": "x",
                 "SMS_ALLOWED_NUMBERS": "01812345679"}.items():
        monkeypatch.setenv(k, v)
    r = sms.send_sms("01711998877", "কৃষিভল্ট পরীক্ষা")                  # refused before any network call
    assert r["dry_run"] is False and "restricted" in r["error"]


# ------------------------------------------------------------------ every message also as a call

def test_sms_becomes_speech_with_the_same_numbers():
    from src.notify.call_audio import call_text, sms_speech
    sms = "কৃষিভল্ট: রসিদ CSA-0004। এখন দাম ভালো: ৮ বস্তা বেচুন; প্রায় ১৪,৬০০ টাকা। (ডেমো)"
    spoken = sms_speech(sms)
    assert spoken == "রসিদ CSA-0004। এখন দাম ভালো: ৮ বস্তা বেচুন; প্রায় ১৪,৬০০ টাকা। এটি ডেমো বার্তা।"
    assert call_text(spoken).startswith("আসসালামু আলাইকুম, কৃষিভল্ট থেকে বলছি।")


def test_call_me_choice_follows_the_farmer_from_receipt_to_loan_to_alert():
    from unittest.mock import patch
    from src import contacts
    from src.main import app, reset_call_limits
    reset_call_limits()
    c = TestClient(app, client=("127.0.0.1", 50000))
    calls = []
    with patch("src.main.dispatch_call", side_effect=lambda phone, text: calls.append((phone, text)) or
               {"success": True, "dry_run": True}):
        r = c.post("/api/receipts", json={"cold_storage_id": "cs-a", "farmer_name": "Rahim", "phone": "01711998877",
                                          "sacks": 17, "month": 3, "year": 2027, "voice": True}).json()
        no = r["receipt"]["no"]
        assert r["receipt"]["by_call"] is True and r["call_result"]["success"] is True
        assert contacts.prefers_voice(f"receipt:{no}") and "পরিকল্পনা" not in calls[-1][1]
        assert no in calls[-1][1] and "এটি ডেমো বার্তা" in calls[-1][1]              # the receipt, read out

        app_ = c.post("/api/finance/apply", json={"sacks": 17, "price_today": 16, "month": 3, "year": 2027,
                                                  "months": 9, "farmer_name": "Rahim", "receipt_no": no}).json()
        c.post(f"/api/finance/applications/{app_['id']}/receipt", json={"sacks_found": 17})
        d = c.post(f"/api/finance/applications/{app_['id']}/decision", json={"approve": True}).json()
        assert d["call_result"]["success"] is True and "ঋণ অনুমোদন" in calls[-1][1]   # the decision, read out

        reset_call_limits()
        a = c.post("/api/alerts/price-window", json={"month": 12, "year": 2027, "price_today": 26,
                                                      "send": True}).json()
        assert a[0]["sms_result"]["dry_run"] is True and a[0]["call_result"]["success"] is True
    assert all(phone == "01711998877" for phone, _ in calls) and len(calls) == 3


def test_no_call_for_a_farmer_who_reads_sms():
    from src.main import app
    c = TestClient(app)
    r = c.post("/api/receipts", json={"cold_storage_id": "cs-a", "farmer_name": "Karim", "phone": "01711998877",
                                      "sacks": 10}).json()
    assert r["receipt"]["by_call"] is False and "call_result" not in r
    a = c.post("/api/alerts/price-window", json={"month": 12, "year": 2027, "price_today": 26, "send": True}).json()
    assert "call_result" not in a[0]


def test_advice_hold_plan_and_curing_by_call():
    from unittest.mock import patch
    from src.main import app, reset_call_limits
    from src.notify.call_audio import sms_speech
    reset_call_limits()
    c = TestClient(app, client=("127.0.0.1", 50000))
    body = {"quantity": 80, "unit": "maund", "price_today": 16, "month": 3, "year": 2027,
            "cash_needed_tk": 25000, "cash_days": 4, "phone": "01711998877", "voice": True}
    spoken = []
    with patch("src.main.dispatch_call", side_effect=lambda phone, text: spoken.append(text) or
               {"success": True, "dry_run": True}):
        for path, payload in (("/api/sms/advice", body), ("/api/sms/hold-plan", body),
                              ("/api/sms/curing", {"phone": "01711998877", "voice": True})):
            r = c.post(path, json=payload).json()
            assert r["dry_run"] is True and r["call_result"]["success"] is True
            assert spoken[-1] == sms_speech(r["text"])                    # the SMS's own words
        r = c.post("/api/sms/advice", json={**body, "voice": False}).json()
    assert "call_result" not in r and len(spoken) == 3
