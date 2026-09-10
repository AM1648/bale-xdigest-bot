import os
import logging

import httpx
from dotenv import load_dotenv
from balethon import Client
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from models.config import Config
from clients.twitter_client import TwitterClient
from clients.bale_bot_client import BaleBotClient
from clients.media_downloader import MediaDownloader
from core.tweet_renderer import TweetRenderer
from core.bot_state import BotState
from core.persian_text import PersianText
from core.user_scraper import UserScraper, Busy

log = logging.getLogger("bale-x-bot")


class BaleXBot:
    def __init__(self, config_path: str = "config.yaml", env_path: str = ".env"):
        load_dotenv(env_path)
        self._ensure_env()
        self.config = Config.from_yaml(config_path, env_path)
        self.bot = Client(os.environ["BALE_TOKEN"])
        self.http = self._create_http_client()
        self.state = BotState()
        self.persian = PersianText(self.config.timezone)
        self.twitter_client = TwitterClient(self.http, os.environ["RAPIDAPI_KEY"])
        self.media_downloader = MediaDownloader(self.http)
        self.renderer = TweetRenderer(self.persian)
        self.bale_client = BaleBotClient(self.bot, self.media_downloader, self.renderer)
        self.scraper = UserScraper(self.config, self.twitter_client, self.bale_client, self.state, self.persian)
        self.scheduler = AsyncIOScheduler()
        self._register_handlers()

    def _ensure_env(self):
        required = ("BALE_TOKEN", "RAPIDAPI_KEY")
        missing = [v for v in required if not os.environ.get(v)]
        if missing:
            raise SystemExit(f"Missing environment variables: {', '.join(missing)}")

    def _create_http_client(self) -> httpx.AsyncClient:
        proxy = os.environ.get("PROXY_URL")
        return httpx.AsyncClient(proxy=proxy or None, timeout=30, follow_redirects=True)

    def _register_handlers(self):
        @self.bot.on_command(name="trigger")
        async def trigger(channel_name=None, *, message):
            if message.author.id not in self.config.admins:
                return await message.reply("شما ادمین نیستید.")
            if channel_name is None:
                return await message.reply("📝 روش استفاده: /trigger <نام کانال>")
            channel = self.config.channel(channel_name)
            if channel is None:
                return await message.reply(f"❓ کانال ناشناخته: '{channel_name}'")
            try:
                report = await self.scraper.process_channels([channel])
            except Busy:
                return await message.reply("⏳ یک اجرا در حال انجام است؛ بعداً تلاش کنید")
            await message.reply(self._format_report(report))

        @self.bot.on_command(name="chat-id")
        async def get_id(*, message):
            await message.reply(f"شناسهٔ گفتگو: {message.chat.id}")

        @self.bot.on_error()
        async def log_error(*, event=None, error=None):
            log.error("Unhandled exception: %r", error or event)

        @self.bot.on_initialize()
        async def start_scheduler():
            for t in self.config.trigger_times:
                self.scheduler.add_job(
                    self._scheduled_run,
                    "cron",
                    hour=t.hour,
                    minute=t.minute,
                    second=t.second,
                    timezone=self.config.timezone,
                    misfire_grace_time=300,
                )
            self.scheduler.start()
            log.info(
                "bot started; scheduled runs at %s (%s)",
                ", ".join(f"{t:%H:%M}" for t in self.config.trigger_times),
                self.config.timezone,
            )

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
        header = f"📊 گزارش اجرا — {self.persian.format_datetime(self.config.now())}"
        lines = [header]
        for channel_name, users in reports.items():
            lines.append("")
            lines.append(f"🔊 {channel_name}")
            for user_name, result in users.items():
                lines.append(f" • '{user_name}': {result}")
        return "\n".join(lines)

    def run(self):
        self.bot.run()