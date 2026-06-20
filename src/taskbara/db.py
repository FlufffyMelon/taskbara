import time
from typing import Optional
import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  hash        TEXT NOT NULL UNIQUE,
  chat_id     INTEGER NOT NULL,
  creator     TEXT NOT NULL,
  assignee    TEXT NOT NULL,
  body        TEXT NOT NULL,
  status      TEXT NOT NULL DEFAULT 'open',
  created_at  INTEGER NOT NULL,
  updated_at  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee);
CREATE INDEX IF NOT EXISTS idx_tasks_hash ON tasks(hash);

CREATE TABLE IF NOT EXISTS comments (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id     INTEGER NOT NULL REFERENCES tasks(id),
  author      TEXT NOT NULL,
  body        TEXT NOT NULL,
  created_at  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_comments_task ON comments(task_id);

CREATE TABLE IF NOT EXISTS chat_members (
  chat_id        INTEGER NOT NULL,
  username_lower TEXT NOT NULL,
  username       TEXT NOT NULL,
  PRIMARY KEY (chat_id, username_lower)
);
"""


async def init_db(db_path: str) -> None:
    """Initialize the database schema."""
    async with aiosqlite.connect(db_path) as conn:
        await conn.executescript(SCHEMA)
        await conn.commit()


async def create_task(
    db_path: str,
    hash_: str,
    chat_id: int,
    creator: str,
    assignee: str,
    body: str,
) -> dict:
    """Insert a new task and return it as a dict."""
    now = int(time.time())
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute(
            """
            INSERT INTO tasks (hash, chat_id, creator, assignee, body, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'open', ?, ?)
            """,
            (hash_, chat_id, creator, assignee, body, now, now),
        )
        await conn.commit()
        async with conn.execute(
            "SELECT * FROM tasks WHERE hash = ?", (hash_,)
        ) as cur:
            row = await cur.fetchone()
        return dict(row)


async def get_task_by_hash(db_path: str, hash_: str) -> Optional[dict]:
    """Return task dict or None if not found."""
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT * FROM tasks WHERE hash = ?", (hash_,)
        ) as cur:
            row = await cur.fetchone()
        return dict(row) if row else None


async def list_tasks_by_assignee(db_path: str, assignee: str) -> list[dict]:
    """Return tasks for assignee ordered: open first, then by created_at asc."""
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            """
            SELECT * FROM tasks WHERE assignee = ? COLLATE NOCASE
            ORDER BY
              CASE status WHEN 'open' THEN 0 ELSE 1 END,
              created_at ASC
            """,
            (assignee,),
        ) as cur:
            rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def update_task_body(db_path: str, hash_: str, body: str) -> bool:
    """Update task body. Returns True if a row was updated."""
    now = int(time.time())
    async with aiosqlite.connect(db_path) as conn:
        cur = await conn.execute(
            "UPDATE tasks SET body = ?, updated_at = ? WHERE hash = ?",
            (body, now, hash_),
        )
        await conn.commit()
        return cur.rowcount > 0


async def set_task_status(db_path: str, hash_: str, status: str) -> bool:
    """Set task status ('open' or 'done'). Returns True if a row was updated."""
    now = int(time.time())
    async with aiosqlite.connect(db_path) as conn:
        cur = await conn.execute(
            "UPDATE tasks SET status = ?, updated_at = ? WHERE hash = ?",
            (status, now, hash_),
        )
        await conn.commit()
        return cur.rowcount > 0


async def add_comment(
    db_path: str, hash_: str, author: str, body: str
) -> Optional[int]:
    """Add a comment to the task identified by hash. Returns comment id or None if task not found."""
    now = int(time.time())
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT id FROM tasks WHERE hash = ?", (hash_,)
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        task_id = row["id"]
        cur2 = await conn.execute(
            "INSERT INTO comments (task_id, author, body, created_at) VALUES (?, ?, ?, ?)",
            (task_id, author, body, now),
        )
        await conn.commit()
        return cur2.lastrowid


async def get_comments_for_task(db_path: str, hash_: str) -> list[dict]:
    """Return all comments for a task, ordered by created_at."""
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT id FROM tasks WHERE hash = ?", (hash_,)
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return []
        task_id = row["id"]
        async with conn.execute(
            "SELECT * FROM comments WHERE task_id = ? ORDER BY created_at ASC",
            (task_id,),
        ) as cur:
            rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def record_member(db_path: str, chat_id: int, username: str) -> None:
    """Remember that *username* has been seen in *chat_id* (case-insensitive key)."""
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            """
            INSERT INTO chat_members (chat_id, username_lower, username)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id, username_lower) DO UPDATE SET username = excluded.username
            """,
            (chat_id, username.lower(), username),
        )
        await conn.commit()


async def get_known_member(
    db_path: str, chat_id: int, username: str
) -> Optional[str]:
    """
    Look up a username among known members of a chat, case-insensitively.
    *username* may include a leading '@'. Returns the canonical '@username'
    (last-seen casing) if known, else None.
    """
    uname = username.lstrip("@").lower()
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT username FROM chat_members WHERE chat_id = ? AND username_lower = ?",
            (chat_id, uname),
        ) as cur:
            row = await cur.fetchone()
        return f"@{row['username']}" if row else None
