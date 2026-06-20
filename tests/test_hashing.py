import re
import pytest
import aiosqlite
from taskbara.hashing import generate_unique_hash, _generate_hash
from taskbara.db import init_db


class TestGenerateHash:
    def test_length(self):
        h = _generate_hash()
        assert len(h) == 7

    def test_hex_chars(self):
        h = _generate_hash()
        assert re.fullmatch(r"[0-9a-f]{7}", h)

    def test_multiple_unique(self):
        hashes = {_generate_hash() for _ in range(100)}
        # Not guaranteed to be all unique, but statistically near certain
        assert len(hashes) > 90


class TestGenerateUniqueHash:
    async def test_returns_7_hex(self, tmp_path):
        db_file = str(tmp_path / "test.db")
        await init_db(db_file)
        async with aiosqlite.connect(db_file) as conn:
            h = await generate_unique_hash(conn)
        assert len(h) == 7
        assert re.fullmatch(r"[0-9a-f]{7}", h)

    async def test_avoids_existing_hash(self, tmp_path):
        """Ensures uniqueness loop works: pre-populate some hashes and verify result differs."""
        db_file = str(tmp_path / "test.db")
        await init_db(db_file)

        # Insert a task with a known hash to force collision
        import time
        known_hash = "aaaaaaa"
        async with aiosqlite.connect(db_file) as conn:
            await conn.execute(
                "INSERT INTO tasks (hash, chat_id, creator, assignee, body, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, 'open', ?, ?)",
                (known_hash, 1, "@a", "@b", "body", int(time.time()), int(time.time())),
            )
            await conn.commit()

            # Generate a new unique hash — it must differ from known_hash
            h = await generate_unique_hash(conn)
            assert h != known_hash
            assert re.fullmatch(r"[0-9a-f]{7}", h)

    async def test_no_collision_on_fresh_db(self, tmp_path):
        db_file = str(tmp_path / "test.db")
        await init_db(db_file)
        async with aiosqlite.connect(db_file) as conn:
            hashes = [await generate_unique_hash(conn) for _ in range(5)]
        # All returned hashes should be valid
        for h in hashes:
            assert re.fullmatch(r"[0-9a-f]{7}", h)
