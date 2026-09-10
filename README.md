# Bale X-Digest Bot

A Bale messenger bot that forwards new tweets from configured X (Twitter) accounts to Bale channels — automatically at scheduled times, or on demand via `/trigger`.

## Features

- 📅 **Scheduled runs** at configurable times of day (e.g., `08:00`, `14:00`, `20:00`)
- 🎯 **Manual trigger** by admins via `/trigger <channel_name>`
- 🔁 **Global deduplication** — each tweet is sent only once, tracked per channel/user in persistent state
- 🖼️ **Media support** — photos, videos, GIFs, and albums, with automatic fallback to text-only on failure
- 🇮🇷 **Persian output** — Jalali timestamps, Persian digits, and translated status messages
- 🔒 **Proxy support** (optional) for RapidAPI and media downloads
- 📊 **Daily reports** DM'd to admins after each scheduled run

## Requirements

- Python 3.13 (via Docker)
- A Bale bot token (from [@BotFather](https://ble.ir/BotFather) in Bale)
- A RapidAPI key for [twitter283](https://rapidapi.com/)

## Setup

1. **Create a bot** in Bale via @BotFather and add it as an **admin** to your target channels.
2. **Clone the repository** and prepare your config:
   ```bash
   cp .env.example .env
   cp config.example.yaml config.yaml
   ```
3. **Fill in `.env`**:
   ```env
   TZ=Asia/Tehran
   BALE_TOKEN=123456789:your-bot-token
   RAPIDAPI_KEY=your-rapidapi-key
   PROXY_URL=              # optional, e.g. socks5://host.docker.internal:20170
   ```
4. **Edit `config.yaml`** (see below).
5. **Run with Docker**:
   ```bash
   docker compose up -d --build
   ```

## Configuration (`config.yaml`)

```yaml
trigger_times:            # times of day (in TZ from env) to run automatically
  - "08:00"
  - "14:00"
  - "20:00"
api_delay_ms: 3000        # pause between RapidAPI calls
admins: [1234567890]      # Bale user IDs allowed to use /trigger; receive daily reports

channels:
  - channel_name: news
    channel_id: 1234567890
    users:
      - user_name: elonmusk    # X screen name (display only)
        user_id: "44196397"    # X numeric user ID
```
