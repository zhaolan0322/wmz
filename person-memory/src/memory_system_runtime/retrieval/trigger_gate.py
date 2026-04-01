from __future__ import annotations

from ..core.models import QueryState


class TriggerGate:
    def allows(self, state: QueryState) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        if state.explicit_recall_requested:
            reasons.append("T_EXPLICIT_RECALL")
            return True, reasons
        if state.query_type in {"task_continue", "historical_lookup", "exact_recall"}:
            reasons.append("T_CONTINUATION")
            return True, reasons
        if state.query_type == "problem_blocked":
            reasons.append("T_BLOCKED_PATTERN")
            return True, reasons
        if state.query_type == "project_planning":
            reasons.append("T_PERSONALIZATION")
            return True, reasons
        reasons.append("T_NO_HISTORY_NEEDED")
        return False, reasons
