"""
DAM Price Scraper
==================
Scrapes daily potato market prices from the Department of Agricultural 
Marketing (DAM) Bangladesh portal: http://market.dam.gov.bd

Collects wholesale and retail prices for potatoes (Deshi & Holland varieties)
across target districts (Bogura, Rangpur, Dinajpur, Rajshahi, Dhaka).

Usage:
    python -m src.scrapers.dam_scraper          # One-time scrape
    python -m src.scrapers.dam_scraper --daemon  # Scheduled daily at 6 PM
"""

import re
import sys
import json
import time
import argparse
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import (
    DAM_BASE_URL, DAM_DAILY_PRICE_URL, DAM_COMMODITY_URL,
    DAM_TARGET_COMMODITIES, DAM_TARGET_DISTRICTS,
    RAW_DIR, PROCESSED_DIR
)

# Configure logging
logger.add(
    RAW_DIR / "scraper_logs" / "dam_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    level="INFO"
)


class DAMPriceScraper:
    """
    Scrapes potato prices from the DAM (Department of Agricultural Marketing)
    Bangladesh portal.
    
    The DAM portal provides:
    - Market Daily Price Report (all commodities, all markets)
    - Commodity Wise Report (filter by specific commodity)
    - Retail Price Comparative Report
    
    Since there's no public API, we use HTTP requests + BeautifulSoup
    to parse the HTML tables.
    """

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
        "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.collected_prices = []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30)
    )
    def _fetch_page(self, url: str, params: dict = None) -> BeautifulSoup:
        """Fetch a page with retry logic."""
        logger.info(f"Fetching: {url}")
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    def scrape_daily_prices(self, target_date: date = None) -> list[dict]:
        """
        Scrape the Market Daily Price Report for potato prices.
        
        Strategy:
        1. Navigate to the daily price report page
        2. Look for price table with commodity rows
        3. Filter for potato-related commodities
        4. Extract wholesale and retail price ranges
        
        Returns:
            List of price records as dicts
        """
        target_date = target_date or date.today()
        logger.info(f"📊 Scraping DAM prices for {target_date}")

        try:
            # Try to fetch the commodity-wise report for potatoes
            soup = self._fetch_page(
                DAM_COMMODITY_URL,
                params={
                    "commodity": "potato",
                    "date": target_date.strftime("%Y-%m-%d")
                }
            )
            records = self._parse_price_table(soup, target_date)

            if not records:
                # Fallback: try the daily price report page
                logger.warning("Commodity report empty, trying daily report...")
                soup = self._fetch_page(
                    DAM_DAILY_PRICE_URL,
                    params={"date": target_date.strftime("%Y-%m-%d")}
                )
                records = self._parse_price_table(soup, target_date)

            if records:
                logger.success(f"✅ Collected {len(records)} price records for {target_date}")
                self.collected_prices.extend(records)
            else:
                logger.warning(f"⚠️ No records found for {target_date}")

            return records

        except Exception as e:
            logger.error(f"❌ Scraping failed for {target_date}: {e}")
            return []

    def _parse_price_table(self, soup: BeautifulSoup, target_date: date) -> list[dict]:
        """
        Parse HTML tables from DAM portal to extract price data.
        
        DAM tables typically have columns like:
        | SL | Commodity | Unit | Wholesale (Min-Max) | Retail (Min-Max) | Market |
        
        Note: The actual table structure may vary. This parser handles
        multiple possible layouts.
        """
        records = []
        tables = soup.find_all("table")

        for table in tables:
            rows = table.find_all("tr")

            # Find header row to identify column positions
            header_row = None
            for row in rows:
                headers = row.find_all(["th", "td"])
                header_texts = [h.get_text(strip=True).lower() for h in headers]

                # Look for price-related headers
                if any(keyword in " ".join(header_texts) for keyword in
                       ["wholesale", "retail", "পাইকারি", "খুচরা", "price", "দাম"]):
                    header_row = header_texts
                    break

            if not header_row:
                continue

            # Identify column indices
            col_map = self._map_columns(header_row)
            if not col_map:
                continue

            # Parse data rows
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 3:
                    continue

                cell_texts = [c.get_text(strip=True) for c in cells]

                # Check if this row contains potato data
                commodity_text = self._safe_get(cell_texts, col_map.get("commodity", -1), "")
                if not self._is_potato(commodity_text):
                    continue

                # Extract market/district
                market = self._safe_get(cell_texts, col_map.get("market", -1), "")
                district = self._extract_district(market)

                # Filter for target districts
                if district and district not in DAM_TARGET_DISTRICTS:
                    continue

                # Extract prices
                record = {
                    "date": target_date.isoformat(),
                    "market_name": market,
                    "district": district or "Unknown",
                    "commodity": commodity_text,
                    "wholesale_min": self._parse_price(
                        self._safe_get(cell_texts, col_map.get("wholesale_min", -1), "")
                    ),
                    "wholesale_max": self._parse_price(
                        self._safe_get(cell_texts, col_map.get("wholesale_max", -1), "")
                    ),
                    "retail_min": self._parse_price(
                        self._safe_get(cell_texts, col_map.get("retail_min", -1), "")
                    ),
                    "retail_max": self._parse_price(
                        self._safe_get(cell_texts, col_map.get("retail_max", -1), "")
                    ),
                    "source": "DAM",
                    "scraped_at": datetime.utcnow().isoformat(),
                }

                # Compute averages
                if record["wholesale_min"] and record["wholesale_max"]:
                    record["wholesale_avg"] = (record["wholesale_min"] + record["wholesale_max"]) / 2
                if record["retail_min"] and record["retail_max"]:
                    record["retail_avg"] = (record["retail_min"] + record["retail_max"]) / 2

                records.append(record)

        return records

    def _map_columns(self, headers: list[str]) -> Optional[dict]:
        """Map header text to column indices."""
        col_map = {}

        for i, h in enumerate(headers):
            h_lower = h.lower()
            if any(k in h_lower for k in ["commodity", "পণ্য", "item", "product"]):
                col_map["commodity"] = i
            elif any(k in h_lower for k in ["market", "বাজার", "district"]):
                col_map["market"] = i
            elif "wholesale" in h_lower or "পাইকারি" in h_lower:
                if "min" in h_lower or col_map.get("wholesale_min") is None:
                    col_map["wholesale_min"] = i
                else:
                    col_map["wholesale_max"] = i
            elif "retail" in h_lower or "খুচরা" in h_lower:
                if "min" in h_lower or col_map.get("retail_min") is None:
                    col_map["retail_min"] = i
                else:
                    col_map["retail_max"] = i

        return col_map if "commodity" in col_map else None

    def _is_potato(self, text: str) -> bool:
        """Check if commodity text refers to potato."""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in [
            "potato", "আলু", "alu", "aloo",
            "deshi", "দেশী", "holland", "হল্যান্ড"
        ])

    def _extract_district(self, market_text: str) -> Optional[str]:
        """Extract district name from market text."""
        for district in DAM_TARGET_DISTRICTS:
            if district.lower() in market_text.lower():
                return district
        return None

    def _parse_price(self, text: str) -> Optional[float]:
        """Parse price value from text, handling various formats."""
        if not text:
            return None
        # Remove non-numeric characters except dots and dashes
        cleaned = re.sub(r"[^\d.\-]", "", text)
        try:
            value = float(cleaned)
            # Sanity check: potato prices should be between 1 and 200 Tk/kg
            if 1 <= value <= 200:
                return value
            return None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_get(lst: list, index: int, default=""):
        """Safely get list element by index."""
        if 0 <= index < len(lst):
            return lst[index]
        return default

    def save_raw(self, records: list[dict], target_date: date = None):
        """Save raw scraped data as JSON for audit trail."""
        target_date = target_date or date.today()
        output_dir = RAW_DIR / "dam_prices"
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = output_dir / f"dam_prices_{target_date.isoformat()}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        logger.info(f"💾 Saved {len(records)} records to {filename}")
        return filename

    def save_to_database(self, records: list[dict]):
        """Insert scraped records into the database."""
        try:
            from src.database import init_database, MarketPrice
            
            _, Session = init_database()
            session = Session()

            inserted = 0
            skipped = 0

            for record in records:
                # Check for duplicates
                existing = session.query(MarketPrice).filter_by(
                    date=date.fromisoformat(record["date"]),
                    market_name=record["market_name"],
                    commodity=record["commodity"]
                ).first()

                if existing:
                    skipped += 1
                    continue

                price = MarketPrice(
                    date=date.fromisoformat(record["date"]),
                    market_name=record["market_name"],
                    district=record["district"],
                    commodity=record["commodity"],
                    wholesale_min=record.get("wholesale_min"),
                    wholesale_max=record.get("wholesale_max"),
                    retail_min=record.get("retail_min"),
                    retail_max=record.get("retail_max"),
                    wholesale_avg=record.get("wholesale_avg"),
                    retail_avg=record.get("retail_avg"),
                    source=record.get("source", "DAM"),
                )
                session.add(price)
                inserted += 1

            session.commit()
            logger.success(f"💾 DB: {inserted} inserted, {skipped} skipped (duplicates)")
            session.close()

        except Exception as e:
            logger.error(f"❌ Database save failed: {e}")


class HDXPriceFetcher:
    """
    Fetches historical food commodity prices from the 
    World Food Programme (WFP) Humanitarian Data Exchange (HDX).
    
    URL: https://data.humdata.org → search "Bangladesh food prices"
    Format: CSV downloads with standard WFP schema.
    """

    HDX_DATASET_URL = "https://data.humdata.org/dataset/wfp-food-prices-for-bangladesh"

    def __init__(self):
        self.session = requests.Session()

    def fetch_wfp_prices(self) -> Optional[str]:
        """
        Download WFP food price CSV for Bangladesh.
        Returns path to downloaded file.
        """
        import pandas as pd
        
        logger.info("📥 Fetching WFP food prices from HDX...")

        try:
            # The HDX API provides dataset metadata
            api_url = "https://data.humdata.org/api/3/action/package_show"
            response = self.session.get(
                api_url,
                params={"id": "wfp-food-prices-for-bangladesh"},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                resources = data.get("result", {}).get("resources", [])

                for resource in resources:
                    if resource.get("format", "").upper() == "CSV":
                        csv_url = resource.get("url")
                        if csv_url:
                            return self._download_csv(csv_url)

            logger.warning("Could not find CSV resource in HDX API response")
            return None

        except Exception as e:
            logger.error(f"❌ HDX fetch failed: {e}")
            return None

    def _download_csv(self, url: str) -> str:
        """Download CSV and save to raw data directory."""
        output_dir = RAW_DIR / "hdx_prices"
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = output_dir / f"wfp_bangladesh_prices_{date.today().isoformat()}.csv"

        response = self.session.get(url, timeout=60)
        response.raise_for_status()

        with open(filename, "wb") as f:
            f.write(response.content)

        logger.success(f"✅ Downloaded WFP prices to {filename}")
        return str(filename)

    @staticmethod
    def filter_potato_prices(csv_path: str) -> "pd.DataFrame":
        """Filter WFP CSV for potato-related entries."""
        import pandas as pd
        
        df = pd.read_csv(csv_path)

        # WFP schema typically has: date, market, commodity, price, unit, currency
        potato_mask = df["commodity"].str.lower().str.contains(
            "potato|আলু", na=False
        )
        potato_df = df[potato_mask].copy()

        logger.info(f"📊 Filtered {len(potato_df)} potato price records from WFP data")
        return potato_df


# ============================================================
# CLI & Scheduling
# ============================================================

def run_daily_scrape():
    """Execute a single daily scrape."""
    scraper = DAMPriceScraper()
    records = scraper.scrape_daily_prices()

    if records:
        scraper.save_raw(records)
        scraper.save_to_database(records)
    else:
        logger.warning("No records collected today")

    return records


def run_historical_backfill(start_date: date, end_date: date):
    """Backfill historical data by scraping multiple dates."""
    scraper = DAMPriceScraper()
    current = start_date
    total_records = 0

    while current <= end_date:
        logger.info(f"📅 Backfilling {current}...")
        records = scraper.scrape_daily_prices(current)

        if records:
            scraper.save_raw(records, current)
            total_records += len(records)

        # Be polite — don't hammer the server
        time.sleep(2)
        current += timedelta(days=1)

    logger.success(f"✅ Backfill complete: {total_records} total records")


def run_daemon():
    """Run the scraper as a scheduled daemon (daily at 6 PM)."""
    import schedule

    logger.info("🔄 Starting DAM scraper daemon (daily at 18:00)")
    schedule.every().day.at("18:00").do(run_daily_scrape)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KrishiVault DAM Price Scraper")
    parser.add_argument("--daemon", action="store_true", help="Run as scheduled daemon")
    parser.add_argument("--backfill-days", type=int, help="Backfill N days of history")
    parser.add_argument("--date", type=str, help="Scrape specific date (YYYY-MM-DD)")

    args = parser.parse_args()

    if args.daemon:
        run_daemon()
    elif args.backfill_days:
        end = date.today()
        start = end - timedelta(days=args.backfill_days)
        run_historical_backfill(start, end)
    elif args.date:
        target = date.fromisoformat(args.date)
        scraper = DAMPriceScraper()
        records = scraper.scrape_daily_prices(target)
        if records:
            scraper.save_raw(records, target)
            for r in records:
                print(f"  {r['district']}: Tk {r.get('retail_avg', '?')}/kg")
    else:
        run_daily_scrape()
