from dataclasses import dataclass

@dataclass(frozen=True)
class User:
    user_name: str
    user_id: str