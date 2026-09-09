from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import yaml
import os

from models.channel import Channel
from models.user import User


@dataclass(frozen=True)
class Config:
    refresh_period_seconds: int
    api_delay: float
    admins: list[int]
    channels: list[Channel]
    timezone: str  # IANA timezone name, e.g., "Asia/Tehran"

    def channel(self, name: str) -> Channel | None:
        return next((c for c in self.channels if c.channel_name == name), None)

    @staticmethod
    def _parse_period(period_str: str) -> int:
        """Convert '6h', '30m', '2d' to seconds."""
        if not period_str:
            raise ValueError("refresh_period must be non-empty")
        unit = period_str[-1]
        value_str = period_str[:-1]
        if not value_str.isdigit():
            raise ValueError(f"Invalid number in refresh_period: {period_str}")
        value = int(value_str)
        if unit == 's':
            return value
        if unit == 'm':
            return value * 60
        if unit == 'h':
            return value * 3600
        if unit == 'd':
            return value * 86400
        raise ValueError(f"Invalid unit in refresh_period: {period_str} (use s, m, h, d)")

    @classmethod
    def from_yaml(cls, path: str = "config.yaml", env_path: str = ".env") -> "Config":
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv(env_path)

        timezone = os.getenv("TZ", "Asia/Tehran")
        raw = yaml.safe_load(Path(path).read_text()) or {}

        try:
            refresh_period_seconds = cls._parse_period(str(raw["refresh_period"]))
            cfg = cls(
                refresh_period_seconds=refresh_period_seconds,
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
        return cfg

    def now(self) -> datetime:
        """Return current datetime in the configured timezone."""
        return datetime.now(ZoneInfo(self.timezone))