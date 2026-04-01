from __future__ import annotations

from datetime import datetime

from ..core.models import CandidateScore, MemoryItem, QueryState
from ..core.utils import (
    bag_similarity,
    clamp01,
    cosine_similarity,
    keyword_overlap,
    recency_score,
    text_hash_embedding,
)


class Ranker:
    def __init__(self, scoring_config: dict, embedding_dimensions: int = 64):
        self.config = scoring_config
        self.dimensions = embedding_dimensions

    def score(self, query: str, state: QueryState, memory: MemoryItem) -> CandidateScore:
        query_vec = text_hash_embedding(query, self.dimensions)
        memory_vec = text_hash_embedding(memory.summary, self.dimensions)
        semantic = cosine_similarity(query_vec, memory_vec)
        keyword = keyword_overlap(query, " ".join([memory.summary] + memory.keywords))
        if memory.scope == state.scope:
            scope_match = 1.0
        elif memory.scope == "global":
            scope_match = 0.58
        else:
            scope_match = 0.4
        freshness = self._freshness(memory.freshness_ts)
        recency = self._freshness(memory.last_used_ts)
        rerank = bag_similarity(query, memory.summary)
        intent_boost = self._intent_boost(query, memory)
        retrieval_cfg = self.config["retrieval_score"]
        retrieval_score = clamp01(
            retrieval_cfg["semantic_similarity"] * semantic
            + retrieval_cfg["keyword_match"] * keyword
            + retrieval_cfg["scope_match"] * scope_match
            + retrieval_cfg["recency_boost"] * recency
            + retrieval_cfg["importance"] * memory.importance
            + retrieval_cfg["strength"] * memory.strength
            + retrieval_cfg["freshness"] * freshness
            + retrieval_cfg["rerank_score"] * rerank
            + intent_boost
        )
        temporary_state_risk = 0.85 if memory.layer == "working" and state.scope != "task" else 0.15
        outdatedness = 1.0 - freshness
        excessive_length = clamp01(max(0, len(memory.summary) - 160) / 400)
        conflict_risk = 0.7 if memory.status == "conflicted" else 0.0
        unclear_utility = 1.0 - retrieval_score
        pollution_cfg = self.config["pollution_risk"]
        scope_mismatch = 1.0 - scope_match
        pollution_risk = clamp01(
            pollution_cfg["scope_mismatch"] * scope_mismatch
            + pollution_cfg["temporary_state_risk"] * temporary_state_risk
            + pollution_cfg["outdatedness"] * outdatedness
            + pollution_cfg["excessive_length"] * excessive_length
            + pollution_cfg["conflict_risk"] * conflict_risk
            + pollution_cfg["unclear_utility"] * unclear_utility
        )
        confidence_cfg = self.config["confidence"]
        retrieval_quality = retrieval_score
        scope_alignment = scope_match
        conflict_free = 1.0 - conflict_risk
        source_strength = 0.8 if memory.source_refs else 0.5
        evidence_completeness = 0.8 if memory.source_refs else 0.4
        confidence = clamp01(
            confidence_cfg["retrieval_quality"] * retrieval_quality
            + confidence_cfg["source_strength"] * source_strength
            + confidence_cfg["scope_alignment"] * scope_alignment
            + confidence_cfg["freshness"] * freshness
            + confidence_cfg["conflict_free"] * conflict_free
            + confidence_cfg["evidence_completeness"] * evidence_completeness
        )
        return CandidateScore(
            memory_id=memory.memory_id,
            semantic_similarity=semantic,
            keyword_match=keyword,
            scope_match=scope_match,
            recency_boost=recency,
            importance=memory.importance,
            strength=memory.strength,
            freshness=freshness,
            rerank_score=rerank,
            retrieval_score=retrieval_score,
            temporary_state_risk=temporary_state_risk,
            outdatedness=outdatedness,
            excessive_length=excessive_length,
            conflict_risk=conflict_risk,
            unclear_utility=unclear_utility,
            pollution_risk=pollution_risk,
            confidence=confidence,
        )

    @staticmethod
    def _freshness(ts: str | None) -> float:
        if not ts:
            return 0.5
        try:
            age_days = (datetime.now().astimezone() - datetime.fromisoformat(ts)).days
        except ValueError:
            return 0.5
        return recency_score(age_days, 30)

    @staticmethod
    def _intent_boost(query: str, memory: MemoryItem) -> float:
        boost = 0.0
        title = memory.title
        q = query.lower()
        if any(token in q for token in ["课程", "内容结构", "大纲", "训练营"]) and "课程内容结构" in title:
            boost += 0.20
        if any(token in q for token in ["模板", "约束", "html2pptx", "导出"]) and ("模板" in title or "约束" in title):
            boost += 0.18
        if any(token in q for token in ["关键文件", "文件", "产物", "readme", "配置"]) and ("关键文件" in title or "产物" in title):
            boost += 0.20
        if any(token in q for token in ["开始", "先看什么", "入口"]) and memory.memory_type == "project_profile":
            boost += 0.18
        if any(token in q for token in ["结构", "进入顺序", "目录"]) and memory.layer == "procedural":
            boost += 0.18
        return clamp01(boost)
