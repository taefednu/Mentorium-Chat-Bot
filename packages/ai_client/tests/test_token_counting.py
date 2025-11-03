"""Тесты для token counting и trimming"""
import pytest

from mentorium_ai_client import DialogMessage, MentoriumAIClient, StudentContext


@pytest.fixture
def ai_client():
    """Создаём клиента с фейковым API key для тестов"""
    return MentoriumAIClient(api_key="sk-test-key")


def test_count_tokens(ai_client):
    """Проверяем подсчёт токенов"""
    text = "Hello world"
    tokens = ai_client.count_tokens(text)
    assert tokens > 0
    assert isinstance(tokens, int)


def test_trim_messages_preserves_system(ai_client):
    """System prompt всегда сохраняется при trimming"""
    messages = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello" * 1000},  # Очень длинное сообщение
        {"role": "assistant", "content": "Hi there"},
    ]

    trimmed = ai_client.trim_messages_to_fit(messages, max_tokens=50)

    # System prompt должен остаться
    assert trimmed[0]["role"] == "system"
    assert trimmed[0]["content"] == "You are a helpful assistant"

    # Остальные сообщения могут быть обрезаны
    assert len(trimmed) >= 1


def test_trim_messages_keeps_recent(ai_client):
    """При trimming сохраняются последние сообщения"""
    messages = [
        {"role": "system", "content": "System"},
        {"role": "user", "content": "Message 1"},
        {"role": "assistant", "content": "Reply 1"},
        {"role": "user", "content": "Message 2"},
        {"role": "assistant", "content": "Reply 2"},
        {"role": "user", "content": "Message 3"},
    ]

    trimmed = ai_client.trim_messages_to_fit(messages, max_tokens=100)

    # Последнее сообщение должно быть "Message 3"
    assert trimmed[-1]["content"] == "Message 3"
    assert trimmed[-1]["role"] == "user"


def test_build_system_prompt_general(ai_client):
    """Проверяем формирование обычного system prompt"""
    prompt = ai_client.build_system_prompt(scenario="general")

    assert "Mentorium" in prompt
    assert "наставник" in prompt
    assert len(prompt) > 100


def test_build_system_prompt_with_context(ai_client):
    """System prompt должен включать контекст ученика"""
    context = StudentContext(
        student_name="Алиса",
        age=12,
        courses=[{"name": "Python", "progress": 45, "lessons_completed": 10}],
        recent_tests=[{"name": "Variables", "score": 85, "passed": True}],
        activity_days=15,
        last_activity="2024-01-15",
    )

    prompt = ai_client.build_system_prompt(scenario="progress", student_context=context)

    assert "Алиса" in prompt
    assert "12 лет" in prompt
    assert "Python" in prompt
    assert "45%" in prompt
    assert "Variables" in prompt


def test_build_system_prompt_scenarios(ai_client):
    """Разные сценарии дают разные промпты"""
    general = ai_client.build_system_prompt(scenario="general")
    welcome = ai_client.build_system_prompt(scenario="welcome")
    progress = ai_client.build_system_prompt(scenario="progress")
    recommendations = ai_client.build_system_prompt(scenario="recommendations")

    # Все должны содержать базовую информацию
    for prompt in [general, welcome, progress, recommendations]:
        assert "Mentorium" in prompt

    # Но различаться в деталях
    assert "зарегистрировался" in welcome
    assert "прогресс" in progress.lower()
    assert "рекомендации" in recommendations.lower()


def test_dialog_message_creation():
    """Проверяем создание DialogMessage"""
    msg = DialogMessage(role="user", content="Hello", timestamp="2024-01-15 12:00:00")

    assert msg.role == "user"
    assert msg.content == "Hello"
    assert msg.timestamp == "2024-01-15 12:00:00"


def test_student_context_creation():
    """Проверяем создание StudentContext"""
    context = StudentContext(
        student_name="Test",
        age=10,
        courses=[],
        recent_tests=[],
        activity_days=5,
        last_activity=None,
    )

    assert context.student_name == "Test"
    assert context.age == 10
    assert context.activity_days == 5
