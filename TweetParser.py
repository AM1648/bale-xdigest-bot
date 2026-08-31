# TweetParser.py
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from Tweet import Tweet


class TweetParser:
    """Parses X/Twitter 'user tweets' GraphQL API responses."""

    @staticmethod
    def parse_user_tweets_response(json_response: dict) -> List[Optional[Tweet]]:
        try:
            instructions = (json_response["data"]["user_result_by_rest_id"]["result"]
                            ["profile_timeline_v2"]["timeline"]["instructions"])
        except (KeyError, TypeError) as exc:
            raise ValueError(f"Invalid user tweets response: {exc}") from exc

        tweets: List[Optional[Tweet]] = []
        for instruction in instructions:
            for entry in TweetParser._instruction_entries(instruction):
                content = entry.get("content")
                if not isinstance(content, dict) or content.get("__typename") != "TimelineTimelineItem":
                    continue  # non-tweet blocks (e.g. "Who to follow" modules)
                item = content.get("content")
                if not isinstance(item, dict) or item.get("__typename") != "TimelineTweet":
                    continue
                try:
                    tweets.append(TweetParser._parse_tweet_item(item))
                except Exception:
                    tweets.append(None)
        return tweets

    @staticmethod
    def _instruction_entries(instruction: Dict[str, Any]) -> List[Dict[str, Any]]:
        kind = instruction.get("__typename")
        if kind == "TimelinePinEntry":
            entry = instruction.get("entry")
            return [entry] if entry else []
        if kind == "TimelineAddEntries":
            return instruction.get("entries") or []
        return []  # TimelineClearCache, ...

    @staticmethod
    def _parse_tweet_item(item: Dict[str, Any]) -> Tweet:
        result = TweetParser._tweet_result(item.get("tweet_results"))
        if result is None:
            raise ValueError("tweet result unavailable")
        return TweetParser._parse_tweet(result)

    @staticmethod
    def _parse_tweet(result: Dict[str, Any]) -> Tweet:
        legacy = result["legacy"]
        user = TweetParser._dig(result, "core", "user_results", "result", "core") or {}
        retweeted = TweetParser._tweet_result(legacy.get("retweeted_status_results"))
        quoted = TweetParser._tweet_result(result.get("quoted_tweet_results"))
        if quoted is None and retweeted is not None:  # retweet of a quote
            quoted = TweetParser._tweet_result(retweeted.get("quoted_tweet_results"))

        # media: first hit wins across self -> retweeted -> quoted
        images, video, gif = [], None, None
        for source in (result, retweeted, quoted):
            if source is not None:
                images, video, gif = TweetParser._media(source)
                if images or video or gif:
                    break

        note = TweetParser._dig(result, "note_tweet", "note_tweet_results", "result", "text")
        tweet = Tweet(
            text=legacy["full_text"],
            author=user["name"],
            screen_name=user["screen_name"],
            link=f"https://x.com/{user['screen_name']}/status/{result['rest_id']}",
            tweet_id=result["rest_id"],
            created_at=datetime.strptime(legacy["created_at"], "%a %b %d %H:%M:%S %z %Y"),
            has_images=bool(images),
            has_video=video is not None,
            has_gif=gif is not None,
            is_long=note is not None,
            image_urls=images,
            video_url=video,
            gif_url=gif,
            long_text=note,
        )
        if retweeted is not None:
            tweet.has_retweet = True
            (tweet.original_author, tweet.original_screen_name,
             tweet.original_text, tweet.original_link) = TweetParser._ref(retweeted)
        if quoted is not None:
            tweet.has_quote = True
            (tweet.quoted_author, tweet.quoted_screen_name,
             tweet.quoted_text, tweet.quoted_link) = TweetParser._ref(quoted)
        return tweet

    @staticmethod
    def _tweet_result(wrapper: Any) -> Optional[Dict[str, Any]]:
        """Usable Tweet payload from a tweet_results wrapper; None if unavailable."""
        result = wrapper.get("result") if isinstance(wrapper, dict) else None
        if isinstance(result, dict) and result.get("__typename") == "TweetWithVisibilityResults":
            result = result.get("tweet")
        return result if isinstance(result, dict) and result.get("__typename") == "Tweet" else None

    @staticmethod
    def _ref(result: Dict[str, Any]) -> tuple:
        """(author, screen_name, text, link) of a retweeted/quoted tweet."""
        user = TweetParser._dig(result, "core", "user_results", "result", "core") or {}
        note = TweetParser._dig(result, "note_tweet", "note_tweet_results", "result", "text")
        screen_name = user.get("screen_name")
        text = note if note is not None else TweetParser._dig(result, "legacy", "full_text")
        link = f"https://x.com/{screen_name}/status/{result.get('rest_id')}" if screen_name else None
        return user.get("name"), screen_name, text, link

    @staticmethod
    def _media(result: Dict[str, Any]) -> tuple:
        images, video, gif = [], None, None
        for medium in TweetParser._dig(result, "legacy", "extended_entities", "media") or []:
            kind = medium.get("type")
            if kind == "photo":
                images.append(medium["media_url_https"])
            elif kind in ("video", "animated_gif"):
                url = TweetParser._best_video_url(medium)
                if kind == "video":
                    video = video or url
                else:
                    gif = gif or url
        return images, video, gif

    @staticmethod
    def _best_video_url(medium: Dict[str, Any]) -> Optional[str]:
        variants = TweetParser._dig(medium, "video_info", "variants") or []
        mp4s = [v for v in variants if v.get("content_type") == "video/mp4"]
        best = max(mp4s or variants, key=lambda v: v.get("bitrate") or 0, default=None)
        return best.get("url") if best else None

    @staticmethod
    def _dig(obj: Any, *keys: str) -> Any:
        for key in keys:
            obj = obj.get(key) if isinstance(obj, dict) else None
        return obj
