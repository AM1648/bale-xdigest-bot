import httpx
import json
import time

from Tweet import Tweet
from TweetParser import TweetParser

API_URL = "https://twitter283.p.rapidapi.com/UserTweets"


def make_client(proxy: str | None) -> httpx.AsyncClient:
    """Shared client for RapidAPI and tweet media; proxied only when PROXY_URL is set."""
    return httpx.AsyncClient(proxy=proxy or None, timeout=30, follow_redirects=True)


async def fetch_tweets(http: httpx.AsyncClient, api_key: str, user_id: str) -> list[Tweet | None]:
    response = await http.get(
        API_URL,
        params={"user_id": user_id},
        headers={
            "x-rapidapi-host": "twitter283.p.rapidapi.com",
            "x-rapidapi-key": api_key,
            "Content-Type": "application/json",
        },
    )
    response.raise_for_status()
    epoch_seconds = int(time.time())
    with open(f"cache_files/{user_id}-{epoch_seconds}.json", 'w') as f:
        json.dump(response.json(), f)
    return TweetParser.parse_user_tweets_response(response.json())
