import re
from typing import Optional


# ── helpers ──────────────────────────────────────────────────────────────────

def split_message(text: str) -> tuple[str, str]:
    """
    Split a message into (first_line, body).
    first_line is the text of line 0 (may include the /command itself).
    body is the rest (lines 1+), stripped.
    """
    lines = text.split("\n", 1)
    first_line = lines[0].strip()
    body = lines[1].strip() if len(lines) > 1 else ""
    return first_line, body


def extract_mentions(text: str) -> list[str]:
    """Return all @mention strings found in *text*, in order."""
    return re.findall(r"@\w+", text)


def extract_hash(text: str) -> Optional[str]:
    """
    Extract a 7-hex-char hash token from text.
    Looks for a standalone word matching [0-9a-f]{7}.
    Returns the first match or None.
    """
    m = re.search(r"\b([0-9a-f]{7})\b", text)
    return m.group(1) if m else None


# ── /addtask ─────────────────────────────────────────────────────────────────

def parse_addtask(
    first_line: str,
    body: str,
    sender: str,
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse the /addtask command.

    Returns (creator, assignee, error_message).
    On success error_message is None; on failure creator/assignee may be None.

    Forms:
      /addtask @from to @to   → creator=@from, assignee=@to
      /addtask @to            → creator=sender, assignee=@to
    """
    if not body:
        return None, None, "Укажи текст задачи (тело сообщения под командой)."

    mentions = extract_mentions(first_line)

    if len(mentions) == 0:
        return None, None, "Укажи хотя бы одного пользователя: /addtask @кому или /addtask @от to @кому"

    if len(mentions) >= 2:
        # Check for "from to to" pattern: two mentions with literal "to" between them
        # Pattern: @X ... to ... @Y  (case-insensitive 'to')
        pattern = r"(@\w+)\s+to\s+(@\w+)"
        m = re.search(pattern, first_line, re.IGNORECASE)
        if m:
            creator = m.group(1)
            assignee = m.group(2)
        else:
            # fallback: first mention is assignee, creator = sender
            assignee = mentions[0]
            creator = sender
    else:
        # Single mention → assignee, creator = sender
        assignee = mentions[0]
        creator = sender

    return creator, assignee, None


# ── /tasks ────────────────────────────────────────────────────────────────────

def parse_tasks_arg(first_line: str, sender: str) -> str:
    """
    Parse the /tasks command line. Returns the target @user.
    If no mention found, returns sender.
    """
    mentions = extract_mentions(first_line)
    return mentions[0] if mentions else sender


# ── /addcomment ───────────────────────────────────────────────────────────────

def parse_addcomment(first_line: str) -> tuple[Optional[str], Optional[str]]:
    """
    Parse /addcomment <hash> текст...
    Returns (hash, comment_text) or (None, error).
    """
    # Strip the command itself (first token)
    parts = first_line.split(None, 2)  # ['/addcomment', hash, text]
    if len(parts) < 3:
        return None, "Использование: /addcomment <хэш> <текст>"
    hash_ = parts[1]
    if not re.fullmatch(r"[0-9a-f]{7}", hash_):
        return None, f"Неверный формат хэша: {hash_}"
    comment_text = parts[2].strip()
    if not comment_text:
        return None, "Текст комментария не может быть пустым."
    return hash_, None
