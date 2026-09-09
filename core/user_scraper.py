import asyncio
import logging
import time
from typing import Dict, List

from models.config import Config
from models.channel import Channel
from models.user import User
from clients.twitter_client import TwitterClient
from clients.bale_bot_client import BaleBotClient
from core.bot_state import BotState

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
    ):
        self.cfg = config
        self.twitter = twitter_client
        self.bale = bale_client
        self.state = state
        self._lock = asyncio.Lock()
        self._last_api_call = 0.0

    async def process_channels(self, channels: List[Channel]) -> Dict[str, Dict[str, str]]:
        if self._lock.locked():
            raise Busy
        async with self._lock:
            results = {}
            for ch in channels:
                results[ch.channel_name] = await self._process_channel(ch)
            return results

    async def _process_channel(self, ch: Channel) -> Dict[str, str]:
        user_results = {}
        for user in ch.users:
            await self._throttle()
            try:
                tweets = await self.twitter.fetch_user_tweets(user.user_id)
                # Filter out already sent tweets (global dedupe)
                new_tweets = [
                    t for t in tweets
                    if t is not None and not self.state.is_tweet_sent(ch.channel_name, user.user_id, t.tweet_id)
                ]
                # Send oldest first
                sent = 0
                sent_ids = []
                for t in reversed(new_tweets):
                    if await self.bale.send_tweet(ch.channel_id, t, user):
                        sent += 1
                        sent_ids.append(t.tweet_id)
                if sent_ids:
                    self.state.add_sent_tweets(ch.channel_name, user.user_id, sent_ids)
                # Send status message about count
                status_msg = f"کاربر '{user.user_name}': {len(new_tweets)} توییت جدید"
                await self.bale.send_message(ch.channel_id, status_msg)
                user_results[user.user_name] = f"{sent} sent"
            except Exception as e:
                log.error("failed to process user %s: %s", user.user_name, e)
                await self.bale.send_message(ch.channel_id, f"Failed to fetch tweets for @{user.user_name}: {e}")
                user_results[user.user_name] = "FAILED"
        return user_results

    async def _throttle(self):
        wait = self.cfg.api_delay - (time.monotonic() - self._last_api_call)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_api_call = time.monotonic()