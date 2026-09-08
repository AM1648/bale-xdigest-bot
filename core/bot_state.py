import json
from pathlib import Path
from datetime import datetime
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

    def get_last_fetch(self, channel_name: str, user_id: str) -> Optional[datetime]:
        ts = self._data.get("last_fetch", {}).get(channel_name, {}).get(user_id)
        if ts:
            return datetime.fromisoformat(ts)
        return None

    def set_last_fetch(self, channel_name: str, user_id: str, dt: datetime):
        self._data.setdefault("last_fetch", {}).setdefault(channel_name, {})[user_id] = dt.isoformat()
        self._save()