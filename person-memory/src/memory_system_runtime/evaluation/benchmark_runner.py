from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from ..app import MemorySystemApp
from ..core.models import RuntimeContext


class BenchmarkRunner:
    def __init__(self, app: MemorySystemApp, cases_dir: str | Path):
        self.app = app
        self.cases_dir = Path(cases_dir)

    def run(self) -> dict:
        results = []
        for path in sorted(self.cases_dir.glob("*.json")):
            case = json.loads(path.read_text(encoding="utf-8"))
            env = case.get("environment", {})
            context = RuntimeContext(
                query_id=str(uuid4()),
                session_id=env.get("session_id") or str(uuid4()),
                project_id=env.get("project_id"),
                task_id=env.get("task_id"),
                memory_mode=env.get("memory_mode", "summary_first"),
                explicit_recall_requested=env.get("explicit_recall_requested", False),
                retrieval_cost_budget=env.get("retrieval_cost_budget", 10),
                context_token_budget=env.get("context_token_budget", 800),
                delivery_level_ceiling=env.get("delivery_level_ceiling", 2),
            )
            output = self.app.handle_query(case["query"], context)
            expected = case["expected"]
            checks = self._evaluate_case(output, expected)
            passed = all(item["passed"] for item in checks)
            results.append(
                {
                    "case_id": case["case_id"],
                    "passed": passed,
                    "expected_delivery_level": expected.get("delivery_level"),
                    "actual_delivery_level": output["delivery_level"],
                    "checks": checks,
                    "used_memory_ids": output["used_memory_ids"],
                }
            )
        total = len(results)
        passed = sum(1 for item in results if item["passed"])
        return {"total": total, "passed": passed, "pass_rate": passed / total if total else 0.0, "results": results}

    @staticmethod
    def _evaluate_case(output: dict, expected: dict) -> list[dict]:
        checks: list[dict] = []
        checks.append(
            {
                "name": "delivery_level",
                "passed": output["delivery_level"] == expected.get("delivery_level"),
                "expected": expected.get("delivery_level"),
                "actual": output["delivery_level"],
            }
        )
        if "query_type" in expected:
            checks.append(
                {
                    "name": "query_type",
                    "passed": output["query_type"] == expected["query_type"],
                    "expected": expected["query_type"],
                    "actual": output["query_type"],
                }
            )
        expected_ids = expected.get("must_include_memory_ids", [])
        if expected_ids:
            actual_ids = set(output.get("used_memory_ids", []))
            missing = [item for item in expected_ids if item not in actual_ids]
            checks.append(
                {
                    "name": "must_include_memory_ids",
                    "passed": not missing,
                    "expected": expected_ids,
                    "actual": output.get("used_memory_ids", []),
                    "missing": missing,
                }
            )
        response = output.get("response", "")
        response_contains = expected.get("response_contains", [])
        if response_contains:
            missing_terms = [term for term in response_contains if term not in response]
            checks.append(
                {
                    "name": "response_contains",
                    "passed": not missing_terms,
                    "expected": response_contains,
                    "actual": response,
                    "missing": missing_terms,
                }
            )
        response_not_contains = expected.get("response_not_contains", [])
        if response_not_contains:
            present_terms = [term for term in response_not_contains if term in response]
            checks.append(
                {
                    "name": "response_not_contains",
                    "passed": not present_terms,
                    "expected": response_not_contains,
                    "actual": response,
                    "present": present_terms,
                }
            )
        return checks
