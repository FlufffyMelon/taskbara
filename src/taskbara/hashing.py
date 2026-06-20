import secrets
import aiosqlite


def _generate_hash() -> str:
    """Generate a 7-char hex hash."""
    return secrets.token_hex(4)[:7]


async def generate_unique_hash(conn: aiosqlite.Connection) -> str:
    """Generate a hash that doesn't yet exist in tasks.hash."""
    while True:
        h = _generate_hash()
        async with conn.execute("SELECT 1 FROM tasks WHERE hash = ?", (h,)) as cur:
            row = await cur.fetchone()
        if row is None:
            return h
