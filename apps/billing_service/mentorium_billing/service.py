from __future__ import annotations

import logging
import uuid

from mentorium_db import get_session
from mentorium_db.models import SubscriptionInvoice

from .schemas import InvoiceCreate, InvoiceResponse

logger = logging.getLogger(__name__)


async def create_invoice(payload: InvoiceCreate) -> InvoiceResponse:
    invoice_id = uuid.uuid4().hex

    async with get_session() as session:
        invoice = SubscriptionInvoice(
            id=invoice_id,
            parent_email=payload.parent_email,
            amount_rub=payload.amount_rub,
            status="PENDING",
        )
        session.add(invoice)

    logger.info("Invoice created", extra={"invoice_id": invoice_id})
    return InvoiceResponse(invoice_id=invoice_id, payment_url=None)
