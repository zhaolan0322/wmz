from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from ..core.models import ActionPlan, CandidateDecision, DeliveryPayload, QueryState, RuntimeContext, utc_now_iso


class TraceLogger:
    def __init__(self, trace_log_path: str):
        self.trace_log_path = Path(trace_log_path)
        self.trace_log_path.parent.mkdir(parents=True, exist_ok=True)

    def build_trace(
        self,
        context: RuntimeContext,
        state: QueryState,
        entry_documents: list[dict],
        trigger_allowed: bool,
        trigger_reasons: list[str],
        scopes: list[str],
        scope_reasons: list[str],
        plan: ActionPlan,
        decisions: list[CandidateDecision],
        delivery: DeliveryPayload,
    ) -> dict:
        trace_id = str(uuid4())
        steps = [
            {
                "step_id": str(uuid4()),
                "step_order": 0,
                "step_name": "entry_read",
                "decision": "read" if entry_documents else "skip",
                "reason_codes": ["E_GLOBAL_ENTRY", "E_PROJECT_ENTRY"] if entry_documents else ["E_NO_ENTRY"],
                "scores": {},
                "payload": {"entry_documents": entry_documents},
            },
            {
                "step_id": str(uuid4()),
                "step_order": 1,
                "step_name": "trigger_gate",
                "decision": "allow" if trigger_allowed else "block",
                "reason_codes": trigger_reasons,
                "scores": {},
                "payload": {},
            },
            {
                "step_id": str(uuid4()),
                "step_order": 2,
                "step_name": "scope_gate",
                "decision": "+".join(scopes) if scopes else "none",
                "reason_codes": scope_reasons,
                "scores": {},
                "payload": {"selected_scopes": scopes},
            },
            {
                "step_id": str(uuid4()),
                "step_order": 3,
                "step_name": "policy",
                "decision": "retrieve" if plan.retrieval_required else "skip",
                "reason_codes": [],
                "scores": {},
                "payload": {
                    "selected_layers": plan.selected_layers,
                    "delivery_level": plan.delivery_level,
                    "write_action": plan.write_action,
                },
            },
            {
                "step_id": str(uuid4()),
                "step_order": 4,
                "step_name": "candidate_filter",
                "decision": "classified",
                "reason_codes": [],
                "scores": {},
                "payload": {
                    "frontstage": [d.memory.memory_id for d in decisions if d.disposition == "frontstage"],
                    "background": [d.memory.memory_id for d in decisions if d.disposition == "background"],
                    "suppressed": [d.memory.memory_id for d in decisions if d.disposition == "suppressed"],
                },
            },
            {
                "step_id": str(uuid4()),
                "step_order": 5,
                "step_name": "delivery",
                "decision": f"level_{delivery.level}",
                "reason_codes": [],
                "scores": {},
                "payload": {"used_memory_ids": delivery.used_memory_ids},
            },
        ]
        return {
            "trace_id": trace_id,
            "query_id": context.query_id,
            "session_id": context.session_id,
            "task_id": context.task_id,
            "project_id": context.project_id,
            "query_type": state.query_type,
            "state_snapshot": state.__dict__,
            "final_outcome": {
                "memory_used": bool(delivery.used_memory_ids),
                "deep_recall_triggered": plan.deep_recall_required,
                "delivery_level": delivery.level,
            },
            "policy_version": "v0.1.0",
            "threshold_version": "default",
            "created_at": utc_now_iso(),
            "policy_steps": steps,
        }

    def append_jsonl(self, trace: dict) -> None:
        with open(self.trace_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(trace, ensure_ascii=False) + "\n")
