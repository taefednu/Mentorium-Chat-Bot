"""
Click payment provider integration (Uzbekistan)
Документация: https://docs.click.uz/
"""
from __future__ import annotations

import hashlib
import logging
from decimal import Decimal
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class ClickProvider:
    """
    Click payment provider для Узбекистана
    
    Поддерживает:
    - Создание платёжных ссылок
    - Webhook обработку (prepare/complete)
    - Проверку статуса платежа
    """

    def __init__(
        self,
        merchant_id: str | None,
        service_id: str | None,
        secret_key: str | None,
        test_mode: bool = True,
    ):
        self.merchant_id = merchant_id
        self.service_id = service_id
        self.secret_key = secret_key
        self.test_mode = test_mode
        self.enabled = bool(merchant_id and service_id and secret_key)

        if not self.enabled:
            logger.warning("Click provider disabled: missing credentials")

    def is_available(self) -> bool:
        """Проверить, доступен ли провайдер"""
        return self.enabled

    def create_payment_link(
        self,
        amount: Decimal,
        order_id: str,
        return_url: str | None = None,
    ) -> str | None:
        """
        Создать ссылку на оплату Click
        
        Args:
            amount: Сумма в UZS
            order_id: ID подписки/платежа
            return_url: URL для возврата после оплаты
            
        Returns:
            URL для оплаты или None если провайдер недоступен
        """
        if not self.enabled:
            logger.warning("Cannot create Click link: provider disabled")
            return None

        # Формируем параметры
        params = {
            "service_id": self.service_id,
            "merchant_id": self.merchant_id,
            "amount": str(amount),
            "transaction_param": order_id,
        }

        if return_url:
            params["return_url"] = return_url

        # URL зависит от режима
        base_url = "https://my.click.uz/services/pay" if not self.test_mode else "https://test.click.uz/services/pay"

        # Собираем query string
        query = "&".join([f"{k}={v}" for k, v in params.items()])
        payment_url = f"{base_url}?{query}"

        logger.info(f"Created Click payment link for order {order_id}, amount {amount} UZS")
        return payment_url

    def verify_webhook_signature(
        self,
        click_trans_id: str,
        service_id: str,
        order_id: str,
        merchant_trans_id: str,
        amount: str,
        action: str,
        sign_time: str,
        sign_string: str,
    ) -> bool:
        """
        Проверить подпись webhook запроса от Click
        
        Click отправляет sign_string = MD5(click_trans_id + service_id + secret_key + 
                                            merchant_trans_id + amount + action + sign_time)
        """
        if not self.enabled:
            return False

        # Формируем строку для хеширования
        data = f"{click_trans_id}{service_id}{self.secret_key}{order_id}{amount}{action}{sign_time}"

        # Вычисляем MD5
        calculated_sign = hashlib.md5(data.encode()).hexdigest()

        is_valid = calculated_sign == sign_string

        if not is_valid:
            logger.warning(f"Invalid Click signature for order {order_id}")

        return is_valid

    async def check_payment_status(self, click_trans_id: str) -> dict[str, Any] | None:
        """
        Проверить статус платежа через Click API
        
        Returns:
            {"status": "paid|pending|cancelled", "amount": Decimal, ...}
        """
        if not self.enabled:
            return None

        # TODO: Реализовать запрос к Click API для проверки статуса
        logger.info(f"Checking Click transaction {click_trans_id} status")
        return None

    def handle_prepare_webhook(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Обработать prepare webhook от Click (первая фаза)
        
        На этом этапе Click проверяет, можно ли создать платёж
        
        Returns:
            {"error": 0, "error_note": "Success", "merchant_trans_id": "..."}
        """
        if not self.enabled:
            return {"error": -8, "error_note": "Provider disabled"}

        click_trans_id = params.get("click_trans_id")
        service_id = params.get("service_id")
        order_id = params.get("merchant_trans_id")
        amount = params.get("amount")
        action = params.get("action")
        sign_time = params.get("sign_time")
        sign_string = params.get("sign_string")

        # Проверяем подпись
        if not self.verify_webhook_signature(
            click_trans_id, service_id, order_id, order_id, amount, action, sign_time, sign_string
        ):
            return {"error": -1, "error_note": "Invalid signature"}

        # TODO: Проверить, что order_id существует и сумма корректна
        # TODO: Сохранить транзакцию в БД со статусом PENDING

        logger.info(f"Click prepare: order={order_id}, amount={amount}")

        return {
            "error": 0,
            "error_note": "Success",
            "merchant_trans_id": order_id,
            "merchant_prepare_id": click_trans_id,
        }

    def handle_complete_webhook(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Обработать complete webhook от Click (вторая фаза)
        
        На этом этапе Click подтверждает успешный платёж
        
        Returns:
            {"error": 0, "error_note": "Success", "merchant_confirm_id": "..."}
        """
        if not self.enabled:
            return {"error": -8, "error_note": "Provider disabled"}

        click_trans_id = params.get("click_trans_id")
        service_id = params.get("service_id")
        order_id = params.get("merchant_trans_id")
        merchant_prepare_id = params.get("merchant_prepare_id")
        amount = params.get("amount")
        action = params.get("action")
        sign_time = params.get("sign_time")
        sign_string = params.get("sign_string")
        error_code = params.get("error")

        # Проверяем подпись
        if not self.verify_webhook_signature(
            click_trans_id, service_id, order_id, order_id, amount, action, sign_time, sign_string
        ):
            return {"error": -1, "error_note": "Invalid signature"}

        # Проверяем, что prepare прошёл успешно
        if error_code != 0:
            logger.warning(f"Click complete failed: order={order_id}, error={error_code}")
            return {"error": -6, "error_note": "Transaction cancelled"}

        # TODO: Обновить статус транзакции на PAID
        # TODO: Активировать подписку

        logger.info(f"Click complete: order={order_id}, amount={amount}")

        return {
            "error": 0,
            "error_note": "Success",
            "merchant_trans_id": order_id,
            "merchant_confirm_id": click_trans_id,
        }
