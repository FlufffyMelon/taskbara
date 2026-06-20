import html
from datetime import datetime

BODY_TRUNCATE_LEN = 50


def _truncate_body(body: str) -> str:
    """Take first line of body, truncate to BODY_TRUNCATE_LEN chars."""
    first_line = body.split("\n", 1)[0].strip()
    if len(first_line) > BODY_TRUNCATE_LEN:
        return first_line[:BODY_TRUNCATE_LEN] + "…"
    return first_line


def _status_label(status: str) -> str:
    return "открыта" if status == "open" else "сделано"


# ── Task created ──────────────────────────────────────────────────────────────

def fmt_task_created(hash_: str, creator: str, assignee: str, body: str) -> str:
    return f"Создана задача {hash_}\nкому: {assignee}   от: {creator}\n\n{body}"


# ── Task list ─────────────────────────────────────────────────────────────────

def _fmt_date(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime("%d.%m.%Y")


def _fmt_task_group(tasks: list[dict]) -> list[str]:
    """Render tasks (assumed newest-first) with date subheaders and copyable hashes."""
    lines: list[str] = []
    current_date = None
    for t in tasks:
        date = _fmt_date(t["created_at"])
        if date != current_date:
            lines.append(f"  {date}")
            current_date = date
        body = html.escape(_truncate_body(t["body"]))
        lines.append(f"<code>{t['hash']}</code>  {body}")
    return lines


def fmt_task_list(assignee: str, tasks: list[dict]) -> str:
    if not tasks:
        return "Нет задач"

    open_tasks = [t for t in tasks if t["status"] == "open"]
    done_tasks = [t for t in tasks if t["status"] == "done"]

    lines = [f"Задачи {html.escape(assignee)}", ""]

    if open_tasks:
        lines.append("Открытые")
        lines.extend(_fmt_task_group(open_tasks))
        lines.append("")

    if done_tasks:
        lines.append("Сделано")
        lines.extend(_fmt_task_group(done_tasks))
        lines.append("")

    # remove trailing blank line
    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


# ── Task detail ───────────────────────────────────────────────────────────────

def fmt_task_detail(task: dict, comments: list[dict]) -> str:
    label = _status_label(task["status"])
    lines = [
        f"{task['hash']} – {label}",
        f"кому: {task['assignee']}   от: {task['creator']}",
        "",
        task["body"],
    ]

    if comments:
        lines.append("")
        lines.append("Комментарии:")
        for c in comments:
            lines.append(f"  {c['author']}: {c['body']}")

    return "\n".join(lines)


# ── Short confirmations ───────────────────────────────────────────────────────

def fmt_task_updated(hash_: str) -> str:
    return f"Задача {hash_} обновлена"


def fmt_task_done(hash_: str) -> str:
    return f"Задача {hash_} – сделано"


def fmt_task_reopened(hash_: str) -> str:
    return f"Задача {hash_} снова открыта"


def fmt_comment_added(hash_: str) -> str:
    return f"Комментарий добавлен к {hash_}"


# ── Not found ─────────────────────────────────────────────────────────────────

def fmt_not_found(hash_: str) -> str:
    return f"Задача {hash_} не найдена"


# ── Usage hints ───────────────────────────────────────────────────────────────

def fmt_help() -> str:
    return (
        "<b>taskbara</b> – трекер задач прямо в чате.\n"
        "\n"
        "<b>Создать задачу</b>\n"
        "/addtask @кому текст\n"
        "/addtask @от to @кому текст\n"
        "<i>текст задачи – с новой строки под командой</i>\n"
        "\n"
        "<b>Посмотреть</b>\n"
        "/tasks @кто – задачи пользователя\n"
        "/tasks – твои задачи\n"
        "/task хэш – задача и комментарии\n"
        "\n"
        "<b>Статус</b>\n"
        "/done хэш – пометить сделанной\n"
        "/reopen хэш – вернуть в открытые\n"
        "\n"
        "<b>Редактирование</b>\n"
        "/edit хэш текст – заменить текст\n"
        "/addcomment хэш текст – добавить комментарий\n"
        "/help – эта справка"
    )


def fmt_unknown_members(usernames: list[str]) -> str:
    names = ", ".join(usernames)
    return (
        f"Не нашёл среди участников чата: {names}\n"
        "Проверь ник или попроси человека написать что-нибудь в чат."
    )


def fmt_addtask_usage() -> str:
    return (
        "Использование:\n"
        "/addtask @кому текст задачи\n"
        "или\n"
        "/addtask @от to @кому текст задачи\n\n"
        "Текст задачи – в теле сообщения (новая строка после команды)."
    )
