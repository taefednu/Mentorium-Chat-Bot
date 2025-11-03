# Phase 8: Production Deployment - Complete Guide 🚀

## Что реализовано

### 1. Dockerfile (Multi-stage Build)
**Файл:** `Dockerfile`

Особенности:
- ✅ Multi-stage build (builder + runtime)
- ✅ Python 3.11-slim базовый образ
- ✅ Non-root пользователь (mentoriumbot:1000)
- ✅ Poetry для управления зависимостями
- ✅ Health check встроен
- ✅ Минимальный финальный образ

### 2. Docker Compose
**Файл:** `docker-compose.yml`

Сервисы:
- ✅ **postgres** - PostgreSQL 16 (основная БД бота)
- ✅ **redis** - Redis 7 (кэширование, очереди)
- ✅ **bot** - Telegram бот (polling режим)
- ✅ **webhook** - FastAPI приложение (payment webhooks)
- ✅ **migrations** - автоматический запуск миграций при старте

Features:
- Health checks для всех сервисов
- Зависимости между сервисами
- Persistent volumes для данных
- Изолированная сеть
- Graceful restart policies

### 3. Environment Configuration
**Файлы:** `.env.template`, `scripts/validate_env.py`

Категории переменных:
- ✅ Database configuration (Bot + Platform)
- ✅ Redis configuration
- ✅ Telegram Bot token
- ✅ OpenAI API key
- ✅ Payment providers (PayMe, Click)
- ✅ Logging & Monitoring (Sentry)
- ✅ Webhook settings

Валидация:
```bash
python scripts/validate_env.py
```

### 4. Graceful Shutdown
**Файл:** `apps/telegram_bot/mentorium_bot/main.py`

- ✅ Signal handlers (SIGINT, SIGTERM)
- ✅ Graceful shutdown event
- ✅ Cleanup на exit
- ✅ Логирование uptime
- ✅ Корректное закрытие соединений

---

## Quick Start

### Локальная разработка

1. **Клонировать репозиторий:**
```bash
git clone https://github.com/taefednu/Mentorium-Chat-Bot.git
cd Mentorium-Chat-Bot
```

2. **Установить зависимости:**
```bash
poetry install
```

3. **Создать .env файл:**
```bash
cp .env.example .env
# Отредактировать .env с вашими credentials
```

4. **Запустить PostgreSQL локально:**
```bash
docker-compose up -d postgres
```

5. **Применить миграции:**
```bash
cd packages/db
poetry run alembic upgrade head
```

6. **Валидировать environment:**
```bash
python scripts/validate_env.py
```

7. **Запустить бота:**
```bash
cd apps/telegram_bot
poetry run python -m mentorium_bot.main
```

---

## Production Deployment

### Вариант 1: Docker Compose (Простой)

1. **Подготовить сервер:**
```bash
# Установить Docker и Docker Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

2. **Клонировать и настроить:**
```bash
git clone https://github.com/taefednu/Mentorium-Chat-Bot.git
cd Mentorium-Chat-Bot
cp .env.template .env
nano .env  # заполнить все переменные
```

3. **Валидировать environment:**
```bash
python3 scripts/validate_env.py
```

4. **Запустить все сервисы:**
```bash
docker-compose up -d
```

5. **Проверить статус:**
```bash
docker-compose ps
docker-compose logs -f bot
```

6. **Health check:**
```bash
curl http://localhost:8001/health
```

### Вариант 2: Kubernetes (Production-ready)

1. **Создать namespace:**
```bash
kubectl create namespace mentorium
```

2. **Создать secrets:**
```bash
kubectl create secret generic mentorium-secrets \
  --from-env-file=.env \
  --namespace=mentorium
```

3. **Применить манифесты:**
```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
```

4. **Проверить pods:**
```bash
kubectl get pods -n mentorium
kubectl logs -f deployment/mentorium-bot -n mentorium
```

---

## Мониторинг

### Health Checks

**Liveness probe** (жив ли контейнер):
```bash
curl http://localhost:8001/health/live
```

**Readiness probe** (готов к трафику):
```bash
curl http://localhost:8001/health/ready
```

**Full health check** (все компоненты):
```bash
curl http://localhost:8001/health
```

### Prometheus Metrics

Endpoint: `http://localhost:8001/metrics`

Доступные метрики:
- `telegram_messages_total` - количество сообщений
- `ai_requests_total` - количество AI запросов
- `payments_total` - количество платежей
- `subscriptions_active` - активные подписки
- `errors_total` - количество ошибок

### Sentry

Настроить в `.env`:
```bash
SENTRY_DSN=https://your_key@sentry.io/project_id
SENTRY_ENVIRONMENT=production
```

---

## Миграции

### Создать новую миграцию:
```bash
cd packages/db
poetry run alembic revision --autogenerate -m "description"
```

### Применить миграции:
```bash
cd packages/db
poetry run alembic upgrade head
```

### Откатить миграцию:
```bash
cd packages/db
poetry run alembic downgrade -1
```

### В Docker:
```bash
docker-compose run --rm migrations
```

---

## Backup & Recovery

### Backup PostgreSQL:
```bash
docker exec mentorium-postgres pg_dump \
  -U mentoriumbot mentorium_bot > backup_$(date +%Y%m%d).sql
```

### Restore PostgreSQL:
```bash
cat backup_20251103.sql | docker exec -i mentorium-postgres \
  psql -U mentoriumbot mentorium_bot
```

### Backup Redis:
```bash
docker exec mentorium-redis redis-cli --rdb /data/dump.rdb
docker cp mentorium-redis:/data/dump.rdb ./redis_backup.rdb
```

---

## Logs

### Docker Compose:
```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f bot
docker-compose logs -f webhook

# С временными метками
docker-compose logs -f --timestamps bot
```

### JSON формат (для ELK/Loki):
Установить в `.env`:
```bash
LOG_FORMAT=json
```

---

## Scaling

### Горизонтальное масштабирование:
```bash
# Увеличить количество bot replicas
docker-compose up -d --scale bot=3
```

### Для webhook app:
```bash
docker-compose up -d --scale webhook=2
```

**Note:** Для polling режима бота можно запустить только 1 инстанс. Для масштабирования нужно переключиться на webhook режим.

---

## Security Checklist

- [ ] Все пароли в `.env` уникальные и сложные
- [ ] `.env` добавлен в `.gitignore`
- [ ] PostgreSQL доступен только из Docker network
- [ ] Redis защищён паролем
- [ ] Webhook app за reverse proxy (nginx/Caddy)
- [ ] SSL сертификаты настроены (Let's Encrypt)
- [ ] Sentry DSN не в коде, только в environment
- [ ] Platform DB используется в read-only режиме
- [ ] Non-root пользователь в Docker
- [ ] Firewall настроен (только 80, 443, 22)

---

## Troubleshooting

### Бот не запускается:
```bash
# Проверить логи
docker-compose logs bot

# Проверить environment
python scripts/validate_env.py

# Проверить БД
docker-compose exec postgres psql -U mentoriumbot -d mentorium_bot -c "SELECT 1;"
```

### Webhook не работает:
```bash
# Проверить health
curl http://localhost:8001/health

# Проверить логи
docker-compose logs webhook

# Проверить сеть
docker network inspect mentorium_mentorium-network
```

### Миграции не применяются:
```bash
# Проверить версию
docker-compose run --rm migrations poetry run alembic current

# Применить вручную
docker-compose run --rm migrations poetry run alembic upgrade head
```

---

## Производительность

### Рекомендуемые ресурсы:

**Bot container:**
- CPU: 1-2 cores
- RAM: 512MB - 1GB
- Disk: 1GB

**Webhook container:**
- CPU: 0.5-1 core
- RAM: 256MB - 512MB
- Disk: 500MB

**PostgreSQL:**
- CPU: 2 cores
- RAM: 2GB
- Disk: 20GB SSD

**Redis:**
- CPU: 0.5 core
- RAM: 256MB
- Disk: 1GB

---

## CI/CD Pipeline (GitHub Actions)

Создать `.github/workflows/deploy.yml`:
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker image
        run: docker build -t mentorium-bot:${{ github.sha }} .
      
      - name: Push to registry
        run: docker push mentorium-bot:${{ github.sha }}
      
      - name: Deploy
        run: |
          ssh user@server "cd /opt/mentorium && \
          git pull && \
          docker-compose pull && \
          docker-compose up -d"
```

---

## Результат ✅

**Phase 8 полностью завершён!**

- ✅ Dockerfile (multi-stage, non-root, secure)
- ✅ Docker Compose (все сервисы + миграции)
- ✅ Environment setup (.env.template, validation)
- ✅ Graceful shutdown (signal handlers)
- ✅ Health checks (liveness, readiness)
- ✅ Monitoring (Prometheus, Sentry)
- ✅ Production-ready deployment guide
- ✅ Backup & recovery procedures
- ✅ Troubleshooting documentation
- ✅ Security checklist

**Проект готов к production deployment! 🚀**
