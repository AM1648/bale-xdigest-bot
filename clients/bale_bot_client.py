import logging
from balethon import Client
from balethon.objects import InputMediaPhoto
from models.tweet import Tweet
from models.user import User
from core.tweet_renderer import TweetRenderer
from clients.media_downloader import MediaDownloader, MediaError

log = logging.getLogger("bale-bot-client")

class BaleBotClient:
    def __init__(self, bot: Client, media_downloader: MediaDownloader, renderer: TweetRenderer):
        self.bot = bot
        self.media = media_downloader
        self.renderer = renderer

    async def send_tweet(self, chat_id: int, tweet: Tweet, user: User) -> bool:
        """Send one tweet; on any media failure fall back to a text-only message."""
        text = self.renderer.render(tweet, user)
        try:
            if tweet.video_url:
                video = await self.media.download_video(tweet.video_url)
                await self.bot.send_video(chat_id, video, caption=text)
                if tweet.image_urls:
                    await self._send_photos(chat_id, tweet.image_urls)
            elif tweet.gif_url:
                gif = await self.media.download_gif(tweet.gif_url)
                await self.bot.send_animation(chat_id, gif, caption=text)
                if tweet.image_urls:
                    await self._send_photos(chat_id, tweet.image_urls)
            elif tweet.image_urls:
                await self._send_photos(chat_id, tweet.image_urls, caption=text)
            else:
                await self.bot.send_message(chat_id, text)
            return True
        except MediaError as e:
            log.warning("media download failed for %s, falling back to text: %s", tweet.link, e)
            await self.bot.send_message(chat_id, self.renderer.render(tweet, user, media_failed=True))
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

    async def _send_photos(self, chat_id: int, urls: list[str], caption: str | None = None):
        photos = [await self.media.download_photo(url) for url in urls]
        if len(photos) == 1:
            await self.bot.send_photo(chat_id, photos[0], caption=caption)
        else:
            media = [InputMediaPhoto(p, caption=caption if i == 0 else None) for i, p in enumerate(photos)]
            await self.bot.send_media_group(chat_id, media)
