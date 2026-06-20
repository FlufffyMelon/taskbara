import re
from typing import Optional


# ── helpers ──────────────────────────────────────────────────────────────────

def _strip_command(text: str) -> str:
    """Remove the leading /command (or /command@bot) token from *text*."""
    return re.sub(r"^\s*/\w+(?:@\w+)?\s*", "", text, count=1)


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
    text: str,
    sender: str,
) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Parse the /addtask command from the full message text.

    Returns (creator, assignee, body, error). On success error is None.
    The task body may be written right after the mention(s) on the same line
    or on following lines; surrounding whitespace/newlines are trimmed.

    Forms:
      /addtask @from to @to <body>   → creator=@from, assignee=@to
      /addtask @to <body>            → creator=sender, assignee=@to
    """
    rest = _strip_command(text)

    m = re.match(r"\s*(@\w+)\s+to\s+(@\w+)(.*)", rest, re.IGNORECASE | re.DOTALL)
    if m:
        creator, assignee, body = m.group(1), m.group(2), m.group(3)
    else:
        m = re.match(r"\s*(@\w+)(.*)", rest, re.DOTALL)
        if not m:
            return None, None, None, "no_mention"
        assignee, body = m.group(1), m.group(2)
        creator = sender

    body = body.strip()
    if not body:
        return None, None, None, "empty_body"

    return creator, assignee, body, None


# ── /tasks ────────────────────────────────────────────────────────────────────

def parse_tasks_arg(first_line: str, sender: str) -> str:
    """
    Parse the /tasks command line. Returns the target @user.
    If no mention found, returns sender.
    """
    mentions = extract_mentions(first_line)
    return mentions[0] if mentions else sender


# ── /addcomment ───────────────────────────────────────────────────────────────

def _parse_hash_and_text(
    text: str, usage_msg: str, empty_msg: str
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse '<command> <hash> <text...>' from the full message text.

    The text may follow the hash on the same line or on following lines;
    surrounding whitespace/newlines are trimmed.
    Returns (hash, text, error). On success error is None.
    """
    rest = _strip_command(text)
    m = re.match(r"\s*(\S+)(.*)", rest, re.DOTALL)
    if not m:
        return None, None, usage_msg
    token, payload = m.group(1), m.group(2).strip()
    if not re.fullmatch(r"[0-9a-f]{7}", token):
        return None, None, f"Неверный формат хэша: {token}"
    if not payload:
        return None, None, empty_msg
    return token, payload, None


def parse_addcomment(
    text: str,
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Parse /addcomment <hash> <text...>. Returns (hash, comment_text, error)."""
    return _parse_hash_and_text(
        text,
        "Использование: /addcomment хэш текст",
        "Текст комментария не может быть пустым.",
    )


def parse_edit(
    text: str,
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Parse /edit <hash> <new text...>. Returns (hash, new_body, error)."""
    return _parse_hash_and_text(
        text,
        "Использование: /edit хэш новый текст",
        "Укажи новый текст задачи.",
    )
