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
    user = update.effective_user
    name = user.first_name if user else "there"
    await update.message.reply_text(
        f"Hey {name}! \U0001F30A\n\n"
        "I check the Lake Michigan water temperature "
        "at Chicago Shore in real time.\n\n"
        "\U0001F321 /temp — current water temperature\n"
        "\u2753 /help — see all commands\n\n"
        "Data source: NOAA Open Lake Michigan Report"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help — list available commands."""
    await update.message.reply_text(
        "\U0001F4CB Commands\n\n"
        "\U0001F321 /temp — current water temperature\n"
        "\u2753 /help — this message\n\n"
        "Tip: tap the \u2295 button to see the command menu."
    )


async def temp_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /temp — fetch and reply with current water temperature."""
    await update.message.reply_text("\U0001F50D Checking NOAA...")

    temp = fetch_chicago_shore_temp()

    if temp is None:
        await update.message.reply_text(
            "\u26A0\uFE0F Couldn't fetch the temperature right now.\n"
            "NOAA may be updating the report. Try again in a few minutes."
        )
        return

    # Convert to Celsius for the international crowd
    temp_c = round((temp - 32) * 5 / 9)

    # Pick a vibe based on the temp
    if temp >= 70:
        icon = "\U0001F525"
        vibe = "Perfect beach day!"
    elif temp >= 60:
        icon = "\u2600\uFE0F"
        vibe = "Great for the lake."
    elif temp >= 50:
        icon = "\U0001F324\uFE0F"
        vibe = "A bit cool — wetsuits recommended."
    elif temp >= 40:
        icon = "\U0001F976"
        vibe = "Cold. For brave swimmers only."
    else:
        icon = "\u2744\uFE0F"
        vibe = "Way too cold. Stay on the shore."

    msg = (
        f"{icon} Chicago Shore\n\n"
        f"\U0001F321 {temp}°F / {temp_c}°C\n"
        f"\U0001F30A {vibe}\n\n"
        f"\U0001F4CD Lake Michigan — NOAA OMR Report"
    )

    await update.message.reply_text(msg)


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle any non-command message."""
    await update.message.reply_text(
        "Tap /temp to get the current water temperature \U0001F30A"
    )


async def post_init(application: Application) -> None:
    """Set the bot's command menu in Telegram (the '/' button)."""
    await application.bot.set_my_commands([
        BotCommand("temp", "\U0001F321 Current water temperature"),
        BotCommand("help", "\u2753 Show available commands"),
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
