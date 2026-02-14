"""
Chicago Shore (Lake Michigan) temperature checker.
Fetches from NOAA OMR report and sends the temperature to Telegram once per run.
Run daily (e.g. via cron or GitHub Actions) to get a daily message.

FIXED: Now properly sends to multiple chat IDs!
"""
import argparse
import logging
import os
import re
import sys
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

from typing import Optional


def fetch_chicago_shore_temp(max_retries: int = 2) -> Optional[int]:
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


def get_telegram_chat_id() -> bool:
    """
    Call Telegram getUpdates and print your chat ID.
    Message your bot first (e.g. send /start or 'hi'), then run: python check_shore_temp.py --get-chat-id
    """
    if not TELEGRAM_BOT_TOKEN:
        log.error("Set TELEGRAM_BOT_TOKEN in .env (from @BotFather)")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        log.error("Failed to call Telegram: %s", e)
        return False
    except ValueError as e:
        log.error("Invalid response from Telegram: %s", e)
        return False
    if not data.get("ok"):
        log.error("Telegram API error: %s", data.get("description", "unknown"))
        return False
    results = data.get("result", [])
    if not results:
        print(
            "\nNo messages found. Do this:\n"
            "  1. Open Telegram and find your bot (the one you created with @BotFather).\n"
            "  2. Tap Start or send any message (e.g. 'hi').\n"
            "  3. Run this command again: python check_shore_temp.py --get-chat-id\n"
        )
        return False
    seen: set[int] = set()
    for u in results:
        chat = u.get("message", {}).get("chat", {})
        cid = chat.get("id")
        if cid is not None and cid not in seen:
            seen.add(cid)
            title = chat.get("title") or chat.get("username") or chat.get("first_name") or "chat"
            print(f"  Chat ID: {cid}  ({title})")
    if seen:
        print("\nPut one of these in your .env as TELEGRAM_CHAT_ID=")
        print("For multiple users, use comma-separated: TELEGRAM_CHAT_ID=123456,789012")
    return True


def send_telegram(text: str) -> bool:
    """
    Send a message via Telegram Bot API to one or more chat IDs.
    Supports comma-separated TELEGRAM_CHAT_ID values.
    Returns True if at least one message was sent successfully.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("Telegram not configured (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID)")
        return False

    # Parse comma-separated chat IDs
    chat_ids = [cid.strip() for cid in TELEGRAM_CHAT_ID.split(",") if cid.strip()]
    
    if not chat_ids:
        log.warning("No valid chat IDs found in TELEGRAM_CHAT_ID")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    success_count = 0
    
    # CRITICAL FIX: Loop through ALL chat IDs
    for chat_id in chat_ids:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        try:
            r = requests.post(url, json=payload, timeout=10)
            if not r.ok:
                try:
                    err = r.json()
                    msg = err.get("description", r.text)
                    log.error("Telegram API error for chat %s: %s", chat_id, msg)
                except Exception:
                    log.error("Failed to send to chat %s: %s %s", chat_id, r.status_code, r.text)
            else:
                log.info("Telegram message sent to chat %s", chat_id)
                success_count += 1
        except requests.RequestException as e:
            log.error("Failed to send Telegram to chat %s: %s", chat_id, e)
    
    # Return True if at least one message succeeded
    return success_count > 0


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
    parser = argparse.ArgumentParser(description="Chicago Shore (Lake Michigan) temperature → Telegram")
    parser.add_argument(
        "--get-chat-id",
        action="store_true",
        help="Print your Telegram chat ID (message your bot first, then run this)",
    )
    args = parser.parse_args()
    if args.get_chat_id:
        ok = get_telegram_chat_id()
        sys.exit(0 if ok else 1)
    main()
