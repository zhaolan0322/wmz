from __future__ import annotations

from uuid import uuid4

from ..core.models import MemoryItem, utc_now_iso


class CleanupEngine:
    def __init__(self, cleanup_config: dict):
        self.cfg = cleanup_config["cleanup_priority"]

    def cleanup_priority(self, memory: MemoryItem) -> float:
        usage_score = min(1.0, memory.usage_count / 5.0)
        outdatedness = 1.0 - memory.confidence if memory.status != "active" else 0.2
        low_usage = 1.0 - usage_score
        low_confidence = 1.0 - memory.confidence
        low_importance = 1.0 - memory.importance
        duplication_risk = 0.6 if memory.summary.count(" ") < 3 else 0.1
        unclear_utility = 1.0 - memory.confidence
        return min(
            1.0,
            self.cfg["outdatedness"] * outdatedness
            + self.cfg["low_usage"] * low_usage
            + self.cfg["low_confidence"] * low_confidence
            + self.cfg["low_importance"] * low_importance
            + self.cfg["duplication_risk"] * duplication_risk
            + self.cfg["unclear_utility"] * unclear_utility,
        )

    def decide_action(self, memory: MemoryItem, priority: float) -> str:
        thresholds = self.cfg["thresholds"]
        if memory.layer == "core":
            return "keep"
        if priority >= thresholds["delete_review_min"]:
            return "archive"
        if priority >= thresholds["archive_min"]:
            return "suppress"
        if priority >= thresholds["monitor_min"]:
            return "compress"
        return "keep"

    def build_log(self, memory: MemoryItem, action: str, priority: float) -> dict:
        return {
            "action_id": str(uuid4()),
            "memory_id": memory.memory_id,
            "cleanup_action": action,
            "cleanup_priority": priority,
            "reason_codes": [f"CLEANUP_{action.upper()}"],
            "previous_layer": memory.layer,
            "new_layer": memory.layer if action == "keep" else "archive" if action == "archive" else memory.layer,
            "policy_version": "v0.1.0",
            "created_at": utc_now_iso(),
        }
