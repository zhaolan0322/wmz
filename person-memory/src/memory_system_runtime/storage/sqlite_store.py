from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from ..core.models import MemoryItem, utc_now_iso


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS memory_items (
  memory_id TEXT PRIMARY KEY,
  layer TEXT NOT NULL,
  memory_type TEXT NOT NULL,
  scope TEXT NOT NULL,
  title TEXT,
  summary TEXT NOT NULL,
  keywords_json TEXT,
  entities_json TEXT,
  source_refs_json TEXT,
  importance REAL NOT NULL,
  confidence REAL NOT NULL,
  strength REAL NOT NULL,
  freshness_ts TEXT,
  last_used_ts TEXT,
  ttl_days INTEGER,
  status TEXT NOT NULL,
  auto_inject_level TEXT NOT NULL,
  pollution_risk REAL DEFAULT 0.0,
  delivery_options_json TEXT,
  usage_count INTEGER DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS decision_traces (
  trace_id TEXT PRIMARY KEY,
  query_id TEXT NOT NULL,
  session_id TEXT,
  task_id TEXT,
  project_id TEXT,
  query_type TEXT NOT NULL,
  state_snapshot_json TEXT NOT NULL,
  final_outcome_json TEXT NOT NULL,
  policy_version TEXT NOT NULL,
  threshold_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS trace_steps (
  step_id TEXT PRIMARY KEY,
  trace_id TEXT NOT NULL,
  step_order INTEGER NOT NULL,
  step_name TEXT NOT NULL,
  decision TEXT NOT NULL,
  reason_codes_json TEXT,
  scores_json TEXT,
  payload_json TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cleanup_actions (
  action_id TEXT PRIMARY KEY,
  memory_id TEXT NOT NULL,
  cleanup_action TEXT NOT NULL,
  cleanup_priority REAL NOT NULL,
  reason_codes_json TEXT,
  previous_layer TEXT,
  new_layer TEXT,
  policy_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""


class SQLiteStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    def upsert_memory(self, item: MemoryItem) -> None:
        row = item.to_db_row()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO memory_items (
                  memory_id, layer, memory_type, scope, title, summary,
                  keywords_json, entities_json, source_refs_json, importance, confidence,
                  strength, freshness_ts, last_used_ts, ttl_days, status,
                  auto_inject_level, pollution_risk, delivery_options_json,
                  usage_count, created_at, updated_at
                ) VALUES (
                  :memory_id, :layer, :memory_type, :scope, :title, :summary,
                  :keywords_json, :entities_json, :source_refs_json, :importance, :confidence,
                  :strength, :freshness_ts, :last_used_ts, :ttl_days, :status,
                  :auto_inject_level, :pollution_risk, :delivery_options_json,
                  :usage_count, :created_at, :updated_at
                )
                ON CONFLICT(memory_id) DO UPDATE SET
                  layer=excluded.layer,
                  memory_type=excluded.memory_type,
                  scope=excluded.scope,
                  title=excluded.title,
                  summary=excluded.summary,
                  keywords_json=excluded.keywords_json,
                  entities_json=excluded.entities_json,
                  source_refs_json=excluded.source_refs_json,
                  importance=excluded.importance,
                  confidence=excluded.confidence,
                  strength=excluded.strength,
                  freshness_ts=excluded.freshness_ts,
                  last_used_ts=excluded.last_used_ts,
                  ttl_days=excluded.ttl_days,
                  status=excluded.status,
                  auto_inject_level=excluded.auto_inject_level,
                  pollution_risk=excluded.pollution_risk,
                  delivery_options_json=excluded.delivery_options_json,
                  usage_count=excluded.usage_count,
                  updated_at=excluded.updated_at
                """,
                {
                    **row,
                    "keywords_json": json.dumps(row["keywords_json"], ensure_ascii=False),
                    "entities_json": json.dumps(row["entities_json"], ensure_ascii=False),
                    "source_refs_json": json.dumps(row["source_refs_json"], ensure_ascii=False),
                    "delivery_options_json": json.dumps(
                        row["delivery_options_json"], ensure_ascii=False
                    ),
                },
            )
            conn.commit()

    def load_memories(self, *, active_only: bool = True) -> list[MemoryItem]:
        query = "SELECT * FROM memory_items"
        params: tuple[Any, ...] = ()
        if active_only:
            query += " WHERE status = ?"
            params = ("active",)
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_memory(row) for row in rows]

    def update_usage(self, memory_id: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE memory_items
                SET usage_count = usage_count + 1,
                    last_used_ts = ?,
                    updated_at = ?
                WHERE memory_id = ?
                """,
                (utc_now_iso(), utc_now_iso(), memory_id),
            )
            conn.commit()

    def update_status(self, memory_id: str, status: str, layer: str | None = None) -> None:
        with self.connect() as conn:
            if layer:
                conn.execute(
                    "UPDATE memory_items SET status=?, layer=?, updated_at=? WHERE memory_id=?",
                    (status, layer, utc_now_iso(), memory_id),
                )
            else:
                conn.execute(
                    "UPDATE memory_items SET status=?, updated_at=? WHERE memory_id=?",
                    (status, utc_now_iso(), memory_id),
                )
            conn.commit()

    def delete_memories_by_scope(self, scope: str) -> int:
        with self.connect() as conn:
            cursor = conn.execute("DELETE FROM memory_items WHERE scope = ?", (scope,))
            conn.commit()
            return cursor.rowcount

    def insert_trace(self, trace: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO decision_traces (
                  trace_id, query_id, session_id, task_id, project_id, query_type,
                  state_snapshot_json, final_outcome_json, policy_version,
                  threshold_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trace["trace_id"],
                    trace["query_id"],
                    trace.get("session_id"),
                    trace.get("task_id"),
                    trace.get("project_id"),
                    trace["query_type"],
                    json.dumps(trace["state_snapshot"], ensure_ascii=False),
                    json.dumps(trace["final_outcome"], ensure_ascii=False),
                    trace["policy_version"],
                    trace["threshold_version"],
                    trace["created_at"],
                ),
            )
            for step in trace["policy_steps"]:
                conn.execute(
                    """
                    INSERT INTO trace_steps (
                      step_id, trace_id, step_order, step_name, decision,
                      reason_codes_json, scores_json, payload_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        step["step_id"],
                        trace["trace_id"],
                        step["step_order"],
                        step["step_name"],
                        step["decision"],
                        json.dumps(step.get("reason_codes", []), ensure_ascii=False),
                        json.dumps(step.get("scores", {}), ensure_ascii=False),
                        json.dumps(step.get("payload", {}), ensure_ascii=False),
                        trace["created_at"],
                    ),
                )
            conn.commit()

    def insert_cleanup_action(self, action: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO cleanup_actions (
                  action_id, memory_id, cleanup_action, cleanup_priority,
                  reason_codes_json, previous_layer, new_layer, policy_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action["action_id"],
                    action["memory_id"],
                    action["cleanup_action"],
                    action["cleanup_priority"],
                    json.dumps(action.get("reason_codes", []), ensure_ascii=False),
                    action.get("previous_layer"),
                    action.get("new_layer"),
                    action["policy_version"],
                    action["created_at"],
                ),
            )
            conn.commit()

    @staticmethod
    def _row_to_memory(row: sqlite3.Row) -> MemoryItem:
        return MemoryItem(
            memory_id=row["memory_id"],
            layer=row["layer"],
            memory_type=row["memory_type"],
            scope=row["scope"],
            title=row["title"] or "",
            summary=row["summary"],
            keywords=json.loads(row["keywords_json"] or "[]"),
            entities=json.loads(row["entities_json"] or "[]"),
            source_refs=json.loads(row["source_refs_json"] or "[]"),
            importance=row["importance"],
            confidence=row["confidence"],
            strength=row["strength"],
            freshness_ts=row["freshness_ts"],
            last_used_ts=row["last_used_ts"],
            ttl_days=row["ttl_days"],
            status=row["status"],
            auto_inject_level=row["auto_inject_level"],
            pollution_risk=row["pollution_risk"],
            delivery_options=json.loads(row["delivery_options_json"] or "{}"),
            usage_count=row["usage_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
