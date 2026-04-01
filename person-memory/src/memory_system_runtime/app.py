from __future__ import annotations

from pathlib import Path

from .consolidation.cleanup_engine import CleanupEngine
from .core.config import ConfigBundle
from .core.models import CandidateDecision, RuntimeContext
from .delivery.delivery_builder import DeliveryBuilder
from .delivery.pollution_filter import PollutionFilter
from .evaluation.trace_logger import TraceLogger
from .policy.constraints import Constraints
from .policy.policy_engine import PolicyEngine
from .policy.state_builder import StateBuilder
from .retrieval.ranker import Ranker
from .retrieval.scope_gate import ScopeGate
from .retrieval.trigger_gate import TriggerGate
from .storage.sqlite_store import SQLiteStore


class MemorySystemApp:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.config = ConfigBundle(self.root)
        self.store = SQLiteStore(self.config.memory["paths"]["metadata_db"])
        self.trigger_gate = TriggerGate()
        self.scope_gate = ScopeGate()
        self.state_builder = StateBuilder()
        self.policy_engine = PolicyEngine()
        self.ranker = Ranker(
            self.config.scoring,
            self.config.memory["runtime"]["embedding_dimensions"],
        )
        self.pollution_filter = PollutionFilter()
        self.delivery_builder = DeliveryBuilder()
        self.trace_logger = TraceLogger(self.config.memory["paths"]["trace_log"])
        self.cleanup_engine = CleanupEngine(self.config.cleanup)

    def initialize(self) -> None:
        self.store.initialize()

    def handle_query(self, query: str, context: RuntimeContext) -> dict:
        entry_documents = self._load_entry_documents(context)
        state = self.state_builder.build(query, context)
        trigger_allowed, trigger_reasons = self.trigger_gate.allows(state)
        scopes, scope_reasons = self.scope_gate.allowed_scopes(state, context)
        plan = Constraints.apply(self.policy_engine.decide(state, trigger_allowed))
        memories = self.store.load_memories(active_only=True)
        candidates: list[CandidateDecision] = []
        if plan.retrieval_required:
            for memory in memories:
                if memory.scope not in scopes and memory.scope != "global":
                    continue
                if memory.layer not in plan.selected_layers:
                    continue
                score = self.ranker.score(query, state, memory)
                candidates.append(self.pollution_filter.classify(memory, score, state))
        self._enforce_project_priority(candidates, state)
        candidates.sort(key=lambda d: d.score.retrieval_score, reverse=True)
        max_frontstage = self.config.memory["runtime"]["max_frontstage_candidates"]
        if state.scope.startswith("project:") and state.explicit_recall_requested and not state.query_type == "exact_recall":
            max_frontstage = min(max_frontstage, 2)
        frontstage = [d.memory for d in candidates if d.disposition == "frontstage"][
            : max_frontstage
        ]
        for memory in frontstage:
            self.store.update_usage(memory.memory_id)
        delivery = self.delivery_builder.build(frontstage, state, plan.delivery_level)
        trace = self.trace_logger.build_trace(
            context,
            state,
            entry_documents,
            trigger_allowed,
            trigger_reasons,
            scopes,
            scope_reasons,
            plan,
            candidates,
            delivery,
        )
        self.store.insert_trace(trace)
        self.trace_logger.append_jsonl(trace)
        return {
            "query": query,
            "query_type": state.query_type,
            "delivery_level": delivery.level,
            "response": delivery.text,
            "used_memory_ids": delivery.used_memory_ids,
        }

    def _load_entry_documents(self, context: RuntimeContext) -> list[dict]:
        documents: list[dict] = []
        global_entry = Path(self.config.memory["paths"]["global_entry_doc"])
        if global_entry.exists():
            documents.append(
                {
                    "scope": "global",
                    "path": str(global_entry),
                    "title": "固定入口",
                }
            )
        if context.project_id:
            project_entry = Path(self.config.memory["paths"]["archive_root"]) / "projects" / context.project_id / "project_entry.md"
            if project_entry.exists():
                documents.append(
                    {
                        "scope": f"project:{context.project_id}",
                        "path": str(project_entry),
                        "title": "项目入口",
                    }
                )
        return documents

    @staticmethod
    def _enforce_project_priority(candidates: list[CandidateDecision], state) -> None:
        if state.scope == "global":
            return
        if state.explicit_recall_requested:
            for candidate in candidates:
                if candidate.memory.layer == "core":
                    continue
                if candidate.memory.scope == "global" and candidate.disposition == "frontstage":
                    candidate.disposition = "background"
                    candidate.primary_reason = "P_EXPLICIT_PROJECT_PRIORITY"
            return
        has_project_frontstage = any(
            candidate.disposition == "frontstage" and candidate.memory.scope == state.scope
            for candidate in candidates
        )
        if not has_project_frontstage:
            return
        for candidate in candidates:
            if candidate.memory.layer == "core":
                continue
            if candidate.memory.scope == "global" and candidate.disposition == "frontstage":
                candidate.disposition = "background"
                candidate.primary_reason = "P_PROJECT_PRIORITY"
