import asyncio
import logging
import time
from datetime import datetime, timedelta

from config import Channel, Config, TZ, User
import post
import twitter

log = logging.getLogger("runner")


class Busy(Exception):
    """Another trigger run is in progress."""


def prev_occurrence(cfg: Config, now: datetime) -> datetime:
    """Most recent past occurrence of the daily trigger time."""
    t = cfg.trigger
    at = now.replace(hour=t.hour, minute=t.minute, second=t.second, microsecond=0)
    return at if at <= now - timedelta(minutes=5) else at - timedelta(days=1)


def format_report(reports: dict[str, dict[str, str]]) -> str:
    lines = [f"📊 Trigger report — {datetime.now(TZ):%Y-%m-%d %H:%M}"]
    for name, users in reports.items():
        lines.append(f"{name}: " + (" | ".join(f"@{u} {r}" for u, r in users.items()) or "-"))
    return "\n".join(lines)


class Runner:
    def __init__(self, bot, cfg: Config, http, api_key: str):
        self.bot, self.cfg, self.http, self.api_key = bot, cfg, http, api_key
        self._lock = asyncio.Lock()
        self._last_trigger: dict[str, datetime] = {}
        self._last_call = 0.0

    async def run(self, channels: list[Channel]) -> dict[str, dict[str, str]]:
        if self._lock.locked():
            raise Busy
        async with self._lock:
            return {ch.channel_name: await self._run_channel(ch) for ch in channels}

    async def scheduled_run(self):
        try:
            reports = await self.run(self.cfg.channels)
        except Busy:
            log.warning("scheduled run skipped: another run is in progress")
            return
        for admin in self.cfg.admins:
            try:
                await self.bot.send_message(admin, format_report(reports))
            except Exception as e:
                log.warning("could not DM admin %s: %s", admin, e)

    async def _run_channel(self, ch: Channel) -> dict[str, str]:
        now = datetime.now(TZ)
        window = self._last_trigger.get(ch.channel_name, prev_occurrence(self.cfg, now))
        self._last_trigger[ch.channel_name] = now
        return {u.user_name: await self._run_user(ch, u, window) for u in ch.users}

    async def _run_user(self, ch: Channel, user: User, window: datetime) -> str:
        await self._throttle()
        try:
            tweets = await twitter.fetch_tweets(self.http, self.api_key, user.user_id)
        except Exception as e:
            await self._send(ch.channel_id, f"Failed to fetch tweets for @{user.user_name}: {e}")
            return "FAILED"
        kept, seen = [], set()
        for t in reversed(tweets):  # oldest first; dedupe (pinned tweets repeat in the timeline)
            if t is None:
                kept.append(t)
            elif t.tweet_id not in seen:
                seen.add(t.tweet_id)
                if t.created_at >= window:
                    kept.append(t)
        await self._send(ch.channel_id, f"کاربر '{user.user_name}': {len(kept)} توییت جدید")
        sent = 0
        for t in kept:
            if t is None:
                sent += await self._send(ch.channel_id, f"⚠️ A tweet from @{user.user_name} could not be displayed")
            else:
                try:
                    await post.send_tweet(self.bot, ch.channel_id, t, user, self.http)
                    sent += 1
                except Exception as e:
                    log.error("failed to send tweet %s: %s", t.link, e)
        return f"{sent} sent"

    async def _throttle(self):
        wait = self.cfg.api_delay - (time.monotonic() - self._last_call)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_call = time.monotonic()

    async def _send(self, chat_id: int, text: str) -> bool:
        try:
            await self.bot.send_message(chat_id, text)
            return True
        except Exception as e:
            log.error("could not send message to %s: %s", chat_id, e)
            import traceback
            traceback.print_exc()
            return False
