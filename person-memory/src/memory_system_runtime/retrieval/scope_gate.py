from __future__ import annotations

from ..core.models import QueryState, RuntimeContext


class ScopeGate:
    def allowed_scopes(self, state: QueryState, context: RuntimeContext) -> tuple[list[str], list[str]]:
        scopes: list[str] = []
        reasons: list[str] = []
        if context.task_id:
            scopes.append(f"task:{context.task_id}")
            reasons.append("S_TASK_ONLY")
        if context.project_id:
            scopes.append(f"project:{context.project_id}")
            reasons.append("S_PROJECT_ACTIVE")
        scopes.append("global")
        reasons.append("S_GLOBAL_CORE_ONLY")
        return scopes, reasons
