import sqlite3
from datetime import datetime, timezone
from typing import Optional

from models import MealResponse

DB_PATH = "history.db"


def init_db(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS generations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                response_json TEXT NOT NULL,
                favorite INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_generation(response: MealResponse, db_path: str = DB_PATH, created_at: Optional[str] = None) -> int:
    init_db(db_path)
    created_at = created_at or datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            "INSERT INTO generations (created_at, response_json, favorite) VALUES (?, ?, 0)",
            (created_at, response.model_dump_json()),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def list_history(db_path: str = DB_PATH, limit: int = 20) -> list[dict]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, created_at, response_json, favorite FROM generations ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "id": row[0],
            "created_at": row[1],
            "response": MealResponse.model_validate_json(row[2]),
            "favorite": bool(row[3]),
        }
        for row in rows
    ]


def toggle_favorite(entry_id: int, db_path: str = DB_PATH) -> None:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("UPDATE generations SET favorite = 1 - favorite WHERE id = ?", (entry_id,))
        conn.commit()
    finally:
        conn.close()
