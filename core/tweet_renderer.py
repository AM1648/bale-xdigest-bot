import re
from models.tweet import Tweet
from models.user import User
from core.persian_text import PersianText


class TweetRenderer:
    # Bale always parses Markdown: escape these wherever they appear as literal text

    def __init__(self, persian: PersianText):
        self.persian = persian

    def render(self, tweet: Tweet, user: User, media_failed: bool = False) -> str:

        if tweet.has_retweet and tweet.original_link:
            header = f"✍️ [{tweet.original_screen_name}]({tweet.original_link}) (🔃 {user.user_name})"
            body = tweet.long_text if tweet.long_text is not None else tweet.original_text
        else:
            header = f"✍️ [{user.user_name}]({tweet.link})"
            body = tweet.long_text if tweet.long_text is not None else tweet.text

        quote = ""
        if tweet.has_quote and tweet.quoted_link:
            quote = f"💬 [{tweet.quoted_screen_name}]({tweet.quoted_link})\n"
            if tweet.quoted_text:
                quote += f"«{tweet.quoted_text}»\n"
            quote += "\n\n"

        # Timestamp
        timestamp = self.persian.format_datetime(tweet.created_at)

        # Media-failure prefix
        prefix = "⚠️ Media failed to load\n" if media_failed else ""

        return f"{prefix}{quote}{header}\n\n{body}\n\n⏱️ {timestamp}"