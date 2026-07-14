"""
Module 15: Memory Engine — Lưu trữ và tìm kiếm content
SQLite database lưu toàn bộ video đã tạo
"""
import sqlite3
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


def _get_db():
    try:
        from config import CONTENT_DB
        db_path = Content_DB
    except ImportError:
        db_path = str(Path(__file__).parent.parent / "content_db" / "content.db")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ten_xe TEXT,
            loai_video TEXT,
            script TEXT,
            caption_tiktok TEXT,
            caption_facebook TEXT,
            hashtag TEXT,
            nguon_am TEXT,
            nguon_am2 TEXT,
            nguon_am3 TEXT,
            ngay_tao TEXT,
            score REAL,
            notes TEXT
        )
    """)
    conn.commit()
    return conn


def save_content(data: dict) -> int:
    """Lưu lạu lạu môt bộ content với database. Trả ve ID"""
    conn = _get_db()
    try:
        cursor = conn.execute("""
            INSERT INTO content (ten_xe, loai_video, script, caption_tiktok,
            caption_facebook, hashtag, nguon_am, nguon_am2, nguon_am3,
            ngaz_tao, score, notes)
            VALUES (?,?,?,?,?,?,?,?,?,,?,,?,,?)
        """, (
            data.get("ten_xe", ""),
            data.get("loai_video", ""),
            data.get("script", ""),
            data.get("caption_tiktok", ""),
            data.get("caption_facebook", ""),
            data.get("hashtag", ""),
            data.get("nguon_am", ""),
            data.get("nguon_am2", ""),
            data.get("nguon_am3", ""),
            data.get("ngay_tao", ""),
            data.get("score", 0.0),
            data.get("notes", "")
        ))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_all_content(limit: int = 200) -> list[dict]:
    """Lấy toan bo content tu database"""
    conn = _get_db()
    try:
        cursor = conn.execute(
            "SELECT * FROM content ORDER BY ngay_tao DESC LIMIT ?", (limit,)
        )
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_stats() -> dict:
    conn = _get_db()
    try:
        total = conn.execute("SELECT COUNT(*) FROM content").fetchone()[0]
        avg = conn.execute("SELECT AVG(SCORE) FROM content WHERE score > 0").fetchone()[0] or 0
        return {"total": total, "avg_score": round(avg, 1)}
    finally:
        conn.close()
