import asyncio
import logging
import time
from typing import Dict, List

from models.config import Config
from models.channel import Channel
from models.tweet import Tweet
from clients.twitter_client import TwitterClient
from clients.bale_bot_client import BaleBotClient
from core.bot_state import BotState
from core.persian_text import PersianText

log = logging.getLogger("user_scraper")


class Busy(Exception):
    """Another trigger run is in progress."""


class UserScraper:
    def __init__(
        self,
        config: Config,
        twitter_client: TwitterClient,
        bale_client: BaleBotClient,
        state: BotState,
        persian: PersianText,
    ):
        self.cfg = config
        self.twitter = twitter_client
        self.bale = bale_client
        self.state = state
        self.persian = persian
        self._lock = asyncio.Lock()
        self._last_api_call = 0.0

    async def process_channels(self, channels: List[Channel]) -> Dict[str, Dict[str, str]]:
        if self._lock.locked():
            raise Busy
        async with self._lock:
            results = {}
            cache: Dict[str, List[Tweet | None] | Exception] = {}
            for ch in channels:
                results[ch.channel_name] = await self._process_channel(ch, cache)
            return results

    async def _process_channel(self, ch: Channel, cache: Dict[str, List[Tweet | None] | Exception]) -> Dict[str, str]:
        user_results = {}
        single_user = ch.is_single_user
        for user in ch.users:
            try:
                tweets = await self._fetch_user_tweets(user.user_id, cache)
                # Filter out already sent tweets (global dedupe)
                new_tweets = [
                    t for t in tweets
                    if t is not None and not self.state.is_tweet_sent(ch.channel_name, user.user_id, t.tweet_id)
                ]
                if new_tweets and not single_user:
                    count = self.persian.number(len(new_tweets))
                    await self.bale.send_message(ch.channel_id, f"📥 '{user.user_name}': {count} توییت جدید")
                # Send oldest first
                sent = 0
                sent_ids = []
                for t in reversed(new_tweets):
                    if await self.bale.send_tweet(ch.channel_id, t, user, show_header=not single_user):
                        sent += 1
                        sent_ids.append(t.tweet_id)
                if sent_ids:
                    self.state.add_sent_tweets(ch.channel_name, user.user_id, sent_ids)
                user_results[user.user_name] = f"{self.persian.number(sent)} تا"
            except Exception as e:
                log.error("failed to process user '%s': %s", user.user_name, e)
                for admin in self.cfg.admins:
                    try:
                        await self.bale.send_message(
                            admin,
                            f"⚠️ دریافت توییت‌های '{user.user_name}' ناموفق بود: {e}",
                        )
                    except Exception as e:
                        log.warning("could not DM admin %s: %s", admin, e)
                user_results[user.user_name] = "ناموفق"
        return user_results

    async def _fetch_user_tweets(
        self, user_id: str, cache: Dict[str, List[Tweet | None] | Exception]
    ) -> List[Tweet | None]:
        cached = cache.get(user_id)
        if cached is None:
            await self._throttle()
            try:
                cached = await self.twitter.fetch_user_tweets(user_id)
            except Exception as e:
                cached = e
            cache[user_id] = cached
        else:
            log.debug("reusing cached result for user %s", user_id)
        if isinstance(cached, Exception):
            raise cached
        return cached

    async def _throttle(self):
        wait = self.cfg.api_delay - (time.monotonic() - self._last_api_call)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_api_call = time.monotonic()