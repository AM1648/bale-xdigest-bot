from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo
import yaml
import os

from models.channel import Channel
from models.user import User


@dataclass(frozen=True)
class Config:
    trigger_times: list[time]   # local times of day for automatic runs
    api_delay: float
    admins: list[int]
    channels: list[Channel]
    timezone: str               # IANA timezone name, e.g., "Asia/Tehran"

    def channel(self, name: str) -> Channel | None:
        return next((c for c in self.channels if c.channel_name == name), None)

    @staticmethod
    def _parse_time(value: str) -> time:
        try:
            return time.fromisoformat(value)
        except ValueError as e:
            raise ValueError(f"Invalid time '{value}' (expected HH:MM): {e}") from None

    @classmethod
    def from_yaml(cls, path: str = "config.yaml", env_path: str = ".env") -> "Config":
        from dotenv import load_dotenv
        load_dotenv(env_path)

        timezone = os.getenv("TZ", "Asia/Tehran")
        raw = yaml.safe_load(Path(path).read_text()) or {}

        try:
            cfg = cls(
                trigger_times=[cls._parse_time(str(t)) for t in raw["trigger_times"]],
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
                timezone=timezone,
            )
        except (KeyError, TypeError, ValueError) as e:
            raise SystemExit(f"invalid config.yaml: {e}") from None

        if not cfg.channels:
            raise SystemExit("invalid config.yaml: no channels configured")
        if not cfg.trigger_times:
            raise SystemExit("invalid config.yaml: trigger_times must not be empty")
        return cfg

    def now(self) -> datetime:
        return datetime.now(ZoneInfo(self.timezone))