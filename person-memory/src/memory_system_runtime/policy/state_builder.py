from __future__ import annotations

from uuid import uuid4

from ..core.models import QueryState, RuntimeContext
from ..core.utils import continuation_likelihood, estimate_complexity, simple_query_type


class StateBuilder:
    def build(self, query: str, context: RuntimeContext) -> QueryState:
        query_type = simple_query_type(query)
        if query_type in {"project_planning", "problem_blocked", "historical_lookup"} and context.project_id:
            scope = f"project:{context.project_id}"
        elif context.explicit_recall_requested and context.project_id:
            scope = f"project:{context.project_id}"
        elif context.task_id:
            scope = f"task:{context.task_id}"
        elif context.project_id:
            scope = f"project:{context.project_id}"
        else:
            scope = "global"
        return QueryState(
            query=query,
            query_type=query_type,
            complexity=estimate_complexity(query),
            scope=scope,
            continuation_likelihood=continuation_likelihood(query, context.project_id),
            explicit_recall_requested=context.explicit_recall_requested,
            current_risk="high" if query_type == "exact_recall" else "medium",
            available_memory_layers=["core", "working", "dynamic", "procedural", "raw"],
            recent_failures=[],
            user_preference_mode=context.memory_mode,
            budgets={
                "retrieval_cost_budget": context.retrieval_cost_budget,
                "context_token_budget": context.context_token_budget,
                "delivery_level_ceiling": context.delivery_level_ceiling,
            },
        )

    @staticmethod
    def new_context(project_id: str | None = None, task_id: str | None = None) -> RuntimeContext:
        return RuntimeContext(query_id=str(uuid4()), session_id=str(uuid4()), project_id=project_id, task_id=task_id)
