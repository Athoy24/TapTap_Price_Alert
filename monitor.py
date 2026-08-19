import os
import sys
import time
import json
import logging
import argparse
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

def get_env_var(key, default):
    val = os.getenv(key, "").strip()
    return val if val else default

SOURCE_CURRENCY = get_env_var("SOURCE_CURRENCY", "GBP").upper()
TARGET_COUNTRY = get_env_var("TARGET_COUNTRY", "bangladesh").lower()
TARGET_RATE_THRESHOLD = float(get_env_var("TARGET_RATE_THRESHOLD", "150.0"))
CHECK_INTERVAL_SECONDS = int(get_env_var("CHECK_INTERVAL_SECONDS", "900"))

STATE_FILE = "state.json"
API_URL = "https://api.taptapsend.com/api/fxRates"

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
    return {}

def save_state(state):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        logger.error(f"Failed to save state: {e}")

def fetch_taptap_rate():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Appian-Version": "web/2022-05-03.0",
        "X-Device-Id": "web",
        "X-Device-Model": "web"
    }
    try:
        response = requests.get(API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        for country in data.get('availableCountries', []):
            if country.get('currency', '').upper() == SOURCE_CURRENCY:
                for corridor in country.get('corridors', []):
                    if corridor.get('countryDisplayName', '').lower() == TARGET_COUNTRY:
                        return float(corridor.get('fxRate')), corridor.get('currency')
        
        logger.error(f"Could not find corridor for {SOURCE_CURRENCY} -> {TARGET_COUNTRY}")
        return None, None
    except Exception as e:
        logger.error(f"Error fetching rates from Taptap Send: {e}")
        return None, None

def send_telegram_alert(rate, target_currency, previous_rate=None):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("Telegram Bot Token or Chat ID is missing. Cannot send alert.")
        return False

    chat_ids = [cid.strip() for cid in str(TELEGRAM_CHAT_ID).split(',')]
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    if previous_rate is not None:
        increase = rate - previous_rate
        rate_info = (
            f"**New Rate:** 1 {SOURCE_CURRENCY} = {rate:.2f} {target_currency}\n"
            f"**Previous Rate:** {previous_rate:.2f} {target_currency}\n"
            f"**Increase:** +{increase:.2f} {target_currency}\n"
        )
    else:
        rate_info = f"**New Rate:** 1 {SOURCE_CURRENCY} = {rate:.2f} {target_currency}\n"

    message = (
        f"🚨 **Taptap Send Exchange Rate Alert** 🚨\n\n"
        f"The exchange rate is above your threshold and has increased!\n\n"
        f"{rate_info}\n"
        f"**Target Threshold:** {TARGET_RATE_THRESHOLD:.2f}\n"
        f"**Country:** {TARGET_COUNTRY.capitalize()}\n\n"
        f"💸 [Send money now](https://www.taptapsend.com/)"
    )
    
    success_count = 0
    for chat_id in chat_ids:
        if not chat_id:
            continue
            
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Telegram alert sent successfully to {chat_id}.")
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send Telegram alert to {chat_id}: {e}")

    return success_count > 0

def check_rate_and_alert():
    logger.info(f"Checking Taptap Send exchange rate for {SOURCE_CURRENCY} to {TARGET_COUNTRY}...")
    rate, target_currency = fetch_taptap_rate()
    
    if rate is None:
        return
    
    logger.info(f"Current rate: 1 {SOURCE_CURRENCY} = {rate:.2f} {target_currency} (Threshold: {TARGET_RATE_THRESHOLD})")
    
    state = load_state()
    last_rate = state.get("last_rate")
    
    send_alert = False
    
    if rate >= TARGET_RATE_THRESHOLD:
        if last_rate is None:
            send_alert = True
            logger.info("First time crossing threshold. Sending alert.")
        elif rate > last_rate:
            send_alert = True
            logger.info(f"Rate increased from {last_rate} to {rate}. Sending alert.")
        else:
            logger.info(f"Rate ({rate}) is above threshold but not greater than last recorded rate ({last_rate}). No alert.")
    else:
        logger.info("Rate is below threshold. No alert needed.")

    # Update state
    now = datetime.now()
    state["last_rate"] = rate
    state["target_country"] = TARGET_COUNTRY
    
    if send_alert:
        success = send_telegram_alert(rate, target_currency, previous_rate=last_rate)
        if success:
            state["last_alert_time"] = now.isoformat()
            
    # Always persist state to track the latest rate
    save_state(state)

def main():
    parser = argparse.ArgumentParser(description="Taptap Send Exchange Rate Monitor")
    parser.add_argument("--run-once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    if args.run_once:
        check_rate_and_alert()
    else:
        logger.info(f"Starting monitor in continuous loop mode. Polling every {CHECK_INTERVAL_SECONDS} seconds.")
        while True:
            check_rate_and_alert()
            time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
