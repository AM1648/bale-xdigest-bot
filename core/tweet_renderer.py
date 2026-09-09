from datetime import datetime
from zoneinfo import ZoneInfo
import jdatetime
from models.tweet import Tweet
from models.user import User


class TweetRenderer:
    # Bale always parses Markdown: escape these wherever they appear as literal text
    _MARKDOWN = str.maketrans({c: "\\" + c for c in "\\()[]*`_"})
    _locale_set = False
    # Persian digits translation table
    _PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

    def __init__(self, timezone_str: str):
        self.timezone = ZoneInfo(timezone_str)
        # Set jdatetime locale to Persian (once)
        if not TweetRenderer._locale_set:
            jdatetime.set_locale('fa_IR')
            TweetRenderer._locale_set = True

    def render(self, tweet: Tweet, user: User, media_failed: bool = False, limit: int = 4096) -> str:
        def _esc(text: str | None) -> str:
            return (text or "").translate(self._MARKDOWN)

        # Build the main content
        if tweet.has_retweet and tweet.original_link:
            header = f"✍️ [{_esc(tweet.original_screen_name)}]({tweet.original_link}) (🔃 {_esc(user.user_name)})"
        else:
            header = f"✍️ [{_esc(user.user_name)}]({tweet.link})"

        body = _esc(tweet.long_text if tweet.long_text is not None else tweet.text)

        quote = ""
        if tweet.has_quote and tweet.quoted_link:
            quote = f"💬 [{_esc(tweet.quoted_screen_name)}]({tweet.quoted_link})\n{_esc(tweet.quoted_text)}\n\n"

        note = "\n\n⚠️ Media failed to load" if media_failed else ""

        # Build timestamp in Jalali format with Persian digits
        timestamp = self._format_timestamp(tweet.created_at)
        timestamp_part = f"\n\n⏱️ {timestamp}" if not media_failed else f"\n{timestamp}"

        def message(b: str, q: str, ts: str) -> str:
            return f"{b}{header}\n\n{q}{note}{ts}"

        # Truncate body and quote to fit within limit
        if len(message(quote, body, timestamp_part)) > limit:
            room_for_body = limit - len(message(quote, "", timestamp_part))
            body = self._trunc(body, room_for_body)
        if len(message(quote, body, timestamp_part)) > limit:
            room_for_quote = limit - len(message("", body, timestamp_part))
            quote = self._trunc(quote, room_for_quote)

        # If still over, drop timestamp (rare)
        if len(message(quote, body, timestamp_part)) > limit:
            timestamp_part = ""
            if len(message(quote, body, timestamp_part)) > limit:
                body = self._trunc(body, limit - len(message(quote, "", "")))
                if len(message(quote, body, timestamp_part)) > limit:
                    quote = self._trunc(quote, limit - len(message("", body, "")))

        return message(quote, body, timestamp_part)

    def _format_timestamp(self, dt: datetime) -> str:
        # Convert to local timezone
        local_dt = dt.astimezone(self.timezone)
        # Convert to Jalali
        jalali = jdatetime.datetime.fromgregorian(datetime=local_dt)
        # Format with Persian locale (should give Persian digits, but we force conversion)
        formatted = jalali.strftime("%H:%M / %d %B")
        # Ensure all digits are Persian
        return formatted.translate(self._PERSIAN_DIGITS)

    def _trunc(self, text: str, room: int) -> str:
        if room <= 3 or len(text) <= room:
            return text
        return text[: room - 3].rstrip() + "..."