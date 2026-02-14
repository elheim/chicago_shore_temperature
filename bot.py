"""
Interactive Telegram bot for Chicago Shore water temperature.
Users send /temp and get the current Lake Michigan temperature back.

Runs in two modes (auto-detected):
  - LOCAL:  python3 bot.py          → polling mode (for development)
  - CLOUD:  Render sets PORT env    → webhook mode (for deployment)
"""

import logging
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Reuse the NOAA scraper from Phase 1
from check_shore_temp import fetch_chicago_shore_temp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "").strip()
PORT = int(os.getenv("PORT", "8443"))


# ─── Command Handlers ────────────────────────────────────────────────────────


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — welcome message."""
    await update.message.reply_text(
        "Hey! I'm the Chicago Shore Temperature Bot.\n\n"
        "Send /temp to get the current Lake Michigan water temperature.\n"
        "Send /help to see all commands."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help — list available commands."""
    await update.message.reply_text(
        "Available commands:\n\n"
        "/temp  — Get the current Chicago Shore water temperature\n"
        "/help  — Show this help message"
    )


async def temp_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /temp — fetch and reply with current water temperature."""
    await update.message.reply_text("Fetching temperature...")

    temp = fetch_chicago_shore_temp()

    if temp is None:
        await update.message.reply_text(
            "Sorry, I couldn't fetch the temperature right now. "
            "NOAA might be down or the report isn't available. Try again later."
        )
        return

    if temp > 50:
        msg = f"Chicago Shore water temp: {temp}°F — good time for the lake!"
    else:
        msg = f"Chicago Shore water temp: {temp}°F — bit chilly for swimming."

    await update.message.reply_text(msg)


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle any non-command message."""
    await update.message.reply_text(
        "Send /temp to get the Chicago Shore water temperature."
    )


async def post_init(application: Application) -> None:
    """Set the bot's command menu in Telegram (the '/' button)."""
    await application.bot.set_my_commands([
        BotCommand("temp", "Get current water temperature"),
        BotCommand("help", "Show available commands"),
    ])


# ─── Main ────────────────────────────────────────────────────────────────────


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        log.error(
            "TELEGRAM_BOT_TOKEN is not set. "
            "Add it to your .env file (get it from @BotFather)."
        )
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Register handlers (order matters — commands first, fallback last)
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("temp", temp_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))

    # Auto-detect mode: webhook on Render, polling locally
    if RENDER_EXTERNAL_URL:
        # ── Cloud mode (Render) ──────────────────────────────────────────
        webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
        log.info("Starting in WEBHOOK mode → %s", webhook_url)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="/webhook",
            webhook_url=webhook_url,
            allowed_updates=Update.ALL_TYPES,
        )
    else:
        # ── Local mode (polling) ─────────────────────────────────────────
        log.info("Starting in POLLING mode... (press Ctrl+C to stop)")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
