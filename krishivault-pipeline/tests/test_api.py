"""
API Endpoint Integration Tests
==============================
Tests FastAPI endpoints:
- GET /
- GET /api/prices/latest
- GET /api/prices/predict/{district}
- POST /api/decision/evaluate
- POST /api/voice/webhook
- GET /api/cold-storages
- GET /api/buyers
"""

import pytest
from fastapi.testclient import TestClient
from src.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "KrishiVault" in response.text

def test_api_status_endpoint(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"

def test_latest_prices_endpoint(client):
    response = client.get("/api/prices/latest?district=Bogura")
    assert response.status_code == 200
    prices = response.json()
    assert isinstance(prices, list)

def test_price_prediction_endpoint(client):
    response = client.get("/api/prices/predict/Bogura")
    assert response.status_code == 200
    data = response.json()
    assert "forecasts" in data
    assert "7_days" in data["forecasts"]
    assert "30_days" in data["forecasts"]

def test_decision_evaluation_endpoint(client):
    payload = {
        "crop": "potato",
        "quantity_maunds": 50.0,
        "district": "Bogura",
        "cash_needed_tk": 15000.0,
        "deadline_days": 5,
        "has_cold_storage": True
    }
    response = client.post("/api/decision/evaluate", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert "recommendation" in res
    assert "all_scenarios" in res
    assert "bangla_voice_response" in res

def test_voice_webhook_endpoint(client):
    payload = {
        "phone_number": "+8801711998877",
        "caller_name": "আব্দুর রহিম",
        "transcript": "আমার ৪০ মণ আলু উঠছে। জরুরি ১৫ হাজার টাকা দরকার ৩ দিনে।"
    }
    response = client.post("/api/voice/webhook", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert "extracted_entities" in res
    assert res["extracted_entities"]["quantity_maunds"] == 40.0
    assert res["extracted_entities"]["cash_needed_tk"] == 15000.0
    assert "response_speech_bn" in res

def test_cold_storages_endpoint(client):
    response = client.get("/api/cold-storages")
    assert response.status_code == 200
    storages = response.json()
    assert len(storages) >= 5

def test_buyers_endpoint(client):
    response = client.get("/api/buyers")
    assert response.status_code == 200
    buyers = response.json()
    assert len(buyers) >= 5

def test_voice_synthesize_endpoint(client):
    payload = {
        "text": "আসসালামু আলাইকুম। কৃষিভল্ট এ আপনাকে স্বাগতম।",
        "filename": "api_test_greeting.mp3",
        "gender": "MALE"
    }
    response = client.post("/api/voice/synthesize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "/audio/" in data["audio_url"]
    assert data["file_size_bytes"] > 0
