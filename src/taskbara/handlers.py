import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Router
from aiogram.filters import Command
from aiogram.types import Message, TelegramObject

from .db import (
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
from .hashing import generate_unique_hash
from .parsing import (
    split_message,
    parse_addtask,
    parse_tasks_arg,
    parse_addcomment,
    extract_hash,
)
from .formatting import (
    fmt_task_created,
    fmt_task_list,
    fmt_task_detail,
    fmt_task_updated,
    fmt_task_done,
    fmt_task_reopened,
    fmt_comment_added,
    fmt_not_found,
    fmt_addtask_usage,
    fmt_unknown_members,
    fmt_help,
)

import aiosqlite

logger = logging.getLogger(__name__)

router = Router()


class MemberTrackingMiddleware(BaseMiddleware):
    """Record every message sender (with a username) as a known chat member."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        user = event.from_user
        chat = event.chat
        if user is not None and user.username and chat is not None:
            try:
                await record_member(self.db_path, chat.id, user.username)
            except Exception:
                logger.exception("failed to record chat member")
        return await handler(event, data)


def _sender_identity(message: Message) -> str:
    """Return sender as @username, first_name, or id:<num>."""
    user = message.from_user
    if user is None:
        return "unknown"
    if user.username:
        return f"@{user.username}"
    if user.first_name:
        return user.first_name
    return f"id:{user.id}"


@router.message(Command("help", "start"))
async def cmd_help(message: Message) -> None:
    logger.info("help requested by %s", _sender_identity(message))
    await message.reply(fmt_help(), parse_mode="HTML")


@router.message(Command("addtask"))
async def cmd_addtask(message: Message, db_path: str) -> None:
    sender = _sender_identity(message)
    text = message.text or ""
    first_line, body = split_message(text)

    creator, assignee, error = parse_addtask(first_line, body, sender)
    if error:
        logger.warning("addtask parse error from %s: %s", sender, error)
        await message.reply(fmt_addtask_usage())
        return

    # Validate @mentions against known chat members (case-insensitive),
    # auto-correcting casing. Non-mention values (sender without a username)
    # are passed through unchecked.
    unknown: list[str] = []
    canonical: dict[str, str] = {}
    for name in {assignee, creator}:
        if not name.startswith("@"):
            continue
        match = await get_known_member(db_path, message.chat.id, name)
        if match is None:
            unknown.append(name)
        else:
            canonical[name] = match

    if unknown:
        logger.warning("addtask: unknown members %s from %s", unknown, sender)
        await message.reply(fmt_unknown_members(unknown))
        return

    assignee = canonical.get(assignee, assignee)
    creator = canonical.get(creator, creator)

    async with aiosqlite.connect(db_path) as conn:
        hash_ = await generate_unique_hash(conn)

    task = await create_task(
        db_path,
        hash_=hash_,
        chat_id=message.chat.id,
        creator=creator,
        assignee=assignee,
        body=body,
    )
    logger.info("Task %s created by %s for %s", hash_, creator, assignee)
    await message.reply(fmt_task_created(hash_, creator, assignee, body))


@router.message(Command("tasks"))
async def cmd_tasks(message: Message, db_path: str) -> None:
    sender = _sender_identity(message)
    text = message.text or ""
    first_line, _ = split_message(text)

    target = parse_tasks_arg(first_line, sender)
    tasks = await list_tasks_by_assignee(db_path, target)
    logger.info("tasks query for %s by %s: %d results", target, sender, len(tasks))
    await message.reply(fmt_task_list(target, tasks))


@router.message(Command("task"))
async def cmd_task(message: Message, db_path: str) -> None:
    sender = _sender_identity(message)
    text = message.text or ""
    first_line, _ = split_message(text)

    hash_ = extract_hash(first_line)
    if not hash_:
        logger.warning("task: no hash provided by %s", sender)
        await message.reply("Использование: /task <хэш>")
        return

    task = await get_task_by_hash(db_path, hash_)
    if not task:
        logger.warning("task: hash %s not found (requested by %s)", hash_, sender)
        await message.reply(fmt_not_found(hash_))
        return

    comments = await get_comments_for_task(db_path, hash_)
    logger.info("task %s viewed by %s", hash_, sender)
    await message.reply(fmt_task_detail(task, comments))


@router.message(Command("edit"))
async def cmd_edit(message: Message, db_path: str) -> None:
    sender = _sender_identity(message)
    text = message.text or ""
    first_line, body = split_message(text)

    hash_ = extract_hash(first_line)
    if not hash_:
        logger.warning("edit: no hash provided by %s", sender)
        await message.reply("Использование: /edit <хэш>\n<новый текст>")
        return

    if not body:
        await message.reply("Укажи новый текст задачи в теле сообщения.")
        return

    updated = await update_task_body(db_path, hash_, body)
    if not updated:
        logger.warning("edit: hash %s not found (by %s)", hash_, sender)
        await message.reply(fmt_not_found(hash_))
        return

    logger.info("Task %s body updated by %s", hash_, sender)
    await message.reply(fmt_task_updated(hash_))


@router.message(Command("done"))
async def cmd_done(message: Message, db_path: str) -> None:
    sender = _sender_identity(message)
    text = message.text or ""
    first_line, _ = split_message(text)

    hash_ = extract_hash(first_line)
    if not hash_:
        logger.warning("done: no hash provided by %s", sender)
        await message.reply("Использование: /done <хэш>")
        return

    updated = await set_task_status(db_path, hash_, "done")
    if not updated:
        logger.warning("done: hash %s not found (by %s)", hash_, sender)
        await message.reply(fmt_not_found(hash_))
        return

    logger.info("Task %s marked done by %s", hash_, sender)
    await message.reply(fmt_task_done(hash_))


@router.message(Command(commands=["reopen", "всефигнядавайпоновой"]))
async def cmd_reopen(message: Message, db_path: str) -> None:
    sender = _sender_identity(message)
    text = message.text or ""
    first_line, _ = split_message(text)

    hash_ = extract_hash(first_line)
    if not hash_:
        logger.warning("reopen: no hash provided by %s", sender)
        await message.reply("Использование: /reopen <хэш>")
        return

    updated = await set_task_status(db_path, hash_, "open")
    if not updated:
        logger.warning("reopen: hash %s not found (by %s)", hash_, sender)
        await message.reply(fmt_not_found(hash_))
        return

    logger.info("Task %s reopened by %s", hash_, sender)
    await message.reply(fmt_task_reopened(hash_))


@router.message(Command("addcomment"))
async def cmd_addcomment(message: Message, db_path: str) -> None:
    sender = _sender_identity(message)
    text = message.text or ""
    first_line, _ = split_message(text)

    hash_, error = parse_addcomment(first_line)
    if error:
        logger.warning("addcomment parse error from %s: %s", sender, error)
        await message.reply(error)
        return

    comment_id = await add_comment(db_path, hash_, sender, _extract_comment_body(first_line, hash_))
    if comment_id is None:
        logger.warning("addcomment: hash %s not found (by %s)", hash_, sender)
        await message.reply(fmt_not_found(hash_))
        return

    logger.info("Comment added to task %s by %s", hash_, sender)
    await message.reply(fmt_comment_added(hash_))


def _extract_comment_body(first_line: str, hash_: str) -> str:
    """Extract the comment text portion from '/addcomment <hash> <text>'."""
    parts = first_line.split(None, 2)
    return parts[2] if len(parts) >= 3 else ""
