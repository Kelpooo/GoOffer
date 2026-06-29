"""Storage abstractions used by the current OfferGo backend."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any

from offergo_backend.database import connect_sqlite


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_json_file(path: Path, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        return default


def save_json_file(path: Path, payload: Any) -> None:
    ensure_parent_dir(path)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
    temp_path.replace(path)


class FileVisitorTracker:
    def __init__(self, stats_path: Path, now_factory):
        self.stats_path = stats_path
        self.now_factory = now_factory
        self.lock = Lock()

    def _default_stats(self) -> dict[str, Any]:
        return {
            "total_visits": 0,
            "unique_visitors": {},
            "path_counts": {},
            "last_visit_at": "",
        }

    def _load(self) -> dict[str, Any]:
        return load_json_file(self.stats_path, self._default_stats())

    def _save(self, payload: dict[str, Any]) -> None:
        save_json_file(self.stats_path, payload)

    def track_visit(self, visitor_id: str, path: str, user_agent: str = "") -> None:
        now = self.now_factory()
        with self.lock:
            stats = self._load()
            stats["total_visits"] = int(stats.get("total_visits", 0)) + 1
            stats["last_visit_at"] = now

            path_counts = stats.setdefault("path_counts", {})
            path_counts[path] = int(path_counts.get(path, 0)) + 1

            visitors = stats.setdefault("unique_visitors", {})
            record = visitors.get(visitor_id)
            if record:
                record["last_seen_at"] = now
                if user_agent and not record.get("user_agent"):
                    record["user_agent"] = user_agent[:160]
            else:
                visitors[visitor_id] = {
                    "first_seen_at": now,
                    "last_seen_at": now,
                    "user_agent": user_agent[:160],
                }

            self._save(stats)

    def get_public_stats(self) -> dict[str, Any]:
        with self.lock:
            stats = self._load()
        path_counts = stats.get("path_counts", {})
        return {
            "ok": True,
            "totalVisits": int(stats.get("total_visits", 0)),
            "uniqueVisitors": len(stats.get("unique_visitors", {})),
            "homeVisits": int(path_counts.get("/web_mvp/", 0)),
            "lastVisitAt": stats.get("last_visit_at", ""),
            "storageMode": "file",
        }


class InMemoryResumeSessionStore:
    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    def save(self, resume_id: str, record: dict[str, Any]) -> None:
        self._records[resume_id] = record

    def get(self, resume_id: str) -> dict[str, Any] | None:
        return self._records.get(resume_id)


class SqliteVisitorTracker:
    def __init__(self, db_path: Path, now_factory):
        self.db_path = db_path
        self.now_factory = now_factory
        self.lock = Lock()
        self.storage_mode = "postgres" if isinstance(db_path, str) and db_path.startswith(("postgres://", "postgresql://")) else "sqlite"

    def track_visit(self, visitor_id: str, path: str, user_agent: str = "") -> None:
        now = self.now_factory()
        with self.lock:
            with connect_sqlite(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO visitor_events (visitor_id, path, user_agent, visited_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (visitor_id, path, user_agent[:160], now),
                )

                existing = conn.execute(
                    "SELECT visitor_id, first_seen_at, user_agent FROM visitors WHERE visitor_id = ?",
                    (visitor_id,),
                ).fetchone()
                if existing:
                    conn.execute(
                        """
                        UPDATE visitors
                        SET last_seen_at = ?, user_agent = CASE WHEN user_agent = '' THEN ? ELSE user_agent END
                        WHERE visitor_id = ?
                        """,
                        (now, user_agent[:160], visitor_id),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO visitors (visitor_id, first_seen_at, last_seen_at, user_agent)
                        VALUES (?, ?, ?, ?)
                        """,
                        (visitor_id, now, now, user_agent[:160]),
                    )

    def get_public_stats(self) -> dict[str, Any]:
        with self.lock:
            with connect_sqlite(self.db_path) as conn:
                total_visits_row = conn.execute("SELECT COUNT(*) AS total_visits FROM visitor_events").fetchone()
                unique_visitors_row = conn.execute("SELECT COUNT(*) AS unique_visitors FROM visitors").fetchone()
                home_visits = conn.execute(
                    "SELECT COUNT(*) AS home_visits FROM visitor_events WHERE path = ?",
                    ("/web_mvp/",),
                ).fetchone()
                last_visit_at_row = conn.execute(
                    "SELECT visited_at FROM visitor_events ORDER BY id DESC LIMIT 1"
                ).fetchone()
        return {
            "ok": True,
            "totalVisits": int((total_visits_row["total_visits"] if total_visits_row else 0) or 0),
            "uniqueVisitors": int((unique_visitors_row["unique_visitors"] if unique_visitors_row else 0) or 0),
            "homeVisits": int((home_visits["home_visits"] if home_visits else 0) or 0),
            "lastVisitAt": last_visit_at_row["visited_at"] if last_visit_at_row else "",
            "storageMode": self.storage_mode,
        }
