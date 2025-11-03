"""
FastAPI приложение для обработки payment webhooks
Запускается отдельно от Telegram бота (на другом порту)
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse

from mentorium_db.repositories.parent import ParentRepository
from mentorium_db.repositories.payment import PaymentRepository
from mentorium_db.repositories.subscription import SubscriptionRepository
from mentorium_db.session import bot_session_factory
from mentorium_observability import get_health_status, get_liveness_status, get_metrics, get_readiness_status

from .config import BotSettings
from .handlers.webhooks import click_complete_webhook, click_prepare_webhook, payme_webhook
from .services.billing_service import BillingService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mentorium Payment Webhooks", version="1.0.0")


@app.get("/health")
async def health_check():
    """Full health check endpoint"""
    health = await get_health_status()
    status_code = 200 if health["status"] == "healthy" else 503
    return JSONResponse(content=health, status_code=status_code)


@app.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe - simple check without dependencies"""
    return get_liveness_status()


@app.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe - check if ready to serve traffic"""
    readiness = await get_readiness_status()
    status_code = 200 if readiness["ready"] else 503
    return JSONResponse(content=readiness, status_code=status_code)


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=get_metrics(), media_type="text/plain")


@app.post("/webhooks/payme")
async def handle_payme_webhook(request):
    """PayMe webhook endpoint"""
    settings = BotSettings()
    
    async with bot_session_factory() as session:
        billing_service = BillingService(settings=settings)
        response = await payme_webhook(request, authorization=None, billing_service=billing_service)
        return JSONResponse(content=response)


@app.get("/webhooks/click/prepare")
async def handle_click_prepare(request):
    """Click prepare webhook endpoint"""
    settings = BotSettings()
    
    async with bot_session_factory() as session:
        billing_service = BillingService(settings=settings)
        response = await click_prepare_webhook(request, billing_service=billing_service)
        return JSONResponse(content=response)


@app.get("/webhooks/click/complete")
async def handle_click_complete(request):
    """Click complete webhook endpoint"""
    settings = BotSettings()
    
    async with bot_session_factory() as session:
        billing_service = BillingService(settings=settings)
        response = await click_complete_webhook(request, billing_service=billing_service)
        return JSONResponse(content=response)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
