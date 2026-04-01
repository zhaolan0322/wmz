from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class SessionRecord:
    session_key: str
    session_type: str
    totalTokens: int
    last_active_at: datetime | None
    channel: str | None = None
