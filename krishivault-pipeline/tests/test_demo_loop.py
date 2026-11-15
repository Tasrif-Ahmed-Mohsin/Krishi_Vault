"""The whole loop in one click, the price-window alert's weight loss, and the shared signing key."""

import time

import pytest
from fastapi.testclient import TestClient

from src.engine import alerts, demo_loop, financing, market_access, receipts
from src.engine.facts import StorageTerms


@pytest.fixture(autouse=True)
def temp_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("KV_EVENTS_PATH", str(tmp_path / "events.jsonl"))
    monkeypatch.setenv("KV_RUNTIME_DIR", str(tmp_path))


def test_loop_runs_the_plan_end_to_end():
    out = demo_loop.run()                      # the demo call: 80 maunds, ৳16, ৳25,000 within 4 days
    assert [s["step"] for s in out["steps"]] == [1, 2, 3, 4, 5]
    assert out["steps"][0]["headline"] == "Sell 19 sacks now, store 17 until December"
    assert "DEMO" in out["note"] and "not a promise" in out["note"]

    # The receipt and the loan are real records, so the partner screens show them
    r = receipts.get(out["ids"]["receipt"])
    assert r["sacks"] == 17 and r["status"].startswith("sold")
    app = next(a for a in financing.applications() if a["id"] == out["ids"]["application"])
    assert app["status"] == "repaid from the sale (demo)"

    # The sale pays the cold storage, the bank, then the farmer; every taka is accounted for
    split = out["steps"][4]["split"]
    assert split[0]["line"] == "Sale" and split[-1]["to"] == "farmer"
    assert sum(x["tk"] for x in split[:-1]) == split[-1]["tk"]
    assert [x["to"] for x in split[1:-1]] == ["selling", "cold storage", "bank", "bank"]

    # The bad case is shown, not only the middle path
    assert any("bad-case price" in line for line in out["steps"][4]["lines"])


def test_loop_stops_honestly_in_a_glut_year():
    out = demo_loop.run(price_today=14, year=2025)     # the 2024-25 big crop: the engine says sell now
    assert len(out["steps"]) == 1 and out["steps"][0]["headline"] == "Sell now"
    assert "nothing goes into cold storage" in out["stopped"]
    assert receipts.all_receipts() == []


def test_loop_api():
    from src.main import app
    r = TestClient(app).post("/api/demo/loop", json={"maunds": 80, "price_today": 16}).json()
    assert len(r["steps"]) == 5 and r["steps"][3]["sms_bn"]


def test_alert_money_allows_for_weight_lost_in_store():
    r = receipts.issue("cs-a", "Demo farmer", None, 17, month=3, year=2027)
    a = alerts.price_window(12, 2027, 26, receipt_no=r["no"])[0]
    assert a["action"] == "sell" and a["sell_sacks"] == 17
    kg_left = r["kg"] * StorageTerms().kept_share(9)               # 9 months in store, rotten ones sorted out
    expected = market_access.compare_offers(kg_left, 26)["best"]["money_total"]
    assert a["buyer"]["money_total"] == expected
    assert a["buyer"]["money_total"] < market_access.compare_offers(r["kg"], 26)["best"]["money_total"]


def test_signing_key_is_shared_by_every_server_process(tmp_path, monkeypatch):
    from src.voice import conversation
    monkeypatch.delenv("KV_STATE_SECRET", raising=False)
    monkeypatch.setattr(conversation, "_secret", None)
    first = conversation.sign("কৃষিভল্ট")
    assert (tmp_path / "state_secret").read_text().strip()
    monkeypatch.setattr(conversation, "_secret", None)         # a second worker process starting up
    assert conversation.sign("কৃষিভল্ট") == first


def test_gemini_never_keeps_the_farmer_waiting(monkeypatch):
    from src.voice.gemini import GeminiClient
    g = GeminiClient(api_key="test", budget_s=0.2)
    monkeypatch.setattr(g, "_try_models", lambda *a, **k: time.sleep(2) or "late")
    start = time.time()
    assert g.text("anything") is None                      # the template answer is used instead
    assert time.time() - start < 1.0
