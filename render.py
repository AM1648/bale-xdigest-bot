from Tweet import Tweet
from config import User

# Bale always parses Markdown: escape these wherever they appear as literal text
_MARKDOWN = str.maketrans({c: "\\" + c for c in "\\()[]*`_"})


def _esc(text: str | None) -> str:
    return (text or "").translate(_MARKDOWN)


def render(tweet: Tweet, user: User, media_failed: bool = False, limit: int = 4096) -> str:
    if tweet.has_retweet and tweet.original_link:
        header = f"✍️ [{_esc(tweet.original_screen_name)}]({tweet.original_link}) (🔃 {_esc(user.user_name)})"
    else:
        header = f"✍️ [{_esc(user.user_name)}]({tweet.link})"

    body = _esc(tweet.long_text if tweet.long_text is not None else tweet.text)

    quote = ""
    if tweet.has_quote and tweet.quoted_link:
        quote = f"💬 [{_esc(tweet.quoted_screen_name)}]({tweet.quoted_link})\n{_esc(tweet.quoted_text)}\n\n"

    note = "\n\n⚠️ Media failed to load" if media_failed else ""

    def message(b: str, q: str) -> str:
        return f"{b}{header}\n\n{q}{note}"

    if len(message(quote, body)) > limit:  # shrink body, then quote, until it fits
        body = _trunc(body, limit - len(message(quote, "")))
    if len(message(quote, body)) > limit:
        quote = _trunc(quote, limit - len(message("", body)))
    return message(quote, body)


def _trunc(text: str, room: int) -> str:
    if room <= 3 or len(text) <= room:
        return text
    return text[: room - 3].rstrip() + "..."
