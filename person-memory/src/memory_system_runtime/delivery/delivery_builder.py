from __future__ import annotations

import re

from ..core.models import DeliveryPayload, MemoryItem, QueryState


class DeliveryBuilder:
    def build(self, frontstage: list[MemoryItem], state: QueryState, level: int) -> DeliveryPayload:
        frontstage = self._prioritize_for_state(frontstage, state)
        used = [m.memory_id for m in frontstage]
        if not frontstage or level == 0:
            return DeliveryPayload(level=0, text="本轮无需显式调用历史记忆。", used_memory_ids=[])
        if level == 1:
            keywords = []
            for memory in frontstage:
                keywords.extend(memory.delivery_options.get("keyword_hint", memory.keywords[:3]))
            unique_keywords = list(dict.fromkeys(keywords))[:6]
            text = "可先关注这些关键词：" + "、".join(unique_keywords)
            return DeliveryPayload(level=1, text=text, used_memory_ids=used)
        if level == 2:
            direct_answer = self._build_direct_summary(frontstage, state)
            if direct_answer:
                return DeliveryPayload(level=2, text=direct_answer, used_memory_ids=used)
            summaries = [m.delivery_options.get("method_summary", m.summary) for m in frontstage[:2]]
            text = "可参考的方法：\n- " + "\n- ".join(summaries)
            return DeliveryPayload(level=2, text=text, used_memory_ids=used)
        if level == 3:
            patterns = [m.delivery_options.get("reusable_pattern", m.summary) for m in frontstage[:2]]
            text = "建议直接复用的现成模式：\n- " + "\n- ".join(patterns)
            return DeliveryPayload(level=3, text=text, used_memory_ids=used)
        evidence = [m.summary for m in frontstage[:3]]
        text = "完整参考记忆如下：\n- " + "\n- ".join(evidence)
        return DeliveryPayload(level=4, text=text, used_memory_ids=used)

    @staticmethod
    def _prioritize_for_state(frontstage: list[MemoryItem], state: QueryState) -> list[MemoryItem]:
        if state.query_type not in {"historical_lookup", "exact_recall"}:
            return frontstage

        def priority(memory: MemoryItem) -> tuple[int, int]:
            if memory.memory_type in {"experience", "episode", "procedure"} and memory.layer in {"dynamic", "raw", "procedural"}:
                return (0, 0)
            if memory.layer == "core":
                return (2, 0)
            return (1, 0)

        return sorted(frontstage, key=priority)

    @staticmethod
    def _build_direct_summary(frontstage: list[MemoryItem], state: QueryState) -> str:
        query = state.query
        if DeliveryBuilder._asks_for_entry_point(query):
            for memory in frontstage:
                if memory.memory_type == "project_profile":
                    summary = memory.delivery_options.get("method_summary", memory.summary)
                    if "模板约束" in summary and "模板与导出约束" not in summary:
                        summary = summary.replace("模板约束", "模板与导出约束")
                    return summary
        if DeliveryBuilder._asks_for_structure(query):
            for memory in frontstage:
                if "课程内容结构" in memory.title:
                    return f"当前项目的课程内容结构可以先按这条主线理解：{memory.summary}"
        if DeliveryBuilder._asks_for_template_constraints(query):
            for memory in frontstage:
                if "模板" in memory.title or "约束" in memory.title:
                    return f"当前项目的模板与导出约束重点是：{memory.summary}"
        if DeliveryBuilder._asks_for_workflow(query):
            for memory in frontstage:
                if "工作流" in memory.title:
                    return f"当前项目的主工作流是：{memory.summary}"
        if state.query_type != "project_planning":
            return ""
        joined = " ".join(memory.summary for memory in frontstage)
        if "Path A" in joined and "Path B" in joined:
            answer = "默认优先 Path A：可编辑 HTML 转 PPTX；需要视觉优先或全 AI 画面时，再使用 Path B：全 AI 视觉图转 PPTX。"
            if any(memory.memory_type == "project_profile" for memory in frontstage):
                answer += " 当前项目入口摘要也建议先看工作流，再看模板与导出约束。"
            return answer
        if re.search(r"先.*再", joined):
            condensed = []
            for memory in frontstage[:2]:
                condensed.append(memory.delivery_options.get("method_summary", memory.summary))
            return "可按这个顺序处理：\n- " + "\n- ".join(condensed)
        return ""

    @staticmethod
    def _asks_for_entry_point(query: str) -> bool:
        return any(token in query for token in ["先看什么", "先从哪里", "先从哪", "先读什么", "先做什么", "看起", "入口"])

    @staticmethod
    def _asks_for_structure(query: str) -> bool:
        return any(token in query for token in ["课程", "内容结构", "大纲", "模块"])

    @staticmethod
    def _asks_for_template_constraints(query: str) -> bool:
        return any(token in query for token in ["模板", "约束", "导出", "html2pptx"])

    @staticmethod
    def _asks_for_workflow(query: str) -> bool:
        return any(token in query for token in ["工作流", "流程", "主流程", "路径", "路线"])
