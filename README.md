# Taptap Send Automated Exchange Rate Monitor & Telegram Alert Bot

A lightweight Python background service that periodically fetches live currency exchange rates from Taptap Send. If the exchange rate crosses your specified threshold, it sends an instant push alert via a Telegram Bot.

## Features
- Connects directly to Taptap Send's backend API for accurate, real-time rates.
- Sends beautifully formatted Telegram push notifications.
- State management (`state.json`) prevents alert spamming.
- Supports both continuous local background execution and one-shot execution for cron jobs/GitHub Actions.
- Automatically saves state back to your GitHub repository when running via Actions to persist cooldowns between serverless runs.

## Setup Instructions

### 1. Telegram Bot Setup
1. Open the Telegram app and search for `@BotFather`.
2. Send `/newbot` and follow the prompts to create your bot.
3. Save the **Bot Token** provided by BotFather.
4. Open a chat with your new bot and send a message like `Hello`.
5. Visit `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates` in your browser. Look for `"chat":{"id":123456789}` in the JSON response. Save this **Chat ID**.

### 2. Local Execution
1. Clone this repository to your local machine.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your details:
   ```env
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   SOURCE_CURRENCY=GBP
   TARGET_COUNTRY=bangladesh
   TARGET_RATE_THRESHOLD=150.0
   CHECK_INTERVAL_SECONDS=900
   ALERT_COOLDOWN_HOURS=6
   ```
4. Run the script:
   - **Continuous loop:** `python monitor.py`
   - **Run once:** `python monitor.py --run-once`

### 3. Deploying via GitHub Actions (Free Serverless)
This repository includes a GitHub Actions workflow (`.github/workflows/rate_check.yml`) that runs the script every 30 minutes automatically.

1. Fork or push this code to your own private GitHub repository.
2. Go to your repository **Settings** > **Secrets and variables** > **Actions**.
3. Under **Repository secrets**, add:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
4. Under **Repository variables**, add:
   - `SOURCE_CURRENCY` (e.g., `GBP`)
   - `TARGET_COUNTRY` (e.g., `bangladesh` or `pakistan`)
   - `TARGET_RATE_THRESHOLD` (e.g., `150.0`)
   - `ALERT_COOLDOWN_HOURS` (e.g., `6.0` - minimum hours to wait before sending another alert if the rate stays above threshold)
5. Go to the **Actions** tab in your repository and enable workflows. You can manually trigger the "Taptap Send Rate Check" to test it.
6. The workflow will automatically commit any changes to `state.json` back to your repository using the `[skip ci]` flag to prevent infinite loops. Ensure your repository allows Actions to push commits.
