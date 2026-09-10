import json
import time
from pathlib import Path
import aiofiles
import httpx
from models.tweet import Tweet
from core.tweet_parser import TweetParser

class TwitterClient:
    API_URL = "https://twitter283.p.rapidapi.com/UserTweets"

    def __init__(self, http_client: httpx.AsyncClient, api_key: str, cache_dir: Path = Path("cache_files")):
        self.http = http_client
        self.api_key = api_key
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        self.parser = TweetParser()

    async def fetch_user_tweets(self, user_id: str) -> list[Tweet | None]:
        response = await self.http.get(
            self.API_URL,
            params={"user_id": user_id},
            headers={
                "x-rapidapi-host": "twitter283.p.rapidapi.com",
                "x-rapidapi-key": self.api_key,
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        data = response.json()
        return self.parser.parse_user_tweets_response(data)