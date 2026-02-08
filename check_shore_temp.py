"""
Chicago Shore (Lake Michigan) temperature checker.
Fetches from NOAA OMR report and sends the temperature to Telegram once per run.
Run daily (e.g. via cron or GitHub Actions) to get a daily message.
"""
import logging
import os
import re
import time

import requests
from bs4 import BeautifulSoup

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

URL = os.getenv(
    "NOAA_OMR_URL",
    "https://forecast.weather.gov/product.php?issuedby=lot&product=omr&site=lot",
)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def fetch_chicago_shore_temp(max_retries: int = 2) -> int | None:
    """
    Fetches the Chicago Shore water temperature in Fahrenheit from the NOAA OMR report.
    Returns an integer temperature or None if not found.
    """
    headers = {"User-Agent": "ChicagoShoreTemp/1.0 (weather check)"}
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            response = requests.get(URL, timeout=10, headers=headers)
            response.raise_for_status()
            break
        except requests.RequestException as e:
            last_error = e
            log.warning("Fetch attempt %s failed: %s", attempt + 1, e)
            if attempt < max_retries:
                time.sleep(2)
    else:
        log.error("Failed to fetch weather data: %s", last_error)
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    text_content = soup.get_text()

    # NOAA format: "CHICAGO SHORE...........47." or "... 47 F"
    pattern = re.compile(r"CHICAGO SHORE[.\s]+(\d+)", re.IGNORECASE)
    match = pattern.search(text_content)
    if not match:
        pattern_f = re.compile(r"CHICAGO SHORE.*?(\d+)\s*F", re.IGNORECASE | re.DOTALL)
        match = pattern_f.search(text_content)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    return None


def send_telegram(text: str) -> bool:
    """Send a message via Telegram Bot API. Returns True on success."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("Telegram not configured (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID)")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if not r.ok:
            try:
                err = r.json()
                msg = err.get("description", r.text)
                log.error("Telegram API error: %s", msg)
            except Exception:
                log.error("Failed to send Telegram: %s %s", r.status_code, r.text)
            return False
        log.info("Telegram message sent")
        return True
    except requests.RequestException as e:
        log.error("Failed to send Telegram: %s", e)
        return False


def main() -> None:
    temp = fetch_chicago_shore_temp()
    if temp is None:
        log.error("Could not parse Chicago shore temperature")
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            send_telegram("Chicago Shore: could not fetch temperature.")
        return

    log.info("Chicago Shore temperature: %s°F", temp)

    # One daily message: temp + short note if it's nice for the lake
    if temp > 50:
        msg = f"Chicago Shore water temp: {temp}°F — good time for the lake."
    else:
        msg = f"Chicago Shore water temp: {temp}°F"
    send_telegram(msg)


if __name__ == "__main__":
    main()
