"""
Potato storage facts and default costs
======================================
Every number the storage engine uses by default, in one place, with where it
comes from. A farmer or helper can change any of them on the dashboard.

"Field notes" means the team's notes from Bogura cold storages (14 October 2026).
"Assumption" means a working figure to check in the field before the pilot.
"""

from dataclasses import dataclass, asdict

from config.settings import MAUND_TO_KG as MAUND_KG  # 1 maund (মণ) = 37.3242 kg

SACK_KG = 84.0              # field notes: the cold-storage sack holds 84 kg
SEASON_MONTHS = 9           # field notes: one rent covers up to 9 months
RENT_PER_SACK = 250.0       # field notes: ৳250 a sack for the season (some charge ৳300)
CS_ADVANCE_PER_SACK = (200.0, 300.0)   # field notes: cold storage lends ৳200-300 a sack, the sacks are the security
HOME_STORAGE_MAX_MONTHS = 3  # field notes: potato keeps up to about 3 months at home (onion 2-3)

# Calendar months in the potato year
HARVEST_MONTH = 3            # March: the main harvest and the lowest prices
LAST_SALE_MONTH = 12         # cold storages empty by December, before the new crop

MONTHS_EN = ["", "January", "February", "March", "April", "May", "June", "July",
             "August", "September", "October", "November", "December"]
MONTHS_BN = ["", "জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই",
             "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"]


@dataclass
class StorageTerms:
    """The costs of one farmer's storage choice. All taka figures are per sack unless named otherwise."""
    sack_kg: float = SACK_KG
    rent_per_sack: float = RENT_PER_SACK          # flat for the whole season
    season_months: int = SEASON_MONTHS
    sack_cost: float = 40.0                       # assumption: an empty sack
    carry_in_per_sack: float = 25.0               # assumption: field to cold storage
    load_unload_per_sack: float = 15.0            # assumption: labour in and out
    sell_from_store_per_sack: float = 30.0        # assumption: cold storage to buyer or haat
    sell_now_per_sack: float = 10.0               # assumption: selling at the field, trader collects
    monthly_weight_loss: float = 0.005            # assumption: 0.5% of weight a month in cold storage
    exit_sorting_loss: float = 0.02               # assumption: 2% sorted out as rotten when taken out
    home_monthly_loss: float = 0.04               # assumption: 4% a month in a home store
    home_max_months: int = HOME_STORAGE_MAX_MONTHS
    cs_advance_per_sack: float = 250.0            # field notes: ৳200-300
    cs_advance_rate_year: float = 0.14            # assumption: ask the cold storage
    bank_rate_year: float = 0.11                  # assumption: set by the bank

    def handling_per_sack(self) -> float:
        """One-off costs of putting a sack into cold storage (not the rent)."""
        return self.sack_cost + self.carry_in_per_sack + self.load_unload_per_sack

    def to_dict(self) -> dict:
        return asdict(self)


SOURCES = {
    "sack_kg": "Field notes, Bogura cold storages",
    "rent_per_sack": "Field notes: ৳250 a sack for up to 9 months, the same for 1 month or 9",
    "cs_advance_per_sack": "Field notes: cold storages lend ৳200-300 a sack against the stored sacks",
    "losses": "Assumptions until measured in the pilot",
    "costs": "Assumptions until collected from farmers in the pilot",
}


def maunds_to_kg(maunds: float) -> float:
    return maunds * MAUND_KG


def kg_to_sacks(kg: float, sack_kg: float = SACK_KG) -> float:
    return kg / sack_kg


def month_after(month: int, k: int) -> int:
    """The calendar month k months after `month` (1-12)."""
    return (month - 1 + k) % 12 + 1
