"""
Storage and selling-time engine
===============================
Answers the farmer's question: "Should I sell my potatoes now, store them,
or sell part and store the rest, and until when?"

How it decides, in plain words:
- It compares selling today with storing for 1, 2, ... up to 9 months (until
  the cold storage empties in December).
- For each month it works out the money left in the farmer's hand: the price
  that month (from the price outlook, 2,000 simulated paths), minus weight
  loss, rent, sacks, carrying, selling costs and loan interest.
- **Rent is flat:** ৳250 a sack whether the sack stays 1 month or 9. So a
  sack stored and sold after 1-2 months usually loses money; storing pays
  only if it is held until prices have risen enough. The engine shows the
  price needed ("break-even") for each month.
- If cash is needed soon, storing means borrowing against the stored sacks
  (cold-storage advance or a bank loan) or selling part now. Interest is
  counted.
- It recommends one of three options, with the chance that storing beats
  selling now and the worst likely outcome (1 path in 10 is worse):
    1. Sell now           (storing is unlikely to pay after costs)
    2. Store longer       (storing very likely pays, even in a bad case)
    3. Sell part, store the rest (storing probably pays, but not surely)

Every taka figure the farmer hears comes from here; the wording layer may not
change them (see `src/voice/number_lock.py`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from src.engine.facts import (
    StorageTerms, MONTHS_EN, MONTHS_BN, LAST_SALE_MONTH, MAUND_KG, month_after,
)
from src.models.price_outlook import real_path, rise_strength, simulate, season_for_decision
from src.voice.bangla_numbers import to_bn_digits

DAYS_PER_MONTH = 30


@dataclass
class FarmerLot:
    quantity_kg: float
    price_today: float                     # ৳/kg the farmer is offered today (farm gate)
    decision_month: int = 3
    decision_year: int = 2027
    stored: str = "no"                     # "no" (just harvested), "cold" (already in cold storage)
    stored_since_month: Optional[int] = None
    cash_needed_tk: float = 0.0
    cash_days: int = 0                     # cash needed within this many days
    loan_source: str = "cheapest"          # "cheapest", "cold_storage", "bank", "none"
    bank_ltv: float = 0.6                  # a bank lends up to this share of the stored crop's value
    production_cost_per_kg: Optional[float] = None
    allow_home: bool = True
    terms: StorageTerms = field(default_factory=StorageTerms)
    # price outlook options
    season_start: Optional[int] = None
    area_ha: Optional[float] = None
    gap_override_pct: Optional[float] = None
    weather_adjust_pct: float = 0.0

    @property
    def sacks(self) -> int:
        return max(1, math.ceil(self.quantity_kg / self.terms.sack_kg - 1e-9))


def months_left(lot: FarmerLot) -> int:
    """How many more months the potatoes can stay in cold storage."""
    m = lot.decision_month
    to_december = 0 if m == 1 else LAST_SALE_MONTH - m
    if lot.stored == "cold" and lot.stored_since_month:
        used = (m - lot.stored_since_month) % 12
        return max(0, min(lot.terms.season_months - used, to_december))
    return max(0, min(lot.terms.season_months, to_december))


def _round_tk(x: float) -> int:
    """Money is shown to the nearest ৳10."""
    return int(round(x / 10.0) * 10)


def _loan_for(lot: FarmerLot, sacks_stored: int, amount: float, crop_value: float) -> dict:
    """The cheapest loan that covers `amount` against `sacks_stored` sacks, or None if none can."""
    t = lot.terms
    options = []
    if lot.loan_source in ("cheapest", "cold_storage"):
        options.append({"source": "cold_storage", "limit": sacks_stored * t.cs_advance_per_sack,
                        "rate_year": t.cs_advance_rate_year})
    if lot.loan_source in ("cheapest", "bank"):
        options.append({"source": "bank", "limit": crop_value * lot.bank_ltv, "rate_year": t.bank_rate_year})
    fitting = [o for o in options if o["limit"] >= amount]
    if not fitting:
        return {"source": None, "limit": max((o["limit"] for o in options), default=0.0), "rate_year": None}
    return min(fitting, key=lambda o: o["rate_year"])


class StoragePlanner:
    def __init__(self, simulations: int = 2000, seed: int = 7):
        self.simulations = simulations
        self.seed = seed

    # ----------------------------------------------------------- price paths
    def price_paths(self, lot: FarmerLot, horizon: int) -> tuple[np.ndarray, dict]:
        season = lot.season_start if lot.season_start is not None else season_for_decision(
            lot.decision_year, lot.decision_month)
        rs = rise_strength(season, lot.area_ha, lot.gap_override_pct, lot.weather_adjust_pct,
                           lot.decision_year, lot.decision_month)
        rs["season"] = f"{season}-{str(season + 1)[-2:]}"
        ratios = simulate(lot.decision_month, horizon, rs["k"], rs["k_sd"], self.simulations, self.seed,
                          sigma=rs["sigma_month"])
        return ratios * lot.price_today, rs

    # ----------------------------------------------------------- money per path
    def _cold_net(self, lot: FarmerLot, kg: float, sacks: int, prices: np.ndarray, h: int) -> tuple[np.ndarray, dict]:
        """Money in hand from `sacks` sacks kept in cold storage and sold after h months (all paths)."""
        t = lot.terms
        already = lot.stored == "cold"
        if h == 0 and not already:
            costs = sacks * t.sell_now_per_sack
            kept = kg
        else:
            costs = sacks * (t.rent_per_sack + t.sell_from_store_per_sack)
            if not already:
                costs += sacks * t.handling_per_sack()
            kept = kg * t.kept_share(h)
        return kept * prices[:, h] - costs, {"kept_kg": kept, "costs": costs}

    def _home_net(self, lot: FarmerLot, kg: float, sacks: int, prices: np.ndarray, h: int) -> np.ndarray:
        t = lot.terms
        kept = kg * (1 - t.home_monthly_loss) ** h
        return kept * prices[:, h] - sacks * (t.sack_cost + t.sell_now_per_sack)

    def _interest(self, lot: FarmerLot, h: int, sacks_stored: int, crop_value: float, cash_from_sale_now: float):
        """Interest if the cash need falls before the stored potatoes are sold."""
        need = max(0.0, lot.cash_needed_tk - cash_from_sale_now)
        if need <= 0 or h == 0 or lot.cash_days >= h * DAYS_PER_MONTH:
            return 0.0, None
        loan = _loan_for(lot, sacks_stored, need, crop_value)
        if loan["source"] is None:
            return None, loan
        months = h - lot.cash_days / DAYS_PER_MONTH
        interest = need * loan["rate_year"] / 12 * max(months, 0)
        return interest, {**loan, "amount": need, "months": round(months, 1), "interest": interest}

    # ----------------------------------------------------------- the plan
    def plan(self, lot: FarmerLot) -> dict:
        t = lot.terms
        H = months_left(lot)
        prices, rise = self.price_paths(lot, max(H, 0))
        kg, sacks = lot.quantity_kg, lot.sacks
        now_net, _ = self._cold_net(lot, kg, sacks, prices, 0)
        now_value = float(now_net.mean())
        crop_value_today = kg * lot.price_today

        rows = []
        for h in range(H + 1):
            net, detail = self._cold_net(lot, kg, sacks, prices, h)
            raw_mean = float(net.mean())
            interest, loan = self._interest(lot, h, sacks, crop_value_today, 0.0)
            feasible = interest is not None
            if feasible:
                net = net - interest
            kept = detail["kept_kg"]
            # price needed this month for storing to match selling today
            break_even = (now_value + detail["costs"] + (interest or 0)) / kept if kept else None
            m = month_after(lot.decision_month, h)
            rows.append({
                "h": h, "month": m, "month_en": MONTHS_EN[m], "month_bn": MONTHS_BN[m],
                "price_mid": round(float(np.median(prices[:, h])), 2),
                "price_low": round(float(np.percentile(prices[:, h], 10)), 2),
                "price_high": round(float(np.percentile(prices[:, h], 90)), 2),
                "net_mean": _round_tk(float(net.mean())), "net_low": _round_tk(float(np.percentile(net, 10))),
                "net_high": _round_tk(float(np.percentile(net, 90))),
                "gain_vs_now": _round_tk(float(net.mean()) - now_value),
                "chance_beats_now": round(float((net > now_value).mean()), 2) if h else None,
                "break_even_price": round(break_even, 2) if (h and break_even) else None,
                "kept_kg": round(kept), "costs": _round_tk(detail["costs"] + (interest or 0)),
                "interest": _round_tk(interest or 0), "loan": loan, "feasible": feasible,
                "_net": net, "_raw_mean": raw_mean,
            })

        # best month to sell stored potatoes (prices and storage costs; the loan question comes after)
        store_rows = [r for r in rows if r["h"] >= 1]
        best = max(store_rows, key=lambda r: r["_raw_mean"]) if store_rows else None

        # home storage (only for a fresh harvest)
        home = None
        if lot.allow_home and lot.stored == "no":
            best_home = None
            for h in range(1, min(t.home_max_months, H) + 1):
                net = self._home_net(lot, kg, sacks, prices, h)
                if best_home is None or net.mean() > best_home[1].mean():
                    best_home = (h, net)
            if best_home:
                h, net = best_home
                m = month_after(lot.decision_month, h)
                home = {"h": h, "month_en": MONTHS_EN[m], "month_bn": MONTHS_BN[m],
                        "net_mean": _round_tk(float(net.mean())), "net_low": _round_tk(float(np.percentile(net, 10))),
                        "gain_vs_now": _round_tk(float(net.mean()) - now_value),
                        "chance_beats_now": round(float((net > now_value).mean()), 2)}

        options = {"sell_now": self._option_now(lot, now_value)}
        if best:
            options["store"] = self._option_store(lot, best, now_value) if best["feasible"] else None
            options["sell_part"] = self._option_part(lot, prices, best, now_value)
        rec = self._recommend(lot, options, now_value, H, rise["k"])
        replay = self._replay(lot, options, rec, now_value, H)

        for r in rows:
            r.pop("_net", None)
            r.pop("_raw_mean", None)
        return {
            "inputs": {
                "quantity_kg": round(kg), "sacks": sacks, "maunds": round(kg / MAUND_KG, 1),
                "price_today": lot.price_today, "decision_month": lot.decision_month,
                "decision_month_en": MONTHS_EN[lot.decision_month], "decision_year": lot.decision_year,
                "stored": lot.stored, "cash_needed_tk": lot.cash_needed_tk, "cash_days": lot.cash_days,
                "terms": t.to_dict(),
            },
            "months_left": H,
            "outlook": rise,
            "by_month": rows,
            "best_month": ({"h": best["h"], "month_en": best["month_en"], "month_bn": best["month_bn"]}
                           if best else None),
            "home_storage": home,
            "options": options,
            "recommendation": rec,
            "cost_floor": self._cost_floor(lot),
            "notes": self._notes(lot, rows, best, H),
            "replay": replay,
        }

    # ----------------------------------------------------------- replays: what really happened
    def _replay(self, lot: FarmerLot, options: dict, rec: dict, now_value: float, H: int) -> Optional[dict]:
        """
        For a past decision date: each option, and the advice, valued at the prices that really followed (the
        WFP national retail change applied to today's price), with the same costs as the advice. Stored sacks
        are sold in the planned month, or the next month with a real price. None when nothing later is known.
        """
        real = real_path(lot.decision_year, lot.decision_month, H) if H else None
        if not real:
            return None
        prices = np.array([[lot.price_today * (r if r is not None else 1.0) for r in real]])
        prices[0, 0] = lot.price_today

        def outcome(option: Optional[dict]) -> Optional[dict]:
            if option is None:
                return None
            if option["key"] == "sell_now":
                return {"money": _round_tk(now_value), "vs_sell_now": 0, "sold_in": MONTHS_EN[lot.decision_month]}
            later = [h for h in range(option["months"], H + 1) if real[h] is not None]
            if not later:
                return None
            h = later[0]
            sell, store = option["sell_sacks_now"], option["store_sacks"]
            kg_store = lot.quantity_kg * store / lot.sacks
            net_now = float(self._cold_net(lot, lot.quantity_kg - kg_store, sell, prices, 0)[0][0]) if sell else 0.0
            net_store = float(self._cold_net(lot, kg_store, store, prices, h)[0][0])
            interest, _ = self._interest(lot, h, store, kg_store * lot.price_today, net_now)
            money = net_now + net_store - (interest or 0.0)
            return {"money": _round_tk(money), "vs_sell_now": _round_tk(money - now_value),
                    "sold_in": MONTHS_EN[month_after(lot.decision_month, h)]}

        valued = {key: outcome(o) for key, o in options.items()}
        # Net profit, when the farmer's growing cost is known: money in hand minus the cost of growing the crop
        profit = None
        if lot.production_cost_per_kg:
            growing = lot.quantity_kg * lot.production_cost_per_kg
            at_harvest = now_value - growing
            advice_gain = (valued.get(rec["key"]) or {}).get("vs_sell_now")
            with_advice = at_harvest + advice_gain if advice_gain is not None else None
            profit = {"growing_cost": _round_tk(growing), "growing_cost_per_kg": lot.production_cost_per_kg,
                      "sold_at_harvest": _round_tk(at_harvest),
                      "with_advice": _round_tk(with_advice) if with_advice is not None else None,
                      "times": (round(with_advice / at_harvest, 1)
                                if with_advice is not None and at_harvest > 0 else None)}
        # Storing every sack, sold in each month that has a real price
        by_month = []
        for h in range(1, H + 1):
            if real[h] is not None:
                money = float(self._cold_net(lot, lot.quantity_kg, lot.sacks, prices, h)[0][0])
                by_month.append({"h": h, "month_en": MONTHS_EN[month_after(lot.decision_month, h)],
                                 "vs_sell_now": _round_tk(money - now_value)})
        return {"basis": "the national retail price change that really followed (WFP), applied to today's price",
                "options": valued, "advice": {"key": rec["key"], **(valued.get(rec["key"]) or {})},
                "store_all_by_month": by_month, "net_profit": profit}

    # ----------------------------------------------------------- the three options
    def _option_now(self, lot: FarmerLot, now_value: float) -> dict:
        return {"key": "sell_now", "title_en": "Sell now", "title_bn": "এখন বেচুন",
                "sell_sacks_now": lot.sacks, "store_sacks": 0, "sell_month_en": MONTHS_EN[lot.decision_month],
                "money_mean": _round_tk(now_value), "money_low": _round_tk(now_value),
                "money_high": _round_tk(now_value), "gain_vs_now": 0, "chance_beats_now": None}

    def _option_store(self, lot: FarmerLot, best: dict, now_value: float) -> dict:
        net = best["_net"]
        return {"key": "store", "title_en": f"Store, sell in {best['month_en']}",
                "title_bn": f"রেখে {best['month_bn']} মাসে বেচুন",
                "sell_sacks_now": 0, "store_sacks": lot.sacks, "sell_month_en": best["month_en"],
                "sell_month_bn": best["month_bn"], "months": best["h"],
                "money_mean": best["net_mean"], "money_low": best["net_low"], "money_high": best["net_high"],
                "gain_vs_now": best["gain_vs_now"], "chance_beats_now": best["chance_beats_now"],
                "worst_case_vs_now": _round_tk(float(np.percentile(net, 10)) - now_value),
                "loan": best["loan"], "break_even_price": best["break_even_price"]}

    def _part_split(self, lot: FarmerLot, chance: float, best_h: int) -> int:
        """How many sacks to sell now: enough for the cash need, and a safety share when storing is uncertain."""
        sack_value_now = lot.terms.sack_kg * lot.price_today - lot.terms.sell_now_per_sack
        need_now = lot.cash_needed_tk > 0 and lot.cash_days < best_h * DAYS_PER_MONTH
        cash_sacks = math.ceil(lot.cash_needed_tk / sack_value_now) if (need_now and sack_value_now > 0) else 0
        safety_share = 0.25 if chance >= 0.8 else 0.4 if chance >= 0.65 else 0.5
        sell = max(cash_sacks, math.ceil(lot.sacks * safety_share))
        return min(max(sell, 1), max(lot.sacks - 1, 1))

    def _option_part(self, lot: FarmerLot, prices: np.ndarray, best: dict, now_value: float) -> dict:
        sell_now = self._part_split(lot, best["chance_beats_now"] or 0, best["h"])
        store = lot.sacks - sell_now
        if store <= 0:
            return None
        share_now = sell_now / lot.sacks
        kg_now, kg_store = lot.quantity_kg * share_now, lot.quantity_kg * (1 - share_now)
        net_now, _ = self._cold_net(lot, kg_now, sell_now, prices, 0)
        net_store, _ = self._cold_net(lot, kg_store, store, prices, best["h"])
        cash_now = float(net_now.mean())
        interest, loan = self._interest(lot, best["h"], store, kg_store * lot.price_today, cash_now)
        if interest is None:
            return None
        total = net_now + net_store - interest
        return {"key": "sell_part", "title_en": f"Sell {sell_now} sacks now, store {store} until {best['month_en']}",
                "title_bn": f"এখন {to_bn_digits(str(sell_now))} বস্তা বেচুন, {to_bn_digits(str(store))} বস্তা {best['month_bn']} পর্যন্ত রাখুন",
                "sell_sacks_now": sell_now, "store_sacks": store, "sell_month_en": best["month_en"],
                "sell_month_bn": best["month_bn"], "months": best["h"],
                "cash_now": _round_tk(cash_now),
                "money_mean": _round_tk(float(total.mean())), "money_low": _round_tk(float(np.percentile(total, 10))),
                "money_high": _round_tk(float(np.percentile(total, 90))),
                "gain_vs_now": _round_tk(float(total.mean()) - now_value),
                "chance_beats_now": round(float((total > now_value).mean()), 2),
                "worst_case_vs_now": _round_tk(float(np.percentile(total, 10)) - now_value),
                "loan": loan}

    def _recommend(self, lot: FarmerLot, options: dict, now_value: float, H: int, k: float) -> dict:
        store, part = options.get("store"), options.get("sell_part")
        reasons = []
        small = max(500.0, 0.03 * now_value)
        if H == 0:
            reasons.append("The cold-storage season is over: sell now.")
            return {"key": "sell_now", **_titles(options["sell_now"]), "reasons": reasons}
        if not store:
            reasons.append("A loan against the stored sacks cannot cover the cash you need, "
                           "so storing everything is not possible.")
            if part and part["gain_vs_now"] > small and (part["chance_beats_now"] or 0) >= 0.55:
                reasons.append(f"Selling {part['sell_sacks_now']} sacks now covers the cash "
                               f"(৳{part['cash_now']:,}); storing the rest adds about ৳{part['gain_vs_now']:,} "
                               f"({round(part['chance_beats_now'] * 100)}% chance).")
                return {"key": "sell_part", **_titles(part), "reasons": reasons}
            return {"key": "sell_now", **_titles(options["sell_now"]), "reasons": reasons}

        gain, chance = store["gain_vs_now"], store["chance_beats_now"] or 0
        worst = store["worst_case_vs_now"]
        if gain <= small or chance < 0.55:
            if gain < 0:
                reasons.append(
                    f"Even at the best month ({store['sell_month_en']}), storing would leave you about "
                    f"৳{abs(gain):,} less than selling now, after rent and other costs.")
            else:
                reasons.append(
                    f"Storing until {store['sell_month_en']} would add only about ৳{gain:,} on average, "
                    f"with a {round(chance * 100)}% chance of beating today's sale: not worth the rent and the risk.")
            if k <= 0.3:
                reasons.append("A big crop is keeping prices from rising this season.")
            return {"key": "sell_now", **_titles(options["sell_now"]), "reasons": reasons}
        if chance >= 0.8 and worst >= -0.05 * now_value:
            reasons.append(
                f"Storing until {store['sell_month_en']} adds about ৳{gain:,} on average, "
                f"and beats selling now in {round(chance * 100)} of 100 price paths.")
            if worst >= 0:
                reasons.append(f"Even in a bad case (1 in 10) you still get ৳{worst:,} more than selling now.")
            else:
                reasons.append(f"In a bad case (1 in 10) you get ৳{abs(worst):,} less than selling now.")
            if store.get("loan"):
                loan = store["loan"]
                reasons.append(f"You need a loan of ৳{_round_tk(loan['amount']):,} against the stored sacks "
                               f"({_loan_name(loan['source'])}, about ৳{_round_tk(loan['interest']):,} interest).")
            return {"key": "store", **_titles(store), "reasons": reasons}
        rec = part or store
        reasons.append(
            f"Storing probably pays (about ৳{gain:,} more, {round(chance * 100)}% chance), "
            f"but in a bad case (1 in 10) storing everything would lose ৳{abs(min(worst, 0)):,}.")
        if part:
            reasons.append(f"Selling {part['sell_sacks_now']} sacks now gives ৳{part['cash_now']:,} in hand "
                           f"and limits the risk; the rest waits for the higher price.")
            if part.get("loan"):
                loan = part["loan"]
                reasons.append(f"The rest of the cash you need comes from a loan of ৳{_round_tk(loan['amount']):,} "
                               f"against the stored sacks ({_loan_name(loan['source'])}).")
        return {"key": rec["key"], **_titles(rec), "reasons": reasons}

    # ----------------------------------------------------------- extras
    def _cost_floor(self, lot: FarmerLot) -> Optional[dict]:
        if not lot.production_cost_per_kg:
            return None
        below = lot.price_today < lot.production_cost_per_kg
        return {"production_cost_per_kg": lot.production_cost_per_kg, "price_today": lot.price_today,
                "below_cost_today": below,
                "loss_per_kg_if_sold_now": round(max(0.0, lot.production_cost_per_kg - lot.price_today), 2)}

    def _notes(self, lot: FarmerLot, rows: list, best: Optional[dict], H: int) -> list[str]:
        t = lot.terms
        notes = []
        if lot.stored == "cold":
            notes.append(f"Rent (৳{t.rent_per_sack:,.0f} a sack) is owed either way, so holding on costs only "
                         f"weight loss and any interest. {H} month(s) of storage left.")
        else:
            notes.append(f"Rent is ৳{t.rent_per_sack:,.0f} a sack whether you store 1 month or {t.season_months}. "
                         f"Storing pays only if you hold until the price has risen enough.")
            early = [r for r in rows if r["h"] in (1, 2) and r["gain_vs_now"] < 0]
            if early and best and best["h"] > 2:
                notes.append(f"Selling stored potatoes after 1-2 months loses money on average; "
                             f"{best['month_en']} is the best month.")
        if H and H < 3 and lot.stored == "no":
            notes.append(f"Only {H} month(s) left before the cold storages empty in December: "
                         f"the full rent buys little time.")
        return notes


def _loan_name(source: str) -> str:
    return {"cold_storage": "cold-storage advance", "bank": "bank loan"}.get(source, source)


def _titles(option: dict) -> dict:
    return {"title_en": option["title_en"], "title_bn": option["title_bn"]}


def quick_plan(quantity_kg: float, price_today: float, **kwargs) -> dict:
    """A plan with default terms; kwargs go to FarmerLot."""
    terms = kwargs.pop("terms", None) or StorageTerms()
    return StoragePlanner().plan(FarmerLot(quantity_kg=quantity_kg, price_today=price_today, terms=terms, **kwargs))
