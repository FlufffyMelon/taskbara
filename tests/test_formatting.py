import pytest
from taskbara.formatting import (
    fmt_task_created,
    fmt_task_list,
    fmt_task_detail,
    fmt_task_updated,
    fmt_task_done,
    fmt_task_reopened,
    fmt_comment_added,
    fmt_not_found,
    fmt_help,
    BODY_TRUNCATE_LEN,
)


def make_task(hash_="4951cd3", creator="@oryabkov", assignee="@avoiko",
              body="Fix the login bug", status="open", chat_id=1,
              created_at=1000, updated_at=1000):
    return {
        "id": 1,
        "hash": hash_,
        "chat_id": chat_id,
        "creator": creator,
        "assignee": assignee,
        "body": body,
        "status": status,
        "created_at": created_at,
        "updated_at": updated_at,
    }


class TestFmtTaskCreated:
    def test_basic(self):
        result = fmt_task_created("4951cd3", "@oryabkov", "@avoiko", "Fix the bug")
        assert "Создана задача 4951cd3" in result
        assert "кому: @avoiko" in result
        assert "от: @oryabkov" in result
        assert "Fix the bug" in result

    def test_format(self):
        result = fmt_task_created("4951cd3", "@a", "@b", "body")
        lines = result.split("\n")
        assert lines[0] == "Создана задача 4951cd3"
        assert "@b" in lines[1] and "@a" in lines[1]


class TestFmtTaskList:
    def test_no_tasks(self):
        result = fmt_task_list("@user", [])
        assert result == "Нет задач"

    def test_open_tasks_only(self):
        tasks = [make_task(hash_="aaa1111", status="open", body="First task")]
        result = fmt_task_list("@avoiko", tasks)
        assert "Задачи @avoiko" in result
        assert "Открытые" in result
        assert "aaa1111" in result
        assert "Сделано" not in result

    def test_done_tasks_only(self):
        tasks = [make_task(hash_="bbb2222", status="done", body="Done task")]
        result = fmt_task_list("@avoiko", tasks)
        assert "Сделано" in result
        assert "Открытые" not in result

    def test_both_statuses(self):
        tasks = [
            make_task(hash_="aaa1111", status="open", body="Open task"),
            make_task(hash_="bbb2222", status="done", body="Done task"),
        ]
        result = fmt_task_list("@avoiko", tasks)
        assert "Открытые" in result
        assert "Сделано" in result
        assert "aaa1111" in result
        assert "bbb2222" in result

    def test_body_truncation(self):
        long_body = "A" * 60
        tasks = [make_task(hash_="aaa1111", status="open", body=long_body)]
        result = fmt_task_list("@avoiko", tasks)
        assert "…" in result
        # truncated to 50 chars + ellipsis
        assert "A" * BODY_TRUNCATE_LEN in result
        assert "A" * (BODY_TRUNCATE_LEN + 1) not in result

    def test_body_truncation_first_line_only(self):
        body = "First line\nSecond line"
        tasks = [make_task(hash_="aaa1111", status="open", body=body)]
        result = fmt_task_list("@avoiko", tasks)
        assert "First line" in result
        assert "Second line" not in result


class TestFmtTaskDetail:
    def test_open_task_no_comments(self):
        task = make_task(status="open")
        result = fmt_task_detail(task, [])
        assert "4951cd3 – открыта" in result
        assert "кому: @avoiko" in result
        assert "от: @oryabkov" in result
        assert "Fix the login bug" in result
        assert "Комментарии:" not in result

    def test_done_task(self):
        task = make_task(status="done")
        result = fmt_task_detail(task, [])
        assert "– сделано" in result

    def test_with_comments(self):
        task = make_task()
        comments = [
            {"id": 1, "task_id": 1, "author": "@oryabkov", "body": "Great job", "created_at": 1001},
            {"id": 2, "task_id": 1, "author": "@avoiko", "body": "Thanks!", "created_at": 1002},
        ]
        result = fmt_task_detail(task, comments)
        assert "Комментарии:" in result
        assert "@oryabkov: Great job" in result
        assert "@avoiko: Thanks!" in result


class TestConfirmations:
    def test_updated(self):
        assert fmt_task_updated("4951cd3") == "Задача 4951cd3 обновлена"

    def test_done(self):
        assert fmt_task_done("4951cd3") == "Задача 4951cd3 – сделано"

    def test_reopened(self):
        assert fmt_task_reopened("4951cd3") == "Задача 4951cd3 снова открыта"

    def test_comment_added(self):
        assert fmt_comment_added("4951cd3") == "Комментарий добавлен к 4951cd3"

    def test_not_found(self):
        assert fmt_not_found("4951cd3") == "Задача 4951cd3 не найдена"


class TestHelp:
    def test_lists_all_commands(self):
        result = fmt_help()
        for cmd in ("/addtask", "/tasks", "/task", "/edit", "/done", "/reopen", "/addcomment", "/help"):
            assert cmd in result
