"""
KrishiVault Decision Engine
=============================
The core brain of KrishiVault — takes farmer's situation + market data
and generates a ranked, personalized harvest decision.

Four scenarios evaluated:
  1. Sell Now — full immediate sale
  2. Sell Part Now — partial sale to cover urgent cash needs
  3. Store & Review — calculate break-even for storage
  4. Group Sell — pool with nearby farmers for better price

Each scenario produces:
  - Expected net proceeds (Tk)
  - Risk level
  - Confidence score
  - Plain-language explanation (in Bangla)
"""

import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import (
    COLD_STORAGE_COST_PER_KG_MONTH,
    SPOILAGE_RATE_COLD_STORAGE,
    SPOILAGE_RATE_HOME_STORAGE,
    SPOILAGE_RATE_TRANSPORT,
    MAUND_TO_KG,
)


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class FarmerSituation:
    """Everything we extract from the farmer's phone call."""
    crop: str = "potato"
    quantity_kg: float = 0.0               # Total harvest
    district: str = "Bogura"
    upazila: str = ""
    cash_needed_tk: float = 0.0            # Urgent cash requirement
    deadline_days: int = 7                  # Days until money is needed
    current_offer_per_kg: float = 0.0       # Best offer farmer has now
    has_cold_storage: bool = False          # Can they access cold storage?
    storage_cost_per_kg: float = COLD_STORAGE_COST_PER_KG_MONTH
    storage_handling_cost_per_kg: float = 2.00 # Jute sack (Tk 1.20) + kuli/labor (Tk 0.80)
    transport_cost_per_kg: float = 0.50     # Transport to market/storage
    variety: str = "deshi"                  # deshi or holland
    has_dadon: bool = False                 # Is the farmer bound by advance loans (দাদন)?
    dadon_amount_tk: float = 0.0           # Total loan amount owed to faria/arhatdar
    corporate_rejection_rate: float = 0.15  # Expected factory grading rejection/cull rate (15%)

    @classmethod
    def from_maunds(cls, quantity_maunds: float, **kwargs):
        """Create from quantity in maunds (common farmer unit)."""
        return cls(quantity_kg=quantity_maunds * MAUND_TO_KG, **kwargs)

    @property
    def quantity_maunds(self) -> float:
        return self.quantity_kg / MAUND_TO_KG


@dataclass
class MarketContext:
    """Current and predicted market data."""
    current_price_per_kg: float = 0.0      # Today's market price
    predicted_7d_price: float = 0.0
    predicted_14d_price: float = 0.0
    predicted_30d_price: float = 0.0
    price_trend: str = "stable"            # "up", "down", "stable"
    confidence_7d: float = 0.0             # 0-1 confidence
    confidence_14d: float = 0.0
    confidence_30d: float = 0.0
    volatility_30d: float = 0.0            # Price volatility measure


@dataclass
class BuyerOffer:
    """A specific buyer's current offer."""
    buyer_name: str = ""
    buyer_type: str = ""                   # arhatdar, wholesaler, cooperative
    price_per_kg: float = 0.0
    min_quantity_kg: float = 0.0
    payment_days: int = 0                  # Days until payment
    district: str = ""


@dataclass
class ScenarioResult:
    """Result of evaluating one scenario."""
    scenario: str                          # "sell_now", "sell_part", "store", "group_sell"
    rank: int = 0                          # 1 = best recommendation
    feasible: bool = True                  # Can the farmer actually do this?
    infeasible_reason: str = ""

    # Financial outcome
    expected_proceeds_tk: float = 0.0      # Net money farmer gets
    sell_quantity_kg: float = 0.0          # How much to sell
    store_quantity_kg: float = 0.0         # How much to store
    sell_price_per_kg: float = 0.0

    # Storage analysis
    break_even_price: float = 0.0          # Price needed for storage to be worth it
    storage_cost_total: float = 0.0
    spoilage_loss_kg: float = 0.0

    # Risk assessment
    risk_level: str = "medium"             # "low", "medium", "high"
    confidence: float = 0.5                # 0-1

    # Explanation
    explanation_en: str = ""               # English explanation
    explanation_bn: str = ""               # Bangla explanation

    # For group sell
    group_quantity_needed_kg: float = 0.0
    nearby_farmers_count: int = 0
    group_price_premium: float = 0.0


@dataclass
class DecisionOutput:
    """Complete decision output from the engine."""
    farmer: FarmerSituation
    market: MarketContext
    scenarios: list = field(default_factory=list)
    recommended: Optional[ScenarioResult] = None
    generated_at: str = ""
    summary_en: str = ""
    summary_bn: str = ""


# ============================================================
# DECISION ENGINE
# ============================================================

class DecisionEngine:
    """
    The core KrishiVault decision engine.
    
    Evaluates all four scenarios given a farmer's situation
    and current/predicted market data, then ranks them.
    """

    def __init__(self):
        pass

    def evaluate(
        self,
        farmer: FarmerSituation,
        market: MarketContext,
        buyer_offers: list[BuyerOffer] = None,
        nearby_farmers: list[dict] = None,
    ) -> DecisionOutput:
        """
        Run full 4-scenario evaluation and produce ranked recommendation.
        """
        buyer_offers = buyer_offers or []
        nearby_farmers = nearby_farmers or []

        scenarios = [
            self._evaluate_sell_now(farmer, market, buyer_offers),
            self._evaluate_sell_part(farmer, market, buyer_offers),
            self._evaluate_store_review(farmer, market),
            self._evaluate_group_sell(farmer, market, buyer_offers, nearby_farmers),
        ]

        # Rank scenarios
        feasible = [s for s in scenarios if s.feasible]
        feasible.sort(key=lambda s: s.expected_proceeds_tk, reverse=True)
        
        for i, s in enumerate(feasible):
            s.rank = i + 1

        # Apply urgency override: if cash deadline is very tight,
        # prefer immediate-cash scenarios even if they earn less
        recommended = self._apply_urgency_rules(farmer, feasible)

        output = DecisionOutput(
            farmer=farmer,
            market=market,
            scenarios=scenarios,
            recommended=recommended,
            generated_at=date.today().isoformat(),
        )

        # Generate summaries
        output.summary_en = self._generate_summary_en(output)
        output.summary_bn = self._generate_summary_bn(output)

        return output

    # --------------------------------------------------------
    # Scenario 1: SELL NOW (Full immediate sale)
    # --------------------------------------------------------
    def _evaluate_sell_now(
        self,
        farmer: FarmerSituation,
        market: MarketContext,
        offers: list[BuyerOffer]
    ) -> ScenarioResult:
        """Evaluate selling the entire harvest immediately."""
        
        # Best available price
        sell_price = farmer.current_offer_per_kg or market.current_price_per_kg
        if offers:
            # Find best offer that can be fulfilled within deadline
            valid_offers = [
                o for o in offers
                if o.payment_days <= farmer.deadline_days
                and o.min_quantity_kg <= farmer.quantity_kg
            ]
            if valid_offers:
                best = max(valid_offers, key=lambda o: o.price_per_kg)
                sell_price = max(sell_price, best.price_per_kg)

        # Net proceeds after transport
        net_price = sell_price - farmer.transport_cost_per_kg
        proceeds = farmer.quantity_kg * net_price

        # Feasibility check
        feasible = True
        reason = ""
        if sell_price <= 0:
            feasible = False
            reason = "No valid price/offer available"

        # Risk: Low (immediate cash, no storage risk)
        result = ScenarioResult(
            scenario="sell_now",
            feasible=feasible,
            infeasible_reason=reason,
            expected_proceeds_tk=proceeds,
            sell_quantity_kg=farmer.quantity_kg,
            store_quantity_kg=0,
            sell_price_per_kg=sell_price,
            risk_level="low",
            confidence=0.95,
            explanation_en=(
                f"Sell your entire {farmer.quantity_maunds:.1f} maunds "
                f"at Tk {sell_price:.1f}/kg. "
                f"Net proceeds: Tk {proceeds:,.0f} after transport costs."
            ),
        )

        # Check if this covers cash needs
        if proceeds < farmer.cash_needed_tk and farmer.cash_needed_tk > 0:
            result.explanation_en += (
                f" ⚠️ This covers only Tk {proceeds:,.0f} of your "
                f"Tk {farmer.cash_needed_tk:,.0f} requirement."
            )
            result.risk_level = "medium"

        # Check Dadon loan encumbrance
        if getattr(farmer, "has_dadon", False) and getattr(farmer, "dadon_amount_tk", 0) > 0:
            if proceeds >= farmer.dadon_amount_tk:
                net_after_debt = proceeds - farmer.dadon_amount_tk
                result.explanation_en += (
                    f" (Clears your Tk {farmer.dadon_amount_tk:,.0f} Dadon debt; net cash remaining: Tk {net_after_debt:,.0f})."
                )
            else:
                shortfall = farmer.dadon_amount_tk - proceeds
                result.explanation_en += (
                    f" ⚠️ Shortfall of Tk {shortfall:,.0f} to clear Dadon debt."
                )
                result.risk_level = "high"

        return result

    # --------------------------------------------------------
    # Scenario 2: SELL PART NOW
    # --------------------------------------------------------
    def _evaluate_sell_part(
        self,
        farmer: FarmerSituation,
        market: MarketContext,
        offers: list[BuyerOffer]
    ) -> ScenarioResult:
        """
        Sell just enough to cover urgent cash needs,
        store the rest for potentially better prices.
        """
        sell_price = farmer.current_offer_per_kg or market.current_price_per_kg
        net_price = sell_price - farmer.transport_cost_per_kg

        # Feasibility
        if farmer.cash_needed_tk <= 0:
            return ScenarioResult(
                scenario="sell_part",
                feasible=False,
                infeasible_reason="No urgent cash need specified — full strategies preferred",
            )

        if net_price <= 0:
            return ScenarioResult(
                scenario="sell_part",
                feasible=False,
                infeasible_reason="Price too low for any sale",
            )

        # Calculate minimum quantity to sell
        sell_kg = farmer.cash_needed_tk / net_price
        store_kg = farmer.quantity_kg - sell_kg

        if sell_kg >= farmer.quantity_kg:
            return ScenarioResult(
                scenario="sell_part",
                feasible=False,
                infeasible_reason=(
                    f"Need to sell entire harvest "
                    f"({farmer.quantity_maunds:.1f} maunds) to cover cash needs. "
                    f"Sell Now is better."
                ),
            )

        if store_kg < 0:
            store_kg = 0
            sell_kg = farmer.quantity_kg

        # Estimate future value of stored portion
        future_price = market.predicted_30d_price or sell_price
        spoilage_rate = (
            SPOILAGE_RATE_COLD_STORAGE if farmer.has_cold_storage
            else SPOILAGE_RATE_HOME_STORAGE
        )
        stored_value = store_kg * (1 - spoilage_rate) * future_price
        storage_cost = store_kg * farmer.storage_cost_per_kg if farmer.has_cold_storage else 0

        immediate_proceeds = sell_kg * net_price
        total_expected = immediate_proceeds + stored_value - storage_cost

        sell_maunds = sell_kg / MAUND_TO_KG
        store_maunds = store_kg / MAUND_TO_KG

        return ScenarioResult(
            scenario="sell_part",
            feasible=True,
            expected_proceeds_tk=total_expected,
            sell_quantity_kg=sell_kg,
            store_quantity_kg=store_kg,
            sell_price_per_kg=sell_price,
            storage_cost_total=storage_cost,
            spoilage_loss_kg=store_kg * spoilage_rate,
            risk_level="medium",
            confidence=market.confidence_30d or 0.6,
            explanation_en=(
                f"Sell {sell_maunds:.1f} maunds now at Tk {sell_price:.1f}/kg "
                f"(covers your Tk {farmer.cash_needed_tk:,.0f} need). "
                f"Store remaining {store_maunds:.1f} maunds. "
                f"Expected total proceeds: Tk {total_expected:,.0f}."
            ),
        )

    # --------------------------------------------------------
    # Scenario 3: STORE & REVIEW
    # --------------------------------------------------------
    def _evaluate_store_review(
        self,
        farmer: FarmerSituation,
        market: MarketContext,
    ) -> ScenarioResult:
        """
        Calculate whether storing the entire harvest is worthwhile.
        Computes the break-even future price.
        """
        sell_price = farmer.current_offer_per_kg or market.current_price_per_kg

        # Feasibility
        if not farmer.has_cold_storage:
            # Home storage has much higher losses
            spoilage_rate = SPOILAGE_RATE_HOME_STORAGE
            storage_cost = 0  # No rental cost, but high spoilage
        else:
            spoilage_rate = SPOILAGE_RATE_COLD_STORAGE
            # Include seasonal storage rent + jute sacks + labor/loading handling
            storage_cost = farmer.storage_cost_per_kg + getattr(farmer, "storage_handling_cost_per_kg", 2.00)

        # Cannot store if deadline is too tight
        if farmer.deadline_days <= 3 and farmer.cash_needed_tk > 0:
            return ScenarioResult(
                scenario="store_review",
                feasible=False,
                infeasible_reason=(
                    f"Cash deadline of {farmer.deadline_days} days is too tight for storage."
                ),
            )

        # Break-even calculation:
        # break_even_price = (sell_price + storage_cost) / (1 - spoilage_rate)
        break_even = (sell_price + storage_cost) / (1 - spoilage_rate)
        price_increase_needed = ((break_even / sell_price) - 1) * 100

        # Estimate proceeds if stored:
        # In real Bangladesh potato economics, cold storage is held for the seasonal lean period (Oct-Nov)
        # We compare against the 30-day forecast as a minimum milestone, plus seasonal lean expectation
        future_price = market.predicted_30d_price or sell_price
        surviving_kg = farmer.quantity_kg * (1 - spoilage_rate)
        net_future_proceeds = (surviving_kg * future_price) - (farmer.quantity_kg * storage_cost)
        immediate_proceeds = farmer.quantity_kg * (sell_price - farmer.transport_cost_per_kg)

        # Is storage likely to be profitable?
        storage_profitable = future_price >= break_even
        confidence = market.confidence_30d or 0.5

        risk = "low" if storage_profitable and confidence > 0.7 else (
            "high" if not storage_profitable else "medium"
        )

        return ScenarioResult(
            scenario="store_review",
            feasible=True,
            expected_proceeds_tk=max(net_future_proceeds, 0),
            sell_quantity_kg=0,
            store_quantity_kg=farmer.quantity_kg,
            sell_price_per_kg=0,
            break_even_price=break_even,
            storage_cost_total=farmer.quantity_kg * storage_cost,
            spoilage_loss_kg=farmer.quantity_kg * spoilage_rate,
            risk_level=risk,
            confidence=confidence,
            explanation_en=(
                f"Store all {farmer.quantity_maunds:.1f} maunds. "
                f"Break-even price: Tk {break_even:.2f}/kg "
                f"(requires {price_increase_needed:.1f}% price increase including Tk {storage_cost:.2f}/kg rent+sacks). "
                f"30-day forecast: Tk {future_price:.1f}/kg. "
                f"{'✅ Storage looks profitable.' if storage_profitable else '⚠️ Storage may not be worth it.'}"
            ),
        )

    # --------------------------------------------------------
    # Scenario 4: GROUP SELL
    # --------------------------------------------------------
    def _evaluate_group_sell(
        self,
        farmer: FarmerSituation,
        market: MarketContext,
        offers: list[BuyerOffer],
        nearby_farmers: list[dict],
    ) -> ScenarioResult:
        """
        Evaluate pooling with nearby farmers to unlock better prices.
        Includes a 15% corporate grading & cull buffer (sold locally at distress rate).
        """
        sell_price = farmer.current_offer_per_kg or market.current_price_per_kg

        # Find bulk buyer offers (higher price, higher minimum)
        bulk_offers = [
            o for o in offers
            if o.min_quantity_kg > farmer.quantity_kg
            and o.price_per_kg > sell_price
        ]

        if not bulk_offers and not nearby_farmers:
            return ScenarioResult(
                scenario="group_sell",
                feasible=False,
                infeasible_reason="No bulk buyers or nearby farmers available for pooling.",
            )

        # Best bulk offer
        if bulk_offers:
            best_bulk = max(bulk_offers, key=lambda o: o.price_per_kg)
            group_price = best_bulk.price_per_kg
            min_needed = best_bulk.min_quantity_kg
        else:
            # Estimate: group selling typically gets 10-15% premium
            group_price = sell_price * 1.10
            min_needed = farmer.quantity_kg * 3  # Need ~3x more

        # How much more quantity is needed?
        quantity_gap = max(0, min_needed - farmer.quantity_kg)

        # Can nearby farmers fill the gap?
        available_from_neighbors = sum(
            f.get("available_kg", 0) for f in nearby_farmers
        )

        if available_from_neighbors >= quantity_gap:
            feasible = True
            total_pool = farmer.quantity_kg + available_from_neighbors
        elif nearby_farmers:
            feasible = True
            total_pool = farmer.quantity_kg + available_from_neighbors
        else:
            feasible = False
            total_pool = farmer.quantity_kg

        # Net proceeds with realistic factory grading (85% Grade-A, 15% local culls)
        rejection_rate = getattr(farmer, "corporate_rejection_rate", 0.15)
        grade_a_kg = farmer.quantity_kg * (1 - rejection_rate)
        cull_kg = farmer.quantity_kg * rejection_rate
        cull_price = sell_price * 0.60  # Local haat rate for culled/graded-out potatoes

        revenue_grade_a = grade_a_kg * group_price
        revenue_cull = cull_kg * cull_price
        transport_total = farmer.quantity_kg * farmer.transport_cost_per_kg
        proceeds = (revenue_grade_a + revenue_cull) - transport_total
        effective_price = proceeds / farmer.quantity_kg if farmer.quantity_kg > 0 else (group_price - farmer.transport_cost_per_kg)
        premium = effective_price - sell_price

        return ScenarioResult(
            scenario="group_sell",
            feasible=feasible,
            infeasible_reason="" if feasible else f"Need {quantity_gap:.0f}kg more from neighbors",
            expected_proceeds_tk=proceeds,
            sell_quantity_kg=farmer.quantity_kg,
            store_quantity_kg=0,
            sell_price_per_kg=effective_price,
            risk_level="medium",
            confidence=0.7 if feasible else 0.3,
            group_quantity_needed_kg=quantity_gap,
            nearby_farmers_count=len(nearby_farmers),
            group_price_premium=premium,
            explanation_en=(
                f"Pool with {len(nearby_farmers)} nearby farmers "
                f"(total: {total_pool / MAUND_TO_KG:.0f} maunds). "
                f"Corporate offer: Tk {group_price:.1f}/kg. "
                f"Net realized price: Tk {effective_price:.1f}/kg after 15% grading buffer & transport. "
                f"Your net proceeds: Tk {proceeds:,.0f}."
            ),
        )

    # --------------------------------------------------------
    # Urgency Rules
    # --------------------------------------------------------
    def _apply_urgency_rules(
        self,
        farmer: FarmerSituation,
        ranked: list[ScenarioResult]
    ) -> Optional[ScenarioResult]:
        """
        Apply urgency overrides:
        - If deadline ≤ 3 days, strongly prefer immediate-cash options
        - If cash need > 0, ensure the recommended option covers it
        """
        if not ranked:
            return None

        if farmer.deadline_days <= 3 and farmer.cash_needed_tk > 0:
            # Urgent: prioritize scenarios that provide cash within deadline
            for s in ranked:
                if s.scenario in ("sell_now", "sell_part"):
                    sell_proceeds = s.sell_quantity_kg * (s.sell_price_per_kg - farmer.transport_cost_per_kg)
                    if sell_proceeds >= farmer.cash_needed_tk:
                        return s
            # If nothing fully covers, still recommend the one that comes closest
            immediate = [s for s in ranked if s.scenario in ("sell_now", "sell_part")]
            if immediate:
                return immediate[0]

        return ranked[0]

    # --------------------------------------------------------
    # Summary Generation
    # --------------------------------------------------------
    def _generate_summary_en(self, output: DecisionOutput) -> str:
        """Generate English summary of the recommendation."""
        rec = output.recommended
        if not rec:
            return "Unable to generate a recommendation. Please provide more information."

        return (
            f"Recommendation: {rec.scenario.replace('_', ' ').title()}. "
            f"{rec.explanation_en} "
            f"Risk level: {rec.risk_level}. Confidence: {rec.confidence:.0%}."
        )

    def _generate_summary_bn(self, output: DecisionOutput) -> str:
        """
        Generate Bangla summary of the recommendation.
        In production, this would use an LLM for natural Bangla generation.
        For now, we use template-based translation.
        """
        rec = output.recommended
        if not rec:
            return "সুপারিশ তৈরি করা সম্ভব হয়নি। আরও তথ্য দিন।"

        scenario_bn = {
            "sell_now": "এখনই সব বিক্রি করুন",
            "sell_part": "কিছু অংশ বিক্রি করুন",
            "store_review": "সংরক্ষণ করুন এবং পর্যালোচনা করুন",
            "group_sell": "দলগতভাবে বিক্রি করুন",
        }

        return (
            f"সুপারিশ: {scenario_bn.get(rec.scenario, rec.scenario)}। "
            f"প্রত্যাশিত আয়: ৳{rec.expected_proceeds_tk:,.0f}।"
        )


# ============================================================
# USAGE EXAMPLE
# ============================================================

if __name__ == "__main__":
    # Example: A farmer from Bogura calls with 20 maunds of potatoes
    farmer = FarmerSituation.from_maunds(
        quantity_maunds=20,
        district="Bogura",
        cash_needed_tk=8000,
        deadline_days=3,
        current_offer_per_kg=20.0,
        has_cold_storage=True,
        storage_cost_per_kg=6.0,
    )

    market = MarketContext(
        current_price_per_kg=20.0,
        predicted_7d_price=21.5,
        predicted_14d_price=22.8,
        predicted_30d_price=24.5,
        price_trend="up",
        confidence_7d=0.85,
        confidence_14d=0.75,
        confidence_30d=0.62,
        volatility_30d=2.3,
    )

    # Example buyer offers
    offers = [
        BuyerOffer(
            buyer_name="Local Arhatdar",
            buyer_type="arhatdar",
            price_per_kg=20.0,
            min_quantity_kg=50,
            payment_days=1,
            district="Bogura",
        ),
        BuyerOffer(
            buyer_name="Regional Wholesaler",
            buyer_type="wholesaler",
            price_per_kg=22.0,
            min_quantity_kg=2000,   # ~53 maunds — too much for one farmer
            payment_days=3,
            district="Bogura",
        ),
    ]

    # Nearby farmers willing to pool
    nearby = [
        {"name": "Farmer B", "available_kg": 450},
        {"name": "Farmer C", "available_kg": 930},
    ]

    engine = DecisionEngine()
    result = engine.evaluate(farmer, market, offers, nearby)

    print("=" * 60)
    print("🧠 KRISHIVAULT DECISION ENGINE")
    print("=" * 60)
    print(f"\n📋 Farmer: {farmer.quantity_maunds:.0f} maunds in {farmer.district}")
    print(f"   Cash need: Tk {farmer.cash_needed_tk:,.0f} in {farmer.deadline_days} days")
    print(f"   Current offer: Tk {farmer.current_offer_per_kg}/kg")
    print(f"\n📈 Market: Tk {market.current_price_per_kg}/kg → "
          f"Tk {market.predicted_30d_price}/kg (30d forecast)")

    print("\n" + "-" * 60)
    for s in result.scenarios:
        status = "✅" if s.feasible else "❌"
        rank = f"#{s.rank}" if s.rank > 0 else "N/A"
        print(f"\n{status} [{rank}] {s.scenario.upper()}")
        if s.feasible:
            print(f"   💰 Expected: Tk {s.expected_proceeds_tk:,.0f}")
            print(f"   📝 {s.explanation_en}")
            print(f"   ⚡ Risk: {s.risk_level} | Confidence: {s.confidence:.0%}")
        else:
            print(f"   ⛔ {s.infeasible_reason}")

    print("\n" + "=" * 60)
    if result.recommended:
        print(f"🏆 RECOMMENDATION: {result.recommended.scenario.upper()}")
        print(f"   {result.summary_en}")
        print(f"\n🇧🇩 বাংলা: {result.summary_bn}")
    print("=" * 60)
