"""
What the decision engine needs during a call, besides what the farmer said
==========================================================================
- Price outlook: the farmer's own offer (or a demo partner buyer's price) as today's price, moved by the
  seasonal pattern in config/settings.py. This is NOT a trained forecast (the SARIMA/LSTM model has never
  been trained); every screen that shows it says "seasonal pattern".
- Partners: buyers, the cold storage and neighbours for a group lot. In the prototype these are the
  sample rows in data/krishivault.db: demo data, never real partners.

District names: the WFP data and the sample database spell some districts the old way (Bogra), so a
lookup for Bogura also checks Bogra.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from config.settings import POTATO_SEASONAL_PATTERN, MAUND_TO_KG
from src.database import Buyer, ColdStorage
from src.engine.decision_engine import BuyerOffer, MarketContext

DISTRICT_ALIASES = {
    "bogura": ["Bogura", "Bogra"],
    "chattogram": ["Chattogram", "Chittagong"],
    "cumilla": ["Cumilla", "Comilla"],
    "jashore": ["Jashore", "Jessore"],
    "barishal": ["Barishal", "Barisal"],
}

# Used only when the farmer does not know the offer and no demo buyer is listed for the district
ASSUMED_PRICE_PER_KG = 20.0

# Neighbours who could join a group lot (demo; real ones come from officer registrations)
DEMO_NEIGHBOURS = [
    {"name": "Demo neighbour A", "available_kg": round(40 * MAUND_TO_KG, 1)},
    {"name": "Demo neighbour B", "available_kg": round(35 * MAUND_TO_KG, 1)},
]


def district_names(district: str) -> list[str]:
    key = (district or "").strip().lower()
    for names in DISTRICT_ALIASES.values():
        if key in (n.lower() for n in names):
            return names
    return [district]


def seasonal_ratio(month: int, days_ahead: int) -> float:
    """How the seasonal pattern moves a price from this month to days_ahead later (1.08 = up 8%)."""
    pos = (month - 1) + days_ahead / 30.0
    lo = int(pos) % 12
    hi = (lo + 1) % 12
    frac = pos - int(pos)
    later = POTATO_SEASONAL_PATTERN[lo + 1] * (1 - frac) + POTATO_SEASONAL_PATTERN[hi + 1] * frac
    return later / POTATO_SEASONAL_PATTERN[month]


def seasonal_outlook(price_today: float, month: Optional[int] = None) -> tuple[MarketContext, dict]:
    month = month or date.today().month
    r7, r14, r30 = (seasonal_ratio(month, d) for d in (7, 14, 30))
    trend = "up" if r30 > 1.02 else ("down" if r30 < 0.98 else "stable")
    market = MarketContext(
        current_price_per_kg=price_today,
        predicted_7d_price=round(price_today * r7, 2),
        predicted_14d_price=round(price_today * r14, 2),
        predicted_30d_price=round(price_today * r30, 2),
        price_trend=trend,
        # Low on purpose: a seasonal pattern, not a forecast
        confidence_7d=0.5,
        confidence_14d=0.5,
        confidence_30d=0.5,
    )
    note = {
        "method": "seasonal pattern (config/settings.py), not a trained forecast",
        "month": month,
        "change_30d_pct": round((r30 - 1) * 100, 1),
        "price_in_30d": market.predicted_30d_price,
    }
    return market, note


@dataclass
class PartnerContext:
    buyer_offers: list = field(default_factory=list)
    reference_price: Optional[float] = None
    reference_label: str = ""
    cold_storage: Optional[dict] = None
    neighbours: list = field(default_factory=list)


def partner_context(session, district: str) -> PartnerContext:
    """Demo partners from the sample database for one district (plus Dhaka buyers, as before)."""
    names = district_names(district)
    ctx = PartnerContext(neighbours=list(DEMO_NEIGHBOURS))

    buyers = session.query(Buyer).filter(Buyer.district.in_(names + ["Dhaka"])).all()
    for b in buyers:
        if not b.current_offer_per_kg:
            continue
        ctx.buyer_offers.append(BuyerOffer(
            buyer_name=b.name,
            buyer_type=b.buyer_type,
            price_per_kg=b.current_offer_per_kg,
            min_quantity_kg=b.min_quantity_kg or 0.0,
            payment_days=b.payment_days or 3,
            district=b.district,
        ))

    local = [o for o in ctx.buyer_offers if o.district in names]
    if local:
        nearest = min(local, key=lambda o: o.min_quantity_kg)
        ctx.reference_price = nearest.price_per_kg
        ctx.reference_label = "demo partner buyer's price in the district"
    else:
        ctx.reference_price = ASSUMED_PRICE_PER_KG
        ctx.reference_label = "assumed price (no buyer listed for the district)"

    storage = (
        session.query(ColdStorage)
        .filter(ColdStorage.district.in_(names), ColdStorage.is_active.is_(True))
        .order_by(ColdStorage.available_tonnes.desc())
        .first()
    )
    if storage and (storage.available_tonnes or 0) > 0:
        ctx.cold_storage = {
            "id": storage.id,
            "name": storage.name,
            "upazila": storage.upazila,
            "rate_per_kg": storage.actual_rate_per_kg or storage.official_rate_per_kg,
            "available_tonnes": storage.available_tonnes,
            "demo": True,
        }
    return ctx
