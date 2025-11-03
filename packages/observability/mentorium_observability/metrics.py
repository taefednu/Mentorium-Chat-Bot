"""
Prometheus metrics для мониторинга
"""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, generate_latest

# Bot metrics
telegram_messages_total = Counter(
    "telegram_messages_total",
    "Total number of Telegram messages processed",
    ["message_type", "status"],
)

telegram_commands_total = Counter(
    "telegram_commands_total",
    "Total number of Telegram commands processed",
    ["command", "status"],
)

telegram_active_users = Gauge(
    "telegram_active_users",
    "Number of active users in the last 24 hours",
)

# AI metrics
ai_requests_total = Counter(
    "ai_requests_total",
    "Total number of AI requests",
    ["model", "status"],
)

ai_request_duration_seconds = Histogram(
    "ai_request_duration_seconds",
    "AI request duration in seconds",
    ["model"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

ai_tokens_used_total = Counter(
    "ai_tokens_used_total",
    "Total number of AI tokens used",
    ["model", "token_type"],
)

# Payment metrics
payments_total = Counter(
    "payments_total",
    "Total number of payments",
    ["provider", "status"],
)

payments_amount_total = Counter(
    "payments_amount_total",
    "Total payment amount",
    ["provider", "currency"],
)

subscriptions_active = Gauge(
    "subscriptions_active",
    "Number of active subscriptions",
)

subscriptions_created_total = Counter(
    "subscriptions_created_total",
    "Total number of subscriptions created",
    ["tariff"],
)

# Database metrics
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)

db_connections_active = Gauge(
    "db_connections_active",
    "Number of active database connections",
    ["pool"],
)

# Error metrics
errors_total = Counter(
    "errors_total",
    "Total number of errors",
    ["error_type", "handler"],
)

# System metrics
bot_uptime_seconds = Gauge(
    "bot_uptime_seconds",
    "Bot uptime in seconds",
)


def get_metrics() -> bytes:
    """
    Получить метрики в формате Prometheus
    
    Returns:
        Метрики в текстовом формате Prometheus
    """
    return generate_latest()


class MetricsCollector:
    """Helper для удобного сбора метрик"""

    @staticmethod
    def record_message(message_type: str, success: bool = True) -> None:
        """Записать метрику обработки сообщения"""
        status = "success" if success else "error"
        telegram_messages_total.labels(message_type=message_type, status=status).inc()

    @staticmethod
    def record_command(command: str, success: bool = True) -> None:
        """Записать метрику выполнения команды"""
        status = "success" if success else "error"
        telegram_commands_total.labels(command=command, status=status).inc()

    @staticmethod
    def record_ai_request(
        model: str,
        duration: float,
        tokens_prompt: int,
        tokens_completion: int,
        success: bool = True,
    ) -> None:
        """Записать метрику AI запроса"""
        status = "success" if success else "error"
        ai_requests_total.labels(model=model, status=status).inc()
        ai_request_duration_seconds.labels(model=model).observe(duration)
        ai_tokens_used_total.labels(model=model, token_type="prompt").inc(tokens_prompt)
        ai_tokens_used_total.labels(model=model, token_type="completion").inc(tokens_completion)

    @staticmethod
    def record_payment(provider: str, amount: float, currency: str, success: bool = True) -> None:
        """Записать метрику платежа"""
        status = "success" if success else "error"
        payments_total.labels(provider=provider, status=status).inc()
        if success:
            payments_amount_total.labels(provider=provider, currency=currency).inc(amount)

    @staticmethod
    def record_subscription(tariff: str) -> None:
        """Записать метрику создания подписки"""
        subscriptions_created_total.labels(tariff=tariff).inc()

    @staticmethod
    def record_error(error_type: str, handler: str = "unknown") -> None:
        """Записать метрику ошибки"""
        errors_total.labels(error_type=error_type, handler=handler).inc()

    @staticmethod
    def set_active_users(count: int) -> None:
        """Установить количество активных пользователей"""
        telegram_active_users.set(count)

    @staticmethod
    def set_active_subscriptions(count: int) -> None:
        """Установить количество активных подписок"""
        subscriptions_active.set(count)

    @staticmethod
    def set_bot_uptime(seconds: float) -> None:
        """Установить время работы бота"""
        bot_uptime_seconds.set(seconds)
