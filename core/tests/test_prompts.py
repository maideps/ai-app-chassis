import pytest

from ai_app_chassis import PromptNotFoundError, PromptStore


def write(root, rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_latest_is_the_highest_version_number(tmp_path):
    write(tmp_path, "greet/v2/user.txt", "v2 {name}")
    write(tmp_path, "greet/v10/user.txt", "Hello {name}")
    write(tmp_path, "greet/v10/system.txt", "Be brief.")
    store = PromptStore(tmp_path)
    assert store.versions("greet") == ["v2", "v10"]
    prompt = store.load("greet")
    assert prompt.id == "greet/v10"
    messages = prompt.render(name="Ada")
    pairs = [(m.role, m.content) for m in messages]
    assert pairs == [("system", "Be brief."), ("user", "Hello Ada")]


def test_a_pinned_version_without_system_prompt(tmp_path):
    write(tmp_path, "greet/v1/user.txt", "Hi {name}")
    [message] = PromptStore(tmp_path).load("greet", "v1").render(name="Bo")
    assert (message.role, message.content) == ("user", "Hi Bo")


def test_missing_prompts_raise(tmp_path):
    with pytest.raises(PromptNotFoundError):
        PromptStore(tmp_path).load("nope")
    write(tmp_path, "half/v1/system.txt", "only a system prompt")
    with pytest.raises(PromptNotFoundError):
        PromptStore(tmp_path).load("half")
