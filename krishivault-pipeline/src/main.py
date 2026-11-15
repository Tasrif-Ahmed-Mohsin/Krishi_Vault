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

import os
import sys
import time
import threading
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src import contacts, demo_data, events as event_log
from src.engine import (alerts, business_model, dadon, demo_loop, export_intel, farmer_signals, financing,
                        group_storage, hold_plan, market_access, profit, receipts)
from src.engine.facts import MAUND_KG, SACK_KG, SOURCES, StorageTerms
from src.engine.storage_plan import FarmerLot, StoragePlanner
from src.models import backtest as price_backtest, price_outlook, production_forecast
from src.notify import sms as sms_client, voiceblast as voiceblast_client, call_audio
from src.notify.voiceblast import get_voiceblast_client, get_broadcast_api_client
from src.voice import ussd
from src.voice.conversation import Conversation, advice_sms, call_script, curing_sms, receipt_sms

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

# ------------------------------------------------------------------ Abuse protection
_call_limit_lock = threading.Lock()
_ip_call_timestamps: dict[str, list[float]] = defaultdict(list)
_daily_call_date: str = ""
_daily_call_count: int = 0


def reset_call_limits() -> None:
    """Reset rate limiter and daily cap state (used in tests)."""
    global _daily_call_date, _daily_call_count
    with _call_limit_lock:
        _ip_call_timestamps.clear()
        _daily_call_date = ""
        _daily_call_count = 0


def client_ip(request: Request) -> str:
    """
    The caller's address for the rate limit. Behind nginx on the same machine (the Azure set-up),
    nginx appends the real address as the LAST X-Forwarded-For entry; anything before it was sent
    by the browser and can be made up, so it is never used. Other peers: their own address.
    """
    peer = request.client.host if request.client else "127.0.0.1"
    trusted = {p.strip() for p in os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1").split(",") if p.strip()}
    forwarded = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    if peer in trusted and forwarded:
        return forwarded[-1]
    return peer


def check_and_record_dial(client_ip: str, clean_phone: str) -> None:
    """Enforce allow-list, daily call cap, and per-IP rate limits."""
    global _daily_call_date, _daily_call_count
    now = time.time()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 1. Allow-list check
    allowed_env = os.getenv("CALL_ALLOWED_NUMBERS", "").strip()
    if allowed_env:
        raw_allowed = [p.strip() for p in allowed_env.split(",") if p.strip()]
        allowed_set = set()
        for p in raw_allowed:
            clean_p = voiceblast_client.bd_mobile(p)
            if clean_p:
                allowed_set.add(clean_p)
            else:
                allowed_set.add(p)
        if clean_phone not in allowed_set:
            raise HTTPException(
                status_code=403,
                detail="Outbound calls are currently restricted to authorized test numbers.",
            )

    with _call_limit_lock:
        # 2. Daily cap check
        daily_cap = int(os.getenv("CALL_DAILY_CAP", "30"))
        if _daily_call_date != today:
            _daily_call_date = today
            _daily_call_count = 0

        if _daily_call_count >= daily_cap:
            raise HTTPException(
                status_code=429,
                detail=f"Daily outbound call limit ({daily_cap}) reached. Please try again tomorrow.",
            )

        # 3. Per-IP rate limit (3 calls per 10 minutes = 600s)
        window = 600.0
        max_per_ip = 3
        timestamps = [ts for ts in _ip_call_timestamps[client_ip] if now - ts < window]
        if len(timestamps) >= max_per_ip:
            raise HTTPException(
                status_code=429,
                detail="Too many calls requested from your IP. Limit is 3 calls per 10 minutes.",
            )

        # Record this dial
        timestamps.append(now)
        _ip_call_timestamps[client_ip] = timestamps
        _daily_call_count += 1


# ============================================================ pages and status

# The browser checks for a newer page on every visit, so a fresh deploy is seen at once
PAGE_HEADERS = {"Cache-Control": "no-cache"}


@app.get("/")
def dashboard():
    return FileResponse(static_dir / "index.html", headers=PAGE_HEADERS)


@app.get("/call")
def call_preview():
    return FileResponse(static_dir / "call.html", headers=PAGE_HEADERS)


@app.get("/ussd")
def ussd_preview():
    return FileResponse(static_dir / "ussd.html", headers=PAGE_HEADERS)


@app.get("/api/status")
def status():
    """What is switched on. Never returns keys."""
    sms_cfg = sms_client.sms_config()
    calls_live = get_voiceblast_client().live or get_broadcast_api_client().live
    return {
        "status": "operational",
        "gemini": {"on": gemini_client.available, "model": gemini_client.model_used},
        "google_voice": tts_service.status(),
        "sms": {"configured": sms_cfg["configured"], "live": sms_cfg["live"]},
        "calls": ("live: outbound calls that read the engine's answer (no inbound line or USSD code yet)"
                  if calls_live else "preview only (no phone line switched on)"),
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
    plan["hold_plan"] = hold_plan.build(plan)     # "do not sell before", and the price that makes it pay
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


class DadonIn(BaseModel):
    advance_tk: float = Field(..., gt=0, le=10_000_000)
    months: float = Field(..., gt=0, le=12)
    promised_maunds: float = Field(..., gt=0, le=100_000)
    trader_price: float = Field(..., gt=0, le=500)
    market_price: float = Field(..., gt=0, le=500)
    extra_tk: float = Field(0, ge=0, le=10_000_000)
    bank_id: str = "bank-a"


@app.post("/api/finance/dadon")
def finance_dadon(req: DadonIn):
    """What a trader's advance repaid in potatoes below the market price really costs, beside a bank loan."""
    try:
        return dadon.true_cost(req.advance_tk, req.months, req.promised_maunds * MAUND_KG, req.trader_price,
                               req.market_price, req.extra_tk, req.bank_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown bank")


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
    channel: Literal["sms", "voice"] = "sms"     # voice: an outbound call, for farmers who cannot read an SMS


@app.post("/api/alerts/price-window")
def price_window_alerts(req: AlertsIn, request: Request):
    """For every receipt in store: sell now (how many, to which buyer) or hold (until when); SMS or a call on request."""
    found = alerts.price_window(req.month, req.year, req.price_today)
    if not req.send:
        return found
    if req.channel == "voice":
        return alerts.call(found, lambda phone, text: place_call(phone, text, request))
    return alerts.send(found, sms_client.send_sms)


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

class ProfitSaleIn(BaseModel):
    month: Optional[str] = Field(None, max_length=20)
    kg: float = Field(..., ge=0)
    price_per_kg: float = Field(..., ge=0, le=500)


class ProfitIn(BaseModel):
    land_amount: float = Field(1, gt=0, le=10_000)
    land_unit: Literal["bigha", "acre", "decimal", "hectare"] = "bigha"
    harvest_kg: float = Field(..., gt=0)
    growing: dict[str, float] = Field(default_factory=dict)
    after: dict[str, float] = Field(default_factory=dict)
    sales: list[ProfitSaleIn] = Field(default_factory=list, max_length=50)
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


@app.post("/api/sms/hold-plan")
def sms_hold_plan(req: AdviceSmsIn):
    """The hold plan by SMS: the month to sell, "do not sell before", and the price that makes an early sale pay."""
    hold = hold_plan.build(planner.plan(req.lot()))
    if not hold:
        raise HTTPException(status_code=400, detail="The advice is to sell everything now: there is nothing to hold.")
    return {"text": hold["sms"], **sms_client.send_sms(req.phone, hold["sms"])}


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
    state: Optional[dict] = None       # the call preview's state: the call speaks its signed answer
    # Nothing else comes from the page: no free text, caller ID or audio file, so the line cannot be
    # used to ring a stranger with someone else's message (the rule the SMS already follows).


CALL_WELCOME = ("কৃষিভল্ট আলু সংরক্ষণ ও বাজারজাতকরণ সেবায় আপনাকে স্বাগতম। "
                "আপনার এলাকার আলুর বাজার ও হিমাগার তথ্য জানতে সাথেই থাকুন।")


@app.get("/api/call/status")
def call_status():
    sms_cfg = sms_client.sms_config()
    vb = get_voiceblast_client()
    bc = get_broadcast_api_client()

    balance = None
    if bc.live:
        try:
            balance = bc.get_balance()
        except Exception:
            pass
    elif vb.live:
        try:
            balance = vb.get_balance()
        except Exception:
            pass

    is_live = bc.live or vb.live
    caller_id = bc.caller_id if bc.live else (vb.caller_id or bc.caller_id)
    route = "broadcast" if bc.live else ("voiceblast" if vb.live else "dry_run")

    return {
        "gemini": {"on": gemini_client.available, "model": gemini_client.model_used},
        "google_voice": tts_service.status(),
        "sms": {"configured": sms_cfg["configured"], "live": sms_cfg["live"]},
        "voiceblast": {
            "live": is_live,
            "route": route,
            "caller_id": caller_id,
            "balance": balance or ("Active" if is_live else "dry_run"),
            "default_audio_id": vb.default_audio_id,
        },
        "calls": "live" if is_live else "preview",
    }


@app.post("/api/call/dial")
def call_dial(req: VoiceDialRequest, request: Request):
    """
    A real outbound call to a Bangladeshi mobile (VoiceBlast, or the Broadcast API) that speaks the
    answer of this call preview, signed by the server like the SMS; without one, a fixed welcome.
    """
    clean_phone = voiceblast_client.bd_mobile(req.phone)
    if not clean_phone:
        raise HTTPException(status_code=400, detail="Phone number must be a valid Bangladeshi mobile (01XXXXXXXXX)")
    text_to_speak = CALL_WELCOME
    if req.state:
        text_to_speak = call_script(req.state)
        if not text_to_speak:
            raise HTTPException(status_code=400, detail="There is no answer in this call to read out yet.")

    # Abuse protection (allow-list, daily cap, per-IP rate limit) before anything is spent
    check_and_record_dial(client_ip(request), clean_phone)
    res = dispatch_call(clean_phone, text_to_speak)
    if not res.get("success"):
        raise HTTPException(status_code=res.pop("status", 400), detail=res.get("error", "Call dispatch failed"))
    return res


def dispatch_call(clean_phone: str, text: str) -> dict:
    """Ring one number and read `text`, which this server built: the Broadcast API when live, else VoiceBlast."""
    vb = get_voiceblast_client()
    bc = get_broadcast_api_client()
    if bc.live:
        wav_path = call_audio.prepare(text, tts_service)
        if not wav_path or not wav_path.exists():
            return {"success": False, "status": 500, "error": "Failed to synthesize advice audio for broadcast"}
        res = bc.send_broadcast(clean_phone, audio_file_path=wav_path, caller_id=None)
        if not res.get("success"):
            from loguru import logger
            logger.warning(f"Broadcast API failed: {res.get('error')}")
        return res
    # VoiceBlast with the cached audio ID (pre-warmed when the answer was given); a dry run spends nothing
    audio_id = (call_audio.voiceblast_audio_id(text, vb, tts_service) if vb.live else None) or vb.default_audio_id
    return vb.send_call(clean_phone, audio_file_id=audio_id, caller_id=None)


def place_call(phone_input: Optional[str], text: str, request: Request) -> dict:
    """One call for a batch (the price-window alerts): within the same limits; problems come back, not raised."""
    clean = next(iter(sms_client.parse_bd_mobiles(phone_input or "")), None)
    if not clean:
        return {"error": "no Bangladeshi mobile number"}
    try:
        check_and_record_dial(client_ip(request), clean)
    except HTTPException as e:
        return {"error": e.detail}
    res = dispatch_call(clean, text)
    res.pop("status", None)
    return {**res, "phone": event_log.mask_phone(clean)}


@app.get("/api/call/history")
def call_history():
    """Recent outbound calls from VoiceBlast (or Broadcast if active); numbers masked, like every screen."""
    bc = get_broadcast_api_client()
    vb = get_voiceblast_client()
    client = bc if bc.live else vb
    history = [{**h, "phone": event_log.mask_phone(h.get("phone")) or ""} for h in client.get_history(limit=10)]
    return {"history": history, "balance": client.get_balance()}


@app.post("/api/call/turn")
def call_turn(req: CallTurnRequest):
    if req.kind not in ("start", "speech", "keypad"):
        raise HTTPException(status_code=400, detail="kind must be start, speech or keypad")
    if req.kind != "start" and not (req.state and req.state.get("step")):
        raise HTTPException(status_code=400, detail="Start a call first (kind=start)")
    reply = conversation.turn(req.state, {
        "kind": req.kind, "text": req.text, "digits": req.digits, "district": req.district,
        "month": req.month, "year": req.year, "phone": req.phone,
    })

    # Pre-warm the phone-call audio with the exact text a call would speak, so "Call me" starts at once
    answer = call_script(reply.get("state") or {})
    if answer and call_audio.is_advice(answer):
        vb = get_voiceblast_client()
        bc = get_broadcast_api_client()
        if vb.live or bc.live:
            call_audio.prewarm(answer, vb, tts_service)

    return reply


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


# ============================================================ the whole loop in one click (demo walkthrough)

class LoopIn(BaseModel):
    maunds: float = Field(80, gt=0, le=10_000)
    price_today: float = Field(16, gt=0, le=500)
    cash_needed_tk: float = Field(25_000, ge=0, le=10_000_000)
    cash_days: int = Field(4, ge=0, le=365)
    month: int = Field(3, ge=1, le=12)
    year: int = Field(2027, ge=2013, le=2035)


@app.post("/api/demo/loop")
def demo_loop_run(req: LoopIn):
    """The plan's loop for one demo farmer: call, receipt, bank loan, price alert, sale. Demo partners; nothing sent."""
    return demo_loop.run(req.maunds, req.price_today, req.cash_needed_tk, req.cash_days, req.month, req.year)


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
