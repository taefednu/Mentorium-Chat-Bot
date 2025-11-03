# Phase 7: Monitoring & Logging - Completed ✅

## Что реализовано

### 1. Structured Logging (structlog)
**Файл:** `packages/observability/mentorium_observability/logging.py`

- ✅ JSON формат для продакшена (easy parsing в ELK/Loki)
- ✅ Красивый цветной вывод для разработки
- ✅ Автоматический context (timestamp, log level, logger name)
- ✅ Call stack и exception info
- ✅ Bind контекста (request_id, user_id, etc)

**Использование:**
```python
from mentorium_observability import configure_logging, get_logger

# В main.py
configure_logging(
    level="INFO",
    json_logs=True,  # для продакшена
    dev_mode=False,
)

# В любом модуле
logger = get_logger(__name__)
logger.info("user_action", user_id=123, action="subscribe")
```

### 2. Event Logging (DB)
**Файл:** `packages/observability/mentorium_observability/event_log.py`

Отслеживание событий в БД:
- ✅ **USER_ACTION**: регистрация, диалоги, отчёты
- ✅ **PAYMENT**: платежи, подписки
- ✅ **ERROR**: ошибки с контекстом
- ✅ **SYSTEM**: запуск, остановка, миграции

**Использование:**
```python
from mentorium_observability import EventLogService

# Логировать действие пользователя
await EventLogService.log_user_action(
    action="registration",
    user_telegram_id=123456,
    metadata={"email": "user@example.com"}
)

# Логировать платёж
await EventLogService.log_payment(
    payment_event="payment_success",
    user_telegram_id=123456,
    amount=99000,
    provider="payme",
)

# Логировать ошибку
await EventLogService.log_error(
    error_name="dialog_error",
    error_message="AI timeout",
    user_telegram_id=123456,
)
```

### 3. Sentry Integration
**Файл:** `packages/observability/mentorium_observability/sentry_config.py`

- ✅ Автоматическое отслеживание исключений
- ✅ Performance monitoring (traces)
- ✅ Context (user_id, handler name)
- ✅ Фильтрация временных ошибок (NetworkError, CancelledError)
- ✅ Privacy (send_default_pii=False)

**Настройка:**
```python
from mentorium_observability import configure_sentry

configure_sentry(
    dsn=os.getenv("SENTRY_DSN"),
    environment="production",
    release=os.getenv("GIT_COMMIT"),
    traces_sample_rate=0.1,  # 10% транзакций
)
```

**Использование:**
```python
from mentorium_observability import capture_exception

try:
    # your code
except Exception as e:
    capture_exception(
        error=e,
        user_id=telegram_id,
        handler_name="dialog_handler",
        extra={"context": "additional info"}
    )
```

### 4. Health Checks
**Файл:** `packages/observability/mentorium_observability/health.py`

Endpoints для Kubernetes:
- ✅ `/health` - полная проверка (БД бота + платформы)
- ✅ `/health/live` - liveness probe (без зависимостей)
- ✅ `/health/ready` - readiness probe (проверка БД)

**Response example:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-03T22:30:00Z",
  "checks": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5.2
    },
    "platform_database": {
      "status": "healthy",
      "response_time_ms": 8.1
    }
  }
}
```

### 5. Prometheus Metrics
**Файл:** `packages/observability/mentorium_observability/metrics.py`

Метрики для мониторинга:

**Bot metrics:**
- `telegram_messages_total` - количество сообщений
- `telegram_commands_total` - количество команд
- `telegram_active_users` - активные пользователи за 24ч

**AI metrics:**
- `ai_requests_total` - количество AI запросов
- `ai_request_duration_seconds` - время выполнения
- `ai_tokens_used_total` - использованные токены

**Payment metrics:**
- `payments_total` - количество платежей
- `payments_amount_total` - сумма платежей
- `subscriptions_active` - активные подписки

**System metrics:**
- `db_query_duration_seconds` - время запросов к БД
- `errors_total` - количество ошибок
- `bot_uptime_seconds` - время работы бота

**Использование:**
```python
from mentorium_observability import MetricsCollector

# Записать метрику сообщения
MetricsCollector.record_message("text", success=True)

# Записать метрику AI запроса
MetricsCollector.record_ai_request(
    model="gpt-4o",
    duration=1.5,
    tokens_prompt=100,
    tokens_completion=50,
)

# Записать метрику платежа
MetricsCollector.record_payment(
    provider="payme",
    amount=99000,
    currency="UZS",
    success=True,
)
```

**Endpoint:** `GET /metrics` возвращает метрики в формате Prometheus

## Интеграция

### В main.py:
```python
from mentorium_observability import (
    configure_logging,
    configure_sentry,
    EventLogService,
    MetricsCollector,
)

# Настройка логирования
configure_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    json_logs=os.getenv("LOG_FORMAT") == "json",
    dev_mode=os.getenv("ENVIRONMENT") == "development",
)

# Настройка Sentry
if sentry_dsn := os.getenv("SENTRY_DSN"):
    configure_sentry(
        dsn=sentry_dsn,
        environment=os.getenv("ENVIRONMENT", "development"),
        release=os.getenv("GIT_COMMIT", "unknown"),
    )

# Логирование событий
await EventLogService.log_system("bot_started")
```

### В webhook_app.py:
```python
from mentorium_observability import (
    get_health_status,
    get_readiness_status,
    get_liveness_status,
    get_metrics,
)

@app.get("/health")
async def health_check():
    health = await get_health_status()
    return JSONResponse(health, status_code=200 if health["status"] == "healthy" else 503)

@app.get("/metrics")
async def metrics():
    return Response(get_metrics(), media_type="text/plain")
```

## Environment Variables

```bash
# Logging
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json                   # json или text
ENVIRONMENT=production            # development, staging, production

# Sentry
SENTRY_DSN=https://...@sentry.io/...
GIT_COMMIT=abc123                 # release version
```

## Grafana Dashboard Query Examples

```promql
# RPS (requests per second)
rate(telegram_messages_total[5m])

# Error rate
rate(errors_total[5m])

# AI request latency (p95)
histogram_quantile(0.95, rate(ai_request_duration_seconds_bucket[5m]))

# Active subscriptions
subscriptions_active

# Database query latency
histogram_quantile(0.99, rate(db_query_duration_seconds_bucket[5m]))
```

## Результат

✅ **Structured logging** с JSON форматом  
✅ **Event tracking** в БД для аналитики  
✅ **Sentry** для отслеживания ошибок  
✅ **Health checks** для Kubernetes  
✅ **Prometheus metrics** для мониторинга  

**Phase 7 завершён! Готов к продакшену 🚀**
