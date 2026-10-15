"""
Tests for the SMS (REVE) and call (Awaj) clients: dry run by default, live only with the switch and keys.
No network: live sends are never made here.
"""

import pytest

from src.notify import awaj, sms


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for key in ("SMS_API_KEY", "SMS_SECRET_KEY", "SMS_SENDER_ID", "SMS_LIVE", "SMS_BASE_URL",
                "AWAJ_API_TOKEN", "AWAJ_SENDER", "AWAJ_SENDER_NUMBER", "AWAJ_LIVE", "AWAJ_BASE_URL", "AWAJ_VOICE"):
        monkeypatch.delenv(key, raising=False)


def test_bd_mobile_forms():
    assert awaj.bd_mobile("+8801712345678") == "01712345678"
    assert awaj.bd_mobile("01712-345678") == "01712345678"
    assert awaj.bd_mobile("8801712345678") == "01712345678"
    assert awaj.bd_mobile("01212345678") is None   # not a mobile prefix
    assert awaj.bd_mobile("12345") is None


def test_sms_parts_bangla_and_plain():
    assert sms.sms_parts("ক" * 70) == 1
    assert sms.sms_parts("ক" * 71) == 2
    assert sms.sms_parts("a" * 160) == 1
    assert sms.sms_parts("a" * 161) == 2


def test_sms_dry_run_without_keys_masks_and_formats_number():
    result = sms.send_sms("01712345678", "কৃষিভল্ট পরীক্ষা")
    assert result["dry_run"] is True
    assert result["request"]["toUser"] == "8801712345678"
    assert "apikey=***" in result["endpoint"]


def test_sms_live_switch_needs_keys(monkeypatch):
    monkeypatch.setenv("SMS_LIVE", "1")
    assert sms.sms_config()["live"] is False          # switch on, keys missing: still a dry run
    for k, v in (("SMS_API_KEY", "a"), ("SMS_SECRET_KEY", "b"), ("SMS_SENDER_ID", "c")):
        monkeypatch.setenv(k, v)
    assert sms.sms_config()["live"] is True
    monkeypatch.setenv("SMS_LIVE", "0")
    assert sms.sms_config()["live"] is False
    assert sms.send_sms("01712345678", "x")["dry_run"] is True


def test_sms_bad_number_is_not_sent():
    result = sms.send_sms("12345", "x")
    assert "error" in result


def test_sms_multiple_numbers_parsed_and_formatted():
    result = sms.send_sms("01712345678, 01812345678", "পরীক্ষা")
    assert result["dry_run"] is True
    assert result["request"]["toUser"] == "8801712345678,8801812345678"


def test_sms_too_many_numbers_is_not_sent():
    numbers = ", ".join(f"0171100000{i}" for i in range(sms.MAX_RECIPIENTS + 1))
    result = sms.send_sms(numbers, "পরীক্ষা")
    assert "error" in result and "endpoint" not in result


def test_sms_keys_never_reach_the_log(monkeypatch):
    # A failed request's error text holds the whole URL, keys included; it must not be logged or returned
    from loguru import logger
    import requests

    monkeypatch.setenv("SMS_API_KEY", "KEY-SHOULD-NOT-LEAK")
    monkeypatch.setenv("SMS_SECRET_KEY", "SECRET-SHOULD-NOT-LEAK")
    monkeypatch.setenv("SMS_SENDER_ID", "8809600000000")
    monkeypatch.setenv("SMS_LIVE", "1")

    def unreachable(url, params=None, **kw):
        raise requests.ConnectionError(f"Max retries exceeded with url: {url}?apikey={params['apikey']}&secretkey={params['secretkey']}")

    monkeypatch.setattr(sms.requests, "get", unreachable)
    lines = []
    sink = logger.add(lines.append, level="DEBUG")
    try:
        result = sms.send_sms("01711998877", "পরীক্ষা")
    finally:
        logger.remove(sink)
    text = "".join(lines) + str(result)
    assert "could not reach" in result["error"]
    assert "LEAK" not in text
    assert "01711998877" not in text and "01711-XXX877" in text


def test_partner_screens_mask_every_number():
    from src.events import mask_phone
    assert mask_phone("01711998877") == "01711-XXX877"
    assert mask_phone("01711000000, 01811000123") == "01711-XXX000, 01811-XXX123"
    assert mask_phone("") is None


def test_awaj_sender_under_either_name(monkeypatch):
    monkeypatch.setenv("AWAJ_SENDER_NUMBER", "09612345678")
    assert awaj.awaj_config()["sender"] == "09612345678"


def test_awaj_tts_call_dry_run_request():
    result = awaj.send_tts_call(["+8801712345678", "01712345678", "bad"], ["আসসালামু আলাইকুম"])
    assert result["dry_run"] is True
    body = result["request"]
    assert body["phone_numbers"] == ["01712345678"]   # cleaned and de-duplicated
    assert body["language_code"] == "bn-BD"
    assert 16 <= len(body["request_id"]) <= 64
    assert body["sender"] == "<AWAJ_SENDER>"


def test_awaj_live_needs_token_sender_and_switch(monkeypatch):
    monkeypatch.setenv("AWAJ_LIVE", "1")
    monkeypatch.setenv("AWAJ_API_TOKEN", "t")
    assert awaj.awaj_config()["live"] is False        # no sender
    monkeypatch.setenv("AWAJ_SENDER", "09612345678")
    assert awaj.awaj_config()["live"] is True


def test_awaj_keypad_survey_officer_transfer():
    result = awaj.send_keypad_survey(["01712345678"], "menu_v1", ["1", "2", "3"], officer_key="9",
                                     officer_number="01812345678")
    options = result["request"]["dtmf_options"]
    assert options[-1] == {"key": "9", "option_type": "transfer", "transfer_numbers": ["01812345678"]}
