"""SQLite 存储层。

表结构：
- books:    统一书架（跨数据源合并后的记录）
- notes:    划线/想法（微信读书源）
- chapters: 章节目录（微信读书源）

NAS 侧存的是"同步快照"，供设备端随时拉取，无需再请求微信读书。
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from typing import Iterator, Optional

from . import config
from .models import ChapterRow, NoteRow

_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
  id             TEXT PRIMARY KEY,
  source         TEXT NOT NULL,
  source_book_id TEXT NOT NULL,
  title          TEXT NOT NULL DEFAULT '',
  author         TEXT NOT NULL DEFAULT '',
  category       TEXT NOT NULL DEFAULT '',
  has_epub       INTEGER NOT NULL DEFAULT 0,
  epub_path      TEXT NOT NULL DEFAULT '',
  cover_url      TEXT NOT NULL DEFAULT '',
  progress       REAL NOT NULL DEFAULT 0,
  read_update_time INTEGER NOT NULL DEFAULT 0,
  summary        TEXT NOT NULL DEFAULT '',
  synced_at      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS notes (
  book_id     TEXT NOT NULL,
  bookmark_id TEXT NOT NULL DEFAULT '',
  mark_text   TEXT NOT NULL DEFAULT '',
  range       TEXT NOT NULL DEFAULT '',
  chapter_uid INTEGER NOT NULL DEFAULT 0,
  create_time INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (book_id, bookmark_id)
);

CREATE TABLE IF NOT EXISTS chapters (
  book_id     TEXT NOT NULL,
  chapter_uid INTEGER NOT NULL,
  chapter_idx INTEGER NOT NULL DEFAULT 0,
  title       TEXT NOT NULL DEFAULT '',
  word_count  INTEGER NOT NULL DEFAULT 0,
  paid        INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (book_id, chapter_uid)
);

CREATE INDEX IF NOT EXISTS idx_books_source ON books(source);
CREATE INDEX IF NOT EXISTS idx_notes_book ON notes(book_id);
CREATE INDEX IF NOT EXISTS idx_chapters_book ON chapters(book_id);
"""


def init() -> None:
    with _conn() as conn:
        conn.executescript(_SCHEMA)


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    with _lock:
        conn = sqlite3.connect(config.DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


# --------------------------------------------------------------------------- books

def upsert_book(
    book_id: str,
    source: str,
    source_book_id: str,
    title: str,
    author: str = "",
    category: str = "",
    has_epub: bool = False,
    epub_path: str = "",
    cover_url: str = "",
    progress: float = 0.0,
    read_update_time: int = 0,
    summary: str = "",
) -> None:
    with _conn() as conn:
        conn.execute(
            """INSERT INTO books
               (id, source, source_book_id, title, author, category,
                has_epub, epub_path, cover_url, progress, read_update_time,
                summary, synced_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 source=excluded.source,
                 source_book_id=excluded.source_book_id,
                 title=excluded.title,
                 author=excluded.author,
                 category=excluded.category,
                 has_epub=excluded.has_epub,
                 epub_path=excluded.epub_path,
                 cover_url=excluded.cover_url,
                 summary=excluded.summary,
                 synced_at=excluded.synced_at
            """,
            (book_id, source, source_book_id, title, author, category,
             int(has_epub), epub_path, cover_url, progress, read_update_time,
             summary, _now()),
        )


def list_books(source: Optional[str] = None) -> list[dict]:
    with _conn() as conn:
        if source:
            rows = conn.execute("SELECT * FROM books WHERE source=? ORDER BY synced_at DESC", (source,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM books ORDER BY synced_at DESC").fetchall()
        return [dict(r) for r in rows]


def get_book(book_id: str) -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        return dict(row) if row else None


def update_progress(book_id: str, progress: float, read_update_time: int = 0) -> None:
    with _conn() as conn:
        now = read_update_time or _now()
        conn.execute(
            "UPDATE books SET progress=?, read_update_time=? WHERE id=?",
            (progress, now, book_id),
        )


def delete_book(book_id: str) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM books WHERE id=?", (book_id,))
        conn.execute("DELETE FROM notes WHERE book_id=?", (book_id,))
        conn.execute("DELETE FROM chapters WHERE book_id=?", (book_id,))


# --------------------------------------------------------------------------- notes / chapters

def replace_notes(book_id: str, notes: list[NoteRow]) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM notes WHERE book_id=?", (book_id,))
        conn.executemany(
            "INSERT OR REPLACE INTO notes (book_id, bookmark_id, mark_text, range, chapter_uid, create_time) "
            "VALUES (?,?,?,?,?,?)",
            [(book_id, n.bookmark_id, n.mark_text, n.range, n.chapter_uid, n.create_time) for n in notes],
        )


def get_notes(book_id: str) -> list[NoteRow]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM notes WHERE book_id=? ORDER BY create_time", (book_id,)).fetchall()
        return [NoteRow(**dict(r)) for r in rows]


def replace_chapters(book_id: str, chapters: list[ChapterRow]) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM chapters WHERE book_id=?", (book_id,))
        conn.executemany(
            "INSERT OR REPLACE INTO chapters (book_id, chapter_uid, chapter_idx, title, word_count, paid) "
            "VALUES (?,?,?,?,?,?)",
            [(book_id, c.chapter_uid, c.chapter_idx, c.title, c.word_count, c.paid) for c in chapters],
        )


def get_chapters(book_id: str) -> list[ChapterRow]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM chapters WHERE book_id=? ORDER BY chapter_idx", (book_id,)).fetchall()
        return [ChapterRow(**dict(r)) for r in rows]


def _now() -> int:
    import time

    return int(time.time())