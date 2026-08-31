from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Tweet:
    text: str
    author: str
    screen_name: str
    link: str
    tweet_id: str
    created_at: datetime

    has_retweet: bool = False
    has_quote: bool = False
    has_images: bool = False
    has_video: bool = False
    has_gif: bool = False
    is_long: bool = False

    original_author: Optional[str] = None
    original_screen_name: Optional[str] = None
    original_text: Optional[str] = None
    original_link: Optional[str] = None

    quoted_author: Optional[str] = None
    quoted_screen_name: Optional[str] = None
    quoted_text: Optional[str] = None
    quoted_link: Optional[str] = None

    image_urls: List[str] = field(default_factory=list)
    video_url: Optional[str] = None
    gif_url: Optional[str] = None
    long_text: Optional[str] = None
