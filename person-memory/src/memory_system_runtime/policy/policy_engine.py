from __future__ import annotations

from ..core.models import ActionPlan, QueryState


class PolicyEngine:
    def decide(self, state: QueryState, retrieval_allowed: bool) -> ActionPlan:
        if not retrieval_allowed:
            return ActionPlan(
                memory_needed=False,
                selected_layers=["core"],
                retrieval_required=False,
                deep_recall_required=False,
                delivery_level=0,
                write_action="update_working_state_only",
            )
        selected_layers = ["core"]
        if state.explicit_recall_requested and state.query_type == "chat_simple":
            selected_layers += ["dynamic", "procedural"]
        elif state.query_type in {"task_continue", "problem_blocked"}:
            selected_layers += ["working", "procedural", "dynamic"]
        elif state.query_type in {"historical_lookup", "project_planning"}:
            selected_layers += ["dynamic", "procedural"]
        elif state.query_type == "exact_recall":
            selected_layers += ["dynamic", "procedural", "raw"]
        delivery_level = 2
        if state.query_type == "exact_recall":
            delivery_level = min(4, state.budgets["delivery_level_ceiling"])
        elif state.query_type == "problem_blocked":
            delivery_level = min(3, state.budgets["delivery_level_ceiling"])
        return ActionPlan(
            memory_needed=True,
            selected_layers=selected_layers,
            retrieval_required=True,
            deep_recall_required=state.query_type == "exact_recall",
            delivery_level=delivery_level,
            write_action="update_working_state_only",
        )
