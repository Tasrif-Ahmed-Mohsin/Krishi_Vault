"""
Weather Data Fetcher
=====================
Fetches daily weather data for KrishiVault target districts.

Primary source: BMD AIS (Bangladesh Meteorological Department)
Fallback: OpenWeather API

Weather data is critical for:
- Price prediction (temperature → spoilage, rainfall → transport/harvest)
- Dynamic monitoring alerts (storm warnings, heat waves)
- Storage decision support
"""

import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import (
    BMD_AIS_URL, OPENWEATHER_API_KEY, OPENWEATHER_BASE_URL,
    BOGURA_LAT, BOGURA_LON, RAW_DIR
)


# District coordinates for weather fetching
DISTRICT_COORDINATES = {
    "Bogura": {"lat": 24.8465, "lon": 89.3773},
    "Rangpur": {"lat": 25.7439, "lon": 89.2752},
    "Dinajpur": {"lat": 25.6279, "lon": 88.6332},
    "Rajshahi": {"lat": 24.3636, "lon": 88.6241},
    "Dhaka": {"lat": 23.8103, "lon": 90.4125},
}


class WeatherFetcher:
    """
    Multi-source weather data fetcher.
    
    Tries BMD AIS first (official Bangladesh Met data),
    falls back to OpenWeather API if BMD is unavailable.
    """

    def __init__(self):
        self.session = requests.Session()

    def fetch_all_districts(self, target_date: date = None) -> list[dict]:
        """Fetch weather for all target districts."""
        target_date = target_date or date.today()
        results = []

        for district, coords in DISTRICT_COORDINATES.items():
            record = self.fetch_weather(district, coords, target_date)
            if record:
                results.append(record)

        logger.info(f"🌤️ Collected weather for {len(results)}/{len(DISTRICT_COORDINATES)} districts")
        return results

    def fetch_weather(
        self, district: str, coords: dict, target_date: date = None
    ) -> Optional[dict]:
        """
        Fetch weather for a single district.
        Tries BMD first, falls back to OpenWeather.
        """
        target_date = target_date or date.today()

        # Try BMD AIS first
        record = self._fetch_bmd(district, coords, target_date)
        if record:
            return record

        # Fallback to OpenWeather
        if OPENWEATHER_API_KEY:
            record = self._fetch_openweather(district, coords, target_date)
            if record:
                return record

        logger.warning(f"⚠️ No weather data for {district} on {target_date}")
        return None

    def _fetch_bmd(
        self, district: str, coords: dict, target_date: date
    ) -> Optional[dict]:
        """
        Fetch from BMD Automated Integrated System.
        
        BMD AIS (ais.bmd.gov.bd) has weather stations across Bangladesh.
        The API structure may require specific station IDs.
        """
        try:
            # BMD AIS endpoint (may need adjustment based on actual API docs)
            url = f"{BMD_AIS_URL}/api/weather"
            response = self.session.get(
                url,
                params={
                    "lat": coords["lat"],
                    "lon": coords["lon"],
                    "date": target_date.isoformat()
                },
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "date": target_date.isoformat(),
                    "district": district,
                    "station_name": data.get("station", ""),
                    "temp_min": data.get("temp_min"),
                    "temp_max": data.get("temp_max"),
                    "temp_avg": data.get("temp_avg"),
                    "rainfall_mm": data.get("rainfall", 0),
                    "humidity_pct": data.get("humidity"),
                    "wind_speed_kmh": data.get("wind_speed"),
                    "source": "bmd",
                    "fetched_at": datetime.utcnow().isoformat(),
                }
        except Exception as e:
            logger.debug(f"BMD fetch failed for {district}: {e}")

        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _fetch_openweather(
        self, district: str, coords: dict, target_date: date
    ) -> Optional[dict]:
        """
        Fetch from OpenWeather API (reliable fallback).
        
        Uses the 'weather' endpoint for current data or 
        'onecall/timemachine' for historical data.
        """
        try:
            is_today = target_date == date.today()

            if is_today:
                # Current weather
                url = f"{OPENWEATHER_BASE_URL}/weather"
                params = {
                    "lat": coords["lat"],
                    "lon": coords["lon"],
                    "appid": OPENWEATHER_API_KEY,
                    "units": "metric"
                }
            else:
                # Historical weather (requires One Call API 3.0)
                timestamp = int(datetime.combine(target_date, datetime.min.time()).timestamp())
                url = f"{OPENWEATHER_BASE_URL}/onecall/timemachine"
                params = {
                    "lat": coords["lat"],
                    "lon": coords["lon"],
                    "dt": timestamp,
                    "appid": OPENWEATHER_API_KEY,
                    "units": "metric"
                }

            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            if is_today:
                return {
                    "date": target_date.isoformat(),
                    "district": district,
                    "station_name": f"OpenWeather ({district})",
                    "temp_min": data["main"].get("temp_min"),
                    "temp_max": data["main"].get("temp_max"),
                    "temp_avg": data["main"].get("temp"),
                    "rainfall_mm": data.get("rain", {}).get("1h", 0) * 24,  # Estimate daily
                    "humidity_pct": data["main"].get("humidity"),
                    "wind_speed_kmh": (data["wind"].get("speed", 0) * 3.6),  # m/s → km/h
                    "source": "openweather",
                    "fetched_at": datetime.utcnow().isoformat(),
                }
            else:
                # Historical data structure differs
                hourly = data.get("data", [])
                if hourly:
                    temps = [h.get("temp", 0) for h in hourly]
                    humidity = [h.get("humidity", 0) for h in hourly]
                    rain = sum(h.get("rain", {}).get("1h", 0) for h in hourly)

                    return {
                        "date": target_date.isoformat(),
                        "district": district,
                        "station_name": f"OpenWeather Historical ({district})",
                        "temp_min": min(temps) if temps else None,
                        "temp_max": max(temps) if temps else None,
                        "temp_avg": sum(temps) / len(temps) if temps else None,
                        "rainfall_mm": rain,
                        "humidity_pct": sum(humidity) / len(humidity) if humidity else None,
                        "wind_speed_kmh": None,
                        "source": "openweather",
                        "fetched_at": datetime.utcnow().isoformat(),
                    }

        except Exception as e:
            logger.error(f"OpenWeather fetch failed for {district}: {e}")

        return None

    def save_to_database(self, records: list[dict]):
        """Insert weather records into the database."""
        try:
            from src.database import init_database, WeatherData

            _, Session = init_database()
            session = Session()
            inserted = 0

            for record in records:
                existing = session.query(WeatherData).filter_by(
                    date=date.fromisoformat(record["date"]),
                    district=record["district"]
                ).first()

                if existing:
                    continue

                weather = WeatherData(
                    date=date.fromisoformat(record["date"]),
                    district=record["district"],
                    station_name=record.get("station_name"),
                    temp_min=record.get("temp_min"),
                    temp_max=record.get("temp_max"),
                    temp_avg=record.get("temp_avg"),
                    rainfall_mm=record.get("rainfall_mm"),
                    humidity_pct=record.get("humidity_pct"),
                    wind_speed_kmh=record.get("wind_speed_kmh"),
                    source=record.get("source", "unknown"),
                )
                session.add(weather)
                inserted += 1

            session.commit()
            logger.success(f"💾 Saved {inserted} weather records to database")
            session.close()

        except Exception as e:
            logger.error(f"❌ Weather DB save failed: {e}")


if __name__ == "__main__":
    fetcher = WeatherFetcher()
    records = fetcher.fetch_all_districts()

    for r in records:
        print(f"  {r['district']}: {r.get('temp_avg', '?')}°C, "
              f"Rain: {r.get('rainfall_mm', 0)}mm, "
              f"Humidity: {r.get('humidity_pct', '?')}%")
