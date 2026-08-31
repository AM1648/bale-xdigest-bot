Bale X Bot

Forwards new tweets of configured X (Twitter) users to private Bale channels,daily at a fixed time (Asia/Tehran) or on demand via /trigger <channel_name>.
Setup

    Create a bot with @BotFather in Bale and add it as admin to your channels.
    cp .env.example .env — fill in BALE_TOKEN and RAPIDAPI_KEY (set PROXY_URL only if needed).
    Edit config.yaml.
    docker compose up -d --build

Admins must have started a private chat with the bot, otherwise it cannot DM them the daily report (the bot logs a warning and continues).
