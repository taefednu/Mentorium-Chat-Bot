"""
PayMe payment provider integration (Uzbekistan)
Документация: https://developer.help.paycom.uz/
"""
from __future__ import annotations

import base64
import hashlib
import logging
from decimal import Decimal
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class PayMeProvider:
    """
    PayMe payment provider для Узбекистана
    
    Поддерживает:
    - Создание платёжных ссылок
    - Webhook обработку (Merchant API)
    - Проверку статуса платежа
    """

    def __init__(
        self,
        merchant_id: str | None,
        secret_key: str | None,
        test_mode: bool = True,
    ):
        self.merchant_id = merchant_id
        self.secret_key = secret_key
        self.test_mode = test_mode
        self.enabled = bool(merchant_id and secret_key)

        if not self.enabled:
            logger.warning("PayMe provider disabled: missing merchant_id or secret_key")

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
        Создать ссылку на оплату PayMe
        
        Args:
            amount: Сумма в UZS (копейки, т.е. умножить на 100)
            order_id: ID подписки/платежа
            return_url: URL для возврата после оплаты
            
        Returns:
            URL для оплаты или None если провайдер недоступен
        """
        if not self.enabled:
            logger.warning("Cannot create PayMe link: provider disabled")
            return None

        # Сумма в тийинах (1 UZS = 100 tiyin)
        amount_tiyin = int(amount * 100)

        # Формируем параметры
        params = {
            "m": self.merchant_id,
            "a": str(amount_tiyin),
            "ac.order_id": order_id,
        }

        if return_url:
            params["c"] = return_url

        # Кодируем параметры в base64
        params_str = ";".join([f"{k}={v}" for k, v in params.items()])
        params_base64 = base64.b64encode(params_str.encode()).decode()

        # URL зависит от режима (test/prod)
        base_url = "https://checkout.test.paycom.uz" if self.test_mode else "https://checkout.paycom.uz"

        payment_url = f"{base_url}/{params_base64}"

        logger.info(f"Created PayMe payment link for order {order_id}, amount {amount} UZS")
        return payment_url

    def verify_webhook_signature(self, auth_header: str) -> bool:
        """
        Проверить подпись webhook запроса от PayMe
        
        PayMe отправляет Basic Auth в формате: Paycom:{password}
        где password - это LOGIN из настроек кабинета
        """
        if not self.enabled:
            return False

        try:
            # Декодируем Basic Auth
            auth_type, credentials = auth_header.split(" ")
            if auth_type.lower() != "basic":
                return False

            decoded = base64.b64decode(credentials).decode()
            username, password = decoded.split(":")

            # Проверяем, что username = "Paycom" и password совпадает с secret_key
            return username == "Paycom" and password == self.secret_key

        except Exception as e:
            logger.error(f"Failed to verify PayMe webhook signature: {e}")
            return False

    async def check_payment_status(self, transaction_id: str) -> dict[str, Any] | None:
        """
        Проверить статус платежа через PayMe API
        
        Returns:
            {"status": "paid|pending|cancelled", "amount": Decimal, ...}
        """
        if not self.enabled:
            return None

        # TODO: Реализовать запрос к PayMe Merchant API
        # Требуется отправить JSON-RPC запрос на CheckTransaction
        logger.info(f"Checking PayMe transaction {transaction_id} status")
        return None

    def handle_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Обработать webhook от PayMe (JSON-RPC)
        
        PayMe использует JSON-RPC 2.0 протокол:
        - CheckPerformTransaction: проверка возможности платежа
        - CreateTransaction: создание транзакции
        - PerformTransaction: выполнение платежа
        - CancelTransaction: отмена
        - CheckTransaction: проверка статуса
        
        Returns:
            JSON-RPC ответ
        """
        if not self.enabled:
            return {"error": {"code": -32400, "message": "Provider disabled"}}

        method = payload.get("method")
        params = payload.get("params", {})

        logger.info(f"Received PayMe webhook: method={method}")

        # Обработка методов
        if method == "CheckPerformTransaction":
            return self._check_perform_transaction(params)
        elif method == "CreateTransaction":
            return self._create_transaction(params)
        elif method == "PerformTransaction":
            return self._perform_transaction(params)
        elif method == "CancelTransaction":
            return self._cancel_transaction(params)
        elif method == "CheckTransaction":
            return self._check_transaction(params)
        else:
            return {"error": {"code": -32601, "message": "Method not found"}}

    def _check_perform_transaction(self, params: dict) -> dict:
        """Проверка возможности платежа"""
        # TODO: Проверить, что order_id существует и сумма корректна
        return {"result": {"allow": True}}

    def _create_transaction(self, params: dict) -> dict:
        """Создание транзакции"""
        # TODO: Сохранить транзакцию в БД со статусом PENDING
        return {"result": {"create_time": 1234567890, "transaction": "1", "state": 1}}

    def _perform_transaction(self, params: dict) -> dict:
        """Выполнение платежа"""
        # TODO: Обновить статус на PAID, активировать подписку
        return {"result": {"perform_time": 1234567890, "transaction": "1", "state": 2}}

    def _cancel_transaction(self, params: dict) -> dict:
        """Отмена транзакции"""
        # TODO: Обновить статус на CANCELLED
        return {"result": {"cancel_time": 1234567890, "transaction": "1", "state": -1}}

    def _check_transaction(self, params: dict) -> dict:
        """Проверка статуса транзакции"""
        # TODO: Вернуть текущий статус из БД
        return {"result": {"create_time": 1234567890, "transaction": "1", "state": 2}}
