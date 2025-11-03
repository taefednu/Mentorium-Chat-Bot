# Multi-stage build для Mentorium Chat Bot
# Stage 1: Builder - устанавливаем зависимости
FROM python:3.11-slim as builder

# Устанавливаем Poetry
ENV POETRY_VERSION=1.8.0 \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

# Копируем только файлы для установки зависимостей
WORKDIR /app
COPY pyproject.toml poetry.lock ./

# Устанавливаем зависимости (без dev)
RUN poetry install --no-root --no-dev --no-interaction --no-ansi

# Stage 2: Runtime - финальный образ
FROM python:3.11-slim

# Метаданные
LABEL maintainer="dev@mentorium.io"
LABEL description="Mentorium Telegram Chat Bot"

# Создаём пользователя для безопасности (non-root)
RUN groupadd -r mentoriumbot && \
    useradd -r -g mentoriumbot -u 1000 mentoriumbot && \
    mkdir -p /app /home/mentoriumbot && \
    chown -R mentoriumbot:mentoriumbot /app /home/mentoriumbot

# Устанавливаем системные зависимости
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копируем виртуальное окружение из builder
COPY --from=builder --chown=mentoriumbot:mentoriumbot /app/.venv /app/.venv

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем код приложения
COPY --chown=mentoriumbot:mentoriumbot packages/ packages/
COPY --chown=mentoriumbot:mentoriumbot apps/ apps/
COPY --chown=mentoriumbot:mentoriumbot pyproject.toml poetry.lock ./

# Переключаемся на non-root пользователя
USER mentoriumbot

# Добавляем виртуальное окружение в PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Порт для webhook app (если используется)
EXPOSE 8001

# Команда по умолчанию - запуск бота
CMD ["python", "-m", "mentorium_bot.main"]
