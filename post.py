import logging
from io import BytesIO

from balethon.objects import InputMediaPhoto

from Tweet import Tweet
from config import User
from render import render

log = logging.getLogger("bale-x-bot")

PHOTO_CAP = 10 * 1024 * 1024   # Bale upload limits
VIDEO_CAP = 50 * 1024 * 1024


class MediaError(Exception):
    """Downloaded media exceeds Bale upload limits."""


async def send_tweet(bot, chat_id: int, tweet: Tweet, user: User, http):
    """Send one tweet; on any media failure fall back to a text-only message."""
    text = render(tweet, user)
    try:
        if tweet.video_url:
            await bot.send_video(chat_id, await _download(http, tweet.video_url, VIDEO_CAP), caption=text)
            if tweet.image_urls:
                await _send_photos(bot, chat_id, tweet.image_urls, http)
        elif tweet.gif_url:
            await bot.send_animation(chat_id, await _download(http, tweet.gif_url, VIDEO_CAP), caption=text)
            if tweet.image_urls:
                await _send_photos(bot, chat_id, tweet.image_urls, http)
        elif tweet.image_urls:
            await _send_photos(bot, chat_id, tweet.image_urls, http, caption=text)
        else:
            await bot.send_message(chat_id, text)
    except Exception as e:
        log.warning("media send failed for %s, falling back to text: %s", tweet.link, e)
        await bot.send_message(chat_id, render(tweet, user, media_failed=True))


async def _send_photos(bot, chat_id: int, urls: list[str], http, caption: str | None = None):
    photos = [await _download(http, url, PHOTO_CAP) for url in urls]
    if len(photos) == 1:
        await bot.send_photo(chat_id, photos[0], caption=caption)
    else:
        media = [InputMediaPhoto(p, caption=caption if i == 0 else None) for i, p in enumerate(photos)]
        await bot.send_media_group(chat_id, media)


async def _download(http, url: str, cap: int) -> bytes:
    async with http.stream("GET", url) as response:
        response.raise_for_status()
        buffer = BytesIO()
        async for chunk in response.aiter_bytes(65536):
            buffer.write(chunk)
            if buffer.tell() > cap:
                raise MediaError(f"larger than {cap // (1024 * 1024)} MB")
        return buffer.getvalue()