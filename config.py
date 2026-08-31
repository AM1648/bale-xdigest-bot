from dataclasses import dataclass
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

TZ_NAME = "Asia/Tehran"
TZ = ZoneInfo(TZ_NAME)


@dataclass(frozen=True)
class User:
    user_name: str
    user_id: str


@dataclass(frozen=True)
class Channel:
    channel_name: str
    channel_id: int
    users: list[User]


@dataclass(frozen=True)
class Config:
    trigger: time
    api_delay: float
    admins: list[int]
    channels: list[Channel]

    def channel(self, name: str) -> Channel | None:
        return next((c for c in self.channels if c.channel_name == name), None)


def load_config(path: str = "config.yaml") -> Config:
    raw = yaml.safe_load(Path(path).read_text()) or {}
    try:
        cfg = Config(
            trigger=time.fromisoformat(str(raw["trigger"])),
            api_delay=raw.get("api_delay_ms", 0) / 1000,
            admins=[int(a) for a in raw["admins"]],
            channels=[
                Channel(
                    channel_name=c["channel_name"],
                    channel_id=int(c["channel_id"]),
                    users=[User(u["user_name"], str(u["user_id"])) for u in c["users"]],
                )
                for c in raw["channels"]
            ],
        )
    except (KeyError, TypeError, ValueError) as e:
        raise SystemExit(f"invalid config.yaml: {e}") from None
    if not cfg.channels:
        raise SystemExit("invalid config.yaml: no channels configured")
    return cfg
