# Chicago Shore Temperature Checker

Fetches Lake Michigan water temperature at Chicago Shore from the [NOAA OMR report](https://forecast.weather.gov/product.php?issuedby=lot&product=omr&site=lot) and sends it to your phone via Telegram.

## Current Features (Phase 1 — Push Notifications)

- **Scrapes NOAA OMR report** for the Chicago Shore water temperature (°F)
- **Sends a Telegram message** with the current temp (notes "good time for the lake" when >50°F)
- **Supports multiple recipients** via comma-separated `TELEGRAM_CHAT_ID`
- **Retry logic** — up to 2 retries if NOAA is slow or down
- **Runs on a schedule** — GitHub Actions (daily at 8 AM CST), cron, or macOS launchd
- **`--get-chat-id` helper** — discovers your Telegram chat ID automatically

## Project Structure

```
chicago_shore_temperature/
├── check_shore_temp.py              # Phase 1: scheduled push (fetch temp + send Telegram)
├── bot.py                           # Phase 2: interactive bot (polling locally, webhook on Render)
├── render.yaml                      # Phase 3: Render deployment config
├── requirements.txt                 # Python dependencies
├── .env                             # Local secrets (not committed to git)
├── .github/
│   └── workflows/
│       └── check-shore-temp.yml     # GitHub Actions: daily schedule
└── README.md
```

## Quick Start

```bash
# 1. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure secrets
cp .env .env.backup   # keep a backup
# Edit .env: set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID (see Telegram setup below)

# 4. Run
python3 check_shore_temp.py
```

> **Note:** On macOS, use `python3` not `python`. The `python` command is not installed by default on newer macOS versions.

## Telegram Bot Setup

1. **Create a bot**
   - In Telegram, search for [@BotFather](https://t.me/BotFather).
   - Send `/newbot`, choose a name (e.g. "Chicago Shore Temp") and a username (e.g. `chicago_shore_temp_bot`).
   - Copy the **HTTP API token** — that's your `TELEGRAM_BOT_TOKEN`.

2. **Get your chat ID**
   - Start a chat with your new bot (tap "Start" or send any message).
   - Run: `python3 check_shore_temp.py --get-chat-id` — it prints your chat ID.
   - Put that number in `.env` as `TELEGRAM_CHAT_ID`.
   - For multiple users, use comma-separated IDs: `TELEGRAM_CHAT_ID=123456,789012`

3. **Configure `.env`**
   ```
   TELEGRAM_BOT_TOKEN=your_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   ```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Yes | Your Telegram chat ID (comma-separated for multiple) |
| `NOAA_OMR_URL` | No | Override NOAA OMR URL (default: Chicago LOT) |

## Run Daily (Automatically)

**Option 1: GitHub Actions (recommended — no machine to leave on)**

1. Push this repo to GitHub.
2. Go to repo **Settings → Secrets and variables → Actions → New repository secret**.
3. Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
4. The workflow runs daily at 8:00 AM CST (14:00 UTC). You can also trigger it manually from the **Actions** tab.

**Option 2: Cron (Linux/Mac)**

```bash
crontab -e
# Daily at 8:00 AM:
0 8 * * * cd /path/to/chicago_shore_temperature && .venv/bin/python3 check_shore_temp.py >> /tmp/shoretemp.log 2>&1
```

**Option 3: macOS launchd**

Create `~/Library/LaunchAgents/com.chicago.shoretemp.plist` with `ProgramArguments` pointing to your `.venv/bin/python3` and `check_shore_temp.py`, set `WorkingDirectory` to the project folder, and include your Telegram env vars in `EnvironmentVariables`. Load with:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.chicago.shoretemp.plist
```

## Phase 2 — Interactive Bot

The bot responds to Telegram commands in real time. It runs as a long-lived process using polling.

**Bot commands:**

| Command | What it does |
|---------|-------------|
| `/start` | Welcome message |
| `/temp` | Fetches and replies with the current water temperature |
| `/help` | Lists available commands |

**Run the interactive bot:**

```bash
source .venv/bin/activate
pip install -r requirements.txt   # installs python-telegram-bot
python3 bot.py                    # stays running — press Ctrl+C to stop
```

> **Both scripts can coexist.** `check_shore_temp.py` is for scheduled daily pushes (GitHub Actions / cron). `bot.py` is for on-demand interactive queries. They share the same `.env` and the same NOAA scraping function.

## Phase 3 — Deploy to Render (Free, No SSH)

Run your bot in the cloud for free — no server management, no SSH keys. Just connect GitHub and go.

> **How it works:** Locally, `bot.py` uses polling (asks Telegram for messages). On Render, it auto-switches to webhook mode (Telegram pushes messages to your Render URL). Same code, two modes.

### One-time setup

1. Go to [render.com](https://render.com) and sign up (free, no credit card).
2. Click **New → Web Service**.
3. Connect your GitHub account and select the `chicago_shore_temperature` repo.
4. Render auto-detects settings from `render.yaml`. Verify:
   - **Name:** `chicago-shore-bot`
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `python bot.py`
   - **Plan:** Free
5. Go to the **Environment** tab and add:
   - `TELEGRAM_BOT_TOKEN` = your bot token (from @BotFather)
6. Click **Create Web Service**. Render builds and deploys automatically.
7. Send `/temp` to your bot in Telegram — it works!

### Updating your bot

Push changes to GitHub → Render re-deploys automatically. That's it.

### Notes on the free tier

- Free instances sleep after 15 minutes of no messages.
- First message after sleeping takes ~30-50 seconds (Render wakes up). After that, replies are instant.
- For a weather bot used a few times a day, this is perfectly fine.

## Roadmap

- [x] **Phase 1** — Push notifications: daily scheduled temp → Telegram
- [x] **Phase 2** — Interactive bot: users can request temp on demand via Telegram commands
- [x] **Phase 3** — Deploy to Render (free, auto-deploys from GitHub)
