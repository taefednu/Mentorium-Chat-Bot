"""
Webhook endpoints для PayMe и Click платёжных систем
"""
from __future__ import annotations

import json
import logging
from typing import Any

from aiogram import Router
from aiogram.types import Update
from fastapi import Depends, HTTPException, Header, Request

from mentorium_db.repositories.payment import PaymentRepository
from mentorium_db.repositories.subscription import SubscriptionRepository
from mentorium_db.session import get_session

from ..config import BotSettings
from ..services.billing_service import BillingService
from ..services.payment.click import ClickProvider
from ..services.payment.payme import PayMeProvider

logger = logging.getLogger(__name__)

webhook_router = Router(name="webhooks")


async def get_billing_service(session=Depends(get_session)) -> BillingService:
    """Dependency для BillingService"""
    settings = BotSettings()
    return BillingService(settings=settings)


async def payme_webhook(
    request: Request,
    authorization: str | None = Header(None),
    billing_service: BillingService = Depends(get_billing_service),
) -> dict[str, Any]:
    """
    PayMe webhook endpoint
    Обрабатывает JSON-RPC 2.0 запросы от PayMe
    """
    payme_provider = billing_service.payme

    if not payme_provider or not payme_provider.is_available():
        raise HTTPException(status_code=503, detail="PayMe provider not configured")

    # Верифицируем подпись
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    if not payme_provider.verify_webhook_signature(authorization):
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Парсим JSON-RPC запрос
    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse PayMe webhook body: {e}")
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32700, "message": "Parse error"},
        }

    # Обрабатываем через PayMeProvider
    try:
        response = payme_provider.handle_webhook(body)
        return response
    except Exception as e:
        logger.error(f"PayMe webhook error: {e}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
        }


async def click_prepare_webhook(
    request: Request,
    billing_service: BillingService = Depends(get_billing_service),
) -> dict[str, Any]:
    """
    Click prepare webhook
    Первая фаза транзакции Click
    """
    click_provider = billing_service.click

    if not click_provider or not click_provider.is_available():
        raise HTTPException(status_code=503, detail="Click provider not configured")

    # Получаем параметры из query string
    params = dict(request.query_params)

    # Верифицируем подпись - передаём все параметры из запроса
    click_trans_id = params.get("click_trans_id", "")
    service_id = params.get("service_id", "")
    order_id = params.get("merchant_trans_id", "")
    amount = params.get("amount", "")
    action = params.get("action", "")
    sign_time = params.get("sign_time", "")
    sign_string = params.get("sign_string", "")
    
    if not click_provider.verify_webhook_signature(
        click_trans_id, service_id, order_id, order_id, amount, action, sign_time, sign_string
    ):
        return {
            "error": -1,
            "error_note": "Invalid signature",
        }

    # Обрабатываем prepare
    try:
        response = click_provider.handle_prepare_webhook(params)
        return response
    except Exception as e:
        logger.error(f"Click prepare webhook error: {e}", exc_info=True)
        return {
            "error": -9,
            "error_note": f"Internal error: {str(e)}",
        }


async def click_complete_webhook(
    request: Request,
    billing_service: BillingService = Depends(get_billing_service),
) -> dict[str, Any]:
    """
    Click complete webhook
    Вторая фаза транзакции Click
    """
    click_provider = billing_service.click

    if not click_provider or not click_provider.is_available():
        raise HTTPException(status_code=503, detail="Click provider not configured")

    # Получаем параметры из query string
    params = dict(request.query_params)

    # Верифицируем подпись - передаём все параметры из запроса
    click_trans_id = params.get("click_trans_id", "")
    service_id = params.get("service_id", "")
    order_id = params.get("merchant_trans_id", "")
    amount = params.get("amount", "")
    action = params.get("action", "")
    sign_time = params.get("sign_time", "")
    sign_string = params.get("sign_string", "")
    
    if not click_provider.verify_webhook_signature(
        click_trans_id, service_id, order_id, order_id, amount, action, sign_time, sign_string
    ):
        return {
            "error": -1,
            "error_note": "Invalid signature",
        }

    # Обрабатываем complete
    try:
        response = click_provider.handle_complete_webhook(params)
        return response
    except Exception as e:
        logger.error(f"Click complete webhook error: {e}", exc_info=True)
        return {
            "error": -9,
            "error_note": f"Internal error: {str(e)}",
        }
