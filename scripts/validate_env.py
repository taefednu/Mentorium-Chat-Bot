#!/usr/bin/env python3
"""
Environment validation script
Проверяет наличие всех необходимых переменных окружения перед запуском
"""
import os
import sys
from typing import List, Tuple


# Обязательные переменные
REQUIRED_VARS = [
    "BOT_TELEGRAM_TOKEN",
    "BOT_OPENAI_API_KEY",
    "DB_PASSWORD",
    "REDIS_PASSWORD",
]

# Обязательные для продакшена
PRODUCTION_VARS = [
    "PLATFORM_DB_HOST",
    "PLATFORM_DB_USER",
    "PLATFORM_DB_PASSWORD",
    "PLATFORM_DB_NAME",
]

# Опциональные но рекомендуемые
RECOMMENDED_VARS = [
    "SENTRY_DSN",
    "GIT_COMMIT",
    "LOG_LEVEL",
    "ENVIRONMENT",
]


def check_required_vars() -> List[str]:
    """Проверить обязательные переменные"""
    missing = []
    for var in REQUIRED_VARS:
        if not os.getenv(var):
            missing.append(var)
    return missing


def check_production_vars() -> List[str]:
    """Проверить переменные для продакшена"""
    environment = os.getenv("ENVIRONMENT", "development")
    if environment.lower() != "production":
        return []
    
    missing = []
    for var in PRODUCTION_VARS:
        if not os.getenv(var):
            missing.append(var)
    return missing


def check_recommended_vars() -> List[str]:
    """Проверить рекомендуемые переменные"""
    missing = []
    for var in RECOMMENDED_VARS:
        if not os.getenv(var):
            missing.append(var)
    return missing


def validate_database_urls() -> List[Tuple[str, str]]:
    """Валидировать формат database URLs"""
    errors = []
    
    # Проверяем BOT_DB_URL если есть
    bot_db_url = os.getenv("BOT_DB_URL")
    if bot_db_url and not bot_db_url.startswith("postgresql"):
        errors.append(("BOT_DB_URL", "должен начинаться с 'postgresql://' или 'postgresql+psycopg://'"))
    
    # Проверяем PLATFORM_DB_URL если есть
    platform_db_url = os.getenv("PLATFORM_DB_URL")
    if platform_db_url and not platform_db_url.startswith("postgresql"):
        errors.append(("PLATFORM_DB_URL", "должен начинаться с 'postgresql://' или 'postgresql+psycopg://'"))
    
    return errors


def validate_telegram_token() -> List[Tuple[str, str]]:
    """Валидировать формат Telegram токена"""
    errors = []
    token = os.getenv("BOT_TELEGRAM_TOKEN")
    
    if token:
        # Telegram token format: 1234567890:ABCdef...
        parts = token.split(":")
        if len(parts) != 2 or not parts[0].isdigit():
            errors.append(("BOT_TELEGRAM_TOKEN", "неверный формат (должно быть: 'bot_id:token')"))
    
    return errors


def validate_openai_key() -> List[Tuple[str, str]]:
    """Валидировать формат OpenAI API ключа"""
    errors = []
    key = os.getenv("BOT_OPENAI_API_KEY")
    
    if key and not key.startswith("sk-"):
        errors.append(("BOT_OPENAI_API_KEY", "должен начинаться с 'sk-'"))
    
    return errors


def main():
    """Запустить все проверки"""
    print("🔍 Проверка переменных окружения...")
    print()
    
    has_errors = False
    
    # 1. Обязательные переменные
    missing_required = check_required_vars()
    if missing_required:
        print("❌ ОШИБКА: Отсутствуют обязательные переменные:")
        for var in missing_required:
            print(f"   - {var}")
        print()
        has_errors = True
    else:
        print("✅ Все обязательные переменные присутствуют")
    
    # 2. Продакшен переменные
    missing_production = check_production_vars()
    if missing_production:
        print("❌ ОШИБКА: Отсутствуют переменные для продакшена:")
        for var in missing_production:
            print(f"   - {var}")
        print()
        has_errors = True
    
    # 3. Рекомендуемые переменные
    missing_recommended = check_recommended_vars()
    if missing_recommended:
        print("⚠️  ПРЕДУПРЕЖДЕНИЕ: Рекомендуется установить:")
        for var in missing_recommended:
            print(f"   - {var}")
        print()
    
    # 4. Валидация форматов
    validation_errors = []
    validation_errors.extend(validate_database_urls())
    validation_errors.extend(validate_telegram_token())
    validation_errors.extend(validate_openai_key())
    
    if validation_errors:
        print("❌ ОШИБКА: Неверный формат переменных:")
        for var, error in validation_errors:
            print(f"   - {var}: {error}")
        print()
        has_errors = True
    
    # 5. Информация об окружении
    print()
    print("📊 Информация об окружении:")
    print(f"   ENVIRONMENT: {os.getenv('ENVIRONMENT', 'не установлена')}")
    print(f"   LOG_LEVEL: {os.getenv('LOG_LEVEL', 'не установлена')}")
    print(f"   LOG_FORMAT: {os.getenv('LOG_FORMAT', 'не установлена')}")
    print(f"   SENTRY: {'включён' if os.getenv('SENTRY_DSN') else 'отключён'}")
    
    # Payment providers
    payme_configured = bool(os.getenv("BOT_PAYME_MERCHANT_ID"))
    click_configured = bool(os.getenv("BOT_CLICK_MERCHANT_ID"))
    print(f"   PayMe: {'настроен' if payme_configured else 'не настроен'}")
    print(f"   Click: {'настроен' if click_configured else 'не настроен'}")
    
    print()
    
    # Результат
    if has_errors:
        print("❌ Валидация не пройдена. Исправьте ошибки перед запуском.")
        sys.exit(1)
    else:
        print("✅ Валидация успешно пройдена! Можно запускать приложение.")
        sys.exit(0)


if __name__ == "__main__":
    main()
