"""
Unit Tests for DecisionEngine
=============================
Tests the 4 harvest optimization scenarios:
1. Sell Now
2. Sell Part Now (partial sale to cover urgent debt)
3. Store & Review (break-even vs expected price)
4. Group Sell (quantity aggregation for buyer premium)
"""

import pytest
from src.engine.decision_engine import (
    DecisionEngine, FarmerSituation, MarketContext, BuyerOffer
)
from config.settings import MAUND_TO_KG

def test_sell_now_proceeds():
    situation = FarmerSituation(
        crop="potato",
        quantity_kg=1000.0,
        district="Bogura",
        cash_needed_tk=10000.0,
        deadline_days=5,
        current_offer_per_kg=20.0,
        transport_cost_per_kg=0.50
    )
    market = MarketContext(
        current_price_per_kg=20.0,
        predicted_7d_price=21.0,
        predicted_30d_price=22.0
    )

    engine = DecisionEngine()
    output = engine.evaluate(farmer=situation, market=market)

    # Expected net price = 20.0 - 0.50 transport = 19.50/kg
    # Total net proceeds = 1000 * 19.50 = 19,500 Tk
    sell_now = [s for s in output.scenarios if s.scenario == "sell_now"][0]
    assert sell_now.feasible is True
    assert sell_now.expected_proceeds_tk == 19500.0

def test_store_review_infeasible_when_tight_deadline():
    # If farmer needs cash in 3 days, 30-day cold storage cannot meet the cash deadline
    situation = FarmerSituation(
        crop="potato",
        quantity_kg=2000.0,
        cash_needed_tk=30000.0,
        deadline_days=3,
        has_cold_storage=True
    )
    market = MarketContext(
        current_price_per_kg=20.0,
        predicted_30d_price=30.0
    )

    engine = DecisionEngine()
    output = engine.evaluate(farmer=situation, market=market)

    store_scenario = [s for s in output.scenarios if s.scenario == "store_review"][0]
    assert store_scenario.feasible is False
    assert "deadline" in store_scenario.infeasible_reason.lower()

def test_group_sell_aggregation():
    situation = FarmerSituation(
        crop="potato",
        quantity_kg=1500.0,  # ~40 maunds
        cash_needed_tk=10000.0,
        deadline_days=10,
        current_offer_per_kg=18.0
    )
    market = MarketContext(
        current_price_per_kg=18.0,
        predicted_7d_price=18.5,
        predicted_30d_price=19.0
    )
    # Buyer requiring 3000 kg minimum at Tk 21.00/kg
    buyers = [
        BuyerOffer(
            buyer_name="PRAN Agro",
            buyer_type="company",
            price_per_kg=21.00,
            min_quantity_kg=3000.0,
            payment_days=3,
            district="Bogura"
        )
    ]
    # 2 nearby farmers with 2000 kg
    nearby = [{"id": 2, "quantity_kg": 2000.0, "distance_km": 3.0}]

    engine = DecisionEngine()
    output = engine.evaluate(farmer=situation, market=market, buyer_offers=buyers, nearby_farmers=nearby)

    group_scenario = [s for s in output.scenarios if s.scenario == "group_sell"][0]
    assert group_scenario.feasible is True
    # Farmer sells at 21.00 - transport (0.50) = 20.50/kg
    assert group_scenario.expected_proceeds_tk > 1500.0 * 18.0
