import os
import logging
import yaml
from datetime import time
from zoneinfo import ZoneInfo
from pathlib import Path

import httpx
from dotenv import load_dotenv
from balethon import Client
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from models.config import Config, TZ_NAME
from models.channel import Channel
from models.user import User
from clients.twitter_client import TwitterClient
from clients.bale_bot_client import BaleBotClient
from clients.media_downloader import MediaDownloader
from core.tweet_renderer import TweetRenderer
from core.bot_state import BotState
from core.user_scraper import UserScraper, Busy

log = logging.getLogger("bale-x-bot")

class BaleXBot:
    def __init__(self, config_path: str = "config.yaml", env_path: str = ".env"):
        load_dotenv(env_path)
        self._ensure_env()
        self.config = self.load_config(config_path)
        self.bot = Client(os.environ["BALE_TOKEN"])
        self.http = self._create_http_client()
        self.state = BotState()
        self.twitter_client = TwitterClient(self.http, os.environ["RAPIDAPI_KEY"])
        self.media_downloader = MediaDownloader(self.http)
        self.renderer = TweetRenderer()
        self.bale_client = BaleBotClient(self.bot, self.media_downloader, self.renderer)
        self.scraper = UserScraper(self.config, self.twitter_client, self.bale_client, self.state)
        self.scheduler = AsyncIOScheduler()
        self._register_handlers()

    def _ensure_env(self):
        required = ("BALE_TOKEN", "RAPIDAPI_KEY")
        missing = [v for v in required if not os.environ.get(v)]
        if missing:
            raise SystemExit(f"Missing environment variables: {', '.join(missing)}")

    def load_config(self, path: str = "config.yaml") -> Config:
        raw = yaml.safe_load(Path(path).read_text()) or {}
        try:
            cfg = Config(
                trigger=time.fromisoformat(str(raw["trigger"])),
                api_delay=raw.get("api_delay_ms", 0) / 1000,
                admins=[int(a) for a in raw["admins"]],
                channels=[
                    Channel(
                        channel_name=c["channel_name"],
                        channel_id=int(c["channel_id"]),
                        users=[User(u["user_name"], str(u["user_id"])) for u in c["users"]],
                    )
                    for c in raw["channels"]
                ],
            )
        except (KeyError, TypeError, ValueError) as e:
            raise SystemExit(f"invalid config.yaml: {e}") from None
        if not cfg.channels:
            raise SystemExit("invalid config.yaml: no channels configured")
        return cfg

    def _create_http_client(self) -> httpx.AsyncClient:
        proxy = os.environ.get("PROXY_URL")
        return httpx.AsyncClient(proxy=proxy or None, timeout=30, follow_redirects=True)

    def _register_handlers(self):
        @self.bot.on_command(name="trigger")
        async def trigger(channel_name=None, *, message):
            log.info("/trigger triggered")
            if message.author.id not in self.config.admins:
                return await message.reply("⛔ Not authorized")
            if channel_name is None:
                return await message.reply("Usage: /trigger <channel_name>")
            channel = self.config.get_channel_by_name(channel_name)
            if channel is None:
                return await message.reply(f"Unknown channel: {channel_name}")
            try:
                report = await self.scraper.process_channels([channel])
            except Busy:
                return await message.reply("⏳ A run is already in progress, try again later")
            await message.reply(self._format_report(report))

        @self.bot.on_error()
        async def log_error(*, event=None, error=None):
            log.error("Unhandled exception: %r", error or event)

        @self.bot.on_initialize()
        async def start_scheduler():
            self.scheduler.add_job(
                self._scheduled_run,
                "cron",
                hour=self.config.trigger.hour,
                minute=self.config.trigger.minute,
                second=self.config.trigger.second,
                timezone=TZ_NAME,
                misfire_grace_time=300,
            )
            self.scheduler.start()
            log.info("bot started; daily trigger at %s (%s)", self.config.trigger, TZ_NAME)

    async def _scheduled_run(self):
        try:
            reports = await self.scraper.process_channels(self.config.channels)
        except Busy:
            log.warning("scheduled run skipped: another run is in progress")
            return
        report_text = self._format_report(reports)
        for admin in self.config.admins:
            try:
                await self.bot.send_message(admin, report_text)
            except Exception as e:
                log.warning("could not DM admin %s: %s", admin, e)

    def _format_report(self, reports: dict[str, dict[str, str]]) -> str:
        from datetime import datetime
        lines = [f"📊 Trigger report — {datetime.now(ZoneInfo(TZ_NAME)):%Y-%m-%d %H:%M}"]
        for name, users in reports.items():
            lines.append(f"{name}: " + (" | ".join(f"@{u} {r}" for u, r in users.items()) or "-"))
        return "\n".join(lines)

    def run(self):
        self.bot.run()
