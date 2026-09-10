import logging
from balethon import Client
from balethon.objects import InputMediaPhoto
from models.tweet import Tweet
from models.user import User
from clients.media_downloader import MediaDownloader, MediaError
from core.tweet_renderer import TweetRenderer

log = logging.getLogger("bale-bot-client")


class BaleBotClient:
    MESSAGE_LIMIT = 4096
    CAPTION_LIMIT = 1000
    MORE_SUFFIX = " (👇)"

    def __init__(self, bot: Client, media_downloader: MediaDownloader, renderer: TweetRenderer):
        self.bot = bot
        self.media = media_downloader
        self.renderer = renderer

    # ---------- public API ----------

    async def send_tweet(self, chat_id: int, tweet: Tweet, user: User) -> bool:
        """Send one tweet; on any media failure fall back to a text-only message."""
        text = self.renderer.render(tweet, user)
        try:
            if tweet.video_url:
                video = await self.media.download_video(tweet.video_url)
                chunks = self._split_text(text, self.CAPTION_LIMIT)
                await self.bot.send_video(chat_id, video, caption=chunks[0])
                await self._send_chunks(chat_id, chunks[1:])
                if tweet.image_urls:
                    await self._send_photos(chat_id, tweet.image_urls)
            elif tweet.gif_url:
                gif = await self.media.download_gif(tweet.gif_url)
                chunks = self._split_text(text, self.CAPTION_LIMIT)
                await self.bot.send_animation(chat_id, gif, caption=chunks[0])
                await self._send_chunks(chat_id, chunks[1:])
                if tweet.image_urls:
                    await self._send_photos(chat_id, tweet.image_urls)
            elif tweet.image_urls:
                await self._send_photos(chat_id, tweet.image_urls, caption=text)
            else:
                await self._send_long_message(chat_id, text)
            return True
        except MediaError as e:
            log.warning("media download failed for %s, falling back to text: %s", tweet.link, e)
            fallback = self.renderer.render(tweet, user, media_failed=True)
            await self._send_long_message(chat_id, fallback)
            return True
        except Exception as e:
            log.error("unexpected error sending tweet %s: %s", tweet.link, e)
            return False

    async def send_message(self, chat_id: int, text: str) -> bool:
        try:
            await self.bot.send_message(chat_id, text)
            return True
        except Exception as e:
            log.error("could not send message to %s: %s", chat_id, e)
            return False

    # ---------- internal helpers ----------

    async def _send_long_message(self, chat_id: int, text: str):
        """Send text, splitting it into multiple messages if it exceeds MESSAGE_LIMIT."""
        chunks = self._split_text(text, self.MESSAGE_LIMIT)
        await self._send_chunks(chat_id, chunks)

    async def _send_chunks(self, chat_id: int, chunks: list[str]):
        for chunk in chunks:
            await self.bot.send_message(chat_id, chunk)

    async def _send_photos(self, chat_id: int, urls: list[str], caption: str | None = None):
        photos = [await self.media.download_photo(url) for url in urls]
        chunks = self._split_text(caption, self.CAPTION_LIMIT) if caption else [None]
        if len(photos) == 1:
            await self.bot.send_photo(chat_id, photos[0], caption=chunks[0])
        else:
            media = [InputMediaPhoto(p, caption=chunks[0] if i == 0 else None) for i, p in enumerate(photos)]
            await self.bot.send_media_group(chat_id, media)
        await self._send_chunks(chat_id, chunks[1:])

    def _split_text(self, text: str, limit: int) -> list[str]:
        """
        Split text into chunks that fit in `limit`.
        Each non-final chunk gets MORE_SUFFIX appended.
        Splits at word boundaries; hard-splits a single word that is too long.
        """
        if len(text) <= limit:
            return [text]

        suffix = self.MORE_SUFFIX
        budget = limit - len(suffix)
        chunks: list[str] = []
        remaining = text

        while remaining:
            if len(remaining) <= limit:
                chunks.append(remaining)
                break
            split_at = remaining.rfind(' ', 0, budget + 1)
            if split_at <= 0:
                split_at = budget  # single word longer than budget → hard split
            chunk = remaining[:split_at].rstrip()
            chunks.append(chunk + suffix)
            remaining = remaining[split_at:].lstrip()

        return chunks