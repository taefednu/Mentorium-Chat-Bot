# Mentorium Chat Bot - Обзор проекта

## 📋 Описание

Telegram-бот для платформы Mentorium, который помогает родителям отслеживать прогресс своих детей в обучении. Бот предоставляет AI-диалоги с наставником, генерирует отчёты о прогрессе, управляет подписками и платежами.

## 🏗️ Архитектура проекта

Проект построен как **монорепозиторий** (все сервисы в одном репозитории) с использованием **Poetry** для управления зависимостями.

```
Mentorium-Chat-Bot/
├── apps/                    # Приложения (сервисы)
├── packages/                # Переиспользуемые библиотеки
├── docs/                    # Документация
├── scripts/                 # Вспомогательные скрипты
├── tests/                   # Тесты
├── docker-compose.yml       # Оркестрация контейнеров
├── Dockerfile              # Сборка Docker-образа
├── Makefile                # Команды для разработки
└── pyproject.toml          # Зависимости и конфигурация
```

---

## 📁 Структура директорий

### `/apps` - Приложения

Основные сервисы проекта:

#### 1. **telegram_bot** - Telegram бот (основной сервис)
```
apps/telegram_bot/mentorium_bot/
├── handlers/              # Обработчики команд и событий
│   ├── start.py          # /start, регистрация
│   ├── dialog.py         # AI-диалоги с наставником
│   ├── report.py         # Запрос отчётов
│   ├── billing.py        # Подписки и тарифы
│   └── webhooks.py       # Вебхуки от платёжных систем
├── middleware/            # Промежуточные обработчики
│   └── subscription.py   # Проверка активной подписки
├── services/              # Бизнес-логика
│   ├── ai_dialog_service.py      # Работа с AI (OpenAI)
│   ├── billing_service.py        # Управление подписками
│   └── payment/                  # Интеграция с платёжками
│       ├── payme.py             # PayMe (Узбекистан)
│       ├── click.py             # Click (Узбекистан)
│       └── telegram_stars.py    # Telegram Stars
├── states/                # FSM состояния для диалогов
├── config.py             # Настройки бота (из .env)
├── main.py               # Точка входа (polling)
└── webhook_app.py        # FastAPI для webhooks (порт 8001)
```

**Что делает:**
- Принимает команды от пользователей в Telegram
- Общается с OpenAI для AI-диалогов
- Управляет подписками (создание, продление, отмена)
- Принимает webhooks от платёжных систем (PayMe, Click)
- Отправляет уведомления родителям

**Запуск:**
```bash
make dev                    # Локальная разработка
docker-compose up bot       # В Docker
```

---

#### 2. **reporting_worker** - Фоновый планировщик отчётов
```
apps/reporting_worker/mentorium_reporting/
├── jobs/                  # Периодические задачи
│   ├── weekly_reports.py  # Еженедельные отчёты (понедельник 9:00)
│   └── monthly_reports.py # Ежемесячные отчёты (1-е число)
├── config.py             # Настройки воркера
└── main.py               # APScheduler + задачи
```

**Что делает:**
- По расписанию генерирует отчёты о прогрессе
- Отправляет отчёты родителям через Telegram
- Использует OpenAI для адаптации тона сообщений

**Запуск:**
```bash
python -m mentorium_reporting.main
```

---

### `/packages` - Переиспользуемые библиотеки

Общий код, который используется в разных приложениях:

#### 1. **ai_client** - Клиент для работы с OpenAI
```
packages/ai_client/mentorium_ai_client/
├── client.py             # Основной класс MentoriumAIClient
├── prompts.py            # Системные промпты для AI
└── utils.py              # Подсчёт токенов, retry-логика
```

**Возможности:**
- Генерация ответов от AI-наставника
- Подсчёт токенов (tiktoken)
- Автоматические повторы при ошибках (tenacity)
- Стриминг ответов для длинных сообщений

**Использование:**
```python
from mentorium_ai_client import MentoriumAIClient

client = MentoriumAIClient(api_key="sk-...")
reply = await client.generate_reply("Как дела с учёбой?", user_id=123)
```

---

#### 2. **db** - Работа с базой данных
```
packages/db/mentorium_db/
├── models.py             # SQLAlchemy модели (таблицы)
├── session.py            # Подключение к БД
├── repositories/         # Репозитории (DAL - Data Access Layer)
│   ├── parent.py        # Работа с родителями
│   ├── learner.py       # Работа с учениками
│   ├── subscription.py  # Подписки
│   ├── payment.py       # Платежи
│   ├── dialog.py        # История AI-диалогов
│   ├── notification.py  # Уведомления
│   └── platform.py      # Чтение из основной БД платформы
└── alembic/             # Миграции базы данных
    └── versions/        # История изменений схемы
```

**Две базы данных:**

1. **Bot Database** (PostgreSQL) - собственная БД бота:
   - `parents` - зарегистрированные родители
   - `learners` - привязанные ученики
   - `subscriptions` - активные подписки
   - `payments` - история платежей
   - `dialogs` - история AI-диалогов
   - `notifications` - отправленные уведомления
   - `event_logs` - лог событий
   - `report_history` - сгенерированные отчёты

2. **Platform Database** (PostgreSQL, read-only) - основная БД платформы:
   - Данные об учениках и их прогрессе
   - Результаты тестов
   - Курсы и достижения

**Использование:**
```python
from mentorium_db import get_session
from mentorium_db.repositories import ParentRepository

async with get_session() as session:
    repo = ParentRepository(session)
    parent = await repo.get_by_telegram_id(123456789)
```

---

#### 3. **observability** - Мониторинг и логирование
```
packages/observability/mentorium_observability/
├── logging.py            # Структурированные логи (structlog)
├── event_log.py          # Запись событий в БД
├── sentry_config.py      # Отслеживание ошибок (Sentry)
├── health.py             # Health checks для Kubernetes
└── metrics.py            # Метрики Prometheus
```

**Возможности:**
- **Структурированное логирование** - JSON-логи для ELK/Loki
- **EventLog** - запись важных событий в БД (регистрации, платежи, ошибки)
- **Sentry** - автоматическая отправка ошибок с контекстом
- **Health checks** - `/health/live`, `/health/ready`, `/health` для Kubernetes
- **Prometheus** - метрики (количество сообщений, запросов к AI, платежей)

**Использование:**
```python
from mentorium_observability import configure_logging, get_logger, EventLogService

# Настройка логирования
configure_logging(level="INFO", json_logs=True, dev_mode=False)

# Использование логгера
logger = get_logger(__name__)
logger.info("user_registered", user_id=123, subscription="monthly")

# Запись событий
await EventLogService.log_user_action("registration", user_telegram_id=123)
await EventLogService.log_payment("payment_success", user_telegram_id=123, amount=99000)
```

---

### `/docs` - Документация

| Файл | Описание |
|------|----------|
| `PROJECT_OVERVIEW.md` | 📖 Этот файл - общий обзор проекта |
| `PROJECT_COMPLETE.md` | ✅ Полная сводка всех 8 фаз разработки |
| `DEPLOYMENT.md` | 🚀 Инструкция по развёртыванию в production |
| `PHASE_7_MONITORING.md` | 📊 Настройка мониторинга и логирования |
| `ERROR_FIXES.md` | 🔧 История исправления 73 ошибок |

---

### `/scripts` - Вспомогательные скрипты

```
scripts/
├── validate_env.py       # Проверка .env на наличие всех переменных
└── verify_setup.py       # Проверка окружения (БД, Redis, Poetry)
```

**Использование:**
```bash
python scripts/validate_env.py    # Проверить .env перед запуском
make validate                      # То же через Makefile
```

---

### `/tests` - Тесты

```
tests/
└── test_parent_repository.py     # Тесты репозитория родителей
```

**Запуск:**
```bash
make test                 # Все тесты
make test-cov            # С покрытием
pytest tests/            # Напрямую через pytest
```

---

## 🗄️ База данных

### Схема таблиц (Bot Database)

```sql
-- Родители (пользователи бота)
CREATE TABLE parents (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    registration_code VARCHAR(10),
    registration_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Ученики (дети родителей)
CREATE TABLE learners (
    id SERIAL PRIMARY KEY,
    parent_id INTEGER REFERENCES parents(id),
    platform_student_id INTEGER NOT NULL,  -- ID из основной БД платформы
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    added_at TIMESTAMP DEFAULT NOW()
);

-- Подписки
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    parent_id INTEGER REFERENCES parents(id),
    tariff VARCHAR(20) NOT NULL,  -- monthly, quarterly, annual
    amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'ACTIVE',  -- ACTIVE, EXPIRED, CANCELLED
    start_date TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    auto_renew BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Платежи
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    parent_id INTEGER REFERENCES parents(id),
    subscription_id INTEGER REFERENCES subscriptions(id),
    transaction_id VARCHAR(255) UNIQUE,
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'UZS',
    provider VARCHAR(50),  -- TELEGRAM_STARS, PAYME, CLICK
    status VARCHAR(20) DEFAULT 'PENDING',  -- PENDING, SUCCESS, FAILED
    external_ref VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- История AI-диалогов
CREATE TABLE dialogs (
    id SERIAL PRIMARY KEY,
    parent_telegram_id BIGINT NOT NULL,
    user_message TEXT,
    ai_reply TEXT,
    tokens_used INTEGER,
    model VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Уведомления
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    parent_telegram_id BIGINT NOT NULL,
    notification_type VARCHAR(50),  -- REPORT, SUBSCRIPTION, ACHIEVEMENT
    message TEXT,
    sent_at TIMESTAMP DEFAULT NOW()
);

-- Лог событий
CREATE TABLE event_logs (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50),     -- USER_ACTION, PAYMENT, ERROR, SYSTEM
    event_name VARCHAR(100),
    user_telegram_id BIGINT,
    metadata JSONB,
    severity VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- История отчётов
CREATE TABLE report_history (
    id SERIAL PRIMARY KEY,
    parent_telegram_id BIGINT NOT NULL,
    report_type VARCHAR(50),    -- WEEKLY, MONTHLY, ON_DEMAND
    report_period VARCHAR(100),
    content TEXT,
    generated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 💳 Платёжные системы

### Поддерживаемые провайдеры

#### 1. **Telegram Stars** ⭐
- Встроенная валюта Telegram
- Самый простой способ оплаты
- Без дополнительной настройки
- Конвертация: ~1 Star = 100 UZS

#### 2. **PayMe** 🇺🇿
- Узбекистанская платёжная система
- Поддержка карт Uzcard/Humo
- JSON-RPC 2.0 API
- Webhook: `POST /webhooks/payme`

#### 3. **Click** 🇺🇿
- Узбекистанская платёжная система
- Двухфазные транзакции (prepare → complete)
- Webhooks: 
  - `GET /webhooks/click/prepare`
  - `GET /webhooks/click/complete`

### Тарифы

| Тариф | Длительность | Цена | Скидка |
|-------|-------------|------|--------|
| **Месячная** | 30 дней | 99,000 UZS | - |
| **Квартальная** | 90 дней | 249,000 UZS | -17% |
| **Годовая** | 365 дней | 899,000 UZS | -25% |

---

## 🤖 AI-функционал

### Системные промпты

Бот использует разные промпты в зависимости от контекста:

**1. Наставник для родителей:**
```
Ты - виртуальный наставник платформы Mentorium. Твоя задача - помогать 
родителям понять прогресс их детей в обучении нейросетям и AI. Отвечай 
дружелюбно, но профессионально. Используй простые термины.
```

**2. Генератор отчётов:**
```
Создай еженедельный отчёт для родителя о прогрессе ребёнка. Включи:
- Основные достижения
- Области для улучшения
- Рекомендации
- Предстоящие этапы
```

### Управление контекстом

- Хранение последних 10 сообщений в истории
- Ограничение контекста до 4000 токенов
- Автоматическая обрезка старых сообщений

---

## 🔔 Уведомления

### Типы уведомлений

1. **REPORT** - Отчёты о прогрессе
   - Еженедельные (понедельник 9:00)
   - Ежемесячные (1-е число 10:00)
   - По запросу (`/report`)

2. **SUBSCRIPTION** - Подписка
   - Истекает через 3 дня
   - Истекла (grace period)
   - Автопродление успешно

3. **ACHIEVEMENT** - Достижения
   - Завершил курс
   - Получил 100% на тесте
   - Дошёл до milestone

4. **REMINDER** - Напоминания
   - Не было активности 7 дней
   - Есть новые материалы

5. **PAYMENT** - Платежи
   - Платёж успешен
   - Платёж отклонён
   - Требуется оплата

---

## 🚀 Развёртывание

### Локальная разработка

```bash
# 1. Клонировать репозиторий
git clone https://github.com/taefednu/Mentorium-Chat-Bot.git
cd Mentorium-Chat-Bot

# 2. Установить зависимости
poetry install

# 3. Настроить окружение
cp .env.template .env
nano .env  # Заполнить реальные значения

# 4. Применить миграции
make migrate

# 5. Запустить бота
make dev
```

### Production (Docker Compose)

```bash
# 1. Настроить .env
cp .env.template .env
nano .env

# 2. Проверить конфигурацию
make validate

# 3. Запустить все сервисы
make docker-up

# 4. Проверить здоровье
make health
```

**Сервисы:**
- `postgres` - База данных PostgreSQL 16
- `redis` - Redis 7 для кэширования
- `bot` - Telegram бот (polling)
- `webhook` - FastAPI для webhooks (порт 8001)
- `migrations` - Автоматические миграции при старте

---

## 🛠️ Полезные команды (Makefile)

```bash
# Разработка
make dev                  # Запустить бота локально
make test                 # Запустить тесты
make lint                 # Проверить код (ruff + mypy)
make format               # Отформатировать код (black)

# Docker
make docker-build         # Собрать образ
make docker-up            # Запустить контейнеры
make docker-down          # Остановить контейнеры
make docker-logs          # Посмотреть логи
make docker-logs-bot      # Логи только бота

# База данных
make migrate              # Применить миграции
make migrate-create       # Создать новую миграцию
make backup-db            # Бэкап PostgreSQL
make restore-db           # Восстановить из бэкапа

# Мониторинг
make health               # Проверить health checks
make metrics              # Посмотреть метрики Prometheus

# Развёртывание
make validate             # Проверить .env
make deploy               # Полный deploy (validate + build + up + health)
```

---

## 📊 Мониторинг

### Health Checks

- **`GET /health/live`** - Liveness probe (просто возвращает OK)
- **`GET /health/ready`** - Readiness probe (проверяет БД)
- **`GET /health`** - Полная проверка (БД + Redis + Platform DB)

### Prometheus метрики

```
# Telegram
telegram_messages_total{message_type="text|command", status="success|error"}
telegram_commands_total{command="start|subscribe|report"}
telegram_active_users

# AI
ai_requests_total{model="gpt-4", status="success|error"}
ai_request_duration_seconds
ai_tokens_used_total{type="input|output"}

# Платежи
payments_total{provider="telegram_stars|payme|click", status="success|failed"}
subscriptions_active{tariff="monthly|quarterly|annual"}

# Система
errors_total{error_type="api|database|payment"}
bot_uptime_seconds
```

### Sentry

Автоматическая отправка всех ошибок с контекстом:
- User ID
- Handler name
- Request parameters
- Stack trace

---

## 🔒 Безопасность

### Переменные окружения

**Критически важные (никогда не коммитить!):**
- `BOT_TELEGRAM_TOKEN` - токен бота
- `BOT_OPENAI_API_KEY` - API ключ OpenAI
- `DB_PASSWORD` - пароль БД
- `REDIS_PASSWORD` - пароль Redis
- `PAYME_SECRET_KEY` - секретный ключ PayMe
- `CLICK_SECRET_KEY` - секретный ключ Click

**Файлы:**
- `.env` - реальные значения (в `.gitignore`)
- `.env.template` - шаблон для production (без секретов)

### Docker Security

- Бот запускается от **непривилегированного пользователя** `mentoriumbot:1000`
- Используется **multi-stage build** для минимизации образа
- Secrets передаются через переменные окружения, не в образ

---

## 📈 Производительность

### Рекомендуемые ресурсы

**Минимальные:**
- CPU: 1 core
- RAM: 1 GB
- Disk: 10 GB

**Рекомендуемые (100+ пользователей):**
- CPU: 2 cores
- RAM: 4 GB
- Disk: 50 GB (логи + бэкапы)

### Масштабирование

**Текущее ограничение:** Polling режим (1 экземпляр бота)

**Для масштабирования:**
1. Переключиться на webhook-режим
2. Запустить несколько инстансов за load balancer
3. Использовать Redis для shared state (FSM)

---

## 🎯 Roadmap

### ✅ Реализовано (Phases 1-8)

1. ✅ Database Architecture - 8 таблиц, миграции
2. ✅ AI Client - интеграция с OpenAI
3. ✅ Registration Flow - FSM, валидация email
4. ✅ AI Dialogs - стриминг, контекст
5. ✅ Reports & Notifications - еженедельные/месячные отчёты
6. ✅ Billing - 3 платёжные системы, подписки
7. ✅ Monitoring - логи, метрики, Sentry
8. ✅ Production Deployment - Docker, Kubernetes

### 🔮 Будущие улучшения

- [ ] Admin-панель для управления
- [ ] Telegram Mini App для статистики
- [ ] Webhook-режим вместо polling
- [ ] Интеграция с email (рассылка отчётов)
- [ ] Многоязычность (uz, ru, en)
- [ ] Голосовые сообщения для отчётов
- [ ] Gamification (бейджи, рейтинги)

---

## 👥 Для разработчиков

### Добавление нового handler

1. Создайте файл в `apps/telegram_bot/mentorium_bot/handlers/`:
```python
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

my_router = Router(name="my_feature")

@my_router.message(Command("mycommand"))
async def my_command_handler(message: Message):
    await message.answer("Hello!")
```

2. Зарегистрируйте в `main.py`:
```python
from mentorium_bot.handlers.my_feature import my_router

dp.include_router(my_router)
```

### Добавление новой таблицы

1. Создайте модель в `packages/db/mentorium_db/models.py`:
```python
class MyModel(Base):
    __tablename__ = "my_table"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
```

2. Создайте миграцию:
```bash
make migrate-create MSG="add my_table"
```

3. Примените:
```bash
make migrate
```

### Добавление нового репозитория

Создайте файл `packages/db/mentorium_db/repositories/my_repo.py`:
```python
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import MyModel

class MyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, id: int) -> MyModel | None:
        return await self.session.get(MyModel, id)
```

---

## 📞 Контакты

- **Репозиторий:** https://github.com/taefednu/Mentorium-Chat-Bot
- **Платформа:** https://mentorium.uz
- **Email:** dev@mentorium.io

---

## 📄 Лицензия

Proprietary - все права принадлежат Mentorium Platform

---

**Последнее обновление:** 3 ноября 2025

**Версия:** 0.1.0

**Статус:** ✅ Production Ready
