import json
from pathlib import Path
from typing import Optional

class BotState:
    def __init__(self, file_path: Path = Path("state.json")):
        self.path = file_path
        self._data = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            with open(self.path, 'r') as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self._data, f, indent=2)

    def is_tweet_sent(self, channel_name: str, user_id: str, tweet_id: str) -> bool:
        return tweet_id in self._data.get("sent_tweets", {}).get(channel_name, {}).get(user_id, [])

    def add_sent_tweet(self, channel_name: str, user_id: str, tweet_id: str):
        self._data.setdefault("sent_tweets", {}).setdefault(channel_name, {}).setdefault(user_id, []).append(tweet_id)
        self._save()

    def add_sent_tweets(self, channel_name: str, user_id: str, tweet_ids: list[str]):
        if not tweet_ids:
            return
        sent = self._data.setdefault("sent_tweets", {}).setdefault(channel_name, {}).setdefault(user_id, [])
        sent.extend(tweet_ids)
        self._save()