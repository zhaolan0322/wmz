from __future__ import annotations

from ..core.models import ActionPlan, MemoryItem


class Constraints:
    @staticmethod
    def filter_layers(selected_layers: list[str]) -> list[str]:
        banned = {"protected", "raw_auto"}
        return [layer for layer in selected_layers if layer not in banned]

    @staticmethod
    def can_frontstage(memory: MemoryItem, pollution_risk: float, ceiling: int) -> bool:
        if memory.layer == "raw":
            return False
        if pollution_risk >= 0.60:
            return False
        return ceiling >= 1

    @staticmethod
    def apply(plan: ActionPlan) -> ActionPlan:
        plan.selected_layers = Constraints.filter_layers(plan.selected_layers)
        if plan.delivery_level > 4:
            plan.delivery_level = 4
        return plan
