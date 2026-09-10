import re
from models.tweet import Tweet
from models.user import User
from core.persian_text import PersianText


class TweetRenderer:
    # Bale always parses Markdown: escape these wherever they appear as literal text
    _MARKDOWN = str.maketrans({c: "\\" + c for c in "\\()[]*`_"})
    _RT_PREFIX = re.compile(r"^RT @\w+:\s*")

    def __init__(self, persian: PersianText):
        self.persian = persian

    def render(self, tweet: Tweet, user: User, media_failed: bool = False) -> str:
        def _esc(text: str | None) -> str:
            return (text or "").translate(self._MARKDOWN)

        if tweet.has_retweet and tweet.original_link:
            header = f"✍️ [{_esc(tweet.original_screen_name)}]({tweet.original_link}) (🔃 {_esc(user.user_name)})"
        else:
            header = f"✍️ [{_esc(user.user_name)}]({tweet.link})"

        # Body (strip leading "RT @username:")
        body_raw = tweet.long_text if tweet.long_text is not None else tweet.text
        body_raw = self._RT_PREFIX.sub("", body_raw or "")
        body = _esc(body_raw)

        quote = ""
        if tweet.has_quote and tweet.quoted_link:
            quote = f"💬 [{_esc(tweet.quoted_screen_name)}]({tweet.quoted_link})\n"
            if tweet.quoted_text:
                quote += f"«{_esc(tweet.quoted_text)}»\n"
            quote += "\n"

        # Timestamp
        timestamp = self.persian.format_datetime(tweet.created_at)

        # Media-failure prefix
        prefix = "⚠️ Media failed to load\n" if media_failed else ""

        return f"{prefix}{quote}{header}\n\n{body}\n\n⏱️ {timestamp}"