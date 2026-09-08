from dataclasses import dataclass
from models.user import User

@dataclass(frozen=True)
class Channel:
    channel_name: str
    channel_id: int
    users: list[User]