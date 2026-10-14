"""The API behind the dashboard and the call preview."""

import pytest
from fastapi.testclient import TestClient

from src.main import app, gemini_client, tts_service


@pytest.fixture(autouse=True)
def temp_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("KV_EVENTS_PATH", str(tmp_path / "events.jsonl"))
    monkeypatch.setenv("KV_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setenv("SMS_LIVE", "0")
    monkeypatch.setattr(gemini_client, "api_key", "")  # no network calls, even when GEMINI_API_KEY is set


@pytest.fixture
def client():
    return TestClient(app)


def test_pages(client):
    assert "KrishiVault" in client.get("/").text
    assert "KrishiVault" in client.get("/call").text


def test_status_has_no_keys(client):
    data = client.get("/api/status").json()
    assert data["status"] == "operational"
    assert "preview" in data["calls"]
    text = str(data).lower()
    assert "secret" not in text and "api_key" not in text


def test_forecasts(client):
    prod = client.get("/api/forecast/production?district=Bogura").json()
    assert prod["area"] == "Bogura" and len(prod["history"]) == 13
    price = client.get("/api/forecast/price?price_today=16&month=3&year=2027").json()
    assert len(price["months"]) == 10
    assert client.get("/api/forecast/price?price_today=0").status_code == 400
    model = client.get("/api/forecast/model").json()
    assert model["card"]["limits"]
    assert client.get("/api/forecast/production?district=Atlantis").status_code == 404


def test_regions(client):
    data = client.get("/api/market/regions").json()
    assert data["price_index"] and data["supply"][0]["production_t"] > 0


def test_storage_plan(client):
    r = client.post("/api/storage/plan", json={"quantity": 36, "unit": "sack", "price_today": 18, "month": 3, "year": 2024})
    assert r.status_code == 200
    plan = r.json()
    assert plan["inputs"]["sacks"] == 36 and plan["recommendation"]["key"] == "store"
    r = client.post("/api/storage/plan", json={"quantity": 80, "price_today": 16, "terms": {"rent_per_sack": 300}})
    assert r.json()["inputs"]["terms"]["rent_per_sack"] == 300
    assert client.post("/api/storage/plan", json={"quantity": -1, "price_today": 16}).status_code == 422


def test_offers(client):
    data = client.post("/api/market/offers", json={"quantity_kg": 3000, "price_today": 16,
                                                   "extra_offers": [{"name": "Neighbour's trader", "price_per_kg": 17}]}).json()
    eligible = [o for o in data["offers"] if o["eligible"]]
    assert eligible == sorted(eligible, key=lambda o: -o["money_total"])
    assert any(o["type"] == "own offer" for o in eligible)


def test_finance_flow(client):
    est = client.post("/api/finance/estimate", json={"sacks": 36, "price_today": 16, "months": 6}).json()
    assert any(r["bank"]["id"] == "bank-a" for r in est)
    app_ = client.post("/api/finance/apply", json={"sacks": 36, "price_today": 16, "months": 6, "farmer_name": "Demo",
                                                   "receipt_no": "DEMO-1"}).json()
    assert app_["status"].startswith("waiting")
    r = client.post(f"/api/finance/applications/{app_['id']}/receipt", json={"sacks_found": 36}).json()
    assert r["receipt_checked"]["matches"]
    r = client.post(f"/api/finance/applications/{app_['id']}/decision", json={"approve": True}).json()
    assert "approved" in r["status"]
    assert client.get("/api/events?partner=bank").json()[0]["kind"] == "loan_application"


def test_groups(client):
    pools = client.get("/api/groups?district=Bogura").json()
    assert pools
    cmp = client.post("/api/groups/compare", json={"pool_id": pools[0]["id"], "sacks": 40}).json()
    assert cmp["group_now"]["saving"] > 0
    joined = client.post("/api/groups/join", json={"pool_id": pools[0]["id"], "sacks": 40, "name": "Demo"}).json()
    assert joined["pool"]["total_sacks"] == pools[0]["total_sacks"] + 40
    assert client.post("/api/groups/compare", json={"pool_id": "nope", "sacks": 4}).status_code == 404


def test_export(client):
    src = client.get("/api/export/sourcing").json()
    assert src["districts"][0]["production_t"] > 0
    ev = client.post("/api/export/evaluate", json={"farmgate_price": 16}).json()
    assert ev["markets"] and "demo" in ev["note"].lower()


def test_profit(client):
    ex = client.get("/api/profit/example").json()
    inp = ex["inputs"]
    r = client.post("/api/profit/calculate", json={"harvest_kg": inp["harvest_kg"], "growing": inp["growing"],
                                                   "after": inp["after"], "sales": inp["sales"],
                                                   "harvest_price_per_kg": 14}).json()
    assert r["profit"] == ex["result"]["profit"]


def test_sms_advice_is_dry_run(client):
    r = client.post("/api/sms/advice", json={"quantity": 80, "price_today": 16, "phone": "01711000000"}).json()
    assert r["dry_run"] is True and r["text"].startswith("কৃষিভল্ট")


def test_call_turns_and_sms(client):
    r = client.post("/api/call/turn", json={"kind": "start", "month": 3, "year": 2024}).json()
    for d in ["1", "80#", "18#", "0#", "1"]:
        r = client.post("/api/call/turn", json={"kind": "keypad", "digits": d, "state": r["state"]}).json()
    assert r["result"]["key"] == "store"
    sms = client.post("/api/call/sms", json={"state": r["state"], "phone": "01711000000"}).json()
    assert sms["dry_run"] is True
    bad = dict(r["state"], sms="anything")
    assert client.post("/api/call/sms", json={"state": bad, "phone": "01711000000"}).status_code == 400
    assert client.post("/api/call/turn", json={"kind": "keypad", "digits": "1"}).status_code == 400


def test_old_misleading_endpoints_are_gone(client):
    assert client.get("/api/prices/predict/Bogura").status_code == 404
    assert client.post("/api/call/ring", json={}).status_code in (404, 405)


@pytest.mark.skipif(tts_service.ready, reason="only checks the no-key path")
def test_speak_without_key(client):
    assert client.post("/api/voice/speak", json={"text": "পরীক্ষা"}).status_code == 503


def test_booking_and_lot_reach_partner_screens(client):
    b = client.post("/api/storage/book", json={"sacks": 36, "farmer_name": "Demo"}).json()
    assert b["for"] == "cold_storage" and b["ref"].isdigit()
    lot = client.post("/api/market/lot", json={"kg": 3000, "price_today": 16, "farmer_name": "Demo"}).json()
    assert lot["for"] == "buyer"
    assert client.post("/api/storage/book", json={"sacks": 3, "farmer_name": "x", "cold_storage_id": "zz"}).status_code == 404


def test_backtest(client):
    r = client.get("/api/forecast/backtest")
    assert r.status_code == 200
    data = r.json()
    assert data["seasons"] and data["summary"]["outlook"]["average_miss_pct"] is not None
