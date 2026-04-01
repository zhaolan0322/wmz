from __future__ import annotations

import hashlib
import math
import re
from collections import Counter


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]", re.UNICODE)


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


def text_hash_embedding(text: str, dimensions: int = 64) -> list[float]:
    vector = [0.0] * dimensions
    for token in tokenize(text):
        h = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(h[:2], "big") % dimensions
        sign = 1.0 if h[2] % 2 == 0 else -1.0
        vector[idx] += sign
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return clamp01((sum(x * y for x, y in zip(a, b)) + 1.0) / 2.0)


def keyword_overlap(query: str, memory_text: str) -> float:
    q_tokens = set(tokenize(query))
    m_tokens = set(tokenize(memory_text))
    if not q_tokens or not m_tokens:
        return 0.0
    return clamp01(len(q_tokens & m_tokens) / len(q_tokens))


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def recency_score(age_days: int | None, half_life_days: int = 14) -> float:
    if age_days is None:
        return 0.5
    return clamp01(math.exp(-max(age_days, 0) / max(half_life_days, 1)))


def estimate_complexity(query: str) -> str:
    q = normalize_text(query)
    length = len(q)
    if length < 20:
        return "low"
    if length < 80:
        return "medium"
    return "high"


def simple_query_type(query: str) -> str:
    q = normalize_text(query).lower()
    if any(x in q for x in ["逐字", "原文", "exact recall", "exact", "一字不差", "原话照抄"]):
        return "exact_recall"
    if any(x in q for x in ["继续", "接着", "continue", "resume", "延续", "接上", "往下做"]):
        return "task_continue"
    if any(x in q for x in ["回忆", "回顾", "复盘", "还记得", "当时", "那次", "结论是什么", "主要结论"]) and any(
        x in q for x in ["上次", "之前", "earlier", "previous", "当时", "那次"]
    ):
        return "historical_lookup"
    if any(x in q for x in ["卡住", "bug", "issue", "问题", "check first", "排查", "先该检查", "先看什么"]):
        return "problem_blocked"
    if re.search(r"(如何|怎么).{0,8}(配置|搭建|实现|开始|使用)", q):
        return "project_planning"
    if re.search(r"(正确|最佳|合适).{0,6}(配置|使用|开始)", q):
        return "project_planning"
    if any(
        x in q
        for x in [
            "规划",
            "plan",
            "roadmap",
            "next step",
            "起步",
            "怎么开始",
            "怎么起步",
            "如何开始",
            "应该如何开始",
            "如何正确使用",
            "正确使用",
            "怎么理解",
            "如何理解",
            "怎么实现",
            "如何实现",
            "怎么配置",
            "如何配置",
            "工作流",
            "能力",
            "功能",
            "怎么走",
            "流程",
            "路径",
            "路线",
            "架构",
            "三层",
            "完整提示词",
            "主流程",
            "从哪开始",
        ]
    ):
        return "project_planning"
    if any(x in q for x in ["上次", "之前", "remember", "previous", "earlier", "原话", "回忆", "回顾", "复盘", "当时", "那次"]):
        return "historical_lookup"
    return "chat_simple"


def continuation_likelihood(query: str, project_id: str | None) -> float:
    q = normalize_text(query).lower()
    hints = ["继续", "接着", "上次", "之前", "同样", "类似", "那个", "that issue", "same project"]
    score = 0.2 + 0.15 * sum(1 for h in hints if h in q)
    if project_id:
        score += 0.2
    return clamp01(score)


def bag_similarity(a: str, b: str) -> float:
    ca = Counter(tokenize(a))
    cb = Counter(tokenize(b))
    if not ca or not cb:
        return 0.0
    inter = sum((ca & cb).values())
    union = sum((ca | cb).values())
    return clamp01(inter / union)
