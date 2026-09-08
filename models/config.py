from dataclasses import dataclass
from datetime import time

from models.channel import Channel
from models.user import User

TZ_NAME = "Asia/Tehran"

@dataclass(frozen=True)
class Config:
    trigger: time
    api_delay: float
    admins: list[int]
    channels: list[Channel]

    def get_channel_by_name(self, name: str) -> Channel | None:
        return next((c for c in self.channels if c.channel_name == name), None)
