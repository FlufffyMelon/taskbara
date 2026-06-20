import time
import pytest
import aiosqlite
from taskbara.db import (
    init_db,
    create_task,
    get_task_by_hash,
    list_tasks_by_assignee,
    update_task_body,
    set_task_status,
    add_comment,
    get_comments_for_task,
    record_member,
    get_known_member,
)


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


async def test_init_db(db_path):
    """init_db should create tables without error, and be idempotent."""
    await init_db(db_path)
    await init_db(db_path)  # second call should not raise


async def test_create_and_fetch_task(db_path):
    await init_db(db_path)
    task = await create_task(
        db_path,
        hash_="4951cd3",
        chat_id=100,
        creator="@oryabkov",
        assignee="@avoiko",
        body="Fix the login bug",
    )
    assert task["hash"] == "4951cd3"
    assert task["creator"] == "@oryabkov"
    assert task["assignee"] == "@avoiko"
    assert task["body"] == "Fix the login bug"
    assert task["status"] == "open"

    fetched = await get_task_by_hash(db_path, "4951cd3")
    assert fetched is not None
    assert fetched["hash"] == "4951cd3"


async def test_get_task_not_found(db_path):
    await init_db(db_path)
    result = await get_task_by_hash(db_path, "0000000")
    assert result is None


async def test_list_tasks_by_assignee_ordering(db_path):
    await init_db(db_path)
    now = int(time.time())

    # Create tasks: done first, then open — ordering should reverse them
    await create_task(db_path, "aaaaaaa", 1, "@a", "@avoiko", "First task (done)")
    await create_task(db_path, "bbbbbbb", 1, "@a", "@avoiko", "Second task (open)")
    await create_task(db_path, "ccccccc", 1, "@a", "@avoiko", "Third task (open)")

    # Mark first one done
    await set_task_status(db_path, "aaaaaaa", "done")

    tasks = await list_tasks_by_assignee(db_path, "@avoiko")
    assert len(tasks) == 3

    # Open tasks come first
    statuses = [t["status"] for t in tasks]
    open_indices = [i for i, s in enumerate(statuses) if s == "open"]
    done_indices = [i for i, s in enumerate(statuses) if s == "done"]
    assert max(open_indices) < min(done_indices)


async def test_list_tasks_empty(db_path):
    await init_db(db_path)
    tasks = await list_tasks_by_assignee(db_path, "@nobody")
    assert tasks == []


async def test_update_task_body(db_path):
    await init_db(db_path)
    await create_task(db_path, "4951cd3", 1, "@a", "@b", "Old body")

    updated = await update_task_body(db_path, "4951cd3", "New body")
    assert updated is True

    task = await get_task_by_hash(db_path, "4951cd3")
    assert task["body"] == "New body"


async def test_update_nonexistent_task_body(db_path):
    await init_db(db_path)
    updated = await update_task_body(db_path, "0000000", "Body")
    assert updated is False


async def test_set_task_status(db_path):
    await init_db(db_path)
    await create_task(db_path, "4951cd3", 1, "@a", "@b", "body")

    result = await set_task_status(db_path, "4951cd3", "done")
    assert result is True

    task = await get_task_by_hash(db_path, "4951cd3")
    assert task["status"] == "done"

    result2 = await set_task_status(db_path, "4951cd3", "open")
    assert result2 is True

    task2 = await get_task_by_hash(db_path, "4951cd3")
    assert task2["status"] == "open"


async def test_set_status_nonexistent(db_path):
    await init_db(db_path)
    result = await set_task_status(db_path, "0000000", "done")
    assert result is False


async def test_add_and_fetch_comments(db_path):
    await init_db(db_path)
    await create_task(db_path, "4951cd3", 1, "@a", "@b", "body")

    cid1 = await add_comment(db_path, "4951cd3", "@oryabkov", "First comment")
    cid2 = await add_comment(db_path, "4951cd3", "@avoiko", "Second comment")

    assert cid1 is not None
    assert cid2 is not None

    comments = await get_comments_for_task(db_path, "4951cd3")
    assert len(comments) == 2
    assert comments[0]["author"] == "@oryabkov"
    assert comments[0]["body"] == "First comment"
    assert comments[1]["author"] == "@avoiko"
    assert comments[1]["body"] == "Second comment"


async def test_add_comment_to_nonexistent_task(db_path):
    await init_db(db_path)
    result = await add_comment(db_path, "0000000", "@user", "comment")
    assert result is None


async def test_get_comments_no_comments(db_path):
    await init_db(db_path)
    await create_task(db_path, "4951cd3", 1, "@a", "@b", "body")
    comments = await get_comments_for_task(db_path, "4951cd3")
    assert comments == []


async def test_get_comments_nonexistent_task(db_path):
    await init_db(db_path)
    comments = await get_comments_for_task(db_path, "0000000")
    assert comments == []


async def test_member_lookup_case_insensitive(db_path):
    await init_db(db_path)
    await record_member(db_path, 1, "FlufffyMelon")

    # any casing resolves to the canonical last-seen username
    assert await get_known_member(db_path, 1, "@flufffymelon") == "@FlufffyMelon"
    assert await get_known_member(db_path, 1, "@FLUFFFYMELON") == "@FlufffyMelon"
    assert await get_known_member(db_path, 1, "flufffymelon") == "@FlufffyMelon"


async def test_member_unknown_returns_none(db_path):
    await init_db(db_path)
    await record_member(db_path, 1, "alice")
    assert await get_known_member(db_path, 1, "@bob") is None


async def test_member_scoped_per_chat(db_path):
    await init_db(db_path)
    await record_member(db_path, 1, "alice")
    assert await get_known_member(db_path, 2, "@alice") is None


async def test_member_upsert_updates_casing(db_path):
    await init_db(db_path)
    await record_member(db_path, 1, "alice")
    await record_member(db_path, 1, "Alice")  # same user, new casing
    assert await get_known_member(db_path, 1, "@alice") == "@Alice"


async def test_list_tasks_assignee_case_insensitive(db_path):
    await init_db(db_path)
    await create_task(db_path, "4951cd3", 1, "@a", "@FlufffyMelon", "body")
    tasks = await list_tasks_by_assignee(db_path, "@flufffymelon")
    assert len(tasks) == 1
