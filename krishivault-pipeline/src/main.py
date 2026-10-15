"""
KrishiVault API and web screens
===============================
One FastAPI app for the prototype:
- `/`      the dashboard (static/index.html): forecasts, the store-or-sell engine, buyers, bank loans,
           group storage, export and the profit calculator, plus the partner screens (cold-storage
           receipts, the bank's hold and the split at sale, the government screen);
- `/call`  the call preview (static/call.html): a farmer's phone call played in the browser.

Run:  uvicorn src.main:app --port 8000      (from krishivault-pipeline/)
SMS is a dry run unless SMS_LIVE=1 and the REVE keys are set. Phone calls are preview-only.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src import contacts, demo_data, events as event_log
from src.engine import (alerts, business_model, export_intel, farmer_signals, financing, group_storage,
                        market_access, profit, receipts)
from src.engine.facts import MAUND_KG, SACK_KG, SOURCES, StorageTerms
from src.engine.storage_plan import FarmerLot, StoragePlanner
from src.models import backtest as price_backtest, price_outlook, production_forecast
from src.notify import sms as sms_client, voiceblast as voiceblast_client
from src.notify.voiceblast import get_voiceblast_client
from src.voice import ussd
from src.voice.conversation import Conversation, advice_sms, curing_sms, receipt_sms

from src.voice.gemini import GeminiClient
from src.voice.tts_generator import BengaliVoiceSynthesizer

app = FastAPI(
    title="KrishiVault",
    description="Store or sell, and until when: potato storage, prices, buyers, bank loans, group storage and export.",
    version="2.0.0",
)

BASE = Path(__file__).parent.parent
audio_dir = BASE / "data" / "audio_out"
audio_dir.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(audio_dir)), name="audio")
static_dir = BASE / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

tts_service = BengaliVoiceSynthesizer()
gemini_client = GeminiClient()
planner = StoragePlanner()
conversation = Conversation(gemini=gemini_client, planner=planner)


# ============================================================ pages and status

@app.get("/")
def dashboard():
    return FileResponse(static_dir / "index.html")


@app.get("/call")
def call_preview():
    return FileResponse(static_dir / "call.html")


@app.get("/ussd")
def ussd_preview():
    return FileResponse(static_dir / "ussd.html")


@app.get("/api/status")
def status():
    """What is switched on. Never returns keys."""
    sms_cfg = sms_client.sms_config()
    return {
        "status": "operational",
        "gemini": {"on": gemini_client.available, "model": gemini_client.model_used},
        "google_voice": tts_service.status(),
        "sms": {"configured": sms_cfg["configured"], "live": sms_cfg["live"]},
        "calls": "preview only (no phone line in the prototype)",
        "data": {"prices": price_outlook.model_card()["trained_on"]["prices"],
                 "production": price_outlook.model_card()["trained_on"]["production"]},
    }


# ============================================================ forecasts and market data

@app.get("/api/forecast/production")
def forecast_production(district: Optional[str] = None, season_start: Optional[int] = None,
                        area_ha: Optional[float] = None, weather_adjust_pct: float = 0.0,
                        as_known_at_harvest: bool = False):
    """as_known_at_harvest: for a past season, the crop as it could be estimated at its harvest (fair replays)."""
    try:
        return production_forecast.production_forecast(district, season_start, area_ha, weather_adjust_pct,
                                                       as_known_at_harvest)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/forecast/price")
def forecast_price(price_today: float = 16.0, month: int = 3, year: int = 2027, horizon: Optional[int] = None,
                   gap_override_pct: Optional[float] = None, area_ha: Optional[float] = None):
    if not 1 <= month <= 12 or price_today <= 0:
        raise HTTPException(status_code=400, detail="month 1-12 and a positive price_today")
    h = horizon if horizon is not None else (0 if month == 1 else min(9, 12 - month))
    return price_outlook.outlook(price_today, month, year, max(0, min(h, 11)), area_ha=area_ha,
                                 gap_override_pct=gap_override_pct)


@app.get("/api/forecast/model")
def forecast_model():
    return {"card": price_outlook.model_card(), "national_prices": price_outlook.national_history(),
            "season_curve": price_outlook.SEASON_CURVE}


@app.get("/api/forecast/backtest")
def forecast_backtest(only_past: bool = False):
    """The price outlook replayed on past seasons it did not see, against the usual shape and no change."""
    return price_backtest.backtest(only_past)


@app.get("/api/market/regions")
def market_regions():
    return {"price_index": price_outlook.regional_index(), "supply": production_forecast.district_supply(),
            "national_latest": price_outlook.national_latest(),
            "note": "Retail prices in town markets (WFP), not farm-gate prices. Index 1.00 = the national level."}


@app.get("/api/districts")
def districts():
    return production_forecast.district_names()


# ============================================================ the storage engine

class TermsIn(BaseModel):
    sack_kg: Optional[float] = Field(None, gt=10, le=150)
    rent_per_sack: Optional[float] = Field(None, ge=0, le=2000)
    sack_cost: Optional[float] = Field(None, ge=0)
    carry_in_per_sack: Optional[float] = Field(None, ge=0)
    load_unload_per_sack: Optional[float] = Field(None, ge=0)
    sell_from_store_per_sack: Optional[float] = Field(None, ge=0)
    sell_now_per_sack: Optional[float] = Field(None, ge=0)
    monthly_weight_loss: Optional[float] = Field(None, ge=0, le=0.2)
    exit_sorting_loss: Optional[float] = Field(None, ge=0, le=0.5)
    cs_advance_per_sack: Optional[float] = Field(None, ge=0)
    cs_advance_rate_year: Optional[float] = Field(None, ge=0, le=1)
    bank_rate_year: Optional[float] = Field(None, ge=0, le=1)

    def build(self) -> StorageTerms:
        return StorageTerms(**{k: v for k, v in self.model_dump().items() if v is not None})


class PlanIn(BaseModel):
    quantity: float = Field(..., gt=0, le=10_000_000)
    unit: Literal["kg", "maund", "sack"] = "maund"
    price_today: float = Field(..., gt=0, le=500)
    month: int = Field(3, ge=1, le=12)
    year: int = Field(2027, ge=2013, le=2035)
    stored: Literal["no", "cold"] = "no"
    stored_since_month: Optional[int] = Field(None, ge=1, le=12)
    cash_needed_tk: float = Field(0, ge=0, le=100_000_000)
    cash_days: int = Field(0, ge=0, le=365)
    loan_source: Literal["cheapest", "cold_storage", "bank", "none"] = "cheapest"
    production_cost_per_kg: Optional[float] = Field(None, gt=0, le=500)
    gap_override_pct: Optional[float] = Field(None, ge=-40, le=40)
    area_ha: Optional[float] = Field(None, gt=0)
    terms: Optional[TermsIn] = None
    district: str = Field("Bogura", max_length=40)
    count_me: bool = False             # the farmer agreed to be counted, without name or number

    def lot(self) -> FarmerLot:
        terms = self.terms.build() if self.terms else StorageTerms()
        factor = {"kg": 1.0, "maund": MAUND_KG, "sack": terms.sack_kg}[self.unit]
        return FarmerLot(
            quantity_kg=self.quantity * factor, price_today=self.price_today,
            decision_month=self.month, decision_year=self.year, stored=self.stored,
            stored_since_month=self.stored_since_month or (3 if self.stored == "cold" else None),
            cash_needed_tk=self.cash_needed_tk, cash_days=self.cash_days, loan_source=self.loan_source,
            production_cost_per_kg=self.production_cost_per_kg, gap_override_pct=self.gap_override_pct,
            area_ha=self.area_ha, terms=terms,
        )


@app.post("/api/storage/plan")
def storage_plan(req: PlanIn):
    lot = req.lot()
    plan = planner.plan(lot)
    if req.count_me:     # only with the farmer's agreement; nothing with a name or number is kept
        farmer_signals.record(req.district, lot.decision_month, lot.decision_year, lot.sacks, lot.cash_needed_tk,
                              lot.cash_days, lot.stored, plan["recommendation"]["key"], "dashboard")
        plan["counted"] = True
    return plan


class BookIn(BaseModel):
    sacks: int = Field(..., gt=0, le=100_000)
    cold_storage_id: str = "cs-a"
    farmer_name: str = Field(..., min_length=1, max_length=80)
    phone: Optional[str] = Field(None, max_length=20)
    advice: Optional[str] = Field(None, max_length=120)


@app.post("/api/storage/book")
def storage_book(req: BookIn):
    """A cold-storage space request; its number is the receipt a bank loan can use later."""
    try:
        cs = demo_data.cold_storage(req.cold_storage_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="No such cold storage")
    free = farmer_signals.free_sacks(cs)
    no_space = req.sacks > free        # counted for government: farmers who wanted storage but found none
    ev = event_log.record("cold_storage_booking",
                          f"{req.farmer_name}: {req.sacks} বস্তা আলু রাখার অনুরোধ" + (" (জায়গা নেই)" if no_space else ""),
                          {"sacks": req.sacks, "cold_storage": cs["name"], "rent_per_sack": cs["rent_per_sack"],
                           "farmer": req.farmer_name, "advice": req.advice, "no_space": no_space,
                           "free_sacks": max(free, 0)},
                          district=cs["district"], phone=req.phone)
    if no_space:
        others = [c for c in demo_data.partners()["cold_storages"]       # verified partners with space
                  if c["id"] != cs["id"] and not receipts.partner_check(c) and farmer_signals.free_sacks(c) >= req.sacks]
        ev["no_space"] = True
        ev["try_instead"] = [{"id": c["id"], "name": c["name"], "district": c["district"]} for c in others]
    return ev


@app.get("/api/storage/terms")
def storage_terms():
    return {"defaults": StorageTerms().to_dict(), "season_loss": round(StorageTerms().season_loss(), 4),
            "sources": SOURCES}


class ReceiptIn(BaseModel):
    cold_storage_id: str = "cs-a"
    farmer_name: str = Field(..., min_length=1, max_length=80)
    phone: Optional[str] = Field(None, max_length=200)
    sacks: int = Field(..., gt=0, le=100_000)
    kg_weighed: Optional[float] = Field(None, gt=0, le=10_000_000)
    grade: Literal["table", "seed"] = "table"
    advance_per_sack: float = Field(0, ge=0, le=2000)
    month: int = Field(3, ge=1, le=12)            # when the sacks went in (the season on the dashboard)
    year: int = Field(2027, ge=2013, le=2035)


@app.post("/api/receipts")
def receipt_issue(req: ReceiptIn):
    """The cold storage weighs and grades the sacks and issues a digital receipt; the farmer gets it by SMS."""
    try:
        r = receipts.issue(req.cold_storage_id, req.farmer_name, req.phone, req.sacks, req.kg_weighed,
                           req.grade, req.advance_per_sack, req.month, req.year)
    except KeyError:
        raise HTTPException(status_code=404, detail="No such cold storage")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    sent = sms_client.send_sms(req.phone, r["sms"]) if req.phone else None
    return {"receipt": r, "sms_result": sent}


@app.get("/api/receipts")
def receipt_list(cold_storage_id: Optional[str] = None):
    return list(reversed(receipts.all_receipts(cold_storage_id)))


# ============================================================ market access

class OfferIn(BaseModel):
    name: Optional[str] = Field(None, max_length=80)
    price_per_kg: float = Field(..., gt=0, le=500)
    farmer_transport_per_kg: float = Field(0, ge=0, le=50)
    payment_days: int = Field(0, ge=0, le=180)


class OffersIn(BaseModel):
    quantity_kg: float = Field(..., gt=0, le=10_000_000)
    price_today: float = Field(..., gt=0, le=500)
    extra_offers: list[OfferIn] = Field(default_factory=list, max_length=10)


@app.post("/api/market/offers")
def market_offers(req: OffersIn):
    return market_access.compare_offers(req.quantity_kg, req.price_today, [o.model_dump() for o in req.extra_offers])


class LotIn(BaseModel):
    kg: float = Field(..., gt=0, le=10_000_000)
    price_today: float = Field(..., gt=0, le=500)
    district: str = Field("Bogura", max_length=40)
    farmer_name: str = Field(..., min_length=1, max_length=80)
    phone: Optional[str] = Field(None, max_length=20)


@app.post("/api/market/lot")
def market_lot(req: LotIn):
    """Send a lot to the buyers' screen; buyers answer with offers."""
    return event_log.record("buyer_lot", f"{req.farmer_name}: {round(req.kg):,} কেজি আলু বিক্রির লট",
                            {"kg": round(req.kg), "sacks": round(req.kg / SACK_KG, 1), "price_today": req.price_today,
                             "farmer": req.farmer_name}, district=req.district, phone=req.phone)


@app.get("/api/partners")
def partners():
    """The demo partners (made up; never real businesses)."""
    p = demo_data.partners()
    return {k: p[k] for k in ("_note", "cold_storages", "buyers", "banks", "transport")}


# ============================================================ financing

class LoanIn(BaseModel):
    sacks: int = Field(..., gt=0, le=100_000)
    price_today: float = Field(..., gt=0, le=500)
    month: int = Field(3, ge=1, le=12)
    year: int = Field(2027, ge=2013, le=2035)
    months: int = Field(6, ge=1, le=9)
    amount: Optional[float] = Field(None, gt=0)
    bank_id: str = "bank-a"


@app.post("/api/finance/estimate")
def finance_estimate(req: LoanIn):
    return financing.compare_banks(req.sacks, req.price_today, req.month, req.year, req.months, req.amount)


class ApplyIn(LoanIn):
    farmer_name: str = Field(..., min_length=1, max_length=80)
    phone: Optional[str] = Field(None, max_length=20)
    district: str = "Bogura"
    cold_storage_id: str = "cs-a"
    receipt_no: str = Field(..., min_length=1, max_length=40)


@app.post("/api/finance/apply")
def finance_apply(req: ApplyIn):
    try:
        return financing.apply(req.farmer_name, req.phone, req.district, req.cold_storage_id, req.receipt_no,
                               req.sacks, req.price_today, req.month, req.year, req.months, req.bank_id, req.amount)
    except (KeyError, StopIteration):
        raise HTTPException(status_code=404, detail="Unknown bank or cold storage")


@app.get("/api/finance/applications")
def finance_applications():
    return financing.applications()


class ReceiptCheckIn(BaseModel):
    sacks_found: int = Field(..., ge=0, le=100_000)


@app.post("/api/finance/applications/{app_id}/receipt")
def finance_confirm_receipt(app_id: str, req: ReceiptCheckIn):
    out = financing.confirm_receipt(app_id, req.sacks_found)
    if not out:
        raise HTTPException(status_code=404, detail="No such application")
    return out


class DecisionIn(BaseModel):
    approve: bool


class SaleIn(BaseModel):
    price_per_kg: float = Field(..., gt=0, le=500)
    kg_sold: Optional[float] = Field(None, gt=0, le=10_000_000)


@app.post("/api/finance/applications/{app_id}/decision")
def finance_decision(app_id: str, req: DecisionIn):
    try:
        out = financing.bank_decision(app_id, req.approve)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not out:
        raise HTTPException(status_code=404, detail="No such application")
    phone = contacts.get(f"application:{app_id}")
    text = financing.decision_sms(out)
    return {**out, "sms_text": text, "sms_result": sms_client.send_sms(phone, text) if phone else None}


@app.post("/api/finance/applications/{app_id}/sale")
def finance_sale(app_id: str, req: SaleIn):
    """The stored potatoes are sold (demo): the sale pays the cold storage, the bank, then the farmer."""
    try:
        out = financing.settle_sale(app_id, req.price_per_kg, req.kg_sold)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not out:
        raise HTTPException(status_code=404, detail="No such application")
    return out


# ============================================================ price-window alerts (step 4 of the loop)

class AlertsIn(BaseModel):
    month: int = Field(10, ge=1, le=12)
    year: int = Field(2026, ge=2013, le=2035)
    price_today: float = Field(..., gt=0, le=500)
    send: bool = False


@app.post("/api/alerts/price-window")
def price_window_alerts(req: AlertsIn):
    """For every receipt in store: sell now (how many, to which buyer) or hold (until when); SMS on request."""
    found = alerts.price_window(req.month, req.year, req.price_today)
    return alerts.send(found, sms_client.send_sms) if req.send else found


# ============================================================ group storage

@app.get("/api/groups")
def groups(district: Optional[str] = None):
    return group_storage.pools(district)


class GroupCompareIn(BaseModel):
    pool_id: str
    sacks: int = Field(..., gt=0, le=100_000)


@app.get("/api/groups/{pool_id}/sale")
def groups_sale(pool_id: str, price_today: float = 16.0):
    """The plan's "group sell": the group's sacks as one lot, shared out to the buyers that pay most."""
    if not 0 < price_today <= 500:
        raise HTTPException(status_code=400, detail="price_today must be between 0 and 500")
    try:
        return group_storage.group_sale(pool_id, price_today)
    except KeyError:
        raise HTTPException(status_code=404, detail="No such group")


@app.post("/api/groups/{pool_id}/lot")
def groups_lot(pool_id: str, price_today: float = 16.0):
    """Send the group's lot to the buyers' screen."""
    if not 0 < price_today <= 500:
        raise HTTPException(status_code=400, detail="price_today must be between 0 and 500")
    try:
        return group_storage.send_group_lot(pool_id, price_today)
    except KeyError:
        raise HTTPException(status_code=404, detail="No such group")


@app.post("/api/groups/compare")
def groups_compare(req: GroupCompareIn):
    try:
        return group_storage.compare(req.pool_id, req.sacks)
    except KeyError:
        raise HTTPException(status_code=404, detail="No such group")


class GroupJoinIn(GroupCompareIn):
    name: str = Field(..., min_length=1, max_length=80)
    phone: Optional[str] = Field(None, max_length=20)


@app.post("/api/groups/join")
def groups_join(req: GroupJoinIn):
    try:
        return group_storage.join(req.pool_id, req.name, req.sacks, req.phone)
    except KeyError:
        raise HTTPException(status_code=404, detail="No such group")


class AgreeIn(BaseModel):
    min_sacks: int = Field(..., gt=0)


@app.post("/api/groups/{pool_id}/agree")
def groups_agree(pool_id: str, req: AgreeIn):
    try:
        return group_storage.agree_offer(pool_id, req.min_sacks)
    except KeyError:
        raise HTTPException(status_code=404, detail="No such group")


# ============================================================ export

@app.get("/api/export/sourcing")
def export_sourcing(top: int = 12):
    national = price_outlook.national_latest()["median"]
    return {"districts": export_intel.sourcing(min(max(top, 1), 64)),
            "domestic_gaps": export_intel.domestic_gaps(national)}


class ExportIn(BaseModel):
    farmgate_price: float = Field(..., gt=0, le=500)
    source_district: str = "Bogura"
    quantity_t: float = Field(26, gt=0, le=100_000)


@app.post("/api/export/evaluate")
def export_evaluate(req: ExportIn):
    return export_intel.evaluate_all(req.farmgate_price, req.source_district, req.quantity_t)


# ============================================================ profit calculator

class SaleIn(BaseModel):
    month: Optional[str] = Field(None, max_length=20)
    kg: float = Field(..., ge=0)
    price_per_kg: float = Field(..., ge=0, le=500)


class ProfitIn(BaseModel):
    land_amount: float = Field(1, gt=0, le=10_000)
    land_unit: Literal["bigha", "acre", "decimal", "hectare"] = "bigha"
    harvest_kg: float = Field(..., gt=0)
    growing: dict[str, float] = Field(default_factory=dict)
    after: dict[str, float] = Field(default_factory=dict)
    sales: list[SaleIn] = Field(default_factory=list, max_length=50)
    unsold_price_per_kg: Optional[float] = Field(None, ge=0, le=500)
    harvest_price_per_kg: Optional[float] = Field(None, gt=0, le=500)


@app.get("/api/profit/example")
def profit_example():
    return {"inputs": profit.EXAMPLE_BIGHA, "result": profit.example(),
            "lines": {"growing": profit.GROWING_LINES, "after": profit.AFTER_LINES, "labels": profit.LABELS}}


@app.post("/api/profit/calculate")
def profit_calculate(req: ProfitIn):
    return profit.calculate(req.harvest_kg, req.growing, req.after, [s.model_dump() for s in req.sales],
                            req.land_amount, req.land_unit, req.unsold_price_per_kg, req.harvest_price_per_kg)


# ============================================================ SMS (dry run unless SMS_LIVE=1)

class AdviceSmsIn(PlanIn):
    phone: str = Field(..., max_length=200)


@app.post("/api/sms/advice")
def sms_advice(req: AdviceSmsIn):
    """Send the store-or-sell advice by SMS. The text is built here from the engine, never sent from the page."""
    plan = planner.plan(req.lot())
    text = advice_sms(plan)
    return {"text": text, **sms_client.send_sms(req.phone, text)}


class PhoneIn(BaseModel):
    phone: str = Field(..., max_length=200)


@app.post("/api/sms/curing")
def sms_curing(req: PhoneIn):
    """The reminder before the harvest: cure the potatoes in shade before cold storage."""
    text = curing_sms()
    return {"text": text, **sms_client.send_sms(req.phone, text)}


# ============================================================ the business plan

@app.get("/api/business/plan")
def business_plan():
    """The plan's income streams, start-up money and 3-year projection, worked out from its assumptions."""
    return business_model.business_plan()


# ============================================================ call preview

class CallTurnRequest(BaseModel):
    state: Optional[dict] = None       # what the last turn returned; None starts a call
    kind: str = "start"                # "start", "speech" or "keypad"
    text: Optional[str] = Field(None, max_length=2000)
    digits: Optional[str] = Field(None, max_length=12)
    district: Optional[str] = "Bogura"
    month: Optional[int] = Field(None, ge=1, le=12)
    year: Optional[int] = Field(None, ge=2013, le=2035)
    phone: Optional[str] = Field(None, max_length=200)


class CallSmsRequest(BaseModel):
    state: dict
    phone: str = Field(..., max_length=200)


class SpeakRequest(BaseModel):
    text: str = Field(..., max_length=4000)
    gender: Optional[str] = "MALE"


class VoiceDialRequest(BaseModel):
    phone: str = Field(..., max_length=20)
    audio_file_id: Optional[int] = None
    caller_id: Optional[str] = None
    text: Optional[str] = None


@app.get("/api/call/status")
def call_status():
    sms_cfg = sms_client.sms_config()
    vb = get_voiceblast_client()
    return {
        "gemini": {"on": gemini_client.available, "model": gemini_client.model_used},
        "google_voice": tts_service.status(),
        "sms": {"configured": sms_cfg["configured"], "live": sms_cfg["live"]},
        "voiceblast": {
            "live": vb.live,
            "caller_id": vb.caller_id,
            "balance": vb.get_balance() if vb.live else "dry_run",
            "default_audio_id": vb.default_audio_id,
        },
        "calls": "live" if vb.live else "preview",
    }


@app.post("/api/call/dial")
def call_dial(req: VoiceDialRequest):
    """Trigger a real outbound voice phone call to a Bangladeshi mobile via VoiceBlast."""
    vb = get_voiceblast_client()
    audio_id = req.audio_file_id

    # If dynamic text is provided and TTS is ready, synthesize & upload customized G.711 speech!
    if not audio_id and req.text and tts_service.ready:
        try:
            from google.cloud import texttospeech
            s_input = texttospeech.SynthesisInput(text=req.text[:4800])
            voice = texttospeech.VoiceSelectionParams(
                language_code="bn-BD", ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
            )
            audio_cfg = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16, sample_rate_hertz=8000
            )
            speech_resp = tts_service.client.synthesize_speech(
                input=s_input, voice=voice, audio_config=audio_cfg, timeout=15
            )
            g711_wav = voiceblast_client.make_g711_wav(speech_resp.audio_content[44:])
            clean_phone = voiceblast_client.bd_mobile(req.phone) or "anon"
            tmp_dir = BASE / "data" / "audio_out"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            tmp_file = tmp_dir / f"advice_{clean_phone[-6:]}.wav"
            with open(tmp_file, "wb") as f:
                f.write(g711_wav)
            uploaded_id = vb.upload_audio(tmp_file, filename=tmp_file.name)
            if uploaded_id:
                audio_id = uploaded_id
        except Exception as exc:
            from loguru import logger
            logger.warning(f"Could not synthesize dynamic voice advisory: {exc}")

    res = vb.send_call(req.phone, audio_file_id=audio_id, caller_id=req.caller_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Call dispatch failed"))
    return res



@app.get("/api/call/history")
def call_history():
    """Fetch recent outbound phone call logs from VoiceBlast."""
    vb = get_voiceblast_client()
    return {"history": vb.get_history(limit=10), "balance": vb.get_balance()}


@app.post("/api/call/turn")
def call_turn(req: CallTurnRequest):
    if req.kind not in ("start", "speech", "keypad"):
        raise HTTPException(status_code=400, detail="kind must be start, speech or keypad")
    if req.kind != "start" and not (req.state and req.state.get("step")):
        raise HTTPException(status_code=400, detail="Start a call first (kind=start)")
    return conversation.turn(req.state, {
        "kind": req.kind, "text": req.text, "digits": req.digits, "district": req.district,
        "month": req.month, "year": req.year, "phone": req.phone,
    })


@app.post("/api/voice/speak")
def speak(req: SpeakRequest):
    """The Google Bangla voice for one reply (cached). 503 without a key: the screen uses the browser's voice."""
    if not tts_service.ready:
        raise HTTPException(status_code=503, detail="Google voice not set up (GOOGLE_APPLICATION_CREDENTIALS)")
    path = tts_service.speak(req.text, voice_gender=req.gender or "MALE")
    if not path:
        raise HTTPException(status_code=502, detail=f"Google voice failed: {tts_service.last_error}")
    return {"audio_url": f"/audio/{path.name}", "language": tts_service.language_used}


@app.post("/api/call/sms")
def call_sms(req: CallSmsRequest):
    """The call's SMS receipt. The text comes from the call state the engine filled in."""
    text = receipt_sms(req.state)
    if not text:
        raise HTTPException(status_code=400, detail="There is no answer yet in this call to send.")
    return {"text": text, **sms_client.send_sms(req.phone, text)}



# ============================================================ USSD (the plan's Grameenphone USSD menu)

class UssdIn(BaseModel):
    session_id: str = Field("preview", max_length=64)
    phone_number: Optional[str] = Field(None, max_length=20)
    text: str = Field("", max_length=200)      # everything entered in the session, joined by '*'
    month: int = Field(3, ge=1, le=12)
    year: int = Field(2027, ge=2013, le=2035)
    district: str = Field("Bogura", max_length=40)


@app.post("/api/ussd")
def ussd_turn(req: UssdIn):
    """One USSD turn, in the gateway's format: 'CON <screen>' keeps the session open, 'END <screen>' closes it."""
    return ussd.turn(req.text, req.phone_number, req.month, req.year, req.district, sms_client.send_sms)


# ============================================================ partner screens

@app.get("/api/government")
def government(month: int = 3, year: int = 2027, gap_override_pct: Optional[float] = None):
    """The government screen: glut warning (real data), cold-storage fill (demo), farmer figures (with consent)."""
    if not (1 <= month <= 12 and 2013 <= year <= 2035):
        raise HTTPException(status_code=400, detail="month 1-12, year 2013-2035")
    if gap_override_pct is not None and not -40 <= gap_override_pct <= 40:
        raise HTTPException(status_code=400, detail="gap_override_pct must be between -40 and 40")
    return farmer_signals.government_view(month, year, gap_override_pct)


@app.get("/api/events")
def list_events(partner: Optional[str] = None, limit: int = 50):
    """Requests from farmers (calls and dashboard), newest first; phone numbers masked."""
    return event_log.recent(limit=min(max(limit, 1), 200), partner=partner)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=False)
