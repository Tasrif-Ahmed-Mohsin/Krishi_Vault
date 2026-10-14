"""
KrishiVault Database Models
============================
SQLAlchemy ORM models for storing potato price data, weather data,
farmer profiles, buyer networks, and decision logs.
"""

import sys
from pathlib import Path
from datetime import datetime, date
from sqlalchemy import (
    create_engine, Column, Integer, Float, String, Date, DateTime,
    Boolean, Text, ForeignKey, Enum, UniqueConstraint, Index
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import enum

sys.path.insert(0, str(Path(__file__).parent.parent))

Base = declarative_base()


# ============================================================
# ENUMS
# ============================================================

class DecisionType(enum.Enum):
    SELL_NOW = "sell_now"
    SELL_PART = "sell_part"
    STORE_REVIEW = "store_review"
    GROUP_SELL = "group_sell"


class StorageType(enum.Enum):
    COLD_STORAGE = "cold_storage"
    HOME_STORAGE = "home_storage"
    NO_STORAGE = "no_storage"


# ============================================================
# PRICE DATA
# ============================================================

class MarketPrice(Base):
    """
    Daily potato market prices scraped from DAM portal.
    One row per market per commodity per day.
    """
    __tablename__ = "market_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    market_name = Column(String(100), nullable=False, index=True)
    district = Column(String(50), nullable=False, index=True)
    division = Column(String(50), nullable=True)
    commodity = Column(String(100), nullable=False)  # "আলু (দেশী)", "আলু (হল্যান্ড)"

    # Prices in Tk per kg
    wholesale_min = Column(Float, nullable=True)
    wholesale_max = Column(Float, nullable=True)
    retail_min = Column(Float, nullable=True)
    retail_max = Column(Float, nullable=True)

    # Computed fields
    wholesale_avg = Column(Float, nullable=True)
    retail_avg = Column(Float, nullable=True)

    # Metadata
    source = Column(String(50), default="DAM")  # DAM, HDX, manual
    scraped_at = Column(DateTime, default=datetime.utcnow)
    is_validated = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint("date", "market_name", "commodity", name="uq_daily_market_commodity"),
        Index("ix_price_lookup", "district", "commodity", "date"),
    )

    def __repr__(self):
        return f"<MarketPrice {self.date} {self.market_name} {self.commodity}: Tk {self.retail_avg}/kg>"


class PricePrediction(Base):
    """
    Model-generated price predictions stored for each forecast run.
    """
    __tablename__ = "price_predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)
    target_date = Column(Date, nullable=False, index=True)
    district = Column(String(50), nullable=False)
    commodity = Column(String(100), nullable=False)

    # Predictions
    predicted_price = Column(Float, nullable=False)       # Tk per kg
    confidence_lower = Column(Float, nullable=True)        # Lower bound
    confidence_upper = Column(Float, nullable=True)        # Upper bound
    confidence_pct = Column(Float, nullable=True)          # Confidence %

    # Model info
    model_name = Column(String(50), nullable=False)        # "sarima", "lstm", "ensemble"
    model_version = Column(String(20), nullable=True)
    horizon_days = Column(Integer, nullable=False)          # 7, 14, or 30

    # Evaluation (filled in after actual price is known)
    actual_price = Column(Float, nullable=True)
    error_pct = Column(Float, nullable=True)

    __table_args__ = (
        Index("ix_prediction_lookup", "district", "commodity", "target_date"),
    )


# ============================================================
# WEATHER DATA
# ============================================================

class WeatherData(Base):
    """
    Daily weather observations for target districts.
    Sourced from BMD AIS or OpenWeather API.
    """
    __tablename__ = "weather_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    district = Column(String(50), nullable=False, index=True)
    station_name = Column(String(100), nullable=True)

    # Temperature (°C)
    temp_min = Column(Float, nullable=True)
    temp_max = Column(Float, nullable=True)
    temp_avg = Column(Float, nullable=True)

    # Precipitation & Humidity
    rainfall_mm = Column(Float, nullable=True)
    humidity_pct = Column(Float, nullable=True)

    # Wind
    wind_speed_kmh = Column(Float, nullable=True)

    # Metadata
    source = Column(String(50), default="openweather")  # bmd, openweather
    fetched_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("date", "district", name="uq_daily_weather"),
        Index("ix_weather_lookup", "district", "date"),
    )


# ============================================================
# COLD STORAGE
# ============================================================

class ColdStorage(Base):
    """
    Cold storage facilities in target districts.
    Tracks capacity, current utilization, and actual rates.
    """
    __tablename__ = "cold_storages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    district = Column(String(50), nullable=False, index=True)
    upazila = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)

    # Capacity
    total_capacity_tonnes = Column(Float, nullable=True)
    current_utilization_pct = Column(Float, nullable=True)
    available_tonnes = Column(Float, nullable=True)

    # Pricing (Tk per kg)
    official_rate_per_kg = Column(Float, nullable=True)      # Government cap
    actual_rate_per_kg = Column(Float, nullable=True)         # What they actually charge
    rate_last_updated = Column(Date, nullable=True)

    # Contact
    phone = Column(String(20), nullable=True)
    owner_name = Column(String(100), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    last_verified = Column(Date, nullable=True)

    def __repr__(self):
        return f"<ColdStorage {self.name} ({self.district}): Tk {self.actual_rate_per_kg}/kg>"


# ============================================================
# FARMER PROFILES
# ============================================================

class Farmer(Base):
    """
    Registered farmer profiles for the KrishiVault service.
    """
    __tablename__ = "farmers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String(15), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=True)
    district = Column(String(50), nullable=False, index=True)
    upazila = Column(String(100), nullable=True)
    village = Column(String(100), nullable=True)

    # Farm profile
    total_land_bigha = Column(Float, nullable=True)  # 1 bigha ≈ 0.134 hectares
    primary_crop = Column(String(50), default="potato")
    has_cold_storage_access = Column(Boolean, default=False)
    nearest_cold_storage_id = Column(Integer, ForeignKey("cold_storages.id"), nullable=True)

    # Registration
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_call_at = Column(DateTime, nullable=True)
    total_calls = Column(Integer, default=0)
    preferred_language = Column(String(10), default="bn")  # bn = Bangla

    # Relationships
    nearest_cold_storage = relationship("ColdStorage", backref="nearby_farmers")
    decisions = relationship("DecisionLog", back_populates="farmer")

    def __repr__(self):
        return f"<Farmer {self.name} ({self.phone_number}) @ {self.district}>"


# ============================================================
# BUYER NETWORK
# ============================================================

class Buyer(Base):
    """
    Registered buyers (arhatdars, wholesalers, cooperatives, companies).
    """
    __tablename__ = "buyers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    buyer_type = Column(String(50), nullable=False)  # arhatdar, wholesaler, cooperative, company
    district = Column(String(50), nullable=False, index=True)
    upazila = Column(String(100), nullable=True)
    phone = Column(String(15), nullable=True)

    # Purchase requirements
    min_quantity_kg = Column(Float, nullable=True)     # Minimum order (e.g., 50 maunds)
    max_quantity_kg = Column(Float, nullable=True)
    current_offer_per_kg = Column(Float, nullable=True)  # Current buying price
    offer_last_updated = Column(Date, nullable=True)
    payment_days = Column(Integer, nullable=True)         # Days to payment after delivery

    # Quality requirements
    accepts_mixed_quality = Column(Boolean, default=True)
    preferred_variety = Column(String(50), nullable=True)  # deshi, holland

    is_active = Column(Boolean, default=True)
    last_verified = Column(Date, nullable=True)

    def __repr__(self):
        return f"<Buyer {self.name} ({self.buyer_type}): Tk {self.current_offer_per_kg}/kg>"


# ============================================================
# DECISION LOGS
# ============================================================

class DecisionLog(Base):
    """
    Every decision recommendation KrishiVault makes is logged
    for analysis, model improvement, and audit.
    """
    __tablename__ = "decision_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Farmer's input
    crop = Column(String(50), default="potato")
    quantity_kg = Column(Float, nullable=False)
    cash_needed_tk = Column(Float, nullable=True)
    deadline_days = Column(Integer, nullable=True)
    storage_type = Column(String(30), nullable=True)
    current_offer_per_kg = Column(Float, nullable=True)

    # Market context at decision time
    market_price_per_kg = Column(Float, nullable=True)
    predicted_7d_price = Column(Float, nullable=True)
    predicted_14d_price = Column(Float, nullable=True)
    predicted_30d_price = Column(Float, nullable=True)
    storage_cost_per_kg = Column(Float, nullable=True)
    break_even_price = Column(Float, nullable=True)

    # Decision output
    recommendation = Column(String(20), nullable=False)  # DecisionType value
    recommendation_detail = Column(Text, nullable=True)   # Full explanation
    sell_quantity_kg = Column(Float, nullable=True)        # How much to sell now
    store_quantity_kg = Column(Float, nullable=True)       # How much to store
    expected_proceeds_tk = Column(Float, nullable=True)

    # Follow-up
    farmer_accepted = Column(Boolean, nullable=True)
    actual_outcome_tk = Column(Float, nullable=True)  # What they actually earned
    follow_up_date = Column(Date, nullable=True)

    # Relationships
    farmer = relationship("Farmer", back_populates="decisions")

    def __repr__(self):
        return f"<Decision {self.id}: {self.recommendation} for Farmer {self.farmer_id}>"


# ============================================================
# GROUP SELLING
# ============================================================

class GroupSellPool(Base):
    """
    Group selling pools — collections of nearby farmers 
    pooling harvest to meet buyer minimums.
    """
    __tablename__ = "group_sell_pools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    district = Column(String(50), nullable=False, index=True)
    upazila = Column(String(100), nullable=True)

    # Pool status
    target_quantity_kg = Column(Float, nullable=False)    # Buyer's minimum
    current_quantity_kg = Column(Float, default=0.0)
    target_buyer_id = Column(Integer, ForeignKey("buyers.id"), nullable=True)
    target_price_per_kg = Column(Float, nullable=True)

    # Status
    status = Column(String(20), default="open")  # open, filled, completed, cancelled
    deadline = Column(Date, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Results
    actual_price_per_kg = Column(Float, nullable=True)
    total_proceeds_tk = Column(Float, nullable=True)

    # Relationships
    target_buyer = relationship("Buyer")
    members = relationship("GroupSellMember", back_populates="pool")


class GroupSellMember(Base):
    """Individual farmer contribution to a group sell pool."""
    __tablename__ = "group_sell_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pool_id = Column(Integer, ForeignKey("group_sell_pools.id"), nullable=False)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    quantity_kg = Column(Float, nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)

    # Payout
    proceeds_tk = Column(Float, nullable=True)
    paid_out = Column(Boolean, default=False)

    # Relationships
    pool = relationship("GroupSellPool", back_populates="members")
    farmer = relationship("Farmer")

    __table_args__ = (
        UniqueConstraint("pool_id", "farmer_id", name="uq_pool_farmer"),
    )


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_database(database_url: str = None):
    """Create all tables and return engine + session factory."""
    from config.settings import DATABASE_URL as default_url
    
    url = database_url or default_url
    engine = create_engine(url, echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session


if __name__ == "__main__":
    # Quick init for development
    engine, Session = init_database("sqlite:///./data/krishivault.db")
    print(f"✅ Database initialized with {len(Base.metadata.tables)} tables:")
    for table_name in Base.metadata.tables:
        print(f"   📋 {table_name}")
