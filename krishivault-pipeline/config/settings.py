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
DAM_BASE_URL = "http://market.dam.gov.bd"
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

# === Potato Market Constants (Bangladesh-specific) ===
# These are research-backed defaults — update from field data
POTATO_SEASONAL_PATTERN = {
    # Month: typical price index (1.0 = average)
    1: 0.85,   # January — late harvest, prices still low
    2: 0.70,   # February — peak harvest, LOWEST prices
    3: 0.72,   # March — harvest glut continues
    4: 0.80,   # April — harvest ending, prices rising
    5: 0.90,   # May — transition to stored stock
    6: 1.00,   # June — average
    7: 1.10,   # July — stored stock period
    8: 1.15,   # August — rising
    9: 1.20,   # September — continued rise
    10: 1.25,  # October — approaching peak
    11: 1.35,  # November — near peak
    12: 1.40,  # December — HIGHEST prices (lean season)
}

# Cold storage defaults (Tk per kg per month)
# Government cap: Tk 6.00/kg, actual: Tk 6-7.50/kg
COLD_STORAGE_COST_PER_KG_MONTH = 6.00   # Use government cap as default
COLD_STORAGE_COST_RANGE = (5.75, 7.50)  # Min-max observed

# Spoilage rates (per month)
SPOILAGE_RATE_COLD_STORAGE = 0.05    # 5% per month in cold storage
SPOILAGE_RATE_HOME_STORAGE = 0.10    # 10% per month at home
SPOILAGE_RATE_TRANSPORT = 0.02       # 2% during transport

# Unit conversions
MAUND_TO_KG = 37.3242  # 1 maund = 37.3242 kg (Bengali maund)

# === Model Configuration ===
SARIMA_ORDER = (1, 1, 1)              # (p, d, q)
SARIMA_SEASONAL_ORDER = (1, 1, 1, 12)  # (P, D, Q, s) — monthly seasonality
LSTM_SEQUENCE_LENGTH = 30              # 30-day lookback window
LSTM_HIDDEN_SIZE = 64
LSTM_NUM_LAYERS = 2
LSTM_DROPOUT = 0.2
PREDICTION_HORIZONS = [7, 14, 30]      # Forecast days ahead

# === Voice / Telephony (Phase 4) ===
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")
WHISPER_MODEL_SIZE = "large-v3"  # Best for Bangla accuracy
STT_SAMPLE_RATE = 16000  # 16kHz required by Whisper

# === API Server ===
API_HOST = "0.0.0.0"
API_PORT = 8000
