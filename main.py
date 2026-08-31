import asyncio
import logging
import os
import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from balethon import Client
from dotenv import load_dotenv

from config import TZ_NAME, load_config
from runner import Busy, Runner, format_report
from twitter import make_client

log = logging.getLogger("main")

def require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Environment variable {name} is required")
    return value


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("balethon.network.connection").setLevel(logging.WARNING)
    load_dotenv()

    cfg = load_config()
    bot = Client(require("BALE_TOKEN"))
    http = make_client(os.environ.get("PROXY_URL"))
    runner = Runner(bot, cfg, http, require("RAPIDAPI_KEY"))

    @bot.on_command(name="trigger")
    async def trigger(channel_name=None, *, message):
        log.info("/trigger triggered")
        if message.author.id not in cfg.admins:
            return await message.reply("⛔ Not authorized")
        if channel_name is None:
            return await message.reply("Usage: /trigger <channel_name>")
        channel = cfg.channel(channel_name)
        if channel is None:
            return await message.reply(f"Unknown channel: {channel_name}")
        try:
            report = await runner.run([channel])
        except Busy:
            return await message.reply("⏳ A run is already in progress, try again later")
        await message.reply(format_report(report))

    @bot.on_error()
    async def log_error(*, event=None, error=None):
        log.error("Unh exc: %r", error or event)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        runner.scheduled_run, "cron",
        hour=cfg.trigger.hour, minute=cfg.trigger.minute, second=cfg.trigger.second,
        timezone=TZ_NAME, misfire_grace_time=300,
    )

    @bot.on_initialize()
    async def st_sched():
        scheduler.start()
        log.info("bot started; daily trigger at %s (%s)", cfg.trigger, TZ_NAME)

    bot.run()


if __name__ == "__main__":
    main()
