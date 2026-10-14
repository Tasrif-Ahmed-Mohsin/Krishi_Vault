"""
KrishiVault Pipeline Configuration
===================================
Central configuration for all pipeline components.
Loads sensitive values from environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# === Paths ===
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MODEL_DIR = BASE_DIR / "models_saved"

# === Database ===
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./data/krishivault.db"  # SQLite for dev, PostgreSQL for prod
)

# === DAM (Department of Agricultural Marketing) ===
DAM_BASE_URL = "https://market.dam.gov.bd"  # moved; the downloader still needs fixing
DAM_DAILY_PRICE_URL = f"{DAM_BASE_URL}/market-daily-price-report"
DAM_COMMODITY_URL = f"{DAM_BASE_URL}/commodity-wise-report"
DAM_SCRAPE_HOUR = 18  # 6 PM — after market closes
DAM_TARGET_COMMODITIES = [
    "আলু (দেশী)",      # Potato (Local/Deshi)
    "আলু (হল্যান্ড)",    # Potato (Holland)
    "Potato",
]
DAM_TARGET_DISTRICTS = [
    "Bogura", "Bogra",
    "Rangpur",
    "Dinajpur",
    "Rajshahi",
    "Dhaka",
]

# === Weather ===
# BMD AIS (Bangladesh Meteorological Department)
BMD_AIS_URL = "http://ais.bmd.gov.bd:48080"

# OpenWeather as fallback
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"

# Bogura coordinates (pilot area)
BOGURA_LAT = 24.8465
BOGURA_LON = 89.3773

# === Units ===
# Cold-storage sack size, rent and cost defaults live in src/engine/facts.py (with their sources).
MAUND_TO_KG = 37.3242  # 1 maund = 37.3242 kg (Bengali maund)

# === API Server ===
API_HOST = "0.0.0.0"
API_PORT = 8000
