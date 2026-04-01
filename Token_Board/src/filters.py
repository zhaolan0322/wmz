from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

# Beijing Timezone (UTC+8)
BJ_TZ = timezone(timedelta(hours=8))


def in_range(dt: Optional[datetime], range_name: str, now: datetime) -> bool:
    if range_name == 'all':
        return True
    if dt is None:
        return False
    
    # Normalize to UTC for internal calculation
    dt_utc = dt.astimezone(timezone.utc)
    now_utc = now.astimezone(timezone.utc)

    if range_name == 'today':
        # "Today" means since 00:00 Beijing Time
        now_bj = now.astimezone(BJ_TZ)
        start_bj = now_bj.replace(hour=0, minute=0, second=0, microsecond=0)
        # Convert back to UTC for comparison
        return dt_utc >= start_bj.astimezone(timezone.utc)
    
    if range_name == '7d':
        return dt_utc >= now_utc - timedelta(days=7)
    if range_name == '30d':
        return dt_utc >= now_utc - timedelta(days=30)
    raise ValueError(f'Unsupported range: {range_name}')
