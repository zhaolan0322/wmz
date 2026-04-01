from __future__ import annotations

from ..core.models import CandidateDecision, CandidateScore, MemoryItem, QueryState


class PollutionFilter:
    def classify(
        self,
        memory: MemoryItem,
        score: CandidateScore,
        state: QueryState,
    ) -> CandidateDecision:
        same_scope = memory.scope == state.scope
        if memory.layer == "core" and state.query_type not in {"historical_lookup", "exact_recall"}:
            if (
                memory.memory_type == "project_profile"
                and same_scope
                and state.query_type in {"project_planning", "problem_blocked"}
                and score.retrieval_score >= 0.45
                and score.pollution_risk < 0.50
            ):
                return CandidateDecision(memory, score, "frontstage", "R_PROJECT_ENTRY_PASS")
            return CandidateDecision(memory, score, "background", "P_CORE_SILENT_USE")
        if memory.layer == "working" and state.query_type != "task_continue":
            if score.keyword_match < 0.20:
                return CandidateDecision(memory, score, "suppressed", "P_TEMPORARY_STATE")
        if (
            memory.layer == "working"
            and same_scope
            and state.query_type == "task_continue"
            and score.retrieval_score >= 0.45
            and score.pollution_risk < 0.45
        ):
            return CandidateDecision(memory, score, "frontstage", "R_TASK_CONTINUE_PASS")
        if score.retrieval_score < 0.35:
            return CandidateDecision(memory, score, "suppressed", "R_LOW_SCORE_REJECTED")
        if (
            same_scope
            and memory.layer in {"dynamic", "procedural"}
            and score.retrieval_score >= 0.50
            and score.pollution_risk < 0.45
        ):
            return CandidateDecision(memory, score, "frontstage", "R_SAME_SCOPE_PASS")
        if score.pollution_risk >= 0.60:
            return CandidateDecision(memory, score, "suppressed", "P_SCOPE_MISMATCH")
        if score.pollution_risk >= 0.30:
            return CandidateDecision(memory, score, "background", "P_LOW_UTILITY")
        return CandidateDecision(memory, score, "frontstage", "R_HARD_MIN_PASS")
