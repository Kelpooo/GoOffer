"""Database initialization and helpers for OfferGo."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS visitors (
        visitor_id TEXT PRIMARY KEY,
        first_seen_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL,
        user_agent TEXT NOT NULL DEFAULT ''
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS visitor_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        visitor_id TEXT NOT NULL,
        path TEXT NOT NULL,
        user_agent TEXT NOT NULL DEFAULT '',
        visited_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS questions (
        id TEXT PRIMARY KEY,
        domain TEXT NOT NULL,
        section TEXT NOT NULL DEFAULT '',
        category TEXT NOT NULL DEFAULT '',
        difficulty TEXT NOT NULL DEFAULT 'mid',
        question TEXT NOT NULL,
        summary TEXT NOT NULL DEFAULT '',
        source_title TEXT NOT NULL DEFAULT '',
        source_url TEXT NOT NULL DEFAULT '',
        tags_json TEXT NOT NULL DEFAULT '[]',
        answer_points_json TEXT NOT NULL DEFAULT '[]',
        follow_ups_json TEXT NOT NULL DEFAULT '[]',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS question_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        visitor_id TEXT NOT NULL DEFAULT '',
        user_id TEXT NOT NULL DEFAULT '',
        question_id TEXT NOT NULL,
        favorite INTEGER NOT NULL DEFAULT 0,
        mastered INTEGER NOT NULL DEFAULT 0,
        practice_count INTEGER NOT NULL DEFAULT 0,
        last_practiced_at TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(visitor_id, question_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS learning_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scope_type TEXT NOT NULL,
        scope_id TEXT NOT NULL,
        question_id TEXT NOT NULL,
        favorite INTEGER NOT NULL DEFAULT 0,
        mastered INTEGER NOT NULL DEFAULT 0,
        practice_count INTEGER NOT NULL DEFAULT 0,
        last_practiced_at TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(scope_type, scope_id, question_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        username_normalized TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        password_salt TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_sessions (
        session_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        expires_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


def connect_sqlite(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(db_path: Path) -> None:
    with connect_sqlite(db_path) as conn:
        for statement in SCHEMA_STATEMENTS:
            conn.execute(statement)
        migrate_legacy_progress(conn)


def ensure_questions_seeded(db_path: Path, questions_path: Path) -> int:
    with connect_sqlite(db_path) as conn:
        existing_count = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        if int(existing_count or 0) > 0:
            return 0

    with questions_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    return upsert_questions_from_payload(db_path, payload)


def migrate_legacy_progress(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO learning_progress (
            scope_type,
            scope_id,
            question_id,
            favorite,
            mastered,
            practice_count,
            last_practiced_at,
            created_at,
            updated_at
        )
        SELECT
            'visitor',
            visitor_id,
            question_id,
            favorite,
            mastered,
            practice_count,
            last_practiced_at,
            created_at,
            updated_at
        FROM question_progress
        WHERE visitor_id <> ''
        ON CONFLICT(scope_type, scope_id, question_id) DO NOTHING
        """
    )


def upsert_questions_from_payload(db_path: Path, payload: dict[str, Any]) -> int:
    questions = payload.get("questions", [])
    count = 0
    with connect_sqlite(db_path) as conn:
        for item in questions:
            conn.execute(
                """
                INSERT INTO questions (
                    id, domain, section, category, difficulty, question, summary,
                    source_title, source_url, tags_json, answer_points_json, follow_ups_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    domain=excluded.domain,
                    section=excluded.section,
                    category=excluded.category,
                    difficulty=excluded.difficulty,
                    question=excluded.question,
                    summary=excluded.summary,
                    source_title=excluded.source_title,
                    source_url=excluded.source_url,
                    tags_json=excluded.tags_json,
                    answer_points_json=excluded.answer_points_json,
                    follow_ups_json=excluded.follow_ups_json
                """,
                (
                    item.get("id", ""),
                    item.get("domain", ""),
                    item.get("section", ""),
                    item.get("category", ""),
                    item.get("difficulty", "mid"),
                    item.get("question", ""),
                    item.get("summary", ""),
                    item.get("sourceTitle", ""),
                    item.get("sourceUrl", ""),
                    json.dumps(item.get("tags", []), ensure_ascii=False),
                    json.dumps(item.get("answerPoints", []), ensure_ascii=False),
                    json.dumps(item.get("followUps", []), ensure_ascii=False),
                ),
            )
            count += 1
    return count


def load_questions_payload(db_path: Path) -> dict[str, Any]:
    with connect_sqlite(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                id, domain, section, category, difficulty, question, summary,
                source_title, source_url, tags_json, answer_points_json, follow_ups_json
            FROM questions
            ORDER BY domain, category, id
            """
        ).fetchall()

    questions: list[dict[str, Any]] = []
    domain_counts: dict[str, dict[str, int]] = {}

    for row in rows:
        domain = row["domain"] or "other"
        category = row["category"] or "other"
        domain_counts.setdefault(domain, {})
        domain_counts[domain][category] = domain_counts[domain].get(category, 0) + 1

        questions.append(
            {
                "id": row["id"],
                "domain": domain,
                "section": row["section"] or "",
                "question": row["question"] or "",
                "category": category,
                "difficulty": row["difficulty"] or "mid",
                "tags": json.loads(row["tags_json"] or "[]"),
                "answerPoints": json.loads(row["answer_points_json"] or "[]"),
                "followUps": json.loads(row["follow_ups_json"] or "[]"),
                "summary": row["summary"] or "",
                "sourceTitle": row["source_title"] or "",
                "sourceUrl": row["source_url"] or "",
            }
        )

    return {
        "meta": {
            "total": len(questions),
            "domains": domain_counts,
        },
        "questions": questions,
    }


def _resolve_scope(visitor_id: str = "", user_id: str = "") -> tuple[str, str]:
    if user_id:
        return "user", user_id
    return "visitor", visitor_id


def _load_progress_payload(conn: sqlite3.Connection, scope_type: str, scope_id: str) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT question_id, favorite, mastered, practice_count, last_practiced_at
        FROM learning_progress
        WHERE scope_type = ? AND scope_id = ?
        """,
        (scope_type, scope_id),
    ).fetchall()

    favorites: list[str] = []
    mastered: list[str] = []
    practice: dict[str, dict[str, Any]] = {}

    for row in rows:
        question_id = row["question_id"]
        if row["favorite"]:
            favorites.append(question_id)
        if row["mastered"]:
            mastered.append(question_id)
        if row["practice_count"] or row["last_practiced_at"]:
            practice[question_id] = {
                "practiceCount": int(row["practice_count"] or 0),
                "lastPracticedAt": row["last_practiced_at"] or "",
            }

    return {
        "ok": True,
        "favorites": favorites,
        "mastered": mastered,
        "practice": practice,
    }


def get_user_progress_payload(db_path: Path, visitor_id: str = "", *, user_id: str = "") -> dict[str, Any]:
    scope_type, scope_id = _resolve_scope(visitor_id, user_id)
    with connect_sqlite(db_path) as conn:
        return _load_progress_payload(conn, scope_type, scope_id)


def upsert_question_progress(
    db_path: Path,
    visitor_id: str,
    question_id: str,
    *,
    user_id: str = "",
    favorite: bool | None = None,
    mastered: bool | None = None,
    practiced_at: str | None = None,
) -> dict[str, Any]:
    scope_type, scope_id = _resolve_scope(visitor_id, user_id)

    with connect_sqlite(db_path) as conn:
        existing = conn.execute(
            """
            SELECT favorite, mastered, practice_count, last_practiced_at
            FROM learning_progress
            WHERE scope_type = ? AND scope_id = ? AND question_id = ?
            """,
            (scope_type, scope_id, question_id),
        ).fetchone()

        current_favorite = int(existing["favorite"]) if existing else 0
        current_mastered = int(existing["mastered"]) if existing else 0
        current_practice_count = int(existing["practice_count"]) if existing else 0
        current_last_practiced_at = existing["last_practiced_at"] if existing else ""

        next_favorite = current_favorite if favorite is None else int(bool(favorite))
        next_mastered = current_mastered if mastered is None else int(bool(mastered))
        next_practice_count = current_practice_count + (1 if practiced_at else 0)
        next_last_practiced_at = practiced_at or current_last_practiced_at

        conn.execute(
            """
            INSERT INTO learning_progress (
                scope_type, scope_id, question_id, favorite, mastered, practice_count, last_practiced_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(scope_type, scope_id, question_id) DO UPDATE SET
                favorite=excluded.favorite,
                mastered=excluded.mastered,
                practice_count=excluded.practice_count,
                last_practiced_at=excluded.last_practiced_at,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                scope_type,
                scope_id,
                question_id,
                next_favorite,
                next_mastered,
                next_practice_count,
                next_last_practiced_at,
            ),
        )

    return {
        "ok": True,
        "questionId": question_id,
        "favorite": bool(next_favorite),
        "mastered": bool(next_mastered),
        "practiceCount": next_practice_count,
        "lastPracticedAt": next_last_practiced_at,
    }


def sync_user_progress(
    db_path: Path,
    visitor_id: str,
    favorites: list[str],
    mastered: list[str],
    *,
    user_id: str = "",
) -> dict[str, Any]:
    scope_type, scope_id = _resolve_scope(visitor_id, user_id)
    favorites_set = set(favorites or [])
    mastered_set = set(mastered or [])
    all_ids = favorites_set | mastered_set

    with connect_sqlite(db_path) as conn:
        for question_id in all_ids:
            conn.execute(
                """
                INSERT INTO learning_progress (
                    scope_type, scope_id, question_id, favorite, mastered, updated_at
                )
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(scope_type, scope_id, question_id) DO UPDATE SET
                    favorite=excluded.favorite,
                    mastered=excluded.mastered,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    scope_type,
                    scope_id,
                    question_id,
                    int(question_id in favorites_set),
                    int(question_id in mastered_set),
                ),
            )
        return _load_progress_payload(conn, scope_type, scope_id)


def merge_progress_into_user(db_path: Path, visitor_id: str, user_id: str) -> dict[str, Any]:
    if not visitor_id or not user_id:
        return get_user_progress_payload(db_path, user_id=user_id)

    with connect_sqlite(db_path) as conn:
        rows = conn.execute(
            """
            SELECT question_id, favorite, mastered, practice_count, last_practiced_at
            FROM learning_progress
            WHERE scope_type = 'visitor' AND scope_id = ?
            """,
            (visitor_id,),
        ).fetchall()

        for row in rows:
            existing = conn.execute(
                """
                SELECT favorite, mastered, practice_count, last_practiced_at
                FROM learning_progress
                WHERE scope_type = 'user' AND scope_id = ? AND question_id = ?
                """,
                (user_id, row["question_id"]),
            ).fetchone()

            favorite = max(int(row["favorite"] or 0), int(existing["favorite"] or 0) if existing else 0)
            mastered = max(int(row["mastered"] or 0), int(existing["mastered"] or 0) if existing else 0)
            practice_count = int(row["practice_count"] or 0) + (int(existing["practice_count"] or 0) if existing else 0)
            last_practiced_at = max(
                row["last_practiced_at"] or "",
                (existing["last_practiced_at"] or "") if existing else "",
            )

            conn.execute(
                """
                INSERT INTO learning_progress (
                    scope_type, scope_id, question_id, favorite, mastered, practice_count, last_practiced_at, updated_at
                )
                VALUES ('user', ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(scope_type, scope_id, question_id) DO UPDATE SET
                    favorite=excluded.favorite,
                    mastered=excluded.mastered,
                    practice_count=excluded.practice_count,
                    last_practiced_at=excluded.last_practiced_at,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    user_id,
                    row["question_id"],
                    favorite,
                    mastered,
                    practice_count,
                    last_practiced_at,
                ),
            )

        conn.execute(
            """
            DELETE FROM learning_progress
            WHERE scope_type = 'visitor' AND scope_id = ?
            """,
            (visitor_id,),
        )
        return _load_progress_payload(conn, "user", user_id)


def create_user(
    db_path: Path,
    *,
    user_id: str,
    username: str,
    username_normalized: str,
    password_hash: str,
    password_salt: str,
    now_iso: str,
) -> dict[str, Any]:
    with connect_sqlite(db_path) as conn:
        conn.execute(
            """
            INSERT INTO users (id, username, username_normalized, password_hash, password_salt, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, username, username_normalized, password_hash, password_salt, now_iso, now_iso),
        )
        row = conn.execute(
            """
            SELECT id, username, created_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
    return _serialize_user(row)


def get_user_by_username(db_path: Path, username_normalized: str) -> dict[str, Any] | None:
    with connect_sqlite(db_path) as conn:
        row = conn.execute(
            """
            SELECT id, username, username_normalized, password_hash, password_salt, status, created_at
            FROM users
            WHERE username_normalized = ?
            """,
            (username_normalized,),
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(db_path: Path, user_id: str) -> dict[str, Any] | None:
    with connect_sqlite(db_path) as conn:
        row = conn.execute(
            """
            SELECT id, username, created_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
    return _serialize_user(row) if row else None


def get_user_auth_record_by_id(db_path: Path, user_id: str) -> dict[str, Any] | None:
    with connect_sqlite(db_path) as conn:
        row = conn.execute(
            """
            SELECT id, username, username_normalized, password_hash, password_salt, status, created_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def update_user_password(db_path: Path, user_id: str, password_hash: str, password_salt: str) -> None:
    with connect_sqlite(db_path) as conn:
        conn.execute(
            """
            UPDATE users
            SET password_hash = ?, password_salt = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (password_hash, password_salt, user_id),
        )


def get_account_overview(db_path: Path, user_id: str) -> dict[str, Any]:
    with connect_sqlite(db_path) as conn:
        summary_row = conn.execute(
            """
            SELECT
                SUM(CASE WHEN favorite = 1 THEN 1 ELSE 0 END) AS favorite_count,
                SUM(CASE WHEN mastered = 1 THEN 1 ELSE 0 END) AS mastered_count,
                SUM(practice_count) AS practice_total,
                SUM(CASE WHEN practice_count > 0 THEN 1 ELSE 0 END) AS practiced_question_count
            FROM learning_progress
            WHERE scope_type = 'user' AND scope_id = ?
            """,
            (user_id,),
        ).fetchone()

        recent_rows = conn.execute(
            """
            SELECT
                lp.question_id,
                lp.favorite,
                lp.mastered,
                lp.practice_count,
                lp.last_practiced_at,
                q.question,
                q.domain,
                q.section,
                q.category,
                q.difficulty
            FROM learning_progress lp
            LEFT JOIN questions q ON q.id = lp.question_id
            WHERE lp.scope_type = 'user'
              AND lp.scope_id = ?
              AND lp.practice_count > 0
            ORDER BY lp.last_practiced_at DESC, lp.updated_at DESC
            LIMIT 20
            """,
            (user_id,),
        ).fetchall()

    summary = {
        "favoriteCount": int(summary_row["favorite_count"] or 0),
        "masteredCount": int(summary_row["mastered_count"] or 0),
        "practiceTotal": int(summary_row["practice_total"] or 0),
        "practicedQuestionCount": int(summary_row["practiced_question_count"] or 0),
    }

    recent_records = [
        {
            "questionId": row["question_id"],
            "question": row["question"] or row["question_id"],
            "domain": row["domain"] or "other",
            "section": row["section"] or "",
            "category": row["category"] or "",
            "difficulty": row["difficulty"] or "mid",
            "favorite": bool(row["favorite"]),
            "mastered": bool(row["mastered"]),
            "practiceCount": int(row["practice_count"] or 0),
            "lastPracticedAt": row["last_practiced_at"] or "",
        }
        for row in recent_rows
    ]

    return {
        "ok": True,
        "summary": summary,
        "recentPractice": recent_records,
    }


def create_auth_session(db_path: Path, *, session_id: str, user_id: str, expires_at: str, now_iso: str) -> None:
    with connect_sqlite(db_path) as conn:
        conn.execute(
            """
            INSERT INTO auth_sessions (session_id, user_id, expires_at, last_seen_at, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, user_id, expires_at, now_iso, now_iso),
        )


def get_auth_session_user(db_path: Path, session_id: str, now_iso: str) -> dict[str, Any] | None:
    with connect_sqlite(db_path) as conn:
        row = conn.execute(
            """
            SELECT s.session_id, s.expires_at, u.id, u.username, u.status, u.created_at
            FROM auth_sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.session_id = ?
            """,
            (session_id,),
        ).fetchone()

        if not row:
            return None
        if (row["status"] or "active") != "active":
            conn.execute("DELETE FROM auth_sessions WHERE session_id = ?", (session_id,))
            return None
        if (row["expires_at"] or "") <= now_iso:
            conn.execute("DELETE FROM auth_sessions WHERE session_id = ?", (session_id,))
            return None

        conn.execute(
            """
            UPDATE auth_sessions
            SET last_seen_at = ?
            WHERE session_id = ?
            """,
            (now_iso, session_id),
        )
        return {
            "id": row["id"],
            "username": row["username"],
            "createdAt": normalize_db_timestamp(row["created_at"]),
        }


def delete_auth_session(db_path: Path, session_id: str) -> None:
    with connect_sqlite(db_path) as conn:
        conn.execute("DELETE FROM auth_sessions WHERE session_id = ?", (session_id,))


def _serialize_user(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "createdAt": normalize_db_timestamp(row["created_at"]),
    }


def normalize_db_timestamp(value: str | None) -> str:
    if not value:
        return ""

    raw = str(value).strip()
    if not raw:
        return ""

    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return raw

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()
