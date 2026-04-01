from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


def utc_now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


@dataclass
class RuntimeContext:
    query_id: str
    session_id: str
    task_id: str | None = None
    project_id: str | None = None
    memory_mode: str = "summary_first"
    explicit_recall_requested: bool = False
    retrieval_cost_budget: int = 10
    context_token_budget: int = 800
    delivery_level_ceiling: int = 2


@dataclass
class QueryState:
    query: str
    query_type: str
    complexity: str
    scope: str
    continuation_likelihood: float
    explicit_recall_requested: bool
    current_risk: str
    available_memory_layers: list[str]
    recent_failures: list[str]
    user_preference_mode: str
    budgets: dict[str, int]


@dataclass
class MemoryItem:
    memory_id: str
    layer: str
    memory_type: str
    scope: str
    title: str
    summary: str
    keywords: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)
    importance: float = 0.5
    confidence: float = 0.5
    strength: float = 0.33
    freshness_ts: str | None = None
    last_used_ts: str | None = None
    ttl_days: int | None = None
    status: str = "active"
    auto_inject_level: str = "explicit_only"
    pollution_risk: float = 0.0
    delivery_options: dict[str, Any] = field(default_factory=dict)
    usage_count: int = 0
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def to_db_row(self) -> dict[str, Any]:
        row = asdict(self)
        row["keywords_json"] = row.pop("keywords")
        row["entities_json"] = row.pop("entities")
        row["source_refs_json"] = row.pop("source_refs")
        row["delivery_options_json"] = row.pop("delivery_options")
        return row


@dataclass
class CandidateScore:
    memory_id: str
    semantic_similarity: float
    keyword_match: float
    scope_match: float
    recency_boost: float
    importance: float
    strength: float
    freshness: float
    rerank_score: float
    retrieval_score: float
    temporary_state_risk: float
    outdatedness: float
    excessive_length: float
    conflict_risk: float
    unclear_utility: float
    pollution_risk: float
    confidence: float


@dataclass
class CandidateDecision:
    memory: MemoryItem
    score: CandidateScore
    disposition: str
    primary_reason: str


@dataclass
class ActionPlan:
    memory_needed: bool
    selected_layers: list[str]
    retrieval_required: bool
    deep_recall_required: bool
    delivery_level: int
    write_action: str


@dataclass
class DeliveryPayload:
    level: int
    text: str
    used_memory_ids: list[str]

