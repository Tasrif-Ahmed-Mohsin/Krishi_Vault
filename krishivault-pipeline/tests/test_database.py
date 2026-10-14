"""
Database and Pipeline Integration Tests
========================================
Tests SQLite database models, querying records, and checking seed data integrity.
"""

import pytest
from src.database import init_database, MarketPrice, WeatherData, ColdStorage, Buyer, Farmer
from config.settings import DATABASE_URL

@pytest.fixture(scope="module")
def db_session():
    engine, Session = init_database(DATABASE_URL)
    session = Session()
    yield session
    session.close()

def test_market_prices_loaded(db_session):
    count = db_session.query(MarketPrice).count()
    assert count > 0, "MarketPrice table should contain records from ingestion"

    # Query latest record for Bogura or any district
    sample = db_session.query(MarketPrice).first()
    assert sample.retail_avg > 0
    assert sample.date is not None

def test_weather_data_loaded(db_session):
    count = db_session.query(WeatherData).count()
    assert count > 0, "WeatherData table should contain ingested rows"
    sample = db_session.query(WeatherData).first()
    assert sample.district in ["Bogura", "Rangpur", "Dinajpur", "Rajshahi", "Dhaka"]

def test_cold_storage_facilities(db_session):
    storages = db_session.query(ColdStorage).all()
    assert len(storages) >= 5
    for s in storages:
        assert s.actual_rate_per_kg >= 5.0
        assert s.total_capacity_tonnes > 0

def test_buyer_network(db_session):
    buyers = db_session.query(Buyer).all()
    assert len(buyers) >= 5
    for b in buyers:
        assert b.current_offer_per_kg > 0
        assert b.min_quantity_kg > 0

def test_farmer_profiles(db_session):
    farmers = db_session.query(Farmer).all()
    assert len(farmers) >= 2
    abdur_rahim = db_session.query(Farmer).filter_by(phone_number="+8801711998877").first()
    assert abdur_rahim is not None
    assert abdur_rahim.district == "Bogura"
