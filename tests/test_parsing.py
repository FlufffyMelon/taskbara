import pytest
from taskbara.parsing import (
    split_message,
    extract_mentions,
    extract_hash,
    parse_addtask,
    parse_tasks_arg,
    parse_addcomment,
)


class TestSplitMessage:
    def test_single_line(self):
        first, body = split_message("/addtask @user")
        assert first == "/addtask @user"
        assert body == ""

    def test_multiline(self):
        first, body = split_message("/addtask @user\nHere is the task body\nmore text")
        assert first == "/addtask @user"
        assert body == "Here is the task body\nmore text"

    def test_strips_whitespace(self):
        first, body = split_message("  /addtask @user  \n  body here  ")
        assert first == "/addtask @user"
        assert body == "body here"


class TestExtractMentions:
    def test_no_mention(self):
        assert extract_mentions("hello world") == []

    def test_single_mention(self):
        assert extract_mentions("/addtask @alice") == ["@alice"]

    def test_two_mentions(self):
        assert extract_mentions("/addtask @alice to @bob") == ["@alice", "@bob"]

    def test_mention_with_underscore(self):
        assert extract_mentions("@john_doe") == ["@john_doe"]


class TestExtractHash:
    def test_valid_hash(self):
        assert extract_hash("/task 4951cd3") == "4951cd3"

    def test_no_hash(self):
        assert extract_hash("/task") is None

    def test_hash_in_text(self):
        assert extract_hash("/done a1b2c3d") == "a1b2c3d"

    def test_too_short(self):
        assert extract_hash("/done abc123") is None

    def test_too_long_not_matched_as_7(self):
        # 8 hex chars should not match
        result = extract_hash("/done 4951cd3a")
        # The regex is \b[0-9a-f]{7}\b so 4951cd3a would not match as a 7-char word
        assert result is None


class TestParseAddtask:
    def test_two_mentions_with_to(self):
        creator, assignee, error = parse_addtask(
            "/addtask @oryabkov to @avoiko", "Fix the bug", "@sender"
        )
        assert error is None
        assert creator == "@oryabkov"
        assert assignee == "@avoiko"

    def test_two_mentions_with_to_case_insensitive(self):
        creator, assignee, error = parse_addtask(
            "/addtask @alice TO @bob", "Do something", "@sender"
        )
        assert error is None
        assert creator == "@alice"
        assert assignee == "@bob"

    def test_single_mention_uses_sender(self):
        creator, assignee, error = parse_addtask(
            "/addtask @avoiko", "Task body", "@oryabkov"
        )
        assert error is None
        assert creator == "@oryabkov"
        assert assignee == "@avoiko"

    def test_no_mention_returns_error(self):
        creator, assignee, error = parse_addtask("/addtask", "Task body", "@sender")
        assert error is not None
        assert creator is None
        assert assignee is None

    def test_empty_body_returns_error(self):
        creator, assignee, error = parse_addtask("/addtask @user", "", "@sender")
        assert error is not None

    def test_body_empty_string(self):
        _, _, error = parse_addtask("/addtask @alice to @bob", "", "@sender")
        assert error is not None


class TestParseTasksArg:
    def test_with_mention(self):
        result = parse_tasks_arg("/tasks @avoiko", "@sender")
        assert result == "@avoiko"

    def test_without_mention_returns_sender(self):
        result = parse_tasks_arg("/tasks", "@sender")
        assert result == "@sender"


class TestParseAddcomment:
    def test_valid(self):
        hash_, error = parse_addcomment("/addcomment 4951cd3 Great work!")
        assert error is None
        assert hash_ == "4951cd3"

    def test_missing_hash(self):
        hash_, error = parse_addcomment("/addcomment")
        assert hash_ is None
        assert error is not None

    def test_missing_text(self):
        hash_, error = parse_addcomment("/addcomment 4951cd3")
        assert hash_ is None
        assert error is not None

    def test_invalid_hash_format(self):
        hash_, error = parse_addcomment("/addcomment ZZZZZZZ text")
        assert hash_ is None
        assert error is not None
