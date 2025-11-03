"""
Тесты для ParentRepository
"""
import pytest
from mentorium_db.repositories import ParentRepository
from mentorium_db.session import get_session


@pytest.mark.asyncio
async def test_create_parent():
    """Тест создания родителя"""
    async with get_session() as session:
        repo = ParentRepository(session)
        parent = await repo.create(
            telegram_id=123456789,
            first_name="Иван",
            last_name="Петров",
            username="ivan_p",
            email="ivan@example.com",
        )

        assert parent.id is not None
        assert parent.telegram_id == 123456789
        assert parent.first_name == "Иван"
        assert parent.is_active is True


@pytest.mark.asyncio
async def test_get_by_telegram_id():
    """Тест получения родителя по Telegram ID"""
    async with get_session() as session:
        repo = ParentRepository(session)

        # Создаём родителя
        created = await repo.create(telegram_id=987654321, first_name="Test")

        # Ищем по telegram_id
        found = await repo.get_by_telegram_id(987654321)

        assert found is not None
        assert found.id == created.id
        assert found.telegram_id == 987654321


@pytest.mark.asyncio
async def test_deactivate_parent():
    """Тест деактивации родителя"""
    async with get_session() as session:
        repo = ParentRepository(session)
        parent = await repo.create(telegram_id=111222333, first_name="Test")

        assert parent.is_active is True

        # Деактивируем
        success = await repo.deactivate(parent.id)
        assert success is True

        # Проверяем
        updated = await repo.get_by_id(parent.id)
        assert updated is not None
        assert updated.is_active is False
