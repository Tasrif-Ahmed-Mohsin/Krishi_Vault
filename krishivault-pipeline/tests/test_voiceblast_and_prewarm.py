"""
Tests for VoiceBlast client improvements, audio pre-warming, and abuse protections.
All tests run with network calls disabled / mocked.
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from src.main import app, reset_call_limits
from src.notify.call_audio import call_text, is_advice
from src.notify.voiceblast import VoiceBlastClient


@pytest.fixture(autouse=True)
def safe_env(monkeypatch):
    """Ensure all external services are safe / dry-run during tests."""
    monkeypatch.setenv("VOICEBLAST_LIVE", "0")
    monkeypatch.setenv("BROADCAST_LIVE", "0")
    monkeypatch.setenv("SMS_LIVE", "0")
    monkeypatch.delenv("CALL_ALLOWED_NUMBERS", raising=False)
    monkeypatch.setenv("CALL_DAILY_CAP", "30")
    reset_call_limits()


def test_call_text_removes_keypad_and_preserves_numbers():
    sample_advice = (
        "আপনার ১০০ বস্তা আলুর জন্য ৩০ বস্তা এখনই বেচুন প্রতি কেজি ২৩ টাকায়। "
        "বাকি ৭০ বস্তা হিমাগারে রাখুন। আরও জানতে ১ চাপুন।"
    )
    result = call_text(sample_advice)

    # Keypad prompt must be stripped
    assert "আরও জানতে ১ চাপুন" not in result

    # Greetings and sign-off
    assert result.startswith("আসসালামু আলাইকুম, কৃষিভল্ট থেকে বলছি। ")
    assert result.endswith(" ধন্যবাদ।")

    # Numbers must be strictly preserved
    assert "১০০" in result
    assert "৩০" in result
    assert "২৩" in result
    assert "৭০" in result


def test_is_advice():
    assert is_advice("আপনার ১০০ বস্তা আলু এখনই বেচুন") is True
    assert is_advice("৫০ বস্তা হিমাগারে রাখুন") is True
    assert is_advice("আসসালামু আলাইকুম, কেমন আছেন?") is False
    assert is_advice("বগুড়ার আবহাওয়া ভালো আছে।") is False


def test_voiceblast_login_fails_when_dashboard_returns_login_page():
    vb = VoiceBlastClient(username="test_user", password="wrong_password", live=True)

    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 200
    mock_post_resp.text = "Redirecting..."

    mock_dash_resp = MagicMock()
    mock_dash_resp.status_code = 200
    mock_dash_resp.url = "http://voice.smsvaults.work/login"
    mock_dash_resp.text = '<html><form action="/login"><input type="password" name="password"></form></html>'

    with patch.object(vb.session, "post", return_value=mock_post_resp), \
         patch.object(vb.session, "get", return_value=mock_dash_resp):
        success = vb.login()
        assert success is False
        assert vb._logged_in is False


def test_voiceblast_login_succeeds_on_valid_dashboard():
    vb = VoiceBlastClient(username="test_user", password="correct_password", live=True)

    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 302
    mock_post_resp.text = ""

    mock_dash_resp = MagicMock()
    mock_dash_resp.status_code = 200
    mock_dash_resp.url = "http://voice.smsvaults.work/customer/dashboard"
    mock_dash_resp.text = '<html><div class="dashboard">Welcome test_user!</div></html>'

    with patch.object(vb.session, "post", return_value=mock_post_resp), \
         patch.object(vb.session, "get", return_value=mock_dash_resp):
        success = vb.login()
        assert success is True
        assert vb._logged_in is True


def test_voiceblast_session_recovery_retries_once():
    vb = VoiceBlastClient(username="test_user", password="secret_password", live=True)
    vb._logged_in = True

    # 1st request: returns login page (expired session)
    expired_resp = MagicMock()
    expired_resp.status_code = 200
    expired_resp.text = '<form action="/login"><input type="password" name="password"></form>'

    # 2nd request (after re-login): returns valid JSON
    success_resp = MagicMock()
    success_resp.status_code = 200
    success_resp.text = '{"status": "ok"}'

    with patch.object(vb.session, "get", side_effect=[expired_resp, success_resp]), \
         patch.object(vb, "login", return_value=True) as mock_login:
        res = vb._request_with_retry("get", "http://voice.smsvaults.work/api/test")
        assert res is success_resp
        assert mock_login.call_count == 1


def test_voiceblast_send_call_non_json_error():
    vb = VoiceBlastClient(username="u", password="p", live=True)
    vb._logged_in = True

    err_resp = MagicMock()
    err_resp.status_code = 502
    err_resp.text = "Bad Gateway: upstream server error"
    err_resp.json.side_effect = ValueError("Invalid JSON")

    with patch.object(vb, "_request_with_retry", return_value=err_resp):
        result = vb.send_call("01712345678", audio_file_id=123)
        assert result["success"] is False
        assert "502" in result["error"]


def test_dial_skips_broadcast_when_broadcast_live_is_zero():
    client = TestClient(app)

    with patch("src.main.get_broadcast_api_client") as mock_bc, \
         patch("src.main.get_voiceblast_client") as mock_vb, \
         patch("src.notify.call_audio.voiceblast_audio_id", return_value=9999):
        
        bc_inst = MagicMock(live=False)
        mock_bc.return_value = bc_inst

        vb_inst = MagicMock(live=False, default_audio_id=1106)
        vb_inst.send_call.return_value = {
            "success": True,
            "status": "dry_run",
            "phone": "01712345678",
            "audio_file_id": 9999,
            "caller_id": "09612010692",
        }
        mock_vb.return_value = vb_inst

        resp = client.post("/api/call/dial", json={
            "phone": "01712345678",
            "text": "আপনার আলুর জন্য পরামর্শ নিন",
        })

        assert resp.status_code == 200
        # Broadcast API was not called
        assert bc_inst.send_broadcast.call_count == 0
        # VoiceBlast send_call was called with the audio ID
        vb_inst.send_call.assert_called_once_with(
            "01712345678", audio_file_id=9999, caller_id=None
        )


def test_abuse_protection_allow_list(monkeypatch):
    monkeypatch.setenv("CALL_ALLOWED_NUMBERS", "01712345678, 01812345679")
    client = TestClient(app)

    # Disallowed number returns 403
    resp_blocked = client.post("/api/call/dial", json={"phone": "01999999999"})
    assert resp_blocked.status_code == 403
    assert "restricted" in resp_blocked.json()["detail"].lower()

    # Allowed number succeeds (dry-run)
    resp_ok = client.post("/api/call/dial", json={"phone": "01712345678"})
    assert resp_ok.status_code == 200


def test_abuse_protection_daily_cap(monkeypatch):
    monkeypatch.setenv("CALL_DAILY_CAP", "2")
    reset_call_limits()
    client = TestClient(app)

    # 1st call
    assert client.post("/api/call/dial", json={"phone": "01712345678"}).status_code == 200
    # 2nd call
    assert client.post("/api/call/dial", json={"phone": "01712345678"}).status_code == 200
    # 3rd call exceeds cap
    resp_cap = client.post("/api/call/dial", json={"phone": "01712345678"})
    assert resp_cap.status_code == 429
    assert "daily" in resp_cap.json()["detail"].lower()


def test_abuse_protection_per_ip_rate_limit():
    reset_call_limits()
    client = TestClient(app)

    # 3 calls from same IP
    for _ in range(3):
        assert client.post(
            "/api/call/dial",
            json={"phone": "01712345678"},
            headers={"X-Forwarded-For": "198.51.100.1"},
        ).status_code == 200

    # 4th call from same IP within window -> 429
    resp_rate = client.post(
        "/api/call/dial",
        json={"phone": "01712345678"},
        headers={"X-Forwarded-For": "198.51.100.1"},
    )
    assert resp_rate.status_code == 429
    assert "limit is 3 calls" in resp_rate.json()["detail"].lower()

    # Different IP is not affected
    resp_other_ip = client.post(
        "/api/call/dial",
        json={"phone": "01712345678"},
        headers={"X-Forwarded-For": "198.51.100.2"},
    )
    assert resp_other_ip.status_code == 200
